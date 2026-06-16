---
phase: 20
phase_name: Cut-Over & External-Catalog Verification
status: passed
verified: 2026-06-16
must_haves_verified: 2
must_haves_total: 2
verified_by: orchestrator (direct assertions)
---

# Phase 20 Verification — Cut-Over & External-Catalog Verification

**Status: PASSED** (2/2 must-haves)

## MIG-05 — maccat verified against an external catalog repo
Plan 20-01 built the `.pyz` and ran maccat with `--catalog-dir <mktemp> --computer test --no-commit`,
producing a complete 775-line catalog (header + Homebrew + 18 section separators). Real `personal/`
and `office/` confirmed byte-unchanged; temp dirs cleaned up. Corroborated by the earlier manual UAT
(same flow) which proved the `--catalog-dir` path end-to-end. Evidence: 20-01-SUMMARY.md.

## MIG-04 — this repo reduced to catalog-data-only
Direct post-strip assertions (orchestrator, 2026-06-16):

| Check | Result |
|-------|--------|
| `src/ tests/ scripts/ docs/ .github/` removed | gone ✓ |
| `update-list.sh pyproject.toml CLAUDE.md .python-version` removed | gone ✓ |
| 3 root `test-*.sh` scripts removed | gone ✓ |
| `personal/` (8 + 72 archived), `office/` (11 + 33 archived) kept | intact ✓ |
| `machine-labels.tsv`, `.gitignore`, `.git` kept | intact ✓ |
| `README.md` rewritten → points to github.com/scottkw/maccat | ✓ |
| `origin` still `a private git host/...` (private) | ✓ |
| Strip committed (`3e2c2ef`) + pushed to a private Git host; HEAD == upstream | ✓ |
| Strip commit excluded pre-existing `personal/*.txt` churn | ✓ |

## Note
`.planning/` is intentionally retained at verification time; it is removed by the orchestrator as the
FINAL cut-over act, after the milestone lifecycle (audit → complete → cleanup) and the final
`.planning/` push to the maccat repo. Its removal is recorded by the a private Git host commit, not in `.planning`.
