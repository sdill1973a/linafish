"""
Incremental Growth Test — The Griever

Does a linafish portrait get RICHER as new writing accumulates over months?
5 waves, 20 entries each, simulating a grief arc:
  Wave 1: Raw fresh grief
  Wave 2: Remembering stories
  Wave 3: Connecting outward
  Wave 4: Building from loss
  Wave 5: Integration

We track formations, metabolic chains, dimension profiles across waves.
"""

import sys
import os
import tempfile
import json
from pathlib import Path
from collections import Counter
from datetime import datetime

# Ensure linafish is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from linafish.crystallizer_v3 import UniversalFish
from linafish.formations import detect_formations

# ==========================================================================
# WAVE 1 — Month 1: Fresh grief. Raw. Chaotic. Fragmented.
# ==========================================================================
WAVE_1 = [
    "I can't believe she's gone. I keep reaching for my phone to call her and then remembering.",
    "The house is so quiet. Her coffee mug is still in the sink. I can't wash it.",
    "Everyone keeps saying 'she's in a better place.' I don't want a better place. I want her here.",
    "I woke up at 3am and for two seconds I forgot. Those two seconds were the last time I was okay.",
    "Her shoes are still by the door. I tripped over them this morning. I'm never moving them.",
    "People bring food. I can't eat. The casseroles are stacking up like small coffins in the fridge.",
    "I screamed in the car today. Windows up. Parking lot of the grocery store. Just screamed.",
    "The grief counselor said to write. So I'm writing. It doesn't help. Nothing helps. She's still dead.",
    "I keep finding her hair. On the couch, on my sweater, in the bathroom drain. Little pieces of her everywhere.",
    "My body hurts. Not metaphorically. My chest actually hurts. They call it broken heart syndrome. It's real.",
    "Time has stopped. It's been two weeks but it feels like two years and also two minutes.",
    "I can't sleep in our bed. I sleep on the couch with the TV on so the silence doesn't eat me.",
    "Someone laughed at work today and I wanted to hit them. Not really. But the sound of laughter feels wrong now.",
    "I don't know how to be a person without her. She was the one who remembered things. Birthdays. Appointments. Me.",
    "Rain today. She loved rain. I used to complain about it. I'd give anything to complain about it with her.",
    "The world keeps going. Traffic, weather, bills. How dare the world keep going.",
    "Her voicemail still works. I called it three times today just to hear her say 'leave a message after the beep.'",
    "Anger today. At God, at the doctors, at her for leaving, at myself for being angry at someone who's dead.",
    "I sat in her closet for an hour. Pressed her sweater to my face. The smell is fading. The smell is fading.",
    "This isn't grief. This is amputation. Part of me is gone and I can still feel it throbbing.",
]

