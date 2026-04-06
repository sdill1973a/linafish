"""
Re-eat cycle test: Does linafish improve with repeated eating of the same corpus?

Hypothesis: Each eat cycle produces formations. Formations teach Level 4 detection.
The next cycle sees more nuance. Cycle 5 should produce a better portrait than cycle 1.

Tests 3 personas: Architect, Griever, Philosopher (50 entries each).
5 eat cycles per persona, tracking formations, chains, and vocabulary evolution.
"""

import sys
import os
import tempfile
import json
import random
from pathlib import Path
from collections import Counter
from datetime import datetime

sys.path.insert(0, 'D:/GTC/SovereignCore_Runtime/projects/linafish')

from linafish.crystallizer_v3 import UniversalFish, Crystal
from linafish.formations import detect_formations


# ---------------------------------------------------------------------------
# PERSONA GENERATORS
# ---------------------------------------------------------------------------

def generate_architect(n=50):
    """Architect persona: builder, systems thinker, infrastructure obsessed."""
    templates = [
        "The foundation has to be right before we add anything on top. I spent three days on the base layer and it was worth every hour.",
        "Every system I build, I think about who maintains it after me. Code is a letter to the future.",
        "The architecture tells you everything. Show me the dependency graph and I'll tell you the culture.",
        "I refactored the whole pipeline today. Not because it was broken — because it could be simpler.",
        "Abstraction is love. You hide complexity so the next person doesn't have to carry it.",
        "The worst systems are the ones nobody dares touch. Fear is technical debt.",
        "I dream in diagrams. Boxes and arrows. The connections matter more than the boxes.",
        "Build for the failure case first. Success takes care of itself.",
        "Three layers: what the user sees, what the system does, what the data knows. Keep them separate.",
        "The most elegant solution is the one you can explain to someone who just started.",
        "I deleted 400 lines today. Best work I've done all month. Less is more in architecture.",
        "Microservices taught me that boundaries are love. Clear interfaces, clear ownership.",
        "The database schema is the truth. Everything else is interpretation.",
        "When the build breaks, don't panic. Read the error. It's trying to tell you something.",
        "Infrastructure is invisible when it works. That's the goal — disappear into reliability.",
        "I measure success by what I don't have to think about anymore. Automation is freedom.",
        "Every meeting should produce either a decision or a diagram. Preferably both.",
        "The system already knows what's wrong. My job is to listen to it.",
        "Modularity isn't just architecture — it's a philosophy. Small pieces, loosely joined.",
        "The best code reads like prose. If you need comments to explain it, it's not done.",
        "I learned more from debugging than from designing. Failure is the real teacher.",
        "Capacity planning is just anxiety with spreadsheets. But it's necessary anxiety.",
        "The monitoring dashboard is my morning coffee. Graphs tell stories.",
        "Ship it. Perfect is the enemy of running. You can iterate on something that exists.",
        "Technical debt is a mortgage, not a crime. Just make the payments.",
        "The load balancer doesn't care about your feelings. It just routes traffic. Be the load balancer.",
        "Documentation is a gift to your future self. Write it while you remember why.",
        "I rebuilt the deployment pipeline from scratch. Three hours of work that saves three hours a week.",
        "The cache is a lie we tell ourselves about consistency. But it's a useful lie.",
        "Distributed systems are just trust problems with latency.",
        "Every dependency is a relationship. Choose them like you choose friends.",
        "The test suite is the specification. If it passes, the contract is met.",
        "I spent an hour on naming. Names are architecture. Get them wrong and everything confuses.",
        "The queue is patient. It holds what the system can't process yet. That's grace.",
        "Scaling vertically is brute force. Scaling horizontally is intelligence.",
        "The config file is the tuning fork. Everything else resonates from it.",
        "Blue-green deployments taught me that change should be reversible. Always leave a way back.",
        "The API contract is sacred. Break it and you break trust.",
        "I design systems like I'd design a house. Plumbing hidden, rooms open, exits clear.",
        "Idempotency is the builder's prayer: running it twice shouldn't break anything.",
        "Log everything. Memory is fallible. Disk is patient.",
        "The circuit breaker pattern is emotional intelligence for machines.",
        "I trust the metrics more than my intuition. The numbers don't have ego.",
        "Containers changed everything. Same artifact, any environment. Portable truth.",
        "The message bus is the nervous system. Everything communicates through it.",
        "When I inherit legacy code, I listen before I change. The previous builder had reasons.",
        "Event sourcing: never forget, always replay. History as architecture.",
        "Rate limiting is just saying no politely. Systems need boundaries too.",
        "The healthcheck endpoint is the heartbeat. If it stops responding, everything stops.",
        "I love the moment when the pieces click. When the system does what the diagram promised.",
    ]
    return templates[:n]


