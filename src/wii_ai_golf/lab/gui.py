"""Windows Tkinter UI over the exact same reviewed golf lab runner.

Live trials start ONLY on explicit click+confirmation. Interactive prompt
runs in a new console; results/bridge state are never inferred from exit code.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from .core import ROOT, get_experiment, history, available_experiments, plan
from .github_sync import sync_merged_main


def launch(root: Path = ROOT) -> int:
    if os.name != "nt":
        raise RuntimeError("Desktop lab requires Windows. CLI 'golf lab list|plan|run|history' works elsewhere.")
    import tkinter as tk
    from tkinter import messagebox, ttk

    catalog = available_experiments(root)
    sync_messages: queue.SimpleQueue = queue.SimpleQueue()
    sync_busy = [False]
    last_changes: set[str] = set()
    ui = tk.Tk()
    ui.title("Wii AI Golf — Research Lab")
    ui.geometry("1020x760")
    ui.minsize(820, 620)
    outer = ttk.Frame(ui, padding=18)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="Wii AI Golf · Research Lab",
              font=("Segoe UI", 19, "bold")).pack(anchor="w")
    ttk.Label(outer, text="S000–S005  •  Agent tests pulled from approved GitHub main  •  One canonical Dolphin startup").pack(anchor="w")
    sync_line = tk.StringVar(value="GitHub: checking for newly merged tests...")
    ttk.Label(outer, textvariable=sync_line, wraplength=930).pack(anchor="w", pady=(4, 0))
    panes = ttk.PanedWindow(outer, orient="horizontal")
    panes.pack(fill="both", expand=True, pady=12)
    left, right = ttk.Frame(panes), ttk.Frame(panes)
    panes.add(left, weight=2)
    panes.add(right, weight=3)
    filter_mode = tk.StringVar(value="All")
    ttk.Label(left, text="Show").pack(anchor="w", pady=(0, 3))
    filter_select = ttk.Combobox(left, textvariable=filter_mode,
                                 values=("All", "Agent tests", "Experiments"),
                                 state="readonly", width=22)
    filter_select.pack(fill="x", padx=(0, 12), pady=(0, 7))
    listing = ttk.Treeview(left, columns=("owner", "mode"), show="tree headings", height=15)
    listing.heading("#0", text="Experiment")
    listing.heading("owner", text="Agent")
    listing.heading("mode", text="Mode")
    listing.column("#0", width=220)
    listing.column("owner", width=58, anchor="center")
    listing.column("mode", width=65, anchor="center")
    listing.pack(fill="both", expand=True, padx=(0, 12))
    def refill_catalog():
        nonlocal catalog
        wanted = listing.selection()[0] if listing.selection() else None
        catalog = available_experiments(root)
        for row in listing.get_children():
            listing.delete(row)
        for e in catalog:
            agent_test = e["id"].startswith("agent-tests.")
            if filter_mode.get() == "Agent tests" and not agent_test:
                continue
            if filter_mode.get() == "Experiments" and agent_test:
                continue
            marker = "NEW  " if agent_test and (
                "tests/" + e["title"]) in last_changes else ""
            label = marker + e["title"]
            listing.insert("", "end", iid=e["id"], text=label,
                           values=(e["owner"], e["mode"]))
        if wanted and listing.exists(wanted):
            listing.selection_set(wanted)
            listing.focus(wanted)
        elif listing.get_children():
            first = listing.get_children()[0]
            listing.selection_set(first)
            listing.focus(first)
    refill_catalog()
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

    def request_sync() -> None:
        """Never block Tkinter while fetching GitHub; never run fetched tests."""
        if sync_busy[0]:
            return
        lab_root = root.parent / "Wii-AI-Golf-Data" / "lab"
        if active or any((lab_root / name).exists()
                         for name in ("live-session.lock", "run-session.lock")):
            sync_line.set("GitHub: synchronization deferred while an experiment runs.")
            return
        sync_busy[0] = True
        sync_line.set("GitHub: checking approved origin/main (offline tests NOT auto-run)...")

        def worker():
            try:
                result = sync_merged_main(
                    root, lab_data=root.parent / "Wii-AI-Golf-Data" / "lab")
                sync_messages.put(result)
            except Exception as exc:
                sync_messages.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=True, name="golf-lab-git-sync").start()

    def sync_messages_poll():
        try:
            while True:
                item = sync_messages.get_nowait()
                sync_busy[0] = False
                if isinstance(item, tuple):
                    sync_line.set("GitHub update error: " + str(item[1])[:200])
                    continue
                if item.status == "updated":
                    last_changes.clear()
                    last_changes.update(item.changed_tests)
                    try:
                        refill_catalog()
                        selected()
                    except (OSError, ValueError) as exc:
                        sync_line.set("Updated checkout; restart Lab to read new code: " + str(exc))
                        continue
                    sync_line.set(
                        f"GitHub: updated main; {len(item.changed_tests)} merged test files "
                        "added/modified. Select NEW tests to run. Restart app if Lab code changed."
                    )
                else:
                    sync_line.set("GitHub: " + item.status + " — " + item.note)
        except queue.Empty:
            pass
        ui.after(800, sync_messages_poll)

    def auto_sync_tick():
        request_sync()
        ui.after(120000, auto_sync_tick)

    def run_selected(live: bool):
        try:
            if sync_busy[0]:
                raise ValueError("GitHub update is in progress; start this test after it finishes.")
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

    actions = ttk.Frame(right)
    actions.pack(fill="x")
    ttk.Button(actions, text="Preview", command=preview).pack(side="left", padx=3)
    offline_btn = ttk.Button(actions, text="Run offline", state="disabled",
                             command=lambda: run_selected(False))
    offline_btn.pack(side="left", padx=3)
    live_btn = ttk.Button(actions, text="Run ONE live", state="disabled",
                          command=lambda: run_selected(True))
    live_btn.pack(side="left", padx=3)
    ttk.Button(actions, text="Refresh results", command=refresh).pack(side="left", padx=3)
    ttk.Button(actions, text="Sync GitHub", command=request_sync).pack(side="left", padx=3)
    ttk.Button(actions, text="Sanitized outcomes", command=show_sanitized_reports).pack(side="left", padx=3)
    ttk.Button(actions, text="Offline log", command=show_last_offline_log).pack(side="left", padx=3)
    listing.bind("<<TreeviewSelect>>", selected)
    filter_select.bind("<<ComboboxSelected>>",
                       lambda _event: (refill_catalog(), selected()))
    refresh()
    if catalog:
        listing.selection_set(catalog[0]["id"])
        selected()
    sync_messages_poll()
    auto_sync_tick()
    ui.after(1400, poll)
    ui.mainloop()
    return 0
