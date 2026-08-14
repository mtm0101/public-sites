# Convert BBC 6 Minute English HTML lessons to JSON for the IELTS practice app.
import json, re, html, argparse
from pathlib import Path
from datetime import datetime, timezone

TOOL = Path(__file__).resolve().parent.parent
HTML_DIR = TOOL.parent / "bbc-lessons"
OUT_DIR = TOOL / "data" / "claude-cowork" / "bbc"

SECTION_MAP = [
    ("vocab", "Vocabulary", 1, "header", "dialogue"),
    ("dialogue", "Bilingual Study Dialogue", 1, "header", "ielts"),
    ("sp1", "Speaking Part 1", 2, "ielts-sub", "sp2"),
    ("sp2", "Speaking Part 2", 2, "ielts-sub", "sp3"),
    ("sp3", "Speaking Part 3", 2, "ielts-sub", "patterns"),
    ("patterns", "Sentence Patterns", 2, "ielts-sub", "writing"),
    ("writing", "Writing Task 2", 2, "ielts-sub", "grammar"),
    ("grammar", "Grammar Band 7–8", 1, "header", None),
]

def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()

_VOCAB_IPA_RE = re.compile(
    r'<(?:span|div) class="vocab-ipa"[^>]*>[\s\S]*?</(?:span|div)>', re.I
)


def strip_baked_ipa_html(h):
    """Remove inline IPA — index.html lazy-loads from data/ipa/ shards."""
    if not h:
        return h
    return _VOCAB_IPA_RE.sub('<span class="vocab-ipa"></span>', h)


def strip_doc_bbc_ipa(doc):
    changed = False
    for sec in doc.get("sections") or []:
        html_val = sec.get("html") or ""
        new_html = strip_baked_ipa_html(html_val)
        if new_html != html_val:
            sec["html"] = new_html
            changed = True
    return changed

def extract_region(text, start_pat, end_pat=None):
    m = re.search(start_pat, text, re.I | re.S)
    if not m:
        return ""
    start = m.end()
    if end_pat:
        em = re.search(end_pat, text[start:], re.I | re.S)
        end = start + em.start() if em else len(text)
    else:
        end = len(text)
    return text[start:end]

def normalize_section_html(h):
    if not h:
        return ""
    h = re.sub(r"<style[\s\S]*?</style>", "", h, flags=re.I)
    h = re.sub(r"<script[\s\S]*?</script>", "", h, flags=re.I)
    # plain English paragraphs -> class="en"
    def fix_p(m):
        tag = m.group(0)
        if re.search(r'\bclass="[^"]*\bvi\b', tag, re.I):
            return tag
        if re.search(r'\bclass="[^"]*\ben\b', tag, re.I):
            return tag
        if re.search(r'\bclass="[^"]*\b(speaker-name|vocab-label|grammar-row-label|pattern-label)\b', tag, re.I):
            return tag
        if re.search(r'\bclass="', tag, re.I):
            return re.sub(r'\bclass="', 'class="en ', tag, count=1)
        return re.sub(r"<p\b", '<p class="en"', tag, count=1)
    h = re.sub(r"<p\b[^>]*>", fix_p, h)
    # merge duplicate class attributes (class="en" class="pattern-formula" -> one class attr)
    h = re.sub(r'\bclass="([^"]*)"\s+class="([^"]*)"', r'class="\1 \2"', h)
    # error/correct styling -> labels
    h = re.sub(
        r'<p([^>]*class="[^"]*\berror-sentence[^"]*"[^>]*)>([\s\S]*?)</p>',
        r'<p class="en"><strong>Incorrect:</strong> \2</p>', h, flags=re.I)
    h = re.sub(
        r'<p([^>]*class="[^"]*\bcorrect-sentence[^"]*"[^>]*)>([\s\S]*?)</p>',
        r'<p class="en"><strong>Corrected:</strong> \2</p>', h, flags=re.I)
    # unwrap em inside vi for cleaner rendering
    h = re.sub(r'(<p class="vi"[^>]*>)<em>([\s\S]*?)</em></p>', r'\1\2</p>', h)
    # drop trailing comments / partial next-section tags from bad slice boundaries (end only)
    h = re.sub(r'(?:\s*<!--[^>]*-->\s*)+$', '', h)
    h = re.sub(r'\s*<!--[^>]*$', '', h)
    h = re.sub(r'<div class="(?:section-header|ielts-sub)"[^>]*$', '', h, flags=re.I)
    h = strip_baked_ipa_html(h)
    return h.strip()

