# Wii AI Golf CLI reference

**Use one human-facing command surface:** `py scripts/golf.py` on your Windows game machine. It works directly from this checkout without `pip install -e .`. Optional installed equivalents are `wii-golf` and `python -m wii_ai_golf`; installed versions depend on the interpreter's environment and can point to older worktrees.

~~~powershell
cd "D:\Projects\Wii Golf AI\Wii-AI-Golf"
py scripts/golf.py --help
py scripts/golf.py doctor
~~~

## Primary commands

| Command | Purpose | Requires Dolphin closed? | Real game action? |
| --- | --- | --- | --- |
| `golf doctor` | Check files needed for local workflows; never auto-fix | No | No |
| `golf play --slot 2` | Launch Felk, select Emulated Wii Remote/None, restore registered green-pre-start, dispatch A → A+B → A intro | **Yes** | Yes, no swing |
| `golf swing --slot 2` | Same fresh intro + one prompted human-confirmed baseline swing | **Yes** | Yes, one swing |
| `golf swing --slot 2 --follow-through-frames 45` | Single-factor A-release timing test | **Yes** | Yes, one swing |
| `golf state list` | Print registered local savestate profiles | No | No |
| `golf state register NAME --slot N` | Label an existing save slot (does not capture/write a savestate) | No | Catalog metadata only |
| `golf state reset NAME` | Advanced named reset in a known running Dolphin, no intro | No | Yes, state load request |
| `golf scenarios list` | Inspect observed scene registry | No | No |
| `golf scenarios plan --rounds 3 --out PATH` | Deterministic local plan; no emulation | No | No |
| `golf research studies` | Inspect S001–S005 proposals and blockers | No | No |
| `golf research evidence` | Summarize local swing observation records; human labels distinct from score | No | No |
| `golf research audit-motion --input PATH` | Offline RAM candidate audit | No | No |
| `golf test` | Run unittest tests against *this* checkout | No | No |
| `golf demo` | Run synthetic toy optimizer (clearly labeled) | No | No |

In tables, `golf` abbreviates `py scripts/golf.py`.

The **golden path** for experiments:

~~~powershell
# Dolphin MUST be closed before each fresh independent shot.
py scripts/golf.py swing --slot 2 --preset forward --follow-through-frames 30
~~~

The CLI delegates verbatim to `scripts/launch_golf.py --slot 2 --swing ...`. That existing launcher delegates to `launch_hitting_green.py`, which alone owns menu timing `120, 30, 315, 60, 135, 45, 300` requested frames. It attaches a single swing probe only after launching Dolphin, restoring the correct named state and dispatching the full intro. Before the swing you must visually verify the first ball and press Enter. There are no automatic repeated trials or state overwrites.

## Safe dry-runs, diagnostics, and extension points

~~~powershell
py scripts/golf.py swing --slot 2 --dry-run
py scripts/golf.py play --dry-run
py scripts/golf.py bridge patch --source "D:\Projects\Wii Golf AI\tools\mcp_bridge.py" --output "D:\Projects\Wii Golf AI\tools\mcp_bridge_swing.py" --enable-swing
py scripts/golf.py bridge ping
~~~

`--dry-run` prints only the delegated process command, without contacting Dolphin. `bridge patch` is an **advanced local operation**; it must never overwrite its pinned upstream input. `bridge ping` is an intentional read-only check against a running bridge, *not* a complete launch path.

`doctor` is read-only and lists missing local assets without inventing a game image or new Dolphin profile. Local paths are configuration-specific and aren't checked into Git.

## Universal experiment driver

When another agent adds a live, approved action under `scripts/`, reuse the coordinator's dispatcher without implementing any duplicate startup or bridge:

~~~powershell
# Dry run: shows both safe boot and approved action commands
py scripts/golf.py experiment --script probe_swing.py -- --preset forward --send-live-swing

# Live: closes the loop ONLY after a fresh verified intro
py scripts/golf.py experiment --send-live --script probe_swing.py -- --preset forward --follow-through-frames 30 --send-live-swing
~~~

The driver preserves the coordinator allowlist/disallowlist and injects `--attach-running` into its own already-booted swing subprocess, preventing two Dolphin processes. Never put `--attach-running` in the user-supplied flags for a normal experiment. For a specialized already-at-ball checkpoint, define a separate explicit scenario contract; do not send menu A/A+B/A over a ready-shot state.

## Research evidence versus measured performance

~~~powershell
py scripts/golf.py research studies --json
py scripts/golf.py research evidence --json
py scripts/golf.py research evidence --path "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\integration\swing-probes.jsonl"
~~~

`studies` reads the static proposal queue and **does not imply studies have executed**. `evidence` reads only the provided local JSONL file and reports observed-trial count, completed bridge dispatches, user-reported ball movement/green landing and explicit verified score count. Unknown/invalid lines are counted, never silently turned into zeros. A non-null game score without independent verification is **not** considered reliable.

Results should distinguish:

1. **Dispatch:** bridge status, frame count, full input hash, bridge and game builds.
2. **Human observation:** screenshot, hit/no-hit, visual power gauge estimate, displayed landing value + literal unit.
3. **Verified physical measure:** independently validated game distance/score extraction with unit and method.
4. **Research claim:** repeatability/splits/budget/held-out evaluation, only after measurements pass gates.

Store raw evidence in the sibling `Wii-AI-Golf-Data` folder. Source control contains lightweight sanitized reports, schemas, and verified research summaries—not copyrighted game assets or save-state bytes.

## Compatibility and agent guidance

Existing `scripts/*.py` commands remain intact. They are **implementation adapters and advanced diagnostics**, not competing product entrypoints. S001 owns live startup/bridge, S002 score extraction, S003 motion modeling, S004 search and S005 generalization. New functionality should implement a well-scoped module and expose it through this CLI, with a fake-subprocess test proving the expected delegation. Avoid importing Dolphin at CLI import time. No GPU training or GitHub Actions are triggered by the CLI.
