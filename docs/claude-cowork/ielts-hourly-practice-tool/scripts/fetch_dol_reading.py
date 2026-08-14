#!/usr/bin/env python3
"""Cache DOL Reading L3 passages, excluding the question area.

The DOL catalog is the queue source.  For every reading vocab entry it finds
the matching L3 page, then saves only ``testSections[].passage`` (the content
shown between "Bài đọc" and "Câu hỏi") in data/chatgpt/dol/reading.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from dol_vocab_utils import extract_next_inner, fetch_html  # noqa: E402

DOL_DIR = ROOT / "data" / "chatgpt" / "dol"
READING_DIR = DOL_DIR / "reading"
READING_TEST_DIR = DOL_DIR / "reading-test"
CATALOG = DOL_DIR / "catalog.json"
STATE = READING_DIR / "state.json"
MANIFEST = READING_DIR / "manifest.json"
READING_TEST_MANIFEST = READING_TEST_DIR / "manifest.json"


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default
    except (OSError, json.JSONDecodeError):
        return default


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def paragraph_blocks(value) -> list[str]:
    """Keep DOL's blank-line paragraph boundaries in regular passages."""
    raw = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    return [text(block) for block in re.split(r"\n\s*\n+", raw) if text(block)]


def paragraph_label(marked_by, index: int) -> str:
    if str(marked_by or "").upper() == "ALPHABET":
        return chr(64 + index) if index <= 26 else str(index)
    if str(marked_by or "").upper() in {"NUMBER", "NUMERIC"}:
        return str(index)
    return ""


def reading_rows() -> list[dict]:
    rows = []
    for book in read(CATALOG, {"books": []}).get("books", []):
        for page in book.get("pages", []):
            if page.get("skill") != "reading" or not page.get("queueKey"):
                continue
            title = page.get("title") or page["queueKey"]
            if "listening test" in title.lower():
                title = f"{book.get('name') or 'IELTS'} - Reading Test {page.get('testNum') or ''}".strip()
            rows.append({
                "id": page["queueKey"], "title": title,
                "group": book.get("group") or "", "book": book.get("name") or "",
                "testNum": page.get("testNum") or 0, "vocabUrl": page.get("url") or "",
            })
    return rows


