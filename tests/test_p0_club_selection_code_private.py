"""Synthetic source-audit checks; no Dolphin, disc bytes, or native RAM."""
import importlib.util
from pathlib import Path
import struct
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_p0_club_selection_code_private.py"
spec = importlib.util.spec_from_file_location("club_selector_static", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

def ins(op, rd=3, ra=3, imm=0):
    return (op << 26) | (rd << 21) | (ra << 16) | (imm & 0xffff)

def words(*seq):
    return struct.pack(">" + "I" * len(seq), *seq)

class TestClubSelectionStatic(unittest.TestCase):
    def test_store_ppc_big_endian(self):
        self.assertEqual(audit.decode_access(ins(36,4,30,0x38)),
                         {"op":"stw","reg":4,"base":30,"disp":0x38})
        self.assertEqual(audit.decode_access(ins(38,5,3,0x23))["op"],"stb")
        self.assertEqual(audit.decode_access(ins(44,5,3,0x24))["op"],"sth")

    def test_signed_displacement(self):
        self.assertEqual(audit.decode_access(ins(36,4,3,-1))["disp"], -1)

    def test_signed_backward_branch(self):
        pc=0x8029e630
        self.assertEqual(audit.decode_branch(pc,0x4BFFFFFC)["target"],pc-4)
        self.assertEqual(audit.decode_branch(pc,0x48000005),
                         {"target":pc+4,"link":True})

    def test_cmp_step_store_reported(self):
        code=words(ins(11,3,0,3),ins(14,3,3,1),0x41820008,ins(36,4,3,0x34))
        result=audit.candidate_sites(code,0x8029e62c,audit.SOURCE_UNITS[2],[])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["candidate_object_field_offset"],"+0x034")
        self.assertFalse(result[0]["club_selector_verified"])

    def test_stack_store_excluded(self):
        code=words(ins(11,3,0,2),ins(36,4,1,0x10))
        self.assertEqual(audit.candidate_sites(code,0x8029e62c,audit.SOURCE_UNITS[2],[]),[])

    def test_absolute_store_and_out_of_bounded_field_excluded(self):
        code=words(ins(11,3,0,2),ins(36,4,0,0x20),ins(36,4,3,0x400))
        self.assertEqual(audit.candidate_sites(code,0x8029e62c,audit.SOURCE_UNITS[2],[]),[])

    def test_plain_unrelated_copy_excluded(self):
        code=words(ins(32,5,3,0x20),ins(36,5,3,0x20))
        self.assertEqual(audit.candidate_sites(code,0x8029e62c,audit.SOURCE_UNITS[2],[]),[])

    def test_direct_call_controller_is_scored(self):
        origin=0x8029e62c
        code=words(0x48000041,ins(36,5,3,0x20))
        result=audit.candidate_sites(code,origin,audit.SOURCE_UNITS[2],
                                     [(origin+0x40,origin+0x44)])
        self.assertEqual(result[0]["nearby_direct_controller_calls"],1)

    def test_map_not_arbitrary_or_unverified(self):
        with self.assertRaises(audit.Abstain):
            audit.source_units({"kind":"faked","intervals":[]})
        payload={"kind":"PUBLIC-RSPE01-REV1-TEXT-OBJECT-SPLITS",
                 "game_id":"RSPE01","disc_revision":1,
                 "intervals":[[0x80000000+i*4,0x80000004+i*4,"unit%d"%i]
                              for i in range(101)]}
        with self.assertRaises(audit.Abstain):
            audit.source_units(payload)


    def test_focused_c0_writer_without_ordinal_nearby(self):
        blob=words(ins(36,4,3,0xC0),ins(36,4,1,0xC0),
                   ins(36,4,3,0x40))
        matches=audit.focused_writer_sites(blob,0x8029e62c,audit.SOURCE_UNITS[2])
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]["candidate_store_displacement"],"+0x0C0")
        self.assertFalse(matches[0]["club_selection_writer_verified"])

    def test_private_bank_bad_length_abstains(self):
        with self.assertRaises(audit.Abstain):
            audit.inspect_mem1_bank(bytes(1024), {}, 5)

if __name__=="__main__":
    unittest.main()
