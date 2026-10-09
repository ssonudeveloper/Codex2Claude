---
name: sync
description: Import Codex conversations that are new or changed since the last sync. Add "on" or "off" to turn automatic sync at every Claude Code start on or off.
argument-hint: "[on | off]"
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/codex2claude":*)
---
Run exactly one command, chosen by the arguments ("$ARGUMENTS"):
- no arguments: `sh "${CLAUDE_PLUGIN_ROOT}/bin/codex2claude" --sync --data "${CLAUDE_PLUGIN_DATA}"`
- `on`: `sh "${CLAUDE_PLUGIN_ROOT}/bin/codex2claude" --autosync on --data "${CLAUDE_PLUGIN_DATA}"`. This turns auto-sync on and also syncs straight away.
- `off`: `sh "${CLAUDE_PLUGIN_ROOT}/bin/codex2claude" --autosync off --data "${CLAUDE_PLUGIN_DATA}"`

Report the printed result in one or two sentences. Then add only what fits:
- The first sync imports every conversation. Later syncs only bring in new or changed ones.
- After `on`: each time Claude Code starts, it imports new and changed Codex conversations, and shows a one-line notice when it does. It runs as a plain script, with no AI and no token use.
- Imported conversations are titled `[Codex] <title>`. In the Claude desktop app, they appear in the sidebar under their project after the app restarts. In the terminal (CLI), they open from `/resume` in their project folder.
- A conversation the user continued in Claude is never overwritten, and one they deleted is never brought back.
- If the output says Python is missing, tell the user to install Python 3.8 or newer.
