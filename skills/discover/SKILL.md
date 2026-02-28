---
description: Actively reflect on recent work to discover generalizable methods worth hoarding
---

Use the Agent tool to launch the `method-hoard:discover` agent with model `opus`. Pass `$ARGUMENTS` as context for what to reflect on (file paths, topic, "diff", or empty for broad reflection).

When the agent returns with candidates, present each candidate to the user via AskUserQuestion. For each candidate, offer three options:

- **Stock** — proceed to run `/method-hoard:stock` with the candidate details
- **Discuss** — the user wants to refine or talk through the candidate before deciding
- **Skip** — don't stock this one

Then act on the user's choices: invoke `/method-hoard:stock` for each "Stock" selection, discuss any "Discuss" selections, and move on past any "Skip" selections.
