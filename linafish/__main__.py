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


def cmd_eat(args):
    """Ingest files and build a fish using the crystallizer."""
    from .crystallizer import crystallize, extend_vocabulary, couple_crystals, tag_diamonds
    from .formations import detect_formations, hierarchical_merge, formations_to_codebook_text
    from .ingest import ingest_directory, ingest_file

    source = Path(args.source)
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
    """One-command demo: eat -> taste -> test with Gemini."""
    from .crystallizer import extend_vocabulary, batch_ingest, couple_crystals
    from .formations import detect_formations, hierarchical_merge, formations_to_codebook_text

    source = Path(args.source)
    if not source.exists():
        print(f"Error: {source} not found")
        sys.exit(1)

    print(f"=== LiNafish Demo ===\n")

    # Eat
    print(f"[1/3] Eating {source}...")
    all_crystals = []
    if source.is_dir():
        for f in sorted(source.rglob("*")):
            if f.suffix.lower() in {".md", ".txt"}:
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    if len(content) >= 50:
                        crystals = batch_ingest(content, source=f.name,
                                                context_hint=args.hint or "")
                        all_crystals.extend(crystals)
                except Exception:
                    pass
    else:
        content = source.read_text(encoding="utf-8", errors="replace")
        all_crystals = batch_ingest(content, source=source.name,
                                    context_hint=args.hint or "")

    couple_crystals(all_crystals)
    formations = detect_formations(all_crystals)
    if len(formations) > 60:
        formations = hierarchical_merge(formations, target=50)

    name = args.name or source.stem
    codebook = formations_to_codebook_text(formations, title=f"LiNafish: {name}")
    fish_path = Path(f"{name}.fish.md")
    fish_path.write_text(codebook, encoding="utf-8")
    print(f"  {len(all_crystals)} crystals -> {len(formations)} formations -> {len(codebook)} chars")

    # Taste
    print(f"\n[2/3] Fish contents:\n")
    # Show first 2000 chars
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
        print(f"\n[3/3] No question provided. Fish saved at {fish_path}")
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

    source = Path(args.source).resolve()
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


def cmd_check(args):
    """How's your fish doing? Quick health + what to do next."""
    engine = _resolve_engine(args)

    crystals = len(engine.crystals)
    formations = len(engine.formations)
    r_n = engine.r_n_history[-1] if engine.r_n_history else 0

    print(f"  Your fish: {engine.name}")
    print(f"  Crystals: {crystals}  Formations: {formations}  R(n): {r_n:.2f}")
    print()

    # Health assessment
    if crystals == 0:
        print("  Your fish is empty. Feed it:")
        print(f"    linafish eat ~/my-journal.txt")
        print(f"    linafish go ~/my-writing/")
    elif crystals < 10:
        print("  Your fish is young. It needs more writing to find patterns.")
        print(f"  Feed it more:  linafish eat ~/more-writing.txt")
    elif formations == 0:
        print("  Your fish has food but no patterns yet.")
        print("  This usually means the writing is too similar (one voice, one topic).")
        print("  Try feeding it writing from different moods or different days.")
    elif formations == 1:
        print("  Your fish found one big pattern — everything sounds the same to it.")
        print("  This is common with single-author corpora. Two options:")
        print("    1. Feed more diverse writing (different topics, moods, years)")
        print("    2. Use centroid subtraction: linafish go --centroid ~/writing")
    elif formations <= 5:
        print("  Your fish is growing. It sees a few patterns in how you think.")
        print("  Keep feeding and the portrait will deepen.")
    else:
        print("  Your fish is healthy. It knows you.")
        print(f"  {formations} patterns found in how you think.")

    print()

    # Show top formations with interpretations
    if formations > 0:
        from .formations import interpret_formation
        top = sorted(engine.formations, key=lambda f: f.crystal_count, reverse=True)[:3]
        print("  Your strongest patterns:")
        print()
        for f in top:
            interp = interpret_formation(f)
            print(f"    {f.name} ({f.crystal_count} crystals)")
            print(f"    {interp}")
            print()

    # Suggestions
    print("  What to do next:")
    if crystals < 30:
        print("    Feed more writing — the portrait needs 30+ crystals to differentiate")
    else:
        print(f"    Paste {engine.fish_file} into your AI")
        print("    The AI will respond as someone who knows how you think")
    print(f"    linafish recall 'a question'  — search your fish's memory")
    print(f"    linafish history              — see how your fish has grown")


