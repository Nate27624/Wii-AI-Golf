"""Offline synthetic tests for private golfer RAM phase and pointer-pattern analysis."""
import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
spec=importlib.util.spec_from_file_location("golfer_private_analysis",ROOT/"scripts"/"analyze_golfer_private.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def setword(buf,offset,value):
    struct.pack_into(">I",buf,offset,value)

def observations():
    rows=[]
    for i,(stage,phase) in enumerate([(0,"idle")]*4+[(1,"aim_only")]*4+[(2,"idle")]*4):
        main=bytearray(0x100)
        child=bytearray(0x80)
        setword(main,0x08,0x80050000)
        setword(main,0x10,0x80060000)
        setword(main,0x74,100+i)
        # Another word only changes during the aim stage, then stays frozen.
        aim=1 if i<4 else (i-2 if i<8 else 5)
        setword(child,0x20,struct.unpack(">I",struct.pack(">f",float(aim)))[0])
        rec={"frame_start":100+i*3,"frame_end":101+i*3,
             "stage":stage,"phase":phase,"bytes_hex":main.hex(),
             "child_windows":{"+0x008":child.hex()},
             "runtime_scene_address":"0x80030000",
             "runtime_golf_main_address":"0x80040000",
             "watched_child_addresses":{"+0x008":"0x80050000"}}
        rows.append(rec)
    return rows

def wrap(rows):
    return [(row,{"main":bytes.fromhex(row["bytes_hex"]),
                  "child_at_main+0x008":bytes.fromhex(row["child_windows"]["+0x008"])})
            for row in rows]

class PatternTests(unittest.TestCase):
    def test_aim_variable_vs_per_frame_counter(self):
        result=module.summarize(wrap(observations()))
        self.assertEqual(result["sample_count"],12)
        self.assertEqual(result["comparisons"],11)
        self.assertEqual(result["watched_first_level_children"],1)
        self.assertEqual(result["unwatched_main_pointer_offsets"],["+0x010"])
        self.assertEqual(result["changed_word_count"],2)
        rows={r["region"]:r for r in result["candidate_words"]}
        self.assertEqual(rows["main"]["interpretation"],"continuous_during_idle_and_aim")
        self.assertEqual(rows["main"]["relative_offset"],"+0x074")
        self.assertEqual(rows["main"]["positive_integer_steps"],11)
        self.assertEqual(rows["child_at_main+0x008"]["relative_offset"],"+0x020")
        self.assertEqual(rows["child_at_main+0x008"]["interpretation"],"aim_phase_correlated_candidate")
        self.assertEqual(rows["child_at_main+0x008"]["aim_changed_pairs"],3)
        self.assertEqual(rows["child_at_main+0x008"]["idle_changed_pairs"],0)
        report=json.dumps(result)
        for forbidden in ("0x80050000","0x80040000","bytes_hex","1065353216"):
            self.assertNotIn(forbidden,report)
        self.assertFalse(result["confirmed_power"])

    def test_load_actual_private_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"golfer-private.jsonl"
            p.write_text("\n".join(json.dumps(x) for x in observations())+"\n",encoding="utf-8")
            samples=module.load(p)
            self.assertEqual(len(samples),12)
            self.assertEqual(len(samples[0][1]["main"]),0x100)
            self.assertEqual(module.summarize(samples)["changed_word_count"],2)

    def test_refuse_private_file_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"golfer-private.jsonl"
            p.write_text("\n".join(json.dumps(x) for x in observations())+"\n",encoding="utf-8")
            self.assertEqual(module.main(["--input",str(p),"--output",str(p)]),1)

    def test_reject_changed_scene_address(self):
        rows=observations()
        rows[-1]["runtime_scene_address"]="0x80031000"
        with self.assertRaises(ValueError):
            module.summarize(wrap(rows))

    def test_reject_changed_children(self):
        rows=observations()
        rows[-1]["child_windows"]={}
        with self.assertRaises(ValueError):
            module.summarize([(row,{"main":bytes.fromhex(row["bytes_hex"]),
                                    **({"child_at_main+0x008":bytes.fromhex(row["child_windows"]["+0x008"])}
                                      if row["child_windows"] else {})}) for row in rows])

    def test_reject_nonmonotonic_frame_count(self):
        rows=observations()
        rows[-1]["frame_start"]=1
        with self.assertRaises(ValueError):
            module.summarize(wrap(rows))

if __name__=="__main__":unittest.main()
