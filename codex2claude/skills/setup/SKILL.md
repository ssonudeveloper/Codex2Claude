---
name: setup
description: Move your Codex setup to Claude Code: skills, AGENTS.md instructions and MCP servers. Asks before each change. Use for "migrate my Codex setup/skills/MCP servers".
---
# Move Codex setup to Claude Code

Look at what exists, show the user a short checklist of what can move, and make each change only after they approve it. Never do anything silently.

## Skills

Codex skills in `~/.codex/skills/*/SKILL.md` use the same format as Claude skills. Offer to copy each folder that doesn't already exist in `~/.claude/skills/`. Skip `.system`, and skip any skill that relies on Codex-only tools (check its body for things like `imagegen`).

## AGENTS.md

Claude Code already reads a project's AGENTS.md by itself whenever the project has **no** CLAUDE.md. Only these cases need a change:
- **The project has both a CLAUDE.md and an AGENTS.md**, and the CLAUDE.md doesn't mention AGENTS.md: offer to add a line `@AGENTS.md` to the CLAUDE.md.
- **`~/.codex/AGENTS.md` isn't empty**: it holds global instructions. Offer to add `@~/.codex/AGENTS.md` to `~/.claude/CLAUDE.md`, creating that file if needed.

Both are imports rather than copies, so Codex and Claude keep reading the same file.

## MCP servers

Codex lists them in `~/.codex/config.toml`, one `[mcp_servers.<name>]` table each, with `command`, `args`, `env` or `url`. For each server:
1. **Skip Codex internals**: servers whose `command` points inside Codex's own install, for example `...\OpenAI\Codex\runtimes\...`.
2. **Show the matching command.** For a local server, use `claude mcp add --scope user <name> -e KEY=VALUE -- <command> <args...>`. For a remote one, use `claude mcp add --scope user --transport http <name> <url>`. When the args or env are complicated, use `claude mcp add-json --scope user <name> '<json>'` instead. `--scope user` makes the server available in every project.
3. **Run it only after the user approves.** Never print secret env values back to the user.

End with a short list of what was moved and what was skipped.
