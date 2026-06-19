# Phase 30: Markdown Emitter & `.md` Plumbing - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Catalog generation produces a rendered markdown `.md` snapshot instead of plain text:
YAML frontmatter provenance + a `#` title + one `##` per-source section rendering items as
a uniform `Name | Version | ID` markdown table. Every `.txt`-keyed file behavior (filename
pattern, newest-per-computer retention, archive pruning, git staging) moves to `.md`.

This phase is **format-only**. The 22 sources, the collectors, and the data they collect are
unchanged — only how that data is rendered and which file extension/glob is used changes.
Out of scope: the reinstall parser (Phase 31), the convert command (Phase 32), any new data
sources, and dual-format support.

</domain>

<decisions>
## Implementation Decisions

### Frontmatter & Title
- Frontmatter is a standard `---`-fenced YAML block at the very top of the file.
- Frontmatter keys are snake_case: `computer`, `hostname`, `generated`, `maccat_version`.
- `generated` value is an ISO-8601 local timestamp (e.g. `2026-06-18T12:34:56`) — readable and
  cleanly parseable for the Phase 31 round-trip. (The 14-digit filename timestamp stays as-is in
  the filename.)
- The `#` title text stays `# Installed Mac Software List` (continuity with prior format;
  per-machine provenance lives in the frontmatter, not the title).

### Table Rendering
- Each source renders as a `##` heading followed by a three-column markdown table with the
  header row `Name | Version | ID` (exact casing per MD-03).
- A missing version or ID renders as an empty, space-padded cell — no `-`/`—` placeholder.
- A literal `|` appearing in any cell value is escaped as `\|` so the table cannot break and the
  value round-trips cleanly (Phase 31 parser must unescape).
- **Raw sections (Homebrew formulae/casks, mas) render as the same 3-column table** — their
  current verbatim lines are split into name / version / ID columns so all 22 sources are uniform
  (MD-03). This means the markdown emitter needs the structured (name, version, id) fields, not the
  pre-joined `emit_item` strings; planning must decide how to surface those fields (re-parse the
  emitted line via the same inverse logic Phase 31 uses, or thread structured data through).

### Empty Sections, Ordering & Sort
- A source with no items renders a plain `(none found)` line under its `##` heading — no empty
  table (MD-04).
- Section order preserves the current collector-registry order (no reordering behavior change).
- Items within a table keep the existing `LC_ALL=C sort -f -u` ordering/dedup (determinism +
  parity with prior behavior). Do NOT switch to Python's built-in sort.
- One blank line precedes each `##` heading for clean markdown rendering.

### Determinism
- Two consecutive runs must produce byte-identical `.md` output modulo the `generated`
  timestamp. Tests should inject/fix the timestamp to assert byte-identity. Stable sort + stable
  frontmatter key order + stable section order are the determinism guarantees.

### Claude's Discretion
- Exact module layout for the markdown emitter (extend `catalog/format.py` vs a new
  `catalog/markdown.py`), the YAML-serialization approach (hand-rolled vs minimal), and how the
  CatalogWriter / generate loop in `cli.py` is adapted — all at Claude's discretion, guided by
  the existing stdlib-only, byte-deterministic conventions.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/maccat/catalog/format.py` — `emit_item(name, version, id_)` builds the current
  `name (version) [id]` line and encodes the FMT-01 degradation rules; `flush_section()` does the
  mandatory `LC_ALL=C sort -f -u`; `version_sort_tail()` for version dir selection. The emitter's
  field→string logic is the inverse of what the markdown table needs.
- `src/maccat/catalog/writer.py` — `CatalogWriter` atomic tmp+rename context manager with
  `write_section(title)` / `write_lines(lines)`. The markdown emitter plugs in here.
- `src/maccat/naming.py` — `make_catalog_filename()` / `parse_catalog_filename()` and
  `_FILENAME_RE` are hardcoded to `.txt`; these move to `.md`.
- `src/maccat/retention.py` — globs `mac-software-list-*.txt` (lines 64, 75, 118) for
  newest-per-host retention and archive pruning; the glob moves to `.md` (replaced, not duplicated).
- `src/maccat/cli.py` (~lines 311–327) — the generate loop: `make_catalog_filename` →
  `CatalogWriter` → `write_section("Installed Mac Software List")` then per-collector
  `write_section(section.title)` + `flush_section` (or raw `write_lines` for `section.raw`).
- `src/maccat/gitops.py` — `git_commit_and_push` stages the computer folder; verify the
  add/discovery path is extension-agnostic or update it for `.md`.

### Established Patterns
- stdlib-only, no third-party deps; byte-deterministic output is a hard invariant.
- Collectors return `result.sections` each with `.title`, `.items` (pre-formatted strings),
  and a `.raw` flag (Homebrew/mas are raw → currently written verbatim, unsorted).
- Atomic write via tmp + rename; never commit a partial catalog. Non-zero `sort` exit aborts.
- Warn-and-continue / never-raise policy in collectors and filename parsing.

### Integration Points
- Filename + glob: `naming.py` + `retention.py` extension change to `.md`.
- Generate loop: `cli.py` switches from plain `write_section`/`write_lines` to markdown
  frontmatter + `##` sections + tables.
- Git: `gitops.py` staging must pick up `.md` adds, archive moves, and `.txt`→removed deletions.

</code_context>

<specifics>
## Specific Ideas

- Filename pattern target: `mac-software-list-[computer]-YYYYMMDDHHMMSS.md`.
- A stray legacy `.txt` left in a folder must be ignored by `.md` retention (not deleted) — the
  `.txt` glob is replaced by a `.md` glob, so legacy files simply fall outside retention's view.

</specifics>

<deferred>
## Deferred Ideas

- Reinstall parser reading the markdown format and the round-trip contract test — Phase 31.
- `maccat convert --from PATH` upgrading legacy `.txt` catalogs — Phase 32.
- Bulk/folder-wide conversion, dual-format reinstall, per-source variable columns, JSON/HTML
  output — explicitly out of scope for v3.0.0 (REQUIREMENTS.md).

</deferred>
