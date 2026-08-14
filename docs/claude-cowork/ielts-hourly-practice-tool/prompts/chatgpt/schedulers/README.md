# ChatGPT scheduler baselines — one-time bootstrap only

## MAX LIMIT — what may change in `schedulers/`

**Hard rule for all AI agents:** This folder is **bootstrap only**. The owner pastes each `.scheduler.md` COPY block **once** into ChatGPT automation and should **never** need to re-paste when behavior changes.

### Allowed in `schedulers/*.scheduler.md` (and nothing else)

| # | Content |
|---|---------|
| 1 | Title + link to this README |
| 2 | Metadata table: `baseline-version`, parent task prompt link |
| 3 | COPY block (~5 lines): GitHub connector + repo/branch + ordered fetch URLs + “execute fetched prompt” + commit to `main` |

### FORBIDDEN in `schedulers/` — edit parent `../<task>.md` instead

- Queue size, refill order, episode date caps, state rules
- SKIP / never-SKIP / FULL / REPAIR / CHAT-DELIVERY modes
- Duplicate scan, filename collision (`HHMM`), content schema
- Privacy rules, delivery templates, commit message wording
- **Bumping `baseline-version`** for any of the above
- **Telling the owner to re-paste** after a behavior-only change
- Duplicating rules from the parent task prompt into the COPY block

### When a scheduler edit is allowed (rare)

Bump `baseline-version` **only** if:

- Pages base URL or path to `SHARED.md` / task prompt changes
- GitHub repo or branch in the COPY block changes
- A new **mandatory** fetch URL is added to the bootstrap list

Then tell the owner to re-paste **once**. For everything else: edit `../<task>.md`, bump its `version:`, push — next run fetches the update automatically.

---

## Two-file pattern

| Role | File | Who uses it | When to update |
|------|------|-------------|----------------|
| **Task prompt** | `../<task>.md` | ChatGPT **fetches every run** via Pages | **All behavior** — edit freely; bump `version:` |
| **Scheduler baseline** | `<task>.scheduler.md` | **Owner pastes once** | **Bootstrap only** — see MAX LIMIT above |

The baseline is a **static bootstrap**: connector + URL list only. It tells ChatGPT to fetch `SHARED.md` and the task prompt with `?t=<unix_ts>`.

---

## Policy for AI agents (mandatory)

### DO edit parent task prompts (`../<task>.md`)

- Queue size, refill order, skip/never-SKIP rules, FULL/CHAT-DELIVERY modes
- Duplicate scan, filename collision (`HHMM`), content schema, delivery templates
- Bump the task prompt's `version:` header when behavior changes

### DO NOT edit schedulers for behavior

- **Never** add behavior rules to `*.scheduler.md`
- **Never bump `baseline-version`** for behavior, queue, or skip-rule changes
- **Never** tell the user to re-paste the scheduler after a behavior-only change
- **Never** mirror parent-prompt rules into the COPY block “for convenience”

---

## Pages base

```
https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/
```

After pushing to GitHub, wait **~1–2 minutes** before the next scheduled run.

---

## Tasks

| Task | Scheduler baseline (paste once) | Task prompt (fetched each run) |
|------|----------------------------------|--------------------------------|
| BBC 6 Minute English | [bbc-6min.scheduler.md](./bbc-6min.scheduler.md) | [../bbc-6min.md](../bbc-6min.md) |
| IELTS hourly | [ielts-hourly.scheduler.md](./ielts-hourly.scheduler.md) | [../ielts-hourly.md](../ielts-hourly.md) |
| Daily news | [daily-news.scheduler.md](./daily-news.scheduler.md) | [../daily-news.md](../daily-news.md) |
| World Cup daily | [worldcup-daily.scheduler.md](./worldcup-daily.scheduler.md) | [../worldcup-daily.md](../worldcup-daily.md) |
| Morning brief | [morning-brief.scheduler.md](./morning-brief.scheduler.md) | [../morning-brief.md](../morning-brief.md) — **no GitHub connector; no `SHARED.md`** |

Shared rules (fetched, not pasted alone): [../SHARED.md](../SHARED.md) — **not used by morning brief**

---

## How to paste (owner — one time)

1. Open the `.scheduler.md` file for your task.
2. Copy **only** the block under `## COPY BELOW INTO CHATGPT SCHEDULED TASK`.
3. Paste into the ChatGPT scheduled task / automation prompt field.
4. Attach **GitHub connector** to `mtm0101/public-sites`, branch **`main`** — **except morning brief** (chat-only; do not attach GitHub).

Replace `<unix_ts>` with the current Unix timestamp when testing manually, or instruct the task to use the current time each run.

**You do not need to re-paste** when queue size, skip rules, or other behavior changes — push the parent `*.md` and the next run picks it up automatically.

See also: [specs/08-agent-workflows.md](../../specs/08-agent-workflows.md) §2.
