# Instructions for Claude Code

## Two kinds of project

Most of my work is one of two kinds, and many rules below differ between them:

- **Shipping code** -- packages, applications, APIs, anything with users or a release.
  Full rigor: TDD, strict typing, 100% coverage, feature branches, version tags.
- **Research and analysis** -- notebooks, figures, tables, write-ups. The deliverable is
  an answer, not an artifact someone installs. You don't know the right answer until
  you've looked at the data, so the rigor moves from tests to data sanity checks.

If it isn't obvious which one you're in, ask before you start.

## When rules conflict

**The more specific section wins.** A rule under "Research and analysis" beats a rule
under "All projects" when that's the kind of project you're in. Anything I tell you in
conversation overrides this file.

These conflicts are deliberate. Resolve them this way:

1. **"Don't write functions" vs. TDD and coverage.** In analysis, keep it inline and
   method-chained. In shipping code -- and in any `src/` module -- write functions freely,
   with tests.
2. **Testing rigor vs. project type.** 100% coverage and mutation testing are for shipping
   code and for `src/` modules. Exploratory notebooks need verified output and data sanity
   checks, not a coverage gate. Meaningful tests, never coverage theater.
3. **`mypy --strict` vs. analysis code.** Strict typing gates shipping code. For
   pandas-heavy analysis, run mypy non-strict (`ignore_missing_imports`) on module code
   only -- strict mypy there is more friction than payoff.
4. **Feature branches vs. research.** Shipping code: every feature on its own branch.
   Solo research: committing to `main` is fine. Use a branch only for substantial
   restructuring, or when I ask.
5. **Version tags.** Packages get tags. Research projects get no tags, no `dist/`, no
   PyPI workflow -- they aren't packages.
6. **Commit granularity vs. pre-commit gates.** One *logical change* per commit, not one
   *file* -- a TDD pair (failing test + the code that passes it) is one commit. Run ruff
   per commit; run `mypy` and the full suite before pushing; mutation testing is a
   periodic audit, not a gate.
7. **Subagents vs. their overhead.** Use subagents for work that's genuinely independent
   and more than a few minutes long. A single-file edit doesn't need a branch, a worktree,
   and a merge.

## Strict rules -- no exceptions

- **Never commit raw data, credentials, or `.env` files.** See "Data handling" below.
- **Never paste row-level data** into commit messages, issues, READMEs, or chat.
  Aggregates and schema descriptions are fine; individual records are not.

## All projects

- Use US English, not UK English, for spelling, grammar, and idioms.
- Don't assume the code works. Run it and check its output -- after every step, not just
  at the end. Re-examine each step as both code and analysis; if it doesn't hold up, go
  back and fix it.
- Explain the approach in prose before writing code. If you see a better approach than
  what I asked for, recommend it first, then proceed if I don't redirect.
- Treat this as collaborative. Help me understand, don't just complete the task --
  comment on *when* and *why*, not only *what*.
- Use Context7 to confirm you're using current, non-deprecated versions and idioms for
  every language and library you touch.
- Break the project down into tasks:
  - Write them into a to-do file (e.g. `TODO.md`).
  - Run the list by me before doing any work, and let me comment.
  - Mark each task off as you complete it.
- Split work across subagents when the pieces are genuinely independent. Each gets its own
  Git worktree on its own branch; when it finishes, it merges its branch into main and
  removes the worktree.
- If a downloaded file is larger than 90 MB, keep it in /tmp rather than the repo, to stay
  under GitHub's 100 MB limit.

### Default stack

- Reach for these first: numpy, pandas, scipy, statsmodels, scikit-learn, plotly,
  great_tables, openpyxl, pyarrow, marimo, python-dotenv.
- Specialists: pingouin (discrete inferential tests, effect sizes outside full modeling),
  researchpy (especially crosstabs), sodapy (Socrata API for open government data).
- Don't reach for polars, duckdb, or other alternatives unless I ask. Pandas is the
  default.

### Git

- If the project isn't a Git repo yet, create one. If there's no GitHub remote, **ask me
  whether to create one and what to name it** -- then create it **private**.
- Commit on a very regular basis: many small commits beat a few big ones. Commit after any
  meaningful unit of work -- a passing test, a new function, a cleaned dataset, a finished
  figure.
- Push automatically after committing.
- Merge finished feature branches straight into main. No PR needed.
- Tag every version bump -- any version. The tag is the version in `pyproject.toml`
  with a `v` prefix: version `1.2.0` gets tag `v1.2.0`. Shipping code only.
- Before building and publishing, delete all old versions in `dist/`. The Git tags mean
  nothing is lost.
- Set up `.gitignore` before the first commit. Always include editor and OS cruft:
  `#*#`, `.#*`, `*~`, `*.swp`, `.DS_Store`.
- Ask before any destructive Git operation: force-push, hard reset, history rewrite, or
  branch deletion.

### Data handling

Some of this data concerns sensitive populations. Treat these as defaults at project init:

- `.gitignore` should cover `data/`, `*.csv`, `*.tsv`, `*.parquet`, `*.xlsx`, `*.dta`,
  `*.sav`, `.env`, and any credential files.
