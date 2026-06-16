# Phase 4: Browser Collectors — Research

**Researched:** 2026-06-13
**Domain:** Chrome and Firefox extension cataloging — pure Zsh, profile enumeration, component denylist, version selection, jq/plutil extraction
**Confidence:** HIGH (all findings verified live against real browser data on this machine)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Chrome Profile Enumeration & Version Selection (USER LOCKED: accept all)**
- Iterate `~/Library/Application Support/Google/Chrome/` for `Default` and `Profile *` dirs that
  contain an `Extensions/` subdirectory (null-glob guarded). On this machine only `Default` exists.
- Per extension: `<profile>/Extensions/<id>/<version>/manifest.json`. When multiple version dirs
  exist, use the highest/latest version dir.
- `name` resolved via the Phase 1 `chrome_ext_name <manifest>` helper (resolves `__MSG_*__` via
  `_locales/<default_locale>/messages.json`, case-insensitive, falls back to the 32-char ID).
- `id` = the 32-char extension directory name. `version` from the manifest's `version`.

**Chrome Built-in / Component Exclusion (USER LOCKED: exclude components)**
- Skip a denylist of well-known Google component/pre-installed extension IDs (e.g. the Chrome
  Web Store `nmmhkkegccagdldgiimedpiccmgmieda`, default-apps components) so the catalog lists
  user-installed extensions only.
- Skip the `Temp` directory and any extension/version dir that lacks a `manifest.json`.
- When a name still can't be resolved, fall back to the extension ID (CHR-01) — never blank,
  never a raw `__MSG_` string.

**Firefox Filtering & Fields (USER LOCKED: app-profile only, INCLUDE user themes)**
- Parse each profile's `extensions.json` `.addons[]`. Keep addons with
  `location == "app-profile"` (this is the built-in/system exclusion mechanism).
- INCLUDE user themes (`type == "theme"`) as well as extensions — both are installed machine
  state, both are `app-profile`. (Built-in/system add-ons have other `location` values and are
  excluded.)
- Enumerate every profile listed in `~/Library/Application Support/Firefox/profiles.ini`
  (`Path=` entries) that has an `extensions.json`.
- `name` = `.defaultLocale.name` (fall back to `id` if absent); `version` = `.version`;
  `id` = `.id`.

**Section Structure & Cross-Profile Handling (USER LOCKED: accept all)**
- Two sections: `Google Chrome Extensions` and `Firefox Extensions`.
- The same extension present in multiple profiles is MERGED and DEDUPED — identical
  `name (version) [id]` lines collapse via `flush_section`'s `LC_ALL=C sort -f -u`.
- Browser absent, profile missing, or zero extensions → section written with `(none found)`,
  run continues.
- Everything routed through `emit_item` → `flush_section` for deterministic, stably-sorted output (FMT-04).

### Claude's Discretion

None specified.

### Deferred Ideas (OUT OF SCOPE)

- Wiring collectors into `generate_catalog` — Phase 5.
- Capturing extension enabled/disabled state (CHR-02/FF-02) — out of scope (v2; fragile
  `Secure Preferences` parsing for Chrome).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHR-01 | Catalog Google Chrome extensions across all profiles (name + version + ID), resolving `__MSG_*` localized names via `_locales/<default_locale>/messages.json` and falling back to the extension ID when a name can't be resolved | Profile enumeration verified; `sort -V` version selection verified; `chrome_ext_name` resolution confirmed end-to-end on Bitwarden + 6 other extensions; denylist of 10 component IDs documented; 7 user extensions extracted and sorted; output verified byte-identical across two runs |
| FF-01 | Catalog Firefox extensions across all profiles (name + version + ID), parsing each profile's `extensions.json` and excluding built-in/system add-ons | `profiles.ini` Path= parsing verified; 2 profiles found (1 has extensions.json); `location=="app-profile"` filter yields 6 user addons out of 18 total; jq tab-separated extraction with `while IFS=$'\t' read -r` verified; plutil index-based fallback verified (all 18 addons iterated); 6-addon sorted output verified byte-identical across two runs |
</phase_requirements>

---

## Summary

Phase 4 adds two Zsh collector functions — `collect_chrome_extensions` and `collect_firefox_extensions` — to `update-list.sh`. They are defined alongside existing Phase 1–3 helpers and NOT wired into `generate_catalog` (Phase 5 does that). Both collectors emit `name (version) [id]` lines through the existing `emit_item` → `flush_section` pipeline, producing deterministic, sorted, deduplicated output.

All five research flags are fully answered below and verified live against real browser data on this machine. The extraction was run twice for determinism confirmation — both runs produced byte-identical output.

**Concrete live findings:** Chrome yields 7 user extensions (8 dirs minus 1 component — `nmmhkkegccagdldgiimedpiccmgmieda` / Chrome Web Store Payments); Firefox yields 6 `app-profile` addons out of 18 total (the remaining 12 are `app-builtin` and `app-builtin-addons`, correctly excluded). All 4 Firefox themes on this machine are `app-builtin` — the include-themes decision is correct but has no effect on this machine's output.

**Primary recommendation:** Implement `collect_chrome_extensions` and `collect_firefox_extensions` following the exact patterns below. Chrome uses `sort -V` for version dir selection and the existing `chrome_ext_name` helper for name resolution. Firefox uses `jq` with tab-separated output + `while IFS=$'\t' read -r` iteration, with `plutil` index-loop fallback. Both collectors follow the established Phase 2/3 section-writing flow exactly.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Chrome profile enumeration | Collector function (`collect_chrome_extensions`) | — | Profile list is per-user filesystem state; no external tool involved |
| Chrome version dir selection | `sort -V` (Zsh subshell per extension) | — | `sort -V` is the only correct version-sort for `N.N.N_N` dirs; lexical sort gives wrong results for 14.1302.0_0 vs 3.8_0 |
| Chrome name resolution | `chrome_ext_name` helper (Phase 1) | Extension ID fallback | Phase 1 already handles `__MSG_*__`, case-insensitive lookup, locale fallback — reuse directly |
| Firefox profile discovery | `grep '^Path='` on `profiles.ini` | — | `profiles.ini` is the authoritative profile registry; no CLI needed |
| Firefox addon extraction | `jq` (primary) | `plutil` index loop (fallback) | Firefox `extensions.json` is a JSON array — requires array iteration, which plutil supports via `addons.N.*` indexing |
| Component/built-in exclusion | Chrome: hardcoded ID denylist | Firefox: `location` field filter | Chrome has no single flag per manifest to distinguish user vs component; denylist is the reliable approach. Firefox's `location` field is designed for exactly this purpose. |
| Cross-profile deduplication | `flush_section` (`LC_ALL=C sort -f -u`) | — | `flush_section` already dedups identical lines; different versions across profiles produce distinct lines (correct — both are installed) |
| Section emission | `emit_item` + `flush_section` (Phase 1 helpers) | — | FMT-01 / FMT-04 contract — never emit directly to `OUTPUT_FILE` |

