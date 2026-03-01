# method-hoard

Claude Code plugin for discovering, stocking, searching, and retrieving generalizable methods with working code. Enacts Simon Willison's "hoard things you know how to do" insight.

## Architecture Gotchas

- IMPORTANT: `${CLAUDE_PLUGIN_ROOT}` does NOT resolve in agent Bash calls — only in hooks/MCP configs. All agents use `~/.method-hoard/hoard.py` (a symlink created by `init`).
- IMPORTANT: `disable-model-invocation: true` in skill frontmatter blocks the Skill tool entirely. It is intentionally absent from all skills.
- IMPORTANT: Never run `hoard.py` directly from main context. Always invoke through the plugin system (skills → agents).
- All agents run as opus. Haiku was tested and failed to follow agent instructions reliably.
- Markdown files in `~/.method-hoard/methods/` are the source of truth. The SQLite FTS5 index is derived and rebuildable via `reindex`.
- Item 0 (`000-discover-heuristic.md`) is protected from deletion at the CLI level.

## Skill Design Pattern

Skills are thin launchers that fork to agents to preserve main context. Skills serve dual duty: agent launch instruction AND return-handling script.

- Discover skill: main context must present AskUserQuestion (Stock/Discuss/Skip) after agent returns
- List skill: main context must show actionable follow-up commands after agent returns
- Search/Get/Stock skills: fire-and-forget — agent output speaks for itself

## CLI Conventions

- All `hoard.py` subcommands output JSON for agent consumption
- `stock` and `update` read JSON from stdin (pipe), not CLI args for the method body
- `init` is idempotent — agents should always call it first
- Stock agent must call `tags` before stocking to promote tag convergence
- Subcommands: init, stock, search (--tag), get, heuristic, list, tags, update, delete, reindex

## File Structure

- `scripts/hoard.py` — Python CLI; symlinked to `~/.method-hoard/hoard.py` on init
- `seed/000-discover-heuristic.md` — heuristic zero; seeded into `~/.method-hoard/methods/` on init
- `agents/*.md` — agent prompts with YAML frontmatter (name, model, tools)
- `skills/*/SKILL.md` — skill launchers with frontmatter (description, allowed-tools)

## Testing

Local development: `claude --plugin-dir /Users/david/Projects/method-store`
