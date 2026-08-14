# Speaking Source — Q&A Practice Sets

**Spec id:** `speaking-source` · **Version:** 1.0 · **App tab:** 🗣 Speaking  
**Reference:** [`data/claude-cowork/speaking/0.speaking.json`](../data/claude-cowork/speaking/0.speaking.json)

---

## 1. Purpose

Structured Speaking Part 1 practice: topics → questions → model answers (EN + VI + optional IPA). Rendered in dedicated Speaking section with per-question confidence rating.

---

## 2. Shape (not `sections[]`)

```json
{
  "source": "claude-cowork",
  "l1": "DOL IELTS 7.0 Speaking Exercise",
  "items": [
    {
      "item_no": 1,
      "l1": "DOL IELTS 7.0 Speaking Exercise",
      "l2": "L1",
      "l3": "Structure (Direct Approach)",
      "topic": "Work",
      "title": "Work & Careers — Part 1",
      "questions": [
        {
          "question_no": 1,
          "question": "What do you do for work?",
          "question_vi": "Bạn làm nghề gì?",
          "question_ipa": "/wʌt du ju du fər wɝk/",
          "answers": [
            {
              "label": "Answer",
              "english": "I work as a software engineer…",
              "english_ipa": "/…/",
              "vietnamese": "Tôi làm kỹ sư phần mềm…"
            }
          ]
        }
      ]
    }
  ]
}
```

---

## 3. Field rules

| Field | Notes |
|-------|-------|
| `item_no` | Unique integer within file; app id `sp-NN` for `0.speaking.json` |
| `l1` / `l2` / `l3` | Optional hierarchy shown and filterable in Speaking; item values override top-level defaults |
| `topic` | Short label for lists |
| `title` | Longer display title |
| `question` | English question text |
| `question_vi` | Vietnamese translation |
| `question_ipa` | US IPA of full question (optional but recommended) |
| `answers[]` | One or more variants; `label` e.g. "Answer", "Answer B" |
| `english_ipa` | US IPA of full answer (optional) |

Other sources: filename-hash prefix on ids to avoid collision with `sp-NN`.

---

## 4. Output paths

| File | Role |
|------|------|
| `data/claude-cowork/speaking/0.speaking.json` | Primary 14-topic / 68-question set |
| `data/{source}/speaking/*.json` | Additional sets from any agent |

Files with `template` in name are ignored by converter.

---

## 5. App behaviour

- Fetched on every **⟳ Reload data**
- Progress keys: `sp-NN|qI` in IndexedDB `progress` store
- Search indexes question + answer EN/VI
- L1/L2/L3 filter values are reflected in the page URL, so filtered Speaking lists are bookmarkable
- Every rendered question section has a `#` permalink that stores its section id in the URL
- IPA rendered as `<p class="ipa">` between EN and VI lines
- User edits to VI stored in `speakingEdits` (prefer maintaining `question_vi`/`vietnamese` in source file)

---

## 6. Validation

- [ ] Valid JSON with non-empty `items[]`
- [ ] Each item has `questions[]` with at least one question
- [ ] `question_vi` and `vietnamese` on all entries
- [ ] No personal names in public content

---

## 7. IPA generation (maintainers)

Use Python `eng-to-ipa` package when adding/updating entries. Regenerate manifest after edits.