---

## Standard Stack

### Core

| Tool | Availability | Role | Source |
|------|-------------|------|--------|
| `jq` | Optional (Homebrew, `/opt/homebrew/bin/jq`) | Primary: Chrome name field, Firefox addon array iteration | [VERIFIED: jq-1.8.1 present, used in all live tests] |
| `plutil` | Always present (`/usr/bin/plutil`, macOS since 10.4) | Fallback: Chrome manifest scalar reads, Firefox index-loop | [VERIFIED: works for `addons.N.defaultLocale.name` nested path] |
| `sort -V` | Always present (macOS BSD sort) | Selects highest version dir under `Extensions/<id>/` | [VERIFIED: correctly sorts `3.8_0 < 4.154.0_0 < 14.1302.0_0 < 2026.5.1_0`] |
| Phase 1 helpers | Already in `update-list.sh` | `json_get`, `chrome_ext_name`, `emit_item`, `flush_section` | [VERIFIED: live in script lines 259–476] |

### No new packages

This phase installs nothing. All backends are probed at runtime.

---

## Package Legitimacy Audit

Not applicable — Phase 4 installs no external packages.

---

## Research Flag Answers (All 5)

### Flag 1: Chrome Component Denylist

**VERIFIED against this machine's Extensions directory.**

The correct denylist contains exactly these IDs, representing Google's default-installed and component extensions that do NOT reflect user choices. None have a manifest flag that distinguishes them from user extensions — the ID itself is the only reliable signal.

```zsh
# Chrome component / pre-installed extension IDs to SKIP
# Source: jamieweb.net/info/chrome-extension-ids/ [CITED] + live verification on this machine
local chrome_component_ids=(
    "nmmhkkegccagdldgiimedpiccmgmieda"  # Chrome Web Store Payments / Google Wallet [VERIFIED: present on this machine]
    "ghbmnnjooekpmoecnnnilnnbdlolhkhi"  # Google Docs Offline (very commonly pre-installed)
    "aapocclcgogkmnckokdopfmhonfmgoek"  # Google Slides (offline)
    "blpcfgokakmgnkcojhhkbfbldkacnbeo"  # YouTube (old default app)
    "felcaaldnbdncclmgdcncolpebgiejap"  # Google Sheets (offline)
    "aohghmighlieiainnegkcijnfilokake"  # Google Docs (offline)
    "apdfllckaahabafndbhieahigkjlhalf"  # Google Drive (offline)
    "pjkljhegncpnkpknbcohdijeoejaedia"  # Google Mail (Gmail app)
    "mhjfbmdgcfjbbpaeojofohoefgiehjai"  # Chrome PDF Viewer (old built-in)
    "pkedcjkdefgpdelpbcmbmeomcjbeemfm"  # Chrome Cast / Chrome Web Store (old)
)
```

**Implementation as a lookup function:**

The most Zsh-idiomatic approach is an associative array (available in Zsh natively):

```zsh
# At top of collect_chrome_extensions function:
typeset -A _chrome_denied
for id in "${chrome_component_ids[@]}"; do
    _chrome_denied[$id]=1
done

# In the inner loop:
[[ -n "${_chrome_denied[$ext_id]}" ]] && continue
```

Or equivalently (simpler, fine for 10 items):

```zsh
# Simple case-statement skip (no associative array needed for short list)
case "$ext_id" in
    nmmhkkegccagdldgiimedpiccmgmieda|\
    ghbmnnjooekpmoecnnnilnnbdlolhkhi|\
    aapocclcgogkmnckokdopfmhonfmgoek|\
    blpcfgokakmgnkcojhhkbfbldkacnbeo|\
    felcaaldnbdncclmgdcncolpebgiejap|\
    aohghmighlieiainnegkcijnfilokake|\
    apdfllckaahabafndbhieahigkjlhalf|\
    pjkljhegncpnkpknbcohdijeoejaedia|\
    mhjfbmdgcfjbbpaeojofohoefgiehjai|\
    pkedcjkdefgpdelpbcmbmeomcjbeemfm)
        continue ;;
esac
```

**Additional guards (both required):**

- Skip the `Temp` directory: `[[ "$ext_id" == "Temp" ]] && continue` — Chrome uses this for in-progress downloads. Absent on this machine but the guard is cheap and correct.
- Skip version dirs without `manifest.json`: `[[ -f "$manifest" ]] || continue` — mid-install state.

**This machine's 8 extensions classified:**

| Extension ID | Resolved Name | Class |
|---|---|---|
| `cpkepcpjdmcaldbhbolnkjjelmmknfgg` | YouTube Watch Later Cleaner | USER |
| `deafalnegnfhjhejolidiobnapigcfpd` | YT Watch Later Assist | USER |
| `fcoeoabgfenejglbffodgkkbkcdhcgfn` | Claude | USER |
| `hdokiejnpimakedhajhdlcegeplioahd` | LastPass: Free Password Manager | USER |
| `kbfnbcaeplbcioakkpcpgfkobkghlhen` | Grammarly: AI Writing Assistant and Grammar Checker App | USER |
| `knjbgabkeojmfdhindppcmhhfiembkeb` | Matter | USER |
| `nmmhkkegccagdldgiimedpiccmgmieda` | Chrome Web Store Payments | **COMPONENT — EXCLUDED** |
| `nngceckbapebfimnlniiiahkandclblb` | Bitwarden Password Manager | USER |

**Result: 7 user extensions after exclusion.** [VERIFIED: live extraction]

---

### Flag 2: Chrome Profile Enumeration + Version Selection + Name Resolution

#### (a) Profile enumeration

```zsh
CHROME_BASE="$HOME/Library/Application Support/Google/Chrome"

setopt local_options null_glob   # required: "Profile *" glob must not abort when no multi-profile

for profile_dir in "$CHROME_BASE/Default" "$CHROME_BASE"/Profile\ */; do
    [[ -d "${profile_dir}/Extensions" ]] || continue
    # process this profile...
done
```

