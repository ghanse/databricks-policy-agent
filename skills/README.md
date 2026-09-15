# Policy Agent skills

Claude Code skills that teach an agent how to work with the Policy Agent. They ship as a plugin
named **`policy-agent`** (manifest at [`.claude-plugin/plugin.json`](../.claude-plugin/plugin.json)),
with one skill per workflow:

| Skill | Invoke as | Covers |
| --- | --- | --- |
| [`author/`](author/SKILL.md) | `/policy-agent:author` | Policy schema, condition operators, every resource type and its attributes, the Python DSL, and validation. |
| [`scan/`](scan/SKILL.md) | `/policy-agent:scan` | Running scans from the CLI and library, `POLICY_AGENT_*` configuration, and reading findings. |
| [`enforce/`](enforce/SKILL.md) | `/policy-agent:enforce` | Gating a Databricks Asset Bundle before deploy: thresholds, overrides, and fix suggestions. |

All content (resource attributes, operators, CLI flags, `POLICY_AGENT_*` env vars) is derived from
the library, so it stays accurate.

## Using the skills

Install the plugin so Claude Code loads the skills on demand. The plugin root is the repository root
(where `.claude-plugin/plugin.json` lives); its `skills` field points here at `./skills/`.

- **From this repo, as a marketplace/plugin:** add the repo as a plugin source in Claude Code and
  enable the `policy-agent` plugin (see the Claude Code plugin docs), then invoke `/policy-agent:author`,
  `/policy-agent:scan`, or `/policy-agent:enforce`.
- **Standalone:** copy any skill directory into a Claude Code skills location:

  ```bash
  cp -r skills/author ~/.claude/skills/policy-agent-author       # user scope
  cp -r skills/scan   <project>/.claude/skills/policy-agent-scan  # project scope
  ```

Claude Code reads each `SKILL.md` frontmatter to decide when a skill is relevant and pulls in its
body as needed.