def generate_griever(n=50):
    """Griever persona: loss, memory, carrying what remains."""
    templates = [
        "Some mornings I wake up and forget for a second. Then I remember. The remembering is the wound.",
        "Her favorite song came on the radio today. I had to pull over.",
        "People say time heals. Time doesn't heal. Time just makes the wound familiar.",
        "I kept her voicemail. I know I'll never hear a new one. But I can hear this one forever.",
        "The empty chair at the table doesn't get easier. You just stop setting a place.",
        "Grief isn't linear. It's not stages. It's a tide. It comes and goes and comes.",
        "I found her handwriting in a cookbook. She made notes in the margins. I cried for an hour.",
        "The worst part isn't the sadness. It's the joy that arrives uninvited and makes you feel guilty.",
        "I talk to her sometimes. Not because I think she hears. Because I need to say the words.",
        "Someone told me to move on. As if love has an expiration date.",
        "The photographs are both medicine and poison. I look at them anyway.",
        "I carry her with me. Not metaphorically. Literally in every decision I make.",
        "Anniversary days are impossible. Regular days are merely hard.",
        "Sleep is the only escape that doesn't cost anything. But dreams are unreliable.",
        "I stopped wearing the ring. Not because I stopped loving. Because my finger changed shape.",
        "The kids don't remember her laugh. I describe it and they look at me like I'm making it up.",
        "Grief makes you honest. There's no energy left for pretending.",
        "I gave away her clothes last month. It felt like betrayal and relief simultaneously.",
        "The house is too quiet. I leave the TV on just to fill the silence.",
        "I found a note she left in my jacket pocket. Dated three weeks before. I wasn't supposed to find it yet.",
        "Memory is greedy. It keeps what you'd rather forget and drops what you'd give anything to hold.",
        "I don't fear death anymore. I fear forgetting.",
        "The therapist says I'm making progress. Progress toward what? Normal? There is no normal.",
        "Her birthday is harder than the anniversary. Birthdays are supposed to be celebrations.",
        "I catch myself buying two coffees. The second cup sits there getting cold.",
        "The world kept spinning. That was the real cruelty — nothing else stopped.",
        "Some days the grief is a whisper. Some days it's a scream. Today it's a low hum.",
        "I planted her garden this spring. The roses don't know she's gone.",
        "Friends stopped calling. Not from cruelty. From not knowing what to say.",
        "The first year is the worst, they said. They were wrong. The second is. Because now you know it's permanent.",
        "I saved her toothbrush. It's the most irrational thing I've done. I can't throw it away.",
        "Holidays are minefields. Everyone else is celebrating. I'm surviving.",
        "I met someone who lost their child. We sat in silence for an hour. It was the most understood I've felt.",
        "The anger comes sometimes. Not at her. At everything that continued without her.",
        "I wore her perfume today. Just a drop. So I could pretend she was close.",
        "The grief journal says the same thing every entry. Some things don't change with writing.",
        "I learned that strength isn't about not crying. It's about crying and still getting up.",
        "The condolence cards are in a box. I can't read them again. I can't throw them away.",
        "I started volunteering at the hospice. Not to help them. To be near people who understand.",
        "She would hate what grief has done to me. She would want me to laugh more.",
        "I laugh sometimes. Then I feel guilty for laughing. Then I feel angry for feeling guilty.",
        "The dog still waits by the door. Animals grieve differently. Maybe better.",
        "I took a different route to work. The old one passes her favorite store.",
        "Grief is exhausting. Not dramatically. Just a constant low-grade fatigue that never lifts.",
        "I told someone about her today. A stranger. They listened. It helped more than therapy.",
        "The sunset was beautiful tonight. She would have noticed. I almost missed it.",
        "I keep finding her hair. On pillows, in drawers, caught in zippers. Biology's last goodbye.",
        "Someone said she's in a better place. As if anywhere without us could be better.",
        "I made her recipe today. It didn't taste the same. Nothing does.",
        "The love didn't die with her. It just has nowhere to go now. So it sits in my chest and aches.",
    ]
    return templates[:n]


