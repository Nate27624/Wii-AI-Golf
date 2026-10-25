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
from .core import ROOT, get_experiment, history, available_experiments, plan, execute
from .github_sync import sync_merged_main
from .bridge_ui import inspect_game_bridges


def launch(root: Path = ROOT) -> int:
    if os.name != "nt":
        raise RuntimeError("Desktop lab requires Windows. CLI 'golf lab list|plan|run|history' works elsewhere.")
    import tkinter as tk
    from tkinter import messagebox, ttk

    catalog = available_experiments(root)
    sync_messages: queue.SimpleQueue = queue.SimpleQueue()
    sync_busy = [False]
    sync_manual_requested = [False]
    last_changes: set[str] = set()
    ui = tk.Tk()
    ui.title("Wii AI Golf — Research Lab")
    ui.geometry("1100x830")
    ui.minsize(850, 660)
    outer = ttk.Frame(ui, padding=18)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="Wii AI Golf · Research Lab",
              font=("Segoe UI", 19, "bold")).pack(anchor="w")
    ttk.Label(outer, text="S000–S005  •  Agent tests pulled from approved GitHub main  •  One canonical Dolphin startup").pack(anchor="w")
    sync_line = tk.StringVar(value="GitHub: checking for newly merged tests...")
    ttk.Label(outer, textvariable=sync_line, wraplength=930).pack(anchor="w", pady=(4, 0))
    # This task-specific panel is deliberately OUTSIDE the experiment
    # filter/list: a user should never need PowerShell or know registry IDs
    # to prepare a historical game test.
    game_panel = ttk.LabelFrame(
        outer, text="Game Testing — historical V1 versus installed V2", padding=10)
    game_panel.pack(fill="x", pady=(8, 0))
    ttk.Label(game_panel, text=(
        "1 Inspect bridge → 2 Prepare separate V1 copy → 3 Run ONE shot. "
        "The first two steps NEVER start Dolphin."), wraplength=900).pack(anchor="w")
    game_buttons = ttk.Frame(game_panel)
    game_buttons.pack(fill="x", pady=(7, 4))
    bridge_status = tk.StringVar(value="Checking local bridge files...")
    ttk.Label(game_panel, textvariable=bridge_status, wraplength=900).pack(anchor="w", pady=(3, 4))
    game_details = tk.Text(game_panel, height=8, wrap="word",
                           font=("Consolas", 9), relief="flat",
                           padx=10, pady=8, cursor="arrow")
    game_details.pack(fill="x", pady=(2, 0))
    game_details.configure(state="disabled")

    panes = ttk.PanedWindow(outer, orient="horizontal")
    panes.pack(fill="both", expand=True, pady=12)
    left, right = ttk.Frame(panes), ttk.Frame(panes)
    panes.add(left, weight=2)
    panes.add(right, weight=3)
    filter_mode = tk.StringVar(value="All")
    ttk.Label(left, text="Show").pack(anchor="w", pady=(0, 3))
    filter_select = ttk.Combobox(left, textvariable=filter_mode,
                                 values=("All", "Game tests", "Agent tests", "Experiments"),
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
            if filter_mode.get() == "Game tests" and not (
                e["id"].startswith("integration.") or e["id"] == "evaluation.capture"):
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
        ("a-lead", "Observed A lead frames (V1: 0–90)", "0"),
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
        for key, arg in (("a-prime", "a_prime"), ("a-lead", "a_lead"), ("follow-through", "follow_through")):
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
    active_studies: dict[int, str] = {}
    restart_needed = [False]
    game_job_busy = [False]
    game_job_messages: queue.SimpleQueue = queue.SimpleQueue()
    lab_data = root.parent / "Wii-AI-Golf-Data" / "lab"

    def show_game_details(message: str):
        """Single persistent results area, no temporary console or missing-log popup."""
        game_details.configure(state="normal")
        game_details.delete("1.0", "end")
        game_details.insert("1.0", message)
        game_details.configure(state="disabled")

    def refresh_bridge_status():
        try:
            view = inspect_game_bridges(root)
            bridge_status.set(view.title)
            prep_button.configure(
                state="normal" if view.can_prepare and not game_job_busy[0] else "disabled")
            v1_button.configure(
                state="normal" if view.can_test and not game_job_busy[0] else "disabled")
            show_game_details(view.as_text())
            return view
        except (OSError, ValueError, UnicodeError) as exc:
            bridge_status.set("Bridge inspection failed")
            prep_button.configure(state="disabled")
            v1_button.configure(state="disabled")
            show_game_details("Unable to inspect bridge files.\\n\\n" + str(exc))
            return None

    def inspect_bridges():
        """Read-only local source inspection, rendered instantly INSIDE Lab."""
        if game_job_busy[0]:
            bridge_status.set("Bridge preparation is still running.")
            return
        refresh_bridge_status()


    def navigate_study(identifier: str):
        # Game Testing shortcuts always show the intended experiment,
        # regardless of a previous Agent tests filter or a stale selection.
        filter_mode.set("Game tests")
        refill_catalog()
        if not listing.exists(identifier):
            raise ValueError(f"Experiment {identifier} not loaded. Restart the Lab after Sync GitHub.")
        listing.selection_set(identifier)
        listing.focus(identifier)
        listing.see(identifier)
        selected()

    def prepare_historical_v1():
        """Run the reviewed Lab preparation and record it, without another console."""
        if game_job_busy[0] or sync_busy[0] or active:
            bridge_status.set("Finish the current Lab task or GitHub update first.")
            return
        view = refresh_bridge_status()
        if view is None or not view.can_prepare:
            return
        if not messagebox.askyesno(
            "Create isolated historical V1 bridge?",
            "Create a separate test copy from the VERIFIED pre-V2 backup?\\n\\n"
            "The active V2 bridge and all Dolphin save states remain untouched. "
            "If any file differs unexpectedly, preparation will stop."):
            return
        game_job_busy[0] = True
        prep_button.configure(state="disabled")
        v1_button.configure(state="disabled")
        bridge_status.set("Preparing historical V1 copy...")
        show_game_details(
            "Working in the background using the reviewed Lab runner.\\n"
            "No Dolphin session is being launched, and your current bridge is untouched.")

        def worker():
            try:
                trial = plan("integration.prepare-v1", root=root, python=sys.executable)
                record = execute(trial, root=root, data=lab_data)
                game_job_messages.put(("finished", record))
            except (OSError, ValueError, RuntimeError) as exc:
                game_job_messages.put(("error", str(exc)))
        threading.Thread(target=worker, daemon=True,
                         name="golf-lab-prepare-v1").start()

    def check_game_job():
        try:
            while True:
                kind, payload = game_job_messages.get_nowait()
                game_job_busy[0] = False
                view = refresh_bridge_status()
                if kind == "error":
                    bridge_status.set("Preparation could not start")
                    show_game_details("The Lab did not prepare a bridge.\\n\\n" + str(payload))
                elif payload.get("exit_code") != 0:
                    bridge_status.set("Preparation failed — no game started")
                    log_path = payload.get("offline_log")
                    details = ""
                    if isinstance(log_path, str):
                        path = Path(log_path)
                        if path.is_file() and path.parent.resolve() == (lab_data / "runs").resolve():
                            details = path.read_text(encoding="utf-8", errors="replace")[-3500:]
                    show_game_details(
                        "Bridge preparation did not succeed. Nothing was replaced.\\n\\n" +
                        (details or str(payload.get("launch_error", "No diagnostic output available."))))
                elif view is not None and view.can_test:
                    bridge_status.set("Historical V1 is ready for the single-shot comparison")
                    show_game_details(view.as_text() + "\\n\\nPreparation recorded in Lab history.")
                else:
                    bridge_status.set("Preparation finished; V1 could not be verified")
                    show_game_details(
                        (view.as_text() if view else "Bridge check unavailable") +
                        "\\n\\nThe output did not pass the readiness check. "
                        "Do not start the live shot.")
                refresh()
        except queue.Empty:
            pass
        ui.after(350, check_game_job)

    def launch_v1_trial():
        try:
            view = inspect_game_bridges(root)
            if not view.can_test:
                refresh_bridge_status()
                return
            # The top-row quick action is a controlled baseline, not an
            # accidental reuse of inputs from another selected study.
            values["a-prime"].set("0")
            values["a-lead"].set("0")
            navigate_study("integration.v1-diagnostic")
            run_selected(True)
        except (OSError, ValueError) as exc:
            bridge_status.set("Could not start V1 comparison")
            show_game_details(str(exc))

    ttk.Button(game_buttons, text="1  Inspect bridges",
               command=inspect_bridges).pack(side="left", padx=(0, 8))
    prep_button = ttk.Button(
        game_buttons, text="2  Prepare historical V1", state="disabled",
        command=prepare_historical_v1)
    prep_button.pack(side="left", padx=(0, 8))
    v1_button = ttk.Button(
        game_buttons, text="3  Run ONE V1 shot", state="disabled",
        command=launch_v1_trial)
    v1_button.pack(side="left", padx=(0, 8))
    ttk.Button(game_buttons, text="Refresh check",
               command=inspect_bridges).pack(side="left")

    def request_sync(*, manual: bool = False) -> None:
        """Never block Tkinter while fetching GitHub; never run fetched tests."""
        if sync_busy[0]:
            if manual:
                messagebox.showinfo("GitHub sync", "A GitHub sync is already running.")
            return
        sync_manual_requested[0] = manual
        lab_root = root.parent / "Wii-AI-Golf-Data" / "lab"
        if active or any((lab_root / name).exists()
                         for name in ("live-session.lock", "run-session.lock")):
            sync_line.set("GitHub: synchronization deferred while an experiment runs.")
            if manual:
                messagebox.showwarning("GitHub sync blocked", sync_line.get())
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
                manual = sync_manual_requested[0]
                sync_manual_requested[0] = False
                if isinstance(item, tuple):
                    sync_line.set("GitHub update error: " + str(item[1])[:200])
                    if manual:
                        messagebox.showerror("GitHub sync failed", sync_line.get())
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
                    restart_needed[0] = True
                    restart_button.configure(state="normal")
                    sync_line.set(
                        f"GitHub: updated main; {len(item.changed_tests)} merged test files "
                        "added/modified. Click RESTART LAB to load new UI features."
                    )
                else:
                    sync_line.set("GitHub: " + item.status + " — " + item.note)
                if manual:
                    details = sync_line.get()
                    if item.status in ("updated", "up_to_date"):
                        messagebox.showinfo("GitHub sync confirmed", details)
                    else:
                        messagebox.showwarning("GitHub sync blocked", details)
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
            if p.experiment["id"] == "integration.prepare-v1" and not messagebox.askyesno(
                "Prepare isolated historical V1 bridge",
                "Copy the saved V1 bridge into a SEPARATE diagnostic file? "
                "Your active V2 bridge and savestates will not be overwritten. "
                "The step will refuse unsafe/mismatched backup files."):
                return
            if live and not messagebox.askyesno(
                "Confirm ONE live swing", "Close Dolphin completely before continuing.\n"
                "Start ONE canonical full-boot Wii Sports trial? The terminal "
                "will ask you to confirm tee readiness and label ball contact.\n"
                "V1/A-lead experiments are UNVERIFIED; previous 12-frame timing made motion worse."):
                return
            flags, _ = args_and_kwargs()
            cmd = [sys.executable, str(root / "scripts" / "golf.py"),
                   "lab", "run", p.experiment["id"], *flags]
            if live:
                cmd.append("--live")
            # A separate console remains interactive for Dolphin/menu prompts.
            # Keep it open on nonzero exits so failures like argparse code 2
            # do not vanish before the operator can read the actual exception.
            observed_command = [sys.executable,
                                str(root / "scripts" / "lab_interactive_console.py"),
                                "--", *cmd]
            process = subprocess.Popen(
                observed_command, cwd=root,
                creationflags=subprocess.CREATE_NEW_CONSOLE)
            active.append(process)
            active_studies[process.pid] = p.experiment["id"]
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
            study = active_studies.pop(p.pid, "")
            status.set(f"{study or 'Experiment'} process {p.pid} exited ({p.returncode}); "
                       "execution is not a ball hit.")
            if p.returncode != 0:
                messagebox.showwarning("Experiment failed — not a golf result",
                    f"{study or 'Experiment'} exited with code {p.returncode}. "
                    "The interactive terminal should display the exact error. "
                    "Exit 2 often indicates command validation; do not record a swing.")
            if study in ("integration.bridge-audit", "integration.prepare-v1"):
                # Show the real audit/error result in the GUI rather than
                # losing it in a short-lived subprocess console.
                show_last_offline_log()
        if finished:
            refresh()
            refresh_bridge_status()
        ui.after(1400, poll)

    actions = ttk.Frame(right)
    actions.pack(fill="x")
    primary_actions = ttk.Frame(actions)
    primary_actions.pack(fill="x", pady=(0, 4))
    secondary_actions = ttk.Frame(actions)
    secondary_actions.pack(fill="x")
    ttk.Button(primary_actions, text="Preview", command=preview).pack(side="left", padx=3)
    offline_btn = ttk.Button(primary_actions, text="Run offline", state="disabled",
                             command=lambda: run_selected(False))
    offline_btn.pack(side="left", padx=3)
    live_btn = ttk.Button(primary_actions, text="Run ONE live", state="disabled",
                          command=lambda: run_selected(True))
    live_btn.pack(side="left", padx=3)
    ttk.Button(primary_actions, text="Refresh results", command=refresh).pack(side="left", padx=3)
    ttk.Button(secondary_actions, text="Sync GitHub", command=lambda: request_sync(manual=True)).pack(side="left", padx=3)
    def restart_lab():
        if active or sync_busy[0] or any(
                (root.parent / "Wii-AI-Golf-Data" / "lab" / name).exists()
                for name in ("live-session.lock", "run-session.lock")):
            messagebox.showwarning("Restart deferred",
                                   "Finish current GitHub update or Lab experiment first.")
            return
        # Launch a fresh Python process so all newly downloaded UI modules
        # and registry adapters are actually imported from current main.
        try:
            subprocess.Popen(
                [sys.executable, str(root / "scripts" / "golf_lab.py")],
                cwd=root, creationflags=subprocess.CREATE_NEW_CONSOLE)
        except OSError as exc:
            messagebox.showerror("Lab restart failed", str(exc))
            return
        ui.destroy()
    restart_button = ttk.Button(
        secondary_actions, text="Restart Lab (updated)", state="disabled",
        command=restart_lab)
    restart_button.pack(side="left", padx=3)
    ttk.Button(secondary_actions, text="Sanitized outcomes", command=show_sanitized_reports).pack(side="left", padx=3)
    ttk.Button(secondary_actions, text="Offline log", command=show_last_offline_log).pack(side="left", padx=3)
    listing.bind("<<TreeviewSelect>>", selected)
    filter_select.bind("<<ComboboxSelected>>",
                       lambda _event: (refill_catalog(), selected()))
    refresh()
    refresh_bridge_status()
    if catalog:
        listing.selection_set(catalog[0]["id"])
        selected()
    sync_messages_poll()
    auto_sync_tick()
    ui.after(1400, poll)
    ui.mainloop()
    return 0