def _anchor_pos(region, anchor_id):
    m = re.search(rf'\bid="{re.escape(anchor_id)}"', region, re.I)
    return m.start() if m else -1

def _section_start(region, anchor_id):
    """Start of the section-header or ielts-sub opening tag — not mid-attribute."""
    m = re.search(
        rf'<div class="(?:section-header|ielts-sub)"[^>]*\bid="{re.escape(anchor_id)}"',
        region, re.I)
    return m.start() if m else _anchor_pos(region, anchor_id)

def extract_section(region, anchor_id, kind, until_id):
    if kind == "ielts-sub":
        open_m = re.search(rf'<div class="ielts-sub"[^>]*\bid="{re.escape(anchor_id)}"[^>]*>', region, re.I)
        if not open_m:
            return ""
        start = open_m.start()
    else:
        hdr = re.search(
            rf'<div class="section-header"[^>]*\bid="{re.escape(anchor_id)}"[^>]*>[\s\S]*?</div>',
            region, re.I)
        if not hdr:
            return ""
        start = hdr.end()
    end = len(region)
    if until_id:
        nxt = _section_start(region, until_id)
        if nxt > start:
            end = nxt
    return normalize_section_html(region[start:end])

def parse_html(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"bbc-6min-(\d{4})-(\d{2})-(\d{2})-(.+)\.html$", path.name, re.I)
    if not m:
        return None
    y, mo, d, slug = m.groups()
    ep_date = f"{y}-{mo}-{d}"
    yymmdd = f"{y[2:]}{mo}{d}"

    header_m = re.search(r'<header class="page-header"[^>]*>([\s\S]*?)</header>', text, re.I)
    header = header_m.group(1) if header_m else ""

    h1 = strip_tags(re.search(r"<h1[^>]*>([\s\S]*?)</h1>", header, re.I).group(1)) if re.search(r"<h1", header, re.I) else slug.replace("-", " ").title()
    title_vi = ""
    h1vi = re.search(r'<em class="h1-vi[^"]*"[^>]*>([\s\S]*?)</em>', header, re.I)
    if h1vi:
        title_vi = strip_tags(h1vi.group(1))

    summary_en, summary_vi = [], []
    for block in re.finditer(r'<div class="summary-block"[^>]*>([\s\S]*?)</div>', header, re.I):
        inner = block.group(1)
        for pm in re.finditer(r"<p([^>]*)>([\s\S]*?)</p>", inner, re.I):
            attrs, body = pm.group(1), pm.group(2)
            plain = strip_tags(body)
            if not plain:
                continue
            if re.search(r'\bclass="[^"]*\bvi\b', attrs, re.I):
                summary_vi.append(plain)
            else:
                summary_en.append(strip_tags(re.sub(r"</?em>", "", body)))

    links = {"bbc": "", "transcript": "", "sounds": "", "spotify": ""}
    for am in re.finditer(r'<a class="ext-link"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>', header, re.I):
        href, label = am.group(1), strip_tags(am.group(2)).lower()
        if "transcript" in label:
            links["transcript"] = href
        elif "spotify" in label:
            links["spotify"] = href
        elif "sounds" in label:
            links["sounds"] = href
        elif "bbc" in label:
            links["bbc"] = href

    ep_url = links["bbc"] or f"https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_{y}/ep-{yymmdd}"
    saved_at = ""
    saved_m = re.search(r"Saved\s+(\d+\s+\w+\s+\d{4})", header, re.I)
    if saved_m:
        try:
            saved_at = datetime.strptime(saved_m.group(1), "%d %B %Y").strftime("%Y-%m-%d")
        except ValueError:
            saved_at = saved_m.group(1)

    # content region: after TOC, before footer/script
    nav_end = text.find("</nav>")
    start = nav_end + 6 if nav_end != -1 else text.find('<header class="page-header"')
    footer_m = re.search(r"<footer\b", text[start:], re.I)
    script_m = re.search(r"<script\b", text[start:], re.I)
    end = start + (footer_m.start() if footer_m else (script_m.start() if script_m else len(text) - start))
    region = text[start:end]

    sections = []
    for sid, title, level, kind, until_id in SECTION_MAP:
        html_chunk = extract_section(region, sid, kind, until_id)
        sec_id = f"speaking-{sid[-1]}" if re.fullmatch(r"sp[123]", sid) else sid
        if html_chunk:
            sections.append({"id": sec_id, "title": title, "level": level, "html": html_chunk})

    # footer -> sources
    footer_m = re.search(r"<footer[^>]*>([\s\S]*?)</footer>", text, re.I)
    if footer_m:
        src_html = normalize_section_html(footer_m.group(1))
        if src_html:
            sections.append({"id": "sources", "title": "Sources & Disclaimer", "level": 1, "html": src_html})

    words = []
    seen = set()
    for wm in re.finditer(r'<span class="vocab-word"[^>]*>([\s\S]*?)</span>', text, re.I):
        w = strip_tags(wm.group(1))
        if w and w.lower() not in seen:
            seen.add(w.lower())
            words.append(w)

    for sec in sections:
        if sec.get("id") == "dialogue":
            mode = "original" if re.search(
                r"official BBC episode transcript|follows the official BBC|bản ghi chính thức",
                sec.get("html") or "",
                re.I,
            ) else "paraphrase"
            sec["title"] = "Bilingual Dialogue" if mode == "original" else "Bilingual Study Dialogue"
            break
    else:
        mode = "paraphrase"

    lesson = {
        "schema": 2,
        "format": "bbc-6min",
        "id": f"bbc-claude-{yymmdd}-{slug}",
        "type": "lesson",
        "source": "claude-cowork",
        "category": "bbc-6-minute-english",
        "topicNumber": 0,
        "title": h1,
        "titleVi": title_vi,
        "band": "7.0–8.0",
        "dateTime": f"{ep_date}T00:00",
        "dialogueMode": mode,
        "episode": {
            "id": f"ep-{yymmdd}",
            "date": ep_date,
            "title": h1,
            "url": ep_url,
            "savedAt": saved_at or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "links": links,
        "summary": {"en": summary_en, "vi": summary_vi},
        "words": words,
        "sections": sections,
    }
    return lesson

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="Overwrite existing JSON files")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(HTML_DIR.glob("bbc-6min-*.html"))
    converted, skipped, problems = 0, 0, []
    for f in files:
        lesson = parse_html(f)
        if not lesson:
            problems.append((f.name, "could not parse filename"))
            continue
        out = OUT_DIR / (lesson["id"] + ".json")
        if out.exists() and not args.force:
            skipped += 1
            continue
        if len(lesson["sections"]) < 3:
            problems.append((f.name, f"only {len(lesson['sections'])} sections"))
        if len(lesson["words"]) < 3:
            problems.append((f.name, f"only {len(lesson['words'])} words"))
        out.write_text(json.dumps(lesson, ensure_ascii=False, indent=1), encoding="utf-8")
        converted += 1
        print(f"  OK {out.name}")
    print(f"Converted {converted}, skipped {skipped}, problems {len(problems)}")
    for name, why in problems:
        print(f"  WARN {name}: {why}")

if __name__ == "__main__":
    main()
