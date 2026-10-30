"""Source-coordinate Tkinter replay and opt-in read-only live candidate inspector."""
from __future__ import annotations

import math
import time
from collections import deque
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .replay import AIM, BALL, CACHE, Replay, Sample, float_hypothesis, load_replay
from .live import LiveSampler
from .a_button import AButtonStudy, LABELS

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
        self.landmark_status = tk.StringVar(value="Pin / flag: not sampled   ·   Tee: not sampled")
        self.aim_status = tk.StringVar(value="Aim ray: set a tee→flag baseline first; no player position.")
        self.aim_baseline_source: str | None = None
        self.aim_baseline_mode = "assumed first packet"
        self.a_study = AButtonStudy()
        self.a_status = tk.StringVar(value="A BUTTON: UNKNOWN — connect LIVE, then calibrate")
        self.a_instructions = tk.StringVar(value="A study: R0 released → H0 held → R1 → H1 → R2 → H2 → R3 (3 samples each). No swing.")
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
        a_panel = ttk.Frame(head)
        a_panel.pack(fill="x", pady=3)
        ttk.Label(a_panel, textvariable=self.a_status, font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Button(a_panel, text="Capture next A window", command=self.capture_a_window).pack(side="left", padx=12)
        ttk.Button(a_panel, text="Reset A detector", command=self.reset_a_detector).pack(side="left")
        ttk.Label(head, textvariable=self.a_instructions, wraplength=1200).pack(anchor="w")

        main = ttk.PanedWindow(self.root, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10)
        left = ttk.LabelFrame(main, text="Phase / sample", padding=8)
        center = ttk.LabelFrame(main, text="3D candidate view — left/right drag to rotate", padding=8)
        right = ttk.LabelFrame(main, text="Raw source candidates", padding=8)
        main.add(left, weight=1)
        main.add(center, weight=3)
        main.add(right, weight=2)
        self.phase_list = tk.Listbox(left, exportselection=False, width=19)
        self.phase_list.pack(fill="both", expand=True)
        self.phase_list.bind("<<ListboxSelect>>", self.select_phase)
        ttk.Label(left, textvariable=self.phase, wraplength=190).pack(fill="x", pady=6)
        ttk.Button(left, text="Set aim baseline (point at flag)", command=self.set_baseline).pack(fill="x")
        ttk.Label(left, textvariable=self.aim, wraplength=200).pack(fill="x", pady=7)

        self.canvas = tk.Canvas(center, background="#111c29", height=450, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self.draw_path())
        self.canvas.bind("<ButtonPress-1>", self.drag_start)
        self.canvas.bind("<B1-Motion>", self.drag_move)
        self.canvas.bind("<ButtonRelease-1>", self.drag_end)
        self.canvas.bind("<ButtonPress-3>", self.drag_start)
        self.canvas.bind("<B3-Motion>", self.drag_move)
        self.canvas.bind("<ButtonRelease-3>", self.drag_end)
        ttk.Label(center, text="White: ball +0x30  |  Amber: cache +0xCC  |  Cyan flag: PIN candidate  |  Green diamond: TEE candidate", wraplength=640).pack(anchor="w")
        ttk.Label(center, textvariable=self.landmark_status, wraplength=640).pack(anchor="w")
        ttk.Label(center, text="Magenta dashed: flag-aligned aim reference, rotated only by Δ+0x3C (unverified mapping; no player position)", wraplength=640).pack(anchor="w")
        ttk.Label(center, textvariable=self.aim_status, wraplength=640).pack(anchor="w")
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
            self.landmark_status.set("Pin / flag: capture unavailable   ·   Tee: capture unavailable")
            self.aim_status.set("Aim ray: unavailable (capture integrity failed).")
            messagebox.showerror("Integrity / capture error", str(exc))
            return
        self.replay = replay
        self.baseline = None
        self.aim_baseline_source = None
        self.a_study = AButtonStudy()
        self.a_status.set("A BUTTON: UNKNOWN — offline capture has no validated live A state")
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

    def connect_live(self) -> None:
        if self.live_worker is not None and self.live_worker.thread is not None and self.live_worker.thread.is_alive():
            return
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
        self.a_study = AButtonStudy()
        self.a_status.set("A BUTTON: UNKNOWN — calibration required")
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
                    self.status.set(f"LIVE READ-ONLY · {self.live_location} · achieved {self.live_rate:.2f} samples/s · source checked · training_approved=false")
                elif event.kind == "error":
                    self.status.set("LIVE FAILED: " + event.reason + " Existing sample trace frozen. Check RSPE01 Rev1 and bridge.")
                    self.live_last = None
                    self.a_status.set("A BUTTON: UNKNOWN — bridge/source error")
                    self.a_study.invalidate("bridge/source error")
                elif event.kind == "disconnected":
                    self.status.set("LIVE DISCONNECTED. Existing sample trace retained; no background retries.")
                    self.live_last = None
                    self.a_status.set("A BUTTON: UNKNOWN — disconnected")
                    self.a_study.invalidate("disconnected")
            if self.live_last is not None:
                age = time.monotonic() - self.live_last
                if age > 3.0:
                    self.a_status.set("A BUTTON: UNKNOWN — stale live sample")
                    self.a_study.history.clear()
                    self.status.set(f"STALE LIVE SAMPLE {age:.1f}s ago · {self.live_location} · check source/bridge · training_approved=false")
        self.root.after(200, self.poll_live)

    def close(self) -> None:
        self.disconnect_live(silent=True)
        self.live_worker = None
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

    def reset_a_detector(self) -> None:
        self.a_study = AButtonStudy()
        self.a_status.set("A BUTTON: UNKNOWN — not calibrated")
        self.a_instructions.set("A study reset: R0 released → H0 held → R1 → H1 → R2 → H2 → R3; 3 reads each. Hold input BEFORE clicking Capture.")

    def capture_a_window(self) -> None:
        if (self.live_worker is None or self.live_worker.thread is None
                or not self.live_worker.thread.is_alive() or self.live_last is None):
            self.a_instructions.set("Connect to a responsive live bridge first; no automatic A inputs.")
            return
        if time.monotonic() - self.live_last > 3.0:
            self.a_status.set("A BUTTON: UNKNOWN — stale source")
            return
        phase = self.a_study.next_phase
        if phase is None:
            self.a_instructions.set("Calibration already completed; Reset to repeat.")
            return
        try:
            # Give the human time to return focus to Dolphin and set the
            # requested A state BEFORE any calibration sample is accepted.
            self.a_study.arm(time.monotonic_ns() + 3_000_000_000)
        except ValueError:
            self.a_instructions.set("A window still collecting or calibration failed. Reset to retry.")
            return
        self.a_status.set("A BUTTON: UNKNOWN — sampling " + phase)
        self.a_instructions.set("FOCUS DOLPHIN NOW: set A " + LABELS[phase] +
                                " within 3 seconds. Then HOLD that state until 3 valid samples are captured. No swing.")

    def process_a_sample(self, event: object) -> None:
        sample = event.sample
        if sample is None:
            return
        ball, aim = sample.words.get(BALL), sample.words.get(AIM)
        record = event.a_record
        if self.a_study.phase_active:
            progress = self.a_study.observe(record, sample.source_digest, ball, aim,
                                            event.a_read_start_ns or 0)
            self.a_instructions.set("A study: " + progress)
            if self.a_study.verified:
                self.a_instructions.set("A study passed repeated fit + withheld R2/H2/R3; candidate only, not native A latch.")
        if self.a_study.verified:
            state = self.a_study.predict(record, sample.source_digest, ball, aim)
            self.a_status.set("A BUTTON: " + state + " (CALIBRATED CANDIDATE; non-atomic, ~2 reads to settle)")
        elif self.a_study.failure:
            self.a_status.set("A BUTTON: UNKNOWN — " + self.a_study.failure)
        elif not self.a_study.phase_active:
            self.a_status.set("A BUTTON: UNKNOWN — calibrate " + (self.a_study.next_phase or "A state"))


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
        # Include pin, tee and the illustrative aim line in the plot bounds.
        points = [p for p, _ in path + caches] + list(landmarks.values()) + (list(aim_ray) if aim_ray else [])
        if not points:
            canvas.create_text(width // 2, height // 2, text="No finite source-qualified ball/cache/pin/tee candidates", fill="white")
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
            canvas.create_text(tip[0] + 7, tip[1] - 10, text="AIM? (flag ref + Δ0x3C)",
                               anchor="sw", fill="#e39bff", tags=("aim_hypothesis",))
        for name, color in ((BALL, "#f1f6ff"), (CACHE, "#f5b942")):
            position = current.vec(name)
            if position is not None:
                x, y = xy(position)
                canvas.create_text(x + 8, y - 12, anchor="w", text=("ball +0x30" if name == BALL else "cache +0xCC"), fill=color)
        # Draw the flag LAST, over ball/cache trails: the pin should remain
        # unmistakable even when a cache value exactly equals the pin candidate.
        if TEE in landmarks:
            x, y = xy(landmarks[TEE])
            canvas.create_polygon(x, y - 8, x + 8, y, x, y + 8, x - 8, y,
                                  fill="#59d47d", outline="#173a23", width=1,
                                  tags=("tee_candidate",))
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
            canvas.create_text(x + 23, y - 14, anchor="nw", text="PIN / FLAG (candidate)",
                               fill="#44d7ef", tags=("pin_candidate",))
        canvas.create_text(12, height - 15, text="Left/right drag: orbit view. Initial aim assumed TEE→FLAG; Δ+0x3C radian/sign unverified; TEE ≠ player.", anchor="sw", fill="#bacbe1")


def launch(capture: str = "", manifest: str = "") -> int:
    root = tk.Tk()
    Inspector(root, capture, manifest)
    root.mainloop()
    return 0
