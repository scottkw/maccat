# Coding Conventions

**Analysis Date:** 2026-08-25

This project is a **Python 3.11+ package** (`src/maccat/`, 42 source files) with zero
runtime dependencies (stdlib only). Any ZSH-era guidance elsewhere in the repo
(`CLAUDE.md`, `README.md` history, `update-list.sh`) is **obsolete** for convention
purposes — `update-list.sh` survives only as a *behavioral reference spec* cited in
docstrings, not as the implementation.

## Naming Patterns

**Files:**
- `snake_case.py`, one module per concern: `src/maccat/retention.py`, `src/maccat/naming.py`, `src/maccat/gitops.py`
- One collector per source, named after the source: `src/maccat/collectors/homebrew.py`, `src/maccat/collectors/vscode.py`, `src/maccat/collectors/firefox.py`
- Small pure helpers live in `src/maccat/helpers/`: `json_io.py`, `plist_version.py`, `vsc_name.py`, `chrome_name.py`

**Functions:**
- `snake_case`, verb-first: `parse_catalog_filename`, `retain_newest_per_host`, `prune_old_archives`, `emit_item`, `flush_section`
- Leading underscore for module-private helpers and constants: `_build_parser` (`src/maccat/cli.py:24`), `_default_config_path` (`src/maccat/config.py:34`), `_collect_editor_extensions` (`src/maccat/collectors/vscode.py:23`)

**Variables:**
- `snake_case` locals; trailing underscore to dodge builtins/keywords — `id_` is used throughout (`src/maccat/catalog/format.py:16`, `src/maccat/collectors/vscode.py:65`)
- Module-level constants are `UPPER_SNAKE`: `TITLE` (`src/maccat/collectors/homebrew.py:10`), `_FILENAME_RE` (`src/maccat/naming.py:17`)
- Class-level section titles are underscore-prefixed class attributes: `ClaudeCollector._PLUGINS_TITLE`, `VSCodeCollector.TITLE`

**Types:**
- `PascalCase` dataclasses: `Section`, `CollectorResult` (`src/maccat/collectors/base.py`), `CatalogFilename` (`src/maccat/naming.py:24`), `ParsedCatalog` / `ParsedItem` / `ParsedSection` (`src/maccat/reinstall/parser.py`)
- Collectors are `<Source>Collector`: `HomebrewCollector`, `MasCollector`, `VSCodeCollector`, `CursorCollector`, `ClaudeCollector`

**Section titles are a hard uniqueness contract.** All 22 collector title constants must
be unique — enforced by `tests/collectors/test_section_titles.py` because
`reinstall/emitter.py` routes on title strings.

## Code Style

**Formatting:**
- No formatter is configured (no black, no `ruff format` config). Style is hand-maintained.
- **Line length: 100** (`[tool.ruff] line-length = 100` in `pyproject.toml`)
- 4-space indent, double quotes throughout.

**Linting:**
- `ruff >= 0.15`, configured in `pyproject.toml`:
  - `src = ["src"]`
  - `[tool.ruff.lint] select = ["E", "F", "I", "UP"]` — pycodestyle errors, pyflakes, isort, pyupgrade
- Run: `./venv/bin/ruff check src tests` (currently clean)
- Unavoidable unused imports get an inline justification, not a blanket ignore:
  `import maccat.collectors.claude as claude_mod  # noqa: F401 — used via ClaudeCollector class`
  (`tests/collectors/test_section_titles.py:13`)

**Type checking:**
- `mypy` in **strict mode**: `[tool.mypy] strict = true`, `python_version = "3.11"`
- Run: `PYTHONPATH=src ./venv/bin/mypy --strict src/maccat` (currently clean, 42 files)
- Strict mode applies to `src/maccat` only — `tests/` is not type-checked by CI, though
  test files are still fully annotated by convention (`def test_x(self, tmp_path: Path) -> None:`)

