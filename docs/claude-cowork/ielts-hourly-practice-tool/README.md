# IELTS Hourly Practice Tool

Single-page bilingual IELTS study app + multi-agent content pipeline.

**AI agents:** start at [AGENTS.md](./AGENTS.md) → [specs/README.md](./specs/README.md)

---

## Folder map

```
ielts-hourly-practice-tool/
├── index.html          # The app (GitHub Pages entry)
├── manifest.json       # App lesson index (auto-generated)
├── AGENTS.md           # AI entry point
├── CLAUDE.md           # Maintainer / runtime docs
│
├── specs/              # Content contracts (WHAT to build)
├── prompts/            # HOW each agent runs
│   ├── chatgpt/        # Task .md (fetched) + schedulers/ (copy-paste baselines)
│   └── claude/         # Claude Cowork schedulers
│
├── scripts/            # Python + PowerShell automation
│   ├── convert_lessons.py
│   └── convert_bbc_html.py
│
└── data/               # Study content (GitHub Pages; not AWS S3)
    ├── templates/      # Shared JSON skeletons + template-spec.json
    ├── ipa/            # Pronunciation shards (app data)
    ├── claude-cowork/  # Claude Cowork agent output
    ├── chatgpt/        # ChatGPT agent output
    └── codex/          # Codex / future agents
```

---

## Quick commands

From this folder:

```powershell
python scripts/convert_lessons.py      # rebuild manifest.json
python scripts/convert_bbc_html.py     # BBC HTML → JSON
```

From repo root:

```powershell
powershell -File update-index-and-push.ps1   # convert + commit + push
```

---

## Agent content paths

| Agent | Folder | State file |
|-------|--------|------------|
| Claude Cowork | `data/claude-cowork/` | `data/claude-cowork/state.json` |
| ChatGPT | `data/chatgpt/` | `data/chatgpt/state.json`, `data/chatgpt/bbc/processed.json`, `data/chatgpt/bbc/upcoming.json` |
| Codex | `data/codex/` | per task |

See [data/README.md](./data/README.md) for standard subfolders (`lessons/`, `bbc/`, `news/`, …).
