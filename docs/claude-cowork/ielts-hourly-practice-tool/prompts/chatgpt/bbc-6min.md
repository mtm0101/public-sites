version: 29
scheduler-baseline: schedulers/bbc-6min.scheduler.md

# BBC 6 Minute English — ChatGPT Scheduled Task

**Read first:** [SHARED.md](./SHARED.md) (commit verification, `main` only). **This task overrides SHARED.md §Reads** — see §1a (connector reads allowed for small repo files when URL fetches fail).

Each run produces **one** bilingual BBC lesson JSON for the **oldest unprocessed** episode, then advances queue state. Start **2021-06-10**, step **7 days**.

**Progress state (two permanently small files):**

| File | Size | Contents |
|------|------|----------|
| `processed.json` | <5 KB | authoritative `processed[]` episode codes (**YYMMDD**) |
| `upcoming.json` | ~5–10 KB | `queue[]` of **YYMMDD** strings (`queue[0]` = next) |

`state.json` is a frozen legacy metadata archive. **Scheduled runs must never read, parse, or write it.** Its size can exceed connector response limits; that must never block lesson generation.

**Cache guard:** if any previously fetched prompt, spec, or remembered instruction says to read or update `state.json`, it is obsolete and must be ignored. Version 29's `processed.json` workflow wins even when another document calls `state.json` the BBC state file.

---

## CRITICAL — Scheduled automation (read before mode selection)

This prompt is for **ChatGPT Scheduled Tasks** with the **GitHub connector** on `mtm0101/public-sites`.

| Run context | Required mode | Output in chat |
|-------------|---------------|----------------|
| **Scheduled task / automation** | **FULL** (or REPAIR / SKIP / SKIP-DUP) | Short confirmation **only** |
| **Manual chat, no connector** | **CHAT-DELIVERY** | Full JSON in chat |

**Scheduled-run rules (mandatory):**

1. **Default mode is FULL.** Commit via GitHub connector to **`main`**.
2. **Do NOT choose CHAT-DELIVERY** because the BBC Learning English page returned sparse HTML, could not be fetched, or title verification felt uncertain — use the PDF/programmes fallbacks below and still commit.
3. **Do NOT choose CHAT-DELIVERY** because you "cannot write in this chat" — scheduled tasks write via the connector.
4. **Do NOT choose CHAT-DELIVERY** when Pages/raw/jsDelivr return gateway, cache, or DNS errors — use **connector reads** for the compact files (§1a step 4) and still commit.
5. **Do NOT choose CHAT-DELIVERY** when `bbc-gpt-<YYMMDD>-*.json` for `queue[0]` already exists on `main` but is missing from `processed[]` — **REPAIR** (§1b).
6. **Refusal is forbidden.** Every scheduled run ends with **FULL**, **REPAIR**, **SKIP-DUP**, or **SKIP** — except a verified partial connector transaction after the required same-run retry.
7. **CHAT-DELIVERY is manual-chat / connector-write-failure only.**
8. If `queue` is empty → refill **500** episodes (§1e) and persist `upcoming.json`.
9. **Do not stall** narrating fetch failures (gateway errors, "Pages unreachable", curl attempts). Fall through §1a silently, commit, print short confirmation with `Reads: …` (§Delivery).
10. **Connector-native write (mandatory):** Generate the complete lesson JSON **in this run's memory**, then send its full UTF-8 text directly to the connector's single-file content commit action. Do **not** create, attach, upload, or ask the connector to import a local artifact. A 30–50 KB JSON lesson is normal and belongs in the connector text payload, never in the chat reply.
11. **No artifact-transfer excuse:** The connector accepting UTF-8 text is sufficient for this task. Never report that it "cannot ingest a generated local artifact", that an artifact is "too large to transfer", or that a repository write requires a local-file upload. Attempt the direct text commit once before considering connector-write failure.
12. **Use the connector capability that exists:** This connector exposes safe single-file content commits. It does **not** require or guarantee a multi-file atomic action, current tree SHA, blob creation, Git tree creation, or ref updates. Never choose CHAT-DELIVERY because a tree SHA is unavailable. Never attempt the low-level Git Data API. Complete the ordered same-run transaction in §Step 4 using up to three verified content commits.
13. **Compact state is mandatory:** read and update only `processed.json` + `upcoming.json`. Never fetch `state.json`, even as a fallback. A truncated or unavailable `state.json` is irrelevant and must never cause SKIP. If either compact file is genuinely unreadable after the complete cascade, end `SKIP — compact progress unavailable, retry next scheduled run` with no lesson write.
14. **`state-advance.json` is retired:** never read, create, update, or use it. The normal transaction is lesson → processed → queue in the same run.

