<div align="center">

# codex2claude

**Bring your OpenAI Codex conversations into Claude Code.**
They appear in the sidebar under their project, open with their full history, and Claude continues them with all the context.

[![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-D97757?logo=anthropic&logoColor=white)](https://code.claude.com/docs/en/plugins)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![Dependencies: none](https://img.shields.io/badge/dependencies-none-2EA44F)](#requirements)
[![Runs locally](https://img.shields.io/badge/data-stays_on_your_machine-555555)](#privacy-and-safety)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

[Quick start](#quick-start) · [Commands](#commands) · [What gets imported](#what-gets-imported) · [FAQ](#troubleshooting)

</div>

---

## Why

Codex has a built-in setting that imports your history from other AI apps like Claude Code. Claude Code has nothing like it, so moving from Codex to Claude means starting from scratch.

**codex2claude** closes that gap:
- **Your Codex conversations become real Claude Code sessions,** listed by project.
- **Claude picks them up where Codex stopped,** with all the context.
- **A few other things can move too:** your Codex skills, AGENTS.md instructions, MCP servers and memories.

## Highlights

| | |
|---|---|
| 🗂️ **Shows up in the sidebar** | Imported conversations appear under their project folder in the Claude desktop app, titled `[Codex] <title>`. In the terminal, they're in `/resume`. |
| 🧩 **Looks native** | Each Codex message keeps its Markdown, and tool calls appear as collapsible tool cards, like in any Claude session. |
| 🔄 **Optional auto-sync** | New and changed Codex conversations can be imported every time Claude Code starts. This runs as a script, with no AI and no tokens. |
| 🪙 **Low token cost** | A script does the conversion, so the AI never reads your conversations during import. An import costs about 7k tokens in total. |
| 🛡️ **Safe to re-run** | Conversations you continued in Claude are never overwritten. Ones you deleted are never brought back. Nothing is duplicated. |
| 🧠 **Memory, if you want it** | It turns your Codex history into Claude memory, reusing the summaries Codex already wrote. It asks with a token estimate before reading any raw conversation. |
| 🧰 **Setup migration** | It moves Codex skills, AGENTS.md instructions and MCP servers across, asking before each change. |

## Quick start

**1. Install the plugin.** In Claude Code, run:

```text
/plugin marketplace add ssonudeveloper/codex2claude
/plugin install codex2claude@codex2claude
```

<details>
<summary>Or from a terminal</summary>

```bash
claude plugin marketplace add ssonudeveloper/codex2claude
```
```bash
claude plugin install codex2claude@codex2claude
```
</details>

<details>
<summary>Or in the Claude desktop app's settings</summary>

Open the app's plugin settings and, under **Plugin marketplaces**, choose **Add marketplace**. Enter `ssonudeveloper/codex2claude`, then install **codex2claude** from that marketplace.
</details>

**2. Start a new session.** codex2claude tells you once how many Codex conversations aren't in Claude yet:

```text
codex2claude: 52 Codex conversation(s) aren't in Claude Code yet. Run /codex2claude:import
to bring them in, or /codex2claude:sync on to keep them in sync.
```

**3. Import.** Choose one:

```text
/codex2claude:import            # see what's there, then pick (asks before writing)
/codex2claude:sync on           # import everything now and keep it in sync automatically
```

**4. Open them.**
- **Claude desktop app:** fully quit the app (from the system tray or menu bar) and reopen it. Your conversations are in the sidebar under their project, titled `[Codex] …`.
- **Terminal:** run `/resume` in the project folder.

> [!TIP]
> You can also just ask in plain language, for example *"import my Codex sessions for this project"*.

## Commands

Type `/codex2claude` in Claude Code to see them all, each with a short description.

| Command | What it does |
|---|---|
| `/codex2claude:list` | Shows your Codex conversations grouped by project, with the status of each, plus whether auto-sync is on and the result of the last sync. |
| `/codex2claude:import [all \| this project \| <id>…]` | Imports conversations. It shows a dry run with sizes first, and writes only after you confirm. |
| `/codex2claude:sync` | Imports conversations that are new, or changed in Codex, since the last sync. |
| `/codex2claude:sync on` \| `off` | Turns automatic sync at each Claude Code start on or off. `on` also syncs straight away. |
| `/codex2claude:memory [this project \| all]` | Turns your Codex history into Claude memory (decisions, preferences, gotchas). |
| `/codex2claude:setup` | Moves your Codex skills, AGENTS.md instructions and MCP servers to Claude Code. |

**What the statuses in `list` mean:**

| Status | Meaning |
|---|---|
| `new` | Not imported yet. |
| `in Claude` | Imported and up to date. |
| `changed in Codex` | You kept using it in Codex after importing. `sync` brings in the new messages. |
| `continued in Claude` | You kept chatting in Claude, so it's protected and Codex changes are no longer applied. |
| `deleted in Claude` | You deleted it in Claude, so it's never re-imported. |

### Import options

Mention these when you run `/codex2claude:import`, for example *"import this project with reasoning"*. All are off by default.

| Option | Effect |
|---|---|
| `--context` | Keeps what Codex added to each conversation behind the scenes: AGENTS.md instructions, environment info and permission notes. It's labeled `[codex context]`. |
| `--reasoning` | Keeps Codex's plain-text reasoning summaries. Full reasoning is encrypted by OpenAI and can't be imported. |
| `--out-chars N` | Sets how many characters of each tool output to keep. The default is `400`; `0` keeps everything, which makes conversations about 4× larger. |
| `--subagents` | Also imports Codex's own sub-agent threads: "Guardian" safety reviews and spawned workers. |

## What gets imported

| ✅ Imported | ❌ Not imported |
|---|---|
| Your messages and Codex's replies, with Markdown intact | Codex's full reasoning (encrypted by OpenAI) |
| Tool calls and their results, as tool cards (outputs trimmed to 400 characters by default) | Images |
| The conversation title and its project folder | Sub-agent threads, unless you ask with `--subagents` |
| Codex's plain-text reasoning summaries, with `--reasoning` | Conversations that Codex itself imported from Claude Code or Claude Cowork, which would be duplicates |

With `/codex2claude:setup`, you can also move:
- **Skills:** `~/.codex/skills/*` uses the same `SKILL.md` format as Claude, so they're copied across.
- **AGENTS.md:** Claude Code already reads a project's AGENTS.md when there's no CLAUDE.md. Setup links it in the other cases with `@AGENTS.md`, so both tools keep reading the same file.
- **MCP servers:** from `~/.codex/config.toml`. You approve each `claude mcp add` command, and secrets are never shown.

## Auto-sync

```text
/codex2claude:sync on
```

- **When it runs:** each time Claude Code starts, a small script imports Codex conversations that are new or changed since the last sync.
- **What you see:** a one-line notice when something was imported, and nothing otherwise.
- **Cost:** no AI and no tokens.

```text
codex2claude: imported 3 Codex conversation(s). Restart the Claude app to see them in the sidebar.
```

If a sync fails, you get a notice that tells you to run `/codex2claude:list`, which shows the error. Your session still starts normally.

> [!NOTE]
> The Claude desktop app reads its session list only when it starts. A conversation imported while the app is open appears in the sidebar after the next restart.

## Memory

`/codex2claude:memory` turns your Codex history into a handful of lasting facts per project, saved in Claude's own memory. It takes the cheapest route first:

1. **Codex's own summaries.** Codex keeps memory notes in `~/.codex/memories`, and they're already condensed. These are read first.
2. **Conversations Codex never summarized are read only if you agree.** It first shows how many there are and roughly how many tokens reading them would cost. Then you choose to *skip*, *read all*, or *pick some*.
3. **Nothing is saved until you approve.** You see the proposed memories first, and running it again updates them rather than duplicating them.

## Privacy and safety

- **Everything stays on your machine.** codex2claude reads `~/.codex` and writes to `~/.claude` and the desktop app's local session folder, with no network calls.
- **Your conversations aren't sent to the AI during import.** A script converts them, and Claude only sees a short summary of what it did. They're read by the model only when you open one and keep chatting, like any session.
- **It never overwrites** a conversation you continued in Claude, or a session record the desktop app already has.
- **It never brings back** a conversation you deleted in Claude.
- **It never duplicates.** Each Claude session uses the Codex thread id, so importing again updates rather than copies.
- **Commands run without permission prompts only for the plugin's own script.** Everything else asks as usual.

## Requirements

| | |
|---|---|
| **Claude Code** | A recent version, desktop app or terminal. Tested with Claude Code 2.1.289 and the Claude desktop app on Windows 11. |
| **Python** | 3.8 or newer, available as `python3` or `python`. Only the standard library is used, so there's nothing to `pip install`. |
| **Codex history** | In `~/.codex`, or wherever `CODEX_HOME` points. |

> [!IMPORTANT]
> **Showing imports in the desktop sidebar has only been tested on Windows so far.** On macOS and Linux, imported conversations open from `/resume` in the terminal.

## Troubleshooting

<details>
<summary><b>My imported conversations aren't in the desktop sidebar</b></summary>

The app reads its session list only when it starts. Quit it fully (from the system tray or menu bar, not just by closing the window) and reopen it. Then check `/codex2claude:list`: the conversation should show `in Claude`. To group the sidebar by project, use its filter menu.
</details>

<details>
<summary><b>"codex2claude needs Python 3.8 or newer"</b></summary>

Install Python from [python.org](https://www.python.org/downloads/). On Windows, if typing `python` opens the Microsoft Store, Python isn't installed yet. Either install it, or turn off the `python.exe` / `python3.exe` aliases in **Settings → Apps → Advanced app settings → App execution aliases**.
</details>

<details>
<summary><b>A conversation didn't update after I used it in Codex again</b></summary>

If you also continued it in Claude, it's protected on purpose, so your Claude messages are never lost. `/codex2claude:list` shows it as `continued in Claude`.
</details>

<details>
<summary><b>A conversation is too long to continue</b></summary>

Run `/compact` right after opening it, or import it again with a smaller `--out-chars`, for example 150.
</details>

<details>
<summary><b>How do I remove imported conversations?</b></summary>

Delete them in Claude like any other session. codex2claude won't bring them back. Uninstalling the plugin (`/plugin uninstall codex2claude@codex2claude`) leaves already-imported conversations in place.
</details>

<details>
<summary><b>Can I run it from a terminal?</b></summary>

Yes. The script works without Claude Code. After installing the plugin, it's at:

```text
~/.claude/plugins/cache/codex2claude/codex2claude/<version>/bin/codex2claude
```

```bash
sh ~/.claude/plugins/cache/codex2claude/codex2claude/*/bin/codex2claude --help
```

Useful flags: `--list`, `--all`, `--cwd <folder>`, `--dry-run`, `--sync`, `--text <id>`, `--self-test`. It respects `CODEX_HOME` and `CLAUDE_CONFIG_DIR`.

Run from a plain terminal, it imports for `/resume` but doesn't add desktop sidebar entries. Those need the account details Claude Code passes to its commands, so import from inside Claude Code if you want them in the sidebar.
</details>

## License

[MIT](LICENSE) © 2026 Sonu Pandey

---

<div align="center">
<sub>Not affiliated with OpenAI or Anthropic. "Codex" and "Claude" are trademarks of their respective owners.</sub>
</div>
