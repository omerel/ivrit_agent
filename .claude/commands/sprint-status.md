---
description: Print current sprint progress
---

Print the current sprint status.

Steps:
1. Read `sprints/.active`. If missing, say "No active sprint. Run /sprint-start <goal>." and stop.
2. Read `sprints/<active>/plan.md`.
3. Print:
   - Sprint folder name
   - Sprint goal (from plan.md header)
   - Task counts by status: pending / in_progress / done / blocked
   - The current `in_progress` task (if any), including its assignee
   - Any tasks with status `blocked`, including the reason
   - The last 3 entries from each work-log under `sprints/<active>/work-logs/` (most recent first)
