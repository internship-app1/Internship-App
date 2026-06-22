Interactive pre-PR code review: finds issues, posts PR comments, proposes fixes one at a time, applies approved changes, and commits.

---

## PHASE 1 — GATHER CONTEXT

Run these in parallel:
- `git diff -U5 --merge-base origin/HEAD` — the full diff to review
- `git branch --show-current` — current branch name
- `git log --oneline -5` — recent commits for context
- `gh pr view --json number,title,url,state 2>/dev/null || echo "NO_PR"` — detect open PR

If the diff is empty, stop and tell the user there is nothing to review.
If NO_PR, note it — you will skip the GitHub comment step but still do the full review and fix flow.

---

## PHASE 2 — REVIEW

Using the diff from Phase 1, perform a thorough code review. Look for:

**HIGH severity:**
- Correctness bugs (logic errors, off-by-one, wrong condition, null dereference)
- Security issues (injection, exposed secrets, unvalidated input, auth bypass)
- Data loss risks (destructive operations without guard, broken transactions)

**MEDIUM severity:**
- Performance issues (N+1 queries, unnecessary re-renders, blocking I/O in async context)
- Error handling gaps (uncaught exceptions on expected failure paths)
- Broken or missing tests for changed logic

**LOW severity:**
- Dead code, unused imports, leftover debug statements
- Readability and naming
- Simplifications (repeated logic, overly complex expressions)

For each issue record: file path, line number, severity, one-sentence title, explanation, and a concrete fix as a unified diff.

---

## PHASE 3 — REPORT

Print the full report before doing anything interactive:

```
# Pre-PR Review — <branch name>

## Summary
<2-3 sentence high-level assessment>

## Issues Found: <N total> (<H> HIGH, <M> MEDIUM, <L> LOW)
```

Then for each issue (HIGH → MEDIUM → LOW):

```
### [<SEVERITY>] <file>:L<line> — <title>
<explanation>

Proposed fix:
```diff
- old line(s)
+ new line(s)
```
```

After the full report, tell the user:
> "I'll walk through each issue one at a time. Reply: **approve** to apply the fix, **edit: <description>** to modify it first, **skip** to leave it alone, or **done** to stop and commit what's been approved."

---

## PHASE 4 — INTERACTIVE FIX LOOP

Go issue by issue, HIGH → MEDIUM → LOW. For each:

1. Print: `Issue <N>/<total>: [<SEVERITY>] <file>:L<line> — <title>` plus the compact fix diff.
2. Wait for the user's reply.
3. Act on reply:
   - **approve** → apply the fix with the Edit tool, confirm "Applied ✓"
   - **edit: ...** → interpret the change, show the revised fix, ask "Apply this? (yes/no)", then apply if yes
   - **skip** → confirm "Skipped ↷", move on
   - **done** → exit the loop immediately, go to Phase 5

---

## PHASE 5 — POST PR COMMENTS (if PR exists)

If a PR was detected, post a `gh pr comment` for every issue (approved or skipped):

```
[<SEVERITY>] <file>:L<line> — <title>

<explanation>

<"Fix applied in this branch." if approved, or "Not yet fixed — flagged for awareness." if skipped>
```

Then post a summary comment:
```
## Pre-PR Review Summary
- Issues reviewed: <N>
- Fixes applied: <count>
- Skipped: <count>

Review run by Claude Code on branch `<branch>`.
```

If no PR exists, tell the user to open one and re-run `/pre-pr-review` to post comments.

---

## PHASE 6 — COMMIT

If any fixes were applied:
1. Run `git diff --stat` and show the user what changed.
2. Ask: "Commit these fixes? Reply **yes**, **no**, or a custom commit message."
3. Stage the changed files and commit. Never use `git push`.

If no fixes were applied, tell the user there is nothing to commit.

---

## RULES
- Never apply a fix without explicit user approval in Phase 4.
- Never commit without explicit user approval in Phase 6.
- Never run `git push`.
- Keep Phase 4 tight — one issue per message, no walls of text.
