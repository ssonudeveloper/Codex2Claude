---
name: list
description: List your Codex conversations and whether each one is in Claude yet. Also shows whether auto-sync is on and the result of the last sync.
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/codex2claude":*)
---
!`sh "${CLAUDE_PLUGIN_ROOT}/bin/codex2claude" --list --data "${CLAUDE_PLUGIN_DATA}"`

Show the user the output above, laid out compactly:
1. The auto-sync line and the totals.
2. One short table per project folder: title, status and id. Keep the ids, because they're needed to import a single conversation.

Don't run anything else. If the output says Python is missing, tell the user to install Python 3.8 or newer.

What each status means:
- **new**: not imported yet.
- **in Claude**: imported and up to date.
- **changed in Codex**: continued in Codex after it was imported. `/codex2claude:sync` brings in the new messages.
- **continued in Claude**: continued in Claude, so changes from Codex are no longer applied to it.

Suggest next steps only if they fit: `/codex2claude:import` when there are new conversations, and `/codex2claude:sync on` to keep them in sync automatically.
