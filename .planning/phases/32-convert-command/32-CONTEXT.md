# Phase 32: Convert Command - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 3 grey areas; 2 user overrides recorded

<domain>
## Phase Boundary

Add `maccat convert --from PATH` — upgrade ONE legacy plain-text `.txt` catalog to
the new markdown `.md` format. Read the `.txt` via the RETAINED legacy text parser
(`reinstall/parser.py::parse_catalog`), rewrite its full contents (every section,
every item's name/version/ID) through the Phase 30 markdown emitter
(`catalog/markdown.py::render_markdown_catalog`), write the `.md`, remove the old
`.txt`, and stage both changes in a single commit. `--no-commit` performs the file
operations without git. Degrade gracefully on malformed/partial input; never
execute anything.

**In scope:** the `convert` subcommand; the ParsedCatalog→Section bridge feeding the
emitter; in-place `.txt`→`.md` replacement + single-commit git staging; `--no-commit`.

**Out of scope:** bulk/folder-wide convert (`--computer NAME` / all catalogs) — that
is the deferred CONV-bulk item, single-file only here. The reinstall markdown parser
(Phase 31) and the emitter (Phase 30) are stable; do not modify them.
</domain>

<decisions>
## Implementation Decisions

### Synthesized Frontmatter (USER OVERRIDE — "Fill from current machine")
The legacy `.txt` has no frontmatter. Convert synthesizes it as:
- **computer**: parsed from the `.txt` filename `mac-software-list-[computer]-TS.txt`.
- **generated**: **now()** (current ISO-8601 local time) — NOT the original filename
  timestamp. Rationale (user's choice): the `.md` is genuinely being produced now;
  stamp it with the conversion's actual context.
- **hostname**: the **current machine's hostname** (`socket.gethostname()`).
- **maccat_version**: current `maccat.__version__`.
- **Coherence note (locked):** the OUTPUT FILENAME keeps the ORIGINAL 14-digit
  timestamp from the source filename (just swaps `.txt`→`.md`, same basename, per
  CONV-02 "writes the .md, removes the old .txt"). So filename timestamp (original,
  preserves identity/sort order) intentionally differs from frontmatter `generated`
  (now(), records the conversion). Do NOT "fix" this apparent mismatch — it is the
  agreed design.

### In-Place Replacement & Git (CONV-02)
- Output filename = source basename with `.txt` → `.md` (original timestamp preserved).
- **If the target `.md` already exists → ERROR and skip** (USER OVERRIDE — do not
  clobber). Clean ERROR convention + non-zero exit; tell the user to remove the
  existing `.md` first. (Breaks idempotent re-runs by design — safety over convenience.)
- On success: write `.md`, remove the old `.txt`, and stage BOTH (add `.md` + delete
  `.txt`) in a SINGLE commit. The `git_commit_rename` pattern in `gitops.py`
  (`git add -A -- <path>` for both old and new, single commit, no-changes guard,
  warn-and-continue on push failure) is the closest analog to reuse/mirror.
- `--no-commit`: perform the file operations (write `.md`, remove `.txt`) WITHOUT any
  git calls.

### Graceful Degradation (CONV-03)
- **Abort (clean ERROR + non-zero exit) ONLY when:** the `--from` file is missing /
  unreadable, OR its filename is not a recognizable catalog filename (cannot derive
  `computer`). Nothing to convert → fail clearly, write nothing, delete nothing.
- **Warn-and-continue** for parseable-but-weird content: the legacy `parse_catalog`
  never raises (name-only fallback, `raw_line` preserved), so convert rewrites
  whatever it parsed without fabricating data. Never execute anything.
- Never delete the `.txt` unless the `.md` was written successfully (no data loss on
  a mid-operation failure).

### Claude's Discretion
- The `ParsedCatalog` → `list[Section]` bridge for the emitter: the faithful approach
  is `Section(title=ps.title, items=[it.raw_line for it in ps.items], raw=True)` so
  `render_markdown_catalog` re-parses the raw lines in original order (raw=True skips
  flush_section re-sorting). Degraded/empty `ParsedSection`s (items=[]) render as
  `(none found)`. Implementer's call on exact bridging, provided every parsed section
  and item round-trips into the `.md`.
- Parsing the LEGACY `.txt` filename for `computer`: `naming.parse_catalog_filename`
  matches `.md` only, so convert needs its own `.txt`-aware extraction (a `.txt`
  variant of `_FILENAME_RE`, or generalize). Implementer's choice.
- `convert` subcommand wiring in `cli.py` (a new `subparsers.add_parser("convert", …)`
  alongside `reinstall`), with deferred imports per PKG-03.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/maccat/reinstall/parser.py::parse_catalog(path) -> ParsedCatalog` — RETAINED
  legacy plain-text reader. `ParsedCatalog.sections: list[ParsedSection]`;
  `ParsedSection(title, items: list[ParsedItem], degraded)`;
  `ParsedItem(name, version, id, raw_line)`. Never raises (name-only fallback).
- `src/maccat/catalog/markdown.py::render_markdown_catalog(sections, *, computer,
  hostname, generated, maccat_version) -> str` — the emitter. Takes collector
  `Section`s (`base.Section(title, items: list[str], raw: bool)`); raw=True writes
  items verbatim (no re-sort). Frontmatter scalars are double-quoted (CR-01 fix).
- `src/maccat/naming.py` — `make_catalog_filename(machine, ts)` returns `.md`;
  `parse_catalog_filename(name)` parses `.md` names only (machine + timestamp).
- `src/maccat/gitops.py::git_commit_rename(repo, old_name, new_name)` — closest
  git analog: stages both paths with `git add -A -- <path>`, single commit, skips when
  nothing staged, warn-and-continue on push failure. `_git_available` / `_is_git_repo`
  guards. Also `git_commit_and_push`.
- `socket.gethostname()` + `maccat.__version__` + `datetime.now()` — same provenance
  sources the Phase 30 `cli.py` generate loop already uses.

### Established Patterns
- `cli.py` registers subcommands via `subparsers.add_parser(...)`; dispatch at bottom
  with deferred imports (PKG-03). `reinstall` is the closest subcommand analog.
- Clean ERROR convention: `sys.exit("ERROR: ...")` (non-zero), no traceback.
- stdlib-only; no PyYAML; ruff + mypy --strict clean; byte-stable output.

### Integration Points
- New `convert` subparser in `cli.py` + a `run_convert(args)` orchestrator (likely a
  new `src/maccat/convert.py` or `convert/cli.py`, implementer's choice).
- Reuses `parse_catalog` (read), `render_markdown_catalog` (write), `gitops` (commit).
- Does NOT touch the reinstall markdown parser or the emitter.
</code_context>

<specifics>
## Specific Ideas

- The convert round-trip is: legacy `.txt` → `parse_catalog` → `ParsedCatalog` →
  (bridge to Section[], raw=True) → `render_markdown_catalog` → `.md`. The resulting
  `.md` must itself be parseable by the Phase 31 markdown parser (it will be, since it
  goes through the same emitter) — worth a test that converts a fixture `.txt` and then
  `parse_markdown_catalog`s the output to prove the full chain.
</specifics>

<deferred>
## Deferred Ideas

- **CONV-bulk** — bulk / folder-wide convert (`--computer NAME` or all catalogs). Already
  tracked as a deferred item; explicitly out of scope for this single-file phase.
</deferred>
