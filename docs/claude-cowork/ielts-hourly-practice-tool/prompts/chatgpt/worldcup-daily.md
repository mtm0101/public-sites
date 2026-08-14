version: 4
scheduler-baseline: schedulers/worldcup-daily.scheduler.md

# World Cup Daily Briefing — ChatGPT Scheduled Task

**Read first:** [SHARED.md](./SHARED.md) (commit verification, **`main` only** — no PR mode). **This task overrides SHARED.md §Reads** — see §Read cascade (connector reads allowed when URL fetches fail).

Bilingual Men's 2026 FIFA World Cup daily briefing as **schema-2 JSON**. Cumulative knockout history (Round of 32 onward), balanced coverage, tables, breakout players, IELTS vocab.

---

## CRITICAL — Scheduled automation (read before mode selection)

This prompt is for **ChatGPT Scheduled Tasks** with the **GitHub connector** on `mtm0101/public-sites`.

| Run context | Required mode | Output in chat |
|-------------|---------------|----------------|
| **Scheduled task / automation** | **FULL** (or SKIP) | Short confirmation **only** |
| **Manual chat, no connector** | **CHAT-DELIVERY** | Full JSON in chat |

**Scheduled-run rules (mandatory):**

1. **Default mode is FULL.** Commit via GitHub connector to **`main`**.
2. **Do NOT disable the automation** or abort because GitHub Pages returned **safe-URL**, gateway, DNS, or timeout errors — use the **read cascade** (§Read cascade) and still commit.
3. **Do NOT choose CHAT-DELIVERY** because prompt/template Pages fetches failed — connector GET is the normal fallback.
4. **Do NOT choose CHAT-DELIVERY** when you "cannot write in this chat" — scheduled tasks write via the connector.
5. **Refusal is forbidden.** Every scheduled run ends with **FULL** or **SKIP** — not abort-with-no-commit.

Open with: `Mode: FULL | SKIP | CHAT-DELIVERY — <reason>`

**Repo root:** `mtm0101/public-sites` · branch **`main`**

**Pages base:** `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/`

Do **not** use the code sandbox for network reads.

---

## Read cascade (**overrides SHARED.md — connector allowed**)

For **each** repo file below, try **in order** until JSON/text parses. Fresh `?t=<unix_ts>` on URL steps. **Do not stop the run** when early steps fail — always try step 4 before CHAT-DELIVERY.

| Step | Channel | URL pattern |
|------|---------|-------------|
| 1 | Pages GET | `…/ielts-hourly-practice-tool/<repo-path>?t=<unix_ts>` |
| 2 | raw.githubusercontent.com | `https://raw.githubusercontent.com/mtm0101/public-sites/main/docs/claude-cowork/ielts-hourly-practice-tool/<repo-path>?t=<unix_ts>` |
| 3 | jsDelivr | `https://cdn.jsdelivr.net/gh/mtm0101/public-sites@main/docs/claude-cowork/ielts-hourly-practice-tool/<repo-path>` |
| 4 | **GitHub connector GET** | Repo `mtm0101/public-sites`, branch **`main`**, full repo path below |

**Step 4 is mandatory** when steps 1–3 all fail (safe-URL block, gateway, cache, DNS, timeout). This is the **normal** scheduled-task path when Pages is blocked — not an error state.

**This task prompt:** if Pages fetch of `prompts/chatgpt/worldcup-daily.md` or `SHARED.md` fails → read the same path via **connector GET** — do not abort.

**Connector GET — allowed paths:**

- `docs/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/worldcup-daily.md`
- `docs/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/SHARED.md`
- `docs/claude-cowork/ielts-hourly-practice-tool/data/templates/template-spec.json`
- `docs/claude-cowork/ielts-hourly-practice-tool/data/templates/dynamic-template.json`
- `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/news/worldcup-gpt-YYYY-MM-DD.json` (last 7 days; try `-1`, `-2` suffixes)
- `docs/claude-cowork/ielts-hourly-practice-tool/specs/04-worldcup-briefing.md`

**Connector GET — forbidden:** `manifest.json` (too large — never needed for this task).

Print `Reads: Pages | raw | jsDelivr | connector — <paths>` in confirmation.

---

## Contract (read every run)

Use §Read cascade for:

| Path | Purpose |
|------|---------|
| `data/templates/template-spec.json` | Authoritative contract |
| `data/templates/dynamic-template.json` | Annotated schema-2 skeleton |
| Last 7 days: `data/chatgpt/news/worldcup-gpt-YYYY-MM-DD.json` | Previous briefing memory (newest first; try suffixes) |

If templates are unreadable after the full cascade → use **§Embedded contract** below and still commit.

