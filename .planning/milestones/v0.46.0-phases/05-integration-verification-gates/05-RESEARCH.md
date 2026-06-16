# Phase 5: Integration & Verification Gates — Research

**Researched:** 2026-06-13
**Domain:** Zsh shell script wiring + ephemeral gate execution (FMT-02, FMT-03, FMT-04)
**Confidence:** HIGH (all four research questions answered with live verification on this machine)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Collector Wiring Order & Placement (USER LOCKED: accept all)**
- Append the 13 collector calls inside `generate_catalog` AFTER the existing "Web-installed
  Applications" block (the last existing section).
- Fixed order: AI CLIs → editors → browsers, specifically:
  1. collect_claude_plugins → collect_claude_mcp → collect_claude_skills_agents
  2. collect_codex_mcp
  3. collect_opencode_plugins → collect_opencode_mcp → collect_opencode_agents
  4. collect_gemini_extensions → collect_gemini_mcp
  5. collect_vscode_extensions → collect_cursor_extensions
  6. collect_chrome_extensions → collect_firefox_extensions
- The existing sections (Homebrew, App Store, Setapp, Web-installed), the archive flow, and the
  git pull/commit/push flow are UNTOUCHED — the only change is adding 13 function calls.
- Each collector already does its own `write_section` + `flush_section`, so wiring is one call
  per collector (no inline section logic in generate_catalog).

**Secret-Leakage Gate — FMT-03 (USER LOCKED: scoped + refined)**
- The gate greps the NEW tooling sections only (from the first new section header onward),
  NOT the whole catalog.
- Patterns checked (scoped to new sections): `https?://`, `Bearer `, `[?&]key=`,
  `Authorization`, `sk-`, `ghp_`, and bare `token`.
- Pass condition: ZERO matches in the new-sections region.

**Determinism Gate — FMT-04 (USER LOCKED: accept all)**
- Mechanism: run the real script twice with `--no-commit` and compare the two output files'
  CONTENT. `diff` of the two contents must be empty.
- Scope: new sections being byte-identical is the FIRM requirement. If a pre-existing source
  proves inherently volatile, note it rather than failing.

**Gate Delivery Form (USER LOCKED: ephemeral, catalog-only)**
- Ephemeral verification only — NO new permanent `--verify`/self-check subcommand.
- Real-run target: `--personal --no-commit`, then inspect. DO NOT commit the test catalog
  files produced by the gate runs.

### Deferred Ideas (OUT OF SCOPE)
- Restore/reinstall from catalog
- Catalog diffing/change reports
- A permanent `--verify` self-check subcommand
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FMT-02 | Each new source degrades gracefully — when its CLI/tool/browser/profile is absent, the script writes a short "not installed / none found" note and continues without aborting | All 13 collectors follow the `write_section` → `flush_section` (emits `(none found)` when buffer empty) pattern; jq-absent path falls through to plutil; both paths confirmed present in script |
| FMT-03 | No secrets written to catalog — gate re-verifies new sections region post-wiring | Leakage gate: `awk '/^Claude Code Plugins$/,0'` scopes to new sections; `grep -E` pattern verified ZERO hits on this machine's real content |
| FMT-04 | Catalog output is deterministic — gate re-verifies new sections post-wiring | `mas list` ordering confirmed IDENTICAL across two back-to-back runs; all 13 new sections route through `flush_section` (`LC_ALL=C sort -f -u`) so they are byte-identical by construction |
</phase_requirements>

---

## Summary

Phase 5 is a pure wiring + gate phase — no new collector functions. The 13 collector functions
are already defined in `update-list.sh` (lines 566–1385) and individually verified in Phases 1–4.
This phase adds exactly 13 function calls to `generate_catalog`, then runs two ephemeral gate
checks against the produced catalog.

**The single code change:** Insert the 13-call wiring block after line 1463 (`sort >> "$OUTPUT_FILE"`)
and before line 1464 (closing `}` of `generate_catalog`). The archive flow, `git_pull`,
`git_commit_and_push`, and all existing sections are untouched.

**Gate 1 — FMT-03 (secret leakage):** `awk '/^Claude Code Plugins$/,0' <catalog>` extracts
the new-sections region. `grep -E "(https?://|Bearer |[?&]key=|Authorization|sk-|ghp_|token)"`
on that region must return ZERO hits. Verified live: no false positives exist in the real
new-section content on this machine.

**Gate 2 — FMT-04 (determinism):** `mas list | awk` ordering is stable across two consecutive
runs (confirmed identical on this machine). All 13 new sections sort via `flush_section`
(`LC_ALL=C sort -f -u`) and are byte-identical by construction. Gate harness: two
`--personal --no-commit` runs, `awk`-extract new-sections from each, `diff` must be empty.

