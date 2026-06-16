---
phase: quick
plan: 260614-ckx
type: execute
wave: 1
depends_on: []
files_modified: [update-list.sh]
autonomous: true
requirements: [interactive-machine-label-ux]
must_haves:
  truths:
    - "Fresh-machine interactive menu lists the raw hostname as option 1 and defaults to it on empty Enter"
    - "Invalid menu choice re-prompts instead of exiting the script"
    - "Invalid new-label input re-prompts instead of exiting the script"
    - "Timestamp extraction in rename_machine uses pure-zsh expansion with zero subprocess forks"
  artifacts:
    - path: "update-list.sh"
      provides: "All three fixes applied; zsh -n passes"
  key_links:
    - from: "resolve_machine_label (interactive path)"
      to: "validate_machine_label_quiet"
      via: "non-fatal label validation helper"
      pattern: "validate_machine_label_quiet"
    - from: "rename_machine step 5"
      to: "ts extraction"
      via: "pure-zsh parameter expansion"
      pattern: 'base##\*-'
---

<objective>
Fix three usability and performance bugs in `update-list.sh`'s interactive machine-label
handling:

1. `resolve_machine_label` — surface hostname + catalog-file labels as candidates, default
   to hostname on empty Enter, so a fresh-machine user is never forced to invent a name.
2. `resolve_machine_label` + `rename_machine` — re-prompt on bad menu choice or invalid
   new-label entry instead of calling `exit 1` mid-interaction.
3. `rename_machine` step 5 — replace the 3-subprocess-per-file `echo | grep | cut` chain
   with pure-zsh `${base##*-}` parameter expansion.

Purpose: Eliminate friction and unexpected exits during interactive label resolution; cut
subprocess overhead on rename operations over large catalog histories.

Output: Updated `update-list.sh` with all three fixes; syntax-verified and snippet-tested.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@update-list.sh
</context>

<safety_constraint>
NEVER run `./update-list.sh` end-to-end for verification. End-to-end execution moves real
catalog files, triggers archive deletion, and fires `git commit/push` against the live repo.
All verification MUST be performed via:
  - `zsh -n update-list.sh` (syntax check only)
  - `grep` assertions against the source text
  - Isolated function tests inside a `mktemp -d` fixture with `source update-list.sh` or
    inline sourcing of the affected function in a throw-away Zsh subprocess
</safety_constraint>

<tasks>

<task type="auto">
  <name>Task 1: Rebuild resolve_machine_label interactive path with hostname-first candidates and re-prompt loops</name>
  <files>update-list.sh</files>
  <action>
Replace the interactive section of `resolve_machine_label` (the block that begins at the
comment "# 4. Interactive numbered-menu path" through the closing `upsert_machine_label`
call, currently ~lines 441-496) with the following revised logic. All other paths (flag,
map-lookup, TTY guard) are unchanged.

**Candidate-list construction (replaces lines 443-460):**

Build `labels` as the UNION of three sources, in order, deduplicating across all three:

a. Current hostname: `local current_host=$(hostname)`. Prepend it as `labels[1]`
   unconditionally — it is always listed first.

b. Labels from `machine-labels.tsv` (same read loop as today; skip comments/blanks/no-label
   entries; skip if already in `labels`).

c. Labels parsed from catalog filenames across all four directories
   `("personal" "personal/archive" "office" "office/archive")` — use the same
   `setopt local_options null_glob` / `for file in "${dir_path}"/mac-software-list-*.txt`
   glob + `${filename#*\[}` / `${tmp%\]-*}` extraction that `rename_machine` step 2b
   already uses (lines 550-575). Skip if label already in `labels`.

After building the list, `create_new_idx=$(( ${#labels[@]} + 1 ))`.

**Menu display:**

Print `"  1) ${labels[1]}   (keep current machine name)"` for the first entry, then
`"  ${i}) ${labels[$i]}"` for entries 2..N, then `"  ${create_new_idx}) Create new label"`.

**Prompt + re-prompt loop (replaces lines 462-496):**

Wrap the prompt in a `while true` loop:

```
prompt: "Enter your choice [1-${create_new_idx}, or Enter for 1]: "
read -r choice
```

- If `choice` is empty: set `choice=1` and break (default to keep current hostname — FIX 1).
- If `choice` is a positive integer in range `[1..create_new_idx]`: break (valid pick).
- Otherwise: print `"ERROR: Invalid choice '${choice}'. Please enter 1-${create_new_idx}."` and
  continue the loop (FIX 2 — no `exit 1`).

