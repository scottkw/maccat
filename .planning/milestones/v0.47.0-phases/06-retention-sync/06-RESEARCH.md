# Phase 6: Retention & Sync - Research

**Researched:** 2026-06-13
**Domain:** Zsh shell script — archive/retention logic, filename parsing, git staging
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **"Newest per machine"** is determined from the FILENAME: group catalogs by the `[hostname]`
  segment in `mac-software-list-[hostname]-YYYYMMDDHHMMSS.txt`, and within each hostname keep the
  highest `YYYYMMDDHHMMSS` timestamp (lexicographic comparison — the fixed-width timestamp makes
  string sort == chronological sort). Not mtime.
- **Move-to-archive:** plain `mv` of older-per-host catalogs from the main folder into
  `<location>/archive/`. Git staging is done once with `git add -A "<location>"` (or equivalent)
  so additions, renames (moves), and deletions are all captured in one commit.
- **30-day prune:** plain `rm` on disk of `archive/` catalogs whose filename timestamp is older
  than 30 days. The disk op runs on every invocation regardless of git; the same `git add -A`
  stages the deletions.
- **Order within a run:** `git pull` (existing, at start) → generate the new catalog (existing) →
  **retention sweep** (archive all-but-newest-per-host in the main folder) → **30-day prune**
  (rm old files in archive/) → `git add -A` + commit + push. Generating BEFORE the sweep
  guarantees the just-written file is the newest and is never archived.
- **File selection:** operate ONLY on files matching the catalog name pattern
  `mac-software-list-[*]-*.txt`. Never touch other files, and never treat the `archive/`
  directory (or any non-matching file) as a catalog.
- **Identical newest timestamp for the same host:** keep ALL tied-newest files — never delete or
  archive on a timestamp ambiguity (data-loss-averse).
- **Pre-existing pending-deleted catalogs:** the ~19 old catalogs currently showing as deleted in
  the working tree are absorbed naturally by the new retention/prune + `git add -A` commit — no
  separate cleanup commit needed.
- **`--no-commit`:** the retention sweep and 30-day prune disk operations STILL run; only the git
  commit/push step is skipped (SYNC-02).
- `ARCHIVE_AGE_DAYS` changes from 60 → 30. Its SEMANTICS change: previously it meant "move
  catalogs older than 60 days from main → archive"; now the main folder keeps newest-per-machine
  (regardless of age) and `ARCHIVE_AGE_DAYS` governs the HARD-DELETE prune of the archive folder.

### Claude's Discretion
(None specified — all mechanics are locked.)

### Deferred Ideas (OUT OF SCOPE)
- Configurable retention window / "keep N per machine"
- Rewriting git history to purge already-committed old catalogs
- Pruning both locations on a single run
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RET-01 | On every run, the targeted location's main folder retains only the newest catalog per machine; every older catalog for each hostname is moved to `archive/` | Per-host grouping + newest selection via Zsh associative arrays (Q2); verified against real filenames |
| RET-02 | Catalog files in `archive/` whose filename timestamp is older than 30 days are hard-deleted from disk | BSD `date -v-30d` cutoff + existing grep timestamp extraction (Q1); verified working on this machine |
| RET-03 | Retention and pruning are scoped to the targeted location only | Functions take `$1` (target_dir); only `${SCRIPT_DIR}/${target_dir}/` and `${SCRIPT_DIR}/${target_dir}/archive/` are touched |
| RET-04 | Retention and pruning never abort the run — empty folder, missing archive/, unparseable timestamp handled gracefully (warn-and-continue) | Null-glob guard + `-z "$ts"` skip pattern (existing convention); `mkdir -p` for archive/ |
| SYNC-01 | git commit/push stages all working-tree changes — additions, moves, deletions — in a single commit | `git add -A "${TARGET_LOCATION}/"` verified to stage deletions + adds; replaces current targeted `git add` calls |
| SYNC-02 | `--no-commit` skips commit/push but retention/prune disk ops still run | Retention/prune run unconditionally before the `AUTO_COMMIT` check; `git_commit_and_push` is only called when `AUTO_COMMIT=true` |
</phase_requirements>

---

## Summary

Phase 6 replaces `archive_old_catalogs` with two focused functions: a **retention sweep** that keeps the newest catalog per hostname in the main folder and moves all others to `archive/`, and a **30-day prune** that hard-deletes archive files whose filename timestamp is older than 30 days. The `git_commit_and_push` function is updated to stage all working-tree changes in the targeted location with `git add -A` instead of the current targeted `git add` calls. The main-block call order is corrected to run retention and prune AFTER `generate_catalog`.

The implementation is almost entirely a rework of existing code patterns. All critical primitives are verified working on this machine: BSD `date -v-30d` arithmetic, the `grep -oE '[0-9]{14}\.txt$' | cut -c1-8` timestamp extraction, Zsh parameter expansion for hostname extraction, Zsh associative arrays for per-host grouping, and `git add -A personal/` for staging deletions. No new dependencies are required.