**Critical points:**
- `"$CHROME_BASE/Default"` is listed explicitly (not via glob) — it is always the primary profile name.
- `"$CHROME_BASE"/Profile\ */` covers Profile 1, Profile 2, etc. The backslash-space quotes the space in the pattern correctly in Zsh.
- `setopt local_options null_glob` prevents Zsh aborting when no `Profile *` dirs exist (as on this machine). [VERIFIED: single `Default` profile on this machine; glob returns no matches without aborting]
- Each profile must be guarded with `[[ -d "${profile_dir}/Extensions" ]]` — the `Default` literal and any Profile dirs without an `Extensions/` subdir are skipped.

#### (b) Highest version dir selection

```zsh
# Inside the extension ID loop:
ver_dir=$(ls -1 "$ext_dir" 2>/dev/null | sort -V | tail -1)
[[ -z "$ver_dir" ]] && continue
manifest="${ext_dir}${ver_dir}/manifest.json"
[[ -f "$manifest" ]] || continue
```

**Why `sort -V` is correct for Chrome version dirs:**

Chrome version dirs follow the pattern `<semver>_<N>` where `_N` is a suffix that increments on repeated updates of the same version. Examples from this machine: `1.0.0_0`, `3.8_0`, `14.1302.0_0`, `2026.5.1_0`.

`sort -V` (version sort) correctly handles both the numeric version components and the `_N` suffix:
- `3.8_0 < 14.1302.0_0 < 2026.5.1_0` — numeric comparison, not lexical [VERIFIED]
- `1.0.0_0 < 1.0.0_1 < 2.0.0_0` — same-version different suffixes ordered correctly [VERIFIED]
- `10.0.0_0 > 2.0.0_0` — lexical sort would reverse this; `sort -V` is correct [VERIFIED]

`tail -1` picks the highest/latest version. This is correct: the highest version dir holds the currently-active extension code.

#### (c) chrome_ext_name resolution

```zsh
name=$(chrome_ext_name "$manifest")
version=$(json_get "$manifest" "version")
```

`chrome_ext_name` is already in `update-list.sh` (Phase 1, line ~327). It handles:
- Plain names: returned as-is
- `__MSG_<key>__` names: resolved via `_locales/<default_locale>/messages.json` with case-insensitive key lookup
- Fallback: returns the 32-char extension ID (grandparent dir of the manifest)

**Both `__MSG_` extensions on this machine confirmed:**

| Extension | ID | Raw name in manifest | Resolution | Result |
|---|---|---|---|---|
| Bitwarden | `nngceckbapebfimnlniiiahkandclblb` | `__MSG_extName__` | msg_key=`extName` → locale=`en` → `_locales/en/messages.json` → key `extName` (case-insensitive) → `message` | **"Bitwarden Password Manager"** [VERIFIED] |
| Chrome Web Store | `nmmhkkegccagdldgiimedpiccmgmieda` | `__MSG_APP_NAME__` | msg_key=`APP_NAME` → lowercase=`app_name` → `_locales/en/messages.json` → key `app_name` → `message` | **"Chrome Web Store Payments"** (EXCLUDED by denylist anyway) [VERIFIED] |

**Version extraction:**

`json_get "$manifest" "version"` works for all 7 user extensions. Chrome's `version` field is always a plain string — never a `__MSG_` placeholder. [VERIFIED: all manifests on this machine use plain version strings like `"1.0.0"`, `"14.1302.0"`, `"2026.5.1"`]

---

### Flag 3: Firefox Profile Iteration + Addon Filtering

#### Profile iteration from profiles.ini

```zsh
FF_DIR="$HOME/Library/Application Support/Firefox"

while IFS= read -r rel_path; do
    local ext_json="${FF_DIR}/${rel_path}/extensions.json"
    [[ -f "$ext_json" ]] || continue
    # process this profile's extensions.json...
done < <(grep '^Path=' "${FF_DIR}/profiles.ini" 2>/dev/null | sed 's/^Path=//')
```

**Key points:**
- `grep '^Path='` on `profiles.ini` reliably extracts all profile paths. Paths are relative to the Firefox dir (not absolute). [VERIFIED: `Profiles/l7e7es5w.default` and `Profiles/rv4siqj3.default-release` extracted correctly]
- No special handling needed for `.default` vs `.default-release` — they are just different path strings. Both are parsed the same way.
- `[[ -f "$ext_json" ]]` guards against profiles with no extensions.json (e.g. a fresh profile). On this machine, `l7e7es5w.default` has no `extensions.json`; `rv4siqj3.default-release` does. [VERIFIED]
- `while IFS= read -r` is required to prevent word-splitting on profile paths that might contain spaces (rare, but defensive).

#### Addon extraction with jq (primary path)

```zsh
while IFS=$'\t' read -r name version id; do
    [[ -z "$id" ]] && continue
    [[ -z "$name" ]] && name="$id"   # fallback: use id as name
    emit_item "$name" "$version" "$id"
done < <(jq -r '.addons[] | select(.location == "app-profile") |
    "\(.defaultLocale.name // .id)\t\(.version // "")\t\(.id)"' \
    "$ext_json" 2>/dev/null)
```

**Critical implementation notes:**

- `select(.location == "app-profile")`: This is the correct filter. Firefox uses three location values: `app-profile` (user-installed), `app-builtin` (Firefox built-in themes/system), `app-builtin-addons` (Firefox built-in functional add-ons like Form Autofill, PiP, etc.). [VERIFIED: 18 total = 6 app-profile + 5 app-builtin + 7 app-builtin-addons]
- `.defaultLocale.name` is the correct field path — `defaultLocale` is a JSON object with a `name` string inside it. **Note the capital L**: `defaultLocale`, not `defaultlocale`. [VERIFIED: `jq '.addons[0].defaultLocale.name'` returns `"Vue.js devtools"` correctly]
- `.defaultLocale.name // .id` fallback in jq: if `defaultLocale.name` is null, use `.id`. [VERIFIED: all 6 app-profile addons have non-null `defaultLocale.name`]
- Tab-separated output with `IFS=$'\t'` read: required because addon names contain spaces (`"Vue.js devtools"`, `"Grammarly: AI Writing and Grammar Checker App"`, etc.). Using `\t` as delimiter avoids word-splitting on spaces. [VERIFIED: all 6 names read correctly]
- Do NOT use `for item in $(jq ...)` — splits on spaces in names.

**jq handles the array iteration natively** — no index loop needed. One entry per `addons[]` element, filtered and formatted in a single pipeline. [VERIFIED]

#### Addon extraction with plutil (fallback path)

`plutil` CAN access nested fields in Firefox's `extensions.json` via index-based paths like `addons.N.defaultLocale.name`. [VERIFIED: `plutil -extract "addons.0.defaultLocale.name" raw -o - extensions.json` returns `"Vue.js devtools"`]

