"""Offline regression: automated minimap summary must not claim contact."""
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
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
    def test_changed_pointer_is_not_compared_as_byte_movement(self):
        a={"phase":"pre","pointer":10,"hex":bytes(128).hex()}
        b={"phase":"post","pointer":20,"hex":(bytes([5])*128).hex()}
        result=module.summary([a,b],{})
        self.assertEqual(result["adjacent_changes"],0)
if __name__=="__main__":unittest.main()
