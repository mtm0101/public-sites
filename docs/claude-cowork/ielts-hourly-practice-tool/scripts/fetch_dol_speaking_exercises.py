#!/usr/bin/env python3
"""Clone a DOL SuperLMS Speaking exercise course into speaking-source JSON."""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_COURSE_ID = "403ca28a18"
DEFAULT_L1 = "DOL IELTS 7.0 Speaking Exercise"
SHEET_API = "https://api.dolenglish.vn/course-app-sheet/api"
OFFLINE_API = "https://api.dolenglish.vn/offline-course-management/api"
EXERCISE_API = "https://api.dolenglish.vn/exercise-v2/api"


def api_json(url: str, jwt: str) -> dict | list:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {jwt}",
            "Accept": "application/json",
            "Origin": "https://superlms.dolenglish.vn",
            "Referer": "https://superlms.dolenglish.vn/",
            "User-Agent": "ielts-practice-tool/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:300]}") from exc


def jwt_contact_id(jwt: str) -> str:
    payload = jwt.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    data = json.loads(base64.urlsafe_b64decode(payload))
    return str(data.get("hsContactId") or data.get("uid") or "")


def registration_key(course_id: str, jwt: str) -> str:
    rows = api_json(
        f"{SHEET_API}/course-appsheet/subclass/{course_id}/registrations", jwt
    )
    contact_id = jwt_contact_id(jwt)
    if isinstance(rows, list):
        for row in rows:
            if str(row.get("contactId") or "") == contact_id:
                return str(row.get("key") or "")
        for row in rows:
            if course_id in (row.get("subClassKeys") or []):
                return str(row.get("key") or "")
    raise RuntimeError(f"No student registration found for course {course_id}")


def list_exercises(course_id: str, reg_key: str, jwt: str) -> list[dict]:
    query = urllib.parse.urlencode(
        {"studentRegistrationKey": reg_key, "page": 0, "size": 100}
    )
    data = api_json(
        f"{OFFLINE_API}/learning-management/courses/{course_id}/exercises?{query}",
        jwt,
    )
    rows = data.get("content") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError("Exercise catalog did not return content[]")
    total = int(data.get("totalElements") or len(rows))
    if len(rows) != total:
        raise RuntimeError(f"Only received {len(rows)} of {total} exercise pages")
    return rows


def rich_text(value: object) -> str:
    """Flatten Slate-style JSON while preserving every authored text node."""
    if value is None:
        return ""
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return ""
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return re.sub(r"\s+", " ", raw).strip()
    texts: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("text"), str):
                texts.append(node["text"])
            for key, child in node.items():
                if key != "text":
                    walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(value)
    return re.sub(r"\s+", " ", "".join(texts)).strip()


def answer_from_words(words: object) -> str:
    if not isinstance(words, list):
        return ""
    values: list[str] = []
    for word in words:
        if isinstance(word, dict) and isinstance(word.get("value"), str):
            values.append(word["value"])
    text = " ".join(values)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def conversation_questions(page: dict, start_no: int) -> list[dict]:
    """Expand one CONVERSATION page into its authored DOL → USER turn pairs."""
    content = page.get("content") or {}
    turns = content.get("sentenceMeanings") or []
    questions: list[dict] = []
    pending_prompts: list[str] = []
    opening_prompt = rich_text(content.get("question")) or "Opening conversation turn"
    for turn in turns:
        if not isinstance(turn, dict):
            continue
        text = answer_from_words(turn.get("words"))
        if not text:
            continue
        if str(turn.get("speakerType") or "").upper() == "USER":
            if not pending_prompts:
                # Some Part 2 scripts deliberately begin with the learner's
                # opening line. The page instruction is the only authored
                # prompt before it, so retain that instruction as the question.
                pending_prompts.append(opening_prompt)
            question = " ".join(pending_prompts).strip()
            number = start_no + len(questions)
            questions.append(
                {
                    "question_no": number,
                    "question": question,
                    "question_vi": "",
                    "answers": [
                        {
                            "label": "Answer",
                            "english": text,
                            "vietnamese": "",
                            "segments": sentence_segments(text),
                        }
                    ],
                    "sourcePageId": page.get("id") or "",
                    "questionType": "CONVERSATION",
                }
            )
            pending_prompts = []
        else:
            pending_prompts.append(text)
    if pending_prompts:
        # Preserve a scripted interviewer closing line without inventing an
        # extra learner answer or changing DOL's declared question count.
        if not questions:
            raise RuntimeError("Conversation contains prompts but no USER turns")
        closing = " ".join(pending_prompts).strip()
        questions[-1]["answers"].append(
            {
                "label": "Closing turn",
                "english": closing,
                "vietnamese": "",
                "segments": sentence_segments(closing),
            }
        )
    return questions