The fallback loop:

```zsh
local idx=0
while true; do
    local loc
    loc=$(plutil -extract "addons.${idx}.location" raw -o - "$ext_json" 2>/dev/null) || break
    if [[ "$loc" == "app-profile" ]]; then
        local name="" version="" id=""
        name=$(plutil -extract "addons.${idx}.defaultLocale.name" raw -o - "$ext_json" 2>/dev/null) || name=""
        version=$(plutil -extract "addons.${idx}.version" raw -o - "$ext_json" 2>/dev/null) || version=""
        id=$(plutil -extract "addons.${idx}.id" raw -o - "$ext_json" 2>/dev/null) || id=""
        [[ -z "$id" ]] && { ((idx++)); continue; }
        [[ -z "$name" ]] && name="$id"
        emit_item "$name" "$version" "$id"
    fi
    ((idx++))
done
```

**Performance note:** The plutil loop makes ~4 calls per addon and iterates all 18 addons. On a large Firefox installation with many extensions this is slower than jq (which processes the whole file once), but it is correct and works gracefully. For typical Firefox installs (< 100 addons), the performance impact is negligible. [VERIFIED: loop correctly iterated all 18 addons and filtered to 6 app-profile ones]

**Real counts on this machine (default-release profile):**

| Location | Count | Action |
|---|---|---|
| `app-profile` | 6 | INCLUDE — user-installed |
| `app-builtin` | 5 | EXCLUDE — Firefox built-in (4 themes + 1 extension) |
| `app-builtin-addons` | 7 | EXCLUDE — Firefox built-in functional add-ons |
| **Total** | **18** | **6 included after filter** |

**6 app-profile addons (all extensions, 0 themes on this machine):**

```
DuckDuckGo Search & Tracker Protection (2026.5.22) [jid1-ZAdIEUB7XOzOJw@jetpack]
Evernote Web Clipper (7.40.0) [{E0B8C461-F8FB-49b4-8373-FE32E9252800}]
Grammarly: AI Writing and Grammar Checker App (8.937.0) [87677a2c52b84ad3a151a4a72f5bd3c4@jetpack]
LastPass (4.153.1) [support@lastpass.com]
New Tab (153.1.20260528.133333) [newtab@mozilla.org]
Vue.js devtools (7.7.7) [{5caff8cc-3d2e-4110-a88a-003cc85b3858}]
```

[VERIFIED: exact output from two consecutive runs — byte-identical]

---

### Flag 4: Cross-Profile Dedupe Correctness

The emit → flush flow correctly handles multi-profile deduplication:

**Case 1: Same extension, same version, in two profiles:**
Both profiles emit `"Bitwarden Password Manager (2026.5.1) [nngceckbapebfimnlniiiahkandclblb]"` — identical strings. `flush_section`'s `LC_ALL=C sort -f -u` deduplicates them to one line. [VERIFIED: double-emit test confirmed]

**Case 2: Same extension ID, different versions across profiles:**
Profile A emits `"Bitwarden Password Manager (2026.4.0) [nngceckbapebfimnlniiiahkandclblb]"`, Profile B emits `"Bitwarden Password Manager (2026.5.1) [nngceckbapebfimnlniiiahkandclblb]"` — different strings (version differs). Both survive the `-u` filter. Result: two lines, both correct — the machine has two different versions installed across its profiles. [VERIFIED: two-version test confirmed]

This is intentional: the catalog captures per-machine state, not per-profile. Showing both versions faithfully represents reality.

**No additional code needed:** The existing `emit_item` → `flush_section` pipeline (with `_section_lines` accumulating across all profile iterations) handles this automatically. The collector iterates all profiles in a single loop, accumulating all lines into `_section_lines[]` before calling `flush_section` once at the end.

---

### Flag 5: Zsh Nested-Glob Safety + Determinism

#### Null-glob pattern for nested loops

The Chrome collector has three levels of glob nesting:

```zsh
setopt local_options null_glob   # set ONCE at top of function; covers all loops below

# Level 1: Profile dirs
for profile_dir in "$CHROME_BASE/Default" "$CHROME_BASE"/Profile\ */; do
    [[ -d "${profile_dir}/Extensions" ]] || continue

    # Level 2: Extension ID dirs
    for ext_dir in "${profile_dir}/Extensions"/*/; do
        [[ -e "$ext_dir" ]] || continue   # null-glob guard per established pattern
        ext_id=$(basename "$ext_dir")
        [[ "$ext_id" == "Temp" ]] && continue

        # Level 3: version dir selection (not a glob — uses ls + sort -V + tail -1)
        ver_dir=$(ls -1 "$ext_dir" 2>/dev/null | sort -V | tail -1)
        [[ -z "$ver_dir" ]] && continue
        manifest="${ext_dir}${ver_dir}/manifest.json"
        [[ -f "$manifest" ]] || continue
        # ...
    done
done
```

`setopt local_options null_glob` at the function top covers all loops in that function invocation — no need to repeat it per loop. [VERIFIED: Phase 3 collectors use this same pattern; confirmed working when `Profile *` dirs are absent]

**Level 3 is not a glob:** `ls -1 "$ext_dir" | sort -V | tail -1` uses `ls` output piped through sort, not a glob expansion. No null-glob issue; empty dir returns empty string, guarded by `[[ -z "$ver_dir" ]]`.

#### Quoting the "Application Support" space

The Chrome base path contains a literal space: `~/Library/Application Support/`. Every path variable that contains this path MUST be double-quoted. The pattern is:

```zsh
CHROME_BASE="$HOME/Library/Application Support/Google/Chrome"
# Always use "$CHROME_BASE" not $CHROME_BASE
# Always use "${profile_dir}/Extensions" not ${profile_dir}/Extensions
manifest="${ext_dir}${ver_dir}/manifest.json"   # both vars quoted together
```

Unquoted expansions split on spaces: `$CHROME_BASE/Default` becomes `/Users/ken/Library/Application` followed by `Support/Google/Chrome/Default` as two words. [VERIFIED: all path variables in prior phases use double-quoting]

#### Firefox path also contains a space

`~/Library/Application Support/Firefox/` has the same space issue. Same rule: always quote `"$FF_DIR/..."`.

#### Determinism confirmation

Two consecutive runs of both pipelines on an unchanged machine produce byte-identical output. [VERIFIED: both Chrome (7 extensions) and Firefox (6 addons) pipelines re-run and compared — identical]

