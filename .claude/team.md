# ivrit_agent — Team Roster

This file is the live roster of agent nicknames and their official roles. The Orchestrator and the Planner read it at sprint start. Edit it via `python .claude/scripts/team_setup.py --rename old=new` (do not hand-edit unless you know what you're doing).

## Roster

- **@planner** — planner: Breaks sprint goals into structured plans with per-task assignments.
- **@reviewer** — reviewer: Independent QA gate; verifies completed work against acceptance criteria.
- **@researcher** — researcher: Reads resources and external sources; synthesizes findings.
- **@architect** — architect: Owns system design, tech stack, and module boundaries.
- **@implementer** — implementer: Generic builder; default executor for code tasks.
- **@backend** — backend-specialist: APIs, services, data layer, server-side logic.
- **@frontend** — frontend-specialist: UI/UX implementation; components, styling, client state.
- **@qa** — qa-engineer: Test design and execution; behavioral validation.
- **@devops** — devops: CI/CD, deployment, infrastructure, build pipelines.
- **@documenter** — documenter: READMEs, API docs, user guides, changelog.
- **@ml** — data-ml-engineer: Data pipelines and ML model code paths.
- **@security** — security-reviewer: Audits code for security risks.

## Conventions

- Reference teammates by nickname only (e.g., `@nickname`). Never use the role name in `plan.md` assignments.
- Nicknames are unique across the team.
- The Orchestrator is the main Claude session reading `CLAUDE.md`; it is not listed here because it isn't dispatchable.
