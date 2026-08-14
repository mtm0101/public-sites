#!/usr/bin/env python3
"""Backfill exampleVi on existing dol-gpt-*.json files (IPA is lazy-loaded in index.html)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from dol_vocab_utils import enrich_doc_examples, rebuild_passage_sections  # noqa: E402

DOL_DIR = ROOT / "data" / "chatgpt" / "dol"


def main() -> None:
    ap = argparse.ArgumentParser(description="Enrich DOL vocab JSON with example VI (IPA is app-side)")
    ap.add_argument("files", nargs="*", help="JSON paths (default: all dol-gpt-*.json in data/chatgpt/dol)")
    ap.add_argument("--no-translate", action="store_true", help="IPA only, skip MyMemory VI")
    ap.add_argument("--rebuild-html", action="store_true", help="Force rebuild sections HTML")
    args = ap.parse_args()

    paths = [Path(p) for p in args.files] if args.files else sorted(DOL_DIR.glob("dol-gpt-*.json"))
    if not paths:
        print("No dol-gpt-*.json files found.")
        return

    for path in paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        n = enrich_doc_examples(doc, translate=not args.no_translate, rebuild_html=False)
        if args.rebuild_html or n:
            rebuild_passage_sections(doc)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        with_ex = sum(1 for it in doc.get("items") or [] if (it.get("example") or "").strip())
        with_vi = sum(1 for it in doc.get("items") or [] if (it.get("exampleVi") or "").strip())
        with_ipa = sum(1 for it in doc.get("items") or [] if it.get("exampleIpa"))
        print(
            f"{path.name}: updated {n} items · examples {with_ex} · VI {with_vi}/{with_ex} · IPA {with_ipa}/{with_ex}",
            flush=True,
        )


if __name__ == "__main__":
    main()
