# Codebase Structure

**Analysis Date:** 2026-08-25

> The repository is a Python package (`src/` layout), not a shell script. `update-list.sh` no
> longer exists anywhere in the tree; references to it in docstrings are historical provenance
> notes only.

## Directory Layout

```
maccat/
├── pyproject.toml            # hatchling build, deps, ruff/mypy/pytest config, console script
├── config.example.toml       # template for ~/.config/maccat/config.toml
├── README.md                 # user-facing docs (stale on architecture — do not trust)
├── CLAUDE.md                 # project instructions (stale on architecture — do not trust)
├── LICENSE                   # MIT
├── .python-version           # 3.11
├── src/
│   └── maccat/               # the package — all production code
│       ├── __init__.py       # __version__ only
│       ├── __main__.py       # version guard + main() (console-script target)
│       ├── cli.py            # argparse tree + run() orchestration
│       ├── config.py         # TOML config, catalog-repo resolution + validation
│       ├── identity.py       # computer folders, machine-labels.tsv, rename workflow
│       ├── naming.py         # catalog filename parse/generate
│       ├── retention.py      # retain-newest-per-host, prune-old-archives
│       ├── gitops.py         # pull / commit+push / rename commit / convert commit
│       ├── convert.py        # legacy .txt → .md conversion subcommand
│       ├── catalog/          # WRITE side of the catalog format
│       │   ├── format.py     # emit_item, flush_section, version_sort_tail
│       │   ├── markdown.py   # render_markdown_catalog (v3 .md emitter)
│       │   └── writer.py     # CatalogWriter (atomic tmp+rename)
│       ├── collectors/       # plugin layer — one module per software source
│       │   ├── base.py       # Collector / CollectorResult / Section
│       │   ├── __init__.py   # get_registry() — ordered, deferred imports
│       │   └── <16 modules>  # homebrew, mas, setapp, webapps, claude, codex,
│       │                     # opencode, gemini, vscode, cursor, zed, chrome,
│       │                     # chromium, edge, brave, firefox, safari
│       ├── helpers/          # small shared parsers used by collectors
│       │   ├── chrome_name.py, json_io.py, plist_version.py, vsc_name.py
│       └── reinstall/        # READ side + reinstall.sh generation
│           ├── parser.py     # BOTH parsers: parse_catalog (.txt), parse_markdown_catalog (.md)
│           ├── emitter.py    # emit_reinstall_script
│           ├── picker.py     # resolve_catalog_path (--from or interactive)
│           └── cli.py        # run_reinstall (called by top-level cli.py)
├── tests/                    # pytest suite, mirrors src/ layout (~11k lines)
│   ├── conftest.py
│   ├── collectors/           # one test module per collector + test_section_titles.py
│   ├── helpers/
│   ├── reinstall/
│   └── test_*.py             # cli, config, convert, format, gitops, helpers, identity,
│                             # markdown_emitter, naming, pyz, retention,
│                             # safety_invariants, writer
├── scripts/
│   └── build-pyz.sh          # zipapp build → dist/maccat.pyz
├── .github/workflows/
│   ├── ci.yml                # macos-latest: ruff, mypy --strict, pytest × 3 PYTHONHASHSEEDs
│   └── release.yml
├── docs/superpowers/specs/   # design specs (computer-folder model)
├── dist/maccat.pyz           # built artifact (gitignored build output)
├── .planning/                # GSD planning artifacts (this document lives here)
└── venv/                     # local virtualenv — never commit, never import from
```

## Directory Purposes

**`src/maccat/` (package root):**
- Purpose: Flat top-level modules for repo/machine concerns that are not part of the
  collect→emit→parse pipeline
- Contains: `cli.py`, `config.py`, `identity.py`, `naming.py`, `retention.py`, `gitops.py`,
  `convert.py`, `__main__.py`, `__init__.py`
- Key files: `src/maccat/cli.py` (the orchestrator — read this first),
  `src/maccat/identity.py` (596 lines, the largest module)

**`src/maccat/collectors/`:**
- Purpose: One module per software source, each exporting a `Collector` subclass
- Contains: `base.py` (the ABC and dataclasses), `__init__.py` (the ordered registry), and 16
  concrete collector modules
