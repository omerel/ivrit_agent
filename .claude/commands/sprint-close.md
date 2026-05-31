---
description: Close the active sprint after Reviewer signs off
---

Close the active sprint.

Steps:
1. Read `sprints/.active`. If missing, say "No active sprint." and stop.
2. Read `sprints/<active>/plan.md`. If any task is `pending` or `in_progress`, refuse and list the unfinished tasks. The guide can pass `--force` to close anyway.
3. Dispatch the **reviewer** subagent with this prompt:
   - "Validate sprints/<active>/plan.md against acceptance criteria for each task. Read each task's relevant work-log entries and the files referenced. Write the Sprint Closeout section at the bottom of plan.md with STATUS: PASS or STATUS: FAIL plus per-task notes. Return when written."
4. After reviewer returns, read the Sprint Closeout:
   - If PASS: delete `sprints/.active` and tell the guide the sprint is closed.
     Then report the current sprint branch name (`sprint/<slug>`) and suggest next
     steps — merge, open a PR, or keep the branch. **Do not merge automatically.**
     The guide may invoke the `finishing-a-development-branch` skill to decide.
   - If FAIL: keep `sprints/.active`, summarize what failed, and ask the guide whether to dispatch fixes or accept the close anyway.
