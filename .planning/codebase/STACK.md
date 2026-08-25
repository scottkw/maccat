# Technology Stack

**Analysis Date:** 2026-08-25

> Derived from files on disk (`pyproject.toml`, `src/maccat/**`, `tests/**`, `scripts/`, `.github/workflows/`, `venv/`).
> `CLAUDE.md` / `README.md` prose describing a "single Zsh script `update-list.sh`" is obsolete — that file no longer exists.
> The tool is a Python package. Zsh survives only as *emitted output* (`maccat reinstall` renders a shell script) and as historical parity references in docstrings.

## Languages

**Primary:**
- Python (`requires-python = ">=3.11"`, `.python-version` pins `3.11`) — the entire tool: 41 modules, ~7,750 lines under `src/maccat/`

**Secondary:**
- Bash — one build script, `scripts/build-pyz.sh` (zipapp packaging)
- Zsh/sh — *generated*, not source: `src/maccat/reinstall/emitter.py` renders a `reinstall.sh` string containing `brew install` / `mas install` lines
- TOML — config format (`config.example.toml`, `~/.config/maccat/config.toml`), read via stdlib `tomllib`

## Runtime

**Environment:**
- CPython >= 3.11 (`pyproject.toml`). CI runs 3.11; local `./venv` currently holds Python 3.14.7
- macOS-only in practice — collectors read `~/Library/Application Support/...`, `/Applications`, and `/usr/bin/pluginkit`; CI `test` and `build` jobs run on `macos-latest`

**Package Manager:**
- `pip` inside a project-local venv at `./venv` (CI: `python -m venv venv && ./venv/bin/pip install -e ".[dev]"`)
- No lockfile — dependency set is small and version-ranged in `pyproject.toml`

## Frameworks

**Core:**
- None. **Zero runtime dependencies — stdlib only.** `pyproject.toml` carries no `dependencies` key and states so explicitly.
- Stdlib modules doing the framework-shaped work: `argparse` (CLI, `src/maccat/cli.py`), `subprocess` (all external tool probes), `json`, `tomllib`, `plistlib` (`src/maccat/helpers/plist_version.py`), `pathlib`, `dataclasses`, `socket` (hostname, `src/maccat/identity.py`), `zipapp` (packaging)

**Testing:**
- pytest `>=9.0` (installed: 9.1.0) — 712 collected tests under `tests/`
- Config in `pyproject.toml` `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, custom markers `safety_invariant` and `zsh_parity`

**Build/Dev:**
- hatchling `>= 1.26` — build backend; wheel packages `src/maccat`
- ruff `>=0.15` (installed 0.15.17) — lint, `line-length = 100`, `select = ["E", "F", "I", "UP"]`, `src = ["src"]`
- mypy `>=1.10` (installed 2.1.0) — `strict = true`, `python_version = "3.11"`
- `python -m zipapp` — produces the distributable `dist/maccat.pyz`

## Key Dependencies

**Runtime (Python packages):** none.

**External command-line tools (optional, probed at runtime — see INTEGRATIONS.md):**
- `git` — required for the commit/push workflow (`src/maccat/gitops.py`); skipped gracefully when absent or when `--no-commit` is passed
- `brew`, `mas`, `codex`, `code`, `cursor`, `/usr/bin/pluginkit` — each guarded by `shutil.which()` / `Path.is_file()` and degraded to an empty or notice section when missing

**Dev:**
- `pytest>=9.0`, `ruff>=0.15`, `mypy>=1.10` — declared under `[project.optional-dependencies] dev`

## Configuration

**Entry point:**
- Console script `maccat = "maccat.__main__:main"` (`pyproject.toml` `[project.scripts]`)

**Config file:**
- `${XDG_CONFIG_HOME:-$HOME/.config}/maccat/config.toml`, path built in `_default_config_path()` at `src/maccat/config.py`
- Flat schema: `catalog_dir = "/abs/path"`. Template at `config.example.toml`
- Written by hand-emitting TOML (stdlib `tomllib` is read-only)
- Managed via `maccat config init` / `maccat config show`

**Precedence chain** (`src/maccat/config.py`, CFG-01..CFG-06):
1. `--catalog-dir PATH` flag
2. `MACCAT_CATALOG_DIR` env var
3. `~/.config/maccat/config.toml`
4. hard error — `catalog_dir` has no default

**Environment variables:**
- `MACCAT_CATALOG_DIR` — catalog repo path override
- `XDG_CONFIG_HOME` — relocates the config file
- `PYTHONHASHSEED` — CI matrix values `0`, `42`, `random`, guarding output determinism
- No `.env` file, no secrets of any kind

**CLI surface** (`src/maccat/cli.py`):
- Top level: `--version`, `--catalog-dir PATH`, `--computer NAME`, `--rename`, `--archive-days N`, `--no-commit`
- Subcommands: `config init`, `config show`, `reinstall [--from PATH] [--computer NAME]`, `convert --from PATH [--no-commit]`

**Version stamping:**
- `src/maccat/__init__.py` → `__version__ = "3.0.0"`
- `pyproject.toml` → `version = "2.1.0"` — **these disagree**; `.github/workflows/release.yml` reconciles them at tag time by `sed`-stamping both from `${GITHUB_REF_NAME#v}` and asserting `maccat --version` matches

## Packaging & Distribution

**Mechanism:** stdlib `zipapp`, not PyPI.
- `scripts/build-pyz.sh` runs `python3 -m zipapp src/ --output dist/maccat.pyz --python "/usr/bin/env python3" --main "maccat.__main__:main" --compress`
- Source root is `src/` (not `src/maccat/`) so `maccat/` is a top-level directory inside the archive and `import maccat` resolves
- `dist/` is gitignored (`.gitignore:10`); `dist/maccat.pyz` exists locally as a build output only
- `tests/test_pyz.py` smoke-tests the artifact: runs `--version`/`--help` from an unrelated cwd, asserts no `.so`/`.dylib` in the archive, asserts the catalog repo is never resolved from `__file__`, asserts correct `maccat/` nesting. Skips when `dist/maccat.pyz` is unbuilt
- A hatchling wheel target is also configured (`[tool.hatchling.build.targets.wheel] packages = ["src/maccat"]`) but no publish workflow exists

**Release:** `.github/workflows/release.yml` on tag `v*.*.*` — stamps version, builds the `.pyz`, verifies the built artifact's `--version`, publishes/updates a GitHub Release with `dist/maccat.pyz` attached via `gh`.

## CI

`.github/workflows/ci.yml`, on push to `main` and on PRs:
- `test` job — `macos-latest`, Python 3.11, matrix over `PYTHONHASHSEED ∈ {0, 42, random}`; `ruff check src tests` → `mypy --strict src/maccat` → `pytest -x -q` (all with `PYTHONPATH=src`)
- `build` job — `macos-latest`, runs `scripts/build-pyz.sh` and uploads `dist/maccat.pyz` with `if-no-files-found: error`

## Platform Requirements

**Development:**
- macOS, Python >= 3.11, venv at `./venv`
- Commands: `./venv/bin/python -m pytest`, `./venv/bin/ruff check src tests`, `PYTHONPATH=src ./venv/bin/mypy --strict src/maccat`

**Production:**
- macOS with `python3` on PATH; ship a single `maccat.pyz` (no install step, no dependencies)
- A git repository at `catalog_dir` for the snapshot history

---

*Stack analysis: 2026-08-25*
