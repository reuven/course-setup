# TODO — archive-course size guard

## Goal

Course archives get emailed to clients. Occasionally a dataset left in the course
directory rides along and the attachment is too big to send. Those datasets are
nearly always available from other sources, so dropping them costs the client
little — Reuven just needs a chance to say "not that one" before the zip is sealed.

When the finished zip would exceed a size limit (default 10 MB), show the biggest
*actual contributors* largest-first and offer to drop them one at a time, stopping
as soon as the archive is under the limit.

## Decisions already made

- **Measure compressed contribution, not raw size.** A realistic 400k-row CSV is
  18.27 MB raw but 4.51 MB zipped (4.1x) — judging on raw bytes would ask about
  files that were never a problem. An already-compressed PNG or PDF contributes
  nearly its full size.
- **Per-member compressed size is exact, not an estimate.** ZIP deflates each
  member independently with no cross-file/solid compression, so a file's
  compressed size *is* its contribution to the archive.
- **`.git` / `.venv` need no work** — excluded since `f3cc03c` (2026-03-20) and
  verified working against a fixture on 2026-10-22.

## Decisions I made on my own (say if you disagree)

- **Every file is a candidate**, ranked by compressed contribution — not an
  extension allowlist. Simpler, and a notebook will essentially never outrank a
  dataset.
- **Stop prompting once under the limit.** One huge CSV becomes one question.
- **Non-interactive runs never prompt.** If stdin isn't a TTY (CI, scripts, the
  test suite), keep every file and print a warning naming the oversized archive.
- **New flags:** `--max-size MB` (default 10, `0` disables the check) and
  `--keep-all` to skip prompting and include everything.
- **Prompt shows** each candidate's path, compressed size, and the running
  projected zip size, so the effect of each answer is visible.

## Tasks

- [x] 1. Feature branch `feature/archive-size-guard`
- [x] 2. TDD: helper computing each file's exact compressed contribution
- [x] 3. TDD: selection logic — rank by contribution, walk largest-first, stop
      once projected size is under the limit (pure function, no I/O, no prompting)
- [x] 4. TDD: non-interactive path — keep everything, warn, never block
- [x] 5. TDD: interactive prompting, with stdin stubbed
- [x] 6. Wire into `archive_course()`; thread `max_size` / `keep_all` through
- [x] 7. CLI flags `--max-size` and `--keep-all` in `main()`
- [x] 8. Report dropped files in the archive summary
- [x] 9. `ruff format`, `ruff check`, `mypy --strict`, full suite at 100% coverage
- [x] 10. `mutmut run` as a pre-merge audit; close real logic gaps
- [x] 11. Update README.md and MANUAL.md
- [x] 12. Bump version 3.3.1 → 3.4.0, tag `v3.4.0`, merge to main, delete branch, push

## Changed along the way

- **Build-then-trim, not estimate-then-build.** Task 2 was going to compress
  each file separately to price it. That does the same deflate work twice, so
  instead the zip is written normally and each member's size is read back out
  of it with `compress_size`. Nothing is estimated, and the common case (under
  the limit) costs one pass.
- **Added a second stopping rule.** The first end-to-end run declined the big
  dataset and then got asked about a 76 KB file — which could not bring a
  4.6 MB archive under a 3 MB limit even in principle. The walk now also stops
  when the files still on offer cannot close the gap between them.
- **Corrected one claim.** `compress_size` leaves out each member's ~100 bytes
  of ZIP header, so a projected size lands a couple hundred bytes under the
  archive that follows. Never enough to change which file is the problem, but
  not "exact" either, and the docstring now says so.

## Mutation audit (task 10)

214 of 278 mutants killed, 77% -- above the project's ~68% baseline. It found
three real verification gaps, all now closed: the limit boundary itself, the
MiB-vs-MB unit, and the 10 MB default in the signature. Of the survivors in
the new code, four were confirmed unkillable by inspection: two `break` ->
`continue` mutations that produce identical behavior, `dropped = None` (falsy
either way, and invalid under mypy --strict), and `limit > 0` -> `limit > 1`,
which differs only at a one-byte limit. The rest are string literals in output
and help text, plus the pre-existing PDF-export baseline.

## Released

3.4.0, approved as a minor bump since the size guard is a new user-visible
feature with two new flags.
