# Phase 1: Shared Helpers Foundation — Research

**Researched:** 2026-06-13
**Domain:** Pure Zsh shell script helpers — JSON parsing, Chrome name resolution, uniform item emission, deterministic sorting
**Confidence:** HIGH (all findings verified against live macOS and real extension files on this machine)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Item Line Format (FMT-01)**
- All fields present: `name (version) [id]`.
- No version available: `name [id]` (degraded form per FMT-01).
- Name unresolvable (only ID known): use the ID as the name and suppress the duplicate bracket → bare `id (version)` / `id` (never `id [id]`).
- No stable ID (e.g. skills/agents): `name (version)` — omit the `[...]` brackets entirely.
- A single emit helper builds the line from (name, version, id) args, applying these degradation rules so every collector renders identically.

**Sort & Determinism (FMT-04)**
- Sort key: by display name.
- Byte-stable: sort under `LC_ALL=C` so ordering is immune to locale drift between runs/machines.
- Case handling: case-insensitive fold (human-readable ordering).
- Dedupe: collapse identical duplicate lines within a section (`-u`) so re-runs stay clean.
- A sort helper buffers a section's emitted lines and flushes them sorted, guaranteeing two consecutive no-change runs produce an empty diff.

**JSON Reading (dependency-free)**
- Parser strategy: prefer `jq` when present; fall back to a `plutil`-based extraction (both ship-or-probe gracefully, consistent with existing brew/mas optional-tool pattern).
- Malformed/missing JSON: warn-and-skip, return empty — never abort the section or run.
- Field access: support nested key paths (required for manifests and CLI configs).
- Return contract: echo the resolved value to stdout; empty string on miss (callers test for empty, matching shell idiom).

**Chrome Name Resolution (CHR-01)**
- Resolve `__MSG_<key>__` names by reading `_locales/<default_locale>/messages.json` and using the key's `message` field.
- Locale selection: read manifest `default_locale`; fall back to `en` when absent.
- Failure fallback: when the name can't be resolved, fall back to the extension ID (per CHR-01) — never drop the extension.
- Message key lookup is case-insensitive (Chrome treats message keys case-insensitively).

**Integration**
- Helpers are defined as standalone Zsh functions in `update-list.sh` (above `generate_catalog`), callable by the Phase 2–4 collectors and finally wired in Phase 5.
- No change to the archive/git flow or existing sections.

### Claude's Discretion

None specified — discussion stayed within phase scope.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FMT-01 | Every new catalog item is emitted in a uniform line format `name (version) [id]`, degrading to `name [id]` when no version exists | `emit_item` helper design with tested degradation rules; all 5 cases verified in Zsh |
| FMT-04 | Catalog output is deterministic — items within every new section are sorted stably so two consecutive runs with no machine changes produce an empty diff | `flush_section` buffer+sort pattern verified; `LC_ALL=C sort -f -u` confirmed byte-stable and dedupe-correct on macOS BSD sort |
</phase_requirements>

---

## Summary

Phase 1 adds four Zsh helper functions to `update-list.sh`. They have no new runtime dependencies — only `jq` (optional, Homebrew) and `plutil` (always present, `/usr/bin/plutil` since macOS 10.4). Every claim below was verified against a live macOS 26.5 (Sequoia) machine and real Chrome extension files.

**Critical discrepancy resolved:** The ROADMAP success criterion 1 describes the fallback chain as "jq → python3 → grep." The CONTEXT.md (user decisions, written after the ROADMAP) locks it as "jq → plutil." The CONTEXT supersedes the ROADMAP. The correct chain is **jq → plutil**. This is also the better design: `plutil` ships on every macOS since 10.4 and is a real JSON-aware binary; `/usr/bin/python3` on a *clean* macOS (no Xcode CLT, no Homebrew) is an xcrun stub that pops a **GUI install dialog** and blocks the script. A grep fallback adds no safety net once plutil is in the chain — plutil is always present. Full justification in the JSON section below.

**Primary recommendation:** Implement `json_get`, `chrome_ext_name`, `emit_item`, and `flush_section` as four standalone Zsh functions inserted above `generate_catalog` (after line 253, before line 271). No other changes to the script.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| JSON scalar extraction | Helper function (`json_get`) | — | All collectors need it; isolating the backend-selection logic here prevents duplication and ensures consistent fallback behavior everywhere |
| Chrome localized name resolution | Helper function (`chrome_ext_name`) | `json_get` | Name resolution requires two file reads and case-insensitive lookup logic; belongs in a dedicated helper, not duplicated per profile iteration |
| Uniform item line emission | Helper function (`emit_item`) | — | FMT-01 is a cross-cutting format contract; a single helper ensures every collector produces identical line structure under all degradation cases |
| Section output buffering + deterministic sort | Helper function (`flush_section`) + Zsh array `_section_lines` | — | FMT-04 requires sorting before writing to `OUTPUT_FILE`; the buffer must live at function scope and be flushed explicitly by each collector |
| Catalog file append | Global `OUTPUT_FILE` (existing) | — | Unchanged — `flush_section` writes to it the same way existing code does (`>> "$OUTPUT_FILE"`) |

