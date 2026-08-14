version: 10
scheduler-baseline: schedulers/dol-vocab.scheduler.md

# DOL Vocab — ChatGPT Scheduled Task

> **Deprecated (2026-07-11):** DOL is published locally via `dol-done-publish-all.ps1` / `scripts/publish_dol_all.py`. The `data/chatgpt/dol/snapshots/` cache and bundle scripts were removed. Keep this prompt only if you re-enable the ChatGPT scheduler.

**Read first:** [SHARED.md](./SHARED.md) (commit verification, `main` only). **This task overrides SHARED.md §Reads** — connector reads allowed for small repo files (§1a).

**Scheduled runs cannot reach `tuhoc.dolenglish.vn` reliably** (sandbox DNS/timeouts). **Owner pipeline pre-publishes full lesson files** (`dol-gpt-<queueKey>.json`) via `dol-done-publish-all.ps1` (local fetch). **Your primary job = sync `state.json` / `upcoming.json` (REPAIR)** when the lesson file is already on `main`. Bundle assembly (§2a) is **legacy** — snapshots folder removed.

Each run advances the queue by **one** key. Commit to **`main`**.

**Tool root:** `docs/claude-cowork/ielts-hourly-practice-tool/`

---

## CRITICAL — Scheduled automation (read before mode selection)

| Run context | Required mode | Output in chat |
|-------------|---------------|----------------|
| **Scheduled task / automation** | **REPAIR** or **FULL** (small lessons only) | Short confirmation **only** |
| **Manual chat, no connector** | **CHAT-DELIVERY** | Split blocks in chat (§6) |

**Scheduled-run rules (mandatory):**

1. **Default mode is REPAIR** when `dol-gpt-<queueKey>.json` is already on `main` (owner pre-published). **FULL** only when the lesson file is missing **and** the bundle is small enough to assemble (§2a limits).
2. **Do NOT choose CHAT-DELIVERY** on scheduled automation — **ever**. Overrides SHARED.md. If the connector fails, use **§4 commit retry** then **COMMIT-PENDING** (§4c) — not CHAT-DELIVERY.
3. **Do NOT choose CHAT-DELIVERY** because the lesson JSON is ~40–90 KB — size is normal; pass **file content as a string** to the connector (§4a), not as a sandbox artifact upload.
4. **Do NOT choose SKIP** or **DEFER** until you have checked **§1d** (pre-published lesson on `main`) and completed any allowed **§2 cascade**.
5. **Do NOT DEFER** when `dol-gpt-<queueKey>.json` exists on `main` — use **REPAIR** (§1d / §1b).
6. **Do NOT attempt §2a bundle assembly** when `index.chunkFiles.length > 12` or `index.itemCount > 150` — owner must publish; if lesson on `main`, **REPAIR**; if missing, **REPAIR-NEXT** to next `queue[0]` that has a lesson on `main`.
7. **Do NOT stall** narrating DNS/gateway/browsing errors — if §1d finds the lesson on `main`, proceed to REPAIR immediately (`Fetch: owner-prebuilt`).
8. **Forbidden end state:** `Mode: CHAT-DELIVERY` + `Commit: none` + unchanged queue on a **scheduled** run.
9. **Forbidden end state:** `Commit: none` + unchanged queue when `dol-gpt-<queueKey>.json` is verified on `main` but `sent[]` was not advanced — must **REPAIR**.
10. If current target still unreachable after §1d + allowed §2 → **REPAIR-NEXT** (§2d). Retry `failed[]` first per §1c **before** §1b orphan checks.
11. **Forbidden end state:** `Mode: DEFER` with `Commit: none` when **any** key in `queue[0..4]` has `dol-gpt-*.json` on `main` not yet in `sent[]` — REPAIR that key instead.
12. **Forbidden end state:** `Mode: DEFER` when `dol-gpt-<queueKey>.json` is already on `main` — use **REPAIR** (§1d) instead.
13. **Forbidden end state:** `Mode: DEFER` for bundle truncation on lessons with `chunkFiles.length > 12` — never attempt assembly; use §1d REPAIR if owner published.
14. **CHAT-DELIVERY** = manual chat with **no** GitHub connector only.
15. **Never disable, pause, or modify the hourly automation.** A content/read failure changes only repo pending/state files.

Open with: `Mode: FULL | REPAIR | REPAIR+FULL | REPAIR-NEXT | DEFER | COMMIT-PENDING | STATE-PENDING | CHAT-DELIVERY — <reason>`

**Progress guarantee:** Every **scheduled** run ends with **at least one connector commit** OR verified file already on `main`:

| Action | Result |
|--------|--------|
| **FULL** | New `dol-gpt-*.json` + `state.json` + `upcoming.json` advanced |
| **REPAIR** | State advanced only (JSON already on `main`) — allowed only when `queue[0]` has no bundle |
| **REPAIR+FULL** | Orphan state fixed **and** new `dol-gpt-*.json` for `queue[0]` in same run |
| **REPAIR-NEXT** | FULL for next queue key; failed target moved to `failed[]` |
| **DEFER** | `failed[]` updated only — entire run unreachable (rare) |
| **COMMIT-PENDING** | `dol-pending.json` committed — lesson parsed but lesson file commit failed; queue **not** advanced |
| **STATE-PENDING** | Lesson on `main`; `dol-state-pending.json` committed — state advance deferred to next run |

