# ChatGPT scheduled task prompts

Two-file pattern per task — see **[schedulers/README.md](./schedulers/README.md)**.

| Role | Location | Who |
|------|----------|-----|
| **Task prompt** | `<task>.md` (this folder) | ChatGPT **fetches every run** |
| **Scheduler baseline** | `schedulers/<task>.scheduler.md` | **You paste once** into ChatGPT automation (frozen bootstrap) |

## Read order (every automated run)

1. **[SHARED.md](./SHARED.md)** — commit rules, `main` only, verification links
2. **Task prompt** — e.g. [bbc-6min.md](./bbc-6min.md)

## Tasks

| Task prompt (fetched) | Scheduler baseline (copy-paste) | Output folder |
|----------------------|--------------------------------|---------------|
| [bbc-6min.md](./bbc-6min.md) | [schedulers/bbc-6min.scheduler.md](./schedulers/bbc-6min.scheduler.md) | `data/chatgpt/bbc/` |
| [ielts-hourly.md](./ielts-hourly.md) | [schedulers/ielts-hourly.scheduler.md](./schedulers/ielts-hourly.scheduler.md) | `data/chatgpt/lessons/` |
| [daily-news.md](./daily-news.md) | [schedulers/daily-news.scheduler.md](./schedulers/daily-news.scheduler.md) | `data/chatgpt/news/` |
| [worldcup-daily.md](./worldcup-daily.md) | [schedulers/worldcup-daily.scheduler.md](./schedulers/worldcup-daily.scheduler.md) | `data/chatgpt/news/` |
| [morning-brief.md](./morning-brief.md) | [schedulers/morning-brief.scheduler.md](./schedulers/morning-brief.scheduler.md) | **chat only** (no repo write; no `SHARED.md`) |
| [dol-vocab.md](./dol-vocab.md) | [schedulers/dol-vocab.scheduler.md](./schedulers/dol-vocab.scheduler.md) | `data/chatgpt/dol/` |

## Maintenance (MAX LIMIT)

- **Behavior change** → edit task `.md` only; bump `version:`. Push — next run picks it up. **Never** re-paste scheduler for behavior.
- **Scheduler edit** → **only** if bootstrap URL list or repo/branch changes ([MAX LIMIT](./schedulers/README.md#max-limit--what-may-change-in-schedulers)).
- `schedulers/` = connector + fetch URLs only — no behavior rules.

Pages base: `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/`

Append `?t=<unix_timestamp>` on fetch URLs to bypass cache.
