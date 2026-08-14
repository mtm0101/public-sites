# BBC 6 Minute English — JSON Contract Specification

**Spec id:** `bbc-6min` · **Version:** 1.1 · **App tab:** `#/bbc`
**Index:** [specs/README.md](./README.md) · **Catalog:** [INDEX.json](./INDEX.json)

This document is the authoritative contract for any AI agent (ChatGPT, Claude Cowork, Codex) that publishes BBC 6 Minute English lessons into the IELTS Hourly Practice Tool.

---

## 1. Purpose

BBC 6 Minute English episodes are bilingual (English + Vietnamese) IELTS study lessons derived from BBC Learning English. Each episode becomes one JSON file consumed by the single-page app [`index.html`](index.html).

The app renders BBC items in a **dedicated navigation tab** (`🎧 BBC 6 Minutes`) between Speaking and Others. Items are discovered via [`../manifest.json`](../manifest.json), which is rebuilt by [`../scripts/convert_lessons.py`](../scripts/convert_lessons.py).

---

## 2. File Locations

| Role | Path |
|------|------|
| ChatGPT scheduled output | `data/chatgpt/bbc/bbc-gpt-<YYMMDD>-<slug>.json` |
| Claude HTML conversion output | `data/claude-cowork/bbc/bbc-claude-<YYMMDD>-<slug>.json` |
| Rotation state (ChatGPT) | `data/chatgpt/bbc/processed.json` + `data/chatgpt/bbc/upcoming.json` (`state.json` is legacy read-only compatibility data) |
| HTML source (Claude Cowork) | `../bbc-lessons/bbc-6min-YYYY-MM-DD-<slug>.html` |
| Annotated skeleton | [`../data/templates/bbc-lesson-template.json`](../data/templates/bbc-lesson-template.json) |
| HTML → JSON converter | [`../scripts/convert_bbc_html.py`](../scripts/convert_bbc_html.py) |

**Publish workflow (local agents):**

```powershell
cd C:\Users\USERNAME\Downloads\gpt-codex\public-sites\docs\claude-cowork\ielts-hourly-practice-tool
python scripts/convert_bbc_html.py          # if converting HTML
python scripts/convert_lessons.py           # rebuild manifest.json
```

Then commit and push (or run `update-index-and-push.ps1` from repo root).

---

## 3. JSON Schema

### 3.1 Top-level fields

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `schema` | yes | `2` | Study item schema version |
| `format` | yes | `"bbc-6min"` | Discriminator for BBC-native layout |
| `id` | yes | string | Filename stem; unique repo-wide |
| `type` | yes | `"lesson"` | Always `lesson` for BBC episodes |
| `source` | yes | string | `chatgpt`, `claude-cowork`, etc. |
| `category` | yes | `"bbc-6-minute-english"` | Used by app filter |
| `topicNumber` | yes | `0` | Not part of hourly IELTS rotation |
| `title` | yes | string | English episode title |
| `titleVi` | yes | string | Vietnamese title |
| `band` | recommended | string | e.g. `"7.0–8.0"` |
| `dateTime` | yes | string | ISO-like; use episode air date: `YYYY-MM-DDT00:00` |
| `episode` | yes | object | BBC episode metadata (see below) |
| `links` | yes | object | External URLs: `bbc`, `transcript`, `sounds`, `spotify` (see §3.4) |
| `dialogueMode` | yes | string | `"original"` (full BBC transcript used) or `"paraphrase"` (fallback) |
| `summary` | yes | object | `{ "en": string[], "vi": string[] }` — 2–4 paragraphs each |
| `words` | yes | string[] | 6–10 headwords from vocab section |
| `sections` | yes | array | 7–9 section objects (see §4) |

### 3.2 `episode` object

```json
{
  "id": "ep-211021",
  "date": "2021-10-21",
  "title": "What Makes Us Laugh?",
  "url": "https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_2021/ep-211021",
  "savedAt": "2026-07-01"
}
```

- `id`: BBC episode code matching URL `ep-<YYMMDD>`
- `date`: ISO date of original BBC broadcast
- `url`: Official BBC Learning English page
- `savedAt`: Date this lesson file was created (YYYY-MM-DD)

### 3.4 `links` object