**Never invent vocabulary** — only publish content parsed from DOL `__NEXT_DATA__` JSON. **You may translate** parsed example sentences to Vietnamese and **may build IPA** from the app's UK shard files (§2d) — that is enrichment, not invention.

---

## Example enrichment (mandatory)

DOL source provides English `example` only. **Every item with a non-empty `example` MUST also have:**

| Field | Required | Rule |
|-------|----------|------|
| `example` | yes (from DOL) | English sentence from `vocabs[j].example` |
| `exampleVi` | **yes** | Natural Vietnamese translation of the full sentence (plain text) |
| `exampleIpa` | **yes** | UK RP IPA line — space-separated `/chunk/` per content word; **bold** headword token(s) with `<strong>` (HTML string) |

**HTML card** (in `sections[].html`) for each word with an example — **all four lines**:

```html
<p class="en ex">He finds it difficult to <strong>handle stress</strong> at work.</p>
<p class="ipa ex-ipa"><strong>/ˈhændl strɛs/</strong> /æt/ /wɜːk/</p>
<p class="vi ex-vi">Anh ấy thấy khó <strong>xử lý căng thẳng</strong> tại nơi làm việc.</p>
```

- **Bold** the headword (`text`) in English example and its Vietnamese gloss in `exampleVi` / HTML.
- IPA: prefer UK shards (`data/ipa/uk/<letter>.json` on repo); fallback to DOL `pronounce` for the headword only, still list other words from shards.
- **Commit gate:** if any item has `example` but missing `exampleVi` or `exampleIpa` → do **not** commit; complete enrichment first.

**Cards / app:** `items[].example` → `exEn`; `exampleVi` → Vietnamese; `exampleIpa` → IPA row (app reads these when present).

---

## Queue state

| File | Role |
|------|------|
| `data/chatgpt/dol/state.json` | `sent[]` processed pages |
| `data/chatgpt/dol/upcoming.json` | `queue[]` keys + optional `failed[]` |
| `data/chatgpt/dol/catalog.json` | URL lookup (`scripts/build_dol_queue.py`) |
| `data/chatgpt/dol/snapshots/<queueKey>/index.json` | Bundle index; always under 20 KB |
| `data/chatgpt/dol/snapshots/<queueKey>/items-NN.json` | Enriched item chunks listed by index; each under 20 KB |

The old monolithic `snapshots/<queueKey>.json` is **forbidden for connector reads** because ~90–130 KB responses truncate. This is the same size rule used by the working BBC prompt.

**Order:** IELTS Cambridge **20 → 9**, Practice Test Plus, Actual Test. Per test: Reading, then Listening.

**Resolve URL for target key:**

1. Find `queueKey` in `catalog.json` → matching `pages[].url` (**preferred**)
2. Else pattern: `cam20-t1-listening` → `https://tuhoc.dolenglish.vn/luyen-thi-ielts/tu-vung-cam-ielts-20-test-1-listening-vocab`
3. Never guess a different host — always `tuhoc.dolenglish.vn`

---

## §1 — Read state (repo files)

### §1a-0. Apply pending files (first action every run)

Read via §1a cascade (404 = none):

- `data/chatgpt/dol/dol-state-pending.json`
- `data/chatgpt/dol/dol-pending.json`

If **state-pending** exists and `dol-gpt-<queueKey>.json` is verified on `main` → advance `state`/`upcoming` per §5, delete `dol-state-pending.json`, Mode **REPAIR**. Stop if that completes the run.

If **commit-pending** exists and lesson file is **not** on `main`:

1. Ignore its old `attempts` / `lastError`; these describe the obsolete monolithic snapshot.
2. Load the connector bundle for its `queueKey` via §2a.
3. Build and commit the lesson via §3–§4.
4. After lesson verification, advance state/queue and **delete `dol-pending.json` in state commit B**.

Do not increment pending attempts when the connector bundle exists. Do not disable the automation.

### §1a. Read cascade (**overrides SHARED — connector allowed**)

For each repo file below, try **in order** until JSON parses. Fresh `?t=<unix_ts>` on URL steps.

| Step | Channel |
|------|---------|
| 1 | Pages GET `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/<path>?t=<ts>` |
| 2 | raw.githubusercontent.com `…/main/docs/claude-cowork/ielts-hourly-practice-tool/<path>?t=<ts>` |
| 3 | jsDelivr `https://cdn.jsdelivr.net/gh/mtm0101/public-sites@main/docs/claude-cowork/ielts-hourly-practice-tool/<path>` |
| 4 | **GitHub connector GET** `mtm0101/public-sites` branch **`main`** |

**Required reads every run:**

- `data/chatgpt/dol/state.json`
- `data/chatgpt/dol/upcoming.json`
- `data/chatgpt/dol/catalog.json`
- `data/templates/dol-vocab-template.json`
- `specs/09-dol-vocab.md` (optional if template suffices)

### §1c. Retry `failed[]` (before `queue[0]` — runs **before** §1b)

