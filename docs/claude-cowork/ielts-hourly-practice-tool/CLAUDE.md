# IELTS Hourly Practice Tool

> **Stable common contract:** The vocabulary examples, IPA, Vietnamese formatting, audio, confidence, completion, filtering, canonical-state, and persistence rules in this file apply across the whole Study app: all current and future pages/views, all importers/converters, and every generated or newly added data file. Future Codex, Claude, ChatGPT, Cursor, or other AI work must preserve them by default. They may be changed only by an explicit user request to revise the permanent common contract.

A single-page study app for bilingual (EN/VI) IELTS practice lessons. Everything lives in this folder.

## Files

| File | Role |
|---|---|
| `index.html` | The entire app — the ONLY file to maintain. |
| `data/` | Content root: `claude-cowork/`, `chatgpt/`, `codex/`, `templates/`, `ipa/` |
| `manifest.json` | Lesson index — rebuilt by `scripts/convert_lessons.py` |
| `scripts/` | `convert_lessons.py`, `convert_bbc_html.py`, deprecated S3 scripts |
| `specs/` | Content contracts — start at `specs/README.md` or `AGENTS.md` |
| `prompts/` | Scheduler prompts: `chatgpt/` (task + `schedulers/` baselines) + `claude/` |
| `data/templates/` | JSON skeletons + `template-spec.json` (not indexed by app) |
| `README.md` | Human folder map |

## Lesson JSON schema (`schema: 1`)

```json
{
  "schema": 1,
  "id": "ielts-2026-07-05-1000-topic16-sports-hobbies-arts",   // filename stem, primary key
  "sourceFile": "….html",
  "title": "Sports, Hobbies, Arts & Entertainment",             // topic name
  "fullTitle": "…", "topicNumber": 16,
  "angle": "creative hobbies & well-being", "band": "7.5–8.0",
  "dateTime": "2026-07-05T10:00",                               // from filename
  "words": ["take up", "pastime", …],                           // vocab list, for search
  "sections": [ {"id": "vocab", "title": "Vocabulary", "html": "…raw inner HTML…"}, … ]
}
```

Section ids seen in practice: `vocab` or `vocab-a` + `vocab-b`, then `reading`, `listening`, `writing`, `speaking`, `strategy`. Section HTML is rendered as-is inside `index.html`; the app's CSS covers the union of class names used by all generator variants (`.en`, `.vi`/`.vn`, `.ipa`, `.vocab`/`.card`, `.word`/`.head`/`.hw`, `.key`/`.answerkey`/`.answer-key`, `.label`/`.tag`, `.q`, `.speaker`, …). If a future lesson introduces new class names, add styling under the `.lesson-content` rules in `index.html`.

Literal "Meaning:" / "Example:" markers (and VI "Nghĩa:" / "Ví dụ:") are **removed from the JSON files themselves** by `convert_lessons.py` (`normalize_lesson()` runs on every existing JSON each time the script executes — idempotent). At render time `cleanVocabSections()` in `index.html` is a safety net for un-normalized data and does the colour-coding: in vocab sections, the first `.en` line of each card is a definition (`--def`, teal) and subsequent `.en` lines are examples (`--ex`, violet). It runs **before** flag handlers are attached, so sentence-flag hashes are computed over the cleaned text — do not reorder. VI/IPA lines are indented (24px, 16px on mobile) relative to EN lines.

## Pronunciation audio (streamed, nothing stored locally)

## Mandatory vocabulary example policy

All AI agents and all Study app features must treat each vocabulary item as canonical across lesson, Words, Cards, and Dictionary views. Examples remain owned by their original JSON source and must not be duplicated into user-progress data.

Never accept, display, cache, or persist filler such as `The term “democracy” appeared in a discussion about people, family & relationships.`, or equivalent wording that merely says a term appeared/was used/came up in a discussion. Examples must show natural, meaningful use of the vocabulary.

Example resolution order is fixed: dictionary examples/quotations first; DOL Cambridge Reading and Listening; DOL Actual Test and Practice Test Plus/Test Plus; other DOL data; other local JSON; finally a genuinely contextual generated sentence. Enforce the rejection test both during import and at runtime, preserve `exampleOrigin` metadata, and keep confidence synchronized live by canonical vocabulary identity.

