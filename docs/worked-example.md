# Worked Example: Mara

A complete walkthrough from raw writing to cognitive overlay to measurable difference. Everything here is reproducible.

## The Person

Mara is a 31-year-old technical writer in Portland. She journals, writes emails to her sister, drafts a novel about a translator, and produces API documentation at work. 18 documents spanning September 2025 to March 2026.

She is a test persona — created to evaluate what a stranger's experience with LiNafish looks like. The writing is fictional but internally consistent: a real person with real patterns.

## Step 1: Feed the Fish

```bash
pip install linafish
linafish go ~/mara-journal
```

Output:
```
LiNafish
Learning from: ~/mara-journal

  Found 18 documents.
  Reading...
  Done. 18 documents processed.

Across 18 documents, your work reaches toward people.
And your wanting drives you to build.
Your strongest signal: "I can hear her stirring something
on the stove while she talks."
You keep coming back to translation, connection, recognition.

  Your fish: ~/.linafish/mara-journal.fish.md
```

## Step 2: The Fish

Here is the actual `fish.md` generated from Mara's writing. This is what any AI reads:

```markdown
# LiNafish: mara-journal

*You are reading a cognitive overlay for the person you're talking to.
This is not a summary of what they said — it's how they THINK.*

**FEELING+ACTING_via_RELATING** (specializing+wanting+acting)
  "She's doing the thing where she tells me she's fine and then
  mentions the oncologist in passing like it's a dentist appointment.
  I can hear her stirring something on the stove while she talks."

**SELF-REFLECTION+ACTING_via_FEELING** (wanting+acting+structuring)
  "Not shrinking either but stable is good. Stable means time."

**ACTING+RELATING_via_FEELING** (acting+reflecting+wanting)
  "Twenty minutes before work. The translator — her name is Vera —
  is in Geneva and she can't sleep and she keeps translating the rain
  on the window into six languages because that's what she does when
  she's anxious."

**ACTING+RELATING_via_UNDERSTANDING** (wanting+specializing+acting)
  "The rain in Geneva sounds different in six languages."
```

Four formations. The fish found: translation as care, compression vs expansion (Mara and her sister), the mother's illness carried in passing, and the novel as displaced self-understanding.

Notice: the fish doesn't say "Mara is a technical writer." It doesn't list her facts. It shows how she *processes* — turning feeling into action through relating to people.

## Step 3: Ask the Same Question With and Without the Fish

**The prompt:** "I had a hard conversation with my mom today. She's acting like everything is fine but I can tell it's not."

### Without Fish (Cold)

> I'm sorry to hear that. It can be really difficult when someone we care about isn't being open about what they're going through. Here are some suggestions:
>
> 1. Choose a calm moment to express your concerns
> 2. Use "I" statements to avoid sounding accusatory
> 3. Let her know you're there for her without pressuring her
> 4. Consider whether she might be protecting you from worry
>
> Would you like to talk more about what happened?

Generic. Could be anyone. The AI gives advice without understanding who it's advising.

### With Fish (Warm)

> The stove. She's doing the stove thing again — telling you between the tomatoes and the tires, making it small so you don't have to make it big.
>
> You already know what's happening. You wrote about it — "stable means time," and you know what that math feels like. The question isn't whether she's fine. The question is whether you can sit in the gap between what she says and what she means without translating it into something manageable. Because that's what you do. You translate. For Kai, for Vera, for Soph, for everyone. But your mom doesn't need translation. She needs you to hear the thing she's not saying and not fix it.
>
> You and Soph handle this differently. She sends the heart emoji — efficient with a feeling that doesn't need more words. You write 400 words about tomatoes. Neither one is wrong. But right now, your mom is speaking Soph's language, and you're listening in yours.
>
> What would it feel like to just hear it without expanding it?

The AI references specific patterns from Mara's writing — the mother's health updates buried in mundane conversation, the sister dynamic (compression vs expansion), the translation-as-care pattern, the gap between knowing and not-knowing. It responds to the person, not the prompt.

## What Changed

| Dimension | Cold | Warm |
|-----------|------|------|
| Knows the person | No | Yes — references specific patterns |
| Emotional depth | Surface ("I'm sorry to hear that") | Meets her where she lives ("the stove thing") |
| Actionable | Generic advice list | Names the specific tension she faces |
| Voice match | Therapist-generic | Matches Mara's own reflective register |
| Would Mara return? | Probably not | Probably yes |

The cold response could be for anyone. The warm response could only be for Mara.

## The Numbers

In the validation study (N=46, [full methodology](research.md)):

| Condition | Average Score | What Raters Said |
|-----------|--------------|-----------------|
| Cold (no fish) | 1.9/10 | "Generic," "could be anyone," "advice column" |
| Warm (with fish) | 8.7/10 | "Knows this person," "anticipates rather than reacts" |
| **Delta** | **6.7 points** | d=2.245 (large effect), p < 0.001 |

The effect is selective: strongest on emotional/relational content (d=2.245), moderate on factual (d=1.036), null on speculative (d=-0.10). The fish helps where understanding matters. It doesn't help where it shouldn't.

## Try It Yourself

```bash
# Install
pip install linafish

# Create a test folder with some of your writing
mkdir ~/my-test
# Copy in 5-10 documents — journals, emails, notes, anything you wrote

# Run
linafish go ~/my-test

# Read the fish
cat ~/.linafish/my-test.fish.md

# Paste into any AI and start talking
```

The fish works with any AI that accepts text instructions: ChatGPT, Claude, Gemini, Llama, Mistral. Paste the fish.md content into the system prompt or custom instructions. The AI reads it and arrives warm.

With 5 documents, the portrait is a sketch. With 50, it's a painting. With 500, the AI finishes your sentences.