Sources of potential non-determinism and how they are handled:
- **Filesystem glob order:** `sort -V` for version selection and `LC_ALL=C sort -f -u` in `flush_section` make the final output order independent of filesystem iteration order.
- **Locale drift:** `LC_ALL=C` locks byte-order sorting immune to macOS locale settings.
- **Extension update during run:** Extremely unlikely, but if a version dir appears mid-run, `sort -V | tail -1` would simply pick it. On re-run, the same dir would be picked again — still deterministic.

---

## Architecture Patterns

### System Architecture Diagram

```
collect_chrome_extensions()
        │
        │  1. [[ -d ~/Library/Application Support/Google/Chrome ]] || flush+return
        │
        │  2. setopt local_options null_glob
        │
        │  3. Loop: Default + Profile */ dirs with Extensions/
        │     │
        │     │  4. Loop: Extensions/*/  (null-glob guarded)
        │     │     │  Skip Temp, skip denylist IDs
        │     │     │  ver_dir = ls | sort -V | tail -1
        │     │     │  manifest = $ext_dir$ver_dir/manifest.json
        │     │     │  [[ -f manifest ]] || continue
        │     │     │
        │     │     │  name = chrome_ext_name "$manifest"   (Phase 1 helper)
        │     │     │  version = json_get "$manifest" "version"
        │     │     │
        │     │     └─ emit_item "$name" "$version" "$ext_id"
        │     │
        │     └─ (next extension ID)
        │
        └─ flush_section  (sorts _section_lines[], writes to OUTPUT_FILE, resets buffer)


collect_firefox_extensions()
        │
        │  1. [[ -f ~/Library/Application Support/Firefox/profiles.ini ]] || flush+return
        │
        │  2. Parse profiles.ini: grep '^Path=' | sed 's/^Path=//'
        │     │
        │     │  3. For each rel_path: check extensions.json exists
        │     │     │
        │     │     │  4a. jq present:
        │     │     │    jq -r '.addons[] | select(.location == "app-profile") |
        │     │     │        "\(.defaultLocale.name // .id)\t\(.version // "")\t\(.id)"'
        │     │     │    | while IFS=$'\t' read -r name version id
        │     │     │    | emit_item "$name" "$version" "$id"
        │     │     │
        │     │     └─ 4b. plutil fallback:
        │     │          idx=0 loop: plutil -extract "addons.$idx.location" ...
        │     │          filter loc=="app-profile", extract name/version/id by index
        │     │          emit_item "$name" "$version" "$id"
        │     │
        │     └─ (next profile)
        │
        └─ flush_section  (sorts _section_lines[], writes to OUTPUT_FILE, resets buffer)
```

### Recommended Project Structure

No new files. Both collector functions are added to `update-list.sh` after `collect_gemini_mcp` (the last Phase 3 collector, currently ending around line 1238) and before `generate_catalog` (line 1252):

```
update-list.sh
├── display_usage, parse_arguments, get_target_location, archive_old_catalogs  (unchanged)
├── write_section                         (unchanged)
├── json_get, chrome_ext_name, emit_item, flush_section  (Phase 1)
├── resolve_vsc_ext_name, collect_vscode_extensions, collect_cursor_extensions  (Phase 2)
├── collect_claude_plugins, collect_claude_mcp, collect_claude_skills_agents   (Phase 3)
├── collect_codex_mcp, collect_opencode_plugins, collect_opencode_mcp,         (Phase 3)
│   collect_opencode_agents, collect_gemini_extensions, collect_gemini_mcp
├── [NEW] collect_chrome_extensions       ← Phase 4
├── [NEW] collect_firefox_extensions      ← Phase 4
├── generate_catalog                      (unchanged — collectors not called yet)
├── git_pull, git_commit_and_push         (unchanged)
└── main block                            (unchanged)
```

---

## Section Writing Flow

Exact pattern mirroring Phases 2–3:

```zsh
collect_chrome_extensions() {
    local chrome_base="$HOME/Library/Application Support/Google/Chrome"
    # ... local vars ...

    write_section "Google Chrome Extensions"
    _section_lines=()   # defensive reset per Phase 1 contract

    if [[ ! -d "$chrome_base" ]]; then
        echo "  NOTE: Google Chrome not installed."
        flush_section
        return
    fi

    setopt local_options null_glob

    for profile_dir in "$chrome_base/Default" "$chrome_base"/Profile\ */; do
        [[ -d "${profile_dir}/Extensions" ]] || continue
        for ext_dir in "${profile_dir}/Extensions"/*/; do
            [[ -e "$ext_dir" ]] || continue
            # ... skip Temp, skip denylist ...
            # ... version selection ...
            # ... name resolution via chrome_ext_name ...
            emit_item "$name" "$version" "$ext_id"
        done
    done

    flush_section
}
```

Section titles (verbatim from CONTEXT.md success criteria):
- `"Google Chrome Extensions"`
- `"Firefox Extensions"`

Graceful degradation paths — all call `flush_section` which emits `(none found)`:
- Chrome base dir absent → note + flush_section
- `profiles.ini` absent (Firefox not installed) → note + flush_section
- Profile dir found but no extensions.json → skip profile (no note, just continue to next)
- Profile found, extensions.json present, zero app-profile addons → flush_section emits `(none found)`

---

## Code Examples

### collect_chrome_extensions — complete function

```zsh
# Source: verified design from live Chrome data on this machine
collect_chrome_extensions() {
    local chrome_base="$HOME/Library/Application Support/Google/Chrome"
    local ext_dir="" ext_id="" ver_dir="" manifest="" name="" version=""

    write_section "Google Chrome Extensions"
    _section_lines=()

    if [[ ! -d "$chrome_base" ]]; then
        echo "  NOTE: Google Chrome not installed."
        flush_section
        return
    fi

    setopt local_options null_glob

    for profile_dir in "$chrome_base/Default" "$chrome_base"/Profile\ */; do
        [[ -d "${profile_dir}/Extensions" ]] || continue

        for ext_dir in "${profile_dir}/Extensions"/*/; do
            [[ -e "$ext_dir" ]] || continue

            ext_id=$(basename "$ext_dir")

            # Skip Chrome's in-progress download directory
            [[ "$ext_id" == "Temp" ]] && continue

            # Skip Google component / pre-installed extensions (not user choices)
            case "$ext_id" in
                nmmhkkegccagdldgiimedpiccmgmieda|\
                ghbmnnjooekpmoecnnnilnnbdlolhkhi|\
                aapocclcgogkmnckokdopfmhonfmgoek|\
                blpcfgokakmgnkcojhhkbfbldkacnbeo|\
                felcaaldnbdncclmgdcncolpebgiejap|\
                aohghmighlieiainnegkcijnfilokake|\
                apdfllckaahabafndbhieahigkjlhalf|\
                pjkljhegncpnkpknbcohdijeoejaedia|\
                mhjfbmdgcfjbbpaeojofohoefgiehjai|\
                pkedcjkdefgpdelpbcmbmeomcjbeemfm)
                    continue ;;
            esac

            # Pick highest version dir; Chrome dirs are named <semver>_<N>
            # sort -V handles numeric comparison correctly (e.g. 14.x > 3.x > 2.x)
            ver_dir=$(ls -1 "$ext_dir" 2>/dev/null | sort -V | tail -1)
            [[ -z "$ver_dir" ]] && continue

            manifest="${ext_dir}${ver_dir}/manifest.json"
            [[ -f "$manifest" ]] || continue

            # chrome_ext_name resolves __MSG_<key>__ via _locales/; falls back to ext_id
            name=$(chrome_ext_name "$manifest")
            version=$(json_get "$manifest" "version")

            emit_item "$name" "$version" "$ext_id"
        done
    done

    flush_section
}
```

