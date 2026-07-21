# Design: per-course GitHub URLs in `list-courses`

Date: 2026-07-21

Show each listed course's GitHub URL on an indented line beneath it, so the URL
is clickable in the terminal. **On by default**, with `--no-urls` to suppress.
Ships together with year ranges in **3.3.0**.

---

## 1. Behavior

- Under each **listed** course, print an indented line with its GitHub URL:

  ```
  Active courses:
    python-intro — 3 notebooks (2026-03-01 → 2026-03-15)
      https://github.com/reuven/python-intro
  ```

- The URL line is indented **2 spaces deeper** than its course line:
  - active course at 2 spaces → URL at 4;
  - archived course at 4 spaces (under `  <year>:`) → URL at 6.
- Applies only where courses are actually **listed** — the active section and the
  **expanded** archive (`--archived`/`--year`). It does NOT apply to the default
  one-line archive summary (no per-course lines) nor to `--count` (counts only).
- **`--no-urls`** suppresses all URL lines (matches the existing `--no-html` /
  `--no-pdf` opt-out convention; no short alias).

### Source — local, no network

The URL comes from the course repo's `origin` remote, read locally via
`git config --get remote.origin.url` (run with `cwd` = the course dir). No
network call — `list-courses` stays read-only and offline. The SSH or HTTPS
remote is normalized to `https://github.com/<owner>/<repo>`.

### No usable remote → placeholder

If the course has no git repo, no `origin`, or a non-GitHub remote (e.g. an
archived course whose `.git` was stripped), print an indented placeholder instead
so the layout stays uniform:

```
    old-course — 4 notebooks (n/a)
      (no GitHub remote)
```

---

## 2. Implementation (contained to `list_courses.py`)

- `_github_url(remote: str) -> str | None` — pure normalizer. Match
  `github.com[:/]<owner>/<repo>` (optionally `.git`, optional trailing `/`) with a
  regex; return `https://github.com/<owner>/<repo>`, or `None` if the remote is
  empty or not a GitHub URL. Handles the SSH form (`git@github.com:owner/repo.git`),
  the HTTPS form (`https://github.com/owner/repo.git`), and `ssh://` URLs.
- `github_url(course_path: Path) -> str | None` — run
  `subprocess.run(["git", "config", "--get", "remote.origin.url"], cwd=course_path,
  capture_output=True)`; on non-zero exit or empty output return `None`, else
  `_github_url(stdout.decode().strip())`. Needs `import subprocess`.
- `main()`:
  - `show_urls = not args.no_urls`.
  - A small helper, e.g. `_print_course(course: Path, indent: int, show_urls: bool)`,
    prints the `course_summary_line` at `indent` spaces and, when `show_urls`, the
    URL (or `(no GitHub remote)`) at `indent + 2`. Used by both the active loop
    (indent 2) and the archived loop (indent 4).
  - `--count` and the archive summary path do not call it.
- Add `--no-urls` (argparse `store_true`).

### Performance note

One `git` subprocess per listed course. Fine for the active section and filtered
archive views (the common case). A full `list-courses --archived` over a large
archive spawns one git process per course; `--no-urls` avoids that. Optimizing
(e.g. parsing `.git/config` directly) is deferred unless it proves needed (YAGNI).

---

## 3. Tests

- `_github_url` (pure): SSH form, HTTPS form, `ssh://` form, with/without `.git`,
  trailing slash; non-GitHub remote → `None`; empty string → `None`.
- `github_url` (integration, real git in `tmp_path`): `git init` a dir, `git
  remote add origin git@github.com:reuven/demo.git`, assert
  `https://github.com/reuven/demo`; a dir with a repo but no `origin` → `None`.
- `main()` (capsys):
  - default view: an active course is followed by its indented URL line.
  - a course with no remote shows the `(no GitHub remote)` placeholder.
  - `--no-urls` suppresses URL/placeholder lines entirely.
  - `--count` prints no URL lines.
- **Existing `main` tests:** these build courses with a fake (empty) `.git` dir,
  so with URLs on-by-default they now emit `(no GitHub remote)` placeholders.
  Their substring assertions still hold, but to keep each test focused on what it
  targets, add `--no-urls` to the existing `main` list-invocations (the URL
  behavior gets its own dedicated tests above). Count-mode and summary-only tests
  need no change.

---

## 4. Docs & release

- README + MANUAL: document that per-course GitHub URLs show by default, the
  `--no-urls` opt-out, the indented placement, and the `(no GitHub remote)`
  placeholder. Update the options table and example output.
- Bundled into the **3.3.0** release with the year-range feature (single PR, one
  version bump, one PyPI publish).
- Mutation-audit the new logic (the `_github_url` regex/normalization branches);
  ignore output-string mutations.

---

## 5. Out of scope (YAGNI)

- Non-GitHub host support (GitLab/Bitbucket URLs), fetching live repo metadata
  (stars, visibility) over the network, and per-course URL in the archive summary
  line. Revisit only if needed.