If `upcoming.json` has `failed[]` with any entry where `attempts < 3`:

1. Pick the **oldest** such entry (earliest `lastAt`, or first in array).
2. Use its `queueKey` + `url` as this run's target (**instead of** `queue[0]`).
3. **Ignore stale `lastError` text** (DNS, browsing, curl) when `data/chatgpt/dol/snapshots/<queueKey>/index.json` returns 200 — load §2a bundle and proceed to FULL.
4. On FULL success → remove from `failed[]` and from `queue[]` if still present; append to `sent[]`.
5. On another fetch failure (bundle 404 **and** §2b/§2c failed) → increment `attempts`, update `lastAt` / `lastError`; then continue with `queue[0]` per §2d.

Report retried key in confirmation: `Retry: cam20-t3-listening (failed[], attempt 2)`.

### §1b. REPAIR (orphan JSON on main — runs **after** §1c)

Scan `queue[]`, `failed[]`, and any key visible in recent commits for orphans: `dol-gpt-<queueKey>.json` exists on `main` but `queueKey` ∉ `sent[]`.

For each orphan found (process at most **one** orphan before continuing):

1. Read title/wordCount from existing JSON.
2. Append `sent[]` row; remove `queueKey` from `queue[]` and `failed[]` if present.
3. Commit `state.json` + `upcoming.json` (commit A).

**Do not stop after commit A when any of these is true:**

4. **Continue to FULL** in the **same run** when `queue[0]` (after orphan removal) has `snapshots/<queueKey>/index.json` on `main` — process `queue[0]` via §2a→§4. Confirmation: `Mode: REPAIR+FULL`.
5. Or `failed[]` still has an entry with `attempts < 3` and a connector bundle — return to §1c for that key.

**Stop (REPAIR only)** only when: orphan repaired, `failed[]` empty, and `queue[0]` has **no** connector bundle (404 on `index.json` after full §1a cascade).

If file exists **and** already in `sent` but still at `queue[0]` → dedupe queue, commit if needed, then continue to §1d for `queue[0]` (do not stop).

### §1d. Pre-published lesson on `main` (**runs before §2 — preferred path**)

For the current target `queueKey` (from §1c or `queue[0]`):

1. Try to read `data/chatgpt/dol/dol-gpt-<queueKey>.json` via jsDelivr → raw → Pages → connector (same order as §2a-i).
2. If the file parses and `id === "dol-gpt-<queueKey>"`:
   - If `queueKey` ∉ `sent[]` → append `sent[]`, remove from `queue[]` / `failed[]`, commit `state.json` + `upcoming.json`. Mode **REPAIR**. Report `Fetch: owner-prebuilt`. **Stop** unless §1b step 4 applies to the new `queue[0]`.
   - If already in `sent[]` but still in `queue[]` → dedupe queue, commit if needed, Mode **REPAIR**.
3. If the lesson file is **missing** on `main`:
   - Read `snapshots/<queueKey>/index.json` (if present).
   - If `chunkFiles.length > 12` or `itemCount > 150` → **skip §2a assembly**; use §2d REPAIR-NEXT (move to `failed[]` with `lastError: owner-publish-required`) and try the next queue key whose lesson file **is** on `main`.
   - Else → continue to §2 (small-lesson assembly allowed).

**Large-lesson rule:** 252-word / 18-chunk lessons (e.g. `cam18-t1-listening`) are **never** assembled in the scheduled sandbox. Owner publishes them; you **REPAIR** state only.

---

## §2 — Obtain DOL vocab (`doc`)

**Order (mandatory — do not skip §2a on scheduled runs):**

| Step | When | Method |
|------|------|--------|
| **§2a** | **Always first** | Read repo snapshot via §1a |
| **§2b** | Snapshot 404 / invalid only | Live Python fetch cascade |
| **§2c** | §2b failed only | Live browsing fallback |
| **§2d** | §2a–§2c failed | REPAIR-NEXT / DEFER |

### §2a. Connector-safe repo bundle (**small lessons only — ≤12 chunks, ≤150 items**)

**Skip this section entirely** when §1d step 3 applies (large bundle / owner-publish-required) or when §1d found the lesson on `main`.

Follow the working BBC read strategy: each file must be complete. **Enriched `items-NN.json` chunks often truncate via GitHub connector even under 20 KB** — use URL/CDN reads first for chunks.

**Hard limits (scheduled assembly):** do not start §2a when `index.chunkFiles.length > 12` or `index.itemCount > 150`.

#### §2a-i. Chunk read order (**differs from §1a state files**)

For `index.json` and each `items-NN.json`, try until JSON parses completely:

| Step | Channel |
|------|---------|
| 1 | jsDelivr `https://cdn.jsdelivr.net/gh/mtm0101/public-sites@main/docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/dol/snapshots/<queueKey>/<file>?t=<ts>` |
| 2 | raw.githubusercontent.com `…/main/docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/dol/snapshots/<queueKey>/<file>?t=<ts>` |
| 3 | Pages GET `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/dol/snapshots/<queueKey>/<file>?t=<ts>` |
| 4 | **GitHub connector GET** (last resort for chunks) |

Use §1a order (Pages → raw → jsDelivr → connector) only for `state.json`, `upcoming.json`, and `index.json` when CDN steps fail.

