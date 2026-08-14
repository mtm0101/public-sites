# Morning Brief — Schema 2 (English-only)

**Spec id:** `morning-brief` · **Version:** 1.1 · **App tab:** 🗂 Others

---

## 1. Purpose

Weekday personal morning brief as JSON: calendar, email summary, priorities. **English-only** — no `.vn` lines. Source data from user's calendar/email (scheduler context).

---

## 2. Output

**ChatGPT scheduled task:** **message-only** — brief appears in the ChatGPT run chat to the owner. **No repo write, no GitHub commit, no S3 upload** (private calendar/email content).

**Optional app JSON path** (manual / other pipelines only — not ChatGPT scheduler): `data/chatgpt/brief/brief-gpt-YYYY-MM-DD.json`  
**Schedule:** Weekdays ~7:45 US Eastern

---

## 3. Top-level fields

```json
{
  "schema": 2,
  "id": "brief-gpt-2026-07-10",
  "type": "brief",
  "source": "chatgpt",
  "category": "morning-brief",
  "title": "Morning Brief — July 10, 2026",
  "dateTime": "2026-07-10T07:45:00",
  "words": ["priority", "deadline"],
  "sections": []
}
```

---

## 4. Sections

| id | title | Content |
|----|-------|---------|
| `summary` | Overview | Day snapshot |
| `calendar` | Today's schedule | Meetings/events |
| `email` | Email highlights | Important threads |
| `priorities` | Top priorities | Action items |
| `vocab` | IELTS Vocabulary | Optional 3–4 EN cards |
| `sources` | Notes | Disclaimer |

**HTML:** `<p class="en">` only — no Vietnamese.

---

## 5. Privacy (mandatory)

- **Roles not names** (team lead, client contact)
- **Paraphrase** email subjects — no verbatim personal subjects
- Sensitive items as **counts only**
- No emails, usernames, phone numbers, home addresses
- Same rules in chat delivery (ChatGPT never publishes to GitHub)

---

## 6. Agent pointer

[`prompts/chatgpt/morning-brief.md`](../prompts/chatgpt/morning-brief.md)

---

## 7. Validation

- [ ] EN-only (no `.vn` in html)
- [ ] Privacy rules applied
- [ ] `type: "brief"`, `category: "morning-brief"`
