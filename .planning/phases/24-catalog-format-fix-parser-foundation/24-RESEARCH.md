# Phase 24: Catalog Format Fix + Parser Foundation — Research

**Researched:** 2026-06-16
**Domain:** Pure Python stdlib — shell script catalog parsing, regex-based line inversion, dataclass API design
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**MAS-01 — mas collector format change**
- Route mas lines through `emit_item(name, version, id_)` — do NOT duplicate the format string in the collector.
- De-paren the version: strip a single leading `(` / trailing `)` from `mas list` column 3 before passing to `emit_item` to avoid `AppName ((14.0)) [id]`.
- Parse multi-word app names robustly: split column 1 (numeric id) off the front, take the trailing `(version)` token as the version, and treat everything in between as the name.
- Keep the mas section `raw=True`.
- Update the existing mas collector tests in `tests/collectors/test_homebrew.py` with assertions reflecting the new `name (version) [id]` format.

**PARSE-01 — parser data model and API**
- `ParsedItem` fields: `name: str`, `version: str | None`, `id: str | None`, `raw_line: str`.
- Shape detection: a single **right-anchored** regex with optional groups — optional `[id]` at end, optional `(version)` before it, remainder = name.
- `(none found)` sentinel: exact string `  (none found)` (two leading spaces) yields an **empty item list** for that section — never a fake item.
- Collector degradation/fallback messages: detect known fallback lines and mark the section degraded with zero items — do not parse them as software items.

**Section identity and parser strictness**
- Section identification keyed on the header line (title between `------` separators). Store section title verbatim on `ParsedSection`.
- Unknown/new section titles: parse generically rather than error.
- Embedded parens/brackets in names (`App (Beta) (1.2.3) [id]`): right-anchored matching takes the LAST `(...)` as version and LAST `[...]` as id.
- Unparseable item line: fall back to a name-only `ParsedItem` (whole line as name) — never crash.

### Claude's Discretion

Exact regex syntax, dataclass module layout, state-machine internals, and test-fixture organization.

### Deferred Ideas (OUT OF SCOPE)

None — title→source mapping and the emitter itself are Phase 25. The CLI subcommand and picker are Phase 26.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MAS-01 | App Store section preserves numeric App Store ID, emits `AppName (version) [id]`; MasCollector + tests updated | `mas list` column layout confirmed; de-paren logic verified; emit_item routing pattern tested end-to-end |
| PARSE-01 | Parser reads catalog sectioned plain text into structured per-source items; round-trip contract test locks parser ↔ `catalog/format.py` coupling | emit_item four shapes enumerated; alternation regex tested; state machine verified against real catalog bytes; sentinel/degradation strings inventoried |
</phase_requirements>

---

## Summary

Phase 24 makes two changes that are foundational to the v2.1.0 reinstall feature. First, `MasCollector._parse_mas_output` is rewritten to extract all three columns from `mas list` output and route each entry through `emit_item(name, version, id_)`, preserving the numeric App Store ID in the catalog for the first time. Second, a new `src/maccat/reinstall/` subpackage provides `parse_catalog(path) -> ParsedCatalog`, a pure-stdlib state-machine parser that inverts the four line shapes `emit_item` can produce, handling every known sentinel and degradation string, and locked by a round-trip contract test.

All work is self-contained: no new runtime dependencies (stdlib only), no user-facing behavior, and `catalog/format.py:emit_item()` is not changed (the parser inverts its existing output exactly). The baseline is 426 passing tests; this phase adds new tests and updates three existing ones.

**Primary recommendation:** Implement `_parse_mas_output` as a three-column splitter (id = parts[0], version = strip-parens on parts[-1] when paren-wrapped, name = join of parts[1:-1]), then route through `emit_item`. Build the parser with the verified alternation regex and a three-state (SEEKING_TITLE / SEEKING_SEPARATOR / COLLECTING) state machine that matches the exact bytes `CatalogWriter` produces.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| mas list column extraction | `collectors/mas.py` | — | Collector owns its source-specific parsing; format layer owns serialization |
| Catalog line formatting | `catalog/format.py::emit_item` | — | Centralized format rule per FMT-01; the sole source of truth for line shapes |
| Catalog file writing | `catalog/writer.py::CatalogWriter` | — | Atomic write, byte-exact separator/section protocol |
| Catalog parsing / inversion | `reinstall/parser.py` | — | New subpackage; inverts emit_item output; consumed by Phase 25 emitter |
| Round-trip contract lock | `tests/reinstall/test_parser_contract.py` | — | Regression guard between format.py and parser.py |