**Truncation signals:** `JSON.parse` error; body ends mid-string; missing closing `]}`; `items` shorter than the part should contain; `exampleVi`/`exampleIpa` cut off mid-field.

1. Read `data/chatgpt/dol/snapshots/<queueKey>/index.json` via §2a-i (or §1a for index only).
2. Parse `chunkFiles[]`.
3. Read **every listed file**, in order, via **§2a-i** (not connector-only).
4. Validate each chunk: matching `queueKey`, `part`, `totalParts`, and a complete `items[]`.
5. Concatenate all `items[]`; require `items.length === index.itemCount`.
6. Build `doc = index.docMeta`, then set:
   - `doc.source = "chatgpt"`
   - `doc.id = "dol-gpt-<queueKey>"`
   - `doc.items = concatenatedItems`
   - `doc.words = items.map(item => item.text)`
   - `doc.wordCount = items.length`
   - `doc.sections` rebuilt by passage (§3)

**Index shape:**

```json
{
  "schema": 2,
  "queueKey": "cam20-t2-reading",
  "url": "https://tuhoc.dolenglish.vn/…",
  "fetchedAt": "2026-07-11T01:00:00Z",
  "itemCount": 97,
  "chunkFiles": ["items-01.json", "items-02.json"],
  "docMeta": { "format": "dol-vocab", "wordCount": 97, … }
}
```

**Success criteria:**

- Every file parses completely (no truncation markers)
- Every chunk file is below **10 KB** on `main` (owner pipeline target; larger files may truncate via connector)
- Combined count equals `index.itemCount` and `docMeta.wordCount`
- Every item with `example` already has non-empty `exampleVi` and `exampleIpa`

The bundle is already enriched locally. **Do not call MyMemory, Google Translate, or IPA shard endpoints when the bundle passes validation.** Proceed directly to §3 and §4. Report `Fetch: connector-bundle` when connector was used for any file; `Fetch: jsdelivr-bundle` or `Fetch: raw-bundle` when CDN/raw served all chunks without connector.

**If index is missing (404 on all §2a-i steps):** continue to §2b — do not DEFER yet.

**If one chunk is unreadable on one channel:** retry that chunk through **all four §2a-i channels** before trying the next chunk or falling back to live fetch. Never fall back to the monolithic snapshot.

**Owner note (not agent action):** lessons are pre-published locally via `dol-done-publish-all.ps1` / `scripts/publish_dol_all.py` — if `dol-gpt-<queueKey>.json` is already on `main`, use §1b REPAIR instead of DEFER.

### §2b. Live Python fetch (**FALLBACK — only when §2a snapshot missing**)

**ChatGPT sandbox DNS often fails for `tuhoc.dolenglish.vn` while `curl --resolve` succeeds.** Run this script **once** per target URL (it retries internally). Set `URL` from catalog.

**Cascade inside the script (do not skip steps):**

| Step | Method | Retries |
|------|--------|---------|
| 1 | `urllib.request` direct | 3 × (5 s pause) |
| 2 | `subprocess` → `curl` direct | 2 × |
| 3 | `curl --resolve tuhoc.dolenglish.vn:443:176.97.118.19` (DNS bypass) | 2 × |

