---
description: List all methods in the hoard with their metadata
allowed-tools: ["Bash(uv run:*)"]
---

Use the Agent tool to launch the `method-hoard:list` agent with model `opus`. Pass `$ARGUMENTS` if any filtering is desired.

When the agent returns, present the methods as a readable table (id, slug, title, tags, retrievals). Then show available actions the user can take on any item:

- `/method-hoard:get <slug>` — see the full method with working code
- `/method-hoard:search <query>` — find related methods
- `/method-hoard:discover` — look for new methods to add
