# Phase 6: Retention & Sync - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase reworks `update-list.sh`'s archive/retention/git logic so every run leaves the
**targeted** location's main folder (`personal/` or `office/`) holding only the **newest
catalog per machine (hostname)**, moves all older per-machine catalogs into that location's
`archive/`, **hard-deletes** archive catalogs older than 30 days, and stages every resulting
change (additions, moves, deletions) in a single git commit/push so machines converge. Covers
RET-01..04 and SYNC-01..02. It does NOT add new catalog sources or features — it changes how
catalog files are retained and synced. The catalog-generation logic (Phases 1–5) is untouched.
</domain>

<decisions>
## Implementation Decisions

### Operation Mechanics & Order (USER LOCKED)
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

### Edge Cases & Safety (USER LOCKED)
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

### Retention Window
- `ARCHIVE_AGE_DAYS` changes from 60 → 30. Its SEMANTICS change: previously it meant "move
  catalogs older than 60 days from main → archive"; now the main folder keeps newest-per-machine
  (regardless of age) and `ARCHIVE_AGE_DAYS` governs the HARD-DELETE prune of the archive folder.
</decisions>

<code_context>
## Existing Code Insights
- `archive_old_catalogs` (update-list.sh ~line 187–253): currently uses
  `date -v-${ARCHIVE_AGE_DAYS}d "+%Y%m%d"` to compute a cutoff and `mv`s catalogs older than the
  cutoff from main → archive, parsing the timestamp out of the filename. This function is the
  primary thing being reworked: it splits into (a) a retention sweep that keeps newest-per-host
  in main and archives the rest, and (b) a 30-day hard-delete prune of the archive folder.
- `ARCHIVE_AGE_DAYS=60` constant (~line 45) → change to 30.
- `git_commit_and_push` (~line 1559+): currently `git add`s the new catalog + archived files.
  Must change to stage ALL working-tree changes in the targeted location (`git add -A`) so
  moves and deletions propagate; skipped entirely when `AUTO_COMMIT=false`.
- Main block orchestration (~line 1600+): sets `CURRENT_DATE`, `CURRENT_MACHINE` (hostname),
  `OUTPUT_FILENAME`, `OUTPUT_FILE`, `TARGET_LOCATION`; calls git_pull, archive, generate, commit.
  The call order may need adjustment so retention runs AFTER generate.
- Filename parsing precedent: the existing archive function already extracts the timestamp from
  the filename with `grep`/parameter expansion — reuse that pattern; the hostname is the
  bracketed segment.
- Conventions: `local` vars, `[[ ]]`, double-quoted paths, `return` not `exit` on non-fatal,
  null-glob guards in file loops, macOS BSD `date -v`.

## Integration Points
- Touches `archive_old_catalogs` (rework), `ARCHIVE_AGE_DAYS` (constant), `git_commit_and_push`
  (staging), and the main-block call order. The catalog generation + all 13 collectors are
  unchanged.
</code_context>

<specifics>
## Specific Ideas (verification grounding — THIS machine)
- The repo is used on two machines: `[computer-one.local]` and `[computer-two.local]`.
  Per-machine retention means after a `--personal` run, `personal/` should hold the newest
  catalog for EACH of those hostnames (plus the just-generated one), with all older ones in
  `personal/archive/`.
- Determinism/idempotence: running twice in a row should be stable — the second run finds only
  the newest-per-host already in main and nothing new to archive (beyond its own freshly
  generated file superseding the previous newest for THIS host).
- The 30-day prune must be testable with synthetic archive files dated >30 and <30 days ago.
</specifics>

<deferred>
## Deferred Ideas
- Configurable retention window / "keep N per machine" — out of scope (fixed at newest-1 + 30d).
- Rewriting git history to purge already-committed old catalogs — out of scope (prune applies
  going forward).
- Pruning both locations on a single run — out of scope (target-location-only).
</deferred>

<research_flags>
## Open Questions for Research
1. **macOS BSD date arithmetic for the 30-day cutoff** — confirm the exact `date -v-30d` cutoff
   computation and the safe filename-timestamp comparison (the existing function's pattern), and
   that an unparseable filename timestamp is skipped (warn-and-continue), never deleted.
2. **Per-host grouping in Zsh** — the cleanest dependency-free way to enumerate main-folder
   catalogs, extract `[hostname]` + timestamp, group by hostname, and select the max-timestamp
   file per host (associative array vs sort-based). Null-glob guarded.
3. **`git add -A` scoping + deletion propagation** — confirm that staging the targeted location
   dir captures moves (as delete+add or rename) and the prune deletions, and that a pull on
   another machine then removes the pruned files locally. Confirm `--no-commit` path leaves the
   disk changes in place without staging.
4. **Call-order correctness** — verify generating the new catalog BEFORE the retention sweep, and
   that the existing archive/git function signatures and the main-block sequence are adjusted
   without breaking the catalog generation or the existing flags.
5. **Idempotence + safety** — confirm a second consecutive run is stable and that no run can
   delete the only/newest catalog for a host or a file that doesn't match the catalog pattern.
</research_flags>
