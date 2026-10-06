# <Project> — Agent Guide

This guide applies to the entire repository and is the shared source of instructions for coding agents.
Its purpose is not to govern every decision, but to preserve project workflows and invariants that are
easy to miss. Developer requests may override working defaults; hard constraints may only be overridden
when the developer explicitly asks for it.

## Product and repository map

<One sentence: what the product does and for whom.>

- `<dir>/` — <role; mark which directory is the source of truth>.
- `<dir>/` — <role>.
- `docs/` — <which docs are active contracts vs research/history>.
- `scripts/` — <operations/experiments; not production code unless the task targets them>.

## Hard constraints

<!-- Only rules whose violation is expensive or irreversible. Each one states the safe alternative. -->
- Run the application and runtime checks through <Docker / the dev script>: `<command>`.
- Do not run production builds unless requested.
- The developer manages staging, commits, and deployments. Do not run `git add`, `git commit`, push,
  create PRs, merge, rebase, or deploy unless requested.
- Do not reset volumes/databases or perform destructive data operations without permission and a clearly
  resolved target.
- Do not expose or place secrets, tokens, API keys, credentials, or personal data in code,
  documentation, conversation logs, or commits.
- Do not test paid transactions, payment callbacks, or real email delivery before confirming that the
  environment, account, cost, and impact are safe.

## Working defaults

- Understand the affected flow, then make the smallest coherent change that solves the problem.
- Follow existing code patterns before introducing abstractions, dependencies, or services.
- The worktree may already be dirty. Preserve developer changes and avoid touching unrelated files.
- Use independent judgment for details that are easy to reverse. Ask when a choice materially affects
  product behavior, data, cost, security, or scope and the answer cannot be found in the repository.
- Do not claim results, tests, or diagnoses that have not been verified.

## Naming and language

- Code is English: identifiers, file names, database columns, API/JSON keys, CSS classes, log/event names.
- Text a person reads is Indonesian: UI labels, toasts, error messages returned to users, emails.
- Comments follow the surrounding file. Do not mass-rename existing identifiers.

## Architecture invariants

<!-- Non-obvious facts that break things when ignored: dependency direction, sources of truth,
     idempotency requirements, where new code belongs, framework-version quirks. -->

### <Area>

- <Invariant and why it exists.>

## Documentation on demand

- Read `<doc>` when <situation>.
- When code and documentation disagree, verify actual behavior and correct the active documentation.

## Verification and debugging

- Use the smallest evidence proportional to the change's risk. Start with targeted checks and expand
  only when shared code or regression risk warrants it.

  ```bash
  <exact check commands, each with when it is required>
  ```

- For UI work, prioritize DOM snapshots, console, and network inspection; take screenshots when the
  issue is visual or final visual evidence is needed. Save them outside the tracked tree.
- The final handoff reports the outcome, changed files, checks performed, and remaining limitations.

## Maintaining this guide

Add a new rule only when it records a non-obvious invariant, prevents an expensive failure, or addresses
a repeated correction. When instructions become specific to one directory or workflow, move them into
domain documentation or a closer `AGENTS.md` instead of expanding the root file.
