# Private GitHub Issues -> Windows LocalOps (v1, opt-in)

This is a **private mailbox protocol for this ChatGPT conversation**, not
Codex, not a new ChatGPT plugin, and not a GitHub Actions self-hosted runner.
It is an optional local Windows program. The ChatGPT GitHub connector creates
requests; the local agent obtains them using a minimal GitHub Issues token,
checks a strict allowlist, executes fixed commands in the configured
Wii-AI-Golf checkout and comments the results back onto a **PRIVATE** issue.

**The public `Nate27624/Wii-AI-Golf` repository must NEVER be the mailbox.**
GitHub explicitly warns against attaching unrestricted self-hosted runners to
public code repositories. The local agent refuses to operate unless the
GitHub API confirms the mailbox repository is private. No source ROM/BRRES,
Dolphin memory bytes, private asset coordinates, GitHub credentials, home
directory contents or open-ended shell commands should be committed to an
issue.

## One-time Windows setup (operator must perform)

1. Create a **separate private repository** named
   `Nate27624/Wii-AI-Golf-LocalOps` in GitHub. Enable Issues. Keep
   `Wii-AI-Golf` itself public if desired.
2. Allow the existing ChatGPT **GitHub** connector access to the new private
   repository. This is necessary for ChatGPT to create requests and read
   result comments from within the current conversation. The owner can
   confirm access by asking ChatGPT to create an initial `repo_status` issue
   **after** the agent setup.
3. On GitHub, create a **fine-grained PAT** restricted to the **new private
   mailbox repository only**. Grant `Issues: Read and write` and default
   `Metadata: Read` permissions. Do NOT grant `Contents`, `Actions`,
   `Administration`, or any broad repository scope. Never put the token
   in a chat, issue, file, or permanent shell profile.
4. Install or use Python 3 and Git on Windows. Open an ordinary
   **non-administrator** PowerShell. The source checkout
   `D:\Projects\Wii-Golf-Visual-Review` should already exist.
5. Check out this bridge's reviewed commit or copy the `private_issue_agent.py`
   file to a **stable separate folder**, e.g.
   `$env:LOCALAPPDATA\WiiGolfLocalOps\private_issue_agent.py`.
   The script must not itself be fetched and executed directly from the
   mailbox or run from a worktree that it later switches.
6. Start a foreground interactive agent:

```powershell
$ErrorActionPreference = 'Stop'
$agent = Join-Path $env:LOCALAPPDATA 'WiiGolfLocalOps\private_issue_agent.py'
$secret = Read-Host 'Fine-grained GitHub Issues token (input hidden)' -AsSecureString
$env:WII_GOLF_LOCALOPS_GITHUB_TOKEN = (
    [pscredential]::new('localops', $secret).GetNetworkCredential().Password
)
try {
    & py -3 -I $agent `
        --mailbox 'Nate27624/Wii-AI-Golf-LocalOps' `
        --trusted-actor 'Nate27624' `
        --worktree 'D:\Projects\Wii-Golf-Visual-Review' `
        --terrain-obj 'D:\Projects\hole01-collision-candidate-PRIVATE.obj' `
        --terrain-labels 'D:\Projects\hole01-collision-candidate-labels-PRIVATE.json' `
        --watch
}
finally {
    Remove-Item Env:\WII_GOLF_LOCALOPS_GITHUB_TOKEN -ErrorAction SilentlyContinue
}
```

Stop safely with **Ctrl+C**. Nothing is installed as a Windows service,
scheduled task, browser extension or system-wide runner. The agent does not
make outbound GitHub requests while stopped. In `--once` mode (default)
only one pending request is considered, and the process exits. Use
`--dry-run` to inspect the next request without marking or executing it.

## ChatGPT command issue protocol

In the **private** mailbox only, create an ordinary GitHub issue with the
exact title:

```text
[WII-LOCALOPS-v1]
```

and a body that is **nothing but strict JSON**:

```json
{
  "schema": "wii-golf-localops-v1",
  "operation": "repo_status",
  "params": {}
}
```

Valid operations (all arguments must match exactly):

| Operation | Parameters | Execution |
|---|---|---|
| `repo_status` | `{}` | Auto; short HEAD and tracked file status |
| `list_project_files` | `{"subdir":"scripts"}` | Auto; filenames ONLY inside existing checkout |
| `run_inspector_tests` | `{"suite":"inspector"}` or `{"suite":"localops"}` | **Approve locally**; runs fixed unittest patterns |
| `sync_review_branch` | `{"branch":"agent/...","required_sha":"40 hex chars"}` | **Approve locally**; refuses dirty checkout, unexpected origin or a branch whose current head differs from the EXACT approved SHA |
| `launch_inspector` | `{}` | **Approve locally**; launches fixed FC3 inspector command using operator-configured terrain/labels |

There is intentionally **no `cmd`, `powershell`, `script`, `run arbitrary
shell`, arbitrary path argument, arbitrary Python snippet, GitHub Actions
runner or background RCE endpoint**. GitHub issue comments are **output
only**, not executable commands. A trusted-actor issue is not itself enough
to authorize code execution.

The agent posts an acknowledgement comment before a local command, then a
structured `WII_LOCALOPS_RESULT_V1` comment with JSON output and closes the
issue. ChatGPT can read the result through the same installed GitHub
connector, so no pasting command output into the chat is required once
the private mailbox is connected. Declined requests are closed without
running. A crashed execution after an ACK is NOT retried automatically:
issue a new request instead.

Results have size limits, and token-like strings are redacted. Results
are private to the mailbox repository and anyone with access to it;
do not treat them as a security secret from other mailbox collaborators.

## Safety guarantees and remaining limitations

- **Mailbox must be private**, verified on GitHub API before polling.
- **Only owner-authored issues** (by default `Nate27624`) with the exact
  title, strict schema, approved operation and parameter fields are parsed.
  PR descriptions, arbitrary comments, untrusted issue authors and
  program commands in prose are never executed.
- **No shell evaluation**: subprocesses use fixed `argv` with
  `shell=False` and the token removed from child environments.
- **No uncontrolled execution**: source tests, Git fetch/checkout and
  GUI launch require explicit local console Y. Running repository Python
  tests can execute **any code contained in that checkout**, so inspect
  untrusted branches before granting approval.
- **Not a remote desktop**: there is no screen capture, input injection,
  game controller operation, or remote access to non-project directories.
- **Not yet installed**: until you create the private repo, authorize its
  GitHub connector and start the local script, ChatGPT cannot run any local
  commands. Do not assume that posting a public GitHub issue triggers it.
- Use a **standard Windows user** where possible. Do not run as Administrator
  or let untrusted contributors modify the exact agent copy.

The bridge code itself lives in the public source repo for review, but
the **mailbox, authorization, operation output and local token** do not.
