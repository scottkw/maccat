# Phase 29: Safari Extensions - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a new `SafariCollector` (BRW-04) that catalogs user-installed Safari extensions via
`pluginkit` + `plistlib`. New `src/maccat/collectors/safari.py`, registered LAST (after Firefox).
Final phase of v2.2.0.

Out of boundary: Safari content blockers (separate plugin point — deferred SAF-02), extension
enabled/disabled state (deferred), and any changes to existing sections or the reinstall pipeline.
</domain>

<decisions>
## Implementation Decisions

### pluginkit invocation + parse
- Run `pluginkit -mAvv -p com.apple.Safari.web-extension` (verified live; the legacy
  `com.apple.Safari.extension` point returns nothing on modern macOS). The `-p` filter excludes
  Apple's built-in extensions automatically.
- Parse the verbose output: extract each indented `Path = <…>.appex` line (regex, e.g.
  `^\s*Path\s*=\s*(.+\.appex)\s*$`) → the `.appex` bundle path. Read `<path>/Contents/Info.plist`.
- Live-verified output shape (for fixtures): a `   <bundle-id>(<version>)` header line followed by
  indented `Key = Value` lines (`Path`, `UUID`, `Timestamp`, `SDK`, `Parent Bundle`).

### Entry fields (name / version / id)
- **name** = `CFBundleDisplayName`; fallback to `CFBundleName` ONLY if it is not the generic binary
  name (`CFBundleName` is often `"safari"`); final fallback = `CFBundleIdentifier` (so name is never
  empty and never the bogus `"safari"`).
- **version** = reuse `helpers/plist_version.get_plist_version` (CFBundleShortVersionString →
  CFBundleVersion → "") — consistent with Setapp/web-apps; do NOT use the pluginkit parenthetical
  (it can be `(null)`).
- **id** = `CFBundleIdentifier`.
- Emit `emit_item(name, version, id)` → `name (version) [id]`, degrading per FMT-01.
- Reference example (test machine): `Bitwarden (2026.5.0) [com.bitwarden.desktop.safari]`.

### plist reads
- Reuse `get_plist_version(path)` for the version. Add a small Safari-specific helper/read for
  `CFBundleDisplayName` / `CFBundleName` / `CFBundleIdentifier` (a single `plistlib.load` returning
  the dict, with key precedence applied) — do NOT duplicate the version logic.

### Never-raising / graceful degradation
- `pluginkit` absent (no `/usr/bin/pluginkit`) or non-zero exit or empty output → empty section →
  `(none found)`. Wrap the subprocess in try/except OSError (mirror MasCollector/CodexCollector).
- Each extension's `Info.plist` read is wrapped in its OWN try/except — a single unreadable/malformed
  plist is skipped, never aborts the whole collection. `(none found)` when nothing resolves.

### Smoke test (SC #3 — mandatory before phase close)
- Unit tests parse a **captured fixture** of real `pluginkit -mAvv -p com.apple.Safari.web-extension`
  output (the Bitwarden block) — assert `_parse_pluginkit_output` extracts the tab/indented
  `Path = …appex` field correctly.
- PLUS a **live-gated smoke test**: if `/usr/bin/pluginkit` exists, run it and assert the parser
  returns a list of `.appex` paths without raising (`pytest.skip` if pluginkit absent — keeps CI green).

### Registry, titles, reinstall
- Register `SafariCollector` LAST in `get_registry()` (after Firefox) → browser block becomes
  Chrome → Edge → Brave → Firefox → Safari.
- Section title `"Safari Extensions"`; module-level `_TITLE` for the uniqueness test.
- Section-title uniqueness test bumps to **22** titles (add "Safari Extensions").
- Zero changes to `reinstall/parser.py` or `reinstall/emitter.py` — Safari extensions flow through
  as manual-checklist items automatically.
- Output via `flush_section` (sorted, dedup, `(none found)`), `raw=False`.

### Claude's Discretion
- Exact regex, the name/id plist-read helper shape, fixture file layout, and where the Safari plist
  helper lives (helpers/ vs inline in safari.py) — at Claude's discretion within the above.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/maccat/helpers/plist_version.py::get_plist_version(path)` — never-raising version read
  (CFBundleShortVersionString → CFBundleVersion → ""); reuse for Safari version.
- `src/maccat/collectors/mas.py` / `codex.py` — the subprocess-wrapped-in-try/except-OSError,
  never-raising pattern to mirror for the `pluginkit` call.
- `src/maccat/collectors/base.py` — Collector/Section/CollectorResult; `available()` gating.
- `src/maccat/collectors/__init__.py::get_registry()` — append SafariCollector last.
- `tests/collectors/test_section_titles.py` — bump expected count 21 → 22; add "Safari Extensions".

### Established Patterns
- `from __future__ import annotations` line 1; stdlib-only (`subprocess`, `plistlib`, `re`,
  `shutil.which` for availability); ruff + mypy --strict clean; type hints; module-level constants
  for monkeypatching; never-raising; deterministic stable sort via orchestrator flush_section.

### Integration Points
- New `tests/collectors/test_safari.py` (fixture-parse unit tests + live-gated smoke + never-raising
  + name/version/id fallback cases + (none found)). Update `test_section_titles.py` to 22.
</code_context>

<specifics>
## Specific Ideas

- Live reference fixture (capture verbatim for the parse test):
  ```
       com.bitwarden.desktop.safari(2026.5.0)
              Path = /Applications/Bitwarden.app/Contents/PlugIns/safari.appex
              UUID = 5AFDA995-8D64-43CA-B696-154F57ABF85B
           Timestamp = 2026-06-08 02:49:27 +0000
                 SDK = com.apple.Safari.web-extension
       Parent Bundle = /Applications/Bitwarden.app
  ```
- Test cases: pluginkit absent → (none found); pluginkit present but no web-extensions → (none found);
  one .appex with full plist → `name (version) [id]`; .appex whose Info.plist is missing/unreadable →
  skipped (others still collected); CFBundleDisplayName missing → name fallback chain.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Safari content blockers = SAF-02 v2; extension
enabled/disabled state = deferred CHR-02/FF-02 family.) This is the last phase of v2.2.0.
</deferred>
