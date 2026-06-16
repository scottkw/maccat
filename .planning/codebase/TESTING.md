# Testing Patterns

**Analysis Date:** 2026-06-12

## Test Framework

**Runner:** None — no automated test framework exists for this project.

**Assertion Library:** None.

**Test Files:** None. No `*.test.*`, `*.spec.*`, or `test/` directory is present in the
repository.

## Current State

This project has no automated tests. The sole artifact under test is `update-list.sh`
(~19KB, ~513 lines). Validation happens exclusively through manual execution on real
macOS machines and inspection of the committed output files in the `personal/` and
`office/` directories.

Evidence of correctness is indirect: the git log records successful runs across multiple
machines (`computer-one.local`, `computer-two.local`, `computer-two.local`),
and the presence of timestamped `.txt` catalog files proves the script executed without
aborting.

## Manual Validation Approach

The script is validated manually by:

1. **Running with each flag combination and verifying output:**
   ```bash
   ./update-list.sh --personal --no-commit   # No git side-effects
   ./update-list.sh --office --no-commit
   ./update-list.sh --personal               # Includes git commit+push
   ```

2. **Inspecting the generated catalog file** for the expected four sections:
   - `Homebrew Packages`
   - `App Store Applications`
   - `Setapp Applications`
   - `Web-installed Applications`

3. **Checking archiving behavior** by temporarily setting `ARCHIVE_AGE_DAYS=0` and
   running the script against a directory with existing `.txt` files, then confirming
   they were moved to `archive/`.

4. **Verifying git operations** by checking `git log` after a run to confirm the
   commit message matches the expected format:
   `Added personal catalog for [hostname] at YYYYMMDDHHMMSS`

5. **Testing error paths** by running with an invalid flag:
   ```bash
   ./update-list.sh --bad-flag   # Should print ERROR and exit 1
   echo $?                       # Expect: 1
   ```

## If Tests Were Added

If automated testing were introduced, the recommended approach for a zsh/shell script
of this type is **bats-core** (Bash Automated Testing System), which also works with zsh.

**Installation:**
```bash
brew install bats-core
```

**Run command:**
```bash
bats test/                   # Run all test files
bats test/update-list.bats   # Run a specific file
```

**Example test structure using bats-core:**

```bash
#!/usr/bin/env bats

# test/update-list.bats

setup() {
    # Create a temp directory to act as SCRIPT_DIR
    TMPDIR=$(mktemp -d)
    cp update-list.sh "$TMPDIR/"
    chmod +x "$TMPDIR/update-list.sh"
}

teardown() {
    rm -rf "$TMPDIR"
}

@test "rejects invalid flag with exit code 1" {
    run "$TMPDIR/update-list.sh" --bad-flag
    [ "$status" -eq 1 ]
    [[ "$output" == *"ERROR: Invalid option"* ]]
}

@test "creates output file in personal directory" {
    run "$TMPDIR/update-list.sh" --personal --no-commit
    [ "$status" -eq 0 ]
    # Check a .txt file was created under personal/
    [ "$(ls "$TMPDIR/personal/"mac-software-list-*.txt 2>/dev/null | wc -l)" -gt 0 ]
}
```

## Coverage

**Requirements:** None enforced.

**Assessed coverage:**
- **Happy path (personal, office):** Validated via real runs (evidence: committed `.txt` files)
- **`--no-commit` path:** Validated manually
- **Invalid argument handling:** Not systematically tested
- **Archive cutoff logic:** Not automatically tested — timestamp comparison relies on
  `date -v-Nd` (macOS-only) and has no unit test
- **Missing optional tools (brew, mas, Setapp):** Not automatically tested; behavior
  is observable only on machines where those tools are absent

## Risk Areas Without Tests

**Timestamp parsing in `archive_old_catalogs`:**
- File: `update-list.sh` lines 220–228
- The `grep -oE '[0-9]{14}\.txt$' | cut -c1-8` pipeline is fragile — a filename with
  a different extension or format silently produces an empty `$timestamp` and logs a
  WARNING rather than erroring.

**`$?` after a pipe (lines 304–307):**
- `mas list 2>/dev/null | awk ... >> "$OUTPUT_FILE"` — `$?` captures `awk`'s exit
  code, not `mas`'s. A `mas` failure would not be detected. No test catches this.

**zsh-only features:**
- `${0:A:h}` path resolution and `{filename:t}` are zsh-specific. Running the script
  under `bash` silently produces wrong behavior. No compatibility tests exist.

---

*Testing analysis: 2026-06-12*
