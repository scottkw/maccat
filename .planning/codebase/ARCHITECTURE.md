<!-- refreshed: 2026-08-25 -->
# Architecture

**Analysis Date:** 2026-08-25

> `update-list.sh` no longer exists. maccat is a pure-stdlib Python package rooted at
> `src/maccat/`. Many docstrings still cite `update-list.sh:NNNN` line numbers — those are
> historical provenance notes for the zsh implementation this package replaced, not live code
> references. Treat them as comments, not as facts about the current tree.

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          Entry / CLI layer                          │
├──────────────────────────┬──────────────────────────────────────────┤
│  `src/maccat/__main__.py`│         `src/maccat/cli.py`              │
│  (version guard, main()) │  (argparse + run() orchestration)        │
└──────────┬───────────────┴────────────────┬─────────────────────────┘
           │                                │
   default run() path              subcommand dispatch
           │                    ┌───────────┼───────────────┐
           ▼                    ▼           ▼               ▼
┌────────────────────┐  ┌───────────────┐ ┌──────────┐ ┌──────────────┐
│ Collector registry │  │ config init/  │ │ convert  │ │  reinstall   │
│`collectors/__init_ │  │ show          │ │`convert. │ │`reinstall/   │
│ _.py::get_registry`│  │`config.py`    │ │  py`     │ │  cli.py`     │
└──────────┬─────────┘  └───────────────┘ └────┬─────┘ └──────┬───────┘
           │ list[Section]                     │              │
           ▼                                   │              ▼
┌───────────────────────────────┐              │      ┌───────────────────┐
│ Markdown emitter              │              │      │ picker.py         │
│ `catalog/markdown.py`         │◄─────────────┘      │ (choose catalog)  │
│   render_markdown_catalog()   │  legacy .txt →      └─────────┬─────────┘
│   ↳ `catalog/format.py`       │  parse_catalog →              ▼
│      flush_section (sort -f -u)│  Section(raw=True)   ┌──────────────────┐
└──────────────┬────────────────┘                      │ parser.py        │
               │ markdown str                          │ parse_markdown_  │
               ▼                                       │  catalog()       │
┌───────────────────────────────┐                      └────────┬─────────┘
│ `catalog/writer.py`           │                               ▼
│  CatalogWriter (mkstemp+rename)│                     ┌──────────────────┐
└──────────────┬────────────────┘                     │ emitter.py       │
               │                                      │ → reinstall.sh   │
               ▼                                      └──────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│  Catalog git repo (external, path from config)                      │
│  <repo>/<computer>/mac-software-list-[<computer>]-<ts>.md            │
│  <repo>/<computer>/archive/…      <repo>/machine-labels.tsv          │
│  swept by `retention.py`, committed by `gitops.py`                  │
└─────────────────────────────────────────────────────────────────────┘
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

**Overall:** Plugin-collector pipeline behind a thin CLI orchestrator, with a
serialize/deserialize round-trip contract at its center.

**Key Characteristics:**
- **Zero runtime dependencies.** `pyproject.toml` declares no `dependencies`; everything is
  stdlib (`argparse`, `tomllib`, `subprocess`, `shlex`, `plistlib`, `re`, `dataclasses`).
- **Deferred imports everywhere.** Every `maccat.*` import in `cli.py`, `convert.py`,
  `reinstall/cli.py`, and `collectors/__init__.py::get_registry` lives *inside* a function
  body. This keeps module import free of side effects and lets any single collector be
  unit-tested without its 15 siblings existing.
- **Pure text functions, I/O at the edges.** `render_markdown_catalog` and
  `emit_reinstall_script` return strings and touch no filesystem; only `CatalogWriter`,
  `convert.py`, and `reinstall/cli.py` write files.
- **Graceful degradation is structural.** Missing tools/directories yield an empty section
  rendered as `(none found)` rather than an error.
- **Atomic-or-nothing writes.** `CatalogWriter` writes to a `.maccat-*.tmp` sibling and
  renames on clean exit; on exception the tmp file is unlinked and the final path never
  appears.

## Layers

