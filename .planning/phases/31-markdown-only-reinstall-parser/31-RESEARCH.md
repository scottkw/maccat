# Phase 31: Markdown-Only Reinstall Parser — Research

**Researched:** 2026-06-18
**Domain:** Python stdlib, markdown table parsing, round-trip contract testing
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- `.txt` refusal: extension AND content-sniff (refuse non-`.md`, and refuse `.md` lacking valid frontmatter); message names `maccat convert --from PATH`; lives in parse/dispatch step; clean ERROR convention + non-zero exit; no silent partial parse.
- Frontmatter: parse-and-skip (validate fences, skip to sections); `ParsedCatalog` stays unchanged (no new provenance fields). Round-trip contract covers sections + items only.
- Strictness: lenient at item level (name-only fallback, `raw_line` preserved), strict at structure level (no frontmatter + tables → refuse). Reverse the emitter's cell escaping: `\|` → `|`, `\\` → `\` (backslash-aware, inverse of `_escape_cell`). Reconstruct `ParsedItem` from the 3 columns; preserve `raw_line`. `(none found)` → empty section; degradation lines → `degraded=True`.
- stdlib-only (NO PyYAML). Frontmatter is a fixed 4-key block — hand-parse/skip it.

### Claude's Discretion

- New public function name/shape for the markdown parser (e.g. `parse_markdown_catalog(path) -> ParsedCatalog`) vs how `reinstall/cli.py` is rewired to call it — implementer's choice, provided the legacy `parse_catalog` stays importable and unchanged for Phase 32.
- Whether the markdown round-trip contract test lives beside or replaces the existing reinstall parser tests — but the legacy `parse_catalog` tests must remain (convert depends on that reader). Per the roadmap, the markdown round-trip lock replaces the v2.1.0 plain-text lock for the reinstall path; it does not delete the legacy reader's own coverage.

### Deferred Ideas (OUT OF SCOPE)

- The `convert` command that reads old `.txt` through the retained legacy parser — Phase 32, already roadmapped.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RIN-01 | `reinstall/parser.py` parses the new markdown catalog format (frontmatter + per-section tables) into the typed `ParsedCatalog`, with the parser ↔ emitter round-trip re-locked by the contract test against the markdown emitter. | `parse_markdown_catalog()` state machine design verified; table row splitting algorithm proven; unescape algorithm verified exhaustively. |
| RIN-02 | `maccat reinstall` consumes the markdown format only; handed a legacy `.txt` catalog it fails with a clear message directing the user to `convert` it first (no silent partial parse). | Extension check + frontmatter content-sniff design verified; `ValueError` → `sys.exit` wiring in `cli.py` documented. |
</phase_requirements>

---

## Summary

This phase adds `parse_markdown_catalog(path: Path) -> ParsedCatalog` to `reinstall/parser.py`, re-locking the reinstall pipeline to the Phase 30 markdown emitter. The function inverts `render_markdown_catalog()` from `catalog/markdown.py`: it reads the `---` frontmatter fences (validate + skip), iterates `## Section Title` headings, and converts `| Name | Version | ID |` table rows back into `ParsedItem` dataclasses — using the same `ParsedCatalog / ParsedSection / ParsedItem` dataclasses as the legacy `parse_catalog`, so `emitter.py` requires zero changes.

The cell unescaping is the inverse of `_escape_cell`: `\|` → `|` then `\\` → `\`. This order is correct. The table column separator is always ` | ` (space-pipe-space) because `_escape_cell` converts all bare `|` in cell values to `\|` (backslash-pipe), which can never produce the ` | ` (space-pipe-space) pattern. Splitting on ` | ` after stripping the leading `| ` and trailing ` |` is therefore exact and safe for all possible cell contents.

The `.txt` refusal fires in `run_reinstall` via a `ValueError` raised by `parse_markdown_catalog` (extension check + frontmatter content-sniff), caught in `cli.py` alongside the existing `OSError` catch and converted to `sys.exit("ERROR: ...")`. Three test files require fixture updates (`.txt` → `.md` content); a new `TestMarkdownRoundTrip` and `TestMarkdownParserRefusal` class establish the contract.

**Primary recommendation:** Add `parse_markdown_catalog()` to `reinstall/parser.py` (co-located with dataclasses and `parse_catalog`). Raise `ValueError` for format errors. Catch `ValueError` alongside `OSError` in `cli.py`. The markdown round-trip contract test belongs in a new test class inside `tests/reinstall/test_parser_contract.py` (or a new `test_markdown_parser_contract.py`).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Markdown catalog parsing (frontmatter + table rows → ParsedCatalog) | `reinstall/parser.py` | — | Co-located with dataclasses and `parse_catalog`; pure parsing, no I/O side effects |
| `.txt` / malformed `.md` refusal guard | `reinstall/parser.py` (`parse_markdown_catalog`) | `reinstall/cli.py` (converts ValueError → sys.exit) | Parser detects format error; CLI converts to clean user-facing exit |
| Reinstall pipeline wiring | `reinstall/cli.py::run_reinstall` | — | Replaces `parse_catalog` call with `parse_markdown_catalog` call |
| Round-trip contract test | `tests/reinstall/test_parser_contract.py` | — | New `TestMarkdownRoundTrip` class; locks `catalog/markdown.py` ↔ `reinstall/parser.py` |
| Legacy `parse_catalog` preservation | `reinstall/parser.py` (unchanged) | — | Phase 32 `convert` reads old `.txt` files through the existing legacy reader |

---

## Standard Stack

### Core (stdlib only — no new dependencies)
| Module | Purpose |
|--------|---------|
| `re` | Already imported in `reinstall/parser.py` (for `ITEM_RE`); no new usage needed for the markdown parser — column splitting uses string methods |
| `pathlib.Path` | Already used; `parse_markdown_catalog(path: Path)` signature mirrors `parse_catalog` |
| `sys` | `sys.exit()` in `cli.py` for the refusal ERROR output |

No new packages. `pyproject.toml` stays: `# Zero runtime deps — stdlib only`. [VERIFIED: direct file inspection; venv pip list confirms no PyYAML]

