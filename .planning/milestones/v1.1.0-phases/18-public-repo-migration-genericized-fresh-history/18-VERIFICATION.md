---
phase: 18-public-repo-migration-genericized-fresh-history
verified: 2026-06-15T00:00:00Z
status: passed
score: 8/8 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: none
  previous_score: n/a
---

# Phase 18: Public Repo Migration (Genericized, Fresh History) Verification Report

**Phase Goal:** A new public GitHub repo exists holding the genericized maccat code, tests, build tooling, docs, the zsh reference, and `.planning/` history — started from a fresh git history that exposes zero personal catalog data anywhere in the tree or the log.
**Verified:** 2026-06-15
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

This is an infrastructure/migration phase. Deliverables live outside this repo's working tree:
- Public GitHub repo `github.com/scottkw/maccat`
- Staging tree `/tmp/maccat-staging.AxZxJN` (the single-commit source that was pushed)

**Critical evidence anchor:** The published GitHub `main` HEAD SHA (`100e70d1d9c4f90a3e64da469b27ab3bf9e033be`) is byte-identical to the staging tree HEAD. Because the published commit == the staging commit, all staging-tree scans below are authoritative for the actual published content — not a proxy.

### Observable Truths

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 (MIG-01) | A new public GitHub repo created via `gh` exists | ✓ VERIFIED | `gh repo view scottkw/maccat --json visibility -q .visibility` → `PUBLIC`; default branch `main`; `gh auth status` account `scottkw` |
| 2 (MIG-02) | Repo contains src/maccat, tests, pyproject.toml, scripts/build-pyz.sh, docs, update-list.sh, .planning/ | ✓ VERIFIED | `git -C $S ls-files` shows all present (src/maccat, tests/, pyproject.toml, scripts/build-pyz.sh, docs/, update-list.sh, .planning); 313 tracked files |
| 3 (MIG-03) | Fresh single-commit history; zero personal identifiers in tree AND full log | ✓ VERIFIED | `rev-list --count HEAD` = 1; working-tree personal-token scan = 0; `git log --all -p \| grep -E '...'` = 0; private-remote/private refs tree = 0, log = 0; stray catalog `.txt` outside tests/ = 0 |
| 4 (GEN-01) | README is a generic install-from-Releases tool, no personal paths/values | ✓ VERIFIED | README contains "Releases", "MACCAT_CATALOG_DIR", config refs; `.pyz` mentioned 16×; `update-list.sh --personal` as install path = 0; personal-identifier count = 0; no canonical `personal/`/`office/` usage |
| 5 (GEN-02) | config.example.toml present, template config, no personal values | ✓ VERIFIED | `config.example.toml` tracked; contains `catalog_dir`; non-comment personal-value count = 0 |
| 6 (GEN-03) | Excluded items absent from tree | ✓ VERIFIED | `ls-files \| grep -E 'maccat\.pyz$\|^venv/\|^dist/\|^personal/\|^office/\|machine-labels\.tsv\|test-parse-arguments-11-02\|test-rename'` = 0 matches |
| 7 (GEN-04) | LICENSE present (MIT) | ✓ VERIFIED | `LICENSE` tracked; contains "MIT License"; `gh api repos/scottkw/maccat/license -q .license.spdx_id` → `MIT` |
| 8 (SAFETY) | This repo's origin still private remote; no github.com/scottkw/maccat remote here | ✓ VERIFIED | `git -C /Users/ken/dev/mac-software-list remote get-url origin` → `a private catalog remote`; grep for github.com/scottkw/maccat in this repo's remotes = none |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `github.com/scottkw/maccat` | Public repo, branch main | ✓ VERIFIED | visibility PUBLIC, default branch main, 1 commit (`gh api commits?per_page=100 \| length` = 1) |
| `$S/.git` (staging) | Fresh single-commit history | ✓ VERIFIED | rev-list count = 1, branch main, origin = github.com/scottkw/maccat |
| `$S/LICENSE` | MIT license text | ✓ VERIFIED | "MIT License" present |
| `$S/.gitignore` | Artifact + personal-data ignore rules | ✓ VERIFIED | venv/, dist/, personal/, office/, machine-labels.tsv, mac-software-list-, *.pyz all present |
| `$S/config.example.toml` | Template config | ✓ VERIFIED | catalog_dir key present, no personal values |
| `$S/README.md` | Install-from-Releases README | ✓ VERIFIED | Releases + MACCAT_CATALOG_DIR + .pyz install, zero personal identifiers |
| `$S/src/maccat` | Migrated package | ✓ VERIFIED | tracked in staging + published |
| tests/golden fixtures | Parity fixtures preserved | ✓ VERIFIED | 38 tracked files under tests/golden/ (synthetic placeholders, intentionally retained) |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| staging initial commit | github.com/scottkw/maccat main | git push to gh-created public repo | ✓ WIRED | staging HEAD SHA == github main SHA (`100e70d...`), single commit |
| README.md | config.example.toml | documented precedence (--catalog-dir > MACCAT_CATALOG_DIR > ~/.config/maccat/config.toml) | ✓ WIRED | MACCAT_CATALOG_DIR + config refs present in README |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Public repo reachable + public | `gh repo view scottkw/maccat --json visibility` | PUBLIC | ✓ PASS |
| Published == staging | compare HEAD SHAs | identical (100e70d...) | ✓ PASS |
| Published commit count | `gh api commits?per_page=100 \| length` | 1 | ✓ PASS |
| Published README clean | fetch + base64 decode + grep | 0 personal identifiers | ✓ PASS |
| This repo origin unchanged | `git remote get-url origin` | a private Git host host | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| MIG-01 | 18-02 | Public GitHub repo via gh | ✓ SATISFIED | visibility PUBLIC, owner scottkw |
| MIG-02 | 18-01 | Repo holds code/tests/tooling/docs/zsh/.planning | ✓ SATISFIED | all paths tracked, 313 files |
| MIG-03 | 18-02 | Fresh history, zero personal data tree + log | ✓ SATISFIED | 1 commit; tree/log scans 0/0; private-remote refs 0/0; stray catalogs 0 |
| GEN-01 | 18-01 | Generic install-from-Releases README | ✓ SATISFIED | Releases/.pyz/config precedence, 0 personal identifiers |
| GEN-02 | 18-01 | Example/template config | ✓ SATISFIED | config.example.toml with catalog_dir, neutral placeholder |
| GEN-03 | 18-01 | No setup-specific content / artifacts / stray scripts | ✓ SATISFIED | exclusion grep = 0 matches |
| GEN-04 | 18-01 | Open-source LICENSE | ✓ SATISFIED | MIT LICENSE present (SPDX MIT) |

No orphaned requirements — all 7 declared phase requirements verified.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| (none) | — | TBD/FIXME/XXX scan of new staging files (LICENSE, config.example.toml, README, .gitignore) | — | Zero debt markers found |

No blocker anti-patterns. tests/golden fixtures intentionally retain synthetic placeholders (correctly excluded from the personal-identifier scan per plan design — confirmed clean of real hostnames).

### Human Verification Required

None — every success criterion is scriptable and was verified via `git -C $S`, `gh repo view`, and `gh api`. The human privacy-gate checkpoint (Plan 02 Task 3) was an execution-time control already approved before the irreversible push; this verifier independently re-ran all three privacy-gate surfaces and confirmed 0/0/0.

### Gaps Summary

No gaps. All 8 must-haves verified against actual deliverables. The published GitHub repo's `main` HEAD is byte-identical to the verified staging tree, the fresh history is a single commit, all privacy surfaces (working tree, full `git log --all -p`, stray catalog files, private git-host references) scan clean, the genericized artifacts (README, MIT LICENSE, config.example.toml, .gitignore) are present and correct, and this repo's private remote origin is untouched with no GitHub remote leakage.

---

_Verified: 2026-06-15_
_Verifier: Claude (gsd-verifier)_
