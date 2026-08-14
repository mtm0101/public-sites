#!/usr/bin/env python3
"""Queue-aware DOL listening audio/transcript cache.

Source of truth for order: data/chatgpt/dol/catalog.json.

Default action initializes catalog/upcoming/state and processes the queue one test
at a time. It is safe to stop between or during tests; a later run resumes from
state/upcoming and retries any unfinished current item.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import unquote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from dol_vocab_utils import fetch_html  # noqa: E402

BASE = "https://tuhoc.dolenglish.vn/"
MEDIA_BASE = "https://media.dolenglish.vn/"
DOL_DIR = ROOT / "data" / "chatgpt" / "dol"
LISTENING_DIR = DOL_DIR / "listening"
SOURCE_CATALOG_PATH = DOL_DIR / "catalog.json"
LISTENING_CATALOG_PATH = LISTENING_DIR / "catalog.json"
UPCOMING_PATH = LISTENING_DIR / "upcoming.json"
STATE_PATH = LISTENING_DIR / "state.json"
MANIFEST_PATH = LISTENING_DIR / "manifest.json"


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def slug_from_queue_key(queue_key: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", queue_key.lower()).strip("-")


def answer_key_url_from_queue_key(queue_key: str) -> str | None:
    m = re.match(r"cam(\d+)-t(\d+)-listening$", queue_key)
    if m:
        return f"{BASE}luyen-thi-ielts/ielts-online-test-answer-key-cambridge-ielts-{m.group(1)}-test-{m.group(2)}-listening"
    m = re.match(r"ptp(\d+)-t(\d+)-listening$", queue_key)
    if m:
        return f"{BASE}luyen-thi-ielts/ielts-online-test-answer-key-practice-test-plus-{m.group(1)}-test-{m.group(2)}-listening"
    m = re.match(r"actual(\d+)-t(\d+)-listening$", queue_key)
    if m:
        return f"{BASE}luyen-thi-ielts/ielts-online-test-answer-key-actual-test-{m.group(1)}-test-{m.group(2)}-listening"
    return None


def extract_inner(html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("__NEXT_DATA__ not found")
    outer = json.loads(m.group(1))
    enc = outer.get("props", {}).get("pageProps", {}).get("encryptedData", "")
    if not enc:
        raise ValueError("encryptedData missing")
    return json.loads(unquote(enc))


def media_url(path: str | None) -> str:
    return MEDIA_BASE + str(path or "").lstrip("/")


def related_pages_from_inner(inner: dict) -> list[dict]:
    page_data = (inner.get("data") or {}).get("pageData") or {}
    return page_data.get("pages") or (page_data.get("pageDetail") or {}).get("pages") or []


def related_url_from_inner(inner: dict, page_type: str) -> str:
    for page in related_pages_from_inner(inner):
        if (page.get("contentType") == page_type or page.get("templateTypeId") == page_type) and page.get("url"):
            return BASE + str(page["url"]).lstrip("/")
    return ""


def practice_url_from_inner(inner: dict) -> str:
    """Return the canonical DOL `Làm bài` URL exposed by a related page."""
    return related_url_from_inner(inner, "DO_TEST")


def strip_question_payload(value):
    """Keep the test UI and sourced explanations while removing CMS/user metadata."""
    omitted = {
        "createdAt", "lastModifiedAt", "createdBy", "lastModifiedBy",
        "vocabularies", "userAnswers", "notes",
        "sheetTranscriptStr",
    }
    if isinstance(value, dict):
        return {
            key: strip_question_payload(item)
            for key, item in value.items()
            if key not in omitted
        }
    if isinstance(value, list):
        return [strip_question_payload(item) for item in value]
    return value


def test_sections(inner: dict) -> list[dict]:
    return (((inner.get("data") or {}).get("data") or {}).get("testSections") or [])


def explanation_count(inner: dict) -> int:
    count = 0

    def walk(value):
        nonlocal count
        if isinstance(value, dict):
            if isinstance(value.get("explanation"), dict):
                count += 1
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(test_sections(inner))
    return count


def fetch_test_inner(row: dict) -> dict:
    """Prefer DOL's answer page so answers, examples and explanations stay authoritative."""
    candidates = [row.get("answerKeyUrl") or ""]
    fallback_inner = None
    vocab_url = row.get("vocabUrl") or ""
    if vocab_url:
        vocab_inner = extract_inner(fetch_html(vocab_url))
        fallback_inner = vocab_inner if test_sections(vocab_inner) else None
        related_solution = related_url_from_inner(vocab_inner, "VIEW_SOLUTION")
        if related_solution and related_solution not in candidates:
            candidates.insert(0, related_solution)
    for url in candidates:
        if not url:
            continue
        try:
            inner = extract_inner(fetch_html(url))
        except Exception:
            continue
        if test_sections(inner):
            if explanation_count(inner):
                return inner
            fallback_inner = fallback_inner or inner
    if fallback_inner:
        return fallback_inner
    raise ValueError("DOL test sections not found")