def l3_urls(row: dict) -> list[str]:
    """Return possible L3 URLs, including legacy CAM landing-page patterns."""
    slug = row["vocabUrl"].rstrip("/").rsplit("/", 1)[-1]
    slug = re.sub(r"^(?:ielts-online-test-)?tu-vung-", "", slug)
    slug = re.sub(r"-vocab$", "", slug)
    short_url = "https://tuhoc.dolenglish.vn/luyen-thi-ielts/" + slug
    match = re.fullmatch(r"cam(\d+)-t(\d+)-reading", row["id"], re.I)
    if match and int(match.group(1)) <= 19:
        book, test = match.groups()
        return [
            "https://tuhoc.dolenglish.vn/luyen-thi-ielts/"
            f"ielts-online-test-cam-ielts-{book}-test-{test}-reading-"
            "questions-answer-key-de-bai-dap-an-giai-thich-chi-tiet-free-pdf-download",
            short_url,
        ]
    ptp = re.fullmatch(r"ptp(\d+)-t(\d+)-reading", row["id"], re.I)
    if ptp:
        book, test = ptp.groups()
        return [
            "https://tuhoc.dolenglish.vn/luyen-thi-ielts/"
            f"ielts-online-test-practice-test-plus-{book}-test-{test}-reading-"
            "questions-answer-key-de-bai-dap-an-giai-thich-chi-tiet-free-pdf-download",
            short_url,
        ]
    actual = re.fullmatch(r"actual(\d+)-t(\d+)-reading", row["id"], re.I)
    if actual:
        book, test = actual.groups()
        candidates = []
        if book == "1":
            candidates.append(
                "https://tuhoc.dolenglish.vn/luyen-thi-ielts/"
                f"ielts-online-test-ielts-actual-test-{book}-reading-test-{test}-"
                "questions-answer-key-audio-transcript-dap-an-giai-thich-chi-tiet-free-pdf-download"
            )
        candidates.append(
            "https://tuhoc.dolenglish.vn/luyen-thi-ielts/"
            f"ielts-online-test-actual-test-{book}-test-{test}-reading-"
            "questions-answer-key-de-bai-dap-an-giai-thich-chi-tiet-free-pdf-download"
        )
        candidates.append(short_url)
        return candidates
    candidates = []
    try:
        inner = extract_next_inner(fetch_html(row["vocabUrl"]))
        pages = (((inner.get("pageData") or {}).get("pageDetail") or {}).get("pages") or [])
        for page in pages:
            if page.get("templateTypeId") == "VIEW_TEST_QUESTION" and page.get("url"):
                candidates.append(urljoin("https://tuhoc.dolenglish.vn/", page["url"]))
    except Exception:
        # A derived URL is still worth trying when a companion vocab page is
        # temporarily unavailable.
        pass
    # CAM 9–19 use a long SEO URL. It is the actual L3 page selected by
    # “Đề và đáp án” from the L2 book page, not the short URL above.
    match = re.fullmatch(r"cam(\d+)-t(\d+)-reading", row["id"], re.I)
    if match:
        book, test = match.groups()
        candidates.append(
            "https://tuhoc.dolenglish.vn/luyen-thi-ielts/"
            f"ielts-online-test-cam-ielts-{book}-test-{test}-reading-"
            "questions-answer-key-de-bai-dap-an-giai-thich-chi-tiet-free-pdf-download"
        )
    # Newer CAM pages use this short form; retain it as a fallback for every
    # catalog family after the known legacy CAM URL above.
    candidates.append(short_url)
    return list(dict.fromkeys(candidates))


def strip_test_payload(value):
    omitted = {"createdAt", "lastModifiedAt", "createdBy", "lastModifiedBy", "vocabularies", "userAnswers", "notes", "sheetTranscriptStr"}
    if isinstance(value, dict):
        return {key: strip_test_payload(item) for key, item in value.items() if key not in omitted}
    if isinstance(value, list):
        return [strip_test_payload(item) for item in value]
    return value


def related_page_url(inner: dict, page_type: str) -> str:
    page_data = inner.get("pageData") or {}
    pages = page_data.get("pages") or (page_data.get("pageDetail") or {}).get("pages") or []
    for page in pages:
        if (page.get("templateTypeId") == page_type or page.get("contentType") == page_type) and page.get("url"):
            return urljoin("https://tuhoc.dolenglish.vn/", page["url"])
    return ""


def passages_from_l3(url: str) -> tuple[str, list[dict], dict, dict]:
    inner = extract_next_inner(fetch_html(url))
    data = (inner.get("data") or {}).get("data") or {}
    sections = data.get("testSections") or []
    passages = []
    for index, section in enumerate(sections, start=1):
        source = section.get("passage") or {}
        paragraphs = [text(p.get("content")) for p in source.get("paragraphs") or [] if text(p.get("content"))]
        # Some regular passages use one ``paragraph`` object instead of the
        # annotated passage's ``paragraphs`` array.
        if not paragraphs and text((source.get("paragraph") or {}).get("content")):
            paragraphs = paragraph_blocks((source.get("paragraph") or {}).get("content"))
        if not paragraphs:
            continue
        passages.append({
            "number": index,
            "label": source.get("passageType") or f"PASSAGE{index}",
            "title": text(source.get("title")) or f"Passage {index}",
            "subtitle": text(source.get("subTitle")),
            "paragraphs": [
                {"label": paragraph_label(source.get("markedBy"), i), "en": value, "vi": ""}
                for i, value in enumerate(paragraphs, start=1)
            ],
        })
    page_title = text((((inner.get("pageData") or {}).get("seoPage") or {}).get("title")))
    return page_title, passages, data, inner