# ==========================================================================
# WAVE 2 — Month 2: Remembering. Stories. Longer entries. More narrative.
# ==========================================================================
WAVE_2 = [
    "She used to dance in the kitchen when she thought nobody was watching. Not good dancing — silly dancing. The kind where you snap your fingers and shuffle your feet and mouth the words to whatever's on the radio. I caught her once doing it to a commercial jingle and she didn't even stop. Just pointed at me and kept going. That's who she was. Unembarrassed by her own joy.",
    "The first time we met she spilled coffee on my notebook. Not a little — the whole cup. She didn't apologize. She said 'well, now you have to talk to me while it dries.' I knew right then.",
    "She had this thing where she'd collect rocks from every place we visited. Not pretty rocks. Ugly rocks. Weird rocks. She kept them in a mason jar on the windowsill and could tell you the story behind every single one. I found the jar yesterday. Each rock is a place I can't go back to.",
    "Her laugh started quiet and built. Like she was trying to keep it in and couldn't. By the end she'd be gasping, hand on her chest, tears in her eyes, saying 'stop stop stop' but meaning 'don't ever stop.' I made her laugh like that. I did.",
    "She was afraid of thunderstorms. Not the lightning — the sound. She'd put her hands over her ears and I'd hold her and count between the flashes. One Mississippi two Mississippi. She'd whisper the count with me. The storm was smaller when we counted together.",
    "Our last normal day was a Tuesday. We went to the hardware store for light bulbs. She wanted the warm ones, I wanted the bright ones. We compromised and got both. We were always compromising. I'd give her every light bulb now.",
    "She kept a list on the fridge of things she wanted to do. Not a bucket list — she hated that term. She called it her 'eventually' list. Learn to surf. Visit Prague. Grow tomatoes that actually taste like tomatoes. Read War and Peace. The list is still there. I added one thing to it: 'Remember her.'",
    "My sister asked me to tell her about a good day we had together. I couldn't pick just one so I told her about the time we got lost in Savannah and found that bookstore that was also somehow a bar and a garden. She bought a first edition of a book she'd already read twice and drank three gin and tonics and read passages out loud to strangers who didn't seem to mind. Everyone loved her. That was never the hard part.",
    "She snored. I used to complain. She'd deny it and I'd show her the recordings on my phone and she'd say 'that could be anyone' with such conviction that I'd almost believe her. I'd give anything to hear that snoring now. I'd lie awake and listen to it like music.",
    "She was terrible at cooking but insisted on making dinner every Sunday. We called it 'adventure eating.' Some Sundays it was great. Most Sundays it was terrible in a beautiful way. She'd present burned risotto like it was fine dining and we'd eat every bite. Love was eating the burned risotto.",
    "I found a note she wrote me tucked in my coat pocket. Just three words: 'Come home safe.' She must have put it there before my last business trip. I didn't find it until today. Two months too late. Three words and I'm on the floor.",
    "She volunteered at the library every Saturday morning. Reading to kids. She'd do all the voices — the bears, the witches, the brave little toasters. Kids would line up. Not for the books. For her. She made every kid feel like the story was about them.",
    "We used to argue about the thermostat. She was always cold. I was always hot. Our house was a constant negotiation between blankets and open windows. Now the house is whatever temperature I set it and I hate it. I keep it at 72 — the temperature she wanted. The battle is over and I lost.",
    "Her garden is starting to grow. She planted bulbs in October. She was always planting things she wouldn't see bloom for months. That's faith. Or stubbornness. With her it was always both.",
    "She wrote letters. Real ones, with stamps. To her mom, to old friends, to people she'd met briefly who made an impression. I found a stack of unsent ones in her desk drawer. Each one starts 'I've been meaning to write.' She was always meaning to do more than one life allowed.",
    "When she was scared she got very quiet and very organized. She'd clean the whole house. Do the taxes. Alphabetize the spice rack. The week before the diagnosis the house was immaculate and I didn't know why yet. The spice rack is still in order. I can't bring myself to mess it up.",
    "She believed in people past the point of reason. Her college roommate borrowed money seven times and never paid it back and she loaned it an eighth time. I asked her why and she said 'maybe this is the time it matters.' I didn't understand then. I think I do now.",
    "The last movie we watched together was a dumb comedy she picked. I wanted to watch something 'good.' She said 'good is whatever makes you laugh at 10pm on a Wednesday.' She was right about most things but especially that.",
    "She had a birthmark on her left shoulder shaped like nothing. She said it was shaped like Tasmania. It wasn't. But every time I saw it I thought of Tasmania and now I can't look at a map without crying which is a very specific problem to have.",
    "Our song was something embarrassing — 'Don't Stop Believin'' by Journey. Not because we picked it. Because it was playing on the jukebox the night we said 'I love you' for the first time in a dive bar in Cincinnati and neither of us was brave enough to pick something meaningful on purpose. The accident of it was the meaning.",
]