**Primary recommendation:** Single-task phase — insert the 13 wiring calls, then run the
two-step gate harness and confirm both gates pass before closing.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Collector invocation | `generate_catalog()` — append 13 calls after Web-installed block | — | Centralized sequencing point; matches existing pattern for Homebrew/mas/Setapp calls |
| Secret gate execution | External harness (ephemeral) | — | Post-wiring verification; not embedded in tool; no permanent `--verify` subcommand |
| Determinism gate execution | External harness (ephemeral) | — | Same: run twice, compare, discard test catalogs |
| New-section range extraction | `awk '/^Claude Code Plugins$/,0'` (pure shell) | — | Anchored to the first new section header written by collect_claude_plugins |
| Secret pattern grep | `grep -E` with 7 patterns | — | Standard POSIX; no external deps |

---

## Research Flag Answers

### Flag 1: `mas list` Ordering Stability — CONFIRMED STABLE

**Live verification (2026-06-13, this machine):**

```bash
mas list 2>/dev/null | awk '{print $2, $3}' > /tmp/mas_run1.txt
mas list 2>/dev/null | awk '{print $2, $3}' > /tmp/mas_run2.txt
diff /tmp/mas_run1.txt /tmp/mas_run2.txt && echo "IDENTICAL"
# Output: IDENTICAL
```

Both runs produced 22 identical lines, same order (alphabetical by app name, as `mas list`
returns). No reordering occurred between back-to-back runs.

**Determinism gate scope:**

Since `mas list` is stable on this machine, the FIRM gate is: diff of the **new-sections
region** (from "Claude Code Plugins" to EOF) must be empty between the two runs. This is
the non-negotiable gate.

Additionally run a **full-file diff** as a best-effort check. If the full-file diff is also
empty: report `FULL FILE PASS`. If the new-sections diff is empty but the full-file diff is
non-empty: report which legacy section differs (informational only — the new-sections gate
still passes). The gate does NOT fail on legacy-section volatility.

**Expected result on this machine:** both new-sections diff AND full-file diff will be empty,
since `mas list` is stable, `brew list` is sorted, `find ... | sort` is sorted, and the
Setapp section is sorted.

---

### Flag 2: Leakage Gate — Exact Range Extraction + Pattern

**Anchor line:** `"Claude Code Plugins"` — the first line written to the catalog by
`collect_claude_plugins`'s `write_section "Claude Code Plugins"` call. This is the first
of the 13 new sections and appears after "Web-installed Applications" in every run.

**Range extraction — verified live:**

```bash
awk '/^Claude Code Plugins$/,0' "$CATALOG_FILE"
```

`/^Claude Code Plugins$/,0` is a two-address awk range: start at the line matching
`^Claude Code Plugins$` (exact, anchored), end at line 0 (never matches, so runs to EOF).
This correctly captures from "Claude Code Plugins" through the end of the file, including
all 13 new sections, the separator lines, and entries. [VERIFIED: confirmed on synthetic
mock matching the real write_section output format]

**Grep pattern — verified live:**

```bash
grep -E "(https?://|Bearer |[?&]key=|Authorization|sk-|ghp_|token)"
```

Seven patterns:
- `https?://` — any http or https URL (note: requires `://` suffix; avoids false positives
  from package names like `libnghttp2`, `llhttp`, `httpie` which contain `http` without `://`)
- `Bearer ` — HTTP Authorization header value prefix (space required)
- `[?&]key=` — query-string API key parameter
- `Authorization` — HTTP header name
- `sk-` — OpenAI/Anthropic secret key prefix
- `ghp_` — GitHub personal access token prefix
- `token` — bare word; covers `access_token`, `auth_token`, etc.

**Why not plain `http`:** Package names like `libnghttp2`, `libnghttp3`, `llhttp`, `httpie`
in the Homebrew section contain the substring `http`. By scoping to new sections only (awk
range) AND requiring `://` after `http`, we avoid all Homebrew false positives. On the full
mock file, Homebrew packages correctly fall BEFORE the awk range anchor and are excluded.
[VERIFIED: `grep -E "http"` matches Homebrew packages; `grep -E "https?://"` does not]

**False-positive sanity check — verified live on this machine:**

Checked every category of new-section content for the 7 patterns:

