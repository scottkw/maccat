<!-- GSD:project-start source:PROJECT.md -->

## Project

**Mac Software List Generator**

**`maccat`** — a single-file Python (`.pyz`) CLI that catalogs everything installed on a macOS
machine — applications plus the extensions, plugins, MCP servers, and skills/agents of the
user's AI coding CLIs, editors, and browsers — into a timestamped, per-machine markdown
snapshot, auto-archives old catalogs, and auto-commits/pushes to git. Runs against a
user-configured external catalog repo. It's a personal tool for keeping a restorable, diffable
history of a machine's full software + tooling state. (Originally a Zsh script, ported to Python
in v1.0.0; the zsh reference was retired in v2.0.0.)

**Core Value:** A single run produces one complete, restorable snapshot of a machine's software *and*
tooling extensions — accurate enough to rebuild the environment from, degrading gracefully
when any source isn't installed.

### Constraints

- **Tech stack**: Python >= 3.11, **stdlib only — zero runtime dependencies**. Distributed as a
  single-file zipapp (`dist/maccat.pyz`). Dev-only tooling: pytest, ruff, mypy --strict.

- **Compatibility**: macOS-only — collectors read `/Applications`, `~/Library/Application Support/...`,
  and `/usr/bin/pluginkit`; CI runs on `macos-latest`

- **Output format**: Rendered **markdown** catalog (v3.0.0). The emitter (`catalog/format.py`) and
  the reinstall parser (`reinstall/parser.py`) form a lossless round-trip contract — the central
  invariant. Never drift one without the other. Legacy `.txt` catalogs are read-only via `convert`.

- **Detail level**: name + version + ID per extension/plugin where each is obtainable
- **Behavior**: graceful degradation is mandatory — a missing tool or browser must warn-and-continue

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python (`requires-python = ">=3.11"`, `.python-version` pins `3.11`) — the entire tool: 41 modules, ~7,750 lines under `src/maccat/`
- Bash — one build script, `scripts/build-pyz.sh` (zipapp packaging)
- Zsh/sh — *generated*, not source: `src/maccat/reinstall/emitter.py` renders a `reinstall.sh` string containing `brew install` / `mas install` lines
- TOML — config format (`config.example.toml`, `~/.config/maccat/config.toml`), read via stdlib `tomllib`

## Runtime

- CPython >= 3.11 (`pyproject.toml`). CI runs 3.11; local `./venv` currently holds Python 3.14.7
- macOS-only in practice — collectors read `~/Library/Application Support/...`, `/Applications`, and `/usr/bin/pluginkit`; CI `test` and `build` jobs run on `macos-latest`
- `pip` inside a project-local venv at `./venv` (CI: `python -m venv venv && ./venv/bin/pip install -e ".[dev]"`)
- No lockfile — dependency set is small and version-ranged in `pyproject.toml`

## Frameworks

