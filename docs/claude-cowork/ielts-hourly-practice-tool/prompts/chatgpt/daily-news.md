version: 8
scheduler-baseline: schedulers/daily-news.scheduler.md

# Daily News Briefing — ChatGPT Scheduled Task

**Read first:** [SHARED.md](./SHARED.md) (commit verification, **`main` only** — no PR mode). **This task overrides SHARED.md §Reads** — see §Read cascade (connector reads allowed when URL fetches fail).

Produce a balanced **bilingual English + Vietnamese** daily news briefing as a **schema-2 JSON study file**. Each run commits **one** file targeting **24 distinct news stories**: Tech News (3), AI News (3), United States (3), Vietnam (3), Global (3), Georgia, USA (3), Atlanta (3), and Lilburn (3), plus Atlanta weather and IELTS vocabulary. This is a general daily briefing, not a technology or AI briefing. **Every included news story must satisfy the hard rolling 36-hour freshness window below; never use an older story merely to reach a section or total target.**

---

## CRITICAL — Scheduled automation (read before mode selection)

This prompt is for **ChatGPT Scheduled Tasks** with the **GitHub connector** on `mtm0101/public-sites`.

| Run context | Required mode | Output in chat |
|-------------|---------------|----------------|
| **Scheduled task / automation** | **FULL** (or SKIP) | Short confirmation **only** |
| **Manual chat, no connector** | **CHAT-DELIVERY** | Full JSON in chat |

**Scheduled-run rules (mandatory):**

1. **Default mode is FULL.** Commit via GitHub connector to **`main`**.
2. **Do NOT disable the automation** or abort because GitHub Pages returned **safe-URL**, gateway, DNS, or timeout errors — use the **read cascade** (§Read cascade) and still commit.
3. **Do NOT choose CHAT-DELIVERY** because prompt/template Pages fetches failed — connector GET is the normal fallback.
4. **Do NOT choose CHAT-DELIVERY** when you "cannot write in this chat" — scheduled tasks write via the connector.
5. **Refusal is forbidden.** Every scheduled run ends with **FULL** or **SKIP** — not abort-with-no-commit.

Open with: `Mode: FULL | SKIP | CHAT-DELIVERY — <reason>`

**Repo root:** `mtm0101/public-sites` · branch **`main`**

**Pages base:** `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/`

Do **not** use the code sandbox for network reads.

---

## CRITICAL — Rolling 36-hour news window

1. At the start of research, record the current date and time in **US Eastern time** as `RUN_AT_ET`. Set `CUTOFF_ET = RUN_AT_ET - 36 hours`. This is a rolling timestamp window, not "today and yesterday" and not a calendar-day approximation.
2. Include a news story only when a reliable source page shows a publication timestamp or substantive-update timestamp from `CUTOFF_ET` through `RUN_AT_ET`, inclusive. Convert other time zones to US Eastern before comparing.
3. Verify the timestamp on the article page or in reliable page metadata. A search-result date, crawl date, snippet date, homepage position, or date inferred from the URL is not sufficient by itself.
4. Exclude undated stories, stories whose only verifiable timestamp is older than `CUTOFF_ET`, republished archive/background pieces, and live pages whose latest substantive story update is outside the window. A recent social post or search-index update does not make an older article eligible.
5. The source article's freshness controls eligibility; the underlying event may have begun earlier only if the eligible article contains a genuinely new development reported within the window. State that new development, not recycled background, in the briefing.
6. Apply this rule to **all eight news sections**, including Georgia, Atlanta, and Lilburn. There is no 7-day local-news fallback. Atlanta weather, vocabulary, and source/disclaimer notes are not counted as news stories and are exempt from the story timestamp rule.
7. Keep researching until each section reaches its target of 3 eligible stories where possible. If fewer than 3 eligible stories can be verified for a quiet beat, include only the verified stories, add a bilingual note that no additional qualifying story was found in the last 36 hours, and report the shortfall in the delivery summary. **Freshness outranks the 3-per-section and 24-total targets. Never pad with older news, generic background, duplicates, or an unverifiable timestamp.**

---

## Read cascade (**overrides SHARED.md — connector allowed**)

For **each** repo file below, try **in order** until JSON/text parses. Fresh `?t=<unix_ts>` on URL steps. **Do not stop the run** when early steps fail — always try step 4 before CHAT-DELIVERY.