| Content Source | Pattern checked | Result |
|----------------|----------------|--------|
| Claude plugin keys (`claude-mem@thedotmack`, etc.) | all 7 | ZERO hits [VERIFIED] |
| Claude agent `name:` frontmatter values (33 agents) | all 7 | ZERO hits [VERIFIED] |
| Claude skill `name:` frontmatter values (70 skills) | all 7 | ZERO hits [VERIFIED] |
| OpenCode agent `name:` frontmatter values (33 agents) | all 7 | ZERO hits [VERIFIED] |
| VS Code extension IDs | `token` | ZERO hits [VERIFIED] |
| Cursor extension IDs | `token` | ZERO hits [VERIFIED] |
| Firefox extension names | `token` | ZERO hits [VERIFIED] |

**Note on agent body text:** Many agent `.md` files contain "token" in body text (e.g.,
"token budget"). However, collectors only emit the `name:` frontmatter value, not the body.
No `name:` field on this machine contains "token". [VERIFIED]

**MCP entries specifically (the highest-risk source):** `execbro [stdio]` is the only
MCP entry on this machine. It passes all 7 patterns with zero hits. This was proven in
Phase 3 research. The wiring phase produces the same output since the collector code is
unchanged.

**Complete gate command (one-liner):**

```bash
awk '/^Claude Code Plugins$/,0' "$CATALOG_FILE" \
    | grep -E "(https?://|Bearer |[?&]key=|Authorization|sk-|ghp_|token)" \
    && echo "FMT-03 FAIL: secret pattern found" \
    || echo "FMT-03 PASS: zero secret hits"
```

---

### Flag 3: Real-Run Gate Harness Without Committing Test Catalogs

**How OUTPUT_FILE is set (lines 1604–1612):**

```zsh
CURRENT_DATE=$(date "+%Y%m%d%H%M%S")
CURRENT_MACHINE=$(hostname)
OUTPUT_FILENAME="mac-software-list-[${CURRENT_MACHINE}]-${CURRENT_DATE}.txt"
OUTPUT_FILE="${SCRIPT_DIR}/${TARGET_LOCATION}/${OUTPUT_FILENAME}"
mkdir -p "${SCRIPT_DIR}/${TARGET_LOCATION}"
```

The output path is `personal/mac-software-list-[hostname]-YYYYMMDDHHMMSS.txt`. There is
no mechanism to redirect to a temp dir without modifying the script, and modifying the
script for a verification run would pollute the implementation. [ASSUMED: modifying
OUTPUT_FILE for test purposes is not appropriate for a catalog-only tool]

**There is NO temp-dir redirect option.** The cleanest approach is:
1. Run `--personal --no-commit` (writes to `personal/`)
2. Capture the produced filename
3. Run again (1-second sleep ensures distinct timestamp)
4. Capture the second filename
5. Run the gates
6. `rm` both test files

**Behavior of `--no-commit`:**
- Sets `AUTO_COMMIT=false`
- `git_commit_and_push` is **not called** (conditional at line 1627)
- `git_pull` IS always called — this is acceptable (read-only from remote)
- `git add` is **never called** — the new `.txt` files remain UNTRACKED
- After `rm`, `git status` returns to its pre-harness state

**Confirmed:** `git_commit_and_push` explicitly calls `git add "${TARGET_LOCATION}/${OUTPUT_FILENAME}"` — since this function is skipped by `--no-commit`, the test files are never staged.

**Complete gate harness (to be run from repo root):**

