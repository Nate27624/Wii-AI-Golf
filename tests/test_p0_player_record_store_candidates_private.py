"""Entirely fabricated PPC words; NEVER reads native game RAM in CI."""
import contextlib
import io
import json
import struct
import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import audit_p0_player_record_store_candidates_private as s

BASE=0x80001000
UNITS=(("RPGolPlayer",BASE,BASE+32),("RPGolPlayerManager",BASE+32,BASE+64))

def w(op,rs,ra,d):
    return (op << 26) | (rs << 21) | (ra << 16) | (d & 0xffff)

def sample():
    arr=[0x60000000]*16
    arr[0]=w(52,3,30,0x30)   # stfs candidate
    arr[1]=w(36,7,31,0x90)   # stw candidate
    arr[2]=w(54,8,31,0x34)   # stfd; not exact four-byte store
    arr[8]=w(52,2,9,0x30)   # manager candidate
    arr[9]=w(52,2,9,-0x30)  # negative displacement
    return b''.join(struct.pack('>I',x) for x in arr)

class Tests(unittest.TestCase):
    def test_decode_and_signed(self):
        self.assertEqual(s.decode_dform_store(w(52,9,3,-1)),('stfs',9,3,-1))
        self.assertIsNone(s.decode_dform_store(0x60000000))
        with self.assertRaises(ValueError):s.decode_dform_store(-1)

    def test_two_source_units_and_width(self):
        x=s.scan_candidate_stores(sample(),BASE,UNITS)
        self.assertEqual(x['candidates'][0]['dform_store_count'],2)
        self.assertEqual(x['candidates'][0]['word_width_store_count'],2)
        self.assertEqual(x['candidates'][1]['word_width_store_count'],0)
        self.assertEqual(x['candidates'][-1]['dform_store_count'],1)
        self.assertEqual(x['candidates'][-1]['candidate_sites'][0]['opcode'],'stw')
        self.assertFalse(x['game_power_ram_verified'])

    def test_no_raw_private_values_or_addresses(self):
        x=s.scan_candidate_stores(sample(),BASE,UNITS)
        raw=json.dumps(x)
        self.assertNotIn('0x80001000',raw)
        self.assertNotIn('0x60000000',raw)
        self.assertNotIn('ball-study-20261027',raw)
        self.assertFalse(x['record_word_changes_source_attributed'])
        self.assertFalse(x['approved_for_training'])

    def test_truncation_and_missing_owner(self):
        for a,b,u in ((sample()[:-1],BASE,UNITS),(sample(),BASE,UNITS[:1]),(sample(),BASE+4,UNITS)):
            with self.assertRaises(ValueError):s.scan_candidate_stores(a,b,u)

    def test_false_positive_other_unit(self):
        u=(("Other",BASE,BASE+32),("RPGolPlayerManager",BASE+32,BASE+64))
        with self.assertRaises(ValueError):s.scan_candidate_stores(sample(),BASE,u)

    def test_no_candidate_still_not_proof_of_absence(self):
        x=s.scan_candidate_stores(b'\x60\0\0\0'*16,BASE,UNITS)
        self.assertTrue(all(v['dform_store_count']==0 for v in x['candidates']))
        self.assertFalse(x['indexed_store_and_other_unit_coverage_complete'])

    def test_cli_failure_hides_private_path(self):
        err=io.StringIO()
        with contextlib.redirect_stderr(err):
            code=s.main(['--private-session','SECRET-PRIVATE-NAME','--data-root','/missing'])
        self.assertEqual(code,2)
        self.assertNotIn('SECRET',err.getvalue())

if __name__=='__main__':
    unittest.main()
