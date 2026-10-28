## Agent owner / issue / branch

- Owner (S000–S005):
- Issue / CLAIM comment:
- Source branch + upstream PR dependencies:
- Changed paths / possible collisions:
- Downstream consumer + handoff link:

## Operator-command contract (MANDATORY)

- [ ] I read AGENTS.md, docs/operator-powershell-contract.md and docs/repository-map.md.
- [ ] The operator receives **one complete Windows PowerShell block**, auto-cd to D:\Projects\Wii Golf AI\Wii-AI-Golf with $ErrorActionPreference='Stop', real script paths/flags, exit checks and expected sanitized output; **OR** I explicitly state that NO local action is needed.
- [ ] NO manual Dolphin opening/loading, Lab GUI, Git Bash, bare attach-running, second startup, guessed tool or command that only exists in an unmerged PR presented as main.
- [ ] I reused existing canonical S001 fresh boot/menu, named checkpoint, original frozen waveform and currently source-validated bridge; I did not invent/replace controller timing or conflate A45 final menu, A-prime, V1 lead, neutral trace or follow-through.
- [ ] Any novel swing/launcher/shared CLI or source contract change is separately justified, preregistered, owner-reviewed and backward-tested, not presented as a new default.

## Validation / provenance / safety

- [ ] Focused tests and **FULL Windows suite** run with exact commands, platform, commit SHA and results; or explain which were not run and keep DRAFT.
- [ ] No overlapping S000/S001/S002 workstream code changed without canonical owner acknowledgement. Respect the current GitHub PR dependency order and no force push.
- [ ] All local RAM, ROM, savestates, generated bridges, private traces/config/pointers remain in ignored private Data; only typed sanitized records may be uploaded.
- [ ] Actual Dolphin hit, source-correlated RAM motion, frame timing, physical ball XYZ/velocity, game score and training gates are reported **separately**. Synthetic tests or RPC ACK are not game-outcome evidence.
- [ ] For LIVE actions: original clean Felk + physical named savestate, one canonical fresh boot, zero redundant Dolphin process, clear human consent and one attempt; do not run live from a new unreviewed PR.
- [ ] Reviewed status, blockers, future operator action (PowerShell only), next owner and evidence limitations documented in linked GitHub issue.

### Actual tests and observed outputs

(Paste exact targeted/full command and succinct pass/fail counts. Do NOT paste raw RAM/private paths, passwords or ROM data.)

### Operator PowerShell (if any)

(Paste one real self-contained command block, or say 'No PowerShell action needed'. For an unmerged branch, explain exact offline worktree provenance and never imply it is deployed.)
