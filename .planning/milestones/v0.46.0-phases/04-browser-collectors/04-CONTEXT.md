# Phase 4: Browser Collectors - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds two plain-text catalog sections to `update-list.sh` — **"Google Chrome
Extensions"** and **"Firefox Extensions"** — listing user-installed extensions across every
profile as `name (version) [id]`, using the Phase 1 helpers (`json_get`, `chrome_ext_name`,
`emit_item`, `flush_section`). Covers CHR-01 and FF-01.

The Phase 1 `chrome_ext_name` helper (already verified against the Bitwarden `__MSG_extName__`
extension on this machine) is the name-resolution engine for Chrome. Collectors are DEFINED
and self-testable but NOT wired into `generate_catalog` (Phase 5 wires them). No editor or
AI-CLI work here.

NOTE: the ROADMAP "**UI hint**: yes" is a keyword-grep false positive — this phase produces
plain-text catalog sections, not a UI. No UI-SPEC needed.
</domain>

<decisions>
## Implementation Decisions

### Chrome Profile Enumeration & Version Selection (USER LOCKED: accept all)
- Iterate `~/Library/Application Support/Google/Chrome/` for `Default` and `Profile *` dirs that
  contain an `Extensions/` subdirectory (null-glob guarded). On this machine only `Default` exists.
- Per extension: `<profile>/Extensions/<id>/<version>/manifest.json`. When multiple version dirs
  exist, use the highest/latest version dir.
- `name` resolved via the Phase 1 `chrome_ext_name <manifest>` helper (resolves `__MSG_*__` via
  `_locales/<default_locale>/messages.json`, case-insensitive, falls back to the 32-char ID).
- `id` = the 32-char extension directory name. `version` from the manifest's `version`.

### Chrome Built-in / Component Exclusion (USER LOCKED: exclude components)
- Skip a denylist of well-known Google component/pre-installed extension IDs (e.g. the Chrome
  Web Store `nmmhkkegccagdldgiimedpiccmgmieda`, default-apps components) so the catalog lists
  user-installed extensions only.
- Skip the `Temp` directory and any extension/version dir that lacks a `manifest.json`
  (mid-install / partial state).
- When a name still can't be resolved, fall back to the extension ID (CHR-01) — never blank,
  never a raw `__MSG_` string.

### Firefox Filtering & Fields (USER LOCKED: app-profile only, INCLUDE user themes)
- Parse each profile's `extensions.json` `.addons[]`. Keep addons with
  `location == "app-profile"` (this is the built-in/system exclusion mechanism).
- INCLUDE user themes (`type == "theme"`) as well as extensions — both are installed machine
  state, both are `app-profile`. (Built-in/system add-ons have other `location` values and are
  excluded.)
- Enumerate every profile listed in `~/Library/Application Support/Firefox/profiles.ini`
  (`Path=` entries) that has an `extensions.json`.
- `name` = `.defaultLocale.name` (fall back to `id` if absent); `version` = `.version`;
  `id` = `.id`.

### Section Structure & Cross-Profile Handling (USER LOCKED: accept all)
- Two sections: `Google Chrome Extensions` and `Firefox Extensions` (names per success criteria).
- The same extension present in multiple profiles is MERGED and DEDUPED — identical
  `name (version) [id]` lines collapse via `flush_section`'s `LC_ALL=C sort -f -u`. The catalog
  reflects the machine's installed set, not per-profile copies.
- Browser absent, profile missing, or zero extensions → section written with `(none found)`,
  run continues. Every profile/extension loop is null-glob guarded so an unmatched glob never
  aborts the script.
- Everything routed through `emit_item` → `flush_section` for deterministic, stably-sorted output (FMT-04).
</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (Phases 1–3)
- `chrome_ext_name <manifest_path>` (Phase 1) — THE Chrome name resolver; verified against the
  real Bitwarden `__MSG_extName__` extension. Use directly for CHR-01.
- `json_get <file> <key>` — for Firefox `extensions.json` fields (`.addons[N].defaultLocale.name`,
  `.version`, `.id`, `.location`, `.type`) and Chrome manifest `version`.
