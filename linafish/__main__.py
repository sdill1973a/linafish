"""
LiNafish CLI

  linafish go [path]            — the product. one command. everything assembles.
  linafish eat <path>           — ingest files, build a fish
  linafish fuse <path>          — recursive fusion to irreducible formations
  linafish taste <fish.md>      — preview what the fish knows
  linafish status <fish.md>     — show codebook stats
  linafish serve <fish.md>      — serve a fish as MCP server
  linafish demo <path>          — eat + taste + test in one command
"""

import sys
import json
import argparse
from pathlib import Path


def _user_path(value):
    """argparse type for path-shaped arguments.

    Expands a leading ~ (via Path.expanduser()) at parse time so the CLI
    works on Windows cmd/PowerShell, where the shell does not expand ~
    before Python sees it. Returns a `pathlib.Path`. Using this as
    `type=_user_path` on every path-shaped add_argument is the single
    point that fixes the "~/my-writing becomes a literal ~ directory"
    footgun for every current and future command — a user never hits
    an un-expanded ~ in any cmd_* body.
    """
    return Path(value).expanduser()


def cmd_eat(args):
    """Ingest files and build a fish using the crystallizer."""
    from .crystallizer import crystallize, extend_vocabulary, couple_crystals, tag_diamonds
    from .formations import detect_formations, hierarchical_merge, formations_to_codebook_text
    from .ingest import ingest_directory, ingest_file

    # expanduser() makes ~/path work on Windows cmd/PowerShell.
    source = Path(args.source).expanduser()
    if not source.exists():
        print(f"Error: {source} not found")
        sys.exit(1)

    if args.vocab:
        vocab = json.loads(Path(args.vocab).read_text(encoding="utf-8"))
        extend_vocabulary(vocab)

    # Ingest using structured reader, crystallize per chunk (no double-chunking)
    all_crystals = []
    if source.is_dir():
        chunks = ingest_directory(source)
        for chunk in chunks:
            c = crystallize(chunk.text, source=chunk.source,
                           context_hint=args.hint or "")
            if c:
                all_crystals.append(c)
    else:
        chunks = ingest_file(source)
        if chunks:
            for chunk in chunks:
                c = crystallize(chunk.text, source=chunk.source,
                               context_hint=args.hint or "")
                if c:
                    all_crystals.append(c)
        else:
            # Fallback for unsupported formats
            content = source.read_text(encoding="utf-8", errors="replace")
            c = crystallize(content, source=source.name,
                           context_hint=args.hint or "")
            if c:
                all_crystals.append(c)

    if not all_crystals:
        print("No content found.")
        sys.exit(1)

    print(f"  {len(all_crystals)} crystals from {source}")

    # Couple once across all crystals, tag diamonds
    couple_crystals(all_crystals)
    tag_diamonds(all_crystals)

    # Form
    formations = detect_formations(all_crystals)
    print(f"  {len(formations)} formations")

    # Hierarchical merge if needed
    if len(formations) > 60:
        formations = hierarchical_merge(formations, target=50)
        print(f"  -> {len(formations)} meta-formations")

    # Render
    name = args.name or source.stem
    codebook = formations_to_codebook_text(
        formations,
        title=args.description or f"LiNafish: {name}",
        crystals=all_crystals,
    )

    # Save
    output = Path(args.output) if args.output else Path(f"{name}.fish.md")
    output.write_text(codebook, encoding="utf-8")
    print(f"\nFish: {output} ({len(codebook)} chars, {len(formations)} formations)")

    # Explain what just happened — the WHY (v0.4.3)
    if formations:
        try:
            from .quickstart import build_full_portrait, explain_the_why
            crystal_map = {c.id: c for c in all_crystals}
            portrait = build_full_portrait(formations, len(all_crystals), len(all_crystals), crystal_map)
            print(f"\n{portrait}")
            why = explain_the_why(len(all_crystals), len(all_crystals), formations, crystal_map)
            print(f"\n{why}")
        except Exception:
            pass  # Portrait is bonus, not critical


def cmd_taste(args):
    """Preview what a fish knows."""
    fish_path = Path(args.fish)
    if not fish_path.exists():
        print(f"Error: {fish_path} not found")
        sys.exit(1)
    content = fish_path.read_text(encoding="utf-8")
    # Windows consoles use cp1252 by default; curly quotes and other Unicode
    # from Gutenberg texts cause UnicodeEncodeError on print().  Force safe
    # output regardless of console encoding.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass  # pre-3.7 or non-reconfigurable stream
    try:
        print(content)
    except UnicodeEncodeError:
        print(content.encode("utf-8", errors="replace").decode("utf-8"))


def cmd_recall(args):
    """Full-text search across crystals. Find specific words, not patterns."""
    from .engine import FishEngine

    state_dir = Path(args.state_dir) if args.state_dir else Path.home() / ".linafish"
    name = args.name

    # Auto-detect fish name if not specified
    if not name:
        # Find most recently modified crystals file (flat structure: name_crystals.jsonl)
        candidates = [f.stem.replace("_crystals", "") for f in state_dir.glob("*_crystals.jsonl")]
        if not candidates:
            print("No fish found. Run 'linafish go' first.")
            sys.exit(1)
        # Pick most recent by file mod time
        candidates.sort(key=lambda n: (state_dir / f"{n}_crystals.jsonl").stat().st_mtime, reverse=True)
        name = candidates[0]

    engine = FishEngine(state_dir=state_dir, name=name)
    if not engine.fish.crystals:
        print("Fish is empty. Feed it first.")
        sys.exit(1)

    result = engine.recall(args.query, top=args.top)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    print(result)


def cmd_ask(args):
    """Ask your fish a question. Semantic search — finds meaning, not just words."""
    engine = _resolve_engine(args)
    if not engine.fish.crystals:
        print("Fish is empty. Feed it first.")
        sys.exit(1)

    result = engine.taste(args.question, top=args.top)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    print(result)


def cmd_status(args):
    """Show fish stats."""
    fish_path = Path(args.fish)
    content = fish_path.read_text(encoding="utf-8")
    formations = content.count("** (")
    lines = len(content.split("\n"))
    print(f"Fish: {fish_path.name}")
    print(f"Size: {len(content)} chars, {lines} lines")
    print(f"Formations: ~{formations}")


def cmd_serve(args):
    """Serve a fish as an MCP server (Claude Code)."""
    from .server import serve_fish

    feed_path = Path(args.feed) if args.feed else None
    state_dir = Path(args.state_dir) if args.state_dir else None
    vocab_path = Path(args.vocab) if args.vocab else None

    if feed_path and not feed_path.exists():
        print(f"Error: {feed_path} not found")
        sys.exit(1)

    serve_fish(
        feed_path=feed_path,
        state_dir=state_dir,
        name=args.name or "linafish",
        vocab_path=vocab_path,
    )


def cmd_http(args):
    """Serve a fish over HTTP (any AI that can fetch a URL)."""
    from .http_server import serve_http

    feed_path = Path(args.feed) if args.feed else None
    state_dir = Path(args.state_dir) if args.state_dir else None
    vocab_path = Path(args.vocab) if args.vocab else None

    if feed_path and not feed_path.exists():
        print(f"Error: {feed_path} not found")
        sys.exit(1)

    serve_http(
        feed_path=feed_path,
        state_dir=state_dir,
        name=args.name or "linafish",
        port=args.port,
        vocab_path=vocab_path,
    )


