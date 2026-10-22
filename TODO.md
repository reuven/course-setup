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

- [ ] 1. Feature branch `feature/archive-size-guard`
- [ ] 2. TDD: helper computing each file's exact compressed contribution
- [ ] 3. TDD: selection logic — rank by contribution, walk largest-first, stop
      once projected size is under the limit (pure function, no I/O, no prompting)
- [ ] 4. TDD: non-interactive path — keep everything, warn, never block
- [ ] 5. TDD: interactive prompting, with stdin stubbed
- [ ] 6. Wire into `archive_course()`; thread `max_size` / `keep_all` through
- [ ] 7. CLI flags `--max-size` and `--keep-all` in `main()`
- [ ] 8. Report dropped files in the archive summary
- [ ] 9. `ruff format`, `ruff check`, `mypy --strict`, full suite at 100% coverage
- [ ] 10. `mutmut run` as a pre-merge audit; close real logic gaps
- [ ] 11. Update README.md and MANUAL.md
- [ ] 12. Bump version 3.3.1 → 3.4.0, tag `v3.4.0`, merge to main, delete branch, push

## Open question

Task 12 assumes a minor bump (new user-visible feature). Say if you'd rather
this ride along to a later release instead.