---

## Standard Stack

### Core (all stdlib — no new dependencies)

| Module | Purpose | Why Standard |
|--------|---------|--------------|
| `dataclasses` | `ParsedItem`, `ParsedSection`, `ParsedCatalog` | Zero-overhead typed containers; `@dataclass` is idiomatic for this project (`collectors/base.py` already uses it) |
| `re` | Right-anchored alternation regex for item line inversion | `re.compile` with non-greedy name group and explicit alternation handles all six emit_item output shapes |
| `pathlib.Path` | File I/O for `parse_catalog(path)` | Consistent with rest of codebase |
| `typing` | `str \| None` annotations | Already in use; `from __future__ import annotations` deferred eval pattern |

No new packages. No install step needed.

---

## Package Legitimacy Audit

Not applicable — this phase installs zero external packages.

---

## Architecture Patterns

### Catalog File Structure (exact bytes from `CatalogWriter`)

`CatalogWriter.write_section(title)` emits: `\n{title}\n{'-'*36}\n`
`CatalogWriter.write_lines(lines)` emits: `{line}\n` per line

A real two-section catalog fragment:
```
\nHomebrew Packages\n------------------------------------\ngit (2.44.0)\nnode (18.0.0)\n\nApp Store Applications\n------------------------------------\nSafari (15.0) [1234567890]\n  ...
```

Rendered as line-by-line (the result of splitting on `\n`):
```
[0]  ''                              <- leading blank (write_section's \n prefix)
[1]  'Homebrew Packages'             <- section title
[2]  '------------------------------------'  <- 36 dashes (SEPARATOR constant)
[3]  'git (2.44.0)'                  <- item
[4]  'node (18.0.0)'                 <- item
[5]  ''                              <- blank line between sections
[6]  'App Store Applications'        <- next section title
[7]  '------------------------------------'
[8]  'Safari (15.0) [1234567890]'    <- item
...
```

