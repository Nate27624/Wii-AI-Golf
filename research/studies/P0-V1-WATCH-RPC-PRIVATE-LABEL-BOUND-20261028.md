# S001 V1 private watcher: RPC response bound and separate human evidence

This is a stacked DRAFT review on #206; not a live-shot authorization. Operator Windows verified #206 exact head with 12/12 tests PASS and the offline dry run. Prior adapter #202 real Windows source-preflight passed and exclusively generated separate watched V1 source SHA 465b6b02a9ae3833c65233b0d7a26fca79c613330eedf4eeb1de2a5d89ff886b. No Dolphin started.

## Two defects caught BEFORE any live watched shot

1. Up to 70 phase samples each contain 51 u32 player words plus metadata. Synthetic 70-record JSON exceeds default 65536-byte FelkRPC max response. The private V1 watcher alone now uses a bounded max_response_bytes of 262144, leaving all other RPC client defaults unchanged. This changes no sampling or input control.
2. Old human prompt asked if a ball was visually STRUCK but passed that response to the motion validator as human_ball_moved. Human contact and ball movement are different observations. Now asks both independently. The private record retains operator_observation for observed movement and adds operator_contact_human; redacted summary includes contact_human. Unknown/invalid values are never inferred yes.

No changes to historical V1 or separate watched bridge, frozen 89 samples, 45 measured A frames, original source-selected 51-word watcher, game launch/savestate, data publishing or training.

## Owner gates

S001: reviewed native callback overhead <=5ms, exact bridge runtime, watcher noninterference, source/phase provenance and full Windows regression. S002: preserve distinct contact vs motion semantics and unverified ball/shot state; no physics identity claims. S000: approve safe redacted labels and private pointer-bearing RAM evidence retention. S003: no training. Live one-shot needs further explicit owner approval and operator consent.

Tests on synthetic max-sized JSON response, dedicated transport options, independent contact/movement prompts and old 12 offline collector regressions on both Windows and Ubuntu.
