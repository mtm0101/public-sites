# Agent Workflows — How Each AI Publishes

**Spec id:** `agent-workflows` · **Version:** 1.0  
**Read with:** [00-platform.md](./00-platform.md)

---

## 1. Agent matrix

| Agent | Read specs | Write method | State files | Task prompt | Scheduler baseline |
|-------|------------|--------------|-------------|-------------|-------------------|
| **Claude Cowork** IELTS hourly | 01 | Local write + `scripts/convert_lessons.py` | `data/claude-cowork/state.json` | [`prompts/claude/ielts-hourly.md`](../prompts/claude/ielts-hourly.md) | — |
| **Claude Cowork** BBC HTML | 02 | HTML in `bbc-lessons/` → `convert_bbc_html.py` | — | repo root `CLAUDE.md` | — |
| **ChatGPT** IELTS hourly | 01 | GitHub connector → `main` | `data/chatgpt/state.json` | `prompts/chatgpt/ielts-hourly.md` | `schedulers/ielts-hourly.scheduler.md` |
| **ChatGPT** BBC 6 min | 02 | GitHub connector → `main` | `data/chatgpt/bbc/processed.json` + `upcoming.json` | `prompts/chatgpt/bbc-6min.md` | `schedulers/bbc-6min.scheduler.md` |
| **ChatGPT** Daily news | 03 | GitHub connector → `main` | — | `prompts/chatgpt/daily-news.md` | `schedulers/daily-news.scheduler.md` |
| **ChatGPT** World Cup | 04 | GitHub connector → `main` | previous file = memory | `prompts/chatgpt/worldcup-daily.md` | `schedulers/worldcup-daily.scheduler.md` |
| **ChatGPT** Morning brief | 05 | **Chat only — no GitHub connector, no commit** | — | `prompts/chatgpt/morning-brief.md` | `schedulers/morning-brief.scheduler.md` |
| **Cursor / Codex** | relevant spec | Local git commit | per spec | `AGENTS.md` → specs | — |

---

## 2. ChatGPT scheduled tasks

### Two-file pattern (mandatory)

| File | Purpose | Update trigger |
|------|---------|----------------|
| `prompts/chatgpt/<task>.md` | Full task instructions — **fetched every run** via Pages | Edit freely; bump `version:` |
| `prompts/chatgpt/schedulers/<task>.scheduler.md` | Frozen bootstrap (connector + fetch URLs) — **owner pastes once** | **Only** if URL list or repo/branch changes — **never** for behavior/queue/skip |
| `prompts/chatgpt/SHARED.md` | Shared commit rules — fetched, not pasted alone | Edit freely; bump `version:` |

Index: [`prompts/chatgpt/schedulers/README.md`](../prompts/chatgpt/schedulers/README.md)

### MAX LIMIT — schedulers folder

**Bootstrap only.** Each `*.scheduler.md` may contain: metadata table + COPY block (connector + fetch URLs). **Nothing else.**

| Change type | Edit | Re-paste ChatGPT task? |
|-------------|------|------------------------|
| Queue, skip, schema, delivery, privacy | `prompts/chatgpt/<task>.md` (+ bump `version:`) | **No** — push; next run fetches |
| Pages URL, repo/branch, fetch URL list | `schedulers/<task>.scheduler.md` (+ bump `baseline-version`) | **Yes — once** |

**Agents must not:** add behavior to schedulers; bump `baseline-version` for behavior; instruct re-paste after behavior-only changes.

### Fetch order (every automated run)

```
1. prompts/chatgpt/SHARED.md?t=<unix_ts>
2. prompts/chatgpt/<task>.md?t=<unix_ts>
3. specs/<task-spec>.md (when task prompt references it)
```

Pages base: `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/`

**Agents:** never merge scheduler baseline text into task prompts. Never add behavior rules to `schedulers/`. Never bump `baseline-version` for behavior changes. Never remove `?t=` cache bust.

### Commit rules ([SHARED.md](../prompts/chatgpt/SHARED.md))

- Branch **`main` only** — no PR mode
- Descriptive commit message: `ielts lesson (chatgpt): …`, `bbc 6min lesson (chatgpt): …`, etc.
- After commit, print:
  - `Commit link: https://github.com/mtm0101/public-sites/commit/<sha>`
  - `File(s): https://github.com/mtm0101/public-sites/blob/main/docs/…/<file>`
- If no commit this run: `Commit: none — reason: …`
- **Never** invent or reuse SHA from another run

### manifest.json

**Never** commit from ChatGPT agents. Owner pipeline runs `convert_lessons.py`.

---

## 3. Claude Cowork (local)

### IELTS hourly workflow

1. Read [`prompts/claude/ielts-hourly.md`](../prompts/claude/ielts-hourly.md) + spec 01 + templates
2. Read/update `data/claude-cowork/state.json`
3. Write lesson JSON to `data/claude-cowork/lessons/`
4. Run from repo root:

```powershell
powershell -File update-index-and-push.ps1
```

Script runs `scripts/convert_lessons.py`, commits, pushes.

### BBC HTML workflow

1. Generate HTML to `docs/claude-cowork/bbc-lessons/`
2. `python scripts/convert_bbc_html.py`
3. `python scripts/convert_lessons.py`
4. Commit + push

---

## 4. Local developer (Cursor, manual)

1. Read [`AGENTS.md`](../AGENTS.md) → pick spec
2. Implement content or app change
3. If new JSON: `python scripts/convert_lessons.py`
4. Commit to `main` (user request only for git)

---

## 5. Existence checks

Before creating a file, GET Pages URL:
- 404 → safe to create
- 200 → resolve per task:
  - **IELTS hourly (ChatGPT):** never SKIP — advance topic and/or use `HHMM` minute stamp (see `prompts/chatgpt/ielts-hourly.md` §Never-SKIP)
  - **Other tasks:** suffix filename (`-1`, `-2`) or SKIP if already published

Pages lags commits ~1–2 minutes.

---

## 6. Orphan repair pattern

Lesson JSON exists on GitHub but state not advanced:
- **Do not** duplicate lesson
- Commit **state only** (REPAIR mode)
- Re-read state immediately before commit (concurrent runs)

---

## 7. CHAT-DELIVERY fallback (ChatGPT manual chat only)

When GitHub connector unavailable:
- Still generate full content
- IELTS: section-split blocks (see `prompts/chatgpt/ielts-hourly.md`)
- Print paths + `Commit: none`
- **Forbidden:** refusing due to output size

---

## 8. New agent onboarding checklist

- [ ] Read `specs/README.md` + `00-platform.md`
- [ ] Pick catalog entry from `specs/INDEX.json`
- [ ] ChatGPT task? Use two-file pattern: edit `prompts/chatgpt/<task>.md`; scheduler baseline in `prompts/chatgpt/schedulers/`
- [ ] Use unique `-<agent>-` marker in filenames
- [ ] Write only under `data/<your-folder>/`
- [ ] Never touch manifest, index.html, other agents' folders
- [ ] Add spec file if introducing new content type

---

## 9. New session (minimal context)

Paste from [specs/README.md § New session bootstrap](./README.md#new-session-bootstrap-copy-into-a-fresh-chat).

This clears dependency on prior chat history and saves tokens.