**Primary recommendation:** Replace `archive_old_catalogs` with two new functions (`retain_newest_per_host` and `prune_old_archives`), change `ARCHIVE_AGE_DAYS=60` to `=30`, update `git_commit_and_push` to use `git add -A "${TARGET_LOCATION}/"`, and reorder the main block so generate → retain → prune → commit.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-host newest selection | Shell (update-list.sh) | — | Pure filename parsing + associative array logic; no external tools |
| 30-day archive prune | Shell (update-list.sh) | — | BSD date arithmetic + rm; same pattern as existing cutoff logic |
| git staging of all changes | Shell (update-list.sh) | git | `git add -A` delegates to git; script controls the scope path |
| Call-order orchestration | Main block (update-list.sh) | — | Top-level sequencing; no function-level changes to generate_catalog |

---

## Q1: BSD Date Arithmetic for the 30-Day Cutoff

**Verified on this machine (macOS, git 2.50.1, Zsh).**

### Cutoff computation

The existing `archive_old_catalogs` function at line 207 uses:

```zsh
local cutoff_date=$(date -v-${ARCHIVE_AGE_DAYS}d "+%Y%m%d")
```

With `ARCHIVE_AGE_DAYS=30` this produces an 8-digit date string (e.g., `20260514` when today is
`20260613`). [VERIFIED: confirmed via `date -v-30d "+%Y%m%d"` on this machine — output: `20260514`]

### Timestamp extraction from filename

The existing function extracts the date portion of the 14-digit filename timestamp using:

```zsh
local timestamp=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-8)
```

This strips the filename suffix to isolate the 14-digit timestamp, then takes the first 8
characters (YYYYMMDD). [VERIFIED: tested against real filenames on this machine]

Real filename verification:
- `mac-software-list-[computer-one.local]-20260609144429.txt` → `20260609` [VERIFIED]
- `mac-software-list-[computer-two.local]-20260607205427.txt` → `20260607` [VERIFIED]
- `mac-software-list-[computer-one.local]-20250106144526.txt` (archive) → `20250106` [VERIFIED]

### Comparison

The existing comparison pattern (string comparison works because the fixed-width format makes
lexicographic sort identical to chronological sort):

```zsh
if [[ "$timestamp" -lt "$cutoff_date" ]]; then
    # older than cutoff — prune
fi
```

Both `"$timestamp"` and `"$cutoff_date"` are 8-digit numeric strings; `-lt` (integer comparison)
and `<` (string comparison) are both safe here because YYYYMMDD zero-pads naturally. The existing
code uses `-lt` — reuse it.

### Unparseable timestamp: skip, never delete

The existing guard at line 227-229 is the correct pattern:

```zsh
if [[ -z "$timestamp" ]]; then
    echo "  WARNING: Could not parse timestamp from: $filename"
    continue
fi
```

An empty `$timestamp` (grep returned nothing) triggers a warning and `continue` — the file is
skipped. This is the RET-04 requirement. A file with an unparseable timestamp is NEVER deleted
or moved. [VERIFIED: pattern confirmed in existing code; tested with `mac-software-list-[somehost]-badname.txt` → empty result from grep]

---

## Q2: Per-Host Grouping + Newest Selection in Zsh

**All code patterns verified against real filenames on this machine.**

### Correct glob for the main folder

```zsh
for file in "${full_path}"/mac-software-list-*.txt; do
    [[ -e "$file" ]] || continue        # null-glob guard
    [[ -d "$file" ]] && continue        # skip if somehow a directory
```

The `archive/` subdirectory is named `archive`, which does NOT match `mac-software-list-*.txt`,
so it is never enumerated. [VERIFIED: tested `ls personal/` — archive dir name has no match]

### Hostname extraction via parameter expansion

The `[hostname]` segment sits between the first `[` and the last `]-` before the timestamp:

```zsh
local filename="${file:t}"          # basename via Zsh :t modifier
local tmp="${filename#*\[}"         # strip up to and including the first [
local host="${tmp%\]-*}"            # strip from ]-YYYYMMDDHHMMSS.txt onward
```

[VERIFIED: tested against real filenames]
- `mac-software-list-[computer-one.local]-20260609144429.txt` → `computer-one.local`
- `mac-software-list-[computer-two.local]-20260607205427.txt` → `computer-two.local`

Both hostnames contain dots and hyphens; the `#*\[` / `%\]-*` pair handles them correctly.

### 14-digit timestamp extraction

Reuse the existing grep pattern (full 14 digits instead of 8 for comparison):

```zsh
local ts=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14)
```

[VERIFIED: `20260609144429` extracted correctly from real filenames]

### Two-pass associative array approach

Zsh associative arrays (`typeset -A`) are the correct pattern here. The algorithm requires two
passes: first to find the max timestamp per host, then to decide what to archive.

**Pass 1 — find newest timestamp per host:**

```zsh
typeset -A newest_ts    # host -> newest timestamp string (14 digits)

for file in "${full_path}"/mac-software-list-*.txt; do
    [[ -e "$file" ]] || continue
    [[ -d "$file" ]] && continue
    local filename="${file:t}"
    local tmp="${filename#*\[}"
    local host="${tmp%\]-*}"
    local ts=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14)
    if [[ -z "$ts" || -z "$host" ]]; then
        echo "  WARNING: Could not parse hostname/timestamp from: $filename"
        continue
    fi
    # Keep the lexicographically larger (newer) timestamp
    if [[ -z "${newest_ts[$host]}" || "$ts" > "${newest_ts[$host]}" ]]; then
        newest_ts[$host]="$ts"
    fi
done
```