- None. **Zero runtime dependencies — stdlib only.** `pyproject.toml` carries no `dependencies` key and states so explicitly.
- Stdlib modules doing the framework-shaped work: `argparse` (CLI, `src/maccat/cli.py`), `subprocess` (all external tool probes), `json`, `tomllib`, `plistlib` (`src/maccat/helpers/plist_version.py`), `pathlib`, `dataclasses`, `socket` (hostname, `src/maccat/identity.py`), `zipapp` (packaging)
- pytest `>=9.0` (installed: 9.1.0) — 712 collected tests under `tests/`
- Config in `pyproject.toml` `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, custom markers `safety_invariant` and `zsh_parity`
- hatchling `>= 1.26` — build backend; wheel packages `src/maccat`
- ruff `>=0.15` (installed 0.15.17) — lint, `line-length = 100`, `select = ["E", "F", "I", "UP"]`, `src = ["src"]`
- mypy `>=1.10` (installed 2.1.0) — `strict = true`, `python_version = "3.11"`
- `python -m zipapp` — produces the distributable `dist/maccat.pyz`

## Key Dependencies

- `git` — required for the commit/push workflow (`src/maccat/gitops.py`); skipped gracefully when absent or when `--no-commit` is passed
- `brew`, `mas`, `codex`, `code`, `cursor`, `/usr/bin/pluginkit` — each guarded by `shutil.which()` / `Path.is_file()` and degraded to an empty or notice section when missing
- `pytest>=9.0`, `ruff>=0.15`, `mypy>=1.10` — declared under `[project.optional-dependencies] dev`

## Configuration

- Console script `maccat = "maccat.__main__:main"` (`pyproject.toml` `[project.scripts]`)
- `${XDG_CONFIG_HOME:-$HOME/.config}/maccat/config.toml`, path built in `_default_config_path()` at `src/maccat/config.py`
- Flat schema: `catalog_dir = "/abs/path"`. Template at `config.example.toml`
- Written by hand-emitting TOML (stdlib `tomllib` is read-only)
- Managed via `maccat config init` / `maccat config show`
- `MACCAT_CATALOG_DIR` — catalog repo path override
- `XDG_CONFIG_HOME` — relocates the config file
- `PYTHONHASHSEED` — CI matrix values `0`, `42`, `random`, guarding output determinism
- No `.env` file, no secrets of any kind
- Top level: `--version`, `--catalog-dir PATH`, `--computer NAME`, `--rename`, `--archive-days N`, `--no-commit`
- Subcommands: `config init`, `config show`, `reinstall [--from PATH] [--computer NAME]`, `convert --from PATH [--no-commit]`
- `src/maccat/__init__.py` → `__version__ = "3.0.0"`
- `pyproject.toml` → `version = "2.1.0"` — **these disagree**; `.github/workflows/release.yml` reconciles them at tag time by `sed`-stamping both from `${GITHUB_REF_NAME#v}` and asserting `maccat --version` matches

## Packaging & Distribution

- `scripts/build-pyz.sh` runs `python3 -m zipapp src/ --output dist/maccat.pyz --python "/usr/bin/env python3" --main "maccat.__main__:main" --compress`
- Source root is `src/` (not `src/maccat/`) so `maccat/` is a top-level directory inside the archive and `import maccat` resolves
- `dist/` is gitignored (`.gitignore:10`); `dist/maccat.pyz` exists locally as a build output only
- `tests/test_pyz.py` smoke-tests the artifact: runs `--version`/`--help` from an unrelated cwd, asserts no `.so`/`.dylib` in the archive, asserts the catalog repo is never resolved from `__file__`, asserts correct `maccat/` nesting. Skips when `dist/maccat.pyz` is unbuilt
- A hatchling wheel target is also configured (`[tool.hatchling.build.targets.wheel] packages = ["src/maccat"]`) but no publish workflow exists

## CI

- `test` job — `macos-latest`, Python 3.11, matrix over `PYTHONHASHSEED ∈ {0, 42, random}`; `ruff check src tests` → `mypy --strict src/maccat` → `pytest -x -q` (all with `PYTHONPATH=src`)
- `build` job — `macos-latest`, runs `scripts/build-pyz.sh` and uploads `dist/maccat.pyz` with `if-no-files-found: error`

## Platform Requirements

- macOS, Python >= 3.11, venv at `./venv`
- Commands: `./venv/bin/python -m pytest`, `./venv/bin/ruff check src tests`, `PYTHONPATH=src ./venv/bin/mypy --strict src/maccat`
- macOS with `python3` on PATH; ship a single `maccat.pyz` (no install step, no dependencies)
- A git repository at `catalog_dir` for the snapshot history

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- `snake_case.py`, one module per concern: `src/maccat/retention.py`, `src/maccat/naming.py`, `src/maccat/gitops.py`
- One collector per source, named after the source: `src/maccat/collectors/homebrew.py`, `src/maccat/collectors/vscode.py`, `src/maccat/collectors/firefox.py`
- Small pure helpers live in `src/maccat/helpers/`: `json_io.py`, `plist_version.py`, `vsc_name.py`, `chrome_name.py`
- `snake_case`, verb-first: `parse_catalog_filename`, `retain_newest_per_host`, `prune_old_archives`, `emit_item`, `flush_section`
- Leading underscore for module-private helpers and constants: `_build_parser` (`src/maccat/cli.py:24`), `_default_config_path` (`src/maccat/config.py:34`), `_collect_editor_extensions` (`src/maccat/collectors/vscode.py:23`)
- `snake_case` locals; trailing underscore to dodge builtins/keywords — `id_` is used throughout (`src/maccat/catalog/format.py:16`, `src/maccat/collectors/vscode.py:65`)
- Module-level constants are `UPPER_SNAKE`: `TITLE` (`src/maccat/collectors/homebrew.py:10`), `_FILENAME_RE` (`src/maccat/naming.py:17`)
- Class-level section titles are underscore-prefixed class attributes: `ClaudeCollector._PLUGINS_TITLE`, `VSCodeCollector.TITLE`
- `PascalCase` dataclasses: `Section`, `CollectorResult` (`src/maccat/collectors/base.py`), `CatalogFilename` (`src/maccat/naming.py:24`), `ParsedCatalog` / `ParsedItem` / `ParsedSection` (`src/maccat/reinstall/parser.py`)
- Collectors are `<Source>Collector`: `HomebrewCollector`, `MasCollector`, `VSCodeCollector`, `CursorCollector`, `ClaudeCollector`

## Code Style

- No formatter is configured (no black, no `ruff format` config). Style is hand-maintained.
- **Line length: 100** (`[tool.ruff] line-length = 100` in `pyproject.toml`)
- 4-space indent, double quotes throughout.
- `ruff >= 0.15`, configured in `pyproject.toml`:
- Run: `./venv/bin/ruff check src tests` (currently clean)
- Unavoidable unused imports get an inline justification, not a blanket ignore:
- `mypy` in **strict mode**: `[tool.mypy] strict = true`, `python_version = "3.11"`
- Run: `PYTHONPATH=src ./venv/bin/mypy --strict src/maccat` (currently clean, 42 files)
- Strict mode applies to `src/maccat` only — `tests/` is not type-checked by CI, though
- `str | None`, not `Optional[str]` (`src/maccat/catalog/format.py:16`)
- `list[str]`, `dict[str, str]`, `tuple[list[str], list[str]]` — never `typing.List`
- Walrus in comprehension filters is idiomatic here:

## Import Organization

## Error Handling

- Gate on presence: `def available(self) -> bool: return shutil.which("brew") is not None` (`src/maccat/collectors/homebrew.py:32`)
- Non-zero subprocess exit → return `[]`, never raise (`HomebrewCollector._run`, `src/maccat/collectors/homebrew.py:35-42`)
- Narrow, explicit `except` tuples — never bare `except`:
- Parsers return `None` instead of raising: `parse_catalog_filename` (`src/maccat/naming.py:35`)
- Missing source → `Collector.degraded_result(title)` produces an empty section, which
- Defensive `isinstance` guards before dict/list traversal of external JSON
- `raise SystemExit("ERROR: ...")` with an actionable multi-line message
- `sys.exit("ERROR: ...")` in `src/maccat/convert.py:61,65,70,79`
- Destructive ops **hard refuse** rather than guess: `rename_machine` raises `SystemExit`

## Logging

- Collector diagnostics go to **stderr**: `print("  WARNING: brew not found.", file=sys.stderr)` (`src/maccat/collectors/homebrew.py:69`)
- Orchestration/progress and git status go to **stdout**: `print("  WARNING: git not found. Skipping git operations.")` (`src/maccat/gitops.py:27`)
- `  WARNING: ...` — degraded but continuing
- `  NOTE: ...` — source simply absent (`src/maccat/collectors/vscode.py:82`)
- `ERROR: ...` — fatal, paired with `SystemExit` / `sys.exit`

## Comments

- `# Call order is a test contract — do not reorder.` (`src/maccat/collectors/homebrew.py:76`)
- `CRITICAL: Do NOT use Python built-in sort here — it diverges from LC_ALL=C sort -f` (`src/maccat/catalog/format.py:6`)
- `IMPORTANT: Do NOT use this for VS Code NLS key lookup` (`src/maccat/helpers/json_io.py:21`)
- Tap-name mismatch rationale in `src/maccat/collectors/homebrew.py:80-82`

## Function Design

- Pure functions return values; no output params.
- Multi-value returns use plain tuples with a documented shape: `-> tuple[list[str], list[str]]  # (items, warnings)`
- Optionality is `X | None` and the docstring states "never raises" when that is the contract.

## Module Design

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| Version guard + `main()` | Fail-fast on Python < 3.11 before any package import; console-script target | `src/maccat/__main__.py` |
| CLI parser + orchestrator | Argparse tree, subcommand dispatch, non-negotiable run order | `src/maccat/cli.py` |
| Collector ABC + result types | `Collector`, `CollectorResult`, `Section` | `src/maccat/collectors/base.py` |
| Collector registry | Ordered instantiation of the 16 collectors (22 sections) | `src/maccat/collectors/__init__.py` |
| Markdown emitter | Sections → complete `.md` catalog string (frontmatter + tables) | `src/maccat/catalog/markdown.py` |
| Line format + sort primitives | `emit_item`, `flush_section`, `version_sort_tail` | `src/maccat/catalog/format.py` |
| Atomic writer | tmp-file + rename; never leaves a partial catalog | `src/maccat/catalog/writer.py` |
| Markdown catalog parser | `.md` → `ParsedCatalog` (round-trip inverse of the emitter) | `src/maccat/reinstall/parser.py` (`parse_markdown_catalog`) |
| Legacy text catalog parser | Plain-text `.txt` → `ParsedCatalog` (separate state machine) | `src/maccat/reinstall/parser.py` (`parse_catalog`) |
| Reinstall script emitter | `ParsedCatalog` → `reinstall.sh` text, shlex-quoted | `src/maccat/reinstall/emitter.py` |
| Reinstall orchestrator | Resolve → parse → emit → write `./reinstall.sh` (0o644) | `src/maccat/reinstall/cli.py` |
| Catalog picker | `--from PATH` or interactive computer/newest-catalog selection | `src/maccat/reinstall/picker.py` |
| Legacy conversion | `.txt` catalog → `.md` in place, then remove `.txt`, then commit | `src/maccat/convert.py` |
| Config resolution | TOML load, `--catalog-dir`/env/file precedence, repo validation | `src/maccat/config.py` |
| Computer identity | Folder discovery, validation, `machine-labels.tsv`, rename workflow | `src/maccat/identity.py` |
| Filename contract | Parse/generate `mac-software-list-[machine]-<ts>.md` | `src/maccat/naming.py` |
| Retention sweep | Keep newest per host; prune archives older than N days | `src/maccat/retention.py` |
| Git operations | pull, commit+push, rename commit, convert commit — all warn-and-continue | `src/maccat/gitops.py` |
| Shared parsers | plist version, JSON key read, Chrome/VS Code display-name resolution | `src/maccat/helpers/` |

## Pattern Overview

- **Zero runtime dependencies.** `pyproject.toml` declares no `dependencies`; everything is
- **Deferred imports everywhere.** Every `maccat.*` import in `cli.py`, `convert.py`,
- **Pure text functions, I/O at the edges.** `render_markdown_catalog` and
- **Graceful degradation is structural.** Missing tools/directories yield an empty section
- **Atomic-or-nothing writes.** `CatalogWriter` writes to a `.maccat-*.tmp` sibling and

## Layers

- Purpose: Interpreter version guard and console-script binding
- Location: `src/maccat/__main__.py`
- Contains: `main()`, a `sys.version_info < (3, 11)` guard placed before *any* package import
- Depends on: `sys` only
- Used by: the `maccat` console script (`maccat.__main__:main`) and `dist/maccat.pyz`
- Purpose: Parse args, dispatch subcommands, run the fixed catalog workflow
- Location: `src/maccat/cli.py`, `src/maccat/reinstall/cli.py`, `src/maccat/convert.py`
- Contains: `_build_parser()`, `run()`, `run_reinstall()`, `run_convert()`
- Depends on: every other layer (via deferred imports)
- Used by: `__main__.main()`
- Purpose: Query each software source and return `Section` objects
- Location: `src/maccat/collectors/`
- Contains: `base.py` plus 16 concrete collectors and shared helpers in `helpers/`
- Depends on: `subprocess`/filesystem probes, `catalog/format.py::emit_item`
- Used by: `cli.py::run` via `get_registry()`
- Purpose: Turn `Section`s into catalog bytes and back
- Location: `src/maccat/catalog/` (write side), `src/maccat/reinstall/parser.py` (read side)
- Contains: `render_markdown_catalog`, `emit_item`, `flush_section`, `CatalogWriter`,
- Used by: `cli.py`, `convert.py`, `reinstall/cli.py`
- Purpose: Own the on-disk catalog repo — where files go, which survive, what gets committed
- Location: `src/maccat/config.py`, `identity.py`, `naming.py`, `retention.py`, `gitops.py`
- Depends on: `git` binary (optional), filesystem
- Used by: `cli.py::run`

## Data Flow

### Primary Request Path — `maccat` (catalog generation)

### Reinstall Flow — `maccat reinstall`

### Legacy Conversion Flow — `maccat convert --from X.txt`

## Key Abstractions

- Purpose: A source of installed software; one class per tool/browser/editor
- Location: `src/maccat/collectors/base.py`
- Contract: subclasses implement `collect() -> CollectorResult`; `available() -> bool` may be
- Shape: `CollectorResult(sections=[Section], warnings=[str])`; a single collector may return
- **Availability is self-policed.** The orchestrator calls `collect()` unconditionally
- **`CollectorResult.warnings` is collected but discarded** — `run()` extends only
- **`degraded_result()` has zero call sites** in `src/`.
- Location: `src/maccat/collectors/base.py:9`
- `raw=False` (default): the emitter passes `items` through
- `raw=True`: items are written in collector-native order with no sorting. Used by the four
- Empty `items`, or `raw` items that are entirely known degradation strings, render as the
- Location: `src/maccat/reinstall/parser.py:85-106`
- The typed read-side representation shared by both parsers and consumed by the emitter
- `ParsedItem.raw_line` always preserves the original source line, so lossy field extraction
- Location: `src/maccat/naming.py`
- Contract: `mac-software-list-[{machine}]-{YYYYMMDDHHMMSS}.md`; `parse_catalog_filename`
- Location: `src/maccat/identity.py`
- A per-machine directory at the catalog-repo root, discovered from two merged sources:
- `machine-labels.tsv` is a hostname→label map with a single shared reader,

## Entry Points

- Location: `src/maccat/__main__.py` → `main()` → `maccat.cli.run()`
- Declared in `pyproject.toml` as `maccat = "maccat.__main__:main"` — this is the **only**
- `src/maccat/reinstall/cli.py` is **not** an independent entry point: it exposes
- Built by `scripts/build-pyz.sh` via `python3 -m zipapp src/ --main maccat.__main__:main`
- The source dir must be `src/` (not `src/maccat/`) so `maccat/` is a top-level archive

## Architectural Constraints

- **macOS-only.** Collectors hard-code macOS paths (`~/Library/Application Support/...`,
- **Python ≥ 3.11**, enforced twice: `requires-python` in `pyproject.toml` and the runtime
- **Subprocess `sort` is mandatory, not incidental.** `flush_section` shells out to
- **Threading:** single-threaded and fully sequential. Collectors run one at a time in registry
- **Global state:** none mutable. Module-level values are compiled regexes, frozensets, and
- **Circular imports:** none. `catalog/markdown.py` deliberately *duplicates* `ITEM_RE` and
- **Registry order is semantically significant.** `get_registry()` returns a hand-ordered list
- **`reinstall.sh` is never executed.** It is written 0o644 (non-executable, explicitly

## The Round-Trip Contract (central invariant)

| Concern | Emitter | Parser |
|---------|---------|--------|
| Frontmatter | `---` fence, fixed key order `computer / hostname / generated / maccat_version`, **all values double-quoted** so colons and YAML-1.1 datetime auto-cast cannot corrupt them (`_yaml_quote`) | Validates the opening `---`, scans for the closing `---`, skips the block |
| Title | `# Installed Mac Software List` emitted unconditionally as H1 | H1 line ignored |
| Sections | `## <title>` | `line.startswith("## ")` → new `ParsedSection` |
| Rows | `\| Name \| Version \| ID \|` header + `\| --- \|` rule + one row per item | Header and rule rows skipped by exact string match; other `\| … \|` rows parsed |
| Cell escaping | `_escape_cell`: backslash first, then pipe | `_unescape_cell`: strip, then `\|`→`\|`, then `\\`→`\` |
| Empty cells | rendered as a single space `" "` | `.strip()` → `""` → `None` |
| Empty section | `(none found)` with **no** leading spaces (`MD_NONE_FOUND`) | matched exactly; yields `items=[]` |

- The emitter renders *both* empty and degraded sections as `(none found)`, so
- Item lines are split into columns by `_ITEM_RE`, whose lossy cases are documented at
- The legacy `NONE_FOUND_SENTINEL` is `"  (none found)"` with **exactly two** leading spaces

## Two Parsers, Deliberately

| | `parse_catalog` | `parse_markdown_catalog` |
|---|---|---|
| Input | Legacy plain-text `.txt` | Current `.md` (v3 format) |
| Structure cue | Title line followed by a 36-dash `SEPARATOR` | `---` frontmatter + `## ` headings + pipe tables |
| Machinery | Explicit 3-state machine: `SEEKING_TITLE` → `SEEKING_SEPARATOR` → `COLLECTING`, with an EOF flush | Frontmatter validation then a linear body scan |
| Item shape | `ITEM_RE` against a free-form `name (version) [id]` line | 3-column table row split on `" \| "` |
| Errors | Never raises on malformed lines; falls back to name-only | Raises `ValueError` for non-`.md` extension, missing/unclosed frontmatter |
| Empty sentinel | `NONE_FOUND_SENTINEL` (2 leading spaces) | `MD_NONE_FOUND` (no leading spaces) |
| Sole consumer | `src/maccat/convert.py` | `src/maccat/reinstall/cli.py` |

## Anti-Patterns

### Silently dropped collector warnings

### Assuming `available()` is called for you

### Importing across the emitter/parser boundary

### Sorting in Python instead of via `sort(1)`

### Module-level `maccat.*` imports in CLI modules

### Writing `.md` and `.txt` removal in the wrong order

## Error Handling

- User-facing fatal errors use `sys.exit("ERROR: …")` with an actionable multi-line message and
- Parsers never raise on malformed *content*; they fall back to a name-only `ParsedItem` with
- `naming.parse_catalog_filename` returns `None` instead of raising, so retention sweeps can
- All git operations are guarded by `_git_available()` + `_is_git_repo()` and warn-and-continue;
- `subprocess` calls always use `shell=False` with list arguments.
- A non-zero `sort` exit is escalated to `RuntimeError` specifically so the atomic writer aborts

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