### IPA, Vietnamese, markup, and sounding requirements

- Preserve source IPA and use the existing canonical US/UK fields. Resolve IPA from local shards first and dictionary data only as fallback; never fabricate IPA. All views of one vocabulary item share the same resolved IPA. Sentence/example IPA belongs to the exact English sentence and accent and becomes invalid if that sentence changes.
- Pair every maintained English vocabulary meaning/example with Vietnamese. Preserve source Vietnamese when present; otherwise use the shared translation/cache layer without writing the generated translation back over original JSON. English is `.en`, new Vietnamese is `.vi`, IPA is `.ipa`, main meaning is `.main-meaning`, English example is `.ex`/`.exline`, and Vietnamese example is `.ex-vi`. Keep EN and VI adjacent, one sentence per paragraph. No literal Meaning/Example labels and no inline styles.
- The parent reader label is exactly **`Non-vocab sound`**. Off speaks only main vocabulary headwords. On speaks all visible eligible units in DOM order, including meanings, examples/translations, headings, and section sentences. Top-level reading must not skip section sentences.
- This control is the sole authoritative filter and synchronizes immediately across the page, sections, reader dock, and saved preferences. Do not retain a contradictory `main only` gate.
- Preserve shared audio controls at word, sentence, section, and page scope: US/UK accent, play/pause/resume, stop, previous/next, one-item mode, rate, gap, and active-line highlighting. Hidden examples do not sound. All views must use the shared queue, IPA, example, confidence, and canonical-vocabulary resolvers.

### Confidence, Complete, filters, and persistence requirements

- Normalize each vocabulary headword to one canonical review ID. Occurrence IDs exist only for source navigation. Confidence, review count, seen state, and completion are shared live across every occurrence and view; never duplicate records to synchronize them.
- Ratings are `0 / 25 / 50 / 75 / 100`; explicit 0 is data, not unrated. A rating change updates all mounted views and every total/progress badge immediately, then writes one canonical IndexedDB record.
- Complete/100% sets all eligible canonical children to 100%; invoking it when all are already 100% clears them to unrated. Scope it strictly and leave content, flags, bookmarks, examples, IPA, translations, and unrelated progress unchanged. Deduplicate repeated words in averages and completion totals.
- All filters combine with AND semantics and remain active together: source/L1, book/L2, band/L3, topic/L4, skill, lesson/test/passage, confidence, difficulty, seen, flagged, completion, and search. Sorting/shuffling changes order only. Counts equal the deduplicated rows shown; empty results retain controls and show an explicit empty state; Reset is the only general filter reset.
- Vocabulary detail pages put Seen above Confidence with `All`, `Seen`, `Unseen`, and `Unseen OR Confidence filter`. The first three retain normal AND semantics with Confidence; the named OR option alone evaluates `(unseen || passesCurrentConfidenceFilter)`. Persist both controls and refresh cards/counts immediately.
- Restore persisted filters defensively. Content reload must never write user-progress stores. Import/cloud merge keeps canonical IDs and newer-record-wins behavior. Source JSON remains immutable at runtime; user state lives in IndexedDB.
- Legacy-ID migrations write/verify the canonical record before removing obsolete duplicates and merge deterministically. Every new view must reuse shared canonical state/resolvers and be tested for duplicate headwords, cross-view live updates, persistence after reload, 0%, 100%-toggle clearing, combined filters, and empty states.

### Sub-navigation requirements

