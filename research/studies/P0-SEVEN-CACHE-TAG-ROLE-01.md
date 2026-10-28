# P0 S002 — seven-phase cache update metadata tags (+0x118/+0x11C)

**Status: proposed, offline only. No real private seven-pair execution yet. No training. No merge approval.**

## Specific question

S002 [#183](https://github.com/Nate27624/Wii-AI-Golf/pull/183) traces the source Rev1 conditional F0/FC cache copy paths in fn_80299C70, including 32-bit tag stores at ball object +0x118 (F0) and +0x11C (FC). Their semantics are unknown. [#236](https://github.com/Nate27624/Wii-AI-Golf/pull/236) found real W5→W6→W7 selected ball+0x30 changed 3/3 on each edge while cache F0/FC/CC all remained stable. Did the tag words also remain unchanged, or did any tag change without its associated cached triple?

This is distinct from #235 selected player-record masks, #238 main counter, #239 score table, #233 endpoint ordering and the four-slot CC ownership study. The tags are in the *ball object*, not the player record.

## Gates

- Stack on [#231](https://github.com/Nate27624/Wii-AI-Golf/pull/231), verifying all 14 original 24MiB/64MiB banks against the archive SHA manifest; source-gate every Rev1 scene, selected player/ball, pin and start.
- Resolve four PlayerManager records with source stride 0xCC, each record+0x88 child ball, full 0x1AC MEM2 objects and ball+0x4C == ball+0x30 self-pointers. Reject duplicates and selected-ball alias disagreement.
- Inspect only two ball-object metadata words per slot (+0x118, +0x11C), selected F0/FC caches and source-selected current. Compare selected tag-change bools with inactive slot change counts, and report whether a tag changed while its associated cache triplet remained bitwise fixed.
- Require stable selected owner, hole, source record/ball/field/pin/start pointers, source pin/tee vectors and Config BC/C0/C4 for within-shot edges. Compare D1→D2 and W5→W6→W7, including W5→W7. Exclude P3→D4: club, pose and A differ.
- Hash-verify original 14 banks again after reading. No new Dolphin, swing, RAM writes, private dump/upload, numeric tag or float print, pointer/hash/path or binary output.

## Commands

First run **fabricated** tests from the stacked checkout:

    py -I -m unittest discover -s tests -p test_p0_seven_cache_update_tags_private.py -v

After source-owner review only, run against the already preserved private archive:

    py -I scripts/audit_p0_seven_cache_update_tags_private.py --archive "<EXISTING_IGNORED_PRIVATE_SEVEN_ARCHIVE>"

The CLI emits sanitized JSON to stdout, creates no files, and never uploads anything. Original human phase labels have not been independently joined to guest frames. Local synthetic PASS does not establish native PASS.

## What the results can mean

- Tag and cache both unchanged: sampled state did not change, but identical-value writes/transients remain possible.
- Tag changed while cache unchanged: metadata changed separately at the snapshots. This justifies investigating tag RHS and writer object, **not** naming it a clock, hit or impact flag.
- Tag and cache both changed: consistent with the source copy path, but not proof of execution by this receiver.
- Inactive tag changes: reject a selected-only interpretation without further owner/lifecycle proof.

**Remaining P0:** #183/#219 source-global ball pointer and r27 receiver identity, independently of this tag equality audit. No evidence here verifies physical XYZ, velocity, world axes/units, frame delta, swing power, collision, score, cache endpoint semantics, training or publication. Keep all promotion gates FALSE.
