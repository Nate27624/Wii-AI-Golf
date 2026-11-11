"""Source-anchored offline memory audit regression tests."""
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("golf_memory_regions",ROOT/"scripts"/"audit_golf_memory_regions.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def sample(phase,value,base="0x80010000"):
    window=bytearray(0xA0)
    window[0x94:0x98]=(4).to_bytes(4,"big")
    window[0x9C:0xA0]=value.to_bytes(4,"big")
    return {"game_id":"RSPE01","disc_revision":1,"phase":phase,
            "windows":{"golf_config":{"address":base,"bytes_hex":window.hex()}}}

class RegionAuditTests(unittest.TestCase):
    def test_phase_boundary_and_within_phase(self):
        result=module.analyze([sample("pre",1),sample("pre",1),
                               sample("post",2),sample("post",3)])
        self.assertEqual(result["changed_word_count"],1)
        entry=result["top_changed_words"][0]
        self.assertEqual(entry["offset_hex"],"+0x9C")
        self.assertEqual(entry["known_role"],"undocumented")
        self.assertEqual(entry["within_phase"],1)
        self.assertEqual(entry["across_phase"],1)

    def test_relocated_instance_not_false_motion(self):
        result=module.analyze([sample("pre",1),sample("post",2,"0x80020000")])
        self.assertEqual(result["changed_word_count"],0)
        self.assertEqual(result["relocation_skips"],1)

    def test_visual_effect_tail_is_pointer_pattern_not_pose(self):
        def row(phase,ptr):
            raw=bytearray(128)
            raw[124:128]=ptr.to_bytes(4,"big")
            return {"phase":phase,"pointer":0x91BF48BC,"hex":raw.hex()}
        result=module.analyze([row("pre",0x81659250),row("post",0x816596B0)])
        entry=result["top_changed_words"][0]
        self.assertEqual(entry["offset_hex"],"+0x7C")
        self.assertEqual(entry["pointer_like_transitions"],1)
        self.assertEqual(entry["known_role"],"rendering_effect_undocumented")
        self.assertNotIn("81659250",str(result))

    def test_documented_roles(self):
        self.assertEqual(module.known_role("golf_config",0x94),"game_mode")
        self.assertEqual(module.known_role("golf_field",0x04),"player_shadow_ptr")
        self.assertEqual(module.known_role("sports_sequence",0x08),"sequence")

    def test_wrong_revision_rejected(self):
        bad=sample("pre",1)
        bad["disc_revision"]=0
        with self.assertRaises(ValueError):
            module.analyze([bad,sample("post",2)])

if __name__=="__main__":unittest.main()