- Derive sub-navigation from rendered visible sections and stable IDs, preserving L1–L4/`level` hierarchy; never maintain a drifting hard-coded copy. Mark the active section accessibly and keep parent/child scope correct.
- Keep the sticky top TOC and fixed bottom previous/current/next controls synchronized with scrolling, programmatic jumps, filtering/collapse, async loading, and rerenders. Previous/next traverse only eligible visible sections and disable at boundaries.
- All routes begin `#/`; never use a plain `href="#section"`. Use `scrollToSec()` or the shared equivalent, preserve the lesson route/history, focus the destination appropriately, and honor reduced motion.
- Deep links from search, Words, Cards, Dictionary, bookmarks, filters, and duplicate vocabulary entries must retain occurrence metadata and open/highlight the correct source section. Preserve route/section scroll position through rerender and back/forward; missing targets fail gracefully.
- Recompute after visibility changes, prevent duplicate IDs, and share one ordered navigation model across desktop/mobile. Require keyboard/screen-reader support, adequate touch targets, non-obscuring fixed controls, and tests for nested levels, first/last boundaries, hidden sections, duplicate headings, deep links, rerenders, mobile, and back/forward.

- **Words** (🔊 UK / 🔊 US buttons on vocab cards and the Words view): streamed from Oxford Learner's Dictionaries MP3s. URL shape: `https://www.oxfordlearnersdictionaries.com/media/english/{uk|us}_pron/{c}/{ccc}/{ccccc}/{word}__{gb|us}_1.mp3` where the 1/3/5-char dirs come from the normalized word (lowercase, spaces/hyphens/apostrophes → `_`, parentheses and leading a/an/the/to stripped). Numbered entries use `{word}_1_{gb|us}_1.mp3` (single underscore — e.g. `take_up_1_gb_1.mp3`). `oxfordCandidates()` tries both shapes plus a singular form, then falls back to the browser's Web Speech API (`speechSynthesis`, en-GB/en-US).
- **Sentences** (🔊 on every `.en` line and in the Sentences view): Google Translate TTS (`translate.googleapis.com/translate_tts?client=gtx` then `translate.google.com/...client=tw-ob`), falling back to `speechSynthesis` for failures or texts > 190 chars.
- The `<meta name="referrer" content="no-referrer">` tag is REQUIRED — Google TTS rejects requests carrying a Referer header (media error code 4). Don't remove it.
- Sentence flagging is via the 📌 icon appended to each `.en` line (next to 🔊) — there is NO click-on-paragraph flagging. Each `.en`'s text is captured for hashing BEFORE the 📌/🔊 buttons are appended, so flag hashes never include the icon glyphs.
- **Word tap-to-pronounce**: clicking a word in English text ANYWHERE in the app (lesson content, titles, speaking question headers, review lists — everywhere except buttons/links, navigation rows/cards with their own click actions, and Vietnamese/IPA elements; `wordAtPoint` also rejects any word containing non-ASCII letters, so Vietnamese text never triggers) opens `#wordpop` — word + US IPA + **English definition** + **Vietnamese meaning** (word translation + translated definition) — and plays it via the Oxford cascade. **IPA sources = the shard files** — US: `data/ipa/<letter>.json` (125k words, Oxford-US notation, from `eng_to_ipa`'s CMU_dict via `transcribe.cmu_to_ipa`); UK: `data/ipa/uk/<letter>.json` (65k words, RP, from open-dict-data ipa-dict `en_UK.txt`, normalized: stress marks moved to syllable onset, `ɹ→r`, `ɐ→ə`). api.dictionaryapi.dev (Wiktionary) is only the fallback because its transcriptions do NOT match Oxford conventions (user-reported bug); its UK is used only when explicitly UK-tagged. English definition picks the part of speech with the MOST senses (Wiktionary's first sense is often obscure — e.g. "positive" led with a rare noun sense). The popup includes an "Oxford ↗" search link for the authoritative entry. The `ipa/` shard folder is excluded from the app's S3 scan AND from convert_lessons.py. Vietnamese comes from `translateVi()`: a flagged lesson word's saved `vn` wins; otherwise MyMemory (api.mymemory.translated.net — CORS-enabled, primary) with Google gtx as fallback (gtx has NO CORS header, so it only works where CORS is not enforced). Translations are cached in-memory AND persistently in the `meta` store under keys `tr:<text>` to conserve MyMemory's anonymous quota. Async fills are guarded by `pop.dataset.word` so a quick second tap can't paint stale content. Desktop: left-click = US, right-click = UK (contextmenu is preventDefault'ed only for mouse pointers and only when no text is selected). Mobile: double-tap = US, triple-tap = UK (tap counter with a 380 ms resolve timer; `touch-action: manipulation` on `.lesson-content` disables double-tap zoom). `.vn`/`.vi`/`.ipa` elements and buttons/links are excluded (`eligibleWordTarget`). Word extraction uses `caretRangeFromPoint`/`caretPositionFromPoint` (`wordAtPoint`).

Navigation notes: app routes all start with `#/` — `route()` ignores any other hash. Never use plain `href="#sec-…"` anchors (they used to bounce users to the dashboard); use `scrollToSec(id)`. The lesson page has a sticky top TOC and a fixed bottom section-nav bar (`#secnav`, prev/current/next section titles, driven by `CUR_LESSON` + a window scroll listener). Re-rendering the same lesson preserves scroll position (`keepY` in `renderLesson`).

## Adding a new lesson

1. If it's HTML in the old format: drop the file here and run `python convert_lessons.py` (converts it, rewrites `manifest.json` from all JSONs). Then optionally delete the HTML.
2. If generating JSON directly: write the lesson JSON following the schema above, then run `python convert_lessons.py` to regenerate the manifest (or hand-edit `manifest.json`, including a fresh md5 `hash` of the file bytes).
3. In the app, click **⟳ Reload data** — it fetches `manifest.json` and only the lesson files whose hash changed (each fetch has an 8.5 s timeout; a full cold load of all 48 finishes well under 10 s).

## User progress (never stored in these files)

All progress lives in the browser's **IndexedDB**, database `ielts-practice-tool` (version 2), stores:

- `lessons` — cached lesson JSON (refreshed by Reload data)
- `progress` — key `lessonId|sectionId` → confidence 0/25/50/75/100 per section (an explicit 0% button exists; unrated and rated-0 render the same). Speaking questions reuse this store with keys `sp-NN|qI`. The "✓ 100%" buttons (`markLesson100`/`markSpeaking100` → `setWhole100`) set every child section/question to 100% at once; clicking again when everything is 100% clears them all back to unrated.
- `words` / `sentences` — flagged items, key `lessonId|djb2hash(text)`, each with its own confidence. `lessonId` may be a speaking id (`sp-NN`); resolve display links with `srcInfo(id)`, never `lessonById` directly.
- `sessions` — study time, key `lessonId|YYYY-MM-DD`, seconds per lesson/speaking topic per day (feeds dashboard + calendar)
- `speaking` — cached speaking topics from `0.speaking.json`, key `sp-NN`
- `speakingEdits` — user-corrected Vietnamese translations, key `sp-NN|qI` (question) or `sp-NN|aI.J` (answer variant J of question I). Overrides still render on top of the source (`spVn()`), but the in-app ✎ editor was removed — translations are now maintained in `0.speaking.json` (`question_vi` / `vietnamese`) directly.
- `meta` — misc

Rules the app must keep honoring:
- **Reload data must never write to `progress`/`words`/`sentences`/`sessions`** — lesson data and user data are strictly separated.
- Flag/word/sentence ids are content-hashes of normalized text, so re-fetching identical lesson content keeps flags attached. Changing a sentence's wording in a lesson JSON orphans its flag (the flag stays in the list, still linked to the lesson).
- Export/Import (Data tab) dumps/restores **all** stores as one JSON — that is the backup/migration path.
- `navigator.storage.persist()` is requested at boot to protect against eviction.

## The contract every AI agent reads

**Start here:** [`AGENTS.md`](AGENTS.md) → [`specs/README.md`](specs/README.md) → task spec (e.g. [`specs/01-ielts-hourly-lesson.md`](specs/01-ielts-hourly-lesson.md)).

| Layer | File | Role |
|-------|------|------|
| Agent entry | [`AGENTS.md`](AGENTS.md) | First file any AI tool should open |
| Spec index | [`specs/README.md`](specs/README.md) + [`specs/INDEX.json`](specs/INDEX.json) | Human + machine catalog |
| Platform | [`specs/00-platform.md`](specs/00-platform.md) | Publishing, HTML rules, manifest |
| JSON contract | [`data/templates/template-spec.json`](data/templates/template-spec.json) | Machine-readable platform summary |

## Dynamic content (schema 2) — news, quizzes, tests, any study item from any AI service

Any `.json` with a non-empty `sections[]` array is a study item; `ielts-*` lessons are just one kind. Generic fields (see `dynamic-template.json` for the annotated skeleton): `type` (lesson/news/quiz/test/listening/… — free label, shown as chip + filter), `source` (claude-cowork/chatgpt/codex/… — free label), `category`, `dateTime` (optional — defaults to S3 LastModified), `sections[].level` (1–3; level>1 renders indented with a smaller heading and an indented nav link). `normalizeItem()` in index.html fills all defaults, so minimal files work. Every section gets confidence buttons and a 🔖 bookmark (store `bookmarks`, key `itemId|sectionId`, listed on the dashboard, synced in user-data). Section HTML uses the same class conventions as lessons, so 📌/🔊/⭐/word-tap all work automatically.

Files with the speaking shape (`items[]` → `questions[]`) from ANY source are merged into the Speaking section; ids from `0.speaking.json` stay `sp-NN`, other files get a filename-hash prefix so sources don't collide.

**Rogue schema auto-repair (worldcup briefings):** ChatGPT's World Cup task has repeatedly ignored the JSON contract and invented its own schema — top-level `results`/`biggestMoments`/`tables`/… with no `sections[]` at all, or the same fields nested one level under a `briefing` key with slightly different names (`resultsAndScoreboard` etc.) — which used to make the converter skip the file entirely (silent 100%-data-loss, only visible as a WARN line). `build_worldcup_sections()` in convert_lessons.py detects either shape (by the presence of `results` or `briefing.resultsAndScoreboard`) and synthesizes a full `sections[]` from every field present (headlines, results, biggest moments, implications, breakout players, schedule table, IELTS focus, sources) so 100% of the content renders. It is **idempotent and unconditional** — it runs on every convert pass regardless of whether `sections[]` already exists, and it force-sets `type`/`category` to `news`/`worldcup` (not `setdefault`) because these files carry invented type strings like `"worldcup_daily_briefing"` that must not leak into the app's type filter. If ChatGPT invents yet another field name, extend the key lists in `build_worldcup_sections` rather than special-casing a single file.

The local folder is the **claude-cowork source**: any number of files per hour/day/adhoc, any filename — `convert_lessons.py` indexes every `*.json` in the tool root AND recursively under `data/` (excluding manifest/state/user-data/0.speaking/templates) into `manifest.json` with folder-relative `file` paths; the source label defaults to the first folder under `data/`. The app fetches local speaking from `data/claude-cowork/speaking/0.speaking.json` (root fallback).

## S3 — user-data sync ONLY (architecture change 2026-07-09)

**S3 is no longer a content channel.** The app loads ALL study content (lessons, speaking, news, IPA shards) exclusively from the json files/folders next to index.html via the local `manifest.json`; `listS3Keys`/bucket scanning was removed from index.html, and `update-index-and-push.ps1` no longer syncs to the bucket (GitHub push only). The bucket now stores exactly ONE object the app touches: `user-data.json` — "☁ Save to S3" PUTs it (still requires the `x-amz-checksum-sha256` header) and every reload GETs + merges it (newer record wins). `upload-to-s3.ps1` is DEPRECATED — moved to [`scripts/upload-to-s3.ps1`](scripts/upload-to-s3.ps1). The old content objects on the bucket could not be deleted (anonymous DELETE is denied by policy + Object Lock) — they are harmless orphans the app never reads; the owner can purge them with credentials (`aws s3 rm --recursive`, subject to Object Lock retention). template-spec.json is at version 2 describing GitHub-based publishing (remote agents commit via the GitHub connector; local agents write files + run the converter + push). The `data/` local folder name is historical — it is simply the content folder.

## (historical) S3 cloud sync (`S3_BASE` in index.html)

Bucket: `https://t-do-not-delete-ihp-7xf29m4kq9vnb1zt8we5yu3hj6kf0fd4jh1sa9vr2mn.s3.amazonaws.com/`

- **Reload data** fetches the local folder's `manifest.json` AND **scans the entire bucket** with `listS3Keys()` (ListObjectsV2 XML, continuation-token paging, anonymous listing verified working). Every `.json` anywhere in the bucket is discovered — per-source folders like `claude-cowork/`, `chatgpt/`, `codex/` need no manifest; the folder name becomes the default `source`, the ETag doubles as the change-detection hash, and LastModified as the dateTime fallback. On id conflicts S3 wins. Fetched files are classified by shape (sections → study item, items+questions → speaking, else skipped). `user-data.json` from the bucket is merged into the user stores via `mergeUserData()` — per record, the newer `updatedAt`/`lastAt`/`addedAt` wins, so a cloud save acts as source of truth without clobbering newer local activity. Every S3 step is catch-and-fallback: an unreachable bucket degrades to local-only with a toast note.
- **☁ Save to S3** (nav + Data tab) uploads the whole IndexedDB dump as `user-data.json` via anonymous `PUT` with an `x-amz-checksum-sha256` header.
- **Status 2026-07-09 (working):** anonymous LIST, GET, and PUT all work against the bucket — the critical trick is that PUTs MUST carry `x-amz-checksum-sha256` (base64). `Content-MD5` alone is rejected with a SigV4 demand by the bucket's Object Lock; the sha256 checksum header satisfies it. DELETE is denied (Object Lock), so uploads are effectively append/overwrite-only. All 61 objects (folder markers + 55 json) were uploaded via `upload-to-s3.ps1`, which uploads ONLY the `data/` folder. **Remaining caveat:** the bucket has no CORS configuration; the preview browser ignores CORS so everything verified there, but a normal browser (Chrome, mobile) will block fetch/PUT until CORS is enabled (config example in `upload-to-s3.ps1`). S3 ETags are content-MD5s and converge with the app's contentHash after one reload.

## Lessons vs BBC vs Others split (`#/lessons` / `#/bbc` / `#/others`)

The unified item list is split across three tabs:

| Tab | Route | Filter |
|-----|-------|--------|
| 📚 Lessons | `#/lessons` | `isLessonLike()` — `topicNumber` truthy (hourly IELTS rotation, topics 1–17) |
| 🎧 BBC 6 Minutes | `#/bbc` | `isBbcLike()` — `format === "bbc-6min"`, `category` matches `/bbc/i`, or `id` matches `/^bbc-(gpt\|claude)-/` |
| 🗂 Others | `#/others` | Everything else (news, briefs, quizzes, …) |

BBC episodes sort by `episode.date` ascending in the list view. Lesson detail uses `#/lesson/:id` for all study items; BBC items get a custom episode header, `.lesson-content.bbc` styling, and prev/next navigation within the BBC subset only.

## BBC 6 Minute English

Dedicated section for bilingual BBC episode lessons. Full contract: [`specs/02-bbc-6min.md`](specs/02-bbc-6min.md). Skeleton: [`data/templates/bbc-lesson-template.json`](data/templates/bbc-lesson-template.json).

| File / folder | Role |
|---|---|
| `data/claude-cowork/bbc/bbc-claude-*.json` | Converted from HTML in `../bbc-lessons/` via [`convert_bbc_html.py`](convert_bbc_html.py) |
| `data/chatgpt/bbc/bbc-gpt-*.json` | ChatGPT scheduled task output |
| `data/chatgpt/bbc/processed.json` + `upcoming.json` | ChatGPT compact progress + rotation queue; **500** queued ahead — post-2021-12-09 forward through July 2026 first, then pre-June-2021 **newer-first** |
| [`specs/`](specs/README.md) | All content type specs — [`AGENTS.md`](AGENTS.md) for new AI sessions |
| [`prompts/chatgpt/`](prompts/chatgpt/README.md) | ChatGPT task prompts (fetched each run) |
| [`prompts/chatgpt/schedulers/`](prompts/chatgpt/schedulers/README.md) | ChatGPT one-time bootstrap (frozen — behavior in parent `*.md` only) |
| [`prompts/claude/ielts-hourly.md`](prompts/claude/ielts-hourly.md) | Claude Cowork IELTS hourly scheduler |

**JSON schema:** `format: "bbc-6min"`, `category: "bbc-6-minute-english"`, `topicNumber: 0`, top-level `episode` / `links` / `summary` / `titleVi`, and 9 BBC-native sections (`vocab`, `dialogue`, `speaking-1..3`, `patterns`, `writing`, `grammar`, `sources`). **Not** the IELTS hourly 6-section shape.

**Convert HTML → JSON:** `python scripts/convert_bbc_html.py [--force]` then `python scripts/convert_lessons.py`.

**UI reference:** `../bbc-lessons/bbc-6min-2021-10-21-what-makes-us-laugh.html`

## Global search (`#/search`)

Full-text, case-insensitive substring search over ALL content: every lesson section (HTML stripped to text), lesson titles/angles/word lists, and every speaking question + answer (EN and VN). The index (`buildSearchIndex`) is built lazily on first search and cached with a stamp of lesson/speaking counts + last fetchedAt, so a data reload invalidates it. Results show grouped rows with `<mark>`-highlighted snippets (max 2 per entry, 150-entry cap); clicking calls `jumpToResult` → navigates to the lesson/speaking page, scrolls to the section/question, finds the first element containing the query (selector includes `h2` — speaking questions live in the panel header) and flashes it (`.flash` animation).

## Flashcards (`#/cards`)

Deck built from flagged words and/or sentences (selectable), front side EN or VN (selectable), optional hide-100% filter, shuffle. Click/space flips, arrows navigate, confidence buttons on the card write to the words/sentences stores. `CF.order` is only rebuilt on deck-setting changes or shuffle, so rating a card keeps the position.

## Scheduled-agent prompts — the authoring playbook

The user runs a family of scheduled AI agents that publish content for this app. When asked to "generate a prompt for X schedule", follow this playbook (all of these prompts were authored in this session and follow the same skeleton).

**ChatGPT scheduler MAX LIMIT (mandatory):** All behavior lives in `prompts/chatgpt/<task>.md` (fetched every run). **`schedulers/` is bootstrap only** — connector + fetch URLs. Never edit schedulers for queue/skip/schema changes; never bump `baseline-version` or ask the owner to re-paste for behavior updates. See [`prompts/chatgpt/schedulers/README.md`](prompts/chatgpt/schedulers/README.md#max-limit--what-may-change-in-schedulers).

**Prompt-as-file pattern (Claude Cowork IELTS hourly):** the scheduler reads [`prompts/claude/ielts-hourly.md`](prompts/claude/ielts-hourly.md) (Pages: `…/prompts/claude/ielts-hourly.md`).

**Existing prompts (owned by the user, pasted into each scheduler):**
| Agent / cadence | Output key | type/category | State |
|---|---|---|---|
| Claude Cowork — IELTS hourly | local `data/claude-cowork/lessons/…` + `scripts/convert_lessons.py` + `update-index-and-push.ps1` | lesson / ielts-hourly | `data/claude-cowork/state.json` · prompt: [`prompts/claude/ielts-hourly.md`](prompts/claude/ielts-hourly.md) |
| ChatGPT — IELTS hourly | `data/chatgpt/lessons/ielts-gpt-…` | lesson / ielts-hourly | `data/chatgpt/state.json` · prompt: [`prompts/chatgpt/ielts-hourly.md`](prompts/chatgpt/ielts-hourly.md) |
| ChatGPT — World Cup daily 7:00 ET | `data/chatgpt/news/worldcup-gpt-YYYY-MM-DD.json` | news / worldcup | previous file = memory · prompt: [`prompts/chatgpt/worldcup-daily.md`](prompts/chatgpt/worldcup-daily.md) |
| ChatGPT — Daily news 7:30 ET | `data/chatgpt/news/news-gpt-YYYY-MM-DD.json` | news / daily-news | stateless · prompt: [`prompts/chatgpt/daily-news.md`](prompts/chatgpt/daily-news.md) |
| ChatGPT — BBC 6 Minute hourly | `data/chatgpt/bbc/bbc-gpt-<YYMMDD>-<slug>.json` | lesson / bbc-6-minute-english | `data/chatgpt/bbc/processed.json` + `upcoming.json` · prompt: [`prompts/chatgpt/bbc-6min.md`](prompts/chatgpt/bbc-6min.md) |
| ChatGPT — Morning brief 7:45 ET weekdays | **chat only** (no repo write) | brief / morning-brief | stateless; ENGLISH-ONLY · private · prompt: [`prompts/chatgpt/morning-brief.md`](prompts/chatgpt/morning-brief.md) |

**Shared skeleton for any NEW S3-only agent prompt (in this order):**
1. Role + "you work ONLY against the S3 bucket: no local folders, no GitHub, no manifest".
2. NETWORK PROTOCOL — critical since ChatGPT's task sandbox hit DNS failure ("Temporary failure in name resolution") on the long bucket subdomain. List three endpoints: virtual-hosted `https://<bucket>.s3.amazonaws.com` plus path-style `https://s3.amazonaws.com/<bucket>` and `https://s3.us-east-1.amazonaws.com/<bucket>`; try code-tool GET with retries, then the browsing tool (reads only); declare RUN MODE = FULL / READ-ONLY / OFFLINE; HONESTY RULES (never claim found/read/uploaded without the actual retrieved content or a verifying GET 200; open the final message with mode + exact error when degraded). MANUAL-UPLOAD OUTPUT RULE for degraded modes: full JSON in a code block + exact key (+ updated state as a second block), "no upload happened", never advance state without a verified upload.
3. CONTRACT: read `<endpoint>/templates/template-spec.json` (+ the relevant skeleton: lesson-template.json for schema-1 IELTS, dynamic-template.json for schema 2); "the spec wins over this prompt"; ALSO embed a self-sufficient contract summary in the prompt (bilingual p.en/p.vn rule, exact vocab-card markup, allowed classes, forbidden markers) so OFFLINE runs still produce conformant files.
4. STATE on the bucket in the agent's own subfolder as `…/state.json` (the app scanner excludes any `state.json`); write state only AFTER verified upload; add a deterministic fallback when state is unreadable (e.g. topic = ((dayOfYear_ET×24+hour_ET) mod 17)+1, arithmetic shown).
5. FILE NAMING: `<something>-gpt-…` marker (or per-agent marker) so ids never collide across sources; exists-check (GET/HEAD 200) before writing; suffix instead of overwrite.
6. UPLOAD: anonymous PUT with `x-amz-checksum-sha256` (base64 SHA-256 of exact bytes) + Content-Type — include the working Python urllib snippet; PUT lesson → verify GET → PUT state → verify. Never DELETE (denied anyway); never touch user-data.json, templates/, or other sources' folders.
7. VERIFY checklist + SHORT confirmation delivery (never print the whole content in chat in FULL mode).
8. For content shown on the PUBLIC bucket that derives from personal data (calendar/email), enforce hard privacy rules: roles not names, paraphrased subjects, sensitive items as counts only — in the file AND the chat confirmation.

**Content conventions recap for prompts:** schema-2 files need `type`/`source`/`category` labels (drive app filters); prose = one sentence per `p.en` (+ `p.vn` pair for bilingual content; briefs may be English-only); simple classless `<table>` allowed for results/fixtures; no inline styles (use bold `Incorrect:`/`Corrected:` labels instead of colours); a small level-2 vocab-card section is a nice add-on to news/briefs since it feeds the app's word/flashcard workflow.

## Serving

`fetch()` needs HTTP — GitHub Pages (this repo's `docs/` folder) or any static server works. Opened via `file://`, fetch fails and the app points the user to Data → "Load JSON files" (manual file picker fallback).
Local preview: `.claude/launch.json` config `ielts-tool` (npx serve on port 4323).

## Conventions

- Keep everything in the single `index.html` — no build step, no external JS.
- No personal names, emails, or usernames in any generated file.
- Final deliverable set: `index.html` + lesson `*.json` + `manifest.json` (+ this file and the converter).
