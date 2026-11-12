"""Tk source-UV viewport, embedded in the inspector or a standalone window.

Expensive full-source CPU raster runs on ONE cancellable worker. Tk widgets
and PhotoImage are exclusively updated on the main UI thread. Source models,
game memory, original collision OBJ and PNGs are NEVER modified.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Event
import math
import time
import tkinter as tk
from tkinter import ttk

from .navigation import wheel_steps
from .scene_camera import (
    fit_camera, frame_playable_camera, look_in_place, orbit, pan, dolly,
    move_continuous, camera_axes)
from .unified_source_view import (
    prepare_comparison_kcl, draw_comparison, draw_tree_comparison, overlay_summary)
from .material_alignment import (
    derive_material_alignment, MaterialAlignmentError)
from .texture_render import PreviewCancelled, prepare_textures, render_preview
from .texture_sampling import build_rgba_mips
from .fast_texture_render import (
    accelerated_available, prepare_fast_scene, render_fast)
from .visual_model import PrivateVisualModel, VisualAssetError
from .source_actor_overlay import (
    SourceActorSnapshot, illustrative_from_terrain, draw_source_actors)


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
        # Generated once in memory; preview mips are NOT original Wii TEX0 banks.
        self.texture_mips = (
            None if self.fast_active else
            {name:build_rgba_mips(arr) for name,arr in self.textures.items()})
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
        self._source_terrain = None
        # Source-authored Collada scene node matrices are now applied. No extra
        # guessed yaw is authoritative; rotations remain visual trials.
        self.display_rotation = tk.IntVar(value=0)
        # Opt-in visual review ONLY. Never saved as a native KCL transform.
        self.review_manual = False
        self.review_scale = 1.
        self.review_offset_xz = (0., 0.)
        self.review_status = tk.StringVar(
            value="Visual check: choose Review top-down; overlay is UNVERIFIED.")
        self.actor_snapshot = SourceActorSnapshot()
        self.illustrative_actors = SourceActorSnapshot()
        self.actor_sample_seen = False
        self.show_flag = tk.BooleanVar(value=True)
        self.show_ball = tk.BooleanVar(value=True)
        self.show_player = tk.BooleanVar(value=True)
        self.show_actor_labels = tk.BooleanVar(value=True)
        self.actor_status = tk.StringVar(value=(
            "Illustrative scene markers until source-qualified replay / LIVE"
            " is available. Real player XYZ not mapped."))
        self.tree_overlay = ()
        self.tree_overlay_visible = True
        self.tree_illustrations = True
        self.tree_labels = False
        self.mode = tk.StringVar(value="Textures")
        self.filtered_texture = tk.BooleanVar(value=True)
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
        scene_warning = getattr(model, "source_scene_warning", None)
        if scene_warning:
            ttk.Label(
                head, text=scene_warning,
                foreground="#c84820", wraplength=820,
            ).pack(anchor="w")
        else:
            ttk.Label(
                head,
                text="Collada-authored scene transforms applied where supported; "
                     "KCL/tee/pin native mapping UNVERIFIED · shaders approximate",
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
        for label in ("Textures", "Collision", "Both", "Overlay", "Split"):
            ttk.Radiobutton(
                controls, text=label, value=label, variable=self.mode,
                command=self.schedule).pack(side="left", padx=(1, 3))
        filter_controls = ttk.Frame(self.top, padding=(6, 2))
        filter_controls.pack(fill="x")
        ttk.Checkbutton(
            filter_controls, text="Smooth grass/terrain textures (preview filtering)",
            variable=self.filtered_texture, command=self.schedule,
        ).pack(side="left")
        ttk.Label(
            filter_controls,
            text="Mipmapped bilinear sampling · toggle off to inspect original TEX0 texels",
        ).pack(side="left", padx=9)
        review = ttk.Frame(self.top, padding=(6, 2))
        review.pack(fill="x")
        ttk.Button(review, text="Top-down view",
                   command=self.start_visual_review).pack(side="left")
        ttk.Label(review,
                  text="FC3 visual alignment operator-confirmed; physics coordinates unverified"
                  ).pack(side="left", padx=8)
        markers = ttk.Frame(self.top, padding=(6, 2))
        markers.pack(fill="x")
        ttk.Label(markers, text="Show in 3D:").pack(side="left")
        for label, state in (
            ("Flag", self.show_flag), ("Ball", self.show_ball),
            ("Player (tee proxy)", self.show_player),
            ("Labels", self.show_actor_labels)):
            ttk.Checkbutton(markers, text=label, variable=state,
                            command=self.schedule).pack(side="left", padx=(6, 0))
        ttk.Label(self.top, textvariable=self.actor_status,
                  padding=(8, 1), wraplength=1000).pack(fill="x")

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
        # Interactive navigation moves the eye at 60Hz, independent of
        # render throughput. Avoid full-resolution UV + mip filtering during
        # motion (especially without Numba). Restore full resolution and
        # smooth filtering immediately after release. Never stride-drop
        # original model faces or alter native UVs/vertices.
        interactive = (
            getattr(self, "drag_button", None) is not None or
            bool(getattr(self, "_held_keys", ())))
        if interactive:
            ratio = .68 if self.fast_active else .40
            width = max(16, int(width * ratio))
            height = max(16, int(height * ratio))
        mode = self.mode.get() if hasattr(self, "mode") else "Textures"
        kcl = getattr(self, "comparison_kcl", None)
        self._queued = (self._request_version, width, height,
                        self.camera, mode, kcl)
        self._queued_actor_snapshot = (
            getattr(self, "actor_snapshot", None)
            if getattr(self, "actor_sample_seen", False)
            else getattr(self, "illustrative_actors", None),
            bool(self.show_flag.get()) if hasattr(self, "show_flag") else True,
            bool(self.show_ball.get()) if hasattr(self, "show_ball") else True,
            bool(self.show_player.get()) if hasattr(self, "show_player") else True,
            bool(self.show_actor_labels.get()) if hasattr(self, "show_actor_labels") else True)
        self._queued_tree_snapshot = (
            getattr(self, "tree_overlay", ()),
            getattr(self, "tree_overlay_visible", True),
            getattr(self, "tree_illustrations", True),
            getattr(self, "tree_labels", False))
        filter_var = getattr(self, "filtered_texture", None)
        self._queued_texture_filter = (
            bool(filter_var.get()) if filter_var is not None else False
        ) and not interactive
        self.status.set(
            f"Rendering all {len(self.model.faces):,} native UV triangles "
            "(" + ("compiled CPU" if self.fast_active else "slow NumPy fallback") + ")")
        self._start_latest()

    def _start_latest(self):
        if self._closed or self._render_future is not None or self._queued is None:
            return
        version, width, height, camera, mode, kcl = self._queued
        tree_points, tree_visible, tree_illustrations, tree_labels = getattr(
            self, "_queued_tree_snapshot", ((), True, True, False))
        self._queued = None
        self._queued_tree_snapshot = None
        filtered = getattr(self, "_queued_texture_filter", False)
        self._queued_texture_filter = None
        actor_state = getattr(self, "_queued_actor_snapshot",
                              (None, True, True, True, True))
        self._queued_actor_snapshot = None
        cancel = Event()
        self._cancel_render = cancel
        future = self._executor.submit(
            self._render_frame, width, height, camera, cancel.is_set,
            mode, kcl, tree_points, tree_visible, tree_illustrations,
            tree_labels, filtered, actor_state)
        self._render_future = (version, camera, future)

    def _render_frame(self, width, height, camera, cancelled,
                      mode="Textures", collision=None, tree_points=(),
                       tree_visible=True, tree_illustrations=True,
                       tree_labels=False, filtered=False,
                       actor_state=(None, True, True, True, True)):
        """Worker-only: one source-local camera, no Tk operations or writes."""
        if cancelled():
            raise PreviewCancelled()
        started = time.perf_counter()
        if mode == "Collision" and collision is not None:
            from PIL import Image
            image, drawn = Image.new("RGB", (width, height), (19, 32, 46)), 0
        elif self.fast_scene is not None:
            image, drawn = render_fast(
                self.fast_scene, width, height, camera, filtered=filtered)
        else:
            image, drawn = render_preview(
                self.model, width, height, camera=camera,
                textures=self.textures, cancelled=cancelled,
                filtered=filtered, mipmaps=getattr(self,"texture_mips",None))
        if cancelled():
            raise PreviewCancelled()
        if collision is not None and mode in {"Collision", "Both", "Overlay", "Split"}:
            image = draw_comparison(image, collision, camera, mode=mode)
            # Split is a clean same-camera texture/KCL comparison. In Both
            # and Overlay the original source tree base markers remain visible.
            if mode != "Split" and tree_visible and tree_points:
                image = draw_tree_comparison(
                    image, collision, camera, tree_points,
                    illustrations=tree_illustrations, labels=tree_labels)
        if cancelled():
            raise PreviewCancelled()
        if collision is not None:
            actor, flag, ball, player, labels = actor_state
            image = draw_source_actors(
                image, collision, camera, actor,
                show_flag=flag, show_ball=ball,
                show_player=player, labels=labels)
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
                        or bool(getattr(self, "_held_keys", ()))
                        or getattr(self, "drag_button", None) is not None):
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
        # Mouse look/orbit must not discard every in-flight native frame.
        # Display progressive completed poses while continuously dragging.
        self.schedule(navigation=True)

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

    def _update_review_status(self):
        status_var = getattr(self, "review_status", None)
        if status_var is None:
            return
        if not getattr(self, "review_manual", False):
            status_var.set(
                "Visual review idle · show Both/Overlay/Split to inspect source KCL."
                " Native game/KCL registration UNVERIFIED.")
            return
        dx, dz = getattr(self, "review_offset_xz", (0., 0.))
        scale = getattr(self, "review_scale", 1.)
        status_var.set(
            f"MANUAL DISPLAY TRIAL · scale {scale:.4f}× of initial bounds fit"
            f" · X {dx:+.3f}, Z {dz:+.3f} of visual diagonal"
            " · no physical / Wii coordinate change. Tell me aligned YES/NO.")

    def start_visual_review(self):
        """One-click same-camera top-down inspection; no game/asset writes."""
        self.review_manual = True
        self.review_scale = 1.
        self.review_offset_xz = (0., 0.)
        # Top-down camera looks from visual-world +Y toward the course.
        cam = self.home_camera
        distance = math.dist(cam.position, cam.focus)
        yaw, pitch = 0., -1.35
        _, _, toward = camera_axes(yaw, pitch)
        self.camera = cam._replace(
            position=tuple(cam.focus[i] + toward[i] * distance for i in range(3)),
            yaw=yaw, pitch=pitch)
        # Hide illustrative crowns (not original tree meshes); source tree
        # BASES continue to display with exactly the same manual KCL fit.
        self.tree_illustrations = False
        self.display_rotation.set(0)
        self.mode.set("Overlay" if getattr(self, "_source_terrain", None)
                      is not None else "Textures")
        self._update_review_status()
        self.set_display_rotation(0)

    def nudge_visual_review(self, axis: str, direction: int):
        """Small bounded reversible UI-only transform for operator A/B checks."""
        if axis not in ("scale", "x", "z") or direction not in (-1, 1):
            raise ValueError("Unknown manual display adjustment")
        if getattr(self, "_source_terrain", None) is None:
            self._update_review_status()
            return
        self.review_manual = True
        scale = getattr(self, "review_scale", 1.)
        dx, dz = getattr(self, "review_offset_xz", (0., 0.))
        if axis == "scale":
            scale = min(4., max(.25, scale * (1.05 if direction > 0 else 1./1.05)))
        elif axis == "x":
            dx = max(-1., min(1., round(dx + direction * .01, 6)))
        else:
            dz = max(-1., min(1., round(dz + direction * .01, 6)))
        self.review_scale = scale
        self.review_offset_xz = (dx, dz)
        self._update_review_status()
        self.set_display_rotation()

    def reset_visual_review(self):
        """Restore source-derived display candidate, discard all manual edits."""
        self.review_manual = False
        self.review_scale = 1.
        self.review_offset_xz = (0., 0.)
        self.display_rotation.set(0)
        self._update_review_status()
        self.mode.set("Both" if getattr(self, "_source_terrain", None)
                      is not None else "Textures")
        self.set_display_rotation(0)

    def _source_comparison(self, terrain, yaw: int):
        """Return a display-mapping and reason, never fake native alignment.

        Most importantly, GEOMETRY-ONLY Collada imports can have a huge
        background and missing controller transforms. Whole-model bounding
        boxes DO NOT establish the KCL/tree scale. A source-material fit
        must pass independent surface and holdout checks before auto-overlay.
        """
        warning = getattr(self.model, "source_scene_warning", None)
        incomplete = isinstance(warning, str) and bool(warning)
        if getattr(self, "review_manual", False):
            # Review never calls centroid solver: the operator controls
            # coarse yaw, bounded scale and XZ offsets explicitly.
            mapped = prepare_comparison_kcl(
                terrain, self.model, rotation_degrees=yaw,
                display_scale_multiplier=getattr(self, "review_scale", 1.),
                display_offset_fraction_xz=getattr(
                    self, "review_offset_xz", (0., 0.)))
            reason = ("INCOMPLETE ORIGINAL DAE SCENE · " if incomplete else "")
            return mapped, (
                reason + "MANUAL VISUAL TRIAL, NOT PHYSICS · "
                + overlay_summary(mapped))
        if yaw == 0:
            try:
                fitted = derive_material_alignment(terrain, self.model)
            except MaterialAlignmentError as exc:
                if incomplete:
                    return None, (
                        "KCL/TREES AUTO-OVERLAY HIDDEN: " + str(exc) +
                        ". No guessed scale applied to geometry-only DAE. "
                        "Original source collision remains available in fallback.")
            else:
                mapped = prepare_comparison_kcl(
                    terrain, self.model, material_alignment=fitted)
                return mapped, overlay_summary(mapped)
        # Explicit nonzero dial remains an UNVERIFIED, user-selected
        # experiment; never apply the old bounds-fit automatically when an
        # original Collada controller/scene mapping is incomplete.
        mapped = prepare_comparison_kcl(
            terrain, self.model, rotation_degrees=yaw)
        status = overlay_summary(mapped)
        if incomplete:
            status = (
                "MANUAL BOUNDS-FIT TRIAL ONLY — SCALE NOT VERIFIED · " +
                status)
        return mapped, status

    def set_display_rotation(self, degrees=None):
        """Choose measured source display-fit or an explicitly guessed yaw."""
        angle = getattr(self, "display_rotation", None)
        value = degrees if degrees is not None else (
            angle.get() if angle is not None else 0)
        if type(value) is not int or value not in (0, 90, 180, 270):
            raise ValueError("KCL comparison yaw must be 0, 90, 180, or 270")
        if degrees is not None and angle is not None:
            angle.set(value)
        terrain = getattr(self, "_source_terrain", None)
        if terrain is not None:
            mapped, status = self._source_comparison(terrain, value)
            self.comparison_kcl = mapped
            if mapped is None:
                self.mode.set("Textures")
            self.comparison_status.set(status)
        self.schedule()

    def set_collision_terrain(self, terrain):
        """Source-labeled material fit; decline missing controller scale."""
        if terrain is None:
            self.illustrative_actors = SourceActorSnapshot()
            self._source_terrain = None
            self.comparison_kcl = None
            self.mode.set("Textures")
            self.comparison_status.set(
                "KCL not loaded · no original collision/visual alignment claim.")
        else:
            angle = getattr(self, "display_rotation", None)
            value = angle.get() if angle is not None else 0
            mapped, status = self._source_comparison(terrain, value)
            self._source_terrain = terrain
            self.illustrative_actors = illustrative_from_terrain(terrain)
            self.comparison_kcl = mapped
            self.mode.set("Both" if mapped is not None else "Textures")
            self.comparison_status.set(status)
        self.schedule()
        if hasattr(self, "actor_status"):
            self.set_actor_overlay(self.actor_snapshot if self.actor_sample_seen else None)

    def set_actor_overlay(self, snapshot: SourceActorSnapshot | None) -> None:
        """Same-packet replay/live actor snapshot; no stale field carryover."""
        if snapshot is not None and not isinstance(snapshot, SourceActorSnapshot):
            raise ValueError("Invalid current source actor sample")
        self.actor_sample_seen = snapshot is not None
        self.actor_snapshot = snapshot if snapshot is not None else SourceActorSnapshot()
        if self.actor_sample_seen:
            if self.actor_snapshot.source_qualified:
                status = ("SOURCE-QUALIFIED SAMPLE: selected ball/pin/tee when present."
                          " Player marker uses tee proxy, NOT actual player XYZ.")
            else:
                status = ("Source sample unqualified: all actor markers hidden;"
                          " never reusing stale source coordinates.")
        elif self.illustrative_actors.illustrative_only:
            status = ("ILLUSTRATIVE: flag≈green; ball/player≈far fairway."
                      " NOT actual source positions. Load replay / LIVE for data.")
        else:
            status = ("No source actors or classified terrain available."
                      " Load KCL labels and qualified replay / LIVE.")
        if hasattr(self, "actor_status"):
            self.actor_status.set(status)
        self.schedule()

    def set_tree_overlay(self, points, *, visible: bool, illustrations: bool,
                         labels: bool):
        """Only strict-loader positions; visual/KCL fit remains display-only."""
        from .tree_positions import SOURCE_TREE_COUNT
        points = tuple(points)
        if points and len(points) != SOURCE_TREE_COUNT:
            raise ValueError("Tree overlay requires exactly 94 source bases")
        self.tree_overlay = points
        self.tree_overlay_visible = bool(visible)
        self.tree_illustrations = bool(illustrations)
        self.tree_labels = bool(labels)
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
