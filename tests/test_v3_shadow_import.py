"""Synthetic safety controls for offline V2 -> V3 shadow migration."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from wii_ai_golf.orchestration import shadow_import as shadow
from wii_ai_golf.orchestration import state as model

MAIN = "a" * 40
GOAL = "b" * 40
MANAGER = "S000-manager-v3-synthetic"


def row(task, instance, role, status, paths, thread=485):
    return {"instance": instance, "role": role, "task_id": task, "state": status,
            "thread": "https://github.com/Nate27624/Wii-AI-Golf/issues/" + str(thread),
            "owned_paths": paths, "objective": "Safely preserve V2 research scope.",
            "acceptance": "Check synthetic controls; no live game actions."}


def fixture():
    return {"version": 1, "revision": 68, "main_sha": MAIN,
            "manager_id": MANAGER, "assignments": [
                row("V3-P0-LEASE-CORE", MANAGER, "S000", "CLAIMED",
                    ["docs/v3-orchestration.md"]),
                row("S002-P0-PROVENANCE", "S002-test", "S002", "CLAIMED",
                    ["scripts/source.py", "tests/source.py"], 415),
                row("S003-COMPLETE", "S003-test", "S003", "COMPLETED",
                    ["src/physics.py"], 467),
                row("S005-PAUSED", "S005-test", "S005", "PARKED",
                    ["src/evaluation.py"], 6),
                row("S001-ASSIGNED", "S001-test", "S001", "ASSIGNED",
                    ["scripts/control.py"], 390)]}


def as_comment(data):
    return ("[S000-manager] ASSIGNMENT ROSTER V2\n" +
            shadow.BEGIN + "\n" + json.dumps(data) + "\n" + shadow.END)


def parse(data=None, **overrides):
    defaults = {"revision": 68, "main_sha": MAIN, "manager_id": MANAGER,
                "comment_id": 7143524743}
    defaults.update(overrides)
    return shadow.parse_roster(as_comment(fixture() if data is None else data),
                               **defaults)


class ShadowTests(unittest.TestCase):
    def test_all_states_and_holds_preserved_without_v3_dispatch(self):
        parsed = parse()
        self.assertEqual(parsed["reservation_count"], 6)
        result = shadow.preview(parsed, goal_sha=GOAL)
        self.assertEqual(result["mode"], "SHADOW_READ_ONLY")
        self.assertFalse(result["cutover_eligible"])
        s = model.validate(result["state"])
        self.assertEqual(len(s["tasks"]), 6)
        self.assertEqual(len(s["holds"]), 5)
        self.assertEqual(s["tasks"][model.MANAGER]["status"], "BLOCKED")
        self.assertEqual(s["tasks"]["S002-P0-PROVENANCE"]["status"], "BLOCKED")
        self.assertEqual(s["tasks"]["S003-COMPLETE"]["status"], "CLOSED")
        self.assertEqual(s["tasks"]["S005-PAUSED"]["status"], "PARKED")
        self.assertEqual(s["tasks"]["S001-ASSIGNED"]["status"], "BLOCKED")
        self.assertEqual(result["original_v2_states"]["S001-ASSIGNED"], "ASSIGNED")
        self.assertEqual(result["source"]["comment_id"], 7143524743)
        with self.assertRaises(model.LeaseError):
            model.acquire(s, model.MANAGER, "mgr1", "S000", 10)
        with self.assertRaises(model.LeaseError):
            model.acquire(s, "S002-P0-PROVENANCE", "run1", "S002", 10)

    def test_nonmutation_and_determinism(self):
        data = fixture()
        original = copy.deepcopy(data)
        a = parse(data)
        b = parse(data)
        self.assertEqual(a, b)
        self.assertEqual(data, original)
        self.assertEqual(shadow.preview(a, goal_sha=GOAL),
                         shadow.preview(b, goal_sha=GOAL))

    def test_source_revision_and_main_pins(self):
        with self.assertRaises(shadow.ShadowError):
            parse(revision=67)
        with self.assertRaises(shadow.ShadowError):
            parse(main_sha="c" * 40)
        with self.assertRaises(shadow.ShadowError):
            parse(manager_id="someone-else")
        with self.assertRaises(shadow.ShadowError):
            parse(comment_id=0)

    def test_malformed_markers_truncation_and_duplicate_json_members(self):
        value = as_comment(fixture())
        for corrupt in (value.replace(shadow.BEGIN, ""),
                        value + shadow.END,
                        value.replace(shadow.END, shadow.BEGIN),
                        value.replace("[S000-manager]", "[forged]"),
                        "[S000-manager] ASSIGNMENT ROSTER V2\n" +
                        shadow.BEGIN + '{"version":1,"version":1}' + shadow.END):
            with self.subTest(corrupt=corrupt[:30]), self.assertRaises(
                    shadow.ShadowError):
                shadow.parse_roster(corrupt, revision=68, main_sha=MAIN,
                                    manager_id=MANAGER, comment_id=1)

    def test_duplicate_path_and_prefix_overlap_fail(self):
        for duplicate in ("scripts/source.py", "scripts/source.py/other",
                          "scripts/SOURCE.py"):
            data = fixture()
            data["assignments"][3]["owned_paths"] = [duplicate]
            with self.subTest(path=duplicate), self.assertRaises(
                    (shadow.ShadowError, model.LeaseError)):
                parse(data)

    def test_duplicate_task_and_instance_fail(self):
        data = fixture()
        data["assignments"][2]["task_id"] = "S002-P0-PROVENANCE"
        with self.assertRaises(shadow.ShadowError):
            parse(data)
        data = fixture()
        data["assignments"][2]["instance"] = "S002-test"
        with self.assertRaises(shadow.ShadowError):
            parse(data)

    def test_only_one_manager_can_be_source(self):
        data = fixture()
        data["assignments"][0]["instance"] = "someone-else"
        with self.assertRaises(shadow.ShadowError):
            parse(data)
        data = fixture()
        data["assignments"][0]["role"] = "S003"
        with self.assertRaises(shadow.ShadowError):
            parse(data)

    def test_bad_thread_or_control_text_fails(self):
        data = fixture()
        data["assignments"][2]["thread"] = "https://evil.invalid/issues/467"
        with self.assertRaises(shadow.ShadowError):
            parse(data)
        data = fixture()
        data["assignments"][2]["objective"] = "secret\nnew line"
        with self.assertRaises(model.LeaseError):
            parse(data)

    def test_invalid_unknown_states_are_not_guessed(self):
        data = fixture()
        data["assignments"][1]["state"] = "RUNNING"
        with self.assertRaises(shadow.ShadowError):
            parse(data)

    def test_unknown_extra_fields_and_incomplete_rows_fail(self):
        data = fixture()
        data["unverified"] = True
        with self.assertRaises(shadow.ShadowError):
            parse(data)
        data = fixture()
        del data["assignments"][3]["owned_paths"]
        with self.assertRaises(shadow.ShadowError):
            parse(data)

    def test_overlong_or_empty_roster_is_not_partially_accepted(self):
        data = fixture()
        data["assignments"] = []
        with self.assertRaises(shadow.ShadowError):
            parse(data)
        data = fixture()
        data["assignments"] = data["assignments"] * 5
        with self.assertRaises(shadow.ShadowError):
            parse(data)

    def test_goal_must_be_independently_pinned(self):
        p = parse()
        for bad in ("", MAIN.upper(), "unverified", None):
            with self.subTest(goal=bad), self.assertRaises(shadow.ShadowError):
                shadow.preview(p, goal_sha=bad)

    def test_cannot_shadow_reserved_manager_task_id(self):
        data = fixture()
        data["assignments"][2]["task_id"] = model.MANAGER
        with self.assertRaises(shadow.ShadowError):
            parse(data)

    def test_boolean_schema_is_not_version_one(self):
        data = fixture()
        data["version"] = True
        with self.assertRaises(shadow.ShadowError):
            parse(data)


if __name__ == "__main__":
    unittest.main()
