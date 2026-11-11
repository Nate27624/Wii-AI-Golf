"""Source-coordinate Tkinter replay and opt-in read-only live candidate inspector."""
from __future__ import annotations

import math
import time
import platform
import subprocess
import sys
from collections import deque
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .replay import AIM, BALL, CACHE, Replay, Sample, float_hypothesis, load_replay
from .live import LiveSampler
from .a_reference import discover_reference
from .a_live import LiveAIndicator
from .terrain import TerrainError, TerrainMesh, load_private_obj, surface_style, SURFACE_STYLE, MAX_DRAW_FACES
from .terrain_solid import back_to_front, shaded_hex
from .terrain_labels import apply_private_surface_labels
from .visual_model import VisualAssetError, load_private_visual_model
from .dae_visual import load_private_dae_visual_model
from .startup import StartupError, occupied_bridge, powershell_command, runtime_checkout
from .tree_positions import TreePositions, TreePositionsError, load_private_tree_positions
from .tree_render import draw_tree_layer, fit_points
from .asset_preferences import (
    AssetSelections, SavedAssetError, discover_private_tree,
    inspect_private_trees, load_asset_selections, remember_asset, save_asset_selections,
)

# Source-qualified candidate channels already captured by the existing read-only
# P0 packet reader.  These are hypotheses, not calibrated screen positions.
PIN = "pin_candidate"
TEE = "tee_start_candidate"


def candidate_landmarks(sample: Sample) -> dict[str, tuple[float, float, float]]:
    """Qualified per-sample pin/tee only; never join actors or invent positions.

    A missing or malformed channel remains absent. No carry-forward between
    packets: a pin in a different source epoch cannot leak into this view.
    """
    if not sample.source_qualified or not sample.source_digest:
        return {}
    return {key: point for key in (PIN, TEE)
            if (point := sample.vec(key)) is not None}


