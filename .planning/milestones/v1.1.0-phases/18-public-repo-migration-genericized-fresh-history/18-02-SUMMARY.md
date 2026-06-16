---
phase: 18-public-repo-migration-genericized-fresh-history
plan: "02"
subsystem: public-repo-publication
tags: [migration, privacy-gate, fresh-history, github, public-repo]
dependency_graph:
  requires: [staging-tree-ready-for-git-init]
  provides: [public-repo-scottkw-maccat, fresh-history-published]
  affects: [plan-19-01]
tech_stack:
  added: []
  patterns: [git-init-fresh-history, three-surface-privacy-gate, gh-repo-create-source-push]
key_files:
  created:
    - /tmp/maccat-staging.AxZxJN/.git  # fresh git repo (single-commit main)
    - github.com/scottkw/maccat  # public GitHub repo
  modified: []
decisions:
  - "Public repo locked identity: owner=scottkw, name=maccat, visibility=PUBLIC, default branch=main"
  - "Fresh history approach confirmed: single git init commit, no filter-branch; MIG-03 satisfied"
  - "Privacy gate: three-surface scan (working-tree grep, git log --all -p, stray-catalog find), all 0 before push"
  - "Orchestrator scrubbed 3 a private git host references from .planning/ docs in staging tree and git commit --amended the initial commit before this plan's execution began"
metrics:
  duration: 5 min
  completed: "2026-06-16"
  tasks_completed: 4
  files_count: 313
---

# Phase 18 Plan 02: Public Repo Creation (Fresh History) — Summary

**One-liner:** Fresh `git init -b main` on the genericized staging tree, three-surface privacy gate confirmed 0/0/0 across 313 files, human checkpoint approved, then `gh repo create scottkw/maccat --public --push` published the single-commit history to GitHub — MIG-01 and MIG-03 satisfied.

## What Was Built

A public GitHub repository at https://github.com/scottkw/maccat containing:

- Single initial commit: "Initial commit: maccat — macOS software & tooling cataloger"
- Default branch: `main`
- Visibility: `PUBLIC`
- Content: the full genericized maccat tree (313 files: `src/maccat/`, `tests/`, `docs/`, `scripts/`, `.planning/`, `update-list.sh`, `CLAUDE.md`, `.github/`, `LICENSE`, `README.md`, `.gitignore`, `config.example.toml`, `.python-version`, `pyproject.toml`)
- Zero personal hostnames, machine labels, or catalog data files in any surface

## Task Results

| Task | Name | Result | Notes |
|------|------|--------|-------|
| 1 | Fresh git init + single initial commit | DONE (prior executor) | 1 commit on main, no remote |
| 2 | Privacy gate — working tree + git log + stray catalogs | DONE (prior executor) | 0/0/0 across 313 files |
| 3 | Human checkpoint — review gate results before push | APPROVED | Human confirmed before irreversible push |
| 4 | Create public GitHub repo and push fresh history | DONE | All 6 acceptance criteria PASS |

## Privacy Gate Results

| Surface | Scan Method | Matches | Result |
|---------|-------------|---------|--------|
| Working tree (excluding tests/golden) | `git grep -nE "$RX" -- . ':(exclude)tests/golden/*'` | 0 | PASS |
| Full git history | `git log --all -p \| grep -nE "$RX"` | 0 | PASS |
| Stray catalog .txt files | `find "$S" -name 'mac-software-list-*.txt' -not -path '*/tests/*'` | 0 | PASS |

**Files scanned:** 313  
**Regex used:** `computer-one|computer-one|local|Example Computer`  
**Format string NOT matched:** `mac-software-list-[` (legitimate code/docs pattern — not personal data)

## Post-Push Verification

| Check | Command | Result |
|-------|---------|--------|
| Visibility | `gh repo view scottkw/maccat --json visibility -q .visibility` | `PUBLIC` PASS |
| Default branch | `gh repo view scottkw/maccat --json defaultBranchRef -q .defaultBranchRef.name` | `main` PASS |
| Commit count | `git -C "$S" rev-list --count origin/main` | `1` PASS |
| Origin URL (staging) | `git -C "$S" remote get-url origin` | `https://github.com/scottkw/maccat.git` PASS |
| LICENSE present | `gh api repos/scottkw/maccat/contents/LICENSE -q .name` | `LICENSE` PASS |
| This repo origin untouched | `git -C /Users/ken/dev/mac-software-list remote get-url origin` | `a private catalog remote.git` PASS |

**Public repo URL:** https://github.com/scottkw/maccat

## Deviations from Plan

### Orchestrator Pre-Execution Amendment (Documented, Not a Deviation)

Before this plan's execution began, the orchestrator discovered 3 references to the private git host (`a private git host`) in `.planning/` docs inside the staging tree. It scrubbed them to neutral placeholders and `git commit --amend`ed the single initial commit so neither the working tree nor the full git history contained the private hostname. The privacy gate re-verification at execution start confirmed 0/0/0. This was handled correctly by the orchestrator between the Task 3 checkpoint approval and this plan's Task 4 execution — no re-scrub was needed.

## Threat Mitigations Applied

| Threat ID | Status |
|-----------|--------|
| T-18-05 Personal data in working tree or git log published to public repo | MITIGATED — three-surface gate passed (0/0/0), orchestrator amended commit to remove private-remote hostname before push |
| T-18-06 Accidentally pushing to this repo's private remote origin | MITIGATED — all git ops used `git -C "$S"`; staging origin verified as github.com/scottkw/maccat; this repo's remote unchanged |
| T-18-07 Wrong owner or visibility | MITIGATED — `gh repo create scottkw/maccat --public`; verified PUBLIC post-create |
| T-18-09 Irreversible publication on unreviewed tree | MITIGATED — Task 3 human checkpoint approved explicitly before `gh repo create --push` |

## Known Stubs

None — the published repo is the complete genericized maccat source tree. No placeholder sections or unimplemented stubs.

## Threat Flags

None — no new network endpoints, auth paths, or file access patterns beyond the planned public GitHub repo creation.

## Self-Check: PASSED

**Public repo exists:**
- https://github.com/scottkw/maccat — FOUND (visibility=PUBLIC, branch=main)

**Single-commit history pushed:**
- `git -C "$S" rev-list --count origin/main` == 1 — CONFIRMED

**This repo's private remote untouched:**
- `a private catalog remote.git` — CONFIRMED unchanged
