# Convert IELTS hourly practice lesson HTML files to JSON data files + manifest.json
import json, re, html, hashlib, sys, os
from pathlib import Path
from datetime import datetime, timezone

FOLDER = Path(__file__).resolve().parent.parent
SECTION_IDS = ["vocab", "vocab-a", "vocab-b", "vocabA", "vocabB", "reading", "listening", "writing", "speaking", "strategy"]
ID_NORMALIZE = {"vocabA": "vocab-a", "vocabB": "vocab-b"}
ANCHOR_RE = re.compile(r'<(section|h2)\b[^>]*\bid="(' + "|".join(SECTION_IDS) + r')"[^>]*>', re.I)

# "Meaning:" / "Example:" style markers inside vocabulary cards — removed permanently;
# the viewer colour-codes definition vs example lines instead.
LABEL_CHIP_RE = re.compile(
    r'<(div|span|p)\b[^>]*class="[^"]*(?<![\w-])(?:label|tag)(?![\w-])[^"]*"[^>]*>\s*'
    r'(?:Meaning|Definition|Examples?(?:\s+sentences?)?)\s*:?\s*</\1>\s*', re.I)
WRAPPED_PREFIX_RE = re.compile(
    r'(>\s*)<(strong|b|em)>\s*(?:Meaning|Examples?|Nghĩa|Ý nghĩa|Ví dụ|VD)\s*:\s*</\2>\s*', re.I)
TEXT_PREFIX_RE = re.compile(
    r'(>\s*)(?:Meaning|Examples?|Nghĩa|Ý nghĩa|Ví dụ|VD)\s*:\s*', re.I)

def clean_vocab_html(h):
    h = LABEL_CHIP_RE.sub("", h)
    h = WRAPPED_PREFIX_RE.sub(r"\1", h)
    h = TEXT_PREFIX_RE.sub(r"\1", h)
    return h

def _bi(en, vi, tag="p"):
    en = html.escape(str(en or ""), quote=False)
    out = f'<{tag} class="en">{en}</{tag}>'
    if vi:
        out += f'\n<{tag} class="vn">{html.escape(str(vi), quote=False)}</{tag}>'
    return out


def _txt(v, lang="en"):
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        return str(v.get(lang) or v.get("en" if lang == "en" else "vi") or "").strip()
    return str(v).strip()


