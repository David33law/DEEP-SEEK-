#!/usr/bin/env python3
"""DeepSeek reads a repository IN FULL and returns a roadmap to the highest tier.

One mode only: it reads EVERY first-party source file and contract (never a sample), analyses
the whole codebase in parallel, then synthesises one demanding roadmap — with deep reasoning
(deepseek-reasoner) by default. `--dry-run` shows the exact size and a cost ESTIMATE before you
spend anything; every real run prints the actual token usage afterwards.

    python deepseek_review.py --repo .                 # review the current repo
    python deepseek_review.py --repo . --dry-run       # size + cost estimate, no call

Asks for your DeepSeek API key at runtime and starts on entry (no environment variable needed).
Only the Python standard library is used.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

PRIORITY_DOCS = [
    "README.md", "CLAUDE.md", "SYSTEM-HIERARCHY.txt", "SEMANTIC-CONTRACT.md",
    "DEPENDENCY-CONTRACT.md", "CHANGELOG.md", "PROVENANCE.yaml", "DEPLOY-PRODUCTION.md",
    "ARCHITECTURE.md", "DESIGN.md",
]
EXCLUDE_DIRS = {".git", "third-party", "deps", "node_modules", "__pycache__", "output",
                "output_run1", "dist", "build", ".venv", "venv", "vendor"}
CODE_EXT = (".lisp", ".lsp", ".cl", ".asd", ".md", ".txt", ".yaml", ".yml", ".sh", ".py")
PRICE = {"deepseek-reasoner": (0.55, 2.19), "deepseek-chat": (0.27, 1.10)}   # EUR / 1M tok (est.)


def read(path, limit=None):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            s = f.read()
        return s[:limit] if limit else s
    except OSError:
        return None


def approx_tokens(chars):
    return chars // 4


def tree(root, max_entries=400):
    lines, n = [], 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith("."))
        rel = os.path.relpath(dirpath, root)
        depth = 0 if rel == "." else rel.count(os.sep) + 1
        if depth > 3:
            dirnames[:] = []
            continue
        code = sum(1 for f in filenames if f.endswith(CODE_EXT))
        lines.append(f"{'  ' * depth}{os.path.basename(dirpath) if rel != '.' else '.'}/  "
                     f"({len(filenames)} files{', ' + str(code) + ' source' if code else ''})")
        n += 1
        if n >= max_entries:
            lines.append("  … (tree truncated)")
            break
    return "\n".join(lines)


def arch_context(root):
    """Contracts + system definitions + directory map — the framing for the final synthesis
    (the actual code is read in full by the map pass, so no source is sampled here)."""
    parts = ["## KEY DOCUMENTS & CONTRACTS\n"]
    seen = set()
    for name in PRIORITY_DOCS:
        p = os.path.join(root, name)
        if os.path.isfile(p):
            seen.add(name)
            parts.append(f"\n----- {name} -----\n{read(p)}\n")
    for f in sorted(os.listdir(root)):
        if f.endswith(".md") and f not in seen and os.path.isfile(os.path.join(root, f)):
            parts.append(f"\n----- {f} -----\n{read(os.path.join(root, f), 6000)}\n")
    for f in sorted(x for x in os.listdir(root) if x.endswith(".asd")):
        parts.append(f"\n----- {f} -----\n{read(os.path.join(root, f))}\n")
    parts.append("\n## DIRECTORY MAP\n" + tree(root) + "\n")
    return "".join(parts)


def gather_corpus(root):
    """EVERY first-party source file and contract, in FULL. Third-party, deps and generated
    data are excluded — they are not logic to improve."""
    out = []
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for f in sorted(fn):
            if f.endswith(CODE_EXT):
                c = read(os.path.join(dp, f))
                if c is not None:
                    out.append((os.path.relpath(os.path.join(dp, f), root), c))
    return sorted(out)


def make_chunks(files, budget_chars):
    chunks, cur, size = [], [], 0
    for rel, c in files:
        block = f"\n===== FILE: {rel} =====\n{c}\n"
        if len(block) > budget_chars:
            if cur:
                chunks.append(cur); cur, size = [], 0
            for i in range(0, len(block), budget_chars):
                chunks.append([(rel, block[i:i + budget_chars])])
            continue
        if size + len(block) > budget_chars and cur:
            chunks.append(cur); cur, size = [], 0
        cur.append((rel, block)); size += len(block)
    if cur:
        chunks.append(cur)
    return chunks


MAP_SYSTEM = (
    "You are a world-class systems architect and legal-AI expert reviewing PART of a large "
    "Common Lisp system (LAWMAX-Ω). You are terse, specific, and honest; you never flatter and "
    "never pad. You cite exact file names.")
MAP_USER = (
    "Analyse the files below (one part of the whole codebase). For each meaningful module output:\n"
    "- FILE(s), one line on PURPOSE;\n- QUALITY: S/A/B/C/D + a one-line reason;\n"
    "- WEAKNESSES: concrete and specific (bugs, coupling, missing checks, perf, unclear invariants);\n"
    "- UPGRADES: concrete changes that would raise it toward the highest tier.\n"
    "Be compact. Dismiss trivial/boilerplate files in one line. Do NOT write a generic summary.\n\n{body}")

CONSOLIDATE_SYSTEM = MAP_SYSTEM
CONSOLIDATE_USER = (
    "Consolidate the partial analyses below (each covers part of the same codebase) into a compact "
    "but COMPLETE synthesis. Keep every concrete weakness, upgrade and file reference; remove only "
    "repetition. Preserve the S/A/B/C/D grades.\n\n{body}")

REDUCE_SYSTEM = (
    "You are a world-class systems architect and legal-AI domain expert conducting a rigorous, "
    "honest final review. You do not flatter. You cite concrete files and modules. You mark UNKNOWN "
    "where evidence is insufficient. Your goal is to tell the owner exactly how to bring this system "
    "to the ABSOLUTE HIGHEST TIER.")
REDUCE_USER = (
    "Below are (a) the system's contracts/architecture and (b) analyses that together cover the "
    "ENTIRE codebase of LAWMAX-Ω. Produce the definitive review with EXACTLY these sections:\n"
    "1. WHAT THIS SYSTEM IS (5-8 lines).\n"
    "2. CURRENT-TIER ASSESSMENT — grade each dimension (architecture, correctness/verification, "
    "robustness, performance, testing, security, legal-domain completeness, operability) S/A/B/C/D "
    "with a one-line justification.\n"
    "3. TOP GAPS TO THE HIGHEST TIER — most important first, each tied to a file/module.\n"
    "4. PRIORITISED ROADMAP — ordered phases; each item: what to change, which file/module, why it "
    "raises the tier, rough effort (S/M/L).\n"
    "5. QUICK WINS.\n"
    "6. RESIDUAL RISKS / WHAT STILL NEEDS A HUMAN.\n"
    "Be demanding and concrete. This is the owner's real system.\n\n"
    "===== CONTRACTS & ARCHITECTURE =====\n{arch}\n\n===== CODEBASE ANALYSES =====\n{maps}\n")


ESCALATE_SYSTEM = (
    "You are the most demanding reviewer alive, bound by the owner's SUPREME LAW: nothing "
    "mediocre — ONLY the highest implementation. If a STRICTLY SUPERIOR conception exists, the "
    "current one does not qualify and must be replaced, even if the change is larger. You never "
    "flatter, you cite concrete files/modules/mechanisms, and you never invent progress.")
ESCALATE_CRITIQUE = (
    "Grounding (whole-codebase understanding + contracts):\n{grounding}\n\n"
    "CURRENT highest-tier vision & roadmap for LAWMAX-Ω:\n---\n{vision}\n---\n\n"
    "Attack it. Is there a STRICTLY SUPERIOR conception — a better target architecture, or a "
    "materially more correct/complete/robust roadmap — worth climbing to? Be concrete and specific.\n"
    "ONLY if you genuinely cannot find ANY strictly higher conception worth pursuing (i.e. climbing "
    "further is not worthwhile — this IS the ceiling), reply with 'CEILING_REACHED' as the very "
    "first line, then 3-6 lines justifying why this is the supreme, un-improvable target. Otherwise, "
    "describe precisely the higher conception and why it dominates the current one.")
ESCALATE_IMPROVE = (
    "Rewrite the vision & roadmap to fully incorporate this strictly-higher conception. Output the "
    "COMPLETE improved version (all six sections), concrete and prioritised — not a diff.\n\n"
    "CURRENT:\n---\n{vision}\n---\n\nHIGHER CONCEPTION TO INCORPORATE:\n{critique}\n")


def escalate_to_ceiling(vision, grounding, a, key, spent):
    """Climb until DeepSeek can find no strictly higher conception, confirmed by `dry_required`
    consecutive 'CEILING_REACHED' rounds — the owner's supreme law as a stop condition. Bounded
    by --max-rounds and --budget-eur so it converges rather than runs forever."""
    pin, pout = PRICE.get(a.model, PRICE["deepseek-reasoner"])
    dry, rnd, log = 0, 0, []
    g = grounding[:120_000]
    while dry < a.dry_required and rnd < a.max_rounds:
        if a.budget_eur and spent[0] >= a.budget_eur:
            log.append(f"round {rnd + 1}: stopped — budget €{a.budget_eur} reached"); break
        rnd += 1
        crit, u = call_deepseek(a.endpoint, a.model, key, ESCALATE_SYSTEM,
                                ESCALATE_CRITIQUE.format(grounding=g, vision=vision),
                                a.max_output_tokens, a.timeout)
        spent[0] += u.get("prompt_tokens", 0) / 1e6 * pin + u.get("completion_tokens", 0) / 1e6 * pout
        if crit.strip().upper().startswith("CEILING_REACHED") or "CEILING_REACHED" in crit[:120].upper():
            dry += 1
            log.append(f"round {rnd}: no strictly higher conception found  (ceiling {dry}/{a.dry_required})")
            continue
        dry = 0
        vision, u2 = call_deepseek(a.endpoint, a.model, key, ESCALATE_SYSTEM,
                                   ESCALATE_IMPROVE.format(vision=vision, critique=crit),
                                   a.max_output_tokens, a.timeout)
        spent[0] += u2.get("prompt_tokens", 0) / 1e6 * pin + u2.get("completion_tokens", 0) / 1e6 * pout
        log.append(f"round {rnd}: climbed to a strictly higher conception — "
                   f"{crit.strip().splitlines()[0][:120] if crit.strip() else ''}")
        print(f"  · escalation round {rnd}: climbed higher")
    reached = dry >= a.dry_required
    if reached:
        print(f"  · CEILING reached ({a.dry_required} dry rounds) — no worthwhile climb remains")
    elif rnd >= a.max_rounds:
        print(f"  · stopped at --max-rounds {a.max_rounds} (still improving; raise the cap for more)")
    return vision, log, reached


def call_deepseek(endpoint, model, key, system, user, max_output_tokens, timeout):
    body = {"model": model, "temperature": 0.2, "max_tokens": max_output_tokens,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    req = urllib.request.Request(
        endpoint, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        obj = json.loads(r.read().decode("utf-8"))
    content = obj["choices"][0]["message"].get("content") or ""
    if obj["choices"][0].get("finish_reason") == "length":
        content += "\n\n> [truncated by output limit]"
    return content, obj.get("usage", {})


def _looks_fake(k):
    k = (k or "").strip()
    return (not k) or k.endswith("...") or k == "sk-..." or len(k) < 20


def ask_key(est):
    # A missing OR placeholder env value both count as "not set" → ALWAYS prompt, so a leftover
    # $env:DEEPSEEK_API_KEY="sk-..." from an earlier command can never skip the question.
    key = (os.environ.get("DEEPSEEK_API_KEY") or "").strip()
    if _looks_fake(key):
        try:
            key = input(f"\nΕπικόλλησε το DeepSeek API key σου (ξεκινά με sk-) και πάτα Enter\n"
                        f"— θα κοστίσει ~€{est:.2f} — : ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit("\nΑκυρώθηκε.")
    if _looks_fake(key):
        sys.exit("Δεν δόθηκε πραγματικό κλειδί (κενό ή placeholder). Πάρ' το από "
                 "https://platform.deepseek.com → API keys και κάνε επικόλληση εδώ.")
    return key


def group_by_size(items, budget_chars):
    groups, cur, size = [], [], 0
    for it in items:
        if size + len(it) > budget_chars and cur:
            groups.append(cur); cur, size = [], 0
        cur.append(it); size += len(it)
    if cur:
        groups.append(cur)
    return groups


def main():
    ap = argparse.ArgumentParser(description="DeepSeek FULL-codebase review → highest-tier roadmap")
    ap.add_argument("--repo", default=".", help="path to the repository to review")
    ap.add_argument("--model", default="deepseek-reasoner",
                    help="deep reasoning by default; deepseek-chat is faster/cheaper")
    ap.add_argument("--endpoint", default=os.environ.get("DEEPSEEK_ENDPOINT",
                                                         "https://api.deepseek.com/chat/completions"))
    ap.add_argument("--out", default="LAWMAX-UPGRADE-ROADMAP.md")
    ap.add_argument("--chunk-chars", type=int, default=140_000, help="chars per read chunk (~35k tokens)")
    ap.add_argument("--workers", type=int, default=6, help="parallel read calls")
    ap.add_argument("--max-output-tokens", type=int, default=8000)
    ap.add_argument("--timeout", type=int, default=900)
    # Escalation to the ceiling is CORE: it does not stop until DeepSeek can find no strictly
    # higher conception, confirmed by `dry-required` consecutive rounds (bounded by max-rounds/budget).
    ap.add_argument("--max-rounds", type=int, default=6, help="escalation cap (climb toward the ceiling)")
    ap.add_argument("--dry-required", type=int, default=2,
                    help="consecutive 'no strictly higher' rounds to declare the ceiling")
    ap.add_argument("--budget-eur", type=float, default=None, help="hard cost cap; escalation stops if exceeded")
    ap.add_argument("--no-escalate", action="store_true", help="single review only, no climb")
    ap.add_argument("--dry-run", action="store_true", help="show size + cost estimate, do not call")
    a = ap.parse_args()

    if not os.path.isdir(a.repo):
        sys.exit(f"no such directory: {a.repo}")

    files = gather_corpus(a.repo)
    total_chars = sum(len(c) for _, c in files)
    chunks = make_chunks(files, a.chunk_chars)
    pin, pout = PRICE.get(a.model, PRICE["deepseek-reasoner"])
    est = (approx_tokens(total_chars) / 1e6 * pin
           + (len(chunks) + 2) * a.max_output_tokens / 1e6 * pout)

    print(f"repo:          {os.path.abspath(a.repo)}")
    print(f"files read:    {len(files)}  (FULL content, not a sample)")
    print(f"corpus size:   {total_chars:,} chars  (~{approx_tokens(total_chars):,} tokens)")
    print(f"read passes:   {len(chunks)}  (parallel ×{a.workers}) + synthesis")
    print(f"model:         {a.model}  (deep reasoning)")
    print(f"cost ESTIMATE: ~€{est:.2f}")
    if a.dry_run:
        print("\n[dry-run] nothing sent.")
        return 0
    if not files:
        sys.exit("no source files found under --repo")

    key = ask_key(est)
    in_tok = out_tok = 0

    def do_map(i, ch):
        body = "".join(b for _, b in ch)
        names = ", ".join(sorted({r for r, _ in ch}))
        try:
            content, usage = call_deepseek(a.endpoint, a.model, key, MAP_SYSTEM,
                                           MAP_USER.format(body=body), a.max_output_tokens, a.timeout)
            return i, content, usage, names
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            detail = getattr(e, "read", lambda: b"")()
            return i, f"[FAILED to read this part: {e}. {detail[:200] if detail else ''}]", {}, names

    print(f"\n· reading the whole codebase in {len(chunks)} passes ({a.workers} in parallel)…")
    results = [None] * len(chunks)
    done = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(do_map, i, ch) for i, ch in enumerate(chunks)]
        for fut in as_completed(futs):
            i, content, usage, names = fut.result()
            results[i] = (content, names)
            in_tok += usage.get("prompt_tokens", 0); out_tok += usage.get("completion_tokens", 0)
            done += 1
            print(f"  · [{done}/{len(chunks)}] {names[:80]}")

    analyses = [f"----- part {i + 1} ({names}) -----\n{content}"
                for i, (content, names) in enumerate(results)]

    # Hierarchical consolidation so the final synthesis fits the context window.
    while sum(len(x) for x in analyses) > 300_000 and len(analyses) > 1:
        groups = group_by_size(analyses, 220_000)
        print(f"· consolidating {len(analyses)} analyses → {len(groups)} …")
        merged = []
        for g in groups:
            content, usage = call_deepseek(a.endpoint, a.model, key, CONSOLIDATE_SYSTEM,
                                           CONSOLIDATE_USER.format(body="\n\n".join(g)),
                                           a.max_output_tokens, a.timeout)
            in_tok += usage.get("prompt_tokens", 0); out_tok += usage.get("completion_tokens", 0)
            merged.append(content)
        analyses = merged

    print("· synthesising the initial vision & roadmap from the whole codebase…")
    arch = arch_context(a.repo)[:140_000]
    vision, usage = call_deepseek(a.endpoint, a.model, key, REDUCE_SYSTEM,
                                  REDUCE_USER.format(arch=arch, maps="\n\n".join(analyses)),
                                  a.max_output_tokens, a.timeout)
    in_tok += usage.get("prompt_tokens", 0); out_tok += usage.get("completion_tokens", 0)

    # ESCALATE to the ceiling — do not stop until no strictly higher conception remains.
    spent = [in_tok / 1e6 * pin + out_tok / 1e6 * pout]
    esc_log, reached = [], None
    if not a.no_escalate:
        print("\n· escalating toward the ceiling (stops only when no strictly higher conception remains)…")
        grounding = arch + "\n\n===== CODEBASE ANALYSES =====\n" + "\n\n".join(analyses)
        vision, esc_log, reached = escalate_to_ceiling(vision, grounding, a, key, spent)

    with open(a.out, "w", encoding="utf-8") as f:
        f.write(f"# LAWMAX-Ω — DeepSeek FULL-codebase review & roadmap to the highest tier\n\n"
                f"_Model: {a.model}. Read {len(files)} source files in full across {len(chunks)} passes")
        if not a.no_escalate:
            status = ("CEILING REACHED — no strictly higher conception found" if reached
                      else f"stopped at the {a.max_rounds}-round cap (still improving)")
            f.write(f", then escalated to the ceiling. Outcome: **{status}**._\n\n")
            f.write("## Escalation log\n" + "\n".join(f"- {x}" for x in esc_log) + "\n\n---\n\n")
        else:
            f.write("._\n\n")
        f.write(vision)
    print(f"\n✔ wrote {a.out}")
    print(f"  cost ≈ €{spent[0]:.2f}"
          + ("" if a.no_escalate else f"  |  ceiling: {'REACHED' if reached else 'round-cap'}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
