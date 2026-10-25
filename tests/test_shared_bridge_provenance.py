"""Shared bridge identity is identical across S001 audit and S000 lab imports."""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for path in (str(ROOT), str(ROOT / "src")):
    if path in sys.path:
        sys.path.remove(path)
    sys.path.insert(0, path)

from wii_ai_golf.shared.bridge_provenance import (
    ATOMIC, AUTOLOAD, SWING_V1, NEUTRAL_V2,
    inspect_bridge_file, audit_bridge_sources,
    prepare_isolated_legacy_bridge,
)
from scripts import audit_local_swing_bridge


class SharedBridgeIdentityTests(unittest.TestCase):
    def setUp(self):
        context = tempfile.TemporaryDirectory()
        self.addCleanup(context.cleanup)
        self.root = Path(context.name)
        self.active = self.root / "mcp_bridge_swing.py"
        self.backup = self.active.with_name(self.active.name + ".before-neutral-v2.bak")

    def make_files(self):
        self.active.write_text(
            ATOMIC + "\n" + SWING_V1 + "\n" + NEUTRAL_V2 + "\n",
            encoding="utf-8",
        )
        self.backup.write_text(ATOMIC + "\n" + SWING_V1 + "\n", encoding="utf-8")

    def test_s001_cli_and_shared_module_return_exact_same_identity(self):
        self.make_files()
        a = audit_local_swing_bridge.audit_local_bridge(self.active)
        b = audit_bridge_sources(self.active)
        self.assertEqual(a, b)
        self.assertEqual(audit_local_swing_bridge.inspect_bridge(self.active),
                         inspect_bridge_file(self.active))
        self.assertEqual(a["current"]["revision"], "V2-neutral-button-only")
        self.assertEqual(a["saved_pre_v2_backup"]["revision"], "V1-neutral-swing-calls")
        self.assertTrue(a["v1_isolated_trial_possible"])
        self.assertEqual(len(a["current"]["sha256"]), 64)

    def test_read_only_never_calls_dolphin_or_writes_files(self):
        self.make_files()
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        audit_bridge_sources(self.active)
        inspect_bridge_file(self.active)
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, before)

    def test_shared_safe_legacy_copy_and_backward_compatibility(self):
        self.make_files()
        left = prepare_isolated_legacy_bridge(self.active)
        self.assertEqual(left.read_bytes(), self.backup.read_bytes())
        self.assertEqual(audit_local_swing_bridge.prepare_legacy_copy(self.active), left)
        self.assertEqual(inspect_bridge_file(left)["revision"], "V1-neutral-swing-calls")

    def test_autoload_legacy_rejected_for_every_agent(self):
        self.make_files()
        self.backup.write_text(self.backup.read_text() + AUTOLOAD)
        self.assertFalse(audit_bridge_sources(self.active)["v1_isolated_trial_possible"])
        with self.assertRaises(ValueError):
            prepare_isolated_legacy_bridge(self.active)
        with self.assertRaises(ValueError):
            audit_local_swing_bridge.prepare_legacy_copy(self.active)

    def test_unchanged_public_report_keys_for_gui_and_outcome_provenance(self):
        self.make_files()
        identity = inspect_bridge_file(self.active)
        self.assertEqual(set(identity), {
            "exists", "path", "sha256", "bytes", "revision",
            "atomic_marker", "autoload_marker", "swing_v1_marker",
            "neutral_v2_marker", "safe_for_isolated_legacy_copy",
        })
        self.assertNotIn("game_score", identity)
        self.assertNotIn("ball_contact", identity)
        self.assertNotIn("game_score_verified", identity)

    def test_source_text_markers_do_not_certify_live_runtime(self):
        self.make_files()
        info = audit_bridge_sources(self.active)
        self.assertTrue(any("NOT prove" in note for note in info["notes"]))
        self.assertFalse(any("hit" in key for key in info["current"]))


if __name__ == "__main__":
    unittest.main()