---

## Package Legitimacy Audit

No new packages are installed in this phase. The project remains stdlib-only with zero runtime dependencies. The Package Legitimacy Gate protocol does not apply.

---

## Architecture Patterns

### System Architecture Diagram

```
maccat reinstall --from PATH.md
     ↓
resolve_catalog_path(args)              [picker.py — unchanged; already globs .md]
     ↓ Path
run_reinstall()                         [cli.py — step 2 rewired]
     ↓
parse_markdown_catalog(path)            [parser.py — NEW function]
     ├── extension check: suffix != '.md' → raise ValueError("not a markdown catalog")
     ├── open file (UTF-8)
     ├── frontmatter check: no '---' fence → raise ValueError("missing frontmatter")
     ├── skip frontmatter lines until closing '---'
     ├── skip H1 title line (# Installed Mac Software List)
     └── for each line:
           ├── '## Title' → start new ParsedSection
           ├── '| Name | Version | ID |' → skip (table header)
           ├── '| --- | --- | --- |' → skip (separator row)
           ├── '| cell | cell | cell |' → parse_table_row() → ParsedItem
           ├── '(none found)' → current section: items=[], degraded=False
           └── blank / unrecognized → continue
     ↓
ParsedCatalog(sections=[...], path=str(path))
     ↓
emit_reinstall_script(catalog, ...)     [emitter.py — UNCHANGED]
     ↓
reinstall.sh
```

### Recommended Project Structure

No new files needed. Changes are limited to:
```
src/maccat/reinstall/
├── parser.py       # ADD: parse_markdown_catalog(); KEEP: parse_catalog() unchanged
└── cli.py          # UPDATE: parse_catalog → parse_markdown_catalog; expand except
tests/reinstall/
├── test_parser_contract.py          # ADD: TestMarkdownRoundTrip, TestMarkdownParserRefusal
├── test_reinstall_cli.py            # UPDATE: .txt fixture → .md fixture + markdown content
└── test_picker_and_reinstall_cli.py # UPDATE: .txt fixture → .md fixture + markdown content
```

### Pattern 1: `parse_markdown_catalog` State Machine

**What:** A line-by-line state machine that consumes the `---` frontmatter block, skips the H1 title, then collects `## sections` and table rows.

**States:**
- `FRONTMATTER_OPEN`: skip lines until first `---`
- `IN_FRONTMATTER`: consume lines until closing `---`; presence of both fences validates the frontmatter
- `BODY`: process H1 title, `##` headings, table rows, `(none found)`, blank lines

**Frontmatter validation rule:** The file must begin with `---\n` (line 0) and the closing `---\n` must appear before any `##` heading. If the first line is NOT `---`, raise `ValueError` immediately (extension-only guard already fired; this is the content-sniff guard).

**Example:**
```python
# Source: direct analysis of catalog/markdown.py render output (verified 2026-06-18)
def parse_markdown_catalog(path: Path) -> ParsedCatalog:
    """Parse a .md catalog into ParsedCatalog. Raises ValueError for non-markdown catalogs."""
    path = Path(path)
    if path.suffix != ".md":
        raise ValueError(
            f"{path} is not a markdown catalog (.md). "
            f"Convert it first: maccat convert --from {path}"
        )
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    
    # Validate frontmatter fences
    if not lines or lines[0] != "---":
        raise ValueError(
            f"{path} is missing valid frontmatter. "
            f"Convert it first: maccat convert --from {path}"
        )
    
    # Skip frontmatter (find closing ---)
    fm_close = -1
    for i, line in enumerate(lines[1:], 1):
        if line == "---":
            fm_close = i
            break
    if fm_close == -1:
        raise ValueError(f"{path}: frontmatter is not closed with ---.")
    
    catalog = ParsedCatalog(path=str(path))
    current_section: ParsedSection | None = None
    
    for line in lines[fm_close + 1:]:
        if line.startswith("## "):
            if current_section is not None:
                catalog.sections.append(current_section)
            current_section = ParsedSection(title=line[3:])
        elif line == "(none found)":
            if current_section is not None:
                pass  # items=[] and degraded=False already — no action needed
        elif line.startswith("| ") and line.endswith(" |") and "---" not in line:
            # Skip header rows: '| Name | Version | ID |'
            if line == "| Name | Version | ID |":
                continue
            item = _parse_markdown_row(line)
            if item is not None and current_section is not None:
                current_section.items.append(item)
        # blank lines, H1 title, separator rows: skip
    
    if current_section is not None:
        catalog.sections.append(current_section)
    
    return catalog
```

### Pattern 2: Table Row Parsing — `_parse_markdown_row`

**What:** Split `| name | ver | id |` into three cells, unescape each cell, map empty cells to `None`.

