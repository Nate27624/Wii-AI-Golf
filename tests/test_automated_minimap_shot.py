"""Offline regression: automated minimap summary must not claim contact."""
import importlib.util
from pathlib import Path
import unittest
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("auto_minimap",ROOT/"scripts"/"collect_automated_minimap_shot.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class AutomaticMinimapTests(unittest.TestCase):
    def test_byte_deltas_and_no_contact_claim(self):
        zero=bytes(128)
        changed=bytearray(zero);changed[84]=3
        rows=[{"phase":"pre","pointer":10,"hex":zero.hex()},
              {"phase":"post","pointer":10,"hex":changed.hex()}]
        result=module.summary(rows,{"state":"finished"})
        self.assertEqual(result["changed_byte_offsets"],[84])
        self.assertEqual(result["adjacent_changes"],1)
        self.assertEqual(result["phase_counts"],{"pre":1,"post":1})
        self.assertEqual(result["claim"],"AUTOMATED_SWING_COMMAND_NOT_VERIFIED_BALL_CONTACT")
        self.assertNotIn("hex",result)
    def test_idle_control_has_no_swing_dispatch(self):
        raw=bytes(128).hex()
        result=module.summary([{"phase":"pre","pointer":10,"hex":raw},
                               {"phase":"post","pointer":10,"hex":raw}],None,"idle_control")
        self.assertEqual(result["condition"],"idle_control")
        self.assertFalse(result["swing_dispatch_received"])
        self.assertEqual(result["adjacent_changes"],0)
        public=module.public_summary(result,"test-idle")
        self.assertEqual(public["condition"],"idle_control")
    def test_published_summary_excludes_raw_private_values(self):
        original=module.summary([{"phase":"pre","pointer":123,"hex":bytes(128).hex()}],{})
        original.update({"raw_path":"C:/private/location","secret":"must-not-upload"})
        published=module.public_summary(original,"20261025T013043Z")
        self.assertEqual(published["kind"],"automated-minimap-effect")
        self.assertEqual(published["changed_byte_offsets"],[])
        for prohibited in ("raw_path","secret","hex","pointer"):
            self.assertNotIn(prohibited,str(published))
    def test_changed_pointer_is_not_compared_as_byte_movement(self):
        a={"phase":"pre","pointer":10,"hex":bytes(128).hex()}
        b={"phase":"post","pointer":20,"hex":(bytes([5])*128).hex()}
        result=module.summary([a,b],{})
        self.assertEqual(result["adjacent_changes"],0)
if __name__=="__main__":unittest.main()
