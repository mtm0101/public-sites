# App Features — Extending index.html

**Spec id:** `app-features` · **Version:** 1.0  
**Single file to edit:** [`index.html`](../index.html) — no build step, no external JS.

---

## 1. Architecture

- Vanilla JS single-page app; routes via hash `#/…`
- Content from [`manifest.json`](../manifest.json) + local JSON under `data/`
- User data in IndexedDB `ielts-practice-tool` v2 — **never** in content JSON
- CSS variables for light/dark; `<meta name="referrer" content="no-referrer">` **required** (Google TTS)

---

## 2. Navigation routes

| Route | Function | Content filter |
|-------|----------|----------------|
| `#/` | Dashboard | stats, bookmarks, calendar |
| `#/lessons` | `renderLessons('lessons')` | `isLessonLike()` && !BBC |
| `#/speaking` | Speaking panel | `items[]` files |
| `#/bbc` | `renderLessons('bbc')` | `isBbcLike()` |
| `#/others` | `renderLessons('others')` | `isOtherItem()` |
| `#/search` | Full-text search | lazy index |
| `#/cards` | Flashcards | flagged words/sentences |
| `#/words` | Word list | flagged vocab |
| `#/sentences` | Sentence list | flagged `.en` lines |
| `#/data` | Import/export, S3 user sync | |

**Rule:** Only hashes starting `#/` are handled by `route()`.

---

## 3. Content classification helpers

```javascript
isBbcLike(item)    // format === 'bbc-6min' || category matches /bbc/i || id /^bbc-(gpt|claude)-/
isLessonLike(item) // topicNumber OR type contains lesson/ielts (BBC excluded from Lessons tab)
isOtherItem(item)  // study item not lesson-like and not BBC
listBase(mode)     // 'lessons' | 'bbc' | 'others' — filters unified item list
```

When adding a new content category:
1. Add detection helper
2. Add nav tab + route case
3. Add filter in `listBase()` / `renderLessons()`
4. Add CSS under `.lesson-content` if new HTML classes
5. Document in new spec under `specs/` + update `INDEX.json`

---

## 4. Lesson rendering

- `renderLesson(id, keepY)` — main lesson view
- Section HTML injected into `.lesson-content` (add `.bbc` class for BBC items)
- `decorateLesson()` — attaches 📌 🔊 ⭐ to `.en` lines and vocab cards
- `cleanVocabSections()` — strips forbidden markers; colours def vs example **before** flag hashes
- Sticky TOC + bottom `#secnav` section bar
- `scrollToSec(id)` — use instead of raw `#sec-` anchors

---

## 5. Key features to preserve

| Feature | Implementation notes |
|---------|---------------------|
| Sentence flags | 📌 on each `.en`; hash normalized text before buttons appended |
| Word tap | `wordAtPoint()` + `#wordpop`; Oxford MP3 cascade; IPA from `data/ipa/` shards |
| TTS | Google Translate TTS for sentences; Web Speech fallback |
| Confidence | 0/25/50/75/100 per section; keys `lessonId\|sectionId` |
| Bookmarks | `itemId\|sectionId` in IndexedDB; shown on dashboard |
| Reload data | Fetches manifest; hash-diff downloads; **never writes progress** |
| S3 user sync | PUT/GET `user-data.json` only — not content |
| Flashcards | 2-step flow; optional speak; confidence filter |
| Search | `buildSearchIndex()` lazy; invalidates on reload |

---

## 6. Adding CSS for new content types

Add rules under `.lesson-content` (and `.lesson-content.bbc` for BBC-specific).  
Support both `.vn` and `.vi` for Vietnamese.  
Tables: plain `<table>` gets borders via app CSS.

---

## 7. convert_lessons.py integration

When new JSON shape needs repair/normalization:
- Add repair in `convert_lessons.py` (idempotent)
- Run converter to rebuild manifest
- Never require manual manifest edits

BBC HTML path: [`convert_bbc_html.py`](../convert_bbc_html.py)

---

## 8. Testing locally

```powershell
npx serve -p 4323
# Open http://localhost:4323/docs/claude-cowork/ielts-hourly-practice-tool/
```

Or GitHub Pages. `file://` fails fetch — app shows manual JSON picker fallback.

---

## 9. Maintainer doc

Full operational detail: [`CLAUDE.md`](../CLAUDE.md) (companion to this spec — specs win for contracts, CLAUDE.md for runtime behaviour).