### collect_firefox_extensions — complete function

```zsh
# Source: verified design from live Firefox data on this machine
collect_firefox_extensions() {
    local ff_dir="$HOME/Library/Application Support/Firefox"
    local profiles_ini="${ff_dir}/profiles.ini"
    local rel_path="" ext_json="" name="" version="" id="" entry="" idx=0 loc=""

    write_section "Firefox Extensions"
    _section_lines=()

    if [[ ! -f "$profiles_ini" ]]; then
        echo "  NOTE: Firefox not installed."
        flush_section
        return
    fi

    # Iterate profiles from profiles.ini (Path= entries are relative to $ff_dir)
    while IFS= read -r rel_path; do
        [[ -z "$rel_path" ]] && continue
        ext_json="${ff_dir}/${rel_path}/extensions.json"
        [[ -f "$ext_json" ]] || continue

        if command -v jq &>/dev/null; then
            # jq path: array iteration + location filter in one pass
            # Tab-separated to handle spaces in addon names
            while IFS=$'\t' read -r name version id; do
                [[ -z "$id" ]] && continue
                [[ -z "$name" ]] && name="$id"
                emit_item "$name" "$version" "$id"
            done < <(jq -r '.addons[] | select(.location == "app-profile") |
                "\(.defaultLocale.name // .id)\t\(.version // "")\t\(.id)"' \
                "$ext_json" 2>/dev/null)
        else
            # plutil fallback: index-based iteration; filter location == app-profile
            idx=0
            while true; do
                loc=$(plutil -extract "addons.${idx}.location" raw -o - "$ext_json" 2>/dev/null) || break
                if [[ "$loc" == "app-profile" ]]; then
                    name=$(plutil -extract "addons.${idx}.defaultLocale.name" raw -o - "$ext_json" 2>/dev/null) || name=""
                    version=$(plutil -extract "addons.${idx}.version" raw -o - "$ext_json" 2>/dev/null) || version=""
                    id=$(plutil -extract "addons.${idx}.id" raw -o - "$ext_json" 2>/dev/null) || id=""
                    [[ -z "$id" ]] && { ((idx++)); continue; }
                    [[ -z "$name" ]] && name="$id"
                    emit_item "$name" "$version" "$id"
                fi
                ((idx++))
            done
        fi

    done < <(grep '^Path=' "$profiles_ini" 2>/dev/null | sed 's/^Path=//')

    flush_section
}
```

### Verified live output (this machine)

**Google Chrome Extensions** (7 user extensions, 2 runs — identical):
```
Bitwarden Password Manager (2026.5.1) [nngceckbapebfimnlniiiahkandclblb]
Claude (1.0.75) [fcoeoabgfenejglbffodgkkbkcdhcgfn]
Grammarly: AI Writing Assistant and Grammar Checker App (14.1302.0) [kbfnbcaeplbcioakkpcpgfkobkghlhen]
LastPass: Free Password Manager (4.154.0) [hdokiejnpimakedhajhdlcegeplioahd]
Matter (4.8.1) [knjbgabkeojmfdhindppcmhhfiembkeb]
YouTube Watch Later Cleaner (1.0.0) [cpkepcpjdmcaldbhbolnkjjelmmknfgg]
YT Watch Later Assist (3.8) [deafalnegnfhjhejolidiobnapigcfpd]
```
[VERIFIED: live run; `LC_ALL=C sort -f -u` applied; byte-identical on second run]

**Firefox Extensions** (6 app-profile addons, 2 runs — identical):
```
DuckDuckGo Search & Tracker Protection (2026.5.22) [jid1-ZAdIEUB7XOzOJw@jetpack]
Evernote Web Clipper (7.40.0) [{E0B8C461-F8FB-49b4-8373-FE32E9252800}]
Grammarly: AI Writing and Grammar Checker App (8.937.0) [87677a2c52b84ad3a151a4a72f5bd3c4@jetpack]
LastPass (4.153.1) [support@lastpass.com]
New Tab (153.1.20260528.133333) [newtab@mozilla.org]
Vue.js devtools (7.7.7) [{5caff8cc-3d2e-4110-a88a-003cc85b3858}]
```
[VERIFIED: live run; `LC_ALL=C sort -f -u` applied; byte-identical on second run]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chrome name resolution | Inline `__MSG_` extraction in the collector | `chrome_ext_name` (Phase 1 helper) | Already handles: `__MSG_` detection, `default_locale` read, `_locales` path, case-insensitive key lookup, fallback to ID — 30 lines of verified logic |
| Chrome version selection | Glob pattern like `Extensions/<id>/<version>/` | `ls | sort -V | tail -1` | Glob expansion order is not version-sorted; `sort -V` is the correct numeric-aware sort for semver dirs |
| Firefox addon iteration | Line-by-line parse of extensions.json | `jq -r '.addons[] | select(...)` | extensions.json is a real JSON array; line-by-line parsing breaks on multi-line values and special chars in names |
| Location-based filtering | `grep "app-profile" extensions.json` | `jq select(.location == "app-profile")` | Field can appear in other positions; grep produces false positives; jq selects structurally |
| Cross-profile dedup | Custom dedup logic | `flush_section` (`LC_ALL=C sort -f -u`) | Already built in Phase 1; handles duplicate and distinct-version cases correctly |
| Section emission | Direct `echo` to OUTPUT_FILE | `emit_item` + `flush_section` | FMT-01 / FMT-04 contracts; never bypass the buffer |

---

## Common Pitfalls

### Pitfall 1: Lexical sort for Chrome version dirs gives wrong order