**Column separator:** The emitter's format string is `f"| {_escape_cell(name)} | {ver_cell} | {id_cell} |"`. The column separator is always ` | ` (space-pipe-space). Since `_escape_cell` converts all bare `|` in cell values to `\|` (backslash-pipe), a bare ` | ` (space-pipe-space) can never appear inside an escaped cell value. Splitting on ` | ` after stripping the leading `| ` and trailing ` |` is therefore unambiguous and safe for all possible cell contents. [VERIFIED: exhaustive test over all combinations of `a`, `\`, `|` up to length 3, 2026-06-18]

**Empty cell mapping:** The emitter renders missing version/id as a single space `" "`. After stripping leading `| ` and splitting on ` | `, the empty cell becomes `' '` (one space). Map any cell where `cell.strip() == ''` to `None` to match `ParsedItem.version` / `ParsedItem.id` semantics. [VERIFIED: direct Python testing, 2026-06-18]

**`raw_line`:** Set to the table row string itself (the source text). The reinstall `emitter.py` does not use `raw_line` at all — it is purely a forensics/fallback field. [VERIFIED: grep of emitter.py — zero `raw_line` references]

```python
# Source: direct analysis of catalog/markdown.py and parser.py (verified 2026-06-18)
def _parse_markdown_row(row: str) -> ParsedItem | None:
    """Parse '| name | ver | id |' → ParsedItem. Returns None on structural mismatch."""
    # row already confirmed to start with '| ' and end with ' |'
    inner = row[2:-2]               # strip leading '| ' and trailing ' |'
    cols = inner.split(" | ")
    if len(cols) != 3:
        # Structural mismatch — name-only fallback
        name = _unescape_cell(inner.strip())
        return ParsedItem(name=name, version=None, id=None, raw_line=row)
    name = _unescape_cell(cols[0])
    version = _unescape_cell(cols[1]) or None  # ' ' → '' → None
    id_ = _unescape_cell(cols[2]) or None
    return ParsedItem(name=name, version=version, id=id_, raw_line=row)

def _unescape_cell(value: str) -> str:
    """Inverse of _escape_cell. Strip surrounding whitespace then unescape."""
    # The cell value may have surrounding spaces from '|  |' (empty cell) or
    # legitimate leading/trailing spaces in a name (edge case only).
    # strip() is correct here because _escape_cell never adds leading/trailing spaces.
    s = value.strip()
    # Unescape \| → | first, then \\ → \. Either order works mathematically
    # (proven exhaustively), but pipe-first matches the intuitive inverse of
    # "backslash first then pipe" escaping.
    return s.replace("\\|", "|").replace("\\\\", "\\")
```

### Pattern 3: Unescape Algorithm — Proven Correct in Both Orders

**What:** `_escape_cell` escapes in order: `\` → `\\` first, then `|` → `\|`. The inverse unescaping can be applied in EITHER order and still produce the correct result.

**Why both orders work:** After escaping, every `\\` in the output represents exactly one original `\`, and every `\|` represents exactly one original `|`. These two sequences do not overlap in a way that causes ambiguity — there are no "accidental" `\\` patterns that could arise from unescaping `\|` first, because all backslashes were already doubled before any pipe was escaped. [VERIFIED: exhaustive Python test over all 3-char combinations of `{a, \, |}`, 2026-06-18]

**Adversarial cases and their round-trips:**

| Original value | After `_escape_cell` | After unescape | Round-trip ok? |
|----------------|---------------------|----------------|----------------|
| `git` | `git` | `git` | Yes |
| `foo\|bar` | `foo\\\|bar` | `foo\|bar` | Yes |
| `a\b` | `a\\b` | `a\b` | Yes |
| `a\|b` | `a\\\|b` | `a\|b` | Yes |
| `stdio\|sse` (id) | `stdio\\\|sse` | `stdio\|sse` | Yes |
| `\\\\` | `\\\\\\\\` | `\\\\` | Yes |

[VERIFIED: direct Python testing, 2026-06-18]

**Implementation note:** The `strip()` call in `_unescape_cell` handles the empty cell case (`' '` → `''` after strip → returns `''` → caller maps `''` to `None`). This is correct because `_escape_cell` never adds surrounding whitespace to a cell value.

### Pattern 4: `(none found)` Handling — Unified Treatment

**What:** In the markdown format, BOTH empty sections and degraded sections render as `(none found)` under the `##` heading. The markdown parser cannot distinguish which was which.

**Why this is safe:** `emitter.py::_should_skip()` returns `True` for `section.degraded` OR `len(section.items) == 0`. Mapping all `(none found)` lines to `items=[], degraded=False` is therefore correct — the emitter skips both cases. [VERIFIED: emitter.py source inspection]

**CONTEXT.md note:** The CONTEXT.md says "degradation lines → `degraded=True`", but this refers to lines from the LEGACY plain-text format (`"Homebrew is not installed."` etc.) that appear in the legacy `parse_catalog`. In the markdown format, those degradation lines were already converted to `(none found)` by the emitter — they never appear in the `.md` file. The markdown parser sees only `(none found)`, which maps to `items=[], degraded=False`.

### Pattern 5: `cli.py` Wiring — `ValueError` Pattern

**What:** `parse_markdown_catalog` raises `ValueError` for format errors. `run_reinstall` in `cli.py` catches both `OSError` and `ValueError` and converts both to `sys.exit("ERROR: ...")`.

