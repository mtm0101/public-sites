# Platform — Publishing, Discovery & Shared HTML Rules

**Spec id:** `platform` · **Version:** 1.0  
**Read before:** any content spec or app change.

---

## 1. What this tool is

Single-page app ([`index.html`](../index.html)) for bilingual (EN/VI) IELTS study.  
All study content = JSON files under [`data/`](../data/). User progress = browser IndexedDB only (never in JSON files).

---

## 2. Repository & publishing

| Field | Value |
|-------|--------|
| Repo | `mtm0101/public-sites` |
| Branch | **`main`** |
| Content root | `docs/claude-cowork/ielts-hourly-practice-tool/data/` |
| Tool root | `docs/claude-cowork/ielts-hourly-practice-tool/` |

### Source folders (under `data/`)

| Folder | Agent | Marker in filename |
|--------|-------|-------------------|
| `claude-cowork/` | Claude Cowork (local) | `ielts-`, `bbc-claude-`, etc. |
| `chatgpt/` | ChatGPT scheduled tasks | `-gpt-` required |
| `codex/` | Codex / other | your choice |

Organize freely: `lessons/`, `news/`, `bbc/`, `brief/`, `speaking/`.

### Write rules

- **ADD or UPDATE only** — never delete other agents' files
- **Never** edit `manifest.json`, `index.html`, `ipa/`, `templates/` from content agents
- Filename stem = unique **id** repo-wide
- Remote agents (ChatGPT): GitHub connector commit to **`main`**
- Local agents: write files + run `python scripts/convert_lessons.py` + push

### Reads (remote agents)

GitHub Pages (append `?t=<unix_ts>`):

```
https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/<path>
```

Fallback for state/templates:

```
https://raw.githubusercontent.com/mtm0101/public-sites/main/docs/claude-cowork/ielts-hourly-practice-tool/<path>
```

---

## 3. Discovery (`manifest.json`)

- Rebuilt by [`scripts/convert_lessons.py`](../scripts/convert_lessons.py) — indexes every `*.json` under `data/`
- App loads **only** via [`manifest.json`](../manifest.json) next to `index.html`
- A committed JSON is invisible until owner runs converter + push
- Each manifest entry has `hash` (md5) plus `updatedAt` for cache invalidation
- The manifest has a stable `contentVersion` and `contentUpdatedAt`. Rebuilding an unchanged manifest preserves both, allowing the app to skip all lesson fetches and cache scans.
- Study files should provide `contentUpdatedAt` as an ISO 8601 timestamp with timezone. Set it at creation and advance it only after a meaningful content change; never advance it for reads, no-op rebuilds, or unchanged republishes. The converter preserves the prior entry timestamp when the hash is unchanged and uses hashes as the integrity fallback.

```powershell
cd docs\claude-cowork\ielts-hourly-practice-tool
python scripts/convert_lessons.py
```

Repo-root shortcut: `update-index-and-push.ps1`

---

## 4. JSON shapes (two kinds)

### Study item — `sections[]` present

Used for lessons, news, briefs, quizzes. Schema 1 (IELTS hourly) or Schema 2 (generic).

```json
{
  "schema": 1,
  "id": "unique-filename-stem",
  "type": "lesson",
  "source": "chatgpt",
  "category": "ielts-hourly",
  "title": "Display title",
  "dateTime": "2026-07-10T08:00",
  "contentUpdatedAt": "2026-07-10T08:00:00+07:00",
  "words": ["headword"],
  "sections": [
    { "id": "vocab", "title": "Vocabulary", "level": 1, "html": "…" }
  ]
}
```

### Speaking source — `items[]` with `questions[]`

See [06-speaking-source.md](./06-speaking-source.md).

---

## 5. Section object

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | `[a-zA-Z0-9_-]+`, unique within item |
| `title` | yes | Plain string — app renders as heading; **do not repeat in html** |
| `html` | **yes** | Non-empty. App renders **only** this — not raw `stories[]` or `{en,vi}` objects |
| `level` | no | `1` default; `2`/`3` = indented sub-section in nav |