def write_questions(row: dict, inner: dict, meta: dict) -> dict:
    data = (inner.get("data") or {}).get("data") or {}
    sections = []
    question_number = 1
    for index, section in enumerate(data.get("testSections") or [], start=1):
        groups = strip_question_payload(section.get("questionGroups") or [])
        section_total = sum(int(group.get("totalQuestion") or 0) for group in groups)
        sections.append(
            {
                "section": index,
                "name": section.get("name") or f"Section {index}",
                "duration": section.get("duration"),
                "questionStart": question_number,
                "questionEnd": question_number + max(0, section_total - 1),
                "questionGroups": groups,
            }
        )
        question_number += section_total
    test_url = practice_url_from_inner(inner)
    payload = {
        "schema": 1,
        "id": row["id"],
        "title": row.get("title") or row["id"],
        "group": row.get("group") or "",
        "book": row.get("book") or "",
        "testNum": row.get("testNum") or 0,
        "durationMinutes": int(data.get("durationInMinutes") or 40),
        "questionCount": question_number - 1,
        "testUrl": test_url,
        "answerKeyUrl": related_url_from_inner(inner, "VIEW_SOLUTION") or row.get("answerKeyUrl") or "",
        "sections": sections,
        "fetchedAt": now_iso(),
    }
    out_dir = LISTENING_DIR / slug_from_queue_key(row["id"])
    write_json(out_dir / "questions.json", payload)
    meta["questions"] = {
        "localJsonPath": "questions.json",
        "questionCount": payload["questionCount"],
        "availableLocal": bool(sections),
    }
    source = meta.get("source")
    if not isinstance(source, dict):
        source = {"answerKeyUrl": source or row.get("answerKeyUrl") or ""}
        meta["source"] = source
    source["testUrl"] = test_url
    return meta


def download(url: str, dest: Path, *, timeout: int = 120) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return True
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        request = Request(url, headers={"User-Agent": "ielts-practice-tool/1.0"})
        with urlopen(request, timeout=timeout) as response, tmp.open("wb") as output:
            shutil.copyfileobj(response, output)
        if tmp.stat().st_size > 0:
            tmp.replace(dest)
            return True
    except OSError:
        pass
    if tmp.exists():
        tmp.unlink()
    cmd = ["curl.exe", "-L", "-sS", "--fail", "--noproxy", "*", "--ssl-no-revoke", "--max-time", str(timeout), "-o", str(tmp), url]
    r = subprocess.run(cmd, check=False)
    if r.returncode != 0:
        if tmp.exists():
            tmp.unlink()
        return False
    tmp.replace(dest)
    return True


