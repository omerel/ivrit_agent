---
name: using-git
description: Use when committing your work, attributing a commit to yourself, or working on a sprint or quick-fix branch — defines the team's commit-attribution and clean-commit rules.
---

# Using Git

You are a teammate committing to the guide's shared git history. Because every
commit lands on the guide's git identity, your commits MUST be attributed to you.

## Attribution (required)

Every commit subject MUST start with your nickname followed by `: `.

```
@<your-nickname>: <imperative summary>
```

Example: `@rocky: fix pagination off-by-one`. You know your nickname from your
own agent prompt. Never commit without this prefix.

## Clean commits

- One focused change per commit. Do not stage unrelated files.
- Imperative subject line ("add", "fix", "rename"), not past tense.
- Run `git status` and `git diff --staged` before committing to confirm exactly
  what you are about to record.

## Branch awareness

- Check the current branch (`git status`) before committing. Sprint work belongs
  on the active `sprint/<slug>` branch — do NOT switch branches unless your task
  explicitly tells you to.
- A `/quick-fix` commits on whatever branch is currently checked out.

## Safety

- Never force-push and never rewrite published history unless the guide
  explicitly asks for it.
