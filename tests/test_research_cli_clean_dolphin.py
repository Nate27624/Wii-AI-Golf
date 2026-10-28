"""Synthetic-only P0 safety gates for the MAINTAINED research_cli.py V1 entrypoint.

No Dolphin, controller, RPC, savestate, network, or real operator files.
"""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import research_cli
from wii_ai_golf.lab.github_sync import SyncReport
from wii_ai_golf.shared import bridge_provenance


class P0CleanCliV1Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "Wii-AI-Golf"
        (self.repo / "research").mkdir(parents=True)
        (self.repo / "scripts").mkdir()
        self.tools = self.repo.parent / "tools"
        self.tools.mkdir()
        self.clean = self.tools / "FelkDolphin-Clean"
        self.bridge = self.tools / "mcp_bridge_swing_legacy_eval.py"

    def prepare_clean(self):
        self.clean.mkdir()
        (self.clean / "User").mkdir()
        (self.clean / "Dolphin.exe").write_bytes(b"fake EXE not executable")
        (self.clean / "portable.txt").write_text("", encoding="utf-8")
        (self.repo / "research" / "launch.local.json").write_text("{}", encoding="utf-8")
        (self.repo / "research" / "savestates.local.json").write_text("{}", encoding="utf-8")

    def test_missing_clean_setup_fails_without_creating_files(self):
        with self.assertRaisesRegex(RuntimeError, "safe launch blocked"):
            research_cli.v1_clean_boot_args(self.repo)
        self.assertFalse(self.clean.exists())

    def test_missing_one_required_input_fails_closed(self):
        for missing in ("Dolphin.exe", "portable.txt", "User", "launch.local.json",
                        "savestates.local.json"):
            with self.subTest(missing=missing):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp) / "Wii-AI-Golf"
                    (root / "research").mkdir(parents=True)
                    clean = root.parent / "tools" / "FelkDolphin-Clean"
                    clean.mkdir(parents=True)
                    (clean / "User").mkdir()
                    (clean / "Dolphin.exe").write_bytes(b"fake")
                    (clean / "portable.txt").write_text("")
                    (root / "research" / "launch.local.json").write_text("{}")
                    (root / "research" / "savestates.local.json").write_text("{}")
                    target = (clean / missing if missing in ("Dolphin.exe", "portable.txt", "User")
                              else root / "research" / missing)
                    if target.is_dir():
                        target.rmdir()
                    else:
                        target.unlink()
                    with self.assertRaises(RuntimeError):
                        research_cli.v1_clean_boot_args(root)

    def test_portable_marker_directory_is_not_accepted(self):
        self.prepare_clean()
        (self.clean / "portable.txt").unlink()
        (self.clean / "portable.txt").mkdir()
        with self.assertRaisesRegex(RuntimeError, "portable.txt"):
            research_cli.v1_clean_boot_args(self.repo)

    def test_alternate_user_environment_without_portable_marker_blocks_dispatch(self):
        # The explicit config target is not evidence that native Dolphin will
        # choose it; require the reviewed portable-root selector before launch.
        self.prepare_clean()
        (self.clean / "portable.txt").unlink()
        alternate = self.repo.parent / "alternate-dolphin-user"
        alternate.mkdir()
        with patch.dict("os.environ", {"DOLPHIN_EMU_USERPATH": str(alternate)}):
            code, calls = self.patched_main(["v1", "--live", "--no-upload"])
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        self.assertFalse((self.clean / "portable.txt").exists())

    def test_explicit_paths_correct_order_no_legacy_fallback(self):
        self.prepare_clean()
        args = research_cli.v1_clean_boot_args(self.repo)
        self.assertEqual(args, [
            "--dolphin", str(self.clean / "Dolphin.exe"),
            "--dolphin-user", str(self.clean / "User"),
            "--config", str(self.repo / "research" / "launch.local.json"),
            "--catalog", str(self.repo / "research" / "savestates.local.json")
        ])
        self.assertNotIn(str(self.tools / "FelkDolphin" / "Dolphin.exe"), args)

    def patched_main(self, commands):
        from contextlib import ExitStack
        with ExitStack() as stack:
            stack.enter_context(patch.object(research_cli, "ROOT", self.repo))
            stack.enter_context(patch.object(research_cli, "DATA",
                                             self.repo.parent / "Wii-AI-Golf-Data"))
            stack.enter_context(patch.object(research_cli, "sync_merged_main",
                                             return_value=SyncReport("up_to_date")))
            stack.enter_context(patch.object(bridge_provenance, "inspect_bridge_file",
                                             return_value={
                                                 "revision": "V1-neutral-swing-calls",
                                                 "safe_for_isolated_legacy_copy": True
                                             }))
            fake = stack.enter_context(patch.object(research_cli, "_run", return_value=0))
            stack.enter_context(patch.object(research_cli, "_fresh_human_labels",
                                             return_value={
                                                 "capture_status": "sanitized_human_annotation_only",
                                                 "human": {"contact_human": "unknown"}
                                             }))
            result = research_cli.main(commands)
            return result, fake.call_args_list

    def test_live_v1_uses_one_canonical_boot_and_zero_a_prime(self):
        self.prepare_clean()
        code, calls = self.patched_main(["v1", "--live", "--no-upload",
                                         "--a-lead", "0"])
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        argv = calls[0].args[0]
        self.assertEqual(argv.count("--send-live"), 1)
        self.assertEqual(argv.count("--send-live-swing"), 1)
        self.assertEqual(argv[argv.index("--dolphin") + 1],
                         str(self.clean / "Dolphin.exe"))
        self.assertEqual(argv[argv.index("--dolphin-user") + 1],
                         str(self.clean / "User"))
        self.assertEqual(argv[argv.index("--bridge") + 1],
                         str(self.bridge))
        self.assertEqual(argv[argv.index("--a-prime-requests") + 1], "0")
        self.assertEqual(argv[argv.index("--a-lead-frames") + 1], "0")
        self.assertEqual(argv[argv.index("--script") + 1], "collect_outcome_transition.py")

    def test_a_lead_45_modifies_only_a_lead_argument(self):
        self.prepare_clean()
        _, a = self.patched_main(["v1", "--live", "--no-upload", "--a-lead", "0"])
        _, b = self.patched_main(["v1", "--live", "--no-upload", "--a-lead", "45"])
        x, y = list(a[0].args[0]), list(b[0].args[0])
        index = x.index("--a-lead-frames") + 1
        self.assertEqual(index, y.index("--a-lead-frames") + 1)
        self.assertEqual(x[:index] + x[index+1:], y[:index] + y[index+1:])
        self.assertEqual(x[index], "0")
        self.assertEqual(y[index], "45")

    def test_missing_clean_setup_blocks_live_dispatch(self):
        code, calls = self.patched_main(["v1", "--live", "--no-upload"])
        self.assertEqual(code, 2)
        self.assertEqual(len(calls), 0)

    def test_offline_test_path_does_not_require_clean_dolphin(self):
        code, calls = self.patched_main([
            "test", "--no-upload", "--pattern",
            "test_research_cli_clean_dolphin.py"
        ])
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("--send-live", calls[0].args[0])


if __name__ == "__main__":
    unittest.main()
