# S002 — Standalone PowerShell native-shot status and integrity (corrected)

**Operator feedback 2026-10-28:** Earlier two scripts caused confusion. Tests locally were reported as `OK (skipped=8)` on Windows lacking `pwsh` and a fresh session was checked with `-RequirePost` before ANY memory had been captured. Neither was evidence of a successful PRE or POST. The scripts were replaced with ONE `scripts/Invoke-GolfNativeShot.ps1`, compatible with native Windows PowerShell 5.1, and the tests now refuse to skip silently.

## One standalone script (downloadable anywhere)

Run with normal Windows PowerShell 5.1 or PowerShell 7; no Python, `pwsh`, emulator, or Git worktree needed for these three operations. Download the single script; pass `-Workspace` when the file is outside the main repo's `scripts` directory.

```powershell
$script = 'D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\tools\Invoke-GolfNativeShot.ps1'
$workspace = 'D:\Projects\Wii Golf AI'
$session = & $script -Action Start -Workspace $workspace
& $script -Action Status -Workspace $workspace -Session $session
# The expected result here is Status=AWAITING_PRE; this is NOT a saved memory snapshot.

# Much later, only after an approved #201 reader really saved PRE and POST:
& $script -Action Verify -Workspace $workspace -Session $session
```

Do **not** invoke `Verify` immediately after `Start`: it intentionally throws `NOT READY` until real native PRE+POST exists. `Status` on a fresh session instead returns AWAITING_PRE without throwing; on PRE-only returns AWAITING_POST after validating present banks. `Verify` requires both checkpoints, real full native file sizes, SHA-256 agreement, game revision header, exact keeper manifest shape, phase ordering, human pause and displaced-ball attestations. An integrity pass does not prove guest-frame atomicity, ball motion/world XYZ/velocity, official score, or training suitability.

### Scope / remaining blocker

This is standalone for the session/check workflow, **not a fully automated gameplay snapshot**. Real native capture still needs upstream owner-reviewed S002 #201 Dolphin Memory Engine reader, an already running operator-paused CLEAN Felk Dolphin, S001 approved V1 45 **observed** frame lead, and confirmed ball displacement before reset for POST. No one-click automatic POST freeze exists yet. Do not run unapproved live #201 or copy raw RAM to GitHub.

## CI

`python -m unittest discover -s tests -p 'test_s002_native_phase_powershell.py' -v` exercises synthetic sparse 24 MiB/64 MiB bank fixtures and session statuses. Uses built-in `powershell.exe` on Windows and `pwsh` on Ubuntu; missing PowerShell is a hard test error, never skipped. Exact-branch Windows PowerShell 5.1 and Ubuntu PS7 CI are the verification source; raw RAM never used or uploaded.

**Handoff:** S002 #201/#184 uses real reader/keeper; S001 #206/#211 handles swing/selected-record watch; S000 approves combined operator workflow. This PR only adds one offline script, tests, workflow, and documentation.
