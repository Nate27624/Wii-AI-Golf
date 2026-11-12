"""Synthetic-only UI layout regression: existing data tools stay available."""
from __future__ import annotations

import inspect
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from wii_ai_golf.inspector.gui import Inspector
from wii_ai_golf.inspector.textured_preview import TexturedPreviewWindow


class FakeWidget:
    def __init__(self):
        self.calls = []
    def pack(self, **kwargs):
        self.calls.append(("pack", kwargs))
    def pack_forget(self):
        self.calls.append(("pack_forget", {}))
    def configure(self, **kwargs):
        self.calls.append(("configure", kwargs))


class FakePanes:
    def __init__(self):
        self.calls = []
    def insert(self, pos, widget, **kwargs):
        self.calls.append(("insert", pos, widget, kwargs))
    def add(self, widget, **kwargs):
        self.calls.append(("add", widget, kwargs))
    def forget(self, widget):
        self.calls.append(("forget", widget))


class InspectorFocusTests(unittest.TestCase):
    def _fake_inspector(self):
        ui = object.__new__(Inspector)
        ui._advanced_visible = True
        ui._advanced_setup = FakeWidget()
        ui._advanced_button = FakeWidget()
        ui._head_status_label = FakeWidget()
        ui._advanced_lower = FakeWidget()
        ui._advanced_left = FakeWidget()
        ui._advanced_right = FakeWidget()
        ui._advanced_center_tools = tuple(FakeWidget() for _ in range(3))
        ui._main_panes = FakePanes()
        ui.visual_preview = Mock()
        return ui

    def test_compact_default_keeps_phase_raw_kcl_widgets_constructed(self):
        src = inspect.getsource(Inspector._draw_controls)
        self.assertIn('text="Wii Golf · Shot Inspector"', src)
        self.assertIn('text="Connect LIVE (read-only)"', src)
        self.assertIn('textvariable=self.a_status', src)
        self.assertIn('textvariable=self.club_status', src)
        self.assertIn('self._advanced_visible = True', src)
        self.assertIn('self.set_advanced_visible(False)', src)
        # Widgets are still created; hiding doesn't delete source samples.
        self.assertIn('self.phase_list = tk.Listbox(', src)
        self.assertIn('self.rows = ttk.Treeview(', src)
        self.assertIn('self.slider = ttk.Scale(', src)
        self.assertIn('self.visual_tab = ttk.Frame(', src)
        self.assertIn('self._legacy_terrain_tab = terrain_tab', src)
        self.assertIn('self._advanced_center_tools', src)
        self.assertIn('self._advanced_lower = lower', src)

    def test_roundtrip_hides_panels_not_destroying_them(self):
        ui = self._fake_inspector()
        raw = ui._advanced_right
        phase = ui._advanced_left
        tools = ui._advanced_center_tools
        Inspector.set_advanced_visible(ui, False)
        self.assertFalse(ui._advanced_visible)
        self.assertIn(("forget", raw), ui._main_panes.calls)
        self.assertIn(("forget", phase), ui._main_panes.calls)
        self.assertTrue(all(
            any(action == "pack_forget" for action, _ in widget.calls)
            for widget in tools))
        ui.visual_preview.set_diagnostics_visible.assert_called_with(False)
        Inspector.toggle_advanced(ui)
        self.assertTrue(ui._advanced_visible)
        self.assertIn(("insert", 0, phase, {"weight": 1}), ui._main_panes.calls)
        self.assertIn(("add", raw, {"weight": 2}), ui._main_panes.calls)
        ui.visual_preview.set_diagnostics_visible.assert_called_with(True)
        self.assertEqual(
            ui._advanced_button.calls[-1],
            ("configure", {"text": "Advanced ▾"}))
        before = list(ui._main_panes.calls)
        Inspector.set_advanced_visible(ui, True)
        self.assertEqual(ui._main_panes.calls, before)
        Inspector.toggle_advanced(ui)
        self.assertFalse(ui._advanced_visible)

    def test_reject_non_boolean_advanced_state(self):
        ui = self._fake_inspector()
        for bad in (None, 1, 0, "yes", []):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                Inspector.set_advanced_visible(ui, bad)

    def test_renderer_details_collapse_without_losing_display_variables(self):
        view = object.__new__(TexturedPreviewWindow)
        detail = FakeWidget()
        other = FakeWidget()
        view._diagnostic_widgets = (
            (detail, {"fill": "x"}), (other, {"side": "left"}))
        view._diagnostics_visible = True
        # No canvas, camera, source model or render thread is modified.
        TexturedPreviewWindow.set_diagnostics_visible(view, False)
        self.assertFalse(view._diagnostics_visible)
        self.assertEqual(detail.calls[-1][0], "pack_forget")
        TexturedPreviewWindow.set_diagnostics_visible(view, True)
        self.assertTrue(view._diagnostics_visible)
        self.assertEqual(detail.calls[-1], ("pack", {"fill": "x"}))
        self.assertEqual(other.calls[-1], ("pack", {"side": "left"}))
        TexturedPreviewWindow.set_diagnostics_visible(view, True)
        self.assertEqual(len(detail.calls), 2)

    def test_source_warning_and_render_failure_are_not_hidden(self):
        code = inspect.getsource(TexturedPreviewWindow.__init__)
        self.assertIn("if scene_warning:", code)
        self.assertIn('foreground="#c84820"', code)
        self.assertIn('self._render_error_label = ttk.Label(', code)
        poll = inspect.getsource(TexturedPreviewWindow._poll_completed)
        self.assertIn('self._render_error_label.configure(text=message)', poll)
        self.assertIn('self._render_error_label.pack(fill="x")', poll)

    def test_keeps_source_setup_and_live_readonly_controls(self):
        src = inspect.getsource(Inspector._draw_controls)
        self.assertIn('"Capture JSONL"', src)
        self.assertIn('"SHA-256 manifest"', src)
        self.assertIn('"PowerShell: Launch ready for shot"', src)
        self.assertIn('"Verify SHA-256 and Open Offline"', src)
        self.assertIn('command=self.disconnect_live', src)
        self.assertIn('command=self.open_capture', src)
        self.assertIn('command=self.load_tree_positions', src)
        self.assertIn('command=self.load_terrain', src)


if __name__ == "__main__":
    unittest.main()