**What goes wrong:** `ls Extensions/<id>/ | sort | tail -1` with lexical sort: `14.1302.0_0` sorts before `3.8_0` (because `'1' < '3'` lexically but `14 > 3` numerically). You pick `3.8_0` instead of `14.1302.0_0`.

**Why it happens:** Default `sort` is lexicographic. Version numbers need numeric comparison per component.

**How to avoid:** Always use `sort -V`. [VERIFIED: `14.1302.0_0` correctly sorts above `3.8_0` and `4.154.0_0` with `sort -V`]

**Warning signs:** A well-known extension appearing at an old version number when a newer version is clearly installed in Chrome.

---

### Pitfall 2: Not quoting "Application Support" path with spaces

**What goes wrong:** `for f in $CHROME_BASE/Default/Extensions/*/` — Zsh word-splits on the space in `Application Support`, producing `No such file or directory` errors for `Support/Google/Chrome/Default/Extensions/`.

**How to avoid:** Always double-quote every path variable derived from CHROME_BASE or FF_DIR. Use `"$chrome_base/Default"`, `"${profile_dir}/Extensions"`, etc.

**Warning signs:** `no such file` errors for paths that clearly exist when running the script manually.

---

### Pitfall 3: Chrome `Profile *` glob aborting when no multi-profile exists

**What goes wrong:** In Zsh without `null_glob`, `"$CHROME_BASE"/Profile\ */` expands to a literal string and causes a "no match" error, aborting the loop.

**How to avoid:** `setopt local_options null_glob` at the top of the collector function. The `local_options` flag means it's automatically unset when the function returns — no cleanup needed.

**Warning signs:** Script exits with `zsh: no matches found: .../Chrome/Profile */` for any machine with only one Chrome profile (which is most machines).

---

### Pitfall 4: Using `\n`-split or `for` loop on Firefox jq output

**What goes wrong:** `for entry in $(jq -r '.addons[] | select(.location=="app-profile") | .defaultLocale.name' file)` — word-splits on spaces in names like `"Vue.js devtools"` → `"Vue.js"` and `"devtools"` become separate iterations.

**How to avoid:** Use `while IFS=$'\t' read -r name version id` with tab-delimited jq output. Tab is a safe delimiter because addon names and IDs never contain literal tabs.

**Warning signs:** Extension names appearing truncated at the first space.

---

### Pitfall 5: Using `defaultLocale` (wrong case) instead of `defaultLocale`

**What goes wrong:** `jq '.addons[].defaultLocale.name'` returns null. Both jq and plutil are case-sensitive on JSON key names.

**How to avoid:** The correct field is `defaultLocale` (capital L). Both `jq '.addons[0].defaultLocale.name'` and `plutil -extract "addons.0.defaultLocale.name"` work correctly with the exact casing. [VERIFIED]

**Warning signs:** All Firefox addon names falling back to IDs even when `defaultLocale.name` should be present.

---

### Pitfall 6: Calling flush_section inside the profile loop

**What goes wrong:** If `flush_section` is called inside the `while IFS= read -r rel_path` loop (once per profile), the second profile's addons end up in a new section or their output replaces rather than merges with the first profile's.

**How to avoid:** Accumulate all `emit_item` calls across ALL profiles, then call `flush_section` ONCE after the outer loop exits. The `_section_lines` buffer accumulates across profiles; deduplication happens at flush time.

---

### Pitfall 7: _section_lines dirty state from previous section

**What goes wrong:** If a previous collector's `flush_section` was skipped (e.g. early return without flush), `_section_lines` retains those lines, which appear in the Chrome or Firefox section output.

**How to avoid:** `_section_lines=()` at the top of EVERY collector function (before any `emit_item` call). This is the established Phase 1 contract. [VERIFIED: all Phase 2/3 collectors follow this pattern in update-list.sh]

---

## State of the Art

| Old Approach | Current Approach | Impact |
|---|---|---|
| No browser extension cataloging | `collect_chrome_extensions` + `collect_firefox_extensions` | Complete browser extension coverage via CHR-01 + FF-01 |
| Chrome name resolution unaddressed | `chrome_ext_name` (Phase 1) resolves `__MSG_*__` | Bitwarden and Chrome Web Store Payments both resolve to real names |
| No component exclusion | 10-ID denylist via `case` statement | Chrome Web Store Payments excluded; 7 clean user extensions on this machine |
| Firefox `location` field not used | `select(.location == "app-profile")` | All 12 built-in addons (Form Autofill, PiP, themes, etc.) excluded |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | The 9 component IDs beyond `nmmhkkegccagdldgiimedpiccmgmieda` (not present on this machine) correctly identify Google-bundled extensions on machines that do have them | Flag 1 denylist | Low — a component ID in the denylist that is absent on a machine is a no-op skip. The only risk is a user-installed extension sharing a denylist ID, which is impossible because these IDs are cryptographically derived from Google's extension keys. |
| A2 | `sort -V` is available on all macOS versions this script targets | Flag 2 version selection | Very low — `sort -V` is present in macOS BSD sort since at least macOS 10.13 (2017). The project's macOS-only constraint makes this safe. |
| A3 | Firefox `extensions.json` `location=="app-profile"` remains the correct filter for user-installed addons in current and future Firefox versions | Flag 3 | Low — this is Firefox's public add-on API field. Location values documented in Firefox source. Filter would need updating only if Mozilla redesigns the add-on storage format. |

---

## Open Questions

None — all 5 research flags are fully answered with live verification.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| `jq` | Chrome name field extraction, Firefox addon array iteration | Yes (Homebrew) | `jq-1.8.1` | `plutil` |
| `plutil` | JSON scalar extraction (fallback backend) | Yes (macOS built-in) | macOS 26.5 build | — (always present) |
| `sort -V` | Chrome version dir selection | Yes (macOS BSD sort) | macOS 26.5 build | — (always present on macOS) |
| `Google Chrome` | `collect_chrome_extensions` | Yes | `~/Library/Application Support/Google/Chrome/` exists | `flush_section` writes `(none found)` |
| `Firefox` | `collect_firefox_extensions` | Yes | `profiles.ini` + `rv4siqj3.default-release/extensions.json` confirmed | `flush_section` writes `(none found)` |
| Chrome `Default` profile | `collect_chrome_extensions` | Yes | 8 extension dirs (7 user) | Skip profile, continue |
| Firefox `default-release` profile | `collect_firefox_extensions` | Yes | 6 app-profile addons | Skip profile if no extensions.json |

**Missing dependencies with no fallback:** None. Both plutil and sort -V are always present on macOS.

