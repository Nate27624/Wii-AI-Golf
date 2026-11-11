"""Synthetic-only Felk crash triage checks. Never launches Dolphin."""
from __future__ import annotations

from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import json
import tempfile
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import triage_felk_startup_crash_offline as triage


def bridge(*, v2, startup=0, autoload=False):
    markers = [
        "# WII_AI_GOLF_ATOMIC_TRACE_V1",
        "# WII_AI_GOLF_SWING_TRACE_V1",
    ]
    if v2:
        markers.append("# WII_AI_GOLF_SWING_NEUTRAL_BUTTON_ONLY_V2")
    if autoload:
        markers.append("# WII_AI_GOLF_STARTUP_STATE_V1")
    return "\n".join(markers + [
        "import math",
        "x = 2" if startup == 0 else "x = 5",
        "def tick():",
        "    return math.sin(0)",
        ""]) + "\n"


def xml(event_id="1000", app="Dolphin.exe", module="python311.dll",
        code="c0000005"):
    return f'''<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
      <System><Provider Name="Application Error"/>
        <EventID>{event_id}</EventID>
        <TimeCreated SystemTime="2026-10-27T21:00:00.000Z"/>
        <Computer>PRIVATE-PC-NOT-FOR-PUBLIC</Computer>
      </System>
      <EventData>
        <Data Name="AppName">{app}</Data>
        <Data Name="ModuleName">C:\\Private\\Local\\{module}</Data>
        <Data Name="ExceptionCode">{code}</Data>
        <Data Name="AppPath">C:\\Private\\My Stuff\\Dolphin.exe</Data>
      </EventData>
    </Event>'''


class OfflineStartupCrashTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.v2 = self.root / "mcp_bridge_swing.py"
        self.v1 = self.root / "mcp_bridge_swing_legacy_eval.py"
        self.v2.write_text(bridge(v2=True), encoding="utf-8")
        self.v1.write_text(bridge(v2=False), encoding="utf-8")
        self.event = self.root / "event.xml"
        self.event.write_text(xml(), encoding="utf-8")

    def report(self, **kwargs):
        return triage.triage_bridge_startup(
            self.v2, self.v1, event_xml=self.event, **kwargs)

    def test_matching_dolphin_access_violation_is_only_provenance(self):
        report = self.report()
        self.assertEqual(report["active"]["revision"], "V2-neutral-button-only")
        self.assertEqual(report["legacy"]["revision"], "V1-neutral-swing-calls")
        self.assertTrue(report["windows_error_evidence"][
            "event_is_dolphin_app_error_1000"])
        self.assertTrue(report["windows_error_evidence"][
            "event_exception_code_matches_exit_code"])
        self.assertEqual(report["windows_error_evidence"][
            "faulting_module_bucket"], "python_runtime")
        for key in ("fresh_dolphin_started", "ball_movement_verified",
                    "training_allowed", "allowed_to_publish",
                    "controller_input_sent", "savestate_loaded"):
            self.assertFalse(report[key])

    def test_python_startup_structure_identical_with_v2_marker_only(self):
        report = self.report()
        self.assertFalse(report["module_level_executable_structure_differs"])
        self.assertEqual(report["module_level_statement_edit_count"], 0)
        self.assertFalse(report["module_level_import_set_differs"])

    def test_python_startup_structure_difference_detected(self):
        self.v1.write_text(bridge(v2=False, startup=2), encoding="utf-8")
        report = self.report()
        self.assertTrue(report["module_level_executable_structure_differs"])
        self.assertGreater(report["module_level_statement_edit_count"], 0)

    def test_faulting_module_bucket_is_not_root_cause_claim(self):
        self.event.write_text(xml(module="nvoglv64.dll"), encoding="utf-8")
        report = self.report()
        self.assertEqual(report["windows_error_evidence"][
            "faulting_module_bucket"], "graphics_stack")
        self.assertFalse(report["ball_movement_verified"])

    def test_non_dolphin_windows_event_cannot_support_claim(self):
        self.event.write_text(xml(app="NotDolphin.exe"), encoding="utf-8")
        report = self.report()
        self.assertFalse(report["windows_error_evidence"][
            "event_is_dolphin_app_error_1000"])
        self.assertFalse(report["windows_error_evidence"][
            "event_exception_code_matches_exit_code"])

    def test_exception_code_mismatch_detected(self):
        self.event.write_text(xml(code="c0000409"), encoding="utf-8")
        self.assertFalse(self.report()["windows_error_evidence"][
            "event_exception_code_matches_exit_code"])

    def test_non_1000_event_is_not_accepted_as_application_error(self):
        self.event.write_text(xml(event_id="1001"), encoding="utf-8")
        self.assertFalse(self.report()["windows_error_evidence"][
            "event_is_dolphin_app_error_1000"])

    def test_bad_xml_or_entity_fails_closed(self):
        self.event.write_text("<!DOCTYPE foo><Event/>", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.report()
        self.event.write_text("<Event>", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.report()

    def test_unknown_marker_and_autoload_rejected(self):
        self.v1.write_text(bridge(v2=True), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.report()
        self.v1.write_text(bridge(v2=False, autoload=True), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.report()

    def test_script_log_is_summarized_not_printed(self):
        log = self.root / "Script.txt"
        log.write_text(
            "Traceback (most recent call last)\n"
            "C:\\Private\\Sensitive\\MyUser\\TokenWasHere.py\n"
            "script error\n", encoding="utf-8")
        info = self.report(script_log=log)
        self.assertTrue(info["scripting_log_evidence"][
            "mentions_python_traceback"])
        self.assertTrue(info["scripting_log_evidence"]["mentions_script_error"])
        self.assertNotIn("TokenWasHere", json.dumps(info))

    def test_no_paths_or_raw_event_fields_in_json(self):
        report = self.report()
        data = json.dumps(report)
        for forbidden in (str(self.root), "PRIVATE-PC-NOT-FOR-PUBLIC",
                          "My Stuff", "Local", "AppPath", "python311.dll"):
            self.assertNotIn(forbidden, data)
        self.assertFalse(report["allowed_to_publish"])

    def test_no_event_still_allows_offline_structure_audit(self):
        x = triage.triage_bridge_startup(self.v2, self.v1)
        self.assertFalse(x["windows_error_evidence"][
            "application_error_event_supplied"])

    def test_invalid_utf8_and_symlink_rejected(self):
        self.v1.write_bytes(b"\xff\xfe")
        with self.assertRaises(UnicodeError):
            self.report()
        self.v1.write_text(bridge(v2=False), encoding="utf-8")
        alias = self.root / "alias.py"
        try:
            alias.symlink_to(self.v2)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks unavailable")
        with self.assertRaises(ValueError):
            triage.triage_bridge_startup(alias, self.v1)

    def test_cli_error_redacts_private_paths(self):
        output = StringIO()
        with redirect_stderr(output):
            code = triage.main([
                "--current-bridge", str(self.v2),
                "--legacy-bridge", str(self.root / "PRIVATE-ABSENT.py")])
        self.assertEqual(code, 1)
        self.assertNotIn(str(self.root), output.getvalue())

if __name__ == "__main__":
    unittest.main()