def write_reading_test(row: dict, source_url: str, data: dict, inner: dict, passages: list[dict]) -> None:
    sections = []
    question_number = 1
    for index, section in enumerate(data.get("testSections") or [], start=1):
        groups = strip_test_payload(section.get("questionGroups") or [])
        total = sum(int(group.get("totalQuestion") or 0) for group in groups)
        passage = passages[index - 1] if index <= len(passages) else {"number": index, "title": f"Passage {index}", "subtitle": "", "paragraphs": []}
        sections.append({
            "section": index,
            "name": section.get("name") or passage.get("title") or f"Part {index}",
            "duration": section.get("duration") or 20,
            "questionStart": question_number,
            "questionEnd": question_number + max(0, total - 1),
            "passage": passage,
            "questionGroups": groups,
        })
        question_number += total
    payload = {
        "schema": 1, "id": row["id"], "title": row["title"], "group": row["group"],
        "book": row["book"], "testNum": row["testNum"], "durationMinutes": int(data.get("durationInMinutes") or 60),
        "questionCount": question_number - 1, "testUrl": related_page_url(inner, "DO_TEST"),
        "answerKeyUrl": related_page_url(inner, "VIEW_SOLUTION") or source_url,
        "sourceUrl": source_url, "sections": sections, "fetchedAt": now(),
    }
    out_dir = READING_TEST_DIR / row["id"]
    write(out_dir / "questions.json", payload)


def rebuild_reading_test_manifest() -> None:
    tests = []
    for row in reading_rows():
        path = READING_TEST_DIR / row["id"] / "questions.json"
        doc = read(path, {})
        if not doc.get("sections"):
            continue
        tests.append({
            "id": row["id"], "title": row["title"], "group": row["group"], "book": row["book"],
            "testNum": row["testNum"], "sectionCount": len(doc["sections"]), "questionCount": doc.get("questionCount", 0),
            "questionsPath": f"{row['id']}/questions.json", "testUrl": doc.get("testUrl") or "",
        })
    write(READING_TEST_MANIFEST, {"schema": 1, "generatedAt": now(), "tests": tests})


def process(row: dict, force: bool) -> dict:
    file_name = row["id"] + ".json"
    path = READING_DIR / file_name
    if path.exists() and not force:
        return read(path, {})
    tried = []
    title, passages, url, data, inner = "", [], "", {}, {}
    for candidate in l3_urls(row):
        tried.append(candidate)
        title, passages, data, inner = passages_from_l3(candidate)
        if passages:
            url = candidate
            break
    if not passages:
        raise RuntimeError("no reading passages were found at: " + "; ".join(tried))
    doc = {
        "schema": 1, "id": row["id"], "title": row["title"], "pageTitle": title,
        "group": row["group"], "book": row["book"], "testNum": row["testNum"],
        "sourceUrl": url, "fetchedAt": now(), "passageCount": len(passages),
        "translationNote": "DOL does not include Vietnamese passage translations; vi is reserved for user-supplied translations.",
        "passages": passages,
    }
    write(path, doc)
    write_reading_test(row, url, data, inner, passages)
    return doc


def rebuild_manifest(done: list[dict]) -> None:
    tests = []
    for item in done:
        doc = read(READING_DIR / item.get("file", ""), {})
        if doc.get("passages"):
            tests.append({k: doc.get(k) for k in ("id", "title", "group", "book", "testNum", "sourceUrl", "fetchedAt", "passageCount")})
            tests[-1]["file"] = item["file"]
    write(MANIFEST, {"schema": 1, "generatedAt": now(), "tests": tests})


