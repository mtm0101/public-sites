version: 5
scheduler-baseline: schedulers/ielts-hourly.scheduler.md

# IELTS Hourly Practice — ChatGPT Scheduled Task

**Read first:** [SHARED.md](./SHARED.md) (commit verification, **`main` only**).

Generate **one** hourly IELTS practice lesson JSON (schema 1) for band **7.5–8.0**, **one** topic from the 17-topic rotation.

---

## CRITICAL — Scheduled automation (read before mode selection)

This prompt is designed for **ChatGPT Scheduled Tasks** with the **GitHub connector** attached to `mtm0101/public-sites`.

| Run context | Required mode | Output in chat |
|-------------|---------------|----------------|
| **Scheduled task / automation** | **FULL** (or REPAIR) | Short confirmation **only** — never the full lesson JSON |
| **Manual chat, no connector** | **CHAT-DELIVERY** | Section-split blocks (below) |

**Scheduled-run rules (mandatory):**

1. **Default mode is FULL.** Attempt GitHub connector commit to **`main`** before anything else.
2. **Do NOT choose CHAT-DELIVERY** because you "cannot write in this chat" — scheduled tasks write via the connector, not chat paste.
3. **Output-size limits do not apply to FULL mode** — the lesson lives in the committed file, not in your reply.
4. **Refusal is forbidden.** Never end without generating the lesson (FULL commit) or delivering section-split blocks (CHAT-DELIVERY).
5. If the connector fails after one attempt, report the exact error, then fall back to **CHAT-DELIVERY section-split** — still generate everything.
6. **Never SKIP on scheduled runs** because a lesson for the current Vietnam hour/topic already exists on `main`. Always advance the topic rotation and commit a **new** lesson (see §Never-SKIP).

Open with: `Mode: FULL | REPAIR | CHAT-DELIVERY — <reason>`  
(`SKIP` is **not used** by this scheduled task.)

---

## Run modes

| Mode | When | Action |
|------|------|--------|
| **FULL** | Scheduled task (default) or connector available | Read → pick topic + filename → generate → **connector commit** lesson + state → verify per SHARED |
| **REPAIR** | Lesson on GitHub but `state.json` stale (orphan) | Re-read state; commit **only** state to **`main`** if still stale |
| **CHAT-DELIVERY** | Manual chat only, or connector failed | Section-split delivery (below); Commit: none |

**SKIP is forbidden** for this task on scheduled runs. SHARED.md §5 does **not** apply here — see §Never-SKIP.

---

## Architecture

| Channel | Rule |
|---------|------|
| **READS** | Web/browsing GET only (`?t=<unix_ts>`) — try fallbacks below |
| **WRITES** | GitHub connector commit to **`main`** as **last** step |
| **Forbidden** | S3/bucket, `manifest.json`, tool-root `state.json`, `claude-cowork/`, `codex/`, `templates/`, `ipa/`, `.html` |

**Pages base:** `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/`

Never use code sandbox for network. Never use connector for reads.

**manifest.json** — owner rebuilds via `convert_lessons.py`. Never commit manifest.

---

## Read at start (try ALL sources for state)

1. `…/data/templates/template-spec.json?t=<ts>`
2. `…/data/templates/lesson-template.json?t=<ts>`
3. **State** — try in order until valid JSON with `last_topic`:
   - `…/data/chatgpt/state.json?t=<ts>` (Pages)
   - `https://raw.githubusercontent.com/mtm0101/public-sites/main/docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/state.json?t=<ts>` (raw GitHub)

If state still unreadable → **mandatory arithmetic fallback** (never stop):

```
topic = ((dayOfYear_VN × 24 + hour_VN) mod 17) + 1
```

Show the arithmetic and Vietnam date/time used. For state output, set `last_topic` to the chosen topic and build `recent_history` from the generated lesson. Note: `State read: fallback arithmetic`.

---

## Paths (`mtm0101/public-sites`, branch **`main`**)

| Role | Path |
|------|------|
| Lesson (default) | `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/lessons/ielts-gpt-YYYY-MM-DD-HH00-topicNN-<slug>.json` |
| Lesson (hour collision) | `…/ielts-gpt-YYYY-MM-DD-HHMM-topicNN-<slug>.json` — use Vietnam **hour+minute** when `HH00` slot is taken |
| State | `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/state.json` |

`-gpt-` required. `id` = filename stem. `source`: `"chatgpt"`. `category`: `"ielts-hourly"`.  
**Time:** Vietnam (Asia/Ho_Chi_Minh) for date/time in filename and `dateTime`. Default stamp = current VN hour on the hour (`HH00`). Use `HHMM` only when §Filename selection requires disambiguation.

