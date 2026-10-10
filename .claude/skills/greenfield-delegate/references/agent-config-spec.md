# Claude Code Subagent Config — Spec Summary & Our Choices

Load this file when you edit `.claude/agents/*.md` or debug why a subagent misbehaves.

Source: Anthropic, *Create custom subagents*, <https://code.claude.com/docs/en/sub-agents>, read on 2026-10-31. Sections cited: Frontmatter reference, Subagent files Claude Code skips, Choose the subagent scope, Choose a model, Available tools, Restrict which tools, Scope MCP servers, Permission modes, Preload skills, Hooks for subagents, Foreground/background, Resume subagents, What loads at startup. Supporting evidence: `anthropics/claude-code` `CHANGELOG.md` (hook payloads gained `agent_id` / `agent_type`; `disallowedTools`; the `skills` preload cap of 32). The lint `scripts/lint-agents.py` enforces the mechanical parts.

## 1. File format and discovery

- **The file:** one Markdown file per agent. YAML frontmatter between `---` lines, with the opening `---` on line 1, then a Markdown body that **is the whole system prompt**. The subagent gets this body plus environment details, not the Claude Code system prompt.
- **Required fields:** only `name` and `description`.
  - `name`: ≤ 256 characters, must not start with `-`, must not contain `:` (reserved for plugin scope). Hooks receive it as `agent_type`.
  - The filename does not have to match the name.
- **Files Claude Code skips silently** (with a note in the debug log):
  - no `name` (treated as documentation);
  - the `---` is not on line 1;
  - a bad `name`;
  - a `name` without a `description`;
  - YAML that doesn't parse.
- **Unknown fields are silently ignored.** Fields are camelCase (`maxTurns`, `disallowedTools`). This is why `lint-agents.py` treats an unknown field as an ERROR.
- **Where agents live, by priority:**
  1. managed settings;
  2. the `--agents` JSON flag;
  3. project `.claude/agents/`;
  4. user `~/.claude/agents/`;
  5. plugin `agents/`.

  Directories are scanned recursively. Duplicate names in one tree load in undefined order. Edits are hot-reloaded; restart only after creating the **first** file in a new `agents/` directory, or for `--add-dir` directories.
- **Creating agents:** ask Claude to write the file, or write it by hand. Since v2.1.198, `/agents` only prints that reminder; the interactive wizard existed in v2.1.197 and earlier.
- **Invoking an agent:**
  - automatic delegation, via the `description` (phrases like "use proactively" encourage it);
  - natural language ("use the gf-planner subagent …");
  - `@agent-<name>` or `@"<name> (agent)"`;
  - session-wide with `claude --agent <name>` or the `agent` setting.
- **Budget:** combined custom-agent descriptions over **15,000 tokens** trigger a startup warning. Keep descriptions short and trigger-focused, and put detail in the body, which loads only when the agent runs.

## 2. Fields (all optional except `name` and `description`)

| Field | Values | Notes that matter here |
| --- | --- | --- |
| `tools` | comma string or YAML list | Allowlist. Omitted = inherit everything available to subagents. MCP tools need `mcp__<server>__*`. An all-unresolved list = launch failure. |
| `disallowedTools` | same | Denylist, applied before `tools`. A `Bash(git push *)` entry removes **all** Bash. |
| `model` | `sonnet` · `opus` · `haiku` · `fable` · full `claude-*` ID · `inherit` | Order: per-call parameter → frontmatter → `CLAUDE_CODE_SUBAGENT_MODEL` → main model. A family alias resolves to the main model when the main model is in that family. |
| `permissionMode` | `default` (`manual`) · `acceptEdits` · `auto` · `dontAsk` · `bypassPermissions` · `plan` | Applied only when the main session is in `default` / `dontAsk`. The main session's `auto`, `acceptEdits`, `bypassPermissions` or `plan` takes over. Ignored for plugin agents. |
| `maxTurns` | integer | On hitting the cap the output is marked partial and the agent can be resumed. |
| `autoCompactWindow` | 100000–1000000 | Per-agent auto-compact window. |
| `skills` | list | **Full content** of each skill is injected at start (first 32 distinct). Missing or disabled skills are skipped with a debug-log warning. Skills with `disable-model-invocation: true` **cannot** be preloaded. Unlisted skills stay invocable via the `Skill` tool. |
| `mcpServers` | list of names or inline defs (`.mcp.json` schema) | Inline servers connect when the agent starts and disconnect when it ends, and **don't appear in the main conversation**. Project-agent inline servers need the folder to be trusted. Ignored for plugin agents. |
| `hooks` | hooks block | Runs only while this agent is active; `Stop` becomes `SubagentStop`. Needs workspace trust for project agents. Settings-level hooks fire inside subagents too. |
| `memory` | `user` · `project` · `local` | Persistent per-agent directory; auto-enables Read/Write/Edit. |
| `background` | bool | Always background. Spawns from the main conversation already default to background. |
| `omitClaudeMd` | bool | Start without the CLAUDE.md files. |
| `effort` | `low` · `medium` · `high` · `xhigh` · `max` | Overrides the session effort (not `CLAUDE_CODE_EFFORT_LEVEL`). Available levels depend on the model. |
| `isolation` | `worktree` | Temporary git worktree, branched from the **default branch**, not `HEAD`. |
| `color` | `red` · `blue` · `green` · `yellow` · `purple` · `orange` · `pink` · `cyan` | Display colour only. |
| `initialPrompt` | string | Only used when the agent runs as the main session (`--agent`). |
| `experimental` | map (`cacheTtl: 5m\|1h`) | Prompt-cache lifetime. |

