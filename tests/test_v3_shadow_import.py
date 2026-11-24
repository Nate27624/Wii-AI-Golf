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

class ParsedSourceIntegrityTests(unittest.TestCase):
    def test_mutated_source_after_parse_fails_closed(self):
        for mutate in (
            lambda r: r["value"]["assignments"][1]["owned_paths"].append(
                "scripts/unreviewed.py"),
            lambda r: r.update({"comment_url": "https://wrong.invalid/source"}),
            lambda r: r.update({"reservation_count": 5}),
            lambda r: r.update({"sha256": "0" * 64}),
        ):
            parsed = parse()
            mutate(parsed)
            with self.assertRaises(shadow.ShadowError):
                shadow.preview(parsed, goal_sha=GOAL)


class FrozenLiveRosterRevision68Tests(unittest.TestCase):
    """Read-only real public roster data frozen at #320 comment 7143524743."""

    def test_exact_authenticated_source_snapshot_shape(self):
        # Authenticated GitHub fetch occurred when fixture was frozen; runtime
        # never contacts GitHub. Synthetic GOAL does NOT approve cutover.
        body = "[S000-manager] ASSIGNMENT ROSTER V2\nmanager_id: S000-manager-v3-successor-20261124-c\n\n**REVISION #68 — sole S000 succession + isolated read-only shadow migration.** Supersedes [rev67](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-7143285535); operator requested this chat assume S000. The permanent V3 S000-MANAGER is a planned Work Queue task, NOT an activated V3 worker. 19 V2 rows preserved, same 75 existing owned paths, with the prior manager instance changed only to its explicitly authorized successor. One separate S000 implementation task adds four new-only paths (20 rows / 79 reservations), claim [on #485](https://github.com/Nate27624/Wii-AI-Golf/issues/485#issuecomment-7143510484). Existing S001–S005 owners, states and paths unchanged. No new PR after #488 at review; four new path names disjoint from all current V2 reservations and from the staged V3 #486/#487/#488 files. The full 150-open-PR filename re-audit is pending before changes; do not infer completed global overlap verification. Main stays 501361a9742f399891604a2c3f4b818de9b51fa8. Shadow is blocked/read-only and creates no ownership; production cutover remains forbidden. Latest exact-head #488 CI Windows/Ubuntu focused/full green: 45479414021, 45479414005, 45479414117. V3 stack still draft/unmerged.\n\n<!-- V2_ASSIGNMENTS_JSON_BEGIN -->\n{\n  \"version\": 1,\n  \"revision\": 68,\n  \"main_sha\": \"501361a9742f399891604a2c3f4b818de9b51fa8\",\n  \"manager_id\": \"S000-manager-v3-successor-20261124-c\",\n  \"assignments\": [\n    {\n      \"instance\": \"S000-manager-continuation-20261030-a\",\n      \"role\": \"S000\",\n      \"task_id\": \"S000-P0-MEMORY-TEAM-INTEGRATION-REV36\",\n      \"state\": \"BLOCKED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/pull/320\",\n      \"owned_paths\": [\n        \"docs/S000-manager-playbook.md\",\n        \"research/studies/S000-P0-MEMORY-INTEGRATION-PLAN-01.md\"\n      ],\n      \"objective\": \"Retain old integration plan and playbook reservations pending explicit reconciliation; do not resume manager coordination.\",\n      \"acceptance\": \"Prior integration evidence and ownership remain in rev60. No code edits or private work until a new assignment.\"\n    },\n    {\n      \"instance\": \"S002-provenance-successor-20261029-b\",\n      \"role\": \"S002\",\n      \"task_id\": \"S002-P0-A-MOTION-COMPONENT-RETROSPECTIVE\",\n      \"state\": \"CLAIMED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/121\",\n      \"owned_paths\": [\n        \"scripts/audit_p0_a_motion_components_private.py\",\n        \"tests/test_p0_a_motion_components_private.py\",\n        \"research/studies/S002-A-MOTION-COMPONENT-MATRIX-01.md\",\n        \".github/workflows/p0-a-motion-retrospective-offline.yml\"\n      ],\n      \"objective\": \"Complete exact-SHA original A-motion retrospective; repair mixed-event controls and dedicated offline CI.\",\n      \"acceptance\": \"Synthetic and separately approved archived evidence; Win/Ubuntu exact-head focused/full tests; no promotion.\"\n    },\n    {\n      \"instance\": \"S001-g1-source-successor-20261029-b\",\n      \"role\": \"S001\",\n      \"task_id\": \"S001-P0-A-MOTION-CORRECTED-CAPTURE\",\n      \"state\": \"ASSIGNED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/390\",\n      \"owned_paths\": [\n        \"scripts/p0_live_a_motion_controls.py\",\n        \"scripts/run_p0_live_a_motion_controls.ps1\",\n        \"tests/test_p0_live_a_motion_controls.py\",\n        \".github/workflows/p0-live-a-motion-controls-offline.yml\"\n      ],\n      \"objective\": \"Preserve assigned offline A-only, release and motion-no-A controls and copy/paste launcher scope.\",\n      \"acceptance\": \"Synthetic cross-platform tests, no live launch or input absent separate operator consent.\"\n    },\n    {\n      \"instance\": \"S001-a-state-blind-20261030-a\",\n      \"role\": \"S001\",\n      \"task_id\": \"S001-P0-BLIND-A-STATE-EXPERIMENT\",\n      \"state\": \"ASSIGNED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/390\",\n      \"owned_paths\": [\n        \"scripts/p0_live_a_state_blind.py\",\n        \"scripts/run_p0_live_a_state_blind.ps1\",\n        \"tests/test_p0_live_a_state_blind.py\"\n      ],\n      \"objective\": \"Preserve separate blind A-state experiment and withheld-label PRESS/RELEASE/UNKNOWN controls.\",\n      \"acceptance\": \"Offline tests and scoped claim; no live run without separate operator approval.\"\n    },\n    {\n      \"instance\": \"S002-live-inspector-20261030-a\",\n      \"role\": \"S002\",\n      \"task_id\": \"S002-P0-INSPECTOR-LIVE-READONLY\",\n      \"state\": \"CLAIMED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/392\",\n      \"owned_paths\": [\n        \"src/wii_ai_golf/inspector/live.py\",\n        \"tests/test_p0_memory_inspector_live.py\",\n        \"src/wii_ai_golf/inspector/gui.py\",\n        \"scripts/p0_memory_inspector.py\",\n        \"docs/p0-memory-inspector.md\",\n        \".github/workflows/p0-memory-inspector-offline.yml\"\n      ],\n      \"objective\": \"Preserve read-only inspector connect/disconnect, bounded sampling and identity/staleness safeguards.\",\n      \"acceptance\": \"Exact-head synthetic Win/Ubuntu focused/full tests; no launch, game input or memory write.\"\n    },\n    {\n      \"instance\": \"S003-memory-feature-successor-20261029-b\",\n      \"role\": \"S003\",\n      \"task_id\": \"S003-P0-SWING-POWER-DISCRIMINATION\",\n      \"state\": \"ASSIGNED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/4\",\n      \"owned_paths\": [\n        \"research/studies/S003-P0-SWING-POWER-DISCRIMINATORS-01.md\",\n        \"scripts/review_p0_swing_power_candidates.py\",\n        \"tests/test_p0_swing_power_candidates.py\"\n      ],\n      \"objective\": \"Separate motion state from graded swing power using existing source evidence and negative controls.\",\n      \"acceptance\": \"No fabricated power semantics or gameplay; exact-head synthetic tests and abstention.\"\n    },\n    {\n      \"instance\": \"S000-dispatcher-20261029-c\",\n      \"role\": \"S000\",\n      \"task_id\": \"S000-DISPATCHER-PAUSED\",\n      \"state\": \"PARKED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/pull/320\",\n      \"owned_paths\": [\n        \"research/studies/S000-DISPATCH-QUEUE-01.md\"\n      ],\n      \"objective\": \"Operator-paused V2 dispatcher; preserve historical queue evidence. No autonomous dispatch.\",\n      \"acceptance\": \"Remain parked until explicit new allocation; V3 migration does not reactivate this dispatcher.\"\n    },\n    {\n      \"instance\": \"S004-consumer-gate-20261029-a\",\n      \"role\": \"S004\",\n      \"task_id\": \"S004-OPERATOR-PAUSED\",\n      \"state\": \"PARKED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/5\",\n      \"owned_paths\": [\n        \"src/wii_ai_golf/memory_input_contract.py\",\n        \"tests/test_memory_input_contract.py\"\n      ],\n      \"objective\": \"Preserve typed consumer eligibility and real-training guard; no new activity.\",\n      \"acceptance\": \"Remain parked; do not release training gate.\"\n    },\n    {\n      \"instance\": \"S005-heldout-audit-1\",\n      \"role\": \"S005\",\n      \"task_id\": \"S005-OPERATOR-PAUSED\",\n      \"state\": \"PARKED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/6\",\n      \"owned_paths\": [\n        \"src/wii_ai_golf/evaluation.py\",\n        \"tests/test_evaluation_real_gate.py\"\n      ],\n      \"objective\": \"Preserve evaluation and censoring safety guards; no new activity.\",\n      \"acceptance\": \"Remain parked; 100ft off-green penalties are censored, not measured physical carry.\"\n    },\n    {\n      \"instance\": \"S003-terrain-lie-20261110-a\",\n      \"role\": \"S003\",\n      \"task_id\": \"S003-P0-TERRAIN-LIE-SCALARS-20261110\",\n      \"state\": \"ASSIGNED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/415\",\n      \"owned_paths\": [\n        \"src/wii_ai_golf/physics/terrain_lie.py\",\n        \"tests/test_terrain_lie.py\",\n        \"research/studies/S003-P0-TERRAIN-LIE-SCALARS-01.md\"\n      ],\n      \"objective\": \"Preserve pure offline player active lie/mode scalar lookup, separate from raw KCL material meanings.\",\n      \"acceptance\": \"Exact source table, unknown/mode fail-closed, tests Win/Ubuntu; no raw KCL-to-player inference or native parity.\"\n    },\n    {\n      \"instance\": \"S003-first-contact-solver-20261111-a\",\n      \"role\": \"S003\",\n      \"task_id\": \"S003-P0-CCD-FACE-FIRST-ENTRY-PRECISION-HOTFIX-20261122-B\",\n      \"state\": \"COMPLETED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/467\",\n      \"owned_paths\": [\n        \"src/wii_ai_golf/physics/first_contact.py\",\n        \"tests/test_first_contact_solver.py\",\n        \"research/studies/S003-P0-FIRST-CONTACT-SOLVER-01.md\"\n      ],\n      \"objective\": \"Completed #482 high-H first-entry face correction; retain three historical protected files.\",\n      \"acceptance\": \"Exact head c6605fdd; CI 45015903524 both platforms, 1230 full tests; no native KCol parity. New allocation required.\"\n    },\n    {\n      \"instance\": \"S002-selected-v0-successor-20261122-b\",\n      \"role\": \"S002\",\n      \"task_id\": \"S002-P0-SELECTED-BALL-V0-PROVENANCE-20261112\",\n      \"state\": \"CLAIMED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/415\",\n      \"owned_paths\": [\n        \"scripts/audit_p0_selected_ball_v0_provenance_private.py\",\n        \"tests/test_p0_selected_ball_v0_provenance.py\",\n        \"research/studies/S002-P0-SELECTED-BALL-V0-PROVENANCE-20261112.md\",\n        \".github/workflows/s002-selected-v0-offline.yml\"\n      ],\n      \"objective\": \"Finish #483 selected-v0 provenance; bound directory enumeration before cap and add requested dedicated CI workflow. Preserve #455 untouched.\",\n      \"acceptance\": \"Fresh #415 CLAIM 7078331722; fix review 4657881880, bounded negatives; exact-head focused/full Win/Ubuntu CI. Native v0 and clock remain UNKNOWN.\"\n    },\n    {\n      \"instance\": \"S002-accepted-power-successor-20261122-b\",\n      \"role\": \"S002\",\n      \"task_id\": \"S002-P0-ACCEPTED-POWER-TO-LAUNCH-20261112\",\n      \"state\": \"CLAIMED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/418\",\n      \"owned_paths\": [\n        \"scripts/audit_p0_accepted_power_launch_boundary_private.py\",\n        \"tests/test_p0_accepted_power_launch_boundary.py\",\n        \"research/studies/S002-P0-ACCEPTED-POWER-LAUNCH-BOUNDARY-20261112.md\",\n        \".github/workflows/s002-accepted-power-boundary-offline.yml\"\n      ],\n      \"objective\": \"Finish #484 accepted-power launch-boundary audit; fail closed for huge integers and add requested dedicated CI workflow.\",\n      \"acceptance\": \"Fresh #418 CLAIM 7078324358; fix review 4657882654, negative tests, exact-head focused/full Win/Ubuntu CI. Native scalar/launch transfer UNKNOWN.\"\n    },\n    {\n      \"instance\": \"S003-airborne-integration-20261112-a\",\n      \"role\": \"S003\",\n      \"task_id\": \"S003-P0-AIRBORNE-INTEGRATOR-20261112\",\n      \"state\": \"COMPLETED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/415\",\n      \"owned_paths\": [\n        \"src/wii_ai_golf/physics/airborne.py\",\n        \"tests/test_airborne_integrator.py\",\n        \"research/studies/S003-P0-AIRBORNE-INTEGRATION-20261112.md\"\n      ],\n      \"objective\": \"Completed #475 M1 airborne integration; preserve exact historical source/test/study paths.\",\n      \"acceptance\": \"Merged ef480b48; exact-head Win/Ubuntu tests and approved task-finish receipt; no actual source parity.\"\n    },\n    {\n      \"instance\": \"S002-guest-step-witness-20261121-a\",\n      \"role\": \"S002\",\n      \"task_id\": \"S002-P0-GUEST-STEP-EVIDENCE-20261121-A\",\n      \"state\": \"COMPLETED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/472\",\n      \"owned_paths\": [\n        \"research/studies/S002-P0-GUEST-STEP-ATTESTATION-20261121.md\",\n        \"scripts/review_p0_guest_step_attestation.py\",\n        \"tests/test_p0_guest_step_attestation.py\",\n        \".github/workflows/s002-guest-step-attestation-offline.yml\"\n      ],\n      \"objective\": \"Completed #476 offline guest-step attestation; preserve four historical paths.\",\n      \"acceptance\": \"Source guest step count remains UNKNOWN; merged tests do not prove native execution.\"\n    },\n    {\n      \"instance\": \"S002-coordinate-basis-20261121-b\",\n      \"role\": \"S002\",\n      \"task_id\": \"S002-P0-BALL-KCL-COORDINATE-PROVENANCE-20261121-B\",\n      \"state\": \"COMPLETED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/415\",\n      \"owned_paths\": [\n        \"research/studies/S002-P0-COORDINATE-BASIS-20261121.md\",\n        \"scripts/review_p0_ball_kcl_basis_provenance.py\",\n        \"tests/test_p0_ball_kcl_basis_provenance.py\",\n        \".github/workflows/s002-ball-kcl-coordinate-basis-offline.yml\"\n      ],\n      \"objective\": \"Completed #477 offline Ball/KCL coordinate-basis evidence checker; preserve four historical paths.\",\n      \"acceptance\": \"Source-native basis/units remain UNKNOWN; preserve transform and identity abstention.\"\n    },\n    {\n      \"instance\": \"S003-m2-parity-oracle-20261122-a\",\n      \"role\": \"S003\",\n      \"task_id\": \"S003-P1-M2-BOUND-AND-ENDPOINT-ALIAS-20261122-A\",\n      \"state\": \"COMPLETED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/472\",\n      \"owned_paths\": [\n        \"src/wii_ai_golf/physics/parity_oracle.py\",\n        \"tests/test_physics_parity_oracle.py\",\n        \"research/studies/S003-P0-M2-PARITY-ORACLE-20261122.md\",\n        \".github/workflows/s003-m2-parity-offline.yml\"\n      ],\n      \"objective\": \"Completed #481 bounded M2 synthetic reference and endpoint alias checks; preserve four historical paths.\",\n      \"acceptance\": \"Exact-head CI 45015093461/45015093403; native parity still UNKNOWN.\"\n    },\n    {\n      \"instance\": \"S003-ccd-first-entry-oracle-20261122-b\",\n      \"role\": \"S003\",\n      \"task_id\": \"S003-P0-CCD-FIRST-ENTRY-PRECISION-ORACLE-20261122-B\",\n      \"state\": \"COMPLETED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/467\",\n      \"owned_paths\": [\n        \"scripts/research_p0_ccd_precision_oracle_v2.py\",\n        \"tests/test_physics_ccd_precision_oracle_v2.py\",\n        \"research/studies/S003-P0-CCD-PRECISION-ORACLE-20261122.md\",\n        \".github/workflows/s003-ccd-precision-oracle-offline.yml\"\n      ],\n      \"objective\": \"Completed #478 high-precision synthetic CCD reference; preserve four historical paths and independent evidence.\",\n      \"acceptance\": \"Exact-head reference tests; production first-contact code remains separate. No native KCol certainty.\"\n    },\n    {\n      \"instance\": \"S000-manager-v3-successor-20261124-c\",\n      \"role\": \"S000\",\n      \"task_id\": \"V3-P0-LEASE-CORE\",\n      \"state\": \"CLAIMED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/485\",\n      \"owned_paths\": [\n        \"src/wii_ai_golf/orchestration/__init__.py\",\n        \"src/wii_ai_golf/orchestration/state.py\",\n        \"tests/test_v3_orchestration_state.py\",\n        \"docs/v3-orchestration.md\",\n        \".github/workflows/v3-orchestration-offline.yml\",\n        \"src/wii_ai_golf/orchestration/github_store.py\",\n        \"tests/test_v3_github_store.py\",\n        \".github/workflows/v3-github-store-offline.yml\",\n        \"docs/v3-github-store.md\",\n        \"src/wii_ai_golf/orchestration/broker.py\",\n        \"tests/test_v3_work_queue_broker.py\",\n        \"docs/v3-work-queue-broker.md\",\n        \".github/workflows/v3-work-queue-broker-offline.yml\",\n        \"src/wii_ai_golf/orchestration/artifact_gateway.py\",\n        \"tests/test_v3_artifact_gateway.py\"\n      ],\n      \"objective\": \"Complete V3 core, persistence, broker and fenced artifact acceptance; no production writes or cutover.\",\n      \"acceptance\": \"15 exclusive paths; integrated artifact journal and exact-head Win/Ubuntu tests; source promotion and credential deployment separate.\"\n    },\n    {\n      \"instance\": \"S000-v3-shadow-20261124-c\",\n      \"role\": \"S000\",\n      \"task_id\": \"V3-P0-MIGRATE-SHADOW\",\n      \"state\": \"CLAIMED\",\n      \"thread\": \"https://github.com/Nate27624/Wii-AI-Golf/issues/485\",\n      \"owned_paths\": [\n        \"src/wii_ai_golf/orchestration/shadow_import.py\",\n        \"tests/test_v3_shadow_import.py\",\n        \"docs/v3-shadow-import.md\",\n        \".github/workflows/v3-shadow-import-offline.yml\"\n      ],\n      \"objective\": \"Read-only V2 roster shadow import with exact provenance, reserved paths and fail-closed V3 task preview.\",\n      \"acceptance\": \"Blocked shadow only; full rev67 identity and path fidelity, negative tests, exact-head Win/Ubuntu CI; no cutover.\"\n    }\n  ]\n}\n<!-- V2_ASSIGNMENTS_JSON_END -->"
        parsed = shadow.parse_roster(
            body, revision=68,
            main_sha="501361a9742f399891604a2c3f4b818de9b51fa8",
            manager_id="S000-manager-v3-successor-20261124-c",
            comment_id=7143524743)
        self.assertEqual(parsed["reservation_count"], 79)
        self.assertEqual(len(parsed["value"]["assignments"]), 20)
        result = shadow.preview(parsed, goal_sha=GOAL)
        self.assertEqual(len(result["state"]["tasks"]), 21)
        self.assertEqual(len(result["state"]["holds"]), 20)
        self.assertEqual(result["source"]["manager_id"],
                         "S000-manager-v3-successor-20261124-c")
        self.assertTrue(all(t["status"] != "OPEN"
                            for t in result["state"]["tasks"].values()))
        self.assertFalse(result["cutover_eligible"])
        self.assertEqual(result["original_v2_states"]["V3-P0-MIGRATE-SHADOW"],
                         "CLAIMED")
        model.validate(result["state"])


if __name__ == "__main__":
    unittest.main()