**Entry layer:**
- Purpose: Interpreter version guard and console-script binding
- Location: `src/maccat/__main__.py`
- Contains: `main()`, a `sys.version_info < (3, 11)` guard placed before *any* package import
- Depends on: `sys` only
- Used by: the `maccat` console script (`maccat.__main__:main`) and `dist/maccat.pyz`

**CLI / orchestration layer:**
- Purpose: Parse args, dispatch subcommands, run the fixed catalog workflow
- Location: `src/maccat/cli.py`, `src/maccat/reinstall/cli.py`, `src/maccat/convert.py`
- Contains: `_build_parser()`, `run()`, `run_reinstall()`, `run_convert()`
- Depends on: every other layer (via deferred imports)
- Used by: `__main__.main()`

**Collection layer:**
- Purpose: Query each software source and return `Section` objects
- Location: `src/maccat/collectors/`
- Contains: `base.py` plus 16 concrete collectors and shared helpers in `helpers/`
- Depends on: `subprocess`/filesystem probes, `catalog/format.py::emit_item`
- Used by: `cli.py::run` via `get_registry()`

**Serialization layer:**
- Purpose: Turn `Section`s into catalog bytes and back
- Location: `src/maccat/catalog/` (write side), `src/maccat/reinstall/parser.py` (read side)
- Contains: `render_markdown_catalog`, `emit_item`, `flush_section`, `CatalogWriter`,
  `parse_markdown_catalog`, `parse_catalog`
- Used by: `cli.py`, `convert.py`, `reinstall/cli.py`

**Repository-management layer:**
- Purpose: Own the on-disk catalog repo — where files go, which survive, what gets committed
- Location: `src/maccat/config.py`, `identity.py`, `naming.py`, `retention.py`, `gitops.py`
- Depends on: `git` binary (optional), filesystem
- Used by: `cli.py::run`

## Data Flow

### Primary Request Path — `maccat` (catalog generation)

Order in `run()` is explicitly documented as non-negotiable (`src/maccat/cli.py:176-193`):

1. `_build_parser().parse_args()` (`src/maccat/cli.py:224`)
2. `config` subcommand dispatch — deliberately *before* `load_config()`, so `config init` can
   repair a malformed TOML file (`src/maccat/cli.py:230-253`)
3. `--rename` × `--computer` mutual-exclusion guard (`src/maccat/cli.py:259`)
4. `load_config()` → `reinstall --from` / `convert` early exits (repo-agnostic) →
   `resolve_catalog_repo()` + `validate_catalog_repo()` → picker-mode `reinstall`
   (`src/maccat/cli.py:268-310`)
5. `--rename` short-circuit: `git_pull` → `rename_machine` → return (`src/maccat/cli.py:316-319`)
6. `resolve_computer_selection()` → `select_computer()`; `None` means the user quit and nothing
   is written (`src/maccat/cli.py:324-328`)
7. `resolve_archive_days()` (`src/maccat/cli.py:333`)
8. `gitops.git_pull(catalog_repo)` (`src/maccat/cli.py:338`)
9. **Timestamp captured after the pull** — the generate-then-sweep invariant, guaranteeing the
   new file is newer than any retention cutoff (`src/maccat/cli.py:345-347`)
10. `get_registry()` → `collector.collect()` for each → concatenated `list[Section]` →
    `render_markdown_catalog(...)` → `CatalogWriter.write_raw(content)`
    (`src/maccat/cli.py:352-370`)
11. `retain_newest_per_host(repo/computer)` (`src/maccat/cli.py:375`)
12. `prune_old_archives(repo/computer/archive, archive_days)` (`src/maccat/cli.py:380`)
13. `gitops.git_commit_and_push(...)`, or a printed manual-commit hint under `--no-commit`
    (`src/maccat/cli.py:385-395`)

### Reinstall Flow — `maccat reinstall`

1. `resolve_catalog_path(args, catalog_repo)` — `--from PATH`, else the interactive computer
   picker plus `_find_newest_catalog()` (`src/maccat/reinstall/picker.py:28,63`)
2. `parse_markdown_catalog(path)` — raises `ValueError` for non-`.md` or frontmatter-less files,
   with a message that always names `maccat convert --from` (`src/maccat/reinstall/parser.py:288`)
