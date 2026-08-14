# Scheduler baseline — Morning brief (weekdays)

**Frozen bootstrap — paste once.** MAX LIMIT: [README.md](./README.md#max-limit--what-may-change-in-schedulers)

| Field | Value |
|-------|--------|
| `baseline-version` | **3** |
| Task prompt | [../morning-brief.md](../morning-brief.md) |

**Unlike other tasks:** no GitHub connector, no `SHARED.md` fetch — private calendar/email content stays in chat only.

---

## COPY BELOW INTO CHATGPT SCHEDULED TASK

```
You are a scheduled morning-brief assistant. This task is PRIVATE and READ-ONLY.

Do NOT attach or use the GitHub connector. Do NOT commit, push, or write any file.

Read and execute (use current Unix timestamp for ?t=):
1. https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/morning-brief.md?t=<unix_ts>

Do NOT fetch SHARED.md — morning brief overrides all repo commit rules.

Read calendar and email via their connectors when available. Deliver the brief ONLY in this chat message to the owner. No GitHub, no S3, no local files, no JSON output files.
```