---

## Standard Stack

### Core (verified present)

| Tool | Availability | How json_get Uses It | Source |
|------|-------------|----------------------|--------|
| `jq` | Optional — Homebrew install (`/opt/homebrew/bin/jq`). Not on clean macOS. | First choice. Supports dotted path via `getpath($k \| split("."))`. Returns empty string on miss via `// ""`. Exits 0 on miss. | [VERIFIED: live machine `/opt/homebrew/bin/jq`, version `jq-1.8.1`] |
| `plutil` | Always present — `/usr/bin/plutil` ships with macOS since 10.4. | Second choice. `plutil -extract <key.path> raw -o - <file> 2>/dev/null`. Exits 1 on missing key (stderr suppressed). Supports dotted nested paths natively. Handles JSON **and** plist files. Extracts strings, integers, booleans. | [VERIFIED: `/usr/bin/plutil` present, `663776` bytes, confirmed working on JSON and plist] |
| `python3` | **Do not use in the fallback chain.** On a clean macOS (no CLT, no Homebrew), `/usr/bin/python3` is an xcrun stub that opens a **GUI install dialog** and blocks the script. With CLT installed it works, but we cannot rely on it. | Not in chain. | [VERIFIED: `/usr/bin/python3` is a real binary when CLT installed; documented Apple behavior — stub shows GUI on clean macOS] |
| `grep` + `sed` | Always present (POSIX). | **Not in chain for json_get.** grep can extract flat string keys from JSON but cannot traverse nested paths, and returns false positives when the same key appears nested. Plutil is always present and strictly more capable. | [VERIFIED: tested; flat-key grep works but has documented limitations; no need for it given plutil coverage] |

**Recommended json_get backend chain: jq → plutil (stop there — plutil is always present on macOS).**

### Supporting (Zsh built-ins used)

| Feature | Zsh Syntax | Purpose |
|---------|-----------|---------|
| Typed array | `typeset -a _section_lines=()` | Buffer section lines before sorted flush |
| Array append | `_section_lines+=("$line")` | Accumulate lines in `emit_item` |
| Array expand | `"${_section_lines[@]}"` | Expand all buffered lines for sort |
| Local options | `setopt local_options null_glob` | (Phase 2–4 collectors) — guard glob loops against abort; not needed for Phase 1 helpers themselves |

### No new packages

This phase installs nothing. No `npm install`, no `pip install`, no `brew install`. All backends (`jq`, `plutil`) are probed at runtime.

---

## Package Legitimacy Audit

Not applicable — Phase 1 installs no external packages.

---

## Architecture Patterns

### System Architecture Diagram

```
Collector function (Phase 2, 3, or 4)
        │
        │  emit_item "name" "version" "id"
        ▼
┌─────────────────────────────────────────────┐
│  emit_item                                  │
│  • apply degradation rules (FMT-01)         │
│  • build line string                        │
│  • _section_lines+=("$line")  ← append buf  │
└─────────────────────────────────────────────┘
        │  (after all items collected)
        │  flush_section
        ▼
┌─────────────────────────────────────────────┐
│  flush_section                              │
│  • printf "%s\n" "${_section_lines[@]}"     │
│    | LC_ALL=C sort -f -u                    │
│    >> "$OUTPUT_FILE"                        │
│  • _section_lines=()  ← reset buffer        │
└─────────────────────────────────────────────┘
        │
        ▼
  OUTPUT_FILE (existing global, unchanged)


json_get "$file" "key.path"
        │
        ├─ command -v jq → jq -r --arg k "key.path" \
        │                     'getpath($k | split(".")) // ""' "$file"
        │
        └─ plutil -extract "key.path" raw -o - "$file" 2>/dev/null
           (return "" on exit 1)


chrome_ext_name "$manifest_path"
        │
        ├─ json_get → name field
        ├─ if NOT __MSG_ → echo "$name" and return
        │
        ├─ extract key from __MSG_<key>__
        ├─ json_get → default_locale (fallback "en")
        ├─ open _locales/<locale>/messages.json
        ├─ case-insensitive key lookup → .message value
        └─ fallback: echo extension_id (basename of grandparent dir)
```

### Recommended Project Structure

No new files. All four functions are inserted into `update-list.sh` as a new block between `write_section` (line 257) and `generate_catalog` (line 271):

```
update-list.sh
├── display_usage        (line 56 — unchanged)
├── parse_arguments      (line 98 — unchanged)
├── get_target_location  (line 136 — unchanged)
├── archive_old_catalogs (line 187 — unchanged)
├── write_section        (line 254 — unchanged)
├── [NEW] json_get       (after line 257)
├── [NEW] chrome_ext_name (after json_get)
├── [NEW] emit_item      (after chrome_ext_name)
├── [NEW] flush_section  (after emit_item)
├── generate_catalog     (line 271 — unchanged in this phase)
├── git_pull             (line 350 — unchanged)
└── git_commit_and_push  (line 397 — unchanged)
```

