---
description: Show available method-hoard commands and usage
allowed-tools: ["Bash(uv run:*)"]
---

Run `uv run ~/.method-hoard/hoard.py help` to get the command reference as JSON.

Present the output as a readable command reference. For each command, show:
- The slash command form: `/method-hoard:<name>`
- What it does (from the help text)
- Arguments if any

Format as a clean table or list. No agent fork needed.