```python
import json, re, subprocess, time, urllib.request, urllib.parse

URL = "https://tuhoc.dolenglish.vn/luyen-thi-ielts/tu-vung-cam-ielts-20-test-1-listening-vocab"  # ← catalog URL
RESOLVE = "tuhoc.dolenglish.vn:443:176.97.118.19"  # vcdn.cloud — bypasses sandbox DNS
IPA_BASE = "https://raw.githubusercontent.com/mtm0101/public-sites/main/docs/claude-cowork/ielts-hourly-practice-tool/data/ipa/uk/"

POS = {"NOUN":"noun","VERB":"verb","ADJ":"adjective","ADV":"adverb","PHRASE":"phrase","PREP":"preposition","CONJ":"conjunction"}
_shard_cache = {}

def fetch_url(u, timeout=45):
    req = urllib.request.Request(u, headers={"User-Agent": "ielts-practice-tool/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def fetch_curl(args, timeout=50):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if r.returncode == 0 and "__NEXT_DATA__" in (r.stdout or ""):
        return r.stdout
    raise RuntimeError((r.stderr or r.stdout or "curl failed")[:200])

def fetch_html(url):
    errs = []
    for i in range(3):
        try:
            html = fetch_url(url)
            if "__NEXT_DATA__" in html:
                return html, "urllib"
        except Exception as e:
            errs.append(f"urllib{i}:{e}")
        time.sleep(5)
    for i in range(2):
        try:
            return fetch_curl(["curl","-sS","--max-time","45","-A","ielts-practice-tool/1.0",url]), "curl"
        except Exception as e:
            errs.append(f"curl{i}:{e}")
        time.sleep(5)
    for i in range(2):
        try:
            return fetch_curl(["curl","-sS","--max-time","45","-A","ielts-practice-tool/1.0",
                "--resolve", RESOLVE, url]), "curl-resolve"
        except Exception as e:
            errs.append(f"resolve{i}:{e}")
        time.sleep(5)
    raise RuntimeError("; ".join(errs[-4:]))

def inner(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m: raise ValueError("__NEXT_DATA__ missing")
    enc = json.loads(m.group(1))["props"]["pageProps"]["encryptedData"]
    return json.loads(urllib.parse.unquote(enc))

def wrap_ipa(raw):
    raw = (raw or "").strip().strip("/")
    return f"/{raw}/" if raw else ""

def uk_shard(letter):
    letter = (letter or "a").lower()
    if letter in _shard_cache: return _shard_cache[letter]
    try:
        data = json.loads(fetch_url(IPA_BASE + letter + ".json"))
    except Exception:
        data = {}
    _shard_cache[letter] = data
    return data

def lookup_uk(word):
    w = re.sub(r"[^a-z'-]", "", (word or "").lower())
    if not w: return ""
    shard = uk_shard(w[0])
    for t in [w, w.rstrip("'s"), w.rstrip("es"), w.rstrip("s")]:
        if t in shard: return wrap_ipa(shard[t])
    return ""

def example_tokens(text):
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text or "")

def headword_targets(hw):
    parts = [p for p in re.split(r"\s+", (hw or "").strip()) if p]
    return parts if parts else [hw] if hw else []

def token_matches_target(tokens, i, targets):
    low = [t.lower() for t in targets]
    for raw in low:
        ps = raw.split()
        if len(ps) == 1:
            if tokens[i].lower().strip("'") == ps[0].strip("'"): return True
        elif i + len(ps) <= len(tokens):
            if " ".join(tokens[i:i+len(ps)]).lower() == " ".join(ps): return True
    return False

def bold_phrase(text, phrase):
    if not text or not phrase: return text
    m = re.search(re.escape(phrase), text, re.I)
    if not m: return text
    return text[:m.start()] + "<strong>" + text[m.start():m.end()] + "</strong>" + text[m.end():]

def example_ipa_html(ex_en, headword, head_ipa):
    tokens = example_tokens(ex_en)
    if not tokens: return ""
    targets = headword_targets(headword)
    chunks = []
    for i, tok in enumerate(tokens):
        ipa = lookup_uk(tok)
        if not ipa and token_matches_target(tokens, i, targets) and head_ipa:
            ipa = head_ipa
        if not ipa: continue
        inner = ipa.strip("/")
        chunk = "/" + inner + "/"
        if token_matches_target(tokens, i, targets):
            chunk = "<strong>" + chunk + "</strong>"
        chunks.append(chunk)
    return " ".join(chunks)

def translate_gtx(text):
    q = urllib.parse.quote(text[:480])
    u = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=vi&dt=t&q=" + q
    try:
        data = json.loads(fetch_url(u, timeout=20))
        parts = data[0] if isinstance(data, list) and data else []
        out = "".join(p[0] for p in parts if isinstance(p, list) and p and p[0]).strip()
        if out and out.upper() != text.upper(): return out
    except Exception:
        pass
    return ""

def translate_vi(text):
    if not text: return ""
    q = urllib.parse.quote(text[:480])
    url = "https://api.mymemory.translated.net/get?q=" + q + "&langpair=en|vi"
    for attempt in range(4):
        try:
            data = json.loads(fetch_url(url, timeout=20))
            out = ((data.get("responseData") or {}).get("translatedText") or "").strip()
            if out and out.upper() != text.upper() and "MYMEMORY WARNING" not in out.upper():
                return out
        except Exception:
            pass
        time.sleep(0.35 * (attempt + 1))
    return translate_gtx(text)

def example_card_html(text, vn, ipa, ex, ex_vi, ex_ipa):
    head = f'<div class="head">{text} <span class="ipa">{ipa}</span></div><p class="vi">{vn}</p>'
    if not ex: return f'<div class="vocab dol-card">{head}</div>'
    ex_b = bold_phrase(ex, text)
    vi_plain = ex_vi or ""
    vi_b = bold_phrase(vi_plain, (vn.split(". ", 1)[-1] if ". " in vn else "").split("(")[0].strip()) if vi_plain else ""
    if not vi_b and vi_plain: vi_b = vi_plain
    return (f'<div class="vocab dol-card">{head}'
        f'<p class="en ex">{ex_b}</p>'
        + (f'<p class="ipa ex-ipa">{ex_ipa}</p>' if ex_ipa else '')
        + (f'<p class="vi ex-vi">{vi_b}</p>' if vi_b else '')
        + '</div>')

html, fetch_method = fetch_html(URL)
data = inner(html)
url_info = data.get("urlInfo") or {}
book = (url_info.get("book") or {}).get("name") or ""
dol = url_info.get("dol") or {}
page = (data.get("data") or {}).get("data") or {}
skill = ((url_info.get("data") or {}).get("skill") or page.get("skill") or "").lower()
title = (dol.get("title") or page.get("name") or book).replace("Từ Vựng IELTS Online Test ", "").strip()
test_m = re.search(r"test\s*(\d+)", page.get("name") or title, re.I)
test_num = int(test_m.group(1)) if test_m else int(re.search(r"test-(\d+)", URL, re.I).group(1))

items, words, sections = [], [], []
missing_vi = 0
for pi, sec in enumerate(page.get("testSections") or [], 1):
    pname = (sec.get("name") or f"Part {pi}").strip()
    plabel = ("Section" if skill == "listening" else "Passage") + f" {pi}: {pname}"
    cards = []
    for vi, v in enumerate((sec.get("vocab") or {}).get("vocabs") or []):
        text = (v.get("value") or "").strip()
        if not text: continue
        pos = POS.get((v.get("type") or "").upper(), (v.get("type") or "").lower())
        vn_raw = (v.get("meaning") or "").strip()
        vn = f"({pos}). {vn_raw}" if pos and vn_raw else vn_raw
        ex = (v.get("example") or "").strip()
        ipa = wrap_ipa(v.get("pronounce") or "")
        ex_vi, ex_ipa = "", ""
        if ex:
            ex_ipa = example_ipa_html(ex, text, ipa)
            ex_vi = translate_vi(ex)
            if not ex_vi: missing_vi += 1
            time.sleep(0.2)
        iid = f"p{pi}-{re.sub(r'[^\w\s-]','',text.lower())[:40]}-{vi}"
        rec = {"id": iid, "passageLabel": plabel, "passageName": pname, "passageNum": pi,
            "text": text, "pos": pos, "vn": vn, "ipaUK": ipa, "example": ex,
            "questionGroup": (v.get("group") or "").strip()}
        if ex:
            rec["exampleVi"] = ex_vi
            rec["exampleIpa"] = ex_ipa
        items.append(rec)
        words.append(text)
        cards.append(example_card_html(text, vn, ipa, ex, ex_vi, ex_ipa))
    if cards:
        sections.append({"id": f"passage-{pi}", "title": plabel, "level": 1, "html": "\n".join(cards)})

bn_m = re.search(r"(\d+)", book)
bn = int(bn_m.group(1)) if bn_m else 0
group = "IELTS Practice Test Plus" if "practice test plus" in book.lower() else (
    "IELTS Actual Test" if "actual test" in book.lower() else "IELTS Cambridge")
prefix = "ptp" if group.startswith("IELTS Practice") else ("actual" if group.startswith("IELTS Actual") else "cam")
qkey = f"{prefix}{bn}-t{test_num}-{skill}"

sections.append({"id": "sources", "title": "Sources", "level": 1,
    "html": f'<p class="en">Vocabulary sourced from <a class="ext-link" href="{URL}" target="_blank" rel="noopener">DOL Tự học</a> for personal IELTS study.</p>'
            f'<p class="vi">Từ vựng lấy từ DOL Tự học — chỉ phục vụ học tập cá nhân.</p>'})

doc = {"schema": 2, "format": "dol-vocab", "id": f"dol-gpt-{qkey}", "type": "vocab", "source": "chatgpt",
    "category": "dol-vocab", "topicNumber": 0, "title": title, "group": group, "book": book,
    "bookSlug": ((url_info.get("book") or {}).get("url") or "").strip("/"), "bookNum": bn or None,
    "testNum": test_num, "skill": skill, "url": URL, "dateTime": "2026-07-10T00:00",
    "wordCount": len(items), "words": words, "items": items, "sections": sections, "queueKey": qkey}

with_ex = [it for it in items if it.get("example")]
bad = [it for it in with_ex if not it.get("exampleVi") or not it.get("exampleIpa")]
print(json.dumps({"ok": True, "queueKey": qkey, "fetch": fetch_method, "wordCount": len(items),
    "withExample": len(with_ex), "missingEnrichment": len(bad), "mymemoryMiss": missing_vi, "title": title}, ensure_ascii=False))
if bad:
    print("WARN: items missing exampleVi/exampleIpa — you MUST fill manually before commit:", [b["text"] for b in bad[:5]])
print("---FULL_JSON---")
print(json.dumps(doc, ensure_ascii=False, indent=1))
```

