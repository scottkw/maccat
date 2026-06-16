---
phase: 18-public-repo-migration-genericized-fresh-history
plan: "01"
subsystem: staging-tree-preparation
tags: [migration, genericization, privacy, staging]
dependency_graph:
  requires: []
  provides: [staging-tree-ready-for-git-init]
  affects: [plan-18-02]
tech_stack:
  added: []
  patterns: [git-archive-export, perl-literal-replacement, deterministic-scrub]
key_files:
  created:
    - /tmp/maccat-staging.AxZxJN/LICENSE
    - /tmp/maccat-staging.AxZxJN/.gitignore
    - /tmp/maccat-staging.AxZxJN/config.example.toml
    - /tmp/maccat-staging.AxZxJN/README.md  # rewritten
  modified:
    - /tmp/maccat-staging.AxZxJN/.planning/  # ~37 files scrubbed
    - /tmp/maccat-staging.AxZxJN/docs/superpowers/specs/2026-06-14-computer-folder-model-design.md
    - /tmp/maccat-staging.AxZxJN/CLAUDE.md
decisions:
  - "Staging dir: /tmp/maccat-staging.AxZxJN (Plan 02 must use this exact path)"
  - "Personal-token replacements: computer-one* -> computer-one*, computer-one*/computer-two.local -> computer-two*, Ken's/Example Computer/Example Computer -> Example Computer"
  - "tests/golden fixtures excluded from scrub (synthetic placeholders, confirmed clean)"
  - "PLAN.md grep pattern fragments neutralized to prevent false-positive token leakage"
metrics:
  duration: 7 min
  completed: "2026-06-16"
  tasks_completed: 4
  files_count: 40+
---

# Phase 18 Plan 01: Genericized Staging Tree — Summary

**One-liner:** Built a clean `/tmp/maccat-staging.AxZxJN` tree via `git archive` export with full personal-identifier scrub (9 token types, ~37 files), new MIT LICENSE, genericized .gitignore + config.example.toml, and rewritten install-from-Releases README — zero personal data, ready for `git init` in Plan 02.

## What Was Built

A genericized maccat staging tree at `/tmp/maccat-staging.AxZxJN` containing:

- Full include-list: `src/maccat/`, `tests/`, `pyproject.toml`, `scripts/`, `docs/`, `update-list.sh`, `.planning/`, `CLAUDE.md`, `.github/`, `.gitignore`, `.python-version`
- New `LICENSE` (MIT, Copyright (c) 2026 Ken Scott)
- Rewritten `.gitignore` (artifacts + personal catalog data patterns + test fixture negation exceptions preserved)
- New `config.example.toml` (catalog_dir key, neutral placeholder, precedence docs)
- Rewritten `README.md` (install-from-Releases, config precedence, neutral placeholders)
- All text files scrubbed of real personal hostnames/machine labels

Zero excluded items: no `dist/`, `venv/`, `personal/`, `office/`, `machine-labels.tsv`, stray test scripts, `*.pyz`, or personal catalog `.txt` files.

## Task Results

| Task | Name | Commit | Result |
|------|------|--------|--------|
| 1 | Export include-list to staging tree | cf34468 | PASS |
| 2 | Add LICENSE, .gitignore, config.example.toml | 46e69b9 | PASS |
| 3 | Rewrite README (genericized, install-from-Releases) | 71f1f80 | PASS |
| 4 | Scrub personal identifiers from entire staging tree | 014eac1 | PASS |

## Staging Tree Path for Plan 02

```
STAGING=/tmp/maccat-staging.AxZxJN
```

Plan 02 must use this path for `git init` and the privacy gate re-scan. If the temp dir is lost between sessions (system reboot), re-run Plan 01.

## Personal-Identifier Scrub Details

**Enumerated token list (Task 4 STEP A output):**

| Token | Replacement | Files |
|-------|-------------|-------|
| `computer-one.local` | `computer-one.local` | 19 |
| `computer-one` | `computer-one` | 2 |
| `computer-one.local` | `computer-two.local` | 4 |
| `computer-one` | `computer-two` | 4 |
| `computer-two.local` | `computer-two.local` | 16 |
| `Example Computer` | `Example Computer` | 17 |
| `Example Computer` | `Example Computer` | 3 |
| `Example Computer` | `Example Computer` | 3 |
| grep pattern fragments in `18-01-PLAN.md` | neutralized | 1 |

**Files affected:** ~37 across `.planning/` (milestones + phases), `docs/superpowers/specs/`, `CLAUDE.md`, README, and the plan file itself.

**Post-scrub verification:**
```
grep -rlE 'computer-one|computer-one|local|Example Computer' \
  $STAGING --exclude-dir=.git --exclude-dir=golden | grep -v '/tests/golden/'
```
Result: **0 files** — PASS.

**tests/golden fixtures:** Untouched and confirmed clean (no real hostnames — synthetic placeholders only).

**Format string preserved:** `mac-software-list-[` legitimately appears in code/tests/docs and was NOT scrubbed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PLAN.md contained grep-pattern fragments referencing personal tokens**
- **Found during:** Task 4 STEP C self-verify
- **Issue:** `18-01-PLAN.md` in the staging copy contained `local` and `Example Computer` as grep regex pattern literals in its automated verify and acceptance criteria sections. These were originally personal hostnames listed as regex patterns for detection — but since the PLAN.md is in the staging tree (which becomes the public repo), these pattern strings would register as personal token hits in the post-scrub grep.
- **Fix:** Neutralized the pattern strings in `18-01-PLAN.md` inside the staging copy: `local` → `computer-two.local`, `Example Computer` patterns → `Example Computer` equivalents; replaced the `key_links.pattern` frontmatter field with neutral values.
- **Files modified:** `/tmp/maccat-staging.AxZxJN/.planning/phases/18-public-repo-migration-genericized-fresh-history/18-01-PLAN.md`
- **Note:** The SOURCE REPO's `18-01-PLAN.md` was NOT modified — only the staging copy.

## Threat Mitigations Applied

| Threat ID | Status |
|-----------|--------|
| T-18-01 Personal catalog .txt files | MITIGATED — git archive + explicit rm + find sweep (0 found) |
| T-18-02 machine-labels.tsv | MITIGATED — explicit rm + added to .gitignore |
| T-18-03 Personal hostnames in README/config | MITIGATED — README rewritten, config uses neutral placeholder |
| T-18-04 dist/maccat.pyz build artifact | MITIGATED — find -name '*.pyz' delete + *.pyz in .gitignore |
| T-18-08 Personal hostnames in .planning/docs/CLAUDE.md | MITIGATED — Task 4 tree-wide scrub, 0 remaining files |

## Self-Check: PASSED

**Staging dir exists:**
- `/tmp/maccat-staging.AxZxJN` — FOUND

**Key files exist in staging:**
- `src/maccat/` — FOUND
- `tests/` — FOUND
- `LICENSE` — FOUND
- `.gitignore` — FOUND
- `config.example.toml` — FOUND
- `README.md` — FOUND

**Commits exist:**
- cf34468 — FOUND (task 1)
- 46e69b9 — FOUND (task 2)
- 71f1f80 — FOUND (task 3)
- 014eac1 — FOUND (task 4)

**Zero personal identifiers in staging tree (excluding tests/golden):** CONFIRMED
