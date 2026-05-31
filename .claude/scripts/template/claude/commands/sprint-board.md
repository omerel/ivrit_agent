---
description: Render and open the active sprint as an offline kanban board
---

Generate `sprint-board.html` from the active sprint and open it in the user's browser.

Steps:
1. Run `python3 .claude/scripts/board.py` from the project root.
2. Surface the script's output (it prints the path it wrote and opens the browser).
3. If the run fails because there is no team-ai project at the cwd, tell the guide which directory to run from.

The board reads `sprints/.active` and the matching `plan.md`. If there is no active sprint, the board still renders with an empty state.
