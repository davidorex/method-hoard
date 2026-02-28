# method-hoard

A Claude Code plugin for discovering, stocking, searching, and retrieving generalizable methods with working code across all projects. Enacts Simon Willison's ["hoard things you know how to do"](https://simonwillison.net/guides/agentic-engineering-patterns/hoard-things-you-know-how-to-do/) insight.

It's designed to support persistence of valuable methods and make them easily discoverable by coding agents.

## Mental model

The blog post focuses on the idea that the valuable unit is a proven method — "here's how you do X," along with working code that demonstrates it. The "method hoard" here is a global store (`~/.method-hoard/`) of markdown files with YAML frontmatter, indexed by SQLite FTS5 for search. Any project can contribute to and draw from the hoard.

The system is self-bootstrapping: the discover heuristic (what makes a method hoard-worthy, how to extract and describe methods, calibration signals) is itself hoard item zero, stored and revisable the same way.

## Commands

Four slash commands, each forking to a subagent to preserve main context:

- `/method-hoard:discover` — Opus agent actively reflects on recent work, applies the heuristic from item 0, surfaces candidates for the user to evaluate
- `/method-hoard:stock` — Sonnet agent takes method details and writes to the global store
- `/method-hoard:search` — Sonnet agent queries FTS5 index, presents results with snippets
- `/method-hoard:get` — Sonnet agent retrieves a specific method by id or slug

## Storage

Each method is a markdown file with YAML frontmatter in `~/.method-hoard/methods/`. A SQLite FTS5 index (`~/.method-hoard/index.db`) is derived from the files and rebuildable via `reindex`.

## Python CLI

`scripts/hoard.py` handles all storage operations: init, stock, search, get, heuristic, list, update, reindex. Uses `uv run` with PEP 723 inline script metadata (a pattern due to Simon Willison). All subcommands output JSON for agent consumption.

## Seed

`seed/000-discover-heuristic.md` provides heuristic zero — seeded into `~/.method-hoard/methods/` on first init. Contains stock/don't-stock criteria, method extraction patterns, and calibration signals for adjusting the bar over time.

## Installation

See Anthropic's documentation on [installing Claude Code plugins](https://code.claude.com/docs/en/discover-plugins).

For local development and testing: `claude --plugin-dir /path/to/method-store`

Once installed: `/method-hoard:discover`, `/method-hoard:search <query>`, `/method-hoard:get <slug>`, `/method-hoard:stock`.