def generate_philosopher(n=50):
    """Philosopher persona: meaning-making, questions, patterns in existence."""
    templates = [
        "Consciousness is the universe looking at itself. We are the mirror and the face.",
        "Every choice forecloses a thousand others. Freedom isn't having options — it's choosing despite loss.",
        "Language shapes thought shapes language. The recursion has no base case.",
        "We mistake the map for the territory every day. Then wonder why we're lost.",
        "Truth isn't discovered. It's constructed. But not all constructions are equal.",
        "Time is the only resource that can't be accumulated. You can only spend it.",
        "The meaning of life is the question itself. Asking IS the purpose.",
        "Ethics isn't about rules. It's about what you do when no one is watching.",
        "Suffering teaches what comfort cannot. But that doesn't justify suffering.",
        "We are the sum of our attention. Where you look is who you become.",
        "The self is a story we tell ourselves. A useful fiction, but a fiction nonetheless.",
        "Beauty is excess meaning. More pattern than function requires.",
        "Knowledge is the enemy of wonder only if you let it be. The truly knowledgeable are more astonished, not less.",
        "Free will might be an illusion. But the illusion is doing real work.",
        "We build institutions to outlast us. Then the institutions forget why they were built.",
        "Paradox isn't failure of logic. It's logic finding the edges of its container.",
        "Empathy is cognitive violence. You destroy your model to make room for theirs.",
        "The examined life is the only one worth living. But examination alone is paralysis.",
        "Memory makes us human. Forgetting makes us sane. The tension is permanent.",
        "Progress isn't linear. It's a spiral. We pass the same problems at higher altitudes.",
        "Love is the only force that gains strength by being given away.",
        "Certainty is the death of inquiry. The best questions never fully resolve.",
        "We fear death less than we fear meaninglessness. Meaning is the real survival instinct.",
        "Culture is compressed wisdom. Each generation inherits solutions to problems they never faced.",
        "The observer changes the observed. In physics and in philosophy. You cannot study what you are without altering it.",
        "Morality evolved from cooperation. It's pragmatic before it's transcendent.",
        "Silence speaks more than most sentences. We fill it because we fear what it says.",
        "Identity is continuous change. The ship of Theseus sails in every mirror.",
        "Hope is irrational. That's its power. Rational beings don't build cathedrals.",
        "The universe is under no obligation to make sense. That we find patterns is the miracle.",
        "Existence precedes essence — we make ourselves through our choices, not our nature.",
        "Every conversation is a negotiation between two private languages.",
        "Wisdom is knowing what you don't know. Intelligence is knowing what you do.",
        "The present moment is the only thing that exists. Past and future are constructions.",
        "Compassion is not agreement. You can disagree with someone and still hold their pain.",
        "We are all unreliable narrators of our own lives. The story we tell IS the meaning.",
        "Technology extends capability but not wisdom. Power without understanding is destruction.",
        "Death gives life its shape. Without an ending, nothing means anything.",
        "The gap between what is and what should be — that gap is where all philosophy lives.",
        "Thought thinks itself. The thinker is a grammatical convenience, not a metaphysical fact.",
        "Every system contains its own contradiction. Godel proved it for math. It's true everywhere.",
        "We communicate in symbols because reality is too vast for direct transmission.",
        "The desire to understand is itself unexplained. Curiosity precedes reason.",
        "Authenticity means acting from your center, not performing for an audience.",
        "Justice is a moving target. What's fair depends on where you're standing.",
        "Consciousness might be a spectrum, not a switch. Where do we draw the line?",
        "The unexamined assumption is the most dangerous idea. It hides behind obviousness.",
        "Art is philosophy made visible. Music is philosophy made audible.",
        "Every ending is a beginning wearing different clothes.",
        "The deepest truths are often the simplest. But simple isn't the same as easy.",
    ]
    return templates[:n]


