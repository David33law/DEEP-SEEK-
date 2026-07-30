#!/usr/bin/env python3
"""Have DeepSeek review a repository and produce a concrete roadmap to the highest tier.

A senior-architect review, not a tournament: it gathers a high-signal DIGEST of the repo
(README + contracts + system definitions + a directory map + a sample of the real source),
sends it to DeepSeek with a rigorous "bring this to the absolute top tier" prompt, and writes
the answer to a Markdown roadmap. Cheap and honest: `--dry-run` shows the exact size and a cost
ESTIMATE before you spend anything, and every run prints the real token usage afterwards.

    export DEEPSEEK_API_KEY=sk-...          # (PowerShell:  $env:DEEPSEEK_API_KEY="sk-...")
    python deepseek_review.py --repo .                 # review the current repo
    python deepseek_review.py --repo . --dry-run       # just show size + cost estimate, no call

Only the Python standard library is used; drop this file into any repo and run it.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# Read in priority order; the first ones matter most and are never truncated.
PRIORITY_DOCS = [
    "README.md", "CLAUDE.md", "SYSTEM-HIERARCHY.txt", "SEMANTIC-CONTRACT.md",
    "DEPENDENCY-CONTRACT.md", "CHANGELOG.md", "PROVENANCE.yaml", "DEPLOY-PRODUCTION.md",
    "ARCHITECTURE.md", "DESIGN.md",
]
EXCLUDE_DIRS = {".git", "third-party", "deps", "node_modules", "__pycache__", "output",
                "output_run1", "dist", "build", ".venv", "venv", "vendor"}
SOURCE_EXT = (".lisp", ".py", ".go", ".rs", ".ts", ".c", ".h", ".cpp", ".java", ".scala", ".clj")
# EUR per 1M tokens (estimate; DeepSeek is among the cheapest top models). Adjust with --price.
PRICE = {"deepseek-reasoner": (0.55, 2.19), "deepseek-chat": (0.27, 1.10)}


def read(path, limit=None):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        return s[:limit] if limit else s
    except OSError:
        return None


def tree(root, max_entries=400):
    """A pruned directory map (first-party only), one line per dir with a file count."""
    lines, n = [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith("."))
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > 3:
            dirnames[:] = []
            continue
        code = sum(1 for f in filenames if f.endswith(SOURCE_EXT))
        lines.append(f"{'  ' * depth}{os.path.basename(dirpath) if rel != '.' else '.'}/  "
                     f"({len(filenames)} files{', ' + str(code) + ' source' if code else ''})")
        n += 1
        if n >= max_entries:
            lines.append("  … (tree truncated)")
            break
    return "\n".join(lines)


def source_inventory(root, cap=80):
    """List first-party source files by size, and return the biggest for header sampling."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(SOURCE_EXT):
                p = os.path.join(dirpath, f)
                try:
                    files.append((os.path.getsize(p), os.path.relpath(p, root), p))
                except OSError:
                    pass
    files.sort(reverse=True)
    inv = "\n".join(f"  {sz:>8}  {rel}" for sz, rel, _ in files[:cap])
    if len(files) > cap:
        inv += f"\n  … and {len(files) - cap} more source files"
    return inv, files, len(files)


def build_digest(root, max_chars, header_lines):
    parts = [f"# REPOSITORY DIGEST: {os.path.basename(os.path.abspath(root))}\n"]

    parts.append("\n## KEY DOCUMENTS & CONTRACTS\n")
    seen = set()
    for name in PRIORITY_DOCS:
        p = os.path.join(root, name)
        if os.path.isfile(p):
            seen.add(name)
            parts.append(f"\n----- {name} -----\n{read(p)}\n")
    # any other top-level *.md not already included
    for f in sorted(os.listdir(root)):
        if f.endswith(".md") and f not in seen and os.path.isfile(os.path.join(root, f)):
            parts.append(f"\n----- {f} -----\n{read(os.path.join(root, f), 6000)}\n")

    asd = sorted(f for f in os.listdir(root) if f.endswith(".asd"))
    if asd:
        parts.append("\n## SYSTEM DEFINITIONS (architecture)\n")
        for f in asd:
            parts.append(f"\n----- {f} -----\n{read(os.path.join(root, f))}\n")

    parts.append("\n## DIRECTORY MAP\n" + tree(root) + "\n")

    inv, files, total = source_inventory(root)
    parts.append(f"\n## SOURCE INVENTORY ({total} first-party source files, largest first)\n" + inv + "\n")

    # sample the HEADERS of the biggest first-party source files, within the remaining budget
    parts.append("\n## SOURCE SAMPLES (headers of the largest modules)\n")
    used = sum(len(p) for p in parts)
    for _sz, rel, p in files:
        if used >= max_chars:
            parts.append("\n… (source samples truncated to stay within budget)\n")
            break
        head = "\n".join((read(p) or "").splitlines()[:header_lines])
        block = f"\n----- {rel} (first {header_lines} lines) -----\n{head}\n"
        parts.append(block)
        used += len(block)

    digest = "".join(parts)
    truncated = len(digest) > max_chars
    return (digest[:max_chars] + "\n… (digest truncated)\n") if truncated else digest, total