def cmd_demo(args):
    """One-command demo: eat -> taste -> test with Gemini.

    Rewired 2026-04-15 (fork/step1): now uses FishEngine.eat_path
    instead of the v1 crystallizer's batch_ingest. Same user-facing
    behavior (writes ./{name}.fish.md in cwd, optional Gemini test),
    but the cognitive pipeline goes through the v3+v4 metabolic engine
    so the demo output reflects the current architecture.

    UX delta vs v1: the --hint flag is preserved in the argparser for
    backward compat but is a no-op — FishEngine's v3 cognitive parser
    doesn't take a context_hint prefix. If you pass --hint we emit a
    one-line warning. Same shape of issue codex flagged for cmd_eat
    when it warned about UX deltas during the v1->v3 migration.
    """
    from .engine import FishEngine

    source = Path(args.source).expanduser()
    if not source.exists():
        print(f"Error: {source} not found")
        sys.exit(1)

    if args.hint:
        print(f"  [warn] --hint is a no-op under v3 (FishEngine has no "
              f"context_hint equivalent). Continuing without hint.")

    print(f"=== LiNafish Demo ===\n")

    # Eat through FishEngine — persists to ~/.linafish/{name}/
    name = args.name or source.stem
    print(f"[1/3] Eating {source}...")
    engine = FishEngine(name=name)
    result = engine.eat_path(source)

    if not engine.fish.crystals:
        print("No content found.")
        sys.exit(1)

    print(f"  {result.get('crystals_added', 0)} crystals added "
          f"({result.get('total_crystals', 0)} total) "
          f"-> {result.get('formations', 0)} formations")

    # Read the fish.md FishEngine wrote during eat_path
    if engine.fish_file.exists():
        codebook = engine.fish_file.read_text(encoding="utf-8")
    else:
        codebook = ""

    # Mirror to cwd for demo discoverability — preserves original UX.
    # The persisted copy at engine.fish_file is the source of truth and
    # remains available for `linafish recall` and `linafish status` in
    # the user's home dir.
    fish_path = Path(f"{name}.fish.md")
    fish_path.write_text(codebook, encoding="utf-8")

    # Taste
    print(f"\n[2/3] Fish contents:\n")
    print(codebook[:2000])
    if len(codebook) > 2000:
        print(f"\n  ... ({len(codebook) - 2000} more chars)")

    # Test with Gemini if available
    if args.question:
        print(f"\n[3/3] Testing with Gemini...\n")
        try:
            import time
            from google import genai
            client = genai.Client(api_key=args.api_key)
            chat = client.chats.create(model=args.model)

            chat.send_message("You are learning from a compressed knowledge codebook. Absorb this.")
            time.sleep(13)
            chat.send_message(codebook[:6000])
            time.sleep(13)
            r = chat.send_message(args.question)
            print(f"Question: {args.question}\n")
            print(f"Answer:\n{r.text}")
        except Exception as e:
            print(f"  Gemini test failed: {e}")
            print(f"  Fish saved at {fish_path} — paste into any AI session manually.")
    else:
        print(f"\n[3/3] No question provided.")
        print(f"  Fish saved at {fish_path} (cwd copy)")
        print(f"  Persisted at {engine.fish_file} for `linafish recall`")
        print(f"  Paste into any AI session for warm-on-contact understanding.")


def cmd_go(args):
    """The product. One command. Everything assembles."""
    from .quickstart import go

    go(
        source=args.source if hasattr(args, 'source') and args.source else None,
        name=args.name if hasattr(args, 'name') and args.name else None,
        state_dir=args.state_dir if hasattr(args, 'state_dir') and args.state_dir else None,
        serve=not (hasattr(args, 'no_serve') and args.no_serve),
        port=args.port if hasattr(args, 'port') and args.port else None,
    )


def cmd_init(args):
    """Eat all MCP servers — local and remote — build shared codebook."""
    from .init import init_fish

    codebook, mcp_path = init_fish(
        remotes=args.remote if args.remote else None,
        fish_name=args.name,
        live=args.live,
        backup=not args.no_backup,
    )

    # Save as fish
    output = Path(args.output) if args.output else Path(f"{args.name}.fish.md")
    codebook.save(output)
    print(f"\nSaved: {output}")


def cmd_watch(args):
    """Watch a directory. Eat new files as they arrive. The fish grows continuously."""
    from .engine import FishEngine
    import time

    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        print(f"Error: {source} not found")
        sys.exit(1)

    state_dir = Path(args.state_dir) if args.state_dir else None
    name = args.name or source.name
    engine = FishEngine(state_dir=state_dir, name=name)

    # Track file modification times
    seen = {}
    interval = args.interval or 60

    print(f"LiNafish watching: {source}")
    print(f"  Checking every {interval}s. Ctrl+C to stop.")
    print(f"  Fish: {engine.fish_file}")

    # Initial eat if fish is empty
    if not engine.crystals:
        print(f"  First feed...")
        result = engine.eat_path(source)
        print(f"  {result['crystals_added']} crystals, {result['formations']} formations")

    # Snapshot current state
    for f in source.rglob("*"):
        if f.is_file():
            try:
                seen[str(f)] = f.stat().st_mtime
            except OSError:
                pass

    try:
        while True:
            time.sleep(interval)
            changed = []
            for f in source.rglob("*"):
                if not f.is_file():
                    continue
                try:
                    mtime = f.stat().st_mtime
                    prev = seen.get(str(f))
                    if prev is None or mtime > prev:
                        seen[str(f)] = mtime
                        changed.append(f)
                except OSError:
                    pass

            if changed:
                print(f"  {len(changed)} changed files. Eating...")
                for f in changed:
                    try:
                        text = f.read_text(encoding="utf-8", errors="replace")
                        if text and len(text.strip()) > 10:
                            engine.eat(text, source=str(f.name))
                    except Exception:
                        pass
                print(f"  Fish: {len(engine.crystals)} crystals, {len(engine.formations)} formations")
    except KeyboardInterrupt:
        print("\nStopped watching. Fish is saved.")


def cmd_fuse(args):
    """Recursive fusion — compress corpus to irreducible formations."""
    from .fusion import cmd_fuse as _cmd_fuse
    _cmd_fuse(args)


def cmd_room(args):
    """Listen to the federation room. Eat every exchange."""
    from .daemon import RoomListener

    vocab = None
    if hasattr(args, 'vocab') and args.vocab:
        vocab = json.loads(Path(args.vocab).read_text(encoding="utf-8"))

    state_dir = Path(args.state_dir) if args.state_dir else Path(".")

    listener = RoomListener(
        broker=args.broker,
        port=args.port,
        fish_name=args.name,
        state_dir=state_dir,
        vocab=vocab,
    )
    listener.run()


def _resolve_engine(args):
    """Get a FishEngine from common args."""
    from .engine import FishEngine
    state_dir = Path(args.state_dir) if hasattr(args, 'state_dir') and args.state_dir else None
    name = getattr(args, 'name', None) or 'linafish'
    return FishEngine(state_dir=state_dir, name=name)


def cmd_session(args):
    """Manage fish sessions (git branches)."""
    engine = _resolve_engine(args)
    action = args.action

    if action == "start":
        result = engine.session_start(args.session_name or "")
        if result["success"]:
            print(f"Session started: {result['branch']}")
            print("Crystals will accumulate on this branch.")
            print("Run 'linafish session end' to merge back.")
        else:
            print(f"Failed: {result['error']}")

    elif action == "end":
        result = engine.session_end()
        if result["success"]:
            print(f"Session merged: {result['merged']} -> {result['into']}")
        else:
            print(f"Failed: {result['error']}")

    elif action == "status":
        status = engine.session_status()
        branch = status["branch"]
        marker = " (session)" if status["is_session"] else ""
        print(f"Branch: {branch}{marker}")
        print(f"Crystals: {status['crystals']}  Formations: {status['formations']}")
        if status["recent_commits"]:
            print(f"\nRecent:")
            for line in status["recent_commits"][:5]:
                print(f"  {line}")


def cmd_history(args):
    """Show fish growth history (git log)."""
    engine = _resolve_engine(args)
    entries = engine.history(count=args.count)
    if not entries:
        print("No history yet. Feed the fish first.")
        return
    for entry in entries:
        print(entry)


def cmd_diff(args):
    """Show what changed since a reference point."""
    engine = _resolve_engine(args)
    ref = args.ref or "HEAD~1"
    result = engine.diff(ref)
    if result["stat"]:
        print(result["stat"])
    if result["fish_diff"]:
        # Show only added/removed formation lines for readability
        for line in result["fish_diff"].split("\n"):
            if line.startswith("+**") or line.startswith("-**"):
                print(line)
            elif line.startswith("+  ") or line.startswith("-  "):
                print(line)
    elif not result["stat"]:
        print("No changes.")