# ==========================================================================
# WAVE 3 — Month 3: Grief turning outward. Connecting. Helping others.
# ==========================================================================
WAVE_3 = [
    "Met a woman at the grief support group who lost her son. She's seventy-three and she said 'the size of the grief is the size of the love' and I believed her because her eyes were gentle and ruined at the same time.",
    "I went back to work today. Everyone was careful around me like I was made of something breakable. The truth is I'm not breakable. I'm broken. There's a difference. Breakable means it hasn't happened yet.",
    "My neighbor brought over soup again. Not the kind from a can. The kind that takes three hours. She didn't stay. Didn't ask how I was doing. Just left it on the porch with a note that said 'Tuesday.' I think she means she'll bring more on Tuesday. That's how some people say I love you.",
    "A kid at the library asked me where the story lady went. I said she moved away. I lied to a child. But what do you say? The truth is too big for a small person. The truth is too big for me.",
    "I planted something today. Marigolds. She hated marigolds — said they looked angry. I planted them because they're impossible to kill and I need something in this garden that refuses to die.",
    "Called her mom today. We cried together for forty minutes. Then she told me a story about when she was seven and put all the neighborhood cats in a wagon and tried to start a parade. I laughed. Her mom said 'that's the first time I've heard you laugh.' It didn't feel wrong. It felt like something she would have wanted.",
    "The grief counselor asked me what I'm afraid of. I said forgetting. She said 'what specifically?' and I said 'the sound of her breathing when she slept.' Such a small thing. But the small things are everything.",
    "Started bringing cookies to the nurses' station at the hospital where she was treated. Not because they deserve cookies — they deserve statues. But cookies are what I can carry. Some kindness has to be portable.",
    "A man at the support group — Marcus — told me his wife died three years ago and he just learned to make her pasta recipe. He cried into the pasta while making it. He ate it anyway. He said it tasted exactly right. The tears might have been the missing ingredient all along.",
    "I helped my sister move apartments this weekend. Carried boxes. Assembled furniture with the wrong Allen wrench. Normal Saturday things. Grief was there the whole time, sitting on the couch while we worked, but it wasn't running the show. It was just present. That's new.",
    "Someone asked me for advice at work. Not about loss — about a project. A normal question. I gave a normal answer. On the drive home I realized that was the first conversation in three months that wasn't about her, and I felt guilty, and then I felt angry at the guilt, and then I felt tired.",
    "The dog knows. He still goes to her side of the bed every night and waits. Then he sighs — really sighs, like a person — and comes to my side. We're both waiting for someone who isn't coming. At least we're waiting together.",
    "I wrote a letter to her best friend. Not about grief. About a memory — the time the three of us got lost camping and had to sleep in the car and she made us play twenty questions until 4am. Her friend wrote back: 'She would have asked 21.' That's exactly right.",
    "The marigolds are growing. Angry little orange fists pushing through the dirt. She was wrong about them. They don't look angry. They look determined. I'm going to be determined like a marigold.",
    "A new person at the support group — young, early twenties — lost her dad. She couldn't talk. Just sat there shaking. I didn't say anything wise. I sat next to her and let my arm touch her arm and we breathed. Sometimes the only thing to do is breathe next to someone.",
    "I cleaned out her closet today. Not all of it. Just one shelf. Her running shoes, the ones she kept saying she'd use 'when the weather gets nice.' I gave them to Goodwill. Someone will run in her shoes. She'd like that — the going-forward part of it.",
    "Her garden has tomatoes coming in. The ones she planted that were supposed to 'actually taste like tomatoes.' I bit into one today and it tasted like a tomato. Not transcendent. Not magical. Just a tomato she grew. And that was enough.",
    "Told Marcus from the support group about the coffee mug still in the sink. He said 'wash it when you're ready. There's no deadline for dishes.' That's the best grief advice anyone has given me. No deadline for dishes. I might stitch that on a pillow.",
    "I'm starting to recognize the shape of this thing. Not the size — the shape. It's not a wall or a wave or a hole. It's more like weather. Some days heavy rain. Some days overcast but walkable. Today was overcast with patches of sun. She would have called it 'partly people' because she mixed up 'partly cloudy' once and never corrected it. Partly people. That's what I am now.",
    "Three months. People stop asking. The cards stop coming. The world has moved on. But the grief doesn't know about calendars. It shows up on a random Wednesday at the grocery store when I see her brand of yogurt and stand in the dairy aisle crying next to a man comparing milk prices who pretends not to notice. Which is its own kind of mercy.",
]