**Why `ValueError` (not `sys.exit` from parser):** Keeps `parse_markdown_catalog` a pure function testable without catching `SystemExit`. `ValueError` is the stdlib convention for "wrong data type/format." [ASSUMED — either approach works; `ValueError` is the cleaner design.]

```python
# Source: direct analysis of reinstall/cli.py (verified 2026-06-18)
# Updated try/except in run_reinstall:
try:
    catalog = parse_markdown_catalog(catalog_path)
except (OSError, ValueError) as exc:
    sys.exit(f"ERROR: {exc}")
```

**Refusal message format:** The `ValueError` message from `parse_markdown_catalog` should be self-contained and actionable:
- For non-`.md` extension: `"PATH is not a markdown catalog. Convert it first with: maccat convert --from PATH"`
- For missing frontmatter: `"PATH is missing valid YAML frontmatter — it may be a legacy .txt catalog renamed to .md. Convert it first with: maccat convert --from PATH"`

### Pattern 6: Fixture Updates in Existing Tests

**What:** Three existing test files use `.txt` fixture catalogs with legacy plain-text content. After Phase 31, `run_reinstall` calls `parse_markdown_catalog` which refuses `.txt` files. All fixtures must be updated to `.md` with valid markdown content.

**Minimal valid markdown catalog (for test fixtures):**
```python
# Source: direct output of render_markdown_catalog (verified 2026-06-18)
_MINIMAL_MD_CATALOG = (
    '---\n'
    'computer: "TestMac"\n'
    'hostname: "test-mac.local"\n'
    'generated: "2026-06-18T12:34:56"\n'
    'maccat_version: "2.1.0"\n'
    '---\n'
    '# Installed Mac Software List\n'
    '\n'
    '## Homebrew Packages\n'
    '| Name | Version | ID |\n'
    '| --- | --- | --- |\n'
    '| wget | 1.21.3 |   |\n'
    '\n'
)
```

**Files requiring fixture updates:**
1. `tests/reinstall/test_reinstall_cli.py`: `_MINIMAL_CATALOG` constant (plain-text) → markdown; `fixture_catalog` path → `.md`
2. `tests/reinstall/test_picker_and_reinstall_cli.py`: `fixture_catalog` content and filename → `.md`; `_find_newest_catalog` / `picker-mode` fixtures already use `.md` (already updated in Phase 30)
3. `tests/reinstall/test_reinstall_cli.py`: `test_gen_path_not_triggered_by_reinstall` asserts `glob("mac-software-list-*.txt")` → update to `*.md` (or remove the assertion since the reinstall path never writes catalogs)

### Anti-Patterns to Avoid

- **Splitting table rows on bare `|`:** A naive `row.split("|")` breaks for escaped pipes (`\|`). Always split on ` | ` (space-pipe-space) after stripping the leading `| ` and trailing ` |`. [VERIFIED: confirmed with adversarial test cases]
- **Unescaping cell values without stripping first:** The empty cell renders as `' '` (one space). After `split(" | ")`, the cell value is `' '`. Strip before unescaping to map empty cells to `None` correctly.
- **Importing PyYAML for frontmatter:** Not available in the venv; not needed — the parser reads frontmatter as opaque lines (validate fences, skip content).
- **Producing `degraded=True` from `(none found)` in the markdown parser:** Neither possible nor necessary. The emitter already skipped the distinction; the markdown format has no degradation lines. Map `(none found)` to `items=[], degraded=False`.
- **Adding a leading empty "Installed Mac Software List" ParsedSection:** The markdown parser reads the H1 title as a plain line, not a `##` section. No phantom leading section is produced. This differs from the legacy `parse_catalog` (WR-05 in its docstring), but the emitter already skips empty non-degraded sections via `_should_skip()`.
- **Silently falling back on a structurally invalid file:** RIN-02 requires a refused `.txt` file to fail loudly with the convert directive. No silent empty ParsedCatalog on format errors.
- **Detecting separator rows by `"---"` content check:** The separator row is `| --- | --- | --- |`. Do NOT treat this as a frontmatter closing fence. Distinguish separator rows from frontmatter fences by their leading `|` character. Or, more robustly: skip any row that matches `| --- |` exactly as a table separator row before applying `_parse_markdown_row`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Column detection in table rows | Regex over the whole row | `row[2:-2].split(" | ")` after confirming row structure | The emitter's format is fixed: cells are always surrounded by `" | "` separators; regex over escaped content is more complex and not needed |
| YAML frontmatter parsing | Full YAML parser | Validate `---` fences and skip content | Only need to know frontmatter is present; no key extraction required |
| New escape/unescape logic | Independent implementation | Exact inverse of `_escape_cell` from `catalog/markdown.py` | Cell escaping is already defined by the emitter; duplicating it risks drift |
| New dataclasses | Custom data structures | `ParsedItem`, `ParsedSection`, `ParsedCatalog` from existing `parser.py` | Zero emitter changes needed; round-trip contract holds via shared types |

---

## Runtime State Inventory

Step 2.2: SKIPPED — this is a greenfield function addition (no rename, refactor, or migration). No external service state, no stored data mutations, no OS-registered state, no secrets.

---

## Common Pitfalls

### Pitfall 1: Table Separator Row Mistaken for Table Data

**What goes wrong:** The table separator row `| --- | --- | --- |` starts with `| ` and ends with ` |`. A generic "parse any row" check will try to parse it as a data row and produce a `ParsedItem(name='---', version=None, id=None)`.