def aim_ray_hypothesis(
    sample: Sample, landmarks: dict[str, tuple[float, float, float]],
    baseline: float | None = None
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    """Tee-to-flag reference rotated by relative +0x3C *hypothesis*.

    No player coordinates anywhere. At a calibrated baseline (+0x3C == baseline)
    the ray ALWAYS points to the pin, regardless of absolute field yaw/angle.
    Ball position is not consulted. Direction-of-change/radians are unproven.
    """
    if not sample.source_qualified or not sample.source_digest or baseline is None or not math.isfinite(baseline):
        return None
    tee, pin = landmarks.get(TEE), landmarks.get(PIN)
    raw = sample.words.get(AIM)
    if tee is None or pin is None or raw is None or len(raw) != 1:
        return None
    angle = float_hypothesis(raw[0])
    if angle is None or not -math.tau <= angle <= math.tau or not -math.tau <= baseline <= math.tau:
        return None
    dx, dz = pin[0] - tee[0], pin[2] - tee[2]
    distance = math.hypot(dx, dz)
    if not 1e-5 < distance <= 1e6:
        return None
    delta = angle - baseline
    # Rotates in the candidate horizontal component0/component2 plane. The
    # direction/sign mapping is still an empirical hypothesis, not calibrated.
    cos_a, sin_a = math.cos(delta), math.sin(delta)
    length = 0.23
    tip = (tee[0] + length * (dx*cos_a - dz*sin_a),
           tee[1],
           tee[2] + length * (dx*sin_a + dz*cos_a))
    return tee, tip


def project(point: tuple[float, float, float], yaw: float, pitch: float) -> tuple[float, float]:
    """Orthographic rotating *source-coordinate* projection; not screen calibration."""
    x, y, z = point
    u = x * math.cos(yaw) + z * math.sin(yaw)
    v = y * math.cos(pitch) + (z * math.cos(yaw) - x * math.sin(yaw)) * math.sin(pitch)
    return u, v


def _known_private_visual_candidate(terrain_obj: str) -> Path | None:
    """Optional local operator candidate, never proof of which hole is active.

    Only auto-discover alongside an explicitly selected private terrain OBJ.
    Never scan the game disc, Git workspace or any external locations.
    """
    if not terrain_obj:
        return None
    base = Path(terrain_obj).absolute().parent
    candidates = (
        base / "WiiGolfVisualPrivate" / "visual_exports" /
        "glf_course_fc1" / "glf_course_fc1.dae",
        Path("D:/Projects/WiiGolfVisualPrivate/visual_exports/glf_course_fc1/glf_course_fc1.dae"),
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


class Inspector:
    def __init__(self, root: tk.Tk, initial_capture: str = "", initial_manifest: str = "",
                 initial_terrain_obj: str = "", initial_terrain_labels: str = "",
                 initial_visual_dae: str = ""):
        self.root = root
        root.title("Wii Golf · P0 Memory Inspector — OFFLINE CANDIDATES")
        root.geometry("1320x850")
        root.minsize(1000, 650)
        self.capture = tk.StringVar(value=initial_capture)
        self.manifest = tk.StringVar(value=initial_manifest)
        self.status = tk.StringVar(value="No capture loaded. Training not approved.")
        self.detail = tk.StringVar(value="Source candidates are NOT verified physics measurements.")
        self.phase = tk.StringVar(value="—")
        self.aim = tk.StringVar(value="Aim candidate: —")
        self.landmark_status = tk.StringVar(value="Pin / flag: not sampled   ·   Tee: not sampled")
        self.aim_status = tk.StringVar(value="Aim ray: set a tee→flag baseline first; no player position.")
        self.aim_baseline_source: str | None = None
        self.aim_baseline_mode = "assumed first packet"
        self.a_indicator = LiveAIndicator(None)
        self.a_status = tk.StringVar(value="A UNKNOWN")
        self.terrain_mesh: TerrainMesh | None = None
        self.terrain_visible = tk.BooleanVar(value=True)
        self.terrain_focus = tk.BooleanVar(value=False)
        self.terrain_full_detail = tk.BooleanVar(value=True)
        self.terrain_point_labels = tk.BooleanVar(value=False)
        self.terrain_colors = tk.BooleanVar(value=True)
        self.terrain_solid = tk.BooleanVar(value=True)
        self.terrain_edges = tk.BooleanVar(value=False)
        self.terrain_status = tk.StringVar(value="Terrain: select a locally exported PRIVATE collision OBJ to display.")
        self.surface_label_status = tk.StringVar(value="Surface colors: no original KCL labels loaded (neutral shading only).")
        self.tree_positions: TreePositions | None = None
        self.tree_visible = tk.BooleanVar(value=True)
        self.tree_illustrations = tk.BooleanVar(value=True)
        self.tree_labels = tk.BooleanVar(value=False)
        self.tree_status = tk.StringVar(value="Trees: no original PRIVATE 94-position JSON loaded.")
        self.asset_settings_status = tk.StringVar(value="Private tree/terrain file paths saved locally, never in Git.")
        self.saved_assets = AssetSelections()
        self.visual_status = tk.StringVar(value="Visual source: no private model loaded. Active hole and alignment UNVERIFIED.")
        self.visual_preview = None
        self.a_reason = tk.StringVar(value="Connect LIVE with A released; 2 stable samples initialize candidate")
        self.baseline: float | None = None
        self.replay: Replay | None = None
        self.index = tk.IntVar(value=0)
        self.yaw, self.pitch = 0.65, 0.48
        self.drag_origin: tuple[int, int] | None = None
        self.drag_button: int | None = None
        self.live_worker: LiveSampler | None = None
        self.live_buffer: deque[Sample] = deque(maxlen=180)
        self.live_last: float | None = None
        self.live_rate = 0.0
        self.live_location = ""
        self.live_port = tk.StringVar(value="55355")
        self.startup_process: subprocess.Popen | None = None
        self._draw_controls()
        self.restore_private_assets()
        if initial_terrain_obj:
            loaded = self.load_terrain_path(initial_terrain_obj, show_dialog=False)
            if loaded:
                self._remember_private_asset("terrain_obj", initial_terrain_obj)
            if loaded and initial_terrain_labels:
                self.load_terrain_labels_path(initial_terrain_labels, show_dialog=False)
        # A prior local original-art export is auto-loaded when the operator
        # already selected the sibling SHA-qualified private KCL. This is a
        # visual-source candidate, NOT verified in-game hole or coordinate map.
        effective_terrain = initial_terrain_obj or self.saved_assets.terrain_obj or ""
        private_candidate = (_known_private_visual_candidate(effective_terrain)
                             if not initial_visual_dae else None)
        selected_visual = initial_visual_dae or (
            str(private_candidate) if private_candidate is not None else "")
        if selected_visual:
            if not self.load_visual_path(selected_visual, show_dialog=False):
                if initial_visual_dae:
                    raise RuntimeError("Explicit private source visual DAE failed: " +
                                       self.visual_status.get())
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(200, self.poll_live)
        if initial_capture and initial_manifest:
            self.open_capture()

    def _draw_controls(self) -> None:
        head = ttk.Frame(self.root, padding=12)
        head.pack(fill="x")
        ttk.Label(head, text="P0 Memory Inspector  ·  offline replay", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(head, text="All positions are candidate component0/1/2 in UNKNOWN units. No power, velocity, guest frame, rendered actor or training claim.").pack(anchor="w")
        for text, variable in (("Capture JSONL", self.capture), ("SHA-256 manifest", self.manifest)):
            row = ttk.Frame(head)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=text, width=20).pack(side="left")
            ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)
            ttk.Button(row, text="Browse", command=lambda var=variable: self.pick(var)).pack(side="left", padx=5)
        actions = ttk.Frame(head)
        actions.pack(fill="x", pady=4)
        ttk.Button(actions, text="Verify SHA-256 and Open Offline", command=self.open_capture).pack(side="left")
        ttk.Label(actions, text="  Existing Dolphin bridge port: ").pack(side="left")
        ttk.Entry(actions, textvariable=self.live_port, width=7).pack(side="left")
        ttk.Button(actions, text="Connect LIVE (read-only)", command=self.connect_live).pack(side="left", padx=5)
        ttk.Button(actions, text="Disconnect", command=self.disconnect_live).pack(side="left")
        ttk.Button(actions, text="PowerShell: Launch ready for shot",
                   command=self.open_game_startup,
                   state="normal" if platform.system() == "Windows" else "disabled").pack(side="left", padx=(10, 0))
        ttk.Label(head, textvariable=self.status, foreground="#9b271d", wraplength=1190).pack(anchor="w")
        a_panel = ttk.Frame(head)
        a_panel.pack(fill="x", pady=3)
        ttk.Label(a_panel, textvariable=self.a_status, font=("Segoe UI", 17, "bold")).pack(side="left")
        ttk.Label(a_panel, text="  Candidate only · start with A RELEASED · press after two baseline samples",
                  foreground="#566171").pack(side="left")

        main = ttk.PanedWindow(self.root, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10)
        left = ttk.LabelFrame(main, text="Phase / sample", padding=8)
        center = ttk.LabelFrame(main, text="Unified 3D: original textures + candidate KCL (display fit UNVERIFIED)", padding=8)
        right = ttk.LabelFrame(main, text="Raw source candidates", padding=8)
        main.add(left, weight=1)
        main.add(center, weight=3)
        main.add(right, weight=2)
        self.phase_list = tk.Listbox(left, exportselection=False, width=19)
        self.phase_list.pack(fill="both", expand=True)
        self.phase_list.bind("<<ListboxSelect>>", self.select_phase)
        ttk.Label(left, textvariable=self.phase, wraplength=190).pack(fill="x", pady=6)
        ttk.Button(left, text="Set aim baseline (point at flag)", command=self.set_baseline).pack(fill="x")
        ttk.Button(left, text="Load PRIVATE visual DAE / OBJ", command=self.open_textured_model).pack(fill="x", pady=(6, 0))
        ttk.Button(left, text="Show unified 3D source viewer", command=self.show_visual_tab).pack(fill="x", pady=(3, 0))
        ttk.Label(left, textvariable=self.aim, wraplength=200).pack(fill="x", pady=7)

        # ONE visible 3D canvas. The legacy terrain Tk canvas and its
        # provenance-safe replay drawing functions are retained ONLY as a
        # fallback when no private source visual DAE has been loaded.
        # Once a DAE exists, the source KCL is shown in the SAME 3D camera
        # via an explicitly unverified display-only bounding-box fit.
        self.visual_tab = ttk.Frame(center, padding=2)
        terrain_tab = ttk.Frame(center, padding=2)
        self._legacy_terrain_tab = terrain_tab
        terrain_tab.pack(fill="both", expand=True)
        shared_actions = ttk.Frame(center)
        shared_actions.pack(side="bottom", fill="x")
        ttk.Button(shared_actions, text="Load KCL OBJ",
                   command=self.load_terrain).pack(side="left")
        ttk.Button(shared_actions, text="Load KCL source IDs",
                   command=self.load_terrain_labels).pack(side="left", padx=3)
        ttk.Button(shared_actions, text="Clear KCL",
                   command=self.clear_terrain).pack(side="left")
        ttk.Label(shared_actions,
                  text="Shared camera; KCL-vs-texture fit is DISPLAY ONLY, not physics.",
                  wraplength=260).pack(side="left", padx=5)
        tree_actions = ttk.Frame(center)
        tree_actions.pack(side="bottom", fill="x", pady=1)
        ttk.Button(tree_actions, text="Load PRIVATE 94 trees",
                   command=self.load_tree_positions).pack(side="left")
        ttk.Button(tree_actions, text="Clear trees",
                   command=self.clear_tree_positions).pack(side="left", padx=4)
        ttk.Checkbutton(tree_actions, text="Show trees", variable=self.tree_visible,
                        command=self._tree_options_changed).pack(side="left")
        ttk.Checkbutton(tree_actions, text="Illustrative crowns (NOT game art)",
                        variable=self.tree_illustrations,
                        command=self._tree_options_changed).pack(side="left", padx=4)
        ttk.Checkbutton(tree_actions, text="Tree IDs", variable=self.tree_labels,
                        command=self._tree_options_changed).pack(side="left")
        tree_info = ttk.Frame(center)
        tree_info.pack(side="bottom", fill="x", pady=1)
        ttk.Label(tree_info, textvariable=self.tree_status, wraplength=650).pack(anchor="w")
        ttk.Label(tree_info, textvariable=self.asset_settings_status,
                  wraplength=650).pack(anchor="w")
        ttk.Label(self.visual_tab, textvariable=self.visual_status,
                  wraplength=630).pack(fill="x", pady=(1, 3))

        self.canvas = tk.Canvas(terrain_tab, background="#111c29", height=450, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw_path())
        self.canvas.bind("<ButtonPress-1>", self.drag_start)
        self.canvas.bind("<B1-Motion>", self.drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.drag_end)
        self.canvas.bind("<ButtonPress-3>", self.drag_start)
        self.canvas.bind("<B3-Motion>", self.drag_move)
        self.canvas.bind("<ButtonRelease-3>", self.drag_end)
        # Narrow center pane: split terrain controls into real rows rather
        # than silently clipping checkboxes beyond the viewport width.
        mesh_actions = ttk.Frame(terrain_tab)
        mesh_actions.pack(fill="x", pady=2)
        ttk.Button(mesh_actions, text="Load PRIVATE terrain OBJ", command=self.load_terrain).pack(side="left")
        ttk.Button(mesh_actions, text="Load source colors", command=self.load_terrain_labels).pack(side="left", padx=4)
        ttk.Button(mesh_actions, text="Clear terrain", command=self.clear_terrain).pack(side="left", padx=4)

        quality_actions = ttk.Frame(terrain_tab)
        quality_actions.pack(fill="x", pady=2)
        ttk.Checkbutton(quality_actions, text="Show", variable=self.terrain_visible, command=self.draw_path).pack(side="left")
        ttk.Checkbutton(quality_actions, text="Solid terrain", variable=self.terrain_solid, command=self.draw_path).pack(side="left")
        ttk.Checkbutton(quality_actions, text="All triangles", variable=self.terrain_full_detail, command=self.draw_path).pack(side="left")
        ttk.Checkbutton(quality_actions, text="Triangle edges", variable=self.terrain_edges, command=self.draw_path).pack(side="left")

        overlay_actions = ttk.Frame(terrain_tab)
        overlay_actions.pack(fill="x", pady=2)
        ttk.Checkbutton(overlay_actions, text="Focus tee/flag", variable=self.terrain_focus, command=self.draw_path).pack(side="left")
        ttk.Checkbutton(overlay_actions, text="Color source surface IDs", variable=self.terrain_colors, command=self.draw_path).pack(side="left")
        ttk.Checkbutton(overlay_actions, text="Point labels", variable=self.terrain_point_labels, command=self.draw_path).pack(side="left")

        view_actions = ttk.Frame(terrain_tab)
        view_actions.pack(fill="x", pady=2)
        ttk.Button(view_actions, text="Top-down", command=lambda: self.set_terrain_view(0.0, 1.35)).pack(side="left")
        ttk.Button(view_actions, text="Isometric", command=lambda: self.set_terrain_view(0.65, 0.60)).pack(side="left", padx=5)
        ttk.Label(terrain_tab, textvariable=self.terrain_status, wraplength=650).pack(anchor="w")
        ttk.Label(terrain_tab, textvariable=self.surface_label_status, wraplength=650).pack(anchor="w")
        source_legend = ttk.Frame(terrain_tab)
        source_legend.pack(fill="x")
        for label, color in (SURFACE_STYLE[v] for v in (0x0001,0x0002,0x0003,0x0006,0x0007,0x0009)):
            ttk.Label(source_legend, text=label, foreground=color).pack(side="left", padx=4)
        ttk.Label(source_legend, text="other/unknown: neutral; ID hypotheses", foreground="#a1aab7").pack(side="left")
        ttk.Label(terrain_tab, text="White: ball +0x30  |  Amber: cache +0xCC  |  Cyan flag: PIN candidate  |  Green diamond: TEE candidate", wraplength=640).pack(anchor="w")
        ttk.Label(terrain_tab, textvariable=self.landmark_status, wraplength=640).pack(anchor="w")
        ttk.Label(terrain_tab, text="Magenta dashed: flag-aligned aim reference, rotated only by Δ+0x3C (unverified mapping; no player position)", wraplength=640).pack(anchor="w")
        ttk.Label(terrain_tab, textvariable=self.aim_status, wraplength=640).pack(anchor="w")
        self.slider = ttk.Scale(terrain_tab, from_=0, to=1, command=self.scrub)
        self.slider.pack(fill="x", pady=4)
        buttons = ttk.Frame(terrain_tab)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="◀", command=lambda: self.move(-1)).pack(side="left")
        ttk.Button(buttons, text="▶", command=lambda: self.move(1)).pack(side="left")
        self.position = ttk.Label(buttons, text="0 / 0")
        self.position.pack(side="left", padx=15)

        self.rows = ttk.Treeview(right, columns=("hex", "f32"), show="tree headings")
        self.rows.heading("#0", text="Field / component")
        self.rows.heading("hex", text="BE-u32 raw")
        self.rows.heading("f32", text="BE-f32 hypothesis")
        self.rows.column("#0", width=220)
        self.rows.column("hex", width=100)
        self.rows.column("f32", width=125)
        self.rows.pack(fill="both", expand=True)
        scroll = ttk.Scrollbar(right, orient="vertical", command=self.rows.yview)
        scroll.pack(side="right", fill="y")
        self.rows.configure(yscrollcommand=scroll.set)
        lower = ttk.LabelFrame(self.root, text="Sampling / provenance / warnings", padding=8)
        lower.pack(fill="x", padx=10, pady=8)
        ttk.Label(lower, textvariable=self.detail, wraplength=1250, justify="left").pack(anchor="w")

    def show_visual_tab(self) -> None:
        """One visible 3D viewport with source texture/KCL visibility modes."""
        if self.visual_preview is None:
            return
        self._legacy_terrain_tab.pack_forget()
        self.visual_tab.pack(fill="both", expand=True)
        self.visual_preview.schedule()

    def load_visual_path(self, filename: str, *, show_dialog: bool = False) -> bool:
        """Embed original source art in the inspector WITHOUT KCL alignment."""
        try:
            model = (load_private_dae_visual_model(filename)
                     if Path(filename).suffix.lower() == ".dae"
                     else load_private_visual_model(filename))
            from .textured_preview import TexturedPreviewWindow
            preview = TexturedPreviewWindow(self.visual_tab, model, embedded=True)
            if getattr(self, "terrain_mesh", None) is not None:
                try:
                    preview.set_collision_terrain(self.terrain_mesh)
                except ValueError as align_error:
                    preview.comparison_status.set(
                        "KCL source comparison unavailable: " + str(align_error))
        except (VisualAssetError, OSError, RuntimeError, tk.TclError,
                ImportError, ValueError) as exc:
            self.visual_status.set("Visual source declined: " + str(exc))
            if show_dialog:
                messagebox.showerror("Private visual model unavailable",
                                     str(exc), parent=self.root)
            return False
        prior = self.visual_preview
        self.visual_preview = preview
        self._sync_visual_trees()
        if prior is not None:
            prior.close()
        self.visual_status.set(
            f"PRIVATE source preview: {model.source_name} · "
            f"{len(model.faces):,} renderable UV triangles · "
            "native hole/world/KCL alignment NOT verified")
        self.show_visual_tab()
        return True

    def open_textured_model(self) -> None:
        """Load a source UV visual model in the INTEGRATED visual tab."""
        filename = filedialog.askopenfilename(
            parent=self.root,
            title="Choose PRIVATE original Collada DAE or UV OBJ",
            filetypes=[("Original Collada DAE", "*.dae"),
                       ("UV Wavefront OBJ", "*.obj")])
        if filename:
            self.load_visual_path(filename, show_dialog=True)

    def load_terrain(self) -> None:
        """User opt-in: load only local private OBJ, never read live RAM for terrain."""
        filename = filedialog.askopenfilename(
            title="Select local source-coordinate private KCL collision OBJ",
            filetypes=[("Wavefront OBJ", "*.obj")])
        if filename and self.load_terrain_path(filename, show_dialog=True):
            self._remember_private_asset("terrain_obj", filename)

    def load_terrain_path(self, filename: str, *, show_dialog: bool = False) -> bool:
        """Load user-selected private OBJ and its validated source material groups."""
        try:
            mesh = load_private_obj(filename)
        except (TerrainError, OSError) as exc:
            if show_dialog:
                messagebox.showerror("Private terrain declined", str(exc))
            self.terrain_status.set("Terrain: private OBJ declined by path/format verification.")
            return False
        self.terrain_mesh = mesh
        # New OBJ invalidates any earlier face-index/source-label association.
        if hasattr(self, "surface_label_status"):
            self.surface_label_status.set("Surface colors: no original KCL labels loaded (neutral shading only).")
        self.terrain_visible.set(True)
        self.terrain_status.set(
            f"PRIVATE terrain OBJ: {len(mesh.faces)} candidate triangles, SHA {mesh.sha256[:12]}… "
            "· visual alignment/active collision UNVERIFIED")
        self.draw_path()
        Inspector._sync_visual_terrain(self)
        return True

    def load_terrain_labels(self) -> None:
        """Operator opt-in: select source labels independently of mesh bytes."""
        filename = filedialog.askopenfilename(
            title="Select SHA-bound PRIVATE KCL source surface labels",
            filetypes=[("Private source label JSON", "*.json")])
        if filename:
            self.load_terrain_labels_path(filename, show_dialog=True)

    def load_terrain_labels_path(self, filename: str, *, show_dialog: bool = False) -> bool:
        """Style the existing loaded OBJ in memory; never modify its file."""
        mesh = self.terrain_mesh
        if mesh is None:
            self.surface_label_status.set("Surface colors: load the private terrain OBJ first.")
            return False
        try:
            labeled = apply_private_surface_labels(mesh, filename)
        except TerrainError as exc:
            # These messages are authored static validation categories:
            # surface only the category, never paths or native RAM values.
            if show_dialog:
                messagebox.showerror("Private source colors declined", str(exc))
            self.surface_label_status.set(f"Source colors: rejected — {exc}")
            return False
        except OSError:
            # OSError text may contain a sensitive absolute private path.
            if show_dialog:
                messagebox.showerror("Private source colors declined",
                                     "Local labels could not be read safely.")
            self.surface_label_status.set("Source colors: rejected — local file read error")
            return False
        self.terrain_mesh = labeled
        self.surface_label_status.set(
            f"Source colors: {len(labeled.faces)} original KCL per-face IDs linked by OBJ SHA "
            "· candidate visual categories, not physics")
        self.draw_path()
        Inspector._sync_visual_terrain(self)
        return True

    def _sync_visual_terrain(self) -> None:
        # Existing GUI source-inspector tests use small SimpleNamespace
        # stubs without a visual preview. Terrain data must remain usable
        # independently of the optional source texture viewer.
        if getattr(self, "visual_preview", None) is None:
            return
        try:
            self.visual_preview.set_collision_terrain(self.terrain_mesh)
        except ValueError as exc:
            self.visual_preview.comparison_status.set(
                "KCL source comparison unavailable: " + str(exc))

    def clear_terrain(self) -> None:
        self.terrain_mesh = None
        self.surface_label_status.set("Surface colors: no original KCL labels loaded.")
        self.terrain_status.set("Terrain: no private OBJ loaded.")
        if hasattr(self, "saved_assets"):
            Inspector._remember_private_asset(self, "terrain_obj", None)
        self.draw_path()
        Inspector._sync_visual_terrain(self)

    def _remember_private_asset(self, kind: str, filename: str | None) -> None:
        """Persist only the approved local path; never source positions/art."""
        try:
            updated = remember_asset(self.saved_assets, kind, filename)
            save_asset_selections(updated)
            self.saved_assets = updated
            self.asset_settings_status.set(
                "Private terrain/tree selections saved locally; reloaded at next launch.")
        except (SavedAssetError, OSError, ValueError) as exc:
            self.asset_settings_status.set(
                f"Could not remember local asset path: {exc}. Current view remains loaded.")

    def _load_terrain_file(self, filename: str, *, remember: bool = False) -> None:
        mesh = load_private_obj(filename)
        self.terrain_mesh = mesh
        self.terrain_visible.set(True)
        self.terrain_status.set(
            f"PRIVATE terrain OBJ: {len(mesh.faces)} candidate triangles, SHA {mesh.sha256[:12]}… "
            "· visual alignment/active collision UNVERIFIED")
        if remember:
            self._remember_private_asset("terrain_obj", filename)
        self.draw_path()

    def _load_tree_file(self, filename: str, *, remember: bool = False) -> None:
        tree_positions = load_private_tree_positions(filename)
        self.tree_positions = tree_positions
        self.tree_visible.set(True)
        self.tree_status.set(
            "94 exact PRIVATE source tree bases loaded · unified Both/Collision shows "
            "source tree x-rays when KCL available · native model/alignment/hitboxes UNVERIFIED.")
        if remember:
            self._remember_private_asset("tree_json", filename)
        self.draw_path()
        Inspector._sync_visual_trees(self)

    def load_tree_positions(self) -> None:
        """Select one verified local private tree file; remember selection."""
        filename = filedialog.askopenfilename(
            parent=self.root,
            title="Select source-gated PRIVATE 94-tree positions from Wii-AI-Golf-Data/derived",
            filetypes=[("Private tree source JSON", "*.json")])
        if not filename:
            return
        try:
            self._load_tree_file(filename, remember=True)
        except (TreePositionsError, OSError) as exc:
            messagebox.showerror("Private tree source rejected", str(exc), parent=self.root)

    def clear_tree_positions(self) -> None:
        self.tree_positions = None
        self.tree_status.set("Trees: cleared; automatic discovery disabled until next manual selection.")
        self._remember_private_asset("tree_json", None)
        self.draw_path()
        Inspector._sync_visual_trees(self)

    def restore_private_assets(self) -> None:
        """On launch restore saved local asset paths; fail closed without dialogs.

        First launch tries only the original expected PRIVATE filename in known
        local folders, then persists that path if the strict loader accepts it.
        A saved invalid path reports an error rather than loading a different
        tree file or silently applying guessed geometry.
        """
        try:
            self.saved_assets = load_asset_selections()
        except (SavedAssetError, OSError) as exc:
            self.saved_assets = AssetSelections()
            self.asset_settings_status.set(f"Saved selections invalid/unavailable: {exc}")
        saved = self.saved_assets
        if saved.terrain_obj is not None:
            try:
                self._load_terrain_file(saved.terrain_obj)
            except (TerrainError, OSError) as exc:
                self.terrain_status.set(f"Saved PRIVATE terrain not loaded: {exc}")
        if saved.tree_json is not None:
            try:
                self._load_tree_file(saved.tree_json)
            except (TreePositionsError, OSError) as exc:
                self.tree_status.set(f"Saved PRIVATE trees not loaded: {exc}")
        elif saved.auto_find_trees:
            # The earlier #411 exporter writes a fixed private filename;
            # discovery never searches other arbitrary JSON or the network.
            checkout = Path(__file__).resolve().parents[3]
            candidate = discover_private_tree(checkout)
            if candidate is not None:
                try:
                    self._load_tree_file(str(candidate), remember=True)
                except (TreePositionsError, OSError) as exc:
                    self.tree_status.set(f"Auto-discovered PRIVATE tree source rejected: {exc}")
            else:
                _, checks = inspect_private_trees(checkout)
                rejected = next(((path, reason) for path, reason in checks
                                 if reason.startswith("rejected:")), None)
                if rejected is not None:
                    path, reason = rejected
                    self.tree_status.set(
                        f"Trees NOT auto-loaded: {reason} ({path}). "
                        "Use a verified PRIVATE source JSON outside Git or select manually.")
                elif checks:
                    self.tree_status.set(
                        f"Trees NOT auto-loaded: PRIVATE source-94 JSON not found in "
                        f"{len(checks)} known locations. Expected: {checks[0][0]}. "
                        "Choose Load PRIVATE 94 trees if stored elsewhere.")
                else:
                    self.tree_status.set(
                        "Trees NOT auto-loaded: no known PRIVATE data locations found.")
        elif saved.tree_json is None:
            self.tree_status.set(
                "Trees auto-loading disabled by Clear trees. "
                "Select Load PRIVATE 94 trees to re-enable it.")
        if saved.terrain_obj or saved.tree_json:
            self.asset_settings_status.set(
                "Saved private asset path(s) checked on launch. Use Load/Clear to change.")

    def _tree_options_changed(self) -> None:
        self.draw_path()
        Inspector._sync_visual_trees(self)

    def _sync_visual_trees(self) -> None:
        preview = getattr(self, "visual_preview", None)
        if preview is None:
            return
        data = getattr(self, "tree_positions", None)
        points = data.drawing_positions() if data is not None else ()
        preview.set_tree_overlay(
            points, visible=self.tree_visible.get(),
            illustrations=self.tree_illustrations.get(),
            labels=self.tree_labels.get())

    def pick(self, var: tk.StringVar) -> None:
        name = filedialog.askopenfilename(title="Choose local file (not uploaded)")
        if name:
            var.set(name)

    def open_capture(self) -> None:
        self.disconnect_live(silent=True)
        self.live_worker = None
        try:
            replay = load_replay(Path(self.capture.get()), Path(self.manifest.get()))
        except (OSError, ValueError) as exc:
            self.replay = None
            self.status.set(f"VERIFY FAILED — {exc}")
            self.phase_list.delete(0, "end")
            self.rows.delete(*self.rows.get_children())
            self.canvas.delete("all")
            self.landmark_status.set("Pin / flag: capture unavailable   ·   Tee: capture unavailable")
            self.aim_status.set("Aim ray: unavailable (capture integrity failed).")
            messagebox.showerror("Integrity / capture error", str(exc))
            return
        self.replay = replay
        self.baseline = None
        self.aim_baseline_source = None
        self.a_indicator = LiveAIndicator(None)
        self.a_status.set("A UNKNOWN")
        self.phase_list.delete(0, "end")
        self.phases: list[tuple[str, int]] = []
        for i, sample in enumerate(replay.samples):
            if not self.phases or self.phases[-1][0] != sample.phase:
                self.phases.append((sample.phase, i))
                self.phase_list.insert("end", f"{sample.phase}  [{sample.state}]")
        self.slider.configure(to=max(1, len(replay.samples) - 1))
        self.status.set(f"SHA-256 VERIFIED {replay.sha256[:16]}…  ·  {len(replay.samples)} samples  ·  {replay.terminated.upper()}  ·  training_approved=false")
        self.show(0)

    def show(self, i: int) -> None:
        if self.replay is None:
            return
        i = max(0, min(i, len(self.replay.samples) - 1))
        self.index.set(i)
        self.slider.set(i)
        sample = self.replay.samples[i]
        # The initial sample is a *provisional* flag-pointing baseline, NOT a
        # native heading. User can explicitly reset at visually known pin aim.
        if self.baseline is None and i == 0 and sample.source_qualified and sample.source_digest:
            raw = sample.words.get(AIM)
            value = float_hypothesis(raw[0]) if raw and len(raw) == 1 else None
            if value is not None and -math.tau <= value <= math.tau:
                self.baseline = value
                self.aim_baseline_source = sample.source_digest
                self.aim_baseline_mode = "ASSUMED first packet points to flag"
        self.phase.set(f"{sample.phase} / sample {sample.phase_index if sample.phase_index is not None else '?'}  ·  {sample.state.upper()}")
        self.position.config(text=f"{i + 1} / {len(self.replay.samples)}")
        active = max(j for j, (_, start) in enumerate(self.phases) if start <= i)
        self.phase_list.selection_clear(0, "end")
        self.phase_list.selection_set(active)
        self.phase_list.see(active)
        self.rows.delete(*self.rows.get_children())
        for field, bits in sorted(sample.words.items()):
            parent = self.rows.insert("", "end", text=field, open=field in {BALL, CACHE, AIM})
            for component, word in enumerate(bits):
                value = float_hypothesis(word)
                self.rows.insert(parent, "end", text=f"component{component}",
                                 values=(f"0x{word:08X}", f"{value:.7g}" if value is not None else "nonfinite"))
        aim_values = sample.words.get(AIM)
        a = float_hypothesis(aim_values[0]) if aim_values and len(aim_values) == 1 else None
        delta = a - self.baseline if a is not None and self.baseline is not None else None
        self.aim.set(f"Aim raw: {aim_values[0]:08X}" if aim_values else "Aim: unavailable")
        if a is not None:
            self.aim.set(self.aim.get() + f"\nCandidate float: {a:.6g}" + (f"\nΔ baseline: {delta:+.6g}" if delta is not None else "\nBaseline not set"))
        timestamp = (f"Host sample end {sample.end_ns} ns" if sample.end_ns is not None else "Host time unavailable")
        details = (*self.replay.messages(sample), *self.replay.warnings)
        if sample.annotation:
            details += (f"Operator annotation: {sample.annotation}",)
        self.detail.set(f"{timestamp} | " + "  •  ".join(details))
        self.draw_path()

    def open_game_startup(self) -> None:
        """Explicit operator-controlled game boot/menu sequence in a visible PS.

        The usual LIVE sampler remains strictly read-only. This separate
        button (after confirmation) invokes the repo's existing canonical
        A -> A+B -> A startup; it NEVER fires a shot or fabricates a ready
        screen claim. Do not run it from an unconfigured detached worktree.
        """
        if platform.system() != "Windows":
            messagebox.showerror("Windows PowerShell required", "This startup button is Windows-only.")
            return
        process = getattr(self, "startup_process", None)
        if process is not None and process.poll() is None:
            messagebox.showinfo("PowerShell already open", "Close the prior startup PowerShell window before launching again.")
            return
        try:
            port = int(self.live_port.get())
            runtime = runtime_checkout(Path(__file__).resolve().parents[3])
            attach = occupied_bridge(port)
            argv = powershell_command(runtime, Path(sys.executable), port, attach=attach)
        except (ValueError, OSError, StartupError) as exc:
            messagebox.showerror("Golf launcher not ready", str(exc))
            return

        target = "reset the existing game's registered checkpoint" if attach else "start a NEW Dolphin session"
        if not messagebox.askyesno("Launch Hitting the Green?",
              "This will " + target + " and automatically send A, A+B, A to the menu.\n\n"
              "It may discard current in-game progress, but will NOT overwrite a savestate or swing.\n"
              "You must visually confirm the golfer is ready to hit. Proceed?"):
            return

        worker = self.live_worker
        if worker is not None:
            worker.stop()
            thread = worker.thread
            if thread is not None and thread.is_alive():
                thread.join(timeout=2.0)
                if thread.is_alive():
                    messagebox.showerror("Inspector is still sampling",
                                         "The read-only worker is still exiting. Retry after it disconnects.")
                    return
            self.live_worker = None
            self.live_last = None
            self.a_indicator.clear()
            self.a_status.set("A UNKNOWN")
            self.a_reason.set("Launch in separate PowerShell; reconnect when ready")
            self.draw_a_overlay()
        try:
            self.startup_process = subprocess.Popen(
                argv, cwd=str(runtime), shell=False,
                creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0))
        except (OSError, ValueError) as exc:
            messagebox.showerror("Unable to open PowerShell", str(exc))
            return
        self.status.set("POWERSHELL STARTED · startup/menu dispatch in separate console; "
                        "visually verify ready golfer, then Connect LIVE. No swing sent.")

    def connect_live(self) -> None:
        if self.live_worker is not None and self.live_worker.thread is not None and self.live_worker.thread.is_alive():
            return
        # Discover only a cryptographically sealed local trial from the
        # sibling PRIVATE Data/captures directory. No calibration controls.
        self.a_indicator = LiveAIndicator(discover_reference(Path(__file__).resolve().parents[3]))
        try:
            port = int(self.live_port.get())
            worker = LiveSampler(port=port, include_a_state=True)
        except ValueError as exc:
            messagebox.showerror("Invalid bridge port", str(exc))
            return
        self.live_worker = worker
        self.live_buffer.clear()
        self.live_last = None
        self.baseline = None
        self.aim_baseline_source = None
        self.a_status.set("A UNKNOWN")
        self.a_reason.set("Connecting; first two samples assume A is RELEASED")
        self.replay = None
        self.phases = []
        self.phase_list.delete(0, "end")
        self.rows.delete(*self.rows.get_children())
        self.canvas.delete("all")
        self.landmark_status.set("Pin / flag: awaiting read-only sample   ·   Tee: awaiting sample")
        self.aim_status.set("Aim ray: awaiting qualified aim, tee and pin candidates.")
        self.status.set("CONNECTING read-only to EXISTING Dolphin. No controller, savestate, boot or guest writes.")
        worker.start()

    def disconnect_live(self, silent: bool = False) -> None:
        if self.live_worker is not None:
            self.live_worker.stop()
            if not silent:
                self.status.set("DISCONNECT requested; RPC timeout may delay worker exit. No automatic reconnection.")

    def poll_live(self) -> None:
        worker = self.live_worker
        if worker is not None:
            for event in worker.drain():
                if event.kind == "sample" and event.sample is not None:
                    self.live_buffer.append(event.sample)
                    self.live_last = time.monotonic()
                    self.live_rate = event.rate_hz
                    self.live_location = f"scene 5 · mode 4 · hole {event.hole} · selected player {event.selected_player}"
                    self.replay = Replay(Path("LIVE-readonly"), "", tuple(self.live_buffer), (), "live")
                    self.phases = [("LIVE", 0)]
                    self.phase_list.delete(0, "end")
                    self.phase_list.insert("end", "LIVE source-qualified")
                    self.slider.configure(to=max(1, len(self.live_buffer) - 1))
                    self.show(len(self.live_buffer) - 1)
                    self.process_a_sample(event)
                    self.status.set(f"LIVE READ-ONLY · {self.live_location} · {self.live_rate:.2f} samples/s "
                                    f"· read {event.read_duration_ms:.0f} ms / {event.rpc_calls} RPCs "
                                    "· source checked · training_approved=false")
                elif event.kind == "error":
                    self.status.set("LIVE FAILED: " + event.reason + " Existing sample trace frozen. Check RSPE01 Rev1 and bridge.")
                    self.live_last = None
                    self.a_status.set("A UNKNOWN")
                    self.a_reason.set("bridge disconnected, stale, or error")
                    self.draw_a_overlay()
                    self.a_indicator.clear()
                elif event.kind == "disconnected":
                    self.status.set("LIVE DISCONNECTED. Existing sample trace retained; no background retries.")
                    self.live_last = None
                    self.a_status.set("A UNKNOWN")
                    self.a_reason.set("bridge disconnected, stale, or error")
                    self.draw_a_overlay()
                    self.a_indicator.clear()
            if self.live_last is not None:
                age = time.monotonic() - self.live_last
                if age > 3.0:
                    self.a_status.set("A UNKNOWN")
                    self.a_reason.set("bridge disconnected, stale, or error")
                    self.draw_a_overlay()
                    self.a_indicator.clear()
                    self.status.set(f"STALE LIVE SAMPLE {age:.1f}s ago · {self.live_location} · check source/bridge · training_approved=false")
        self.root.after(200, self.poll_live)

    def close(self) -> None:
        self.disconnect_live(silent=True)
        self.live_worker = None
        if self.visual_preview is not None:
            self.visual_preview.close()
            self.visual_preview = None
        self.root.destroy()

    def set_baseline(self) -> None:
        if self.replay is None:
            return
        sample = self.replay.samples[self.index.get()]
        bits = sample.words.get(AIM)
        landmarks = candidate_landmarks(sample)
        if (sample.source_qualified and sample.source_digest and TEE in landmarks and PIN in landmarks
                and bits is not None and len(bits) == 1):
            value = float_hypothesis(bits[0])
            if value is not None and -math.tau <= value <= math.tau:
                self.baseline = value
                self.aim_baseline_source = sample.source_digest
                self.aim_baseline_mode = "OPERATOR set pointed-at-flag reference"
                self.show(self.index.get())

    def process_a_sample(self, event: object) -> None:
        """Passive text only. No calibration buttons or inferred input labels."""
        sample = event.sample
        if sample is None:
            self.a_status.set("A UNKNOWN")
            self.a_indicator.clear()
            return
        state = self.a_indicator.observe(
            event.a_record, sample.source_digest,
            sample.words.get(BALL), sample.words.get(AIM))
        self.a_status.set("A " + state)
        self.a_reason.set(self.a_indicator.mode)
        self.draw_a_overlay()


    def select_phase(self, _: object) -> None:
        selection = self.phase_list.curselection()
        if selection and self.replay is not None:
            self.show(self.phases[selection[0]][1])

    def scrub(self, value: str) -> None:
        if self.replay is not None:
            i = int(float(value) + 0.5)
            if i != self.index.get():
                self.show(i)

    def move(self, direction: int) -> None:
        self.show(self.index.get() + direction)

    def set_terrain_view(self, yaw: float, pitch: float) -> None:
        """Local viewer camera preset; never changes Dolphin/game state."""
        if not (math.isfinite(yaw) and math.isfinite(pitch)
                and -1.4 <= pitch <= 1.4):
            return
        self.yaw, self.pitch = yaw, pitch
        self.draw_path()

    def drag_start(self, event: tk.Event) -> None:
        self.drag_origin = (event.x, event.y)
        self.drag_button = getattr(event, "num", 1)

    def drag_end(self, event: tk.Event) -> None:
        if self.drag_button == getattr(event, "num", 1):
            self.drag_origin = None
            self.drag_button = None

    def drag_move(self, event: tk.Event) -> None:
        if self.drag_origin is None:
            return
        x, y = self.drag_origin
        self.yaw += (event.x - x) * 0.01
        self.pitch = min(1.4, max(-1.4, self.pitch + (event.y - y) * 0.01))
        self.drag_origin = (event.x, event.y)
        self.draw_path()

    def draw_a_overlay(self) -> None:
        """A readout stays visible in the upper right of the 3D viewport.

        No game input or source-coordinate geometry is involved; overlay is
        screen anchored, not a badge/button and not a player marker.
        """
        canvas = self.canvas
        canvas.delete("a_state_overlay")
        status = getattr(self, "a_status", None)
        value = status.get() if status is not None else "A UNKNOWN"
        shade = "#e7f4ff" if value == "A PRESSED" else "#b4bed1"
        right = max(canvas.winfo_width()-16, 16)
        canvas.create_text(right, 17, anchor="ne",
                           text=value, fill=shade, font=("Segoe UI", 19, "bold"),
                           tags=("a_state_overlay",))
        reason = getattr(self, "a_reason", None)
        if reason is not None:
            canvas.create_text(right, 47, anchor="ne",
                               text=reason.get(), fill="#a9b8cd", font=("Segoe UI", 9),
                               tags=("a_state_overlay",))

    def draw_path(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        if self.replay is None:
            self.draw_a_overlay()
            return
        width, height = max(canvas.winfo_width(), 1), max(canvas.winfo_height(), 1)
        upto = self.index.get()
        samples = self.replay.samples[:upto + 1]
        path = [(s.vec(BALL), s) for s in samples]
        path = [(p, s) for p, s in path if p is not None]
        caches = [(s.vec(CACHE), s) for s in samples]
        caches = [(p, s) for p, s in caches if p is not None]
        current = self.replay.samples[upto]
        landmarks = candidate_landmarks(current)
        if not current.source_qualified or not current.source_digest:
            self.landmark_status.set("Pin / flag and tee: HIDDEN — source qualification/identity unavailable")
        else:
            pin_state = "sampled" if PIN in landmarks else "not sampled / invalid float"
            tee_state = "sampled" if TEE in landmarks else "not sampled / invalid float"
            self.landmark_status.set(f"Pin / flag: {pin_state}   ·   Tee: {tee_state}   (candidate coordinates, units unknown)")
        # Only source-qualified, same-packet aim+tee+pin can draw a heading
        # hypothesis. Never infer or display a player/body position.
        aim_ray = aim_ray_hypothesis(current, landmarks,
                                      self.baseline if self.aim_baseline_source == current.source_digest else None)
        if aim_ray is not None:
            angle = float_hypothesis(current.words[AIM][0])
            self.aim_status.set(f"Aim: {self.aim_baseline_mode} · Δ+0x3C={angle - self.baseline:+.5g} rad HYPOTHESIS · anchored at TEE, no player coords")
        elif not current.source_qualified or not current.source_digest:
            self.aim_status.set("Aim ray: HIDDEN — source qualification/identity unavailable")
        else:
            self.aim_status.set("Aim ray: unavailable — requires same-source tee, pin and baseline +0x3C; press Set aim baseline when pointed at flag")
        # SOURCE-QUALIFIED private geometry only, with unverified coordinate
        # alignment. Keep previous synthetic GUI test stubs working if they
        # don't construct optional terrain fields.
        terrain_faces = ()
        colored_faces = ()
        mesh = getattr(self, "terrain_mesh", None)
        showing = getattr(self, "terrain_visible", None)
        focusing = getattr(self, "terrain_focus", None)
        if (mesh is not None and (showing is None or showing.get())
                and current.source_qualified and bool(current.source_digest)):
            # Full-face drawing preserves the collision surface. Prior stride
            # preview drew only 600/1200 of 2498 triangles, leaving large gaps.
            # Users can explicitly select the bounded fast preview again.
            live_mode = bool(self.live_worker is not None and self.live_last is not None)
            full_setting = getattr(self, "terrain_full_detail", None)
            request_complete = full_setting is not None and full_setting.get()
            limit = min(len(mesh.faces), MAX_DRAW_FACES) if request_complete else (
                600 if live_mode else 1200)
            colored_faces = mesh.drawing_colored_faces(
                tuple(landmarks.values()), focused=(focusing is None or focusing.get()), limit=limit)
            terrain_faces = tuple(face for face, _ in colored_faces)
            if hasattr(self, "terrain_status"):
                labeled = sum(n for code,n in mesh.material_counts().items() if code is not None)
                self.terrain_status.set(
                    f"PRIVATE terrain: {len(terrain_faces)}/{len(mesh.faces)} "
                    f"triangles drawn · {labeled}/{len(mesh.faces)} source-ID labeled · "
                    + ("COMPLETE" if len(terrain_faces) == len(mesh.faces)
                       else "PARTIAL PREVIEW (gaps expected)")
                    + " · alignment/active collision UNVERIFIED")
        elif mesh is not None and hasattr(self, "terrain_status"):
            self.terrain_status.set("Terrain HIDDEN — Show disabled or source qualification unavailable")
        tree_data = getattr(self, "tree_positions", None)
        tree_toggle = getattr(self, "tree_visible", None)
        crown_toggle = getattr(self, "tree_illustrations", None)
        id_toggle = getattr(self, "tree_labels", None)
        show_crowns = crown_toggle is not None and crown_toggle.get()
        draw_tree_positions = (
            tree_data.drawing_positions()
            if tree_data is not None
            and (tree_toggle is None or tree_toggle.get())
            and current.source_qualified and bool(current.source_digest)
            else ())
        tree_fit = fit_points(draw_tree_positions, illustrations=show_crowns) if draw_tree_positions else ()
        # Plot bounds include the selected collision candidate; do NOT transform
        # vertices to force fit with the ball, tee or pin.
        points = ([p for p, _ in path + caches] + list(landmarks.values())
                  + (list(aim_ray) if aim_ray else [])
                  + [v for face in terrain_faces for v in face] + list(tree_fit))
        if not points:
            canvas.create_text(width // 2, height // 2, text="No finite source-qualified ball/cache/pin/tee candidates", fill="white")
            self.draw_a_overlay()
            return
        axes = [project(p, self.yaw, self.pitch) for p in points]
        low_x, high_x = min(p[0] for p in axes), max(p[0] for p in axes)
        low_y, high_y = min(p[1] for p in axes), max(p[1] for p in axes)
        scale = min(max(1, width - 100) / max(1e-7, high_x - low_x),
                    max(1, height - 90) / max(1e-7, high_y - low_y))
        cx, cy = (low_x + high_x) / 2, (low_y + high_y) / 2
        def xy(p):
            u, v = project(p, self.yaw, self.pitch)
            return width / 2 + (u - cx) * scale, height / 2 - (v - cy) * scale
        canvas.create_text(12, 12, text="Rotatable 3D source-coordinate projection · unknown units", anchor="nw", fill="#bacbe1")
        label_setting = getattr(self, "terrain_point_labels", None)
        point_labels = label_setting is None or label_setting.get()
        # Painter's-order solid triangles (not a Z-buffer), beneath all
        # source-qualified actor/aim/A overlays. Never infer missing IDs.
        solid_setting = getattr(self, "terrain_solid", None)
        edges_setting = getattr(self, "terrain_edges", None)
        solid = solid_setting is not None and solid_setting.get()
        edges = edges_setting is None or edges_setting.get()
        palette = getattr(self, "terrain_colors", None)
        use_colors = palette is None or palette.get()
        for face, source_attr in back_to_front(colored_faces, self.yaw, self.pitch):
            xy_face = [xy(v) for v in face]
            flat = tuple(value for p in xy_face for value in p)
            base = surface_style(source_attr)[1] if use_colors else "#536778"
            if solid:
                canvas.create_polygon(
                    *flat, fill=shaded_hex(base, face),
                    outline=base if edges else "", width=1 if edges else 0,
                    tags=("terrain_collision_candidate", "terrain_solid_face"))
            elif edges:
                canvas.create_line(
                    *flat, *xy_face[0], fill=base, width=1,
                    tags=("terrain_collision_candidate", "terrain_wire_edge"))
        if draw_tree_positions:
            draw_tree_layer(
                canvas, draw_tree_positions, xy, self.yaw, self.pitch,
                illustrations=show_crowns,
                labels=id_toggle is not None and id_toggle.get(),
            )
        # Recenter per displayed prefix; do not imply screen-space projection or verified spatial units.
        for sequence, color in ((path, "#f1f6ff"), (caches, "#f5b942")):
            previous = None
            previous_source = None
            for point, sample in sequence:
                pos = xy(point)
                if previous is not None and previous_source == sample.source_digest:
                    canvas.create_line(*previous, *pos, fill=color, width=2, dash=(5, 4) if color == "#f5b942" else ())
                r = 5 if sample is samples[-1] else 2.5
                canvas.create_oval(pos[0]-r, pos[1]-r, pos[0]+r, pos[1]+r, fill=color, outline="")
                previous, previous_source = pos, sample.source_digest
        # Draw hypothesis ray underneath landmarks, never a player sprite or
        # estimated golfer location. The anchor is the tee point ONLY.
        if aim_ray is not None:
            start, tip = xy(aim_ray[0]), xy(aim_ray[1])
            canvas.create_line(*start, *tip, fill="#e39bff", width=3,
                               dash=(8, 5), arrow=tk.LAST, arrowshape=(10, 12, 4),
                               tags=("aim_hypothesis",))
            if point_labels:
                canvas.create_text(tip[0] + 7, tip[1] - 10, text="AIM? (flag ref + Δ0x3C)",
                                   anchor="sw", fill="#e39bff", tags=("aim_hypothesis",))
        if point_labels:
            for name, color in ((BALL, "#f1f6ff"), (CACHE, "#f5b942")):
                position = current.vec(name)
                if position is not None:
                    x, y = xy(position)
                    canvas.create_text(x + 8, y - 12, anchor="w",
                                       text=("ball +0x30" if name == BALL else "cache +0xCC"),
                                       fill=color)
        # Draw the flag LAST, over ball/cache trails: the pin should remain
        # unmistakable even when a cache value exactly equals the pin candidate.
        if TEE in landmarks:
            x, y = xy(landmarks[TEE])
            canvas.create_polygon(x, y - 8, x + 8, y, x, y + 8, x - 8, y,
                                  fill="#59d47d", outline="#173a23", width=1,
                                  tags=("tee_candidate",))
            if point_labels:
                canvas.create_text(x + 11, y + 11, anchor="nw", text="TEE (candidate)",
                                   fill="#59d47d", tags=("tee_candidate",))
        if PIN in landmarks:
            x, y = xy(landmarks[PIN])
            canvas.create_line(x, y + 13, x, y - 14, fill="#44d7ef", width=3,
                               tags=("pin_candidate",))
            canvas.create_polygon(x, y - 14, x + 20, y - 8, x, y - 2,
                                  fill="#44d7ef", outline="#e3fcff", width=1,
                                  tags=("pin_candidate",))
            canvas.create_oval(x - 3, y + 10, x + 3, y + 16,
                               fill="#44d7ef", outline="", tags=("pin_candidate",))
            if point_labels:
                canvas.create_text(x + 23, y - 14, anchor="nw", text="PIN / FLAG (candidate)",
                                   fill="#44d7ef", tags=("pin_candidate",))
        canvas.create_text(12, height - 15, text="Left/right drag: orbit view. Initial aim assumed TEE→FLAG; Δ+0x3C radian/sign unverified; TEE ≠ player.", anchor="sw", fill="#bacbe1")
        # Overlay is intentionally last in Tk's display list, so trajectory
        # geometry cannot conceal the user-requested A text.
        self.draw_a_overlay()


def launch(capture: str = "", manifest: str = "", terrain_obj: str = "",
           terrain_labels: str = "", visual_dae: str = "") -> int:
    root = tk.Tk()
    try:
        Inspector(root, capture, manifest, terrain_obj, terrain_labels,
                  initial_visual_dae=visual_dae)
    except (VisualAssetError, OSError, RuntimeError, ImportError, ValueError):
        root.destroy()
        raise
    root.mainloop()
    return 0
