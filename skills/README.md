# Agent skills

Claude Code skills that teach an agent how to work with the Policy Agent — authoring and
validating policies, running compliance scans, and gating bundle deployments. The skill content
is derived from the library itself, so resource attributes, operators, CLI flags, and env vars
match the code.

## Contents

- **[databricks-policy-agent/](databricks-policy-agent/)** — the skill:
  - `SKILL.md` — overview, the three CLI verbs, and a policy at a glance.
  - `authoring.md` — policy schema, condition operators, every resource type and its attributes,
    and the Python DSL.
  - `scanning.md` — running scans from the CLI and library, `POLICY_AGENT_*` configuration, and
    reading findings.
  - `enforcement.md` — bundle gating: thresholds, overrides, and fix suggestions.

## Using the skill

Drop the `databricks-policy-agent/` directory into a Claude Code skills location so the agent can
load it on demand:

```bash
# User scope (available in every project):
cp -r skills/databricks-policy-agent ~/.claude/skills/

# Project scope (checked in with a repo that consumes the Policy Agent):
cp -r skills/databricks-policy-agent <project>/.claude/skills/
```

Claude Code reads the `SKILL.md` frontmatter to decide when the skill is relevant and pulls in the
reference files as needed. The skill can also be packaged into a Claude Code plugin — see the
plugin docs for the marketplace layout.
