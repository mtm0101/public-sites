"""Shared helpers for DOL English vocab scrape → JSON."""
from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urljoin

BASE = "https://tuhoc.dolenglish.vn/"
DOL_RESOLVE = "tuhoc.dolenglish.vn:443:176.97.118.19"
ROOT = Path(__file__).resolve().parent.parent
IPA_UK_DIR = ROOT / "data" / "ipa" / "uk"
POS_MAP = {
    "NOUN": "noun",
    "VERB": "verb",
    "ADJ": "adjective",
    "ADV": "adverb",
    "PHRASE": "phrase",
    "PREP": "preposition",
    "CONJ": "conjunction",
}


def fetch_html(url: str, timeout: int = 45) -> str:
    """Fetch DOL page HTML with urllib → curl → curl --resolve cascade."""
    errs: list[str] = []
    headers = {"User-Agent": "ielts-practice-tool/1.0"}
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                html = resp.read().decode("utf-8", "replace")
            if "__NEXT_DATA__" in html:
                return html
        except OSError as e:
            errs.append(f"urllib{i}:{e}")
        time.sleep(5)
    curl_args = [
        ["curl.exe", "-sS", "--noproxy", "*", "--ssl-no-revoke", "--max-time", str(timeout), "-A", headers["User-Agent"], url],
        [
            "curl.exe",
            "-sS",
            "--noproxy",
            "*",
            "--ssl-no-revoke",
            "--max-time",
            str(timeout),
            "-A",
            headers["User-Agent"],
            "--resolve",
            DOL_RESOLVE,
            url,
        ],
    ]
    for label, args in zip(("curl", "curl-resolve"), curl_args):
        for i in range(2):
            try:
                r = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=timeout + 5,
                    check=False,
                )
                if r.returncode == 0 and "__NEXT_DATA__" in (r.stdout or ""):
                    return r.stdout
                errs.append(f"{label}{i}:{(r.stderr or r.stdout or 'fail')[:120]}")
            except OSError as e:
                errs.append(f"{label}{i}:{e}")
            time.sleep(5)
    raise RuntimeError("; ".join(errs[-4:]))


def extract_next_inner(html: str) -> dict:
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        html,
        re.S,
    )
    if not m:
        raise ValueError("__NEXT_DATA__ not found")
    outer = json.loads(m.group(1))
    enc = outer.get("props", {}).get("pageProps", {}).get("encryptedData", "")
    if not enc:
        raise ValueError("encryptedData missing")
    return json.loads(unquote(enc))


def extract_book_stats(html: str) -> dict:
    """Parse DOL book landing page — testTakers (lượt làm), views, test list."""
    inner = extract_next_inner(html)
    bd = (inner.get("data") or {}).get("bookDetail") or {}
    seo = bd.get("seoPage") or {}
    url_info = inner.get("urlInfo") or {}
    tests_out = []
    for t in bd.get("tests") or []:
        pages = t.get("pages") or []
        page_views = sum(int(p.get("views") or 0) for p in pages)
        tests_out.append(
            {
                "name": t.get("name") or "",
                "pageViews": page_views,
                "pages": len(pages),
            }
        )
    return {
        "name": bd.get("name") or "",
        "testTakers": bd.get("testTakers"),
        "views": seo.get("views") or url_info.get("views"),
        "noOfTests": bd.get("noOfTests"),
        "noOfReadingTests": bd.get("noOfReadingTests"),
        "noOfListeningTests": bd.get("noOfListeningTests"),
        "tests": tests_out,
    }


