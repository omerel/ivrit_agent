"""Generate a self-contained sprint-board.html for the active sprint."""
import argparse
import json
import re
import sys
import webbrowser
from pathlib import Path
from typing import Optional


_TASK_RE = re.compile(
    r"^-\s+\[[ xX]\]\s+\*\*(?P<id>T\d+)\*\*\s+"
    r"\[(?P<status>pending|in_progress|done|blocked)\]\s+"
    r"@(?P<assignee>[a-z][a-z0-9-]*)\s+"
    r"(?:—|--|-)\s+(?P<desc>.+?)\s*$"
)

_SUB_RE = re.compile(
    r"^\s+-\s+(?P<key>Acceptance|Notes)\s*:\s*(?P<val>.+?)\s*$",
    re.IGNORECASE,
)

_ROSTER_RE = re.compile(
    r"^-\s+\*\*@(?P<nick>[a-z][a-z0-9-]*)\*\*\s+(?:—|--|-)\s+(?P<role>[a-z0-9-]+)\s*:",
    re.MULTILINE,
)


def _extract_tasks_section(text: str) -> str:
    m = re.search(r"^##\s+Tasks\s*$", text, re.MULTILINE)
    if not m:
        return ""
    start = m.end()
    nxt = re.search(r"^##\s+", text[start:], re.MULTILINE)
    return text[start: start + nxt.start()] if nxt else text[start:]


def parse_plan(text: str) -> dict:
    """Parse a plan.md into {goal, started, tasks}."""
    goal_m = re.search(r"^#\s+Sprint:\s+(.+?)\s*$", text, re.MULTILINE)
    started_m = re.search(r"^\*\*Started:\*\*\s+(\S+)\s*$", text, re.MULTILINE)

    tasks = []
    section = _extract_tasks_section(text)
    current = None
    for line in section.splitlines():
        m = _TASK_RE.match(line)
        if m:
            current = {
                "id": m.group("id"),
                "status": m.group("status"),
                "assignee": m.group("assignee"),
                "desc": m.group("desc").strip(),
                "acceptance": None,
                "notes": None,
            }
            tasks.append(current)
            continue
        if current is None:
            continue
        sub = _SUB_RE.match(line)
        if sub:
            current[sub.group("key").lower()] = sub.group("val").strip()

    return {
        "goal": goal_m.group(1) if goal_m else "",
        "started": started_m.group(1) if started_m else "",
        "tasks": tasks,
    }


def parse_team(text: str) -> dict:
    """Parse .claude/team.md into {nickname: role}."""
    return {m.group("nick"): m.group("role") for m in _ROSTER_RE.finditer(text)}


_TEMPLATE_PATH = Path(__file__).resolve().parent / "sprint-board.template.html"
_SENTINEL = "/*__SPRINT_DATA__*/ null"


def render_html(sprint: dict) -> str:
    """Embed `sprint` as JSON into the HTML template and return the document."""
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    if _SENTINEL not in template:
        raise RuntimeError(
            f"template missing sentinel; expected {_SENTINEL!r} in {_TEMPLATE_PATH}"
        )
    payload = json.dumps(sprint, ensure_ascii=False)
    payload = payload.replace("</", "<\\/")
    return template.replace(_SENTINEL, payload, 1)


def _project_name(project: Path) -> str:
    claude_md = project / "CLAUDE.md"
    if claude_md.is_file():
        m = re.match(r"^#\s+(.+?)\s+—", claude_md.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return project.name


def load_sprint(project: Path) -> dict:
    """Build the sprint dict from disk; tolerate missing/dangling .active."""
    project = Path(project)
    team = {}
    team_md = project / ".claude" / "team.md"
    if team_md.is_file():
        team = parse_team(team_md.read_text(encoding="utf-8"))

    base = {
        "project_name": _project_name(project),
        "folder": None,
        "goal": None,
        "started": None,
        "team": team,
        "tasks": [],
    }

    active = project / "sprints" / ".active"
    if not active.is_file():
        return base
    folder = active.read_text(encoding="utf-8").strip()
    if not folder:
        return base
    plan_path = project / "sprints" / folder / "plan.md"
    if not plan_path.is_file():
        return base

    parsed = parse_plan(plan_path.read_text(encoding="utf-8"))
    base.update({
        "folder": folder,
        "goal": parsed["goal"],
        "started": parsed["started"],
        "tasks": parsed["tasks"],
    })
    return base


def _find_project(start: Path) -> Optional[Path]:
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".claude" / "team.md").is_file():
            return candidate
    return None


def main(argv=None, project: Optional[Path] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="board.py",
        description="Generate a self-contained sprint-board.html for the active sprint.",
    )
    parser.add_argument("--no-open", action="store_true",
                        help="Do not open the result in a browser.")
    parser.add_argument("--out", default="sprint-board.html",
                        help="Output filename, relative to the project root.")
    args = parser.parse_args(argv)

    if project is not None:
        root = Path(project)
    else:
        root = _find_project(Path.cwd()) or _find_project(Path(__file__))
    if root is None or not (root / ".claude" / "team.md").is_file():
        sys.stderr.write(
            "error: not a team-ai project (no .claude/team.md found)\n"
        )
        return 1

    sprint = load_sprint(root)
    out_path = root / args.out
    out_path.write_text(render_html(sprint), encoding="utf-8")
    print(f"✓ Wrote {out_path}")
    if not args.no_open:
        webbrowser.open(out_path.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