**Success criteria:** stdout contains `---FULL_JSON---`, `doc.items` length ≥ 1, and **every** item with `example` has non-empty `exampleVi` + `exampleIpa`.

**If `missingEnrichment` > 0:** you (the agent) MUST translate / build IPA for those items yourself before commit — do not publish partial examples. MyMemory quota exhausted → use agent translation + keep `exampleIpa`; never omit `example` from DOL source.

**If all Python cascade steps fail (incl. `curl-resolve`):** continue to §2c immediately.

**Reference implementation:** `scripts/dol_vocab_utils.py`, `scripts/fetch_dol_vocab.py`, `scripts/publish_dol_all.py`

### §2c. Browsing-tool fallback (**live page only — only when §2a+§2b failed**)

If §2a fails OR returns no `---FULL_JSON---`:

**Forbidden:** cache lookup, search snippets, "browsing cache", or summarised page text without `__NEXT_DATA__`.

**Required sequence (retry full sequence twice, 10 s between):**

1. **Navigate** to the exact catalog `url` (full HTTPS).
2. **Wait 15 s** for client-side render.
3. Read page source / DOM → locate `<script id="__NEXT_DATA__" type="application/json">…</script>`.
4. If step 3 fails: open the **book landing URL** from `catalog.json` for that `queueKey`, wait 15 s, find the vocab link for this test + skill, navigate to it, repeat step 3.
5. Parse `encryptedData` → same fields as §2b; run **example enrichment**.