---

## Validation Architecture

`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json` — this section is skipped.

---

## Security Domain

This phase adds zero-network, zero-credentials, zero-secrets code. Extension names, versions, and IDs are all public metadata — they are exactly what appears in the Chrome Web Store and Firefox Add-ons pages. No ASVS categories apply.

The catalog output for these sections is public metadata already committed to git by the existing script. No FMT-03 concern — browser extension IDs and names do not contain credentials.

---

## Sources

### Primary (HIGH confidence)

- Live macOS 26.5 machine — all commands verified in this research session:
  - Chrome: all 8 extension dirs enumerated; manifests read; `__MSG_` resolution verified on `nngceckbapebfimnlniiiahkandclblb` (Bitwarden) and `nmmhkkegccagdldgiimedpiccmgmieda` (Web Store Payments)
  - `sort -V` behavior on Chrome version dirs: `1.0.0_0`, `3.8_0`, `14.1302.0_0`, `2026.5.1_0` — verified correct ordering
  - Zsh `null_glob` + `"Profile *"` glob: verified returns no error when no Profile dirs exist
  - Firefox: `profiles.ini` Path= extraction; `rv4siqj3.default-release/extensions.json` location breakdown (6 app-profile, 5 app-builtin, 7 app-builtin-addons); jq tab-separated extraction with `while IFS=$'\t'` read; plutil index-loop fallback
  - `plutil -extract "addons.0.defaultLocale.name"` on Firefox extensions.json: verified working
  - `LC_ALL=C sort -f -u` dedup: same-extension-same-version collapses to one line; same-extension-different-versions produces two lines — both verified
  - Determinism: both pipelines run twice, output byte-identical

- `update-list.sh` (live script, lines 259–1238) — Phase 1–3 helpers confirmed present; `chrome_ext_name` function confirmed at line 327; collector pattern from `collect_gemini_mcp` used as template

- Phase 1 RESEARCH.md (`01-RESEARCH.md`) — `chrome_ext_name` algorithm specification + verified Bitwarden resolution; `emit_item`/`flush_section` contract

- Phase 2 RESEARCH.md (`02-RESEARCH.md`) — established `setopt local_options null_glob` + `[[ -e "$f" ]] || continue` null-glob guard pattern; `write_section` → `_section_lines=()` → loop → `flush_section` section flow

### Secondary (MEDIUM confidence)

- [jamieweb.net/info/chrome-extension-ids/](https://www.jamieweb.net/info/chrome-extension-ids/) [CITED] — canonical list of Google-built Chrome extensions; cross-verified `nmmhkkegccagdldgiimedpiccmgmieda` as "Google Wallet / Chrome Web Store Payments" (confirmed matches this machine's manifest content)

---

## Metadata

**Confidence breakdown:**
- Chrome component denylist: HIGH — confirmed on this machine; jamieweb.net source cross-references the IDs; 9 of 10 IDs absent on this machine but all match known Google components
- Chrome profile enumeration + version selection: HIGH — live test confirmed; `sort -V` verified on real dirs
- chrome_ext_name integration: HIGH — Phase 1 function already in script; Bitwarden re-verified
- Firefox profiles.ini parsing: HIGH — live verification; both profiles discovered correctly
- Firefox extensions.json location filter: HIGH — all 18 addons classified by location; 6 app-profile confirmed
- plutil Firefox fallback: HIGH — `addons.N.defaultLocale.name` path confirmed working
- Determinism: HIGH — two consecutive runs produced byte-identical output for both browsers

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (Chrome manifest format and Firefox extensions.json schema are stable; location field values are part of Firefox's public add-on API)

---

## RESEARCH COMPLETE

**Phase:** 04 - Browser Collectors
**Confidence:** HIGH

### Key Findings

1. **Chrome denylist: 10 component IDs confirmed, 1 present on this machine.** `nmmhkkegccagdldgiimedpiccmgmieda` (Chrome Web Store Payments / Google Wallet) is the only component on this machine. The full 10-ID denylist covers Google Docs Offline, Google Drive/Docs/Sheets/Slides offline components, Chrome PDF Viewer, Chrome Cast, and YouTube — all present on some machines. The `case` statement implementation is the simplest correct approach for a short fixed list.

2. **`sort -V` is the correct and only safe version-sort for Chrome dirs.** Chrome version dirs like `3.8_0`, `14.1302.0_0`, `2026.5.1_0` require numeric-aware version sort. `sort` (lexical) gives wrong results for dirs where the major version has 2+ digits. `sort -V | tail -1` selects the highest version correctly in all tested cases.

3. **`chrome_ext_name` resolves both `__MSG_` extensions correctly.** Bitwarden (`__MSG_extName__` → `"Bitwarden Password Manager"`) confirmed again in this session. The Web Store Payments (`__MSG_APP_NAME__` → `"Chrome Web Store Payments"`) also resolves via the case-insensitive lookup (APP_NAME → app_name), but is excluded by the denylist. 7 clean user extensions after exclusion.

4. **Firefox `location=="app-profile"` is the correct and sufficient filter.** 18 total addons split as: 6 user-installed (app-profile) + 7 built-in functional add-ons (app-builtin-addons: Form Autofill, PiP, etc.) + 5 built-in themes/system (app-builtin). The filter correctly excludes all 12 non-user addons in one condition. All 4 themes on this machine are `app-builtin` — the include-themes decision is correct (themes can be user-installed on other machines) but has zero effect here.

5. **plutil CAN handle Firefox's nested `defaultLocale.name` field** via the path `addons.N.defaultLocale.name`. The plutil fallback loop is viable (verified on all 18 addons). jq is preferred for performance (single pass vs N×4 plutil calls), but the fallback is fully functional.

### File Created

`.planning/phases/04-browser-collectors/04-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|---|---|---|
| Chrome component denylist | HIGH | 1 of 10 IDs present on machine; all 10 cross-verified against jamieweb.net source |
| Chrome version selection | HIGH | `sort -V` verified on all 7 real Chrome version dirs |
| chrome_ext_name integration | HIGH | Function already in script; end-to-end pipeline verified |
| Firefox profile iteration | HIGH | profiles.ini parsing verified; both profiles found |
| Firefox location filter | HIGH | All 18 addons classified; 6 app-profile confirmed correct |
| plutil Firefox fallback | HIGH | Index loop verified on all 18 addons |
| Determinism | HIGH | Two consecutive runs → byte-identical output for both browsers |

### Open Questions

None. All 5 research flags answered with live verification.

### Ready for Planning

Research complete. Planner can now create PLAN.md files.
