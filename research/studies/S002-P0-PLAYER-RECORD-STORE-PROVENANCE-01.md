# S002 P0 — Source-store candidates for changing player-record words

Draft, offline, source-only. Different from #235 runtime seven-phase masks and #219 branch callgraph. Focus is Rev1 PPC store-instruction candidates for the distinct selected-player record, NOT ball-object +0x30.

## Evidence motivating this check

#235 exact original fourteen-bank SHA/source-gated operator study found record D1→D2 changed +0x030,+0x034,+0x090; W5→W6 and W6→W7 changed +0x030,+0x090. A two-word role test found bounded BE-f32 interpretations, not proof of type or meaning. +0x054/+0x060 are source writer input/mirror controls from #162/#236; +0x038 is an unchanged control.

## Method and limits

- Reuse #219 original B0 native MEM1 SHA256/manifest and published RSPE01 Rev1 Golf code unit boundaries. Check header and SHA again after bounded source read. No Dolphin, RAM writes, new shots, new captures, raw uploads or private path leaks.
- Scan ONLY RPGolPlayer and RPGolPlayerManager .text for D-form stw/stwu/stfs/stfsu and other D-form stfd/stfdu/sth/sthu/stb/stbu whose signed displacement exactly matches +0x030,+0x034,+0x038,+0x054,+0x060,+0x090. Output source-unit-relative site offsets, names of registers/opcodes, capped candidate counts and explicit false gates.
- A store +0x090(rA) does NOT establish rA as the selected record base. This could be a different object or adjusted base. Indexed/indirect, other object-file and 8-byte overlapping stores remain unresolved. Zero candidates does NOT disprove a runtime writer.
- Source displacement matches cannot be causally joined to #235's changing runtime record until register provenance and actual receiver identity are established.

For approved operator use on EXISTING B0 only, after upstream #219 review:

    python scripts/audit_p0_player_record_store_candidates_private.py --data-root "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data" --private-session "D:\Projects\Wii Golf AI\Wii-AI-Golf-Data\ball-study-20261027-212633"

## Testing and release gates

Seven fully fabricated unit tests cover endian/opcode widths, signed negative displacement, source-unit attribution, no-match and malformed gates, sanitized output and failed private path. Windows/Ubuntu synthetic CI; no native data in GitHub.

No real original B0 was analyzed as part of this PR. Actual field semantics, shot power, velocity, physical XYZ, frame sync, impact, score and training all UNVERIFIED; approved_for_training=false, allowed_to_publish=false. Draft stacked on #219; require S002/S000 owners and full Windows suite before merge.