## 3. Runtime facts the pipeline depends on

- **No `AskUserQuestion` in subagents.** It is removed from every subagent, along with `EnterPlanMode`, `ScheduleWakeup` and others, even when listed. Hence contract rule 4: subagents return questions, and the main thread asks them.
- **Background tool set.** Background subagents (the default) keep every MCP tool plus `Read`, `Grep`, `Glob`, `LSP`, `Bash`, `PowerShell`, `Edit`, `Write`, `NotebookEdit`, `WebFetch`, `WebSearch`, `TodoWrite`, `Skill`, `ToolSearch`, worktree tools, `Monitor`, `TaskStop`, `SendMessage` and `Artifact`. Our `tools:` lists use only these.
- **Permission prompts** from a background subagent surface in the main session and name the agent. A session-wide grant applies to the main conversation too.
- **Fork mode** is on by default in interactive sessions. A fork inherits the whole conversation, which defeats the pipeline. Setting `CLAUDE_CODE_FORK_SUBAGENT=0` (in `.claude/settings.json` `env`) is the documented way to let Claude wait for a named subagent. `install-agent-skills.sh` sets it, and `--check` requires it.
- **Resume:** each spawn is a new instance. `SendMessage` to the returned agent ID resumes it with its full history. The planner gate loop relies on this.
- **What a subagent loads at start:** its body; the task message; the CLAUDE.md hierarchy (unless `omitClaudeMd`); a git status snapshot; its preloaded skills. It does **not** get the main conversation's history, output style or auto memory.
- **Hook payloads** carry `agent_id` (subagents only) and `agent_type`, which equals the agent's `name`. `main-thread-code-guard.sh` keys on both.

## 4. Why our three agents are configured the way they are

| Setting | gf-planner | gf-implementer | gf-reviewer | Reason |
| --- | --- | --- | --- | --- |
| `tools` | read + Bash + Write/Edit (plan file) + Skill + `mcp__gitnexus__*` | + NotebookEdit | read + Bash + Write (review file) + Skill + `mcp__gitnexus__*` (no Edit) | Allowlist excludes `Agent`, so no nested spawns and a predictable depth of 1. The code-path limits for planner and reviewer are enforced by the settings-level guard hook, which fires inside subagents. |
| `model` | `opus` | `inherit` | `opus` | modularity's README recommends Opus 4.5+ for its architectural reasoning. The implementer follows the session's choice of cost and quality. |
| `effort` | `high` | (session) | `high` | Planning and review are the judgement-heavy stages. |
| `permissionMode` | (inherit) | `acceptEdits` | (inherit) | Cuts edit prompts during long implementations. Bash still prompts unless the user's settings allow it. |
| `maxTurns` | 80 | 200 | 80 | Stops runaway loops. A partial result can be resumed. |
| `skills` | GitNexus + `modularity:design` / `balanced-coupling` + **all three** backend ECC pattern packs + `react-patterns` + `coding-standards` + `greenfield-spec-and-plan` + `greenfield-implement` | `greenfield-implement` / `-verify` + all ECC pattern and testing packs incl. `react-patterns` / `react-testing` + `coding-standards` + GitNexus | `modularity:review` / `balanced-coupling` / `document` + all ECC pattern packs incl. `react-patterns` + `coding-standards` + GitNexus + `greenfield-implement` | Only the chosen language's ECC pack, plus the React pack when `frontend=react`, is vendored. Absent skills are skipped, so one static file serves every language/frontend mix with no templating. Per-language agent types were rejected: nothing in the spec varies by language, and 9 near-identical descriptions would triple the description budget and confuse auto-delegation. |
| `mcpServers` | inline `gitnexus@<pin>` | same | same | GitNexus tool descriptions stay out of the main thread. The installer re-pins the version and the lint checks it against the lock. |
| `color` | blue | green | purple | Lets you tell the three apart at a glance in `/tasks`. |
| not used | `memory`, `isolation`, `background`, `omitClaudeMd`, `hooks` | | | `memory` would add files and context per agent (opt in later if review findings recur). `isolation: worktree` branches from the default branch, not the working branch. `omitClaudeMd` would drop the §4 invariants the agents must obey. |