**If browsing succeeds while Python failed:** proceed directly to **§4** — Mode **FULL**, `Fetch: browse`. Do **not** stop with CHAT-DELIVERY.

Still no `__NEXT_DATA__` after both §2c rounds → §2d.

### §2d. REPAIR-NEXT (same run — queue must move)

If the current target (`queue[0]` or §1c `failed[]` retry) failed §2a + §2b + §2c:

1. Append or update `upcoming.json` → `failed[]` (create array if missing):

```json
{"queueKey": "cam20-t1-listening", "url": "https://…", "lastError": "<short incl. fetch steps tried>", "lastAt": "<ISO>", "attempts": 1}
```

If key already in `failed[]`, increment `attempts` (do not reset to 1).

2. Remove that key from `queue[]` (front) if present.
3. **Immediately** process new `queue[0]` — repeat §2 from the top (**§2a snapshot first**).
4. On success → Mode **REPAIR-NEXT** (report deferred key + new FULL file).
5. If new `queue[0]` also fails after full cascade → repeat (max **4** deferrals per run).
6. If all attempts in one run fail → Mode **DEFER** — commit `upcoming.json` with updated `failed[]` only; set `lastError` to include `snapshot-missing` when §2a was 404; **never** leave queue unchanged with zero commits.

**Do not** use Mode SKIP for fetch failures.

---

## §3 — Build output file

**Path:** `data/chatgpt/dol/dol-gpt-<queueKey>.json`

Follow [`data/templates/dol-vocab-template.json`](../../data/templates/dol-vocab-template.json) and [`specs/09-dol-vocab.md`](../../specs/09-dol-vocab.md).

| Field | Rule |
|-------|------|
| `format` | `"dol-vocab"` |
| `id` | `dol-gpt-<queueKey>` |
| `queueKey` | must match processed queue key |
| `items[]` | all words; include `example`, `exampleVi`, `exampleIpa`, `ipaUK`, `vn`, `passageLabel` |
| `sections[]` | one per passage + `sources`; each card with example has `p.en.ex` + `p.ipa.ex-ipa` + `p.vi.ex-vi` |
| `words[]` | headwords in order |
| `wordCount` | `items.length` |

**Rebuild `sections[]` from bundle items:**

1. Group items by ascending `passageNum`.
2. One section per passage: `id = "passage-N"`, title from first item's `passageLabel`.
3. One `.vocab.dol-card` per item in source order.
4. For an item with `example`, emit head + meaning + all required example lines:
   `<p class="en ex">`, `<p class="ipa ex-ipa">`, `<p class="vi ex-vi">`.
5. Append `sources` section with the DOL URL and personal-study attribution.

The final lesson may exceed 90 KB. This affects connector **reads**, not connector **writes**; the previously published DOL files prove inline connector writes work. Pass the serialized JSON text directly as `content`.

**Privacy:** Strip `createdBy`, `lastModifiedBy`, emails, personal names from any DOL CMS fields.

---

## §4 — GitHub connector write (**scheduled runs — mandatory**)

DOL lesson JSON is typically **40–90 KB**. This is **expected** and commits successfully when you follow this protocol.

### §4a. Prepare file body (in memory — not a sandbox upload)

1. Hold the parsed `doc` object from §2 (Python stdout after `---FULL_JSON---`, or rebuilt from browsing parse).
2. Serialize once: `body = json.dumps(doc, ensure_ascii=False, indent=1)` (pretty) or `separators=(',',':')` if retry needs smaller payload.
3. **The connector needs the JSON text as the file `content` / `contents` field** in its create-or-update-file action.

**FORBIDDEN write methods (these cause "could not ingest local artifact" errors):**

- Uploading `/mnt/data/…`, code-interpreter output files, or "generated artifacts"
- Referencing a sandbox path instead of passing the string body
- Pasting the full JSON only in chat without a connector write (scheduled runs)

**Required write method:**

```
GitHub connector → create or update file
  repo:   mtm0101/public-sites
  branch: main
  path:   docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/dol/dol-gpt-<queueKey>.json
  content: <body — full JSON string from step 2>
  message: dol vocab (chatgpt): dol-gpt-<queueKey>.json
```

You may keep `doc` in your working context and serialize at commit time — you do **not** need a local file on disk.

### §4b. Two-step commit (preferred)

| Step | Files | When |
|------|-------|------|
| **A** | `dol-gpt-<queueKey>.json` only | Always first |
| **B** | `state.json` + `upcoming.json` | Only after **A verified** on `main` |

**Verify A** before B (at least one):

- `https://raw.githubusercontent.com/mtm0101/public-sites/main/docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/dol/dol-gpt-<queueKey>.json?t=<ts>` → 200, `wordCount` matches
- Connector GET same path → parses as JSON

**Re-read** `state.json` + `upcoming.json` via §1a immediately before step B.

Commit message B: `dol vocab state: advance <queueKey>`

### §4c. Connector failure retry (same run — before giving up)

If step A fails (artifact error, size error, timeout):