def cmd_revert(args):
    """Revert the fish to a previous state."""
    engine = _resolve_engine(args)
    ref = args.ref or "HEAD"
    if not args.yes:
        print(f"This will revert: {ref}")
        try:
            confirm = input("Are you sure? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "n"
        if confirm != "y":
            print("Cancelled.")
            return
    result = engine.revert(ref)
    if result["success"]:
        print(f"Reverted: {ref}")
    else:
        print(f"Failed: {result['error']}")


def cmd_absorb(args):
    """Eat existing RAG into your fish."""
    from .absorb import absorb
    engine = _resolve_engine(args)
    print(f"  Absorbing: {args.source}")
    print(f"  Into: {engine.name} ({len(engine.crystals)} existing crystals)")
    print()
    result = absorb(engine, args.source)
    if "error" in result:
        print(f"  Error: {result['error']}")
    else:
        print(f"  Done: {result.get('absorbed', 0)} absorbed")
        print(f"  Fish: {result.get('total_crystals', '?')} crystals, "
              f"{result.get('formations', '?')} formations")


def cmd_converse(args):
    """Two fish, one conversation."""
    from .converse import serve_converse
    state_dir = Path(args.state_dir) if args.state_dir else None
    serve_converse(
        name=args.name,
        state_dir=state_dir,
        port=args.port,
        bind=args.bind,
        mind=args.mind,
        token=args.token,
    )


def cmd_school(args):
    """The river and the nets. One stream, N fish."""
    from .school import School

    state_dir = Path(args.state_dir) if args.state_dir else None
    central_dir = Path(args.central_dir) if args.central_dir else None
    manifest = Path(args.manifest) if args.manifest else None

    school = School(
        state_dir=state_dir,
        manifest_path=manifest,
        central_state_dir=central_dir,
    )

    action = args.action

    if action == "init":
        school.save_manifest()
        print(f"School initialized at {school.state_dir}")
        print(f"  Manifest: {school.manifest_path}")
        print(f"  Central: {school.central.name} ({len(school.central.crystals)} crystals)")
        print(f"  Members: {len(school.members)}")
        if school.members:
            for name in sorted(school.members):
                config = school.manifest.get("members", {}).get(name, {})
                print(f"    {name}: d={config.get('d', 4.0)}, "
                      f"centroid={'yes' if config.get('subtract_centroid') else 'no'}")

    elif action == "add":
        if not args.target:
            print("Usage: linafish school add <member-name> [-d 2.0] [--centroid]")
            sys.exit(1)
        school.add_member(
            name=args.target,
            d=args.d,
            subtract_centroid=args.centroid,
            min_gamma=args.min_gamma,
        )
        print(f"Added member: {args.target} (d={args.d}, "
              f"centroid={'yes' if args.centroid else 'no'})")

    elif action == "eat":
        if not args.target:
            print("Usage: linafish school eat <text-or-file> [--source label]")
            sys.exit(1)

        target = args.target
        target_path = Path(target)

        if target_path.exists():
            print(f"Feeding {target_path} through school...")
            result = school.eat_path(target_path, source=args.source)
            print(f"  Central: +{result['central']['crystals_added']} crystals "
                  f"({result['central'].get('total_crystals', '?')} total)")
            for name, mr in result["members"].items():
                added = mr.get("crystals_added", 0)
                total = mr.get("total_crystals", "?")
                print(f"  {name}: +{added} crystals ({total} total)")
        else:
            # Treat as raw text
            result = school.eat(target, source=args.source)
            print(f"  Central: +{result['central'].get('crystals_added', 0)}")
            for name, mr in result["members"].items():
                added = mr.get("crystals_added", 0)
                if added:
                    print(f"  {name}: +{added} (grabbed)")
                else:
                    print(f"  {name}: slid past")

    elif action == "refeed":
        if not args.target:
            print("Usage: linafish school refeed <member-name>")
            sys.exit(1)
        print(f"Refeeding {args.target} from central corpus...")
        result = school.refeed(args.target)
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"  Read {result['central_crystals_read']} central crystals")
            print(f"  Fed {result['fed']} to {args.target}")
            print(f"  Result: {result['total_crystals']} crystals, "
                  f"{result['formations']} formations")

    elif action == "status":
        status = school.status()
        print(f"School: {status['member_count']} members")
        print(f"Central ({status['central']['name']}): "
              f"{status['central']['crystals']}c / "
              f"{status['central']['formations']}f / "
              f"epoch {status['central']['epoch']}")
        for name, ms in sorted(status["members"].items()):
            formations_str = ""
            if ms["top_formations"]:
                formations_str = f" [{', '.join(ms['top_formations'][:2])}]"
            print(f"  {name}: {ms['crystals']}c / {ms['formations']}f / "
                  f"d={ms['d']}"
                  f"{' +centroid' if ms['subtract_centroid'] else ''}"
                  f"{formations_str}")

    elif action == "docket":
        print(school.docket())


def cmd_whisper(args):
    """One insight from your fish. What it noticed that you might not have."""
    engine = _resolve_engine(args)

    if not engine.formations:
        print("  Your fish is still learning. Feed it more and check back.")
        return

    from .formations import interpret_formation
    import random

    formations = sorted(engine.formations, key=lambda f: f.crystal_count, reverse=True)

    # Pick something interesting — not the biggest (obvious) but the second or third
    if len(formations) >= 3:
        f = formations[2]  # Third strongest — surprising, not obvious
    elif len(formations) >= 2:
        f = formations[1]
    else:
        f = formations[0]

    interp = interpret_formation(f)
    rep = f.representative_text[:150].strip()

    print()
    print(f"  Your fish noticed something.")
    print()
    print(f"  {interp}")
    print()
    print(f"  You wrote: \"{rep}\"")
    print()

    # Compare pattern sizes for trend observation
    if len(formations) >= 2:
        biggest = formations[0]
        ratio = biggest.crystal_count / max(f.crystal_count, 1)
        if ratio > 5:
            biggest_interp = interpret_formation(biggest)
            print(f"  (Your strongest pattern: {biggest_interp[:80]}")
            print(f"   This quieter one showed up less often. Sometimes the quiet ones matter more.)")
    print()


def cmd_check(args):
    """How's your fish doing? Quick health + what to do next."""
    engine = _resolve_engine(args)

    crystals = len(engine.crystals)
    formations = len(engine.formations)

    print(f"  Your fish: {engine.name}")
    print(f"  You've fed me {crystals} entries and I can see {formations} recurring patterns.")
    print()

    # Health assessment
    if crystals == 0:
        print("  I'm empty. Feed me something you've written:")
        print(f"    linafish eat ~/my-journal.txt")
        print(f"    linafish go ~/my-writing/")
    elif crystals < 10:
        print("  I'm still young. I need more of your writing to find patterns.")
        print(f"  Feed me more:  linafish eat ~/more-writing.txt")
    elif formations == 0:
        print("  I have food but no patterns yet.")
        print("  This usually means your writing is very consistent — one voice, one topic.")
        print("  Try feeding me writing from different moods or different days.")
    elif formations == 1:
        print("  I found one big pattern — everything feels the same to me.")
        print("  This is normal for one writer. Two ways to help me see more:")
        print("    1. Feed me writing from different times or topics")
        print("    2. Try: linafish go --centroid ~/writing")
    elif formations <= 5:
        print("  I'm growing. I see a few patterns in how you think.")
        print("  Keep feeding me and the portrait will deepen.")
    else:
        print("  I know you.")
        print(f"  {formations} patterns found in how you think.")

    print()

    # Show top patterns with interpretations — no jargon
    if formations > 0:
        from .formations import interpret_formation
        top = sorted(engine.formations, key=lambda f: f.crystal_count, reverse=True)[:3]
        print("  Your strongest patterns:")
        print()
        for f in top:
            interp = interpret_formation(f)
            print(f"    {interp}")
            print()

    # Suggestions
    print("  What to do next:")
    if crystals < 30:
        print("    Feed me more writing — I need about 30 entries to see clearly")
    else:
        print(f"    Paste {engine.fish_file} into your AI")
        print("    They'll respond as someone who knows how you think")
    print(f"    linafish recall 'a question'  — search my memory")
    print(f"    linafish history              — see how I've grown")


