---
phase: 06-retention-sync
reviewed: 2026-06-13T00:00:00Z
depth: standard
files_reviewed: 1
files_reviewed_list:
  - update-list.sh
findings:
  critical: 0
  warning: 3
  info: 0
  total: 3
status: issues_found
---

# Phase 06: Code Review Report

**Reviewed:** 2026-06-13
**Depth:** standard
**Files Reviewed:** 1 (`update-list.sh`)
**Status:** issues_found

## Summary

Reviewed `retain_newest_per_host` (~line 192), `prune_old_archives` (~line 269), the `git add -A` staging change (~line 1639), and the reordered main block (~lines 1687–1727). Priority was data-loss safety on `mv` and `rm` paths, git staging scope, and `--no-commit` compliance.

The core algorithm is sound: the two-pass associative-array approach is correct, hostname extraction handles real hostnames (`computer-one.local`, `computer-two.local`) correctly, the glob never reaches the archive subdirectory, unparseable timestamps are skipped not deleted, tied-newest files are both kept, `null_glob` is set before each loop, call order is correct (generate → retain → prune → git gate), and `SYNC-02` is satisfied. No data-loss critical bugs were found.

Three warnings were found: two are unchecked `mv`/`rm` exit codes that produce misleading output on failure (not data-loss, but incorrect state reporting), and one is a stale `git add .` in the manual `--no-commit` guidance that contradicts the carefully-scoped `git add -A "${TARGET_LOCATION}/"` used in the automatic path.

---

## Warnings

### WR-01: `mv` exit code unchecked — misleading "Archived" report on failure

**File:** `update-list.sh:241-243`
**Issue:** The `mv` call has no exit-code check. If `mv` fails (permissions error, disk full, read-only filesystem), the file stays in the main folder but the script prints `"  Archived: $filename"` and increments `moved_count` as if the operation succeeded. The final summary will report N file(s) archived when zero were actually moved.

On the next run `retain_newest_per_host` will re-evaluate the file correctly (it is still in the main folder with an old timestamp), so there is no data loss — but the misleading output obscures the failure and the run's final state is inconsistent with what git will stage.

```zsh
# Current (lines 241-243):
mv "$file" "${archive_path}/"
echo "  Archived: $filename"
((moved_count++))

# Fixed — check mv exit code and skip echo/increment on failure:
if mv "$file" "${archive_path}/"; then
    echo "  Archived: $filename"
    ((moved_count++))
else
    echo "  WARNING: Failed to archive: $filename — file left in place"
fi
```

---

### WR-02: `rm` exit code unchecked — misleading "Pruned" report on failure

**File:** `update-list.sh:297-299`
**Issue:** Same pattern as WR-01 in `prune_old_archives`. If `rm` fails (file locked, permissions), the file is reported as pruned and counted but remains on disk. On the next run the timestamp comparison will evaluate it again and attempt `rm` again — no permanent data loss — but the current run reports incorrect state and the git staging will not include the expected deletion.

```zsh
# Current (lines 297-299):
rm "$file"
echo "  Pruned: $filename"
((pruned_count++))

# Fixed:
if rm "$file"; then
    echo "  Pruned: $filename"
    ((pruned_count++))
else
    echo "  WARNING: Failed to prune: $filename — file left in archive"
fi
```

---

### WR-03: `--no-commit` manual instruction uses `git add .` (stages whole repo)

**File:** `update-list.sh:1726`
**Issue:** The manual recovery message printed when `--no-commit` is used instructs the user to run:

```
cd $SCRIPT_DIR && git add . && git commit -m 'Added catalog' && git push
```

`git add .` (without a path restriction) stages every change in the working tree under `SCRIPT_DIR` — including `.planning/`, `update-list.sh` itself if modified, and the other location directory (`office/` or `personal/` depending on which was targeted). This directly contradicts the carefully-scoped `git add -A "${TARGET_LOCATION}/"` used in the automatic commit path and could cause a user who copies this command to accidentally commit unrelated planning artifacts or both location directories at once.