def sentence_segments(text: str) -> list[dict]:
    # Retain the source text exactly apart from surrounding whitespace, while
    # exposing each sentence separately to the Speaking detail renderer.
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'“‘(])", text.strip())
    return [{"english": part, "vietnamese": ""} for part in parts if part]


def hierarchy(name: str) -> tuple[str, str]:
    match = re.search(r"\bSpeaking\s*-\s*(L\d+)\s*-\s*(.+)$", name, re.I)
    if not match:
        raise RuntimeError(f"Cannot derive L2/L3 from title: {name}")
    return match.group(1).upper(), match.group(2).strip()


def question_record(page: dict, question_no: int) -> dict:
    content = page.get("content") or {}
    question = rich_text(content.get("question"))
    script = content.get("script") or {}
    answer = str(script.get("content") or "").strip()
    if not answer:
        answer = answer_from_words(content.get("words"))
    if not question or not answer:
        raise RuntimeError(
            f"Missing question/answer in {page.get('name') or page.get('id')}"
        )
    record = {
        "question_no": question_no,
        "question": question,
        "question_vi": "",
        "answers": [
            {
                "label": "Answer",
                "english": answer,
                "vietnamese": "",
                "segments": sentence_segments(answer),
            }
        ],
        "sourcePageId": page.get("id") or "",
        "questionType": content.get("questionType") or "",
    }
    explanation = rich_text(content.get("explanation"))
    if explanation:
        record["explanation"] = explanation
    return record


def question_records(page: dict, start_no: int) -> list[dict]:
    content = page.get("content") or {}
    if str(content.get("questionType") or "").upper() == "CONVERSATION":
        return conversation_questions(page, start_no)
    return [question_record(page, start_no)]


def build_document(course_id: str, catalog: list[dict], jwt: str) -> dict:
    items: list[dict] = []
    total_questions = 0
    for item_no, row in enumerate(catalog, 1):
        original_title = str(row.get("name") or "").strip()
        l2, l3 = hierarchy(original_title)
        exercise_id = str(row.get("exerciseId") or "")
        detail = api_json(f"{EXERCISE_API}/exercises/{exercise_id}", jwt)
        if not isinstance(detail, dict):
            raise RuntimeError(f"Exercise {exercise_id} returned an invalid document")
        question_pages = [
            page
            for page in (detail.get("pages") or [])
            if isinstance(page, dict) and page.get("type") == "QUESTION"
        ]
        questions: list[dict] = []
        for page in question_pages:
            questions.extend(question_records(page, len(questions) + 1))
        expected = int(row.get("noOfQuestions") or detail.get("noOfQuestions") or 0)
        if len(questions) != expected:
            raise RuntimeError(
                f"{original_title}: extracted {len(questions)} of {expected} questions"
            )
        total_questions += len(questions)
        items.append(
            {
                "item_no": item_no,
                "topic": l3,
                "title": l3,
                "l1": DEFAULT_L1,
                "l2": l2,
                "l3": l3,
                "sourceTitle": original_title,
                "sourceUrl": (
                    f"https://superlms.dolenglish.vn/app/course-exercise-v2/"
                    f"exercise/{exercise_id}/preview"
                ),
                "courseExerciseId": row.get("courseExerciseId") or row.get("id") or "",
                "exerciseId": exercise_id,
                "questions": questions,
            }
        )
        print(f"[{item_no:02d}/{len(catalog)}] {l2} · {l3}: {len(questions)} questions")
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "schema": "speaking-source@1.0",
        "format": "speaking-source",
        "id": f"dol-speaking-codex-superlms-{course_id}-exercises",
        "type": "speaking",
        "source": "codex",
        "category": "dol-speaking",
        "title": DEFAULT_L1,
        "l1": DEFAULT_L1,
        "dateTime": now[:16],
        "contentUpdatedAt": now,
        "courseId": course_id,
        "sourceUrl": (
            f"https://superlms.dolenglish.vn/my-classes/{course_id}/exercise?previousUrlId="
        ),
        "pageCount": len(items),
        "questionCount": total_questions,
        "items": items,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--course", default=DEFAULT_COURSE_ID)
    parser.add_argument("--jwt", default=os.environ.get("DOL_JWT", ""))
    parser.add_argument("--output")
    args = parser.parse_args()
    jwt = args.jwt.strip()
    if not jwt:
        print("Missing DOL JWT: pass --jwt or set DOL_JWT", file=sys.stderr)
        return 2
    reg_key = registration_key(args.course, jwt)
    catalog = list_exercises(args.course, reg_key, jwt)
    document = build_document(args.course, catalog, jwt)
    output = Path(args.output) if args.output else (
        ROOT
        / "data"
        / "codex"
        / "speaking"
        / f"dol-speaking-codex-superlms-{args.course}-exercises.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {output}: {document['pageCount']} pages · "
        f"{document['questionCount']} questions"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
