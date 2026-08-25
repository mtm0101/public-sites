# Study content root (`data/`)

All published study JSON lives here (served via GitHub Pages).  
The app loads content via `manifest.json` (rebuilt by `scripts/convert_lessons.py`).

**AWS S3** is used only for `user-data.json` (progress sync) — see the app Data tab.

---

## Layout

```
data/
├── templates/       # Shared contracts — READ only for agents (not indexed by app)
├── ipa/               # US/UK pronunciation shards (app runtime data)
├── claude-cowork/     # Claude Cowork agent
├── chatgpt/           # ChatGPT scheduled tasks
│   └── tests/         # Generic test manifest, taxonomy, definitions and immutable question packs
└── codex/             # Codex / other agents (placeholder)
```

---

## Standard agent subfolders

Each agent folder uses the same shape where applicable:

| Subfolder | Content type | App tab |
|-----------|--------------|---------|
| `lessons/` | IELTS hourly (`ielts-*.json`) | 📚 Lessons |
| `bbc/` | BBC 6 Minute (`bbc-*.json`) | 🎧 BBC |
| `news/` | Daily news, World Cup | 🗂 Others |
| `brief/` | Morning brief | 🗂 Others |
| `speaking/` | Speaking Q&A sets | 🗣 Speaking |

**State files** (rotation queues — not in manifest):

| File | Agent | Purpose |
|------|-------|---------|
| `claude-cowork/state.json` | Claude Cowork | IELTS topic rotation |
| `chatgpt/state.json` | ChatGPT | IELTS topic rotation |
| `chatgpt/bbc/processed.json` | ChatGPT | BBC processed episode codes (`processed[]`) |
| `chatgpt/bbc/upcoming.json` | ChatGPT | BBC compact queue (`queue[]` YYMMDD) |
| `chatgpt/bbc/state.json` | Legacy compatibility | Frozen compact archive; not used by current scheduled runs |

---

## Rules

- One folder per **source** (`claude-cowork`, `chatgpt`, `codex`)
- Filename stem = unique **id** repo-wide
- ChatGPT files must include **`-gpt-`** in the stem
- Never put `manifest.json` here — it lives at tool root next to `index.html`
- Files with `template` in the name are ignored by the converter
- Test Simulator JSON is discovered through `data/chatgpt/tests/manifest.json` and intentionally excluded from the lesson manifest

Spec detail: [specs/00-platform.md](../specs/00-platform.md)