```zsh
# Current (line 1726):
echo "  cd $SCRIPT_DIR && git add . && git commit -m 'Added catalog' && git push"

# Fixed — mirror the automatic path and include TARGET_LOCATION:
echo "  cd ${SCRIPT_DIR} && git add -A \"${TARGET_LOCATION}/\" && git commit -m 'Added ${TARGET_LOCATION} catalog for [${CURRENT_MACHINE}] at ${CURRENT_DATE}' && git push"
```

---

## Data-Loss Safety Confirmation (no findings)

The following properties were verified correct:

- **`rm` scope:** `prune_old_archives` only iterates `"${archive_path}"/mac-software-list-*.txt` — strictly the archive subdirectory of the targeted location. Cannot reach the main folder, the other location, or non-catalog files.
- **`mv` scope:** Pass 2 only moves files from `"${full_path}"/mac-software-list-*.txt` (the main folder) to `"${archive_path}/"`. Cannot reach outside `${SCRIPT_DIR}/${target_dir}/`.
- **Newest-per-host never archived:** Pass 2 skips any file where `ts == newest_ts[$host]`. The just-generated file has the highest timestamp for its host and is always kept.
- **Tied-newest kept:** Both files satisfy `ts == newest_ts[$host]` and both skip the `mv` branch. Data-loss-averse. Correct.
- **Unparseable timestamp:** `[[ -z "$timestamp" ]] → continue` in `prune_old_archives` (line 292) and the combined guard `[[ -z "$ts" || -z "$host" || "$host" == "$filename" ]]` in both passes of `retain_newest_per_host` (lines 216, 234). Unparseable files are never moved or deleted.
- **Bracket handling in filenames:** `"${full_path}"/mac-software-list-*.txt` glob correctly matches filenames containing `[` and `]` because the `*` wildcard expands to any characters. The `[` in filenames does not act as a glob character class since it is in the matched portion (after the literal prefix `mac-software-list-`).
- **Hostname extraction with dots/hyphens:** `${filename#*\[}` / `${tmp%\]-*}` verified correct for `computer-one.local` and `computer-two.local`.
- **`git add -A "${TARGET_LOCATION}/"` scope:** `git_commit_and_push` cds to `SCRIPT_DIR` first (line 1625), then stages `"${TARGET_LOCATION}/"` — a relative path restricted to the targeted location directory. Does not stage `.planning/`, `update-list.sh`, or the other location.
- **SYNC-02 (`--no-commit`):** `retain_newest_per_host` (line 1714) and `prune_old_archives` (line 1717) execute unconditionally before the `if [[ "$AUTO_COMMIT" == "true" ]]` gate at line 1720. Disk operations run; only the git step is skipped.
- **Call order:** `generate_catalog` (1702) → `retain_newest_per_host` (1714) → `prune_old_archives` (1717) → git gate (1720). The just-written catalog is present and newest when the retention sweep runs.
- **`null_glob` coverage:** `setopt local_options null_glob` is called once per function before each set of loops (line 207 covers both passes in `retain_newest_per_host`; line 285 covers `prune_old_archives`). Empty directories produce zero iterations without error.
- **`typeset -A newest_ts` scope:** Function-local in Zsh (verified). Does not leak between calls.
- **Archive dir not iterated by Pass 1/2:** The `archive/` directory name does not match `mac-software-list-*.txt`. Defense-in-depth `[[ -d "$file" ]] && continue` guard also present.
- **Idempotence:** A second consecutive run finds only newest-per-host in main/, generates a new file (T2 > T1), archives T1, leaves other hosts' files untouched. Stable.

---

## Severity Summary

| ID | Severity | Description |
|----|----------|-------------|
| WR-01 | WARNING | `mv` exit code unchecked — misleading archived count on failure |
| WR-02 | WARNING | `rm` exit code unchecked — misleading pruned count on failure |
| WR-03 | WARNING | `--no-commit` manual instruction uses `git add .` instead of scoped `git add -A "${TARGET_LOCATION}/"` |

**Critical:** 0 | **Warning:** 3 | **Info:** 0

---

_Reviewed: 2026-06-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