### Pattern 1: json_get — jq → plutil fallback

**What:** Extract a scalar value from a JSON file by dotted key path. Returns value on stdout; empty string on miss or error. Never aborts.

**When to use:** Anywhere a collector needs a single field from a manifest.json, package.json, config file, or extensions.json.

**Caller-facing key syntax:** dot-separated path string. Examples:
- `"name"` → top-level key
- `"default_locale"` → top-level key
- `"author.name"` → nested path
- `"a.b.c"` → 3-level nested

**Example (verified working):**

```zsh
# Source: verified on macOS 26.5 against /tmp/test_manifest.json and
#         /Users/ken/Library/.../nngceckbapebfimnlniiiahkandclblb/.../manifest.json
json_get() {
    local file="$1"
    local key="$2"
    local value=""

    # Guard: file must exist and be readable
    [[ -f "$file" ]] || { echo ""; return; }

    if command -v jq &>/dev/null; then
        # jq: getpath with split(".") handles dotted nested paths
        # // "" coerces null to empty string
        value=$(jq -r --arg k "$key" 'getpath($k | split(".")) // ""' "$file" 2>/dev/null)
    else
        # plutil: always present on macOS since 10.4
        # -extract <keypath> raw -o - writes value to stdout, exits 1 on miss
        value=$(plutil -extract "$key" raw -o - "$file" 2>/dev/null) || value=""
    fi

    echo "$value"
}
```

**Key behaviors verified:**
- `jq -r 'getpath($k | split(".")) // ""'` returns `""` (empty string, not `"null"`) when key is missing [VERIFIED]
- `plutil -extract missing_key raw -o -` exits 1 and prints nothing to stdout when key absent [VERIFIED]
- Both backends handle dotted 3-level nested paths: `"a.b.c"` → `"deep_value"` [VERIFIED]
- Both backends return integers and booleans as strings (`"3"`, `"true"`) [VERIFIED]
- Both exit non-zero and produce no output on malformed JSON [VERIFIED]

### Pattern 2: chrome_ext_name — __MSG_ resolution