def subtitle_cues(section: dict) -> list[dict]:
    cues = []
    characters = {
        c.get("id"): c.get("name")
        for c in (section.get("script") or {}).get("characters") or []
        if isinstance(c, dict)
    }
    for i, cue in enumerate((section.get("script") or {}).get("subtitle") or [], start=1):
        data = cue.get("data") or {}
        text = str(data.get("text") or "").strip()
        if not text:
            continue
        start = data.get("start")
        end = data.get("end")
        cues.append(
            {
                "id": f"c{i}",
                "start": round(float(start or 0) / 1000, 3),
                "end": round(float(end or start or 0) / 1000, 3),
                "text": text,
                "speaker": characters.get(cue.get("character")) or "",
            }
        )
    return cues


def explanation_cues(section: dict) -> list[dict]:
    seen = set()
    out = []

    def walk(obj):
        if isinstance(obj, dict):
            exp = obj.get("explanation")
            if isinstance(exp, dict):
                for cue in exp.get("transcripts") or []:
                    text = str(cue.get("text") or "").strip()
                    start = cue.get("startTimeInSeconds")
                    end = cue.get("endTimeInSeconds")
                    key = (start, end, text)
                    if text and key not in seen:
                        seen.add(key)
                        out.append(
                            {
                                "start": float(start or 0),
                                "end": float(end or start or 0),
                                "text": text,
                                "speaker": ((cue.get("character") or {}).get("name") or ""),
                            }
                        )
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(section.get("questionGroups") or [])
    out.sort(key=lambda c: (c["start"], c["end"], c["text"]))
    for i, cue in enumerate(out, start=1):
        cue["id"] = f"e{i}"
    return out


def collect_tests(limit: int | None = None) -> list[dict]:
    source = read_json(SOURCE_CATALOG_PATH, {"books": []})
    tests = []
    order = 0
    for book in source.get("books", []):
        for page in book.get("pages", []):
            if page.get("skill") != "listening":
                continue
            qk = page.get("queueKey") or ""
            order += 1
            tests.append(
                {
                    "id": qk,
                    "queueKey": qk,
                    "order": order,
                    "title": page.get("title") or qk,
                    "group": book.get("group") or "",
                    "book": book.get("name") or "",
                    "testNum": page.get("testNum") or 0,
                    "vocabUrl": page.get("url") or "",
                    "answerKeyUrl": answer_key_url_from_queue_key(qk),
                }
            )
    return tests[:limit] if limit else tests


def meta_complete(meta: dict, *, require_audio: bool, require_vtt: bool) -> bool:
    sections = meta.get("sections") or []
    if not sections:
        return False
    for s in sections:
        if require_audio and not (s.get("audio") or {}).get("availableLocal"):
            return False
        if require_vtt and not (s.get("transcript") or {}).get("availableLocalVtt"):
            return False
        if not (s.get("transcript") or {}).get("cueCount"):
            return False
    return True


