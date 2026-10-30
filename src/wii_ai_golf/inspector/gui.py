"""Offline-only Tkinter source-coordinate replay UI (never connects to Dolphin)."""
from __future__ import annotations

import math
import time
from collections import deque
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .replay import AIM, BALL, CACHE, Replay, Sample, float_hypothesis, load_replay
from .live import LiveSampler


def project(point: tuple[float, float, float], yaw: float, pitch: float) -> tuple[float, float]:
    """Orthographic rotating *source-coordinate* projection; not screen calibration."""
    x, y, z = point
    u = x * math.cos(yaw) + z * math.sin(yaw)
    v = y * math.cos(pitch) + (z * math.cos(yaw) - x * math.sin(yaw)) * math.sin(pitch)
    return u, v


class Inspector:
    def __init__(self, root: tk.Tk, initial_capture: str = "", initial_manifest: str = ""):
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
        self.baseline: float | None = None
        self.replay: Replay | None = None
        self.index = tk.IntVar(value=0)
        self.yaw, self.pitch = 0.65, 0.48
        self.drag_origin: tuple[int, int] | None = None
        self.live_worker: LiveSampler | None = None
        self.live_buffer: deque[Sample] = deque(maxlen=180)
        self.live_last: float | None = None
        self.live_rate = 0.0
        self.live_location = ""
        self.live_port = tk.StringVar(value="55355")
        self._draw_controls()
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
        ttk.Label(head, textvariable=self.status, foreground="#9b271d", wraplength=1190).pack(anchor="w")

        main = ttk.PanedWindow(self.root, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10)
        left = ttk.LabelFrame(main, text="Phase / sample", padding=8)
        center = ttk.LabelFrame(main, text="3D candidate view — drag to rotate", padding=8)
        right = ttk.LabelFrame(main, text="Raw source candidates", padding=8)
        main.add(left, weight=1)
        main.add(center, weight=3)
        main.add(right, weight=2)
        self.phase_list = tk.Listbox(left, exportselection=False, width=19)
        self.phase_list.pack(fill="both", expand=True)
        self.phase_list.bind("<<ListboxSelect>>", self.select_phase)
        ttk.Label(left, textvariable=self.phase, wraplength=190).pack(fill="x", pady=6)
        ttk.Button(left, text="Set aim baseline here", command=self.set_baseline).pack(fill="x")
        ttk.Label(left, textvariable=self.aim, wraplength=200).pack(fill="x", pady=7)

        self.canvas = tk.Canvas(center, background="#111c29", height=450, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw_path())
        self.canvas.bind("<ButtonPress-1>", self.drag_start)
        self.canvas.bind("<B1-Motion>", self.drag_move)
        ttk.Label(center, text="White: selected ball candidate   |   Amber: cache +0xCC   |   No verified axes / screen projection", wraplength=640).pack(anchor="w")
        self.slider = ttk.Scale(center, from_=0, to=1, command=self.scrub)
        self.slider.pack(fill="x", pady=4)
        buttons = ttk.Frame(center)
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
            messagebox.showerror("Integrity / capture error", str(exc))
            return
        self.replay = replay
        self.baseline = None
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

    def connect_live(self) -> None:
        if self.live_worker is not None and self.live_worker.thread is not None and self.live_worker.thread.is_alive():
            return
        try:
            port = int(self.live_port.get())
            worker = LiveSampler(port=port)
        except ValueError as exc:
            messagebox.showerror("Invalid bridge port", str(exc))
            return
        self.live_worker = worker
        self.live_buffer.clear()
        self.live_last = None
        self.baseline = None
        self.replay = None
        self.phases = []
        self.phase_list.delete(0, "end")
        self.rows.delete(*self.rows.get_children())
        self.canvas.delete("all")
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
                    self.status.set(f"LIVE READ-ONLY · {self.live_location} · achieved {self.live_rate:.2f} samples/s · source checked · training_approved=false")
                elif event.kind == "error":
                    self.status.set("LIVE FAILED: " + event.reason + " Existing sample trace frozen. Check RSPE01 Rev1 and bridge.")
                    self.live_last = None
                elif event.kind == "disconnected":
                    self.status.set("LIVE DISCONNECTED. Existing sample trace retained; no background retries.")
                    self.live_last = None
            if self.live_last is not None:
                age = time.monotonic() - self.live_last
                if age > 3.0:
                    self.status.set(f"STALE LIVE SAMPLE {age:.1f}s ago · {self.live_location} · check source/bridge · training_approved=false")
        self.root.after(200, self.poll_live)

    def close(self) -> None:
        self.disconnect_live(silent=True)
        self.live_worker = None
        self.root.destroy()

    def set_baseline(self) -> None:
        if self.replay is None:
            return
        bits = self.replay.samples[self.index.get()].words.get(AIM)
        if bits is not None and len(bits) == 1:
            self.baseline = float_hypothesis(bits[0])
            self.show(self.index.get())

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

    def drag_start(self, event: tk.Event) -> None:
        self.drag_origin = (event.x, event.y)

    def drag_move(self, event: tk.Event) -> None:
        if self.drag_origin is None:
            return
        x, y = self.drag_origin
        self.yaw += (event.x - x) * 0.01
        self.pitch = min(1.4, max(-1.4, self.pitch + (event.y - y) * 0.01))
        self.drag_origin = (event.x, event.y)
        self.draw_path()

    def draw_path(self) -> None:
        canvas = self.canvas
        canvas.delete("all")
        if self.replay is None:
            return
        width, height = max(canvas.winfo_width(), 1), max(canvas.winfo_height(), 1)
        upto = self.index.get()
        samples = self.replay.samples[:upto + 1]
        path = [(s.vec(BALL), s) for s in samples]
        path = [(p, s) for p, s in path if p is not None]
        caches = [(s.vec(CACHE), s) for s in samples]
        caches = [(p, s) for p, s in caches if p is not None]
        points = [p for p, _ in path + caches]
        if not points:
            canvas.create_text(width // 2, height // 2, text="No finite 3-component ball/cache candidates", fill="white")
            return
        axes = [project(p, self.yaw, self.pitch) for p in points]
        low_x, high_x = min(p[0] for p in axes), max(p[0] for p in axes)
        low_y, high_y = min(p[1] for p in axes), max(p[1] for p in axes)
        scale = min((width - 100) / max(1e-7, high_x - low_x), (height - 90) / max(1e-7, high_y - low_y))
        cx, cy = (low_x + high_x) / 2, (low_y + high_y) / 2
        def xy(p):
            u, v = project(p, self.yaw, self.pitch)
            return width / 2 + (u - cx) * scale, height / 2 - (v - cy) * scale
        canvas.create_text(12, 12, text="Rotatable 3D source-coordinate projection · unknown units", anchor="nw", fill="#bacbe1")
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
        current = self.replay.samples[upto]
        for name, color in ((BALL, "#f1f6ff"), (CACHE, "#f5b942")):
            position = current.vec(name)
            if position is not None:
                x, y = xy(position)
                canvas.create_text(x + 8, y - 12, anchor="w", text=("ball +0x30" if name == BALL else "cache +0xCC"), fill=color)
        canvas.create_text(12, height - 15, text="Drag to rotate. Component0 / 1 / 2 are not verified X/Y/Z or screen pixels.", anchor="sw", fill="#bacbe1")


def launch(capture: str = "", manifest: str = "") -> int:
    root = tk.Tk()
    Inspector(root, capture, manifest)
    root.mainloop()
    return 0
