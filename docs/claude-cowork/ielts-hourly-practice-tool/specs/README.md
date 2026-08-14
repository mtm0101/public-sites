# Specs — IELTS Hourly Practice Tool

**Version:** 1.0 · **Updated:** 2026-07-10  
**Tool root:** `docs/claude-cowork/ielts-hourly-practice-tool/`  
**Pages base:** `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/`

---

## For any AI agent — read this first

This folder is the **single source of truth** for publishing content and extending the app.  
**Do not ask clarifying questions** — everything needed is here or linked below.

### Reading order (new session / empty context)

| Step | File | When |
|------|------|------|
| 1 | **[00-platform.md](./00-platform.md)** | Always — repo layout, HTML rules, manifest, discovery |
| 2 | **Task spec** (pick one below) | Your assignment |
| 3 | **[08-agent-workflows.md](./08-agent-workflows.md)** | If publishing (Claude / ChatGPT / Codex) |
| 4 | **[07-app-features.md](./07-app-features.md)** | If changing `index.html` or app behaviour |

Machine-readable index: **[INDEX.json](./INDEX.json)**

---

## Task specs (pick one)

| Spec | Content type | App tab | Output path |
|------|--------------|---------|-------------|
| [01-ielts-hourly-lesson.md](./01-ielts-hourly-lesson.md) | Schema-1 IELTS hourly lesson | 📚 Lessons | `data/{source}/lessons/ielts-*.json` |
| [02-bbc-6min.md](./02-bbc-6min.md) | BBC 6 Minute English episode | 🎧 BBC 6 Minutes | `data/{source}/bbc/bbc-*.json` |
| [03-daily-news.md](./03-daily-news.md) | Daily news briefing (bilingual) | 🗂 Others | `data/chatgpt/news/news-gpt-*.json` |
| [04-worldcup-briefing.md](./04-worldcup-briefing.md) | World Cup daily briefing | 🗂 Others | `data/chatgpt/news/worldcup-gpt-*.json` |
| [05-morning-brief.md](./05-morning-brief.md) | Personal morning brief (EN-only) | 🗂 Others | `data/chatgpt/brief/brief-gpt-*.json` |
| [06-speaking-source.md](./06-speaking-source.md) | Speaking Q&A practice sets | 🗣 Speaking | `data/{source}/speaking/*.json` |
| [10-listening-test.md](./10-listening-test.md) | DOL interactive Listening tests | 📝 Listening Test | `data/chatgpt/dol/listening/*/questions.json` |
| [11-reading-test.md](./11-reading-test.md) | DOL interactive Reading tests | 🧾 Reading Test | `data/chatgpt/dol/reading-test/*/questions.json` |

`{source}` = `claude-cowork` | `chatgpt` | `codex` | your agent folder name.

---

## Skeletons & templates (annotated JSON)

| File | Purpose |
|------|---------|
| [`data/templates/template-spec.json`](../data/templates/template-spec.json) | Machine-readable platform contract (JSON) |
| [`data/templates/lesson-template.json`](../data/templates/lesson-template.json) | Schema-1 IELTS lesson skeleton |
| [`data/templates/dynamic-template.json`](../data/templates/dynamic-template.json) | Schema-2 generic content skeleton |
| [`data/templates/bbc-lesson-template.json`](../data/templates/bbc-lesson-template.json) | BBC episode skeleton |

---

## Scheduler prompts (behaviour, not schema)

ChatGPT uses a **two-file pattern** — see [`prompts/chatgpt/schedulers/README.md`](../prompts/chatgpt/schedulers/README.md) (**MAX LIMIT:** schedulers = bootstrap only; all behavior in parent `*.md`):

| Role | Path |
|------|------|
| Task prompt (fetched every run) | `prompts/chatgpt/<task>.md` + `SHARED.md` |
| Scheduler baseline (owner copy-paste **once**) | `prompts/chatgpt/schedulers/<task>.scheduler.md` |

Claude Cowork IELTS hourly: [`prompts/claude/ielts-hourly.md`](../prompts/claude/ielts-hourly.md).

Specs define **what** to build; prompts define **how each scheduler runs**.

---

## New session bootstrap (copy into a fresh chat)

Paste this to start a new session with minimal tokens:

```
Project: IELTS Hourly Practice Tool
Tool root: docs/claude-cowork/ielts-hourly-practice-tool/
Read specs in order:
1. specs/00-platform.md
2. specs/<TASK>.md  (see specs/README.md table)
3. specs/08-agent-workflows.md if publishing
Pages: https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/specs/README.md?t=1
Repo: mtm0101/public-sites branch main
Do not ask clarifying questions — specs are authoritative.
```

Replace `<TASK>` with e.g. `01-ielts-hourly-lesson`, `02-bbc-6min`, `07-app-features`.

---

## Repo paths (Windows local)

```
C:\Users\USERNAME\Downloads\gpt-codex\public-sites\docs\claude-cowork\ielts-hourly-practice-tool\
```

Push script (repo root): `update-index-and-push.ps1` — runs `convert_lessons.py` + git push.

---

## Privacy (all public content)

- No personal names, emails, or usernames in JSON/HTML committed to GitHub.
- Morning briefs: roles not names; paraphrase subjects; sensitive items as counts only.

---

## When specs change

1. Edit the spec file; bump `Version:` header.
2. Bump `specs/INDEX.json` → `version`.
3. If schema/HTML contract changed, update matching skeleton in `data/templates/` and `template-spec.json`.
4. Push to `main`; wait ~1–2 min for GitHub Pages.