def ensure_meta_assets(meta: dict, *, download_audio: bool, download_vtt: bool) -> dict:
    out_dir = LISTENING_DIR / slug_from_queue_key(meta["id"])
    changed = False
    for s in meta.get("sections") or []:
        audio = s.get("audio") or {}
        transcript = s.get("transcript") or {}
        if download_audio and audio.get("remoteUrl"):
            local = out_dir / audio.get("localPath", "")
            ok = download(audio["remoteUrl"], local)
            if ok != bool(audio.get("availableLocal")):
                audio["availableLocal"] = ok
                changed = True
        if download_vtt and transcript.get("remoteUrl"):
            local = out_dir / transcript.get("localVttPath", "")
            ok = download(transcript["remoteUrl"], local)
            if ok != bool(transcript.get("availableLocalVtt")):
                transcript["availableLocalVtt"] = ok
                changed = True
    if changed:
        (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return meta


def process_test(row: dict, *, download_audio: bool, download_vtt: bool, force: bool) -> dict:
    out_dir = LISTENING_DIR / slug_from_queue_key(row["id"])
    meta_path = out_dir / "meta.json"
    if meta_path.exists() and not force:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("sections"):
            return ensure_meta_assets(meta, download_audio=download_audio, download_vtt=download_vtt)

    inner = fetch_test_inner(row)
    data = (inner.get("data") or {}).get("data") or {}
    sections = []
    for idx, sec in enumerate(data.get("testSections") or [], start=1):
        script = sec.get("script") or {}
        audio = script.get("audio") or {}
        transcript = script.get("transcript") or {}
        audio_name = f"section-{idx}.m4a"
        vtt_name = f"section-{idx}.vtt"
        cue_name = f"section-{idx}.json"
        cues = subtitle_cues(sec) or explanation_cues(sec)
        (out_dir / "transcripts").mkdir(parents=True, exist_ok=True)
        (out_dir / "transcripts" / cue_name).write_text(
            json.dumps({"section": idx, "cues": cues}, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
        audio_ok = False
        vtt_ok = False
        if audio.get("path") and download_audio:
            audio_ok = download(media_url(audio.get("path")), out_dir / "audio" / audio_name)
        if transcript.get("path") and download_vtt:
            vtt_ok = download(media_url(transcript.get("path")), out_dir / "transcripts" / vtt_name)
        sections.append(
            {
                "section": idx,
                "name": sec.get("name") or f"Section {idx}",
                "duration": sec.get("duration"),
                "audio": {
                    "remoteUrl": media_url(audio.get("path")) if audio.get("path") else "",
                    "localPath": f"audio/{audio_name}",
                    "availableLocal": audio_ok or (out_dir / "audio" / audio_name).exists(),
                    "size": audio.get("size"),
                },
                "transcript": {
                    "remoteUrl": media_url(transcript.get("path")) if transcript.get("path") else "",
                    "localVttPath": f"transcripts/{vtt_name}",
                    "availableLocalVtt": vtt_ok or (out_dir / "transcripts" / vtt_name).exists(),
                    "localJsonPath": f"transcripts/{cue_name}",
                    "cueCount": len(cues),
                },
            }
        )
    meta = {
        "schema": 1,
        "id": row["id"],
        "title": row["title"],
        "group": row["group"],
        "book": row["book"],
        "testNum": row["testNum"],
        "order": row.get("order"),
        "source": {
            "vocabUrl": row["vocabUrl"],
            "answerKeyUrl": row["answerKeyUrl"],
            "masterUrl": f"{BASE}luyen-thi-ielts/free-ielts-online-test",
        },
        "sections": sections,
        "fetchedAt": now_iso(),
    }
    meta = write_questions(row, inner, meta)
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return meta


def manifest_row(meta: dict) -> dict:
    return {
        "id": meta["id"],
        "title": meta.get("title") or meta["id"],
        "group": meta.get("group") or "",
        "book": meta.get("book") or "",
        "testNum": meta.get("testNum") or 0,
        "metaPath": f"{slug_from_queue_key(meta['id'])}/meta.json",
        "sectionCount": len(meta.get("sections") or []),
        "localAudioCount": sum(1 for s in meta.get("sections") or [] if (s.get("audio") or {}).get("availableLocal")),
        "cueCount": sum((s.get("transcript") or {}).get("cueCount", 0) for s in meta.get("sections") or []),
        "questionCount": int((meta.get("questions") or {}).get("questionCount") or 0),
        "questionsPath": f"{slug_from_queue_key(meta['id'])}/questions.json" if (meta.get("questions") or {}).get("availableLocal") else "",
        "testUrl": (meta.get("source") or {}).get("testUrl", "") if isinstance(meta.get("source"), dict) else "",
    }


def download_questions(args) -> int:
    tests = collect_tests(args.limit or None)
    if args.only:
        selected = {item.strip() for item in args.only.split(",") if item.strip()}
        tests = [row for row in tests if row.get("id") in selected]
    failures = []

    def refresh(row: dict) -> str:
        out_dir = LISTENING_DIR / slug_from_queue_key(row["id"])
        questions_path = out_dir / "questions.json"
        meta_path = out_dir / "meta.json"
        if questions_path.exists() and meta_path.exists() and not args.force:
            return "cached"
        inner = fetch_test_inner(row)
        meta = read_json(meta_path, {
            "schema": 1, "id": row["id"], "title": row.get("title") or row["id"],
            "group": row.get("group") or "", "book": row.get("book") or "",
            "testNum": row.get("testNum") or 0, "sections": [],
            "source": {"vocabUrl": row.get("vocabUrl") or "", "answerKeyUrl": row.get("answerKeyUrl") or ""},
        })
        meta = write_questions(row, inner, meta)
        write_json(meta_path, meta)
        return "questions"

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        pending = {pool.submit(refresh, row): row for row in tests}
        completed = 0
        for future in as_completed(pending):
            row = pending[future]
            completed += 1
            try:
                action = future.result()
                print(f"[{completed}/{len(tests)}] {action} {row['id']}")
            except Exception as error:
                failures.append({"id": row["id"], "error": str(error)})
                print(f"[{completed}/{len(tests)}] failed {row['id']}: {error}", file=sys.stderr)
    rebuild_manifest_from_state(audio_downloaded=False)
    print(f"questions complete: {len(tests) - len(failures)}/{len(tests)}")
    if failures:
        print(json.dumps(failures, ensure_ascii=False, indent=1), file=sys.stderr)
        return 1
    return 0


def rebuild_manifest_from_state(*, audio_downloaded: bool) -> dict:
    state = read_json(STATE_PATH, {"sent": []})
    rows = []
    seen = set()
    for item in state.get("sent") or []:
        qk = item.get("id") or item.get("queueKey")
        if not qk or qk in seen:
            continue
        meta_path = LISTENING_DIR / slug_from_queue_key(qk) / "meta.json"
        if meta_path.exists():
            rows.append(manifest_row(json.loads(meta_path.read_text(encoding="utf-8"))))
            seen.add(qk)
    rows.sort(key=lambda r: (state_order(r["id"]), r["id"]))
    manifest = {
        "schema": 1,
        "generatedFrom": str(SOURCE_CATALOG_PATH.relative_to(ROOT)),
        "generatedAt": now_iso(),
        "audioDownloaded": bool(audio_downloaded),
        "tests": rows,
    }
    write_json(MANIFEST_PATH, manifest)
    return manifest


def state_order(qk: str) -> int:
    catalog = read_json(LISTENING_CATALOG_PATH, {"tests": []})
    for row in catalog.get("tests") or []:
        if row.get("id") == qk:
            return int(row.get("order") or 999999)
    return 999999


def init_tracking(*, reset: bool = False) -> tuple[dict, dict, dict]:
    LISTENING_DIR.mkdir(parents=True, exist_ok=True)
    tests = collect_tests()
    catalog = {
        "schema": 1,
        "generatedFrom": str(SOURCE_CATALOG_PATH.relative_to(ROOT)),
        "generatedAt": now_iso(),
        "total": len(tests),
        "tests": tests,
    }
    write_json(LISTENING_CATALOG_PATH, catalog)

    if reset or not STATE_PATH.exists():
        state = {
            "schema": 1,
            "_readme": "DOL listening download tracking. sent = completed local caches; current = retryable if interrupted; failed = errors kept for review.",
            "sent": [],
            "failed": [],
            "current": None,
        }
    else:
        state = read_json(STATE_PATH, {"schema": 1, "sent": [], "failed": [], "current": None})
        state.setdefault("sent", [])
        state.setdefault("failed", [])
        state.setdefault("current", None)
    sent = {r.get("id") or r.get("queueKey") for r in state.get("sent") or []}
    queue = [row for row in tests if row.get("id") not in sent]
    upcoming = {
        "schema": 1,
        "_readme": "queue[0] is processed next. Rebuilt from listening/catalog.json minus state.sent.",
        "generatedAt": now_iso(),
        "remaining": len(queue),
        "queue": queue,
    }
    write_json(STATE_PATH, state)
    write_json(UPCOMING_PATH, upcoming)
    return catalog, state, upcoming


def mark_sent(state: dict, row: dict, meta: dict) -> dict:
    qk = row["id"]
    state["sent"] = [x for x in state.get("sent", []) if (x.get("id") or x.get("queueKey")) != qk]
    state["failed"] = [x for x in state.get("failed", []) if (x.get("id") or x.get("queueKey")) != qk]
    state["sent"].append(
        {
            "id": qk,
            "queueKey": qk,
            "title": meta.get("title") or row.get("title"),
            "group": meta.get("group") or row.get("group"),
            "book": meta.get("book") or row.get("book"),
            "testNum": meta.get("testNum") or row.get("testNum"),
            "processedAt": now_iso(),
            "metaFile": f"{slug_from_queue_key(qk)}/meta.json",
            "sectionCount": len(meta.get("sections") or []),
            "localAudioCount": sum(1 for s in meta.get("sections") or [] if (s.get("audio") or {}).get("availableLocal")),
            "cueCount": sum((s.get("transcript") or {}).get("cueCount", 0) for s in meta.get("sections") or []),
        }
    )
    state["current"] = None
    write_json(STATE_PATH, state)
    return state


def mark_failed(state: dict, row: dict, error: Exception) -> dict:
    qk = row["id"]
    state["failed"] = [x for x in state.get("failed", []) if (x.get("id") or x.get("queueKey")) != qk]
    state["failed"].append(
        {
            "id": qk,
            "queueKey": qk,
            "title": row.get("title"),
            "failedAt": now_iso(),
            "error": str(error),
        }
    )
    state["current"] = None
    write_json(STATE_PATH, state)
    return state


def pop_completed_from_upcoming(state: dict) -> dict:
    sent = {r.get("id") or r.get("queueKey") for r in state.get("sent") or []}
    catalog = read_json(LISTENING_CATALOG_PATH, {"tests": []})
    queue = [row for row in catalog.get("tests") or [] if row.get("id") not in sent]
    upcoming = read_json(UPCOMING_PATH, {"schema": 1})
    upcoming.update({"generatedAt": now_iso(), "remaining": len(queue), "queue": queue})
    write_json(UPCOMING_PATH, upcoming)
    return upcoming


def run_queue(args) -> int:
    _, state, upcoming = init_tracking(reset=args.reset)
    processed = 0
    attempted = set()
    while True:
        queue = upcoming.get("queue") or []
        if not queue:
            print("DOL listening queue complete.")
            rebuild_manifest_from_state(audio_downloaded=args.download_audio)
            return 0
        if args.max_tests and processed >= args.max_tests:
            print(f"Stopped after --max-tests {args.max_tests}. Remaining: {len(queue)}")
            rebuild_manifest_from_state(audio_downloaded=args.download_audio)
            return 0
        row = next((item for item in queue if item.get("id") not in attempted), None)
        if row is None:
            print("Reached the end of this run. Failed tests remain pending for the next run.")
            rebuild_manifest_from_state(audio_downloaded=args.download_audio)
            return 1
        attempted.add(row["id"])
        if not row.get("answerKeyUrl"):
            print(f"skip {row.get('id')}: no answer-key URL")
            state = mark_failed(state, row, RuntimeError("no answer-key URL"))
            upcoming = pop_completed_from_upcoming(state)
            # Remove impossible URL rows from queue this run by marking as sent-like failed only if requested.
            # Keep it pending for visibility unless --skip-failed is set.
            if not args.skip_failed:
                return 1
            state["sent"].append({"id": row.get("id"), "queueKey": row.get("id"), "processedAt": now_iso(), "skipNote": "no answer-key URL"})
            write_json(STATE_PATH, state)
            upcoming = pop_completed_from_upcoming(state)
            continue
        print(f"[{processed + 1}] {row['id']} - {row.get('title')}")
        state["current"] = {"id": row["id"], "title": row.get("title"), "startedAt": now_iso()}
        write_json(STATE_PATH, state)
        try:
            meta = process_test(row, download_audio=args.download_audio, download_vtt=args.download_vtt, force=args.force)
            if not meta_complete(meta, require_audio=args.download_audio, require_vtt=args.download_vtt):
                raise RuntimeError("download incomplete: missing audio/vtt/cues")
            state = mark_sent(state, row, meta)
            upcoming = pop_completed_from_upcoming(state)
            rebuild_manifest_from_state(audio_downloaded=args.download_audio)
            processed += 1
            print(f"  done: {row['id']} | remaining {upcoming.get('remaining', 0)}")
        except KeyboardInterrupt:
            print("Interrupted. Current item remains retryable in state.json.")
            return 130
        except Exception as e:
            print(f"  failed: {e}", file=sys.stderr)
            state = mark_failed(state, row, e)
            rebuild_manifest_from_state(audio_downloaded=args.download_audio)
            if args.continue_on_error:
                processed += 1
                continue
            return 1


def legacy_batch(args) -> int:
    tests = collect_tests(args.limit or None)
    rows = []
    for i, row in enumerate(tests, start=1):
        if not row.get("answerKeyUrl"):
            print(f"[{i}/{len(tests)}] skip {row['id']}: no answer-key URL")
            continue
        try:
            print(f"[{i}/{len(tests)}] {row['id']}")
            meta = process_test(row, download_audio=args.download_audio, download_vtt=args.download_vtt, force=args.force)
            rows.append(manifest_row(meta))
        except Exception as e:
            print(f"  failed: {e}", file=sys.stderr)
    manifest = {
        "schema": 1,
        "generatedFrom": str(SOURCE_CATALOG_PATH.relative_to(ROOT)),
        "generatedAt": now_iso(),
        "audioDownloaded": bool(args.download_audio),
        "tests": rows,
    }
    write_json(MANIFEST_PATH, manifest)
    print(f"wrote {MANIFEST_PATH} ({len(rows)} tests)")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="Legacy batch: fetch only first N listening tests")
    ap.add_argument("--max-tests", type=int, default=0, help="Queue runner: process at most N tests this run")
    ap.add_argument("--download-audio", action="store_true", help="Download section .m4a files")
    ap.add_argument("--download-vtt", action="store_true", help="Download original .vtt files")
    ap.add_argument("--force", action="store_true", help="Refresh existing meta files")
    ap.add_argument("--reset", action="store_true", help="Reset listening state/upcoming before queue run")
    ap.add_argument("--init-only", action="store_true", help="Only rebuild catalog/upcoming/state, then stop")
    ap.add_argument("--legacy-batch", action="store_true", help="Use the old manifest-only batch behavior")
    ap.add_argument("--continue-on-error", action="store_true", help="Skip failed items and continue queue")
    ap.add_argument("--skip-failed", action="store_true", help="Treat items without answer-key URL as skipped")
    ap.add_argument("--download-questions", action="store_true", help="Cache the full interactive question model for every test")
    ap.add_argument("--only", default="", help="Comma-separated test IDs to refresh with --download-questions")
    ap.add_argument("--workers", type=int, default=6, help="Parallel DOL page fetches for --download-questions")
    args = ap.parse_args()
    LISTENING_DIR.mkdir(parents=True, exist_ok=True)
    if args.legacy_batch or args.limit:
        if args.download_questions:
            raise SystemExit(download_questions(args))
        raise SystemExit(legacy_batch(args))
    if args.download_questions:
        raise SystemExit(download_questions(args))
    init_tracking(reset=args.reset)
    if args.init_only:
        print(f"wrote {LISTENING_CATALOG_PATH}, {UPCOMING_PATH}, {STATE_PATH}")
        raise SystemExit(0)
    raise SystemExit(run_queue(args))


if __name__ == "__main__":
    main()