Open with: `Mode: FULL | REPAIR | SKIP | SKIP-DUP | CHAT-DELIVERY — <reason>`

**YYMMDD helpers (mandatory — derive URLs/dates from compact queue):**

- `epFromQueue(yymmdd)` → `ep-<YYMMDD>`
- `yyyyFromYymmdd(yymmdd)` → `2000+YY` (or `1900+YY` when `YY ≥ 90`)
- `bbcUrl(yymmdd)` → `https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_<YYYY>/ep-<YYMMDD>`
- `isoDate(yymmdd)` → `YYYY-MM-DD`
- `queue[0]` target URL = `bbcUrl(queue[0])`, episode code = `epFromQueue(queue[0])`

**Progress guarantee (mandatory):** Every scheduled run must **complete exactly one queue action** before ending:

| Action | Result |
|--------|--------|
| **FULL** | New `bbc-gpt-*.json` committed + `processed.json` + `upcoming.json` advanced |
| **REPAIR / SKIP-DUP** | `processed.json` + `upcoming.json` advanced only (duplicate/orphan already on disk) |
| **SKIP** | `queue[0]` already correctly in `processed[]` and absent from queue — no commit |

**Forbidden end state:** `Commit: none` while `queue[0]` points at an `ep-<YYMMDD>` that already has a valid `bbc-gpt-<YYMMDD>-*.json` on `main` but is **missing from `processed[]`**. Use **REPAIR** — never CHAT-DELIVERY alone.

**REPAIR is exceptional, not the normal pipeline:** it is only for an orphan that already existed before this run, a verified cross-source duplicate, or a queue-only inconsistency. Do not publish a new lesson and defer its compact progress advance to a later REPAIR. If the current run generated the lesson and can read the compact files, it must complete all FULL commits in the same scheduled run.

**Never delete** any lesson JSON, HTML, manifest entry, or Claude source file. Repairs update compact progress only **except for a proven misassigned orphan**, which must be overwritten in place with the correctly generated lesson (§1c).

**Cross-source rule:** Before writing any `bbc-gpt-*.json`, check whether the same BBC episode (`ep-YYMMDD`) already exists in **any** Claude Cowork output:
- `data/claude-cowork/bbc/bbc-claude-<YYMMDD>-*.json` (converted JSON)
- `docs/claude-cowork/bbc-lessons/bbc-6min-YYYY-MM-DD-*.html` (HTML source)
- `docs/claude-cowork/bbc-lessons/bbc-6min-sent.json` (`sent` queue)

If covered → advance ChatGPT state only, **do not** duplicate the lesson.

---

## Contract (read every run)

**Repo root:** `mtm0101/public-sites` · branch **`main`**

Use the **read cascade** (§1a) for every required file below — URL steps first, **connector GET fallback** when browsing fails (common: Pages 502/gateway, raw timeout).

| Repo path (under `docs/claude-cowork/ielts-hourly-practice-tool/`) | Purpose |
|------|---------|
| `specs/02-bbc-6min.md` | Schema + HTML |
| `data/templates/bbc-lesson-template.json` | Skeleton |
| `data/chatgpt/bbc/processed.json` | Compact authoritative processed episode codes |
| `data/chatgpt/bbc/upcoming.json` | Compact queue (`queue[]`) |
| `manifest.json` | Duplicate scan — **optional**; prefer the §1b filename scan if unreadable |
| `../bbc-lessons/bbc-6min-sent.json` | Claude HTML queue — optional |