**Key invariants verified from actual CatalogWriter output:**
- Separator is exactly 36 ASCII dashes (0x2d × 36). [VERIFIED: tests/test_writer.py + hex dump assertion]
- Exactly one blank line between sections — `"\n\n\n"` never appears. [VERIFIED: test_single_blank_line_between_sections]
- No blank line after the last item of the final section (file ends with `{last_item}\n`).
- The file may start with a blank line (the first `write_section` call's leading `\n`).

### Section-Boundary State Machine

Three states:

```
SEEKING_TITLE  ->  (non-blank, non-separator line) -> current_title = line -> SEEKING_SEPARATOR
SEEKING_TITLE  ->  (blank line) -> stay in SEEKING_TITLE

SEEKING_SEPARATOR  ->  (36-dash line) -> enter COLLECTING, reset items buffer
SEEKING_SEPARATOR  ->  (blank line) -> stay (tolerate blank between title candidates)
SEEKING_SEPARATOR  ->  (any other line) -> discard current_title, back to SEEKING_TITLE

COLLECTING  ->  (blank line) -> flush current section (title + items), back to SEEKING_TITLE
COLLECTING  ->  (non-blank line) -> append to items buffer
```

End-of-file handling: if state is COLLECTING and buffer is non-empty, flush the last section (file may not end with a blank line — the last `write_lines` call ends with `\n` but no additional blank).

[VERIFIED: state machine executed against actual CatalogWriter output above]

### emit_item Line Shapes and the Inversion Regex

All six shapes that `emit_item` can produce (from `src/maccat/catalog/format.py:16-43`):

```
name + version + id  ->  "Final Cut Pro (10.7.1) [424389933]"
name + version       ->  "Safari (15.0)"
name + id            ->  "Final Cut Pro [424389933]"
name only            ->  "Final Cut Pro"
id only (promoted)   ->  "424389933"              (id-as-name, no brackets)
id + version (promo) ->  "424389933 (10.7.1)"     (id-as-name, no brackets)
all empty            ->  None                     (never written to catalog)
```

[VERIFIED: executed against `catalog/format.py` in this session]

**The inversion regex** (three-branch alternation, right-anchored):

```python
ITEM_RE = re.compile(
    r'^'
    r'(?P<name>.+?)'                                        # non-greedy name
    r'(?:'
        r'\s+\((?P<version>[^)]+)\)\s+\[(?P<id>[^\]]+)\]'  # branch 1: version + id
    r'|'
        r'\s+\((?P<version2>[^)]+)\)'                       # branch 2: version only
    r'|'
        r'\s+\[(?P<id2>[^\]]+)\]'                           # branch 3: id only
    r')?'
    r'$'
)
```

Extraction: `version = m.group('version') or m.group('version2')`, `id_ = m.group('id') or m.group('id2')`.

**Round-trip contract verified** (all six shapes produce MATCH=True on re-emit):
```
'Final Cut Pro (10.7.1) [424389933]' -> name='Final Cut Pro' ver='10.7.1' id='424389933' [OK]
'Final Cut Pro (10.7.1)'             -> name='Final Cut Pro' ver='10.7.1' id=None        [OK]
'Final Cut Pro [424389933]'          -> name='Final Cut Pro' ver=None     id='424389933' [OK]
'Final Cut Pro'                      -> name='Final Cut Pro' ver=None     id=None        [OK]
'424389933'                          -> name='424389933'     ver=None     id=None        [OK]
'424389933 (10.7.1)'                 -> name='424389933'     ver='10.7.1' id=None        [OK]
```

[VERIFIED: executed in this session]

**Adversarial fixture behavior (embedded parens in names):**

```
'App (Beta) (1.2.3) [999]' -> name='App (Beta)' ver='1.2.3' id='999'   [round-trip: OK]
'App (Beta) [999]'         -> name='App'         ver='Beta'  id='999'   [round-trip: LOSSY]
'App (Beta)'               -> name='App'         ver='Beta'  id=None    [round-trip: LOSSY]
```

The lossy cases occur for names with embedded parens that have no version field (or no id field). This is the documented known limitation per CONTEXT.md: right-anchored matching takes the LAST `(...)` as version. The contract test must document this behavior explicitly rather than asserting perfect round-trip for those cases.

[VERIFIED: executed against actual regex in this session]

### mas list Output Format and New _parse_mas_output

Real `mas list` output format: `<numeric_id>  <MultiWordName> (<version>)`

```
424389933  Final Cut Pro (10.7.1)
409183694  Keynote (14.0)
1569813296 1Blocker- Ad Blocker & Privacy (8.0.2)
497799835  Xcode (16.0)
1295203466 Microsoft Remote Desktop (10.9.8)
```

[ASSUMED: confirmed from CONTEXT.md description and MasCollector docstring "Awk equivalence: mas list 2>/dev/null | awk '{print $2, $3}'"; real `mas` not invoked in this session because it's an optional macOS tool]

**Column parsing algorithm (verified against all edge cases):**

```python
def _parse_mas_output(self, stdout: str) -> list[str]:
    lines: list[str] = []
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue                            # skip blank/single-field lines
        id_ = parts[0]
        last = parts[-1]
        # Detect version: last part wrapped in parens AND at least 3 fields
        if len(parts) >= 3 and last.startswith("(") and last.endswith(")"):
            version = last[1:-1]               # strip single parens; avoids ((version))
            name = " ".join(parts[1:-1])       # middle fields are the multi-word name
        else:
            version = ""                       # no version in output; degrade gracefully
            name = " ".join(parts[1:])
        item = emit_item(name, version, id_)
        if item is not None:
            lines.append(item)
    return lines
```

Sample outputs verified:
```
emit_item('Final Cut Pro',             '10.7.1', '424389933') = 'Final Cut Pro (10.7.1) [424389933]'
emit_item('1Blocker- Ad Blocker & Privacy', '8.0.2', '1569813296') = '1Blocker- Ad Blocker & Privacy (8.0.2) [1569813296]'
emit_item('Xcode',                     '16.0',   '497799835') = 'Xcode (16.0) [497799835]'
emit_item('OnlyTwo',                   '',       '123')       = 'OnlyTwo [123]'   (2-field line)
```

[VERIFIED: executed against `catalog/format.py::emit_item` in this session]

### Sentinel and Degradation String Inventory

All known strings that the parser must recognize and NOT parse as software items:

**Sentinel (empty section result from `flush_section`):**
```python
NONE_FOUND_SENTINEL = "  (none found)"   # exactly two leading spaces
```
[VERIFIED: `catalog/format.py:flush_section` line 54, confirmed in `tests/test_format.py`]

**Collector degradation messages** (from `raw=True` Section fallback returns):
```python
DEGRADATION_LINES: frozenset[str] = frozenset({
    "Homebrew is not installed.",                        # collectors/homebrew.py
    "mas (Mac App Store CLI) is not installed.",         # collectors/mas.py
    "Install it with Homebrew: brew install mas",        # collectors/mas.py
    "Could not retrieve App Store list.",                # collectors/mas.py
    "Setapp is not installed or detected.",              # collectors/setapp.py
})
```
[VERIFIED: grep of all collector files in this session]

**Parser behavior:**
- Line == `NONE_FOUND_SENTINEL`: section has zero items, `degraded=False` (normal empty section).
- Line in `DEGRADATION_LINES`: section has zero items, `degraded=True`.
- All other non-blank lines in COLLECTING state: parse with `ITEM_RE`, fall back to name-only `ParsedItem` on no-match.

### Recommended Project Structure

New files this phase creates:

```
src/maccat/reinstall/
├── __init__.py           # exports: parse_catalog, ParsedCatalog, ParsedSection, ParsedItem
└── parser.py             # dataclasses + ITEM_RE + parse_catalog() implementation

tests/reinstall/
├── __init__.py
└── test_parser_contract.py   # round-trip contract tests
```

Modified files:
```
src/maccat/collectors/mas.py        # rewrite _parse_mas_output
tests/collectors/test_homebrew.py   # update 3 existing TestMasCollector tests + add new ones
```

### Dataclass Design

```python
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class ParsedItem:
    name: str
    version: str | None
    id: str | None
    raw_line: str

@dataclass
class ParsedSection:
    title: str           # verbatim section title from catalog
    items: list[ParsedItem] = field(default_factory=list)
    degraded: bool = False   # True if known degradation message was found

@dataclass
class ParsedCatalog:
    sections: list[ParsedSection] = field(default_factory=list)
    path: str = ""       # source file path as string (str, not Path, for serialization-friendliness)

def parse_catalog(path: Path) -> ParsedCatalog: ...
```

All dataclasses use `from __future__ import annotations` and are `mypy --strict` compatible.

### Anti-Patterns to Avoid

- **Importing `emit_item` into `parser.py`:** The parser is a consumer of `emit_item`'s output format, not a caller. Do not create a circular coupling. The regex is the sole contract between the two modules.
- **Using `.+` (greedy) for the name group:** Greedy matching pulls the version/id content into the name. Non-greedy `.+?` is required so the alternation branches at the end can consume the version and id.
- **Assuming last field of mas output is always a version:** When `mas list` returns a 2-field line (no version), the last field is the name, not `(version)`. Guard with `startswith("(") and endswith(")")`.
- **Parsing sentinel as a ParsedItem:** `  (none found)` is a section-level signal, not an installed item. Check for sentinel before attempting `ITEM_RE.match`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Catalog line formatting | Custom f-string in `_parse_mas_output` | `emit_item(name, version, id_)` from `catalog/format.py` | FMT-01 centralization; single source of truth for all four line shapes |
| Temp-file atomic write | Custom rename logic | `CatalogWriter` (already exists) | Already handles POSIX rename atomicity + cleanup on exception |
| Sort + dedup | Custom Python sort | `flush_section()` via `LC_ALL=C sort -f -u` subprocess | Byte-parity with zsh reference script; Python sort diverges on mixed-case |

---

## Common Pitfalls

### Pitfall 1: Double-parenthesized version in mas output

**What goes wrong:** `mas list` outputs `1234567890  Xcode (16.0)`. The old code emits `Xcode (16.0)` (treating `(16.0)` as the name). If the new code naively passes `(16.0)` as the version to `emit_item`, the result is `Xcode ((16.0)) [id]` — double parens.

**Why it happens:** `emit_item(name, version, id_)` wraps `version` in parens. If `version` is already paren-wrapped from `mas list` output, the parens are doubled.

**How to avoid:** Strip the outer parens before calling `emit_item`. Only strip if the token actually starts with `(` and ends with `)`:
```python
version = last[1:-1]   # NOT last.strip("()") — strip() removes ALL chars from both ends
```

**Warning signs:** `AppName ((version)) [id]` in catalog output; test assertions `['Safari ((15.0)) [id]']`.

### Pitfall 2: Single-word app names break the multi-word parser

**What goes wrong:** `mas list` line `497799835  Xcode (16.0)` has `parts = ['497799835', 'Xcode', '(16.0)']`. This works fine. But `123  X (1.0)` also works. The edge case is a 2-field line `456  Xcode` (no version). `parts[-1]` is `Xcode`, which does NOT start with `(`, so the version branch is skipped correctly.

**Why it happens:** Real `mas list` always emits 3+ fields, but defensive handling of 2-field lines is needed per the existing test `test_mas_two_field_line_emits_trailing_space` (which will be replaced by the new format).

**How to avoid:** Guard with `len(parts) >= 3 and last.startswith("(") and last.endswith(")")` before treating `last` as a version.

### Pitfall 3: Test assertions for test_mas_collect_parses_output still use old format

**What goes wrong:** The existing test at line 129 of `tests/collectors/test_homebrew.py` asserts:
```python
assert section.items == ["Safari (15.0)", "Xcode (14.0)"]
```
After MAS-01, the mock stdout is `"1234567890  Safari (15.0)\n9876543210  Xcode (14.0)"`, and the new assertions must be:
```python
assert section.items == ["Safari (15.0) [1234567890]", "Xcode (14.0) [9876543210]"]
```

**Why it happens:** The mock stdout uses numeric IDs that are now extracted. Forgetting to update the assertion causes an immediate test failure that looks like the code is wrong.

**Warning signs:** `AssertionError: ['Safari (15.0) [1234567890]', ...] != ['Safari (15.0)', ...]`

### Pitfall 4: test_mas_two_field_line_emits_trailing_space becomes obsolete

**What goes wrong:** `test_mas_two_field_line_emits_trailing_space` (line 167) tests awk byte-parity behavior (`"OnlyTwo "` with trailing space). This is now invalid — the new `_parse_mas_output` does NOT replicate awk; it calls `emit_item`. The test description and assertion must change.

**How to avoid:** Replace this test with a test that verifies 2-field input produces `emit_item(name='OnlyTwo', version='', id_='123') = 'OnlyTwo [123]'`.

### Pitfall 5: Parser state machine misses last section (file ends without blank line)

**What goes wrong:** The last section in the catalog file ends with `{last_item}\n` (no trailing blank line). If the state machine only flushes on blank-line transitions, the last section is silently dropped.

**How to avoid:** After the line loop, if `state == 'COLLECTING'` and `current_title is not None`, flush the buffer as the final section.

**Warning signs:** `ParsedCatalog.sections` has N-1 sections instead of N.

### Pitfall 6: Regex named group collision via alternation

**What goes wrong:** Using duplicate named groups like `(?P<version>...)` in two alternation branches causes `error: redefinition of group name 'version'` in Python's `re` module.

**How to avoid:** Use distinct group names across branches: `version` + `version2`, `id` + `id2`. Merge via `m.group('version') or m.group('version2')`.

---

## Code Examples

### New _parse_mas_output (MAS-01)

```python
# Source: inferred from catalog/format.py::emit_item + CONTEXT.md locked decision
def _parse_mas_output(self, stdout: str) -> list[str]:
    """Extract id, multi-word name, and version from mas list output.

    Real mas list format: '<id>  <MultiWordName> (<version>)'
    Column 1: numeric App Store ID
    Columns 2..N-1: multi-word app name (joined with spaces)
    Column N: version wrapped in parens -- strip before passing to emit_item

    Routes through emit_item(name, version, id_) for FMT-01 compliance.
    """
    from maccat.catalog.format import emit_item

    lines: list[str] = []
    for line in stdout.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        id_ = parts[0]
        last = parts[-1]
        if len(parts) >= 3 and last.startswith("(") and last.endswith(")"):
            version = last[1:-1]
            name = " ".join(parts[1:-1])
        else:
            version = ""
            name = " ".join(parts[1:])
        item = emit_item(name, version, id_)
        if item is not None:
            lines.append(item)
    return lines
```

### ParsedItem / ParsedSection / ParsedCatalog dataclasses

```python
# Source: CONTEXT.md locked decisions + dataclasses stdlib pattern from collectors/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ParsedItem:
    name: str
    version: str | None
    id: str | None       # noqa: A003 (shadows builtin; acceptable for domain clarity)
    raw_line: str

@dataclass
class ParsedSection:
    title: str
    items: list[ParsedItem] = field(default_factory=list)
    degraded: bool = False

@dataclass
class ParsedCatalog:
    sections: list[ParsedSection] = field(default_factory=list)
    path: str = ""
```

### ITEM_RE — the inversion regex

```python
# Source: verified against all six emit_item output shapes in this session
import re

ITEM_RE = re.compile(
    r"^"
    r"(?P<name>.+?)"                                            # non-greedy name
    r"(?:"
        r"\s+\((?P<version>[^)]+)\)\s+\[(?P<id>[^\]]+)\]"     # branch 1: version + id
    r"|"
        r"\s+\((?P<version2>[^)]+)\)"                          # branch 2: version only
    r"|"
        r"\s+\[(?P<id2>[^\]]+)\]"                              # branch 3: id only
    r")?"
    r"$"
)

def _parse_item_line(raw_line: str) -> ParsedItem:
    m = ITEM_RE.match(raw_line)
    if not m:
        return ParsedItem(name=raw_line, version=None, id=None, raw_line=raw_line)
    return ParsedItem(
        name=m.group("name"),
        version=m.group("version") or m.group("version2"),
        id=m.group("id") or m.group("id2"),
        raw_line=raw_line,
    )
```

### Round-trip contract test structure (test_parser_contract.py)

```python
# Source: success criteria + emit_item shapes verified in this session
import pytest
from maccat.catalog.format import emit_item
from maccat.reinstall.parser import ParsedItem, _parse_item_line  # internal helper

# The four canonical shapes + six degradation variants
ROUND_TRIP_CASES = [
    # (name, version, id_, expected_parsed_name, expected_parsed_version, expected_parsed_id)
    ("Final Cut Pro", "10.7.1", "424389933", "Final Cut Pro", "10.7.1", "424389933"),
    ("Safari",        "15.0",   "",          "Safari",        "15.0",   None),
    ("Final Cut Pro", "",       "424389933", "Final Cut Pro", None,     "424389933"),
    ("Final Cut Pro", "",       "",          "Final Cut Pro", None,     None),
    ("",              "",       "424389933", "424389933",     None,     None),   # id-promoted
    ("",              "15.0",   "424389933", "424389933",     "15.0",   None),   # id-promoted+version
]

@pytest.mark.parametrize("name,version,id_,exp_name,exp_ver,exp_id", ROUND_TRIP_CASES)
def test_round_trip(name, version, id_, exp_name, exp_ver, exp_id):
    emitted = emit_item(name, version, id_)
    assert emitted is not None
    item = _parse_item_line(emitted)
    assert item.name == exp_name
    assert item.version == exp_ver
    assert item.id == exp_id
    # Re-emit contract: parse(emit(x)) re-emits identically
    re_emitted = emit_item(item.name, item.version or "", item.id or "")
    assert re_emitted == emitted

# Adversarial fixtures
ADVERSARIAL_CASES = [
    # (raw_line, expected_name, expected_version, expected_id, round_trip_ok)
    ("App (Beta) (1.2.3) [999]", "App (Beta)", "1.2.3", "999",  True),   # inner parens in name
    ("App (Beta) [999]",         "App",        "Beta",  "999",  False),  # KNOWN LOSSY
    ("App (Beta)",               "App",        "Beta",  None,   False),  # KNOWN LOSSY
]

@pytest.mark.parametrize("raw_line,exp_name,exp_ver,exp_id,round_trip_ok", ADVERSARIAL_CASES)
def test_adversarial_fixtures(raw_line, exp_name, exp_ver, exp_id, round_trip_ok):
    item = _parse_item_line(raw_line)
    assert item.name == exp_name
    assert item.version == exp_ver
    assert item.id == exp_id
    if round_trip_ok:
        re_emitted = emit_item(item.name, item.version or "", item.id or "")
        assert re_emitted == raw_line
```

---

## Runtime State Inventory

Not applicable — this is a greenfield addition (new subpackage + collector change). No rename/refactor phase.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| mas entry formatting | `f"{name} ({version}) [{id_}]"` in `_parse_mas_output` | `emit_item(name, version, id_)` | FMT-01 centralization; handles all degradation cases including empty name/version/id |
| Atomic file write | Custom temp-file-and-rename | `CatalogWriter` | Already exists; handles POSIX atomicity and cleanup on exception |

**Key insight:** `emit_item` handles six degradation cases — including what happens when `name` is empty or `id_` is empty. Duplicating even a subset of that logic in `_parse_mas_output` creates drift risk.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `awk '{print $2, $3}'` equivalence (`parts[1] parts[2]`) | Three-column split: id, name (joined middle), version (de-parened last) | Phase 24 (MAS-01) | App Store ID is now preserved in catalog; multi-word names (e.g. "Final Cut Pro", "Microsoft Remote Desktop") are captured correctly |
| No catalog parser | `parse_catalog(path) -> ParsedCatalog` in `reinstall/parser.py` | Phase 24 (PARSE-01) | Enables Phase 25 emitter to produce reinstall scripts from catalog data |

**Deprecated/outdated:**
- `_parse_mas_output` current logic (`parts[1] parts[2]` with trailing-space awk parity): replaced by three-column algorithm. The awk-parity test `test_mas_two_field_line_emits_trailing_space` becomes invalid and must be replaced.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Real `mas list` output is always `<numeric_id>  <MultiWordName> (<version>)` — version is always paren-wrapped and is the last field | mas list Output Format section | If mas ever emits lines without the paren-version, the de-paren guard (`last.startswith("(")`) would degrade to a name-only emit, losing the version — acceptable degradation per FMT-01 |
| A2 | The catalog file always starts with a leading blank line (from the first `write_section` call) | Catalog File Structure | If a catalog header block (title, machine info) were prepended before the first `write_section`, the state machine would encounter those lines in SEEKING_TITLE state and misidentify them as section titles — but there is no such header in `CatalogWriter` (confirmed by writer.py) |

---

## Open Questions

1. **`parse_catalog` file encoding assumption**
   - What we know: `CatalogWriter` writes with `encoding="utf-8"` (writer.py line 43).
   - What's clear: `open(path, encoding="utf-8")` in the parser is correct.
   - Recommendation: Hard-code UTF-8 in `parse_catalog`; document the assumption.

2. **`tests/reinstall/__init__.py` needed?**
   - What we know: `tests/collectors/__init__.py` exists as an empty file; pytest discovers tests without it in some configs.
   - What's clear: The existing project has `__init__.py` in every `tests/` subdirectory.
   - Recommendation: Create it as an empty file for consistency.

---

## Environment Availability

Step 2.6: SKIPPED — this phase is purely code changes with no new external dependencies. The only tool probed by the new code is `mas` (already handled by MasCollector's `available()` guard).

---

## Validation Architecture

`nyquist_validation` is explicitly `false` in `.planning/config.json`. This section is omitted.

---

## Security Domain

No security-sensitive operations in this phase. The parser reads local files written by the same tool. No network I/O, no authentication, no user-supplied untrusted input, no secrets handling, no subprocess execution in the new code. ASVS categories V2/V3/V4/V6 are not applicable. V5 (input validation) applies trivially: the regex safely handles any input string (no ReDoS risk — `[^)]+` and `[^\]]+` are negated character classes with no catastrophic backtracking).

---

## Sources

### Primary (HIGH confidence)
- `src/maccat/catalog/format.py` — all six emit_item output shapes read directly from source and executed
- `src/maccat/catalog/writer.py` — exact byte protocol for section separators and blank-line boundaries
- `src/maccat/collectors/mas.py` — current _parse_mas_output logic and all three fallback Section returns
- `src/maccat/collectors/base.py` — Section/CollectorResult types
- `tests/collectors/test_homebrew.py` — existing TestMasCollector test assertions (three tests require update)
- `tests/test_format.py` — emit_item degradation test cases confirm the six shapes
- `tests/test_writer.py` — confirms 36-dash separator and blank-line invariants

### Secondary (MEDIUM confidence)
- `.planning/phases/24-catalog-format-fix-parser-foundation/24-CONTEXT.md` — locked implementation decisions
- `.planning/REQUIREMENTS.md` — MAS-01 and PARSE-01 requirement text

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- emit_item shapes: HIGH — read directly from source, executed in session
- Catalog file format: HIGH — executed CatalogWriter in session, checked test assertions
- Inversion regex: HIGH — tested against all six shapes + adversarial cases in session
- _parse_mas_output design: HIGH — tested against sample mas output including multi-word names
- Sentinel/degradation strings: HIGH — grep of all collector files; frozenset verified
- State machine: HIGH — executed against real catalog bytes in session
- mas list output format: MEDIUM (ASSUMED) — consistent with existing code docstring and CONTEXT.md but mas CLI not invoked live

**Research date:** 2026-06-16
**Valid until:** 2026-08-16 (stable stdlib domain; no external dependencies)
