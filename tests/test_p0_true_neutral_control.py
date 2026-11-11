"""Focused offline regression for source-safe true A-only vs normal swing control."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "scripts"):
    sys.path.insert(0, str(p))
from wii_ai_golf.integration.a45_neutral_probe_patch import (
    patch_atomic_v1_to_neutral, ATOMIC_NEUTRAL_MARKER
)
from prepare_a45_neutral_bridge import prepare
from p0_input_discovery_sweep import (
    require_genuine_neutral_capability, run_discovery, RefuseTrial
)

FAKE_SOURCE = '''# WII_AI_GOLF_ATOMIC_TRACE_V1
# WII_AI_GOLF_SWING_TRACE_V1
# WII_AI_GOLF_ATOMIC_A45_BRIDGE_V1

def _wii_ai_atomic_a45_capabilities(_p):
    return {"atomic_a45_protocol": 1}


def tick(t, index, controller):
    if t.get("kind") == "swing":
        try:
                controller.set_wiimote_swing(t["port"], *t["samples"][index][1:])
        except Exception:
            raise


HANDLERS = {
    "trace.atomic_a45_capabilities": _wii_ai_atomic_a45_capabilities,
}
'''


class Tests(unittest.TestCase):
    def test_new_source_skips_true_zero_swing_calls(self):
        source = patch_atomic_v1_to_neutral(FAKE_SOURCE)
        self.assertIn(ATOMIC_NEUTRAL_MARKER, source)
        self.assertIn("if any(value != 0.0 for value in motion):", source)
        self.assertIn('"trace.a45_neutral_capabilities":', source)
        namespace = {}
        exec(compile(source, "<synthetic-test>", "exec"), namespace)
        calls = []
        class FakeController:
            def set_wiimote_swing(self, *args):
                calls.append(args)
        t = {"kind": "swing", "port": 0, "samples": [
            (True, 0, 0, 0, 0, 0, 0, 0),
            (True, 0, 1, 0, 0.6, 3.5, 2, 0)]}
        namespace["tick"](t, 0, FakeController())
        self.assertEqual(calls, [])
        namespace["tick"](t, 1, FakeController())
        self.assertEqual(calls, [(0, 0, 1, 0, 0.6, 3.5, 2, 0)])
        self.assertEqual(namespace["_wii_ai_a45_neutral_capabilities"]([]),
                         {"neutral_protocol": 1, "atomic_a45_protocol": 1,
                          "no_swing_calls_for_zero_samples": True,
                          "nonzero_swing_calls_preserved": True})

    def test_fail_closed_incompatible_sources(self):
        for bad in (FAKE_SOURCE.replace("# WII_AI_GOLF_ATOMIC_A45_BRIDGE_V1", ""),
                    FAKE_SOURCE + "\n# WII_AI_GOLF_SWING_NEUTRAL_BUTTON_ONLY_V2\n",
                    FAKE_SOURCE + "\n# WII_AI_GOLF_STARTUP_STATE_V1\n"):
            with self.assertRaises(ValueError):
                patch_atomic_v1_to_neutral(bad)
        with self.assertRaises(ValueError):
            patch_atomic_v1_to_neutral(patch_atomic_v1_to_neutral(FAKE_SOURCE))

    def test_preparer_never_overwrites_original_or_existing_different_file(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            original, output = td / "original.py", td / "neutral.py"
            original.write_text(FAKE_SOURCE, encoding="utf-8")
            before = original.read_bytes()
            report = prepare(original, output)
            self.assertFalse(report["dolphin_launched"])
            self.assertFalse(report["runtime_capability_verified"])
            self.assertNotEqual(output.read_bytes(), before)
            self.assertEqual(before, original.read_bytes())
            self.assertEqual(prepare(original, output)["sha256"],
                             report["sha256"])
            output.write_text("unrelated file", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                prepare(original, output)
            self.assertEqual(original.read_bytes(), before)

    def test_require_runtime_capability_fail_closed(self):
        good = {"neutral_protocol": 1, "atomic_a45_protocol": 1,
                "no_swing_calls_for_zero_samples": True,
                "nonzero_swing_calls_preserved": True}
        class RPC:
            def __init__(self, data):
                self.data=data
                self.calls=[]
            def call(self, method, params):
                self.calls.append(method)
                return self.data
        rpc=RPC(good)
        require_genuine_neutral_capability(rpc)
        self.assertEqual(rpc.calls, ["trace.a45_neutral_capabilities"])
        for key in good:
            bad = dict(good)
            bad[key] = None
            with self.assertRaises(RefuseTrial):
                require_genuine_neutral_capability(RPC(bad))

    def test_two_shot_real_control_sequence_and_immutable_ledger(self):
        events=[]
        with tempfile.TemporaryDirectory() as td:
            directory=Path(td)
            bridge=directory/"neutral.py"
            bridge.write_text(patch_atomic_v1_to_neutral(FAKE_SOURCE),
                              encoding="utf-8")
            sha=hashlib.sha256(bridge.read_bytes()).hexdigest()
            profile=type("P",(),{"name":"green-pre-start","slot":2})()

            class RPC:
                def __init__(self, **kwargs): pass
                def __enter__(self): return self
                def __exit__(self,*args): pass
                def call(self, method, params):
                    if method == "trace.a45_neutral_capabilities":
                        events.append("neutral-check")
                        return {"neutral_protocol":1,"atomic_a45_protocol":1,
                                "no_swing_calls_for_zero_samples":True,
                                "nonzero_swing_calls_preserved":True}
                    raise AssertionError(method)
            class Atomic:
                @staticmethod
                def require_capability(_):
                    events.append("atomic-check")
                def __init__(self,*a,**k):pass
                def run(self, samples):
                    events.append(("swing",tuple(s.direction for s in samples)))
                    return {"state":"complete"}

            def reader(prompt):
                if "RUN-TWO" in prompt: return "RUN-TWO"
                if "initial club position" in prompt: return "back"
                if "precise visual club position" in prompt: return "partial-back"
                if "currently selected club" in prompt: return "iron"
                if "manually change WEDGE" in prompt: return "yes"
                if "Observed gauge" in prompt: return "101"
                if "result G/M" in prompt: return "no"
                if "marked RED" in prompt: return "yes"
                if "curve or rotation" in prompt: return "unknown"
                raise AssertionError(prompt)

            def fake_session(rpc,**kwargs):
                kwargs["input_fn"]("BEFORE pressing A, initial club position [back/center/forward/unknown]: ")
                kwargs["swing_fn"](rpc)
                return {"human_observation":{"initial_club_pose_human":"back",
                       "contact_human":"yes",
                       "visible_result_class_human":"transitioned",
                       "terminal_screen_seen_before_transition_human":False}}
            from p0_input_discovery_sweep import (
                make_variants, preflight_source
            )
            with patch("p0_input_discovery_sweep.FelkRPC",RPC), \
                 patch("p0_input_discovery_sweep.AtomicA45SwingTraceClient",Atomic), \
                 patch("p0_input_discovery_sweep.run_session",side_effect=fake_session), \
                 patch("p0_input_discovery_sweep.release_buttons",lambda *_a,**_k:None), \
                 patch("p0_input_discovery_sweep.preflight_catalog",return_value=profile), \
                 patch("p0_input_discovery_sweep.preflight_source",return_value=sha), \
                 patch("p0_input_discovery_sweep.load_and_replay_intro",
                       side_effect=lambda **kwargs:events.append("reload")):
                rows=run_discovery(scenario="neutral01",catalog=directory/"cat",
                                   bridge_source=bridge,reader=reader,
                                   data_dir=directory,genuine_neutral=True)
            self.assertEqual(len(rows),2)
            self.assertEqual([r["arm"] for r in rows], ["CTRL","ZERO"])
            self.assertEqual([r["club_motion_human"] for r in rows],
                             ["unknown","unknown"])
            self.assertEqual(events.count("reload"),1)
            self.assertEqual(events.count("neutral-check"),2)
            strokes=[e for e in events if isinstance(e,tuple) and e[0]=="swing"]
            self.assertEqual(len(strokes),2)
            self.assertNotEqual(strokes[0],strokes[1])
            self.assertEqual(len((directory/"neutral-button-only-neutral01.jsonl").
                                 read_text().splitlines()),2)
            self.assertTrue(all(r["training_approved"] is False for r in rows))

if __name__=="__main__":
    unittest.main()
