# Phase 20: Cut-Over & External-Catalog Verification - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Final cut-over of milestone v1.1.0: verify `maccat` runs correctly against an external catalog repo
(MIG-05), then reduce THIS repo to catalog-data-only (MIG-04). This is the irreversible step that
separates the now-public code (already on github.com/scottkw/maccat) from the private catalog data
that stays here on a private remote.

Because `.planning/` (the GSD home) moves to the maccat repo as part of this, the milestone
lifecycle (audit → complete → cleanup) and the final `.planning/` push run BEFORE the destructive
strip — not after.

</domain>

<decisions>
## Implementation Decisions

### Cut-over sequence (locked — user-approved)
1. **MIG-05** — verify maccat against an EXTERNAL catalog repo in a disposable `mktemp -d` git dir (never the real `personal/`/`office/`). Largely proven by manual UAT already (a `--catalog-dir <tmp> --computer test --no-commit` run produced a complete 13-section catalog).
2. Run milestone **audit → complete-milestone → cleanup** HERE, while `.planning/` still exists.
3. Push the **final `.planning/`** (all phase 18/19/20 artifacts + archived milestone) to the maccat repo — its authoritative GSD home going forward. Use a fresh `git clone` of maccat (the /tmp staging tree was removed).
4. **Cut the real `v1.1.0` release** — push a `v1.1.0` tag to maccat, triggering `release.yml` to publish the first real GitHub Release with `maccat.pyz` attached.
5. **Human-verify checkpoint** — show exactly what will be kept vs removed in this repo before the strip.
6. **MIG-04 strip** — reduce this repo to catalog-data-only, commit + push to the private remote. This is the last, irreversible action.

### This repo after the strip (locked)
- **KEEP:** catalog folders (`personal/`, `office/`, any computer folders), `machine-labels.tsv`, each folder's `archive/`, `.git`.
- **REMOVE:** `src/`, `tests/`, `scripts/`, `docs/`, `pyproject.toml`, `update-list.sh`, `.github/`, `.python-version`, `config.example.toml`, `CLAUDE.md`, `venv/` (if present), and `.planning/` (only AFTER lifecycle + push to maccat).
- **README:** replace the current code README with a short pointer — "This repo holds my machine software catalogs (data). The maccat tool lives at https://github.com/scottkw/maccat."

### GSD home
- After cut-over, all future GSD/feature work happens in the **maccat** repo. This repo is data-only and no longer carries `.planning/`.

</decisions>

<code_context>
## Existing Code Insights

### What exists
- Public repo `github.com/scottkw/maccat` — code + CI (`ci.yml` builds+tests+uploads `maccat.pyz`; `release.yml` tag-triggered release) all green.
- This repo (`/Users/ken/dev/mac-software-list`, origin = private a private Git host) still has the full code + `.planning/` (unchanged by phases 18/19).
- maccat config precedence: `--catalog-dir` > `MACCAT_CATALOG_DIR` > `~/.config/maccat/config.toml`. Verified working against an external dir.

### Safety
- **maccat / update-list.sh are destructive against a real catalog dir** (retention moves/prunes catalogs, git commit/push). MIG-05 verification MUST use a disposable `mktemp -d` git-init'd dir with `--no-commit` (or no remote), NEVER the real `personal/`/`office/` trees.
- The strip (MIG-04) uses `git rm` + commit; recoverable from this repo's git history but treated as irreversible. Gate behind a human checkpoint.

### Integration
- This repo's origin must stay the private remote; the strip commit pushes there. The maccat (GitHub) repo is touched only for the `.planning/` push and the `v1.1.0` tag — via a fresh clone, not this repo.

</code_context>

<specifics>
## Specific Ideas

- 20-02 (the strip) must include a blocking human-verify checkpoint immediately before the destructive `git rm`, surfacing the exact keep/remove file list and confirming the lifecycle + `.planning` push + `v1.1.0` release already happened.
- The `v1.1.0` release is the capstone — verify the published Release has `maccat.pyz` attached (this time it stays, unlike the throwaway test tag).

</specifics>

<deferred>
## Deferred Ideas

- PKG-04 (PyPI/pipx) — future milestone, in the maccat repo.
- Restore/reinstall from a catalog, catalog diffing, additional browsers/editors — future milestones (maccat repo).

</deferred>
