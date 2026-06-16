# Phase 1: Shared Helpers Foundation - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers a reusable, dependency-free Zsh helper layer inside `update-list.sh`
that every later collector (editors, AI CLIs, browsers) calls. It owns four
responsibilities and nothing else:

1. **Read JSON** from config/manifest files (jq-preferred, plutil fallback).
2. **Resolve Chrome `__MSG_*` localized names** to human-readable strings.
3. **Emit a uniform catalog item line** (FMT-01).
4. **Produce stably-sorted, deterministic section output** (FMT-04).

No collector logic, no new sections wired into `generate_catalog` — only the shared
primitives those collectors will consume. Mirrors existing script conventions
(`local`-scoped vars, `[[ ]]` tests, `command -v` probing, append-to-`OUTPUT_FILE`
side effects, graceful degradation).
</domain>

<decisions>
## Implementation Decisions

### Item Line Format (FMT-01)
- All fields present: `name (version) [id]`.
- No version available: `name [id]` (degraded form per FMT-01).
- Name unresolvable (only ID known): use the ID as the name and suppress the duplicate
  bracket → bare `id (version)` / `id` (never `id [id]`).
- No stable ID (e.g. skills/agents): `name (version)` — omit the `[...]` brackets entirely.
- A single emit helper builds the line from (name, version, id) args, applying these
  degradation rules so every collector renders identically.

### Sort & Determinism (FMT-04)
- Sort key: by display name.
- Byte-stable: sort under `LC_ALL=C` so ordering is immune to locale drift between runs/machines.
- Case handling: case-insensitive fold (human-readable ordering).
- Dedupe: collapse identical duplicate lines within a section (`-u`) so re-runs stay clean.
- A sort helper buffers a section's emitted lines and flushes them sorted, guaranteeing
  two consecutive no-change runs produce an empty diff.

### JSON Reading (dependency-free)
- Parser strategy: prefer `jq` when present; fall back to a `plutil`-based extraction
  (both ship-or-probe gracefully, consistent with existing brew/mas optional-tool pattern).
- Malformed/missing JSON: warn-and-skip, return empty — never abort the section or run.
- Field access: support nested key paths (required for manifests and CLI configs).
- Return contract: echo the resolved value to stdout; empty string on miss (callers test
  for empty, matching shell idiom).

### Chrome Name Resolution (CHR-01)
- Resolve `__MSG_<key>__` names by reading `_locales/<default_locale>/messages.json` and
  using the key's `message` field.
- Locale selection: read manifest `default_locale`; fall back to `en` when absent.
- Failure fallback: when the name can't be resolved, fall back to the extension ID
  (per CHR-01) — never drop the extension.
- Message key lookup is case-insensitive (Chrome treats message keys case-insensitively).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `write_section "$title"` (update-list.sh:254) — emits a section header + separator to
  `$OUTPUT_FILE`. New helpers slot alongside it; collectors keep using it for headers.
- Global `OUTPUT_FILE` is the append target for all catalog data.
- Optional-tool probing pattern already established with `command -v brew` / `command -v mas`.

### Established Patterns
- `local`-scoped variables inside every function; no globals created inside functions.
- `[[ ]]` for all conditionals; `command -v` (not `which`) for tool detection.
- Quote all variable/path expansions; brace expansion for concatenation.
- Suppress noisy stderr with `2>/dev/null`; graceful warn-and-continue on any missing source.
- Catalog data appended via `>> "$OUTPUT_FILE"`; progress/status echoed to stdout.

### Integration Points
- Helpers are defined as standalone Zsh functions in `update-list.sh` (above
  `generate_catalog`), callable by the Phase 2–4 collectors and finally wired in Phase 5.
- No change to the archive/git flow or existing sections.
</code_context>

<specifics>
## Specific Ideas

- The emit helper and the sort/flush helper are the two FMT contracts the whole milestone
  hinges on — every collector must route through them so FMT-01 and FMT-04 hold globally.
- Determinism is testable: run twice with no machine changes → `git diff` on the section is empty.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>
