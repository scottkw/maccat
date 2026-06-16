# Phase 2: Editor Collectors - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds two new plain-text catalog sections to `update-list.sh` — **"VS Code Extensions"**
and **"Cursor Extensions"** — each listing installed editor extensions as
`displayName (version) [id]`, routed through the Phase 1 helpers (`json_get`, `emit_item`,
`flush_section`). It covers VSC-01 and CUR-01 only. It does NOT wire the collectors into
`generate_catalog` (that is Phase 5) — the collector functions are defined and self-testable
but inert in the main flow until integration. No browser or AI-CLI work here.

NOTE: the ROADMAP "**UI hint**: yes" is a false positive from a keyword grep — this phase
produces plain-text catalog sections, not a UI. No UI-SPEC is needed.
</domain>

<decisions>
## Implementation Decisions

### Name / ID Strategy (USER CHOSE higher-fidelity displayName resolution)
- **Resolve the human-readable `displayName`** for each extension from its on-disk
  `package.json`, rather than using the bare extension ID. Output line is
  `displayName (version) [id]`.
- When `displayName` is an nls placeholder of the form `%key%`, resolve it via
  `package.nls.json` (and locale variants like `package.nls.<locale>.json` if present,
  else the base `package.nls.json`) in the same extension directory — analogous to the
  Chrome `__MSG_` resolution already built in Phase 1.
- **Fallback:** when no `displayName` exists, or the `%key%` cannot be resolved, fall back
  to the extension ID as the name (so `emit_item`'s dedup-suppression yields `id (version)`).
  Never emit a blank name and never leak a raw `%key%` placeholder into output.
- `id` = the extension identifier (e.g. `ms-python.python`); `version` = the extension version.
- This resolution requires reading each extension's on-disk `package.json` regardless of
  whether the CLI or the file path was used to enumerate extensions (the CLI only yields
  `id@version`, not a display name). See Source Preference below + research flag.

### Source Preference & Fallback
- **Prefer the CLI** (`code --list-extensions --show-versions`, `cursor --list-extensions
  --show-versions`) when the binary is on PATH (`command -v`); otherwise parse
  `extensions.json`.
- CLI output is `id@version` — split on the LAST `@` to separate id and version.
- If the CLI is present but errors or returns empty, fall back to `extensions.json`.
- extensions.json paths: `~/.vscode/extensions/extensions.json` and
  `~/.cursor/extensions/extensions.json`. Each entry has `.identifier.id`, `.version`, and
  `.relativeLocation` (the per-extension directory under `~/.vscode/extensions/` resp.
  `~/.cursor/extensions/`) — `.relativeLocation` is the reliable map to the extension's
  `package.json` for displayName resolution.
- Built-in/system extensions are excluded (neither the CLI list nor the user
  `extensions.json` enumerates them).

### Section Structure & Degradation
- Two separate sections with headers `VS Code Extensions` and `Cursor Extensions`.
- When an editor has neither a CLI nor an `extensions.json`, still write the section and let
  `flush_section` emit its `(none found)` line; the run continues (FMT-02 graceful degradation).
- Every item is routed through `emit_item` → `flush_section` (`LC_ALL=C sort -f -u`) so output
  is deterministic and stably sorted (success criterion 4).
- Malformed/unparseable `extensions.json` → warn-and-continue with an empty section, never abort.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phase 1)
- `json_get <file> <key>` — jq→plutil→grep scalar reader with nested dotted keys; returns
  empty on miss; empty-key guarded (no root dump). Use to read `.version`, `.displayName`,
  and nls keys.
- `emit_item <name> <version> <id>` — uniform FMT-01 line builder with dedup-suppression and
  full degradation handling.
- `flush_section` — buffers `_section_lines`, flushes `LC_ALL=C sort -f -u`, writes
  `(none found)` when empty, resets the buffer. Collectors must `_section_lines=()` at their top.
- `write_section "$title"` (update-list.sh:254) — section header + separator.
- `chrome_ext_name` (Phase 1) — the nls/`__MSG_` resolution pattern is the closest analog for
  resolving `%key%` displayName placeholders; mirror its case/fallback discipline.

### Established Patterns
- `local`-scoped vars; `[[ ]]`; `command -v` probing; double-quoted expansions; `return` (not
  `exit`) on non-fatal; null-glob guard (`[[ -e "$f" ]] || continue`) in any glob loop;
  `2>/dev/null` for noisy stderr; append catalog data to `OUTPUT_FILE`, progress to stdout.

### Integration Points
- New collector functions (`collect_vscode_extensions`, `collect_cursor_extensions` or similar)
  are defined alongside the Phase 1 helpers; they are NOT called from `generate_catalog` yet.
</code_context>

<specifics>
## Specific Ideas

- **This machine's state (verification grounding):** Neither `code` nor `cursor` CLI is on
  PATH, so the `extensions.json` fallback is the path that will actually execute and be
  verified here. Both `~/.vscode/extensions/extensions.json` and
  `~/.cursor/extensions/extensions.json` exist. Sampled `displayName` values are plain strings
  (e.g. "Error Gutters", "Auto Rename Tag"), but the collector must still handle `%nls%`
  placeholder displayNames (common in Microsoft-published extensions) via `package.nls.json`.
- Determinism is testable: two consecutive collector runs on an unchanged machine must diff-empty.
</specifics>

<deferred>
## Deferred Ideas

- Wiring collectors into `generate_catalog` — deferred to Phase 5 (Integration & Verification Gates).
- Capturing extension enabled/disabled state — out of scope (v2, fragile to detect).
</deferred>

<research_flags>
## Open Questions for Research

1. **displayName nls resolution algorithm** — confirm: `package.json` `displayName` may be a
   literal string OR a `%key%` placeholder; resolve `%key%` via `package.nls.json` in the
   extension dir (and whether locale-specific `package.nls.<locale>.json` should be preferred).
   Provide the exact resolution + ID-fallback algorithm (mirror Phase 1 `chrome_ext_name`).
2. **CLI vs file reconciliation under displayName resolution** — since the CLI only yields
   `id@version` and displayName requires the on-disk `package.json`, determine the cleanest
   design: (a) use extensions.json as the metadata source and map id→relativeLocation→package.json,
   or (b) use CLI for enumeration but still locate each extension dir on disk for displayName.
   Recommend one. Confirm how to locate an extension's dir from a CLI-provided `id@version`
   (is it always `<extensions_dir>/<id>-<version>`? case sensitivity? target-platform suffixes
   like `-darwin-arm64`?).
3. **extensions.json schema stability** — confirm `.identifier.id`, `.version`,
   `.relativeLocation` across both VS Code and Cursor; note any version-key differences.
</research_flags>