---

## Topic rotation

1 Environment · 2 Health · 3 Crime/law · 4 Housing/urban · 5 Education · 6 Travel · 7 Transport · 8 Media · 9 Work · 10 Technology · 11 Government · 12 Culture · 13 Economy · 14 Science · 15 Family/society · 16 Sports/arts · 17 Globalization

1. From state: `topic = last_topic + 1` (wrap 17→1). `last_topic: 0` → Topic **1**.
2. **Every scheduled run advances** — set `last_topic` to the topic you publish, even if an older lesson for the same calendar hour already exists.
3. Use `recent_history` (6 entries) to vary vocab, reading theme, writing prompt, speaking cue card.
4. If state unreadable: arithmetic fallback above — still **generate and commit**; do not SKIP.

Keep **6** most recent history entries. Append the new lesson's fingerprints; drop oldest beyond 6.

State shape:

```json
{
  "last_topic": 3,
  "updated": "2026-07-11T08:00:00+07:00",
  "recent_history": [{
    "topic": 3,
    "vocab_words": ["…10 headwords…"],
    "reading_theme": "…",
    "writing_prompt": "…",
    "speaking_cue_card": "…"
  }]
}
```

---

## Never-SKIP rule (scheduled runs — overrides SHARED.md §5)

**Forbidden SKIP reasons** (always generate instead):

| Situation | Wrong action | Correct action |
|-----------|--------------|----------------|
| Lesson for current VN `YYYY-MM-DD-HH00` already on `main` | SKIP — "already published" | Advance `topic`; generate next topic's lesson; commit |
| Same `topicNN` + hour file already exists | SKIP or stop | §Filename selection — bump topic and/or `HHMM` |
| `last_topic` already matches an existing lesson | SKIP | `topic = last_topic + 1`; generate fresh content |
| Re-run in same clock hour | SKIP as duplicate hour | New topic + new file; optional `HHMM` stamp |

**Only acceptable no-commit outcomes:** **CHAT-DELIVERY** (connector failed) or **concurrent REPAIR** (re-read state immediately before commit — another run already committed the **same** filename + advanced state in the last ~2 min; then Commit: none with reason `concurrent run — state already advanced`).

---

## Filename selection

Before generating content, pick a free filename on `main` (Pages GET with `?t=<ts>`; 404 = free, 200 = taken). Pages may lag ~1–2 min after a fresh commit.

**Algorithm (in order):**

1. `date` = Vietnam today `YYYY-MM-DD`; `time` = `HH00` (current VN hour, zero minutes).
2. `topic = last_topic + 1` (wrap 17→1).
3. Build slug from topic + angle; default path:  
   `ielts-gpt-{date}-{time}-topic{NN:02d}-{slug}.json`
4. Pages GET → **404** → use this `topic`, `time`, slug → generate (FULL).
5. Pages GET → **200** (collision):
   - **5a.** Increment `topic` (wrap) and rebuild slug; retry from step 3 (up to 17 attempts).
   - **5b.** If still 200 for `{date}-{HH00}-topic{NN}-…`: set `time` to current VN `HHMM` (e.g. `0130` at 01:30). Retry.
   - **5c.** If still 200: bump `time` by +30 minutes (`0200`, `0230`, …) until 404.
   - **5d.** Last resort: append `-2`, `-3` to slug (keep `HHMM`).
6. Set `dateTime` in JSON to match the chosen stamp: `YYYY-MM-DDTHH:MM+07:00` (use `:00` when `time` ends in `00`).

**Never** stop without a file because the default `HH00` path exists. **Never** SKIP.

---

## JSON deliverable (schema 1)

Mirror `lesson-template.json`. Six sections:

| id | title |
|----|-------|
| vocab | Vocabulary |
| reading | Reading |
| listening | Listening |
| writing | Writing (Task 2) |
| speaking | Speaking |
| strategy | Strategy Note |

### Content rules (spec wins)

