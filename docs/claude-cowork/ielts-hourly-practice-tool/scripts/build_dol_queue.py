#!/usr/bin/env python3
"""Build DOL vocab catalog.json + upcoming.json from DOL landing/book pages."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from dol_vocab_utils import (  # noqa: E402
    BASE,
    discover_vocab_links,
    fetch_html,
    infer_group,
    queue_key_from_url,
)

OUT = ROOT / "data" / "chatgpt" / "dol"
LANDING = f"{BASE}luyen-thi-ielts/free-ielts-online-test"

# Order: Cambridge 20→9, Practice Test Plus 1→3, Actual Test 1→6
BOOK_ORDER = [
    ("IELTS Cambridge", re.compile(r"^CAM IELTS (\d+)$"), lambda n: -int(n)),
    ("IELTS Practice Test Plus", re.compile(r"^Practice Test Plus (\d+)$"), lambda n: int(n)),
    ("IELTS Actual Test", re.compile(r"^Actual Test (\d+)$"), lambda n: int(n)),
]

SKIP_BOOK = re.compile(
    r"official guide|ielts trainer|dol thpt|tot nghiep",
    re.I,
)


def book_sort_key(name: str) -> tuple:
    for group, pat, fn in BOOK_ORDER:
        m = pat.match(name.strip())
        if m:
            return (BOOK_ORDER.index((group, pat, fn)), fn(m.group(1)))
    return (99, name)


def discover_books(landing_html: str) -> list[dict]:
    books = []
    seen = set()

    def add(url: str, name: str) -> None:
        if SKIP_BOOK.search(url) or SKIP_BOOK.search(name):
            return
        if url in seen:
            return
        seen.add(url)
        books.append({"name": name.strip(), "url": url, "group": infer_group(name, url)})

    # Structured cards on landing page
    for m in re.finditer(
        r"(https://tuhoc\.dolenglish\.vn/luyen-thi-ielts/[^\s\"'<>]+)",
        landing_html,
        re.I,
    ):
        url = m.group(1).split("?")[0]
        if SKIP_BOOK.search(url):
            continue
        cm = re.search(r"cambridge-ielts-(\d+)", url, re.I)
        if cm:
            add(url, f"CAM IELTS {cm.group(1)}")
            continue
        pm = re.search(r"practice-test-plus-(\d+)", url, re.I)
        if pm:
            add(url, f"Practice Test Plus {pm.group(1)}")
            continue
        am = re.search(r"recent-actual-test-(\d+)", url, re.I)
        if am:
            add(url, f"Actual Test {am.group(1)}")
            continue

    books.sort(key=lambda b: book_sort_key(b["name"]))
    return books


def sort_vocab_urls(urls: list[str]) -> list[str]:
    def key(u: str) -> tuple:
        reading = 0 if "reading" in u.lower() else 1
        tm = re.search(r"test[- ]?(\d+)", u, re.I)
        test = int(tm.group(1)) if tm else 0
        return (test, reading, u)

    return sorted(urls, key=key)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("Fetching landing page…")
    landing = fetch_html(LANDING)
    books = discover_books(landing)
    print(f"Found {len(books)} books")

    catalog_entries = []
    queue = []
    seen_keys = set()

    for bi, book in enumerate(books):
        print(f"  [{bi+1}/{len(books)}] {book['name']}…")
        try:
            html = fetch_html(book["url"])
        except Exception as e:
            print(f"    skip book: {e}")
            continue
        vocab_urls = discover_vocab_links(html)
        if not vocab_urls:
            # probe first test link from page for nested vocab
            for m in re.finditer(r'href="(/luyen-thi-ielts/[^"]+)"', html):
                sub = BASE.rstrip("/") + m.group(1)
                if sub == book["url"] or "vocab" in sub:
                    continue
                try:
                    sub_html = fetch_html(sub)
                    vocab_urls.extend(discover_vocab_links(sub_html))
                except Exception:
                    pass
            vocab_urls = sorted(set(vocab_urls))
        vocab_urls = sort_vocab_urls(vocab_urls)
        pages = []
        for url in vocab_urls:
            qk = queue_key_from_url(url)
            if not qk or qk in seen_keys:
                continue
            seen_keys.add(qk)
            skill = "listening" if "listening" in url.lower() else "reading"
            tm = re.search(r"test[-_ ]?(\d+)", url, re.I)
            pages.append(
                {
                    "queueKey": qk,
                    "url": url,
                    "skill": skill,
                    "testNum": int(tm.group(1)) if tm else 0,
                    "title": qk,
                }
            )
            queue.append(qk)
        if pages:
            catalog_entries.append(
                {
                    "group": book["group"],
                    "name": book["name"],
                    "url": book["url"],
                    "pages": pages,
                }
            )
        time.sleep(0.3)

    catalog = {
        "schema": 1,
        "generatedFrom": LANDING,
        "books": catalog_entries,
        "totalPages": len(queue),
    }
    (OUT / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")

    # Remove already-sent keys if state exists
    sent_keys = set()
    state_path = OUT / "state.json"
    if state_path.exists():
        try:
            st = json.loads(state_path.read_text(encoding="utf-8"))
            for row in st.get("sent", []):
                if row.get("queueKey"):
                    sent_keys.add(row["queueKey"])
        except Exception:
            pass
    upcoming = [k for k in queue if k not in sent_keys]

    (OUT / "upcoming.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "_readme": "queue[0] processed next. Keys map to dol-gpt-<key>.json",
                "queue": upcoming,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"catalog: {len(catalog_entries)} books · {len(queue)} pages")
    print(f"upcoming: {len(upcoming)} queued")


if __name__ == "__main__":
    main()