**"Create new label" sub-loop (replaces lines 484-489):**

When `(( choice == create_new_idx ))`, enter a `while true` loop:

```
prompt: "Enter a label for this machine: "
read -r new_label
```

Call `validate_machine_label_quiet "$new_label"` (introduced in Task 2). If it returns
non-zero, print the reason and continue; if it returns 0, break. Assign
`MACHINE_LABEL="$new_label"`.

For valid numbered picks `(( choice != create_new_idx ))`, keep the existing 1-indexed
access: `MACHINE_LABEL="${labels[$choice]}"` — do NOT change to `choice - 1`.

End with `echo "Machine label: ${MACHINE_LABEL}"` and `upsert_machine_label`.
  </action>
  <verify>
    <automated>
# 1. Syntax check
zsh -n /Users/ken/dev/mac-software-list/update-list.sh

# 2. Hostname appears in candidate list
grep -n 'hostname' /Users/ken/dev/mac-software-list/update-list.sh | grep -v '^#'

# 3. Default-to-1 on empty Enter is present
grep -n 'choice=1' /Users/ken/dev/mac-software-list/update-list.sh

# 4. Re-prompt loop present (while true around the main menu)
grep -n 'while true' /Users/ken/dev/mac-software-list/update-list.sh

# 5. No exit 1 in the resolve_machine_label interactive path (lines 440-510)
# (TTY guard exit at ~line 438 is OK; check only the menu section)
awk 'NR>=441 &amp;&amp; NR<=510 {print NR": "$0}' /Users/ken/dev/mac-software-list/update-list.sh | grep 'exit 1' | grep -v 'TTY\|non-interactive'

# 6. Isolated function test — simulate empty-Enter defaulting to hostname
zsh -c '
  SCRIPT_DIR=$(mktemp -d)
  MACHINE_LABEL=""
  AUTO_COMMIT=false
  RENAME_MODE=false
  ARCHIVE_AGE_DAYS=60
  ARCHIVE_DAYS_SET=false
  # Stub out upsert_machine_label to be a no-op
  upsert_machine_label() { : ; }
  source /Users/ken/dev/mac-software-list/update-list.sh
  # Feed empty line to stdin (simulates pressing Enter)
  result=$(echo "" | (SCRIPT_DIR="$SCRIPT_DIR"; resolve_machine_label 2>&amp;1 || true))
  expected=$(hostname)
  if echo "$result" | grep -qF "$expected"; then
    echo "PASS: hostname selected on empty Enter"
  else
    echo "FAIL: expected hostname $expected in output; got: $result"
    exit 1
  fi
  rm -rf "$SCRIPT_DIR"
'
    </automated>
  </verify>
  <done>
- `zsh -n update-list.sh` exits 0.
- Empty Enter resolves to the current hostname (test passes).
- No `exit 1` in the interactive menu or new-label sub-path of `resolve_machine_label`.
- Labels sourced from map file AND catalog filenames AND current hostname, deduplicated, hostname first.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add validate_machine_label_quiet and re-prompt loop in rename_machine</name>
  <files>update-list.sh</files>
  <action>
**Part A — Add `validate_machine_label_quiet` helper (insert immediately before or after
`validate_machine_label`, around line 143):**

Add a new function `validate_machine_label_quiet` that applies the same four validation
rules as `validate_machine_label` but uses `return 1` (non-fatal) instead of `exit 1`, and
emits the error reason to stdout so the caller can print it. Example signature:

```
validate_machine_label_quiet() {
    local val="$1"
    local reason=""
    # same checks as validate_machine_label, setting reason=... and return 1 on fail
    return 0
}
```

Keep `validate_machine_label` itself unchanged — the `--machine` flag path in
`parse_arguments` (~line 192) still calls it and its `exit 1` behaviour is correct there.

**Part B — Wrap the OLD-label menu in `rename_machine` step 3 in a re-prompt loop
(replaces lines 593-600):**

Replace the single `read -r choice` + `if ! [[ valid ]]` block with a `while true` loop:

```
prompt: "Enter your choice [1-${N}]: "
read -r choice
```

- If `choice` is a positive integer in range `[1..N]`: break.
- Otherwise: print `"ERROR: Invalid choice '${choice}'. Please enter 1-${N}."` and continue.
  Do NOT call `exit 1`.

