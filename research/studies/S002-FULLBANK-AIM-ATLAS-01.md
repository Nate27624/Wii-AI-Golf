# S002-FULLBANK-AIM-ATLAS-01 — whole MEM1+MEM2 idle/aim differential with source-owned object overlay

**Status:** pre-registered offline study, no new Dolphin capture, no gameplay swing and no model training. User explicitly authorizes broad in-game memory analysis. Branch STACKED on S002 #163/#160 authoritative source/roster verification; does not compete with active swing watcher S001 #166 or S000 field dictionary #154.

## Why this study now

Operator collected eight distinct, private paired B0 idle/B1 idle/B2 visible WASD aim/B3 idle-after-aim images from one reported Dolphin boot. **Both** complete MEM1 and MEM2 image hashes differ at each transition. S002 #163 established selected record, nested ball-like vector and current-start vec3 remain **bitwise static 3/3 components** across those four phases; S002 #174's candidate record+0x24 is zero across all four records and all four phases. The first 0x80 bytes of the main's player-like candidate were also unchanged. These are valuable negatives, but tell us little about the majority of active RAM. User wants expansive memory analysis, not artificially small windows.

## Method: all source-valid native RAM, with honest causal limits

New `scripts/audit_golf_fullbank_fourphase_private.py` reads the ALREADY PRESERVED 4×(24MiB MEM1 +64MiB MEM2) checkpoint files in the ignored Data sibling folder, verifies their private checkpoint manifest SHA256 and phase labels, then:

1. Compares EVERY 32-bit aligned word of BOTH memory banks: 22,544,384 aligned words per checkpoint (**88 MiB**) and ~90 million word observations across B0/B1/B2/B3. Records B0→B1 idle, B1→B2 visible aiming, B2→B3 idle-after-aim word-change counts and 4KiB changed-page counts.
2. Ranks every changed 256-byte subpage block by `B0=B1`, `B1!=B2` (aim-correlated with negative idle control), followed by `B2=B3` *persisted* or `B3=B1` *reverted* signatures. Captures any idle noise separately rather than labeling any changed word as aim. Does not silently omit changed areas: counts the entire bank, saves the full distinct-block count and an explicit count of omitted blocks past the user-selected local top N.
3. Re-resolves per checkpoint (never assumes heap pointer stability) the complete SOURCE-GATED selected scene, RPGolMain, GolfConfig, FieldManager, PlayerManager, all 4×0xCC player records and 4 ball-like object instances, selected nested ball translation, source pin/start/cup/course/tee transforms, main child Player-like candidate and two source-known nine-word wind BSS tables. Bounded object offsets and exact change signature flags are reported for every changed aligned member; explicit object allocation continuity booleans.
4. Every source-object comparison is fail-closed if Rev1/Golf scene/mode, selector/hole, field translation or PPC linked roster provenance fails. Identical or relocated heap addresses are not guessed as new physical position. **No inference of world XYZ, club pose, contact, power, true game-frame timing or model readiness.**
5. Writes a local-only JSON *detailed differential atlas* with every ranked source-object word and all top 256-byte bank blocks; stdout is a short object-change and whole-bank-count summary. **No code bytes, raw memory arrays, arbitrary four-word values, runtime pointers or private SHA256 in stdout or repo.** The user's local report retains detailed bank-relative subpage indices and source-relative offsets because the user requested broad memory analysis. Do not automatically upload the JSON to a public GitHub repo (no S000 reviewed schema).

### One-time operator steps — no Dolphin launch or new exports

Use PowerShell. Reuse `$private` pointing to the folder that ALREADY contains B0/B1/B2/B3 MEM1/MEM2 and `checkpoint-manifest-PRIVATE.json`. If the variable isn't set, supply your existing directory when prompted. Fetch a new detached worktree so other agents' changes are untouched:

```powershell
$root = 'D:\Projects\Wii Golf AI'
$repo = "$root\Wii-AI-Golf"
$workAtlas = "$root\Wii-AI-Golf-Fullbank-Atlas"
$branch = 'agent/research/fullbank-fourphase-source-overlay-20261027'
if (-not $private -or -not (Test-Path "$private\checkpoint-manifest-PRIVATE.json")) {
    $private = (Read-Host 'Existing B0-B3 checkpoint folder (in Wii-AI-Golf-Data)').Trim('"')
}
if (-not (Test-Path "$private\B3-MEM2.bin")) { throw 'Missing preserved B3; do not recapture' }
git -C $repo fetch origin "refs/heads/${branch}:refs/remotes/origin/${branch}"
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed' }
if (-not (Test-Path $workAtlas)) {
    git -C $repo worktree add --detach $workAtlas "origin/$branch"
    if ($LASTEXITCODE -ne 0) { throw 'Worktree add failed' }
} else {
    $expected = git -C $repo rev-parse "origin/$branch"
    $actual = git -C $workAtlas rev-parse HEAD
    if ($expected -ne $actual) { throw 'Existing worktree revision differs; inspect before using' }
}
py -m unittest discover -s "$workAtlas\tests" -p 'test_golf_fullbank_fourphase_private.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Failed synthetic tests; STOP' }
$report = Join-Path $private 'fullbank-fourphase-atlas-PRIVATE.json'
if (Test-Path $report) { throw 'Report exists; choose a new filename, never overwrite' }
py "$workAtlas\scripts\audit_golf_fullbank_fourphase_private.py" --private-root $private --output $report --top-blocks 2000 --max-object-offsets 4096
if ($LASTEXITCODE -ne 0) { throw 'Full-bank atlas failed; preserve old captures' }
```

**What to paste back:** only script's stdout summary (`bank_summary` and `source_object_change_counts`). It has no raw words or addresses. Keep `fullbank-fourphase-atlas-PRIVATE.json` locally; it includes the detailed bank-relative 256-byte block hotspots and all source-object relative change offsets for S002 follow-on analysis. The file can be reviewed privately within ChatGPT if the user elects to upload it, but should NOT be blindly committed to public GitHub. If the entire bank atlas is too large, run with `--top-blocks 250` rather than re-capturing.

## Scientific interpretation and priority choices

- Many pages/words change at B0→B1 idle: expected timing, animation, heap activity. Rank B1→B2 contrast in regions not moving during B0→B1, then inspect B2→B3 persistence to separate sustained aim from transient aim-cursor animation.
- An offset that changes only at B1→B2 is an **aim-correlated candidate**, never proof of controller aim angle or game-applied input; source register flow and independent boot/aim-direction reversals are needed.
- If source-selected ball/start vectors stay unchanged but camera/HUD pointers change, this is a valuable sanity check and should not be treated as failed test.
- If any supposed source object invalidates or relocates between phases, investigate lifetime before interpreting word deltas. Do not silently label allocator remapping as movement.
- S001's clean Preview4 boot recovery via FelkDolphin-Clean was confirmed for native startup and read-only loopback, **NOT** yet reliable ball contact. No shot is requested here. Continue to abstain from physics/power model training until the game's ball visibly moves and a source-selected vector follows it with proper frame/timing provenance.

## Ownership and tests

S002 #160/#163 own canonical source and selected vector/roster, #162 writes and wind, S002 #174 source candidate +0x24, S001 #166 frame watcher, S000 #154 evidence promotion and privacy, S003 #125 models. This study adds only a new full-snapshot offline instrument and synthetic tests. No Dolphin launch, bridge modification, RPC controls, startup troubleshooting, training labels or automatic merge. **Tests must pass on BOTH Windows and Ubuntu before operator run.**