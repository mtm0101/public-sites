version: 3

# ChatGPT scheduled tasks — shared rules

**Fetched every run** — included in the scheduler baseline URL list; do **not** paste this file alone into ChatGPT automation.

---

## MAX LIMIT — schedulers vs task prompts (mandatory for every agent)

**Behavior changes** (queue, skip rules, schema, delivery, privacy, modes) → edit **`prompts/chatgpt/<task>.md`** only; bump that file's `version:`; push to GitHub. The next scheduled run fetches the update via Pages.

**FORBIDDEN:**
- Editing `prompts/chatgpt/schedulers/*.scheduler.md` for behavior
- Bumping `baseline-version` for behavior / queue / skip changes
- Telling the owner to **re-paste** the ChatGPT scheduled task after a behavior-only change
- Copying task-prompt rules into a scheduler COPY block

**Scheduler edits allowed only when:** Pages URL path, repo/branch, or mandatory fetch URL list changes → re-paste **once**.

Full policy: [schedulers/README.md](./schedulers/README.md#max-limit--what-may-change-in-schedulers)

---

**Two-file pattern:** [schedulers/README.md](./schedulers/README.md) — task `.md` (behavior, fetched every run) vs `.scheduler.md` (frozen one-time bootstrap).

**Specs (schema detail):** read [`specs/README.md`](../../specs/README.md) + the task spec for your assignment.

Read this file **first** on every run (before any task-specific prompt).

**Pages URL:** `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/prompts/chatgpt/SHARED.md?t=<unix_ts>`

---

## Repository (fixed)

| Field | Value |
|-------|--------|
| Repo | `mtm0101/public-sites` |
| Branch | **`main` only** for successful FULL / REPAIR runs |
| Content root | `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/` |

**Never** commit to a feature branch. **Never** use PR mode — if you cannot write to `main`, use **CHAT-DELIVERY** instead.

Use the **task-specific commit message** (e.g. `bbc 6min lesson (chatgpt): …`) — not generic messages like `update: YYYY-MM-DD`. That makes commits findable on [main history](https://github.com/mtm0101/public-sites/commits/main).

---

## Reads vs writes

| Channel | Tool |
|---------|------|
| **READS (default)** | Web/browsing GET of GitHub **Pages** URLs (`…/ielts-hourly-practice-tool/…?t=<ts>`), then raw GitHub / jsDelivr fallbacks |
| **READS (task override)** | Some tasks (e.g. **`bbc-6min.md` §1a**) allow **GitHub connector GET** for small repo files when all URL fetches fail — that task section wins over this row |
| **WRITES** | GitHub connector commit to **`main`** as the **last** step |

Do **not** use the code sandbox for network reads. Do **not** use the connector for reads **unless the task prompt explicitly allows it** (BBC queue files when Pages/raw/jsDelivr fail).

---

## Commit verification (mandatory — prevents fake / missing SHAs)

After the connector reports a commit, you **must** verify before printing confirmation:

### 1. Capture SHA from **this run only**

- Use the **full 40-character** SHA returned by the GitHub connector for **this** commit attempt.
- **Never** invent, abbreviate-only, or reuse a SHA from memory, another task, or an earlier message.
- If the connector did **not** return a SHA (skipped commit, duplicate, concurrent run, read-only chat), go to step 4.

### 2. Verify commit exists on `main`

Confirm **at least one** (prefer two):

- Browse (web tool): `https://github.com/mtm0101/public-sites/commit/<full_sha>` — page must load and show the commit.
- Browse: `https://github.com/mtm0101/public-sites/commits/main` — the SHA appears near the top (may lag ~1 min).
- Re-fetch a file you committed via connector from **`main`** and confirm content/path.

If verification fails → **do not** print that SHA. Report `Commit: none — verification failed` and the error.

### 3. Required links in every confirmation (when commit succeeded)

Always print **all three** lines:

```
Commit: <full_40_char_sha>
Commit link: https://github.com/mtm0101/public-sites/commit/<full_sha>
Branch: main (verified)
File(s): https://github.com/mtm0101/public-sites/blob/main/<repo-path-to-file>
```

Use one `File(s):` line per file changed; comma-separate multiple blob URLs.

Optional: `Main history: https://github.com/mtm0101/public-sites/commits/main`

### 4. When **no** commit happened this run

Use **exactly** this pattern (no SHA line):

```
Commit: none — no new commit on main this run
Reason: <e.g. state already advanced on main | duplicate file | CHAT-DELIVERY | connector unavailable>
Main history: https://github.com/mtm0101/public-sites/commits/main
```

**Forbidden:** printing `Commit: b6d47a4…` while also saying "concurrent run" / "no duplicate commit" / "already existed" unless that **exact** SHA was returned and verified **this run** for **this** state-only commit.

### 5. SKIP mode (no write needed)

If after reading **current** `state.json` on Pages the work is already done (episode in `sent`, topic already advanced, file already committed):

- **Do not** commit.
- Mode: **SKIP**
- Use the "Commit: none" block above with reason `already published on main`.

**Task override:** ChatGPT **IELTS hourly** (`ielts-hourly.md`) **never uses SKIP** on scheduled runs — it always advances topic rotation and commits a new lesson. That task's §Never-SKIP wins over this section.

---

## manifest.json

**Never** commit or edit `manifest.json`. Owner runs `convert_lessons.py`. Report: `Manifest: deferred (owner pipeline)`.

---

## Modes summary

| Mode | Commit to `main`? | Confirmation |
|------|-------------------|--------------|
| **FULL** | Yes — new content file (+ state if task uses state) | SHA + links required |
| **REPAIR** | Yes — state (or fix) only | SHA + links required |
| **SKIP** | No — already on main | Commit: none |
| **CHAT-DELIVERY** | No | Full JSON in chat + paths; Commit: none |

Open and close with: `Mode: FULL | REPAIR | SKIP | CHAT-DELIVERY — <reason>`
