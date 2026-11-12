"""Offline synthetic-only LIVE shot-source recovery; no Dolphin or game writes."""
from __future__ import annotations

from pathlib import Path
import sys
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/"src"), str(ROOT/"scripts")]
from wii_ai_golf.inspector.live import LiveSampler, ReadOnlyRPC
from wii_ai_golf.inspector.gui import Inspector


class FakeBridge:
    def __init__(self):
        self.calls = []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def call(self, method, args):
        self.calls.append((method, list(args)))
        if method == "frame.get_count":
            return 1
        raise AssertionError("Unexpected bridge method")


def qualified(index: int, identity_suffix: int):
    # Two independent original source IDs with 14 fields. Never mix cohorts.
    identity = tuple([0]*13 + [identity_suffix])
    return {
        "identity": identity,
        "words": {
            "selected_ball_plus_0x30": (0x3f800000+identity_suffix,0,0),
            "aim_candidate_plus_0x3c": (0x3f000000,),
        },
        "start_ns": index*100000,
        "end_ns": index*100000+50000,
        "frame_bracket": (index,index+1),
        "club_index": 2,
    }


class SourceTransitionTests(unittest.TestCase):
    def worker(self, scripted, allow=True):
        from wii_ai_golf.inspector import fast, live
        bridge = FakeBridge()
        iterator = iter(scripted)
        def packet(rpc, phase, index, **kwargs):
            rpc.call("frame.get_count",[])
            item=next(iterator, ValueError("not Wii Sports USA Rev1"))
            if isinstance(item, BaseException):
                raise item
            return qualified(index,item)
        sampler=LiveSampler(connector=lambda:bridge,
                            allow_source_transitions=allow,
                            include_a_state=False,poll_pause_s=.0)
        with patch.object(fast, "packet", side_effect=packet), \
             patch.object(live, "_TRANSITION_POLL_S", .001):
            sampler.start()
            sampler.thread.join(timeout=.9)
            sampler.stop()
            sampler.thread.join(timeout=1.)
        self.assertFalse(sampler.thread.is_alive())
        return sampler.drain(), bridge

    def test_selected_owner_change_requires_two_full_qualified_packets(self):
        events,bridge=self.worker([
            1, 2, 2, 2, ValueError("not Wii Sports USA Rev1"),
        ])
        kinds=[e.kind for e in events]
        self.assertEqual(kinds, ["sample","transition","resumed","sample","sample","error"])
        samples=[e for e in events if e.kind == "sample"]
        self.assertEqual(len(samples),3)
        self.assertEqual(samples[0].sample.words[
            "selected_ball_plus_0x30"][0],0x3f800001)
        self.assertTrue(all(s.sample.source_qualified for s in samples))
        self.assertEqual([s.club_index for s in samples],[2,2,2])
        self.assertNotEqual(samples[0].sample.source_digest,
                            samples[1].sample.source_digest)
        self.assertNotIn("pointer",events[1].reason)
        self.assertEqual({method for method,_ in bridge.calls},{"frame.get_count"})

    def test_transient_scene_gap_then_new_source_resumes_without_reconnect(self):
        events, bridge=self.worker([
            1, ValueError("not Golf scene"),
            3, 3, 3, ValueError("not Wii Sports USA Rev1"),
        ])
        kinds=[e.kind for e in events]
        self.assertEqual(kinds,["sample","transition","resumed","sample","sample","error"])
        self.assertEqual(sum(k=="transition" for k in kinds),1)
        self.assertEqual(sum(k=="resumed" for k in kinds),1)

    def test_interleaved_invalid_packet_resets_two_success_streak(self):
        events,_=self.worker([
            1, ValueError("not active Hitting-the-Green hole"),
            2, ValueError("source identity changed across packet"),
            2, 2, ValueError("not Wii Sports USA Rev1"),
        ])
        self.assertEqual([e.kind for e in events],
                         ["sample","transition","resumed","sample","error"])

    def test_bad_revision_never_recovered(self):
        events,_=self.worker([1,ValueError("not Wii Sports USA Rev1")])
        self.assertEqual([e.kind for e in events],["sample","error"])
        self.assertIn("ValueError",events[-1].reason)

    def test_custom_reader_identity_change_stays_fatal_even_if_opted_in(self):
        from wii_ai_golf.inspector.live import LiveSampler
        def injected(rpc, phase, index):
            return qualified(index,1 if index==0 else 2)
        worker=LiveSampler(connector=lambda:FakeBridge(),
                           packet_reader=injected,
                           allow_source_transitions=True,
                           poll_pause_s=.001)
        worker.start()
        worker.thread.join(timeout=.3)
        worker.stop()
        worker.thread.join(timeout=1)
        self.assertEqual([e.kind for e in worker.drain()],["sample","error"])

    def test_gui_handles_gap_and_new_epoch_without_preserving_old_actor(self):
        from wii_ai_golf.inspector.live import LiveEvent
        from wii_ai_golf.inspector.source_actor_overlay import SourceActorSnapshot
        view=object.__new__(Inspector)
        for name in ("a_status","club_status","a_reason","status",
                     "landmark_status","aim_status"):
            setattr(view,name,Mock())
        view.a_indicator=Mock()
        view.visual_preview=Mock()
        view.draw_a_overlay=Mock()
        view.live_buffer=[object(),object()]
        view.baseline=.7
        view.aim_baseline_source="old"
        view.replay=object()
        view.phase_list=Mock()
        view.rows=Mock()
        view.live_last=10.
        # Exercise the event blocks in the real poll handler, no Tk.
        class Worker:
            def drain(self):
                return [LiveEvent("transition"),LiveEvent("resumed")]
        view.live_worker=Worker()
        view.root=Mock()
        view._show_live_club=Mock()
        view.process_a_sample=Mock()
        Inspector.poll_live(view)
        view.visual_preview.set_actor_overlay.assert_called_with(
            SourceActorSnapshot())
        view.a_status.set.assert_called_with("A UNKNOWN")
        view.club_status.set.assert_called_with("CLUB UNKNOWN")
        self.assertEqual(view.live_buffer,[])
        self.assertIsNone(view.replay)
        self.assertIsNone(view.baseline)
        self.assertIsNone(view.aim_baseline_source)
        view.a_indicator.clear.assert_called()
        view.root.after.assert_called()


if __name__ == "__main__":
    unittest.main()