**Modern typing syntax (required by `UP` rules + `from __future__ import annotations`):**
- `str | None`, not `Optional[str]` (`src/maccat/catalog/format.py:16`)
- `list[str]`, `dict[str, str]`, `tuple[list[str], list[str]]` — never `typing.List`
- Walrus in comprehension filters is idiomatic here:
  `[entry for line in formulae if (entry := self._parse_brew_versions_line(line))]`
  (`src/maccat/collectors/homebrew.py:98`)

## Import Organization

**`from __future__ import annotations` is the first import in every non-`__init__` module.**
The only files without it are the five `__init__.py` package markers.

**Order (ruff `I` / isort enforced):**
1. `from __future__ import annotations`
2. Stdlib (`json`, `os`, `re`, `shutil`, `subprocess`, `sys`, `pathlib`, `dataclasses`, `datetime`, `tomllib`)
3. Third party (tests only: `pytest`, `_pytest.capture`)
4. First-party `maccat.*` — always **absolute**, never relative (`from maccat.collectors.base import Collector`)

**Path aliases:** none. There is no `src`-relative import trick; `PYTHONPATH=src` or an
editable install provides the package root.

**Deferred imports are a deliberate pattern (41 occurrences).** `maccat.*` imports inside
function bodies keep interpreter startup safe and cheap — see the module docstring at
`src/maccat/cli.py:11-13` and the lazy loading in `src/maccat/collectors/__init__.py`.
Follow this in `cli.py`, `identity.py`, and collector registries; use top-level imports
everywhere else.

**`__all__` is declared in 15 modules** that export a public surface
(`src/maccat/collectors/base.py:5`, `src/maccat/collectors/vscode.py:19`).

## Error Handling

Two distinct policies — pick by whether the operation is destructive:

**1. Warn-and-continue (graceful degradation) — the default for all collection.**
Every collector must survive a missing tool, missing file, or malformed JSON without
raising. Patterns:
- Gate on presence: `def available(self) -> bool: return shutil.which("brew") is not None` (`src/maccat/collectors/homebrew.py:32`)
- Non-zero subprocess exit → return `[]`, never raise (`HomebrewCollector._run`, `src/maccat/collectors/homebrew.py:35-42`)
- Narrow, explicit `except` tuples — never bare `except`:
  `except (json.JSONDecodeError, OSError, UnicodeDecodeError): return default` (`src/maccat/helpers/json_io.py:29`)
- Parsers return `None` instead of raising: `parse_catalog_filename` (`src/maccat/naming.py:35`)
- Missing source → `Collector.degraded_result(title)` produces an empty section, which
  renders as `  (none found)` (`src/maccat/collectors/base.py:31`)
- Defensive `isinstance` guards before dict/list traversal of external JSON
  (`src/maccat/collectors/vscode.py:57-68`)

**2. Fail loudly — for config and destructive operations.**
- `raise SystemExit("ERROR: ...")` with an actionable multi-line message
  (`src/maccat/config.py:131`, `:196`, `:269`, `:421`)
- `sys.exit("ERROR: ...")` in `src/maccat/convert.py:61,65,70,79`
- Destructive ops **hard refuse** rather than guess: `rename_machine` raises `SystemExit`
  when the destination folder exists (`src/maccat/identity.py`)

**Never silently swallow into a default when data loss is possible.** The Homebrew
`brew leaves` path illustrates the required trade-off explicitly: when the filter list is
unusable, it warns and over-reports rather than emitting an empty list —
"Over-reporting is recoverable; a silently empty formula list is data loss."
(`src/maccat/collectors/homebrew.py:88-95`)

## Logging

**Framework:** none. `logging` is not imported anywhere. All user-facing output is `print()`
(126 call sites).

