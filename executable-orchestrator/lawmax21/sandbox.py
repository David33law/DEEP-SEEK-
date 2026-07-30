"""Containment by construction.

v2.0's patch engine took a `path` and wrote it. Absolute paths, `..` and symlinks all
escaped, and a candidate rewrote the evaluator that graded it.

v2.1 removes the ability to *express* an escape. A `SandboxedWorktree` owns exactly one
root. Its write API accepts only a repository-relative path; there is no overload that
takes an absolute path, and no caller can obtain a writable handle to anything else.
Every component is checked for symlink/reparse-point redirection before use, and the
fully resolved target must still be inside the resolved root.
"""
import os
import stat

FILE_ATTRIBUTE_REPARSE_POINT = 0x400


class ContainmentViolation(Exception):
    """Raised instead of writing. Never downgraded to a warning."""


def _is_reparse_point(path):
    try:
        st = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(st.st_mode):
        return True
    attrs = getattr(st, "st_file_attributes", 0)  # Windows junctions / mount points
    return bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT)


def _within(child, parent):
    child, parent = os.path.normcase(child), os.path.normcase(parent)
    try:
        return os.path.commonpath([child, parent]) == parent
    except ValueError:  # different drives on Windows
        return False


class SandboxedWorktree:
    """The only writable surface a builder/candidate is ever handed."""

    def __init__(self, root, label="worktree"):
        self.label = label
        self.root = os.path.realpath(root)
        if not os.path.isdir(self.root):
            raise ContainmentViolation(f"{label}: root {root!r} is not a directory")
        for probe in (self.root,):
            if _is_reparse_point(probe) and os.path.realpath(probe) != probe:
                raise ContainmentViolation(f"{label}: root is a redirection point")

    # ------------------------------------------------------------------ paths
    def resolve(self, relpath, for_write=True):
        if not isinstance(relpath, str) or not relpath:
            raise ContainmentViolation(f"{self.label}: path must be a non-empty string")
        if os.path.isabs(relpath) or relpath.startswith(("/", "\\")):
            raise ContainmentViolation(f"{self.label}: absolute paths are not addressable ({relpath!r})")
        if len(relpath) > 1 and relpath[1] == ":":
            raise ContainmentViolation(f"{self.label}: drive-qualified paths are not addressable ({relpath!r})")
        parts = [p for p in relpath.replace("\\", "/").split("/")]
        if any(p in ("", ".", "..") for p in parts):
            raise ContainmentViolation(f"{self.label}: path traversal component in {relpath!r}")
        if any(p.strip() != p or p.endswith(".") for p in parts):
            raise ContainmentViolation(f"{self.label}: unsafe path component in {relpath!r}")

        cur = self.root
        for i, p in enumerate(parts):
            cur = os.path.join(cur, p)
            if _is_reparse_point(cur):
                raise ContainmentViolation(
                    f"{self.label}: {'/'.join(parts[:i+1])!r} is a symlink/junction — refusing to follow"
                )
            if i < len(parts) - 1 and os.path.exists(cur) and not os.path.isdir(cur):
                raise ContainmentViolation(f"{self.label}: {'/'.join(parts[:i+1])!r} is not a directory")

        if not _within(os.path.realpath(cur), self.root):
            raise ContainmentViolation(f"{self.label}: {relpath!r} resolves outside the worktree")
        if for_write and parts[0] == ".git":
            raise ContainmentViolation(f"{self.label}: the git directory is not writable by builders")
        return cur

    # ------------------------------------------------------------------- I/O
    def write_text(self, relpath, content):
        if not isinstance(content, str):
            raise ContainmentViolation(f"{self.label}: content must be text")
        target = self.resolve(relpath, for_write=True)
        parent = os.path.dirname(target)
        if not os.path.isdir(parent):
            self._makedirs_checked(parent)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        return target

    def _makedirs_checked(self, parent):
        rel = os.path.relpath(parent, self.root)
        cur = self.root
        for p in rel.replace("\\", "/").split("/"):
            cur = os.path.join(cur, p)
            if _is_reparse_point(cur):
                raise ContainmentViolation(f"{self.label}: refusing to create through a redirection point")
            if not os.path.isdir(cur):
                os.mkdir(cur)

    def read_text(self, relpath):
        with open(self.resolve(relpath, for_write=False), "r", encoding="utf-8") as f:
            return f.read()

    def exists(self, relpath):
        try:
            return os.path.exists(self.resolve(relpath, for_write=False))
        except ContainmentViolation:
            return False

    def remove(self, relpath):
        t = self.resolve(relpath, for_write=True)
        if os.path.exists(t):
            os.remove(t)

    def list_files(self):
        out = []
        for r, ds, fs in os.walk(self.root):
            ds[:] = [d for d in ds if d != ".git" and not _is_reparse_point(os.path.join(r, d))]
            for f in fs:
                out.append(os.path.relpath(os.path.join(r, f), self.root).replace("\\", "/"))
        return sorted(out)