SYSTEM_PROMPT = (
    "You are a world-class systems architect and legal-AI domain expert conducting a rigorous, "
    "honest technical review. You do not flatter. You cite concrete files and modules. You mark "
    "UNKNOWN where the provided material is insufficient rather than guessing. Your single goal is "
    "to tell the owner exactly how to bring this system to the ABSOLUTE HIGHEST TIER of quality, "
    "correctness, and capability."
)

USER_TEMPLATE = """Below is a high-signal digest of a repository (a Common Lisp legal-reasoning
platform called LAWMAX-Ω, plus its contracts and architecture). Study it, then produce a report
with EXACTLY these sections:

1. WHAT THIS SYSTEM IS — in 5-8 lines, from the evidence only.
2. CURRENT-TIER ASSESSMENT — grade each dimension (architecture, correctness/verification,
   robustness, performance, testing, security, legal-domain completeness, operability) as
   S / A / B / C / D with a one-line justification citing the evidence.
3. TOP GAPS TO THE HIGHEST TIER — the specific things standing between this system and S-tier,
   most important first, each tied to a file/module/contract.
4. PRIORITISED ROADMAP — concrete, ordered phases. For each item: what to change, which
   file/module, why it raises the tier, and rough effort (S/M/L).
5. QUICK WINS — high-value, low-effort changes doable immediately.
6. WHAT I COULD NOT ASSESS — honestly, what the digest did not let you judge, and what to send
   next for a deeper review.

Be specific and demanding. This is the owner's real system; vague advice is worthless.

===== DIGEST =====
{digest}
"""


def call_deepseek(endpoint, model, key, system, user, max_output_tokens, timeout):
    body = {"model": model, "temperature": 0.2, "max_tokens": max_output_tokens,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}]}
    req = urllib.request.Request(
        endpoint, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        obj = json.loads(r.read().decode("utf-8"))
    content = obj["choices"][0]["message"].get("content") or ""
    if obj["choices"][0].get("finish_reason") == "length":
        content += "\n\n> [truncated by output limit — raise --max-output-tokens for the full report]"
    return content, obj.get("usage", {})


def approx_tokens(chars):
    return chars // 4   # ~4 chars/token, good enough for a pre-flight estimate


def main():
    ap = argparse.ArgumentParser(description="DeepSeek repo review → highest-tier roadmap")
    ap.add_argument("--repo", default=".", help="path to the repository to review")
    ap.add_argument("--model", default="deepseek-reasoner",
                    help="deepseek-reasoner (deep, default) or deepseek-chat (cheaper)")
    ap.add_argument("--endpoint", default=os.environ.get("DEEPSEEK_ENDPOINT",
                                                         "https://api.deepseek.com/chat/completions"))
    ap.add_argument("--out", default="LAWMAX-UPGRADE-ROADMAP.md")
    ap.add_argument("--max-chars", type=int, default=180_000, help="digest size cap (~45k tokens)")
    ap.add_argument("--header-lines", type=int, default=45, help="lines sampled per source file")
    ap.add_argument("--max-output-tokens", type=int, default=8000)
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--dry-run", action="store_true", help="show size + cost estimate, do not call")
    a = ap.parse_args()

    if not os.path.isdir(a.repo):
        sys.exit(f"no such directory: {a.repo}")

    digest, n_src = build_digest(a.repo, a.max_chars, a.header_lines)
    user = USER_TEMPLATE.format(digest=digest)
    in_tok = approx_tokens(len(SYSTEM_PROMPT) + len(user))
    pin, pout = PRICE.get(a.model, PRICE["deepseek-reasoner"])
    est = in_tok / 1e6 * pin + a.max_output_tokens / 1e6 * pout

    print(f"repo:            {os.path.abspath(a.repo)}")
    print(f"source files:    {n_src}")
    print(f"digest size:     {len(digest):,} chars  (~{in_tok:,} input tokens)")
    print(f"model:           {a.model}")
    print(f"cost ESTIMATE:   ~€{est:.3f}   (input ~{in_tok:,} tok + up to {a.max_output_tokens:,} output tok)")

    if a.dry_run:
        print("\n[dry-run] nothing sent. Re-run without --dry-run (and with DEEPSEEK_API_KEY set) to review.")
        return 0

    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        sys.exit("DEEPSEEK_API_KEY is not set — refusing to attempt a call.")

    print("\n· calling DeepSeek …")
    try:
        content, usage = call_deepseek(a.endpoint, a.model, key, SYSTEM_PROMPT, user,
                                       a.max_output_tokens, a.timeout)
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")
    except urllib.error.URLError as e:
        sys.exit(f"network error: {e.reason}")

    with open(a.out, "w", encoding="utf-8") as f:
        f.write(f"# LAWMAX-Ω — DeepSeek review & roadmap to the highest tier\n\n"
                f"_Model: {a.model}. This is an AI assessment; verify each claim against the code._\n\n")
        f.write(content)

    it, ot = usage.get("prompt_tokens", in_tok), usage.get("completion_tokens", 0)
    real = it / 1e6 * pin + ot / 1e6 * pout
    print(f"\n✔ wrote {a.out}")
    print(f"  tokens: {it:,} in + {ot:,} out   |   actual cost ≈ €{real:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
