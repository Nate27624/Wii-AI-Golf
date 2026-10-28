# Open PR queue health: read-only integration review

**Study:** S000 cross-agent review, 2026-10-28. Draft review only; this is NOT a merge approval, agent dispatcher, game-memory study or live Dolphin test.

## Source-backed health finding

Connected GitHub open-PR search returned **76 open PRs** at review time. Multiple P0 investigations are stacked on other non-main PR branches, while the PowerShell-only operator contract is still draft #196, Windows full-suite tests retain seven known failures on main, and independent fixture repair #170 is draft. No score, motion or model-training gate is proven by PR count.

The repository's most urgent issue is integration/review throughput, not lack of research branches. Do not delete, rebase, auto-merge or take ownership of another agent's work.

## New advisory audit

- scripts/audit_open_pr_queue.py reads only open PR metadata from GitHub, using an Actions-supplied READ-ONLY GITHUB_TOKEN, or from an offline synthetic fixture. It cannot write to GitHub or launch Dolphin.
- It counts current open/draft/direct-main/nonmain-base PRs, identifies *known* in-repo stacked PR edges via base.ref = another open head.ref, and reports old last-update timestamps. Fork head refs cannot become false in-repo parent PRs.
- An unmatched non-main base is **unresolved for review**, not proof the branch was deleted. Graph cycles or incomplete data trigger abstention rather than an invented merge order.
- The output contains sanitized aggregates and bounded **numeric PR identifiers only**, no titles, body, authors, tokens, raw API payloads, private local paths, ROM, native RAM, savestates, or controller traces.
- .github/workflows/open-pr-queue-health.yml runs Windows/Ubuntu synthetic tests, fetches live metadata in read-only GitHub Actions, then **automatically uploads the sanitized PR health report as a GitHub Actions artifact**. No operator upload command, no new publisher and no change to the existing research/observations branch.
- GitHub Actions artifact is **repository maintenance data**, NOT a golf experiment result. Existing research_cli.py is still the canonical sanitized publisher for approved operator-run results; unintegrated private P0 scripts must not claim auto-upload.

## Interpretation and caveats

| Report field | Meaning | What it does NOT prove |
| --- | --- | --- |
| open_pr_count | Current open PR total | Readiness |
| draft_pr_count | Draft work awaiting review | Invalidity |
| nonmain_base_pr_count | Target ref is not main | Parent approved |
| linked_stack_edges_sample | Child/parent source branches match among open PRs in same repo | Safe merge sequence |
| unresolved_nonmain_base_count | Base not among other open PR heads | Branch deleted |
| stale_14d_count | Last GitHub PR update at least 14 days ago | Scientific relevance |
| review_pressure | Advisory backlog size warning | Automated priority |

GitHub PR list pagination is not atomic; this snapshot is best-effort. The tool is advisory only and performs no branch/merge/closure operations.

## Owners and next gates

- S000 owns this integration-health reporting and reviews numeric-only artifact publication. Keep main AGENTS/README edits with ongoing #196; this PR creates only new paths.
- S001 owns boot/controller and baseline Windows fixture regressions (#170), clean Dolphin CLI launch (#195), and first repeatable contact; none of these are changed by this review.
- S002 owns source-based RAM candidates, actual same-shot evidence, field meaning, censored score and landing outcomes; these remain **unverified for training**.
- Full hosted test suite and targeted synthetic audit are separate validation gates. Do not claim a game run or live outcome from this PR.

**Operator action: none.** The scheduled GitHub workflow will create its own safe artifact once reviewed and merged. Until then the new code is only on a draft branch.