```json
{
  "bbc": "https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_2021/ep-211021",
  "transcript": "http://downloads.bbc.co.uk/learningenglish/features/6min/211021_6min_english_what_makes_us_laugh.pdf",
  "sounds": "https://www.bbc.co.uk/sounds/…",
  "spotify": "https://open.spotify.com/search/…"
}
```

- **`transcript` (required):** exact URL of the original episode transcript — BBC PDF preferred; else BBC lesson page or verified mirror.
- The app shows **↗ Original transcript (PDF)** in the lesson header and injects **↗ View original transcript** inside the dialogue disclaimer when missing.

### 3.5 `dialogueMode` and section title

| `dialogueMode` | `sections[id=dialogue].title` | Meaning |
|----------------|----------------------------------|---------|
| `"original"` | **Bilingual Dialogue** | EN lines follow the official BBC transcript ( + VI translation ) |
| `"paraphrase"` | **Bilingual Study Dialogue** | EN lines paraphrased because no full transcript was available |

The app overrides the section heading from `dialogueMode` (or infers mode from disclaimer text in legacy files).

### 3.6 Section object

```json
{
  "id": "vocab",
  "title": "Vocabulary",
  "level": 1,
  "html": "…raw inner HTML…"
}
```

| `id` | `title` | `level` |
|------|---------|---------|
| `vocab` | Vocabulary | 1 |
| `dialogue` | **Bilingual Dialogue** or **Bilingual Study Dialogue** (see §3.5) | 1 |
| `speaking-1` | Speaking Part 1 | 2 |
| `speaking-2` | Speaking Part 2 | 2 |
| `speaking-3` | Speaking Part 3 | 2 |
| `patterns` | Sentence Patterns | 2 |
| `writing` | Writing Task 2 | 2 |
| `grammar` | Grammar Band 7–8 | 1 |
| `sources` | Sources & Disclaimer | 1 |

`level: 2` sections render indented with smaller headings in the app TOC.

---

## 4. HTML Conventions (inside `sections[].html`)

### 4.1 Bilingual rule

- **Every English sentence** → `<p class="en">…</p>`
- **Every Vietnamese sentence** → `<p class="vi">…</p>` (or `class="vn"`)
- One EN line immediately followed by its VI pair
- No literal markers: `Meaning:`, `Example:`, `Nghĩa:`, `Ví dụ:`

The app attaches 🔊 TTS and 📌 sentence flags to `.en` lines only.

### 4.2 Vocabulary section (`id: vocab`)

Each word is a `.vocab-card`:

```html
<div class="vocab-card">
  <div class="vocab-header">
    <span class="vocab-word">contagious</span>
    <span class="vocab-ipa">/kənˈteɪdʒəs/</span>
    <span class="vocab-vi-meaning vi">dễ lây lan</span>
  </div>
  <div class="vocab-row">
    <span class="vocab-label">Definition</span>
    <div class="vocab-content">
      <p class="en">Spreading very quickly from one person to another.</p>
      <p class="vi">Lây lan rất nhanh từ người này sang người khác.</p>
    </div>
  </div>
  <div class="vocab-row">
    <span class="vocab-label">Example</span>
    <div class="vocab-content">
      <p class="en">Laughter is <strong>contagious</strong>.</p>
      <p class="vi">Tiếng cười rất <strong>dễ lây lan</strong>.</p>
    </div>
  </div>
  <div class="vocab-row ielts-row">
    <span class="vocab-label">IELTS</span>
    <div class="vocab-content">
      <p class="en">In IELTS Speaking Part 2: "Her enthusiasm was <strong>contagious</strong>."</p>
      <p class="vi">Trong IELTS Speaking Part 2: "Sự nhiệt tình của cô ấy rất <strong>dễ lan truyền</strong>."</p>
    </div>
  </div>
</div>
```

Requirements per word (6–10 words):
- Word + IPA + VI meaning in header
- EN definition + VI definition
- EN example + VI example (bold key word with `<strong>`)
- IELTS usage note starting with "In IELTS Speaking…" or "In IELTS Writing…" + VI translation

### 4.3 Dialogue section (`id: dialogue`)

**Section title:** **`Bilingual Dialogue`** when `dialogueMode` is `"original"`; **`Bilingual Study Dialogue`** when `"paraphrase"`.

**Full length — not a summary.** Try the **original BBC transcript first**; paraphrase only when a full transcript cannot be obtained.