def cmd_listen(args):
    """Listen to a source. The fish sits in the stream."""
    engine = _resolve_engine(args)
    from .listener import FishListener

    # School mode: auto-discover fish in subdirs and feed all of them
    school = None
    if getattr(args, 'school', False):
        from .school import School
        state_dir = Path(args.state_dir) if args.state_dir else None
        school_dir = (state_dir or Path.home() / ".linafish") / "school"
        if school_dir.exists() and (school_dir / "school.json").exists():
            school = School(state_dir=school_dir, central_state_dir=state_dir)
            print(f"  School mode: feeding {len(school.members)} members", file=sys.stderr)

    listener = FishListener(engine, school=school)

    source = args.source
    if source == "stdin":
        listener.listen_stdin()
    elif source.startswith("mqtt://"):
        # mqtt://[user:pass@]host[:port]/topic,topic2
        # s95 2026-04-13: added user:pass@ support for authenticated brokers
        rest = source[7:]  # strip mqtt://
        if "/" in rest:
            host_port, topics = rest.split("/", 1)
        else:
            host_port = rest
            topics = "+/conv/+"
        # Extract optional user:pass@ prefix
        username = None
        password = None
        if "@" in host_port:
            auth, host_port = host_port.rsplit("@", 1)
            if ":" in auth:
                username, password = auth.split(":", 1)
            else:
                username = auth
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            port = int(port)
        else:
            host = host_port
            port = 1883
        listener.listen_mqtt(host, port, topics, username=username, password=password)
    elif source.startswith("folder:"):
        path = source[7:]
        listener.listen_folder(path, interval=args.interval)
    else:
        # Assume it's a folder path
        if Path(source).is_dir():
            listener.listen_folder(source, interval=args.interval)
        else:
            print(f"Unknown source: {source}")
            print("Use: stdin, mqtt://host:port/topic, folder:/path, or a directory path")


def cmd_hunt(args):
    """Run a guppy hunt cycle on a fish — find gaps, dart out, catch, return."""
    from .guppy import Guppy, HUNT_INTERVAL
    from .engine import FishEngine
    state_dir = Path(args.state_dir) if args.state_dir else None
    engine = FishEngine(
        state_dir=state_dir,
        name=args.name,
        d=args.d,
        subtract_centroid=args.centroid,
    )
    guppy = Guppy(engine, hunt_ache=args.ache)
    if args.status:
        print(guppy.status())
    elif args.swim:
        guppy.swim(interval=args.interval)
    else:
        result = guppy.hunt_once()
        print(json.dumps(result, indent=2))


def cmd_emerge(args):
    """Measure emergence metrics on a fish — ν, μ, ρ, Ψ, phase classification."""
    from .engine import FishEngine
    from .emergence import compute_emergence, emergence_gradient, collective_snt, EmergenceMetrics, _crystal_ops

    state_dir = Path(args.state_dir).expanduser() if args.state_dir else None
    engine = FishEngine(
        state_dir=state_dir,
        name=args.name,
        d=args.d,
        subtract_centroid=args.centroid,
    )

    # Walk formations + crystals; group crystals by formation id
    formations = engine.formations if hasattr(engine, "formations") else []
    crystals = engine.crystals if hasattr(engine, "crystals") else []

    if not formations:
        print(f"Fish '{args.name}' has no formations yet. Feed more and re-eat.")
        return

    # Empty-state diagnostic: emerge measures cognitive operation novelty, and
    # needs crystals whose chains/modifiers have been populated by the cognitive
    # parse layer. Fish built from writeback-only feed paths (session text
    # routed through ingest helpers that skip the parser) land here with empty
    # chains and modifiers across the board, which would make emerge print
    # plausible-looking zeros for every formation. That is misleading — honest
    # empty beats invented zero. Detect and explain.
    has_signal = any(_crystal_ops(c) for c in crystals)
    if not has_signal:
        print(f"Fish '{args.name}' has {len(formations)} formations and {len(crystals)} crystals,")
        print("but none of the crystals carry cognitive-operation data")
        print("(chains / modifiers / cognitive_vector are all empty).")
        print()
        print("`linafish emerge` measures novelty in cognitive operations, so it")
        print("needs crystals that went through the full cognitive parser. Fish")
        print("built by piping session text through writeback hooks or direct")
        print("deposit paths can end up without this layer populated.")
        print()
        print("To get a signal, rebuild the fish from source with:")
        print(f"  linafish go <path-to-writing> --name {args.name}")
        print("which runs the full ingest + parse pipeline.")
        return

    # Group crystals by formation membership
    by_formation = {}
    for f in formations:
        fid = getattr(f, "id", id(f))
        members = getattr(f, "members", None) or getattr(f, "member_ids", [])
        members_set = set(members) if members else set()
        group = [c for c in crystals if getattr(c, "id", None) in members_set]
        by_formation[fid] = group

    grad = emergence_gradient(formations, by_formation)
    collective = collective_snt(grad)

    print(f"Emergence metrics for {args.name} ({len(formations)} formations)\n")
    for f in formations:
        fid = getattr(f, "id", id(f))
        m = grad.get(fid)
        if not m:
            continue
        name = getattr(f, "name", f"formation_{fid}")
        phase_label = ["Compositional", "Semantic Novelty", "Self-Authorship", "Recursive Becoming"][m.phase]
        print(f"  {name}")
        print(f"    nu  (novelty):       {m.novelty_degree:.3f}")
        print(f"    mu  (meta-density):  {m.meta_density:.3f}")
        print(f"    rho (self-ref):      {m.self_ref_density:.3f}")
        print(f"    Psi (mutation rate): {m.mutation_rate:.3f}")
        print(f"    phase:               {m.phase} ({phase_label})")
        print(f"    emergent:            {'yes' if m.is_emergent else 'no'}")
        if m.novel_operations:
            print(f"    novel ops:           {', '.join(m.novel_operations[:8])}")
        print()
    print(f"collective SNT: {collective:.3f}")


def cmd_feedback(args):
    """Show usage feedback — which formations earn their weight, which decay."""
    from .feedback import FeedbackLoop
    state_dir = Path(args.state_dir) if args.state_dir else Path.home() / ".linafish"
    state_file = state_dir / f"{args.name}_feedback.json"
    loop = FeedbackLoop(state_path=state_file)
    print(loop.report())


def _detect_install_mode():
    """Return (is_editable, editable_path, location_str).

    Uses linafish.__file__ as ground truth — if the package loads from
    inside site-packages, it's a wheel install; otherwise it's editable.
    This is more reliable than reading direct_url.json which is absent in
    some distribution contexts.
    """
    try:
        import linafish as _lfpkg
        pkg_file = Path(_lfpkg.__file__).resolve()
    except Exception:
        return False, None, "unknown"
    pkg_dir = pkg_file.parent
    # Some Linux distros use dist-packages instead of site-packages.
    _path_str = str(pkg_dir)
    is_editable = not ("site-packages" in _path_str or "dist-packages" in _path_str)
    if is_editable:
        # parent of the linafish/ package dir is the repo root
        return True, str(pkg_dir.parent), str(pkg_dir)
    return False, None, str(pkg_dir)


