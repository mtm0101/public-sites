# ChatGPT — content folder

**Source label in app:** `chatgpt`  
**Scheduler prompts:** [prompts/chatgpt/](../prompts/chatgpt/) — read `SHARED.md` first

---

## Paths (GitHub repo, branch `main`)

Base: `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/`

| Type | Path |
|------|------|
| IELTS hourly | `lessons/ielts-gpt-YYYY-MM-DD-HH00-topicNN-<slug>.json` |
| BBC 6 Minute | `bbc/bbc-gpt-<YYMMDD>-<slug>.json` |
| Daily news | `news/news-gpt-YYYY-MM-DD.json` |
| World Cup | `news/worldcup-gpt-YYYY-MM-DD.json` |
| Morning brief | `brief/brief-gpt-YYYY-MM-DD.json` |
| IELTS state | `state.json` |
| BBC queue state | `bbc/state.json` |

**`-gpt-` marker required** in every filename stem.

---

## Publish

Remote agents commit via **GitHub connector** to `main`.  
**Never** commit `manifest.json` — owner runs `scripts/convert_lessons.py`.

Commit confirmation: verifiable links per [prompts/chatgpt/SHARED.md](../prompts/chatgpt/SHARED.md).

---

## Do not touch

Other agents' folders, `templates/`, `ipa/`, `index.html`
