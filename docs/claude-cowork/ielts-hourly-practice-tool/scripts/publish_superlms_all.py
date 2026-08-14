#!/usr/bin/env python3
"""Fetch and publish DOL SuperLMS course vocab into dol-gpt-superlms-*.json."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
DOL = ROOT / "data" / "chatgpt" / "dol"

sys.path.insert(0, str(SCRIPTS))
from superlms_vocab_utils import (  # noqa: E402
    build_doc,
    fetch_vocab_rows,
    find_registration_key,
    list_course_vocab_sets,
    load_courses,
    load_jwt,
    load_state,
    queue_key,
    save_state,
)


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def sent_keys(state: dict) -> set[str]:
    return {row.get("queueKey") or "" for row in state.get("sent") or []}


def advance_state(state: dict, qkey: str, doc: dict, json_file: str) -> None:
    if any(row.get("queueKey") == qkey for row in state.get("sent") or []):
        return
    state.setdefault("sent", []).append(
        {
            "queueKey": qkey,
            "courseId": doc.get("courseId") or "",
            "courseVocabSetId": doc.get("courseVocabSetId") or "",
            "title": doc.get("title") or qkey,
            "group": doc.get("group") or "",
            "book": doc.get("book") or "",
            "skill": doc.get("skill") or "",
            "processedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "jsonFile": json_file,
            "wordCount": doc.get("wordCount") or 0,
        }
    )


def publish_set(
    course: dict,
    set_row: dict,
    jwt: str,
    *,
    dry_run: bool,
    force: bool,
) -> bool:
    set_name = (set_row.get("name") or "").strip()
    qkey = queue_key(course["courseId"], set_name)
    out = DOL / f"dol-gpt-{qkey}.json"
    if out.is_file() and not force:
        print(f"  skip {qkey} (exists)")
        return True
    if dry_run:
        print(f"  fetch {qkey} (dry-run)")
        return True
    vocab_set_id = set_row.get("vocabSetId") or ""
    if not vocab_set_id:
        print(f"  FAIL {qkey}: missing vocabSetId")
        return False
    try:
        vocabs = fetch_vocab_rows(vocab_set_id, jwt)
        doc = build_doc(course=course, set_row=set_row, vocabs=vocabs, enrich=True)
        write_json(out, doc)
        state = load_state()
        advance_state(state, qkey, doc, out.name)
        save_state(state)
        print(f"  published {out.name}: {doc['wordCount']} words")
        return True
    except Exception as exc:
        print(f"  FAIL {qkey}: {exc}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish DOL SuperLMS vocab sets")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force-fetch", action="store_true", help="Re-fetch even if JSON exists")
    ap.add_argument("--no-convert", action="store_true")
    ap.add_argument("--jwt", help="DOL JWT (else DOL_JWT env or scripts/.dol-jwt)")
    ap.add_argument("--course", help="Only this courseId (e.g. 403ca28a16)")
    args = ap.parse_args()

    try:
        jwt = load_jwt(args.jwt)
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    courses = load_courses()
    if args.course:
        courses = [c for c in courses if c.get("courseId") == args.course]
    if not courses:
        print("No courses configured", file=sys.stderr)
        return 1

    ok = fail = skip = 0
    for course in courses:
        cid = course["courseId"]
        print(f"\n== {course.get('group')} ({cid}) ==")
        reg = find_registration_key(cid, jwt)
        if not reg:
            print(f"  FAIL: no studentRegistrationKey for {cid}")
            fail += 1
            continue
        print(f"  registrationKey: {reg}")
        try:
            sets = list_course_vocab_sets(cid, reg, jwt)
        except Exception as exc:
            print(f"  FAIL list: {exc}")
            fail += 1
            continue
        print(f"  vocab sets: {len(sets)}")
        for i, row in enumerate(sets, 1):
            name = row.get("name") or "?"
            print(f"[{i}/{len(sets)}] {name}")
            if publish_set(course, row, jwt, dry_run=args.dry_run, force=args.force_fetch):
                ok += 1
            else:
                fail += 1

    print(f"\nDone: {ok} ok, {skip} skipped, {fail} failed")
    if not args.no_convert and not args.dry_run and fail == 0:
        subprocess.run([sys.executable, str(SCRIPTS / "convert_lessons.py")], cwd=ROOT, check=False)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