**Why it happens:** The row structure check `row.startswith("| ") and row.endswith(" |")` is satisfied by both header rows and separator rows.

**How to avoid:** Skip the row explicitly: check if the row is `"| Name | Version | ID |"` (header) or `"| --- | --- | --- |"` (separator) before calling `_parse_markdown_row`. Or more robustly: check if the inner content after `row[2:-2].split(" | ")` yields `['---', '---', '---']` → skip.

**Warning signs:** `ParsedItem(name='---', ...)` or `ParsedItem(name='Name', ...)` appearing in sections.

### Pitfall 2: Frontmatter Closing Fence Ambiguity with Table Separator

**What goes wrong:** A table row containing `---` (the separator row `| --- | --- | --- |`) could be confused with the frontmatter closing `---` if the state machine is not careful.

**Why it happens:** Both are three dashes. The frontmatter closing fence is `---` on its own line; the separator row starts with `|`.

**How to avoid:** The frontmatter scanner only looks for lines that are EXACTLY `---` (nothing else). The separator row is `| --- | --- | --- |` — it starts with `|`, not `---`, and is therefore never confused. This pitfall is a non-issue if the frontmatter scanner uses `line == "---"` (exact match, not substring).

### Pitfall 3: `split(" | ")` on a Row Produces the Wrong Number of Columns

**What goes wrong:** If the row has a cell value containing a literal ` | ` (space-pipe-space), splitting produces 4+ columns instead of 3. The emitter's `_escape_cell` converts all bare `|` to `\|`, so ` | ` in a cell value becomes ` \| ` — this can NEVER appear as ` | ` (space-pipe-space) in the rendered row. But a hand-edited or corrupted catalog could produce this.

**Why it happens:** Only in hand-edited or corrupted catalogs, not in emitter output.

**How to avoid:** After `split(" | ")`, check `len(cols) != 3`. If so, fall back to a name-only `ParsedItem` with `raw_line=row` preserved. This upholds the "lenient at item level" strictness rule.

**Warning signs:** `len(cols)` assertions failing in tests; `ParsedItem` with concatenated name values.

### Pitfall 4: `test_reinstall_cli.py` and `test_picker_and_reinstall_cli.py` Use `.txt` Fixtures

**What goes wrong:** After Phase 31, `run_reinstall` calls `parse_markdown_catalog` which refuses `.txt` files. Any test that supplies a `.txt` fixture catalog to `run_reinstall` will fail with `SystemExit` before writing `reinstall.sh`.

**Why it happens:** The existing test fixtures predate the markdown format change.

**How to avoid:** Update `_MINIMAL_CATALOG` (and the `fixture_catalog` fixtures) to valid markdown content with `.md` extension. A minimal catalog needs the full `---` frontmatter, `# title`, and at least one `## section` with a valid table.

**Warning signs:** `test_from_path_writes_reinstall_sh` fails with `SystemExit` or `SystemExit.code != 0`.

### Pitfall 5: `test_reinstall_cli.py::test_gen_path_not_triggered_by_reinstall` Asserts on `.txt` Glob

**What goes wrong:** The test at line 155 asserts `list(output_dir.glob("mac-software-list-*.txt"))` is empty. After Phase 30 changed catalog generation to `.md`, the assertion may already pass, but the intent is "no catalog written at all". The assertion should be `*.md` (or verify `reinstall.sh` exists without checking catalog extension).

**Why it happens:** The test was written for the `.txt` era.

**How to avoid:** Update the assertion glob to `mac-software-list-*.md` to match the new format.

### Pitfall 6: `raw_line` Must Be the Table Row String, Not the Reconstructed `emit_item` Form

**What goes wrong:** If `raw_line` is set to a reconstructed `emit_item`-style string (e.g., `"Final Cut Pro (10.7.1) [424389933]"`) instead of the actual source table row (`"| Final Cut Pro | 10.7.1 | 424389933 |"`), the round-trip contract test breaks if it compares `raw_line` values.

**Why it happens:** Developers might think `raw_line` should be the "logical" item format.

**How to avoid:** Always set `raw_line=row` where `row` is the original table row string read from the file. The contract test should NOT compare `raw_line` values — the round-trip contract is sections + items (name/version/id), not raw source lines.

### Pitfall 7: Mypy Strict Mode on `path.suffix` vs `str`

**What goes wrong:** `path.suffix` returns `str`, but if `path` is passed as `str` instead of `Path`, `.suffix` is not available.

**Why it happens:** The function signature accepts `Path` but callers might pass `str`.

**How to avoid:** Mirror `parse_catalog`'s pattern exactly: `path = Path(path)` at the top of `parse_markdown_catalog` before any `.suffix` or `.read_text` call. This makes the function accept both `str` and `Path` inputs.

---

## Code Examples

### Complete `parse_markdown_catalog` Design (verified round-trip)