**Pass 2 — archive files that are NOT the newest:**

```zsh
local moved_count=0

for file in "${full_path}"/mac-software-list-*.txt; do
    [[ -e "$file" ]] || continue
    [[ -d "$file" ]] && continue
    local filename="${file:t}"
    local tmp="${filename#*\[}"
    local host="${tmp%\]-*}"
    local ts=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14)
    if [[ -z "$ts" || -z "$host" ]]; then
        continue    # already warned in pass 1 (or warn again — same guard)
    fi
    # Skip if this IS the newest for its host (includes tied-newest case)
    if [[ "$ts" == "${newest_ts[$host]}" ]]; then
        continue
    fi
    # This file is older — move to archive/
    mv "$file" "${archive_path}/"
    echo "  Archived: $filename"
    ((moved_count++))
done
```

**Tied-timestamp case:** If two files for the same host happen to have the same 14-digit
timestamp (impossible in practice but required by spec), both will have `ts == newest_ts[host]`
and BOTH will be skipped (kept in main). No data loss. [ASSUMED: the 14-digit timestamp
(seconds precision) makes true ties impossible in normal operation, but the code is correct per
the data-loss-averse spec.]

**Empty main folder:** The `[[ -e "$file" ]] || continue` null-glob guard means an empty folder
produces zero iterations — the loop exits immediately. No error, no warning needed. [VERIFIED:
standard Zsh null-glob pattern used throughout the existing script]

---

## Q3: `git add -A` Scoping + Deletion Propagation

**Verified by running `git add -A personal/` on this repo and inspecting staging.**

### What `git add -A "${TARGET_LOCATION}/"` captures

`git add -A <path>` stages all working-tree changes under `<path>`:
- **New file (the just-generated catalog):** staged as `A` (add)
- **Files moved to archive/ (mv = unlink + create):** staged as `D` in main folder + `A` in archive/
- **Files deleted by 30-day prune (rm):** staged as `D`

[VERIFIED: `git add -A personal/` on this repo successfully staged the 20 pending `D` deletions
that were previously unstaged. `git status --short personal/` showed them change from ` D` to `D `.]

### Pull on another machine removes pruned files

When a git pull is done on another machine after the commit, git applies the staged deletions to
its working tree. Files that were `rm`-ed on the committing machine and staged as `D` are removed
from the other machine's working tree on pull. This is standard git behavior. [ASSUMED: based on
git's standard working tree sync semantics; no cross-machine test was run.]

### Current `git_commit_and_push` staging (lines 1576-1581)

The current function stages:
```zsh
git add "${TARGET_LOCATION}/${OUTPUT_FILENAME}"          # only the new catalog
git add "${TARGET_LOCATION}/archive/" 2>/dev/null || true   # archive dir (adds only)
```