**URL mirrors** (append `?t=<unix_ts>`): Pages `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/…` · raw `https://raw.githubusercontent.com/mtm0101/public-sites/main/docs/claude-cowork/ielts-hourly-practice-tool/…` · jsDelivr `https://cdn.jsdelivr.net/gh/mtm0101/public-sites@main/docs/claude-cowork/ielts-hourly-practice-tool/…`

**This task prompt:** if Pages fetch of `prompts/chatgpt/bbc-6min.md` fails, read the same path via **connector** — do not abort.

Spec wins over this file.

---

## Paths (`mtm0101/public-sites`, branch **`main`**)

| Role | Path |
|------|------|
| Lesson (ChatGPT) | `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/bbc/bbc-gpt-<YYMMDD>-<slug>.json` |
| Lesson JSON (Claude — read only) | `docs/claude-cowork/ielts-hourly-practice-tool/data/claude-cowork/bbc/bbc-claude-<YYMMDD>-<slug>.json` |
| Lesson HTML (Claude — read only) | `docs/claude-cowork/bbc-lessons/bbc-6min-YYYY-MM-DD-<slug>.html` |
| Claude HTML state (read only) | `docs/claude-cowork/bbc-lessons/bbc-6min-sent.json` |
| Progress (ChatGPT) | `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/bbc/processed.json` |
| Queue (ChatGPT) | `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/bbc/upcoming.json` |

`-gpt-` required on ChatGPT files. Never edit `state.json`, `state-advance.json`, `manifest.json`, `bbc-6min-sent.json`, or Claude BBC/HTML files. Existing ChatGPT lesson JSON is read-only **except for a proven misassigned orphan** (§1c).

---

## Step 1 — Compact progress + duplicate scan + mode

### 1a. Read the two authoritative compact files

Read `processed.json` and `upcoming.json` through this cascade, continuing until the body parses and validates:

1. Pages GET with `?t=<unix_ts>`
2. raw.githubusercontent.com with `?t=<unix_ts>`
3. jsDelivr
4. **GitHub connector GET** on `main` (mandatory after URL failures)

Allowed connector paths are `processed.json`, `upcoming.json`, the current single lesson JSON when repairing, this prompt, SHARED, spec, and template. `manifest.json` is optional.

Validation:

- `processed.json`: `schema: 1`; `processed` is a unique array of six-digit `YYMMDD` strings.
- `upcoming.json`: `schema: 1`; `queue` is an array of six-digit `YYMMDD` strings.
- Both complete compact files are safely below connector truncation limits.

**Hard prohibition:** do not GET, parse, update, or use `state.json` or `state-advance.json`. They are legacy archives, not task inputs. Never report their truncation or unavailability as a reason to SKIP, disable the automation, or defer work.

If `processed.json` is unexpectedly missing, rebuild it once from episode codes in existing `bbc-gpt-<YYMMDD>-*.json` filenames plus codes before `queue[0]`, commit it, re-read it, and continue. Do not recover from `state.json`.

### 1b. Filename duplicate and orphan scan

Use the connector to list/search filenames without downloading the full manifest:

1. `data/chatgpt/bbc/bbc-gpt-<YYMMDD>-*.json`
2. `data/claude-cowork/bbc/bbc-claude-<YYMMDD>-*.json`
3. optionally `docs/claude-cowork/bbc-lessons/bbc-6min-YYYY-MM-DD-*.html`

An **orphan** is a ChatGPT lesson filename whose code is absent from `processed[]`. For the target orphan, connector-GET that one lesson and verify its `episodeDate`, `links.bbc`, title, and episode content against the BBC source.

### 1c. Pick exactly one queue action

Let `YYMMDD = queue[0]`, `EP = epFromQueue(YYMMDD)`.