**Source priority for conversation text:**

1. BBC PDF transcript (`downloads.bbc.co.uk/learningenglish/features/6min/…`)
2. Full transcript on BBC Learning English episode page or official programme notes
3. Verified mirror with complete script (studocu, docplayer, etc.)
4. **Fallback only:** paraphrase from title, vocab, quiz, and partial snippets

**Two modes:**

| Mode | English (`p.en`) | When |
|------|------------------|------|
| **original** | Transcript sentences **as written** (one pair per source sentence) | Full transcript obtained (≥90% of sentences) |
| **paraphrase** | Closest-meaning rewrite (one pair per inferred sentence) | No full transcript after all sources tried |

Open with disclaimer matching the mode used:

```html
<!-- original mode -->
<div class="disclaimer">
  <p class="en">This dialogue follows the official BBC episode transcript with Vietnamese translation for study.</p>
  <p class="vi">Hội thoại này theo bản ghi chính thức của tập BBC, kèm bản dịch tiếng Việt phục vụ học tập.</p>
  <p class="en"><a class="ext-link" href="TRANSCRIPT_URL" target="_blank" rel="noopener">↗ View original transcript (PDF)</a></p>
  <p class="vi">↗ Xem bản ghi gốc (PDF)</p>
</div>

<!-- paraphrase mode (fallback) -->
<div class="disclaimer">
  <p class="en">This is a paraphrased learning version; the original BBC transcript was unavailable.</p>
  <p class="vi">Đây là bản diễn giải để học; không có bản ghi gốc đầy đủ của BBC.</p>
</div>
```

**Mandatory workflow:**

1. Extract every spoken sentence → count `N` (typical ≈ 60–120).
2. Output **exactly `N`** `<p class="en">` + `<p class="vi">` pairs — same order and speakers.
3. **Never merge** or **skip** sentences. **Never** use a short highlights dialogue.

Each turn (group consecutive sentences by same speaker):

```html
<div class="dialogue-turn">
  <div class="speaker-avatar neil">N</div>
  <div class="dialogue-body">
    <p class="speaker-name">Presenter</p>
    <p class="en">English sentence with <strong>key vocab</strong>.</p>
    <p class="vi">Câu tiếng Việt.</p>
    <p class="en">Next sentence from the same speaker.</p>
    <p class="vi">Câu tiếng Việt tương ứng.</p>
  </div>
</div>
```

- Guest turns: class `guest` on `.dialogue-turn`
- Recap: **one extra** `.dialogue-turn.recap` after all conversation sentences
- Bold episode vocabulary in EN lines
- **`speaker-name`:** role labels only (Presenter, Co-presenter, Guest expert)

**Quality gate:** `<p class="en">` count ≥ `N`, ≥ 50, ≥ 90% of source. In **original** mode, EN must match transcript (not summarised). In **paraphrase** mode, full sentence count from best available reconstruction.

Reference: `../bbc-lessons/bbc-6min-2021-10-21-what-makes-us-laugh.html`

### 4.4 IELTS subsections

Wrap each subsection in `.ielts-sub`:

```html
<div class="ielts-sub">
  <div class="ielts-sub-header">
    <span class="ielts-badge">Speaking Part 1</span>
    <span class="ielts-sub-title">Optional subtitle</span>
  </div>
  <div class="ielts-sub-body">
    <div class="question-block">Question: …</div>
    <p class="en">Model answer.</p>
    <p class="vi">Câu trả lời mẫu.</p>
  </div>
</div>
```

**Speaking Part 1:** one sample Q + **4–5 sentence** model answer (EN + VI pairs)

**Speaking Part 2:** cue card in `.question-block` + **6–8 sentence** long turn (EN + VI)

**Speaking Part 3:** linear answer structure (main idea → cause → example → result) — **minimum 5 EN + VI pairs**

**Patterns:** two `.pattern-block` items. Each block **must** include:
1. `.pattern-label` — `Pattern N — [short description]`
2. **Formula line:** `<p class="en pattern-formula">[slot] + connector + [slot] (+ optional)</p>` — bracket slot notation like grammar `.structure-formula` (e.g. `[Main clause] + rather than + [contrasting clause/phrase]`), **not** a full example sentence
3. **Two worked examples:** episode-themed EN + VI pair, then general IELTS EN + VI pair (bold target phrase)

