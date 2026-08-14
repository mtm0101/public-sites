# World Cup Daily Briefing — Schema 2

**Spec id:** `worldcup-briefing` · **Version:** 1.0 · **App tab:** 🗂 Others

---

## 1. Purpose

Bilingual Men's 2026 FIFA World Cup daily briefing: latest results, moments, implications, breakout players, bracket/schedule tables, what to watch, vocab, sources.

---

## 2. Output

**Path:** `data/chatgpt/news/worldcup-gpt-YYYY-MM-DD.json`  
**Schedule:** Daily ~7:00 US Eastern · **`-gpt-`** required

**Memory:** Previous briefing files = cumulative knockout history (no separate state). Read last 7 days newest-first before writing.

**Scope:** Round of 32 / vòng 1/16 onward — **exclude group stage**.

---

## 3. Top-level fields

```json
{
  "schema": 2,
  "id": "worldcup-gpt-2026-07-10",
  "type": "news",
  "source": "chatgpt",
  "category": "worldcup",
  "title": "2026 FIFA World Cup Daily Briefing — July 10, 2026",
  "dateTime": "2026-07-10T07:00:00",
  "words": ["quarter-final", "clean sheet"],
  "sections": []
}
```

**Do NOT set `topicNumber`**. No rogue top-level `results[]` / `briefing{}` without `sections[].html`.

---

## 4. Sections

| id | title | Content |
|----|-------|---------|
| `summary` | Overview | Tournament snapshot |
| `results` | Latest result(s) | Today's completed match(es) |
| `biggest-moments` | Biggest moments | 3 highlights |
| `implications` | Tournament implications | 3–4 bullets EN+VI |
| `breakout-players` | Breakout players | 2–3 spotlights |
| `schedule` | Schedule & implications | Bracket tables + **cumulative knockout table** |
| `watch` | What to watch | Next matches |
| `vocab` | IELTS Vocabulary | 4–6 cards |
| `sources` | Sources & notes | Sources + disclaimer |

### Match header pattern

```html
<h4>Quarterfinal · France vs Morocco · 2-0</h4>
<p class="en">Analysis sentence.</p>
<p class="vn">Câu phân tích.</p>
```

### Cumulative results table

In `schedule` section — list **every** knockout match recorded so far; extend prior rows, never drop history.

---

## 5. Content rules

- Balanced coverage — no favorite-team bias
- Verify scores/dates via web search
- Tables inside `html` as `<table>` — not bare JSON columns/rows

---

## 6. Agent pointer

[`prompts/chatgpt/worldcup-daily.md`](../prompts/chatgpt/worldcup-daily.md)

Sample: `data/chatgpt/news/worldcup-gpt-2026-07-10.json`

---

## 7. Validation

- [ ] Cumulative knockout history extended from previous file
- [ ] All sections have `html` with EN/VI pairs
- [ ] `category: "worldcup"`