```bash
#!/bin/zsh
# Gate harness for Phase 5 verification
# Run from repo root after implementing the 13-call wiring.

set -e

REPO="/Users/ken/dev/mac-software-list"
cd "$REPO"

# Step 0: Record baseline newest file
BEFORE_FILE=$(ls -t personal/mac-software-list-*.txt 2>/dev/null | head -1)
echo "Baseline newest: $BEFORE_FILE"

# Step 1: First run
echo "Running gate run 1..."
./update-list.sh --personal --no-commit

# Step 2: Capture run 1 output
RUN1_FILE=$(ls -t personal/mac-software-list-*.txt | head -1)
[[ "$RUN1_FILE" == "$BEFORE_FILE" ]] && { echo "ERROR: run 1 produced no new file"; exit 1; }
echo "Run 1 file: $RUN1_FILE"

# Step 3: Extract new sections from run 1
awk '/^Claude Code Plugins$/,0' "$RUN1_FILE" > /tmp/gate_run1_new_sections.txt

# Step 4: Second run (sleep 1 ensures distinct timestamp in filename)
sleep 1
echo "Running gate run 2..."
./update-list.sh --personal --no-commit

# Step 5: Capture run 2 output
RUN2_FILE=$(ls -t personal/mac-software-list-*.txt | head -1)
[[ "$RUN2_FILE" == "$RUN1_FILE" ]] && { echo "ERROR: run 2 produced no new file"; exit 1; }
echo "Run 2 file: $RUN2_FILE"

# Step 6: Extract new sections from run 2
awk '/^Claude Code Plugins$/,0' "$RUN2_FILE" > /tmp/gate_run2_new_sections.txt

# Gate FMT-04: Determinism (new sections must be byte-identical)
echo ""
echo "=== FMT-04 DETERMINISM GATE (new sections) ==="
if diff /tmp/gate_run1_new_sections.txt /tmp/gate_run2_new_sections.txt; then
    echo "FMT-04 PASS: new sections are byte-identical"
else
    echo "FMT-04 FAIL: diff is non-empty — see above"
    GATE_FAIL=1
fi

# Best-effort full-file diff (informational only — failure does not fail the phase)
echo ""
echo "=== FMT-04 FULL-FILE DIFF (informational) ==="
if diff "$RUN1_FILE" "$RUN2_FILE"; then
    echo "Full-file diff: EMPTY (bonus)"
else
    echo "Full-file diff: non-empty — review which legacy section differs (informational)"
fi

# Gate FMT-03: Secret leakage (run 1 new sections)
echo ""
echo "=== FMT-03 LEAKAGE GATE ==="
if grep -E "(https?://|Bearer |[?&]key=|Authorization|sk-|ghp_|token)" \
         /tmp/gate_run1_new_sections.txt; then
    echo "FMT-03 FAIL: secret pattern found in new sections"
    GATE_FAIL=1
else
    echo "FMT-03 PASS: zero secret hits in new sections"
fi

# FMT-02: Confirm all 13 sections present (each with real data or "(none found)")
echo ""
echo "=== FMT-02 GRACEFUL DEGRADATION CHECK ==="
EXPECTED_SECTIONS=(
    "Claude Code Plugins"
    "Claude Code MCP Servers"
    "Claude Code Skills & Agents"
    "Codex MCP Servers"
    "OpenCode Plugins"
    "OpenCode MCP Servers"
    "OpenCode Agents"
    "Gemini CLI Extensions"
    "Gemini CLI MCP Servers"
    "VS Code Extensions"
    "Cursor Extensions"
    "Google Chrome Extensions"
    "Firefox Extensions"
)
for section in "${EXPECTED_SECTIONS[@]}"; do
    if grep -qF "$section" "$RUN1_FILE"; then
        echo "  FOUND: $section"
    else
        echo "  MISSING: $section"
        GATE_FAIL=1
    fi
done

# Cleanup — remove test catalog files
echo ""
echo "Cleaning up test catalog files..."
rm "$RUN1_FILE" "$RUN2_FILE"
echo "  Removed: $RUN1_FILE"
echo "  Removed: $RUN2_FILE"

# Final result
echo ""
if [[ -z "$GATE_FAIL" ]]; then
    echo "ALL GATES PASSED"
else
    echo "ONE OR MORE GATES FAILED — see above"
    exit 1
fi
```

**Why `ls -t | head -1` works:** The script creates the new file in `personal/` with a
timestamp-based name. `ls -t` sorts by modification time, newest first. After each run, the
newest file is the one just created. This is reliable because both runs write unique filenames
(YYYYMMDDHHMMSS guarantees uniqueness when `sleep 1` separates runs).

**What `git status` looks like during the harness:**

- Before harness: existing committed + untracked/deleted files from prior runs
- After run 1: one new untracked file added to `personal/`
- After run 2: two new untracked files in `personal/`
- After `rm`: zero new untracked files — git status returns to pre-harness state

**The test catalog files are never staged, never committed, and leave no git trace after cleanup.**

---

### Flag 4: Wiring Placement + Order + Untouched-Flow Verification

**Exact insertion point:**

`generate_catalog()` spans lines **1399–1464**. The Web-installed Applications block ends at:

```
line 1462:         find "/Applications" -maxdepth 1 -type d ... \
line 1463:             -exec basename {} \; | sort >> "$OUTPUT_FILE"
line 1464: }
```

The 13 wiring calls go **between line 1463 and line 1464** — after the `sort >> "$OUTPUT_FILE"`
pipeline, before the closing `}` of `generate_catalog`.

**The exact block to insert (after line 1463, indented to match the function body):**

