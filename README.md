# course-setup

CLI tools for setting up and retiring GitHub-backed course repositories.

## Installation

Install as a [uv tool](https://docs.astral.sh/uv/concepts/tools/) (recommended):

```bash
uv tool install course-setup
```

This makes `setup-course`, `retire-course`, and `setup-course-config`
available on your PATH. To upgrade:

```bash
uv tool upgrade course-setup
```

You can also install with pip (`pip install course-setup`).

## Configuration

Generate a starter config file:

```bash
setup-course-config
```

This creates `~/.config/course-setup/config.toml`. Open it and fill in your
settings:

```toml
[github]
token = "ghp_YOUR_TOKEN_HERE"

[paths]
archive = "/path/to/your/archive"
# readme_source = "/path/to/custom/README.md"   # or a URL

[defaults]
notebook_type = "jupyter"   # or "marimo"
```

| Setting | Required | Description |
|---------|----------|-------------|
| `[github] token` | Yes | GitHub personal access token. Alternatively, set the `GITHUB_TOKEN` environment variable. |
| `[paths] archive` | Yes | Directory where retired courses are archived. |
| `[paths] readme_source` | No | Local path or URL to a custom README for new courses. Omit to use the bundled default. |
| `[defaults] notebook_type` | No | `"jupyter"` (default) or `"marimo"`. |

To regenerate the config file, use `setup-course-config --force`.

## Usage

### `setup-course` — Create a new course repo

```bash
setup-course -c Acme -t python-intro
```

| Flag | Description |
|------|-------------|
| `-c`, `--client` | Client name (required) |
| `-t`, `--topic` | Course topic (required) |
| `-d`, `--date` | YYYY-MM override (defaults to current month) |
| `-n`, `--num-sessions` | Number of sessions (creates one notebook per session) |
| `--freq` | Session frequency: `daily` or `weekly` (requires `-n`, defaults to `daily`) |
| `--notebook-type` | `jupyter` or `marimo` (overrides config default) |

This will:

1. Create a directory and GitHub repo named `{client}-{topic}-{YYYY-MM}`
2. Create a notebook per session, named `{client}-{topic}-{YYYY-MM-DD}`
   (`.ipynb` for Jupyter, `.py` for Marimo)
3. Generate a `pyproject.toml` with the notebook dependency and `gitautopush`
4. Configure the local `.git/config` with the GitHub SSH remote

By default, a single notebook is created for today's date. Use `-n` to
create multiple notebooks for multi-day or multi-week courses:

```bash
setup-course -c Acme -t python-intro -n 5              # 5 daily sessions
setup-course -c Acme -t python-intro -n 5 --freq weekly # 5 weekly sessions
```

### `retire-course` — Archive a course repo

```bash
retire-course ./Acme-python-intro-2026-03
```

| Argument | Description |
|----------|-------------|
| `DIRNAME` | Path to the course directory to retire |

This will:

1. Make the GitHub repo private
2. Move the local directory to your configured archive path under the current year

## Development

```bash
git clone https://github.com/reuven/course-setup.git
cd course-setup
uv sync --dev
```

Run tests, format, and lint:

```bash
uv run pytest
uv run black src/ tests/
uv run ruff check src/ tests/
uv run mypy --strict src/
```

## License

MIT — see [LICENSE](LICENSE) for details.