def _table_html(cols, rows, title=""):
    parts = []
    if title:
        parts.append(f"<h4>{html.escape(str(title))}</h4>")
    tbl = ["<table>"]
    if cols:
        tbl.append("<tr>" + "".join(f"<th>{html.escape(str(c))}</th>" for c in cols) + "</tr>")
    for row in rows or []:
        if isinstance(row, dict):
            row = [row.get(c, "") for c in cols] if cols else list(row.values())
        tbl.append("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in (row or []) ) + "</tr>")
    tbl.append("</table>")
    parts.append("".join(tbl))
    return "\n".join(parts)


def render_section_html(sec):
    """Synthesize section html from structured ChatGPT fields when html is missing."""
    parts = []
    stype = str(sec.get("type") or "").lower()

    for story in sec.get("stories") or []:
        if not isinstance(story, dict):
            parts.append(_bi(str(story), ""))
            continue
        head_en = _txt(story.get("headline"))
        head_vi = _txt(story.get("headline"), "vi")
        if head_en:
            parts.append(f"<h4>{html.escape(head_en)}</h4>")
            if head_vi:
                parts.append(f'<p class="vi">{html.escape(head_vi)}</p>')
        parts.append(_bi(_txt(story.get("body")), _txt(story.get("body"), "vi")))
        wim_en = _txt(story.get("whyItMatters"))
        if wim_en:
            parts.append(_bi(wim_en, _txt(story.get("whyItMatters"), "vi")))
        for src in story.get("sources") or []:
            parts.append(f'<p class="note en">{html.escape(str(src))}</p>')

    for it in sec.get("items") or []:
        if isinstance(it, str):
            parts.append(_bi(it, ""))
            continue
        if it.get("home") and it.get("away"):
            head = " · ".join(x for x in (it.get("stage"), f"{it.get('home')} vs {it.get('away')}", it.get("score")) if x)
            parts.append(f"<h4>{html.escape(head)}</h4>")
            parts.append(_bi(_txt(it.get("en")), _txt(it.get("vi"))))
            continue
        if it.get("check"):
            parts.append(f'<p class="en"><strong>{html.escape(str(it.get("check")))}</strong> — {html.escape(str(it.get("status", "")))}</p>')
            continue
        head = it.get("headline") or it.get("match") or ""
        if isinstance(head, dict):
            head = _txt(head)
        sub = " · ".join(x for x in (it.get("team"), it.get("date"), it.get("timeEt"), it.get("venue")) if x)
        if it.get("name") and it.get("team"):
            parts.append(f"<h4>{html.escape(str(it.get('name')))} · {html.escape(str(it.get('team')))}</h4>")
        elif head:
            parts.append(f"<h4>{html.escape(str(head))}{(' · ' + html.escape(sub)) if sub else ''}</h4>")
        if it.get("headlineVi") and not isinstance(it.get("headline"), dict):
            parts.append(f'<p class="vi">{html.escape(str(it.get("headlineVi")))}</p>')
        parts.append(_bi(_txt(it.get("en") or it.get("body")), _txt(it.get("vi") or it.get("bodyVi"))))
        url = it.get("url") or it.get("sourceUrl") or ""
        name = it.get("sourceName") or it.get("name") or it.get("description") or url
        if url:
            parts.append(f'<p class="note en"><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener">{html.escape(str(name))}</a></p>')
        elif name and not it.get("name"):
            parts.append(f'<p class="note en">{html.escape(str(name))}</p>')

    if sec.get("columns") or stype == "table":
        parts.append(_table_html(sec.get("columns"), sec.get("rows")))
    if sec.get("noteEn") or sec.get("noteVi"):
        parts.append(_bi(sec.get("noteEn"), sec.get("noteVi")))
    if (sec.get("en") or sec.get("vi")) and not sec.get("items") and not sec.get("stories"):
        parts.append(_bi(sec.get("en"), sec.get("vi")))

    return "\n".join(p for p in parts if p)


def repair_study_sections(lesson):
    """Repair ChatGPT news/worldcup/brief JSON that ships structured fields without sections[].html."""
    changed = False
    lid = str(lesson.get("id") or "").lower()
    sections = lesson.get("sections")
    if not isinstance(sections, list):
        return False

    summ = lesson.get("summary") or {}
    if isinstance(summ, dict) and (_txt(summ.get("en")) or _txt(summ.get("vi"))):
        if not any(str(s.get("id", "")) in ("summary", "briefing", "overview") for s in sections if isinstance(s, dict)):
            sections.insert(0, {"id": "summary", "title": "Overview", "level": 1,
                                "html": _bi(_txt(summ.get("en")), _txt(summ.get("vi")))})
            changed = True

    weather = lesson.get("weather")
    if isinstance(weather, dict) and weather.get("location"):
        if not any(str(s.get("id", "")) == "weather" for s in sections if isinstance(s, dict)):
            wp = [_bi(_txt(weather.get("current")), _txt(weather.get("current"), "vi")),
                  _bi(_txt(weather.get("todayOutlook")), _txt(weather.get("todayOutlook"), "vi")),
                  _bi(_txt(weather.get("studyNote")), _txt(weather.get("studyNote"), "vi"))]
            sections.insert(1 if changed else 0, {
                "id": "weather", "title": "Weather — " + str(weather.get("location", "")), "level": 1,
                "html": "\n".join(x for x in wp if x)
            })
            changed = True

    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            continue
        title = sec.get("title")
        if isinstance(title, dict):
            sec["title"] = _txt(title) + (" | " + _txt(title, "vi") if _txt(title, "vi") else "")
            changed = True
        elif title is not None and not isinstance(title, str):
            sec["title"] = str(title)
            changed = True
        title_vi = sec.pop("titleVi", None)
        if title_vi and isinstance(sec.get("title"), str) and str(title_vi) not in sec["title"]:
            sec["title"] = sec["title"] + " | " + str(title_vi)
            changed = True
        if not sec.get("id"):
            sec["id"] = sec.get("key") or re.sub(r"[^a-z0-9]+", "-", str(sec.get("title", "")).lower()).strip("-") or f"s{i + 1}"
            changed = True
        if not str(sec.get("html") or "").strip():
            built = render_section_html(sec)
            if built:
                sec["html"] = built
                changed = True
        sec.setdefault("level", 1)

    extra_tables = lesson.get("tables") or []
    if extra_tables and not any(str(s.get("id", "")) == "schedule" for s in sections if isinstance(s, dict)):
        tp = [_table_html(t.get("columns"), t.get("rows"), t.get("title")) for t in extra_tables if isinstance(t, dict)]
        if tp:
            sections.append({"id": "schedule", "title": "Schedule & Implications", "level": 2, "html": "\n".join(tp)})
            changed = True

    vocab = lesson.get("ieltsVocabulary") or lesson.get("ieltsLanguageFocus") or []
    if vocab and not any(str(s.get("id", "")).startswith("vocab") for s in sections if isinstance(s, dict)):
        vp = []
        words = []
        for w in vocab:
            if not isinstance(w, dict):
                continue
            word = w.get("word") or w.get("phrase") or w.get("term") or ""
            if word:
                words.append(word)
            ipa = w.get("ipaUS") or w.get("ipa") or ""
            vp.append(f'<div class="vocab"><div class="head">{html.escape(str(word))} <span class="ipa">{html.escape(str(ipa))}</span></div>')
            vp.append(_bi(w.get("meaningEN") or w.get("en"), w.get("meaningVI") or w.get("vi")))
            ex_en = w.get("exampleEN") or ""
            ex_vi = w.get("exampleVI") or ""
            if ex_en:
                vp.append(_bi(ex_en, ex_vi))
            vp.append("</div>")
        if vp:
            sections.append({"id": "vocab", "title": "IELTS Vocabulary", "level": 2, "html": "\n".join(vp)})
            if words:
                lesson["words"] = words
            changed = True

    if "worldcup" in lid or str(lesson.get("category", "")).lower() == "worldcup":
        lesson["type"] = "news"
        lesson["category"] = "worldcup"
        changed = True
    elif lid.startswith("news-gpt"):
        lesson["type"] = "news"
        lesson.setdefault("category", "daily-news")
        changed = True
    elif lid.startswith("brief-gpt"):
        lesson["type"] = "brief"
        changed = True
    if lesson.get("type") == "dynamic":
        lesson["type"] = "news"
        changed = True
    if not lesson.get("dateTime"):
        dt = lesson.get("generatedAt") or lesson.get("date") or ""
        if dt:
            lesson["dateTime"] = str(dt)[:16]
            changed = True
    if lesson.get("topicNumber") is None:
        lesson["topicNumber"] = 0
    return changed


def build_worldcup_sections(lesson):
    """Adapt the rogue 'worldcup daily briefing' schemas (results/biggestMoments/tables/...,
    no sections[] — sometimes nested one level under 'briefing', with field names that drift
    between runs) some ChatGPT runs produce despite the contract, into real sections[] so
    100% of the file's content renders instead of being silently skipped."""
    if isinstance(lesson.get("briefing"), dict):        # unwrap the nested-briefing variant
        b = lesson["briefing"]
        lesson.setdefault("results", b.get("resultsAndScoreboard") or b.get("results"))
        for k in ("biggestMoments", "tournamentImplications", "breakoutPlayers", "tables",
                  "whatToWatchTomorrow", "mainHeadlines", "ieltsLanguageFocus"):
            lesson.setdefault(k, b.get(k))

    sections = []
    if lesson.get("mainHeadlines"):
        parts = [_bi(h.get("en", ""), h.get("vi", "")) for h in lesson["mainHeadlines"]]
        sections.append({"id": "headlines", "title": "Main Headlines", "level": 1, "html": "\n".join(parts)})

    summ = lesson.get("summary") or {}
    intro_parts = []
    if summ.get("en") or summ.get("vi"):
        intro_parts.append(_bi(summ.get("en", ""), summ.get("vi", "")))
    sn = lesson.get("sourceNotes")
    if isinstance(sn, dict) and sn.get("en"):
        intro_parts.append(_bi(sn.get("en", ""), sn.get("vi", "")))
    if intro_parts:
        sections.append({"id": "briefing", "title": "Daily Briefing", "level": 1, "html": "\n".join(intro_parts)})

    if lesson.get("results"):
        parts = []
        for r in lesson["results"]:
            head = " · ".join(x for x in (r.get("stage"), r.get("match")) if x)
            parts.append(f"<h4>{html.escape(head)}</h4>")
            en = r.get("en", "")
            if r.get("sources"):
                en += " (" + ", ".join(r["sources"]) + ")"
            parts.append(_bi(en, r.get("vi", "")))
        sections.append({"id": "results", "title": "Match Results", "level": 1, "html": "\n".join(parts)})

    for key, sec_id, title in [
        ("biggestMoments", "moments", "Biggest Moments"),
        ("tournamentImplications", "implications", "Tournament Implications"),
        ("whatToWatchTomorrow", "preview", "What to Watch Tomorrow"),
    ]:
        items = lesson.get(key)
        if items:
            html_parts = [_bi(it.get("en", ""), it.get("vi", "")) for it in items]
            sections.append({"id": sec_id, "title": title, "level": 2, "html": "\n".join(html_parts)})

    if lesson.get("breakoutPlayers"):
        parts = []
        for p in lesson["breakoutPlayers"]:
            head = " · ".join(x for x in (p.get("player"), p.get("team")) if x)
            parts.append(f"<h4>{html.escape(head)}</h4>")
            parts.append(_bi(p.get("en", ""), p.get("vi", "")))
        sections.append({"id": "players", "title": "Breakout Players", "level": 2, "html": "\n".join(parts)})

    if lesson.get("tables"):
        parts = []
        for t in lesson["tables"]:
            if t.get("title"):
                parts.append(f"<h4>{html.escape(t['title'])}</h4>")
            cols = t.get("columns") or []
            rows = t.get("rows") or []
            tbl = ["<table>"]
            if cols:
                tbl.append("<tr>" + "".join(f"<th>{html.escape(str(c))}</th>" for c in cols) + "</tr>")
            for row in rows:
                tbl.append("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>")
            tbl.append("</table>")
            parts.append("".join(tbl))
        sections.append({"id": "schedule", "title": "Schedule & Implications", "level": 2, "html": "\n".join(parts)})

    if lesson.get("ieltsLanguageFocus"):
        parts = []
        for it in lesson["ieltsLanguageFocus"]:
            if isinstance(it, dict):
                head = it.get("phrase") or it.get("term") or it.get("word")
                if head:
                    parts.append(f"<h4>{html.escape(str(head))}</h4>")
                parts.append(_bi(it.get("en", ""), it.get("vi", "")))
            else:
                parts.append(_bi(str(it), ""))
        sections.append({"id": "ielts-focus", "title": "IELTS Language Focus", "level": 2, "html": "\n".join(parts)})

    src_list = lesson.get("sources")
    if not src_list and isinstance(lesson.get("sourceNotes"), list):
        src_list = lesson["sourceNotes"]   # alternate schema: sourceNotes IS the source list
    if src_list:
        parts = []
        for s in src_list:
            label = " · ".join(x for x in (s.get("publisher"), s.get("date"), s.get("usedFor")) if x)
            url = html.escape(s.get("url", ""), quote=True)
            title = html.escape(s.get("title") or s.get("name") or s.get("url", ""))
            parts.append(f'<p class="note en"><a href="{url}" target="_blank" rel="noopener">{title}</a>'
                         f'{" — " + html.escape(label) if label else ""}</p>')
        sections.append({"id": "sources", "title": "Sources", "level": 2, "html": "\n".join(parts)})

    lesson["sections"] = sections
    lesson["type"] = "news"       # force: whatever nonstandard value the agent invented (e.g.
    lesson["category"] = "worldcup"  # "worldcup_daily_briefing"), this content is unambiguously news/worldcup
    lesson.setdefault("source", "chatgpt")
    if not lesson.get("dateTime"):
        lesson["dateTime"] = (lesson.get("generatedAt") or (lesson.get("date", "") + "T00:00"))[:16]
    if not isinstance(lesson.get("words"), list) or not lesson["words"]:
        lesson["words"] = [p.get("player") for p in (lesson.get("breakoutPlayers") or []) if p.get("player")]
    return True


def normalize_lesson(lesson):
    """Repair missing section ids (some agents omit them) and strip Meaning/Example
    markers from vocab sections. Returns True if the lesson was changed."""
    changed = False
    if not isinstance(lesson.get("words"), list):        # some agents write a count or omit it
        lesson["words"] = []
        changed = True
    for fld in ("title", "fullTitle", "angle", "category", "type", "source"):
        v = lesson.get(fld)
        if isinstance(v, dict):                          # some agents write {"en":..,"vi":..}
            lesson[fld] = str(v.get("en") or next(iter(v.values()), "") or "")
            changed = True
        elif v is not None and not isinstance(v, str):
            lesson[fld] = str(v)
            changed = True
    if not lesson.get("type"):                           # infer an obvious type from the filename stem
        m = re.match(r"(news|worldcup|brief|quiz|test|bbc)[-_]", str(lesson.get("id") or ""), re.I)
        lesson["type"] = ("news" if m.group(1).lower() == "worldcup" else m.group(1).lower()) if m else "lesson"
        changed = True
    if lesson.get("format") == "bbc-6min":
        lesson.setdefault("category", "bbc-6-minute-english")
        lesson.setdefault("topicNumber", 0)
        if not lesson.get("type") or lesson.get("type") == "bbc":
            lesson["type"] = "lesson"
            changed = True
    for i, s in enumerate(lesson.get("sections", [])):
        if not isinstance(s, dict):
            continue
        if not s.get("id"):
            # derive an id from the title (e.g. "Writing (Task 2)" -> "writing-task-2"),
            # falling back to a positional id — mirrors the app's normalizeItem defaults
            slug = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", _txt(s.get("title")).lower())).strip("-")
            s["id"] = slug or f"s{i + 1}"
            changed = True
        title = s.get("title")
        if isinstance(title, dict):
            s["title"] = _txt(title) + (" | " + _txt(title, "vi") if _txt(title, "vi") else "")
            changed = True
        elif title is not None and not isinstance(title, str):
            s["title"] = str(title)
            changed = True
        if str(s["id"]).startswith("vocab"):
            cleaned = clean_vocab_html(s.get("html", ""))
            if cleaned != s.get("html", ""):
                s["html"] = cleaned
                changed = True
    return changed

def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()

def clean_section_title(raw):
    t = strip_tags(raw)
    t = re.sub(r"^\s*\d+(\s*(?:&|and)\s*\d+)?\s*[·.:—–-]+\s*", "", t)
    return t.strip() or raw

def parse_file(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"ielts-(\d{4})-(\d{2})-(\d{2})-(\d{2})(\d{2})-topic(\d+)-(.+)\.html", path.name)
    if not m:
        return None
    y, mo, d, hh, mm, topic_num, slug = m.groups()
    date_time = f"{y}-{mo}-{d}T{hh}:{mm}"

    title_tag = re.search(r"<title>(.*?)</title>", text, re.S)
    title_tag = strip_tags(title_tag.group(1)) if title_tag else ""

    header_m = re.search(r"<header\b[^>]*>([\s\S]*?)</header>", text)
    header_html = header_m.group(1) if header_m else ""
    h1_m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", header_html)
    h1 = strip_tags(h1_m.group(1)) if h1_m else ""
    header_text = strip_tags(re.sub(r"<(?:br[^>]*|/div|/p|/h1)>", " · ", header_html))

    # topic name
    topic_name = None
    for src in (h1, title_tag, header_text):
        tm = re.search(r"Topic\s*\d+\s*[:—–-]\s*(.+?)(?:\s*\(\d{4}.*)?$", src)
        if tm:
            topic_name = tm.group(1).strip(" ·")
            break
    if not topic_name:
        sm = re.search(r"<strong>([\s\S]*?)</strong>", header_html)
        if sm:
            topic_name = strip_tags(sm.group(1))
    if not topic_name:
        topic_name = slug.replace("-", " ").title()
    topic_name = re.sub(r"\s*[·|].*$", "", topic_name)
    topic_name = re.sub(r"\s*[—–-]\s*\d{4}-\d{2}-\d{2}.*$", "", topic_name).strip()

    angle_m = re.search(r"Angle:\s*(.+?)\s*(?:[·|]|Run:|$)", header_text)
    angle = angle_m.group(1).strip() if angle_m else ""
    angle = re.sub(r"\s*\d{4}-\d{2}-\d{2}.*$", "", angle).strip(" |·•-")
    band_m = re.search(r"(?:Target band|Band)\s*([\d.–—-]+(?:\s*[–—-]\s*[\d.]+)?)", header_text)
    band = band_m.group(1).strip() if band_m else ""

    # content region: after toc nav, before script
    nav_end = text.find("</nav>")
    start = nav_end + 6 if nav_end != -1 else 0
    script_pos = text.find("<script", start)
    region = text[start:script_pos if script_pos != -1 else len(text)]

    anchors = [(a.group(1).lower(), ID_NORMALIZE.get(a.group(2), a.group(2)),
                a.start(), a.end()) for a in ANCHOR_RE.finditer(region)]
    if not anchors:
        return None

    sections = []
    for i, (tag, sid, s, e) in enumerate(anchors):
        nxt = anchors[i + 1][2] if i + 1 < len(anchors) else len(region)
        if tag == "section":
            close = region.find("</section>", e)
            if close == -1 or close > nxt:
                close = nxt
            inner = region[e:close]
        else:  # h2-style: from end of h2 open tag to next anchor
            h2_close = region.find("</h2>", e)
            title_raw = region[e:h2_close] if h2_close != -1 else ""
            inner = ("<h2>" + title_raw + "</h2>" if title_raw else "") + region[(h2_close + 5) if h2_close != -1 else e:nxt]
        # pull first h2 out as section title
        h2m = re.search(r"<h2[^>]*>([\s\S]*?)</h2>", inner)
        if h2m:
            sec_title = clean_section_title(h2m.group(1))
            inner = inner[:h2m.start()] + inner[h2m.end():]
        else:
            sec_title = sid.capitalize()
        sections.append({"id": sid, "title": sec_title, "html": inner.strip()})

    # vocab word list
    words, seen = [], set()
    for sec in sections:
        if not sec["id"].startswith("vocab"):
            continue
        for wm in re.finditer(r'<(p|div|span|h4)\b[^>]*class="[^"]*\b(?:word|head|hw)\b[^"]*"[^>]*>([\s\S]*?)</\1>', sec["html"]):
            w = re.sub(r"\s*/[^/]*/\s*$", "", strip_tags(wm.group(2))).strip()
            w = re.sub(r"^\d+\s*[.)·]\s*", "", w)
            if w and w.lower() not in seen:
                seen.add(w.lower())
                words.append(w)

    lesson = {
        "schema": 1,
        "id": path.stem,
        "sourceFile": path.name,
        "title": topic_name,
        "fullTitle": h1 or title_tag,
        "topicNumber": int(topic_num),
        "angle": angle,
        "band": band,
        "dateTime": date_time,
        "words": words,
        "sections": sections,
    }
    normalize_lesson(lesson)
    return lesson

def main():
    manifest_path = FOLDER / "manifest.json"
    try:
        previous_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous_manifest = {}
    previous_entries = {x.get("id"): x for x in previous_manifest.get("lessons", []) if x.get("id")}
    built_at = datetime.now(timezone.utc).isoformat()

    # 1) convert any lesson HTML files present into JSON
    files = sorted(FOLDER.glob("ielts-*.html"))
    problems, converted = [], 0
    for f in files:
        lesson = parse_file(f)
        if not lesson:
            problems.append((f.name, "could not parse"))
            continue
        main_ids = {s["id"] for s in lesson["sections"]}
        if not {"reading", "listening", "writing", "speaking", "strategy"} <= main_ids:
            problems.append((f.name, f"missing sections, got {sorted(main_ids)}"))
        if not any(i.startswith("vocab") for i in main_ids):
            problems.append((f.name, "missing vocab section"))
        for s in lesson["sections"]:
            if len(s["html"]) < 200:
                problems.append((f.name, f"section {s['id']} too short ({len(s['html'])} chars)"))
        if len(lesson["words"]) < 5:
            problems.append((f.name, f"only {len(lesson['words'])} vocab words"))
        (FOLDER / (f.stem + ".json")).write_text(
            json.dumps(lesson, ensure_ascii=False, indent=1), encoding="utf-8")
        converted += 1

    # 2) normalize + rebuild manifest.json from ALL study JSON files:
    #    - the data/ folder (data/<source>/<subfolders>/*.json)
    #    - the tool root (where generators may drop files before sorting into data/)
    EXCLUDE = re.compile(
        r"^(manifest\.json|state\.json|upcoming\.json|state-advance\.json|user-data\.json|catalog\.json|dol-book-stats\.json|superlms-courses\.json|superlms-state\.json|0\.speaking\.json)$|template",
        re.I,
    )
    jfiles = sorted((FOLDER / "data").rglob("*.json")) if (FOLDER / "data").is_dir() else []
    jfiles += sorted(FOLDER.glob("*.json"))
    manifest, normalized = [], 0
    for jf in jfiles:
        if True:
            if EXCLUDE.search(jf.name):
                continue
            rel = jf.relative_to(FOLDER).as_posix()
            if rel.startswith("data/ipa/"):        # US IPA dictionary shards — not study content
                continue
            if rel.startswith("data/chatgpt/tests/"):  # Generic test simulator owns its own manifest/schema
                continue
            if "/snapshots/" in rel:               # DOL prefetch cache — not study content
                continue
            parts = rel.split("/")
            src_dir = parts[1] if len(parts) > 2 and parts[0] == "data" else "claude-cowork"
            payload = jf.read_text(encoding="utf-8")
            try:
                lesson = json.loads(payload)
            except ValueError as e:
                problems.append((rel, f"invalid JSON: {e}"))
                continue
            is_speaking_source = (
                lesson.get("id")
                and isinstance(lesson.get("items"), list)
                and bool(lesson["items"])
                and isinstance(lesson["items"][0], dict)
                and isinstance(lesson["items"][0].get("questions"), list)
            )
            if is_speaking_source:
                content_hash = hashlib.md5(payload.encode("utf-8")).hexdigest()
                previous = previous_entries.get(lesson["id"], {})
                explicit_updated = lesson.get("contentUpdatedAt", "")
                if explicit_updated:
                    updated_at = explicit_updated
                elif previous.get("hash") == content_hash and previous.get("updatedAt"):
                    updated_at = previous["updatedAt"]
                elif previous.get("hash") == content_hash:
                    updated_at = lesson.get("dateTime", "") or previous.get("dateTime", "") or built_at
                else:
                    updated_at = built_at
                manifest.append({
                    "file": rel, "id": lesson["id"], "title": lesson.get("title", ""),
                    "topicNumber": 0, "dateTime": lesson.get("dateTime", ""),
                    "updatedAt": updated_at, "angle": "", "sections": [], "wordCount": 0,
                    "type": lesson.get("type", "speaking"), "source": lesson.get("source", src_dir),
                    "category": lesson.get("category", "dol-speaking"),
                    "format": lesson.get("format", "speaking-source"),
                    **({key: lesson.get(key) for key in ("l1", "l2", "l3") if lesson.get(key)}),
                    "hash": content_hash,
                })
                continue
            rebuilt = False
            is_rogue_worldcup = (isinstance(lesson.get("results"), list)
                                 or (isinstance(lesson.get("briefing"), dict)
                                     and isinstance(lesson["briefing"].get("resultsAndScoreboard"), list)))
            if lesson.get("id") and is_rogue_worldcup:
                rebuilt = build_worldcup_sections(lesson)
            if lesson.get("id") and repair_study_sections(lesson):
                rebuilt = True
            if not (lesson.get("id") and isinstance(lesson.get("sections"), list)):
                problems.append((rel, "not a lesson file (missing id/sections)"))
                continue
            if normalize_lesson(lesson) or rebuilt:
                payload = json.dumps(lesson, ensure_ascii=False, indent=1)
                jf.write_text(payload, encoding="utf-8")
                normalized += 1
            content_hash = hashlib.md5(payload.encode("utf-8")).hexdigest()
            previous = previous_entries.get(lesson["id"], {})
            explicit_updated = lesson.get("contentUpdatedAt", "")
            if explicit_updated:
                updated_at = explicit_updated
            elif previous.get("hash") == content_hash and previous.get("updatedAt"):
                # Preserve the meaningful content timestamp across no-op index rebuilds.
                updated_at = previous["updatedAt"]
            elif previous.get("hash") == content_hash:
                updated_at = lesson.get("dateTime", "") or previous.get("dateTime", "") or built_at
            else:
                updated_at = built_at
            manifest.append({
                "file": rel, "id": lesson["id"], "title": lesson.get("title", ""),
                "topicNumber": lesson.get("topicNumber", 0), "dateTime": lesson.get("dateTime", ""),
                "updatedAt": updated_at,
                "angle": lesson.get("angle", ""), "sections": [s["id"] for s in lesson["sections"]],
                "wordCount": len(lesson["words"]) if isinstance(lesson.get("words"), list) else 0,
                "type": lesson.get("type", "lesson"), "source": lesson.get("source", src_dir),
                "category": lesson.get("category", ""),
                "format": lesson.get("format", ""),
                **({key: lesson.get(key) for key in (
                    "group", "book", "bookNum", "testNum", "skill", "superlmsFlat", "l1", "l2", "l3", "l4"
                ) if lesson.get(key) not in (None, "", 0, False)} if lesson.get("l1") else {}),
                "hash": content_hash,
            })
    manifest.sort(key=lambda x: x["dateTime"])
    version_payload = [{"id": x["id"], "file": x["file"], "hash": x["hash"],
                        "updatedAt": x["updatedAt"]} for x in manifest]
    content_version = hashlib.sha256(json.dumps(
        version_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    if previous_manifest.get("contentVersion") == content_version:
        content_updated_at = previous_manifest.get("contentUpdatedAt") or built_at
    else:
        content_updated_at = built_at
    manifest_path.write_text(
        json.dumps({"schema": 2, "generated": built_at,
                    "contentVersion": content_version, "contentUpdatedAt": content_updated_at,
                    "lessons": manifest}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Converted {converted}/{len(files)} HTML lessons; normalized {normalized} JSONs; manifest lists {len(manifest)} lessons")
    for name, why in problems:
        print(f"  WARN {name}: {why}")

if __name__ == "__main__":
    main()