- `emit_item <name> <version> <id>` (FMT-01 builder, dedup-suppression) and `flush_section`
  (`LC_ALL=C sort -f -u`, `(none found)` when empty, buffer reset).
- `write_section "$title"` (update-list.sh:254). Established collector pattern from Phases 2–3:
  `write_section` → `_section_lines=()` → loop → `emit_item` → `flush_section`.

### Established Patterns
- `local`-scoped vars; `[[ ]]`; `command -v`; double-quoted expansions; `return` (not `exit`);
  null-glob guard (`setopt local_options null_glob` + `[[ -e "$f" ]] || continue`) — CRITICAL here
  given multiple nested profile/extension/version glob loops; `2>/dev/null` for noisy stderr.

### Integration Points
- New collector functions (`collect_chrome_extensions`, `collect_firefox_extensions`) defined
  alongside the existing collectors; NOT called from `generate_catalog` (Phase 5).
</code_context>

<specifics>
## Specific Ideas (verification grounding — THIS machine)
- Chrome dir: `~/Library/Application Support/Google/Chrome/` — only `Default` profile, 8
  extension dirs. Two use `__MSG_` names: `nngceckbapebfimnlniiiahkandclblb` (Bitwarden →
  resolves to "Bitwarden Password Manager") and `nmmhkkegccagdldgiimedpiccmgmieda`
  (`__MSG_APP_NAME__`, the Chrome Web Store component → EXCLUDED per the denylist). After
  exclusion, expect ~7 user extensions.
- Firefox dir: `~/Library/Application Support/Firefox/` — `profiles.ini` lists 2 profiles;
  `Profiles/rv4siqj3.default-release` has `extensions.json` with 18 addons (14 `extension`, 4
  `theme`), all needing the `location=="app-profile"` filter. Sample: "Vue.js devtools" 7.7.7.
- Determinism is testable: two consecutive runs on an unchanged machine must diff-empty.
- No secrets are involved here (extension names/versions/IDs are public), but output still
  routes through the same FMT-04 sort discipline.
</specifics>

<deferred>
## Deferred Ideas
- Wiring collectors into `generate_catalog` — Phase 5.
- Capturing extension enabled/disabled state (CHR-02/FF-02) — out of scope (v2; fragile
  `Secure Preferences` parsing for Chrome).
</deferred>

<research_flags>
## Open Questions for Research
1. **Chrome component denylist:** confirm the canonical set of well-known Google
   component/pre-installed extension IDs to exclude (at minimum Chrome Web Store
   `nmmhkkegccagdldgiimedpiccmgmieda`; check for default-apps like the Google Docs/Drive/Slides
   offline components). Provide the exact ID list and whether any other detection (e.g. the
   `Temp` dir, missing manifest) is needed.
2. **Chrome latest-version selection:** confirm the robust way in Zsh to pick the highest version
   dir under `Extensions/<id>/` (version-sort vs lexical) and that `chrome_ext_name` is given the
   chosen dir's manifest path. Confirm `_locales/<default_locale>/messages.json` resolution still
   works for these specific extensions (Bitwarden verified in Phase 1).
3. **Firefox profile iteration:** confirm parsing `profiles.ini` `Path=` entries (relative to the
   Firefox dir), handling both `.default` and `.default-release`, and that `extensions.json`
   `.addons[]` is iterated with `location=="app-profile"` filter. Confirm exact json_get/jq for
   the addon array (names contain spaces; `while IFS= read -r`). Note `defaultLocale.name` is
   nested.
4. **Cross-profile dedupe correctness:** confirm merging all Chrome profiles' extensions (and all
   Firefox profiles') into one section with `flush_section`'s `-u` dedupe yields the intended
   "machine installed set" and that an extension at different versions across profiles correctly
   shows both (different `(version)` ⇒ distinct lines, which is correct).
5. **Zsh nested-glob safety + determinism:** the null-glob/dir-guard pattern for the
   profile→extension→version nesting; stable byte-identical output across two runs.
</research_flags>
