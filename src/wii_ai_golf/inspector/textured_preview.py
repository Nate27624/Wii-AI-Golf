"""Tk source-UV viewport, embedded in the inspector or a standalone window.

Expensive full-source CPU raster runs on ONE cancellable worker. Tk widgets
and PhotoImage are exclusively updated on the main UI thread. Source models,
game memory, original collision OBJ and PNGs are NEVER modified.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
import tkinter as tk
from tkinter import ttk

from .navigation import wheel_steps
from .scene_camera import (
    fit_camera, frame_playable_camera, look_in_place, orbit, pan, dolly,
    move_continuous)
from .unified_source_view import (
    prepare_comparison_kcl, draw_comparison, overlay_summary)
from .texture_render import PreviewCancelled, prepare_textures, render_preview
from .fast_texture_render import (
    accelerated_available, prepare_fast_scene, render_fast)
from .visual_model import PrivateVisualModel, VisualAssetError


class TexturedPreviewWindow:
    def __init__(self, parent: tk.Misc, model: PrivateVisualModel,
                 *, embedded: bool = False):
        # Confirm source-bound PNG bytes before creating the viewport.
        self.textures = prepare_textures(model)
        self.model = model
        # Original texture PNG admission is unchanged. Pack source triangles
        # and texels once; compiled C-level rendering then reuses this data.
        self.fast_scene = (prepare_fast_scene(model, self.textures)
                           if accelerated_available() else None)
        self.fast_active = self.fast_scene is not None
        self.embedded = embedded
        self.top = ttk.Frame(parent) if embedded else tk.Toplevel(parent)
        if embedded:
            self.top.pack(fill="both", expand=True)
        else:
            self.top.title("Wii Golf · PRIVATE source visual model")
            self.top.geometry("1040x720")
            self.top.minsize(480, 360)

        self.full_camera = fit_camera(model.vertices)
        self.home_camera = frame_playable_camera(model)
        self.camera = self.home_camera
        self.comparison_kcl = None
        self.mode = tk.StringVar(value="Textures")
        self.comparison_status = tk.StringVar(
            value="KCL: none loaded · texture source coordinates unverified.")
        self.drag_origin: tuple[int, int] | None = None
        self.drag_button: int | None = None
        # Held-key state drives monotonic-time camera motion at ~60Hz.
        # OS keyboard repeat events do NOT determine motion speed.
        self._held_keys: set[str] = set()
        self._pending_key_releases: dict[str, str] = {}
        self._nav_timer = None
        self._last_nav_tick = 0.0
        self._last_nav_render = 0.0
        self._shift_held = False
        self.image_ref = None
        self._pending = None
        self._poll_id = None
        self._closed = False
        self._request_version = 0
        self._queued = None
        self._render_future = None
        self._cancel_render = None
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="WiiGolfPrivateUV")

        head = ttk.Frame(self.top, padding=(6, 4))
        head.pack(fill="x")
        ttk.Label(
            head,
            text=f"Source visual: {model.source_name} · "
                 f"{len(model.faces):,} triangles · {len(model.textures)} original PNGs",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            head,
            text="STATIC visual-model LOCAL coordinates · not aligned with "
                 "the separate KCL/ball/tee/flag view · native Wii shaders unverified",
            wraplength=820,
        ).pack(anchor="w")
        if model.skipped_source_faces:
            ttk.Label(
                head,
                text=f"{model.skipped_source_faces:,} source faces omitted: "
                     "untextured effect lacks original diffuse appearance.",
                wraplength=820,
            ).pack(anchor="w")

        controls = ttk.Frame(self.top, padding=(6, 3))
        controls.pack(fill="x")
        ttk.Button(controls, text="Frame course (F)",
                   command=self.frame).pack(side="left")
        ttk.Button(controls, text="Frame whole scene (Shift+F)",
                   command=self.frame_all).pack(side="left", padx=(3, 8))
        for label in ("Textures", "Collision", "Both"):
            ttk.Radiobutton(
                controls, text=label, value=label, variable=self.mode,
                command=self.schedule).pack(side="left", padx=(1, 3))
        ttk.Label(
            controls,
            text="RMB look · LMB orbit · MMB pan · arrows move forward/back/left/right · "
                 "RMB+WASD/QE fly · wheel dolly · Shift faster",
            wraplength=670,
        ).pack(side="left", padx=8)

        self.canvas = tk.Canvas(self.top, background="#13202e",
                                takefocus=1, highlightthickness=0, height=460)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=(2, 6))
        self.canvas.bind("<Configure>", lambda event: self.schedule())
        for button in (1, 2, 3):
            self.canvas.bind(f"<ButtonPress-{button}>", self.drag_start)
            self.canvas.bind(f"<B{button}-Motion>", self.drag_move)
            self.canvas.bind(f"<ButtonRelease-{button}>", self.drag_end)
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.bind("<Button-4>", self.wheel)
        self.canvas.bind("<Button-5>", self.wheel)
        self.canvas.bind("<KeyPress>", self.key_move)
        self.canvas.bind("<KeyRelease>", self.key_release)
        self.canvas.bind("<FocusOut>", self.focus_lost)

        self.camera_status = tk.StringVar()
        ttk.Label(self.top, textvariable=self.camera_status,
                  wraplength=820, padding=(8, 1)).pack(fill="x")
        self._update_camera_status()
        ttk.Label(self.top, textvariable=self.comparison_status,
                  wraplength=820, padding=(8, 1)).pack(fill="x")
        self.status = tk.StringVar(
            value=("Preparing compiled original UV renderer "
                   "(first frame warms the JIT cache once)"
                   if self.fast_active else
                   "Slow fallback UV renderer: install Numba for fast navigation"))
        ttk.Label(self.top, textvariable=self.status,
                  padding=(8, 0)).pack(fill="x")
        if not embedded:
            self.top.protocol("WM_DELETE_WINDOW", self.close)
        self._poll_id = self.top.after(
            16 if self.fast_active else 40, self._poll_completed)
        self.schedule()

    def schedule(self, *, navigation: bool = False):
        """Request a frame: nav ticks coalesce without starving the renderer.

        Holding keys may cause more pose updates than the CPU can render.
        Don't cancel every in-flight native frame, or NONE will ever display.
        """
        if self._closed:
            return
        self._update_camera_status()
        self._request_version += 1
        if not navigation and self._cancel_render is not None:
            self._cancel_render.set()
        if self._pending is not None:
            try:
                self.top.after_cancel(self._pending)
            except tk.TclError:
                pass
        self._pending = self.top.after(
            0 if navigation else (24 if self.fast_active else 85),
            self._request_full_render)

    def _update_camera_status(self):
        cam = self.camera
        self.camera_status.set(
            f"Camera EYE (source local): X={cam.position[0]:.3f}, "
            f"Y={cam.position[1]:.3f}, Z={cam.position[2]:.3f} "
            f"· yaw={cam.yaw:.3f}, pitch={cam.pitch:.3f} "
            "· RMB turn must NOT change eye X/Y/Z")

    def _request_full_render(self):
        self._pending = None
        if self._closed:
            return
        width = min(1280, self.canvas.winfo_width())
        height = min(800, self.canvas.winfo_height())
        if width < 16 or height < 16:
            return
        # Low-resolution interactions keep the full source mesh but reduce
        # pixel shading; pointer-up always requests full-quality rendering.
        if (getattr(self, "drag_button", None) is not None
                or bool(getattr(self, "_held_keys", ()))) and self.fast_active:
            width = max(16, int(width * .68))
            height = max(16, int(height * .68))
        mode = self.mode.get() if hasattr(self, "mode") else "Textures"
        kcl = getattr(self, "comparison_kcl", None)
        self._queued = (self._request_version, width, height,
                        self.camera, mode, kcl)
        self.status.set(
            f"Rendering all {len(self.model.faces):,} native UV triangles "
            "(" + ("compiled CPU" if self.fast_active else "slow NumPy fallback") + ")")
        self._start_latest()

    def _start_latest(self):
        if self._closed or self._render_future is not None or self._queued is None:
            return
        version, width, height, camera, mode, kcl = self._queued
        self._queued = None
        cancel = Event()
        self._cancel_render = cancel
        future = self._executor.submit(
            self._render_frame, width, height, camera, cancel.is_set,
            mode, kcl)
        self._render_future = (version, camera, future)

    def _render_frame(self, width, height, camera, cancelled,
                      mode="Textures", collision=None):
        """Worker-only: one source-local camera, no Tk operations or writes."""
        if cancelled():
            raise PreviewCancelled()
        started = time.perf_counter()
        if mode == "Collision" and collision is not None:
            from PIL import Image
            image, drawn = Image.new("RGB", (width, height), (19, 32, 46)), 0
        elif self.fast_scene is not None:
            image, drawn = render_fast(self.fast_scene, width, height, camera)
        else:
            image, drawn = render_preview(
                self.model, width, height, camera=camera,
                textures=self.textures, cancelled=cancelled)
        if cancelled():
            raise PreviewCancelled()
        if collision is not None and mode in {"Collision", "Both"}:
            image = draw_comparison(image, collision, camera, mode=mode)
        if cancelled():
            raise PreviewCancelled()
        return image, drawn, (time.perf_counter()-started)*1000.

    def _poll_completed(self):
        if self._closed:
            return
        active = self._render_future
        if active is not None and active[2].done():
            version, camera, future = active
            self._render_future = None
            self._cancel_render = None
            try:
                image, drawn, render_ms = future.result()
                if (version == self._request_version
                        or bool(getattr(self, "_held_keys", ()))):
                    # During continuous navigation, show completed poses even
                    # if a newer one is queued. Otherwise slow rendering could
                    # starve the visible canvas until the key is released.
                    from PIL import ImageTk
                    # Interactive half-resolution frames reduce raster cost.
                    # Scale the presentation ONLY, never omit source triangles.
                    target = (min(1280, self.canvas.winfo_width()),
                              min(800, self.canvas.winfo_height()))
                    if image.size != target and min(target) >= 16:
                        from PIL import Image
                        image = image.resize(target, Image.Resampling.BILINEAR)
                    self.image_ref = ImageTk.PhotoImage(image, master=self.canvas)
                    self.canvas.delete("all")
                    self.canvas.create_image(0, 0, image=self.image_ref,
                                             anchor="nw")
                    engine = ("compiled CPU" if self.fast_active
                              else "slow NumPy CPU")
                    self.status.set(
                        f"{drawn:,} visible / {len(self.model.faces):,} "
                        f"source triangles · {render_ms:.0f} ms {engine} "
                        "· one canvas · KCL registration display-only, UNVERIFIED")
            except PreviewCancelled:
                pass
            except (VisualAssetError, OSError, ValueError,
                    ImportError, RuntimeError) as exc:
                if version == self._request_version:
                    self.status.set(f"Source texture preview unavailable: {exc}")
            if self._queued is not None:
                self._start_latest()
        if not self._closed:
            self._poll_id = self.top.after(
                16 if self.fast_active else 40, self._poll_completed)

    def draw(self):
        self.schedule()

    def drag_start(self, event):
        self.drag_origin = (event.x, event.y)
        self.drag_button = getattr(event, "num", 1)
        self.canvas.focus_set()

    def drag_move(self, event):
        if self.drag_origin is None:
            return
        dx = event.x - self.drag_origin[0]
        dy = event.y - self.drag_origin[1]
        if self.drag_button == 3:
            self.camera = look_in_place(self.camera, dx, dy)
        elif self.drag_button == 2:
            self.camera = pan(self.camera, dx, dy,
                              max(16, self.canvas.winfo_height()))
        elif self.drag_button == 1:
            self.camera = orbit(self.camera, dx, dy)
        else:
            return
        self.drag_origin = (event.x, event.y)
        self.schedule()

    def drag_end(self, event):
        if self.drag_button == getattr(event, "num", None):
            self.drag_origin = None
            self.drag_button = None
            # Fly keys are valid ONLY while RMB is held; arrows still work.
            for key in ("w", "a", "s", "d", "q", "e"):
                self._held_keys.discard(key)
                handle = self._pending_key_releases.pop(key, None)
                if handle is not None:
                    try:
                        self.top.after_cancel(handle)
                    except tk.TclError:
                        pass
            if not self._held_keys and self._nav_timer is not None:
                self._stop_navigation()
            else:
                self.schedule()

    def wheel(self, event):
        n = wheel_steps(getattr(event, "delta", None),
                        getattr(event, "num", None))
        if n:
            self.camera = dolly(self.camera, n)
            self.canvas.focus_set()
            self.schedule()

    def key_move(self, event):
        """Start smooth navigation; key repeat must not cause discrete jumps."""
        key = getattr(event, "keysym", "").lower()
        shifted = bool(getattr(event, "state", 0) & 0x0001)
        if key in {"shift_l", "shift_r"}:
            self._shift_held = True
            return None
        if key == "f":
            if shifted:
                self.frame_all()
            else:
                self.frame()
            return "break"
        arrows = {"up", "down", "left", "right"}
        fly = {"w", "a", "s", "d", "q", "e"}
        if key not in arrows and not (key in fly and self.drag_button == 3):
            return None
        self._shift_held = shifted or self._shift_held
        pending = self._pending_key_releases.pop(key, None)
        if pending is not None:
            try:
                self.top.after_cancel(pending)
            except tk.TclError:
                pass
        self._held_keys.add(key)
        if self._nav_timer is None:
            self._last_nav_tick = time.perf_counter()
            self._last_nav_render = 0.
            self._nav_timer = self.top.after(16, self._navigation_tick)
        return "break"

    def key_release(self, event):
        """Debounce Windows/Linux auto-repeat KeyRelease/KeyPress pairs."""
        key = getattr(event, "keysym", "").lower()
        if key in {"shift_l", "shift_r"}:
            self._shift_held = False
            return None
        if key not in self._held_keys:
            return None
        existing = self._pending_key_releases.pop(key, None)
        if existing is not None:
            try:
                self.top.after_cancel(existing)
            except tk.TclError:
                pass
        self._pending_key_releases[key] = self.top.after(
            45, lambda held_key=key: self._finish_key_release(held_key))
        return "break"

    def _finish_key_release(self, key):
        self._pending_key_releases.pop(key, None)
        self._held_keys.discard(key)
        if not self._held_keys:
            self._stop_navigation()

    def _navigation_tick(self):
        """Apply time-proportional velocity even with NO key-repeat events."""
        self._nav_timer = None
        if self._closed or not self._held_keys:
            return
        now = time.perf_counter()
        dt = max(0., min(.05, now - self._last_nav_tick))
        self._last_nav_tick = now
        previous = self.camera
        self.camera = move_continuous(
            self.camera, self._held_keys, dt,
            right_mouse=self.drag_button == 3, fast=self._shift_held)
        if self.camera != previous and now - self._last_nav_render >= .035:
            self._last_nav_render = now
            self.schedule(navigation=True)
        self._nav_timer = self.top.after(16, self._navigation_tick)

    def _stop_navigation(self):
        if self._nav_timer is not None:
            try:
                self.top.after_cancel(self._nav_timer)
            except tk.TclError:
                pass
            self._nav_timer = None
        if not self._closed:
            # One final exact full-pixel source render after the key stops.
            self.schedule()

    def focus_lost(self, event=None):
        """Never keep flying when user Alt+Tabs or clicks another control."""
        for handle in self._pending_key_releases.values():
            try:
                self.top.after_cancel(handle)
            except tk.TclError:
                pass
        self._pending_key_releases.clear()
        self._held_keys.clear()
        self._shift_held = False
        self._stop_navigation()


    def frame(self, event=None):
        self.camera = self.home_camera
        self.schedule()

    def frame_all(self, event=None):
        self.camera = self.full_camera
        self.schedule()

    def set_collision_terrain(self, terrain):
        """Show actual KCL source faces in SAME camera, explicitly uncalibrated."""
        if terrain is None:
            self.comparison_kcl = None
            self.mode.set("Textures")
            self.comparison_status.set(
                "KCL not loaded · no original collision/visual alignment claim.")
        else:
            comp = prepare_comparison_kcl(terrain, self.model)
            self.comparison_kcl = comp
            self.mode.set("Both")
            self.comparison_status.set(overlay_summary(comp))
        self.schedule()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._cancel_render is not None:
            self._cancel_render.set()
        for handle in (self._pending, self._poll_id, self._nav_timer,
                       *self._pending_key_releases.values()):
            if handle is not None:
                try:
                    self.top.after_cancel(handle)
                except tk.TclError:
                    pass
        self._held_keys.clear()
        self._pending_key_releases.clear()
        self._nav_timer = None
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.image_ref = None
        self.top.destroy()
