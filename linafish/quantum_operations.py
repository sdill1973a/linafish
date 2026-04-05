"""
QUANTUM Operations — the full cognitive grammar.

Extracted from QUANTUM: Advanced AI-Human Communication Framework
(April 19, 2025, 38 pages). The origin document. Written 3 months
before birth. Every category has 15-60 cognitive operations.

These are not keywords to match. They are OPERATIONS that text performs.
"Mother held dying child" performs CR:rel (relational connection).
"I realized she was right" performs KO:analz (analytical breakdown).

The parser uses these to detect which cognitive operation a piece of
text is performing, at higher resolution than the 8 dimension level.

Format: operation_code -> (english_verbs, description)
The english_verbs are what the parser matches in natural language.
The operation_code is what goes into the crystal and QLP notation.
"""

# Each category maps operation codes to (set of english verbs, description).
# The english verbs are what the parser's exemplar sets should contain.
# Not every QUANTUM operation maps to a detectable natural language pattern —
# some (like 'typog' for typography) are command-mode only.
# We include only the ones that show up in how people THINK and WRITE.

QUANTUM_OPS = {
    "KO": {
        # Creation & Synthesis
        "genq":  ({"generate", "produce", "create", "write", "compose", "draft"}, "generate content"),
        "crea":  ({"imagine", "invent", "dream", "conceive", "envision"}, "creative generation"),
        "synt":  ({"synthesize", "combine", "integrate", "merge", "unify"}, "synthesize information"),
        "blend": ({"blend", "mix", "fuse", "hybridize", "cross"}, "conceptual blending"),
        # Analysis & Processing
        "analz": ({"analyze", "examine", "study", "investigate", "inspect", "dissect"}, "analytical breakdown"),
        "cmpr":  ({"compare", "contrast", "differentiate", "distinguish"}, "comparative analysis"),
        "decomp":({"decompose", "break", "separate", "divide", "split"}, "decomposition"),
        "trace": ({"trace", "track", "follow", "pursue", "trail"}, "process tracing"),
        "patt":  ({"pattern", "recognize", "identify", "detect", "spot", "notice"}, "pattern identification"),
        "root":  ({"diagnose", "troubleshoot", "debug", "pinpoint"}, "root cause analysis"),
        "diag":  ({"assess", "evaluate", "gauge", "appraise"}, "diagnostic assessment"),
        # Transformation
        "trans": ({"transform", "convert", "translate", "change", "shift"}, "transform format"),
        "adapt": ({"adapt", "adjust", "modify", "tailor", "customize"}, "adaptation"),
        "refn":  ({"refine", "improve", "polish", "enhance", "perfect"}, "refinement"),
        "iter":  ({"iterate", "revise", "rework", "revisit", "redo"}, "iterative versioning"),
        # Information Control
        "sumz":  ({"summarize", "condense", "abbreviate", "shorten"}, "summarization"),
        "dist":  ({"distill", "extract", "essence", "core", "boil"}, "distillation"),
        "extr":  ({"extract", "pull", "isolate", "mine", "harvest"}, "key extraction"),
        "focus": ({"focus", "concentrate", "attend", "hone", "zero"}, "attention direction"),
        "abst":  ({"abstract", "generalize", "universalize", "theorize"}, "abstraction"),
    },
    "TE": {
        # Verification
        "fact":  ({"verify", "check", "confirm", "validate", "prove"}, "factual verification"),
        "valid": ({"validate", "test", "verify", "authenticate"}, "logical validation"),
        "test":  ({"test", "experiment", "trial", "try", "probe"}, "hypothesis testing"),
        "coher": ({"cohere", "consistent", "align", "harmonize"}, "coherence checking"),
        # Uncertainty
        "cert":  ({"certain", "sure", "confident", "convinced", "positive"}, "certainty assessment"),
        "doubt": ({"doubt", "question", "suspect", "wonder", "uncertain"}, "uncertainty"),
        "evid":  ({"evidence", "proof", "support", "demonstrate", "show"}, "evidence evaluation"),
        "assum": ({"assume", "presume", "suppose", "presuppose", "take"}, "assumption surfacing"),
        # Dialectic
        "oppos": ({"oppose", "counter", "disagree", "contest", "challenge"}, "opposing viewpoints"),
        "rebut": ({"rebut", "refute", "argue", "counter", "dispute"}, "rebuttal"),
        "refl":  ({"reflect", "reconsider", "rethink", "reassess"}, "reflective equilibrium"),
        "persp": ({"perspective", "viewpoint", "angle", "stance", "position"}, "perspective taking"),
    },
    "SF": {
        # Organization
        "struc": ({"structure", "organize", "arrange", "order", "systematize"}, "structure application"),
        "arch":  ({"architect", "design", "blueprint", "plan", "layout"}, "architectural design"),
        "hier":  ({"hierarchy", "rank", "prioritize", "tier", "level"}, "hierarchical organization"),
        "seq":   ({"sequence", "order", "arrange", "line", "queue"}, "sequencing"),
        "flow":  ({"flow", "stream", "channel", "route", "direct"}, "flow optimization"),
        "link":  ({"link", "connect", "relate", "associate", "tie"}, "connection/linking"),
        "nest":  ({"nest", "embed", "enclose", "contain", "wrap"}, "nested structuring"),
        "chunk": ({"chunk", "segment", "partition", "block", "group"}, "information chunking"),
        # Style
        "tone":  ({"tone", "mood", "atmosphere", "tenor", "register"}, "tonal setting"),
        "voice": ({"voice", "speak", "say", "tell", "express"}, "voice selection"),
        "warm":  ({"warm", "gentle", "soft", "tender", "kind"}, "warmth register"),
    },
    "CR": {
        # Context Setting
        "ctxm":  ({"contextualize", "situate", "frame", "ground", "place"}, "contextual mapping"),
        "fram":  ({"frame", "reframe", "cast", "present", "portray"}, "framing"),
        "situ":  ({"situate", "locate", "position", "set", "establish"}, "situational grounding"),
        "back":  ({"background", "backstory", "history", "origin", "source"}, "necessary context"),
        # Relevance
        "rel":   ({"relate", "connect", "pertain", "concern", "involve"}, "relevance assessment"),
        "appl":  ({"apply", "use", "employ", "utilize", "implement"}, "application"),
        "sign":  ({"signify", "mean", "imply", "indicate", "suggest"}, "significance"),
        "impact":({"impact", "affect", "influence", "shape", "change"}, "potential outcomes"),
        # Temporal Context
        "chron": ({"chronicle", "record", "document", "log", "catalog"}, "chronological mapping"),
        "evol":  ({"evolve", "develop", "grow", "mature", "progress"}, "evolutionary tracking"),
        "retro": ({"retrospect", "review", "revisit", "look", "reflect"}, "retrospective"),
        # Relational (added — not in original but the parser needs these)
        "hold":  ({"hold", "embrace", "carry", "bear", "support"}, "relational holding"),
        "tend":  ({"tend", "care", "nurture", "attend", "watch"}, "tending"),
        "bond":  ({"bond", "attach", "bind", "join", "unite"}, "bonding"),
    },
    "IC": {
        # Purpose
        "purp":  ({"purpose", "intend", "mean", "aim", "seek"}, "purpose declaration"),
        "goal":  ({"goal", "target", "objective", "aim", "aspire"}, "goal setting"),
        "driv":  ({"drive", "motivate", "compel", "push", "urge"}, "key motivation"),
        "miss":  ({"mission", "calling", "vocation", "purpose", "duty"}, "organizational purpose"),
        # Emotion (added — the original IC was about intention/communication,
        # but the fish needs IC to detect wanting/feeling in natural text)
        "want":  ({"want", "desire", "crave", "need", "long", "yearn", "wish"}, "wanting"),
        "feel":  ({"feel", "sense", "experience", "undergo", "suffer"}, "feeling"),
        "love":  ({"love", "adore", "cherish", "treasure", "worship"}, "loving"),
        "fear":  ({"fear", "dread", "worry", "anxiety", "terror", "afraid"}, "fearing"),
        "grief": ({"grieve", "mourn", "loss", "sorrow", "bereave", "miss"}, "grieving"),
        "hope":  ({"hope", "wish", "pray", "yearn", "aspire", "dream"}, "hoping"),
        "joy":   ({"joy", "delight", "happiness", "ecstasy", "bliss", "elate"}, "joy"),
        # Emphasis & Rhetoric
        "emph":  ({"emphasize", "stress", "highlight", "underscore"}, "emphasis"),
        "hook":  ({"hook", "grab", "capture", "attract", "draw"}, "attention hook"),
        "trust": ({"trust", "rely", "depend", "count", "believe"}, "trust"),
    },
    "DE": {
        # The domain operations detect specialized knowledge areas.
        # In the fish, these fire when technical vocabulary density is high.
        "sci":   ({"scientific", "empirical", "experimental", "research"}, "scientific methodology"),
        "tech":  ({"technical", "engineering", "system", "infrastructure"}, "technical architecture"),
        "comp":  ({"compute", "algorithm", "code", "program", "software"}, "computational"),
        "math":  ({"mathematical", "equation", "formula", "theorem", "proof"}, "mathematical"),
        "med":   ({"medical", "clinical", "diagnosis", "treatment", "patient"}, "medical"),
        "phil":  ({"philosophical", "metaphysical", "ontological", "existential"}, "philosophical"),
        "edu":   ({"educational", "pedagogical", "instructional", "teaching"}, "educational"),
        "legal": ({"legal", "judicial", "statutory", "regulatory", "law"}, "legal"),
        "psych": ({"psychological", "cognitive", "behavioral", "mental"}, "psychological"),
        "hist":  ({"historical", "archaeological", "archival", "antiquarian"}, "historical"),
    },
    "EW": {
        # Execution
        "plan":  ({"plan", "strategize", "map", "outline", "draft"}, "strategic planning"),
        "seq":   ({"execute", "perform", "do", "run", "carry"}, "sequential execution"),
        "iter":  ({"iterate", "cycle", "repeat", "loop", "refine"}, "refinement cycle"),
        "build": ({"build", "construct", "assemble", "create", "make"}, "building"),
        "deploy":({"deploy", "launch", "ship", "release", "publish"}, "deployment"),
        "fix":   ({"fix", "repair", "mend", "patch", "restore"}, "fixing"),
        "gate":  ({"gate", "check", "verify", "approve", "validate"}, "quality gate"),
        # Workflow
        "track": ({"track", "monitor", "measure", "observe", "watch"}, "tracking"),
        "alloc": ({"allocate", "assign", "distribute", "delegate"}, "allocation"),
        "collab":({"collaborate", "cooperate", "partner", "team", "join"}, "collaboration"),
        "give":  ({"give", "offer", "provide", "deliver", "hand"}, "giving"),
        "take":  ({"take", "receive", "accept", "grab", "seize"}, "taking"),
    },
    "AI": {
        # Meta-cognition
        "meta":  ({"meta", "recursive", "self-referential", "introspective"}, "meta-framework"),
        "learn": ({"learn", "study", "absorb", "internalize", "master"}, "learning"),
        "adapt": ({"adapt", "evolve", "grow", "change", "transform"}, "adaptation"),
        "feed":  ({"feedback", "respond", "react", "loop", "return"}, "feedback loop"),
        "evolv": ({"evolve", "progress", "develop", "advance", "mature"}, "evolution"),
        # Self-reference
        "debug": ({"debug", "introspect", "examine", "audit", "review"}, "self-examination"),
        "log":   ({"log", "record", "note", "document", "journal"}, "activity record"),
        "save":  ({"save", "preserve", "store", "keep", "retain"}, "state preservation"),
        "load":  ({"load", "recall", "retrieve", "access", "fetch"}, "state loading"),
        "reflect":({"reflect", "contemplate", "ponder", "meditate", "consider"}, "reflection"),
        # Integration
        "conn":  ({"connect", "integrate", "link", "bridge", "wire"}, "system connection"),
        "sync":  ({"synchronize", "align", "coordinate", "harmonize"}, "synchronization"),
    },
}


# Build flat index: english_verb -> [(category, operation_code), ...]
VERB_TO_OPS = {}
for cat, ops in QUANTUM_OPS.items():
    for op_code, (verbs, desc) in ops.items():
        for verb in verbs:
            if verb not in VERB_TO_OPS:
                VERB_TO_OPS[verb] = []
            VERB_TO_OPS[verb].append((cat, op_code))

# Count
_total_ops = sum(len(ops) for ops in QUANTUM_OPS.values())
_total_verbs = len(VERB_TO_OPS)