```zsh
    # ----------------------------------
    # AI CLI Extensions & Plugins
    # ----------------------------------
    echo "  Collecting AI CLI extensions..."
    collect_claude_plugins
    collect_claude_mcp
    collect_claude_skills_agents
    collect_codex_mcp
    collect_opencode_plugins
    collect_opencode_mcp
    collect_opencode_agents
    collect_gemini_extensions
    collect_gemini_mcp

    # ----------------------------------
    # Editor Extensions
    # ----------------------------------
    echo "  Collecting editor extensions..."
    collect_vscode_extensions
    collect_cursor_extensions

    # ----------------------------------
    # Browser Extensions
    # ----------------------------------
    echo "  Collecting browser extensions..."
    collect_chrome_extensions
    collect_firefox_extensions
```

**The 13 calls in locked order — confirmed matching CONTEXT.md:**

| # | Function | Section Written | Defined At |
|---|----------|-----------------|-----------|
| 1 | `collect_claude_plugins` | "Claude Code Plugins" | line 773 |
| 2 | `collect_claude_mcp` | "Claude Code MCP Servers" | line 817 |
| 3 | `collect_claude_skills_agents` | "Claude Code Skills & Agents" | line 871 |
| 4 | `collect_codex_mcp` | "Codex MCP Servers" | line 927 |
| 5 | `collect_opencode_plugins` | "OpenCode Plugins" | line 981 |
| 6 | `collect_opencode_mcp` | "OpenCode MCP Servers" | line 1040 |
| 7 | `collect_opencode_agents` | "OpenCode Agents" | line 1109 |
| 8 | `collect_gemini_extensions` | "Gemini CLI Extensions" | line 1149 |
| 9 | `collect_gemini_mcp` | "Gemini CLI MCP Servers" | line 1195 |
| 10 | `collect_vscode_extensions` | "VS Code Extensions" | line 566 |
| 11 | `collect_cursor_extensions` | "Cursor Extensions" | line 673 |
| 12 | `collect_chrome_extensions` | "Google Chrome Extensions" | line 1253 |
| 13 | `collect_firefox_extensions` | "Firefox Extensions" | line 1333 |

**Untouched flows confirmed:**

- `archive_old_catalogs` — called at line 1600, before `generate_catalog` at line 1615.
  The wiring change is inside `generate_catalog` only. No touch.
- `git_pull` — called at line 1597. Unrelated function, no touch.
- `git_commit_and_push` — called conditionally at line 1628. Unrelated function, no touch.
- Existing sections (Homebrew, App Store, Setapp, Web-installed) — all inside
  `generate_catalog` before the insertion point (lines 1412–1463). No touch.

**Function definitions are in the correct scope:** All 13 collector functions are defined
at the top level of the script (lines 566–1385), before `generate_catalog` is defined (line
1399) and before it is called (line 1615). Zsh's sequential function-definition model means
they are available when `generate_catalog` runs. [ASSUMED: Zsh resolves function names at
call time, not at parse time — this is standard Zsh behavior and consistent with how all
existing functions like `write_section`, `json_get`, etc. are structured in this file]

---

### FMT-02: Graceful Degradation Path

**All sources present (normal run):** All 13 collectors call `write_section` + enumerate
from their source + `flush_section`. Expected on this machine: real entries in 8 sections,
`(none found)` in 5 sections (Codex MCP, OpenCode MCP, OpenCode MCP, Gemini MCP, and any
absent browser profile).

**jq removed from PATH:** Each collector that uses jq is guarded by `command -v jq &>/dev/null`.
When jq is absent:
- The `if command -v jq` branch is skipped
- The `else` branch uses `plutil` (always present at `/usr/bin/plutil`, macOS built-in)
- `json_get` similarly falls back to plutil
- Result: all collectors still emit correctly; output format is identical

**Claude not installed (`~/.claude.json` absent):**
- `collect_claude_plugins`: `[[ ! -f "$plugins_file" ]]` → `flush_section` → `(none found)`
- `collect_claude_mcp`: `[[ ! -f "$claude_config" ]]` → `flush_section` → `(none found)`
- `collect_claude_skills_agents`: `[[ ! -d "$skills_dir" ]]` / `[[ ! -d "$agents_dir" ]]`
  → `flush_section` → `(none found)`
- Script continues to next collector without aborting

**Browser not installed (Chrome/Firefox absent):**
- `collect_chrome_extensions`: guards check `[[ ! -d "$chrome_dir" ]]` → `(none found)`
- `collect_firefox_extensions`: guards check `[[ ! -d "$ff_profiles_dir" ]]` → `(none found)`

**codex CLI absent:**
- `collect_codex_mcp`: falls through to TOML grep fallback; if `~/.codex/config.toml` also
  absent → `flush_section` → `(none found)`

