---
description: Resume the active or most-recent sprint
---

Resume work on the most recent or active sprint.

Steps:
1. Read `sprints/.active`. If missing, find the most recent `sprints/<YYYY-MM-DD>_<slug>/` folder by mtime.
2. Read its `plan.md` and the latest entry in each work-log under `work-logs/`.
3. Summarize for the guide:
   - Sprint folder + goal
   - Task counts by status
   - The current in_progress task (if any) and its assignee
   - The last activity (most recent work-log entry timestamp + summary)
4. Ask: "Resume this sprint? (yes / start a fresh sprint instead / something else)". Wait for the guide's answer before doing anything.
