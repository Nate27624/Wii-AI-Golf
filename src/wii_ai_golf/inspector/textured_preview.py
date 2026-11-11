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
from .scene_camera import fit_camera, look_in_place, orbit, pan, dolly, move
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

        self.home_camera = fit_camera(model.vertices)
        self.camera = self.home_camera
        self.drag_origin: tuple[int, int] | None = None
        self.drag_button: int | None = None
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
        ttk.Button(controls, text="Frame (F)", command=self.frame).pack(side="left")
        ttk.Label(
            controls,
            text="RMB: look in place · LMB: orbit · MMB: pan · "
                 "Wheel: dolly · Hold RMB + WASD/QE: fly · Shift: faster",
            wraplength=670,
        ).pack(side="left", padx=8)

        self.canvas = tk.Canvas(self.top, background="#13202e",
                                highlightthickness=0, height=460)
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

    def schedule(self):
        """Coalesce rapid mouse/key events; never rasterize on Tk's UI thread."""
        if self._closed:
            return
        self._request_version += 1
        if self._cancel_render is not None:
            self._cancel_render.set()
        if self._pending is not None:
            try:
                self.top.after_cancel(self._pending)
            except tk.TclError:
                pass
        self._pending = self.top.after(
            24 if self.fast_active else 85, self._request_full_render)

    def _request_full_render(self):
        self._pending = None
        if self._closed:
            return
        width = min(1280, self.canvas.winfo_width())
        height = min(800, self.canvas.winfo_height())
        if width < 16 or height < 16:
            return
        self._queued = (self._request_version, width, height, self.camera)
        self.status.set(
            f"Rendering all {len(self.model.faces):,} native UV triangles "
            "(" + ("compiled CPU" if self.fast_active else "slow NumPy fallback") + ")")
        self._start_latest()

    def _start_latest(self):
        if self._closed or self._render_future is not None or self._queued is None:
            return
        version, width, height, camera = self._queued
        self._queued = None
        cancel = Event()
        self._cancel_render = cancel
        future = self._executor.submit(
            self._render_frame, width, height, camera, cancel.is_set)
        self._render_future = (version, camera, future)

    def _render_frame(self, width, height, camera, cancelled):
        """Worker-only: no Tk methods or UI graphics calls."""
        if cancelled():
            raise PreviewCancelled()
        started = time.perf_counter()
        if self.fast_scene is not None:
            image, drawn = render_fast(self.fast_scene, width, height, camera)
        else:
            image, drawn = render_preview(
                self.model, width, height, camera=camera,
                textures=self.textures, cancelled=cancelled)
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
                if version == self._request_version:
                    from PIL import ImageTk
                    self.image_ref = ImageTk.PhotoImage(image, master=self.canvas)
                    self.canvas.delete("all")
                    self.canvas.create_image(0, 0, image=self.image_ref,
                                             anchor="nw")
                    engine = ("compiled CPU" if self.fast_active
                              else "slow NumPy CPU")
                    self.status.set(
                        f"{drawn:,} visible / {len(self.model.faces):,} "
                        f"source triangles · {render_ms:.0f} ms {engine} "
                        "· source-local, not KCL-aligned")
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

    def wheel(self, event):
        n = wheel_steps(getattr(event, "delta", None),
                        getattr(event, "num", None))
        if n:
            self.camera = dolly(self.camera, n)
            self.canvas.focus_set()
            self.schedule()

    def key_move(self, event):
        if getattr(event, "keysym", "").lower() == "f":
            self.frame()
            return
        if self.drag_button != 3:
            return
        motion = {
            "w": (1., 0., 0.), "s": (-1., 0., 0.),
            "a": (0., -1., 0.), "d": (0., 1., 0.),
            "q": (0., 0., -1.), "e": (0., 0., 1.),
        }.get(getattr(event, "keysym", "").lower())
        if motion is None:
            return
        self.camera = move(
            self.camera, forward=motion[0],
            right=motion[1], vertical=motion[2],
            fast=bool(getattr(event, "state", 0) & 0x0001))
        self.schedule()

    def frame(self, event=None):
        self.camera = self.home_camera
        self.schedule()

    def close(self):
        if self._closed:
            return
        self._closed = True
        if self._cancel_render is not None:
            self._cancel_render.set()
        for handle in (self._pending, self._poll_id):
            if handle is not None:
                try:
                    self.top.after_cancel(handle)
                except tk.TclError:
                    pass
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.image_ref = None
        self.top.destroy()