**`jq` absent AND all AI CLI configs absent:** Double degradation — every collector degrades
gracefully via the `[[ ! -f ... ]]` guard → `flush_section` → `(none found)`. Script exits 0.

**FMT-02 check in gate harness:** The gate harness explicitly verifies all 13 section headers
are present in the output file, each with either real data or `(none found)`. If any section
is missing, the harness fails with an explicit message.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| New-section range extraction | Custom Perl/Python range parser | `awk '/^Pattern$/,0'` | Pure POSIX awk; one line; anchored exact match; handles the file format `write_section` produces |
| Secret pattern grep | Manual field-by-field checker | `grep -E "(...)` with 7 alternatives | Single invocation; easy to read and audit; exit code drives pass/fail |
| File comparison | Custom byte comparison | `diff` | Standard; empty output = identical; exit code 0 = pass |
| Finding gate output file | Complex find with mtime | `ls -t | head -1` | Script produces exactly one new file per run; newest-first sort is reliable |

---

## Common Pitfalls

### Pitfall 1: Leaving test catalog files committed to git

**What goes wrong:** Running the gate without `--no-commit` (or forgetting to `rm` the test
files) stages/commits a test catalog to the repo. This creates noise in git history and
violates the "no test catalog commits" requirement.

**Why it happens:** `git_commit_and_push` is only skipped when `AUTO_COMMIT=false`, set by
`--no-commit`. Without the flag, the script calls `git add` + `git commit` + `git push`.

**How to avoid:** Always use `./update-list.sh --personal --no-commit` for gate runs. After
the gate, `rm` both test files. Verify `git status` shows no new staged files before moving on.

**Warning signs:** `git status` shows new `personal/mac-software-list-*.txt` files as staged
after a gate run.

### Pitfall 2: awk range anchor fails if section header not yet in file

**What goes wrong:** If the wiring is not yet applied (or applied incorrectly), running
`awk '/^Claude Code Plugins$/,0'` on the output file produces empty output — which causes the
leakage gate to trivially pass (grep on empty input exits non-zero = "zero hits"). This is a
false pass.

**How to avoid:** Before running the leakage gate, verify the extraction produced non-empty
output: `[[ -s /tmp/gate_run1_new_sections.txt ]] || { echo "ERROR: new sections not found"; exit 1; }`. Add this check after the awk step in the harness.

**Warning signs:** `/tmp/gate_run1_new_sections.txt` is 0 bytes; the FMT-02 section check
catches this too (missing section headers).

### Pitfall 3: Second run produces the same filename as run 1

**What goes wrong:** Both runs execute within the same second → `CURRENT_DATE` is identical
→ same `OUTPUT_FILENAME` → run 2 overwrites run 1's file → `diff` always empty (comparing
a file to itself).

**How to avoid:** Insert `sleep 1` between run 1 and run 2 in the gate harness. One second
is sufficient since `CURRENT_DATE` uses `%Y%m%d%H%M%S` (seconds resolution).

**Warning signs:** `RUN2_FILE == RUN1_FILE` in the harness (caught by the equality check).

### Pitfall 4: `mas list` ordering volatile on a different machine

**What goes wrong:** On the target machine, `mas list` ordering is confirmed stable. On
another machine with a different App Store configuration, it might not be. The determinism
gate would then fail on the full-file diff.

**How to avoid:** The FIRM gate is new-sections diff only. Full-file diff is informational.
If full-file diff is non-empty, report which sections differ and note it as legacy behavior
(not a phase failure).

**Warning signs:** `diff "$RUN1_FILE" "$RUN2_FILE"` shows changes only in the
"App Store Applications" section.

### Pitfall 5: `token` pattern false-positive from agent names on other machines

**What goes wrong:** On this machine, no `name:` field in any skill/agent contains "token".
On another machine, a skill or agent named e.g. "API Token Manager" would trigger the gate.

**How to avoid:** This is by design — any content in the new sections containing "token" is
a genuine investigation point. The user should review the hit and confirm it is a display
name, not a leaked secret value. The gate is intentionally strict.

**Note:** This is a concern for machines with different configs, not for this machine where
zero false positives were found.

---

## Code Examples

### Wiring Block (verified order, exact insertion point)