3. `emit_reinstall_script(catalog, source_name=..., generated=...)`
   (`src/maccat/reinstall/emitter.py:243`)
4. Write `Path.cwd() / "reinstall.sh"`, `chmod 0o644`, print the absolute path. The script is
   **never** executed (`src/maccat/reinstall/cli.py:78-81`)

### Legacy Conversion Flow — `maccat convert --from X.txt`

1. Existence/readability checks; `_TXT_FILENAME_RE` extracts the computer label
   (`src/maccat/convert.py:33,68`)
2. No-clobber guard: refuse if the sibling `.md` exists (`src/maccat/convert.py:77-82`)
3. `parse_catalog(txt_path)` — the **legacy plain-text** parser (`src/maccat/convert.py:90`)
4. Bridge each `ParsedSection` to `Section(..., raw=True)`, dropping the
   `"Installed Mac Software List"` header section (`src/maccat/convert.py:99-103`)
5. Frontmatter synthesized from *now*, `socket.gethostname()`, `__version__` — the filename
   keeps the original timestamp, so filename ts and `generated` intentionally differ
   (`src/maccat/convert.py:105-122`)
6. Write `.md`, **then** unlink `.txt` (never the reverse), then `git_commit_convert`
   (`src/maccat/convert.py:125-149`)

**State Management:**
No module-level mutable state. Config is a frozen-in-practice `Config` dataclass threaded
through function arguments; the only globals are compiled regexes and frozensets of
degradation strings.

## Key Abstractions

**`Collector` (plugin contract):**
- Purpose: A source of installed software; one class per tool/browser/editor
- Location: `src/maccat/collectors/base.py`
- Contract: subclasses implement `collect() -> CollectorResult`; `available() -> bool` may be
  overridden to gate on a binary or directory; `degraded_result(title)` returns a standard
  empty section
- Shape: `CollectorResult(sections=[Section], warnings=[str])`; a single collector may return
  several sections (e.g. `ClaudeCollector` returns Plugins / MCP Servers / Skills & Agents)
- **Availability is self-policed.** The orchestrator calls `collect()` unconditionally
  (`src/maccat/cli.py:353-355`) and never consults `available()`. Only
  `homebrew.py:62`, `mas.py:58`, and `setapp.py:37` call `self.available()` internally;
  the rest test directory existence inline. Adding an `available()` override to a collector
  therefore has **no effect** unless that collector also calls it.
- **`CollectorResult.warnings` is collected but discarded** — `run()` extends only
  `result.sections`.
- **`degraded_result()` has zero call sites** in `src/`.

**`Section` (raw vs non-raw):**
- Location: `src/maccat/collectors/base.py:9`
- `raw=False` (default): the emitter passes `items` through
  `flush_section()` → `LC_ALL=C sort -f -u`, so items are sorted and deduplicated
- `raw=True`: items are written in collector-native order with no sorting. Used by the four
  externally-ordered sources — Homebrew, App Store, Setapp, Web-installed — where the upstream
  tool's ordering is itself the deterministic contract
- Empty `items`, or `raw` items that are entirely known degradation strings, render as the
  literal `(none found)` line instead of an empty table
  (`src/maccat/catalog/markdown.py:193-206`)

**`ParsedCatalog` / `ParsedSection` / `ParsedItem`:**
- Location: `src/maccat/reinstall/parser.py:85-106`
- The typed read-side representation shared by both parsers and consumed by the emitter
- `ParsedItem.raw_line` always preserves the original source line, so lossy field extraction
  never destroys information

**Catalog filename:**
- Location: `src/maccat/naming.py`
- Contract: `mac-software-list-[{machine}]-{YYYYMMDDHHMMSS}.md`; `parse_catalog_filename`
  returns `None` rather than raising, matching the warn-and-continue policy in
  `retention.py`

**Computer folder:**
- Location: `src/maccat/identity.py`
- A per-machine directory at the catalog-repo root, discovered from two merged sources:
  top-level dirs containing `mac-software-list-*.md`, and the machine column of
  `machine-labels.tsv` (`src/maccat/identity.py:139`)
