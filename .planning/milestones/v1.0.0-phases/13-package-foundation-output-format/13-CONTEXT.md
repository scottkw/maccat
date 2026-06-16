# Phase 13: Package Foundation + Output Format - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Stand up a runnable, importable `src/maccat/` Python package skeleton (zero third-party
runtime deps, Python 3.11+ floor with a fail-fast version guard) plus the complete
output-format layer: the `CatalogWriter` (section headers, item lines, `------` separators),
`emit_item`/`flush_section` buffering with `LC_ALL=C sort -f -u` shell-out, the
`name (version) [id]` line format with FMT-01 degradation rules, and the Chrome `__MSG_…__`
/ VS Code `%nls%` placeholder-name resolution. This is the byte-verified foundation every
downstream collector (Phase 15) and parity test (Phase 17) builds on. No collectors, no
config, no git, no CLI in this phase.

Requirements: PKG-01, PKG-02, CAT-02, CAT-03, CAT-04, CAT-07.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion
All implementation choices are at Claude's discretion — this is a pure infrastructure /
output-format-layer phase with no user-facing behavior. The byte-parity requirement against
the untouched `update-list.sh` reference removes design freedom: every formatting,
sorting, and placeholder-resolution choice is dictated by matching the zsh output exactly
(verified by `xxd` at section boundaries). Use the ROADMAP success criteria, REQUIREMENTS
(PKG/CAT IDs), the zsh reference functions, and codebase conventions to guide decisions.

Key non-negotiables carried from requirements:
- Standard library only — no third-party runtime deps.
- Ordering MUST shell out to `LC_ALL=C sort -f -u` (and `sort -V` where the zsh uses it) —
  never Python `sorted()`.
- Package must run from any directory; never resolve the catalog repo from `__file__`.
- Sub-3.11 `python3` must print a clear, actionable error and exit — never hang on the
  macOS Command Line Tools install dialog.

</decisions>

<code_context>
## Existing Code Insights

### Reference Implementation (zsh — untouched parity source)
- `write_section` — `update-list.sh:1075` — emits the section header + `------` separator.
- `emit_item` — `update-list.sh:1243` — appends a formatted `name (version) [id]` line to
  the script-global `_section_lines` buffer (each collector resets `_section_lines=()` at top).
- `flush_section` — `update-list.sh:1290` — pipes the buffer through
  `printf "%s\n" ... | LC_ALL=C sort -f -u >> "$OUTPUT_FILE"`, then resets the buffer; the
  source of truth for sort + dedup behavior.
- `__MSG_…__` / `%nls%` placeholder resolution — `update-list.sh:1127-1217` — strips the
  `__MSG_`/`__` wrapper, looks up the key in the extension's `messages.json`, and falls back
  to ID/displayName; never emits a blank or raw placeholder name.

### Established Patterns (from .planning/codebase/)
- See `.planning/codebase/CONVENTIONS.md`, `STRUCTURE.md`, `STACK.md` (refreshed 2026-06-12)
  for naming and structure conventions to mirror.
- Each collector follows: check availability → buffer via emit_item → flush_section, with a
  fallback message when the source is absent (graceful degradation, CAT-06 — Phase 15).

### Integration Points
- `CatalogWriter` / `flush_section` are the seam every Phase 15 collector plugs into.
- Phase 17 golden-parity tests assert byte-identical section bodies against this layer.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond byte-parity — the zsh reference (`write_section`,
`emit_item`, `flush_section`, placeholder resolution) is the exact spec. Verify with `xxd`
at section boundaries and against `LC_ALL=C sort` output for mixed-case, non-ASCII, and
punctuation-containing names.

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase, scope stayed within the package foundation + output-format layer.

</deferred>
