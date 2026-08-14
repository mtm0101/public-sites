#!/usr/bin/env python3
"""Local BBC 6 Minute English pipeline — no ChatGPT required.

1. Sync bbc-6min-*.html from Claude outputs into bbc-lessons/
2. Convert HTML → bbc-claude-*.json
3. Promote claude JSON → bbc-gpt-*.json for pending queue episodes
4. Advance chatgpt/bbc state.json + upcoming.json
5. Rebuild manifest.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
COWORK = ROOT.parent
HTML_DIR = COWORK / "bbc-lessons"
CLAUDE_BBC = ROOT / "data" / "claude-cowork" / "bbc"
GPT_BBC = ROOT / "data" / "chatgpt" / "bbc"

sys.path.insert(0, str(SCRIPTS))
from bbc_state_utils import (  # noqa: E402
    apply_advance,
    apply_pending_advance,
    load_bbc_state,
    migrate_monolithic_if_needed,
    queue_head,
    save_bbc_state,
    sent_eps,
    yymmdd_from_ep,
)
from convert_bbc_html import strip_doc_bbc_ipa  # noqa: E402

YYMMDD_IN_NAME = re.compile(r"bbc-(?:claude|gpt)-(\d{6})-")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def run(cmd: list[str], *, dry_run: bool) -> int:
    print("+", " ".join(cmd))
    if dry_run:
        return 0
    return subprocess.run(cmd, cwd=ROOT).returncode


def sync_claude_html(*, dry_run: bool) -> int:
    sessions = Path(os.environ.get("APPDATA", "")) / "Claude" / "local-agent-mode-sessions"
    if not sessions.is_dir():
        print("  skip sync: Claude sessions folder not found")
        return 0
    HTML_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in sessions.rglob("bbc-6min-*.html"):
        if "outputs" not in path.parts:
            continue
        dest = HTML_DIR / path.name
        if dest.is_file():
            continue
        print(f"  sync {path.name}")
        if not dry_run:
            dest.write_bytes(path.read_bytes())
        copied += 1
    print(f"  synced {copied} html file(s)")
    return copied


def yymmdd_from_html_name(name: str) -> str:
    m = re.match(r"bbc-6min-(\d{4})-(\d{2})-(\d{2})-", name, re.I)
    if not m:
        return ""
    y, mo, d = m.groups()
    return f"{y[2:]}{mo}{d}"


def find_html(yymmdd: str) -> Path | None:
    if len(yymmdd) != 6:
        return None
    yy, mo, d = yymmdd[:2], yymmdd[2:4], yymmdd[4:6]
    yyyy = str(1900 + int(yy) if int(yy) >= 90 else 2000 + int(yy))
    matches = sorted(HTML_DIR.glob(f"bbc-6min-{yyyy}-{mo}-{d}-*.html"))
    return matches[0] if matches else None


def find_claude_json(yymmdd: str) -> Path | None:
    matches = sorted(CLAUDE_BBC.glob(f"bbc-claude-{yymmdd}-*.json"))
    return matches[0] if matches else None


def find_gpt_json(yymmdd: str) -> Path | None:
    matches = sorted(GPT_BBC.glob(f"bbc-gpt-{yymmdd}-*.json"))
    return matches[0] if matches else None


def title_from_json(path: Path) -> str:
    try:
        obj = load_json(path)
        return (
            obj.get("title")
            or (obj.get("episode") or {}).get("title")
            or path.stem
        ).strip()
    except (OSError, json.JSONDecodeError, AttributeError):
        return path.stem


def promote_claude_to_gpt(claude_path: Path, *, dry_run: bool) -> Path | None:
    m = YYMMDD_IN_NAME.search(claude_path.name)
    if not m:
        return None
    yymmdd = m.group(1)
    if find_gpt_json(yymmdd):
        return find_gpt_json(yymmdd)
    doc = load_json(claude_path)
    slug = claude_path.stem.removeprefix(f"bbc-claude-{yymmdd}-")
    gpt_name = f"bbc-gpt-{yymmdd}-{slug}.json"
    out = GPT_BBC / gpt_name
    doc = dict(doc)
    doc["id"] = out.stem
    doc["source"] = "chatgpt"
    strip_doc_bbc_ipa(doc)
    print(f"  promote {claude_path.name} -> {gpt_name}")
    if not dry_run:
        GPT_BBC.mkdir(parents=True, exist_ok=True)
        write_json(out, doc)
    return out


def strip_all_bbc_json(*, dry_run: bool) -> int:
    """Ensure published BBC JSON has no baked vocab IPA (idempotent)."""
    n = 0
    for folder in (CLAUDE_BBC, GPT_BBC):
        for path in sorted(folder.glob("bbc-*.json")):
            try:
                doc = load_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            if not strip_doc_bbc_ipa(doc):
                continue
            n += 1
            print(f"  strip-ipa {path.name}")
            if not dry_run:
                write_json(path, doc)
    print(f"  stripped IPA from {n} file(s)")
    return n


def pending_yymmdd(upcoming: dict, sent: set[str]) -> list[str]:
    out: list[str] = []
    for yymmdd in upcoming.get("queue") or []:
        ep = f"ep-{yymmdd}"
        if ep not in sent:
            out.append(yymmdd)
    return out


def process_episode(
    yymmdd: str,
    state: dict,
    upcoming: dict,
    *,
    dry_run: bool,
    promote_all: bool,
) -> str:
    ep = f"ep-{yymmdd}"
    if ep in sent_eps(state):
        return "already-sent"

    gpt = find_gpt_json(yymmdd)
    if not gpt:
        claude = find_claude_json(yymmdd)
        if claude:
            gpt = promote_claude_to_gpt(claude, dry_run=dry_run)
        elif find_html(yymmdd):
            return "needs-convert"
        else:
            return "missing-source"

    if dry_run:
        print(f"  advance {ep} via {gpt.name if gpt else '?'}")
        return "dry-run"

    if gpt and apply_advance(
        state,
        upcoming,
        ep,
        json_file=gpt.name,
        title=title_from_json(gpt),
        note="Published locally from Claude HTML/JSON",
    ):
        return "advanced"

    if promote_all and not gpt:
        return "skipped"
    return "no-change"


def main() -> int:
    parser = argparse.ArgumentParser(description="Local BBC 6min publish-all pipeline")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--skip-convert", action="store_true")
    parser.add_argument("--force-convert", action="store_true")
    parser.add_argument("--no-convert-manifest", action="store_true")
    parser.add_argument(
        "--promote-all",
        action="store_true",
        help="Promote every bbc-claude JSON missing a gbc-gpt twin (not only queue)",
    )
    args = parser.parse_args()

    migrate_monolithic_if_needed()
    if not args.dry_run:
        apply_pending_advance()

    if not args.skip_sync:
        print("\n== Sync Claude HTML ==")
        sync_claude_html(dry_run=args.dry_run)

    if not args.skip_convert:
        print("\n== Convert HTML -> JSON ==")
        cmd = [sys.executable, str(SCRIPTS / "convert_bbc_html.py")]
        if args.force_convert:
            cmd.append("--force")
        if run(cmd, dry_run=args.dry_run) != 0:
            print("WARN: convert_bbc_html.py failed", file=sys.stderr)

    state, upcoming = load_bbc_state()
    sent = sent_eps(state)
    todo = pending_yymmdd(upcoming, sent)

    if args.promote_all:
        seen = set(todo)
        for claude_path in sorted(CLAUDE_BBC.glob("bbc-claude-*.json")):
            m = YYMMDD_IN_NAME.search(claude_path.name)
            if not m:
                continue
            yymmdd = m.group(1)
            if f"ep-{yymmdd}" not in sent and yymmdd not in seen:
                todo.append(yymmdd)
                seen.add(yymmdd)

    print(f"\n== Publish / advance ({len(todo)} pending) ==")
    ok, skip, fail = 0, 0, 0
    changed = False

    for i, yymmdd in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}] ep-{yymmdd}")
        result = process_episode(
            yymmdd,
            state,
            upcoming,
            dry_run=args.dry_run,
            promote_all=args.promote_all,
        )
        if result == "advanced":
            ok += 1
            changed = True
        elif result in {"already-sent", "no-change"}:
            skip += 1
        elif result == "needs-convert":
            print("  FAIL: HTML present but claude JSON missing — re-run without --skip-convert")
            fail += 1
        elif result == "missing-source":
            print("  SKIP: no HTML/JSON for this episode")
            skip += 1
        elif result == "dry-run":
            ok += 1
        else:
            fail += 1

    if changed and not args.dry_run:
        save_bbc_state(state, upcoming)

    print("\n== Orphan scan ==")
    if args.dry_run:
        print("  (skipped in dry-run)")
    else:
        run([sys.executable, str(SCRIPTS / "repair_bbc_state_advance.py"), "--scan"], dry_run=False)

    state, upcoming = load_bbc_state()
    head = queue_head(upcoming)
    print(
        f"\nDone: {ok} advanced, {skip} skipped, {fail} failed | "
        f"sent={len(state.get('sent', []))} queue={len(upcoming.get('queue', []))} "
        f"next={'ep-' + head if head else 'empty'}"
    )

    print("\n== Strip baked IPA ==")
    strip_all_bbc_json(dry_run=args.dry_run)

    if not args.no_convert_manifest and not args.dry_run:
        print("\n== Manifest ==")
        run([sys.executable, str(SCRIPTS / "convert_lessons.py")], dry_run=False)

    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
