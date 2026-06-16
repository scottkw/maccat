# Phase 24: Catalog Format Fix + Parser Foundation - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers two foundations for the v2.1.0 reinstall feature:

1. **MAS-01** — `MasCollector` preserves the numeric App Store ID, emitting
   `AppName (version) [id]` (no double-parenthesized version, no missing bracket).
2. **PARSE-01** — a new `reinstall/` subpackage with a `parse_catalog(path)` that reads
   the emitted plain-text catalog sections back into typed structured items
   (`ParsedItem` / `ParsedSection` / `ParsedCatalog`), inverting all four `emit_item`
   line shapes and their degradations, locked by a round-trip contract test.

Out of boundary: the script emitter (Phase 25) and the `reinstall` CLI subcommand /
picker (Phase 26). This phase produces no user-facing behavior — it is the format
fix + parser the later phases build on.
</domain>

<decisions>
## Implementation Decisions

### mas Collector Format Change (MAS-01)
- Route mas lines through `emit_item(name, version, id_)` so the `[id]` format stays
  centralized in `catalog/format.py` (do NOT duplicate the format string in the collector).
- De-paren the version: `mas list` column 3 already wraps the version in parens
  (e.g. `(14.0)`); strip a single leading `(` / trailing `)` before passing to
  `emit_item` to avoid `AppName ((14.0)) [id]`.
- Parse multi-word app names robustly: split column 1 (numeric id) off the front, take
  the trailing `(version)` token as the version, and treat everything in between as the
  name (fixes the pre-existing naive `parts[1]/parts[2]` split that broke names like
  "Final Cut Pro"). Real `mas list` output is `<id> <Name…> (<version>)`.
- Keep the mas section `raw=True` (it stays a raw section like Homebrew / Setapp /
  Web-installed); only the per-line content changes, not the write path.
- Update the existing mas collector tests (in `tests/collectors/test_homebrew.py`) with
  assertions reflecting the new `name (version) [id]` format.

### Parser Data Model & API (PARSE-01)
- `ParsedItem` fields: `name: str`, `version: str | None`, `id: str | None`, plus
  `raw_line: str` retained for round-trip fidelity and debugging.
- Shape detection: a single **right-anchored** regex with optional groups — match an
  optional `[id]` at the end, then an optional `(version)` before it, with the remainder
  as the name. One regex, applied per item line.
- `(none found)` sentinel: recognize the exact `  (none found)` line (two leading spaces)
  and yield an **empty item list** for that section — never a fake item.
- Collector degradation / fallback messages (e.g. "Homebrew is not installed.",
  "mas (Mac App Store CLI) is not installed.", "Could not retrieve App Store list."):
  detect known fallback lines and mark the section degraded with zero items — do not
  parse them as software items.

### Section Identity & Parser Strictness
- Section identification: a section-boundary state machine keyed on the header line
  (title between `------` separators). Store the section title **verbatim** on
  `ParsedSection`; defer title→source mapping to Phase 25's `SECTION_SOURCE_MAP`.
- Unknown / new section titles: parse generically (capture title + items) rather than
  error — forward-compatible with future catalog sections.
- Embedded parens / brackets in names ("App (Beta) (1.2.3) [id]"): right-anchored
  matching takes the LAST `(...)` as version and LAST `[...]` as id, so inner parens
  stay part of the name. Adversarial fixtures cover this.
- Unparseable item line: fall back to a name-only `ParsedItem` (the whole line as name) —
  never crash; the round-trip preserves the original text.

### Claude's Discretion
- Exact regex syntax, dataclass module layout, state-machine internals, and test-fixture
  organization are at Claude's discretion within the decisions above.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `catalog/format.py::emit_item(name, version, id_)` — the canonical line builder; the
  parser inverts EXACTLY the four shapes it produces (`name (version) [id]`,
  `name (version)`, `name [id]`, `name`) plus id-promotion degradations. **Must not change
  except for routing mas through it.**
- `collectors/base.py::Section` — `raw: bool` flag distinguishes raw-write sources
  (Homebrew, App Store, Setapp, Web-installed) from `flush_section` sources.
- `collectors/mas.py::MasCollector` — currently raw-write, drops the id via
  `_parse_mas_output` (`parts[1] parts[2]`). This is the file to change for MAS-01.

### Established Patterns
- Collectors return `CollectorResult(sections=[Section(...)])`; degraded/absent sources
  return a fallback `Section` with `raw=True` and a known message, never abort.
- Tests live under `tests/collectors/` and `tests/` mirroring the source tree; mas tests
  are colocated in `tests/collectors/test_homebrew.py`.
- Section separators in catalogs are `------------------------------------` lines; section
  titles sit between separators (see `catalog/writer.py`).

### Integration Points
- New `src/maccat/reinstall/` subpackage: `__init__.py`, `parser.py` (dataclasses +
  `parse_catalog`). New test dir `tests/reinstall/` with `test_parser_contract.py`.
- The parser is consumed by Phase 25's emitter (`reinstall/emitter.py`) and Phase 26's
  CLI — keep the public API (`parse_catalog(path) -> ParsedCatalog`) stable.
</code_context>

<specifics>
## Specific Ideas

- Round-trip contract test (`tests/reinstall/test_parser_contract.py`) must cover all six
  `emit_item` degradation variants AND adversarial fixtures with embedded parentheses /
  brackets in names. The test locks the parser ↔ `catalog/format.py` coupling so the two
  cannot silently drift.
- Go-forward only: catalogs generated before MAS-01 lack the id, so the parser must
  degrade those mas entries gracefully (name + version, no id) — the emitter (Phase 25)
  routes id-less mas entries to the manual checklist.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Title→source mapping and the emitter itself
are Phase 25; the CLI subcommand and picker are Phase 26, per the roadmap.)
</deferred>
