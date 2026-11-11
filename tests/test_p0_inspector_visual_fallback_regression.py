"""Regression guards for FALLBACK gray KCL, original visual auto-load, navigation.

All tests are synthetic; no user/game files, Dolphin or GUI windows.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"scripts"))

from wii_ai_golf.inspector.asset_preferences import AssetSelections
from wii_ai_golf.inspector.gui import Inspector, _known_private_visual_candidate
from diagnose_inspector_visual_loading import diagnose


def fallback_stub():
    app=Inspector.__new__(Inspector)
    app.root=Mock()
    app.root.after.return_value="navigation-timer"
    app._fallback_held=set()
    app._fallback_pending_release={}
    app._fallback_nav_timer=None
    app._fallback_last_tick=0.
    app._fallback_last_render=0.
    app.camera_pan=(0.,0.)
    app.visual_preview=None
    app.draw_path=Mock()
    return app


class VisualFallbackTests(unittest.TestCase):
    def test_original_visual_known_path_no_longer_requires_terrain(self):
        with patch("wii_ai_golf.inspector.gui.Path.is_file",return_value=True):
            path=_known_private_visual_candidate("")
            self.assertIsNotNone(path)
            self.assertTrue(str(path).replace("\\","/").endswith(
                "WiiGolfVisualPrivate/visual_exports/glf_course_fc1/glf_course_fc1.dae"))

    def test_hidden_fallback_does_not_paint_2498_triangles_on_live_sample(self):
        app=Inspector.__new__(Inspector)
        app.visual_preview=object()
        app.canvas=Mock()
        Inspector.draw_path(app)
        app.canvas.delete.assert_not_called()

    def test_fallback_arrow_movement_is_continuous_not_one_keypress_step(self):
        app=fallback_stub()
        press=Mock(keysym="Right")
        with patch("wii_ai_golf.inspector.gui.time.perf_counter",return_value=0.):
            self.assertEqual(Inspector._fallback_key_press(app,press),"break")
        self.assertEqual(app.camera_pan,(0.,0.))
        self.assertIn("right",app._fallback_held)
        with patch("wii_ai_golf.inspector.gui.time.perf_counter",return_value=.11):
            Inspector._fallback_navigation_tick(app)
        self.assertLess(app.camera_pan[0],0.)
        self.assertAlmostEqual(app.camera_pan[0],-18.,places=3)
        app.draw_path.assert_called_once()
        with patch("wii_ai_golf.inspector.gui.time.perf_counter",return_value=.15):
            Inspector._fallback_navigation_tick(app)
        self.assertLess(app.camera_pan[0],-18.)
        self.assertEqual(app.draw_path.call_count,1)
        Inspector._fallback_finish_key(app,"right")
        self.assertFalse(app._fallback_held)
        self.assertIsNone(app._fallback_nav_timer)
        self.assertEqual(app.draw_path.call_count,2)

    def test_autorepeat_release_debounced_then_cancelled_by_press(self):
        app=fallback_stub()
        app._fallback_held.add("up")
        self.assertEqual(Inspector._fallback_key_release(app,Mock(keysym="Up")),
                         "break")
        self.assertEqual(len(app._fallback_pending_release),1)
        Inspector._fallback_key_press(app,Mock(keysym="Up"))
        self.assertIn("up",app._fallback_held)
        self.assertFalse(app._fallback_pending_release)
        app.root.after_cancel.assert_called_once()

    def test_visual_switch_stops_fallback_navigation(self):
        app=fallback_stub()
        app._fallback_held.add("left")
        app._fallback_nav_timer="timer"
        app.visual_preview=MagicMock()
        app._legacy_terrain_tab=Mock()
        app.visual_tab=Mock()
        Inspector.show_visual_tab(app)
        self.assertEqual(app._fallback_held,set())
        self.assertIsNone(app._fallback_nav_timer)
        app._legacy_terrain_tab.pack_forget.assert_called_once()
        app.visual_tab.pack.assert_called_once()
        app.visual_preview.schedule.assert_called_once()

    def test_fallback_mouse_release_restores_full_source_scene(self):
        app=fallback_stub()
        app.drag_button=3
        app.drag_origin=(12,30)
        Inspector.drag_end(app,Mock(num=3))
        self.assertIsNone(app.drag_button)
        self.assertIsNone(app.drag_origin)
        app.draw_path.assert_called_once()

    def test_slow_unified_camera_navigation_uses_low_res_and_defers_mips(self):
        from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow
        view=TexturedPreviewWindow.__new__(TexturedPreviewWindow)
        view._closed=False
        view.canvas=Mock()
        view.canvas.winfo_width.return_value=1000
        view.canvas.winfo_height.return_value=700
        view._request_version=12
        view.camera=object()
        view.fast_active=False
        view.drag_button=None
        view._held_keys={"up"}
        view.mode=Mock()
        view.mode.get.return_value="Textures"
        view.model=Mock()
        view.model.faces=[None]*10
        view.status=Mock()
        view.filtered_texture=Mock()
        view.filtered_texture.get.return_value=True
        view._start_latest=Mock()
        view._request_full_render()
        self.assertEqual(view._queued[1:3],(400,280))
        self.assertFalse(view._queued_texture_filter)
        self.assertEqual(len(view._queued),6)
        view._held_keys.clear()
        view._request_full_render()
        self.assertEqual(view._queued[1:3],(1000,700))
        self.assertTrue(view._queued_texture_filter)

    def test_collada_failure_is_reported_in_visible_fallback_status(self):
        from wii_ai_golf.inspector.visual_model import VisualAssetError
        app=Inspector.__new__(Inspector)
        app.visual_status=Mock()
        app.root=Mock()
        with patch("wii_ai_golf.inspector.gui.load_private_dae_visual_model",
                   side_effect=VisualAssetError("Unsupported original scene graph")):
            loaded=Inspector.load_visual_path(app,"C:/private/original.dae")
        self.assertFalse(loaded)
        msg=app.visual_status.set.call_args.args[0]
        self.assertIn("TEXTURED MODEL FAILED",msg)
        self.assertIn("Unsupported original scene graph",msg)
        self.assertIn("fallback",msg)

    def test_visual_diagnostic_explains_missing_saved_selection(self):
        with patch("diagnose_inspector_visual_loading.load_asset_selections",
                   return_value=AssetSelections(visual_dae="/abs/missing.dae")),patch(
                   "diagnose_inspector_visual_loading.Path.is_file",
                   return_value=False):
            report=diagnose()
        self.assertEqual(report["status"],"VISUAL_FILE_MISSING")
        self.assertFalse(report["candidate_exists"])


if __name__=="__main__":
    unittest.main()
