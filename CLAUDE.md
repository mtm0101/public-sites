# BBC 6 Minute English Lesson Generator — Claude Code Prompt

Paste this entire prompt into Claude Code (or save as a CLAUDE.md in the project folder).

---

## Task

You are an automated lesson generator. Each time you run:

1. Read the state file to find the next unprocessed BBC 6 Minute English episode
2. Fetch content for that episode
3. Generate a rich bilingual HTML lesson (English + Vietnamese) for IELTS study
4. Save the HTML file to the lessons folder
5. Update the state file
6. Git commit and push to GitHub

Run non-interactively. Make all decisions autonomously. Do not ask clarifying questions.

---

## Paths

- **Repo root:** `C:\Users\USERNAME\Downloads\gpt-codex\public-sites`
- **Lessons folder:** `C:\Users\USERNAME\Downloads\gpt-codex\public-sites\docs\claude-cowork\bbc-lessons`
- **State file:** `C:\Users\USERNAME\Downloads\gpt-codex\public-sites\docs\claude-cowork\bbc-lessons\bbc-6min-sent.json`
- **Push script:** `C:\Users\USERNAME\Downloads\gpt-codex\public-sites\update-index-and-push.ps1`

---

## Step 1 — Read state file

Read `bbc-6min-sent.json`. If it doesn't exist, create it:
```json
{ "sent": [], "upcoming": [] }
```

**Schema:**
```json
{
  "sent": [
    { "url": "...", "title": "...", "episodeDate": "YYYY-MM-DD", "processedAt": "...", "htmlFile": "..." }
  ],
  "upcoming": [
    { "url": "...", "episodeDate": "YYYY-MM-DD", "title": "Title or null" }
  ]
}
```

---

## Step 2 — Find the next episode

**If `upcoming` is non-empty:**
- Take `upcoming[0]`. Skip it if its URL is already in `sent`.
- Proceed to Step 3.

**If `upcoming` is empty — refill with the next 20 episodes:**
- Find the most recent `episodeDate` in `sent`. Next episode = 7 days later.
- If `sent` is empty, start from `2021-06-10`.
- Build URLs using: `https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_<YYYY>/ep-<YYMMDD>`
- Web-search each to confirm it exists and get its title.
- Write all 20 into `upcoming`, save the state file, then take `upcoming[0]`.

---

## Step 3 — Gather episode content

BBC pages are often blocked. Try in order:
1. **BBC PDF transcript (preferred for full dialogue):** `http://downloads.bbc.co.uk/learningenglish/features/6min/<YYMMDD>_6min_english_*.pdf`
2. `https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_<YYYY>/ep-<YYMMDD>`
3. `https://docplayer.net` — search for the episode title
4. `https://www.studocu.com` — search for "BBC 6 Minute English [title] transcript"
5. `https://www.afarinesh.org` — search for the episode code
6. Web search: `BBC 6 Minute English "[title]" transcript vocabulary site:studocu.com OR site:docplayer.net`

Collect:
- Episode title (English)
- Episode date
- **Full conversation transcript** (PDF or mirror) — required for dialogue when available
- Summary (3–5 sentences)
- Vocabulary: **at least 6 items** with BBC definitions and IPA
- Guest expert quotes (role labels in lesson — no personal names in speaker labels)
- Quiz question and answer

---

## Step 4 — Generate the HTML lesson

Create a single self-contained HTML file named:
`bbc-6min-YYYY-MM-DD-<title-slug>.html`

Save to the lessons folder.

### Design specs
- Google Fonts: `Be Vietnam Pro` (Vietnamese) + `Source Serif 4` (body)
- Max-width 800px, background `#fafaf8`, line-height 1.8
- All Vietnamese text: `<em>` with `font-family: 'Be Vietnam Pro', sans-serif; font-style: italic; color: #5a1e6e`
- **No personal names, email addresses, or usernames anywhere in the HTML**

### Required sections

**Header**
- Meta line: `BBC 6 Minute English Archive · Episode date [D Month YYYY] · Saved [D Month YYYY]`
- `<h1>` English title
- `<em>` Vietnamese title
- English summary paragraph + `<em>` Vietnamese summary
- Links: **Original transcript (PDF or web)** · BBC lesson page · BBC Sounds · Spotify search

**Section 2 — Vocabulary (6–10 items)**

For each word/phrase:
1. Word as heading
2. `/IPA/`
3. `<em>Vietnamese meaning</em>`
4. BBC-style English definition
5. `<em>Vietnamese definition</em>`
6. English example sentence
7. `<em>Vietnamese example sentence</em>`
8. IELTS usage note (starts "In IELTS Speaking…" or "In IELTS Writing…") with a model sentence
9. `<em>Vietnamese IELTS note</em>`

**Section 3 — Bilingual dialogue**

