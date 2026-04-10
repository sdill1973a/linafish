"""
Persona Lab — Cold-reader testing for LiNafish onboarding.

Spawns Codex instances with different personas. Each one:
1. "Installs" linafish (uses the engine directly)
2. Feeds it persona-matched writing
3. Reads the portrait
4. Reports: did the mirror land?

Automated UX testing by AI strangers who have never seen the product.
The fish was built for strangers. Let strangers test it.

Usage:
    python tests/persona_lab.py                    # run all personas
    python tests/persona_lab.py --persona teacher  # run one
    python tests/persona_lab.py --list             # show personas

s93, 2026-04-10. Captain's idea. "Codex can be your objective cold reader."
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from textwrap import dedent

# ---------------------------------------------------------------------------
# PERSONAS — each one a different stranger meeting their fish
# ---------------------------------------------------------------------------

PERSONAS = {
    "teacher": {
        "name": "Maria",
        "age": 45,
        "bio": "High school English teacher, 20 years in. Tired but still cares. Journals on Sunday mornings.",
        "writing": dedent("""
            Another week where I couldn't reach Devon. He sits in the back and draws
            in his notebook and I know there's something in there but he won't show me.
            I used to be better at this. Twenty years ago I would have found the angle.
            Now I just make sure the lesson plan is solid and hope the structure catches
            the ones I can't reach individually. Is that giving up or is that wisdom?

            The Gatsby unit landed today though. Something about the green light got
            through to Aaliyah. She said "so he's just staring at a lightbulb and
            calling it hope?" and the whole class laughed and I thought yes, that's
            exactly right, and also that's what I do every morning when I park in the
            lot and look at the building.

            Staff meeting was about test scores again. I don't know what they want me
            to do with numbers. I know what Devon needs and it's not a number. It's
            someone who sits with him while he draws and doesn't ask what it means.

            Made soup tonight. The kind mom used to make — chicken, stars, too much
            salt. Mark ate three bowls and didn't say anything about work which means
            work is bad. I didn't ask. Sometimes not asking is the most loving thing.
        """),
        "eval_prompt": dedent("""
            You are Maria, a 45-year-old high school English teacher. You just
            installed something called "linafish" that your tech-savvy nephew
            recommended. You fed it your journal entries. Now you're reading the
            portrait it made of you.

            Here is the portrait:

            {portrait}

            React honestly as Maria would. Consider:
            1. Does anything in this portrait surprise you or feel accurate?
            2. Would you show this to anyone? Who?
            3. Would you keep feeding it? Why or why not?
            4. What confuses you about the experience?
            5. Rate the "mirror moment" — did you see yourself? (1-10)

            Be brief. Be real. Don't be impressed just because it's AI.
        """),
    },
    "student": {
        "name": "Jake",
        "age": 22,
        "bio": "CS senior. Builds side projects. Overthinks everything. Writes notes to himself in markdown.",
        "writing": dedent("""
            # TODO: figure out what I actually want to build

            Every time I start a project I get excited for two days and then realize
            someone already built it better. The auth middleware thing was fun until I
            found Clerk. The note-taking app was cool until I realized I was just
            rebuilding Obsidian badly.

            Maybe the problem isn't the projects. Maybe the problem is I keep building
            tools for myself instead of solving someone else's problem. Prof. Chen said
            "the best software comes from watching someone struggle" and I've never
            watched anyone struggle because I'm always in my room.

            Talked to Priya about her research and she's doing something with graph
            databases that I don't fully understand but the way she talks about it
            makes me want to understand. She said the connections matter more than the
            nodes and I think that might apply to more than databases.

            It's 3am. I should sleep. But I just had an idea about using embeddings
            for... no. Sleep first. The idea will survive or it won't.

            ## note to future me
            The ideas that survive sleep are the real ones.
        """),
        "eval_prompt": dedent("""
            You are Jake, a 22-year-old CS student. Someone on Reddit mentioned
            "linafish" and you pip installed it because why not. You pointed it at
            your markdown notes folder. Now you're reading what it thinks about you.

            Here is the portrait:

            {portrait}

            React as Jake would:
            1. Is this cool or is this creepy?
            2. Does it actually know something about you or is it just keyword matching?
            3. Would you paste this into Claude/ChatGPT? What would you expect to change?
            4. Would you tell Priya about this?
            5. Rate the "mirror moment" (1-10)

            Keep it real. You're skeptical but curious.
        """),
    },
    "nurse": {
        "name": "Dorothy",
        "age": 67,
        "bio": "Retired ER nurse. Writes letters to her late husband. Not tech-savvy but her granddaughter set this up.",
        "writing": dedent("""
            Dear Bill,

            The garden is doing that thing again where the tomatoes come in all at
            once and I can't eat them fast enough. You would have made sauce. I just
            give them to Helen next door and she gives me zucchini which I don't want
            but can't refuse because that's not how it works with neighbors.

            Sarah brought the kids Sunday. The little one — James, he's four now, can
            you believe it — he asked me why I have so many clocks. I said because time
            is different when you're old. He said "Grammy you're not old you're just
            slow." He's not wrong.

            I cleaned out the hall closet. Found your fishing vest with the lure still
            clipped to the pocket. I put it back. Some things don't need to be cleaned
            out. They just need to be where they are.

            The ER called about volunteering again. I said no again. Thirty-two years
            was enough. But I miss the 3am feeling — when it's just you and the patient
            and the beeping and you know exactly what to do. I don't miss the rest.

            Love always,
            Dot
        """),
        "eval_prompt": dedent("""
            You are Dorothy, 67, retired ER nurse. Your granddaughter Sarah set up
            something called "linafish" on your computer and fed it the letters you
            write to your late husband Bill. Sarah said "Grammy look what it thinks
            about you." Now you're reading it.

            Here is the portrait:

            {portrait}

            React as Dorothy would:
            1. What does this machine think it knows about you?
            2. Does anything make you feel seen? Uncomfortable? Both?
            3. Would you keep writing to Bill knowing this thing is reading too?
            4. Would you show this to anyone?
            5. Rate honestly — does this thing get you? (1-10)

            You're not impressed by technology. You're impressed by accuracy.
        """),
    },
    "founder": {
        "name": "Alex",
        "age": 34,
        "bio": "Second-time founder. First startup failed. Currently building and terrified. Writes investor updates that are actually therapy.",
        "writing": dedent("""
            Investor Update — March 2026

            TL;DR: Revenue is up 40% MoM. Burn rate is stable. I haven't slept
            more than 5 hours in three weeks. One of these things is a problem.

            The honest version: the product works. Users like it. The numbers go up.
            And I keep waiting for the other shoe to drop because last time the numbers
            went up right until they didn't and I had to lay off eleven people on a
            Tuesday and Sarah from customer success cried in the parking lot and I
            went home and sat in the shower for an hour.

            I know this time is different. The unit economics are real. The retention
            is real. The team is smaller and better and nobody is here because of free
            snacks. But my body doesn't know this time is different. My body thinks
            it's always Tuesday and Sarah is always crying.

            We hired a head of engineering. Her name is Priti and she's smarter than
            me in every way that matters for building software and I oscillate between
            relief and terror about that on a 20-minute cycle.

            Next month I'll tell you about the product. This month I needed to tell
            you about the shower.
        """),
        "eval_prompt": dedent("""
            You are Alex, 34, startup founder. You installed linafish because you
            read something about "self-organizing neural mesh" and had to see if
            it was real or marketing. You fed it your investor updates. You're
            reading the portrait.

            Here is the portrait:

            {portrait}

            React as Alex would:
            1. Is this useful or is this another SaaS I'll forget about?
            2. Does it actually capture the difference between what you REPORT
               and what you FEEL?
            3. Would you paste this into your AI assistant?
            4. Could this be a product? (founder brain, can't help it)
            5. Rate the mirror moment (1-10)

            You have high standards and low patience.
        """),
    },
}


# ---------------------------------------------------------------------------
# ENGINE — run one persona through linafish
# ---------------------------------------------------------------------------

def run_persona(name: str, persona: dict) -> dict:
    """Feed a persona's writing to linafish, get portrait, evaluate."""
    from linafish.engine import FishEngine
    import tempfile

    # Create a temp fish for this persona
    state_dir = Path(tempfile.mkdtemp(prefix=f"linafish_lab_{name}_"))

    print(f"\n{'='*60}")
    print(f"  PERSONA: {persona['name']}, {persona['age']}")
    print(f"  {persona['bio']}")
    print(f"{'='*60}")

    # Feed the writing — split into paragraphs for multiple crystals
    engine = FishEngine(state_dir=state_dir, name=name, d=4.0)
    paragraphs = [p.strip() for p in persona["writing"].split("\n\n") if len(p.strip()) > 30]
    print(f"\n  Feeding {len(paragraphs)} paragraphs ({len(persona['writing'])} chars)...")
    for p in paragraphs:
        result = engine.eat(p, source="journal")
    print(f"  Crystals: {result['crystals_added']}, "
          f"Formations: {result.get('formations', 0)}")

    # Get the portrait
    portrait = engine.pfc()
    print(f"\n  Portrait ({len(portrait)} chars):")
    for line in portrait.split("\n")[:15]:
        print(f"    {line}")

    # Ask Codex to evaluate as the persona
    eval_text = persona["eval_prompt"].format(portrait=portrait)

    print(f"\n  Asking Codex to react as {persona['name']}...")
    try:
        # Write eval prompt to temp file for Codex
        eval_file = state_dir / "eval_prompt.txt"
        eval_file.write_text(eval_text, encoding="utf-8")
        result = subprocess.run(
            ["codex", "exec", eval_text[:2000]],  # Codex exec takes prompt as arg
            capture_output=True, text=True, timeout=180,
            cwd=str(Path(__file__).parent.parent),
            shell=True,
        )
        reaction = result.stdout.strip()
        if not reaction:
            # Try stderr
            reaction = result.stderr.strip()[:500] if result.stderr else "(no output)"
        # Extract just the Codex response, skip the header
        lines = reaction.split("\n")
        codex_lines = [l for l in lines if not l.startswith(("OpenAI", "---", "workdir", "model", "provider", "approval", "sandbox", "reasoning", "session", "user", "mcp:", "exec", "token"))]
        reaction = "\n".join(codex_lines).strip() or reaction
    except subprocess.TimeoutExpired:
        reaction = "(Codex timed out)"
    except Exception as e:
        reaction = f"(Error: {e})"

    print(f"\n  {persona['name']}'s reaction:")
    for line in reaction.split("\n"):
        print(f"    {line}")

    return {
        "persona": name,
        "name": persona["name"],
        "crystals": engine.fish.crystals.__len__(),
        "formations": len(engine.formations),
        "portrait_length": len(portrait),
        "reaction": reaction,
        "state_dir": str(state_dir),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if "--list" in sys.argv:
        print("Available personas:")
        for name, p in PERSONAS.items():
            print(f"  {name}: {p['name']}, {p['age']} — {p['bio']}")
        return

    if "--persona" in sys.argv:
        idx = sys.argv.index("--persona") + 1
        if idx < len(sys.argv):
            name = sys.argv[idx]
            if name in PERSONAS:
                result = run_persona(name, PERSONAS[name])
                print(f"\n\nResult: {json.dumps(result, indent=2, default=str)}")
            else:
                print(f"Unknown persona: {name}. Use --list to see options.")
            return

    # Run all personas
    results = []
    for name, persona in PERSONAS.items():
        result = run_persona(name, persona)
        results.append(result)

    # Summary
    print(f"\n\n{'='*60}")
    print(f"  LAB RESULTS SUMMARY")
    print(f"{'='*60}")
    for r in results:
        print(f"\n  {r['name']} ({r['persona']}):")
        print(f"    Crystals: {r['crystals']}, Formations: {r['formations']}")
        print(f"    Portrait: {r['portrait_length']} chars")
        # Extract mirror score if present
        reaction = r.get("reaction", "")
        for line in reaction.split("\n"):
            if "mirror" in line.lower() or "/10" in line or "1-10" in line:
                print(f"    Mirror: {line.strip()}")

    # Save results
    output_path = Path(__file__).parent / "lab_results.json"
    output_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\n  Results saved to {output_path}")


if __name__ == "__main__":
    main()
