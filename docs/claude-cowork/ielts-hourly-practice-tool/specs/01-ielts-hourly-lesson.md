# IELTS Hourly Lesson — Schema 1

**Spec id:** `ielts-hourly-lesson` · **Version:** 1.0 · **App tab:** 📚 Lessons  
**Skeleton:** [`data/templates/lesson-template.json`](../data/templates/lesson-template.json)

---

## 1. Purpose

One complete hourly IELTS practice set for a Vietnamese learner targeting band **7.5–8.0**, focused on **exactly one** of 17 fixed topics. Six sections: vocab, reading, listening, writing, speaking, strategy.

---

## 2. Output paths

| Agent | Lesson path | State path |
|-------|-------------|------------|
| Claude Cowork | `data/claude-cowork/lessons/ielts-YYYY-MM-DD-HH00-topicNN-<slug>.json` | `data/claude-cowork/state.json` |
| ChatGPT | `data/chatgpt/lessons/ielts-gpt-YYYY-MM-DD-HH00-topicNN-<slug>.json` | `data/chatgpt/state.json` |

- ChatGPT: **`-gpt-`** marker required in filename
- **Time:** Vietnam `Asia/Ho_Chi_Minh` for `YYYY-MM-DD-HH00` and `dateTime`
- **Hour collision (ChatGPT scheduled):** if `HH00` path exists on `main`, use `HHMM` (e.g. `0130`) — see `prompts/chatgpt/ielts-hourly.md` §Filename selection
- `id` = filename stem (no `.json`)

---

## 3. Top-level JSON fields

| Field | Required | Value |
|-------|----------|-------|
| `schema` | yes | `1` |
| `id` | yes | Filename stem |
| `sourceFile` | yes | Same as `id` + `.json` |
| `title` | yes | Topic display name |
| `fullTitle` | yes | `IELTS Hourly Practice — Topic NN: …` |
| `topicNumber` | yes | `1`–`17` |
| `angle` | yes | Sub-angle string |
| `band` | yes | `"7.5–8.0"` |
| `dateTime` | yes | `YYYY-MM-DDTHH:00` |
| `contentUpdatedAt` | yes | ISO 8601 with timezone; set on creation, advance only for meaningful content edits |
| `type` | yes | `"lesson"` |
| `source` | yes | `"claude-cowork"` or `"chatgpt"` |
| `category` | yes | `"ielts-hourly"` |
| `words` | yes | 10 plain-text headwords (no IPA) |
| `sections` | yes | Exactly 6 (see §4) |

---

## 4. Sections (fixed order)

| id | title |
|----|-------|
| `vocab` | Vocabulary |
| `reading` | Reading |
| `listening` | Listening |
| `writing` | Writing (Task 2) |
| `speaking` | Speaking |
| `strategy` | Strategy Note |

Shared HTML rules: [00-platform.md](./00-platform.md).

---

## 5. Content quotas

### Vocabulary (`vocab`)

- **10 cards** in `words[]`; split **Section A** (5 cards, band 6.5–7.5) + **Section B** (5 cards, band 7.5–9.0)
- Each card: headword + US IPA, VN meaning, EN definition + IPA, VN definition, EN example + IPA, VN example
- Use `<h3>Section A <span class="band">Band 6.5–7.5</span></h3>` header

### Reading (`reading`)

- **220–320 words** passage (EN/VI sentence pairs)
- Title as `<h3>`
- **5 mixed questions** (T/F/NG, MCQ, matching, etc.)
- `<div class="key">` with explanatory answers

### Listening (`listening`)

- **200–300 words** transcript
- `<p class="note en/vn">` scenario line
- Bold speakers: `<p class="en"><strong>Officer:</strong> …`
- ≥1 distractor/trap
- 5 questions + key

### Writing (`writing`)

- Task 2 prompt in `<div class="card">`
- **260–310 word** model essay (EN/VI pairs)
- Structure breakdown card
- **3 improvement notes**

### Speaking (`speaking`)

- Coherence backbone card
- **2× Part 1** Q + model answers
- **Part 2:** cue card + prep notes + flowing **190–260 word** turn (no inline labels in turn)
- **2× Part 3** discussion questions

### Strategy (`strategy`)

- Topic-specific Band 7.5–8.0 coaching, bilingual paragraphs

---

## 6. Topic rotation (17 topics)

1 Environment/climate · 2 Health/lifestyle · 3 Crime/law · 4 Housing/urban · 5 Education · 6 Travel · 7 Transport · 8 Media · 9 Work · 10 Technology · 11 Government · 12 Culture · 13 Economy · 14 Science · 15 Family/society · 16 Sports/arts · 17 Globalization

### Selection

1. Read state → `current = last_topic + 1` (wrap 17→1)
2. Avoid repeating vocab/reading/writing/speaking themes from `recent_history` (6 entries)
3. **Fallback** if state unreadable: `((dayOfYear_VN × 24 + hour_VN) mod 17) + 1`

### State shape

```json
{
  "last_topic": 3,
  "updated": "2026-07-11T08:00:00+07:00",
  "recent_history": [{
    "topic": 3,
    "vocab_words": ["…10…"],
    "reading_theme": "…",
    "writing_prompt": "…",
    "speaking_cue_card": "…"
  }]
}
```

Keep 6 most recent entries. Advance state **after** successful publish.

---

## 7. Existence check

Before write: GET lesson path on Pages → 404 = free; 200 = suffix slug or state-only REPAIR if lesson valid but state stale.

---

## 8. Validation checklist

- [ ] `schema: 1`, 6 section ids in order
- [ ] 10 words in `words[]` matching vocab cards
- [ ] US IPA on all vocab headwords, definitions, examples
- [ ] No forbidden markers (`Meaning:`, etc.)
- [ ] Reading word count 220–320; writing model 260–310
- [ ] `topicNumber` matches filename `topicNN`
- [ ] In manifest after `convert_lessons.py`

---

## 9. Agent pointers

| Agent | Prompt / workflow |
|-------|-------------------|
| Claude Cowork | [`prompts/claude/ielts-hourly.md`](prompts/claude/ielts-hourly.md) — local write + `update-index-and-push.ps1` |
| ChatGPT | [`prompts/chatgpt/ielts-hourly.md`](../prompts/chatgpt/ielts-hourly.md) — FULL mode connector commit |

Sample file: `data/chatgpt/lessons/ielts-gpt-2026-07-11-0000-topic02-micro-habits-for-busy-adults.json`