```python
# Source: derived from catalog/markdown.py emitter output (verified 2026-06-18)
def parse_markdown_catalog(path: Path) -> ParsedCatalog:
    """Parse a .md catalog file into ParsedCatalog. Raises ValueError for non-markdown input.

    Inverts render_markdown_catalog() from catalog/markdown.py. Reads the YAML
    frontmatter fences (validate + skip), iterates ## section headings, and
    converts | Name | Version | ID | table rows into ParsedItems.

    Raises:
        ValueError: If path does not have .md extension (extension check), or
                    if the file lacks valid ---/--- YAML frontmatter fences
                    (content-sniff check for renamed legacy catalogs).
        OSError: If the file cannot be read (propagated from Path.read_text).
    """
    path = Path(path)
    if path.suffix != ".md":
        raise ValueError(
            f"{path} is not a markdown catalog (.md extension required). "
            f"Convert it first with: maccat convert --from {path}"
        )
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    if not lines or lines[0] != "---":
        raise ValueError(
            f"{path} is missing valid YAML frontmatter (no opening '---' fence). "
            f"It may be a legacy .txt catalog renamed to .md. "
            f"Convert it first with: maccat convert --from {path}"
        )
    # Find the closing ---
    fm_close = -1
    for i, line in enumerate(lines[1:], 1):
        if line == "---":
            fm_close = i
            break
    if fm_close == -1:
        raise ValueError(
            f"{path}: frontmatter block is not closed with '---'. "
            f"Convert it first with: maccat convert --from {path}"
        )

    catalog = ParsedCatalog(path=str(path))
    current_section: ParsedSection | None = None

    for line in lines[fm_close + 1:]:
        if line.startswith("## "):
            if current_section is not None:
                catalog.sections.append(current_section)
            current_section = ParsedSection(title=line[3:])
        elif line == "(none found)":
            pass  # current section stays items=[], degraded=False
        elif line.startswith("| ") and line.endswith(" |"):
            # Skip header and separator rows
            if line in ("| Name | Version | ID |", "| --- | --- | --- |"):
                continue
            if current_section is not None:
                item = _parse_markdown_row(line)
                if item is not None:
                    current_section.items.append(item)
        # blank lines, H1 title, other lines: skip

    if current_section is not None:
        catalog.sections.append(current_section)

    return catalog
```

### `_parse_markdown_row` with Fallback (verified round-trip)

```python
# Source: derived from catalog/markdown.py _escape_cell and _render_table (verified 2026-06-18)
def _unescape_cell(value: str) -> str:
    """Inverse of _escape_cell. Strip surrounding whitespace, then unescape \\| and \\\\."""
    s = value.strip()
    # Unescape in either order — both are correct for this escape scheme.
    # Convention: pipe first, then backslash (mirrors escape: backslash first, then pipe).
    return s.replace("\\|", "|").replace("\\\\", "\\")


def _parse_markdown_row(row: str) -> ParsedItem | None:
    """Parse '| name | ver | id |' into ParsedItem. Name-only fallback on bad structure."""
    # row is confirmed to start with '| ' and end with ' |'
    inner = row[2:-2]
    cols = inner.split(" | ")
    if len(cols) != 3:
        # Structural mismatch: name-only fallback, raw_line preserved
        name = _unescape_cell(inner)
        return ParsedItem(name=name or row, version=None, id=None, raw_line=row)
    name = _unescape_cell(cols[0])
    version = _unescape_cell(cols[1]) or None  # '' from empty cell → None
    id_ = _unescape_cell(cols[2]) or None
    if not name:
        # Completely empty name: name-only fallback (lenient at item level)
        return ParsedItem(name=row, version=None, id=None, raw_line=row)
    return ParsedItem(name=name, version=version, id=id_, raw_line=row)
```

### Round-Trip Contract Test Structure

```python
# Source: derived from test_parser_contract.py patterns (verified 2026-06-18)
# New class to add to tests/reinstall/test_parser_contract.py

from maccat.catalog.markdown import render_markdown_catalog
from maccat.collectors.base import Section

class TestMarkdownRoundTrip:
    """RIN-01: render_markdown_catalog → parse_markdown_catalog preserves sections+items."""

    @pytest.fixture()
    def rendered_catalog(self, tmp_path: Path) -> tuple[list[Section], Path]:
        sections = [
            Section("Homebrew Packages", ["git (2.44.0)", "node (18.0.0)"], raw=True),
            Section("App Store Applications", ["Final Cut Pro (10.7.1) [424389933]"], raw=False),
            Section("Setapp Applications", [], raw=False),
            Section("VS Code Extensions", ["ms-python.python (2024.1.1) [ms-python.python]"], raw=False),
        ]
        content = render_markdown_catalog(
            sections,
            computer="TestMac",
            hostname="test.local",
            generated="2026-06-18T12:34:56",
            maccat_version="2.1.0",
        )
        p = tmp_path / "mac-software-list-[TestMac]-20260618123456.md"
        p.write_text(content, encoding="utf-8")
        return sections, p

    def test_section_titles_preserved(self, rendered_catalog):
        sections, path = rendered_catalog
        from maccat.reinstall.parser import parse_markdown_catalog
        result = parse_markdown_catalog(path)
        assert [s.title for s in result.sections] == [s.title for s in sections]

    def test_item_names_preserved(self, rendered_catalog):
        ...  # assert item names for non-empty sections

    def test_pipe_in_name_round_trips(self, tmp_path):
        # Adversarial: pipe in item name
        ...

    def test_backslash_in_name_round_trips(self, tmp_path):
        # Adversarial: backslash in item name
        ...

    def test_empty_section_parses_to_empty_items(self, rendered_catalog):
        sections, path = rendered_catalog
        from maccat.reinstall.parser import parse_markdown_catalog
        result = parse_markdown_catalog(path)
        setapp_section = next(s for s in result.sections if "Setapp" in s.title)
        assert setapp_section.items == []


class TestMarkdownParserRefusal:
    """RIN-02: parse_markdown_catalog refuses non-.md and malformed-.md inputs."""

    def test_txt_extension_raises_value_error(self, tmp_path):
        f = tmp_path / "catalog.txt"
        f.write_text("content", encoding="utf-8")
        from maccat.reinstall.parser import parse_markdown_catalog
        with pytest.raises(ValueError, match="maccat convert --from"):
            parse_markdown_catalog(f)

    def test_md_without_frontmatter_raises_value_error(self, tmp_path):
        f = tmp_path / "catalog.md"
        f.write_text("# Installed Mac Software List\n\n## Homebrew\n", encoding="utf-8")
        from maccat.reinstall.parser import parse_markdown_catalog
        with pytest.raises(ValueError, match="maccat convert --from"):
            parse_markdown_catalog(f)

    def test_run_reinstall_exits_with_error_on_txt(self, tmp_path, monkeypatch):
        f = tmp_path / "mac-software-list-[T]-20260618120000.txt"
        f.write_text("content", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        import argparse, sys
        args = argparse.Namespace(from_path=str(f), computer=None, rename=False)
        from maccat.reinstall.cli import run_reinstall
        with pytest.raises(SystemExit) as exc:
            run_reinstall(args)
        assert exc.value.code != 0
        assert "convert" in str(exc.value).lower() or "convert" in str(exc.value.code)
```