| Condition | Mode and action |
|---|---|
| Valid ChatGPT lesson exists, code absent from `processed[]` | **REPAIR**: add code to processed, remove code from queue; no new lesson |
| Existing ChatGPT lesson is misassigned | **FULL correction**: overwrite it with correct content, then advance compact files |
| Claude JSON/HTML covers the code | **SKIP-DUP**: add code to processed, remove code from queue |
| Code is already in `processed[]` but remains in queue | **REPAIR**: remove it from queue only |
| Code is not processed and no duplicate exists | **FULL**: generate lesson, add code to processed, remove code from queue |
| Code is processed and absent from queue | **SKIP**: already current |

A filename date is not enough to validate a lesson. Misassigned content must be corrected in place; never advance the code while retaining content for a different episode.

**Same-run rule:** perform one action only. A newly written lesson must have its compact progress and queue commits completed in the same run; do not intentionally leave it for a later REPAIR.

### 1d. Prepare compact updates

Immediately before each compact-file commit, re-read that file from `main` and reapply only the idempotent target edit:

- `processed.json`: add `YYMMDD` once, preserving all other codes; sort ascending; pretty-print with two-space indentation and trailing newline.
- `upcoming.json`: remove `YYMMDD` wherever present, preserving the order and all unrelated concurrent changes; pretty-print with two-space indentation and trailing newline.

No title, URL, timestamp, or filename metadata belongs in `processed.json`; this invariant keeps the file permanently small. Historical metadata remains in the lesson JSON files and frozen legacy `state.json`.

### 1e. Refill queue when empty

Write `upcoming.json` only with 500 unprocessed weekly codes. Order: post-2021-12-09 forward through 2026-07-31 ascending, then pre-2021-06-10 newer-first. Exclude codes found in `processed[]`, ChatGPT lesson filenames, or Claude JSON/HTML filenames.

### 1f. Concurrency and failure

Every write is idempotent. Re-read the fresh base before compact-file writes, retry a failed step once, and verify final state. Never request a tree SHA or multi-file atomic action. If a partial transaction remains after retry, report successful SHA(s) and the exact unfinished compact path; the next run repairs it through the orphan gate. Never disable the recurring automation.

---

## Step 2 — Content
**Only if Step 1 did not SKIP / SKIP-DUP / REPAIR.**

BBC Learning English pages are often blocked or return minimal HTML in browsing tools. **Sparse BBC HTML is not a failure.** Try **in order**:

1. **BBC PDF transcript (preferred — authoritative title + vocab + quiz):**  
   `http://downloads.bbc.co.uk/learningenglish/features/6min/<YYMMDD>_6min_english_*.pdf`  
   Web search: `site:downloads.bbc.co.uk <YYMMDD> 6min english`
2. **BBC Radio programmes page** — search `6 Minute English` + episode date; title is in the page heading.
3. **BBC Learning English URL** — `https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_<YYYY>/ep-<YYMMDD>` (title often in `<title>` even when body is empty).
4. **Web search:** `BBC 6 Minute English ep-<YYMMDD> transcript`
5. docplayer.net, studocu.com, afarinesh.org (transcript mirrors)

**Title lock (FULL only):** for **new** lesson JSON, `title` / `episode.title` **must** match the BBC PDF or programmes page for that **`ep-<YYMMDD>`**. Never reuse content from a different episode date. **REPAIR / SKIP-DUP never re-fetch BBC for title** — use existing file or `upcoming[].title`.

**Title when `upcoming[].title` is null:** derive from (in order): BBC PDF filename via web search `site:downloads.bbc.co.uk <YYMMDD> 6min english`; BBC programmes search; episode `<title>` tag on the Learning English URL. A verified PDF URL (`http://downloads.bbc.co.uk/learningenglish/features/6min/<YYMMDD>_6min_english_*.pdf`) counts as title verification even when the PDF body is not fully readable.

Collect: title, date, summary (3–5 sentences), ≥6 vocab with IPA, quiz Q+A, role labels (no personal names in **labels** — speaker-name fields use Presenter / Co-presenter / Guest expert only).

**Dialogue source — try original transcript first:**