This does NOT stage deletions (rm'd files) or files moved out of main. It must be replaced with:

```zsh
git add -A "${TARGET_LOCATION}/"
```

The trailing `/` is optional but makes the intent clear (stage all changes under that directory
tree). The `2>/dev/null || true` safety wrapper is no longer needed because `git add -A` on a
directory that has no changes is a no-op (exit 0).

### `--no-commit` path

When `AUTO_COMMIT=false`, `git_commit_and_push` is not called (existing `if` check at line 1659).
The retention sweep and prune run unconditionally before that check, so all disk changes are made
but nothing is staged or committed. The working tree is left in a modified state with moved and
deleted files. [VERIFIED: existing code structure at lines 1659-1666 confirms this.]

---

## Q4: Call-Order Correctness

### Current main-block order (CONFIRMED from code)

```
line 1629: git_pull
line 1632: archive_old_catalogs "$TARGET_LOCATION"   ← runs BEFORE CURRENT_DATE/MACHINE are set
line 1636: CURRENT_DATE=$(date "+%Y%m%d%H%M%S")
line 1637: CURRENT_MACHINE=$(hostname)
line 1638: OUTPUT_FILENAME="mac-software-list-[${CURRENT_MACHINE}]-${CURRENT_DATE}.txt"
line 1641: OUTPUT_FILE="${SCRIPT_DIR}/${TARGET_LOCATION}/${OUTPUT_FILENAME}"
line 1644: mkdir -p "${SCRIPT_DIR}/${TARGET_LOCATION}"
line 1647: generate_catalog
line 1659: if AUTO_COMMIT → git_commit_and_push
```

**Bug in current order:** `archive_old_catalogs` runs before the new catalog is generated. This
means the just-written catalog could theoretically be archived if its timestamp fell below the
cutoff (impossible with 60-day cutoff, but with a 30-day cutoff still safe since the file is
brand-new — however the RET-01 semantics now require "newest per host", not "older than N days",
so the order MUST change).

### Corrected main-block order

The new order must move `CURRENT_DATE` / `CURRENT_MACHINE` / `OUTPUT_FILENAME` / `OUTPUT_FILE`
and `generate_catalog` BEFORE the new retention/prune functions:

```zsh
# 1. Pull
git_pull

# 2. Set timestamp + output path (moved up — generate_catalog needs OUTPUT_FILE)
CURRENT_DATE=$(date "+%Y%m%d%H%M%S")
CURRENT_MACHINE=$(hostname)
OUTPUT_FILENAME="mac-software-list-[${CURRENT_MACHINE}]-${CURRENT_DATE}.txt"
OUTPUT_FILE="${SCRIPT_DIR}/${TARGET_LOCATION}/${OUTPUT_FILENAME}"
mkdir -p "${SCRIPT_DIR}/${TARGET_LOCATION}"

# 3. Generate the new catalog (writes OUTPUT_FILE)
generate_catalog

# 4. Retention sweep: keep newest per host in main/, archive rest
retain_newest_per_host "$TARGET_LOCATION"

# 5. 30-day prune: hard-delete old files from archive/
prune_old_archives "$TARGET_LOCATION"

# 6. Stage + commit (or skip if --no-commit)
if [[ "$AUTO_COMMIT" == "true" ]]; then
    git_commit_and_push
fi
```

**Why this is safe:**
- `generate_catalog` writes the file with `CURRENT_DATE` timestamp. Since `CURRENT_DATE` is set
  immediately before `generate_catalog`, the new file's timestamp is always the most recent file
  for this host.
- `retain_newest_per_host` runs after the new file exists. When it scans the main folder, the
  just-written file will have the largest timestamp for `CURRENT_MACHINE` and will be kept. All
  older files for this host (including the previous "newest") are moved to archive/.
- For the OTHER host (`computer-two.local`), its single file is always its own newest — no move.
- `prune_old_archives` then scans archive/ for the 30-day cutoff delete.

### Variable scope notes

- `archive_old_catalogs` was replaced — its split successors (`retain_newest_per_host`,
  `prune_old_archives`) both take `$1` (target_dir) as argument, same as the original.
- Both new functions use `SCRIPT_DIR` and `ARCHIVE_AGE_DAYS` globals, same as the original.
- Neither new function references `OUTPUT_FILE`, `OUTPUT_FILENAME`, `CURRENT_DATE`, or
  `CURRENT_MACHINE` — they work purely from the filesystem contents.
- No other function signatures change.

---

## Q5: Idempotence + Safety

### Second consecutive run is stable

After Run 1:
- `personal/` contains: `mac-software-list-[computer-one.local]-<T1>.txt` and
  `mac-software-list-[computer-two.local]-<T_mac>.txt`

Run 2 generates `mac-software-list-[computer-one.local]-<T2>.txt` (T2 > T1).
`retain_newest_per_host` scans the main folder, finds T2 is the newest for
`computer-one.local`, and moves T1 to archive/. `computer-two.local` has only one
file — it stays. No other files are moved. The prune runs on archive/ but won't touch T1 (it's
brand new). Result: `personal/` still has exactly 2 files (one per host), just the local one
updated. No churn beyond the expected replacement. [ASSUMED: verified by logical analysis of the
two-pass algorithm above; no second actual run was performed.]

### No run can delete the newest catalog for a host

Pass 2 of `retain_newest_per_host` skips any file where `ts == newest_ts[host]`. The only/newest
file for a host always satisfies this condition and is never moved. [VERIFIED: algorithm confirmed
by test run of two-pass logic against real files — `computer-two.local` had one file; it remained.]

### No run can delete a file not matching the catalog pattern

Both new functions only iterate over `"${full_path}"/mac-software-list-*.txt`. Files not
matching that glob are never touched. Non-matching files (e.g., `.DS_Store`, `README.md`, or
any future files added to the directory) are invisible to the loop.

### No run can touch the other (non-targeted) location

Both new functions operate on `"${SCRIPT_DIR}/${target_dir}"` where `target_dir` is the `$1`
argument. `retain_newest_per_host "$TARGET_LOCATION"` and `prune_old_archives "$TARGET_LOCATION"`
only access the targeted location. `personal/` and `office/` are never touched in the same run.

### `archive/` is created if missing

The existing `archive_old_catalogs` pattern (retain) uses:

```zsh
if [[ ! -d "$archive_path" ]]; then
    mkdir -p "$archive_path"
    echo "  Created archive directory: ${archive_path}"
fi
```

Reuse this exact pattern in `retain_newest_per_host`. For `prune_old_archives`, the archive dir
may also be absent (e.g., first run on a machine with no old catalogs) — guard with the same
check OR simply check `[[ -d "$archive_path" ]] || return 0` before looping.

### Empty main folder is handled gracefully

The null-glob guard `[[ -e "$file" ]] || continue` means an empty main folder (or one with only
the `archive/` subdirectory) produces zero loop iterations. No error, no side effect.

### `archive/` directory is never mistaken for a catalog

The `archive/` subdirectory name (`archive`) does NOT match the glob `mac-software-list-*.txt`.
Even without a `-d` guard, the glob simply never matches it. The additional `[[ -d "$file" ]] && continue` guard provides defense in depth. [VERIFIED: tested on this machine.]

---

## Standard Stack

No new packages or libraries. This phase is pure Zsh shell scripting using only:

