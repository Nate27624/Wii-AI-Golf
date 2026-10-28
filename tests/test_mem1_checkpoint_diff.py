"""Synthetic, license-safe tests for offline whole-MEM1 differential triage."""
from __future__ import annotations
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from unittest.mock import patch
import json
from pathlib import Path
import tempfile
import unittest

from importlib.util import module_from_spec, spec_from_file_location

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location(
    "mem1_checkpoint_diff", ROOT / "src" / "wii_ai_golf" / "audit" /
    "mem1_checkpoint_diff.py")
m = module_from_spec(SPEC)
SPEC.loader.exec_module(m)

CLI_SPEC = spec_from_file_location("mem1_cli", ROOT / "scripts" /
                                   "analyze_mem1_checkpoints.py")
cli = module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(cli)


def snapshots(size=8192):
    src = bytearray(size)
    src[0:8] = b"RSPE01\x00\x01"
    return [bytearray(src) for _ in range(4)]


def put(buf, offset, value):
    buf[offset:offset+4] = value.to_bytes(4, "big")


def with_control_aim_return():
    b0, b1, b2, b3 = snapshots()
    # Delayed idle timer/background word
    for x in (b1,b2,b3):
        put(x, 4096 + 16, 77)
    # B2-only transient that returns to idle baseline
    put(b2, 4096 + 32, 0xACED4321)
    # Stable idle -> B2 changed -> B3 still changed
    for x in (b2,b3):
        put(x, 4096 + 36, 0xDEADBEEF)
    return b0,b1,b2,b3


