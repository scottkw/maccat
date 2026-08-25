# maccat

A Python tool that catalogs all software **and developer tooling** installed on your macOS machine — applications, plus the extensions, plugins, MCP servers, and skills/agents of your AI coding CLIs, editors, and browsers. Each catalog is named with a **friendly machine label** you choose, each run keeps only the newest catalog **per machine** in the main folder, archives the rest, auto-prunes the archive after a configurable number of days (default 30), and syncs every change via git.

Catalogs are written as **rendered Markdown (`.md`)** — a YAML frontmatter block (computer, hostname, generated timestamp, maccat version) followed by one `##` section per source, each a uniform `Name | Version | ID` table. The output stays deterministic and stably sorted, so two unchanged runs diff cleanly.

It can also work in reverse: `maccat reinstall` turns a catalog back into a reviewable [`reinstall.sh`](#reinstall-from-a-catalog) — a never-auto-executed script that reinstalls the deterministic sources (Homebrew, Mac App Store, VS Code/Cursor extensions) and lists everything else as a manual checklist. Legacy plain-text (`.txt`) catalogs from before v3.0.0 are upgraded to the new format with [`maccat convert`](#convert-a-legacy-catalog).

> **Format change in v3.0.0:** catalogs moved from plain text (`.txt`) to Markdown (`.md`). `reinstall` consumes `.md` only; run `convert` on any older `.txt` catalog first.

## Overview

This tool generates comprehensive Markdown (`.md`) catalogs of your installed software and tooling from multiple sources — **22 sections** in total:

**Applications**

- **Homebrew packages** (formulae and casks)
- **Mac App Store applications** (via the `mas` CLI)
- **Setapp applications**
- **Web-installed applications** (DMG, PKG, direct downloads)

**AI coding CLI tooling** (name + version + ID where available)

- **Claude Code** — plugins, MCP servers, and skills/agents
- **Codex** — MCP servers and plugins
- **OpenCode** — plugins, MCP servers, and agents
- **Gemini CLI** — extensions and MCP servers

**Editor extensions**

- **VS Code**, **Cursor**, and **Zed** — installed extensions (human-readable display names resolved)

**Browser extensions** (across all profiles)

- **Google Chrome**, **Microsoft Edge**, and **Brave** — user-installed extensions (built-in components excluded via per-browser denylists)
- **Firefox** — user-installed extensions and themes (built-in/system add-ons excluded)
- **Safari** — user-installed web extensions (via `pluginkit` + per-`.appex` `Info.plist`)

Each catalog is timestamped and named with a **friendly machine label** you choose (see [Machine Identity](#machine-identity)) for easy identification across multiple Macs. Every source **degrades gracefully** — if a tool or browser isn't installed, its section renders `(none found)` and the run continues.

> **Privacy:** MCP server entries capture **name + transport type only** (e.g. `my-server [stdio]`). Environment values, headers, tokens, and auth-bearing URLs are **never** written to the catalog — the file is git-committed and pushed, so secrets must not leak into it.

## Installation

maccat ships as a self-contained Python zipapp (`.pyz`). No installation of the package itself is needed — download the file and run it directly.

**Requirements:** Python >= 3.11, macOS.

### Download from GitHub Releases

1. Go to the [Releases page](https://github.com/scottkw/maccat/releases) and download the latest `maccat.pyz`.
2. Make it executable (optional but convenient):
   ```bash
   chmod +x maccat.pyz
   ```
3. Run it:
   ```bash
   python3 maccat.pyz --catalog-dir /path/to/your/catalog-repo
   # or, if executable:
   ./maccat.pyz --catalog-dir /path/to/your/catalog-repo
   ```

The **catalog repo** is a separate git repository where maccat writes its snapshot files. You can create a new one or use an existing repo — maccat just needs a directory with a git remote configured.

## Configuration

maccat needs to know where your catalog repo lives. Resolution order (highest priority first):

1. **`--catalog-dir <path>`** — command-line flag (takes precedence over everything)
2. **`MACCAT_CATALOG_DIR`** — environment variable
3. **`~/.config/maccat/config.toml`** — config file (`catalog_dir` key)
4. **Error** — if none of the above is set, maccat exits with an error

### Config file

Copy `config.example.toml` to `~/.config/maccat/config.toml` and set `catalog_dir`:

```toml
catalog_dir = "/path/to/your/catalog-repo"
```

See `config.example.toml` for the full template with comments.

## Usage

### Basic run

```bash
# Using the config file (~/.config/maccat/config.toml)
python3 maccat.pyz

# Explicitly specify the catalog repo
python3 maccat.pyz --catalog-dir ~/my-catalog-repo

# Using the environment variable
MACCAT_CATALOG_DIR=~/my-catalog-repo python3 maccat.pyz
```

If no computer-folder argument is provided, you'll be prompted to choose a folder:

```
Where would you like to save this catalog?

  1) home
  2) work

Enter your choice (1 or 2):
```

Or specify it directly:

```bash
# Skip the interactive folder-selection prompt
python3 maccat.pyz --computer MyMac
```

### Options

| Option | Description |
|--------|-------------|
| `--computer NAME` | Select (or create) the named computer-folder non-interactively |
| `--catalog-dir <path>` | Path to the catalog git repository (overrides config and env) |
| `--no-commit` | Skip automatic git commit and push |
| `--archive-days N` | Set the archive-retention period in days for this run (default: 30) |
| `--rename` | Separate mode: rename a machine label across all catalog files, then commit |

### Reinstall from a catalog

The `reinstall` subcommand reads a catalog back and generates a **`reinstall.sh`** script in the current directory that can rebuild a machine's software from the snapshot. The script is **never run for you** — it's written non-executable (mode `0644`) and printed for you to review and run yourself.

```bash
# Use an explicit catalog file (must be a Markdown .md catalog)
python3 maccat.pyz reinstall --from /path/to/mac-software-list-[home]-20260616120000.md

# Or omit --from: pick a computer interactively and use its newest catalog
python3 maccat.pyz reinstall

# Non-interactive: pick a computer by name (uses that folder's newest catalog)
python3 maccat.pyz --catalog-dir ~/my-catalog-repo reinstall --computer home
```

maccat prints the absolute path of the generated script:

```
/Users/you/reinstall.sh
```

**What the script does:**

- **Auto-installs the deterministic sources** with idempotent, re-runnable, guarded commands:
  - **Homebrew** — `brew list <n> &>/dev/null || brew list --cask <n> &>/dev/null || brew install <n>` (one command covers formulae and casks)
  - **Mac App Store** — `mas install <id>` for apps whose numeric App Store ID is in the catalog (guarded so an already-installed app doesn't abort the run)
  - **VS Code / Cursor extensions** — `code`/`cursor --install-extension <id>` behind a `command -v` PATH guard and a `--list-extensions` idempotency check
  - Each line carries the cataloged version as a `# cataloged: …` comment (it installs the **latest** version, not a pin).
- **Lists everything else as a manual checklist** (no fabricated install commands): Setapp apps, web-installed `/Applications`, Chrome/Firefox extensions, and all AI-CLI MCP servers / plugins / skills / agents (these are cataloged as identity-only for privacy, so there's nothing to auto-install).
- Opens with `#!/usr/bin/env bash` + `set -Eeuo pipefail` and a provenance header naming the source catalog and generation date. Every catalog-derived value is shell-quoted, so it's safe to generate from any catalog.

> **Note:** App Store entries are only auto-installed when the catalog records their numeric ID. Catalogs generated before v2.1.0 don't have it, so those apps fall into the manual checklist instead.

> **Markdown-only (v3.0.0+):** `reinstall` reads the Markdown (`.md`) format exclusively. Handed a legacy `.txt` catalog — or a `.md` file missing valid frontmatter — it exits with a clear error directing you to `maccat convert --from PATH` first. It never silently part-parses an old catalog.

| Subcommand | Description |
|------------|-------------|
| `reinstall [--from PATH]` | Generate `reinstall.sh` from a Markdown catalog (explicit `--from`, else the computer picker uses the newest catalog; `--computer NAME` selects non-interactively) |
| `convert --from PATH` | Upgrade one legacy `.txt` catalog to the new `.md` format in place (see [Convert a legacy catalog](#convert-a-legacy-catalog)) |

### Convert a legacy catalog

The `convert` subcommand upgrades a single legacy plain-text (`.txt`) catalog to the new Markdown (`.md`) format. It reads the `.txt` through the retained legacy parser, rewrites the full contents — every section and every item's name / version / ID — through the same Markdown emitter used by catalog generation, writes the `.md`, removes the old `.txt`, and stages both changes in one commit.

```bash
# Convert one legacy catalog (writes the .md, removes the .txt, commits both)
python3 maccat.pyz convert --from /path/to/mac-software-list-[home]-20260616120000.txt

# Do the file operations without committing to git
python3 maccat.pyz convert --from /path/to/old-catalog.txt --no-commit
```

- **Frontmatter is synthesized from the current machine** at conversion time: `computer` is parsed from the filename, while `generated` (now), `hostname`, and `maccat_version` reflect the machine running `convert`. The output keeps the **original filename timestamp** (only the extension changes, `.txt` → `.md`).
- **Safe and non-destructive:** the `.txt` is removed only after the `.md` is written successfully. If the target `.md` already exists, convert errors rather than overwriting it. Missing, unreadable, or unrecognizable input aborts cleanly with a clear error — convert never fabricates data and never executes anything.
- **Single-file only.** Bulk / folder-wide conversion is not yet supported.

| Subcommand | Description |
|------------|-------------|
| `convert --from PATH` | Convert one legacy `.txt` catalog to `.md` (in-place replace + single commit; `--no-commit` does the file ops only) |

## Machine Identity

Catalog files are named with a **friendly machine label** you choose, instead of the raw hostname. Each Mac remembers its label, so you're only prompted the first time.

### How the label is resolved

On each run, the label is resolved in this order:

1. **`--computer NAME` flag** — used as-is for this run, and saved to the map.
2. **Saved entry** — if this machine's hostname is already in `machine-labels.tsv`, its label is used automatically with no prompt.
3. **Interactive menu** — on a new machine with no saved label, you get a numbered menu of all known labels plus a **"Create new label"** option:

   ```
   Select a machine label for this run:

     1) My Laptop
     2) Work iMac
     3) Create new label

   Enter your choice (1-3):
   ```

   Whatever you pick (existing label or a new one you type) is saved, so subsequent runs on this machine resolve it automatically.

### The hostname → label map

Mappings live in **`machine-labels.tsv`** at the catalog repo root — a git-tracked, tab-delimited file (`hostname<TAB>label`, one per line; `#` comments and blank lines are ignored). Because it's committed, every machine converges on the same roster of labels when it pulls, which powers the selection menu and the rename feature.

**Labels** may contain spaces, apostrophes, letters, digits, and `-` `_` `.` — but **not** `/`, `[`, `]`, tabs, or newlines, and not leading/trailing whitespace. Invalid labels are rejected with an error.

**Non-interactive runs** (cron, piped stdin) on a machine with no saved label and no `--computer` flag **fail fast** with a clear error rather than hanging — pass `--computer NAME` in that case.

## Renaming a Machine

`--rename` is a **separate mode** (it doesn't generate a catalog) that rewrites a machine label everywhere it appears — across all computer-folders and their archives — in a single self-committing operation:

```bash
python3 maccat.pyz --rename
```

It pulls the latest changes, presents a menu of known labels, asks for the new label, and then:

- Renames every matching `mac-software-list-[OLD]-...md` to `[NEW]` across all directories (preserving timestamps).
- Updates the `machine-labels.tsv` entry to the new label.
- Stages all the moves plus the map change and commits/pushes in **one commit**.

Safety behavior:

- If a destination filename already exists, that individual file is **skipped** (never overwritten) and reported.
- If **no** files match the chosen label anywhere, nothing is changed — no map edit, no commit.
- `--rename` requires an interactive terminal; combine with `--no-commit` to perform the renames on disk without committing.

## Retention & Archiving

On **every run**, maccat keeps the selected computer-folder lean and self-prunes its archive. Two operations run automatically, scoped to the folder you targeted — the other folder is never touched:

**1. Keep newest-per-machine (retention)**

- The main folder keeps only the **newest catalog per machine** — one current snapshot per label.
- All older catalogs for each machine are moved into that folder's `archive/` subfolder.

**2. Prune the archive (configurable retention, default 30 days)**

- Catalogs in `archive/` whose filename timestamp is **older than the retention period** are **hard-deleted** from disk.
- The retention period defaults to **30 days**. Set it per run with `--archive-days N`.
- Age is determined by the timestamp in the filename; an unparseable filename is skipped (never deleted).

Both operations degrade gracefully — an empty folder, a missing `archive/` directory, or an unparseable filename never aborts the run, and the newest catalog for each machine is never archived or deleted.

## Git Integration

By default, maccat automatically commits and pushes changes to git after generating a catalog:

- **Auto-commit**: The new catalog file is automatically committed with a detailed message
- **Auto-push**: Changes are pushed to the remote repository
- **All changes in one commit**: The commit stages the entire targeted folder, so the new catalog, catalogs moved to `archive/`, catalogs removed by the archive prune, and any new/changed machine-label mapping are all synced together.

### Commit Message Format

```
Added personal catalog for [<machine-label>] at YYYYMMDDHHMMSS
```

### Disabling Auto-commit

```bash
python3 maccat.pyz --no-commit
```

The retention and archive prune still run on disk with `--no-commit` — only the git commit/push step is skipped.

## Output

maccat generates a Markdown file named:

```
mac-software-list-[<machine-label>]-YYYYMMDDHHMMSS.md
```

For example: `mac-software-list-[My Laptop]-20260601153045.md`

Each file opens with a YAML frontmatter block carrying provenance, followed by a `#` title and one `##` section per source:

```yaml
---
computer: "My Laptop"
hostname: "my-laptop.local"
generated: "2026-06-01T15:30:45"
maccat_version: "3.1.0"
---
```

### Catalog Contents

Each catalog contains **22 sections**, in this order:

**Applications**

1. **Homebrew Packages** — all formulae and casks installed via Homebrew
2. **App Store Applications** — apps installed from the Mac App Store
3. **Setapp Applications** — apps from the Setapp subscription service
4. **Web-installed Applications** — other apps in /Applications

**AI coding CLI tooling**

5. **Claude Code Plugins** / **Claude Code MCP Servers** / **Claude Code Skills & Agents**
6. **Codex MCP Servers** / **Codex Plugins**
7. **OpenCode Plugins** / **OpenCode MCP Servers** / **OpenCode Agents**
8. **Gemini CLI Extensions** / **Gemini CLI MCP Servers**

**Editor extensions**

9. **VS Code Extensions** / **Cursor Extensions** / **Zed Extensions**

**Browser extensions** (all profiles)

10. **Google Chrome Extensions** / **Microsoft Edge Extensions** / **Brave Browser Extensions** / **Firefox Extensions** / **Safari Extensions**

Every section renders as a `##` heading containing a three-column `Name | Version | ID` table; a missing version or ID renders as an empty cell, and a source with no items renders `(none found)` under its heading. Rows are **stably sorted** and the output is byte-deterministic, so two consecutive runs on an unchanged machine produce an identical catalog (an empty diff). MCP server / plugin / skill entries are **identity-only** (no secrets — see the privacy note above).

## Example Output

````markdown
---
computer: "My Laptop"
hostname: "my-laptop.local"
generated: "2026-06-01T15:30:45"
maccat_version: "3.1.0"
---
# Installed Mac Software List

## Homebrew Packages
| Name | Version | ID |
| --- | --- | --- |
| autoconf | 2.73 |   |
| awscli | 2.35.7 |   |
| git | 2.44.0 |   |

## App Store Applications
| Name | Version | ID |
| --- | --- | --- |
| Amphetamine | 5.3.2 | 937984704 |
| Bitwarden | 2026.5.0 | 1352778147 |
| Xcode | 15.0 | 497799835 |

## Codex Plugins
(none found)

## VS Code Extensions
| Name | Version | ID |
| --- | --- | --- |
| Auto Rename Tag | 0.1.10 | formulahendry.auto-rename-tag |
| Claude Code for VS Code | 2.1.181 | anthropic.claude-code |

## Google Chrome Extensions
| Name | Version | ID |
| --- | --- | --- |
| Bitwarden Password Manager | 2026.5.1 | nngceckbapebfimnlniiiahkandclblb |
| Claude | 1.0.77 | fcoeoabgfenejglbffodgkkbkcdhcgfn |
````

## Prerequisites

maccat reads on-disk config and manifests for the tools it catalogs — no separate integration setup is needed. The following optional tools extend what maccat can catalog:

- **Homebrew** — for listing brew packages
  ```bash
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  ```

- **mas** (Mac App Store CLI) — for listing App Store apps
  ```bash
  brew install mas
  ```

- **jq** — preferred JSON parser; falls back to the built-in `/usr/bin/plutil` if absent
  ```bash
  brew install jq
  ```

No setup is needed for the AI CLIs (Claude Code, Codex, OpenCode, Gemini), editors (VS Code, Cursor, Zed), or browsers (Chrome, Edge, Brave, Firefox, Safari) — maccat auto-detects whichever are installed and silently skips the rest.

maccat was originally implemented as a Zsh script and ported to Python in v1.0.0.

## Troubleshooting

### "mas is not installed" warning

```bash
brew install mas
```

### "Homebrew is not installed" warning

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Permission denied running maccat.pyz

```bash
chmod +x maccat.pyz
```

## License

MIT — see [LICENSE](LICENSE).
