# P0 offline memory inspector (experimental, read-only)

An offline Tkinter viewer for source-gated **candidate** memory observations. It is not an experiment runner and does not start/attach Dolphin or send any guest commands. It does **not** establish actual ball world XYZ, screen coordinates, physical velocity, frame timing, game accepted A, contact or power. `training_approved=false` always.

## Windows PowerShell — one-paste launcher

From the Wii-AI-Golf repository directory after the inspector PR has been merged (or from this branch), paste:

```powershell
py -I scripts/p0_memory_inspector.py
```

Use the two **Browse** buttons to choose your existing LOCAL event JSONL and matching SHA-256 manifest, then click **Verify SHA-256 and Open**. Both files remain local. No ZIP, separate Python code, game startup or console memory dump is needed. Optional command arguments are `--capture "<local-file>.jsonl" --manifest "<local-manifest>.json"`. The viewer requires standard Python Tkinter on Windows; it is not supported on headless CI.

## Schema / integrity

The pinned replay schema matches `scripts/p0_live_directional_aim_series.py`: one JSON object per line with `phase`, `sample_index`, `start_monotonic_ns`, `end_monotonic_ns`, `source_identity_digest_private`, `source_layout_qualified`, and `candidate_words_private_be_u32_hex` (field names -> arrays of exactly eight-digit hexadecimal BE u32 words). The original complete SHA is verified **before parsing**. The manifest must explicitly supply an unambiguous `sha256`, `capture_sha256`, `jsonl_sha256`, `event_stream_sha256`, or a matching `files` / `artifacts` entry with `path` / `filename` and `sha256`; `capture_file` if present must match. Invalid hashes fail closed. The older private 46-packet file may require a format adapter after examining its exact manifest and stream schema; compatibility is not claimed without that check.

Per-word IEEE-754 float32 is only a *hypothesis*. Non-finite candidate floats cannot be plotted but their raw hex remains visible. Records without source qualification are displayed with a warning; source identity switches break visual trajectories. M1 contact in an aborted run is only human observed; the exact impact frame is unknown. A malformed final partial JSONL packet is flagged incomplete and earlier verified complete records remain visible. Malformed earlier packets fail closed. A 32 MB / 30,000-sample bound applies to offline loads.

## Controls

The left panel shows phase segments and raw aim hypothesis with a manual baseline; the middle panel has a scrubber and rotatable orthographic **3D source-component** trajectory with selected ball +0x30 white, cache +0xCC amber. The right panel retains each raw 32-bit hex and tentative float32. The bottom area warns about elapsed host read duration, non-atomic alias reads, phase-abort status and source identity. 3D rotation **is not a camera-calibrated projection into Dolphin**. Power remains an unverified candidate and has no percent gauge.

## Testing

```powershell
py -m unittest discover -s tests -p test_p0_memory_inspector.py -v
py -m unittest discover -s tests -v
```

The isolated workflow runs on Windows and Ubuntu with **synthetic fixtures only**. No private game captures/paths, ROM, savestates or screenshots may be committed. Live read-only bridge integration and optional image calibration require separately scoped review and evidence gates.