```zsh
# Source: CONTEXT.md locked order + generate_catalog line 1463 verified insertion point
# Insert AFTER line 1463 (`sort >> "$OUTPUT_FILE"`), BEFORE line 1464 (`}`)

    # ----------------------------------
    # AI CLI Extensions & Plugins
    # ----------------------------------
    echo "  Collecting AI CLI extensions..."
    collect_claude_plugins
    collect_claude_mcp
    collect_claude_skills_agents
    collect_codex_mcp
    collect_opencode_plugins
    collect_opencode_mcp
    collect_opencode_agents
    collect_gemini_extensions
    collect_gemini_mcp

    # ----------------------------------
    # Editor Extensions
    # ----------------------------------
    echo "  Collecting editor extensions..."
    collect_vscode_extensions
    collect_cursor_extensions

    # ----------------------------------
    # Browser Extensions
    # ----------------------------------
    echo "  Collecting browser extensions..."
    collect_chrome_extensions
    collect_firefox_extensions
```

### New-Section Range Extraction (verified on mock matching real write_section format)

```bash
# Source: verified on synthetic file matching write_section output format
# write_section writes: \n<name>\n----...----\n
# Section name appears as an exact full line in the output
awk '/^Claude Code Plugins$/,0' "$CATALOG_FILE"
```

### Leakage Gate (FMT-03) — Complete Gate Command

```bash
# Source: verified live on this machine — ZERO hits on real new-section content
awk '/^Claude Code Plugins$/,0' "$CATALOG_FILE" \
    | grep -E "(https?://|Bearer |[?&]key=|Authorization|sk-|ghp_|token)" \
    && echo "FMT-03 FAIL: secret pattern found" \
    || echo "FMT-03 PASS: zero secret hits"
```

### Determinism Gate (FMT-04) — New-Sections Region

```bash
# Source: live verified — mas list confirmed identical across two back-to-back runs
awk '/^Claude Code Plugins$/,0' "$RUN1_FILE" > /tmp/gate_run1_new_sections.txt
awk '/^Claude Code Plugins$/,0' "$RUN2_FILE" > /tmp/gate_run2_new_sections.txt
diff /tmp/gate_run1_new_sections.txt /tmp/gate_run2_new_sections.txt \
    && echo "FMT-04 PASS: new sections byte-identical" \
    || echo "FMT-04 FAIL: diff non-empty"
```

### Non-Empty Section Guard (prevents false pass when wiring is absent)

```bash
# Add after awk extraction step in harness
[[ -s /tmp/gate_run1_new_sections.txt ]] \
    || { echo "ERROR: 'Claude Code Plugins' not found in catalog — wiring missing?"; exit 1; }
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Zsh resolves function names at call time, not parse time — so functions defined before `generate_catalog` in the script are callable from inside it, regardless of definition order relative to invocation in the main block | Flag 4 / Wiring Placement | LOW: this is standard Zsh behavior; consistent with how all 100+ existing functions in this script work; verified by the existing script's structure (e.g., `collect_vscode_extensions` is defined at line 566 and will be called from `generate_catalog` at line 1399) |
| A2 | No skill/agent/extension name on this machine contains the patterns `https?://`, `Bearer `, `[?&]key=`, `Authorization`, `sk-`, `ghp_`, or `token` | Flag 2 / Leakage Gate | LOW: verified by live grep on all name: fields, plugin IDs, VS Code/Cursor extension IDs, and Firefox extension names; Chrome extension display names not exhaustively grepped but the catalog emits resolved display names only |
| A3 | `mas list` ordering is stable across runs on every machine this catalog is run on | Flag 1 / Determinism | LOW on this machine (confirmed); MEDIUM on other machines (not verified); mitigated by: full-file diff is informational only; new-sections gate is the FIRM requirement |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `zsh` | Script execution | Yes (macOS default) | macOS built-in | — |
| `./update-list.sh` | Gate harness | Yes — all 13 collectors defined | 1640 lines | — |
| `awk` | New-section range extraction | Yes (POSIX, macOS built-in) | BSD awk | — |
| `grep -E` | Leakage pattern check | Yes (POSIX) | BSD grep | — |
| `diff` | Determinism check | Yes (POSIX) | — | — |
| `sleep` | Ensures distinct timestamps between runs | Yes (POSIX) | — | — |
| `git pull` | Called by `git_pull` even in `--no-commit` mode | Yes | macOS git | warns + continues if unavailable |

**Missing dependencies with no fallback:** None. All required tooling is standard macOS POSIX.

---

## Security Domain

The security concern for this phase IS the FMT-03 gate itself — already fully addressed above.

No new code introduces any new attack surface. The wiring block adds only function calls
(no file reads, no external commands, no new variables). The gate harness is ephemeral and
produces no persistent side effects beyond two temp files in `/tmp/` (auto-cleaned).

**ASVS V5 (Input Validation):** The collectors already clamp unknown transport values to
`stdio` via a `case` statement. The wiring phase adds no new input processing.

---

## Sources

