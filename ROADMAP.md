# Roadmap

Milestones are evidence-based, not a second Work Queue. See [GOALS](GOALS.md), [FINDINGS](FINDINGS.md) and canonical [migration issue #485](https://github.com/Nate27624/Wii-AI-Golf/issues/485). Status reflects the integrated baseline 838c3699 and manager roster rev76, not live CI.

## G-ORCHESTRATION — immediate critical path

| Milestone | Status | Acceptance / dependency |
| --- | --- | --- |
| M-QUEUE | Dormant implementation merged | #490 integrated lease, broker, GitHub store, artifact gateway and task-history code; production authority not enabled. |
| M-READ | Pending | Reviewed LocalOps release, isolated inert snapshot, pinned HTTPS host, independent read-only credentials, actual operator console acceptance; no V2 freeze required for this test. |
| M-SHADOW | Pending | Parse current roster and reconcile current claims, exact PR heads/CI, historical core hold and all prior reservations. No runnable imported work. |
| M-KNOWLEDGE | Seed staged | Four root contracts; goal pin approved separately; fenced finding proposals/curation, stable references and cross-task readback verified. |
| M-CUTOVER | Blocked | M-READ, M-SHADOW, M-KNOWLEDGE; authenticated restricted publication, remote disposable-ref CAS, reviewed freeze/drain, production admission, explicit approval and rollback rehearsal. |
| M-EXECUTOR | Deferred | Optional separately authorized executor; no continuous AI execution implied by the queue. |

Task links: V3-P0-LEASE-CORE, V3-P0-MIGRATE-SHADOW, V3-P1-KNOWLEDGE, V3-P1-LOCALOPS-CLI, V3-P0-CUTOVER, V3-P2-EXECUTOR. Preserve the [integrated source](https://github.com/Nate27624/Wii-AI-Golf/pull/490), [prior roster](https://github.com/Nate27624/Wii-AI-Golf/pull/320#issuecomment-7147241239) and [core retention](https://github.com/Nate27624/Wii-AI-Golf/issues/485#issuecomment-7147252595).

## G-RESEARCH — paused during migration

| Milestone | Status | Acceptance / dependency |
| --- | --- | --- |
| M-POWER | Unresolved | #418; prove accepted native power and transfer with independent controls. |
| M-LAUNCH | Unresolved | #415; verify selected Ball v0, force/step chronology and launch provenance. |
| M-CONTACT | Provisional implementation | #467/#482; explicit initial-state terrain-only solver, native KCol/clock/tree clearance unresolved; end-to-end prediction depends on M-POWER and M-LAUNCH. |
| M-OUTCOME | Blocked | #472/#5/#6; independent joined guest-step/outcome evidence and approved held-out dataset, training false. |

No paused research is newly dispatched by this document. Manager updates roadmap through reviewed fenced publication after activation.
