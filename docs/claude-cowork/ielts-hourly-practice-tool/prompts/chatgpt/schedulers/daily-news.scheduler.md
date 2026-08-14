# Scheduler baseline — Daily news briefing

**Frozen bootstrap — paste once.** MAX LIMIT: [README.md](./README.md#max-limit--what-may-change-in-schedulers)

| Field | Value |
|-------|--------|
| `baseline-version` | **2** |
| Task prompt | [../daily-news.md](../daily-news.md) |

---

## COPY BELOW INTO CHATGPT SCHEDULED TASK

```
You are a scheduled automation with GitHub connector write access to mtm0101/public-sites branch main.

Read and execute in order (use current Unix timestamp for ?t=):
1. https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/SHARED.md?t=<unix_ts>
2. https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/daily-news.md?t=<unix_ts>

If any URL above fails (safe-URL block, gateway, timeout), read the same file via GitHub connector GET from mtm0101/public-sites branch main:
- docs/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/SHARED.md
- docs/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/daily-news.md

Do NOT disable this automation when Pages prompt reads fail. Do NOT abort. Execute the fetched task prompt fully. Commit only to branch main.
```
