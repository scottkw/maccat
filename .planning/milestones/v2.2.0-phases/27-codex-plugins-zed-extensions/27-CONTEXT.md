# Phase 27: Codex Plugins + Zed Extensions - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add two independent new catalog sections (CDX-02, BRW-03):
1. **Codex Plugins** — a new section emitted by the existing `CodexCollector`, alongside its
   existing "Codex MCP Servers" section.
2. **Zed Extensions** — a new `ZedCollector` reading Zed's `index.json`.

This phase also establishes the **section-title uniqueness test** (asserts all collector
`_TITLE` constants are unique) that subsequent phases (28, 29) reuse. It validates the
"new section → reinstall manual checklist, zero reinstall changes" path early.

Out of boundary: the Chromium refactor + Edge/Brave (Phase 28) and Safari (Phase 29). No
changes to existing sections, the catalog/archive/git flow, or the reinstall pipeline.
</domain>

<decisions>
## Implementation Decisions

### Codex Plugins (CDX-02)
- **Structure:** extend the existing `src/maccat/collectors/codex.py::CodexCollector` to return
  TWO sections — `collect()` returns `[self._collect_mcp(), self._collect_plugins()]` — mirroring
  the multi-section pattern in `claude.py`. Do NOT create a new collector file.
- **Section title:** `"Codex Plugins"`, emitted immediately after `"Codex MCP Servers"` (the MCP
  section stays first; the plugins section is the second element of the returned list).
- **Entry format:** identity-only. `emit_item(name, "", id)` → `name [name@marketplace]` when a
  marketplace-qualified id exists, else plain `name`. Codex plugins have no version field, so the
  version is always empty (emit_item degrades accordingly). NEVER emit command/args/env/url.
- **Detection (preference order):** (1) try a `codex plugin list` CLI if the subcommand exists —
  guard on returncode/stderr like the existing MCP CLI path; (2) else text-grep `[plugins."…"]`
  section headers from `~/.codex/config.toml` (header lines ONLY — same safety discipline as the
  existing `_collect_via_toml` MCP path). If neither yields anything — including the currently
  installed Codex v0.46.0, which has no plugin system — the section emits `(none found)`. This is
  the expected output today, NOT an error and NOT a missing section.
- **FMT-03 secret-safety (CRITICAL):** never read plugin bundle files (e.g. `.mcp.json`) — they
  can contain API keys / tokens / env. Identity-only from CLI `.name`/id or the TOML header.
- **Write path:** `flush_section` (sorted, deduped, `(none found)` on empty) — same as the MCP section.

### Zed Extensions (BRW-03)
- **New collector:** `src/maccat/collectors/zed.py::ZedCollector`.
- **Source of truth:** `~/Library/Application Support/Zed/extensions/index.json` (canonical — has
  id, name, version per entry in one file; no per-extension manifest read, no `__MSG_`/locale
  resolution, no profile concept).
- **Entry format:** `name (version) [id]` via `emit_item` where id = the index.json entry's
  extension id (the key / `id` field), name = `name`, version = `version`.
- **Filter:** exclude entries marked `"dev": true` (locally-developed / in-development extensions).
- **Section title:** `"Zed Extensions"`. **Write path:** `flush_section` (sorted; `(none found)`
  when Zed isn't installed or `index.json` is absent/unreadable). Never-raising.

### Registry ordering
- Place `ZedCollector` adjacent to the other editor collectors in `collectors/__init__.py`
  `get_registry()` — **after `CursorCollector`** (Zed is an editor). The "Codex Plugins" section
  position is intrinsic (second section returned by `CodexCollector`, right after Codex MCP Servers).

### Section-title uniqueness test
- Add a test asserting the set of all collector `_TITLE` / `TITLE` constants (across every collector
  module, including the new "Codex Plugins" and "Zed Extensions") has no duplicates. Must pass for
  all 19 section titles (17 existing + 2 new). This guard is reused by Phases 28 and 29.

### Reinstall (no changes)
- Both new sections flow through `reinstall/parser.py` (title-agnostic) and `reinstall/emitter.py`
  (unknown title → `_manual_checklist_block`) as manual-checklist items automatically. ZERO changes
  to `parser.py` or `emitter.py`. A test should confirm the new sections appear in the reinstall
  manual checklist and not as auto-install commands.

### Claude's Discretion
- Exact `_collect_plugins()` / `ZedCollector` internals, the `index.json` schema-tolerance, the CLI
  command name probe, and test-fixture layout are at Claude's discretion within these decisions.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/maccat/collectors/codex.py::CodexCollector` — currently a 1-section MCP collector with a
  CLI-then-TOML-header-grep pattern and a strict "never read values, only headers" safety invariant
  (CAT-05). Extend it for plugins following the SAME discipline. Module-level constants
  (`_TITLE`, `_TOML_PATH`) are monkeypatched in tests.
- `src/maccat/collectors/claude.py` — the multi-section collector template (`collect()` returns
  multiple `Section`s: plugins / MCP / skills&agents).
- `src/maccat/catalog/format.py::emit_item(name, version, id_)` — produces `name [id]` when version
  is empty; `flush_section` sorts + dedups + emits `(none found)` on empty.
- `src/maccat/collectors/base.py` — `Collector` / `CollectorResult` / `Section(title, items, raw=False)`.
- `src/maccat/collectors/__init__.py::get_registry()` — ordered collector list (defines catalog output order).
- `src/maccat/helpers/json_io.py` — existing safe JSON read helper (reuse for Zed's index.json).

### Established Patterns
- `from __future__ import annotations` line 1; stdlib-only (`json`, `tomllib` (py3.11), `re`,
  `subprocess`, `plistlib`); ruff + mypy --strict clean; type hints; deterministic stable sort.
- Each collector `available()`-gates on tool/dir presence and degrades to `(none found)` (never raises).
- Tests under `tests/collectors/` mirror each collector; module-level constants monkeypatched.

### Integration Points
- `get_registry()` gains `ZedCollector` (after Cursor); `CodexCollector` now returns 2 sections.
- New `tests/collectors/test_zed.py`; extend `tests/collectors/test_codex.py` for the plugins section;
  add the section-title-uniqueness test (e.g. in tests/collectors/ or tests/test_registry).
</code_context>

<specifics>
## Specific Ideas

- Codex v0.46.0 (installed) has NO plugin system → the "Codex Plugins" section will legitimately
  show `(none found)` on this machine. The plugin system arrives in later Codex (`[plugins."name@marketplace"]`
  in config.toml; a `codex plugin list --json` CLI in ~v0.133+). Build the collector to populate
  when present and degrade cleanly when not — and assert the `(none found)` behavior in tests
  (mock the no-plugin and has-plugin cases).
- Adversarial/fixture tests should cover: Zed `index.json` absent, malformed, `dev:true` filtering,
  and missing version/id fields; Codex plugins present (mocked) vs absent.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Edge/Brave/Chromium refactor = Phase 28; Safari =
Phase 29; extension enabled/disabled state = deferred CHR-02/FF-02 family.)
</deferred>
