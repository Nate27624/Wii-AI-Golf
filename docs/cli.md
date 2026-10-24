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


## A-button BEFORE swing: independent priming phase (2026-10-24)

The user's 45-neutral-sample variant **failed**: motion was observed BEFORE A appeared to register and the ball was NOT hit. Source audit identified the actual flaw: every neutral `SwingSample` was scheduled through `trace.submit_swing`, and the generated bridge called `controller.set_wiimote_swing` each frame even when the vector/distance/speed were zero. That is **not a genuine A-only button hold**.

The current **source-only** correction uses an explicit separate preparatory RPC phase with **60 requests calling `controller.set_wiimote_buttons` ONLY**, all with A pressed and B released. No `set_wiimote_swing` or `trace.submit_swing` call is made until those requests return. Then the exact first user-confirmed **89-sample** forward swing profile runs (12 neutral A-held inside trace, 15 backswing, 20 forward, 30 A-held follow-through, 12 released). A/B are also best-effort released if priming or swing fails. No bridge patch regeneration and no new menu timing is needed.

~~~powershell
cd "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf"
git pull --ff-only
py scripts/golf.py test --pattern "test_integration_button_prime.py"
py scripts/golf.py test --pattern "test_integration_swing_client.py"
py scripts/golf.py test --pattern "test_integration_launcher.py"
py scripts/golf.py test --pattern "test_unified_cli.py"
# After focused tests PASS, close Dolphin:
py scripts/golf.py swing --slot 2 --a-prime-frames 60 --a-setup-frames 12 --follow-through-frames 30
~~~

The operator still confirms the **actual at-ball game screen before pressing Enter**. The button-only phase automatically finishes before the swing submission; do not manually initiate a second process. `--a-prime-frames 0` reproduces the old no-extra-priming full session with the exact 89-frame trace. `--a-setup-frames N` now explicitly means **neutral samples INSIDE the swing trace**, not a genuine independent button-only phase; default remains 12. These are bounded, separate parameters. The JSONL report records priming requests and swing samples/hash separately. This is an **unverified in-game timing hypothesis**; no new ball hit is claimed.

## 2026-10-24: Swing bridge V2 — neutral frames do NOT issue swing commands

**Negative live evidence:** Dolphin reported 60 completed A-only RPC requests and a complete 89/89-frame swing trace (start frame 1646; completion frame 1735), but the user observed **A released too early and no ball strike**. This is another failed shot, **not** a verified game hit. The Windows machine was still running the V1 `tools/mcp_bridge_swing.py` generator output; source changes do NOT update that local generated file by themselves.

**V1 code defect uncovered:** `set_wiimote_swing` ran every frame of `trace.submit_swing`, *including* zero-direction / zero-speed neutral A-held preparation and follow-through frames, and final A-off tail frames. Sending a zero swing primitive is not equivalent to doing no swing input; it may reset/override the Wii Remote dynamics that the game uses. This is a source-grounded hypothesis, **not yet empirically confirmed as the game's causal failure**.

**V2:** the pinned generated bridge now calls `set_wiimote_buttons` every frame, but calls `set_wiimote_swing` **only when the sample actually contains nonzero motion**. Neutral preparation, neutral follow-through, and A-released tail are therefore **button-only in the emulator frame loop**. A stays True across the full configured follow-through phase. The new read-only RPC `trace.swing_capabilities` advertises `swing_protocol: 2` and `neutral_button_only: true`. Both launcher and live probe fail closed when an outdated generated bridge is present (before launch and before swing, respectively).

**Once after pulling this update, with ALL Dolphin instances CLOSED:**

~~~powershell
cd "D:\\Projects\\Wii Golf AI\\Wii-AI-Golf"
git pull --ff-only
py scripts/golf.py bridge upgrade-swing
~~~

That regenerates `../tools/mcp_bridge_swing.py` from the existing SHA-pinned `../tools/mcp_bridge.py` and saves the former output **once** as `mcp_bridge_swing.py.before-neutral-v2.bak`. It refuses upgrade while port 55355 is in use. If the original source is not found or SHA mismatches, it fails without overwriting the existing bridge. Do **not** patch the already-generated V1 bridge as source. The one-time generated file is local and never pushed to GitHub.

**Tests and a single guarded experiment:**

~~~powershell
py scripts/golf.py test --pattern "test_integration_swing_patch.py"
py scripts/golf.py test --pattern "test_integration_button_prime.py"
py scripts/golf.py test --pattern "test_integration_launcher.py"
py scripts/golf.py test --pattern "test_unified_cli.py"

# Make sure Dolphin is fully closed before starting this fresh session.
py scripts/golf.py swing --slot 2 --a-prime-frames 60 --a-setup-frames 12 --follow-through-frames 90
~~~

This experiment extends **only the A-held neutral follow-through from 30 to 90** frames (new V2 bridge ignores zero-motion swing inputs); the **35 active swing samples** remain the same. Expected trace length: `12 + 15 + 20 + 90 + 12 = 149`. A is held for 137 trace samples, first released on sample 138 (1-based). The original first-hit 89-frame waveform remains available with `--follow-through-frames 30` on V2, but *bridge execution semantics differ*, so never claim a byte-identical game outcome from an identical input hash alone.

The operator confirms the golfer is **at the first ball** before pressing Enter; after the trace, record actual hit/no-hit, A release timing impression, and game distance if visible. V2 test mocks prove button/motion call order but cannot prove Wii Sports consumes them in that order. If the ball still isn't struck, investigate controller input readback, frame sampling and dynamics rather than extending the follow-through indefinitely.
