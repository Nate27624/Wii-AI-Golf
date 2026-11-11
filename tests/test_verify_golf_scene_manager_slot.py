"""Synthetic-only smoke/regression checks for scene singleton slot identification."""
import importlib.util
import struct
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location("scene_slot",ROOT/"scripts"/"verify_golf_scene_manager_slot.py")
module=importlib.util.module_from_spec(s)
s.loader.exec_module(module)


def fixture(*, matched=True, ctor_store=True, valid_bss=True, correct_r13=True):
    data=bytearray(0x1A00)
    struct.pack_into(">III",data,0x00,0x100,0x200,0)
    struct.pack_into(">III",data,0x48,0x80006314,0x80184BA4,0)
    struct.pack_into(">III",data,0x90,0x8,0x1780,0)
    struct.pack_into(">II",data,0xD8,0x804BF000,0x5000 if valid_bss else 0x4)
    struct.pack_into(">I",data,0x100,0x3DA0804C if correct_r13 else 0x3DA0804B)
    struct.pack_into(">I",data,0x104,0x61AD5380)
    def write(addr,w):
        struct.pack_into(">I",data,0x200+addr-0x80184BA4,w)
    targets=((0x80184BA4,0x26C),(0x80185484,0x48),(0x801854CC,0x48))
    for i,(addr,length) in enumerate(targets):
        disp=-24232 if matched else -24232-i*4
        write(addr+0x20,(32<<26)|(3<<21)|(13<<16)|(disp&65535))
    write(0x80186130,(32<<26)|(0<<21)|(13<<16)|(-24232&65535))
    if ctor_store:
        write(0x801861FC,(36<<26)|(30<<21)|(13<<16)|(-24232&65535))
    return bytes(data)


class SceneSlotTests(unittest.TestCase):
    def test_source_backed_signature(self):
        x=module.verify(fixture())
        self.assertEqual(x["candidate_storage_address"],"0x804BF4D8")
        self.assertEqual(x["shared_r13_offset"],"-0x5EA8")
        self.assertIsNone(x["scene_manager_runtime_pointer"])

    def test_no_cross_callsite_consensus(self):
        with self.assertRaisesRegex(ValueError,"unique"):
            module.verify(fixture(matched=False))

    def test_missing_constructor_store(self):
        with self.assertRaisesRegex(ValueError,"constructor"):
            module.verify(fixture(ctor_store=False))

    def test_r13_base_changes_outside_bss(self):
        with self.assertRaisesRegex(ValueError,"BSS"):
            module.verify(fixture(correct_r13=False))

    def test_declared_bss_excludes_slot(self):
        with self.assertRaisesRegex(ValueError,"BSS"):
            module.verify(fixture(valid_bss=False))

    def test_bad_dol_rejected(self):
        with self.assertRaises(ValueError):
            module.verify(b"bad")


if __name__=="__main__":
    unittest.main()
