"""Minimap visual effect read-only differential regressions."""
import unittest
from unittest.mock import patch
from wii_ai_golf.minimap_effect_control import observe_effect,summarize_effect

class RPC:
    def call(self,method,args=None):
        if method=="memory.read_u32":
            return {0x804BF868:0x91000000,0x9100009C:0x91000300}.get(args[0],0)
        raise AssertionError(method)
class MinimapEffectTests(unittest.TestCase):
    @patch("wii_ai_golf.minimap_effect_control.observe_landmarks",return_value={"frame_start":5,"frame_end":10,"landmarks":{}})
    @patch("wii_ai_golf.minimap_effect_control.read_bytes",return_value=b"\x00"*128)
    def test_read_is_bounded(self,read,landmarks):
        row=observe_effect(RPC())
        read.assert_called_once_with(unittest.mock.ANY,0x91000300,128)
        self.assertTrue(row["effect_present"])
    def test_change_report_omits_raw_ram(self):
        b=bytearray(128);c=bytearray(128);c[22]=1
        rows=[{"effect_hex":b.hex(),"effect_pointer":2},{"effect_hex":c.hex(),"effect_pointer":2}]
        z=summarize_effect(rows)
        self.assertEqual(z["changed_byte_offsets"],[22])
        self.assertEqual(z["adjacent_changes"],1)
        self.assertNotIn("effect_hex",str(z))
if __name__=="__main__":unittest.main()
