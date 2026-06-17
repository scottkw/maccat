# Requirements: maccat — v2.2.0 Broader Coverage

**Defined:** 2026-06-17
**Core Value:** A single run produces one complete, restorable snapshot of a machine's software *and* tooling extensions — accurate enough to rebuild the environment from, degrading gracefully when any source isn't installed.

## v1 Requirements

Requirements for this milestone (v2.2.0). Each maps to a roadmap phase. Every new source honors
the established conventions: uniform `name (version) [id]` format with graceful degradation
(FMT-01), no secrets in the catalog (FMT-03), and deterministic stably-sorted output so repeated
runs diff-empty (FMT-04). All implementation is stdlib-only (no new pip dependencies).

### Browser & Editor Coverage

- [x] **BRW-01**: Catalog **Microsoft Edge** user-installed extensions across all profiles —
  `~/Library/Application Support/Microsoft Edge/<Profile>/Extensions/<id>/<version>/manifest.json`,
  Chromium model reusing the shared Chromium collector + `__MSG_`/`_locales` name resolution,
  built-in/component extensions excluded. Emits `name (version) [id]`. Degrades to `(none found)`
  when Edge is absent (presence detected by an actual profile with an `Extensions` dir, not just
  the base directory). (Known gap: Microsoft publishes no canonical component-ID denylist — ship
  with the Chrome baseline + a documented gap.)
- [x] **BRW-02**: Catalog **Brave** user-installed extensions across all profiles —
  `~/Library/Application Support/BraveSoftware/Brave-Browser/<Profile>/Extensions/...`, same shared
  Chromium collector, Brave's confirmed component-ID denylist applied, built-ins excluded.
- [x] **BRW-03**: Catalog **Zed** installed extensions from
  `~/Library/Application Support/Zed/extensions/index.json` (canonical id + name + version), with
  local/`dev` extensions filtered out. Degrades to `(none found)` when Zed or the file is absent.
- [ ] **BRW-04**: Catalog **Safari** user-installed extensions via
  `pluginkit -p com.apple.Safari.web-extension`, reading each `.appex` `Info.plist` for
  `CFBundleDisplayName` (name), `CFBundleShortVersionString` (version), and `CFBundleIdentifier`
  (id). Apple's built-in extensions are excluded by the plugin-point filter. Each step is
  never-raising; missing fields degrade gracefully.

### AI-CLI Coverage

- [x] **CDX-02**: Catalog **Codex plugins** as a new "Codex Plugins" section alongside the existing
  "Codex MCP Servers" section. Detect plugins where the installed Codex supports them (prefer a
  `codex plugin list` CLI if present, else read `[plugins."…"]` headers from `~/.codex/config.toml`),
  emitting **identity-only** entries (name + id; version where available) and **never** reading
  plugin bundle files (e.g. `.mcp.json`) that can contain secrets (FMT-03). Degrades to
  `(none found)` on Codex versions without a plugin system (the currently-installed v0.46.0 has none).

## v2 Requirements

Deferred to future releases.

### Coverage
- **CHR-02 / FF-02 / EDGE-state / BRAVE-state**: browser-extension enabled/disabled state (all browsers).
- **SAF-02**: Safari content-blockers (separate plugin point) — scope decision deferred.

### Reinstall
- **RST-03**: Capture/restore Homebrew taps.
- **RST-04**: Best-effort restore of AI-CLI tooling beyond a manual checklist.

### Other
- **DIFF-01**: Diff two catalogs over time (added / removed / version-changed).
- **PKG-04**: pipx / PyPI distribution channel.

## Out of Scope

Explicitly excluded from v2.2.0.

| Feature | Reason |
|---------|--------|
| Extension enabled/disabled state | Deferred (CHR-02/FF-02 family); this milestone catalogs presence + version + id only |
| New pip dependencies | Tool ships as a single stdlib-only `.pyz`; new sources use `tomllib`/`plistlib`/`json`/`subprocess`/`re` only |
| Changes to existing sections, the catalog/archive/git flow, or the reinstall pipeline | Additive coverage only; new sections flow through reinstall as manual-checklist items with zero reinstall changes |
| Safari content blockers | Different plugin point; scope decision deferred to v2+ (SAF-02) |
| Backfilling component-ID denylists from machines without the browser installed | Out of scope; Edge denylist ships with the Chrome baseline + documented gap |
| Cross-platform support | macOS-only by design |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BRW-01 | Phase 28 | Complete |
| BRW-02 | Phase 28 | Complete |
| BRW-03 | Phase 27 | Complete |
| BRW-04 | Phase 29 | Pending |
| CDX-02 | Phase 27 | Complete |

**Coverage:**
- v1 requirements: 5 total
- Mapped to phases: 5
- Unmapped: 0

---
*Requirements defined: 2026-06-17*
*Traceability filled: 2026-06-17*