Assign `old_label="${labels[$choice]}"` after the loop (Zsh 1-indexed, unchanged).

**Part C — Wrap the NEW-label prompt in `rename_machine` step 4 in a re-prompt loop
(replaces lines 604-610):**

Replace `read -r new_label` + `validate_machine_label "$new_label"` (which exits on bad
input) with a `while true` loop:

```
prompt: "Enter new label for '${old_label}': "
read -r new_label
```

Call `validate_machine_label_quiet "$new_label"`. If non-zero: print the returned reason
and continue. If zero: break.

The no-op guard (`new_label == old_label`) and collision warning that follow remain
unchanged.
  </action>
  <verify>
    <automated>
# 1. Syntax check
zsh -n /Users/ken/dev/mac-software-list/update-list.sh

# 2. validate_machine_label_quiet exists
grep -n 'validate_machine_label_quiet' /Users/ken/dev/mac-software-list/update-list.sh | grep '^[0-9]*:validate_machine_label_quiet()'

# 3. validate_machine_label_quiet uses return 1, not exit 1
awk '/^validate_machine_label_quiet\(\)/,/^}/' /Users/ken/dev/mac-software-list/update-list.sh | grep 'exit 1'
# expect: no output (no exit 1 inside the quiet variant)

# 4. rename_machine step 3 has no bare exit 1 after invalid choice
# (extract step 3 region by searching between "OLD label" and "NEW label" comments)
awk '/OLD label interactive pick/,/NEW label prompt/' /Users/ken/dev/mac-software-list/update-list.sh | grep 'exit 1'
# expect: no output

# 5. rename_machine step 4 has no bare exit 1 after bad new-label
awk '/NEW label prompt/,/No-op guard/' /Users/ken/dev/mac-software-list/update-list.sh | grep 'exit 1'
# expect: no output

# 6. validate_machine_label (original) still has exit 1 (--machine flag path unchanged)
awk '/^validate_machine_label\(\)/,/^}/' /Users/ken/dev/mac-software-list/update-list.sh | grep -c 'exit 1'
# expect: 4  (one per validation rule)

# 7. Unit test: quiet validator returns non-zero on empty string without killing subshell
zsh -c '
  source /Users/ken/dev/mac-software-list/update-list.sh
  validate_machine_label_quiet "" ; echo "exit=$?"
' | grep 'exit=1'
    </automated>
  </verify>
  <done>
- `zsh -n update-list.sh` exits 0.
- `validate_machine_label_quiet` exists, uses `return 1` (not `exit 1`), and fails correctly on empty/whitespace/bad-chars/tab inputs.
- `validate_machine_label` (original) is unchanged and still `exit 1`s for `--machine` flag path.
- Neither the OLD-label menu nor the NEW-label entry in `rename_machine` calls `exit 1` on bad input — both re-prompt.
  </done>
</task>

<task type="auto">
  <name>Task 3: Replace subprocess timestamp extraction in rename_machine step 5 with pure-zsh expansion</name>
  <files>update-list.sh</files>
  <action>
In `rename_machine` step 5, locate the timestamp extraction line (~line 645):

```zsh
local ts=$(echo "$filename2" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14)
```

Replace it with two lines of pure-zsh parameter expansion:

```zsh
local base="${filename2%.txt}"
local ts="${base##*-}"
```

Then update the empty-ts guard that follows (currently `if [[ -z "$ts" ]]`) to also
validate that `ts` is exactly 14 decimal digits:

```zsh
if [[ -z "$ts" || ! "$ts" =~ ^[0-9]{14}$ ]]; then
    echo "  WARNING: Could not parse timestamp from: ${filename2} — skipping"
    continue
fi
```

No other lines in the step 5 loop change. The `new_filename` construction, collision guard,
and `mv` call remain verbatim.

Rationale: the catalog filename format is
`mac-software-list-[LABEL]-YYYYMMDDHHMMSS.txt`. The label is bracketed so it cannot contain
`-`; the timestamp is the only token after the last `-` before `.txt`. `${filename2%.txt}`
strips the extension; `${base##*-}` strips everything through the last `-`, leaving the
14-digit timestamp. Zero subprocess forks.
  </action>
  <verify>
    <automated>
# 1. Syntax check
zsh -n /Users/ken/dev/mac-software-list/update-list.sh

