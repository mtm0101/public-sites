#!/usr/bin/env python3
"""Fetch one DOL vocab page and write dol-gpt-*.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from dol_vocab_utils import fetch_html, parse_vocab_page  # noqa: E402

OUT = ROOT / "data" / "chatgpt" / "dol"
DEFAULT_URL = (
    "https://tuhoc.dolenglish.vn/luyen-thi-ielts/tu-vung-cam-ielts-20-test-1-reading-vocab"
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("-o", "--output", help="Output path (default: data/chatgpt/dol/<id>.json)")
    args = ap.parse_args()
    html = fetch_html(args.url)
    doc = parse_vocab_page(html, args.url)
    OUT.mkdir(parents=True, exist_ok=True)
    out = Path(args.output) if args.output else OUT / f"{doc['id']}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {out.name}: {doc['wordCount']} words · {len(doc['sections'])-1} passages")


if __name__ == "__main__":
    main()