**Writing Task 2:** full essay question + thesis (EN + VI) + **5–7 sentence** model body paragraph (EN + VI), labelled `<strong>Thesis:</strong>` and `<strong>Model body paragraph:</strong>`

Example pattern block:

```html
<div class="pattern-block">
  <p class="pattern-label">Pattern 1 — Highlighting contrast with "rather than"</p>
  <p class="en pattern-formula">[Main clause] + rather than + [contrasting clause/phrase]</p>
  <p class="en">Most laughter arises from natural conversation <strong>rather than</strong> from jokes.</p>
  <p class="vi">Hầu hết tiếng cười xuất phát từ cuộc trò chuyện tự nhiên <strong>hơn là</strong> từ những câu chuyện cười.</p>
  <p class="en">Cities should invest in public spaces, <strong>rather than</strong> relying solely on entertainment.</p>
  <p class="vi">Các thành phố nên đầu tư vào không gian công cộng, <strong>hơn là</strong> chỉ dựa vào giải trí.</p>
</div>
```

Reference: `data/claude-cowork/bbc/bbc-claude-211021-what-makes-us-laugh.json`

### 4.5 Grammar section (`id: grammar`)

Four `.grammar-card` blocks. Each includes:

1. Grammar name + structure pattern (`.structure-formula`)
2. Explanation EN + VI
3. Main example EN + VI
4. Speaking example EN + VI
5. Writing example EN + VI
6. Incorrect sentence with `<strong>Incorrect:</strong>` label (no inline red CSS)
7. Corrected sentence with `<strong>Corrected:</strong>` label (no inline green CSS)
8. VI error explanation

### 4.6 Sources section (`id: sources`)

```html
<p class="en">Official sources: BBC Learning English … This lesson uses a paraphrased study dialogue for personal IELTS learning only.</p>
<p class="vi">Nguồn chính thức: BBC Learning English …</p>
```

---

## 5. File Naming

| Source | Pattern | Example |
|--------|---------|---------|
| ChatGPT | `bbc-gpt-<YYMMDD>-<slug>.json` | `bbc-gpt-211021-what-makes-us-laugh.json` |
| Claude convert | `bbc-claude-<YYMMDD>-<slug>.json` | `bbc-claude-211021-what-makes-us-laugh.json` |

- `<YYMMDD>` = compact episode date (matches `ep-YYMMDD` in BBC URL)
- `<slug>` = kebab-case from episode title
- Never overwrite an existing file; use a suffix if collision

---

## 6. State Files (schema v2 — split queue)

ChatGPT queue uses **two small files** (~12 KB total) so scheduled agents can read/commit reliably:

| File | Role |
|------|------|
| `state.json` | `schema: 2`, `sent[]` processed episodes (full metadata per row) |
| `upcoming.json` | `schema: 1`, `queue[]` of **YYMMDD** strings (`queue[0]` = next) |
| `state-advance.json` | Optional one-shot pending advance when reads fail (~300 B); deleted after apply |

**Derive from `queue[i]`:**

- URL: `https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_<YYYY>/ep-<YYMMDD>`
- `YYYY` = `2000 + YY` (or `1900 + YY` when `YY ≥ 90`)
- ISO date: `20YY-MM-DD` from the six digits

**Legacy v1:** monolithic `state.json` with embedded `upcoming[]` objects — migrate on first write to v2 split files. Local helper: `python scripts/repair_bbc_state_advance.py --migrate`.

```json
// state.json
{
  "schema": 2,
  "sent": [
    {
      "url": "https://www.bbc.co.uk/learningenglish/...",
      "title": "Episode title",
      "episodeDate": "2021-10-21",
      "processedAt": "2026-07-01T10:00:00Z",
      "jsonFile": "bbc-gpt-211021-what-makes-us-laugh.json"
    }
  ]
}

// upcoming.json
{
  "schema": 1,
  "queue": ["211223", "211230", "220106"]
}
```