- **One topic only.** Band 7.5–8.0; Vocab A 6.5–7.5, Vocab B 7.5–9.0.
- **Bilingual:** `<p class="en">` + `<p class="vn">` — one sentence per `.en`.
- **US IPA** on headword, definition, example for all **10** vocab cards.
- **Vocab:** 5+5 cards in `div.vocab` / `div.head`; no `Meaning:`/`Example:`/`Nghĩa:`/`Ví dụ:` markers.
- **Reading:** 220–320 words, 5 mixed questions, explanatory key.
- **Listening:** 200–300 words, bold speakers, ≥1 trap, 5 questions + key.
- **Writing:** Task 2 prompt, 260–310 word model, structure breakdown, 3 improvement notes.
- **Speaking:** coherence card; 2× Part 1; Part 2 cue + prep + flowing 190–260 word turn; 2× Part 3.
- **Strategy:** topic-specific coaching, bilingual.
- **HTML classes only:** `en`, `vn`, `ipa`, `note`, `vocab`, `head`, `card`, `key`, `label`, `band`, `prep`, `q` — no `<style>`/`<script>`/`<h2>`.

Top-level: `schema`, `id`, `sourceFile`, `title`, `fullTitle`, `topicNumber`, `angle`, `band`, `dateTime`, `contentUpdatedAt`, `type`, `source`, `category`, `words` (10), `sections` (6).

Set `contentUpdatedAt` to the current ISO 8601 timestamp with the Vietnam timezone when creating the file. If repairing an existing lesson, advance it only when the lesson content meaningfully changes; preserve it for a no-op, read, retry, or unchanged republish. This timestamp lets the app skip fetching unchanged files; the manifest hash remains the integrity fallback.

---

## Write protocol (FULL / REPAIR — final step)

**One connector commit** to **`main`**:

- FULL: new lesson JSON + updated `data/chatgpt/state.json`
- REPAIR: state only

**Commit message:** `ielts lesson (chatgpt): <filename>`

The connector receives the **full file contents** — you do not paste them in chat. Then **SHARED.md** verification.

---

## CHAT-DELIVERY — section-split (manual chat or connector failure ONLY)

**Never refuse due to size.** Do not output one giant minified JSON. Use **8 labeled blocks**:

| Block | Label | Content |
|-------|-------|---------|
| 1 | `LESSON_META` | JSON: all top-level fields **except** `sections` |
| 2 | `SECTION vocab` | JSON: `{"id":"vocab","title":"Vocabulary","html":"…"}` |
| 3 | `SECTION reading` | JSON section object |
| 4 | `SECTION listening` | JSON section object |
| 5 | `SECTION writing` | JSON section object |
| 6 | `SECTION speaking` | JSON section object |
| 7 | `SECTION strategy` | JSON section object |
| 8 | `STATE` | Updated `data/chatgpt/state.json` (minified) |

After block 8, print merge rule:

```
Merge: sections = [vocab, reading, listening, writing, speaking, strategy] in order → append to LESSON_META → save as <filename>
Paths: docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/lessons/<filename>
       docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/state.json
No GitHub commit occurred — paste merged file or re-run as scheduled task.
```

Self-check: each block valid JSON; 6 section ids; 10 headwords in `words`; EN/VN pairs throughout.

---

## Delivery template

```
Mode: FULL | REPAIR | CHAT-DELIVERY — <reason>
Topic: <N> — <name> [state read | fallback arithmetic]
Angle: <angle>
Time stamp: <HH00 or HHMM> (Vietnam)
Headwords: <10 comma-separated>
Reading theme: …
Writing prompt: …
Cue card: …
Lesson: docs/…/data/chatgpt/lessons/<file> [committed | section-split]
State: last_topic <N> [committed | section-split]
Manifest: deferred (owner pipeline)

Commit: <full_sha>
Commit link: https://github.com/mtm0101/public-sites/commit/<sha>
Branch: main (verified)
File(s): https://github.com/mtm0101/public-sites/blob/main/docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/lessons/<file>, …

OR:

Commit: none — no new commit on main this run
Reason: CHAT-DELIVERY (section-split blocks above) | concurrent run — state already advanced | connector error: …
Main history: https://github.com/mtm0101/public-sites/commits/main
```

**FULL/REPAIR:** never print full lesson or section blocks in chat.

Make all decisions autonomously. Do not ask clarifying questions.

---

## Scheduler baseline (human — one-time bootstrap)

**Not fetched by the agent.** Frozen bootstrap: [`schedulers/ielts-hourly.scheduler.md`](./schedulers/ielts-hourly.scheduler.md) (connector + fetch URLs only). **All behavior lives in this file** (fetched every run with `?t=`).

- **Behavior changes** → edit **this file** only; bump `version:` above. **Do not** edit `schedulers/`.
- **Do not** tell the owner to re-paste after behavior changes ([MAX LIMIT](./schedulers/README.md#max-limit--what-may-change-in-schedulers)).
- **Re-paste scheduler** → only if bootstrap URL list or repo/branch changes.