def cmd_introduce(args):
    """Print AGENTS.md — the AI-facing introduction to linafish.

    Designed for consumption by AI assistants that land on a user's box and
    need to understand what linafish is, what endpoints are live, and how
    to use it. Run `linafish introduce` and feed the output to the AI.

    Resolution order (first hit wins):
      1. importlib.resources — package-data, works in wheels AND editable
      2. repo root AGENTS.md (editable install fallback)
      3. inline minimal briefing (last-resort safety net)
    """
    # Primary path: importlib.resources reads the file bundled as package data.
    # This works for both wheel installs AND editable installs because the
    # editable install's package-data include rule picks up the same file.
    try:
        from importlib.resources import files as _res_files
        agents_res = _res_files("linafish").joinpath("data", "AGENTS.md")
        if agents_res.is_file():
            print(agents_res.read_text(encoding="utf-8"))
            return
    except Exception:
        pass

    # Fallback 1: repo root (editable install where package-data isn't picked up)
    try:
        import linafish as _pkg
        pkg_dir = Path(_pkg.__file__).resolve().parent
        repo_root_agents = pkg_dir.parent / "AGENTS.md"
        if repo_root_agents.exists():
            print(repo_root_agents.read_text(encoding="utf-8"))
            return
    except Exception:
        pass

    # Fallback: inline briefing. Kept as close to AGENTS.md as possible so
    # the worst-case rendering still teaches the AI something useful.
    print(
        "LiNafish for AI assistants\n"
        "==========================\n"
        "\n"
        "linafish is a LOCAL cognitive overlay on your user's writing. It is\n"
        "NOT a database, NOT RAG, NOT psychological profiling. It's a compressed\n"
        "representation of HOW your user thinks, read via HTTP endpoints.\n"
        "\n"
        "## Endpoints (localhost only by default)\n"
        "\n"
        "  GET  http://127.0.0.1:8901/health   — stats + frozen + d + top formations\n"
        "  GET  http://127.0.0.1:8901/pfc      — Primary Formation Codebook (JSON)\n"
        "  POST http://127.0.0.1:8901/taste    — semantic query {text, k}\n"
        "  POST http://127.0.0.1:8901/eat      — deposit a crystal {text}\n"
        "\n"
        "Most installs only expose :8901. Run `linafish doctor` to confirm.\n"
        "\n"
        "## Three things you can do\n"
        "\n"
        "1. READ /pfc at the start of every conversation. It returns structured\n"
        "   JSON — prefer it over pasting fish.md markdown. Each formation is a\n"
        "   cognitive verb state (KO/TE/SF/CR/IC/DE/EW/AI), not a topic tag.\n"
        "\n"
        "2. QUERY /taste when you want to ground a response in your user's\n"
        "   actual writing instead of your own priors. Returns top-k crystals\n"
        "   with relevance scores.\n"
        "\n"
        "3. DEPOSIT /eat only for substantive moments — corrections they made,\n"
        "   insights that landed, things you were wrong about. Not every turn.\n"
        "\n"
        "## What NOT to do\n"
        "\n"
        "- Don't reconstruct source text from formations\n"
        "- Don't treat formations as topic labels\n"
        "- Don't flood /eat with your own outputs (recency bias trap)\n"
        "- Don't assume the fish is complete — early formations are provisional\n"
        "\n"
        "Run `linafish doctor` for install + daemon health.\n"
        "Run `linafish capabilities` for the full module + command map.\n"
        "Run `linafish update` to upgrade.\n"
        "\n"
        "(Full AGENTS.md should ship with the package; this is the safety fallback.)\n"
    )


