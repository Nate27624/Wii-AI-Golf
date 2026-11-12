"""Shot-source transition UI tests; all data is synthetic and source-free."""
from __future__ import annotations

from collections import deque
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.inspector.gui import Inspector
from wii_ai_golf.inspector.live import LiveEvent
from wii_ai_golf.inspector.replay import Replay, Sample
from wii_ai_golf.inspector.source_actor_overlay import SourceActorSnapshot


def source_sample(epoch: str, index: int) -> Sample:
    return Sample(index, "LIVE", index, index*1000, index*1000+10,
                  {"selected_ball_plus_0x30": (0x3f800000+index, 0, 0)},
                  epoch, True, "source-qualified", "complete",
                  (index,index+1))


def fake_ui():
    view=object.__new__(Inspector)
    view.live_buffer=deque(maxlen=24)
    view.live_segment=1
    view.live_last=2.
    view.replay=Replay(Path("LIVE"),"", (source_sample("old",0),),(),"live")
    view.phases=[("LIVE",0)]
    view.baseline=1.
    view.aim_baseline_source="old"
    view.a_indicator=Mock()
    view.a_status=Mock()
    view.club_status=Mock()
    view.a_reason=Mock()
    view.source_segment_status=Mock()
    view.landmark_status=Mock()
    view.aim_status=Mock()
    view.phase_list=Mock()
    view.slider=Mock()
    view.rows=Mock()
    view.rows.get_children.return_value=("row",)
    view.canvas=Mock()
    view.visual_preview=Mock()
    view.status=Mock()
    view.draw_a_overlay=Mock()
    view.index=Mock()
    view.root=Mock()
    view.show=Mock()
    view.process_a_sample=Mock()
    view._show_live_club=Mock()
    view.live_rate=0.
    view.live_location="previous hole"
    view.live_buffer.append(source_sample("old",0))
    return view


class LiveTransitionUITests(unittest.TestCase):
    def test_transition_clears_stale_3d_actor_and_club_but_keeps_connection(self):
        view=fake_ui()
        sentinel=Mock()
        view.live_worker=sentinel
        view.startup_process=sentinel
        view._enter_source_transition("VERIFIED_SOURCE_IDENTITY_CHANGED")
        self.assertEqual(len(view.live_buffer),0)
        self.assertIsNone(view.replay)
        self.assertIsNone(view.live_last)
        self.assertIsNone(view.baseline)
        self.assertIsNone(view.aim_baseline_source)
        self.assertEqual(view.live_segment,0)
        view.club_status.set.assert_called_with("CLUB UNKNOWN")
        view.a_status.set.assert_called_with("A UNKNOWN")
        view.visual_preview.set_actor_overlay.assert_called_once_with(
            SourceActorSnapshot())
        self.assertIn("LIVE TRANSITION",str(view.status.set.call_args))
        self.assertIs(view.live_worker,sentinel)
        self.assertIs(view.startup_process,sentinel)
        self.assertFalse(sentinel.stop.called)

    def test_dropped_transition_event_is_recovered_by_digest_change(self):
        view=fake_ui()
        new=source_sample("qualified-next-source",1)
        sample=LiveEvent("sample",new,hole=3,selected_player=1,
                         source_segment=2,club_index=3,club_label="PUTTER")
        view.live_worker=SimpleNamespace(drain=lambda:[sample])
        Inspector.poll_live(view)
        # Clear previous trace before constructing replay from new epoch.
        self.assertEqual(len(view.live_buffer),1)
        self.assertIs(view.live_buffer[0],new)
        self.assertEqual(view.replay.samples,(new,))
        self.assertEqual(view.live_segment,2)
        self.assertEqual(view.phases,[("LIVE",0)])
        view.visual_preview.set_actor_overlay.assert_called_with(
            SourceActorSnapshot())
        self.assertIn("source segment 2",
                      str(view.status.set.call_args).lower())
        view.show.assert_called_once_with(0)

    def test_transition_event_then_requalified_sample_preserves_new_epoch(self):
        view=fake_ui()
        new=source_sample("digest-epoch2",1)
        events=[
            LiveEvent("transition",reason="SOURCE_TEMPORARILY_UNAVAILABLE",
                      source_segment=1),
            LiveEvent("sample",new,hole=3,selected_player=2,
                      source_segment=2,club_index=2),
        ]
        view.live_worker=SimpleNamespace(drain=lambda:events)
        Inspector.poll_live(view)
        self.assertEqual(tuple(view.live_buffer),(new,))
        self.assertEqual(view.live_segment,2)
        self.assertIn("source segment 2",
                      str(view.status.set.call_args).lower())
        view.a_indicator.clear.assert_called()
        view.source_segment_status.set.assert_called_with(
            "Source segment 2 · actual shot number UNVERIFIED")

    def test_only_real_bridge_error_freezes_and_clears_club(self):
        view=fake_ui()
        view.live_worker=SimpleNamespace(
            drain=lambda:[LiveEvent(
                "error",reason="Read-only failure: "
                "UNEXPECTED_SOURCE_OR_BRIDGE_FAILURE (ValueError). "
                "No automatic reconnect.")])
        Inspector.poll_live(view)
        self.assertEqual(len(view.live_buffer),1)
        view.club_status.set.assert_called_with("CLUB UNKNOWN")
        self.assertIn("LIVE FAILED",str(view.status.set.call_args))
        self.assertFalse(view.visual_preview.set_actor_overlay.called)


if __name__=="__main__":
    unittest.main()