1. **A2** — same path, pass `body` again as inline string (re-serialize from `doc`).
2. **A3** — minified JSON (`separators=(',',':')`, no indent).
3. **A4** — connector update-file if create-file was rejected as duplicate.

If **A2–A4 all fail** but `doc` is valid → **COMMIT-PENDING** (do **not** use CHAT-DELIVERY):

Commit only `docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/dol/dol-pending.json`:

```json
{
  "schema": 1,
  "queueKey": "cam20-t3-reading",
  "jsonFile": "dol-gpt-cam20-t3-reading.json",
  "title": "CAM IELTS 20 - Reading Test 3",
  "wordCount": 98,
  "url": "https://tuhoc.dolenglish.vn/…",
  "status": "lesson-commit-failed",
  "lastError": "<connector error, 1 line>",
  "requestedAt": "<ISO timestamp>"
}
```

- Mode **COMMIT-PENDING** — queue **unchanged** (correct: lesson not on `main` yet).
- **Must still produce a verified commit SHA** for `dol-pending.json`.
- Next run: read `dol-pending.json` first; retry §4 lesson commit with freshly parsed or cached `doc`.

If step A succeeds but step B fails → **STATE-PENDING**:

Commit `dol-state-pending.json` (~350 B):

```json
{
  "schema": 1,
  "queueKey": "cam20-t3-reading",
  "jsonFile": "dol-gpt-cam20-t3-reading.json",
  "title": "CAM IELTS 20 - Reading Test 3",
  "wordCount": 98,
  "processedAt": "<ISO>",
  "requestedAt": "<ISO>"
}
```

Next run: apply state advance from pending file, delete pending, Mode **REPAIR**.

### §4d. Apply pending (first action when present)

Read `dol-pending.json` and `dol-state-pending.json` via §1a (404 = none).

- **state-pending exists** + lesson file verified on `main` → advance `state`/`upcoming`, delete pending, Mode **REPAIR**.
- **commit-pending exists** + lesson file **not** on `main` → retry §4 lesson commit for that `queueKey` before processing `queue[0]`.

---

## §5 — Advance state

After verified commit of JSON:

```json
{
  "queueKey": "cam20-t1-listening",
  "url": "https://…",
  "title": "CAM IELTS 20 - Listening Test 1",
  "group": "IELTS Cambridge",
  "book": "CAM IELTS 20",
  "skill": "listening",
  "testNum": 1,
  "processedAt": "<ISO>",
  "jsonFile": "dol-gpt-cam20-t1-listening.json",
  "wordCount": 114
}
```

Remove processed key from `queue[]`. Commit `state.json` + `upcoming.json`.

**Do not** edit `manifest.json` — owner runs `python scripts/convert_lessons.py`.

---

## §6 — Delivery

**Scheduled FULL / REPAIR / COMMIT-PENDING:** short confirmation only — **never** print the full lesson JSON in chat.

```
Mode: FULL | REPAIR | REPAIR+FULL | REPAIR-NEXT | DEFER | COMMIT-PENDING | STATE-PENDING
Episode: CAM IELTS 20 · Reading Test 3 (cam20-t3-reading)
Words: 98 · Passages: 3 · Examples enriched: 98/98 (VI + IPA)
File: dol-gpt-cam20-t3-reading.json
Queue remaining: N · Failed/deferred: M
Fetch: connector-bundle | urllib | curl | curl-resolve | browse | repair-next
Commit: <sha>
Commit link: https://github.com/mtm0101/public-sites/commit/<sha>
Branch: main (verified)
File(s): https://github.com/mtm0101/public-sites/blob/main/docs/claude-cowork/ielts-hourly-practice-tool/data/chatgpt/dol/dol-gpt-<key>.json
Manifest: deferred (owner pipeline)
```

**COMMIT-PENDING confirmation** must include: `Next run: retry lesson commit for <queueKey>`.

**CHAT-DELIVERY (manual chat only — §6b):**

---

## §6b — CHAT-DELIVERY split blocks (manual chat without connector ONLY)

Never use on scheduled automation. Split into labeled blocks (do not dump one 90 KB JSON):

| Block | Label | Content |
|-------|-------|---------|
| 1 | `DOL_META` | Top-level fields **except** `items`, `sections`, `words` |
| 2 | `DOL_ITEMS` | `{"items":[…]}` |
| 3 | `DOL_SECTIONS` | `{"sections":[…]}` |
| 4 | `DOL_WORDS` | `{"words":[…]}` |
| 5 | `DOL_STATE` | Updated `state.json` + `upcoming.json` |

Merge rule: combine blocks → save as `dol-gpt-<queueKey>.json`; update state files locally.

```
Commit: none — no new commit on main this run
Reason: CHAT-DELIVERY (manual chat — split blocks above)
```

---

## Attribution

- `sources` section: [DOL Tự học](https://tuhoc.dolenglish.vn/luyen-thi-ielts/free-ielts-online-test) — personal study only.
- No personal names from DOL CMS in JSON or chat.

---

**Not fetched by the agent.** Frozen bootstrap: [`schedulers/dol-vocab.scheduler.md`](./schedulers/dol-vocab.scheduler.md). **All behavior lives in this file** (fetched every run with `?t=`).