Queue rules:
- Process oldest unprocessed episode first (`queue[0]`)
- Refill **500** weekly YYMMDD strings when `queue` is empty (post-2021-12-09 forward through **July 2026**, then pre-2021-06-10 newer-first)
- Advance state only after verified file write (or verified state-only repair)
- **Progress guarantee:** do not end with orphan JSON on `main` missing from `sent` — REPAIR, **REPAIR-PENDING** (`state-advance.json`), or REPAIR-NEXT
- **Never delete** lesson JSON/HTML; orphan repair is state-only. Helper: `scripts/repair_bbc_state_advance.py --scan`
- Before creating `bbc-gpt-<YYMMDD>-*.json`, skip if Claude already has the same episode (HTML or JSON) — advance ChatGPT state only with `skippedDuplicate: true`

---

## 7. HTML → JSON Mapping (Claude Cowork pipeline)

| HTML region | JSON destination |
|-------------|------------------|
| `.page-header` meta, h1, summary, ext-links | Top-level `title`, `titleVi`, `summary`, `links`, `episode` |
| `#vocab` | `sections[id=vocab]` |
| `#dialogue` | `sections[id=dialogue]` |
| `#sp1` … `#sp3` | `sections[id=speaking-1..3]` |
| `#patterns` | `sections[id=patterns]` |
| `#writing` | `sections[id=writing]` |
| `#grammar` | `sections[id=grammar]` |
| `<footer>` | `sections[id=sources]` |

Run [`convert_bbc_html.py`](convert_bbc_html.py) to perform this conversion automatically.

---

## 8. App Integration Notes

- BBC items are detected by `format === "bbc-6min"`, `category` matching `/bbc/i`, or `id` matching `/^bbc-(gpt|claude)-/`
- Episode list sorted by `episode.date` ascending
- Lesson view renders custom header (badge, bilingual title, summary, link pills) from top-level fields
- Section HTML rendered inside `.lesson-content.bbc` with BBC-specific CSS
- Features that work automatically: section confidence, bookmarks, word stars (⭐), sentence flags (📌), TTS (🔊), word tap-to-pronounce, global search, flashcards

---

## 9. Privacy & Content Rules

- **No personal names, email addresses, or usernames** in generated JSON
- Use role labels in `speaker-name`: Presenter, Co-presenter, Guest expert (spoken lines may keep names from the original transcript)
- **Dialogue:** obtain full BBC transcript first (PDF preferred); use **original** English when available; **paraphrase** only if no full transcript after all sources; always one EN + one VI pair per sentence, full length
- Minimum 6 vocabulary items per episode
- All Vietnamese text must have a matching English sentence

---

## 10. Validation Checklist

Before publishing, verify:

- [ ] `format` is `"bbc-6min"`
- [ ] `category` is `"bbc-6-minute-english"`
- [ ] `topicNumber` is `0`
- [ ] `episode.date` matches filename date
- [ ] `words.length` >= 6
- [ ] All 9 section ids present (or at minimum: vocab, dialogue, speaking-1..3, writing, grammar, sources)
- [ ] `dialogueMode` is `"original"` or `"paraphrase"` and matches dialogue section title
- [ ] `links.transcript` set; dialogue disclaimer includes `ext-link` to transcript
- [ ] Dialogue: full length (≥50 EN pairs; ≥90% of source sentences); **original transcript** when available, else paraphrase fallback
- [ ] Speaking Part 1 ≥4 EN sentences; Part 2 ≥6; Part 3 ≥5; Writing body ≥5 sentences
- [ ] Patterns: 2 `.pattern-formula` lines with `[bracket]` slot notation + 2 example pairs each
- [ ] Every English `<p>` has `class="en"`
- [ ] No inline `style=` colors in grammar error/correct lines
- [ ] No personal names anywhere
- [ ] File listed in `manifest.json` after running `convert_lessons.py`

---

## 11. Reference Files

- UI reference: `../bbc-lessons/bbc-6min-2021-10-21-what-makes-us-laugh.html`
- Minimal valid JSON: [`data/templates/bbc-lesson-template.json`](../data/templates/bbc-lesson-template.json)
- ChatGPT task prompt: [`../prompts/chatgpt/bbc-6min.md`](../prompts/chatgpt/bbc-6min.md) (read [`../prompts/chatgpt/SHARED.md`](../prompts/chatgpt/SHARED.md) first)
- ChatGPT scheduler baseline (owner copy-paste): [`../prompts/chatgpt/schedulers/bbc-6min.scheduler.md`](../prompts/chatgpt/schedulers/bbc-6min.scheduler.md)
