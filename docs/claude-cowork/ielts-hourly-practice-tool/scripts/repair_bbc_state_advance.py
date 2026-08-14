#!/usr/bin/env python3
"""Advance ChatGPT BBC state when lesson JSON already exists on disk.

Usage:
  python repair_bbc_state_advance.py ep-211209
  python repair_bbc_state_advance.py --scan   # repair all orphans
  python repair_bbc_state_advance.py --migrate  # split state.json / upcoming.json

Never deletes lesson JSON/HTML files — state-only repair.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from bbc_state_utils import (
    ADVANCE_PATH,
    apply_advance,
    apply_pending_advance,
    load_bbc_state,
    migrate_monolithic_if_needed,
    queue_head,
    save_bbc_state,
    sent_eps,
    yymmdd_from_ep,
)

ROOT = Path(__file__).resolve().parents[1]
BBC_DIR = ROOT / "data" / "chatgpt" / "bbc"


def load_json(path: Path) -> dict:
    return __import__("json").loads(path.read_text(encoding="utf-8"))


def gpt_files_by_ep() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in BBC_DIR.glob("bbc-gpt-*.json"):
        if p.name in ("state.json", "upcoming.json", "state-advance.json"):
            continue
        m = re.search(r"bbc-gpt-(\d{6})-", p.name)
        if m:
            out[f"ep-{m.group(1)}"] = p
    return out


def title_from_lesson(path: Path) -> str:
    try:
        obj = load_json(path)
        return (obj.get("title") or obj.get("episode", {}).get("title") or path.stem).strip()
    except Exception:
        return path.stem


def main(argv: list[str]) -> int:
    if argv[1:] == ["--migrate"]:
        if migrate_monolithic_if_needed():
            state, upcoming = load_bbc_state()
            print(
                f"migrated: sent={len(state.get('sent', []))} "
                f"queue={len(upcoming.get('queue', []))} next={queue_head(upcoming)}"
            )
        else:
            print("no migration needed")
        return 0

    migrate_monolithic_if_needed()
    if apply_pending_advance():
        print("applied pending state-advance.json")

    state, upcoming_doc = load_bbc_state()
    files = gpt_files_by_ep()
    eps = argv[1:] if len(argv) > 1 else []

    if eps == ["--scan"]:
        targets = sorted(set(files) - sent_eps(state))
    elif eps:
        targets = [e if e.startswith("ep-") else f"ep-{e}" for e in eps]
    else:
        head = queue_head(upcoming_doc)
        targets = [f"ep-{head}"] if head else []

    changed = False
    for ep in targets:
        path = files.get(ep)
        if not path:
            print(f"skip {ep}: no bbc-gpt JSON on disk")
            continue
        if apply_advance(
            state,
            upcoming_doc,
            ep,
            json_file=path.name,
            title=title_from_lesson(path),
        ):
            print(f"advanced {ep} via {path.name}")
            changed = True
        else:
            print(f"no change for {ep}")

    if changed:
        save_bbc_state(state, upcoming_doc)
        head = queue_head(upcoming_doc)
        print(
            f"sent={len(state['sent'])} queue={len(upcoming_doc.get('queue', []))} "
            f"next={('ep-' + head) if head else 'empty'}"
        )
    if ADVANCE_PATH.is_file():
        print(f"note: {ADVANCE_PATH.name} still present (apply manually or re-run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