| Tool | Use | Availability |
|------|-----|--------------|
| `date -v` (macOS BSD) | 30-day cutoff computation | Always present on macOS |
| `grep -oE` | 14-digit timestamp extraction from filenames | Always present (BSD grep) |
| `mv` | Move files to archive/ | Always present |
| `rm` | Hard-delete prune | Always present |
| `mkdir -p` | Create archive/ if absent | Always present |
| `git add -A` | Stage all working-tree changes | git already required by script |
| Zsh `typeset -A` | Associative array for per-host grouping | Built into Zsh |
| Zsh `:t` parameter expansion | Basename extraction (`${file:t}`) | Built into Zsh; used already |
| Zsh `#` / `%` parameter expansion | Hostname extraction from filename | Built into Zsh |

## Package Legitimacy Audit

Not applicable — this phase installs no packages.

---

## Architecture Patterns

### System Architecture Diagram

```
./update-list.sh --personal
        |
        v
   git_pull
        |
        v
   Set CURRENT_DATE / CURRENT_MACHINE / OUTPUT_FILE
        |
        v
   generate_catalog  ──writes──>  personal/mac-software-list-[host]-YYYYMMDDHHMMSS.txt
        |
        v
   retain_newest_per_host("personal")
     Pass 1: scan personal/mac-software-list-*.txt
             extract [hostname] + 14-digit ts per file
             build newest_ts[host] associative array
     Pass 2: for each file where ts < newest_ts[host]:
             mv file → personal/archive/
        |
        v
   prune_old_archives("personal")
     cutoff = date -v-30d "+%Y%m%d"
     for each personal/archive/mac-software-list-*.txt:
       extract ts (first 8 chars)
       if ts < cutoff → rm file
        |
        v
   git_commit_and_push  (skipped if --no-commit)
     git add -A "personal/"       ← stages: new catalog (A), moves (D+A), prune deletes (D)
     git commit
     git push
        |
        v
   Other machines: git pull → working tree converges
```

### Recommended Project Structure

No structural changes. All code remains in `update-list.sh`. The `archive_old_catalogs` function
block (~lines 175-247) is replaced in-place with two functions:
- `retain_newest_per_host` (replaces move-to-archive logic)
- `prune_old_archives` (new 30-day hard-delete logic)

### Pattern 1: Two-Pass Per-Host Retention (retain_newest_per_host)

**What:** Enumerate main-folder catalogs twice. Pass 1 builds a `newest_ts[hostname]` map. Pass 2
archives any file whose timestamp is not the maximum for its hostname.

**When to use:** Any time files must be grouped by an embedded key and all-but-max retained
differently.

**Why two passes instead of one:** A one-pass approach (track newest and archive previous) fails
if files are not processed in timestamp order. Zsh glob expansion does not guarantee sorted order.
Two passes are required for correctness.

```zsh
# Source: verified against real filenames on this machine (2026-06-13)
retain_newest_per_host() {
    local target_dir="$1"
    local full_path="${SCRIPT_DIR}/${target_dir}"
    local archive_path="${full_path}/archive"

    echo ""
    echo "Retaining newest catalog per machine in ${target_dir}/..."

    # Create archive directory if it doesn't exist
    if [[ ! -d "$archive_path" ]]; then
        mkdir -p "$archive_path"
        echo "  Created archive directory: ${archive_path}"
    fi

    # Pass 1: find the newest (max) timestamp per hostname
    typeset -A newest_ts
    for file in "${full_path}"/mac-software-list-*.txt; do
        [[ -e "$file" ]] || continue
        [[ -d "$file" ]] && continue
        local filename="${file:t}"
        local tmp="${filename#*\[}"
        local host="${tmp%\]-*}"
        local ts=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14)
        if [[ -z "$ts" || -z "$host" || "$host" == "$filename" ]]; then
            echo "  WARNING: Could not parse hostname/timestamp from: $filename"
            continue
        fi
        if [[ -z "${newest_ts[$host]}" || "$ts" > "${newest_ts[$host]}" ]]; then
            newest_ts[$host]="$ts"
        fi
    done

    # Pass 2: move any file that is NOT the newest for its host
    local moved_count=0
    for file in "${full_path}"/mac-software-list-*.txt; do
        [[ -e "$file" ]] || continue
        [[ -d "$file" ]] && continue
        local filename="${file:t}"
        local tmp="${filename#*\[}"
        local host="${tmp%\]-*}"
        local ts=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-14)
        if [[ -z "$ts" || -z "$host" || "$host" == "$filename" ]]; then
            continue    # already warned in pass 1
        fi
        # ts == newest_ts[host]: keep it (includes tied-newest case)
        if [[ "$ts" == "${newest_ts[$host]}" ]]; then
            continue
        fi
        mv "$file" "${archive_path}/"
        echo "  Archived: $filename"
        ((moved_count++))
    done

    if [[ $moved_count -eq 0 ]]; then
        echo "  No older catalogs to archive."
    else
        echo "  Archived $moved_count catalog(s) to ${target_dir}/archive/"
    fi
}
```

### Pattern 2: 30-Day Prune (prune_old_archives)

**What:** Iterate archive/ catalogs. Extract the 8-digit date from the filename timestamp. Delete
if older than `date -v-${ARCHIVE_AGE_DAYS}d`.