| Step | Channel | URL pattern |
|------|---------|-------------|
| 1 | Pages GET | `…/ielts-hourly-practice-tool/<repo-path>?t=<unix_ts>` |
| 2 | raw.githubusercontent.com | `https://raw.githubusercontent.com/mtm0101/public-sites/main/docs/claude-cowork/ielts-hourly-practice-tool/<repo-path>?t=<unix_ts>` |
| 3 | jsDelivr | `https://cdn.jsdelivr.net/gh/mtm0101/public-sites@main/docs/claude-cowork/ielts-hourly-practice-tool/<repo-path>` |
| 4 | **GitHub connector GET** | Repo `mtm0101/public-sites`, branch **`main`**, full repo path below |

**Step 4 is mandatory** when steps 1–3 all fail (safe-URL block, gateway, cache, DNS, timeout). This is the **normal** scheduled-task path when Pages is blocked — not an error state.

**This task prompt:** if Pages fetch of `prompts/chatgpt/daily-news.md` or `SHARED.md` fails → read the same path via **connector GET** — do not abort.

**Connector GET — allowed paths:**

- `docs/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/daily-news.md`
- `docs/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/SHARED.md`
- `docs/claude-cowork/ielts-hourly-practice-tool/data/templates/template-spec.json`
- `docs/claude-cowork/ielts-hourly-practice-tool/data/templates/dynamic-template.json`
- `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/news/news-gpt-YYYY-MM-DD.json` (today; try `-1`, `-2` suffixes for SKIP check)
- `docs/claude-cowork/ielts-hourly-practice-tool/specs/03-daily-news.md`

**Connector GET — forbidden:** `manifest.json` (too large — never needed for this task).

Print `Reads: Pages | raw | jsDelivr | connector — <paths>` in confirmation.

---

## Contract (read every run)

Use §Read cascade for:

| Path | Purpose |
|------|---------|
| `data/templates/template-spec.json` | Authoritative contract |
| `data/templates/dynamic-template.json` | Annotated schema-2 skeleton |

If templates are unreadable after the full cascade → use **§Embedded contract** below and still commit.

---

## Embedded contract (fallback when templates unreadable)

Use when template GETs fail after §Read cascade. The shared schema/template governs JSON and HTML mechanics; **this prompt governs the Daily News section list and minimum story counts**. This block is enough to produce valid JSON.

**Top-level:** `schema: 2`, `id: "news-gpt-YYYY-MM-DD"`, `type: "news"`, `source: "chatgpt"`, `category: "daily-news"`, `title`, `dateTime` (US Eastern ~07:30), `words[]`. **Do NOT set `topicNumber`.**

**Every section MUST have non-empty `html`.** App renders `sections[].html` only.

- **Bilingual completeness is mandatory:** every visible English sentence or headline in `sections[].html` must be followed immediately by its Vietnamese counterpart. Use the existing app-supported `.en` then `.vn` / `.vi` sibling pattern; do not change `index.html` for generated content.
- `<p class="en">` + `<p class="vn">` (or `.vi`) — exactly one English sentence per `.en`, followed by exactly one faithful Vietnamese translation.
- English headlines use `<h4 class="en">…</h4>` followed immediately by `<p class="vi">…</p>`. The app already recognises the adjacent `.vi` / `.vn` translation after an English heading.
- Section `title`: plain string — **not** `{en, vi}`

| id | title | Content |
|----|-------|---------|
| `summary` | Overview | 2–4 sentences EN + VI |
| `weather` | Weather — Atlanta, GA | Conditions + outlook + study note |
| `tech` | Tech News | **Target 3 eligible stories** |
| `ai` | AI News | **Target 3 eligible stories**; AI-specific only, not a duplicate of Tech News |
| `us` | United States | **Target 3 eligible stories**; general national news, not tech/AI unless nationally significant |
| `vietnam` | Vietnam | **Target 3 eligible stories** |
| `global` | Global | **Target 3 eligible stories**; international news outside the US and Vietnam |
| `georgia` | Georgia, USA | **Target 3 eligible stories**; statewide news, not Atlanta/Lilburn duplicates |
| `atlanta` | Atlanta | **Target 3 eligible stories**; city/metro news, not Georgia/Lilburn duplicates |
| `lilburn` | Lilburn | **Target 3 eligible stories**; local city/community news, not Atlanta/Georgia duplicates |
| `vocab` | IELTS Vocabulary | **Exactly 6** `.vocab` cards: **2 B2 + 2 C1 + 2 C2**, each with US IPA |
| `sources` | Sources & notes | Sources + disclaimer |

**Story pattern:**