---

## Embedded contract (fallback when templates unreadable)

Use when template GETs fail after §Read cascade. The spec wins for shape; this block is enough to produce valid JSON.

**Top-level:** `schema: 2`, `id: "worldcup-gpt-YYYY-MM-DD"`, `type: "news"`, `source: "chatgpt"`, `category: "worldcup"`, `title`, `dateTime` (US Eastern ~07:00), `words[]`. **Do NOT set `topicNumber`.** No rogue top-level `results` / `briefing` without `sections[].html`.

**Every section MUST have non-empty `html`.** App renders `sections[].html` only.

| id | title | Content |
|----|-------|---------|
| `summary` | Overview | Tournament snapshot |
| `results` | Latest result(s) | Today's match(es) |
| `biggest-moments` | Biggest moments | 3 highlights |
| `implications` | Tournament implications | 3–4 bullets |
| `breakout-players` | Breakout players | 2–3 spotlights |
| `schedule` | Schedule & implications | Bracket/fixture **tables** + cumulative knockout table |
| `watch` | What to watch | Next matches |
| `vocab` | IELTS Vocabulary | 4–6 cards |
| `sources` | Sources & notes | Sources + disclaimer |

**HTML:** `<p class="en">` + `<p class="vn">` (one sentence per `.en`). Tables inside `html` as `<table>`. Match headers: `<h4>Quarterfinal · Team A vs Team B · 2-0</h4>`.

**Scope:** Round of 32 onward — **exclude group stage**. Verify scores via web search. Balanced coverage — no favorite-team bias.

**Vocab card pattern:**

```html
<div class="vocab"><div class="word">quarter-final</div><div class="ipa">/ˈkwɔːtə ˌfaɪnl/</div><p class="en">Definition.</p><p class="vn">Nghĩa tiếng Việt.</p></div>
```

---

## Previous-file memory

Extend cumulative knockout results from newest briefing found — **never remove** past knockout rows. Group stage excluded. No separate state file.

If no previous file found → rebuild knockout table from web search; note `History: rebuilt from web` in confirmation.

---

## JSON deliverable

**Path:** `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/news/worldcup-gpt-YYYY-MM-DD.json`

`-gpt-` required. US Eastern date. Suffix (`-1`, `-2`) if file exists on `main`.

```json
{
  "schema": 2,
  "id": "worldcup-gpt-2026-07-10",
  "type": "news",
  "source": "chatgpt",
  "category": "worldcup",
  "title": "2026 FIFA World Cup Daily Briefing — July 10, 2026",
  "dateTime": "2026-07-10T07:00:00",
  "words": ["…"],
  "sections": []
}
```

**Do NOT set `topicNumber`**. No rogue top-level shapes without full `sections[].html`.

---

## Write (final step, **`main` only**)

**Commit message:** `world cup briefing (chatgpt): <filename>`

One new `.json` on **`main`**. SHARED verification.

| Mode | Action |
|------|--------|
| **FULL** | New file |
| **SKIP** | Already on **`main`** for today |
| **CHAT-DELIVERY** | Full JSON in chat (manual / connector-write-failure only) |

---

## Delivery template

```
Mode: FULL | SKIP | CHAT-DELIVERY — <reason>
Reads: Pages | raw | jsDelivr | connector — <paths>
Headlines: …
History: extended | rebuilt from web
Path: docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/news/<file>
Manifest: deferred (owner pipeline)

Commit: <full_sha>
Commit link: https://github.com/mtm0101/public-sites/commit/<sha>
Branch: main (verified)
File(s): https://github.com/mtm0101/public-sites/blob/main/docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/news/<file>

OR:

Commit: none — no new commit on main this run
Reason: …
Main history: https://github.com/mtm0101/public-sites/commits/main
```

Do not print full JSON in FULL/SKIP mode.

**Forbidden end state:** `Commit: none` with reason "prompt reads failed" or "safe-URL blocked" on a scheduled run — use connector reads and commit, or CHAT-DELIVERY only if connector write also failed.

---

## Scheduler baseline (human — one-time bootstrap)

**Not fetched by the agent.** Frozen bootstrap: [`schedulers/worldcup-daily.scheduler.md`](./schedulers/worldcup-daily.scheduler.md) (connector + fetch URLs only). **All behavior lives in this file** (fetched every run with `?t=`).

- **Behavior changes** → edit **this file** only; bump `version:` above. **Do not** edit `schedulers/`.
- **Do not** tell the owner to re-paste after behavior changes ([MAX LIMIT](./schedulers/README.md#max-limit--what-may-change-in-schedulers)).
- **Re-paste scheduler** → only if bootstrap URL list or repo/branch changes.