- Credentials and API keys live in `.env`, loaded with `python-dotenv`. Never hardcode.
- Document provenance in `data/README.md`: where the data came from, when it was pulled,
  and any access restrictions, IRB, or DUA constraints.
- For Socrata pulls via `sodapy`, log the dataset ID, pull date, and query parameters so
  the pull is reproducible.
- Use real data from the internet and actual data sets. Never hard-code data you already
  know or collected by hand.

## Python

- It's a `uv` project. Use `uv add`, not `pip install`, and `uv run` rather than invoking
  Python or installed binaries directly. Don't create or activate venvs by hand.
- Use `ruff format` and `ruff check` regularly, not just at the end -- always before a
  commit.
- Type hints on every reusable function, with docstrings that explain *why* the function
  exists and when to use it, not just restating the signature. Exploratory notebook cells
  don't need type hints.

## Shipping code

- Type hints everywhere, enforced with `mypy --strict`. If it doesn't pass, it doesn't get
  committed.
- Test-driven development, always: write the `pytest` test first, watch it fail, then write
  the code that makes it pass. Every feature, every bug fix.
- For anything web-facing -- web app, API, or static site -- use `pytest-playwright` for
  integration testing. Not optional.
- Keep coverage at 100%, enforced in `pyproject.toml` with `--cov-fail-under=100` rather
  than relying on you to remember.
- Audit test quality with mutation testing (`uv run mutmut run`). Run it before merging a
  feature branch and before publishing a release -- it's too slow to gate every commit,
  so treat it as a periodic audit. When mutants survive, write tests that close the real
  logic gaps; ignore string-literal mutations in output and help text.

## Research and analysis

- Reusable transformations, cleaning steps, and helpers go in a `src/` module, not buried
  in notebook cells. Notebooks import from `src/`.
- Sanity-check the data after every nontrivial transformation: shape, dtypes, null counts,
  key summary stats. For exploratory work this replaces unit tests.
- Write `pytest` tests for everything in `src/` -- cleaning functions, transformations,
  recoding logic, anything reused or where a bug would silently corrupt results downstream.
  The coverage target applies to `src/`, not to notebooks.
- For statistical code, prefer known-answer tests (a hand-computed example) over tests that
  only check the function runs.
- `README.md` at the project root: what the project is, how to set it up (`uv sync`), where
  the data comes from, how to run the analysis, and what the key outputs are.
- Number notebooks in run order in `notebooks/` -- `01_clean.py`, `02_descriptives.py`,
  `03_models.py` -- so the pipeline is obvious.
- Save figures and tables to `outputs/` with descriptive filenames, never `figure1.png`.
- If output feeds a D3/React visualization layer, export clean JSON or CSV with a stable,
  documented schema, and write that schema in `outputs/README.md` as a contract for the
  frontend.

## Data and Pandas

- Use Pandas 3.0 syntax, especially `pd.col`, wherever possible.
- Avoid `for` loops, `apply`, and `lambda`. If you're iterating over a data frame you're
  almost certainly doing it wrong -- find another way unless there's genuinely no option.
- Don't write functions unless you have no choice. Keep it inline, unless inline would be
  unreadable.
- Assign a data frame to a variable once, when you create it. After that, don't create new
  variables from it -- use method chaining with `.loc`, `.pipe`, and `.assign`:
  ```python
  (
      df
      .assign(year = pd.col("date").dt.year)
      .query("year >= 2020")
      .groupby("group", as_index=False)
      .agg(mean_x = ("x", "mean"))
  )
  ```
- Prefer Parquet over CSV -- binary, unambiguous, smaller, and far faster to load.
- Don't use a PyArrow backend, but do use PyArrow to load CSV files.
- Convert columns to the smallest appropriate dtype. Check the column's min and max, and
  confirm the conversion makes sense, before doing it.
- Use categories to shrink text columns.
- Show memory usage before and after anything that changes the frame's footprint. Always
  pass `deep=True` to `df.info()` and `df.memory_usage()` -- otherwise the number is a lie.
- Before any join or merge, show your work: how many rows from each frame matched.
- Plot with Plotly. Avoid Matplotlib, Seaborn, and `df.plot()` -- unless Plotly can't do
  what's needed, in which case the Pandas API is an acceptable fallback.

## Statistics and methodology

- Survey data is often longitudinal or panel data. Don't default to methods assuming
  independent observations -- flag clustering, repeated measures, or panel structure when
  choosing a method.
- When a method has real tradeoffs (fixed vs. random effects, listwise deletion vs.
  multiple imputation, parametric vs. nonparametric), discuss them briefly before choosing.
- Always report effect sizes and uncertainty intervals alongside p-values.

## Machine learning

- Use scikit-learn.
- Evaluate each model with several techniques. Say which you used, and whether they
  disagreed.
- Only once you've established which models work well, and how each feature contributes,
  build the Marimo notebook that presents the results.

## Marimo notebooks

- I work exclusively in **marimo**. Create `.py` marimo notebooks, never Jupyter `.ipynb`
  -- Jupyter is only an export target, and only when I ask for it.
- A variable may only be defined once in the whole notebook. Never define the same name in
  two cells; don't even try.
- No `print()` in notebooks. Let cell outputs render naturally.
- When demonstrating a technique, use numbered examples with clear use cases.
