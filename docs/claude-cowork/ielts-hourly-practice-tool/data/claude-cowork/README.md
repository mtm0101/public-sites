# Claude Cowork — content folder

**Source label in app:** `claude-cowork`  
**Scheduler prompts:** [prompts/claude/](../prompts/claude/)

---

## Paths

| Type | Path |
|------|------|
| IELTS hourly lessons | `lessons/ielts-YYYY-MM-DD-HH00-topicNN-<slug>.json` |
| BBC episodes (from HTML) | `bbc/bbc-claude-<YYMMDD>-<slug>.json` |
| News / misc | `news/*.json` |
| Speaking practice | `speaking/0.speaking.json` |
| IELTS rotation state | `state.json` |

---

## Workflow

1. Read [specs/](../specs/README.md) + [prompts/claude/ielts-hourly.md](../prompts/claude/ielts-hourly.md)
2. Write new JSON under this folder
3. Run `python scripts/convert_lessons.py` from tool root
4. Push via `update-index-and-push.ps1`

BBC HTML pipeline: `../bbc-lessons/*.html` → `python scripts/convert_bbc_html.py`

---

## Do not touch

`data/templates/`, `data/ipa/`, `data/chatgpt/`, `manifest.json`, `index.html`