**Stream discipline:**
- Collector diagnostics go to **stderr**: `print("  WARNING: brew not found.", file=sys.stderr)` (`src/maccat/collectors/homebrew.py:69`)
- Orchestration/progress and git status go to **stdout**: `print("  WARNING: git not found. Skipping git operations.")` (`src/maccat/gitops.py:27`)

**Message prefixes (two-space indent is part of the contract, tests assert on it):**
- `  WARNING: ...` — degraded but continuing
- `  NOTE: ...` — source simply absent (`src/maccat/collectors/vscode.py:82`)
- `ERROR: ...` — fatal, paired with `SystemExit` / `sys.exit`

## Comments

**Module docstrings are mandatory and substantive.** Every module opens with a docstring
naming its responsibility and, where relevant, its zsh-parity reference line numbers
(`src/maccat/naming.py:1-13`, `src/maccat/catalog/format.py:1-9`, `src/maccat/retention.py:1-14`).

**Requirement IDs are cited inline.** Codes like `CAT-06`, `FMT-01`, `VER-01/02/05/06`,
`CFG-01..06`, `PKG-03`, `TEST-03`, `WR-03` appear in docstrings and comments to tie code to
requirements. Preserve and extend this — reviewers and tests grep for them.

**Comment the non-obvious constraint, not the mechanics.** The valuable comments here are
guardrails against future "cleanups":
- `# Call order is a test contract — do not reorder.` (`src/maccat/collectors/homebrew.py:76`)
- `CRITICAL: Do NOT use Python built-in sort here — it diverges from LC_ALL=C sort -f` (`src/maccat/catalog/format.py:6`)
- `IMPORTANT: Do NOT use this for VS Code NLS key lookup` (`src/maccat/helpers/json_io.py:21`)
- Tap-name mismatch rationale in `src/maccat/collectors/homebrew.py:80-82`

**Docstring style:** Google-ish `Args:` / `Returns:` sections on non-trivial functions
(`src/maccat/naming.py:38-46`, `src/maccat/retention.py:26-35`). Examples-as-tables for
format functions (`emit_item`, `json_get`). Dataclass fields carry per-attribute docstrings
(`src/maccat/naming.py:27-32`).

## Function Design

**Size:** small and single-purpose. The one large function, `_collect_editor_extensions`
(~95 lines, `src/maccat/collectors/vscode.py`), is documented as a two-path algorithm
(Path A CLI / Path B JSON fallback) and shared by VS Code + Cursor rather than duplicated.

**Parameters:** positional for 1–3 args; explicit types on every parameter and return
(strict mypy). Defaults are simple immutables (`default: str = ""`).

**Return values:**
- Pure functions return values; no output params.
- Multi-value returns use plain tuples with a documented shape: `-> tuple[list[str], list[str]]  # (items, warnings)`
- Optionality is `X | None` and the docstring states "never raises" when that is the contract.

**Subprocess calls always pass `shell=False`, `capture_output=True`, `text=True`**
(`src/maccat/collectors/homebrew.py:40`, `src/maccat/collectors/vscode.py:40`). Never build
shell strings.

## Module Design

**Exports:** explicit `__all__` in 15 modules; underscore prefix marks everything else private.

**Barrel files:** `src/maccat/collectors/__init__.py`, `catalog/__init__.py`,
`helpers/__init__.py`, `reinstall/__init__.py` exist as package markers with lazy/deferred
import behavior — they are not eager re-export barrels.

**Dataclasses over dicts** for structured data (7 `@dataclass` uses). Use
`@dataclass(frozen=True)` when the value must be hashable/immutable (`CatalogFilename`),
`field(default_factory=list)` for mutable defaults (`CollectorResult.warnings`).

**Adding a new collector:** subclass `Collector` in `src/maccat/collectors/base.py`, define a
unique `TITLE`, override `available()` if the source is optional, implement `collect() ->
CollectorResult`, and add its title constant to the uniqueness list in
`tests/collectors/test_section_titles.py`.

---

*Convention analysis: 2026-08-25*
