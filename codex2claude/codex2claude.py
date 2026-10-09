"""codex2claude: bring OpenAI Codex conversations into Claude Code.

  codex2claude --list                       # Codex conversations and whether each is in Claude yet
  codex2claude <thread-id> [...]            # import specific conversations
  codex2claude --all [--cwd D:\\proj]        # import everything (optionally one project)
  codex2claude --sync                       # import conversations that are new or changed since the last sync
  codex2claude --autosync on|off            # also sync at every Claude Code start (SessionStart hook)
  codex2claude --text <id> [--dry-run]      # conversation as plain text, or just its token estimate (for memory)
  codex2claude --self-test

`codex2claude` is bin/codex2claude, which picks python3 or python and handles the Claude desktop app's sidebar.
Imported conversations open with /resume as "[Codex] <title>", and in the desktop app's sidebar after it restarts.
Re-importing overwrites (Claude session id = Codex thread id), except conversations already continued in Claude.
"""
import argparse, collections, datetime, glob, json, os, re, sys, time, uuid
from pathlib import Path

CODEX = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
CLAUDE = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
# Set by bin/codex2claude when the Claude desktop app is present. Microsoft Store Python can't see %APPDATA%, so the
# launcher copies in template.json (newest session record) + deleted.txt, and moves records from out/ to the app.
STAGE = os.environ.get("C2C_STAGE")
DESKTOP_NOTE = "Restart the Claude app to see them in the sidebar."
# Codex injects these as "user" messages; they are harness context, not the human (kept with --context).
INJECTED = ("# AGENTS.md instructions", "<environment_context>", "<permissions instructions>",
            "<recommended_plugins>", "<user_instructions>", "<INSTRUCTIONS>", "<turn_aborted>")
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def clip(s, n):
    s = s if isinstance(s, str) else json.dumps(s, ensure_ascii=False)
    return s if n <= 0 or len(s) <= n else s[:n] + f"… [+{len(s) - n} chars]"


def texts(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content or [] if isinstance(b, dict) and "text" in b)


def norm_cwd(cwd):
    r"""`\\?\c:\x` -> `C:\x`, matching how Claude records Windows folders."""
    cwd = cwd[4:] if cwd.startswith("\\\\?\\") else cwd
    return cwd[0].upper() + cwd[1:] if re.match(r"[a-z]:\\", cwd) else cwd


def dest_of(tid, cwd):
    # ponytail: Claude also hashes very long (>200 char) paths; not handled.
    return CLAUDE / "projects" / re.sub(r"[^a-zA-Z0-9]", "-", norm_cwd(cwd)) / f"{tid}.jsonl"


