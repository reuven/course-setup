# Some rules for this project

- Break the project down into tasks
    - Write those tasks in a to-do list in a file
    - Run those tasks by me before starting, and let me comment
    - Every time you complete a task, mark it off in the file
- You're in a uv project!
    - Use `uv add` instead of pip
    - Use `uv run` instead of invoking Python and programs directly
    - Don't use venvs explicitly. Instead, just rely on uv
- Use TDD (test-driven development)
    - Before implementing a feature, write a test.
    - The test will fail.
    - Implement the feature
    - The test will pass
- Use pytest for testing. And always make sure you have 100% test coverage.
- You're in a Git repo. Use it:
    - Commit to Git on a very regular basis. Better to have many small commits than fewer big commits
    - If you have implemented a feature, or fixed a bug, commit! Even if it's only a small thing on one file.
    - If you have more than one file mentioned in a commit, it's probably too much.
    - Every new feature should be implemented on a separate branch that is merged into main when it's done
- Don't assume that code works. Make sure to run it, and check its output
- Use black to format the code and ruff to check it. Do this on a very regular basis, not just at the end. Certainly do it before each Git commit.

- Use type hints everywhere. Run `mypy` with `strict` option all of the time, certainly before committing.

- Wherever possible, split work across multiple, parallel agents
    - Have each agent use a different Git worktree when working on the repo in parallel
    - When an agent has finished its job, get rid of the unneeded worktree

**STRICT RULE - NO EXCEPTIONS**: Never chain commands with `&&`.
Always issue separate, sequential commands. This applies to ALL
cases, including `cd && git`, `cd && make`, etc.