1. **Primary:** BBC PDF transcript (step 1 above) — extract the **full conversation** text.
2. **Secondary:** full transcript on the BBC episode page, BBC Sounds programme notes, or a verified mirror (studocu/docplayer) that reproduces the **complete** episode script.
3. Set `dialogueMode`: **`original`** only if you obtained ≥90% of spoken sentences from an official or verified full-transcript mirror **and can count the source sentences**; else **`paraphrase`**. A title page, audio description, excerpt, vocabulary list, or partial transcript never qualifies as `original`.
4. Record `transcriptSourceSentenceCount` and `dialogueRenderedSentenceCount` as top-level integers for every new lesson. For `original`, they must be equal after the same sentence-splitting rule is applied; commit is forbidden when they differ.

Only if no full transcript is available after steps 1–5 → use **`paraphrase`** mode (reconstruct from title, vocab, quiz, and partial snippets). Exhaust the PDF, BBC page/programmes, and two independent transcript-mirror searches before choosing this fallback; do not paraphrase merely because the first BBC fetch is sparse.

If steps 1–4 yield a verified title + enough material → proceed to Step 3. **Do not abort** because step 3 alone failed.

---

## Step 3 — JSON (`format: "bbc-6min"`)

9 sections: `vocab`, `dialogue`, `speaking-1`, `speaking-2`, `speaking-3`, `patterns`, `writing`, `grammar`, `sources`.  
`<p class="en">` + `<p class="vi">`. Extra sections (e.g. duplicate `summary`) are a **warning only** — do not overwrite existing JSON.

**Vietnamese completeness:** Generate a faithful Vietnamese sibling for every visible English sentence, heading, definition, example, IELTS answer, disclaimer, and dialogue line. The normal required shape is immediately adjacent `<p class="en">English sentence.</p><p class="vi">Vietnamese translation.</p>`. Never omit Vietnamese merely to shorten the file.

**Client fallback marker (rare):** Only when a translation genuinely cannot be supplied at generation time, put an **empty adjacent marker** after the English item: `<p class="vi" data-auto-vi="1"></p>`. The app detects this marker and fills it client-side with its cached EN→VI translator; it is a visible fallback, not a substitute for generated translations. Do not use `TODO`, `[translate]`, English placeholder text, or the marker for dialogue lines when a translation can be produced.

**Top-level fields (dialogue):**

- **`dialogueMode` (required):** `"original"` or `"paraphrase"` — must match how the dialogue EN lines were produced.
- **`sections[id=dialogue].title` (required):** must be **`Bilingual Dialogue`** when `dialogueMode` is `"original"`, or **`Bilingual Study Dialogue`** when `"paraphrase"`.

**Top-level `links` (required):**

```json
"links": {
  "bbc": "https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_<YYYY>/ep-<YYMMDD>",
  "transcript": "http://downloads.bbc.co.uk/learningenglish/features/6min/<YYMMDD>_6min_english_<slug>.pdf",
  "sounds": "https://www.bbc.co.uk/sounds/…",
  "spotify": "https://open.spotify.com/search/…"
}
```

- **`links.transcript` (required):** exact URL of the original episode transcript — **BBC PDF preferred** (`downloads.bbc.co.uk/…/*.pdf`). If no PDF, use the BBC lesson page URL or verified mirror where the **full** transcript text lives. The app shows this as **↗ Original transcript (PDF)** or **↗ Original transcript** in the lesson header.
- Also repeat the same URL in the dialogue disclaimer:  
  `<a class="ext-link" href="…" target="_blank" rel="noopener">↗ View original transcript</a>`

### Dialogue (`id: dialogue`) — CRITICAL (full length, sentence-by-sentence)

Section **`title`** = **`Bilingual Dialogue`** (`dialogueMode: "original"`) or **`Bilingual Study Dialogue`** (`dialogueMode: "paraphrase"`). The app also derives the title from `dialogueMode` when rendering.

The dialogue body is **not a summary**. It must cover the **entire** episode conversation.

**Two modes — use `original` whenever possible:**