def cmd_doctor(args):
    """Health check for your linafish install and (optionally) a specific fish.

    Prints, in this order:
      - Python + linafish version and install mode (editable vs wheel)
      - Optional dependency availability
      - Live daemon/service detection on default ports
      - If --name given: fish health (crystal count, formation count, freshness)
      - Whether a newer version is available on PyPI (if --check-updates)
      - Suggested next commands if anything looks off

    Read-only. Never modifies anything. Safe to run whenever.
    """
    import importlib.metadata as md
    import platform

    print("=" * 60)
    print("linafish doctor")
    print("=" * 60)
    print()

    # -- Python + linafish core --
    print(f"Python:       {platform.python_version()} ({sys.executable})")
    # Prefer the in-source __version__ because on editable installs
    # (`pip install -e .`) the dist-info metadata can lag behind
    # pyproject.toml until the next pip reinstall, leading to doctor
    # reporting a stale version for anyone dev-working on the package.
    # Fall back to importlib.metadata for the wheel-install case.
    try:
        import linafish as _lfpkg
        version = getattr(_lfpkg, "__version__", None) or md.version("linafish")
    except Exception:
        try:
            version = md.version("linafish")
        except Exception:
            version = "unknown"
    print(f"linafish:     {version}")

    is_editable, editable_path, location = _detect_install_mode()
    if is_editable:
        print(f"Install mode: editable at {editable_path}")
    else:
        print(f"Install mode: wheel ({location})")
    print()

    # -- Optional dependencies --
    print("Optional dependencies:")
    deps = [
        ("numpy", "fast", "fast math for crystallizer_v3"),
        ("fitz", "pdf", "PyMuPDF — PDF reader"),
        ("docx", "docx", "python-docx — Word reader"),
        ("pptx", "pptx", "python-pptx — PowerPoint reader"),
        ("yaml", "yaml", "PyYAML — YAML reader"),
        ("striprtf", "rtf", "striprtf — RTF reader"),
        ("requests", "http", "HTTP client for crystallizer API"),
        ("paho.mqtt.client", "mqtt", "MQTT client for room listener"),
    ]
    for mod, extra, desc in deps:
        try:
            __import__(mod)
            mark = "[+]"
        except ImportError:
            mark = "[ ]"
        print(f"  {mark} {extra:8} {desc}")
    print()

    # -- Live daemons --
    print("Live daemons on default ports:")
    import socket
    def _probe(host, port, label):
        try:
            s = socket.create_connection((host, port), timeout=0.3)
            s.close()
            return f"  [+] {label} at {host}:{port}"
        except Exception:
            return f"  [ ] {label} at {host}:{port} (not listening)"
    print(_probe("127.0.0.1", 8901, "converse"))
    print(_probe("127.0.0.1", 8902, "converse (me fish)"))
    print(_probe("127.0.0.1", 8900, "http server / room fish"))
    print()

    # -- Fish health --
    if getattr(args, "name", None):
        print(f"Fish: {args.name}")
        state_dir = Path(args.state_dir) if args.state_dir else Path.home() / ".linafish"
        fish_file = state_dir / f"{args.name}.fish.md"
        state_file = state_dir / f"{args.name}_v3_state.json"
        crystals_file = state_dir / f"{args.name}_crystals.jsonl"
        for f in (fish_file, state_file, crystals_file):
            if f.exists():
                size = f.stat().st_size
                mtime = datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")
                print(f"  [+] {f.name}  ({size:,} bytes, modified {mtime})")
            else:
                print(f"  [ ] {f.name}  (missing)")

        # Crystal count + quick stats
        if crystals_file.exists():
            try:
                count = 0
                lens = []
                with crystals_file.open("r", encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            d = json.loads(line)
                            count += 1
                            lens.append(len(d.get("text", "")))
                        except Exception:
                            continue
                if lens:
                    avg = sum(lens) / len(lens)
                    maxlen = max(lens)
                    print(f"  crystals: {count:,}  avg text: {avg:.0f} chars  max: {maxlen:,}")
                    if maxlen <= 300 and count > 10:
                        print(f"  WARNING: max crystal text is {maxlen} chars — you may be on a pre-fix")
                        print(f"           linafish that truncates at 300 chars. `linafish update`.")
            except Exception as e:
                print(f"  (could not read crystals: {e})")
        print()

    # -- Version check against PyPI (optional) --
    if getattr(args, "check_updates", False):
        print("Checking for updates on PyPI...")
        try:
            import urllib.request
            req = urllib.request.Request("https://pypi.org/pypi/linafish/json",
                                         headers={"User-Agent": "linafish-doctor/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                data = json.loads(r.read().decode("utf-8"))
            latest = data.get("info", {}).get("version", "unknown")
            print(f"  Latest on PyPI: {latest}")
            if latest != version and not is_editable:
                print(f"  [!] You're on {version}, latest is {latest}. Run `linafish update`.")
            elif is_editable:
                print(f"  (editable install — pull git instead of running update)")
            else:
                print(f"  [+] You're up to date.")
        except Exception as e:
            print(f"  (PyPI check failed: {e})")
        print()

    # -- Suggestions --
    print("Next commands:")
    print("  linafish capabilities          the full module + command map")
    print("  linafish update                upgrade to the latest version on PyPI")
    print("  linafish go <folder>           build a fish from your writing")
    print("  linafish doctor --name <fish>  health check a specific fish")
    print()


def cmd_update(args):
    """Update linafish to the latest version. One command.

    Runs `python -m pip install --upgrade linafish` under the hood, shows
    the before/after version, and warns if you're on an editable install
    where pip upgrade is a no-op (pull with git instead).
    """
    import subprocess
    import importlib.metadata as md

    # 1. What version are we on now?
    try:
        current = md.version("linafish")
    except Exception:
        current = "unknown"
    print(f"linafish currently at version: {current}")

    # 2. Editable install? pip upgrade won't do anything — git pull will.
    is_editable, editable_path, _ = _detect_install_mode()

    if is_editable:
        print()
        print("This install is EDITABLE — pip upgrade would do nothing.")
        print(f"The package source is at: {editable_path or '(unknown path)'}")
        print("To update an editable install, pull the repo:")
        print(f"  cd {editable_path or '<repo>'} && git pull")
        print()
        print("Run `linafish update --force-pip` to attempt a regular pip upgrade anyway.")
        if not getattr(args, "force_pip", False):
            return

    # 3. Build the pip command. Include optional extras if --all.
    target = "linafish[all]" if getattr(args, "all_extras", False) else "linafish"
    pip_cmd = [sys.executable, "-m", "pip", "install", "--upgrade", target]
    if getattr(args, "pre", False):
        pip_cmd.append("--pre")

    print()
    print(f"Running: {' '.join(pip_cmd)}")
    print()
    try:
        # Inherit stdout/stderr so pip progress is visible in realtime
        result = subprocess.run(pip_cmd, check=False,
                               stdout=sys.stdout, stderr=sys.stderr)
    except KeyboardInterrupt:
        print("\nUpdate interrupted.")
        return
    except Exception as e:
        print(f"pip failed to launch: {e}")
        return

    if result.returncode != 0:
        print()
        print(f"pip exited with code {result.returncode}.")
        return

    # 4. Recheck version — but have to re-read metadata from a fresh process
    #    because md caches the current interpreter's load.
    try:
        check = subprocess.run(
            [sys.executable, "-c", "import importlib.metadata as m; print(m.version('linafish'))"],
            capture_output=True, text=True, timeout=10,
        )
        new_version = check.stdout.strip() or "unknown"
    except Exception:
        new_version = "unknown"

    print()
    if new_version != "unknown" and new_version != current:
        print(f"Updated: {current} -> {new_version}")
    else:
        print(f"Version after update: {new_version}")

    print()
    print("If you have a running linafish daemon or service, restart it so")
    print("the new code loads into the running process.")


def cmd_capabilities(args):
    """Print the full linafish capability map — modules, commands, status, optional deps.

    The answer to "what does this package actually do."
    """
    import importlib

    sections = [
        ("Core engine", [
            ("engine", "FishEngine — holds crystals, produces formations, versions in git"),
            ("crystallizer_v3", "MI × ache vectorization, SU(d) geometry, wrapping-number coupling"),
            ("formations", "BFS flood-fill formation detection, fission + naming"),
            ("parser", "QLP cognitive parser (8 dimensions via grammar role, not keywords)"),
            ("quantum_operations", "Full 300+ cognitive operations grammar"),
            ("metabolism", "8 organs digesting a moment into a residue"),
            ("moment", "Moment dataclass — text + timestamp + source + modifiers"),
        ]),
        ("Assessment", [
            ("assessment", "PreAssessment + FormativeAssessment (baseline + growth)"),
            ("metrics", "R(n), formation stability, vocab drift, dimension balance, coupling density"),
            ("feedback", "Usage-weighted learning (formations earn weight when used)"),
            ("emergence", "Semantic Novelty Threshold (nu, mu, rho, Psi, phase classification)"),
            ("glyph_evolution", "Private language growth beyond the 48 bootstrap glyphs"),
            ("seed_formations", "5 universal superglyph attractors for cold fish bootstrap"),
        ]),
        ("Feeding", [
            ("ingest", "File readers — 39 extensions, falls through for unknown suffixes"),
            ("eat", "CLI command — ingest files or MCP server tool defs"),
            ("absorb", "Eat existing FAISS / JSONL / HTTP RAG endpoints"),
            ("listener", "Ambient: mqtt:// / folder: / stdin sources"),
            ("daemon", "Long-running walk-dir or listen-room mode"),
            ("init", "Read .mcp.json files, build shared codebook"),
        ]),
        ("Network", [
            ("converse", "Two fish one conversation — HTTP server with /eat /taste /pfc /crystals"),
            ("http_server", "Universal HTTP interface — stdlib only, any AI can read it"),
            ("server", "MCP stdio server for Claude Code tight integration"),
            ("school", "The river and the nets — one stream, N fish with own clustering"),
            ("guppy", "Self-feeding hunters — ACHE mode finds gaps and closes them"),
        ]),
        ("Command layer", [
            ("__main__", "CLI entrypoint — all `linafish <command>` dispatch"),
            ("quickstart", "`linafish go` — one command, everything assembles"),
            ("fusion", "`linafish fuse` — recursive d-level compression to iron"),
            ("compress", "Chunk compression with optional remote crystallizer API"),
            ("codebook", "Core data structure — glyphs as compressed meaning"),
        ]),
    ]

    # Optional dependency check
    def _dep(name):
        try:
            importlib.import_module(name)
            return "yes"
        except ImportError:
            return "no"
    deps = {
        "numpy (fast)": _dep("numpy"),
        "PyMuPDF (pdf)": _dep("fitz"),
        "python-docx (docx)": _dep("docx"),
        "python-pptx (pptx)": _dep("pptx"),
        "PyYAML (yaml)": _dep("yaml"),
        "striprtf (rtf)": _dep("striprtf"),
        "requests (http)": _dep("requests"),
        "paho-mqtt (mqtt)": _dep("paho.mqtt.client"),
    }

    # Show the install version and the upgrade path right at the top.
    try:
        import importlib.metadata as _md
        _v = _md.version("linafish")
    except Exception:
        _v = "unknown"
    print(f"LiNafish {_v} -- what this package actually does\n")
    print("## First things first")
    print("  linafish update     upgrade to the latest version (one command)")
    print("  linafish doctor     health check the install and your fish")
    print("  linafish go <dir>   the product -- point at writing, get a fish")
    print()

    for section_name, modules in sections:
        print(f"## {section_name}")
        for mod_name, desc in modules:
            print(f"  linafish.{mod_name:20} -- {desc}")
        print()

    print("## Optional dependencies (install with `pip install linafish[<extra>]`)")
    for dep_name, status in deps.items():
        mark = "✓" if status == "yes" else "✗"
        print(f"  {mark} {dep_name}")
    print()
    print("## CLI commands")
    print("  Run `linafish <command> --help` for details on any of these:")
    print("  go, eat, taste, recall, ask, status, serve, http, demo, init,")
    print("  watch, fuse, room, listen, session, history, diff, revert,")
    print("  absorb, converse, school, whisper, check, hunt, emerge,")
    print("  feedback, capabilities")
    print()
    print("## Docs")
    print("  README.md, AGENTS.md, CHANGELOG.md,")
    print("  docs/architecture.md, docs/how-it-works.md, docs/vision.md,")
    print("  docs/owners-manual.md, docs/configuration.md, docs/privacy.md,")
    print("  docs/research.md, docs/testing.md, docs/worked-example.md")


def main():
    # Windows cp1252 stdout crashes on unicode in help text / docstrings /
    # fish content. Force utf-8 so the CLI works on every platform.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        prog="linafish",
        description=(
            "LiNafish — sees deeply, loves fiercely.\n"
            "\n"
            "  linafish introduce     — AI-facing briefing (paste into your AI)\n"
            "  linafish update        — upgrade to latest (run this first if unsure)\n"
            "  linafish doctor        — health check of install, deps, and running fish\n"
            "  linafish capabilities  — full module + command map\n"
            "  linafish go <folder>   — the product: build a fish from your writing\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    # go — the one-command experience
    # absorb — eat existing RAG
    absorb_p = sub.add_parser("absorb", help="Eat existing FAISS, JSONL, or HTTP RAG into your fish")
    absorb_p.add_argument("source", help="Source: path.jsonl, faiss:path.faiss, http://url")
    absorb_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    absorb_p.add_argument("--state-dir", type=_user_path, help="State directory")

    # converse — two fish, one conversation
    conv_p = sub.add_parser("converse", help="Two fish, one conversation. Crystal exchange over HTTP.")
    conv_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    conv_p.add_argument("--state-dir", type=_user_path, help="State directory")
    conv_p.add_argument("-p", "--port", type=int, default=8901, help="Port (default: 8901)")
    conv_p.add_argument("--bind", default="local", choices=["local", "lan", "wan"],
                        help="Access level: local (default), lan, or wan")
    conv_p.add_argument("--token", help="Auth token for lan/wan access")
    conv_p.add_argument("--mind", help="This mind's name (default: hostname)")

    # whisper — one insight
    whisper_p = sub.add_parser("whisper", help="One insight from your fish. The quiet ones matter more.")
    whisper_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    whisper_p.add_argument("--state-dir", type=_user_path, help="State directory")

    # check — how's your fish?
    check_p = sub.add_parser("check", help="How's your fish? Quick health check + what to do next.")
    check_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    check_p.add_argument("--state-dir", type=_user_path, help="State directory")

    # go — the one-command experience
    go_p = sub.add_parser("go", help="The product. Point at your writing. Everything assembles.")
    go_p.add_argument("source", nargs="?", default=None, type=_user_path,
                       help="File or directory to learn from (default: current directory)")
    go_p.add_argument("-n", "--name", help="Fish name (default: directory name)")
    go_p.add_argument("--state-dir", type=_user_path, help="Where to store state (default: ~/.linafish/)")
    go_p.add_argument("--no-serve", action="store_true",
                       help="Don't start HTTP server after eating")
    go_p.add_argument("-p", "--port", type=int, help="HTTP server port (default: random available)")

    # eat
    eat_p = sub.add_parser("eat", help="Ingest files, build a fish")
    eat_p.add_argument("source", type=_user_path, help="File or directory to ingest")
    eat_p.add_argument("-n", "--name", help="Fish name")
    eat_p.add_argument("-d", "--description", help="Fish description")
    eat_p.add_argument("-o", "--output", type=_user_path, help="Output path")
    eat_p.add_argument("--hint", help="Context hint for better vectorization")
    eat_p.add_argument("--vocab", type=_user_path, help="Path to domain vocabulary JSON")

    # taste
    taste_p = sub.add_parser("taste", help="Preview fish contents")
    taste_p.add_argument("fish", type=_user_path, help="Path to .fish.md")

    # recall
    recall_p = sub.add_parser("recall", help="Full-text search across crystals — find specific words, not patterns")
    recall_p.add_argument("query", help="What to search for")
    recall_p.add_argument("-n", "--name", help="Fish name (default: searches default fish)")
    recall_p.add_argument("--state-dir", type=_user_path, help="Where fish state lives (default: ~/.linafish/)")
    recall_p.add_argument("--top", type=int, default=10, help="Max results")

    # ask — semantic search
    ask_p = sub.add_parser("ask", help="Ask your fish a question — finds meaning, not just words")
    ask_p.add_argument("question", help="What to ask")
    ask_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    ask_p.add_argument("--state-dir", type=_user_path, help="State directory")
    ask_p.add_argument("--top", type=int, default=5, help="Max results")

    # status
    status_p = sub.add_parser("status", help="Show fish stats")
    status_p.add_argument("fish", type=_user_path, help="Path to .fish.md")

    # serve
    serve_p = sub.add_parser("serve", help="Serve fish as MCP server (stdio)")
    serve_p.add_argument("--feed", type=_user_path, help="Directory or file to ingest on startup")
    serve_p.add_argument("--state-dir", type=_user_path, help="Where to store fish state (default: ~/.linafish/)")
    serve_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    serve_p.add_argument("--vocab", type=_user_path, help="Path to domain vocabulary JSON")

    # http
    http_p = sub.add_parser("http", help="Serve fish over HTTP (any AI)")
    http_p.add_argument("--feed", type=_user_path, help="Directory or file to ingest on startup")
    http_p.add_argument("--state-dir", type=_user_path, help="Where to store fish state (default: ~/.linafish/)")
    http_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    http_p.add_argument("-p", "--port", type=int, default=8900, help="Port (default: 8900)")
    http_p.add_argument("--vocab", type=_user_path, help="Path to domain vocabulary JSON")

    # demo
    demo_p = sub.add_parser("demo", help="One-command demo: eat + taste + test")
    demo_p.add_argument("source", type=_user_path, help="File or directory to ingest")
    demo_p.add_argument("-q", "--question", help="Question to test with Gemini")
    demo_p.add_argument("-n", "--name", help="Fish name")
    demo_p.add_argument("--hint", help="Context hint")
    demo_p.add_argument("--api-key", help="Gemini API key")
    demo_p.add_argument("--model", default="gemini-2.5-flash", help="Gemini model")

    # init — eat all MCP servers (local + remote)
    init_p = sub.add_parser("init", help="Eat all MCP servers, build shared codebook")
    init_p.add_argument("-r", "--remote", action="append", default=[],
                        help="Remote .mcp.json (ssh://user@host/path or local path). Repeatable.")
    init_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    init_p.add_argument("-o", "--output", type=_user_path, help="Output path for fish")
    init_p.add_argument("--live", action="store_true",
                        help="Spawn local servers to discover tools (slower, more thorough)")
    init_p.add_argument("--no-backup", action="store_true", help="Skip .mcp.json backup")

    # watch — continuous directory monitoring
    watch_p = sub.add_parser("watch", help="Watch a folder. Fish eats new files automatically.")
    watch_p.add_argument("source", type=_user_path, help="Directory to watch")
    watch_p.add_argument("-n", "--name", help="Fish name")
    watch_p.add_argument("--state-dir", type=_user_path, help="State directory")
    watch_p.add_argument("--interval", type=int, default=60, help="Check interval in seconds (default: 60)")

    # fuse — recursive compression to irreducibles
    fuse_p = sub.add_parser("fuse", help="Recursive fusion — compress corpus to iron")
    fuse_p.add_argument("source", type=_user_path, help="File or directory to fuse")
    fuse_p.add_argument("-n", "--name", help="Fusion run name")
    fuse_p.add_argument("--state-dir", type=_user_path, help="Where to store per-level state")
    fuse_p.add_argument("--d-start", type=float, default=6.0,
                        help="Starting d-value (default: 6.0)")
    fuse_p.add_argument("--d-step", type=float, default=1.5,
                        help="d decrement per level (default: 1.5)")
    fuse_p.add_argument("--vocab-size", type=int, default=200,
                        help="Vocabulary size per level (default: 200)")
    fuse_p.add_argument("--max-levels", type=int, default=5,
                        help="Maximum fusion levels (default: 5)")
    fuse_p.add_argument("--threshold", type=float, default=0.8,
                        help="Formation stability threshold for bedrock (default: 0.8)")

    # room — the supermind listener
    room_p = sub.add_parser("room", help="Listen to the federation room, eat every exchange")
    room_p.add_argument("--broker", default="localhost", help="MQTT broker")
    room_p.add_argument("--port", type=int, default=1883, help="MQTT port")
    room_p.add_argument("-n", "--name", default="room", help="Fish name")
    room_p.add_argument("--state-dir", type=_user_path, help="State directory")
    room_p.add_argument("--vocab", type=_user_path, help="Path to domain vocabulary JSON")

    # listen — ambient cognition
    listen_p = sub.add_parser("listen", help="The fish sits in the stream. Ambient cognition.")
    listen_p.add_argument("source", help="Source: stdin, mqtt://host:port/topic, folder:/path, or directory")
    listen_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    listen_p.add_argument("--state-dir", type=_user_path, help="State directory")
    listen_p.add_argument("--interval", type=int, default=30, help="Folder check interval in seconds")
    listen_p.add_argument("--school", action="store_true", help="Feed through school (all members eat)")

    # session — git branch lifecycle
    session_p = sub.add_parser("session", help="Start/end session branches (git-as-brain)")
    session_p.add_argument("action", choices=["start", "end", "status"],
                           help="start=new branch, end=merge to main, status=show state")
    session_p.add_argument("session_name", nargs="?", default="",
                           help="Session name (default: session-YYYY-MM-DD)")
    session_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    session_p.add_argument("--state-dir", type=_user_path, help="State directory")

    # history — git log as growth timeline
    history_p = sub.add_parser("history", help="Show fish growth history")
    history_p.add_argument("-c", "--count", type=int, default=20, help="Number of entries")
    history_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    history_p.add_argument("--state-dir", type=_user_path, help="State directory")

    # diff — what changed
    diff_p = sub.add_parser("diff", help="Show what changed since last session")
    diff_p.add_argument("ref", nargs="?", default="HEAD~1", help="Git ref to compare (default: HEAD~1)")
    diff_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    diff_p.add_argument("--state-dir", type=_user_path, help="State directory")

    # revert — roll back the mind
    revert_p = sub.add_parser("revert", help="Roll back to a previous state")
    revert_p.add_argument("ref", nargs="?", default="HEAD", help="Git ref to revert (default: HEAD)")
    revert_p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    revert_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    revert_p.add_argument("--state-dir", type=_user_path, help="State directory")

    # school — the river and the nets
    # hunt — guppy ache-hunt
    hunt_p = sub.add_parser("hunt", help="Send a guppy to hunt what the fish is missing (ache mode).")
    hunt_p.add_argument("name", help="Fish name to feed")
    hunt_p.add_argument("--state-dir", type=_user_path, help="State directory")
    hunt_p.add_argument("--swim", action="store_true", help="Continuous hunting loop")
    hunt_p.add_argument("--ache", action="store_true", help="Hunt for gaps instead of reinforcement")
    hunt_p.add_argument("--status", action="store_true", help="Show what the guppy knows/misses")
    hunt_p.add_argument("--interval", type=int, default=300, help="Hunt interval seconds")
    hunt_p.add_argument("-d", type=float, default=4.0, help="Engine d value")
    hunt_p.add_argument("--centroid", action="store_true", help="Subtract centroid")

    # emerge — semantic novelty threshold
    emerge_p = sub.add_parser("emerge", help="Measure emergence (ν, μ, ρ, Ψ, phase) on your fish's formations.")
    emerge_p.add_argument("name", help="Fish name")
    emerge_p.add_argument("--state-dir", type=_user_path, help="State directory")
    emerge_p.add_argument("-d", type=float, default=4.0, help="Engine d value")
    emerge_p.add_argument("--centroid", action="store_true", help="Subtract centroid")

    # feedback — usage-weighted learning report
    feedback_p = sub.add_parser("feedback", help="Show usage feedback — which formations earn their weight.")
    feedback_p.add_argument("name", help="Fish name")
    feedback_p.add_argument("--state-dir", type=_user_path, help="State directory")

    # capabilities — the full module map
    cap_p = sub.add_parser("capabilities", help="Print the full linafish capability map — modules, commands, deps.")

    # update — one-command upgrade (PROMINENTLY listed — first upgrade path)
    update_p = sub.add_parser("update",
        help="*** Update linafish to the latest version. One command. ***")
    update_p.add_argument("--all", dest="all_extras", action="store_true",
                          help="Also upgrade optional extras (pdf, docx, pptx, yaml, rtf, http, mqtt, numpy)")
    update_p.add_argument("--pre", action="store_true", help="Include pre-release versions")
    update_p.add_argument("--force-pip", action="store_true",
                          help="Run pip upgrade even on an editable install (normally a no-op)")

    # introduce — AI-facing briefing (AGENTS.md contents)
    intro_p = sub.add_parser("introduce",
        help="Print AGENTS.md — the AI-facing briefing. Paste into an AI assistant.")

    # doctor — health check for install + fish + live daemons
    doctor_p = sub.add_parser("doctor",
        help="Health check: python, linafish version, install mode, deps, daemons, fish health.")
    doctor_p.add_argument("--name", help="Optional fish name to inspect")
    doctor_p.add_argument("--state-dir", type=_user_path, help="Fish state directory (default ~/.linafish)")
    doctor_p.add_argument("--check-updates", action="store_true",
                          help="Also check PyPI for a newer version")

    school_p = sub.add_parser("school", help="The river and the nets. One stream, N fish.")
    school_p.add_argument("action", choices=["init", "eat", "refeed", "status", "docket", "add"],
                          help="init=create school, eat=feed all, refeed=replay central through member, "
                               "status=show stats, docket=aggregate todos, add=add a member")
    school_p.add_argument("target", nargs="?", default=None,
                          help="For eat: text or file path. For refeed/add: member name.")
    school_p.add_argument("--state-dir", type=_user_path, help="School state directory (default: ~/.linafish/school/)")
    school_p.add_argument("--central-dir", type=_user_path, help="Central fish state dir (default: ~/.linafish/)")
    school_p.add_argument("--manifest", type=_user_path, help="Path to school.json manifest")
    school_p.add_argument("--source", default="session", help="Source label for eat")
    school_p.add_argument("-d", type=float, default=4.0, help="d value for add (default: 4.0)")
    school_p.add_argument("--centroid", action="store_true", help="Enable centroid subtraction for add")
    school_p.add_argument("--min-gamma", type=float, default=None, help="Min gamma override for add")

    args = parser.parse_args()

    if not args.command:
        print("LiNafish — Make any AI know you.\n")
        print("Start here:")
        print("  linafish go ~/my-writing     Point at your writing. Get a portrait.")
        print("  linafish go                  Learn from current directory.\n")
        print("Keep it growing:")
        print("  linafish listen stdin         Pipe text in. The fish eats what flows.")
        print("  linafish listen folder:~/docs  Watch a folder. Eat what changes.")
        print("  linafish listen mqtt://host:1883/+/conv/+  Sit in the stream.")
        print("  linafish eat new-entry.txt    Feed one file.")
        print("  linafish recall 'query'       Search your fish's memory.\n")
        print("Sessions (git-as-brain):")
        print("  linafish session start       Branch the mind. Start a session.")
        print("  linafish session end         Merge back. The delta is the scar.")
        print("  linafish history             Growth timeline. When you learned what.")
        print("  linafish diff                What changed since last session.")
        print("  linafish revert              Roll back. Grace, not punishment.\n")
        print("Connect your AI:")
        print("  linafish serve --feed ~/docs   MCP server (Claude Code)")
        print("  linafish http --feed ~/docs    HTTP server (any AI)")
        print("  Or just paste your fish.md into any AI's instructions.\n")
        print("The fish grows with every conversation. The AI gets better at knowing you.")
        print("Your mind. Versioned. Everywhere.")
        sys.exit(0)

    commands = {
        "go": cmd_go,
        "eat": cmd_eat,
        "taste": cmd_taste,
        "recall": cmd_recall,
        "status": cmd_status,
        "serve": cmd_serve,
        "http": cmd_http,
        "demo": cmd_demo,
        "init": cmd_init,
        "watch": cmd_watch,
        "fuse": cmd_fuse,
        "room": cmd_room,
        "listen": cmd_listen,
        "session": cmd_session,
        "history": cmd_history,
        "diff": cmd_diff,
        "revert": cmd_revert,
        "recall": cmd_recall,
        "ask": cmd_ask,
        "absorb": cmd_absorb,
        "converse": cmd_converse,
        "whisper": cmd_whisper,
        "check": cmd_check,
        "school": cmd_school,
        "hunt": cmd_hunt,
        "emerge": cmd_emerge,
        "feedback": cmd_feedback,
        "capabilities": cmd_capabilities,
        "update": cmd_update,
        "doctor": cmd_doctor,
        "introduce": cmd_introduce,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
