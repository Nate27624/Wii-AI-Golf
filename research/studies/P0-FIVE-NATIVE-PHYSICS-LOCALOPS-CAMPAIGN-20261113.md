# Five independent native-physics LocalOps studies — operator-requested staging

**Execution state:** Staging only; **not yet five executed studies**. Source branch depends on draft PR #454 (`audit_p0_localops_rev1_study.py`) and its exact approved source archive qualification. This branch adds only TWO new original-source probes, with zero-argument operator-reviewed entrypoints. Studies 1–3 reuse EXISTING S002 assigned research without duplicating its private source scripts. See [S000 request](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-6844077668).

## Five-study queue (highest native-discriminator first)

1. **Power calc liveness / same-object overwrite** — S002 accepted-power owner #418. Reuse #454 original-source study, extend only in the existing owner's approved path after manager coordination. Must prove r31/r29/r26/r3 aliases and shot-commit branch; #96 triple-store is a prerequisite, NOT liveness evidence. No runnable new mode from this branch.
2. **Selected Ball v0 must-def and overwrite** — S002 v0 owner #415, draft PR #455. Once owner and checkout are confirmed, eligible existing `scripts/audit_p0_selected_ball_v0_provenance_private.py --study mode` then `--study alternative` and `--study gates` independently, with terminal source receipts between each. Do NOT run unbounded `integrator` study.
3. **Native integrator +0x84 speed freshness** — same S002 source owner provides source evidence via PR #455 existing bounded `--study speed`; assigned S003 airborne worker then consumes source contract. Must determine same receiver and path before claiming prior-step speed or float32/native timing. Distinct from study 2.
4. **Wind field-to-force linkage** — proposed new source assignment. This branch's `scripts/research_p0_native_wind_transfer_private.py` analyzes bounded PPC windows inside field generator, Scene wind helper and Ball force candidate. It establishes candidate PC/register/call links ONLY; output keeps actual selected receiver, branch reachability and native execution UNKNOWN.
5. **Ball/KCol collision response provenance** — proposed new source assignment. This branch's `scripts/research_p0_native_kcol_response_private.py` evaluates bounded Ball + Player candidate windows and four source collision-helper targets. It does not equate source query 0.5f to universal physical ball radius, nor confirm native edge/face/roll behavior.

## Required safety/qualification

Both new studies import **the SAME Git-tracked** #454 preflight module from the reviewed checkout. They require: original seven-pair manifest, original 14-bank SHA pre and post, RSPE01 Rev1 header, public source-unit owner check, 1/5/7 identical PPC windows, original nonlinear source gates, bounded synthetic PPC positive/negative controls and complete nontruncated JSON. They emit only source-PC/register/offset candidate syntax, not native words, file paths, private bytes, hashes or captured game data. They never run Dolphin, write local files or approve training. `allowed_to_publish=false`, `training_approved=false`.

Each study runs **sequentially**, never against an assumed shared checkout. S000 must allocate new Study 4/5 exclusive ownership and reconcile Study 1–3 existing owners and S003 airborne CLAIM. Reviewer must inspect exact source and CI. Operator separately approves **one** exact-SHA `checkout_reviewed`, verifies terminal `LOCALOPS_RESULT_V2 status=success`, then separately approves **one** `run_research` at a time. If another agent switches the shared checkout, restage exact verified branch first. Do not open five private issues at once or retry declines.

### Exact form of requests after owner assignment and reviewed branch checkout

Only in PRIVATE `Nate27624/Wii-AI-Golf-LocalOps` as title `[LOCALOPS-v2]`; body must be the sole JSON payload, with no Markdown. The SHA is intentionally omitted here until HEAD and CI are freshly verified; never paste a guessed SHA.

```json
{"schema":"localops-v2","project":"wii-golf","operation":"run_research","params":{"script":"scripts/research_p0_native_wind_transfer_private.py","args":[]},"intent":"Inspect qualified original Rev1 field/wind candidate call and scalar source sites, without game execution.","expected_output":"14-bank SHA/3-phase source gates and bounded public PC/register candidates; selected Ball wind effect unknown."}
```

```json
{"schema":"localops-v2","project":"wii-golf","operation":"run_research","params":{"script":"scripts/research_p0_native_kcol_response_private.py","args":[]},"intent":"Inspect native Ball->KCol source callsites and tentative velocity/state field uses, read only.","expected_output":"Original SHA/3-phase gates, bounded callsite source matrix; collision response and query radius semantics unknown."}
```

**No native parity:** These are preparatory source audits. Exact launch power, selected Ball v0, flight update order, wind transfer, contact response and guest timestep all remain unverified until stronger native evidence and separate independent tests.