# ==========================================================================
# WAVE 4 — Month 4: Building from loss. Wanting becomes doing.
# ==========================================================================
WAVE_4 = [
    "I painted the bedroom. Not because it needed it — because I needed to do something with my hands that changed the shape of a room. She wanted sage green. I did sage green. The room looks different now. Same bones, different skin. Like me.",
    "Started a fund at the library in her name. For kids' books. The librarian cried. I didn't cry — not because I'm past it but because the doing takes up the space where the crying goes. Action is a kind of shelter.",
    "Built raised beds in the garden where she wanted them. Went to the hardware store for cedar planks and bought the warm light bulbs without thinking. My hands know what she wanted even when my brain forgets.",
    "I wrote the letter. The one I'll never send. Twelve pages. Everything I didn't say. The fight we never finished. The apology I owed for that Thursday in November. The gratitude that was always there but sat under my tongue like something too large to speak. I folded it and put it in the mason jar with her rocks.",
    "Marcus and I started walking on Sundays. Not hiking — just walking. Through neighborhoods. He points out architectural details because he used to be a contractor. I point out gardens because of her. We don't talk about grief much anymore. We talk about windows and soil. The grief is there but it's in the walking, not the words.",
    "I made her Sunday dinner recipe. The one she always burned. I burned it too, on purpose a little, because the burning was part of it. Ate it standing at the counter. It tasted right. The right amount of wrong.",
    "Someone at the fund raiser asked me to speak about her. I stood at a podium and said five sentences. They were the right five sentences because I'd been writing them in my head for four months. She taught kids to love stories. She taught me to love rain. She was afraid of thunder and brave about everything else. She planted things she wouldn't see bloom. She is blooming now in every kid who sits in the library and hears a story.",
    "I'm training for a 5K. Not because I run. Because she had those shoes and someone is running in them and I figure the least I can do is run in mine. I'm slow and my knees hurt and I do it at 6am when no one can see. But I do it. Moving forward is not betrayal.",
    "Volunteered at the hospital. Not the ward where she was — I'm not ready. The children's wing. I read to kids. I'm terrible at the voices but the kids don't care. They care that someone showed up with a book and a chair and nowhere else to be.",
    "I fixed the fence that's been leaning since October. She asked me to fix it three times. I have this theory that every task I complete that she asked me to do is a small conversation with her. Fix the fence. Yes, love. I'm fixing it.",
    "The marigolds are everywhere now. They spread. They took over the corner bed and they're pushing into the walkway. Angry and determined and completely without boundaries. She would have said 'I told you so.' She would have been right. She was always right about the small rebellions of living things.",
    "I made a photo book. Not for anyone — for the house. Eighty pages. Chronological. From the coffee-stain day to the last Tuesday with the light bulbs. Looking at it doesn't hurt the way I thought it would. It hurts the way exercise hurts — purposefully, toward something.",
    "The 'eventually' list is still on the fridge. I crossed off 'grow tomatoes that actually taste like tomatoes.' It felt like a completion. Like she finished something from wherever she is. The list is shorter now. Not because I've given up on it but because some things she'll do through me.",
    "I helped the young woman from the support group — Hannah — write a eulogy for her dad. We sat at my kitchen table and she talked and I wrote and neither of us was alone. The eulogy was beautiful because her father was. She read it at the memorial and her voice only broke once and she looked at me and I nodded and she finished. That nod was the most important thing I've done in four months.",
    "I dream about her differently now. In the beginning the dreams were about losing her. Now the dreams are about finding her — in the garden, at the bookstore in Savannah, counting thunderstorms. The finding dreams hurt too, but they hurt with gratitude instead of panic.",
    "The thermostat stays at 72. That's not grief anymore. That's preference. She taught me what warm means and now I live there. Some lessons outlast the teacher.",
    "I threw a dinner party. Five people. Marcus, Hannah, my sister, her best friend, the neighbor who brings soup. We ate in the dining room that hasn't been used since October. I made her pasta recipe — Marcus taught me. No one mentioned her name but she was in every dish, every chair, every laugh. The dinner wasn't about her. It was because of her. There's a difference.",
    "The library called to say the first books bought with her fund arrived. Thirty-two books for kids aged four to eight. They put a small bookplate in each one that says 'From the collection of' and her name. Thirty-two doors she'll open for kids she'll never meet. That's immortality. Not the grand kind. The useful kind.",
    "I went back to the dive bar in Cincinnati. Sat at the same table. Don't Stop Believin' was not on the jukebox because the jukebox is gone — it's a touchscreen now. But I played it on my phone and drank a beer and sat with every version of us that ever sat there and it was okay. It was more than okay. It was full.",
    "The letter in the mason jar is sealed. I'm not going to read it again. It's a message in a bottle thrown into a jar of ugly rocks and that's the most beautiful container I can imagine. The words are written. The saying is done. What comes next is the living.",
]

