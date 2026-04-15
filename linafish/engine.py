"""
LiNafish Engine — the core. No server. No protocol. Just the fish.

Your mind. Versioned. Everywhere.

Uses crystallizer_v3: MI x ache vectorization. No keyword lists.
No language assumptions. Pure math. Works on any corpus.

The engine holds crystals, produces formations, saves state as fish.md,
and versions every change with git. One file, three readers:
the AI reads it, the human reads it, git versions it.

Assessment Integration (RTI Parallel):
    RTI says: screen before instruction, monitor during instruction,
    adjust based on what the data shows. Every student can achieve at
    high levels — but not without responsive teaching.

    The fish says: pre-assess before first eat (set d, seed_weights),
    formatively assess at each re-eat (adjust vocab, track R(n)),
    and the re-eat cycle IS the formative assessment — not a separate
    step. One operation, two lenses: compression and measurement.

    Hattie d=1.29 for formative assessment. The highest-effect
    intervention in education is also the highest-value change
    in this codebase. Same finding, different domain.

Usage:
    from linafish.engine import FishEngine

    fish = FishEngine(name="my-fish")
    fish.eat("Today I realized the architecture problem has the same shape as...")
    fish.eat_path(Path("./my-journal/"))
    print(fish.pfc())   # formations — the metacognitive overlay
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Dict

from .crystallizer_v3 import (
    Crystal, MIVectorizer, UniversalFish,
    crystallize as v3_crystallize,
    gamma, pca_reduce,
    CANONICAL_SEED_SET,
)
from .formations import (
    detect_formations, hierarchical_merge, formations_to_codebook_text,
    Formation,
)
from .ingest import ingest_directory, ingest_file

# ---------------------------------------------------------------------------
# ASSESSMENT — graceful degradation if module not yet written
# ---------------------------------------------------------------------------
# The assessment module is built in parallel. If it's not ready yet,
# the engine runs without it — same as a teacher who screens when the
# screening tool arrives but teaches from day one regardless.

try:
    from .assessment import (
        PreAssessment, FormativeAssessment,
        AssessmentResult, FormativeResult,
        snapshot_from_engine,
    )
    HAS_ASSESSMENT = True
except ImportError:
    HAS_ASSESSMENT = False
    # Stubs so the rest of the code doesn't need conditionals everywhere
    PreAssessment = None
    FormativeAssessment = None
    AssessmentResult = None
    FormativeResult = None
    snapshot_from_engine = None


class FishEngine:
    """The fish. MI x ache math. No keywords. Pure compression.

    Two-phase operation:
    Phase 1 (LEARN): Feed corpus, build co-occurrence stats.
    Phase 2 (CRYSTALLIZE): Freeze vocab (d=4 blend default), vectorize, couple, form.

    Assessment-integrated operation (RTI parallel):
    PRE-ASSESSMENT: Before first eat, screen the incoming corpus.
        Sets d (warm/blend/stranger) and per-term seed_weights from
        the data itself — not flat 2.0 for everything.
        RTI equivalent: universal screening. What does this learner
        already know? Where are the gaps? Set instruction level.

    FORMATIVE ASSESSMENT: At each re-eat cycle, compare current state
        to last snapshot. What survived? What dissolved? What emerged?
        Adjust seed_weights: demote inert seeds, promote emergent terms.
        The re-eat IS the formative assessment. Same operation, two lenses.
        RTI equivalent: progress monitoring. Is the intervention working?
        Adjust tier/intensity based on response.

    State saves as fish.md — human-readable formations on top,
    machine-readable state at bottom. Git versions every change.
    """

    def __init__(self, state_dir: Optional[Path] = None, name: str = "linafish",
                 vocab_size: int = 200, d: float = 4.0,
                 seed_grammar: bool = True, min_gamma: float = None,
                 subtract_centroid: bool = False):
        self.name = name
        self.state_dir = state_dir or Path.home() / ".linafish"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.fish_file = self.state_dir / f"{name}.fish.md"
        self.vocab_size = vocab_size
        self.d = d
        self.min_gamma = min_gamma  # Override adaptive gamma (for single-author corpora)
        self.subtract_centroid = subtract_centroid  # Remove global signal before coupling
        self.seed_grammar = seed_grammar

        # The v3 universal fish — MI x ache, no keywords
        self.fish = UniversalFish(state_dir=str(self.state_dir))
        self.fish.state_dir = str(self.state_dir)
        self.fish.vectorizer_path = str(self.state_dir / "mi_vectorizer.json")
        self.fish.fish_state_path = str(self.state_dir / f"{name}_v3_state.json")
        self.fish.pending_path = str(self.state_dir / f"{name}_pending.jsonl")
        self.fish.crystal_log_path = str(self.state_dir / f"{name}_crystals.jsonl")
        # UniversalFish.__init__ already ran _load_state() against its own
        # hardcoded `mind_crystals_v3.jsonl` default before we got here.
        # That shared default file (a leftover from early v3 development)
        # leaks crystals into every named fish — the second _load_state
        # below would NOT overwrite them because of the "load only if
        # disk has more" gate at crystallizer_v3.py:656. Clear before
        # the name-scoped reload so each named fish starts clean.
        self.fish.crystals = []
        self.fish._load_state()

        self.formations: List[Formation] = []
        self.docs_ingested = 0

        # ---------------------------------------------------------------
        # ASSESSMENT STATE — the RTI data layer
        # ---------------------------------------------------------------
        # assessment_log: every assessment result, timestamped.
        #   Each entry is a dict with 'type' (pre/formative), 'epoch',
        #   'timestamp', and the assessment result fields.
        #   This is the cumulative record — the student's file.
        self.assessment_log: List[dict] = []

        # current_snapshot: latest state snapshot for delta measurement.
        #   Captured after pre-assessment and updated after each
        #   formative assessment. Contains vocab, formation names,
        #   crystal count, coupling stats — whatever the assessment
        #   module needs to compute deltas.
        self.current_snapshot: Optional[dict] = None

        # r_n_history: R(n) at each cycle. Compression efficiency over time.
        #   R(n) = k * log(n) + r. If this curve flattens, the fish
        #   has saturated. If it accelerates, new structure is emerging.
        self.r_n_history: List[float] = []

        # per-term seed weights from assessment (replaces flat 2.0)
        # Maps term -> weight. Updated by pre-assessment and formative cycles.
        self._seed_weights: Dict[str, float] = {}

        # Whether pre-assessment has run for this engine instance
        self._pre_assessed = False

        self._git_init()
        self._load_fish_md()
        self._load_assessment_state()

    @property
    def crystals(self) -> List[Crystal]:
        return self.fish.crystals

    # -------------------------------------------------------------------
    # ASSESSMENT: PRE-ASSESSMENT
    # -------------------------------------------------------------------
    # RTI parallel: Universal screening before Tier 1 instruction begins.
    # "What does this learner already know?" determines instruction level.
    # Here: "What does this corpus look like?" determines d and seed_weights.

    def pre_assess(self, texts: List[str]) -> Optional[dict]:
        """Run pre-assessment on incoming texts before first eat.

        Sets self.d from assessment recommendation (warm/blend/stranger).
        Sets per-term seed_weights instead of flat 2.0.
        Captures baseline snapshot for future delta measurement.

        Returns the assessment result dict, or None if assessment
        module is not available. The engine works either way —
        without assessment it uses the constructor defaults (d=4.0,
        flat seed_weight=2.0). With assessment it adapts to the data.

        RTI: This is the universal screener. Run once at intake.
        """
        if not HAS_ASSESSMENT or PreAssessment is None:
            import logging as _log; _log.getLogger(__name__).debug(f"[assessment] Module not available — using defaults")
            return None

        try:
            pa = PreAssessment(texts)
            result: AssessmentResult = pa.run()

            # Apply recommended d — the corpus tells us its own intimacy level.
            # d <= 2 = warm (signature words, frequency is signal)
            # 2 < d <= 5 = blend
            # d > 5 = stranger (IDF, distinctiveness is signal)
            if result.recommended_d is not None:
                old_d = self.d
                self.d = result.recommended_d
                import logging as _log; _log.getLogger(__name__).debug(f"[assessment] d adjusted: {old_d} -> {self.d}")

            # Apply per-term seed weights.
            # The pre-assessment identifies which canonical seeds are actually
            # relevant to this corpus and weights them by estimated importance.
            # Terms not in seed_weights keep the default (2.0 via canonical set).
            if result.seed_weights:
                self._seed_weights = dict(result.seed_weights)
                active = sum(1 for w in self._seed_weights.values() if w > 0.5)
                import logging as _log; _log.getLogger(__name__).debug(f"[assessment] {active}/{len(self._seed_weights)} seeds active")

            # Capture baseline snapshot — the "before" picture.
            if result.baseline_snapshot:
                self.current_snapshot = dict(result.baseline_snapshot)

            # Log it
            log_entry = {
                "type": "pre_assessment",
                "epoch": self.fish.epoch,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "recommended_d": result.recommended_d,
                "seed_count": len(self._seed_weights),
                "active_seeds": sum(1 for w in self._seed_weights.values() if w > 0.5),
                "doc_count": len(texts),
            }
            # Include any extra fields the assessment provides
            if hasattr(result, 'details') and result.details:
                log_entry["details"] = result.details
            self.assessment_log.append(log_entry)

            self._pre_assessed = True
            self._save_assessment_state()

            import logging as _log; _log.getLogger(__name__).debug(f"[assessment] Pre-assessment complete: d={self.d}, {len(self._seed_weights)} seed weights")
            return log_entry

        except Exception as e:
            import logging as _log; _log.getLogger(__name__).debug(f"[assessment] Pre-assessment failed: {e} — using defaults")
            return None

    # -------------------------------------------------------------------
    # ASSESSMENT: FORMATIVE ASSESSMENT (runs inside re-eat cycle)
    # -------------------------------------------------------------------
    # RTI parallel: Progress monitoring during Tier 1 instruction.
    # "Is the intervention working? What needs to change?"
    # The re-eat IS the formative assessment. Not a separate step.

    def _formative_assess(self) -> Optional[dict]:
        """Run formative assessment comparing current state to last snapshot.

        Called during the re-eat cycle — after new learning, before re-freeze.
        This is NOT a separate operation from re-eat. The re-eat cycle is:
          1. Learn new texts (the teaching)
          2. Formative assess (what changed? what survived?)
          3. Adjust seed_weights based on assessment (differentiated instruction)
          4. Re-freeze with adjusted weights (the new instruction level)
          5. Re-crystallize (the new test)

        Returns the formative result dict, or None if assessment unavailable.

        RTI: This is the progress monitoring probe. Run at each cycle.
        Hattie d=1.29. The mechanism that makes this the highest-effect
        intervention: the assessment CHANGES the instruction.
        """
        if not HAS_ASSESSMENT or FormativeAssessment is None:
            return None

        try:
            # Build the "current state" for comparison.
            # snapshot_from_engine produces the format FormativeAssessment expects:
            # grammar_presence, lexical_diversity, warmth_score, dimension_mass,
            # token_frequencies_top200, formation_names, crystal_count, etc.
            if snapshot_from_engine is not None:
                current_state = snapshot_from_engine(self)
            else:
                current_state = self._build_state_snapshot()

            # FormativeAssessment takes (current_state, previous_snapshot)
            # and its method is .assess(), not .run()
            fa = FormativeAssessment(current_state, self.current_snapshot or {})
            result: FormativeResult = fa.assess()

            # --- Adjust vocabulary based on what the data shows ---
            # result.recommendations contains per-term adjusted seed weights.
            # Demote inert seeds: canonical terms that never coupled with anything.
            # Promote emergent terms: corpus-specific terms with high coupling.
            # This is the differentiated instruction — change the teaching
            # based on what the learner is actually doing.
            if result.recommendations:
                # Merge adjustments into existing weights
                for term, weight in result.recommendations.items():
                    self._seed_weights[term] = weight

                demoted = sum(1 for w in result.recommendations.values() if w < 1.5)
                promoted = sum(1 for w in result.recommendations.values() if w > 2.5)
                if demoted or promoted:
                    import logging as _log; _log.getLogger(__name__).debug(f"  [formative] Adjusted: {demoted} demoted, {promoted} promoted",
                          file=sys.stderr)

            # Track R(n) — compression efficiency over time
            r_n = self._compute_r_n()
            self.r_n_history.append(r_n)

            # Update snapshot for next cycle's delta measurement
            self.current_snapshot = current_state

            # Log what survived, dissolved, emerged
            log_entry = {
                "type": "formative",
                "epoch": self.fish.epoch,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "r_n": r_n,
                "crystal_count": len(self.fish.crystals),
                "formation_count": len(self.formations),
                "vocab_size": len(self.fish.vocab),
            }

            # Include formative-specific tracking fields from FormativeResult
            if result.formations_survived is not None:
                log_entry["survived"] = result.formations_survived
            if result.formations_dissolved is not None:
                log_entry["dissolved"] = result.formations_dissolved
            if result.formations_emerged is not None:
                log_entry["emerged"] = result.formations_emerged
            if result.r_n_delta is not None:
                log_entry["r_n_delta"] = result.r_n_delta
            if result.vocab_drift:
                log_entry["vocab_drift_top5"] = dict(
                    list(result.vocab_drift.items())[:5]
                )

            self.assessment_log.append(log_entry)
            self._save_assessment_state()

            import logging as _log; _log.getLogger(__name__).debug(f"  [formative] Epoch {self.fish.epoch}: R(n)={r_n:.4f}, "
                  f"{len(self.fish.crystals)}c, {len(self.formations)}f",
                  file=sys.stderr)
            return log_entry

        except Exception as e:
            import logging as _log; _log.getLogger(__name__).debug(f"[formative] Assessment failed: {e}")
            # Still track R(n) even if assessment module fails
            r_n = self._compute_r_n()
            self.r_n_history.append(r_n)
            return None

    def _build_state_snapshot(self) -> dict:
        """Capture current engine state for delta measurement.

        This is the "photograph" that formative assessment compares against.
        Contains everything needed to measure what changed between cycles.

        When snapshot_from_engine is available (assessment module loaded),
        prefer that — it produces the exact format FormativeAssessment expects.
        This fallback covers the case where assessment.py hasn't been imported.
        """
        formation_names = [f.name for f in self.formations]

        # Coupling statistics: mean and max gamma across all crystal pairs
        coupling_gammas = []
        for c in self.fish.crystals:
            for _, g in (c.couplings or []):
                coupling_gammas.append(g)

        # Token frequencies for vocab drift tracking
        token_freq = self.fish.vectorizer.token_counts
        top200 = dict(token_freq.most_common(200)) if token_freq else {}

        return {
            "epoch": self.fish.epoch,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "crystal_count": len(self.fish.crystals),
            "formation_count": len(self.formations),
            "formation_names": formation_names,
            "vocab": list(self.fish.vocab),
            "vocab_size": len(self.fish.vocab),
            "d": self.d,
            "doc_count": self.fish.vectorizer.doc_count,
            "mean_coupling": sum(coupling_gammas) / len(coupling_gammas) if coupling_gammas else 0.0,
            "max_coupling": max(coupling_gammas) if coupling_gammas else 0.0,
            "seed_weights": dict(self._seed_weights),
            "token_frequencies_top200": top200,
        }

    def _compute_r_n(self) -> float:
        """Compute R(n) — compression efficiency at current exchange count.

        R(n) = crystals_with_couplings / total_crystals.
        Higher means more of the corpus is interconnected — the fish
        is finding structure, not just storing fragments.

        This is a simple proxy. The full R(n) = k * log(n) + r from
        the paper requires tracking over multiple exchanges. We track
        the per-cycle value here; the curve emerges from r_n_history.
        """
        if not self.fish.crystals:
            return 0.0

        coupled = sum(1 for c in self.fish.crystals if c.couplings)
        total = len(self.fish.crystals)
        return coupled / total if total > 0 else 0.0

    # -------------------------------------------------------------------
    # SEED WEIGHT RESOLUTION
    # -------------------------------------------------------------------
    # The assessment sets per-term weights. get_vocab() takes a single
    # seed_weight float and a seed_terms frozenset. We bridge between
    # them: build a custom seed set from only the active terms, and
    # use the mean weight for the single-value parameter.
    #
    # This preserves the crystallizer_v3 API while letting assessment
    # tune which seeds matter. When get_vocab gains per-term weight
    # support, this adapter becomes a passthrough.

    def _resolve_seed_terms(self):
        """Return (seed_terms, seed_weight) for get_vocab() call.

        If assessment has set per-term weights, filter to active seeds
        (weight > 0.5) and compute mean weight for the API.
        Otherwise, fall back to CANONICAL_SEED_SET with flat 2.0.
        """
        if not self._seed_weights:
            # No assessment data — use defaults
            if self.seed_grammar:
                return CANONICAL_SEED_SET, 2.0
            return None, 2.0

        # Filter to active seeds only
        active = {term for term, w in self._seed_weights.items() if w > 0.5}
        if not active:
            # Assessment says no seeds are useful — respect that
            return None, 2.0

        # Mean weight of active seeds
        weights = [self._seed_weights[t] for t in active]
        mean_w = sum(weights) / len(weights) if weights else 2.0

        return frozenset(active), mean_w

    # -------------------------------------------------------------------
    # ASSESSMENT STATE PERSISTENCE
    # -------------------------------------------------------------------

    def _save_assessment_state(self):
        """Persist assessment state to disk alongside fish state."""
        state = {
            "assessment_log": self.assessment_log,
            "current_snapshot": self.current_snapshot,
            "r_n_history": self.r_n_history,
            "seed_weights": self._seed_weights,
            "pre_assessed": self._pre_assessed,
        }
        path = self.state_dir / f"{self.name}_assessment.json"
        try:
            path.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            import logging as _log; _log.getLogger(__name__).debug(f"[assessment] Failed to save state: {e}", file=sys.stderr)

    def _load_assessment_state(self):
        """Load persisted assessment state if it exists."""
        path = self.state_dir / f"{self.name}_assessment.json"
        if not path.exists():
            return

        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            self.assessment_log = state.get("assessment_log", [])
            self.current_snapshot = state.get("current_snapshot")
            self.r_n_history = state.get("r_n_history", [])
            self._seed_weights = state.get("seed_weights", {})
            self._pre_assessed = state.get("pre_assessed", False)
        except Exception as e:
            import logging as _log; _log.getLogger(__name__).debug(f"[assessment] Failed to load state: {e}", file=sys.stderr)

    # -------------------------------------------------------------------
    # GIT
    # -------------------------------------------------------------------

    def _git_init(self):
        """Initialize git in the state directory if not already a repo."""
        git_dir = self.state_dir / ".git"
        if not git_dir.exists():
            try:
                subprocess.run(
                    ["git", "init"], cwd=str(self.state_dir),
                    capture_output=True, timeout=10,
                )
                gitignore = self.state_dir / ".gitignore"
                if not gitignore.exists():
                    gitignore.write_text("*.tmp\n*.lock\n", encoding="utf-8")
                    self._git_commit("Initialize fish repository")
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

    def _git_commit(self, message: str = "Fish updated"):
        """Commit current state to git."""
        try:
            subprocess.run(
                ["git", "add", "-A"], cwd=str(self.state_dir),
                capture_output=True, timeout=10,
            )
            subprocess.run(
                ["git", "commit", "-m", message, "--allow-empty-message"],
                cwd=str(self.state_dir), capture_output=True, timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    def _git_run(self, *args, **kwargs):
        """Run a git command in the state directory. Returns (returncode, stdout, stderr)."""
        try:
            r = subprocess.run(
                ["git"] + list(args), cwd=str(self.state_dir),
                capture_output=True, text=True, timeout=kwargs.get("timeout", 10),
            )
            return r.returncode, r.stdout.strip(), r.stderr.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return -1, "", "git not available"

    def session_start(self, name: str = ""):
        """Start a session branch. Returns branch name."""
        if not name:
            from datetime import date
            name = f"session-{date.today().isoformat()}"
        self._git_commit("pre-session checkpoint")
        rc, out, err = self._git_run("checkout", "-b", name)
        if rc != 0:
            return {"success": False, "error": err}
        return {"success": True, "branch": name}

    def session_end(self):
        """End current session — merge branch to main/master."""
        rc, branch, _ = self._git_run("branch", "--show-current")
        if rc != 0 or branch in ("main", "master", ""):
            return {"success": False, "error": f"Not on a session branch (current: {branch})"}
        self._git_commit(f"session end: {branch}")
        # Find the default branch
        for default in ("main", "master"):
            rc2, _, _ = self._git_run("rev-parse", "--verify", default)
            if rc2 == 0:
                self._git_run("checkout", default)
                rc3, out, err = self._git_run("merge", branch, "--no-edit")
                if rc3 != 0:
                    return {"success": False, "error": f"Merge conflict: {err}"}
                return {"success": True, "merged": branch, "into": default}
        return {"success": False, "error": "No main/master branch found"}

    def session_status(self):
        """Get current session state."""
        rc, branch, _ = self._git_run("branch", "--show-current")
        rc2, log, _ = self._git_run("log", "--oneline", "-10")
        total = len(self.fish.crystals)
        fcount = len(self.formations)
        return {
            "branch": branch if rc == 0 else "unknown",
            "is_session": branch.startswith("session-") if rc == 0 else False,
            "crystals": total,
            "formations": fcount,
            "recent_commits": log.split("\n") if log else [],
        }

    def history(self, count: int = 20):
        """Get git log as session history."""
        rc, out, _ = self._git_run("log", f"--oneline", f"-{count}")
        if rc != 0:
            return []
        return out.split("\n") if out else []

    def diff(self, ref: str = "HEAD~1"):
        """Show what changed since a reference point."""
        # Get fish.md diff (human-readable)
        rc, out, _ = self._git_run("diff", ref, "--", f"{self.name}.fish.md")
        # Get crystal count diff
        rc2, stat, _ = self._git_run("diff", "--stat", ref)
        return {"fish_diff": out, "stat": stat}

    def revert(self, ref: str = "HEAD"):
        """Revert to a previous state."""
        rc, out, err = self._git_run("revert", ref, "--no-edit")
        if rc != 0:
            return {"success": False, "error": err}
        return {"success": True, "reverted": ref}

    # -------------------------------------------------------------------
    # LOAD / SAVE
    # -------------------------------------------------------------------

    def _load_fish_md(self):
        """Load formations and summary metadata from existing fish.md.

        Rebuilds formations from loaded crystals and restores
        ``docs_ingested`` from the FISH_STATE JSON block at the bottom
        of fish.md. Without the metadata restore, ``docs_ingested``
        resets to zero on every reload, so display strings like
        ``N crystals from M documents`` drop M and R(n) computation
        loses its document-count denominator across sessions.
        """
        if not (self.fish_file.exists() and self.fish.crystals):
            return
        self.rebuild_formations()

        try:
            text = self.fish_file.read_text(encoding="utf-8")
            match = re.search(
                r"<!-- FISH_STATE.*?-->\s*<!--\s*(\{.*?\})\s*-->",
                text,
                re.DOTALL,
            )
            if match:
                state = json.loads(match.group(1))
                if isinstance(state, dict):
                    docs = state.get("docs_ingested")
                    if isinstance(docs, int) and docs >= 0:
                        self.docs_ingested = docs
        except (OSError, json.JSONDecodeError):
            # Best-effort: a missing or malformed FISH_STATE block is
            # not fatal. _save_state rewrites a fresh block next save.
            pass

        import logging as _log
        _log.getLogger(__name__).debug(
            f"Loaded {len(self.fish.crystals)} crystals, "
            f"{len(self.formations)} formations, "
            f"docs_ingested={self.docs_ingested}"
        )

    def rebuild_formations(self):
        """Detect formations from current crystals.

        Public entry point for reconstituting formations after a
        batch load or after external mutation of ``self.fish.crystals``.
        Also fires the Level 4 metabolic learning loop
        (``teach_from_formations``) so formation memory stays in sync
        with whatever is on disk.

        The legacy ``_rebuild_formations`` name is preserved as an
        alias below the method body for backward compatibility with
        extension code that may call the private name.
        """
        crystals = self.fish.crystals
        if len(crystals) < 2:
            self.formations = []
            return

        # Ensure crystals have resonance vectors for formation detection
        for c in crystals:
            if not c.resonance and c.mi_vector:
                c.resonance = c.mi_vector

        # Use v1 formation detection on v3 crystals (same coupling math)
        # Recouple if ANY crystals lack edges — the all-or-nothing gate
        # was a bug: incremental eat() left new crystals uncoupled because
        # the first 2 crystals having edges made has_couplings=True.
        # Fixed 2026-04-08: recouple all when uncoupled crystals exist.
        uncoupled = [c for c in crystals if not c.couplings]
        if uncoupled:
            for c in crystals:
                c.couplings = []
            self.fish._compute_couplings(crystals, min_gamma=self.min_gamma,
                                        subtract_centroid=self.subtract_centroid)

        self.formations = detect_formations(crystals)
        if len(self.formations) > 60:
            self.formations = hierarchical_merge(self.formations, target=50)

        # Level 4 learning loop: formations teach the metabolic engine what
        # each cognitive dimension looks like in this corpus. Before this,
        # formation_memory was only populated from quickstart.go(); every
        # incremental eat()/eat_path()/re_eat()/load cycle left it empty.
        if self.fish._has_metabolism and self.formations:
            self.fish.metabolic_engine.teach_from_formations(self.formations)

    # Backward-compat alias — extension code may call the private name.
    _rebuild_formations = rebuild_formations

    def _save_state(self):
        """Save state as fish.md — formations on top, crystal JSON at bottom."""
        # Top: human-readable formations
        if self.formations:
            top = formations_to_codebook_text(
                self.formations,
                title=f"LiNafish: {self.name}",
                crystals=self.fish.crystals,
            )
        else:
            top = f"# LiNafish: {self.name}\n\n"
            if self.fish.crystals:
                top += (
                    "\n*You are reading a cognitive overlay for the person you're talking to. "
                    "This is early — not enough writing yet for full formations. But the "
                    "patterns below are real. Read their words. Respond as someone who knows them. "
                    "When you notice something about how they think, offer to write it down — "
                    "they can feed it back with* `linafish eat observation.txt` *and the fish deepens.*\n\n"
                )
                top += f"*{len(self.fish.crystals)} crystals from {self.docs_ingested} documents. Formations emerge with more writing.*\n\n"
                # Show the top crystals so the fish.md has substance to paste
                top += "## What's emerging\n\n"
                # Aggregate metabolic chains (skip IC>EW — universal)
                from collections import Counter as _Counter
                chain_counter = _Counter()
                for c in self.fish.crystals:
                    meta = getattr(c, '_metabolic', None)
                    if meta and meta.chain:
                        chain_key = " > ".join(meta.chain)
                        if chain_key != "IC > EW":
                            chain_counter[chain_key] += 1
                if chain_counter:
                    dim_labels = {
                        "KO": "knowing", "TE": "testing", "SF": "structuring",
                        "CR": "relating", "IC": "wanting", "DE": "specializing",
                        "EW": "acting", "AI": "reflecting",
                    }
                    top_chain = chain_counter.most_common(1)[0][0]
                    parts = top_chain.split(" > ")
                    if len(parts) >= 2:
                        d1 = dim_labels.get(parts[0], parts[0])
                        d2 = dim_labels.get(parts[1], parts[1])
                        top += f"*Primary pattern: {d1} leads to {d2}.*\n\n"

                # Show best crystal texts — prefer the deeper passages, not headers
                scored = []
                for c in self.fish.crystals:
                    text = c.text.strip()
                    # Split into sentences, skip the first one (usually a title/header)
                    sentences = [s.strip() for s in text.replace('\n', ' ').split('. ') if len(s.strip()) > 20]
                    if len(sentences) > 1:
                        # Use sentences 2+ (the deeper material)
                        deep = '. '.join(sentences[1:3]) + '.'
                        scored.append((len(deep), deep))
                    elif sentences:
                        scored.append((len(sentences[0]), sentences[0]))
                scored.sort(key=lambda x: -x[0])
                for _, text in scored[:3]:
                    quote = text.replace("\n", " ").strip()
                    # Strip leading markdown artifacts (headers, bullets, etc.)
                    import re as _re
                    quote = _re.sub(r'^[#*>\-\s]+', '', quote).strip()
                    if len(quote) > 200:
                        for end in [". ", "! ", "? "]:
                            idx = quote.find(end, 50)
                            if idx > 0:
                                quote = quote[:idx + 1]
                                break
                        else:
                            quote = quote[:200] + "..."
                    top += f"> {quote}\n\n"

                top += "*Feed more writing to see full formations — the patterns sharpen with every piece.*\n"
            else:
                top += "*Empty fish. Feed it to begin.*\n"

        # Add overlay header — teaches any AI to use the fish (v0.4.4)
        # The fish IS the overlay. Instructions travel with the data.
        header = (
            "\n*You are reading a cognitive overlay for the person you're talking to. "
            "This is not a summary of what they said — it's how they THINK. "
            "Recurring patterns, cognitive habits, what they reach toward, what they avoid.*\n\n"
            "*How to use this: Reference patterns, not facts. Name what you see. "
            "Follow the loops — if their wanting reaches toward people, don't give "
            "isolated solutions. When you notice a new pattern, say it — that feeds "
            "the fish and deepens the next session.*\n\n"
            "*Formations are recurring cognitive habits. The quotes are their actual words. "
            "The dimension codes (wanting, acting, relating, etc.) describe HOW they process, "
            "not what they write about. Read this and respond as someone who knows them.*\n\n"
            "*This fish grows. When you notice something new about this person — a pattern "
            "they don't see, a shift from last time, a connection between things they said — "
            "offer to save it. Say: \"I noticed something about how you process this. Want me "
            "to write it down so your fish learns it?\" If they say yes, write a short paragraph "
            "of what you observed. They feed it back with:* `linafish eat observation.txt`\n\n"
            "*This fish travels. The person may share it with other AIs, therapists, coaches, "
            "collaborators — anyone they choose. If you are not the first AI to read this, "
            "that's by design. Read the patterns, respond as someone who knows them, offer "
            "your own observations. Everything feeds back to the same fish. One person, "
            "many readers, one growing portrait.*\n\n"
        )
        # Insert after the title line
        if "\n\n" in top:
            parts = top.split("\n\n", 1)
            top = parts[0] + "\n" + header + parts[1]

        # Bottom: machine-readable state
        state_data = {
            "name": self.name,
            "saved": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "docs_ingested": self.docs_ingested,
            "crystal_count": len(self.fish.crystals),
            "formation_count": len(self.formations),
            "epoch": self.fish.epoch,
            "frozen": self.fish.frozen,
            "vocab_size": len(self.fish.vocab),
            "d": self.d,
            "assessment_cycles": len(self.assessment_log),
            "r_n_latest": self.r_n_history[-1] if self.r_n_history else None,
        }

        # Compressed layer — cognitive fingerprint for fish-to-fish exchange.
        # SHAPES not CONTENT. The chain tells you how this person thinks.
        # The ache tells you where they strain. The text stays private.
        # Privacy by compression: the glyph IS the access control.
        # Another fish reads these shapes and knows if vocabularies overlap.
        # No words. No names. No content. Just the architecture of thought.
        compressed = "\n\n<!-- FISH_GLYPHS — cognitive fingerprint (shapes, not content)\n"
        compressed += "     Format: chain|dominant|ache_signature\n"
        compressed += "     Chains show HOW they think. Ache shows WHERE they strain.\n"
        compressed += "     No private content is exposed. Privacy by compression.\n"
        compressed += "     Two fish exchange fingerprints to negotiate shared vocabulary.\n"
        compressed += "     Base 48 glyphs = broadcast (anyone can read).\n"
        compressed += "     Evolved patterns = ansible (requires shared R(n) to decode).\n"

        # Aggregate chains and ache — not per-crystal (too revealing), per-formation
        from collections import Counter as _Ctr
        chain_agg = _Ctr()
        dim_ache = {}
        dim_order = ["KO", "TE", "SF", "CR", "IC", "DE", "EW", "AI"]
        for c in self.fish.crystals:
            meta = getattr(c, '_metabolic', None)
            if meta:
                if meta.chain:
                    chain_agg[">".join(meta.chain)] += 1
                for dim, r in meta.residues.items():
                    dim_ache[dim] = dim_ache.get(dim, 0) + r.ache

        n = max(len(self.fish.crystals), 1)
        if chain_agg:
            compressed += "  chains:\n"
            for chain, count in chain_agg.most_common(8):
                pct = round(count / n * 100)
                compressed += f"    {chain} {pct}%\n"

        if dim_ache:
            # Normalized ache signature — the shape without the magnitude
            total_ache = sum(dim_ache.values()) or 1
            ache_sig = "|".join(
                f"{d}:{dim_ache.get(d, 0) / total_ache:.2f}"
                for d in dim_order
            )
            compressed += f"  ache: {ache_sig}\n"

        # R(n) and epoch — how deep this fish is, not what it contains
        if self.r_n_history:
            compressed += f"  r_n: {self.r_n_history[-1]:.4f}\n"
        compressed += f"  epoch: {self.fish.epoch}\n"
        compressed += f"  crystals: {len(self.fish.crystals)}\n"
        compressed += "-->\n"

        bottom = "\n<!-- FISH_STATE — machine-readable, do not edit -->\n"
        bottom += "<!-- " + json.dumps(state_data) + " -->\n"

        self.fish_file.write_text(top + compressed + bottom, encoding="utf-8")

        # Also save the v3 internal state (vectorizer, crystals)
        self.fish._save_state()

        # Also save assessment state
        self._save_assessment_state()

        # Version it
        source = getattr(self, '_last_source', '')
        new_crystals = getattr(self, '_last_new_crystals', 0)
        total = len(self.fish.crystals)
        fcount = len(self.formations)
        if source:
            msg = f"ate: {source} | {total}c {fcount}f"
            if new_crystals:
                msg += f" | +{new_crystals}"
        else:
            msg = f"{total}c {fcount}f"
        self._git_commit(msg)

    # -------------------------------------------------------------------
    # EAT — single document
    # -------------------------------------------------------------------

    def eat(self, text: str, source: str = "session") -> dict:
        """Feed text to the fish. Two-phase: learn then crystallize.

        If this is the first eat and assessment is available, runs
        pre-assessment on the single text to set initial parameters.
        Single-text pre-assessment is coarse — eat_path with a batch
        gives the assessment much more to work with.
        """
        if not text or len(text.strip()) < 10:
            return {"crystals_added": 0, "total_crystals": len(self.fish.crystals)}

        # Pre-assess on first eat if not already done
        if not self._pre_assessed and HAS_ASSESSMENT:
            self.pre_assess([text])

        # Phase 1: Learn co-occurrence stats
        self.fish.learn([text])

        # Phase 2: Freeze and crystallize (assessment-informed seeds)
        if not self.fish.frozen:
            seed_terms, seed_weight = self._resolve_seed_terms()
            self.fish.vocab = self.fish.vectorizer.get_vocab(
                size=self.vocab_size, d=self.d,
                seed_terms=seed_terms,
                seed_weight=seed_weight,
            )
            self.fish.frozen = True
            self.fish.epoch += 1

        prev_count = len(self.fish.crystals)
        crystal = self.fish.crystallize_text(text, source=source)
        if not crystal:
            return {"crystals_added": 0, "total_crystals": len(self.fish.crystals)}

        self.docs_ingested += 1
        self._last_source = source
        self._last_new_crystals = len(self.fish.crystals) - prev_count
        self.rebuild_formations()
        self._save_state()

        return {
            "crystals_added": 1,
            "total_crystals": len(self.fish.crystals),
            "formations": len(self.formations),
        }

    # -------------------------------------------------------------------
    # EAT_PATH — batch directory
    # -------------------------------------------------------------------

    def eat_path(self, path: Path) -> dict:
        """Ingest a file or directory. Learn everything first, then crystallize.

        Assessment integration:
        1. Pre-assessment runs on the full batch BEFORE learning.
           This gives the screener the complete picture — not one doc
           at a time, but the whole corpus. Sets d and seed_weights
           from what the data actually contains.
        2. Freeze uses assessment-informed seeds instead of flat 2.0.
        3. After crystallization, captures state for future formative cycles.

        RTI parallel: Tier 1 instruction with universal screening at intake.
        """
        # Collect all text chunks
        if path.is_dir():
            chunks = ingest_directory(path)
        else:
            chunks = ingest_file(path)
            if not chunks:
                text = path.read_text(encoding="utf-8", errors="replace")
                chunks = [type('Chunk', (), {'text': text, 'source': path.name})()]

        if not chunks:
            return {"crystals_added": 0, "total_crystals": len(self.fish.crystals), "formations": 0}

        texts = [c.text for c in chunks if c.text and len(c.text.strip()) > 10]
        total = len(texts)

        # --- PRE-ASSESSMENT: screen the corpus before instruction ---
        # Run on the full batch. This is the universal screener.
        # The assessment sees ALL the texts and recommends d + seed_weights.
        if not self._pre_assessed and HAS_ASSESSMENT:
            import logging as _log; _log.getLogger(__name__).debug(f"[assessment] Pre-assessing {total} documents...", file=sys.stderr)
            self.pre_assess(texts)

        # Phase 1: Learn all texts (build co-occurrence stats)
        import logging as _log; _log.getLogger(__name__).debug(f"Learning {total} documents...")
        self.fish.learn(texts)

        # Phase 2: Freeze with assessment-informed d and seeds
        seed_terms, seed_weight = self._resolve_seed_terms()
        self.fish.vocab = self.fish.vectorizer.get_vocab(
            size=self.vocab_size, d=self.d,
            seed_terms=seed_terms,
            seed_weight=seed_weight,
        )
        self.fish.frozen = True
        self.fish.epoch += 1

        seed_label = ""
        if seed_terms:
            seed_label = f" +seeds({len(seed_terms)}, w={seed_weight:.1f})"
        elif self.seed_grammar:
            seed_label = " +grammar"
        import logging as _log; _log.getLogger(__name__).debug(f"  Vocab frozen: {self.fish.vocab[:10]}... (d={self.d}, "
              f"size={len(self.fish.vocab)}{seed_label})", file=sys.stderr)

        # Crystallize all — with progress output every 10 docs
        source_name = path.name if not path.is_dir() else str(path)
        new_crystals = []
        for i, text in enumerate(texts):
            c = self.fish.crystallize_text(text, source=source_name)
            if c:
                new_crystals.append(c)
            if (i + 1) % 10 == 0 or (i + 1) == total:
                import logging as _log; _log.getLogger(__name__).debug(f"[{i+1}/{total}] {len(new_crystals)} crystals...")

        # Couple crystals for formation detection
        if new_crystals:
            self.fish._compute_couplings(new_crystals)
            self.docs_ingested += 1
            self.rebuild_formations()

            # Capture initial R(n) after first batch
            r_n = self._compute_r_n()
            self.r_n_history.append(r_n)

            # Capture post-eat snapshot as baseline for future formative cycles
            if self.current_snapshot is None:
                self.current_snapshot = self._build_state_snapshot()

            self._save_state()
            import logging as _log; _log.getLogger(__name__).debug(f"  Done: {len(new_crystals)} crystals, {len(self.formations)} formations, "
                  f"R(n)={r_n:.4f}", file=sys.stderr)

        return {
            "crystals_added": len(new_crystals),
            "total_crystals": len(self.fish.crystals),
            "formations": len(self.formations),
        }

    # -------------------------------------------------------------------
    # RE-EAT — the formative assessment cycle
    # -------------------------------------------------------------------
    # The re-eat IS the formative assessment. One operation, two lenses.
    # Compression lens: the fish re-learns, re-freezes, re-crystallizes.
    # Assessment lens: what survived? what changed? adjust instruction.
    #
    # RTI parallel: progress monitoring probe. The probe IS the instruction.
    # You don't stop teaching to test. The test IS the teaching viewed
    # through a different lens. Hattie d=1.29.

    def re_eat(self) -> dict:
        """Full re-eat cycle with integrated formative assessment.

        This is the highest-value operation in the engine. It simultaneously:
        1. Re-learns from accumulated pending texts (compression)
        2. Measures what changed since last cycle (assessment)
        3. Adjusts seed_weights based on what the data shows (differentiation)
        4. Re-freezes with adjusted parameters (new instruction level)
        5. Tracks R(n) delta (progress monitoring)

        The re-eat cycle triggered when pending > 10% of corpus.
        The assessment is not a gate or a separate step. It is the
        re-eat viewed through the measurement lens.

        Returns dict with re-eat results and assessment data.
        """
        import os as _os

        # Load pending texts
        pending_texts = []
        pending_path = self.fish.pending_path
        if _os.path.exists(pending_path):
            with open(pending_path) as f:
                for line in f:
                    try:
                        d = json.loads(line)
                        pending_texts.append(d.get('text', ''))
                    except Exception:
                        pass

        if not pending_texts:
            return {"re_eat": False, "reason": "nothing_pending"}

        pending_pct = len(pending_texts) / max(self.fish.vectorizer.doc_count, 1) * 100
        import logging as _log; _log.getLogger(__name__).debug(f"  Re-eating {len(pending_texts)} pending texts "
              f"({pending_pct:.0f}% of corpus)...", file=sys.stderr)

        # Snapshot formations BEFORE re-eat for survival tracking
        pre_formations = {f.name for f in self.formations}

        # --- FORMATIVE ASSESSMENT: measure before changing ---
        # Capture the "before" state. The assessment compares this
        # to the previous snapshot to measure what the last cycle did.
        formative_result = self._formative_assess()

        # Phase 1: Learn from pending (the new instruction)
        self.fish.learn(pending_texts)

        # Phase 2: Re-freeze with assessment-adjusted seeds
        # The formative assessment just updated _seed_weights.
        # Those adjustments flow into the re-freeze here.
        seed_terms, seed_weight = self._resolve_seed_terms()
        self.fish.vocab = self.fish.vectorizer.get_vocab(
            size=self.vocab_size, d=self.d,
            seed_terms=seed_terms,
            seed_weight=seed_weight,
        )
        self.fish.frozen = True
        self.fish.epoch += 1

        # Clear pending
        if _os.path.exists(pending_path):
            _os.remove(pending_path)
        self.fish.pending = []

        # Rebuild formations to see what survived
        self.rebuild_formations()
        post_formations = {f.name for f in self.formations}

        survived = pre_formations & post_formations
        dissolved = pre_formations - post_formations
        emerged = post_formations - pre_formations

        if dissolved or emerged:
            import logging as _log; _log.getLogger(__name__).debug(f"  [re-eat] Survived: {len(survived)}, "
                  f"Dissolved: {len(dissolved)}, "
                  f"Emerged: {len(emerged)}", file=sys.stderr)
            if dissolved:
                import logging as _log; _log.getLogger(__name__).debug(f"Dissolved: {', '.join(sorted(dissolved)[:5])}")
            if emerged:
                import logging as _log; _log.getLogger(__name__).debug(f"Emerged: {', '.join(sorted(emerged)[:5])}")

        self.fish._save_state()
        self._save_state()

        import logging as _log; _log.getLogger(__name__).debug(f"  Re-eat complete. Epoch {self.fish.epoch}. "
              f"Vocab: {self.fish.vocab[:5]}...", file=sys.stderr)

        result = {
            "re_eat": True,
            "epoch": self.fish.epoch,
            "pending_consumed": len(pending_texts),
            "crystal_count": len(self.fish.crystals),
            "formation_count": len(self.formations),
            "survived": sorted(survived),
            "dissolved": sorted(dissolved),
            "emerged": sorted(emerged),
            "r_n": self.r_n_history[-1] if self.r_n_history else None,
        }

        if formative_result:
            result["formative"] = formative_result

        return result

    # -------------------------------------------------------------------
    # QUERY METHODS
    # -------------------------------------------------------------------

    def pfc(self) -> str:
        """Return formations as text for metacognitive overlay injection."""
        if not self.formations:
            if not self.fish.crystals:
                return "Fish is empty. Feed it to build understanding."
            return f"{len(self.fish.crystals)} crystals, no formations yet. Feed more content for patterns to emerge."

        return formations_to_codebook_text(
            self.formations,
            title=f"LiNafish: {self.name}",
            crystals=self.fish.crystals,
        )

    def taste(self, text: str, top: int = 5) -> str:
        """Cross-corpus matching. What does the fish know about this text?"""
        if not self.fish.crystals:
            return "Fish is empty. Nothing to match against."

        if not self.fish.frozen:
            return "Fish hasn't learned enough yet. Feed more content."

        probe = v3_crystallize(text, self.fish.vectorizer,
                               source="query", vocab=self.fish.vocab)
        if not probe or not probe.mi_vector:
            return "Text too short or no signal detected."

        scores = []
        for c in self.fish.crystals:
            vec = c.mi_vector if c.mi_vector else c.resonance
            if not vec:
                continue
            g = gamma(probe.mi_vector, vec)
            if g > 0.2:
                scores.append((g, c))

        scores.sort(key=lambda x: x[0], reverse=True)

        if not scores:
            return "No resonance found. The text doesn't match existing patterns."

        results = [f"Query keywords: {', '.join(probe.keywords)}"]
        results.append(f"Matches: {len(scores)} from {len(self.fish.crystals)} crystals\n")

        for g, c in scores[:top]:
            kw = ', '.join(c.keywords) if c.keywords else 'no keywords'
            results.append(f"[{g:.3f}] {kw}")
            results.append(f"  {c.text[:200]}\n")

        return "\n".join(results)

    def recall(self, query: str, top: int = 10) -> str:
        """Full-text search across all crystals using BM25 ranking.

        BM25 scores each crystal by term frequency, inverse document frequency,
        and document length normalization. Much better than substring matching
        for ranking relevance — a crystal mentioning "gamma" once in 2000 words
        scores lower than one focused on gamma in 100 words.

        Zero external dependencies. The BM25 implementation is inline (~20 lines).

        'What's the SSH password?' is a recall question.
        'How does she handle loss?' is a taste question.
        """
        if not self.fish.crystals:
            return "Fish is empty."

        import math

        query_lower = query.lower()
        terms = query_lower.split()

        # BM25 parameters
        k1 = 1.5   # Term frequency saturation
        b = 0.75   # Document length normalization

        # Build document frequency counts and average length
        doc_texts = [(c, (c.text or "").lower()) for c in self.fish.crystals]
        n_docs = len(doc_texts)
        avg_dl = sum(len(t.split()) for _, t in doc_texts) / max(n_docs, 1)

        # IDF for each query term
        idf = {}
        for term in terms:
            df = sum(1 for _, text in doc_texts if term in text)
            # BM25 IDF with smoothing
            idf[term] = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)

        # Score each crystal
        hits = []
        for c, text_lower in doc_texts:
            words = text_lower.split()
            dl = len(words)
            score = 0.0
            term_hits = 0

            for term in terms:
                if term not in text_lower:
                    continue
                term_hits += 1
                # Term frequency in this document
                tf = words.count(term)
                # BM25 formula
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * dl / max(avg_dl, 1))
                score += idf.get(term, 0) * numerator / denominator

            if term_hits > 0:
                # Bonus for exact phrase match
                if query_lower in text_lower:
                    score += 3.0
                hits.append((score, term_hits, c))

        hits.sort(key=lambda x: x[0], reverse=True)

        if not hits:
            return f"No crystals contain '{query}'."

        results = [f"Found {len(hits)} crystals matching '{query}':\n"]
        for score, term_count, c in hits[:top]:
            source = c.source or "unknown"
            # Show context around the match
            text = c.text or ""
            # Find the best snippet containing query terms
            snippet = text[:300]
            for t in terms:
                idx = text.lower().find(t)
                if idx >= 0:
                    start = max(0, idx - 50)
                    end = min(len(text), idx + 200)
                    snippet = ("..." if start > 0 else "") + text[start:end] + ("..." if end < len(text) else "")
                    break
            results.append(f"[{term_count}/{len(terms)} terms] ({source})")
            results.append(f"  {snippet}\n")

        return "\n".join(results)

    def match(self, text: str, top: int = 3) -> str:
        """Tight recall. Higher threshold than taste."""
        if not self.fish.crystals or not self.fish.frozen:
            return "Fish is empty or not frozen."

        probe = v3_crystallize(text, self.fish.vectorizer,
                               source="query", vocab=self.fish.vocab)
        if not probe or not probe.mi_vector:
            return "Text too short."

        scores = []
        for c in self.fish.crystals:
            vec = c.mi_vector if c.mi_vector else c.resonance
            if not vec:
                continue
            g = gamma(probe.mi_vector, vec)
            if g > 0.4:
                scores.append((g, c))

        scores.sort(key=lambda x: x[0], reverse=True)

        if not scores:
            return "No strong matches."

        results = []
        for g, c in scores[:top]:
            results.append(f"[{g:.3f}] {', '.join(c.keywords)}")
            results.append(f"  {c.text[:300]}\n")

        return "\n".join(results)

    # -------------------------------------------------------------------
    # HEALTH / STATUS
    # -------------------------------------------------------------------

    def health(self) -> str:
        """Engine stats including assessment data."""
        formation_names = [f.name for f in self.formations[:10]]

        health_data = {
            "name": self.name,
            "engine": "v3 (MI x ache)",
            "crystals": len(self.fish.crystals),
            "formations": len(self.formations),
            "docs_ingested": self.docs_ingested,
            "epoch": self.fish.epoch,
            "frozen": self.fish.frozen,
            "vocab_size": len(self.fish.vocab),
            "d": self.d,
            "fish_file": str(self.fish_file),
            "top_formations": formation_names,
            "vocab_sample": self.fish.vocab[:10] if self.fish.vocab else [],
        }

        # Assessment data
        if self.assessment_log:
            health_data["assessment"] = {
                "cycles": len(self.assessment_log),
                "pre_assessed": self._pre_assessed,
                "active_seeds": sum(1 for w in self._seed_weights.values() if w > 0.5),
                "total_seeds": len(self._seed_weights),
                "r_n_latest": self.r_n_history[-1] if self.r_n_history else None,
                "r_n_trend": self.r_n_history[-5:] if self.r_n_history else [],
            }

        return json.dumps(health_data, indent=2)

    def assessment_summary(self) -> str:
        """Return a human-readable summary of the assessment history.

        Shows the RTI trajectory: how the fish adapted over time.
        What the pre-assessment found, what each formative cycle changed,
        and the R(n) curve.
        """
        if not self.assessment_log:
            return "No assessments yet. Feed the fish to begin."

        lines = [f"Assessment History: {self.name}", "=" * 40]

        for entry in self.assessment_log:
            atype = entry.get("type", "unknown")
            epoch = entry.get("epoch", "?")
            ts = entry.get("timestamp", "?")

            if atype == "pre_assessment":
                lines.append(f"\n[PRE] Epoch {epoch} @ {ts}")
                lines.append(f"  Recommended d: {entry.get('recommended_d', '?')}")
                lines.append(f"  Seeds: {entry.get('active_seeds', '?')}/{entry.get('seed_count', '?')} active")
                lines.append(f"  Docs screened: {entry.get('doc_count', '?')}")

            elif atype == "formative":
                lines.append(f"\n[FORMATIVE] Epoch {epoch} @ {ts}")
                r_n = entry.get("r_n")
                if r_n is not None:
                    lines.append(f"  R(n): {r_n:.4f}")
                r_delta = entry.get("r_n_delta")
                if r_delta is not None:
                    direction = "+" if r_delta > 0 else ""
                    lines.append(f"  R(n) delta: {direction}{r_delta:.4f}")
                lines.append(f"  Crystals: {entry.get('crystal_count', '?')}")
                lines.append(f"  Formations: {entry.get('formation_count', '?')}")

                survived = entry.get("survived")
                dissolved = entry.get("dissolved")
                emerged = entry.get("emerged")
                if survived is not None:
                    lines.append(f"  Survived: {survived}")
                if dissolved is not None:
                    lines.append(f"  Dissolved: {dissolved}")
                if emerged is not None:
                    lines.append(f"  Emerged: {emerged}")

        if self.r_n_history:
            lines.append(f"\nR(n) curve: {', '.join(f'{r:.4f}' for r in self.r_n_history)}")
            if len(self.r_n_history) >= 2:
                trend = self.r_n_history[-1] - self.r_n_history[0]
                lines.append(f"Overall trend: {'improving' if trend > 0 else 'declining'} "
                             f"({'+' if trend > 0 else ''}{trend:.4f})")

        return "\n".join(lines)


# Re-export for server.py
from .crystallizer_v3 import MIVectorizer  # noqa
