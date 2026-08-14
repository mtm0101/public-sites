# Scripts Reference

Documentation for the PowerShell automation scripts in this repo. Intended for AI agents and future maintainers.

---

## update-index-and-push.ps1

**Location:** repo root  
**Run:** double-click, or `.\update-index-and-push.ps1` in PowerShell from repo root  
**Purpose:** General-purpose sync — rebuilds the HTML index from whatever is currently on disk, then commits and pushes.

### What it does (in order)

0. **Sync `docs/index.html` manifest** — reads the embedded JSON manifest inside `docs/index.html` (`<script id="siteManifest">`), removes any entry whose top-level folder no longer exists on disk, and writes the file back. This is the main public index visible at the repo root — it must stay in sync with what's actually on disk.

1. **Cleanup removed folders** — compares `git ls-files` (what git tracks under `docs/claude-cowork/`) against subdirectories currently on disk. For any folder that no longer exists, it `git rm --cached` every tracked `.html` and `.json` file that belonged to it, so they are staged for deletion in the next commit.

2. **Rebuild index HTML** — scans all subdirectories of `docs/claude-cowork/`, builds a `<div class="section">` block for each one listing its `.html`, `.pdf`, and `.md` files (hidden files excluded). Injects the result between `<!-- BEGIN_SECTIONS -->` and `<!-- END_SECTIONS -->` markers in `docs/index-claude-cowork-13571357.html` and updates the "last updated" date.

3. **Git commit + push** — runs `git add .`, commits with message `update: YYYY-MM-DD HH:mm`, and pushes to `origin/main`. Prompts to press Enter before exit (interactive use).

### Folder → icon mapping

| Keyword in folder name | Icon |
|---|---|
| aws | ☁ |
| bbc | 📻 |
| finance | 💰 |
| morning | 🌅 |
| news | 📰 |
| weekly | 📊 |
| worldcup / world | ⚽ |
| brief | 📋 |
| report | 📈 |
| log | 📝 |
| *(anything else)* | 📄 |

### Adding a new folder

Just create the folder under `docs/claude-cowork/` and drop files in it. Run the script — it picks up the new folder automatically, no code changes needed.

### Removing a folder

Delete the folder from disk. Run the script — it detects the missing folder, unregisters its `.html`/`.json` files from git, removes the section from the index HTML, and commits everything.

---

## docs/claude-cowork/bbc-lessons/bbc-6min-push.ps1

**Location:** `docs/claude-cowork/bbc-lessons/`  
**Run:** called automatically by scheduled task, or manually `.\bbc-6min-push.ps1`  
**Purpose:** Dedicated push script for BBC 6-Minute English lessons. Non-interactive (no prompts). Logs to `.push-log.txt` in the same folder.

### Parameters

| Parameter | Default | Description |
|---|---|---|
| `-Title` | `""` | Episode title, used in the commit message |
| `-Date` | today | Episode date `YYYY-MM-DD`, used in the commit message |

### What it does (in order)

Same three-step flow as `update-index-and-push.ps1`, but:

- **Non-interactive** — no `Read-Host` prompts; safe for scheduled/automated calls.
- **Commit message** uses the episode title and date: `bbc-6min: Title (YYYY-MM-DD)`, or `bbc-6min: lesson YYYY-MM-DD` when no title is passed.
- **Logs** every step with timestamps to `.push-log.txt` via the `Log()` function.
- Uses an absolute `$repoRoot` path (hardcoded for scheduled task compatibility, since `$PSScriptRoot` is unreliable in Task Scheduler).

### Scheduled task integration

The scheduled task calls this script after Claude generates a new episode file, passing `-Title` and `-Date` so the commit message is descriptive. Example:

```powershell
& "C:\Users\<username>\Downloads\gpt-codex\public-sites\docs\claude-cowork\bbc-lessons\bbc-6min-push.ps1" `
    -Title "Is it good to talk?" `
    -Date "2021-06-03"
```

---

## Shared logic

Both scripts share identical logic for folder scanning, icon mapping, and HTML generation. If you need to change display behavior (icons, file types shown, HTML structure), update both files.

The HTML index file that both scripts write to:  
`docs/index-claude-cowork-13571357.html`

The scanned folder:  
`docs/claude-cowork/` — one subdirectory = one section card in the index.