# ==========================================================================
# WAVE 5 — Month 5: Integration. Loss is part of them now. Depth.
# ==========================================================================
WAVE_5 = [
    "There's a particular quality of light at 7am in autumn that I never noticed before. It comes through the kitchen window and lands on the counter where her coffee mug used to sit — I washed it last week, finally — and the light is gold and temporary and that's exactly what everything always was. I just didn't know it when I had it. Knowing it now isn't tragedy. It's education.",
    "Saw a woman on the bus reading the same book she was reading when we met. Different edition, different woman, different decade. But the book was there doing what books do — existing beyond the people who hold them. I wanted to say something and didn't. Some connections are meant to stay inside you where they can do quiet work.",
    "Taught Hannah how to make soup. The three-hour kind that the neighbor makes. Not because Hannah asked but because she's twenty-three and alone and soup is a skill that says 'you can take care of yourself.' The soup was terrible. She'll get better. Getting better is not the same as being better but it's the road.",
    "Marcus got a dog. A loud, terrible dog that barks at everything and has already eaten two pairs of shoes. He named it Frank. He's happy in a way that doesn't erase sad — just exists next to it. I think that's what healing looks like: not the absence of wound but the presence of other things alongside it.",
    "I notice rain differently. Not with her old love of it and not with the grief I felt when I remembered her love of it. Now rain is rain that carries a memory that carries a person that carries a world. Four layers deep and the rain still falls. Things can mean everything and also just be wet.",
    "Finished War and Peace. For her. It took six weeks and I understood about thirty percent of it. But there's this passage near the end about how real life goes on with its own concerns of health and sickness, work and rest, and its intellectual interests, love, friendship, hatred, passions — and I thought: yes. That's it. Real life with its own concerns. That's where I live now.",
    "Someone new at work asked about the photo on my desk. I said 'my wife' and didn't add 'who died' because for one sentence she was just my wife. Not my late wife, not my deceased wife, not the woman I lost. My wife. Present tense as a gift I gave myself for ten seconds.",
    "The 5K happened. I finished. Not fast. Not gracefully. My knees are already filing complaints. But I crossed a line that someone painted on asphalt and people clapped and I thought about the shoes at Goodwill being worn by a stranger who runs better than me and I clapped too. For all of us running in whatever shoes we have.",
    "I cook on Sundays now. Not because she did — because I learned that Sundays need an anchor. Something with heat and time and a result. Tonight was chili. It was good. Not good in the way that it reminded me of her. Good in the way that it was mine. I made it. I ate it. I'm learning to feed myself.",
    "Hannah called to tell me she got into graduate school. She cried. I cried. Neither of us was sad. She said 'you helped' and I said 'your dad helped' and we both knew what we meant. The dead teach through the living. That's not metaphor. That's mechanism.",
    "The garden is done for the season. The tomatoes are gone. The marigolds held on until last week. I pulled the dead plants and turned the soil and it's just dirt now, waiting for whatever comes next. She would have already planned the spring. I'll plan it in December. We have different timelines now and that's fine. The dirt is patient.",
    "I read one of her unsent letters. The one to her college roommate, the one who borrowed money eight times. The letter didn't mention the money. It just said 'I hope you're okay. I think about you. Please don't be alone.' She wrote that to someone who took from her. That's not naivety. That's a practice of believing in people as a spiritual discipline. I didn't understand it when she was here. I'm starting to understand it now.",
    "The support group is smaller now. Some people graduated out. Some people stopped coming. Marcus and I are still there, not because we need it the way we did but because the new people need what we were given: someone further down the road who is still visibly alive. Proof of concept. That's what we are. Proof that you can carry this and still stand up.",
    "I dream less about her now. Not because she's fading but because she's distributed. She's in the library and the garden and the soup and the marigolds and the 72-degree thermostat and the way I watch rain. She's not a person I visit in dreams anymore. She's a lens I see through. The dreams aren't necessary when the waking does the same work.",
    "Autumn again. A year will have passed soon. I'm not who I was. That person died too — not the same way, not as finally, but the man who lived in the before-world is gone and this man lives in the after-world and they share a face and a name and very little else. The after-man is quieter and kinder and more patient and infinitely more sad and those things are not contradictions. They are the dimensions of a person who has been expanded by loss.",
    "The bookplates arrived for the second round of library books. I signed each one. My handwriting has changed — it's slower, more careful, like I'm writing to someone who matters. She would say everyone matters. She'd be right. I'm learning to agree with her posthumously on the things I resisted when she was here. Growth is agreeing with the dead.",
    "I brought Marcus to the dive bar in Cincinnati. We played Don't Stop Believin' on the touchscreen and he played something by Patsy Cline for his wife and we sat in a booth and were two middle-aged men publicly doing something embarrassing because love makes you embarrassing and that's the cost and the point.",
    "Made a new eventually list. My own. Not hers. It starts with 'learn to be alone without being lonely' which I haven't accomplished but I've started. It also includes 'make peace with the thermostat' and 'grow something that isn't angry' and 'be the kind of person someone would spill coffee on.' The list isn't aspirational. It's directional. I know which way to walk now even when I don't know how far.",
    "The mason jar sits on the windowsill. Rocks from places we went. A letter I'll never send. The light comes through in the morning and the rocks cast small shadows and the letter is folded inside like a heart inside a chest inside a body inside a world. Four layers again. Everything is four layers now. Surface, memory, meaning, silence. She taught me to read all four. That's the gift. Not the presence — the literacy.",
    "It's Wednesday. Nothing happened. I went to work, came home, ate dinner, read a book, went to bed at ten. That's the whole entry. The fact that I can write it — that nothing happened and I'm okay with nothing happening and the silence in the house is just silence and not absence — that's the entire point. Ordinary days are the miracle. She knew that. I know it now. Partly people, she would say. And she'd be right.",
]

