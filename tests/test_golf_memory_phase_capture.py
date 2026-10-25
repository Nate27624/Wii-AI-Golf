"""Offline regression for read-only phase capture and sanitized RAM differential."""
from __future__ import annotations
import importlib.util,json,struct,sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"scripts")]
from wii_ai_golf.audit.memory_phases import summarize_phase_memory,documented_role

spec=importlib.util.spec_from_file_location("phase_capture",ROOT/"scripts"/"capture_golf_memory_phases.py")
capture=importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)

def row(stage,phase,value,addr=0x80010000,revision=1):
    config=bytearray(0xA0)
    struct.pack_into(">I",config,0x94,4)
    struct.pack_into(">I",config,0x9C,value)
    windows={
        "golf_config":{"address":f"0x{addr:08X}","bytes_hex":config.hex()},
        "golf_field":{"address":"0x80020000","bytes_hex":bytes(0xA8).hex()},
        "sports_sequence":{"address":"0x80030000","bytes_hex":bytes(0xD0).hex()}
    }
    return {"stage":stage,"phase":phase,"game_id":"RSPE01",
            "disc_revision":revision,"game_mode_raw":4,
            "frame_start":100+stage*100,"frame_end":102+stage*100,
            "windows":windows}

class PhaseCaptureTests(unittest.TestCase):
    def test_registered_phases_and_bounds(self):
        self.assertEqual(capture.parse_phases(["idle:6","aim_only:8"]),
                         [("idle",6),("aim_only",8)])
        for malformed in (["idle:0"],["bad:6"],["idle:41"],["idle:six"],[]):
            with self.subTest(malformed=malformed),self.assertRaises(ValueError):
                capture.parse_phases(malformed)

    def test_differential_does_not_leak_private_values(self):
        rows=[row(0,"idle",0x00000000),row(0,"idle",0x00000000),
              row(1,"aim_only",0x3f800000),row(1,"aim_only",0x40000000)]
        annotations=[{"stage":0,"phase":"idle","observation":"unchanged"},
                     {"stage":1,"phase":"aim_only","observation":"camera_moved"}]
        result=summarize_phase_memory(rows,annotations,scope="focused",run_id="test-123")
        self.assertEqual(result["sample_count"],4)
        self.assertEqual(result["changed_word_count"],1)
        found=result["top_changed_relative_words"][0]
        self.assertEqual(found["region"],"golf_config")
        self.assertEqual(found["relative_offset"],"+0x9C")
        self.assertEqual(found["within_phase_changes"],1)
        self.assertEqual(found["at_phase_boundary_changes"],1)
        self.assertEqual(result["human_observations"][1]["observation"],"camera_moved")
        output=json.dumps(result)
        self.assertNotIn("bytes_hex",output)
        self.assertNotIn("80010000",output)
        self.assertNotIn("3f800000",output)
        self.assertNotIn("40000000",output)
        self.assertFalse(result["confirmed_power_address"])

    def test_relocation_is_not_motion(self):
        rows=[row(0,"idle",1),row(1,"aim_only",2,addr=0x80011000)]
        result=summarize_phase_memory(rows,[],scope="focused",run_id="relocated")
        self.assertEqual(result["changed_word_count"],0)
        self.assertEqual(result["skipped_relocated_windows"],1)

    def test_wrong_revision_rejected(self):
        with self.assertRaises(ValueError):
            summarize_phase_memory([row(0,"idle",1,revision=0),
                                   row(0,"idle",2)],[],scope="focused",run_id="rev")
    def test_documented_roles_do_not_invent_power(self):
        self.assertEqual(documented_role("golf_config",0x94),"game_mode")
        self.assertEqual(documented_role("golf_field",0x04),"shadow_pointer")
        self.assertEqual(documented_role("sports_sequence",0x0C),"training_game")
        self.assertEqual(documented_role("golf_config",0x9C),"unknown")

    def test_invalid_public_observation_rejected(self):
        with self.assertRaises(ValueError):
            summarize_phase_memory([row(0,"idle",1),row(0,"idle",1)],
                                   [{"stage":0,"phase":"idle","observation":"my secret path"}],
                                   scope="focused",run_id="private")

    def test_read_only_rpc_and_expected_region_sizes(self):
        ptrs={"golf_config":0x80010000,"golf_field":0x80020000,
              "sports_sequence":0x80030000}
        static={capture.STATIC_STRUCTS[name][0]:ptr for name,ptr in ptrs.items()}
        class StubRPC:
            def __init__(self):self.calls=[];self.frame=101
            def call(self,name,args):
                self.calls.append((name,args))
                if name=="frame.get_count":
                    self.frame+=1
                    return self.frame
                if name=="memory.read_u32":
                    return 4 if args[0]==ptrs["golf_config"]+0x94 else static[args[0]]
                if name=="memory.read_bytes":
                    address,size=args
                    if address==0x80000000:return (b"RSPE01"+b"\\x00"+b"\\x01").hex()
                    return bytes(size).hex()
                raise AssertionError("unexpected controller or write command "+name)
        rpc=StubRPC()
        # Override header response as source-backed 8 bytes; no controller operations are allowed.
        original_call=rpc.call
        def corrected_call(name,args):
            if name=="memory.read_bytes" and args[0]==0x80000000:
                rpc.calls.append((name,args))
                return (b"RSPE01"+bytes([0,1])).hex()
            return original_call(name,args)
        rpc.call=corrected_call
        observed=capture.snapshot(rpc,"focused","idle",0)
        self.assertEqual(set(observed["windows"]),set(ptrs))
        self.assertEqual(len(bytes.fromhex(observed["windows"]["golf_config"]["bytes_hex"])),0xA0)
        self.assertTrue(all(method.startswith("frame.") or method.startswith("memory.read_")
                            for method,args in rpc.calls))

if __name__=="__main__":unittest.main()