Set the section heading to **`Bilingual Dialogue`** when using the official BBC transcript, or **`Bilingual Study Dialogue`** when paraphrasing (no full transcript). Set top-level `dialogueMode` to match: `"original"` or `"paraphrase"`.

**Try the original BBC transcript first** (PDF → episode page → verified mirrors). **Only if a full transcript is impossible** after all sources, paraphrase sentence-by-sentence.

Include **`links.transcript`** (PDF URL preferred) in the header **and** inside the dialogue disclaimer:

```html
<a class="ext-link" href="TRANSCRIPT_URL" target="_blank" rel="noopener">↗ View original transcript (PDF)</a>
```

**When transcript is available (`original` / Bilingual Dialogue):**
- Disclaimer: official BBC transcript + Vietnamese translation for study (EN + VI).
- Use the transcript’s **English sentences as written** — one sentence per line, full conversation, same order and speakers.
- Add `<em>` Vietnamese translation for each English sentence.

**When transcript is unavailable (`paraphrase` / Bilingual Study Dialogue):**
- Disclaimer: paraphrased learning version; original transcript unavailable (EN + VI).
- Reconstruct **exactly one paraphrased EN + one VI sentence per inferred sentence** — closest meaning, same order/speakers, no summarising.

Each sentence pair (group by speaker into turns):

```
Speaker: English sentence.
         <em>Vietnamese sentence.</em>
```

Bold key vocabulary. Include guest turns and full quiz. End with **one extra** vocab recap turn.

Reference: `bbc-6min-2021-10-21-what-makes-us-laugh.html`

**Section 4 — IELTS application**

Reference: `bbc-claude-211021-what-makes-us-laugh.json` (app) / `bbc-6min-2021-10-21-what-makes-us-laugh.html`

- 4a. Speaking Part 1 — sample Q + **4–5 sentence** model answer (EN + VI); use episode vocab with `<strong>`
- 4b. Speaking Part 2 — cue card (full bullet points) + **6–8 sentence** model answer using episode vocab (EN + VI)
- 4c. Speaking Part 3 — linear answer (**≥5 EN+VI pairs**: main idea → cause → example → result) (EN + VI)
- 4d. Two sentence patterns — each in `.pattern-block` with:
  - `.pattern-label` (Pattern N — description)
  - `<p class="en pattern-formula">[slot] + connector + [slot]</p>` — bracket notation like grammar structure formulas, e.g. `[Main clause] + rather than + [contrasting clause/phrase]`
  - **Two** example pairs (episode + general IELTS), EN + VI each
- 4e. Writing Task 2 — full essay question, **thesis** (EN + VI), **5–7 sentence model body paragraph** (EN + VI)
- 4f. Grammar Band 7–8 — four grammar points, each with:
  - Name + structure pattern
  - Explanation EN + `<em>VI</em>`
  - Main example EN + `<em>VI</em>`
  - Speaking example EN + `<em>VI</em>`
  - Writing example EN + `<em>VI</em>`
  - Incorrect sentence (red) + Corrected sentence (green) + `<em>VI error explanation</em>`

**Footer**
- Official sources used + disclaimer (EN + `<em>VI</em>`)

---

## Step 5 — Update state file

Move `upcoming[0]` into `sent`:
```json
{
  "url": "...",
  "title": "...",
  "episodeDate": "YYYY-MM-DD",
  "processedAt": "<ISO timestamp>",
  "htmlFile": "bbc-6min-YYYY-MM-DD-<slug>.html"
}
```
Remove it from the front of `upcoming`. Write the updated JSON back to the state file.

---

## Step 6 — Commit and push

```bash
cd C:\Users\USERNAME\Downloads\gpt-codex\public-sites

# Try push script first
powershell -File update-index-and-push.ps1

# If that fails, fall back to direct git
git add docs/claude-cowork/bbc-lessons/
git commit -m "bbc lesson: $(date +%Y-%m-%d)"
git push
```

---

## Step 7 — Print summary

```
✅ Episode: [title] ([date])
📁 HTML: [filename]
📋 State: [N] upcoming episodes remaining
🚀 Push: [Method A / Method B / FAILED]
```

If push failed, print:
```
⚠️ Push failed — run `git push` manually from:
   C:\Users\USERNAME\Downloads\gpt-codex\public-sites
```

---

## Running on a schedule (Windows Task Scheduler)

To run every hour without Cowork:

1. Open Task Scheduler → Create Basic Task
2. Trigger: Daily, repeat every 1 hour
3. Action: Start a program
   - Program: `claude`
   - Arguments: `--print "run bbc lesson task per CLAUDE.md" --dangerously-skip-permissions`
   - Start in: `C:\Users\USERNAME\Downloads\gpt-codex\public-sites`

Or save this prompt as `CLAUDE.md` in the repo root and just run `claude` from that folder.