def convert(rollout, title=None, out_chars=400, context=False, reasoning=False, tools=True):
    """Codex rollout -> Claude Code JSONL records, one per message, tool call and tool result, like a native session."""
    meta, model, items, pending, ts = {}, "codex", [], set(), None

    def result(cid, text):  # (role, content, timestamp, extra record fields)
        return "user", [{"type": "tool_result", "tool_use_id": cid, "content": text or "(empty)"}], ts, {"toolUseResult": text}

    for line in open(rollout, encoding="utf8"):
        try:
            o = json.loads(line)
        except ValueError:  # Codex may be mid-write on the last line
            continue
        p, ts = o.get("payload") or {}, o.get("timestamp") or ts
        if o["type"] == "session_meta":  # sub-agent rollouts also carry their parent's: keep the first
            meta = meta or p
        elif o["type"] == "turn_context":
            model = p.get("model") or model
        if o["type"] != "response_item":
            continue
        t, cid = p.get("type"), "toolu_codex_" + re.sub(r"[^A-Za-z0-9_-]", "_", str(p.get("call_id")))
        if t == "message" and p.get("role") in ("user", "developer"):
            text = texts(p.get("content"))
            injected = p["role"] == "developer" or text.lstrip().startswith(INJECTED)
            if injected and not context or not text.strip():
                continue
            items += [result(c, "(no output recorded)") for c in sorted(pending)]  # the API wants results before user text
            pending.clear()
            items.append(("user", f"[codex context]\n{text}" if injected else text, ts, {}))
        elif not items:
            continue  # the transcript must start with the user
        elif t == "message" and p.get("role") == "assistant" and texts(p.get("content")).strip():
            items.append(("assistant", [{"type": "text", "text": texts(p.get("content"))}], ts, {}))
        elif t == "reasoning" and reasoning and p.get("summary"):
            items.append(("assistant", [{"type": "text", "text": f"[codex reasoning summary]\n{texts(p['summary'])}"}], ts, {}))
        elif t in ("function_call", "custom_tool_call") and tools:
            raw = p.get("arguments") or p.get("input") or ""
            try:
                args = json.loads(raw) if t == "function_call" else None
            except ValueError:
                args = None
            if not isinstance(args, dict) or 0 < out_chars * 2 < len(raw):
                args = {"input": clip(raw, out_chars * 2)}
            items.append(("assistant", [{"type": "tool_use", "id": cid, "name": p.get("name") or "tool", "input": args}], ts, {}))
            pending.add(cid)
        elif t in ("function_call_output", "custom_tool_call_output") and cid in pending:
            out = p.get("output")
            items.append(result(cid, clip(out if isinstance(out, str) else texts(out), out_chars)))
            pending.discard(cid)
        elif t == "web_search_call" and tools:
            items.append(("assistant", [{"type": "text", "text": f"[codex web search] {clip((p.get('action') or {}).get('query', ''), 200)}"}], ts, {}))
        # skipped: encrypted reasoning/compaction/agent_message (only OpenAI can read them), images.
    items += [result(c, "(no output recorded)") for c in sorted(pending)]
    if not items:
        return None, []

    sid, cwd = meta.get("id") or meta["session_id"], norm_cwd(meta.get("cwd", ""))
    banner = f"[Imported from Codex thread {sid} ({meta.get('timestamp', '')[:10]}, model {model})]\n\n"
    recs, parent = [], None
    if title:
        recs.append({"type": "custom-title", "customTitle": f"[Codex] {title}", "sessionId": sid})
    for i, (role, content, at, extra) in enumerate(items):
        u = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{sid}/{i}"))
        msg = ({"role": "user", "content": banner + content if i == 0 else content} if role == "user" else
               {"id": f"msg_codex_{i}", "type": "message", "role": "assistant", "model": model, "content": content,
                "stop_reason": "tool_use" if content[0]["type"] == "tool_use" else "end_turn",
                "stop_sequence": None, "usage": {"input_tokens": 0, "output_tokens": 0}})
        recs.append({"parentUuid": parent, "isSidechain": False, "userType": "external", "cwd": cwd,
                     "sessionId": sid, "version": "codex-import", "gitBranch": "", "type": role,
                     "message": msg, "uuid": u, "timestamp": at, **extra})
        parent = u
    return dest_of(sid, cwd), recs


def continued_in_claude(dest):
    """`claude --resume` appends to the same file: True if it holds turns we didn't write (never overwrite those)."""
    if not dest.exists():
        return False
    with open(dest, encoding="utf8") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except ValueError:  # Claude is writing it right now
                return True
            if r.get("type") in ("user", "assistant") and r.get("version") != "codex-import":
                return True
    return False


def deleted_in_claude(tid):
    """The desktop app leaves a deleted_<transcript id> marker when the user deletes a session: don't bring it back."""
    p = Path(STAGE or ".") / "deleted.txt"
    return bool(STAGE) and p.exists() and f"deleted_{tid}" in p.read_text(encoding="utf8").split()


