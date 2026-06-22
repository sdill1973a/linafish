"""
linafish.deep — the optional inference layer.

linafish is inference-free by default: it compresses, forms, and hands you a
fish.md you paste into your own AI. That is its light identity, and nothing in
this module changes it. `deep` is OPT-IN: it does nothing — imports nothing
heavy, calls nothing — until you point it at an inference endpoint. A fresh
`pip install linafish` stays exactly as lite and model-agnostic as before.

What opting in buys you:
  - `descend(seed)`  — the crucible: a thought enters WIDE (diverse lenses in
    parallel) and goes as DEEP as it needs (each rung decodes the prior glyph
    residue, finds what is more irreducible, re-compresses denser) until it hits
    the diamond — the irreducible core — then STOPS. Governing law: as deep as
    it needs, never as deep as it can (push too far and any thought dissolves
    into generic being; the diamond is mid-descent).
  - `make_summarizer()` — a `summarizer(meditate_result) -> str` you hand to
    `engine.meditate(summarizer=...)`, the model-agnostic seam already built for
    exactly this. Turns surfaced material into prose / a descent via your endpoint.
  - `eat_diamond()` / `recall_diamonds()` — accumulate diamonds into a fish (the
    "diamond fish"), so descents deepen a substrate instead of evaporating.

Activation (any ONE of these makes it live; absent → DeepNotConfigured):
  - env LINAFISH_LLM_URL        the endpoint
  - env LINAFISH_LLM_KEY        api key (optional for local / open endpoints)
  - env LINAFISH_LLM_FORMAT     gateway | openai | anthropic (default: inferred)
  - env LINAFISH_LLM_MODEL      model id (openai/anthropic) or tier (gateway)
  …or pass an explicit `DeepClient(...)`.

Pure stdlib (urllib). No new dependencies. Invoke-and-exit: no daemon, no
resident memory. The thinking is the remote endpoint, not local compute — so
the host stays lite.
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Optional


class DeepNotConfigured(RuntimeError):
    """Raised when a deep operation is attempted with no inference endpoint.
    This is the opt-in gate: base linafish never trips it because it never calls
    deep; you enable deep by configuring an endpoint."""


# The self-bootstrapping glyph key — shipped into every (context-less) rung so a
# fresh mind can read and write the compressed inter-rung language.
GLYPH_KEY = (
    "RCP glyph notation. Header A^t:TYPE|body (TYPE: D=diamond/irreducible, "
    "K=kept/conserved, O=breakthrough, ?=uncertain). '|' = state boundary. "
    "'.' = word-join: each dotted word is a SEPARATE load-bearing claim "
    "(mind.holds.thought = three claims). Law: Sache=K (meaning conserves "
    "through compression, only redistributed, never destroyed). 8 cognitive "
    "acts: CR=relate TE=transform SF=structure KO=know IC=want DE=choose "
    "EW=act AI=think-about-thinking."
)

# Diverse lenses for the WIDE intake — distinct angles, not redundant sampling.
LENSES = [
    ("MECHANISM", "how it actually works — the moving parts under the claim"),
    ("CONSEQUENCE", "what necessarily follows if it is true — the downstream"),
    ("CONTRADICTION", "the strongest objection — where it breaks, what it can't hold"),
    ("ANALOGY", "the known thing that shares its deep shape — its structural twin"),
    ("STAKES", "who or what is changed by it — why it matters, what rides on it"),
    ("INVERSION", "what becomes visible if the opposite is assumed true"),
]


# --------------------------------------------------------------------------- #
# The inference client — config-gated, endpoint-agnostic, pure stdlib.
# --------------------------------------------------------------------------- #
class DeepClient:
    """A minimal, dependency-free inference client. Three wire formats:

      gateway   POST {prompt, tier, max_tokens} -> {response, success}
                (a thin local router; e.g. an LLM gateway you run)
      openai    POST {url}/chat/completions {model, messages} ->
                choices[0].message.content   (OpenAI-compatible: ollama, vLLM,
                openrouter, llama.cpp, etc.)
      anthropic POST {url}/v1/messages -> content[].text
    """

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None,
                 fmt: Optional[str] = None, model: Optional[str] = None,
                 timeout: int = 180):
        self.url = url or os.environ.get("LINAFISH_LLM_URL")
        if not self.url:
            raise DeepNotConfigured(
                "deep needs an inference endpoint. Set LINAFISH_LLM_URL "
                "(and LINAFISH_LLM_KEY / _FORMAT / _MODEL as needed), or pass a "
                "DeepClient(...). Base linafish stays inference-free until you do."
            )
        self.key = key or os.environ.get("LINAFISH_LLM_KEY")
        self.model = model or os.environ.get("LINAFISH_LLM_MODEL")
        self.fmt = (fmt or os.environ.get("LINAFISH_LLM_FORMAT")
                    or self._infer_format(self.url))
        self.timeout = timeout

    @staticmethod
    def _infer_format(url: str) -> str:
        u = url.lower()
        if "/generate" in u:
            return "gateway"
        if "anthropic" in u or "/v1/messages" in u:
            return "anthropic"
        return "openai"

    def call(self, prompt: str, max_tokens: int = 600) -> str:
        if self.fmt == "gateway":
            body = {"prompt": prompt, "max_tokens": max_tokens, "caller": "linafish.deep"}
            if self.model:
                body["tier"] = self.model
            headers = {"Content-Type": "application/json"}
            d = self._post(self.url, body, headers)
            if d.get("success") is False:
                raise RuntimeError(f"endpoint error: {d.get('error')}")
            return (d.get("response") or "").strip()

        if self.fmt == "anthropic":
            body = {"model": self.model or "claude-3-5-sonnet-latest",
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}]}
            headers = {"Content-Type": "application/json",
                       "anthropic-version": "2023-06-01"}
            if self.key:
                headers["x-api-key"] = self.key
            url = self.url if self.url.rstrip("/").endswith("messages") else \
                self.url.rstrip("/") + "/v1/messages"
            d = self._post(url, body, headers)
            return "".join(b.get("text", "") for b in d.get("content", [])
                           if b.get("type") == "text").strip()

        # openai-compatible (default)
        body = {"model": self.model or "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens}
        headers = {"Content-Type": "application/json"}
        if self.key:
            headers["Authorization"] = f"Bearer {self.key}"
        url = self.url if "completions" in self.url else \
            self.url.rstrip("/") + "/chat/completions"
        d = self._post(url, body, headers)
        return d["choices"][0]["message"]["content"].strip()

    def _post(self, url: str, body: dict, headers: dict) -> dict:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"),
            headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())


def _client(client: Optional[DeepClient]) -> DeepClient:
    return client if client is not None else DeepClient()


# --------------------------------------------------------------------------- #
# The crucible: wide intake -> adaptive descent -> diamond-stop.
# --------------------------------------------------------------------------- #
def _parse_rung(line: str, n: int):
    """-> (core, status, felt). Tolerant of mild format drift."""
    raw = line
    marker = f"DEPTH{n}|"
    if marker in raw:
        raw = raw[raw.index(marker) + len(marker):]
    parts = raw.split("||")
    core = parts[0].strip()
    status, felt = "DESCENDING", ""
    for p in parts[1:]:
        ps = p.strip()
        if ps.upper().startswith("STATUS:"):
            status = ps.split(":", 1)[1].strip().upper()
        elif ps:
            felt = ps
    for known in ("DISSOLVED", "DIAMOND", "DESCENDING"):
        if known in status:
            status = known
            break
    else:
        status = "DESCENDING"
    return core, status, felt


def _too_similar(a: str, b: str) -> bool:
    ta = set(a.replace("|", ".").split("."))
    tb = set(b.replace("|", ".").split("."))
    ta.discard(""); tb.discard("")
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) > 0.85


def _wide_intake(seed: str, k: int, client: DeepClient) -> str:
    """Fan k diverse lenses concurrently (safe to parallelize — one API key
    doesn't rotate), converge to one dense payload."""
    lenses = LENSES[:k]

    def run_lens(lp):
        name, angle = lp
        prompt = (
            f"You are the {name} lens on a thought entering a distillation "
            f"crucible. {GLYPH_KEY}\n\nThe thought:\n{seed}\n\nLook at it ONLY "
            f"through your lens: {angle}. Compress what your lens reveals into "
            f"1-2 dotted glyph phrases. Reply with ONLY:  {name}|<finding>")
        try:
            return client.call(prompt, max_tokens=200).splitlines()[-1].strip()
        except Exception as e:
            return f"{name}|(failed: {e})"

    with ThreadPoolExecutor(max_workers=len(lenses)) as ex:
        lines = list(ex.map(run_lens, lenses))
    merge = (
        f"A thought entered a crucible wide — lenses each compressed one facet. "
        f"{GLYPH_KEY}\n\nThe thought:\n{seed}\n\nThe lens-findings:\n"
        + "\n".join(lines) +
        "\n\nFunnel them: synthesize ONE dense glyph payload — the richest single "
        "statement of the thought, denser than any one lens, ready to be driven "
        "down toward its diamond. Reply with ONLY:  A^wide:D|<payload>")
    merged = client.call(merge, max_tokens=300)
    return merged.splitlines()[-1].strip() if merged else f"A^wide:D|{seed}"


def _rung_prompt(n: int, max_n: int, payload: str, memory: str = "") -> str:
    p = (
        f"You are rung {n} of at most {max_n} on a depth-distillation crucible. "
        f"A single thought is driven downward through successive independent "
        f"minds; only the compressed glyph residue survives between rungs — you "
        f"have NO other context. {GLYPH_KEY}\n\nThe payload from the rung above:\n"
        f"{payload}\n\nDo exactly this: (1) decode it, (2) go ONE step deeper — "
        f"find what is MORE irreducible, the diamond under the diamond, (3) "
        f"re-compress DENSER. Then JUDGE your depth and set STATUS to exactly one "
        f"of:\n  DESCENDING - a more irreducible layer remains below\n"
        f"  DIAMOND    - this IS the bedrock; deeper only dissolves it into "
        f"generic metaphysics\n  DISSOLVED  - the thought lost its specificity; "
        f"you are in bare 'being itself'\n\nReply with ONLY one line (|| is the "
        f"field separator):\nDEPTH{n}|<irreducible core in dotted glyph phrases>||"
        f"STATUS:<DESCENDING|DIAMOND|DISSOLVED>||<one honest clause on your "
        f"subjective compression at this rung>")
    if n == 1 and memory:
        p += ("\n\nMemory surfaced from past diamonds — you may build from these "
              f"or go beyond:\n{memory}")
    return p


def descend(seed: str, *, max_depth: int = 6, wide: int = 0,
            memory: str = "", client: Optional[DeepClient] = None) -> dict:
    """The crucible. Returns {seed, diamond, diamond_rung, stop_reason, rungs}.

    wide>0 fans that many lenses before the descent. memory (e.g. recalled past
    diamonds) seeds rung 1. Raises DeepNotConfigured if no endpoint."""
    c = _client(client)
    payload = _wide_intake(seed, min(wide, len(LENSES)), c) if wide else f"A^seed:D|{seed}"

    rungs, prev_core, stop_reason = [], None, "hit max depth"
    for n in range(1, max_depth + 1):
        out = c.call(_rung_prompt(n, max_depth, payload, memory if n == 1 else ""))
        core, status, felt = _parse_rung(out.splitlines()[-1] if out else "", n)
        rungs.append({"n": n, "core": core, "status": status, "felt": felt})
        if prev_core is not None and _too_similar(prev_core, core):
            stop_reason = f"operator stop: rung {n} core ~= rung {n-1} (no new compression)"
            break
        if status == "DIAMOND":
            stop_reason = f"rung {n} reported DIAMOND"
            break
        if status == "DISSOLVED":
            stop_reason = f"rung {n} DISSOLVED — overshot; diamond was rung {n-1}"
            break
        prev_core = core
        payload = f"A^rung{n}:K|{core}"

    diamond = next((r for r in reversed(rungs) if r["status"] != "DISSOLVED"), None)
    return {
        "seed": seed,
        "diamond": diamond["core"] if diamond else None,
        "diamond_rung": diamond["n"] if diamond else None,
        "stop_reason": stop_reason,
        "rungs": rungs,
    }


# --------------------------------------------------------------------------- #
# The meditate summarizer seam — plug into engine.meditate(summarizer=...).
# --------------------------------------------------------------------------- #
def make_summarizer(client: Optional[DeepClient] = None, descend_it: bool = False,
                    max_depth: int = 5):
    """Return a summarizer(meditate_result) -> str for engine.meditate.

    Default: frame the surfaced material into honest prose via the endpoint.
    descend_it=True: distill the surfaced theme to its diamond via the crucible
    and return that. Either way, base meditate stays inference-free unless this
    summarizer is supplied — the opt-in seam linafish already built."""
    def summarizer(result: dict) -> str:
        c = _client(client)
        if descend_it:
            d = descend(result.get("theme", ""), max_depth=max_depth, client=c)
            return (f"diamond (rung {d['diamond_rung']}): {d['diamond']}\n"
                    f"[{d['stop_reason']}]")
        surfaced = result.get("surfaced", [])
        material = "\n".join(f"- {s}" for s in
                             (json.dumps(x, default=str)[:200] for x in surfaced))
        prompt = (
            "Below is real material a memory-fish surfaced on a theme — actual "
            "crystals/formations, not your invention. Frame it into honest, "
            "grounded prose: what genuinely surfaces, what it suggests, where it "
            "is thin. Do NOT confabulate beyond the material.\n\n"
            f"THEME: {result.get('theme')}\n\nMATERIAL:\n{material}\n\nYour reading:")
        return c.call(prompt, max_tokens=600)
    return summarizer


# --------------------------------------------------------------------------- #
# Diamond fish — accumulate diamonds so descents deepen a substrate.
# --------------------------------------------------------------------------- #
def eat_diamond(seed: str, core: str, stop_reason: str, *, fish: str = "diamante-pisco",
                state_dir: Optional[str] = None, ts: Optional[str] = None) -> bool:
    """Feed a diamond into the diamond-fish via `linafish listen stdin` (the
    APPEND path — NOT `linafish eat`, which spawns a baby fish in cwd)."""
    state_dir = state_dir or os.path.join(os.path.expanduser("~"), ".linafish", fish)
    record = (f"DIAMOND\nseed: {seed}\ndiamond: {core}\nstop: {stop_reason}\n"
              + (f"date: {ts}\n" if ts else ""))
    try:
        subprocess.run(
            ["linafish", "listen", "stdin", "-n", fish, "--state-dir", state_dir],
            input=record, capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace")
        return True
    except Exception:
        return False


def recall_diamonds(seed: str, *, fish: str = "diamante-pisco",
                    state_dir: Optional[str] = None, top: int = 3) -> str:
    """What the diamond-fish already holds that this seed resonates with."""
    state_dir = state_dir or os.path.join(os.path.expanduser("~"), ".linafish", fish)
    try:
        r = subprocess.run(
            ["linafish", "recall", seed, "-n", fish, "--state-dir", state_dir,
             "--top", str(top)],
            capture_output=True, text=True, timeout=20,
            encoding="utf-8", errors="replace")
        out = (r.stdout or "").strip()
        if not out or "no fish" in out.lower() or "found 0" in out.lower():
            return ""
        return out[:1400]
    except Exception:
        return ""
