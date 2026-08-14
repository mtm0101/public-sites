# Daily News Briefing — Schema 2

**Spec id:** `daily-news` · **Version:** 1.0 · **App tab:** 🗂 Others  
**Skeleton:** [`data/templates/dynamic-template.json`](../data/templates/dynamic-template.json)

---

## 1. Purpose

Bilingual (EN/VI) daily news JSON: Tech (largest), Vietnam, US, Atlanta & Lilburn GA, Atlanta weather, IELTS vocab, sources.

---

## 2. Output

**Path:** `data/chatgpt/news/news-gpt-YYYY-MM-DD.json`  
**Schedule:** Daily ~7:30 US Eastern · **`-gpt-`** required · suffix if exists

---

## 3. Top-level fields

```json
{
  "schema": 2,
  "id": "news-gpt-2026-07-10",
  "type": "news",
  "source": "chatgpt",
  "category": "daily-news",
  "title": "Daily News Briefing — July 10, 2026",
  "dateTime": "2026-07-10T07:30:00",
  "words": ["cybersecurity", "…"],
  "sections": []
}
```

**Do NOT set `topicNumber`** (shows under Others, not Lessons).

---

## 4. Sections

| id | title | Content |
|----|-------|---------|
| `summary` | Overview | 2–4 sentences EN + VI |
| `weather` | Weather — Atlanta, GA | Current + outlook + study note |
| `tech` | Tech Industry | **3 stories** (largest) |
| `vietnam` | Vietnam | 2 stories |
| `us` | United States | 2 stories |
| `atlanta` | Atlanta & Lilburn | 2 local stories |
| `vocab` | IELTS Vocabulary | 4–6 cards, US IPA, level 2 |
| `sources` | Sources & notes | Citations + disclaimer, level 2 |

Every section: non-empty `html` with `.en`/`.vn` pairs. Platform rules: [00-platform.md](./00-platform.md).

### Story pattern

```html
<h4>English headline</h4>
<p class="vi">Tiêu đề tiếng Việt</p>
<p class="en">One English sentence.</p>
<p class="vn">Một câu tiếng Việt.</p>
<p class="note en">Source Name — article title</p>
```

---

## 5. Content rules

- Web-search today's news; paraphrase
- Tech section largest (AI, platforms, chips, regulation)
- Atlanta weather required
- Privacy: roles not names in public content

---

## 6. Agent pointer

[`prompts/chatgpt/daily-news.md`](../prompts/chatgpt/daily-news.md)

Sample: `data/chatgpt/news/news-gpt-2026-07-10.json`

---

## 7. Validation

- [ ] All 8 sections with `html`
- [ ] Story counts: tech 3, vietnam 2, us 2, atlanta 2
- [ ] No `{en,vi}` objects without rendered html
- [ ] `type: "news"`, `category: "daily-news"`