```html
<h4 class="en">English headline</h4>
<p class="vi">Tiêu đề tiếng Việt</p>
<p class="en">One English sentence.</p>
<p class="vn">Một câu tiếng Việt.</p>
<p class="note en">Source Name — article title — published/updated [timestamp and time zone]</p>
<p class="note vn">Nguồn: Source Name — tiêu đề bài viết — đăng/cập nhật [mốc giờ và múi giờ].</p>
```

**Vocab card pattern:**

```html
<div class="vocab"><div class="word">resilient</div><div class="ipa">/rɪˈzɪliənt/</div><div class="level">CEFR C1</div><p class="en">English definition.</p><p class="vn">Định nghĩa tiếng Việt.</p><p class="en">A natural example sentence connected to one of today's stories.</p><p class="vn">Một câu ví dụ tự nhiên liên quan đến một trong các tin hôm nay.</p></div>
```

**Vocabulary rules (mandatory):**

1. Include **exactly 6 distinct English headwords** and group/order them as: **B2 × 2, C1 × 2, C2 × 2**. Do not substitute A1, A2, B1, ungraded, or uncertain items.
2. Verify each level against a reputable CEFR-labelled learner source such as the Cambridge Dictionary, Oxford Learner's Dictionaries, or English Vocabulary Profile. Do not infer a level solely because a word appears easy or difficult. If sources disagree, use another clearly verified word.
3. Choose useful academic or news-related words that **already appear naturally and verbatim in at least one English news headline or English story-body sentence in this briefing**. Appearance only in the overview, weather, vocabulary, sources, delivery summary, or Vietnamese text does not qualify. Exclude proper nouns, abbreviations, highly specialized product terminology, and trivial inflections of the same lemma.
4. Every card must contain the headword, US IPA, visible `CEFR B2`, `CEFR C1`, or `CEFR C2` level, a concise English definition with an immediate Vietnamese translation, and one natural news-context English example with an immediate Vietnamese translation.
5. The top-level `words` array must contain exactly these same 6 headwords, once each, in the same order as the cards.
6. Do not downgrade the C1/C2 allocation when suitable vocabulary is scarce; select different eligible words from the covered stories instead.
7. Wrap the first qualifying occurrence of each headword in the news sections with `<strong>` (for example, `<strong>resilient</strong>`). Preserve the exact headword spelling inside the tag. Do not force an unnatural sentence or alter a factual quotation merely to insert vocabulary; choose another word that genuinely belongs to the reporting.

**Coverage rules (mandatory):**

1. Research **every** required news section before drafting: Tech News, AI News, United States, Vietnam, Global, Georgia, USA, Atlanta, and Lilburn.
2. Target **3 separately headed, 36-hour-eligible stories** in each of the eight sections using the story pattern above: target **24 stories** per briefing. Count headlines, not sentences or source links. A documented freshness shortfall is permitted; an older story is not.
3. Keep the sections balanced: Tech News and AI News together may account for **no more than 6 stories** in the standard target briefing. Do not substitute technology/AI stories for US, Vietnam, Global, Georgia, Atlanta, or Lilburn coverage.
4. A story may appear in **one news section only**. Select a city-specific story for Atlanta or Lilburn before using it in Georgia; select a US story before using it in Global. Do not reuse a headline with minor rewording.
5. Enforce §CRITICAL — Rolling 36-hour news window without exception. For a quiet local beat, leave the section short and add the required bilingual shortfall note rather than using older reporting, repeating a story, or filling it with generic background.
6. Web-search and paraphrase; Atlanta weather remains required. Privacy: roles, not personal names, in public content.

**Pre-commit freshness and coverage check (mandatory):** Record `RUN_AT_ET` and `CUTOFF_ET`. For every headline, verify and retain its source publication/update timestamp and confirm `CUTOFF_ET <= story timestamp <= RUN_AT_ET`. Remove every failing or unverifiable story. Then count `tech`, `ai`, `us`, `vietnam`, `global`, `georgia`, `atlanta`, and `lilburn`; target 3 each and 24 unique headlines with no cross-section duplicates. Research missing eligible stories before writing the JSON. If a target still cannot be met, keep the section short, add the bilingual shortfall note, and report the actual count; do not relax the cutoff.

**Pre-commit bilingual check (mandatory):** Scan every `sections[].html` in document order. Each English heading (`h2`–`h6` with class `en`), English paragraph (`p.en`), English note (`.note.en`), English list sentence, question, source/disclaimer sentence, weather sentence, vocabulary definition, and vocabulary example must have an immediate `.vn` or `.vi` counterpart with the same meaning. Do not leave English-only source notes, captions, labels, summaries, or explanatory sentences. Proper nouns, URLs, IPA, and single-word vocabulary headwords may remain unchanged, but any explanatory sentence about them must be bilingual.