### Minimal `.md` Fixture Catalog for Tests

```python
# Source: direct output of render_markdown_catalog (verified 2026-06-18)
_MINIMAL_MD_CATALOG = (
    '---\n'
    'computer: "TestMac"\n'
    'hostname: "test-mac.local"\n'
    'generated: "2026-06-18T12:34:56"\n'
    'maccat_version: "2.1.0"\n'
    '---\n'
    '# Installed Mac Software List\n'
    '\n'
    '## Homebrew Packages\n'
    '| Name | Version | ID |\n'
    '| --- | --- | --- |\n'
    '| wget | 1.21.3 |   |\n'
    '\n'
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `run_reinstall` calls `parse_catalog` (plain-text) | `run_reinstall` calls `parse_markdown_catalog` (markdown) | Phase 31 | Legacy `.txt` files can no longer be fed to `maccat reinstall` directly |
| Round-trip contract: `emit_item → _parse_item_line` | Round-trip contract: `render_markdown_catalog → parse_markdown_catalog` | Phase 31 | New contract re-locks at the file level, not just the item-line level |
| Reinstall accepts `.txt` files silently | Reinstall refuses `.txt` (and malformed `.md`) with a convert directive | Phase 31 | Breaking change; convert command (Phase 32) is the upgrade path |

**Preserved:**
- `parse_catalog` (legacy plain-text parser): remains in `parser.py` unchanged, importable for Phase 32 convert.
- `ParsedItem`, `ParsedSection`, `ParsedCatalog` dataclasses: unchanged; both parsers produce the same types.
- `emit_reinstall_script` in `emitter.py`: unchanged; consumes `ParsedCatalog` regardless of which parser produced it.

---

## File Change Inventory

| File | Change Type | What Changes |
|------|-------------|--------------|
| `src/maccat/reinstall/parser.py` | Addition (no deletions) | Add `_unescape_cell()`, `_parse_markdown_row()`, `parse_markdown_catalog()`; keep all existing code |
| `src/maccat/reinstall/cli.py` | Minor update | Replace `parse_catalog` import+call with `parse_markdown_catalog`; expand `except OSError` to `except (OSError, ValueError)` |
| `tests/reinstall/test_parser_contract.py` | Addition | Add `TestMarkdownRoundTrip` and `TestMarkdownParserRefusal` classes |
| `tests/reinstall/test_reinstall_cli.py` | Fixture update | `_MINIMAL_CATALOG` → markdown content; `fixture_catalog` → `.md` extension; `test_gen_path_not_triggered_by_reinstall` glob update |
| `tests/reinstall/test_picker_and_reinstall_cli.py` | Fixture update | `fixture_catalog` content → markdown; filename → `.md`; `TestRunReinstall.fixture_catalog` update |

**Files NOT changed:**
- `src/maccat/catalog/markdown.py` — emitter is locked (Phase 30)
- `src/maccat/reinstall/emitter.py` — unchanged; consumes `ParsedCatalog`
- `src/maccat/reinstall/picker.py` — already globs `.md` (Phase 30 fix)
- All collectors, `cli.py` generate path, `naming.py`, `retention.py`, `identity.py` — out of scope

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already installed in venv) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `./venv/bin/pytest tests/reinstall/ -x -q` |
| Full suite command | `./venv/bin/pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RIN-01 | `parse_markdown_catalog` produces correct `ParsedCatalog` from emitter output | unit + integration | `./venv/bin/pytest tests/reinstall/test_parser_contract.py -x -q` | ❌ Wave 0 (new class) |
| RIN-01 | Round-trip: emit → parse → sections+items match across all item shapes | contract test | `./venv/bin/pytest tests/reinstall/test_parser_contract.py::TestMarkdownRoundTrip -x` | ❌ Wave 0 |
| RIN-01 | Pipe-in-cell, backslash-in-cell, empty cells all round-trip correctly | unit | `./venv/bin/pytest tests/reinstall/test_parser_contract.py::TestMarkdownRoundTrip -x` | ❌ Wave 0 |
| RIN-02 | `.txt` path raises `ValueError` with convert directive message | unit | `./venv/bin/pytest tests/reinstall/test_parser_contract.py::TestMarkdownParserRefusal -x` | ❌ Wave 0 |
| RIN-02 | `.md` without frontmatter raises `ValueError` with convert directive message | unit | `./venv/bin/pytest tests/reinstall/test_parser_contract.py::TestMarkdownParserRefusal -x` | ❌ Wave 0 |
| RIN-02 | `maccat reinstall --from old.txt` exits non-zero with ERROR message | integration | `./venv/bin/pytest tests/reinstall/test_reinstall_cli.py -x` | ⚠️ Exists (fixture needs update) |