def desktop_record(tid, title, recs):
    """Stage a session record for the desktop app's sidebar (it lists only sessions it has a record for)."""
    tpl, t = {}, Path(STAGE) / "template.json"
    if t.exists():  # new sessions get the user's latest model / effort / permission settings
        keep = ("model", "effort", "permissionMode", "chromePermissionMode")
        tpl = {k: v for k, v in json.loads(t.read_text(encoding="utf8")).items() if k in keep}
    msgs = [r for r in recs if "message" in r]
    ms = lambda r: int(datetime.datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")).timestamp() * 1000)
    first = msgs[0]["message"]["content"].split("\n\n", 1)[-1]
    rec = {"sessionId": "local_" + str(uuid.uuid5(uuid.NAMESPACE_URL, "codex2claude/" + tid)), "cliSessionId": tid,
           "cwd": msgs[0]["cwd"], "originCwd": msgs[0]["cwd"], "createdAt": ms(msgs[0]), "lastActivityAt": ms(msgs[-1]),
           "lastFocusedAt": ms(msgs[-1]), "latestUserFrameAt": ms(msgs[-1]), **tpl, "isArchived": False,
           "title": f"[Codex] {title or clip(first, 60)}", "titleSource": "auto",
           "completedTurns": sum(isinstance(r["message"]["content"], str) for r in msgs), "titleTurn": 0,
           "lastAssistantUuid": next((r["uuid"] for r in reversed(msgs) if r["type"] == "assistant"), None),
           "remoteMcpServersConfig": [], "lastSpawnRootDetected": False, "remoteControlAutoEligible": False,
           "steeredByRemoteClient": False, "alwaysAllowedReasons": [], "sessionPermissionUpdates": [],
           "classifierSummaryEnabled": True, "reportFindingsCard": True, "spawnSeed": {}}
    out = Path(STAGE) / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{rec['sessionId']}.json").write_text(json.dumps(rec, indent=2), encoding="utf8")


def status_of(tid, rollout, cwd):
    dest = dest_of(tid, cwd)
    if deleted_in_claude(tid):
        return "deleted in Claude"
    if not dest.exists():
        return "new"
    if continued_in_claude(dest):
        return "continued in Claude"
    return "changed in Codex" if os.path.getmtime(rollout) > os.path.getmtime(dest) else "in Claude"


def threads(subagents=False, since=0):
    """{thread_id: (rollout_path, title, cwd)} from rollout files changed after `since` + session_index titles."""
    names = {}
    idx = CODEX / "session_index.jsonl"
    if idx.exists():
        for l in open(idx, encoding="utf8"):
            try:
                o = json.loads(l)
            except ValueError:  # Codex appends here while it runs
                continue
            names[o["id"]] = o.get("thread_name")
    # Threads Codex itself imported from Claude Code / Cowork: importing them back would duplicate history.
    from_claude = set()
    for name, key in (("external_agent_session_imports.json", "imported_thread_id"),
                      ("claude-cowork-import-history.json", "importedThreadId")):
        if (CODEX / name).exists():
            from_claude |= {r.get(key) for r in json.load(open(CODEX / name, encoding="utf8")).get("records", [])}
    found = {}
    for d in ("sessions", "archived_sessions"):
        for f in glob.glob(str(CODEX / d / "**" / "rollout-*.jsonl"), recursive=True):
            tid = re.search(r"([0-9a-f]{8}-[0-9a-f-]{27})\.jsonl$", f).group(1)
            if since and os.path.getmtime(f) <= since:
                continue
            try:
                with open(f, encoding="utf8") as fh:
                    meta = json.loads(fh.readline()).get("payload") or {}
            except ValueError:  # Codex is creating it right now
                continue
            # Sub-agents (guardian reviews, spawned workers) would flood /resume with non-user threads.
            sub = isinstance(meta.get("source"), dict) and "subagent" in meta["source"]
            if tid not in from_claude and (subagents or not sub):
                found[tid] = (f, names.get(tid), norm_cwd(meta.get("cwd", "")))
    return found


def summarized_ids():
    """Thread ids that Codex's own memory (~/.codex/memories) already summarizes."""
    return {i for f in glob.glob(str(CODEX / "memories" / "**" / "*.md"), recursive=True)
            for i in re.findall(UUID, Path(f).read_text(encoding="utf8", errors="replace"))}


def run(sel, a, log=print):
    """Import the selected threads; returns a Counter of outcomes: wrote / continued / deleted / empty."""
    c = collections.Counter()
    for k, (f, title, _) in sel.items():
        if deleted_in_claude(k):
            c["deleted"] += 1
            log(f"skip  {k} (you deleted it in Claude)")
            continue
        dest, recs = convert(f, title, a.out_chars, a.context, a.reasoning)
        if not recs:
            c["empty"] += 1
            log(f"skip  {k} (no conversation text)")
        elif continued_in_claude(dest):
            c["continued"] += 1
            log(f"skip  {k} (continued in Claude Code; left as is)")
        else:
            c["wrote"] += 1
            size = sum(len(json.dumps(r["message"]["content"])) for r in recs if "message" in r)  # what the model reads
            log(f"{'would write' if a.dry_run else 'wrote'}  {dest}  ({len(recs)} records, ~{size // 4000}k tokens)")
            if not a.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "w", encoding="utf8") as fh:
                    fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in recs)
                if STAGE:
                    desktop_record(k, title, recs)
    return c


def where_note():
    return DESKTOP_NOTE if STAGE else "Open them with /resume."


def state_path(a):
    return Path(a.data or os.environ.get("CLAUDE_PLUGIN_DATA") or CLAUDE) / "codex2claude-state.json"


def load(a):
    p = state_path(a)
    return json.loads(p.read_text(encoding="utf8")) if p.exists() else {}


def save(a, st):
    p = state_path(a)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(st), encoding="utf8")


def sync(a, st):
    """Import conversations whose Codex file changed since the last sync; returns (Counter, message)."""
    since, now = st.get("last_sync", 0), time.time()
    c = run(threads(a.subagents, since), a, log=lambda _: None)
    msg = f"imported {c['wrote']} Codex conversation(s)"
    if c["continued"]:
        msg += f"; left {c['continued']} you continued in Claude as they are"
    st.update(last_sync=now, last_result=f"{time.strftime('%Y-%m-%d %H:%M')}: {msg}")
    return c, msg


