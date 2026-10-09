---
name: import
description: Import Codex conversations into Claude Code so they open with /resume. Shows what will be imported and asks before writing. Use for "import my Codex sessions/chats/history" or "move from Codex".
argument-hint: "[all | this project | <conversation-id>...]"
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/codex2claude":*)
---
# Import Codex conversations

The tool is `sh "${CLAUDE_PLUGIN_ROOT}/bin/codex2claude"`, shortened to `codex2claude` below. It reads `~/.codex` and writes Claude Code transcripts itself. Only its short output reaches you, so never read the conversations or rollout files directly.

Current state:
!`sh "${CLAUDE_PLUGIN_ROOT}/bin/codex2claude" --list --data "${CLAUDE_PLUGIN_DATA}"`

1. **Choose what to import**, from the arguments ("$ARGUMENTS") or by asking the user. Use the list above:
   - `all` → `--all`
   - `this project` → `--all --cwd "<current working dir>"`
   - conversation ids → pass the ids
2. **Mention these options only if they fit what the user wants.** All are off by default:
   - `--context` keeps what Codex added to each conversation: AGENTS.md, environment info, and permission instructions. They're labeled `[codex context]`.
   - `--reasoning` keeps Codex's plain-text reasoning summaries. Full reasoning is encrypted by OpenAI and can't be imported.
   - `--out-chars N` sets how many characters of each tool output to keep. The default is 400, and `0` keeps everything, which makes conversations about 4 times bigger.
   - `--subagents` includes Codex's own sub-agent threads (Guardian reviews, spawned workers).
3. **Dry run.** Run the command with `--dry-run` and show the counts. Point out any conversation over about 150k tokens: it needs `/compact` right after opening, or a smaller `--out-chars`.
4. **Import.** When the user confirms, run it without `--dry-run`. Report how many were imported, and how many were skipped and why:
   - **no conversation text**: the thread was empty.
   - **continued in Claude**: never overwritten.
5. **Tell them how to open the conversations.** Imported ones are titled `[Codex] <title>`.
   - **Claude desktop app:** they appear in the sidebar under their project folder after the app restarts. If the output says "Restart the Claude app", repeat that: the app only reads its session list when it starts.
   - **Terminal (CLI):** run `/resume` in that project folder, or `claude --resume`.
   - Running the same import again updates conversations rather than duplicating them. A conversation the user deleted in Claude is never brought back.
   - Suggest `/codex2claude:sync on` to keep them in sync automatically.

If the output says Python is missing, tell the user to install Python 3.8 or newer. To move Codex skills, AGENTS.md or MCP servers, point to `/codex2claude:setup`. For memory, point to `/codex2claude:memory`.