def main() -> int:
    ap = argparse.ArgumentParser(description="Download DOL Reading passage content from L3 pages.")
    ap.add_argument("--id", dest="test_id", help="Process only one reading test ID, for example cam20-t1-reading")
    ap.add_argument("--max-tests", type=int, default=0, help="Process at most N tests this run")
    ap.add_argument("--force", action="store_true", help="Refresh existing cached tests")
    ap.add_argument("--reset", action="store_true", help="Forget completion tracking and rebuild")
    ap.add_argument("--continue-on-error", action="store_true", help="Record errors and continue")
    ap.add_argument("--download-tests", action="store_true", help="Refresh all interactive Reading test questions and explanations")
    ap.add_argument("--rebuild-test-manifest", action="store_true", help="Rebuild the interactive Reading manifest from cached payloads")
    ap.add_argument("--workers", type=int, default=8, help="Parallel fetches for --download-tests")
    args = ap.parse_args()
    READING_DIR.mkdir(parents=True, exist_ok=True)
    READING_TEST_DIR.mkdir(parents=True, exist_ok=True)
    if args.rebuild_test_manifest:
        rebuild_reading_test_manifest()
        print(f"Reading test manifest rebuilt: {READING_TEST_MANIFEST}")
        return 0
    if args.download_tests:
        rows = reading_rows()
        failures = []
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            pending = {pool.submit(process, row, True): row for row in rows}
            for index, future in enumerate(as_completed(pending), start=1):
                row = pending[future]
                try:
                    future.result(); print(f"[{index}/{len(rows)}] reading test {row['id']}")
                except Exception as exc:
                    failures.append({"id": row["id"], "error": str(exc)}); print(f"failed {row['id']}: {exc}", file=sys.stderr)
        rebuild_reading_test_manifest()
        print(f"Reading tests complete: {len(rows)-len(failures)}/{len(rows)}")
        return 1 if failures else 0
    state = {"schema": 1, "sent": [], "failed": [], "current": None} if args.reset else read(STATE, {"schema": 1, "sent": [], "failed": [], "current": None})
    completed = {x.get("id") for x in state.get("sent", [])}
    catalog_rows = reading_rows()
    if args.test_id:
        catalog_rows = [r for r in catalog_rows if r["id"].lower() == args.test_id.lower()]
        if not catalog_rows:
            ap.error(f"unknown reading test ID: {args.test_id}")
    rows = [r for r in catalog_rows if args.force or r["id"] not in completed]
    failed = {x.get("id") for x in state.get("failed", [])}
    # Retry already-known failures first after a scraper update; users do not
    # need to wait for the whole catalog to reach a previously failed book.
    queue = [r for r in rows if r["id"] in failed] + [r for r in rows if r["id"] not in failed]
    print(f"DOL Reading: {len(queue)} test(s) queued. Safe to stop; rerun resumes.")
    count = 0
    for row in queue:
        if args.max_tests and count >= args.max_tests:
            break
        state["current"] = {"id": row["id"], "startedAt": now()}; write(STATE, state)
        try:
            doc = process(row, args.force)
            state["sent"] = [x for x in state["sent"] if x.get("id") != row["id"]]
            state["sent"].append({"id": row["id"], "title": row["title"], "file": row["id"] + ".json", "passageCount": doc["passageCount"], "processedAt": now()})
            state["failed"] = [x for x in state["failed"] if x.get("id") != row["id"]]
            state["current"] = None; write(STATE, state); rebuild_manifest(state["sent"])
            count += 1; print(f"done {row['id']}: {doc['passageCount']} passages")
        except Exception as exc:
            state["failed"] = [x for x in state["failed"] if x.get("id") != row["id"]]
            state["failed"].append({"id": row["id"], "error": str(exc), "failedAt": now()})
            state["current"] = None; write(STATE, state); rebuild_manifest(state["sent"])
            print(f"failed {row['id']}: {exc}", file=sys.stderr)
            if not args.continue_on_error:
                return 1
    rebuild_manifest(state["sent"])
    print(f"Reading cache ready: {len(state['sent'])} tests in {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