class WholeMem1OfflineTests(unittest.TestCase):
    def test_changed_idle_aim_return_counts_and_reversible_persistent(self):
        out = m.compare_mem1_views(*with_control_aim_return())
        counts=out["counts"]
        self.assertEqual(counts["pages_examined"],2)
        self.assertEqual(counts["B0_B1_idle_changed_words"],1)
        self.assertEqual(counts["B1_B2_aim_transition_changed_words"],2)
        self.assertEqual(counts["B2_B3_return_transition_changed_words"],1)
        self.assertEqual(counts["B2_only_returned_to_B1_value_words"],1)
        self.assertEqual(counts["B2_B3_persisted_after_stable_idle_words"],1)
        self.assertEqual(counts["B0_B1_stable_then_B2_changed_words"],2)
        self.assertEqual(counts["stable_all_four_words"],2045)
        self.assertEqual(out["top_candidate_pages"][0]["mem1_relative_page"],"+0x001000")

    def test_no_bytes_pointer_values_or_filename_leak(self):
        out=m.compare_mem1_views(*with_control_aim_return())
        public=json.dumps(out)
        for private in ("DEADBEEF","ACED4321","0xDEAD","bytes_hex",
                        "memory.write","rawfile","filesystem"):
            self.assertNotIn(private,public)
        self.assertFalse(out["allowed_to_publish"])
        self.assertFalse(out["power_verified"])
        self.assertFalse(out["game_mode_and_hole_verified"])
        self.assertFalse(out["all_checkpoints_verified_same_live_boot"])

    def test_big_endian_word_equality_does_not_decode_values(self):
        b0,b1,b2,b3=snapshots()
        put(b2,4096,0x80FFFFFF)
        out=m.compare_mem1_views(b0,b1,b2,b3)
        self.assertEqual(out["counts"]["B0_B1_stable_then_B2_changed_words"],1)
        self.assertEqual(out["counts"]["B2_only_returned_to_B1_value_words"],1)
        self.assertEqual(out["word_comparison"],"aligned_32_bit_equality_only")

    def test_identical_exports_have_stale_capture_warning(self):
        out=m.compare_mem1_views(*snapshots())
        self.assertEqual(out["counts"]["pages_with_any_changes"],0)
        self.assertIn("identical",out["next_action"])
        self.assertEqual(out["top_candidate_pages"],[])
        self.assertFalse(out["club_pose_verified"])

    def test_wrong_disc_rev_fails_closed(self):
        b=snapshots()
        b[2][7]=0
        with self.assertRaises(ValueError):
            m.compare_mem1_views(*b)
        b=snapshots()
        b[1][0:6]=b"NOTWII"
        with self.assertRaises(ValueError):
            m.compare_mem1_views(*b)

    def test_mismatched_sizes_and_bad_page_budget_fail(self):
        b=snapshots()
        with self.assertRaises(ValueError):
            m.compare_mem1_views(b[0][:-4],*b[1:])
        with self.assertRaises(ValueError):
            m.compare_mem1_views(*b,page_size=15)
        with self.assertRaises(ValueError):
            m.compare_mem1_views(*b,max_pages=999)

    def test_page_budget_caps_output_with_valid_counts(self):
        b=snapshots(6*4096)
        for off in (4096,8192,12288,16384):
            put(b[2],off,16)
        out=m.compare_mem1_views(*b,max_pages=2)
        self.assertEqual(out["counts"]["pages_with_any_changes"],4)
        self.assertEqual(out["candidate_pages_omitted"],2)
        self.assertEqual(len(out["top_candidate_pages"]),2)
        self.assertTrue(all(x["candidate_only_not_gameplay_verified"]
                            for x in out["top_candidate_pages"]))

    def test_subword_byte_change_still_counts_one_aligned_word(self):
        b=snapshots()
        b[2][4096+2]=1
        out=m.compare_mem1_views(*b)
        self.assertEqual(out["counts"]["B1_B2_aim_transition_changed_words"],1)

    def test_non_aim_background_still_flagged(self):
        b=snapshots()
        put(b[1],4096,1)
        put(b[2],4096,2)
        put(b[3],4096,3)
        out=m.compare_mem1_views(*b)
        self.assertEqual(out["counts"]["B0_B1_stable_then_B2_changed_words"],0)
        self.assertEqual(out["counts"]["B0_B1_idle_changed_words"],1)
        self.assertIn("No u32 changes",out["next_action"])

    def test_native_full_mem1_sparse_files_local_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp)
            images=[]
            for i in range(4):
                p=private/f"MEM1_B{i}.bin"
                with p.open("wb") as fp:
                    fp.write(b"RSPE01\x00\x01")
                    fp.truncate(m.MEM1_SIZE)
                images.append(p)
            # Distinguish B2 at one safe synthetic offset
            with images[2].open("r+b") as fp:
                fp.seek(0x20000)
                fp.write(b"\x12\x34\x56\x78")
            output=private/"local-summary.json"
            out=m.analyze_private_mem1_files(
                images,private_root=private,output=output,max_pages=2)
            self.assertEqual(out["counts"]["B1_B2_aim_transition_changed_words"],1)
            self.assertEqual(json.loads(output.read_text()),out)
            with self.assertRaises(ValueError):
                m.analyze_private_mem1_files(
                    images,private_root=private,output=output)
            self.assertFalse(out["allowed_to_publish"])

    def test_rejects_duplicate_or_external_snapshot_path(self):
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp)
            p=private/"x.bin"
            with p.open("wb") as fp:
                fp.write(b"RSPE01\x00\x01")
                fp.truncate(m.MEM1_SIZE)
            with self.assertRaises(ValueError):
                m.analyze_private_mem1_files(
                    [p]*4,private_root=private,output=private/"summary.json")
            with self.assertRaises(ValueError):
                m.analyze_private_mem1_files(
                    [private.parent/"other.bin"]+[p]*3,
                    private_root=private,output=private/"summary.json")

    def test_rejects_savestate_and_partial_mem1(self):
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp)
            b=private/"Dolphin.sav"
            b.write_bytes(b"not native raw memory")
            with self.assertRaises(ValueError):
                m.analyze_private_mem1_files(
                    [b]*4,private_root=private,output=private/"result.json")

    def test_operator_root_and_symlink_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp)
            missing=private/"missing"
            with self.assertRaises(FileNotFoundError):
                m.analyze_private_mem1_files(
                    [missing]*4,private_root=missing,output=private/"result.json")

    def test_cli_public_printed_shape_excludes_private_page_indices(self):
        report = m.compare_mem1_views(*with_control_aim_return())
        safe = cli._public_counts_only(report)
        encoded = json.dumps(safe)
        self.assertNotIn("top_candidate_pages", encoded)
        self.assertNotIn("mem1_relative_page", encoded)
        self.assertNotIn("+0x001000", encoded)
        self.assertNotIn("0x80000000", encoded)
        self.assertNotIn("DEADBEEF", encoded)
        self.assertTrue(safe["private_page_index_and_word_values_omitted"])
        self.assertFalse(safe["allowed_to_publish"])

    def test_cli_blocks_arbitrary_root_that_could_be_a_git_worktree(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / "Wii-AI-Golf-Data").mkdir()
            untrusted = home / "Wii-AI-Golf"
            untrusted.mkdir()
            args = ["--private-root", str(untrusted),
                    "--b0", str(untrusted / "a.raw"),
                    "--b1", str(untrusted / "b.raw"),
                    "--b2", str(untrusted / "c.raw"),
                    "--b3", str(untrusted / "d.raw"),
                    "--output", str(untrusted / "summary.json")]
            err = StringIO()
            with patch.object(cli, "ROOT", home / "Wii-AI-Golf-Review"):
                with patch.object(cli, "analyze_private_mem1_files") as analyze:
                    with redirect_stderr(err):
                        self.assertEqual(cli.main(args), 1)
                    analyze.assert_not_called()
            self.assertNotIn(str(untrusted), err.getvalue())

    def test_cli_accepts_sibling_private_root_and_prints_counts_only(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            data = home / "Wii-AI-Golf-Data"
            captures = data / "mem1-checkpoints"
            captures.mkdir(parents=True)
            args = ["--private-root", str(captures),
                    "--b0", str(captures / "B0.raw"),
                    "--b1", str(captures / "B1.raw"),
                    "--b2", str(captures / "B2.raw"),
                    "--b3", str(captures / "B3.raw"),
                    "--output", str(captures / "local-summary.json")]
            report = m.compare_mem1_views(*with_control_aim_return())
            stdout = StringIO()
            with patch.object(cli, "ROOT", home / "Wii-AI-Golf-Review"):
                with patch.object(cli, "analyze_private_mem1_files",
                                  return_value=report) as analyze:
                    with redirect_stdout(stdout):
                        self.assertEqual(cli.main(args), 0)
                    analyze.assert_called_once()
            self.assertNotIn("mem1_relative_page", stdout.getvalue())
            self.assertNotIn("+0x001000", stdout.getvalue())
            self.assertIn("local-mem1-four-checkpoint-counts-only",
                          stdout.getvalue())

if __name__ == "__main__":
    unittest.main()