# 2. Confirm the old pipeline is gone
grep -n 'grep -oE.*[0-9].*cut' /Users/ken/dev/mac-software-list/update-list.sh
# expect: no output

# 3. Confirm new expansion is present
grep -n 'base##\*-' /Users/ken/dev/mac-software-list/update-list.sh
# expect: at least 1 match

# 4. Confirm 14-digit validation is present
grep -n '\^[0-9]{14}\$' /Users/ken/dev/mac-software-list/update-list.sh
# expect: at least 1 match

# 5. Unit test: extraction correctness across three name shapes
zsh -c '
  pass=0; fail=0
  test_ts() {
    local filename2="$1" expected="$2"
    local base="${filename2%.txt}"
    local ts="${base##*-}"
    if [[ "$ts" =~ ^[0-9]{14}$ ]] && [[ "$ts" == "$expected" ]]; then
      echo "PASS: $filename2 -> $ts"; (( pass++ ))
    else
      echo "FAIL: $filename2 -> ts=$ts (expected $expected)"; (( fail++ ))
    fi
  }
  # Standard hostname (no dashes)
  test_ts "mac-software-list-[Mac.local]-20260123080017.txt"         "20260123080017"
  # Label with a dash inside brackets
  test_ts "mac-software-list-[My-Laptop]-20260309115433.txt"         "20260309115433"
  # Label matching computer-one.local style
  test_ts "mac-software-list-[computer-one.local]-20260406201933.txt" "20260406201933"
  # Malformed name (should fail validation)
  base2="mac-software-list-[Bad]"; ts2="${base2##*-}"
  if ! [[ "$ts2" =~ ^[0-9]{14}$ ]]; then
    echo "PASS: malformed name correctly rejected"
    (( pass++ ))
  else
    echo "FAIL: malformed name wrongly accepted as ts=$ts2"
    (( fail++ ))
  fi
  echo "Results: $pass passed, $fail failed"
  [[ $fail -eq 0 ]]
'
    </automated>
  </verify>
  <done>
- `zsh -n update-list.sh` exits 0.
- `grep 'grep -oE.*cut'` returns no matches in the rename loop.
- Pure-zsh `${base##*-}` expansion is present.
- Unit test passes all four cases including the malformed-name rejection guard.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| user stdin -> label string | Free-text input enters the script; must be sanitized before being embedded in filenames and TSV |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-ckx-01 | Tampering | machine label embedded in filename | mitigate | `validate_machine_label_quiet` rejects `/`, `[`, `]`, TAB, newline — same rules as existing validator |
| T-ckx-02 | Denial of Service | infinite re-prompt loop on EOF | accept | TTY guard upstream (`[[ ! -t 0 ]]`) prevents non-interactive invocation; EOF on a real TTY is handled by `read` returning non-zero which zsh treats as empty string — existing `while true` pattern is safe |
</threat_model>

<verification>
After all three tasks complete, run in order:

1. `zsh -n update-list.sh` — must exit 0 (no syntax errors)
2. Run Task 1 isolated function test (empty-Enter defaults to hostname)
3. Run Task 2 unit test (quiet validator returns 1 on invalid input without killing subshell)
4. Run Task 3 unit test (four timestamp extraction cases, all pass)
5. Confirm via grep that no `exit 1` remains in the interactive branches of
   `resolve_machine_label` (menu + new-label sub-loop) or `rename_machine` steps 3-4.
6. Confirm via grep that the old `grep -oE | cut` pipeline is absent from rename step 5.

Do NOT run `./update-list.sh` end-to-end.
</verification>

<success_criteria>
- `zsh -n update-list.sh` passes (no syntax errors introduced)
- Fresh-machine interactive path: hostname listed first, empty Enter selects it, no forced label creation
- Bad menu choice in `resolve_machine_label` or `rename_machine`: script re-prompts, does not exit
- Bad label text in interactive new-label entry: script re-prompts, does not exit
- `--machine` flag path: still `exit 1` on invalid label (unchanged)
- Rename step 5: timestamp extracted via `${filename2%.txt}` + `${base##*-}` with `^[0-9]{14}$` validation; zero subprocess forks
- All unit tests and grep assertions green
</success_criteria>

<output>
Create `.planning/quick/260614-ckx-fix-interactive-machine-label-ux-keep-ex/260614-ckx-SUMMARY.md` when done.
</output>
