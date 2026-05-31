---
description: Make a small, documented fix without a full sprint
argument-hint: "\"<description>\" [@nickname]"
---

Make a quick fix: $ARGUMENTS

A quick-fix is lighter than a sprint: no planner, no reviewer, no branch, no
approval gates. One agent makes the change, records it, and commits.

Steps:
1. Parse `$ARGUMENTS` into a `<description>` (quoted) and an optional `@nickname`.
2. Read `.claude/team.md` for the valid nicknames. Resolve the assignee:
   - If an `@nickname` was given, validate it against `team.md`. If it is not a
     valid nickname, refuse and list the valid nicknames from `team.md`. Stop.
   - Else default to the `implementer` nickname **if installed**.
   - Else (no `@nickname` and no `implementer`): refuse and ask the guide to name
     an assignee, listing the valid nicknames from `team.md`. Stop.
3. Generate a slug from the description: lowercase, `[a-z0-9-]` only, max 40 chars
   (same rules as `/sprint-start`). If `fixes/<YYYY-MM-DD>_<slug>.md` already
   exists, append `-2`, `-3`, etc.
4. Dispatch the resolved agent (one subagent) with this prompt:
   - "Quick fix: <description>. Read CLAUDE.md, .claude/team.md, and any relevant
     resource/ and src/ files. Make the change. Invoke the `using-git` skill and
     commit on the **current branch** with subject `@<nickname>: <description>`.
     Then write `fixes/<YYYY-MM-DD>_<slug>.md` using the Quick Fix format in
     CLAUDE.md (by @<nickname>, change, result, commit SHA). Create `fixes/` if it
     does not exist. Return a one-paragraph summary with the commit SHA."
5. After the agent returns, report the fix summary and commit SHA to the guide.

Note: with an active sprint, the fix commits onto the current (sprint) branch by
design — quick-fix stays on whatever branch is checked out.