### Sampling Rate

- **Per task commit:** `./venv/bin/pytest tests/reinstall/ -x -q`
- **Per wave merge:** `./venv/bin/pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/reinstall/test_parser_contract.py::TestMarkdownRoundTrip` — covers RIN-01
- [ ] `tests/reinstall/test_parser_contract.py::TestMarkdownParserRefusal` — covers RIN-02
- [ ] Update `_MINIMAL_CATALOG` in `test_reinstall_cli.py` and `test_picker_and_reinstall_cli.py` to markdown format

---

## Environment Availability

Step 2.6: SKIPPED — this phase is a code-only change. No new external tools, services, CLIs, databases, or package managers are introduced. All subprocess infrastructure (`pytest`, `ruff`, `mypy`) is already verified available.

---

## Security Domain

Security enforcement is enabled (no explicit `false` in config). However, this phase has no user-facing inputs, no network operations, no authentication, and no secret handling. The markdown parser reads files from disk via `Path.read_text` (existing pattern). The only security-relevant consideration is shell injection, which is already handled by `emitter.py`'s `quote_for_script()` gate — the markdown parser is upstream of the emitter and has no shell-command responsibility.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V5 Input Validation | Partial | `parse_markdown_catalog` validates frontmatter structure (format check, not trust boundary) |
| V6 Cryptography | No | — |

No new threat patterns introduced. The `ValueError` → `sys.exit` conversion in `cli.py` ensures malformed inputs produce a clean error rather than a traceback.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ValueError` from `parse_markdown_catalog` is the right error signal (vs `sys.exit` from parser) | Pattern 5 | Low — either approach works; `ValueError` is cleaner for testability; cli.py needs a one-line change either way |
| A2 | `raw_line` should be the table row string (`"| name | ver | id |"`), not a reconstructed `emit_item` form | Pattern 2 | Low — `emitter.py` does not use `raw_line` at all; the contract test does not compare `raw_line` |
| A3 | `(none found)` in markdown → `items=[], degraded=False` (not `degraded=True`) | Pattern 4 | Low — `emitter._should_skip()` handles both `degraded=True` and `len(items)==0` identically; behavioral impact is zero |

**Non-assumed claims:** All table parsing, unescape order, column separator safety, and emitter format claims are `[VERIFIED]` by direct Python testing against the actual `catalog/markdown.py` source.

---

## Open Questions

None — all technical questions resolved during research.

---

## Sources

### Primary (HIGH confidence)
- Direct inspection of `src/maccat/catalog/markdown.py` — emitter format contract, `_escape_cell` implementation, `_render_table` format string, `(none found)` sentinel [VERIFIED: file read 2026-06-18]
- Direct inspection of `src/maccat/reinstall/parser.py` — `ParsedItem`, `ParsedSection`, `ParsedCatalog` dataclasses, `parse_catalog` state machine, `ITEM_RE` [VERIFIED: file read 2026-06-18]
- Direct inspection of `src/maccat/reinstall/cli.py` — `run_reinstall` step 2, `OSError` catch pattern, PKG-03 lazy import [VERIFIED: file read 2026-06-18]
- Direct inspection of `src/maccat/reinstall/emitter.py` — `raw_line` not used; `_should_skip()` logic [VERIFIED: file read 2026-06-18]
- Direct inspection of `src/maccat/reinstall/picker.py` — `.md` glob already in place, `sys.exit` error convention [VERIFIED: file read 2026-06-18]
- Direct Python testing — unescape order correctness (exhaustive over all 3-char combinations of `{a, \, |}`), table row splitting, empty cell mapping, round-trip for all adversarial cell values [VERIFIED: 2026-06-18]
- `tests/reinstall/test_parser_contract.py` — existing contract test structure, `ROUND_TRIP_CASES`, `TestParseCatalog` patterns [VERIFIED: file read 2026-06-18]
- `tests/reinstall/test_reinstall_cli.py` and `test_picker_and_reinstall_cli.py` — fixture formats, `_MINIMAL_CATALOG` content, fixture update requirements [VERIFIED: file read 2026-06-18]

### Secondary (MEDIUM confidence)
- None required — all claims grounded in codebase source inspection and direct Python testing.

### Tertiary (LOW confidence)
- None.

---

## Metadata

**Confidence breakdown:**
- Table row parsing algorithm: HIGH — exhaustively verified via Python testing
- Unescape order: HIGH — mathematically proven + exhaustive test
- Standard stack: HIGH — stdlib-only confirmed, no new deps
- File change inventory: HIGH — all affected files read and change sites identified
- Test fixture update requirements: HIGH — all existing test files read
- Error handling design (ValueError vs sys.exit): MEDIUM — recommended pattern is `ValueError`; either approach works [A1]

**Research date:** 2026-06-18
**Valid until:** Stable — grounded in current codebase snapshot. Valid until Phase 30 emitter changes (which would break the round-trip contract anyway and trigger a Phase 31 update).