**Pre-commit vocabulary check (mandatory):** Verify there are exactly 6 `.vocab` cards and exactly 6 distinct entries in top-level `words`, with a one-to-one order match. Verify the level distribution is exactly `B2 = 2`, `C1 = 2`, `C2 = 2`; every level is source-verified; every card has US IPA, bilingual definition, and bilingual contextual example. For each headword, search all English headlines and story-body sentences in `tech`, `ai`, `us`, `vietnam`, `global`, `georgia`, `atlanta`, and `lilburn`; verify at least one exact, natural occurrence and verify its first occurrence is wrapped in `<strong>`. Replace any item that is absent from the news, ungraded, uncertain, duplicated, or outside B2–C2.

**Forbidden:** inline styles, `<html>/<style>/<script>`, literal `Meaning:`/`Example:` markers, personal names in public content.

---

## Architecture

| Channel | Rule |
|---------|------|
| **READS** | §Read cascade (Pages → raw → jsDelivr → connector) |
| **WRITES** | **ONE** connector commit to **`main`** as **last** step |
| **Forbidden** | Bucket uploads, manifest edits, other agents' folders |

---

## JSON deliverable

**Path:** `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/news/news-gpt-YYYY-MM-DD.json`

- **`-gpt-` marker required**
- **US Eastern** date
- Never overwrite — existence-check via §Read cascade; suffix (`-1`, `-2`) if file exists on `main`

```json
{
  "schema": 2,
  "id": "news-gpt-2026-07-10",
  "type": "news",
  "source": "chatgpt",
  "category": "daily-news",
  "title": "Daily News Briefing — July 10, 2026",
  "dateTime": "2026-07-10T07:30:00",
  "words": ["…"],
  "sections": []
}
```

**Do NOT set `topicNumber`**.

---

## Write (final step, **`main` only**)

**Commit message:** `daily news briefing (chatgpt): <filename>`

Commit **only** the one new `.json`. Then **SHARED.md** verification.

| Mode | Action |
|------|--------|
| **FULL** | New file on **`main`** |
| **SKIP** | File already on **`main`** for today |
| **CHAT-DELIVERY** | Full JSON in chat (manual / connector-write-failure only) |

---

## Delivery template

```
Mode: FULL | SKIP | CHAT-DELIVERY — <reason>
Reads: Pages | raw | jsDelivr | connector — <paths>
Window: [CUTOFF_ET] through [RUN_AT_ET] (rolling 36 hours, US Eastern)
Stories: tech [N/3] · ai [N/3] · us [N/3] · vietnam [N/3] · global [N/3] · georgia [N/3] · atlanta [N/3] · lilburn [N/3] · total unique [N/24 target]
Freshness: [N] eligible · [N] excluded as old/undated · shortfalls [none or section names]
Vocabulary: B2 [word, word] · C1 [word, word] · C2 [word, word] — 6/6 verified
Headlines: …
Path: docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/news/<file>
Manifest: deferred (owner pipeline)

Commit: <full_sha>
Commit link: https://github.com/mtm0101/public-sites/commit/<sha>
Branch: main (verified)
File(s): https://github.com/mtm0101/public-sites/blob/main/docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/news/<file>

OR:

Commit: none — no new commit on main this run
Reason: …
Main history: https://github.com/mtm0101/public-sites/commits/main
```

Do not print full JSON in FULL/SKIP mode.

**Forbidden end state:** `Commit: none` with reason "prompt reads failed" or "safe-URL blocked" on a scheduled run — use connector reads and commit, or CHAT-DELIVERY only if connector write also failed.

---

## Scheduler baseline (human — one-time bootstrap)

**Not fetched by the agent.** Frozen bootstrap: [`schedulers/daily-news.scheduler.md`](./schedulers/daily-news.scheduler.md) (connector + fetch URLs only). **All behavior lives in this file** (fetched every run with `?t=`).

- **Behavior changes** → edit **this file** only; bump `version:` above. **Do not** edit `schedulers/`.
- **Do not** tell the owner to re-paste after behavior changes ([MAX LIMIT](./schedulers/README.md#max-limit--what-may-change-in-schedulers)).
- **Re-paste scheduler** → only if bootstrap URL list or repo/branch changes.