- Key files: `src/maccat/collectors/base.py`, `src/maccat/collectors/__init__.py`
- Note: `chromium.py` is a shared implementation module for the Chromium-family browsers
  (`chrome.py`, `edge.py`, `brave.py` are thin wrappers), and `cursor.py` delegates to
  `vscode.py::_collect_editor_extensions`. Registry count is 16 collectors → 22 sections.

**`src/maccat/catalog/`:**
- Purpose: Everything that turns `Section` objects into catalog bytes
- Contains: line formatting + system-`sort` primitives, the markdown emitter, the atomic writer
- Key files: `src/maccat/catalog/markdown.py`, `src/maccat/catalog/format.py`

**`src/maccat/reinstall/`:**
- Purpose: The read side — parse a catalog back into typed data and emit a `reinstall.sh`
- Contains: both catalog parsers, the shell-script emitter, the picker, the subcommand runner
- Key files: `src/maccat/reinstall/parser.py` (372 lines; holds the round-trip contract)

**`src/maccat/helpers/`:**
- Purpose: Small, dependency-free parsing utilities shared across collectors
- Contains: `plist_version.py` (macOS `Info.plist` version read), `json_io.py` (safe JSON key
  read), `chrome_name.py` (Chrome extension display-name resolution, including `_locales`),
  `vsc_name.py` (VS Code / Cursor extension name from `package.json`)

**`tests/`:**
- Purpose: pytest suite; directory layout mirrors `src/maccat/`
- Key files: `tests/reinstall/test_parser_contract.py` (round-trip + adversarial cases),
  `tests/test_safety_invariants.py` (destructive-op guards), `tests/test_pyz.py` (zipapp build)

## Key File Locations

**Entry Points:**
- `src/maccat/__main__.py`: `main()` — the sole console script (`maccat = "maccat.__main__:main"`)
- `src/maccat/cli.py`: `run()` and `_build_parser()` — all argparse lives here
- `dist/maccat.pyz`: standalone zipapp built from `src/`

**Configuration:**
- `pyproject.toml`: build backend, `requires-python = ">=3.11"`, zero runtime deps, dev extras,
  `[tool.ruff]` (line-length 100, `E,F,I,UP`), `[tool.mypy]` strict, pytest markers
  (`safety_invariant`, `zsh_parity`)
- `config.example.toml`: template for the user's `~/.config/maccat/config.toml`
- `src/maccat/config.py`: reads that file; XDG-aware path in `_default_config_path()`
- `.python-version`: `3.11`

**Core Logic:**
- `src/maccat/cli.py`: workflow order (steps 1–13, documented as non-negotiable)
- `src/maccat/collectors/base.py`: the plugin contract
- `src/maccat/collectors/__init__.py`: registry order (semantically significant)
- `src/maccat/catalog/markdown.py`: `.md` write side
- `src/maccat/reinstall/parser.py`: `.md` and legacy `.txt` read sides
- `src/maccat/reinstall/emitter.py`: `reinstall.sh` generation + injection-safety gate

**Testing:**
- `tests/conftest.py`: shared fixtures
- `tests/collectors/test_section_titles.py`: locks section titles across all collectors
- `.github/workflows/ci.yml`: `ruff check src tests`, `mypy --strict src/maccat`, `pytest -x -q`
  under `PYTHONHASHSEED` ∈ {0, 42, random}

## Naming Conventions

**Files:**
- `snake_case.py`, one collector per source, named after the tool: `homebrew.py`, `vscode.py`,
  `safari.py`
- Tests mirror the module under test: `src/maccat/collectors/zed.py` →
  `tests/collectors/test_zed.py`; top-level modules → `tests/test_<module>.py`

**Directories:**
- Lowercase, single word, plural for plugin/helper collections (`collectors/`, `helpers/`),
  singular for a cohesive subsystem (`catalog/`, `reinstall/`)

**Symbols:**
- Collector classes are `<Source>Collector` in PascalCase, matching the module name:
  `HomebrewCollector`, `VSCodeCollector`, `OpenCodeCollector`
- Module-private helpers use a leading underscore (`_render_table`, `_parse_markdown_row`,
  `_collect_editor_extensions`)
- Module-level constants are `UPPER_SNAKE`; private ones take a leading underscore
  (`SEPARATOR`, `ITEM_RE`, `_ITEM_RE`, `_INDEX`, `_TITLE`). Some collectors expose `TITLE` as a
  module constant and some as a class attribute — both patterns exist
  (`homebrew.py:10` vs `cursor.py:23`).