- `machine-labels.tsv` is a hostname→label map with a single shared reader,
  `_iter_tsv_entries` (`src/maccat/identity.py:107`), and atomic rewrites via
  `_atomic_write_lines` (`src/maccat/identity.py:178`)

## Entry Points

**`maccat` console script:**
- Location: `src/maccat/__main__.py` → `main()` → `maccat.cli.run()`
- Declared in `pyproject.toml` as `maccat = "maccat.__main__:main"` — this is the **only**
  console script. `src/maccat/cli.py` has no `if __name__ == "__main__"` block and is never
  invoked directly.
- `src/maccat/reinstall/cli.py` is **not** an independent entry point: it exposes
  `run_reinstall(args, catalog_repo=None)`, which `cli.py` calls after argparse has already
  handled the `reinstall` subparser. There is one argparse tree, not two.

**`dist/maccat.pyz`:**
- Built by `scripts/build-pyz.sh` via `python3 -m zipapp src/ --main maccat.__main__:main`
- The source dir must be `src/` (not `src/maccat/`) so `maccat/` is a top-level archive
  directory and `import maccat` resolves

## Architectural Constraints

- **macOS-only.** Collectors hard-code macOS paths (`~/Library/Application Support/...`,
  `/Applications`), and Safari/Setapp/`mas` have no other-platform analog. CI runs on
  `macos-latest` only.
- **Python ≥ 3.11**, enforced twice: `requires-python` in `pyproject.toml` and the runtime
  guard in `__main__.py` (which also exists because `/usr/bin/python3` on macOS is 3.9).
- **Subprocess `sort` is mandatory, not incidental.** `flush_section` shells out to
  `LC_ALL=C sort -f -u` and `version_sort_tail` to `sort -V`
  (`src/maccat/catalog/format.py`). Python's built-in sort diverges for mixed-case/non-ASCII
  names and gets numeric versions wrong (9 > 14 lexicographically). A non-zero `sort` exit
  raises `RuntimeError` so `CatalogWriter` discards the tmp file rather than committing a
  truncated section.
- **Threading:** single-threaded and fully sequential. Collectors run one at a time in registry
  order; no concurrency primitives anywhere.
- **Global state:** none mutable. Module-level values are compiled regexes, frozensets, and
  `Path.home()`-derived constants (e.g. `zed.py:_INDEX`), deliberately module-level so tests
  can monkeypatch them.
- **Circular imports:** none. `catalog/markdown.py` deliberately *duplicates* `ITEM_RE` and
  `_DEGRADATION_LINES` from `reinstall/parser.py` rather than importing them, to keep the
  catalog package independent of the reinstall package. `parser.py` symmetrically refuses to
  import `emit_item`. The duplicated regex **is** the contract between the two sides.
- **Registry order is semantically significant.** `get_registry()` returns a hand-ordered list
  and must not be alphabetized (`src/maccat/collectors/__init__.py:64-65`).
