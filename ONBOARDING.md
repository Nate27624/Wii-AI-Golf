# Project onboarding

**Status: V3 staged, V2 authoritative until explicit cutover.** Read [AGENTS.md](AGENTS.md) and [merging.md](merging.md) for current permissions and merge rules. This document does not replace them or confer a lease.

## Start here

- [GOALS.md](GOALS.md): operator objectives and non-negotiable constraints.
- [ROADMAP.md](ROADMAP.md): milestones and acceptance gates, not a dispatch list.
- [FINDINGS.md](FINDINGS.md): curated, bounded research claims and provenance.
- [V3 architecture](docs/v3-orchestration.md) and [migration issue #485](https://github.com/Nate27624/Wii-AI-Golf/issues/485): current migration context.

## Universal worker procedure (after activation)

1. Read current knowledge and the sole merge contract; authenticate to the approved broker.
2. Atomically acquire eligible work, or report idle/blocked without editing. The permanent S000 manager is first in the display and preferred when eligible; no worker may self-assign.
3. Read the permanent task objective, acceptance, scope, dependencies and durable history. Verify current source head, permissions and evidence.
4. Work only within the assigned fence and scope. Checkpoint and renew before the 120-second inactivity deadline. An expired run closes and unfinished work reopens; it is not a completed task.
5. Record exact source/PR head, executed checks, findings, uncertainty and next action. Finish/release atomically through the authorized broker. Stale tokens cannot publish or finish.

Until cutover use the V2 roster and claim procedure instead. The manager curates shared knowledge, not operator goals. LocalOps is the sole human Work Queue console; golf.py and research_cli.py remain project-specific commands. Neither the console nor a GitHub comment launches an AI worker.

No private data publication, live Dolphin action, training or local permission expansion without the applicable separate authorization. A failed gate blocks work rather than creating new authority. See [merging.md](merging.md).
