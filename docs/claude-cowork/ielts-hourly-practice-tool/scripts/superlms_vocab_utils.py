"""Fetch DOL SuperLMS course vocab via authenticated API → dol-vocab JSON."""
from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from dol_vocab_utils import (  # noqa: E402
    POS_MAP,
    enrich_doc_examples,
    example_card_html,
    example_ipa_html,
    rebuild_passage_sections,
    slugify,
    wrap_ipa,
)

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
DOL = ROOT / "data" / "chatgpt" / "dol"
COURSES_PATH = DOL / "superlms-courses.json"
JWT_PATH = SCRIPTS / ".dol-jwt"

VOCAB_API = "https://api.dolenglish.vn/vocab-v2/api"
OFFLINE_API = "https://api.dolenglish.vn/offline-course-management/api"
SHEET_API = "https://api.dolenglish.vn/course-app-sheet/api"


def load_jwt(explicit: str | None = None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    env = (os.environ.get("DOL_JWT") or "").strip()
    if env:
        return env
    if JWT_PATH.is_file():
        return JWT_PATH.read_text(encoding="utf-8").strip()
    raise RuntimeError(
        "Missing DOL JWT — set DOL_JWT, pass --jwt, or save token to scripts/.dol-jwt"
    )


def jwt_contact_id(jwt: str) -> str | None:
    try:
        payload = jwt.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return str(data.get("hsContactId") or data.get("uid") or "") or None
    except (IndexError, json.JSONDecodeError, ValueError):
        return None


def api_get(url: str, jwt: str, timeout: int = 60) -> dict | list:
    headers = {
        "User-Agent": "ielts-practice-tool/1.0",
        "Authorization": f"Bearer {jwt}",
        "Accept": "application/json",
        "Origin": "https://superlms.dolenglish.vn",
        "Referer": "https://superlms.dolenglish.vn/",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {e.code} {url}: {body[:240]}") from e


def find_registration_key(course_id: str, jwt: str) -> str | None:
    contact = jwt_contact_id(jwt)
    url = f"{SHEET_API}/course-appsheet/subclass/{course_id}/registrations"
    regs = api_get(url, jwt)
    if not isinstance(regs, list):
        return None
    for row in regs:
        if contact and str(row.get("contactId")) == contact:
            return row.get("key")
    for row in regs:
        keys = row.get("subClassKeys") or []
        if course_id in keys:
            return row.get("key")
    return regs[0].get("key") if regs else None


def list_course_vocab_sets(course_id: str, reg_key: str, jwt: str) -> list[dict]:
    items: list[dict] = []
    page = 0
    while True:
        url = (
            f"{OFFLINE_API}/learning-management/courses/{course_id}/vocab-sets"
            f"?studentRegistrationKey={reg_key}&page={page}&size=50"
        )
        data = api_get(url, jwt)
        batch = (data.get("content") if isinstance(data, dict) else None) or []
        items.extend(batch)
        last = bool(data.get("last")) if isinstance(data, dict) else True
        if last or len(batch) < 50:
            break
        page += 1
    return items


def parse_set_meta(set_name: str) -> tuple[str, int, str]:
    """Return (skill, lesson_num, topic_slug)."""
    skill = "writing"
    for sk in ("writing", "reading", "speaking", "listening"):
        if re.search(rf"\b{sk}\b", set_name, re.I):
            skill = sk
            break
    m = re.search(r"\bL(\d+)\b", set_name, re.I)
    lesson_num = int(m.group(1)) if m else 0
    parts = [p.strip() for p in set_name.split(" - ")]
    topic = parts[-1] if parts else set_name
    return skill, lesson_num, slugify(topic, 32)


def queue_key(course_id: str, set_name: str) -> str:
    _, lesson_num, topic = parse_set_meta(set_name)
    return f"superlms-{course_id}-l{lesson_num}-{topic}"


def detail_url(course_id: str, course_vocab_set_id: str) -> str:
    return (
        f"https://superlms.dolenglish.vn/my-classes/{course_id}/vocab/{course_vocab_set_id}"
    )


def fetch_vocab_rows(vocab_set_id: str, jwt: str) -> list[dict]:
    url = f"{VOCAB_API}/v2/user-vocab-sets/vocab-set/{vocab_set_id}/vocabs"
    data = api_get(url, jwt)
    return data if isinstance(data, list) else []


def build_doc(
    *,
    course: dict,
    set_row: dict,
    vocabs: list[dict],
    enrich: bool = True,
) -> dict:
    course_id = course["courseId"]
    group = course["group"]
    set_name = (set_row.get("name") or "").strip()
    course_vocab_set_id = set_row.get("courseVocabSetId") or set_row.get("id") or ""
    vocab_set_id = set_row.get("vocabSetId") or ""
    skill, lesson_num, _ = parse_set_meta(set_name)
    qkey = queue_key(course_id, set_name)
    url = detail_url(course_id, course_vocab_set_id)

    items: list[dict] = []
    words: list[str] = []
    for vi, v in enumerate(vocabs):
        text = (v.get("term") or "").strip()
        if not text:
            continue
        pos_raw = (v.get("partOfSpeeches") or [""])[0]
        pos = POS_MAP.get(str(pos_raw).upper(), str(pos_raw).lower())
        vn_raw = (v.get("viDefinition") or "").strip()
        vn = f"({pos}). {vn_raw}" if pos and vn_raw else vn_raw
        ctx = (v.get("wordInContexts") or [{}])[0]
        ex = (ctx.get("enContext") or "").strip()
        ex_vi = (ctx.get("meaning") or "").strip()
        ipa = wrap_ipa(v.get("pronounce") or "")
        rec = {
            "id": f"v1-{slugify(text)}-{vi}",
            "passageLabel": set_name,
            "passageName": set_name,
            "passageNum": 1,
            "text": text,
            "pos": pos,
            "vn": vn,
            "ipaUK": ipa,
            "example": ex,
            "exampleVi": ex_vi,
            "exampleIpa": example_ipa_html(ex, text, ipa) if ex else "",
        }
        items.append(rec)
        words.append(text)

    cards = [
        example_card_html(
            x.get("text") or "",
            x.get("vn") or "",
            x.get("example") or "",
            x.get("exampleVi") or "",
        )
        for x in items
    ]
    sections = [
        {
            "id": "vocab",
            "title": set_name,
            "level": 1,
            "html": "\n".join(cards),
        },
        {
            "id": "sources",
            "title": "Sources",
            "level": 1,
            "html": (
                f'<p class="en">Vocabulary from '
                f'<a class="ext-link" href="{url}" target="_blank" rel="noopener">DOL SuperLMS</a> '
                f"({group} · {set_name}) for personal IELTS study.</p>"
                f'<p class="vi">Từ vựng lấy từ DOL SuperLMS — chỉ phục vụ học tập cá nhân.</p>'
            ),
        },
    ]

    doc = {
        "schema": 2,
        "format": "dol-vocab",
        "id": f"dol-gpt-{qkey}",
        "type": "vocab",
        "source": "chatgpt",
        "category": "dol-vocab",
        "topicNumber": 0,
        "title": set_name,
        "group": group,
        "book": set_name,
        "bookSlug": course_id,
        "bookNum": lesson_num,
        "testNum": lesson_num,
        "skill": skill,
        "url": url,
        "dateTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M"),
        "wordCount": len(items),
        "words": words,
        "items": items,
        "sections": sections,
        "queueKey": qkey,
        "superlmsFlat": True,
        "courseId": course_id,
        "courseVocabSetId": course_vocab_set_id,
        "vocabSetId": vocab_set_id,
    }
    if enrich:
        enrich_doc_examples(doc, translate=False, rebuild_html=True)
        rebuild_passage_sections(doc)
    return doc


def load_courses() -> list[dict]:
    return json.loads(COURSES_PATH.read_text(encoding="utf-8")).get("courses") or []


def load_state() -> dict:
    path = DOL / "superlms-state.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"schema": 1, "sent": []}


def save_state(state: dict) -> None:
    path = DOL / "superlms-state.json"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