```zsh
# Source: based on existing archive_old_catalogs timestamp extraction pattern (line 224)
prune_old_archives() {
    local target_dir="$1"
    local full_path="${SCRIPT_DIR}/${target_dir}"
    local archive_path="${full_path}/archive"

    echo ""
    echo "Pruning archive catalogs older than ${ARCHIVE_AGE_DAYS} days..."

    # If archive doesn't exist, nothing to prune
    if [[ ! -d "$archive_path" ]]; then
        echo "  No archive directory found — nothing to prune."
        return
    fi

    local cutoff_date=$(date -v-${ARCHIVE_AGE_DAYS}d "+%Y%m%d")
    local pruned_count=0

    for file in "${archive_path}"/mac-software-list-*.txt; do
        [[ -e "$file" ]] || continue
        [[ -d "$file" ]] && continue
        local filename="${file:t}"
        local timestamp=$(echo "$filename" | grep -oE '[0-9]{14}\.txt$' | cut -c1-8)
        if [[ -z "$timestamp" ]]; then
            echo "  WARNING: Could not parse timestamp from: $filename — skipping"
            continue
        fi
        if [[ "$timestamp" -lt "$cutoff_date" ]]; then
            rm "$file"
            echo "  Pruned: $filename"
            ((pruned_count++))
        fi
    done

    if [[ $pruned_count -eq 0 ]]; then
        echo "  No archive catalogs needed pruning."
    else
        echo "  Pruned $pruned_count catalog(s) from ${target_dir}/archive/"
    fi
}
```

### Pattern 3: Updated `git_commit_and_push` Staging

Replace the two targeted `git add` calls (lines 1577-1581) with:

```zsh
# Stage all working-tree changes in the targeted location:
# - new catalog (A), moved-to-archive files (D from main + A in archive/), pruned files (D)
echo "  Staging all changes in ${TARGET_LOCATION}/..."
git add -A "${TARGET_LOCATION}/"
```

The updated commit message can remain the same. The `|| true` safety wrapper on the old
`git add "${TARGET_LOCATION}/archive/"` line is no longer needed.

### Anti-Patterns to Avoid

- **Single-pass per-host selection:** A one-pass approach that archives the "previous" file
  while finding the new max is broken when glob order is not sorted. Always use two passes.
- **Using file mtime instead of filename timestamp:** mtime can be updated by git operations,
  network sync, or file copies. The filename timestamp is the authoritative source per the
  locked decision.
- **`grep -rn` or find-based hostname extraction:** Parsing the filename with `grep -oE` and
  parameter expansion is simpler, faster, and dependency-free. No `find` or `awk` needed.
- **`git add .` instead of `git add -A`:** `git add .` in older git versions does not stage
  deletions. Always use `git add -A` to capture deletes.
- **Touching archive/ before retain_newest_per_host completes:** If prune runs before retention,
  files moved to archive/ in the same run could be immediately pruned if they happen to be old.
  The correct order is: retain first (populate archive/), then prune (clean archive/).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stage deletions in git | Custom `git rm` loop per deleted file | `git add -A <path>` | One call stages all adds, deletes, and renames under the path |
| 30-day date math | Custom date parsing/arithmetic | BSD `date -v-30d` | macOS built-in; already used in the script for the 60-day cutoff |
| Basename extraction | Custom `sed`/`awk` on path | Zsh `:t` parameter expansion | Already used in the existing `archive_old_catalogs` at line 219 |

---

## Runtime State Inventory

This is a rename/refactor of existing file-management logic, not a data migration.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | 72 files in `personal/archive/` (all older than 30 days per verification); 8 files in `personal/main/` | First run with new code: 7 of 8 main-folder files archived (6 older computer- files + computer-two.local is only one for its host so stays); 72 archive files pruned (all are >30d old per verification) |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | 20 pending-deleted files in git working tree (shown in `git status`) | Absorbed by the first `git add -A personal/` commit — no separate cleanup needed |

**Git working tree state note:** `git status` shows 20 files as ` D` (deleted on disk but not
staged). These are files that were physically deleted from `personal/` but the deletion was never
committed. The new `git add -A personal/` call in `git_commit_and_push` will stage these
deletions along with all other changes in the first run after this phase ships.

---

## Common Pitfalls

### Pitfall 1: Glob Order Not Sorted — One-Pass Max Fails
**What goes wrong:** A one-pass algorithm that archives the previous-newest when it finds a newer
file fails if files are enumerated in non-timestamp order (which Zsh does not guarantee).
**Why it happens:** Zsh glob expansion order is filesystem-order (typically inode order on HFS+),
not lexicographic.
**How to avoid:** Always use two passes: pass 1 to find max per host, pass 2 to archive non-max.
**Warning signs:** Intermittent incorrect archiving; tests pass on clean FS but fail on populated one.

### Pitfall 2: `local` Inside Pass 2 Loop Clobbers Pass 1 Variables
**What goes wrong:** Declaring `local tmp` and `local host` inside the Pass 2 loop with the same
names as in Pass 1 is fine in Zsh (each function invocation has its own scope), but declaring
them at function top and re-assigning per iteration avoids any confusion.
**How to avoid:** Declare `local` variables at function top or consistently within each loop body.
The code patterns above declare them inside the loop body, which is safe and clear.

