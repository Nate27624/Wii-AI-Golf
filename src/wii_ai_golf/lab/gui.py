"""Windows Tkinter UI over the exact same reviewed golf lab runner.

Live trials start ONLY on explicit click+confirmation. Interactive prompt
runs in a new console; results/bridge state are never inferred from exit code.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
from .core import ROOT, get_experiment, history, load_catalog, plan


def launch(root: Path = ROOT) -> int:
    if os.name != "nt":
        raise RuntimeError("Desktop lab requires Windows. CLI 'golf lab list|plan|run|history' works elsewhere.")
    import tkinter as tk
    from tkinter import messagebox, ttk

    catalog = load_catalog(root / "research" / "experiments.json")
    ui = tk.Tk()
    ui.title("Wii AI Golf — Research Lab")
    ui.geometry("1020x760")
    ui.minsize(820, 620)
    outer = ttk.Frame(ui, padding=18)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="Wii AI Golf · Research Lab",
              font=("Segoe UI", 19, "bold")).pack(anchor="w")
    ttk.Label(outer, text="S000–S005  •  Reviewed experiments  •  Local run history  •  One canonical Dolphin startup").pack(anchor="w")
    panes = ttk.PanedWindow(outer, orient="horizontal")
    panes.pack(fill="both", expand=True, pady=12)
    left, right = ttk.Frame(panes), ttk.Frame(panes)
    panes.add(left, weight=2)
    panes.add(right, weight=3)
    listing = ttk.Treeview(left, columns=("owner", "mode"), show="tree headings", height=15)
    listing.heading("#0", text="Experiment")
    listing.heading("owner", text="Agent")
    listing.heading("mode", text="Mode")
    listing.column("#0", width=220)
    listing.column("owner", width=58, anchor="center")
    listing.column("mode", width=65, anchor="center")
    listing.pack(fill="both", expand=True, padx=(0, 12))
    for e in catalog:
        listing.insert("", "end", iid=e["id"], text=e["title"],
                       values=(e["owner"], e["mode"]))
    description = tk.StringVar(value="Select an experiment.")
    ttk.Label(right, textvariable=description, wraplength=455, justify="left").pack(fill="x", pady=7)
    inputs = ttk.LabelFrame(right, text="Optional parameters", padding=8)
    inputs.pack(fill="x")
    values = {}
    for key, label, default in (
        ("input", "Input path", ""), ("second-input", "Second input", ""),
        ("out", "Output path", ""), ("a-prime", "A prime requests", "0"),
        ("follow-through", "Follow-through", "30"), ("contact", "Contact yes/no/unknown", ""),
        ("green", "Green yes/no/unknown", ""), ("distance", "Displayed distance", ""),
    ):
        line = ttk.Frame(inputs)
        line.pack(fill="x", pady=2)
        ttk.Label(line, text=label, width=24).pack(side="left")
        v = tk.StringVar(value=default)
        ttk.Entry(line, textvariable=v).pack(side="left", fill="x", expand=True)
        values[key] = v
    output = tk.Text(right, wrap="word", height=11, font=("Consolas", 9))
    output.pack(fill="both", expand=True, pady=9)
    output.configure(state="disabled")
    status = tk.StringVar(value="Idle — no game launched")
    ttk.Label(right, textvariable=status, wraplength=455).pack(anchor="w", pady=4)

    def selection():
        sel = listing.selection()
        return sel[0] if sel else None

    def args_and_kwargs():
        flags, opts = [], {}
        for key in ("input", "second-input", "out", "contact", "green", "distance"):
            x = values[key].get().strip()
            if x:
                flags += ["--" + key, x]
                optkey = {"input": "input_path", "out": "output_path",
                          "second-input": "second_input"}.get(key, key)
                opts[optkey] = x
        for key, arg in (("a-prime", "a_prime"), ("follow-through", "follow_through")):
            x = int(values[key].get())
            flags += ["--" + key, str(x)]
            opts[arg] = x
        return flags, opts

    def selected_plan():
        chosen = selection()
        if not chosen:
            raise ValueError("Select an experiment first")
        _, opts = args_and_kwargs()
        return plan(chosen, root=root, **opts)

    def preview():
        try:
            p = selected_plan()
            contents = json.dumps(p.summary(), indent=2)
            status.set(f"Preview only: {p.experiment['id']} ({p.experiment['mode']})")
        except (OSError, ValueError) as exc:
            contents = str(exc)
            status.set("Not runnable: " + str(exc))
        output.configure(state="normal")
        output.delete("1.0", "end")
        output.insert("1.0", contents)
        output.configure(state="disabled")

    def selected(_event=None):
        chosen = selection()
        if not chosen:
            return
        e = get_experiment(chosen, catalog=catalog)
        description.set(f"{e['id']} | {e['owner']} | {e['mode'].upper()}\n{e['description']}")
        offline_btn.configure(state="normal" if e["mode"] == "offline" else "disabled")
        live_btn.configure(state="normal" if e["mode"] == "live" else "disabled")
        preview()

    active: list[subprocess.Popen] = []

    def run_selected(live: bool):
        try:
            p = selected_plan()
            if p.live != live:
                raise ValueError("Experiment mode does not match this button")
            if live and not messagebox.askyesno(
                "Confirm ONE live swing", "Close Dolphin completely before continuing.\n"
                "Start ONE canonical full-boot Wii Sports trial? The terminal "
                "will ask you to confirm tee readiness and label ball contact."):
                return
            flags, _ = args_and_kwargs()
            cmd = [sys.executable, str(root / "scripts" / "golf.py"),
                   "lab", "run", p.experiment["id"], *flags]
            if live:
                cmd.append("--live")
            process = subprocess.Popen(
                cmd, cwd=root, creationflags=subprocess.CREATE_NEW_CONSOLE)
            active.append(process)
            status.set(f"Process {process.pid} started in an interactive terminal.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Experiment not started", str(exc))

    def show_last_offline_log():
        items = history(root.parent / "Wii-AI-Golf-Data" / "lab", limit=30)
        folder = (root.parent / "Wii-AI-Golf-Data" / "lab" / "runs").resolve()
        for item in items:
            filename = item.get("offline_log")
            if not isinstance(filename, str):
                continue
            path = Path(filename).resolve()
            # A local metadata file must never trick the UI into opening an
            # unrelated filesystem path.
            if path.parent != folder or path.suffix != ".log" or not path.is_file():
                continue
            log = tk.Toplevel(ui)
            log.title("Last offline execution output — " + str(item.get("experiment_id")))
            log.geometry("820x500")
            view = tk.Text(log, wrap="none", font=("Consolas", 9))
            view.pack(fill="both", expand=True, padx=10, pady=10)
            view.insert("1.0", path.read_text(encoding="utf-8", errors="replace")[:250000])
            view.configure(state="disabled")
            return
        messagebox.showinfo("No offline run log yet",
                            "Run an offline experiment and then refresh. "
                            "Live inputs are displayed in their interactive console.")

    def show_sanitized_reports():
        from .reports import sanitized_reports
        reports = sanitized_reports(root=root)
        window = tk.Toplevel(ui)
        window.title("Sanitized S002 outcomes — HUMAN OBSERVATIONS ONLY")
        window.geometry("820x450")
        box = tk.Text(window, wrap="word", font=("Consolas", 10))
        box.pack(fill="both", expand=True, padx=14, pady=14)
        box.insert("end", "These are SANITIZED reports, not validated game scores.\\n"
                          "RAW-PRIVATE memory files are excluded.\\n\\n")
        if not reports:
            box.insert("end", "No sanitized capture summaries yet.\\n")
        for record in reports:
            box.insert("end", json.dumps(record, indent=2) + "\\n\\n")
        box.configure(state="disabled")

    history_frame = ttk.LabelFrame(outer, text="Recent execution history (NOT game scores)", padding=7)
    history_frame.pack(fill="x")
    recent = ttk.Treeview(history_frame, columns=("agent", "mode", "execution", "exit"),
                          show="tree headings", height=5)
    recent.heading("#0", text="Experiment ID")
    for k, label in (("agent", "Agent"), ("mode", "Mode"),
                     ("execution", "Process"), ("exit", "Exit")):
        recent.heading(k, text=label)
        recent.column(k, width=85, anchor="center")
    recent.column("#0", width=320)
    recent.pack(fill="x")

    def refresh():
        for row in recent.get_children():
            recent.delete(row)
        for h in history(root.parent / "Wii-AI-Golf-Data" / "lab", limit=7):
            recent.insert("", "end", text=h.get("experiment_id", ""),
                          values=(h.get("owner", ""), h.get("mode", ""),
                                  h.get("execution_status", ""),
                                  h.get("exit_code", "")))

    def poll():
        finished = [p for p in active if p.poll() is not None]
        for p in finished:
            active.remove(p)
            status.set(f"Process {p.pid} exited ({p.returncode}); inspect game labels separately.")
        if finished:
            refresh()
        ui.after(1400, poll)

    def run_safe_batch():
        if any(p.poll() is None for p in active):
            messagebox.showwarning("Experiment active", "Finish the current Lab run first.")
            return
        if not messagebox.askyesno("Run approved offline batch",
            "Run all registered zero-input, allowlisted OFFLINE tests and demos? No Dolphin actions."):
            return
        try:
            proc=subprocess.Popen([sys.executable,str(root/"scripts"/"run_lab_offline_batch.py")],
                                  cwd=root,creationflags=subprocess.CREATE_NEW_CONSOLE)
            active.append(proc)
            status.set(f"Offline batch started in console {proc.pid}; see run history.")
        except OSError as exc:
            messagebox.showerror("Batch failed to launch",str(exc))

    def sync_reviewed():
        from .sync import sync_reviewed_main
        if active:
            messagebox.showwarning("Active experiment", "Close active Lab experiments before syncing.")
            return
        if not messagebox.askyesno("Sync reviewed experiments",
            "Fetch and fast-forward origin/main only? Unreviewed PR code will NOT be installed."):
            return
        try:
            result=sync_reviewed_main(root)
            messagebox.showinfo("Repository sync", ("Updated. " if result["updated"] else "Already current. ") +
                                "Restart Golf Lab to load the reviewed experiment catalog.")
        except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
            messagebox.showerror("Sync refused", str(exc))

    actions = ttk.Frame(right)
    actions.pack(fill="x")
    ttk.Button(actions, text="Sync reviewed", command=sync_reviewed).pack(side="left", padx=3)
    ttk.Button(actions, text="Run safe batch", command=run_safe_batch).pack(side="left", padx=3)
    ttk.Button(actions, text="Preview", command=preview).pack(side="left", padx=3)
    offline_btn = ttk.Button(actions, text="Run offline", state="disabled",
                             command=lambda: run_selected(False))
    offline_btn.pack(side="left", padx=3)
    live_btn = ttk.Button(actions, text="Run ONE live", state="disabled",
                          command=lambda: run_selected(True))
    live_btn.pack(side="left", padx=3)
    ttk.Button(actions, text="Refresh results", command=refresh).pack(side="left", padx=3)
    ttk.Button(actions, text="Sanitized outcomes", command=show_sanitized_reports).pack(side="left", padx=3)
    ttk.Button(actions, text="Offline log", command=show_last_offline_log).pack(side="left", padx=3)
    listing.bind("<<TreeviewSelect>>", selected)
    refresh()
    if catalog:
        listing.selection_set(catalog[0]["id"])
        selected()
    ui.after(1400, poll)
    ui.mainloop()
    return 0