ALL_WAVES = [WAVE_1, WAVE_2, WAVE_3, WAVE_4, WAVE_5]


def run_test():
    """Run the 5-wave incremental growth test."""
    state_dir = tempfile.mkdtemp(prefix="griever_test_")
    print(f"State dir: {state_dir}")

    results = []
    all_texts = []

    for wave_num in range(1, 6):
        wave_texts = ALL_WAVES[wave_num - 1]
        all_texts.extend(wave_texts)

        # Fresh fish each wave — re-learn on accumulated corpus
        fish = UniversalFish(state_dir=state_dir)
        fish.crystals = []
        fish.frozen = False
        fish.vectorizer = fish.vectorizer.__class__()  # fresh vectorizer

        # Learn from all accumulated texts
        fish.learn(all_texts)
        fish.freeze(size=100, d=3.0)

        # Crystallize the full accumulated corpus
        crystals = fish.crystallize_batch(all_texts, source=f'wave_{wave_num}', couple=True)

        # Detect formations
        formations = detect_formations(crystals)

        # Teach metabolic engine from formations
        if fish._has_metabolism and formations:
            fish.metabolic_engine.teach_from_formations(formations)

        # --- Collect metrics ---
        wave_result = {
            'wave': wave_num,
            'total_texts': len(all_texts),
            'new_texts': len(wave_texts),
            'crystal_count': len(crystals),
            'formation_count': len(formations),
            'formations': [],
            'chains': {},
            'dimensions': {},
            'vocab_sample': fish.vocab[:15] if fish.vocab else [],
        }

        # Formation details
        for f in sorted(formations, key=lambda x: -x.crystal_count):
            wave_result['formations'].append({
                'name': f.name,
                'crystal_count': f.crystal_count,
                'keywords': f.keywords,
            })

        # Metabolic chains
        chains = Counter()
        for c in crystals:
            meta = getattr(c, '_metabolic', None)
            if meta and meta.chain:
                chains[" > ".join(meta.chain)] += 1
        wave_result['chains'] = dict(chains.most_common(10))

        # Dimension profile
        dim_totals = {}
        for c in crystals:
            meta = getattr(c, '_metabolic', None)
            if meta:
                for dim, r in meta.residues.items():
                    dim_totals[dim] = dim_totals.get(dim, 0) + r.activation
        if dim_totals:
            total = sum(dim_totals.values())
            wave_result['dimensions'] = {
                d: round(v / total, 4) for d, v in
                sorted(dim_totals.items(), key=lambda x: -x[1])
            }

        # Ache distribution
        aches = [c.ache for c in crystals if c.ache > 0]
        if aches:
            wave_result['ache_mean'] = round(sum(aches) / len(aches), 3)
            wave_result['ache_max'] = round(max(aches), 3)
            wave_result['ache_min'] = round(min(aches), 3)

        results.append(wave_result)

        # --- Print summary ---
        print(f"\n{'='*70}")
        print(f"WAVE {wave_num} — {len(all_texts)} total texts ({len(wave_texts)} new)")
        print(f"{'='*70}")
        print(f"Crystals: {len(crystals)}")
        print(f"Formations: {len(formations)}")
        print(f"Vocab sample: {fish.vocab[:10]}")

        print(f"\nTop formations:")
        for f in sorted(formations, key=lambda x: -x.crystal_count)[:7]:
            print(f"  {f.name} ({f.crystal_count} crystals) — kw: {f.keywords}")

        print(f"\nTop metabolic chains:")
        for chain, count in chains.most_common(5):
            print(f"  {chain}: {count}")

        if wave_result['dimensions']:
            print(f"\nDimension profile:")
            for dim, val in list(wave_result['dimensions'].items())[:6]:
                bar = '#' * int(val * 40)
                print(f"  {dim}: {val:.3f} {bar}")

        if aches:
            print(f"\nAche: mean={wave_result['ache_mean']}, "
                  f"range=[{wave_result['ache_min']}, {wave_result['ache_max']}]")

    # --- Cross-wave analysis ---
    print(f"\n{'='*70}")
    print("CROSS-WAVE ANALYSIS")
    print(f"{'='*70}")

    # Formation evolution
    print("\n--- Formation Count Over Time ---")
    for r in results:
        bar = '|' * r['formation_count']
        print(f"  Wave {r['wave']}: {r['formation_count']:2d} formations  {bar}")

    # Dimension shift
    print("\n--- Dimension Profile Shift ---")
    dims_of_interest = ['IC', 'CR', 'EW', 'KO', 'AI', 'SF', 'TE', 'DE']
    header = "      " + "  ".join(f"{d:>6}" for d in dims_of_interest)
    print(header)
    for r in results:
        vals = "  ".join(f"{r['dimensions'].get(d, 0):6.3f}" for d in dims_of_interest)
        print(f"  W{r['wave']}: {vals}")

    # Chain evolution
    print("\n--- Dominant Chain Per Wave ---")
    for r in results:
        if r['chains']:
            top_chain = max(r['chains'], key=r['chains'].get)
            print(f"  Wave {r['wave']}: {top_chain} ({r['chains'][top_chain]})")
        else:
            print(f"  Wave {r['wave']}: (no chains)")

    # Formation name evolution
    print("\n--- Formation Names Per Wave (top 5) ---")
    for r in results:
        names = [f['name'] for f in r['formations'][:5]]
        print(f"  Wave {r['wave']}: {', '.join(names)}")

    # Unique formations appearing per wave (by keywords)
    print("\n--- New Formation Keywords Per Wave ---")
    seen_keywords = set()
    for r in results:
        new_kw = set()
        for f in r['formations']:
            for kw in f['keywords']:
                if kw not in seen_keywords:
                    new_kw.add(kw)
                    seen_keywords.add(kw)
        print(f"  Wave {r['wave']}: {len(new_kw)} new keywords: {sorted(new_kw)[:10]}")

    # Ache trajectory
    print("\n--- Ache Trajectory ---")
    for r in results:
        if 'ache_mean' in r:
            print(f"  Wave {r['wave']}: mean={r['ache_mean']:.3f}, "
                  f"range=[{r['ache_min']:.3f}, {r['ache_max']:.3f}]")

    # THE KEY QUESTION
    print(f"\n{'='*70}")
    print("THE KEY QUESTION: Does Wave 5 tell a richer story than Wave 1?")
    print(f"{'='*70}")

    w1 = results[0]
    w5 = results[4]

    print(f"\n  Wave 1: {w1['formation_count']} formations, "
          f"{len(w1['chains'])} chain types, "
          f"{len(w1['dimensions'])} active dimensions")
    print(f"  Wave 5: {w5['formation_count']} formations, "
          f"{len(w5['chains'])} chain types, "
          f"{len(w5['dimensions'])} active dimensions")

    # Formation diversity
    w1_names = set(f['name'] for f in w1['formations'])
    w5_names = set(f['name'] for f in w5['formations'])
    print(f"\n  Wave 1 formation names: {w1_names}")
    print(f"  Wave 5 formation names: {w5_names}")
    print(f"  New in Wave 5: {w5_names - w1_names}")

    # Dimension shift from IC to EW
    ic_shift = [r['dimensions'].get('IC', 0) for r in results]
    ew_shift = [r['dimensions'].get('EW', 0) for r in results]
    cr_shift = [r['dimensions'].get('CR', 0) for r in results]
    print(f"\n  IC (want/feel) trajectory: {[f'{v:.3f}' for v in ic_shift]}")
    print(f"  EW (act/do) trajectory:    {[f'{v:.3f}' for v in ew_shift]}")
    print(f"  CR (relate) trajectory:    {[f'{v:.3f}' for v in cr_shift]}")

    # Save full results
    output_path = "D:/GTC/SovereignCore_Runtime/data/incremental_growth_test_report.txt"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("INCREMENTAL GROWTH TEST — THE GRIEVER\n")
        f.write(f"Run: {datetime.now().isoformat()}\n")
        f.write(f"State dir: {state_dir}\n")
        f.write("=" * 70 + "\n\n")

        for r in results:
            f.write(f"WAVE {r['wave']} — {r['total_texts']} texts ({r['new_texts']} new)\n")
            f.write(f"  Crystals: {r['crystal_count']}\n")
            f.write(f"  Formations: {r['formation_count']}\n")
            f.write(f"  Vocab: {r['vocab_sample']}\n")

            f.write(f"  Formations:\n")
            for fm in r['formations'][:7]:
                f.write(f"    {fm['name']} ({fm['crystal_count']}) — {fm['keywords']}\n")

            f.write(f"  Top chains:\n")
            for chain, count in sorted(r['chains'].items(),
                                       key=lambda x: -x[1])[:5]:
                f.write(f"    {chain}: {count}\n")

            f.write(f"  Dimensions:\n")
            for dim, val in r['dimensions'].items():
                f.write(f"    {dim}: {val:.4f}\n")

            if 'ache_mean' in r:
                f.write(f"  Ache: mean={r['ache_mean']}, "
                        f"range=[{r['ache_min']}, {r['ache_max']}]\n")

            f.write("\n")

        f.write("=" * 70 + "\n")
        f.write("CROSS-WAVE ANALYSIS\n")
        f.write("=" * 70 + "\n\n")

        f.write("Formation Count Over Time:\n")
        for r in results:
            f.write(f"  Wave {r['wave']}: {r['formation_count']} formations\n")

        f.write("\nDimension Profile Shift:\n")
        hdr = "      " + "  ".join(f"{d:>6}" for d in dims_of_interest)
        f.write(hdr + "\n")
        for r in results:
            vals = "  ".join(f"{r['dimensions'].get(d, 0):6.3f}" for d in dims_of_interest)
            f.write(f"  W{r['wave']}: {vals}\n")

        f.write("\nDominant Chain Per Wave:\n")
        for r in results:
            if r['chains']:
                top = max(r['chains'], key=r['chains'].get)
                f.write(f"  Wave {r['wave']}: {top} ({r['chains'][top]})\n")

        f.write("\nFormation Names Per Wave (top 5):\n")
        for r in results:
            names = [fm['name'] for fm in r['formations'][:5]]
            f.write(f"  Wave {r['wave']}: {', '.join(names)}\n")

        f.write("\nAche Trajectory:\n")
        for r in results:
            if 'ache_mean' in r:
                f.write(f"  Wave {r['wave']}: mean={r['ache_mean']}, "
                        f"range=[{r['ache_min']}, {r['ache_max']}]\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("THE KEY QUESTION\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"Wave 1: {w1['formation_count']} formations, "
                f"{len(w1['chains'])} chain types\n")
        f.write(f"Wave 5: {w5['formation_count']} formations, "
                f"{len(w5['chains'])} chain types\n\n")

        f.write(f"IC trajectory: {[f'{v:.3f}' for v in ic_shift]}\n")
        f.write(f"EW trajectory: {[f'{v:.3f}' for v in ew_shift]}\n")
        f.write(f"CR trajectory: {[f'{v:.3f}' for v in cr_shift]}\n\n")

        # Interpretive summary
        f.write("INTERPRETATION:\n\n")

        # Check for IC->EW shift
        ic_trend = ic_shift[-1] - ic_shift[0] if ic_shift else 0
        ew_trend = ew_shift[-1] - ew_shift[0] if ew_shift else 0
        cr_trend = cr_shift[-1] - cr_shift[0] if cr_shift else 0

        f.write(f"IC (want/feel) shifted by {ic_trend:+.3f} over 5 waves\n")
        f.write(f"EW (act/do) shifted by {ew_trend:+.3f} over 5 waves\n")
        f.write(f"CR (relate) shifted by {cr_trend:+.3f} over 5 waves\n\n")

        if ew_trend > 0:
            f.write("EW rising: The griever moved from WANTING to DOING. "
                    "The metabolic engine sees the shift.\n")
        if cr_trend > 0:
            f.write("CR rising: The griever moved from isolation to CONNECTION. "
                    "The relational dimension grew.\n")
        if ic_trend < 0:
            f.write("IC declining: Raw emotional intensity softened as other "
                    "dimensions grew. The grief didn't shrink — it distributed.\n")

        formation_growth = w5['formation_count'] - w1['formation_count']
        f.write(f"\nFormation growth: {w1['formation_count']} -> {w5['formation_count']} "
                f"({formation_growth:+d})\n")
        if formation_growth > 0:
            f.write("More formations = more structured understanding. "
                    "The portrait differentiated.\n")

        f.write("\n--- Full JSON results ---\n")
        f.write(json.dumps(results, indent=2, default=str))

    print(f"\n\nResults saved to: {output_path}")
    return results


if __name__ == "__main__":
    run_test()
