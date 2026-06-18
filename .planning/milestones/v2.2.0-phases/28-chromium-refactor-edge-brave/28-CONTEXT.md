# Phase 28: Chromium Refactor + Edge + Brave - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Extract a shared `ChromiumBaseCollector` from the existing `chrome.py` (3 real Chromium browsers —
Chrome, Edge, Brave — now justify the abstraction), then add Edge and Brave as thin subclasses
(BRW-01, BRW-02). Chrome's catalog output must remain **byte-identical**.

Out of boundary: Zed/Codex (Phase 27, done), Safari (Phase 29), extension enabled/disabled state
(deferred CHR-02/FF-02). No changes to existing non-Chrome sections, the catalog/archive/git flow,
or the reinstall pipeline.
</domain>

<decisions>
## Implementation Decisions

### Refactor shape
- New `src/maccat/collectors/chromium.py::ChromiumBaseCollector` holds ALL shared profile-scan
  logic moved verbatim from `chrome.py` (`_collect_profile`, `collect()`, profile enumeration,
  `version_sort_tail` version-dir selection, `chrome_ext_name` localized-name resolution,
  cross-profile `flush_section` dedup).
- **Parameterization via class attributes:** `_base: Path`, `_title: str`, `_denylist: frozenset[str]`
  on the base; thin subclasses override only those. `ChromeCollector`, `EdgeCollector`,
  `BraveCollector` are each ~thin subclasses.
- **Chrome stays byte-identical.** `ChromeCollector` is a thin subclass overriding `_base`/`_title`/
  `_denylist` only; its emitted section output is unchanged. The existing `test_chrome.py` patch
  target changes from the module-level `chrome_mod._BASE` to `patch.object(ChromeCollector, "_base", new=tmp_path)`.

### Denylist composition
- `COMPONENT_DENYLIST` (the existing 10 Chrome component IDs) moves to `chromium.py` as the shared
  base, and is **re-exported from `chrome.py`** (`from maccat.collectors.chromium import COMPONENT_DENYLIST`)
  so existing imports (incl. `test_chrome.py` line ~14 and `chrome.py::__all__`) don't break.
- Per-browser `_denylist` = base ∪ browser-specific additions:
  - **Chrome** `_denylist = COMPONENT_DENYLIST` (base only).
  - **Brave** `_denylist = COMPONENT_DENYLIST | BRAVE_COMPONENT_DENYLIST` — the 20 confirmed Brave
    component IDs from the Brave components wiki (defined in `chromium.py` or `brave` module).
  - **Edge** `_denylist = COMPONENT_DENYLIST | EDGE_COMPONENT_DENYLIST` — `EDGE_COMPONENT_DENYLIST`
    starts from the Chrome baseline (Microsoft publishes no canonical component-ID list); a comment
    on the constant documents the gap and that it should be expanded after verifying against a real
    Edge install. (See Specific Ideas — verify Edge denylist live during implementation.)

### Sections & paths
- **Edge:** `_base = ~/Library/Application Support/Microsoft Edge`, `_title = "Microsoft Edge Extensions"`.
- **Brave:** `_base = ~/Library/Application Support/BraveSoftware/Brave-Browser`,
  `_title = "Brave Browser Extensions"`.
- Both reuse the identical Chromium profile layout (`<Profile>/Extensions/<id>/<version>/manifest.json`,
  `_locales` name resolution) — no new parsing logic.

### Presence detection
- Detect presence by enumerating profiles that contain an actual `Extensions` dir — NOT by a
  bare base-dir existence check. A machine with only `NativeMessagingHosts` under the base dir
  (e.g. Brave base dir present without the browser truly installed) must yield an empty section
  silently, not a spurious NOTE. Mirror however the existing Chrome presence/`(none found)` behaves.

### Registry ordering
- In `collectors/__init__.py::get_registry()`, group the Chromium browsers: **Chrome → Edge → Brave**,
  with **Firefox last** (so the browser block is Chrome, Edge, Brave, Firefox). Editors (VS Code,
  Cursor, Zed) stay before the browser block.

### Section-title uniqueness
- The Phase 27 section-title uniqueness test must continue to pass — now across 21 titles (19 +
  "Microsoft Edge Extensions" + "Brave Browser Extensions"). Add the two new titles to the test's
  expected set.

### Reinstall (no changes)
- Edge/Brave sections flow through reinstall as manual-checklist items automatically (browser
  extensions have no CLI installer). ZERO changes to `reinstall/parser.py` or `reinstall/emitter.py`.

### Claude's Discretion
- Exact module layout (one `chromium.py` with both subclasses vs separate `edge.py`/`brave.py`),
  where the Brave/Edge denylists live, and test-fixture structure are at Claude's discretion within
  the decisions above.
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/maccat/collectors/chrome.py` — the collector to generalize: `COMPONENT_DENYLIST` (10 IDs,
  frozenset, in `__all__`), `_BASE`/`_TITLE` module constants, `_collect_profile`, `collect()`
  (Default + sorted `Profile */` enumeration, `version_sort_tail`, `chrome_ext_name`, raw=False so
  the orchestrator dedups via `flush_section`).
- `src/maccat/helpers/chrome_name.py::chrome_ext_name` and `json_io.json_get` — reused unchanged.
- `src/maccat/catalog/format.py::emit_item` / `version_sort_tail` — unchanged.
- `tests/collectors/test_chrome.py` — patches `chrome_mod._BASE`; will switch to
  `patch.object(ChromeCollector, "_base", …)` after the refactor (the most likely break point).
- `tests/collectors/test_section_titles.py` (Phase 27) — add the 2 new titles to its expected set.

### Established Patterns
- `from __future__ import annotations` line 1; stdlib-only; ruff + mypy --strict clean; type hints;
  never-raising collectors; deterministic stable sort (via orchestrator `flush_section`).

### Integration Points
- `get_registry()` gains `EdgeCollector` + `BraveCollector` (Chrome → Edge → Brave → Firefox).
- New `tests/collectors/test_edge.py`, `tests/collectors/test_brave.py`; update `test_chrome.py`
  patch target; update `test_section_titles.py` count to 21.
</code_context>

<specifics>
## Specific Ideas

- **Verify Chrome byte-parity first:** run `test_chrome.py` green (with the updated patch target)
  before adding Edge/Brave — the refactor must not change Chrome's output.
- **Edge denylist gap (known):** `EDGE_COMPONENT_DENYLIST` ships as the Chrome baseline; document
  in a constant comment that Microsoft publishes no authoritative list and it should be verified/
  expanded against a real Edge install. This is acceptable to ship (over-listing user extensions is
  the failure mode; the baseline is conservative). Do not block the phase on it.
- **Brave base-dir false-positive:** the Brave base dir can exist (NativeMessagingHosts) without
  Brave installed — the profile-enumeration presence check handles this; add a test fixture for it.
- Adversarial/fixture tests should cover: Edge/Brave absent, present-with-extensions, multi-profile,
  component-denylist exclusion, and the `_metadata`/non-version dir guard (inherited from Chrome).
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Safari = Phase 29; extension enabled/disabled state =
deferred CHR-02/FF-02; Edge denylist completeness = follow-up after a real Edge install.)
</deferred>
