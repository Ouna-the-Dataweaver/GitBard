---
name: structured-commits
description: Analyze pending changes, logically group them by target/concern, learn the repo's commit naming conventions from git log, and create partial structured commits. Use when the user asks to commit changes, create commits, or organize pending work into commits, or when they ask for commit magic.
---

# Structured Commits

Workflow for turning a working tree with mixed changes into clean, logically separated commits that follow the repository's existing conventions.

## Workflow

### Step 1: Analyze the Repository's Commit Conventions

Run in parallel:
- `git log --oneline -25` — study the message style (prefix, scope, casing, tense)
- `git status` — see all modified, added, deleted, untracked files
- `git diff` — review unstaged changes
- `git diff --cached` — review already-staged changes (preserve intent)

From the log, identify:
- **Prefix set** (e.g. `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `style`, `ci`, `build`, `perf`)
- **Scope usage** — are scopes used? parenthesized? (e.g. `feat(auth):`)
- **Casing & tense** — lowercase imperative (`add X`) vs past tense (`added X`)
- **Body/footer conventions** — single-line vs multi-line, references, breaking-change markers

### Step 2: Classify Changes into Logical Groups

Examine every changed file and hunk. Group by **logical concern**, not just directory. A single file may span multiple groups if hunks are independent.

Grouping heuristics (ordered by priority):
1. **Feature / behavior change** — new capability or modified behavior → `feat`
2. **Bug fix** — corrects wrong behavior → `fix`
3. **Refactor** — structural change, no behavior change → `refactor`
4. **Tests** — test additions or modifications → `test`
5. **Documentation** — README, docstrings, comments → `docs`
6. **Styling / formatting** — whitespace, linting auto-fixes → `style`
7. **Chore / config** — deps, CI, build config, tooling → `chore`
8. **Performance** — measurable perf improvement → `perf`

When uncertain whether hunks belong together, prefer **smaller, focused commits** over large mixed ones.

### Step 3: Plan the Commit Sequence

Before executing, present a numbered plan to the user:

```
Proposed commits (in order):
  1. feat(auth): add JWT token refresh endpoint
     — files: auth/refresh.py, auth/routes.py
  2. fix(chat): prevent duplicate message on reconnect
     — files: chat/handler.py
  3. test(auth): add refresh token expiry tests
     — files: auth/refresh_test.py
  4. chore: update dependencies
     — files: pyproject.toml, uv.lock
```

Wait for user confirmation or adjustments before proceeding. DO NOT PROCEED WITHOUT GETTING CONFIRMATION FROM USER. 

### Step 4: Execute Partial Commits

For each planned commit, sequentially:

1. **Stage precisely** — use `git add <file>` for full-file additions. When a file contains changes for multiple groups, use `git add -p <file>` or stage specific hunks via a temporary approach (apply only relevant hunks).
   - IMPORTANT: prefer whole-file staging (`git add <file>`) when the entire file belongs to one group.
   - Only split a file across commits when hunks are clearly independent concerns.
2. **Verify staging** — run `git diff --cached --stat` to confirm only intended files/hunks are staged.
3. **Commit** — use a HEREDOC for the message to preserve formatting:

```bash
git commit -m "$(cat <<'EOF'
feat(auth): add JWT token refresh endpoint

Add /auth/refresh route that validates existing token
and issues a new one with extended expiry.
EOF
)"
```

4. **Verify** — run `git status` after each commit to confirm clean progression.

### Step 5: Final Verification

After all commits:
- `git log --oneline -N` (where N = number of new commits) to review the result
- `git status` to confirm working tree is in expected state
- Report the summary to the user

## Commit Message Format

Follow the conventions detected in Step 1. If the repo has no clear convention, default to:

```
<type>[(<scope>)]: <short summary in imperative mood>

[Optional body: explain WHY, not WHAT. Wrap at 72 chars.]
```

- **type**: one of `feat`, `fix`, `refactor`, `test`, `docs`, `style`, `chore`, `perf`, `ci`, `build`
- **scope**: optional, lowercase, the subsystem or module affected
- **summary**: imperative mood ("add" not "added"), lowercase start, no period, max ~72 chars
- **issue**: when requested, add #issue_number in the end of commit
- **body**: separated by blank line, explains motivation when non-obvious

## Rules

- Never force-push or amend commits that have been pushed to remote.
- Never skip pre-commit hooks (`--no-verify`) unless the user explicitly requests it.
- Never commit files that likely contain secrets (`.env`, credentials, tokens). Warn the user if such files appear in the changeset.
- If a pre-commit hook modifies files (e.g., auto-format), amend only if the commit was just created and not yet pushed.
- If a commit fails due to hooks, fix the issue and create a new commit — do not amend the failed one.
- Preserve any already-staged changes the user set up intentionally — ask before unstaging.
- When `git add -p` is needed but interactive mode is unavailable, explain the situation to the user and suggest alternatives (e.g., manually editing the file to split changes, or committing the full file in the most relevant group).
