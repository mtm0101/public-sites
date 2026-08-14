# DOL Vocab — JSON Contract

**Spec id:** `dol-vocab` · **App tab:** `#/dol`  
**Skeleton:** [`data/templates/dol-vocab-template.json`](../data/templates/dol-vocab-template.json)

## Purpose

Bilingual vocabulary from [DOL Tự học](https://tuhoc.dolenglish.vn/luyen-thi-ielts/free-ielts-online-test) IELTS online tests. One JSON file per vocab page (Reading or Listening).

## Locations

| Role | Path |
|------|------|
| ChatGPT output | `data/chatgpt/dol/dol-gpt-<queueKey>.json` |
| State | `data/chatgpt/dol/state.json`, `upcoming.json`, `catalog.json` |
| Parser utils | `scripts/dol_vocab_utils.py`, `scripts/fetch_dol_vocab.py` |
| Local publish | `scripts/publish_dol_all.py` via `dol-done-publish-all.ps1` (DONE — 197 sets on disk; queue empty) |
| SuperLMS publish | `scripts/publish_superlms_all.py` via `dol-done-publish-superlms-all.ps1` (DONE — 30 sets on disk) |
| Queue builder | `scripts/build_dol_queue.py` |

## Top-level fields

| Field | Required | Notes |
|-------|----------|-------|
| `format` | yes | `"dol-vocab"` |
| `id` | yes | `dol-gpt-<queueKey>` |
| `type` | yes | `"vocab"` |
| `category` | yes | `"dol-vocab"` |
| `group` | yes | `IELTS Cambridge` / `IELTS Practice Test Plus` / `IELTS Actual Test` |
| `book`, `bookNum`, `testNum`, `skill` | yes | Metadata for filters |
| `url` | yes | Source vocab page |
| `queueKey` | yes | e.g. `cam20-t1-reading` |
| `items[]` | yes | Flat word list (see below) |
| `sections[]` | yes | Grouped HTML for detail view |
| `words[]` | yes | Search index headwords |

## `items[]` entry

```json
{
  "id": "p1-nesting-female",
  "passageLabel": "Passage 1: The kãkãpo",
  "passageName": "The kãkãpo",
  "passageNum": 1,
  "text": "Nesting female",
  "pos": "noun",
  "vn": "(noun). con cái làm tổ",
  "ipaUK": "/ˈnɛstɪŋ ˈfiːmeɪl/",
  "example": "Nesting females were observed…",
  "exampleVi": "Những con cái làm tổ đã được quan sát…",
  "exampleIpa": "<strong>/ˈnɛstɪŋ ˈfiːmeɪlz/</strong> /wɜː/ …",
  "questionGroup": "Q3"
}
```

## App behavior

- **`#/dol`:** All word entries (no dedupe) with filters by group, book, skill, test, passage.
- **`#/dol/pages`:** Collected page list.
- **Flashcards:** Deck **📖 DOL Vocab (deduped)** — one card per headword (`normWordKey`).
- **Confidence:** IndexedDB `words` store, key `<pageId>|p<N>|<hash(text)>`.

## Queue order

1. Cambridge 20 → 9 (books not on DOL are skipped)
2. Practice Test Plus 1 → 3
3. Actual Test 1 → 6

Exclude: Official Guide, IELTS Trainer.

## Attribution

Every file must include a `sources` section: vocabulary from DOL Tự học for personal study; no author names from DOL CMS.