### Pitfall 3: `archive/` Directory Matched by Glob
**What goes wrong:** If the archive glob becomes `*` or `*.txt` instead of
`mac-software-list-*.txt`, the `archive/` directory itself could be enumerated. Then `${file:t}`
returns `archive`, hostname extraction returns the full filename, timestamp is empty, the
`-z "$ts"` guard triggers, and the file is skipped — but a warning is printed falsely.
**How to avoid:** Always use the exact glob `mac-software-list-*.txt`. Add `[[ -d "$file" ]] && continue` as defense in depth.

### Pitfall 4: `prune_old_archives` Runs Before `retain_newest_per_host`
**What goes wrong:** If a catalog that was just moved to archive/ in the same run is also >30
days old, it would be immediately pruned. The just-moved file would be lost before the next run
can see it.
**How to avoid:** Always call `retain_newest_per_host` before `prune_old_archives`. In the
corrected main block, this order is enforced.
**Note:** In practice this can only happen if the CURRENT host has not run the script in 31+
days. Even then, the just-generated file (with today's timestamp) would not be moved to archive/
— only the previous oldest files for this host would be moved. Those old files being pruned
immediately is actually correct behavior (they are older than 30 days). So the risk is minimal
in practice, but the order is still required by the spec.

### Pitfall 5: `typeset -A` Declared with `local` in Zsh
**What goes wrong:** In Zsh, `typeset -A` and `local` are both valid ways to declare function-
local variables. Using `typeset -A newest_ts` without `local` creates a function-local associative
array (Zsh functions create a new scope). However, if the function is called from a subshell
context, the typeset scope could differ.
**How to avoid:** Use `local -A newest_ts` (equivalent to `typeset -A newest_ts`) for explicitness.
Either form is correct in a standard Zsh function context.

### Pitfall 6: The 19 Pending Deletions in Working Tree
**What goes wrong:** The 20 files currently in ` D` state (deleted on disk, not staged) in the
working tree could create confusion if manually resolved before this phase ships, or if another
commit is made that uses the old `git add` pattern (which would NOT stage these deletions).
**How to avoid:** The first run after this phase ships will call `git add -A personal/` which
absorbs all pending deletions. No manual intervention needed. Do NOT commit with the old pattern
in the meantime.

---

## Code Examples

### Hostname extraction verified against real filenames

```zsh
# Source: verified on this machine 2026-06-13
filename="mac-software-list-[computer-one.local]-20260609144429.txt"
tmp="${filename#*\[}"       # → "computer-one.local]-20260609144429.txt"
host="${tmp%\]-*}"          # → "computer-one.local"

filename2="mac-software-list-[computer-two.local]-20260607205427.txt"
tmp2="${filename2#*\[}"     # → "computer-two.local]-20260607205427.txt"
host2="${tmp2%\]-*}"        # → "computer-two.local"
```

### 30-day cutoff verified on this machine

```zsh
# Source: verified via date -v-30d "+%Y%m%d" on this machine 2026-06-13
# Today: 20260613 → cutoff: 20260514
local cutoff_date=$(date -v-${ARCHIVE_AGE_DAYS}d "+%Y%m%d")

# Comparison (existing pattern from archive_old_catalogs line 234):
if [[ "$timestamp" -lt "$cutoff_date" ]]; then
    rm "$file"
fi
```

### git add -A scoping verified

```zsh
# Source: verified by running on this repo 2026-06-13
# Staged 20 pending D deletions with one command:
git add -A "${TARGET_LOCATION}/"
# Equivalent without trailing slash:
git add -A "${TARGET_LOCATION}"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Archive files older than 60 days (age-based) | Keep newest per host + hard-delete archive after 30 days | Phase 6 | Main folder stays lean regardless of run frequency; 30-day archive self-prunes |
| `git add <specific file>` + `git add archive/` | `git add -A <location>/` | Phase 6 | Deletions and renames now propagate via git; other machines converge |
| `archive_old_catalogs` (single function) | `retain_newest_per_host` + `prune_old_archives` (two functions) | Phase 6 | Clearer separation of concerns; each function is independently testable |

**Deprecated/outdated:**
- `ARCHIVE_AGE_DAYS=60`: changes to 30; semantics change from "move age threshold" to "archive delete threshold"
- `archive_old_catalogs`: replaced entirely; do not call from main block

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Tied 14-digit timestamps are impossible in normal operation (seconds-precision clock makes two runs in the same second pathological) | Q2 | If somehow two files have the same timestamp for the same host, both are kept (correct by spec — data-loss-averse) |
| A2 | `git pull` on another machine removes pruned files from its working tree after fetch+merge | Q3 | If git doesn't propagate deletes (e.g., merge conflict), other machine retains old files — but this is standard git behavior |
| A3 | Second consecutive run's idempotence (Pass 2 no-ops when only newest-per-host is in main/) | Q5 | If clock skew or filesystem quirk causes the new file not to be the latest, it could be archived — but the 14-digit timestamp includes seconds, making this an extreme edge case |

---

## Open Questions (RESOLVED)

1. **`display_usage` text update**
   - What we know: `display_usage` at line 82 says "Catalogs older than ${ARCHIVE_AGE_DAYS} days are automatically moved to the archive/ subfolder" — this description becomes inaccurate when semantics change.
   - What's unclear: Whether the planner should include a display_usage text update as an explicit task.
   - Recommendation: Include it as a small sub-task in Wave 1; update the text to reflect the new behavior ("newest catalog per machine is kept; older catalogs are archived and pruned after 30 days").

2. **`prune_old_archives` behavior when archive/ was just populated this run**
   - What we know: Files moved to archive/ by `retain_newest_per_host` in the same run will have today's timestamp — they will NOT be pruned by `prune_old_archives` since today's date is newer than the 30-day cutoff. This is correct behavior.
   - What's unclear: The spec doesn't explicitly address this case.
   - Recommendation: No action needed — the timestamp-based comparison handles it correctly.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `date -v` (BSD date) | 30-day cutoff | ✓ | macOS built-in | None — macOS-only by design |
| `grep -oE` | Timestamp extraction | ✓ | BSD grep (macOS built-in) | None needed |
| `git add -A` | SYNC-01 staging | ✓ | git 2.50.1 | None — git already required |
| Zsh `typeset -A` | Per-host grouping | ✓ | Built into Zsh (script is Zsh-only) | None needed |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

---

## Validation Architecture

nyquist_validation is explicitly set to `false` in `.planning/config.json` — this section is skipped.

---

## Security Domain

No security-sensitive changes. This phase:
- Operates only on files within the repo's `personal/` or `office/` subdirectories
- Reads only filenames (not file contents) during retention/prune operations
- Does not introduce network calls, user input processing, or authentication
- `git add -A` is scoped to the targeted location — no broader working-tree exposure

---

## Sources

### Primary (HIGH confidence)
- `update-list.sh` lines 191-247 (`archive_old_catalogs`) — existing timestamp extraction and cutoff patterns [VERIFIED: read directly from source]
- `update-list.sh` lines 1614-1673 (main block) — exact current call order [VERIFIED: read directly from source]
- `personal/` and `personal/archive/` directory listings — real filenames on this machine [VERIFIED: `ls` on 2026-06-13]
- `date -v-30d "+%Y%m%d"` output: `20260514` [VERIFIED: executed on this machine]
- `grep -oE '[0-9]{14}\.txt$' | cut -c1-8` on real filenames [VERIFIED: executed on this machine]
- `git add -A personal/` staging behavior [VERIFIED: executed on this repo, staged 20 pending deletions]
- Zsh associative array two-pass logic [VERIFIED: executed via `zsh -c` against real files in `personal/`]

### Secondary (MEDIUM confidence)
- Zsh `typeset -A` / `local -A` scoping behavior [ASSUMED: based on Zsh documentation knowledge; no version-specific test run]
- `git pull` deletion propagation to other machines [ASSUMED: standard git working-tree sync semantics]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pure Zsh + existing tools, verified on this machine
- Architecture: HIGH — derived directly from reading the actual source code + live file listing
- Pitfalls: HIGH — grounded in code analysis and live tests; tied-timestamp case is theoretical
- Call order: HIGH — confirmed by reading lines 1629-1660 directly

**Research date:** 2026-06-13
**Valid until:** Stable (Zsh + macOS BSD date are stable APIs); no external dependencies to rot

---

## RESEARCH COMPLETE

**Phase:** 6 - Retention & Sync
**Confidence:** HIGH

### Key Findings

1. **The existing timestamp extraction pattern works unchanged.** `grep -oE '[0-9]{14}\.txt$' | cut -c1-8` correctly extracts the date portion from real filenames including both `computer-one.local` and `computer-two.local` hostnames. BSD `date -v-30d` cutoff is verified working on this machine.

2. **Two-pass Zsh associative array is the correct approach for per-host grouping.** Pass 1 finds max timestamp per hostname; Pass 2 archives non-max. Hostname extraction via `${filename#*\[}` + `${tmp%\]-*}` handles dots and hyphens correctly. Verified against 8 real files in `personal/`.

3. **`git add -A "${TARGET_LOCATION}/"` is verified to stage deletions.** Running it against this repo staged all 20 pending `D` (deleted on disk, unstaged) files. This replaces the current two-call pattern and handles moves and new files in one command.

4. **The main-block call order MUST change.** Currently `archive_old_catalogs` runs before `CURRENT_DATE`/`generate_catalog` (lines 1632 vs 1636-1647). The new order: `git_pull` → set `CURRENT_DATE`/`CURRENT_MACHINE`/`OUTPUT_FILE` → `generate_catalog` → `retain_newest_per_host` → `prune_old_archives` → `git_commit_and_push`.

5. **72 archive files on this machine are all older than 30 days** — all will be pruned on the first run. The 20 pending git deletions are absorbed by `git add -A` with no separate cleanup commit needed.

### File Created
`.planning/phases/06-retention-sync/06-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Pure Zsh + existing tools only; all verified on this machine |
| Architecture | HIGH | Read actual source code + verified live against real files |
| Pitfalls | HIGH | Grounded in code analysis and live execution tests |
| Call order | HIGH | Confirmed from direct source read of lines 1629-1660 |

### Open Questions

- `display_usage` text should be updated to reflect the new semantics (minor, but worth noting)
- Behavior when `prune_old_archives` sees a file just moved in the same run is correct by analysis (new file has today's timestamp, not pruned)

### Ready for Planning
Research complete. Planner can now create PLAN.md.