def slugify(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s[:max_len] or "item"


def wrap_ipa(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("/") and raw.endswith("/"):
        return raw
    return f"/{raw}/"


def infer_group(book_name: str, url: str = "") -> str:
    n = (book_name or "").lower()
    u = (url or "").lower()
    if "practice test plus" in n or "practice-test-plus" in u:
        return "IELTS Practice Test Plus"
    if "actual test" in n or "recent-actual-test" in u:
        return "IELTS Actual Test"
    return "IELTS Cambridge"


def passage_label(skill: str, num: int, name: str) -> str:
    skill = (skill or "").upper()
    prefix = "Section" if skill == "LISTENING" else "Passage"
    return f"{prefix} {num}: {name}"


def book_num_from_name(name: str) -> int | None:
    m = re.search(r"(\d+)", name or "")
    return int(m.group(1)) if m else None


def queue_key(group: str, book: str, test_num: int, skill: str) -> str:
    g = infer_group(book)
    bn = book_num_from_name(book) or 0
    prefix = "cam"
    if g == "IELTS Practice Test Plus":
        prefix = "ptp"
    elif g == "IELTS Actual Test":
        prefix = "actual"
    sk = "reading" if (skill or "").upper() == "READING" else "listening"
    return f"{prefix}{bn}-t{test_num}-{sk}"


def queue_key_from_url(url: str) -> str | None:
    u = (url or "").lower()
    skill = "listening" if "listening" in u else "reading" if "reading" in u else None
    if not skill:
        return None
    # Vocab slugs use "-test-N-reading|listening" — must not match book id
    # "actual-test-2" before the real test number in "...actual-test-2-test-7-listening..."
    tm = re.search(r"-test-(\d+)-(?:reading|listening)", u)
    if not tm:
        tm = re.search(r"test[-_ ]?(\d+)", u)
    if not tm:
        return None
    test_num = int(tm.group(1))
    for pat in (
        r"cambridge-ielts-(\d+)",
        r"cam-ielts-(\d+)",
        r"tu-vung-cam-ielts-(\d+)",
        r"tu-vung-cam-(\d+)",
        r"cam-(\d+)",
    ):
        m = re.search(pat, u)
        if m:
            return queue_key("IELTS Cambridge", f"CAM IELTS {m.group(1)}", test_num, skill)
    ptp = re.search(r"practice-test-plus-(\d+)", u)
    if ptp:
        return queue_key(
            "IELTS Practice Test Plus",
            f"Practice Test Plus {ptp.group(1)}",
            test_num,
            skill,
        )
    act = re.search(r"recent-actual-test-(\d+)|actual-test-(\d+)", u)
    if act:
        n = act.group(1) or act.group(2)
        return queue_key("IELTS Actual Test", f"Actual Test {n}", test_num, skill)
    return None


def parse_vocab_page(html: str, url: str, *, enrich: bool = True) -> dict:
    inner = extract_next_inner(html)
    url_info = inner.get("urlInfo") or {}
    book = url_info.get("book") or {}
    dol = url_info.get("dol") or {}
    page_data = (inner.get("data") or {}).get("data") or {}
    skill = ((url_info.get("data") or {}).get("skill") or page_data.get("skill") or "").lower()
    book_name = book.get("name") or ""
    group = infer_group(book_name, url)
    title = dol.get("title") or page_data.get("name") or book_name
    test_name = page_data.get("name") or title

    test_num = None
    m = re.search(r"test\s*(\d+)", test_name, re.I)
    if m:
        test_num = int(m.group(1))
    if test_num is None:
        m = re.search(r"test-(\d+)", url, re.I)
        test_num = int(m.group(1)) if m else 1

    book_num = book_num_from_name(book_name)
    qkey = queue_key(group, book_name, test_num, skill)
    file_id = f"dol-gpt-{qkey}"

    items = []
    words = []
    sections = []

    for pi, sec in enumerate(page_data.get("testSections") or [], start=1):
        pname = (sec.get("name") or f"Part {pi}").strip()
        plabel = passage_label(skill, pi, pname)
        passage_items = []
        for vi, v in enumerate((sec.get("vocab") or {}).get("vocabs") or []):
            text = (v.get("value") or "").strip()
            if not text:
                continue
            pos = POS_MAP.get((v.get("type") or "").upper(), (v.get("type") or "").lower())
            vn_raw = (v.get("meaning") or "").strip()
            vn = f"({pos}). {vn_raw}" if pos and vn_raw else vn_raw
            item_id = f"p{pi}-{slugify(text)}-{vi}"
            ex = (v.get("example") or "").strip()
            rec = {
                "id": item_id,
                "passageLabel": plabel,
                "passageName": pname,
                "passageNum": pi,
                "text": text,
                "pos": pos,
                "vn": vn,
                "example": ex,
                "questionGroup": (v.get("group") or "").strip(),
            }
            passage_items.append(rec)
            items.append(rec)
            words.append(text)
        if passage_items:
            cards = [
                example_card_html(
                    x.get("text") or "",
                    x.get("vn") or "",
                    x.get("example") or "",
                    x.get("exampleVi") or "",
                )
                for x in passage_items
            ]
            sections.append(
                {
                    "id": f"passage-{pi}",
                    "title": plabel,
                    "level": 1,
                    "html": "\n".join(cards),
                }
            )

    sections.append(
        {
            "id": "sources",
            "title": "Sources",
            "level": 1,
            "html": (
                f'<p class="en">Vocabulary sourced from '
                f'<a class="ext-link" href="{url}" target="_blank" rel="noopener">DOL Tự học</a> '
                f"({book_name} · {test_name}) for personal IELTS study.</p>"
                f'<p class="vi">Từ vựng lấy từ DOL Tự học — chỉ phục vụ học tập cá nhân.</p>'
                f'<p class="note">© DOL English · Not affiliated with Cambridge Assessment.</p>'
            ),
        }
    )

    doc = {
        "schema": 2,
        "format": "dol-vocab",
        "id": file_id,
        "type": "vocab",
        "source": "chatgpt",
        "category": "dol-vocab",
        "topicNumber": 0,
        "title": title.replace("Từ Vựng IELTS Online Test ", "").strip(),
        "group": group,
        "book": book_name,
        "bookSlug": (book.get("url") or "").strip("/"),
        "bookNum": book_num,
        "testNum": test_num,
        "skill": skill,
        "url": url,
        "dateTime": (url_info.get("lastModifiedAt") or "")[:16].replace("T", "T") or "2026-07-10T00:00",
        "wordCount": len(items),
        "words": words,
        "items": items,
        "sections": sections,
        "queueKey": qkey,
    }
    if enrich:
        enrich_doc_examples(doc, translate=True, rebuild_html=True)
    return doc


_VOCAB_PATH = re.compile(r"^/?luyen-thi-ielts/[\w\-/]*vocab[\w\-/]*$", re.I)


def _norm_vocab_url(raw: str) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip().split("?")[0].split("#")[0]
    if " " in s or "<" in s or "{" in s:
        return None
    if not _VOCAB_PATH.match(s.lstrip("/")):
        return None
    return urljoin(BASE, s.lstrip("/"))


def discover_vocab_links(html: str) -> list[str]:
    """Find absolute vocab page URLs in a DOL book/landing HTML."""
    found = set()
    for m in re.finditer(
        r"(https://tuhoc\.dolenglish\.vn/luyen-thi-ielts/[\w\-/]*vocab[\w\-/]*)",
        html,
        re.I,
    ):
        u = _norm_vocab_url(m.group(1))
        if u:
            found.add(u)
    for m in re.finditer(r'"(/luyen-thi-ielts/[\w\-/]*vocab[\w\-/]*)"', html, re.I):
        u = _norm_vocab_url(m.group(1))
        if u:
            found.add(u)
    try:
        inner = extract_next_inner(html)
    except ValueError:
        return sorted(found)

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                if isinstance(v, str):
                    u = _norm_vocab_url(v)
                    if u:
                        found.add(u)
                else:
                    walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(inner)
    return sorted(found)


# --- Example enrichment (VI translation + UK IPA) ---

_uk_shard_cache: dict[str, dict] = {}


def _load_uk_shard(letter: str) -> dict:
    letter = (letter or "a").lower()
    if letter in _uk_shard_cache:
        return _uk_shard_cache[letter]
    path = IPA_UK_DIR / f"{letter}.json"
    data = {}
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    _uk_shard_cache[letter] = data
    return data


def _lookup_uk_ipa(word: str) -> str:
    w = re.sub(r"[^a-z'-]", "", (word or "").lower())
    if not w:
        return ""
    shard = _load_uk_shard(w[0])
    for t in (w, w.rstrip("'s"), w.rstrip("es"), w.rstrip("s")):
        if t in shard:
            return wrap_ipa(shard[t])
    return ""


def _example_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text or "")


def _headword_targets(hw: str) -> list[str]:
    parts = [p for p in re.split(r"\s+", (hw or "").strip()) if p]
    return parts if parts else ([hw] if hw else [])


def _token_matches_target(tokens: list[str], i: int, targets: list[str]) -> bool:
    low = [t.lower() for t in targets]
    for raw in low:
        ps = raw.split()
        if len(ps) == 1:
            if tokens[i].lower().strip("'") == ps[0].strip("'"):
                return True
        elif i + len(ps) <= len(tokens):
            if " ".join(tokens[i : i + len(ps)]).lower() == " ".join(ps):
                return True
    return False


def _bold_phrase(text: str, phrase: str) -> str:
    if not text or not phrase:
        return text
    m = re.search(re.escape(phrase), text, re.I)
    if not m:
        return text
    return (
        text[: m.start()]
        + "<strong>"
        + text[m.start() : m.end()]
        + "</strong>"
        + text[m.end() :]
    )


def _vn_gloss(vn: str) -> str:
    if ". " in vn:
        return vn.split(". ", 1)[-1].strip()
    return vn.strip()


def example_ipa_html(ex_en: str, headword: str, head_ipa: str) -> str:
    tokens = _example_tokens(ex_en)
    if not tokens:
        return ""
    targets = _headword_targets(headword)
    chunks = []
    for i, tok in enumerate(tokens):
        ipa = _lookup_uk_ipa(tok)
        if not ipa and _token_matches_target(tokens, i, targets) and head_ipa:
            ipa = head_ipa
        if not ipa:
            continue
        inner = ipa.strip("/")
        chunk = f"/{inner}/"
        if _token_matches_target(tokens, i, targets):
            chunk = f"<strong>{chunk}</strong>"
        chunks.append(chunk)
    return " ".join(chunks)


# Primary translator for batch enrichment. Google gtx is faster and is not
# rate-limited as aggressively as MyMemory, so bulk publishing defaults to it
# (the app itself still prefers MyMemory because gtx lacks a CORS header).
PRIMARY_TRANSLATOR = "gtx"  # "gtx" | "mymemory"

# On-disk translation cache so re-runs never re-translate the same sentence.
# Lives next to the scripts (outside data/) so convert_lessons.py never indexes it.
_TRANSLATE_CACHE_PATH = Path(__file__).resolve().parent / ".dol-translate-cache.json"
_translate_cache: dict | None = None
_translate_cache_dirty = False


def _load_translate_cache() -> dict:
    global _translate_cache
    if _translate_cache is None:
        try:
            _translate_cache = json.loads(
                _TRANSLATE_CACHE_PATH.read_text(encoding="utf-8")
            )
            if not isinstance(_translate_cache, dict):
                _translate_cache = {}
        except (OSError, json.JSONDecodeError):
            _translate_cache = {}
    return _translate_cache


def save_translate_cache() -> None:
    """Flush the in-memory translation cache to disk if it changed."""
    global _translate_cache_dirty
    if _translate_cache is None or not _translate_cache_dirty:
        return
    try:
        _TRANSLATE_CACHE_PATH.write_text(
            json.dumps(_translate_cache, ensure_ascii=False), encoding="utf-8"
        )
        _translate_cache_dirty = False
    except OSError:
        pass


def _cache_put(key: str, value: str) -> None:
    global _translate_cache_dirty
    cache = _load_translate_cache()
    cache[key] = value
    _translate_cache_dirty = True


def translate_gtx_vi(text: str) -> str:
    if not text:
        return ""
    q = urllib.parse.quote(text[:480])
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=vi&dt=t&q={q}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ielts-practice-tool/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        parts = data[0] if isinstance(data, list) and data else []
        out = "".join(p[0] for p in parts if isinstance(p, list) and p and p[0]).strip()
        if out and out.upper() != text.upper():
            return out
    except (OSError, json.JSONDecodeError, urllib.error.URLError, IndexError, TypeError):
        pass
    return ""


def translate_mymemory_vi(text: str, delay: float = 0.35) -> str:
    if not text:
        return ""
    q = urllib.parse.quote(text[:480])
    url = f"https://api.mymemory.translated.net/get?q={q}&langpair=en|vi"
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ielts-practice-tool/1.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            out = ((data.get("responseData") or {}).get("translatedText") or "").strip()
            if out and out.upper() != text.upper() and "MYMEMORY WARNING" not in out.upper():
                time.sleep(delay)
                return out
        except (OSError, json.JSONDecodeError, urllib.error.URLError):
            pass
        time.sleep(delay * (attempt + 2))
    return ""


def translate_example_vi(text: str, delay: float = 0.35) -> str:
    if not text:
        return ""
    key = text[:480]
    cache = _load_translate_cache()
    if key in cache:
        return cache[key]

    if PRIMARY_TRANSLATOR == "gtx":
        out = translate_gtx_vi(text)
        if not out:
            out = translate_mymemory_vi(text, delay)
        elif delay:
            time.sleep(delay)
    else:
        out = translate_mymemory_vi(text, delay)
        if not out:
            out = translate_gtx_vi(text)
            if out and delay:
                time.sleep(delay)

    if out:
        _cache_put(key, out)
    return out


def example_card_html(text: str, vn: str, ex: str, ex_vi: str) -> str:
    """Vocab card HTML. IPA is omitted — index.html lazy-loads from local shards."""
    head = f'<div class="head">{text} <span class="ipa"></span></div><p class="vi">{vn}</p>'
    if not ex:
        return f'<div class="vocab dol-card">{head}</div>'
    ex_b = _bold_phrase(ex, text)
    gloss = _vn_gloss(vn)
    vi_b = _bold_phrase(ex_vi, gloss) if ex_vi else ""
    parts = [
        f'<div class="vocab dol-card">{head}',
        f'<p class="en ex">{ex_b}</p>',
    ]
    if vi_b:
        parts.append(f'<p class="vi ex-vi">{vi_b}</p>')
    parts.append("</div>")
    return "".join(parts)


def enrich_item_examples(item: dict, *, translate: bool = True) -> bool:
    """Add exampleVi to one item. IPA is left to index.html at render time."""
    ex = (item.get("example") or "").strip()
    if not ex:
        return False
    changed = False
    if translate and not (item.get("exampleVi") or "").strip():
        vi = translate_example_vi(ex)
        if vi:
            item["exampleVi"] = vi
            changed = True
    return changed


def rebuild_passage_sections(doc: dict) -> None:
    """Rebuild vocab passage sections from items[] (keeps sources section)."""
    skill = (doc.get("skill") or "").lower()
    by_passage: dict[int, list] = {}
    for it in doc.get("items") or []:
        pn = int(it.get("passageNum") or 0)
        by_passage.setdefault(pn, []).append(it)

    sections = []
    for pi in sorted(by_passage):
        items = by_passage[pi]
        plabel = items[0].get("passageLabel") or f"Passage {pi}"
        cards = []
        for it in items:
            ex = (it.get("example") or "").strip()
            cards.append(
                example_card_html(
                    it.get("text") or "",
                    it.get("vn") or "",
                    ex,
                    it.get("exampleVi") or "",
                )
            )
        sections.append(
            {"id": f"passage-{pi}", "title": plabel, "level": 1, "html": "\n".join(cards)}
        )

    old = doc.get("sections") or []
    sources = next((s for s in old if s.get("id") == "sources"), None)
    if sources:
        sections.append(sources)
    elif doc.get("url"):
        url = doc["url"]
        book = doc.get("book") or ""
        sections.append(
            {
                "id": "sources",
                "title": "Sources",
                "level": 1,
                "html": (
                    f'<p class="en">Vocabulary sourced from '
                    f'<a class="ext-link" href="{url}" target="_blank" rel="noopener">DOL Tự học</a> '
                    f"({book}) for personal IELTS study.</p>"
                    f'<p class="vi">Từ vựng lấy từ DOL Tự học — chỉ phục vụ học tập cá nhân.</p>'
                ),
            }
        )
    doc["sections"] = sections


def strip_doc_ipa(doc: dict) -> int:
    """Remove baked IPA from items[] and rebuild passage HTML (IPA → index.html lazy load)."""
    n = 0
    for it in doc.get("items") or []:
        changed = False
        for key in ("ipaUK", "ipa", "exampleIpa"):
            if key in it:
                del it[key]
                changed = True
        if changed:
            n += 1
    rebuild_passage_sections(doc)
    return n


def enrich_doc_examples(
    doc: dict,
    *,
    translate: bool = True,
    rebuild_html: bool = True,
    progress: bool = False,
) -> int:
    """Enrich all items missing exampleVi. IPA is left to index.html at render time."""
    todo = [it for it in (doc.get("items") or []) if (it.get("example") or "").strip()]
    total = len(todo)
    n = 0
    for idx, it in enumerate(todo, 1):
        if enrich_item_examples(it, translate=translate):
            n += 1
        if progress and (idx == total or idx % 10 == 0):
            print(f"    enrich {idx}/{total}", flush=True)
            if translate:
                save_translate_cache()
    if translate:
        save_translate_cache()
    if rebuild_html and n:
        rebuild_passage_sections(doc)
    return n
