# P0 source-global ball slot — bounded first-use hints for fifteen reads

## Hypothesis and decision rule

Original source-gated #240 seven-bank study identified a fifth ball-like source-global pointer outside ALL four roster-linked ball objects. The published source includes **15 direct lwz reads of its single r13 slot** (plus one direct stw) in one Golf source unit. This branch targets a specific unexplored question: after each *direct* source-global pointer read, does PPC immediately dereference a field, compare the pointer against zero, forward it into a direct BL, store it elsewhere, or cross a control/alias uncertainty?

Positive outcome: an exactly sourced immediate pointer field access, candidate r3-to-call forwarding, or null-check category gives a small owner-reviewed **next code site** to inspect. Negative outcome: all 15 are source-qualified, but no bounded direct consumers appear. Abstain: any load mismatch, duplicate/fewer sites, unknown effect before first use, source-code drift/Rev1/manifest failure; do NOT infer that an indirect usage cannot exist. Stop this micro-study after one native run if no typed consumer pathway emerges. Further nearest-def scans without new source/visual causal evidence are not worth computing.

## Implementation / boundaries

Review branch stacks on #240 exact commit `25f9660cc068983999f3cc6f44915f3803f8b614`. One NEW pure helper `scripts/review_p0_global_slot_load_consumers.py` classifies a **maximum six subsequent instructions per source-global direct lwz**, independently re-authenticating exact opcode, base r13 and source-slot displacement, and refusing any changes in the count or source unit. Results include only public unit-relative code offsets, GPR names, bounded field displacement (-512..512) and categorical first-use. Branches/calls/unknown X-form register effects stop the window, not assume safety. There are **no raw PPC words, runtime object values, private paths/digests, float values or native dumps** in the report.

The existing #240 read-only `scripts/audit_p0_global_ball_source_xrefs_private.py` is minimally extended to attach `source_global_pointer_read_first_use_hints` as one extra nested field after the existing 15-read source census. Its original seven-source roster/global geometry checks and source PPC SHA equality across W5/W6/W7 are unchanged. Operator must run pinned canonical #231 14-bank original manifest/banks **before and after** owner scanner; no new Dolphin, gameplay, capture or ROM dump. Native-free Windows+Ubuntu CI tests synthetics, privacy and inherited xref controls. Keep DRAFT until S002 #240/#219 and S000 #205 review; no self-merge.

Static first-use is NOT complete CFG, dynamic pointer consumer, rendered ball, simulation role, physics XYZ, velocity, power, impact, score, same guest frame, training permission or publication approval. All flags remain FALSE.
