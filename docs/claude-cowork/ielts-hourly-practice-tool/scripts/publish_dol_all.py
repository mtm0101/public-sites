#!/usr/bin/env python3
"""Fetch and publish every pending DOL vocab lesson locally (no ChatGPT, no snapshots)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
DOL = ROOT / "data" / "chatgpt" / "dol"

sys.path.insert(0, str(SCRIPTS))
import dol_vocab_utils  # noqa: E402
from dol_vocab_utils import (  # noqa: E402
    fetch_html,
    parse_vocab_page,
    enrich_doc_examples,
    rebuild_passage_sections,
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )


def catalog_urls() -> dict[str, str]:
    out: dict[str, str] = {}
    for book in load(DOL / "catalog.json").get("books") or []:
        for page in book.get("pages") or []:
            qk = page.get("queueKey")
            url = page.get("url")
            if qk and url:
                out[qk] = url
    return out


def sent_keys(state: dict) -> set[str]:
    return {row.get("queueKey") or "" for row in state.get("sent") or []}


def pending_keys(upcoming: dict, sent: set[str]) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()

    def add(key: str) -> None:
        if not key or key in seen or key in sent:
            return
        seen.add(key)
        keys.append(key)

    for row in upcoming.get("failed") or []:
        add(row.get("queueKey") or "")
    for key in upcoming.get("queue") or []:
        add(key)

    for path in sorted(DOL.glob("dol-gpt-*.json")):
        add(path.stem.removeprefix("dol-gpt-"))
    return keys


def run(cmd: list[str], *, dry_run: bool) -> int:
    print("+", " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd, cwd=ROOT).returncode


def advance_state(qk: str, doc: dict, json_file: str) -> None:
    state_path = DOL / "state.json"
    state = load(state_path) if state_path.is_file() else {"schema": 1, "sent": []}
    if not any(row.get("queueKey") == qk for row in state.get("sent") or []):
        state.setdefault("sent", []).append(
            {
                "queueKey": qk,
                "url": doc.get("url") or "",
                "title": doc.get("title") or qk,
                "group": doc.get("group") or "",
                "book": doc.get("book") or "",
                "skill": doc.get("skill") or "",
                "testNum": doc.get("testNum"),
                "processedAt": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "jsonFile": json_file,
                "wordCount": doc.get("wordCount") or len(doc.get("items") or []),
                "repairNote": "Published locally from DOL fetch",
            }
        )
        write(state_path, state)

    upcoming_path = DOL / "upcoming.json"
    upcoming = load(upcoming_path)
    upcoming["queue"] = [k for k in upcoming.get("queue") or [] if k != qk]
    upcoming["failed"] = [
        row for row in upcoming.get("failed") or [] if row.get("queueKey") != qk
    ]
    write(upcoming_path, upcoming)

    pending = DOL / "dol-pending.json"
    if pending.is_file() and load(pending).get("queueKey") == qk:
        pending.unlink()


def repair_state_from_lesson(qk: str, *, dry_run: bool) -> bool:
    lesson_path = DOL / f"dol-gpt-{qk}.json"
    if not lesson_path.is_file():
        return False
    if dry_run:
        print(f"  state-sync {qk} (dry-run)")
        return True
    advance_state(qk, load(lesson_path), lesson_path.name)
    print(f"  state-sync {qk}")
    return True


def publish_from_dol(
    qk: str,
    url: str,
    *,
    dry_run: bool,
    force: bool,
    translate: bool = True,
) -> bool:
    lesson_path = DOL / f"dol-gpt-{qk}.json"
    if lesson_path.is_file() and not force:
        return repair_state_from_lesson(qk, dry_run=dry_run)

    if dry_run:
        print(f"  fetch+publish {qk} (dry-run)")
        return True

    try:
        print(f"  fetch {qk}...", flush=True)
        html = fetch_html(url)
        doc = parse_vocab_page(html, url, enrich=False)
        doc["source"] = "chatgpt"
        doc["id"] = f"dol-gpt-{qk}"
        doc["queueKey"] = qk
        enrich_doc_examples(doc, translate=translate, rebuild_html=True, progress=True)
        rebuild_passage_sections(doc)
        json_file = f"dol-gpt-{qk}.json"
        write(DOL / json_file, doc)
        advance_state(qk, doc, json_file)
        print(f"  published {json_file}: {doc.get('wordCount', 0)} words")
        return True
    except Exception as exc:
        print(f"  FAIL {qk}: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch and publish all pending DOL vocab lessons locally"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only; do not fetch, publish, or rewrite state",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Only sync state for lesson files already on disk",
    )
    parser.add_argument(
        "--force-fetch",
        action="store_true",
        help="Re-fetch from DOL even when dol-gpt-*.json already exists",
    )
    parser.add_argument(
        "--no-convert",
        action="store_true",
        help="Skip convert_lessons.py at the end",
    )
    parser.add_argument(
        "--no-translate",
        action="store_true",
        help="Skip Vietnamese example translation (fastest; exampleVi left blank)",
    )
    parser.add_argument(
        "--translator",
        choices=["gtx", "mymemory"],
        default="gtx",
        help="Primary translator for examples (default: gtx — faster, fewer rate limits)",
    )
    args = parser.parse_args()

    dol_vocab_utils.PRIMARY_TRANSLATOR = args.translator
    translate = not args.no_translate

    upcoming_path = DOL / "upcoming.json"
    if not upcoming_path.is_file():
        print("Missing upcoming.json", file=sys.stderr)
        return 1

    state_path = DOL / "state.json"
    state = load(state_path) if state_path.is_file() else {"schema": 1, "sent": []}
    upcoming = load(upcoming_path)
    urls = catalog_urls()
    sent = sent_keys(state)
    todo = pending_keys(upcoming, sent)
    if not todo:
        print("Nothing pending - queue empty and all lessons in sent[]")
        if not args.no_convert and not args.dry_run:
            run([sys.executable, str(SCRIPTS / "convert_lessons.py")], dry_run=False)
        return 0

    print(f"Pending: {len(todo)} key(s)")
    ok, skip, fail = 0, 0, 0

    for qk in todo:
        print(f"\n[{ok + skip + fail + 1}/{len(todo)}] {qk}")
        lesson_path = DOL / f"dol-gpt-{qk}.json"
        if lesson_path.is_file() and qk in sent_keys(load(state_path)) and not args.force_fetch:
            print("  already published")
            skip += 1
            continue
        if args.skip_fetch:
            if lesson_path.is_file():
                if repair_state_from_lesson(qk, dry_run=args.dry_run):
                    ok += 1
                else:
                    fail += 1
            else:
                print("  SKIP: no lesson file (--skip-fetch)")
                skip += 1
            continue
        url = urls.get(qk)
        if not url:
            print("  SKIP: no catalog URL")
            skip += 1
            continue
        if publish_from_dol(
            qk, url, dry_run=args.dry_run, force=args.force_fetch, translate=translate
        ):
            ok += 1
        else:
            fail += 1

    print(f"\nDone: {ok} published/synced, {skip} skipped, {fail} failed")
    if not args.no_convert and not args.dry_run:
        run([sys.executable, str(SCRIPTS / "convert_lessons.py")], dry_run=False)
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
