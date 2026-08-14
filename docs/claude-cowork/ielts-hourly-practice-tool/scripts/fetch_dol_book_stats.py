#!/usr/bin/env python3
"""Fetch DOL book-level stats (lượt làm / testTakers) for every catalog book."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
DOL = ROOT / "data" / "chatgpt" / "dol"
OUT = DOL / "dol-book-stats.json"

sys.path.insert(0, str(SCRIPTS))
from dol_vocab_utils import fetch_html, extract_book_stats  # noqa: E402


def book_key(group: str, name: str) -> str:
    return f"{group}\x1e{name}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch DOL lượt làm stats for catalog books")
    parser.add_argument("--dry-run", action="store_true", help="Print actions only")
    args = parser.parse_args()

    catalog_path = DOL / "catalog.json"
    if not catalog_path.is_file():
        print("Missing catalog.json", file=sys.stderr)
        return 1

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    books_in = catalog.get("books") or []
    if not books_in:
        print("No books in catalog.json", file=sys.stderr)
        return 1

    rows: list[dict] = []
    ok, fail = 0, 0

    for i, book in enumerate(books_in, 1):
        group = book.get("group") or ""
        name = book.get("name") or ""
        url = book.get("url") or ""
        key = book_key(group, name)
        print(f"[{i}/{len(books_in)}] {name}...", flush=True)
        if args.dry_run:
            rows.append({"bookKey": key, "group": group, "name": name, "url": url})
            ok += 1
            continue
        try:
            stats = extract_book_stats(fetch_html(url))
            rows.append(
                {
                    "bookKey": key,
                    "group": group,
                    "name": stats.get("name") or name,
                    "url": url,
                    "testTakers": stats.get("testTakers"),
                    "views": stats.get("views"),
                    "noOfTests": stats.get("noOfTests"),
                    "noOfReadingTests": stats.get("noOfReadingTests"),
                    "noOfListeningTests": stats.get("noOfListeningTests"),
                    "vocabPages": len(book.get("pages") or []),
                    "tests": stats.get("tests") or [],
                }
            )
            tt = stats.get("testTakers")
            print(f"  testTakers: {tt if tt is not None else '?'}", flush=True)
            ok += 1
        except Exception as exc:
            print(f"  FAIL: {exc}", flush=True)
            rows.append(
                {
                    "bookKey": key,
                    "group": group,
                    "name": name,
                    "url": url,
                    "error": str(exc),
                    "vocabPages": len(book.get("pages") or []),
                }
            )
            fail += 1
        time.sleep(0.25)

    payload = {
        "schema": 1,
        "label": "lượt làm",
        "field": "testTakers",
        "source": catalog.get("generatedFrom")
        or "https://tuhoc.dolenglish.vn/luyen-thi-ielts/free-ielts-online-test",
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "books": rows,
    }

    if args.dry_run:
        print(f"Dry-run: would write {len(rows)} book(s) to {OUT}")
        return 0

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nWrote {OUT.name}: {ok} ok, {fail} failed")
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
