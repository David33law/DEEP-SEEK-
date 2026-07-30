# LAWMAX v2.3 — self-improving legal-institution overseer

An **overseer** (`επιτηρητής`) that runs a governed tournament in which an external model
(DeepSeek) proposes successor architectures, and only crowns one that is **measured** to be a
genuine legal institution and **signed off** by the owner. Nothing is trusted that is not either
proven by execution or authorised by the owner's key.

- Sandboxed, isolated candidate evaluation (no key, no network, no filesystem for the candidate).
- A sealed hidden test bank the candidate never sees.
- Seeded, generalisation-hardened institution sensors (layers L1,L2,L7,L8,L10 + consciousness
  dimensions) — a memoriser collapses under the run's secret seed.
- Evidence-bound, re-derived integration credit: the crown requires MEASURED institution layers
  **and** the owner's Ed25519 signature over that exact measurement.
- Hardened against a self-proof suite and four rounds of independent adversarial review
  (see `docs/AUDIT-2.1-FINDINGS-AND-FIXES.md`).

## Requirements

- **Python ≥ 3.9**
- `pip install cryptography PyYAML` (pinned versions in `requirements.lock`)
- For a real run with an **untrusted** candidate: **Docker/Podman** (container isolation is the
  structural guarantee; the in-process subprocess sandbox is hardened best-effort).

## 1. Prove it works — right now, zero cost, no DeepSeek, no keys

```bash
python executable-orchestrator/tools/run_proof.py --out ./proofrun
```

Builds a disposable copy, stands up a local server that speaks the real DeepSeek API shape on
`127.0.0.1`, and drives the **real** launch path end-to-end: owner gates, a crash and a resume, the
full rejection battery, and the seven liveness properties of the crown gate. Expected verdict:

```
overall: PASS · 15/15 rejections · launch + crash/resume · 0 PAID API CALLS
```

## 2. Run it for real — ONE command, only the API key needed

```powershell
$env:DEEPSEEK_API_KEY = "sk-..."      # PowerShell   (bash:  export DEEPSEEK_API_KEY=sk-...)
python run_launch.py
```

`run_launch.py` does everything: on first use it sets the machine up (generates your owner key
**locally** — it is git-ignored, never uploaded), then it drives the launch to completion,
**auto-approving every owner gate** for you, and stops only when a ceiling is **proven**
(`COMMITTED`) or the round budget runs out (`BEST_DISCOVERED_SO_FAR`). It never crowns for budget
or time.

**Rehearse for free** (no money, no DeepSeek), using the bundled mock:
```bash
python executable-orchestrator/tools/mock_deepseek_server.py     # terminal 1
python run_launch.py --endpoint http://127.0.0.1:8731/chat/completions   # terminal 2
```

<details><summary>Prefer to drive it by hand?</summary>

```bash
python setup_owner.py                                              # one-time local setup
python executable-orchestrator/orchestrator.py --preflight         # should print  "ok": true
python executable-orchestrator/orchestrator.py --launch  --run-id RUN-0001
python executable-orchestrator/orchestrator.py --resume --run-id RUN-0001   # after any interruption
```
Each owner gate then pauses for your signature (`tools/owner_sign.py`).
</details>

> **For a genuine run** the `evidence-vault/` here ships **fixtures**. Replace them with your real
> materials and re-run `setup_owner.py` to re-attest. Real legal case material should never sit on
> the experiment machine unanonymised (decision D05).

## Layout

| Path | Role |
|---|---|
| `executable-orchestrator/` | the overseer: `orchestrator.py` + the `lawmax21/` library |
| `private-evaluator/evaluator/` | sealed evaluator: sandbox host, graders, institution sensors |
| `immutable-package/` | charter, invariants, protocols, prompts, owner public key |
| `benchmark/`, `evidence-vault/` | visible suite + attested source material (fixtures here) |
| `executable-orchestrator/tools/` | `run_proof.py`, `owner_sign.py`, setup/verify helpers |
| `docs/` | the adversarial-audit findings & fixes |

## Never commit

`private-evaluator/owner-held-secrets/` (your keys) and the sealed bank key. The `.gitignore`
already excludes them. Anyone holding your owner key can approve merges and crown a successor.