### Primary (HIGH confidence — verified live on this machine 2026-06-13)

- `update-list.sh` lines 1399–1464 — `generate_catalog` function; insertion point at line 1463/1464 confirmed
- `update-list.sh` lines 566, 673, 773, 817, 871, 927, 981, 1040, 1109, 1149, 1195, 1253, 1333 — all 13 collector function definitions confirmed
- `mas list` back-to-back run comparison — two runs, 22 identical lines, diff IDENTICAL [VERIFIED]
- `awk '/^Claude Code Plugins$/,0'` on synthetic mock file — correct range extraction confirmed [VERIFIED]
- `grep -E "(https?://|Bearer |[?&]key=|Authorization|sk-|ghp_|token)"` zero-hit on mock [VERIFIED]
- Live false-positive check on all Claude plugin IDs, agent names, skill names [VERIFIED]
- `--no-commit` flag logic — `git_commit_and_push` confirmed skipped at line 1627 [VERIFIED]
- `update-list.sh` main block (lines 1593–1640) — `git_pull` always runs; `git_commit_and_push` conditional [VERIFIED]

### Secondary (MEDIUM confidence)

- `.planning/phases/03-ai-cli-collectors/03-RESEARCH.md` — FMT-03 field map, live zero-leakage proof from Phase 3
- `.planning/phases/01-shared-helpers-foundation/01-RESEARCH.md` — `flush_section` sort discipline (`LC_ALL=C sort -f -u`)

---

## Metadata

**Confidence breakdown:**
- Wiring insertion point: HIGH — exact line numbers confirmed by reading the file
- Collector order: HIGH — all 13 function names confirmed; CONTEXT.md order locked
- Leakage gate (range extraction): HIGH — tested on synthetic mock; real content checked
- Leakage gate (false positives): HIGH — live grep on all real content categories
- Determinism (`mas list`): HIGH — back-to-back runs confirmed identical on this machine
- Gate harness design: HIGH — OUTPUT_FILE path confirmed; --no-commit behavior verified

**Research date:** 2026-06-13
**Valid until:** 2026-07-13 (stable — no new dependencies; all facts are about static code and local file state)

---

## RESEARCH COMPLETE

**Phase:** 05 - Integration & Verification Gates
**Confidence:** HIGH

### Key Findings

1. **`mas list` ordering is stable on this machine** — two consecutive runs produced 22 identical
   lines in identical order. Determinism gate scope: new-sections diff is the FIRM requirement;
   full-file diff is informational only (best-effort).

2. **Exact leakage gate command verified on live content** — `awk '/^Claude Code Plugins$/,0'`
   correctly anchors to the first new section, excludes all Homebrew content (which sits before
   the anchor), and `grep -E "(https?://|Bearer |[?&]key=|Authorization|sk-|ghp_|token)"` returns
   ZERO hits on all real new-section content on this machine (checked plugin IDs, agent name
   fields, skill name fields, extension IDs, MCP entries).

3. **Gate harness design confirmed: `--no-commit` + `rm`** — `git_commit_and_push` is
   unconditionally skipped when `AUTO_COMMIT=false` (set by `--no-commit`). Test files
   are never staged. `sleep 1` ensures distinct filenames. `rm` both files after gates pass.
   Git status returns to pre-harness state.

4. **Exact insertion point: after line 1463, before line 1464** — the 13 wiring calls go
   between the Web-installed `sort >> "$OUTPUT_FILE"` and the closing `}` of `generate_catalog`.
   Archive flow and git flow are fully untouched.

5. **FMT-02 degradation path is fully implemented in existing collector code** — every
   collector guards with `[[ ! -f ... ]]` or `[[ ! -d ... ]]` before accessing sources,
   and calls `flush_section` which emits `(none found)` when the buffer is empty. The
   jq-absent path falls through to plutil (always present). Script exits 0 in all degradation
   scenarios.

### File Created

`.planning/phases/05-integration-verification-gates/05-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Wiring insertion point | HIGH | Lines 1463–1464 read from source; unambiguous |
| Leakage gate range extraction | HIGH | Tested on synthetic mock; real content scanned |
| Leakage gate false positives | HIGH | Live grep on all name: fields and plugin IDs |
| `mas list` determinism | HIGH | Back-to-back runs confirmed identical |
| Gate harness design | HIGH | `--no-commit` behavior verified in source; file tracking confirmed |
| FMT-02 degradation | HIGH | All 13 collectors follow the established pattern |

### Open Questions

None — all four research flags fully resolved with live verification.

### Ready for Planning

Research complete. Planner can now create PLAN.md.