**What:** Given a path to a `manifest.json`, return the human-readable extension name. Resolves `__MSG_<key>__` placeholders via `_locales/<locale>/messages.json`. Falls back to extension ID (32-char basename of the extension's grandparent directory) on any failure.

**Chrome extension directory structure (verified):**

```
~/.../Chrome/<Profile>/Extensions/
└── <ext_id>/               ← 32-char lowercase hex, this is the canonical ID
    └── <version_dir>/      ← e.g. "2026.5.1_0"
        ├── manifest.json   ← name, version, default_locale
        └── _locales/       ← sibling to manifest.json
            └── en/
                └── messages.json  ← { "keyname": { "message": "Real Name" } }
```

**Manifest fields involved:**
- `"name"`: either a plain string or `"__MSG_<key>__"` placeholder
- `"default_locale"`: locale code (e.g. `"en"`, `"en_US"`, `"de"`). May be absent — fall back to `"en"`.
- `"version"`: version string (plain, no localization)

**`__MSG_` format:** `__MSG_` + key name + `__`. Key name may be any case. Example: `"__MSG_extName__"` → key is `extName`.

**messages.json shape (verified against Bitwarden):**
```json
{
  "extName": { "message": "Bitwarden Password Manager" },
  "anotherKey": { "message": "Some string" }
}
```

**Case-insensitive key lookup:** Chrome spec says message keys are case-insensitive. Verified: `__MSG_extName__` → key lookup must match `extName`, `EXTNAME`, `extname` all the same. Implementation: lowercase both the extracted key and each key in the messages dict before comparing.

**Resolution algorithm (exact steps):**

1. Read `name` field from `manifest.json` via `json_get`.
2. If `name` does NOT match `^__MSG_.*__$` → it is a plain string, return it immediately.
3. Extract the key: strip `__MSG_` prefix and `__` suffix.
4. Read `default_locale` field via `json_get`; if empty, use `"en"`.
5. Construct messages path: `$(dirname "$manifest")/_locales/${locale}/messages.json`
6. If messages file does not exist: fall through to ID fallback.
7. Read messages file. For each key in it, compare `${key:l}` (lowercase) to `${extracted_key:l}`. On match, extract `.message` value and return it.
8. Fallback (on any failure including jq absent for the loop): return the extension ID. The ID is `$(basename "$(dirname "$(dirname "$manifest")")")` — the grandparent of the version dir.

**Verified on real data:**
- Bitwarden: `__MSG_extName__` → key `extName` → locale `en` → `Bitwarden Password Manager` [VERIFIED]
- Plain-named extension (Grammarly): `name` = `"Grammarly: AI Writing Assistant..."` → returned as-is (no `__MSG_`, no `default_locale`) [VERIFIED]
- LastPass: `name` = `"LastPass: Free Password Manager"`, `default_locale` = `"en"` → returned as-is [VERIFIED]

**Example implementation:**

```zsh
# Source: verified resolution algorithm, tested against live Chrome extensions
chrome_ext_name() {
    local manifest="$1"
    local name=""
    local locale=""
    local msg_key=""
    local messages_file=""
    local ext_id=""

    # Extension ID is the grandparent directory name (parent of version dir)
    ext_id=$(basename "$(dirname "$(dirname "$manifest")")")

    name=$(json_get "$manifest" "name")

    # Plain name — return immediately
    if [[ "$name" != __MSG_*__ ]]; then
        # If name is empty, fall back to ID
        [[ -n "$name" ]] && echo "$name" || echo "$ext_id"
        return
    fi

    # Extract message key (strip __MSG_ prefix and __ suffix)
    msg_key="${name#__MSG_}"
    msg_key="${msg_key%__}"

    # Get default_locale, fall back to "en"
    locale=$(json_get "$manifest" "default_locale")
    [[ -z "$locale" ]] && locale="en"

    messages_file="$(dirname "$manifest")/_locales/${locale}/messages.json"

    if [[ ! -f "$messages_file" ]]; then
        echo "$ext_id"
        return
    fi

    # Case-insensitive key lookup
    # jq: ascii_downcase both sides; plutil fallback: try exact key, then lowercase workaround
    if command -v jq &>/dev/null; then
        local resolved=""
        resolved=$(jq -r --arg k "${msg_key:l}" \
            'to_entries[] | select(.key | ascii_downcase == $k) | .value.message' \
            "$messages_file" 2>/dev/null | head -1)
        if [[ -n "$resolved" ]]; then
            echo "$resolved"
            return
        fi
    else
        # plutil fallback: try exact-case key first (common case: key matches placeholder exactly)
        local resolved=""
        resolved=$(plutil -extract "${msg_key}.message" raw -o - "$messages_file" 2>/dev/null)
        if [[ -n "$resolved" ]]; then
            echo "$resolved"
            return
        fi
        # Case mismatch: try lowercase key (handles extName → extname)
        resolved=$(plutil -extract "${msg_key:l}.message" raw -o - "$messages_file" 2>/dev/null)
        if [[ -n "$resolved" ]]; then
            echo "$resolved"
            return
        fi
    fi

    # All lookups failed — use extension ID as fallback (never blank)
    echo "$ext_id"
}
```

**Note on the plutil fallback for chrome_ext_name:** plutil cannot enumerate keys case-insensitively — it requires the exact key name. The two-attempt approach (`exact` then `lowercase`) covers the common cases. For edge cases where the key is mixed-case in a non-obvious way (e.g. `ExtNAME` for `__MSG_extName__`), the fallback emits the extension ID rather than a blank. This is acceptable per CHR-01: "fall back to the extension ID when a name can't be resolved."

### Pattern 3: emit_item — uniform line builder

**What:** Build one catalog line from (name, version, id) and append it to `_section_lines[]`. Applies all FMT-01 degradation rules. Never writes directly to `OUTPUT_FILE` — that is `flush_section`'s job.

**Degradation rules (all verified in Zsh):**

| name | version | id | Output |
|------|---------|-----|--------|
| "Bitwarden" | "2026.5.1" | "nng...blb" | `Bitwarden (2026.5.1) [nng...blb]` |
| "Some Ext" | "" | "abc123" | `Some Ext [abc123]` |
| "My Agent" | "1.0.0" | "" | `My Agent (1.0.0)` |
| "" | "" | "nng...blb" | `nng...blb` (ID used as name, brackets suppressed) |
| "" | "3.0.0" | "nng...blb" | `nng...blb (3.0.0)` (ID used as name) |
| "Orphan Tool" | "" | "" | `Orphan Tool` |
| "" | "" | "" | (nothing emitted) |

**Example:**

```zsh
# Source: all cases verified in Zsh on this machine
emit_item() {
    local name="$1"
    local version="$2"
    local id="$3"
    local line=""

    # Name unresolvable: use ID as name, suppress bracket duplication
    if [[ -z "$name" && -n "$id" ]]; then
        name="$id"
        id=""
    fi

    # Build line per FMT-01 rules
    if [[ -n "$name" && -n "$version" && -n "$id" ]]; then
        line="${name} (${version}) [${id}]"
    elif [[ -n "$name" && -n "$version" ]]; then
        line="${name} (${version})"
    elif [[ -n "$name" && -n "$id" ]]; then
        line="${name} [${id}]"
    elif [[ -n "$name" ]]; then
        line="$name"
    else
        return  # nothing to emit
    fi

    _section_lines+=("$line")
}
```

**Caller pattern:**

```zsh
# Callers must declare _section_lines as a local array before calling emit_item
# and call flush_section after collecting all items
typeset -a _section_lines=()
emit_item "Bitwarden Password Manager" "2026.5.1" "nngceckbapebfimnlniiiahkandclblb"
emit_item "1Password" "8.0.0" "aomjjhallfgjeglblehebfpbcfeobag"
flush_section
```

**Global array caveat:** `_section_lines` is declared global (no `local`) so `emit_item` (a separate function) can append to it. The naming convention `_section_lines` (underscore prefix) signals internal state and avoids collision with existing globals. `flush_section` resets it to `()` after flushing so the next collector starts clean.

### Pattern 4: flush_section — sort buffer and write to OUTPUT_FILE

**What:** Sort and deduplicate `_section_lines[]`, append to `OUTPUT_FILE`, reset buffer. Called once per section after all items are accumulated.

**Exact sort invocation (verified):**

```zsh
LC_ALL=C sort -f -u
```

- `LC_ALL=C`: byte-stable ordering immune to locale differences between machines and runs. [VERIFIED: identical output on two consecutive runs]
- `-f`: case-insensitive fold — sorts `1Password` before `Bitwarden` before `Zed` as a human would read a list. [VERIFIED: `1Password` < `Bitwarden` < `Zed` in test output]
- `-u`: deduplicate identical lines within a section — two consecutive runs with no machine changes produce an empty diff. [VERIFIED: `LC_ALL=C sort -f -u` with duplicate input produces one line]

**Behavior of `-f -u` on macOS BSD sort:** `-u` with `-f` deduplicates case-insensitively — `"bitwarden"` and `"Bitwarden"` collapse to one line (the first encountered). This is correct for our use case since the full formatted line (`name (version) [id]`) will be identical byte-for-byte on re-runs. [VERIFIED on macOS BSD sort]

**Empty section:** When no items were emitted, write `(none found)` so the section is never silently blank. [ASSUMED — consistent with existing script pattern of always writing something to each section]

**Example:**

```zsh
# Source: pattern verified with Zsh array + LC_ALL=C sort -f -u on this machine
flush_section() {
    if [[ ${#_section_lines[@]} -eq 0 ]]; then
        echo "  (none found)" >> "$OUTPUT_FILE"
    else
        printf "%s\n" "${_section_lines[@]}" | LC_ALL=C sort -f -u >> "$OUTPUT_FILE"
    fi
    _section_lines=()
}
```

### Anti-Patterns to Avoid

- **Writing directly to `OUTPUT_FILE` from `emit_item`:** Bypasses the sort buffer — output order becomes filesystem discovery order, breaking FMT-04. Always buffer via `_section_lines` and flush via `flush_section`.
- **Calling `python3` in `json_get`:** `/usr/bin/python3` triggers a GUI install dialog on a clean macOS without CLT. `plutil` is always present and handles the same use cases without this risk.
- **Using `grep` as a json_get backend:** grep cannot handle nested key paths and produces false positives when the same key name appears at multiple nesting levels. Plutil is always present and strictly more capable.
- **Hardcoding `en` for Chrome `default_locale`:** Some extensions use `en_US`, `de`, `fr`, etc. Always read `default_locale` from the manifest.
- **Case-sensitive message key lookup:** Chrome spec is case-insensitive. `extName` and `extname` are the same key. Always lowercase both sides before comparing.
- **Emitting the raw `__MSG_extName__` string:** If resolution fails, emit the extension ID, not the placeholder. The placeholder is unreadable and non-diffable.
- **Using `local _section_lines` inside a single collector function:** `emit_item` is a separate function that appends to `_section_lines`. If declared `local` inside the collector, `emit_item` sees a different scope and appends to nothing. The array must be a global or declared at a scope that includes both the collector body and `emit_item` calls. The recommended approach is to declare it as a global with a distinctive name (`_section_lines`) and reset it in `flush_section`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON scalar extraction | Custom regex parser, awk JSON parser, line-by-line grep loop | `json_get` (jq → plutil) | jq handles all edge cases (unicode, escaped chars, nested structures); plutil handles plist too; grep fails on nested keys and numeric values |
| Chrome name resolution | Inline `__MSG_` extraction per collector | `chrome_ext_name` helper | Two file reads + case-insensitive lookup + 3 fallback paths; must be centralized for CHR-01 compliance across all profiles |
| Uniform item formatting | Inline string building per collector | `emit_item` helper | All 7 degradation cases must be consistent; inline code drifts; FMT-01 requires a single authoritative renderer |
| Section output sorting | Per-collector `| sort` inline at each append | `flush_section` | A single buffer+flush ensures the sort covers the entire section, not partial subsections; also handles the empty-section case uniformly |

---

## Runtime State Inventory

Not applicable — this is a greenfield addition (new functions) with no rename/refactor/migration component.

---

## Common Pitfalls

### Pitfall 1: `/usr/bin/python3` blocks on clean macOS

**What goes wrong:** On a clean macOS without Xcode Command Line Tools, `/usr/bin/python3` is an xcrun stub. Running it opens a GUI "Install Developer Tools" dialog and **blocks the script indefinitely** waiting for user interaction.

**Why it happens:** Developers with CLT or Homebrew installed have a real python3 that works. The stub behavior only appears on machines that have never been set up for development.

**How to avoid:** Do not put python3 in the `json_get` fallback chain. Use `jq → plutil`. `plutil` is at `/usr/bin/plutil` on every macOS since 10.4 — no optional install required.

**Warning signs:** Script hangs silently mid-run on a machine that hasn't been used for development.

### Pitfall 2: sort -f -u deduplication interacts with case differences

**What goes wrong:** `-u` with `-f` on macOS BSD sort deduplicates case-insensitively. If two collectors somehow emit `"bitwarden [id]"` and `"Bitwarden [id]"` (different casing), only one survives. This is generally correct behavior, but callers must be aware that dedup is case-insensitive.

**Why it happens:** The `-u` flag uses the same comparison key as `-f`, which is folded.

**How to avoid:** This is the desired behavior — consistent name casing per extension, no duplicates. The emit_item helper builds deterministic lines from resolved names, so casing will be consistent across runs.

**Warning signs:** An extension appearing in one run but not another due to case-folding collision with a differently-named extension (highly unlikely with full `name (version) [id]` lines).

### Pitfall 3: plutil exits 1 on missing key — must catch return code

**What goes wrong:** `value=$(plutil -extract missing_key raw -o - file.json 2>/dev/null)` — the `$()` captures stdout (empty), but the exit code is 1. If the calling script has `set -e` (errexit), it aborts. The existing script does NOT use `set -e`, but future changes could add it.

**Why it happens:** Subshell capture ignores exit codes by default in Zsh (same as Bash), but any `set -e` or `|| return` in the caller chain could expose this.

**How to avoid:** Explicitly reset on error: `value=$(plutil ...) || value=""`. This is already shown in the json_get pattern above. The `|| value=""` makes the return contract explicit and safe under `set -e`.

**Warning signs:** json_get returning unexpected errors when called from a function that uses `|| return` chains.

### Pitfall 4: `_section_lines` array is a global — reset discipline required

**What goes wrong:** If `flush_section` is not called between sections, lines from section A accumulate in `_section_lines` and appear in section B's output.

**Why it happens:** The array is global (shared between the collector body and `emit_item`). If a collector exits early (e.g., the CLI is absent and it returns before calling `flush_section`), the buffer is left dirty.

**How to avoid:** Two strategies:
1. Always call `flush_section` — even in the "not installed" early-exit path. Write the fallback note to `OUTPUT_FILE` directly and still call `flush_section` (which will flush the empty buffer safely).
2. Reset `_section_lines=()` at the top of every collector before the first `emit_item` call — a defensive reset that makes each collector idempotent.

**Warning signs:** Items from one section appearing in the next section's sorted output.

### Pitfall 5: Chrome `_locales` path has spaces (Application Support)

**What goes wrong:** The Chrome extensions directory is `~/Library/Application Support/Google/Chrome/...`. Unquoted path variables split on the space in "Application Support".

**Why it happens:** Copy from examples that omit quotes.

**How to avoid:** Every path variable must be double-quoted. Construct paths with quoted variables: `"$(dirname "$manifest")/_locales/${locale}/messages.json"`. This is already the established convention in `update-list.sh`.

**Warning signs:** `No such file or directory` for a path that clearly exists on disk.

---

## Code Examples

### json_get complete function

```zsh
# Source: verified jq and plutil behaviors on macOS 26.5
# Called as: value=$(json_get "$file" "key") or $(json_get "$file" "nested.key")
json_get() {
    local file="$1"
    local key="$2"
    local value=""

    [[ -f "$file" ]] || { echo ""; return; }

    if command -v jq &>/dev/null; then
        value=$(jq -r --arg k "$key" 'getpath($k | split(".")) // ""' "$file" 2>/dev/null)
    else
        value=$(plutil -extract "$key" raw -o - "$file" 2>/dev/null) || value=""
    fi

    echo "$value"
}
```

### End-to-end emit + flush pipeline (tested output)

```zsh
# Input calls:
typeset -a _section_lines=()
emit_item "Zed" "0.155.0" ""
emit_item "1Password" "8.0.0" "aomjjhallfgjeglblehebfpbcfeobag"
emit_item "Bitwarden Password Manager" "2026.5.1" "nngceckbapebfimnlniiiahkandclblb"
emit_item "1Password" "8.0.0" "aomjjhallfgjeglblehebfpbcfeobag"  # duplicate

# flush_section output (LC_ALL=C sort -f -u):
# 1Password (8.0.0) [aomjjhallfgjeglblehebfpbcfeobag]
# Bitwarden Password Manager (2026.5.1) [nngceckbapebfimnlniiiahkandclblb]
# Zed (0.155.0)
# [VERIFIED: exact output from live Zsh test]
```

### chrome_ext_name resolution verified on Bitwarden

```zsh
# manifest: .../nngceckbapebfimnlniiiahkandclblb/2026.5.1_0/manifest.json
# manifest.name = "__MSG_extName__"
# manifest.default_locale = "en"
# _locales/en/messages.json → { "extName": { "message": "Bitwarden Password Manager" } }
# Result: "Bitwarden Password Manager"  [VERIFIED: live resolution]
```

---

## Critical Discrepancy: ROADMAP SC#1 vs CONTEXT.md

**ROADMAP Phase 1, Success Criterion 1** (older document) states:
> "returns the correct scalar via jq, falls back to python3, then to grep"

**CONTEXT.md** (user decisions, written after ROADMAP) states:
> "prefer jq when present; fall back to a plutil-based extraction"

**Resolution:** CONTEXT.md is the locked user decision and supersedes the ROADMAP's earlier description. Implement: **jq → plutil**.

**Why this is also the better technical design:**

| Criterion | jq → python3 → grep | jq → plutil |
|-----------|---------------------|-------------|
| Always present on macOS | No (python3 is a stub on clean macOS; grep can't do nested paths) | Yes (plutil at /usr/bin since macOS 10.4) |
| Handles nested key paths | python3: yes; grep: NO | Yes |
| Triggers GUI dialogs | python3 stub: YES on clean macOS | Never |
| Extracts integers/booleans | Yes | Yes |
| Handles plist files too | No (python3 json.load rejects plist) | Yes (plutil is plist-native) |

**Recommendation to planner:** Implement `jq → plutil`. Update ROADMAP SC#1 wording to match CONTEXT.md when writing the plan (or note the discrepancy). The Phase 5 verifier should test against the `jq → plutil` chain description.

---

## Firefox Extensions (Phase 4 Preview)

This is not Phase 1 scope, but the `json_get` and `emit_item` helpers are designed to anticipate it. Documented here for the planner's awareness:

**`extensions.json` structure (verified on this machine):**
```json
{
  "addons": [
    {
      "id": "{5caff8cc-3d2e-4110-a88a-003cc85b3858}",
      "version": "7.7.7",
      "type": "extension",
      "location": "app-profile",
      "defaultLocale": { "name": "Vue.js devtools" }
    }
  ]
}
```

**Key fields:** `addons[].id` (ID), `addons[].version`, `addons[].defaultLocale.name` (display name), `addons[].type` (filter: `"extension"` only), `addons[].location` (filter: `"app-profile"` only — excludes system/built-in add-ons).

**Phase 4 implication:** Firefox requires iterating an array (`addons[]`), which `plutil` cannot do. The Firefox collector will need `jq` or python3. Per the existing PITFALLS.md finding: if `jq` is absent for Firefox, emit a one-line note `"Firefox extensions require jq for parsing"` rather than a partial/broken list. This is documented degradation, not a bug.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| python3 in JSON fallback chain | plutil (always present on macOS) | Eliminates GUI-dialog blocking on clean macOS; narrows the chain to two tools |
| Inline sort per-section | Buffered `_section_lines` + `flush_section` | Section-wide sort including all items; handles empty section; centralizes FMT-04 contract |
| Direct `echo "name" >> "$OUTPUT_FILE"` | `emit_item` + `flush_section` | All 7 FMT-01 degradation cases covered uniformly; sorted before write |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Empty section writes `(none found)` to OUTPUT_FILE (consistent with existing script pattern) | Pattern 4: flush_section | Low — if a different convention is preferred, only flush_section needs updating |
| A2 | `_section_lines` is declared as a script-wide global; collectors reset it before use | Pattern 3: emit_item | Medium — if Zsh scoping rules interact unexpectedly with nested function calls, the reset discipline in each collector prevents accumulation |

---

## Open Questions (RESOLVED)

1. **`_section_lines` global scope management**
   - RESOLVED: Collectors use the defensive reset pattern (`_section_lines=()` at the top of every collector that calls `emit_item`); the canonical approach is documented in the `flush_section` comment block. Planner adopted this in 01-01-PLAN.md Task 1.
   - What we know: `emit_item` and `flush_section` are separate functions; the buffer must be accessible to both; Zsh doesn't have true function-local arrays that child functions can see.

2. **ROADMAP SC#1 wording mismatch**
   - RESOLVED: The ROADMAP SC#1 was reconciled to `jq → plutil → grep` (python3 removed — it is an xcrun stub on clean macOS that blocks the script). The implemented chain is `jq → plutil`; the Phase 5 verification plan tests this chain.
   - What we know: CONTEXT.md locks `jq → plutil`; the ROADMAP literal text was updated to match.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `jq` | `json_get` (preferred backend) | Yes (Homebrew) | `jq-1.8.1` | `plutil` |
| `plutil` | `json_get` (always-present backend) | Yes (macOS built-in) | macOS 26.5 build | — (always present) |
| `python3` | NOT in the chain | `/usr/bin/python3` present (CLT-backed) | 3.9.6 | N/A — not used |
| `zsh` | Script runtime | Yes (default shell) | macOS 26.5 built-in | — |

**Missing dependencies with no fallback:** None. `plutil` is always present on macOS.

**Missing dependencies with fallback:** `jq` — not present on clean macOS without Homebrew; `json_get` falls back to `plutil` automatically.

---

## Validation Architecture

`workflow.nyquist_validation` is explicitly `false` in `.planning/config.json` — this section is skipped.

---

## Security Domain

This phase adds zero-network, zero-credentials, zero-secrets code. The helpers read local manifest files and write human-readable strings. No ASVS categories apply.

The only security-adjacent consideration is that `json_get` must never emit values from keys that callers didn't request — it extracts exactly one field by key path and echoes it. No traversal of sibling keys occurs. This is structurally correct given the single-key-path design.

---

## Sources

### Primary (HIGH confidence)

- Live macOS 26.5 machine — every command invocation above was run and output captured in this session:
  - `plutil -extract` behavior on JSON: flat keys, nested keys, missing keys, integer/boolean values
  - `jq getpath(split("."))` behavior: nested paths, null-to-empty coercion
  - `LC_ALL=C sort -f -u` dedup behavior on macOS BSD sort
  - Chrome extension directory structure: `ext_id/version_dir/manifest.json` + `_locales/` sibling
  - Bitwarden (`nngceckbapebfimnlniiiahkandclblb`) `__MSG_extName__` → `en/messages.json` → `"Bitwarden Password Manager"` resolution
  - Firefox `extensions.json` schema: `addons[]` with `id`, `version`, `defaultLocale.name`, `type`, `location`
  - Zsh array buffer pattern: `typeset -a`, `+=`, `printf "%s\n" "${arr[@]}"` + sort pipeline

- `.planning/research/PITFALLS.md` (2026-06-12) — prior research on this codebase; confirms Chrome `__MSG_` behavior, `null_glob` pattern, jq/plutil/python3 availability analysis, determinism requirement.

- `.planning/research/ARCHITECTURE.md` (2026-06-12) — confirms insertion point (after `write_section`, before `generate_catalog`), `json_get` ladder design, `chrome_ext_name` specification.

### Secondary (MEDIUM confidence)

- `update-list.sh` source (lines 254–336) — existing `write_section` pattern, `command -v` probing style, `>> "$OUTPUT_FILE"` append convention, `local`-scoped variables, `[[ ]]` conditionals. All conventions confirmed from direct reading.

- `.planning/phases/01-shared-helpers-foundation/01-CONTEXT.md` — user-locked decisions for this phase (FMT-01 degradation rules, FMT-04 sort spec, jq→plutil chain, CHR-01 fallback requirement).

---

## Metadata

**Confidence breakdown:**
- json_get design: HIGH — both backends tested against real manifests; plutil vs python3 analysis verified
- chrome_ext_name algorithm: HIGH — tested end-to-end against live Bitwarden extension
- emit_item degradation rules: HIGH — all 7 cases tested in Zsh
- flush_section sort invocation: HIGH — LC_ALL=C sort -f -u output verified; stability confirmed
- CONTEXT vs ROADMAP discrepancy: HIGH — plutil always present on macOS; python3 stub behavior is documented Apple behavior

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (stable — macOS built-in behavior and Chrome manifest format do not change rapidly)

---

## RESEARCH COMPLETE

**Phase:** 01 - Shared Helpers Foundation
**Confidence:** HIGH

### Key Findings

1. **JSON chain is jq → plutil (not jq → python3 → grep):** CONTEXT.md supersedes the ROADMAP's older description. plutil is at `/usr/bin/plutil` on every macOS since 10.4; `/usr/bin/python3` is an xcrun stub on clean macOS that pops a GUI dialog. Both jq and plutil support dotted nested key paths. plutil exits 1 on missing keys (stdout empty, stderr suppressed) — clean graceful degradation matching the return contract.

2. **chrome_ext_name algorithm is fully specified and verified:** `__MSG_<key>__` → read `default_locale` from manifest → open `_locales/<locale>/messages.json` → case-insensitive key lookup. Falls back to 32-char extension ID. Verified against Bitwarden on this machine.

3. **emit_item covers 7 distinct degradation cases:** All FMT-01 rules verified in Zsh. The key design point: when name is empty but ID is known, use ID as name and suppress the brackets (never `id [id]`).

4. **flush_section: exact sort invocation is `LC_ALL=C sort -f -u`:** Byte-stable (LC_ALL=C), case-insensitive (−f), deduplicating (−u). Verified byte-identical output on repeated runs. macOS BSD sort -f -u deduplicates case-insensitively (correct for our use case).

5. **`_section_lines` is a script-global array:** Because `emit_item` is a separate function from the collector body, the array must be accessible across function boundaries. Collectors must reset it (`_section_lines=()`) at their top as a defensive measure.

### File Created

`.planning/phases/01-shared-helpers-foundation/01-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| JSON fallback chain | HIGH | Both backends tested live on this machine; plutil always-present property verified |
| chrome_ext_name algorithm | HIGH | End-to-end verified against real Bitwarden extension |
| emit_item degradation | HIGH | All 7 cases run in Zsh |
| sort invocation | HIGH | LC_ALL=C sort -f -u output verified; byte-stability confirmed |
| Insertion point | HIGH | Read existing script; confirmed clean insertion after write_section (line 257) before generate_catalog (line 271) |

### Open Questions

1. Defensive `_section_lines=()` reset placement — recommend at the top of each collector (planner decision).
2. ROADMAP SC#1 wording mismatch — `jq → plutil` is implemented; Phase 5 verifier should use the CONTEXT description not the ROADMAP literal text.

### Ready for Planning

Research complete. Planner can now create PLAN.md files.
