# 21 — POWERSHELL LAUNCH & RECOVERY SPEC (v2.0)
The ONLY executable form is executable-orchestrator/launch.ps1. This protocol file contains
NO code snippets by design (v1.1's abridged example contained a non-existent cmdlet and
porcelain-regex parsing; both are permanently retired — see 27 changelog v2.0).

Modes (mandatory): -Preflight | -DryRun | -Launch | -Resume | -Audit
- Preflight/DryRun: NO API key requested, ever. Validate package (validate_package), evidence
  vault presence, hidden-bank commitments, repo attestation, runtime root writability.
- Launch: all local preflights must pass first; package/evidence/hidden/repo certified; ONLY
  THEN the key is requested (SecureString -> BSTR -> env var), zeroed and removed in finally.
- Resume: exact checkpoint continuation; paid successful calls replayed from raw store only.
- Audit: read-only; runs independent audit tooling.
Rules: runner path from $PSScriptRoot (never an assumed $Root); canonical path containment via
full-path + directory-boundary check (no naive StartsWith); tracked/staged/untracked checked
via separate git commands; file-backed stdout/stderr; no Git remotes; py.exe/-3 rule; atomic
writes; pre-patch backups; evidence frozen on failure; containers network-off; runtime/ is the
ONLY writable root — the immutable package is never written by the runner (validated by audit).