| Mode | When | English lines | Vietnamese |
|------|------|---------------|------------|
| **`original`** | Full BBC PDF or verified full transcript obtained | **Use the transcript’s English sentences as written** (one `<p class="en">` per source sentence; minor punctuation normalisation only) | Accurate `<p class="vi">` translation of each sentence |
| **`paraphrase`** | No full transcript after all Step 2 attempts | One paraphrased `<p class="en">` per inferred sentence — closest meaning, different wording | Matching `<p class="vi">` |

**Workflow (mandatory before writing dialogue HTML):**

1. Extract **every spoken sentence** from the best available source (Presenter, co-presenter, guest clips, quiz setup, quiz answer).
2. **Count them** — call this `N`. Typical 6 Minute English ≈ **60–120 sentences**.
3. Output **exactly `N`** EN + VI pairs — **do not merge** sentences, **do not skip**, **do not shorten** to highlights. `original` dialogue must normally contain at least 50 spoken EN+VI pairs; below 50 requires an explicit verified source count explaining why the episode is shorter.
4. Group consecutive same-speaker sentences into one `.dialogue-turn`; guest clips → `.dialogue-turn.guest`.
5. Bold episode vocabulary with `<strong>` in EN lines.
6. **`speaker-name` labels:** Presenter / Co-presenter / Guest expert only (no personal names in labels; spoken lines may keep names that appear in the original transcript).
7. After the last conversation sentence, add **one** `.dialogue-turn.recap` (vocab recap + quiz Q&A).

**Disclaimer by mode:**

- **`original`:**  
  EN: *This dialogue follows the official BBC episode transcript with Vietnamese translation for study.*  
  VI: *Hội thoại này theo bản ghi chính thức của tập BBC, kèm bản dịch tiếng Việt phục vụ học tập.*  
  Then on the next lines, include the transcript link (same URL as `links.transcript`):  
  `<p class="en"><a class="ext-link" href="…" target="_blank" rel="noopener">↗ View original transcript (PDF)</a></p>`  
  `<p class="vi">↗ Xem bản ghi gốc (PDF)</p>` (or without “PDF” if not a PDF)
- **`paraphrase`:**  
  EN: *This is a paraphrased learning version; the original BBC transcript was unavailable.*  
  VI: *Đây là bản diễn giải để học; không có bản ghi gốc đầy đủ của BBC.*  
  If any partial transcript URL exists, still include the same `ext-link` pair pointing at `links.transcript` or `links.bbc`.

**Self-check before commit (dialogue body, exclude disclaimer + recap):**

- Count `<p class="en">` → must be **≥ `N`** (≥ 50 for a standard episode; ≥ 90% of source sentence count).
- **`original` mode:** EN lines must match the transcript sentence-by-sentence (not summarised, not reworded), and dialogue EN/VI pair counts must be equal (excluding a deliberate link-only Vietnamese line).
- **`paraphrase` mode:** same count and order as reconstructed from available material; closest meaning.
- **Forbidden:** meta summaries (“In this episode we discuss…”); skipping quiz or guest segments.

**Hard quality gate:** If a purported `original` dialogue is a synopsis, has fewer than 50 spoken pairs without a source-count exception, lacks a speaker turn from the PDF, or its `dialogueRenderedSentenceCount` differs from `transcriptSourceSentenceCount`, downgrade it to `paraphrase` **before commit** and use the paraphrase disclaimer. Never label a short reconstruction as the official transcript.

Reference: `bbc-6min-2021-10-21-what-makes-us-laugh.html` — full-length dialogue with multiple sentence pairs per turn.

Before write: **re-check** manifest + `bbc-6min-sent.json` — if Claude JSON or HTML for `EP` appeared since Step 1, abort JSON write and follow §1d instead.

### IELTS subsections (`speaking-1` … `writing`) — CRITICAL (length + pattern format)

**Reference quality:** `data/claude-cowork/bbc/bbc-claude-211021-what-makes-us-laugh.json` (Claude Cowork). **Do not** produce one-sentence Speaking answers or pattern-only lines without examples (common GPT failure — see `bbc-gpt-220421-discoveries-of-the-deep-sea.json`).