- Constants that tests need to monkeypatch are placed at module level rather than on the class,
  deliberately (`src/maccat/collectors/zed.py:13-19`)

**Output artifacts:**
- Catalogs: `mac-software-list-[{computer}]-{YYYYMMDDHHMMSS}.md` — brackets are literal
  (`src/maccat/naming.py:18`)
- Generated script: `./reinstall.sh`, mode `0o644`, written to the current working directory
- Temp files during write: `.maccat-*.tmp`, created as a sibling of the target so the rename is
  atomic (`src/maccat/catalog/writer.py:39-41`)

## Where to Add New Code

**A new software source (the most common change):**
1. Implementation: `src/maccat/collectors/<source>.py` — subclass `Collector`, implement
   `collect()`, guard availability *inside* `collect()` (the orchestrator never calls
   `available()` for you)
2. Register: add a deferred import and an instance to the return list in
   `src/maccat/collectors/__init__.py::get_registry()`, **in the correct position** — do not
   alphabetize; update the section-order docstring
3. Format items with `emit_item()` from `src/maccat/catalog/format.py` unless the upstream tool's
   own ordering is the contract, in which case return `Section(..., raw=True)`
4. Tests: `tests/collectors/test_<source>.py`, plus add the title to
   `tests/collectors/test_section_titles.py`
5. If the section is reinstallable by a shell command, add a renderer to `SECTION_SOURCE_MAP` in
   `src/maccat/reinstall/emitter.py:230`; otherwise it falls through to the manual checklist
   automatically

**A new CLI flag or subcommand:**
- Parser: `src/maccat/cli.py::_build_parser()`
- Dispatch: `src/maccat/cli.py::run()`, respecting the documented step order
- For subparser flags that shadow a top-level flag, use `default=argparse.SUPPRESS` so the
  subparser does not clobber a value set before the subcommand token
  (`src/maccat/cli.py:118-144`)
- A subcommand with real work gets its own module (`convert.py`) or subpackage runner
  (`reinstall/cli.py`), invoked from `run()` via a deferred import

**A shared parsing utility:**
- `src/maccat/helpers/<name>.py`, one public function, no `maccat.*` imports beyond
  `catalog/format.py`
- Tests: `tests/helpers/test_<name>.py`

**Changes to the catalog format:**
- Both sides must move together: `src/maccat/catalog/markdown.py` **and**
  `src/maccat/reinstall/parser.py::parse_markdown_catalog`
- Do not import one from the other; keep the duplicated `ITEM_RE` / degradation frozenset in
  sync manually and extend `tests/reinstall/test_parser_contract.py`
- Bump `__version__` in `src/maccat/__init__.py` (it is written into every catalog's
  frontmatter as `maccat_version`)

**Repo/machine management logic:**
- Filename shape → `src/maccat/naming.py`
- Folder discovery, labels, rename → `src/maccat/identity.py`
- Sweep/prune policy → `src/maccat/retention.py`
- Anything invoking `git` → `src/maccat/gitops.py` (never call git from other modules)

## Special Directories

**`dist/`:**
- Purpose: Holds the built `maccat.pyz` zipapp
- Generated: Yes, by `scripts/build-pyz.sh` (and by the CI `build` job)
- Committed: No — build output

**`venv/`:**
- Purpose: Local development virtualenv; CI recreates it with
  `python -m venv venv && ./venv/bin/pip install -e ".[dev]"`
- Generated: Yes
- Committed: No

**`.planning/`:**
- Purpose: GSD planning artifacts, including `.planning/codebase/` (these maps)
- Generated: Yes, by GSD commands
- Committed: Yes

**`docs/superpowers/specs/`:**
- Purpose: Design specs; currently one document on the computer-folder model
- Generated: No
- Committed: Yes

**`.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`:**
- Purpose: Tool caches
- Generated: Yes; Committed: No

## Version Discrepancy (note for whoever touches packaging next)

`src/maccat/__init__.py` declares `__version__ = "3.0.0"` while `pyproject.toml` declares
`version = "2.1.0"`. `--version` output and catalog frontmatter come from `__init__.py`; the
built wheel/sdist name comes from `pyproject.toml`. These two are out of sync.

---

*Structure analysis: 2026-08-25*
