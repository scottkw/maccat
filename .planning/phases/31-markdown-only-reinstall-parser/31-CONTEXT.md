# Phase 31: Markdown-Only Reinstall Parser - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous) — 3 grey areas, all recommended answers accepted

<domain>
## Phase Boundary

Add a markdown catalog parser that inverts the Phase 30 emitter
(`catalog/markdown.py::render_markdown_catalog`): read the new `.md` format
(YAML frontmatter + per-section 3-column `Name | Version | ID` tables) back into
the existing typed `ParsedCatalog`. Re-lock the parser↔emitter round-trip with a
contract test against the markdown emitter. Make `maccat reinstall` consume the
markdown format only; handed a legacy `.txt` (or a malformed `.md`) it must fail
with a clear "convert it first" message — never a silent partial parse, nothing
executed.

**In scope:** new markdown parser in `reinstall/parser.py`; the `.txt` refusal in
the reinstall dispatch; the markdown round-trip contract test.

**Out of scope:** the `convert` command (Phase 32); changing the emitter
(locked in Phase 30); the interactive picker glob (already `.md` after Phase 30).
The LEGACY plain-text `parse_catalog` is RETAINED unchanged — Phase 32's convert
reads old `.txt` through it.
</domain>

<decisions>
## Implementation Decisions

### Legacy `.txt` Refusal (RIN-02)
- Detect a non-markdown catalog by **extension AND content sniff**: refuse any
  non-`.md` path, and ALSO refuse an `.md` file that lacks valid YAML frontmatter
  (catches a renamed/mislabeled old catalog). This is the most robust guard.
- The failure message names the exact remedy: `maccat convert --from PATH`.
- Refusal lives in the **parse/dispatch step** (after path resolution), not in the
  picker glob — the picker already only surfaces `.md` files; this guard matters
  most for the explicit `--from PATH` mode.
- Use the project's clean ERROR convention (message + non-zero exit), no traceback.
- No silent partial parse; nothing is executed when a catalog is refused.

### Frontmatter Handling
- **Parse-and-skip**: validate the `---` fences are present and well-formed, then
  skip past the frontmatter to the section tables. The round-trip contract covers
  **sections + items only** — provenance (computer/hostname/generated/maccat_version)
  is not section data, and the reinstall emitter already supplies its own
  `source_name` + today's date. Keep `ParsedCatalog` unchanged (no speculative
  provenance fields until a consumer needs them).
- Presence of valid frontmatter is the positive signal that this IS a markdown
  catalog (ties into the content-sniff refusal above).

### Parser Strictness
- **Lenient at the item level, strict at the structure level.** Unparseable table
  rows fall back to name-only `ParsedItem`s with `raw_line` preserved — mirroring
  the legacy parser's graceful contract and the project's graceful-degradation
  constraint.
- But a file with no recognizable frontmatter + tables triggers the convert
  refusal rather than a silent empty parse (upholds RIN-02's no-silent-partial
  intent).
- Reverse the emitter's cell escaping when reading table cells: `\|` → `|` and
  `\\` → `\` (backslash-aware, the inverse of `_escape_cell`). Reconstruct
  `ParsedItem` from the three table columns directly; preserve `raw_line`.
- `(none found)` under a heading → empty section; known degradation lines →
  `degraded=True`, consistent with the legacy parser's section semantics.

### Claude's Discretion
- New public function name/shape for the markdown parser (e.g.
  `parse_markdown_catalog(path) -> ParsedCatalog`) vs how `reinstall/cli.py` is
  rewired to call it — implementer's choice, provided the legacy `parse_catalog`
  stays importable and unchanged for Phase 32.
- Whether the markdown round-trip contract test lives beside or replaces the
  existing reinstall parser tests — but the legacy `parse_catalog` tests must
  remain (convert depends on that reader). Per the roadmap, the markdown
  round-trip lock **replaces** the v2.1.0 plain-text lock for the reinstall path;
  it does not delete the legacy reader's own coverage.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/maccat/catalog/markdown.py` — the emitter to invert. Key shapes:
  - `render_frontmatter()` → `---\ncomputer: "..."\nhostname: "..."\ngenerated: "..."\nmaccat_version: "..."\n---\n` (all scalars double-quoted; CR-01 fix).
  - Table: `| Name | Version | ID |` then `| --- | --- | --- |` then rows; empty version/id cell is a single space `" "`.
  - `_escape_cell` escapes `\` then `|` (`\\`, `\|`) — the parser must reverse in the opposite order.
  - Empty/degraded sections render `(none found)` (no table).
  - Section headings are `## <Title>`; catalog title is `# Installed Mac Software List`.
- `src/maccat/reinstall/parser.py` — the LEGACY plain-text parser: `parse_catalog(path) -> ParsedCatalog`, dataclasses `ParsedItem(name, version, id, raw_line)`, `ParsedSection(title, items, degraded)`, `ParsedCatalog(sections, path)`. RETAIN it; the new markdown parser reuses the same dataclasses.
- `DEGRADATION_LINES` / `NONE_FOUND_SENTINEL` constants already exist in both parser.py and markdown.py (duplicated to avoid coupling).

### Established Patterns
- `reinstall/cli.py::run_reinstall` uses deferred imports (PKG-03 lazy import) and converts `OSError` from reading the catalog into the clean `sys.exit("ERROR: ...")` convention. The `.txt`/malformed refusal should follow the same `sys.exit("ERROR: ...")` style.
- Parsers never raise on item-level malformation — name-only fallback with `raw_line` preserved.
- stdlib-only; no PyYAML — frontmatter is parsed/skipped by hand (the emitter writes a fixed, simple 4-key block).

### Integration Points
- `reinstall/cli.py::run_reinstall` step 2 (`catalog = parse_catalog(catalog_path)`) is where the new markdown parser + the refusal guard wire in.
- `reinstall/picker.py` already globs `.md` (Phase 30 fix) — no change needed.
- `reinstall/emitter.py::emit_reinstall_script` consumes `ParsedCatalog` unchanged — the markdown parser must produce the same dataclass shape so the emitter is untouched.
</code_context>

<specifics>
## Specific Ideas

- The round-trip contract is the milestone's central invariant: emit a catalog via
  `render_markdown_catalog` → parse via the new markdown parser → assert the parsed
  sections/items match the input across all 22 section types and all `emit_item`
  line shapes (name only; name+version; name+id; name+version+id; pipe-containing;
  backslash-containing; empty/degraded). Re-lock it here.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (The `convert` command that reads old
`.txt` through the retained legacy parser is Phase 32, already roadmapped.)
</deferred>
