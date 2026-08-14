# Scheduler baseline — IELTS hourly

**Frozen bootstrap — paste once.** MAX LIMIT: [README.md](./README.md#max-limit--what-may-change-in-schedulers)

| Field | Value |
|-------|--------|
| `baseline-version` | **1** |
| Task prompt | [../ielts-hourly.md](../ielts-hourly.md) |

---

## COPY BELOW INTO CHATGPT SCHEDULED TASK

```
You are a scheduled automation with GitHub connector write access to mtm0101/public-sites branch main.

Read and execute in order (use current Unix timestamp for ?t=):
1. https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/SHARED.md?t=<unix_ts>
2. https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/ielts-hourly.md?t=<unix_ts>

Execute the fetched task prompt fully. Commit only to branch main.
```