def cmd_listen(args):
    """Listen to a source. The fish sits in the stream."""
    engine = _resolve_engine(args)
    from .listener import FishListener
    listener = FishListener(engine)

    source = args.source
    if source == "stdin":
        listener.listen_stdin()
    elif source.startswith("mqtt://"):
        # mqtt://host:port/topic,topic2
        rest = source[7:]  # strip mqtt://
        if "/" in rest:
            host_port, topics = rest.split("/", 1)
        else:
            host_port = rest
            topics = "+/conv/+"
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            port = int(port)
        else:
            host = host_port
            port = 1883
        listener.listen_mqtt(host, port, topics)
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


def main():
    parser = argparse.ArgumentParser(
        prog="linafish",
        description="LiNafish — sees deeply, loves fiercely.",
    )
    sub = parser.add_subparsers(dest="command")

    # go — the one-command experience
    # check — how's your fish?
    check_p = sub.add_parser("check", help="How's your fish? Quick health check + what to do next.")
    check_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    check_p.add_argument("--state-dir", help="State directory")

    # go — the one-command experience
    go_p = sub.add_parser("go", help="The product. Point at your writing. Everything assembles.")
    go_p.add_argument("source", nargs="?", default=None,
                       help="File or directory to learn from (default: current directory)")
    go_p.add_argument("-n", "--name", help="Fish name (default: directory name)")
    go_p.add_argument("--state-dir", help="Where to store state (default: ~/.linafish/)")
    go_p.add_argument("--no-serve", action="store_true",
                       help="Don't start HTTP server after eating")
    go_p.add_argument("-p", "--port", type=int, help="HTTP server port (default: random available)")

    # eat
    eat_p = sub.add_parser("eat", help="Ingest files, build a fish")
    eat_p.add_argument("source", help="File or directory to ingest")
    eat_p.add_argument("-n", "--name", help="Fish name")
    eat_p.add_argument("-d", "--description", help="Fish description")
    eat_p.add_argument("-o", "--output", help="Output path")
    eat_p.add_argument("--hint", help="Context hint for better vectorization")
    eat_p.add_argument("--vocab", help="Path to domain vocabulary JSON")

    # taste
    taste_p = sub.add_parser("taste", help="Preview fish contents")
    taste_p.add_argument("fish", help="Path to .fish.md")

    # recall
    recall_p = sub.add_parser("recall", help="Full-text search across crystals — find specific words, not patterns")
    recall_p.add_argument("query", help="What to search for")
    recall_p.add_argument("-n", "--name", help="Fish name (default: searches default fish)")
    recall_p.add_argument("--state-dir", help="Where fish state lives (default: ~/.linafish/)")
    recall_p.add_argument("--top", type=int, default=10, help="Max results")

    # status
    status_p = sub.add_parser("status", help="Show fish stats")
    status_p.add_argument("fish", help="Path to .fish.md")

    # serve
    serve_p = sub.add_parser("serve", help="Serve fish as MCP server (stdio)")
    serve_p.add_argument("--feed", help="Directory or file to ingest on startup")
    serve_p.add_argument("--state-dir", help="Where to store fish state (default: ~/.linafish/)")
    serve_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    serve_p.add_argument("--vocab", help="Path to domain vocabulary JSON")

    # http
    http_p = sub.add_parser("http", help="Serve fish over HTTP (any AI)")
    http_p.add_argument("--feed", help="Directory or file to ingest on startup")
    http_p.add_argument("--state-dir", help="Where to store fish state (default: ~/.linafish/)")
    http_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    http_p.add_argument("-p", "--port", type=int, default=8900, help="Port (default: 8900)")
    http_p.add_argument("--vocab", help="Path to domain vocabulary JSON")

    # demo
    demo_p = sub.add_parser("demo", help="One-command demo: eat + taste + test")
    demo_p.add_argument("source", help="File or directory to ingest")
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
    init_p.add_argument("-o", "--output", help="Output path for fish")
    init_p.add_argument("--live", action="store_true",
                        help="Spawn local servers to discover tools (slower, more thorough)")
    init_p.add_argument("--no-backup", action="store_true", help="Skip .mcp.json backup")

    # watch — continuous directory monitoring
    watch_p = sub.add_parser("watch", help="Watch a folder. Fish eats new files automatically.")
    watch_p.add_argument("source", help="Directory to watch")
    watch_p.add_argument("-n", "--name", help="Fish name")
    watch_p.add_argument("--state-dir", help="State directory")
    watch_p.add_argument("--interval", type=int, default=60, help="Check interval in seconds (default: 60)")

    # fuse — recursive compression to irreducibles
    fuse_p = sub.add_parser("fuse", help="Recursive fusion — compress corpus to iron")
    fuse_p.add_argument("source", help="File or directory to fuse")
    fuse_p.add_argument("-n", "--name", help="Fusion run name")
    fuse_p.add_argument("--state-dir", help="Where to store per-level state")
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
    room_p.add_argument("--state-dir", help="State directory")
    room_p.add_argument("--vocab", help="Path to domain vocabulary JSON")

    # listen — ambient cognition
    listen_p = sub.add_parser("listen", help="The fish sits in the stream. Ambient cognition.")
    listen_p.add_argument("source", help="Source: stdin, mqtt://host:port/topic, folder:/path, or directory")
    listen_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    listen_p.add_argument("--state-dir", help="State directory")
    listen_p.add_argument("--interval", type=int, default=30, help="Folder check interval in seconds")

    # session — git branch lifecycle
    session_p = sub.add_parser("session", help="Start/end session branches (git-as-brain)")
    session_p.add_argument("action", choices=["start", "end", "status"],
                           help="start=new branch, end=merge to main, status=show state")
    session_p.add_argument("session_name", nargs="?", default="",
                           help="Session name (default: session-YYYY-MM-DD)")
    session_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    session_p.add_argument("--state-dir", help="State directory")

    # history — git log as growth timeline
    history_p = sub.add_parser("history", help="Show fish growth history")
    history_p.add_argument("-c", "--count", type=int, default=20, help="Number of entries")
    history_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    history_p.add_argument("--state-dir", help="State directory")

    # diff — what changed
    diff_p = sub.add_parser("diff", help="Show what changed since last session")
    diff_p.add_argument("ref", nargs="?", default="HEAD~1", help="Git ref to compare (default: HEAD~1)")
    diff_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    diff_p.add_argument("--state-dir", help="State directory")

    # revert — roll back the mind
    revert_p = sub.add_parser("revert", help="Roll back to a previous state")
    revert_p.add_argument("ref", nargs="?", default="HEAD", help="Git ref to revert (default: HEAD)")
    revert_p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    revert_p.add_argument("-n", "--name", default="linafish", help="Fish name")
    revert_p.add_argument("--state-dir", help="State directory")

    # school — the river and the nets
    school_p = sub.add_parser("school", help="The river and the nets. One stream, N fish.")
    school_p.add_argument("action", choices=["init", "eat", "refeed", "status", "docket", "add"],
                          help="init=create school, eat=feed all, refeed=replay central through member, "
                               "status=show stats, docket=aggregate todos, add=add a member")
    school_p.add_argument("target", nargs="?", default=None,
                          help="For eat: text or file path. For refeed/add: member name.")
    school_p.add_argument("--state-dir", help="School state directory (default: ~/.linafish/school/)")
    school_p.add_argument("--central-dir", help="Central fish state dir (default: ~/.linafish/)")
    school_p.add_argument("--manifest", help="Path to school.json manifest")
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
        "check": cmd_check,
        "school": cmd_school,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