---

## 6. HTML conventions (all study items)

### Bilingual rule (mandatory for EN/VI content)

- One English sentence → `<p class="en">…</p>`
- Vietnamese immediately after → `<p class="vn">…</p>` (or `class="vi"`)
- **Never** merge EN+VI in one element
- **Never** use literal markers: `Meaning:`, `Example:`, `Nghĩa:`, `Ví dụ:`

### Allowed classes

`en`, `vn`, `vi`, `ipa`, `note`, `vocab`, `head`, `card`, `key`, `label`, `band`, `prep`, `q` (as `<ol class="q">`)

BBC additionally uses: `vocab-card`, `dialogue-turn`, `ielts-sub`, `grammar-card`, etc. — see [02-bbc-6min.md](./02-bbc-6min.md).

### Forbidden

`<html>`, `<head>`, `<body>`, `<style>`, `<script>`, section-level `<h2>`, inline styles

### Vocab card (standard IELTS)

```html
<div class="vocab">
  <div class="head">take up <span class="ipa">/ˌteɪk ˈʌp/</span></div>
  <p class="vn">bắt đầu (một hoạt động mới)</p>
  <p class="en">to start doing a new activity regularly.</p>
  <p class="ipa">/tə stɑrt ˈduɪŋ ə nu ækˈtɪvəti ˈrɛɡjələrli/</p>
  <p class="vn">bắt đầu làm một hoạt động mới một cách đều đặn.</p>
  <p class="en">After I retired, I decided to take up watercolour painting.</p>
  <p class="vn">Sau khi nghỉ hưu, tôi quyết định bắt đầu học vẽ màu nước.</p>
</div>
```

First `.en` in card = definition (teal); later `.en` = examples (violet).

### Tables

```html
<table>
  <tr><th>Col A</th><th>Col B</th></tr>
  <tr><td>Cell</td><td>Cell</td></tr>
</table>
```

Inside `sections[].html` only — app adds borders.

### Encoding

UTF-8 JSON; escape `"` as `\"` and newlines as `\n` inside strings.

---

## 7. App navigation (content placement)

| Tab | Route | What appears |
|-----|-------|----------------|
| 📚 Lessons | `#/lessons` | `topicNumber` set OR `type` contains `lesson`/`ielts` (not BBC) |
| 🗣 Speaking | `#/speaking` | `items[]` speaking files |
| 🎧 BBC 6 Minutes | `#/bbc` | `format: "bbc-6min"` or BBC category/id |
| 🗂 Others | `#/others` | news, brief, quiz, worldcup, etc. |

Detection logic: see [07-app-features.md](./07-app-features.md).

---

## 8. S3 bucket (user data only)

Bucket URL exists for **user progress sync** (`user-data.json`) only.  
**No agent publishes content to S3.** Content channel = GitHub repo.

---

## 9. Validation (every publish)

- [ ] Valid UTF-8 JSON
- [ ] Unique `id` / filename stem
- [ ] Every section has non-empty `html`
- [ ] EN/VI pairs complete (except EN-only briefs)
- [ ] No personal names/emails
- [ ] Owner runs `convert_lessons.py` after local writes
- [ ] Remote agents never touch `manifest.json`

---

## 10. Reference files

| File | Role |
|------|------|
| [`data/templates/template-spec.json`](../data/templates/template-spec.json) | Machine-readable mirror of this spec |
| [`data/templates/lesson-template.json`](../data/templates/lesson-template.json) | Schema-1 skeleton |
| [`data/templates/dynamic-template.json`](../data/templates/dynamic-template.json) | Schema-2 skeleton |
| [`data/templates/bbc-lesson-template.json`](../data/templates/bbc-lesson-template.json) | BBC skeleton |
| [`specs/INDEX.json`](./INDEX.json) | Spec catalog |
