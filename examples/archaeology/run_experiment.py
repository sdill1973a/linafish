"""
SECC Fish Experiment — LiNafish archaeology example.

Demonstrates:
1. Full corpus feed → single formation (vocabulary homogeneity)
2. Split corpus by context → asymmetric structure
3. Cross-taste between public and restricted fish

Requires: a corpus/ directory with .txt files extracted from archaeology PDFs.
Use extract_corpus.py to build the corpus from PDFs.
"""

from linafish.engine import FishEngine
from pathlib import Path
import sys


def classify_section(text: str) -> str:
    """Classify text as PUBLIC or RESTRICTED based on content markers."""
    lower = text.lower()
    public_markers = [
        'public', 'broadcast', 'communal', 'monks mound', 'ramey',
        'widely distributed', 'standardized', 'redundan', 'emblemic',
        'platform mound', 'grand plaza'
    ]
    restricted_markers = [
        'restricted', 'private', 'priestly', 'mound 72', 'craig mound',
        'spiro', 'elaborate', 'attached specialist', 'assertive',
        'burial', 'cache', 'ritual', 'mortuary', 'cosmogon'
    ]
    pub_score = sum(1 for m in public_markers if m in lower)
    res_score = sum(1 for m in restricted_markers if m in lower)
    if res_score > pub_score:
        return 'restricted'
    elif pub_score > 0:
        return 'public'
    return 'unclassified'


def run_full_corpus(corpus_dir: Path, output_dir: Path):
    """Experiment 1: Feed full corpus, see how many formations emerge."""
    print("=" * 60)
    print("EXPERIMENT 1: Full corpus fish")
    print("=" * 60)

    engine = FishEngine(
        state_dir=output_dir / 'full',
        name='secc-full',
        min_gamma=0.3,
        vocab_size=100
    )

    files = sorted(corpus_dir.glob('*.txt'))
    print(f"Feeding {len(files)} files...")

    for f in files:
        text = f.read_text(encoding='utf-8', errors='ignore')
        if len(text.strip()) > 100:
            engine.eat(text, source=f.stem)

    engine._save_state()

    print(f"Crystals: {len(engine.crystals)}")
    print(f"Formations: {len(engine.formations)}")
    for f in engine.formations:
        print(f"  {f.name} ({len(f.member_ids)} members) — {', '.join(f.keywords[:6])}")

    return engine


def run_split_corpus(corpus_dir: Path, output_dir: Path):
    """Experiment 2: Split by public/restricted context, compare formations."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 2: Split corpus fish")
    print("=" * 60)

    public_texts = []
    restricted_texts = []

    for f in sorted(corpus_dir.glob('*.txt')):
        text = f.read_text(encoding='utf-8', errors='ignore')
        # Split into paragraphs and classify each
        for para in text.split('\n\n'):
            if len(para.strip()) > 100:
                ctx = classify_section(para)
                if ctx == 'public':
                    public_texts.append(para)
                elif ctx == 'restricted':
                    restricted_texts.append(para)

    print(f"Public sections: {len(public_texts)}")
    print(f"Restricted sections: {len(restricted_texts)}")

    # Build public fish
    print("\n--- PUBLIC fish ---")
    pub_engine = FishEngine(
        state_dir=output_dir / 'public',
        name='secc-public',
        min_gamma=0.3,
        vocab_size=50
    )
    for i, t in enumerate(public_texts):
        pub_engine.eat(t, source=f"public_{i}")
    pub_engine._save_state()
    print(f"Crystals: {len(pub_engine.crystals)}, Formations: {len(pub_engine.formations)}")
    for f in pub_engine.formations:
        print(f"  {f.name} ({len(f.member_ids)}) — {', '.join(f.keywords[:6])}")

    # Build restricted fish
    print("\n--- RESTRICTED fish ---")
    res_engine = FishEngine(
        state_dir=output_dir / 'restricted',
        name='secc-restricted',
        min_gamma=0.3,
        vocab_size=50
    )
    for i, t in enumerate(restricted_texts):
        res_engine.eat(t, source=f"restricted_{i}")
    res_engine._save_state()
    print(f"Crystals: {len(res_engine.crystals)}, Formations: {len(res_engine.formations)}")
    for f in res_engine.formations:
        print(f"  {f.name} ({len(f.member_ids)}) — {', '.join(f.keywords[:6])}")

    return pub_engine, res_engine


def run_cross_taste(pub_engine, res_engine):
    """Experiment 3: Cross-taste public and restricted text through both fish."""
    print("\n" + "=" * 60)
    print("EXPERIMENT 3: Cross-taste asymmetry")
    print("=" * 60)

    pub_text = (
        "Monks Mound broadcasts political authority at maximum scale. "
        "Ramey Incised ceramics are standardized, widely distributed, "
        "immediately recognizable. Communal cult objects appear across "
        "the site in both mound and non-mound contexts."
    )
    res_text = (
        "Mound 72 burial assemblage contained male-female pairs with "
        "elaborate shell beadwork. Craig Mound deposits represent ritual "
        "closing of accumulated sacred materials. Priestly cult objects "
        "show highest compositional complexity and most limited "
        "contextual distribution."
    )

    pub_in_pub = pub_engine.match(pub_text)
    res_in_pub = pub_engine.match(res_text)
    pub_in_res = res_engine.match(pub_text)
    res_in_res = res_engine.match(res_text)

    print(f"\n{'Query':<25} {'Public Fish':<15} {'Restricted Fish':<15}")
    print("-" * 55)
    print(f"{'Public text':<25} {str(pub_in_pub)[:12]:<15} {str(pub_in_res)[:12]:<15}")
    print(f"{'Restricted text':<25} {str(res_in_pub)[:12]:<15} {str(res_in_res)[:12]:<15}")

    print("\nInterpretation:")
    print("  Warm decoder reads cold: restricted fish matches public text well")
    print("  Cold decoder can't read warm: public fish matches restricted text poorly")
    print("  Containment is one-directional: restricted contains public, not vice versa")


def main():
    corpus_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('corpus')
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('output')
    output_dir.mkdir(parents=True, exist_ok=True)

    if not corpus_dir.exists():
        print(f"Corpus directory not found: {corpus_dir}")
        print("Run extract_corpus.py first, or provide a directory of .txt files.")
        sys.exit(1)

    full_engine = run_full_corpus(corpus_dir, output_dir)
    pub_engine, res_engine = run_split_corpus(corpus_dir, output_dir)
    run_cross_taste(pub_engine, res_engine)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Full corpus: {len(full_engine.crystals)} crystals → {len(full_engine.formations)} formation(s)")
    print(f"Public split: {len(pub_engine.crystals)} crystals → {len(pub_engine.formations)} formation(s)")
    print(f"Restricted split: {len(res_engine.crystals)} crystals → {len(res_engine.formations)} formation(s)")
    print(f"\nThe gradient is syntactic, not lexical.")
    print(f"The fish proved it by failing.")


if __name__ == '__main__':
    main()