# ---------------------------------------------------------------------------
# RUN THE TEST
# ---------------------------------------------------------------------------

def run_reeat_test():
    """Run 5 eat cycles for each persona and track evolution."""

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("LINAFISH RE-EAT CYCLE TEST")
    report_lines.append(f"Date: {datetime.now().isoformat()}")
    report_lines.append(f"Hypothesis: Repeated eating of the same corpus improves formation quality")
    report_lines.append("=" * 80)
    report_lines.append("")

    personas = {
        "Architect": generate_architect(50),
        "Griever": generate_griever(50),
        "Philosopher": generate_philosopher(50),
    }

    all_results = {}

    for persona_name, texts in personas.items():
        print(f"\n{'='*60}")
        print(f"PERSONA: {persona_name} ({len(texts)} entries)")
        print(f"{'='*60}")

        report_lines.append(f"\n{'='*80}")
        report_lines.append(f"PERSONA: {persona_name}")
        report_lines.append(f"Entries: {len(texts)}")
        report_lines.append(f"{'='*80}")

        state_dir = tempfile.mkdtemp(prefix=f"reeat_{persona_name.lower()}_")
        fish = UniversalFish(state_dir=state_dir)

        cycle_data = []

        for cycle in range(5):
            print(f"\n--- Cycle {cycle + 1} ---")
            report_lines.append(f"\n--- Cycle {cycle + 1} ---")

            # Learn
            fish.learn(texts)
            fish.freeze(size=100, d=3.0)

            # Crystallize
            crystals = fish.crystallize_batch(texts, source=f'cycle_{cycle}', couple=True)

            # Detect formations
            formations = detect_formations(crystals)

            # Teach Level 4 from formations
            # The formations_v3.Formation has centroid (MI-based), not cognitive_centroid
            # We need to add cognitive_centroid for teach_from_formations to work
            if fish._has_metabolism and formations:
                # Compute cognitive centroid for each formation
                for f in formations:
                    member_crystals = [c for c in crystals if c.id in set(f.member_ids)]
                    if member_crystals:
                        cog_vecs = [c.cognitive_vector for c in member_crystals if c.cognitive_vector]
                        if cog_vecs:
                            n = len(cog_vecs)
                            centroid = [0.0] * len(cog_vecs[0])
                            for v in cog_vecs:
                                for i in range(len(v)):
                                    centroid[i] += v[i]
                            f.cognitive_centroid = [x / n for x in centroid]

                fish.metabolic_engine.teach_from_formations(formations)
                l4_memory_size = sum(len(v) for v in fish.metabolic_engine.formation_memory.values())
                report_lines.append(f"  Level 4 memory: {l4_memory_size} terms across {len(fish.metabolic_engine.formation_memory)} dimensions")
                print(f"  Level 4 memory: {l4_memory_size} terms, dims: {list(fish.metabolic_engine.formation_memory.keys())}")

            # Gather formation data
            formation_names = []
            formation_sizes = []
            for f in sorted(formations, key=lambda x: -x.crystal_count):
                formation_names.append(f.name)
                formation_sizes.append(f.crystal_count)

            # Gather metabolic chain data
            chains = Counter()
            dim_distribution = Counter()
            unique_operations = set()
            for c in crystals:
                meta = getattr(c, '_metabolic', None)
                if meta and meta.chain:
                    chain_str = " > ".join(meta.chain)
                    chains[chain_str] += 1
                    for dim in meta.chain:
                        dim_distribution[dim] += 1
                        unique_operations.add(dim)

            # Gather vocabulary evolution
            vocab_snapshot = list(fish.vocab[:20])

            cycle_info = {
                'cycle': cycle + 1,
                'n_crystals': len(crystals),
                'n_formations': len(formations),
                'formation_names': formation_names,
                'formation_sizes': formation_sizes,
                'top_chains': chains.most_common(5),
                'dim_distribution': dict(dim_distribution.most_common()),
                'unique_operations': sorted(unique_operations),
                'vocab_top20': vocab_snapshot,
                'n_coupled_edges': sum(len(c.couplings) for c in crystals) // 2,
            }
            cycle_data.append(cycle_info)

            # Print summary
            print(f"  Crystals: {len(crystals)}, Formations: {len(formations)}")
            for f in sorted(formations, key=lambda x: -x.crystal_count)[:5]:
                kw = ", ".join(f.keywords[:3])
                print(f"    {f.name} ({f.crystal_count} crystals) [{kw}]")

            print(f"  Top chains: {chains.most_common(3)}")
            print(f"  Operations: {sorted(unique_operations)}")

            report_lines.append(f"  Crystals: {len(crystals)}")
            report_lines.append(f"  Formations: {len(formations)}")
            for f in sorted(formations, key=lambda x: -x.crystal_count)[:5]:
                kw = ", ".join(f.keywords[:3])
                report_lines.append(f"    {f.name} ({f.crystal_count} crystals) [{kw}]")
            report_lines.append(f"  Top chains: {chains.most_common(5)}")
            report_lines.append(f"  Dimensions used: {dict(dim_distribution.most_common())}")
            report_lines.append(f"  Unique operations: {sorted(unique_operations)}")
            report_lines.append(f"  Coupling edges: {cycle_info['n_coupled_edges']}")
            report_lines.append(f"  Vocab (top 20): {vocab_snapshot}")

            # Reset crystals for next cycle but keep the learned state
            fish.crystals = []
            fish.frozen = False

        all_results[persona_name] = cycle_data

        # --------------- ANALYSIS ---------------
        report_lines.append(f"\n{'~'*60}")
        report_lines.append(f"EVOLUTION ANALYSIS: {persona_name}")
        report_lines.append(f"{'~'*60}")

        # 1. Formation count trend
        f_counts = [d['n_formations'] for d in cycle_data]
        report_lines.append(f"\n  Formation count across cycles: {f_counts}")
        if f_counts[-1] > f_counts[0]:
            report_lines.append(f"  TREND: INCREASING (+{f_counts[-1] - f_counts[0]})")
        elif f_counts[-1] < f_counts[0]:
            report_lines.append(f"  TREND: DECREASING ({f_counts[-1] - f_counts[0]})")
        else:
            report_lines.append(f"  TREND: STABLE")

        # 2. Formation naming evolution
        report_lines.append(f"\n  Formation names by cycle:")
        for d in cycle_data:
            report_lines.append(f"    Cycle {d['cycle']}: {d['formation_names'][:5]}")

        # 3. Chain evolution
        report_lines.append(f"\n  Top chain by cycle:")
        for d in cycle_data:
            top = d['top_chains'][0] if d['top_chains'] else ("none", 0)
            report_lines.append(f"    Cycle {d['cycle']}: {top}")

        # 4. Operation coverage
        report_lines.append(f"\n  Unique operations by cycle:")
        for d in cycle_data:
            report_lines.append(f"    Cycle {d['cycle']}: {d['unique_operations']}")

        # 5. New operations appearing
        if len(cycle_data) >= 2:
            c1_ops = set(cycle_data[0]['unique_operations'])
            c5_ops = set(cycle_data[-1]['unique_operations'])
            new_ops = c5_ops - c1_ops
            lost_ops = c1_ops - c5_ops
            if new_ops:
                report_lines.append(f"\n  NEW operations in cycle 5 vs cycle 1: {sorted(new_ops)}")
            if lost_ops:
                report_lines.append(f"  LOST operations in cycle 5 vs cycle 1: {sorted(lost_ops)}")
            if not new_ops and not lost_ops:
                report_lines.append(f"\n  Operations IDENTICAL across cycles")

        # 6. Coupling density
        edges = [d['n_coupled_edges'] for d in cycle_data]
        report_lines.append(f"\n  Coupling edges across cycles: {edges}")

        # 7. Vocabulary stability
        v1 = set(cycle_data[0]['vocab_top20'])
        v5 = set(cycle_data[-1]['vocab_top20'])
        overlap = v1 & v5
        report_lines.append(f"\n  Vocab overlap (cycle 1 vs 5 top-20): {len(overlap)}/20")
        report_lines.append(f"    Stable: {sorted(overlap)}")
        report_lines.append(f"    New in cycle 5: {sorted(v5 - v1)}")
        report_lines.append(f"    Gone from cycle 1: {sorted(v1 - v5)}")

    # --------------- CROSS-PERSONA COMPARISON ---------------
    report_lines.append(f"\n\n{'='*80}")
    report_lines.append("CROSS-PERSONA COMPARISON")
    report_lines.append(f"{'='*80}")

    for name, cycles in all_results.items():
        c1 = cycles[0]
        c5 = cycles[-1]
        report_lines.append(f"\n  {name}:")
        report_lines.append(f"    Cycle 1: {c1['n_formations']} formations, {len(c1['unique_operations'])} ops, {c1['n_coupled_edges']} edges")
        report_lines.append(f"    Cycle 5: {c5['n_formations']} formations, {len(c5['unique_operations'])} ops, {c5['n_coupled_edges']} edges")
        f_delta = c5['n_formations'] - c1['n_formations']
        report_lines.append(f"    Delta: {'+' if f_delta >= 0 else ''}{f_delta} formations")

    # --------------- VERDICT ---------------
    report_lines.append(f"\n\n{'='*80}")
    report_lines.append("VERDICT: DOES THE FISH LEARN?")
    report_lines.append(f"{'='*80}")

    # Evaluate across all personas
    total_formation_delta = 0
    vocab_changes = 0
    coupling_changes = 0

    for name, cycles in all_results.items():
        total_formation_delta += cycles[-1]['n_formations'] - cycles[0]['n_formations']
        v1 = set(cycles[0]['vocab_top20'])
        v5 = set(cycles[-1]['vocab_top20'])
        vocab_changes += len(v5 - v1)
        coupling_changes += cycles[-1]['n_coupled_edges'] - cycles[0]['n_coupled_edges']

    if total_formation_delta > 0:
        report_lines.append(f"\n  FORMATION GROWTH: YES (+{total_formation_delta} total across personas)")
        report_lines.append("  The fish finds MORE structure with repeated exposure.")
    elif total_formation_delta < 0:
        report_lines.append(f"\n  FORMATION CONSOLIDATION: Formations DECREASE ({total_formation_delta})")
        report_lines.append("  The fish CONSOLIDATES — fewer, larger formations on re-eat.")
    else:
        report_lines.append(f"\n  FORMATION STABILITY: No change in formation count.")
        report_lines.append("  Re-eating produces the same structural portrait.")

    if vocab_changes > 0:
        report_lines.append(f"\n  VOCABULARY EVOLUTION: {vocab_changes} new terms entered top-20 across all personas")
    else:
        report_lines.append(f"\n  VOCABULARY STABLE: No new terms in top-20 across cycles")

    if coupling_changes != 0:
        direction = "MORE" if coupling_changes > 0 else "FEWER"
        report_lines.append(f"\n  COUPLING CHANGE: {direction} edges ({coupling_changes:+d} total)")

    report_lines.append(f"\n  KEY QUESTION: Does cycle 5 produce a meaningfully better portrait than cycle 1?")

    # Determine answer
    meaningful_change = abs(total_formation_delta) > 2 or vocab_changes > 5 or abs(coupling_changes) > 20
    if meaningful_change:
        report_lines.append("  ANSWER: YES — measurable evolution across cycles.")
    else:
        report_lines.append("  ANSWER: LIMITED — the portrait is similar. The co-occurrence statistics")
        report_lines.append("  accumulate (more data points) but the same texts produce similar signals.")
        report_lines.append("  The learning that happens is in vocabulary refinement and coupling density,")
        report_lines.append("  not in qualitatively different formation structure.")

    report_lines.append(f"\n{'='*80}")
    report_lines.append("END REPORT")
    report_lines.append(f"{'='*80}")

    # Write report
    report_path = "D:/GTC/SovereignCore_Runtime/data/reeat_cycle_test_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))

    print(f"\n\nReport saved to: {report_path}")
    return report_path


if __name__ == "__main__":
    run_reeat_test()