def hook(a):
    """SessionStart hook: auto-sync when it's on; otherwise, once, tell the user what this plugin can do.
    Prints JSON {"systemMessage": ...}, which Claude Code shows to the user without adding it to Claude's context."""
    st, msg = load(a), None
    try:
        if st.get("autosync"):
            c, result = sync(a, st)
            msg = (c["wrote"] or c["continued"]) and f"codex2claude: {result}." + (" " + where_note() if c["wrote"] else "")
        elif not st.get("hinted"):
            new = sum(not dest_of(k, cwd).exists() and not deleted_in_claude(k) for k, (_, _, cwd) in threads().items())
            st["hinted"] = bool(new)
            msg = new and (f"codex2claude: {new} Codex conversation(s) aren't in Claude Code yet. Run "
                           "/codex2claude:import to bring them in, or /codex2claude:sync on to keep them in sync.")
    except Exception as e:  # never break session start; the error shows in /codex2claude:list
        st["last_result"] = f"{time.strftime('%Y-%m-%d %H:%M')}: failed: {e!r}"
        msg = f"codex2claude: auto-sync failed ({e}). See /codex2claude:list."
    save(a, st)
    if msg:
        print(json.dumps({"systemMessage": msg}))


def list_threads(sel, st):
    rows = [(cwd, title or "", k, status_of(k, f, cwd)) for k, (f, title, cwd) in sel.items()]
    counts = collections.Counter(r[3] for r in rows)
    print(f"Auto-sync: {'on' if st.get('autosync') else 'off'}"
          f" | last sync: {st.get('last_result', 'never')}")
    print(f"{len(rows)} Codex conversation(s): " + ", ".join(f"{n} {s}" for s, n in counts.most_common()))
    for cwd in sorted({r[0] for r in rows}):
        print(f"\n{cwd or '(no folder)'}")
        for _, title, k, s in sorted(r for r in rows if r[0] == cwd):
            print(f"  {k}  {s:20}  {title}")