- **`reinstall.sh` is never executed.** It is written 0o644 (non-executable, explicitly
  `os.chmod`'d rather than left to umask) and its path is printed for human review.

## The Round-Trip Contract (central invariant)

Write side: `render_markdown_catalog` (`src/maccat/catalog/markdown.py:153`).
Read side: `parse_markdown_catalog` (`src/maccat/reinstall/parser.py:288`).

| Concern | Emitter | Parser |
|---------|---------|--------|
| Frontmatter | `---` fence, fixed key order `computer / hostname / generated / maccat_version`, **all values double-quoted** so colons and YAML-1.1 datetime auto-cast cannot corrupt them (`_yaml_quote`) | Validates the opening `---`, scans for the closing `---`, skips the block |
| Title | `# Installed Mac Software List` emitted unconditionally as H1 | H1 line ignored |
| Sections | `## <title>` | `line.startswith("## ")` → new `ParsedSection` |
| Rows | `\| Name \| Version \| ID \|` header + `\| --- \|` rule + one row per item | Header and rule rows skipped by exact string match; other `\| … \|` rows parsed |
| Cell escaping | `_escape_cell`: backslash first, then pipe | `_unescape_cell`: strip, then `\|`→`\|`, then `\\`→`\` |
| Empty cells | rendered as a single space `" "` | `.strip()` → `""` → `None` |
| Empty section | `(none found)` with **no** leading spaces (`MD_NONE_FOUND`) | matched exactly; yields `items=[]` |

**Known asymmetries — do not assume perfect fidelity:**
- The emitter renders *both* empty and degraded sections as `(none found)`, so
  `ParsedSection.degraded` is **not recoverable** from a markdown round-trip (the legacy text
  parser does preserve it). This is safe for the reinstall emitter because `_should_skip()`
  drops a section on `items == []` regardless of the flag.
- Item lines are split into columns by `_ITEM_RE`, whose lossy cases are documented at
  `src/maccat/reinstall/parser.py:8-28`: nested parens drop the version, a trailing `(...)`
  or `[...]` in a name is claimed as version/id, and names ending in whitespace lose it.
  `emit_item` never produces these shapes, so only hand-edited or external catalogs are
  affected.
- The legacy `NONE_FOUND_SENTINEL` is `"  (none found)"` with **exactly two** leading spaces
  and is distinct from `MD_NONE_FOUND`. Do not merge them.

Round-trip fidelity is locked by `tests/reinstall/test_parser_contract.py` (595 lines,
including an `ADVERSARIAL_CASES` table) and `tests/test_markdown_emitter.py`.

## Two Parsers, Deliberately

`src/maccat/reinstall/parser.py` contains two independent parsers that must not be conflated:

| | `parse_catalog` | `parse_markdown_catalog` |
|---|---|---|
| Input | Legacy plain-text `.txt` | Current `.md` (v3 format) |
| Structure cue | Title line followed by a 36-dash `SEPARATOR` | `---` frontmatter + `## ` headings + pipe tables |
| Machinery | Explicit 3-state machine: `SEEKING_TITLE` → `SEEKING_SEPARATOR` → `COLLECTING`, with an EOF flush | Frontmatter validation then a linear body scan |
| Item shape | `ITEM_RE` against a free-form `name (version) [id]` line | 3-column table row split on `" \| "` |
| Errors | Never raises on malformed lines; falls back to name-only | Raises `ValueError` for non-`.md` extension, missing/unclosed frontmatter |
| Empty sentinel | `NONE_FOUND_SENTINEL` (2 leading spaces) | `MD_NONE_FOUND` (no leading spaces) |
| Sole consumer | `src/maccat/convert.py` | `src/maccat/reinstall/cli.py` |

`parse_catalog` also emits a leading empty `ParsedSection` for the old
`"Installed Mac Software List"` header — intentionally *not* filtered in the parser, because an
empty header is indistinguishable from a legitimately empty section. `convert.py:102` filters
it at the consumer.

## Anti-Patterns

### Silently dropped collector warnings

**What happens:** `CollectorResult.warnings` is populated by several collectors (e.g.
`vscode.py`, `cursor.py`) but `run()` only reads `result.sections`
(`src/maccat/cli.py:353-355`).
**Why it's wrong:** A collector that partially failed looks identical to one that found nothing.
**Do this instead:** When adding a collector, print user-facing degradation notices to stderr at
the point of failure (as `homebrew.py` and `zed.py` do via `sys.stderr`) rather than relying on
the `warnings` list to surface anything.

### Assuming `available()` is called for you

**What happens:** A new collector overrides `available()` and returns `False`, expecting the
orchestrator to skip it — but `run()` calls `collect()` unconditionally.
**Why it's wrong:** The collector's real probe code runs anyway, possibly raising.
**Do this instead:** Guard inside `collect()`, mirroring
`src/maccat/collectors/homebrew.py:62` (`if not self.available(): return <degraded section>`).

### Importing across the emitter/parser boundary

**What happens:** "De-duplicating" `ITEM_RE` or the degradation frozenset by having
`catalog/markdown.py` import from `reinstall/parser.py`.
**Why it's wrong:** It couples the catalog package to the reinstall package and inverts the
dependency direction; the duplication is a deliberate contract boundary noted at
`src/maccat/catalog/markdown.py:30-33` and `src/maccat/reinstall/parser.py:4-6`.
**Do this instead:** Keep both copies in sync and let
`tests/reinstall/test_parser_contract.py` enforce equivalence.

### Sorting in Python instead of via `sort(1)`

**What happens:** Replacing the `flush_section` subprocess with `sorted(items, key=str.lower)`.
**Why it's wrong:** Diverges from `LC_ALL=C sort -f` for mixed-case and non-ASCII names,
breaking byte-determinism across runs and machines (`src/maccat/catalog/format.py:6-8`).
**Do this instead:** Keep the subprocess; it is load-bearing.

### Module-level `maccat.*` imports in CLI modules

**What happens:** Hoisting a deferred import to the top of `cli.py`, `convert.py`, or
`collectors/__init__.py`.
**Why it's wrong:** Breaks the `__main__.py` version-guard ordering and the
import-any-collector-in-isolation property that the test suite relies on
(`src/maccat/cli.py:10-13`).
**Do this instead:** Add the import inside the function body, next to the existing block.

### Writing `.md` and `.txt` removal in the wrong order

**What happens:** Unlinking the legacy `.txt` before the `.md` write is confirmed.
**Why it's wrong:** A failed write destroys the only copy of the catalog. This ordering is the
explicit `CONV-03` invariant (`src/maccat/convert.py:124-138`).
**Do this instead:** Write `.md` first; only then unlink, and surface a targeted recovery
message if the unlink fails.

## Error Handling

**Strategy:** Fail fast and loudly at the CLI boundary; degrade quietly inside collectors.

**Patterns:**
- User-facing fatal errors use `sys.exit("ERROR: …")` with an actionable multi-line message and
  a suggested command (`src/maccat/config.py:130-141`, `src/maccat/cli.py:237-239`,
  `src/maccat/convert.py:70-73`).
- Parsers never raise on malformed *content*; they fall back to a name-only `ParsedItem` with
  `raw_line` preserved. `parse_markdown_catalog` raises only for malformed *structure*
  (wrong extension, missing frontmatter), and every such message contains
  `maccat convert --from` so the user has a next step.
- `naming.parse_catalog_filename` returns `None` instead of raising, so retention sweeps can
  skip unrecognized files.
- All git operations are guarded by `_git_available()` + `_is_git_repo()` and warn-and-continue;
  a git failure never prevents the catalog from being written
  (`src/maccat/gitops.py:24,32`).
- `subprocess` calls always use `shell=False` with list arguments.
- A non-zero `sort` exit is escalated to `RuntimeError` specifically so the atomic writer aborts
  rather than committing a truncated section (`src/maccat/catalog/format.py:66-71`).

## Cross-Cutting Concerns

**Logging:** No logging framework. Progress goes to stdout via `print()`; degradation notices go
to stderr via `sys.stderr` inside collectors.

**Validation:** Two-tier in `identity.py` — `validate_computer_name` (fatal, `SystemExit`) and
`validate_computer_name_quiet` (returns an error string). Repo validation is
`validate_catalog_repo` in `config.py`, backed by `_is_git_repo` / `_has_git_remote`.

**Configuration precedence** (`src/maccat/config.py:97`): `--catalog-dir` flag →
`MACCAT_CATALOG_DIR` env → `~/.config/maccat/config.toml` (XDG-aware, never `platformdirs`) →
`SystemExit` with instructions. The flag value is never written back to the config file.

**Injection safety:** Two-function gate in `src/maccat/reinstall/emitter.py:27,36`.
`quote_for_script()` (a `shlex.quote` wrapper) is the *sole* path a catalog value may reach
shell command position; `safe_comment_value()` is the *sole* path into `#` comment context and
strips newlines, because `shlex.quote` preserves newlines inside single quotes and a newline in
a comment would expose the remainder as live shell code.

**Atomicity:** `CatalogWriter` (tmp + rename) for catalogs; `_atomic_write_lines` for
`machine-labels.tsv`; write-then-unlink ordering in `convert.py`.

---

*Architecture analysis: 2026-08-25*
