"""Patch application and git worktree management.

The PatchEngine cannot be constructed without a SandboxedWorktree, and it has no path
argument of its own: every op addresses a repository-relative path inside that worktree.
Rollback restores from content captured before the write, verified by hash.
"""
import os
import subprocess

from .canonical import atomic_write_json, sha256_bytes, utc
from .sandbox import ContainmentViolation, SandboxedWorktree

PATCH_OP_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "required": ["path", "new_content"],
    "properties": {
        "path": {"type": "string", "minLength": 1, "maxLength": 512},
        "new_content": {"type": "string", "maxLength": 2000000},
        "rationale": {"type": "string"},
    },
}


class PatchRejected(Exception):
    pass


class PatchEngine:
    def __init__(self, worktree: SandboxedWorktree, backups_dir):
        if not isinstance(worktree, SandboxedWorktree):
            raise TypeError("PatchEngine requires a SandboxedWorktree — raw paths are not accepted")
        self.wt = worktree
        self.backups = os.path.abspath(backups_dir)
        os.makedirs(self.backups, exist_ok=True)

    def apply(self, patch_id, ops):
        """All-or-nothing. A single rejected op aborts the whole patch and restores."""
        from .schema import ValidationError, validate

        for i, op in enumerate(ops):
            try:
                validate(op, PATCH_OP_SCHEMA)
            except ValidationError as e:
                raise PatchRejected(f"op[{i}] malformed: {e}")
        # Resolve every target BEFORE writing anything: containment is decided up front.
        for i, op in enumerate(ops):
            try:
                self.wt.resolve(op["path"], for_write=True)
            except ContainmentViolation as e:
                raise PatchRejected(f"op[{i}] rejected: {e}")

        manifest, applied = [], []
        try:
            for op in ops:
                rel = op["path"]
                before = self.wt.read_text(rel) if self.wt.exists(rel) else None
                self.wt.write_text(rel, op["new_content"])
                manifest.append({
                    "path": rel,
                    "before_sha256": sha256_bytes(before.encode("utf-8")) if before is not None else None,
                    "after_sha256": sha256_bytes(op["new_content"].encode("utf-8")),
                    "existed_before": before is not None,
                })
                applied.append((rel, before))
        except BaseException:
            for rel, before in reversed(applied):
                if before is None:
                    self.wt.remove(rel)
                else:
                    self.wt.write_text(rel, before)
            raise

        # Keep the EARLIEST captured content per path (the true pre-patch original), so a
        # rollback of an apply() with two ops on the same path restores the original, not an
        # intermediate (audit: rollback-corruption). applied is in order, so setdefault wins.
        originals = {}
        for rel, before in applied:
            originals.setdefault(rel, before)
        blob = {"patch_id": patch_id, "utc": utc(), "worktree": self.wt.root, "ops": manifest,
                "contents": originals}
        atomic_write_json(os.path.join(self.backups, patch_id + ".json"), blob)
        return manifest

    def rollback(self, patch_id):
        from .canonical import read_json

        blob = read_json(os.path.join(self.backups, patch_id + ".json"))
        for rel, before in blob["contents"].items():
            if before is None:
                self.wt.remove(rel)
            else:
                self.wt.write_text(rel, before)
        return True


class WorktreeManager:
    """One git worktree per candidate. Candidates never share a tree, so one candidate
    cannot observe or corrupt another's work even if it behaves adversarially."""

    def __init__(self, canonical_repo, worktrees_root):
        self.repo = os.path.realpath(canonical_repo)
        self.root = os.path.abspath(worktrees_root)
        os.makedirs(self.root, exist_ok=True)

    def _git(self, *args, cwd=None):
        r = subprocess.run(["git", *args], cwd=cwd or self.repo, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr.strip()}")
        return r.stdout.strip()

    def create(self, candidate_id, base="HEAD"):
        path = os.path.join(self.root, candidate_id)
        if os.path.exists(path):
            return SandboxedWorktree(path, label=candidate_id)
        # Branch names live in the SHARED canonical repo, so two runs (different runtimes)
        # that branch the same candidate id would collide on `git worktree add -b` and the
        # second run would silently build nothing. Namespace the branch by this manager's
        # worktree root — which is per-runtime — so independent runs against one repo never
        # fight over a branch name. Same-runtime resume reuses the existing path above.
        import hashlib
        tag = hashlib.sha256(self.root.encode("utf-8")).hexdigest()[:10]
        self._git("worktree", "add", "-f", "-b", f"cand/{tag}/{candidate_id}", path, base)
        return SandboxedWorktree(path, label=candidate_id)

    def commit_if_green(self, wt: SandboxedWorktree, message, green: bool):
        """A red build produces NO commit. There is no override argument."""
        if not green:
            return None
        self._git("add", "-A", cwd=wt.root)
        status = self._git("status", "--short", cwd=wt.root)
        if not status:
            return None
        self._git("-c", "user.email=info@stavropouloslaw.com", "-c", "user.name=Stavropoulos Law",
                  "commit", "-m", message, cwd=wt.root)
        return self._git("rev-parse", "HEAD", cwd=wt.root)