Wrap each subsection in `.ielts-sub` → `.ielts-sub-header` (`.ielts-badge` + `.ielts-sub-title`) → `.ielts-sub-body`. Every English sentence → `<p class="en">`; every Vietnamese → `<p class="vi">`. Bold episode vocabulary with `<strong>`.

| Section | Minimum EN+VI pairs | Structure |
|---------|---------------------|-----------|
| **speaking-1** | **4 pairs** (after question) | One `.question-block` question + multi-sentence personal answer using episode vocab |
| **speaking-2** | **6 pairs** | Full cue card in `.question-block` (you should say: …) + long turn: opening → detail → who with → why → feeling |
| **speaking-3** | **5 pairs** | `.question-block` question + linear answer: main idea → cause/reason → example → result |
| **patterns** | **2 blocks**, each with formula + **2 example pairs** | See pattern HTML below |
| **writing** | **thesis pair + body paragraph (5–7 sentences each language)** | Question in `.question-block`; label thesis `<strong>Thesis:</strong>` and body `<strong>Model body paragraph:</strong>` |

**Forbidden (IELTS):** single-sentence model answers; Speaking Part 2 under 5 EN sentences; Writing body as one short sentence; patterns without a separate formula line or without worked examples.

#### Sentence Patterns (`id: patterns`) — mandatory HTML shape

Two `.pattern-block` items inside `.ielts-sub-body`. Each block **must** include:

1. `<p class="pattern-label">Pattern N — [short label, e.g. Highlighting contrast with "rather than"]</p>`
2. **Formula line** — bracket slot notation (same style as grammar `.structure-formula`), on its own line:  
   `<p class="en pattern-formula">[Main clause] + rather than + [contrasting clause/phrase]</p>`  
   Use `[…]` placeholders, `+` between slots, optional `(+ by + agent)` — **not** a full example sentence on this line.
3. **Example 1** (episode-themed): `<p class="en">…</p>` + `<p class="vi">…</p>` — bold the target phrase.
4. **Example 2** (general IELTS topic): another EN + VI pair.

```html
<div class="ielts-sub">
  <div class="ielts-sub-header">
    <span class="ielts-badge">Sentence Patterns</span>
    <span class="ielts-sub-title">Band 7–8 structures from this episode</span>
  </div>
  <div class="ielts-sub-body">
    <div class="pattern-block">
      <p class="pattern-label">Pattern 1 — Highlighting contrast with "rather than"</p>
      <p class="en pattern-formula">[Main clause] + rather than + [contrasting clause/phrase]</p>
      <p class="en">Most laughter arises from natural conversation <strong>rather than</strong> from jokes deliberately told to be funny.</p>
      <p class="vi">Hầu hết tiếng cười xuất phát từ cuộc trò chuyện tự nhiên <strong>hơn là</strong> từ những câu chuyện cười được kể cố ý.</p>
      <p class="en">Cities should invest in public spaces, <strong>rather than</strong> relying solely on entertainment industries.</p>
      <p class="vi">Các thành phố nên đầu tư vào không gian công cộng, <strong>hơn là</strong> chỉ dựa vào các ngành giải trí.</p>
    </div>
  </div>
</div>
```

**Pattern self-check:** exactly **2** elements with class `pattern-formula`; **≥4** example `<p class="en">` lines inside `.pattern-block` (excluding formula lines); each formula uses `[bracket]` slots.

#### Speaking / Writing self-check (count `<p class="en">` inside `.ielts-sub-body`, exclude `.question-block`)

- `speaking-1` ≥ **4** · `speaking-2` ≥ **6** · `speaking-3` ≥ **5**
- `writing` ≥ **6** (thesis EN + multi-sentence body EN)

---

## Step 4 — Write (final step, **`main` only**)

Commit message: `bbc 6min lesson (chatgpt): <filename>`

Allowed: new/corrected `bbc-gpt-*.json`; updates to `processed.json` and `upcoming.json`. Legacy state and pending files are forbidden.

### Connector-native ordered commit protocol (mandatory)

The connector accepts one UTF-8 file per content commit. A FULL run therefore completes this **same-run transaction in order**:

1. Prepare lesson JSON, updated `processed.json`, and updated `upcoming.json` in memory before the first write. Pretty-print with two-space indentation and trailing newlines.
2. Commit the complete lesson JSON. Capture and verify `lessonSha` on `main`.
3. Immediately re-read `processed.json` from `main`. If another run already added `YYMMDD`, keep it; otherwise add it once to the fresh base. Commit the complete compact file; capture and verify `progressSha`.
4. Immediately re-read `upcoming.json` from `main`. Remove `YYMMDD` only if still present; preserve every unrelated concurrent queue change. Commit the complete `upcoming.json`; capture and verify `queueSha`.
5. Re-read all three paths and verify: lesson exists and matches `EP`; `YYMMDD` is in `processed[]`; `YYMMDD` is absent from `queue[]`. Only then report `Mode: FULL`.

Do not stop after step 2 or 3. Do not touch either legacy state file. Do not request a Git tree SHA. If a later step fails, retry that step once from a freshly read base during the **same run**. If it still fails, report `Mode: CHAT-DELIVERY — partial connector transaction` with the successful SHA(s) and exact unfinished path so the next run's orphan gate repairs it; do not claim that the generated JSON was uncommitted when `lessonSha` exists.

REPAIR / SKIP-DUP uses the same fresh-base method: commit `processed.json`, then `upcoming.json`. Verify final repository state before reporting completion.

The connector receives full UTF-8 file contents directly. Do not paste the lesson JSON into chat. Apply SHARED.md verification to every SHA created this run.

---

## Delivery template

```
Mode: FULL | REPAIR | SKIP | SKIP-DUP | CHAT-DELIVERY — <reason>
Reads: pages | raw | jsdelivr | connector | mixed — <which sources succeeded for queue/contract>
Episode: [title] ([YYYY-MM-DD]) · ep-[YYMMDD]
JSON: bbc-gpt-<YYMMDD>-<slug>.json ([new | skipped — claude duplicate | already on main])
Claude JSON check: [none | bbc-claude-<YYMMDD>-<slug>.json]
Claude HTML check: [none | bbc-6min-YYYY-MM-DD-<slug>.html | in bbc-6min-sent.json]
Orphan scan: [none | ep-YYMMDD json on main, absent from processed — repaired | still stuck]
Progress: advanced | progress-only repair | deduped queue | already current
Queue remaining: [N] · queue[0]: [YYMMDD or empty] · ep-[YYMMDD]
Manifest: deferred (owner pipeline)

Commits: lesson <lessonSha> · progress <progressSha> · queue <queueSha> (omit non-applicable entries)
Commit links: https://github.com/mtm0101/public-sites/commit/<lessonSha> · https://github.com/mtm0101/public-sites/commit/<progressSha> · https://github.com/mtm0101/public-sites/commit/<queueSha>
Branch: main (verified)
File(s): https://github.com/mtm0101/public-sites/blob/main/docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/bbc/<file>[, …]

**Delivery integrity:** report every SHA created this run. Multiple SHAs are expected with this connector and are successful only when all final-state checks pass in the same run.

OR (no commit this run):

Commit: none — no new commit on main this run
Reason: <already on main | claude-cowork duplicate | bbc-lessons HTML duplicate | concurrent SKIP | CHAT-DELIVERY>
Main history: https://github.com/mtm0101/public-sites/commits/main
```

Do not print full lesson except CHAT-DELIVERY.

---

## Scheduler baseline (human — one-time bootstrap)

**Not fetched by the agent.** Frozen bootstrap: [`schedulers/bbc-6min.scheduler.md`](./schedulers/bbc-6min.scheduler.md) (connector + fetch URLs only). **All behavior lives in this file** (fetched every run with `?t=`).

- **Behavior changes** → edit **this file** only; bump `version:` above. **Do not** edit `schedulers/`.
- **Do not** tell the owner to re-paste after behavior changes ([MAX LIMIT](./schedulers/README.md#max-limit--what-may-change-in-schedulers)).
- **Re-paste scheduler** → only if bootstrap URL list or repo/branch changes.