def self_test():
    import tempfile
    rm = lambda role, text: {"type": "response_item", "payload": {"type": "message", "role": role, "content": [{"type": "input_text", "text": text}]}}
    lines = [
        {"type": "session_meta", "payload": {"id": "019f0000-0000-7000-8000-000000000001", "cwd": "\\\\?\\d:\\proj x", "timestamp": "2026-01-01T00:00:00Z"}},
        rm("developer", "sys"), rm("user", "<environment_context>x</environment_context>"), rm("user", "fix bug"),
        {"type": "response_item", "payload": {"type": "reasoning", "summary": [], "encrypted_content": "zz"}},
        {"type": "response_item", "payload": {"type": "function_call", "name": "shell", "call_id": "c1", "arguments": "{\"cmd\":\"ls\"}"}},
        {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "c1", "output": "a" * 1000}},
        rm("assistant", "done"),
        {"type": "response_item", "payload": {"type": "reasoning", "summary": [{"type": "summary_text", "text": "**Plan**"}], "encrypted_content": "zz"}},
        {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "exec", "call_id": "c2", "input": "js()"}},  # never answered
        rm("user", "again"),
        {"type": "session_meta", "payload": {"id": "019f0000-0000-7000-8000-00000000000f", "cwd": "D:\\parent"}},  # sub-agent's parent
    ]
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf8") as fh:
        fh.write("\n".join(map(json.dumps, lines)) + '\n{"type": "respon')  # Codex mid-write
    path, recs = convert(fh.name, "T")
    _, full = convert(fh.name, "T", 0, context=True, reasoning=True)
    _, talk = convert(fh.name, "T", tools=False)
    os.unlink(fh.name)
    assert path.parent.name == "D--proj-x" and path.stem.endswith("0001") and recs[1]["cwd"] == "D:\\proj x", path
    assert [r["type"] for r in recs] == ["custom-title", "user", "assistant", "user", "assistant", "assistant", "user", "user"], recs
    assert recs[1]["message"]["content"].endswith("fix bug") and recs[1]["parentUuid"] is None
    use, res = recs[2]["message"]["content"][0], recs[3]["message"]["content"][0]
    assert use == {"type": "tool_use", "id": "toolu_codex_c1", "name": "shell", "input": {"cmd": "ls"}}, use
    assert res["tool_use_id"] == "toolu_codex_c1" and "+600 chars" in res["content"] and recs[3]["toolUseResult"], res
    assert recs[4]["message"]["content"] == [{"type": "text", "text": "done"}] and recs[4]["parentUuid"] == recs[3]["uuid"]
    assert recs[5]["message"]["content"][0]["input"] == {"input": "js()"} and recs[5]["message"]["stop_reason"] == "tool_use"
    assert recs[6]["message"]["content"][0]["content"] == "(no output recorded)" and recs[7]["message"]["content"] == "again"
    users = " ".join(r["message"]["content"] for r in full if r.get("type") == "user" and isinstance(r["message"]["content"], str))
    assert "[codex context]\nsys" in users and "<environment_context>" in users, users
    assert any("a" * 1000 == b.get("content") for r in full if "message" in r and r["type"] == "user" for b in r["message"]["content"] if isinstance(b, dict))
    assert any(b.get("text") == "[codex reasoning summary]\n**Plan**" for r in full if r.get("type") == "assistant" for b in r["message"]["content"])
    assert [r["type"] for r in talk] == ["custom-title", "user", "assistant", "user"], talk
    dest = Path(tempfile.mkdtemp()) / "s.jsonl"
    dest.write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf8")
    assert not continued_in_claude(dest)
    with open(dest, "a", encoding="utf8") as fh:
        fh.write(json.dumps({"type": "user", "version": "2.1.289"}) + "\n")
    assert continued_in_claude(dest)
    print("self-test ok")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--list", action="store_true", help="show conversations, their status, and auto-sync state")
    ap.add_argument("--all", action="store_true", help="select every conversation")
    ap.add_argument("--cwd", help="only conversations from this project folder (case-insensitive)")
    ap.add_argument("--dry-run", action="store_true", help="show what would happen, write nothing")
    ap.add_argument("--out-chars", type=int, default=400, help="characters kept per tool output (default 400, 0 = all)")
    ap.add_argument("--context", action="store_true", help="keep what Codex injected: AGENTS.md, environment, permission instructions")
    ap.add_argument("--reasoning", action="store_true", help="keep plain-text reasoning summaries (full reasoning is encrypted)")
    ap.add_argument("--subagents", action="store_true", help="include Codex sub-agent threads (guardian reviews, spawned workers)")
    ap.add_argument("--sync", action="store_true", help="import conversations that are new or changed since the last sync")
    ap.add_argument("--autosync", choices=("on", "off"), help="sync at every Claude Code start (on also syncs now)")
    ap.add_argument("--hook", action="store_true", help="SessionStart hook mode (used by the plugin)")
    ap.add_argument("--text", action="store_true", help="print conversation text only (no tool calls); with --dry-run, token estimates")
    ap.add_argument("--unsummarized", action="store_true", help="only conversations Codex's own memory doesn't summarize")
    ap.add_argument("--data", help="folder for auto-sync state (default: the plugin's data folder)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf8", errors="replace")  # Windows pipes default to cp1252
    if a.self_test:
        return self_test()
    if a.hook:
        return hook(a)
    if a.sync or a.autosync:
        st = load(a)
        if a.autosync:
            st["autosync"] = a.autosync == "on"
            print(f"Auto-sync is {a.autosync}.")
        if a.sync or a.autosync == "on":
            c, msg = sync(a, st)
            print(msg[0].upper() + msg[1:] + "." + (" " + where_note() if c["wrote"] else ""))
        return save(a, st)

    sel = {k: v for k, v in threads(a.subagents).items() if a.all or a.list or k in a.ids}
    if a.cwd:
        want = os.path.normcase(os.path.abspath(a.cwd))
        sel = {k: v for k, v in sel.items() if os.path.normcase(os.path.abspath(v[2] or ".")) == want}
    if a.unsummarized:
        done = summarized_ids()
        sel = {k: v for k, v in sel.items() if k not in done}
    if a.list:
        return list_threads(sel, load(a))
    if not sel:
        sys.exit("Nothing selected: pass conversation ids, or --all (see --list).")
    if a.text:
        total = 0
        for k, (f, title, _) in sel.items():
            recs = convert(f, title, a.out_chars, a.context, a.reasoning, tools=False)[1]
            body = "\n".join(f"\n## {r['type']}\n" + (r["message"]["content"] if r["type"] == "user"
                                                      else r["message"]["content"][0]["text"]) for r in recs if "message" in r)
            total += len(body) // 4
            print(f"{k}  ~{len(body) // 4000}k tokens  {title or ''}" if a.dry_run else f"\n# {title or k}\n{body}")
        if a.dry_run:
            print(f"total: {len(sel)} conversation(s), ~{total // 1000}k tokens")
        return
    if run(sel, a)["wrote"] and STAGE and not a.dry_run:
        print(DESKTOP_NOTE)


if __name__ == "__main__":
    main()
