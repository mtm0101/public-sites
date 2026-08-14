"""Shared helpers for ChatGPT BBC queue state (split files + compact upcoming)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BBC_DIR = ROOT / "data" / "chatgpt" / "bbc"
STATE_PATH = BBC_DIR / "state.json"
UPCOMING_PATH = BBC_DIR / "upcoming.json"
ADVANCE_PATH = BBC_DIR / "state-advance.json"

EP_RE = re.compile(r"ep-(\d{6})")
YYMMDD_RE = re.compile(r"^\d{6}$")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def yyyy_from_yymmdd(yymmdd: str) -> str:
    yy = int(yymmdd[:2])
    return str(1900 + yy if yy >= 90 else 2000 + yy)


def iso_date_from_yymmdd(yymmdd: str) -> str:
    return f"{yyyy_from_yymmdd(yymmdd)}-{yymmdd[2:4]}-{yymmdd[4:6]}"


def bbc_url_from_yymmdd(yymmdd: str) -> str:
    yyyy = yyyy_from_yymmdd(yymmdd)
    return (
        f"https://www.bbc.co.uk/learningenglish/english/features/"
        f"6-minute-english_{yyyy}/ep-{yymmdd}"
    )


def ep_from_url(url: str) -> str:
    m = EP_RE.search(url or "")
    return f"ep-{m.group(1)}" if m else ""


def yymmdd_from_ep(ep: str) -> str:
    ep = ep if ep.startswith("ep-") else f"ep-{ep}"
    m = EP_RE.search(ep)
    return m.group(1) if m else ""


def normalize_queue_item(item: Any) -> str:
    if isinstance(item, str):
        s = item.strip()
        if YYMMDD_RE.match(s):
            return s
        if s.startswith("ep-"):
            return yymmdd_from_ep(s)
    if isinstance(item, dict):
        url = item.get("url") or ""
        ep = ep_from_url(url)
        if ep:
            return yymmdd_from_ep(ep)
        d = item.get("episodeDate") or ""
        if len(d) >= 10:
            return d[2:4] + d[5:7] + d[8:10]
    return ""


def queue_to_legacy_rows(queue: list[str]) -> list[dict]:
    rows = []
    for yymmdd in queue:
        if not yymmdd:
            continue
        rows.append(
            {
                "url": bbc_url_from_yymmdd(yymmdd),
                "episodeDate": iso_date_from_yymmdd(yymmdd),
                "title": None,
            }
        )
    return rows


def legacy_rows_to_queue(rows: list) -> list[str]:
    out: list[str] = []
    for row in rows or []:
        y = normalize_queue_item(row)
        if y:
            out.append(y)
    return out


def load_upcoming_file() -> dict:
    if UPCOMING_PATH.is_file():
        data = load_json(UPCOMING_PATH)
        queue = data.get("queue")
        if isinstance(queue, list):
            return data
    return {
        "_readme": (
            "Compact BBC queue for ChatGPT scheduled task. Each entry is YYMMDD only. "
            "queue[0] is processed next. Derive URL: "
            "https://www.bbc.co.uk/learningenglish/english/features/6-minute-english_<YYYY>/ep-<YYMMDD> "
            "where YYYY = 2000+YY (or 1900+YY when YY>=90)."
        ),
        "schema": 1,
        "queue": [],
    }


def load_state_file() -> dict:
    if not STATE_PATH.is_file():
        raise FileNotFoundError("state.json not found")
    return load_json(STATE_PATH)


def load_bbc_state() -> tuple[dict, dict]:
    """Return (state, upcoming_doc). Migrates legacy monolithic state in memory."""
    state = load_state_file()
    upcoming_doc = load_upcoming_file()

    legacy = state.pop("upcoming", None)
    if legacy is not None and not upcoming_doc.get("queue"):
        upcoming_doc["queue"] = legacy_rows_to_queue(legacy)

    if state.get("schema") != 2:
        state.setdefault("schema", 2)
        state.setdefault(
            "_readme",
            "Processed BBC episodes for the ChatGPT scheduled task. "
            "Pending queue lives in upcoming.json (YYMMDD strings).",
        )

    return state, upcoming_doc


def save_bbc_state(state: dict, upcoming_doc: dict) -> None:
    state = dict(state)
    state.pop("upcoming", None)
    state["schema"] = 2
    save_json(STATE_PATH, state)
    upcoming_doc = dict(upcoming_doc)
    upcoming_doc.setdefault("schema", 1)
    save_json(UPCOMING_PATH, upcoming_doc)


def migrate_monolithic_if_needed() -> bool:
    """Split legacy state.json upcoming[] into upcoming.json. Returns True if migrated."""
    if not STATE_PATH.is_file():
        return False
    raw = load_json(STATE_PATH)
    legacy = raw.get("upcoming")
    if legacy is None:
        return False
    if UPCOMING_PATH.is_file():
        existing = load_json(UPCOMING_PATH)
        if existing.get("queue"):
            raw.pop("upcoming", None)
            raw["schema"] = 2
            save_json(STATE_PATH, raw)
            return True

    upcoming_doc = load_upcoming_file()
    upcoming_doc["queue"] = legacy_rows_to_queue(legacy)
    raw.pop("upcoming", None)
    raw["schema"] = 2
    raw["_readme"] = (
        "Processed BBC episodes for the ChatGPT scheduled task. "
        "Pending queue lives in upcoming.json (YYMMDD strings)."
    )
    save_bbc_state(raw, upcoming_doc)
    return True


def sent_eps(state: dict) -> set[str]:
    eps: set[str] = set()
    for row in state.get("sent") or []:
        ep = ep_from_url(row.get("url") or "")
        if ep:
            eps.add(ep)
        elif row.get("episodeDate"):
            d = row["episodeDate"]
            if len(d) >= 10:
                eps.add(f"ep-{d[2:4]}{d[5:7]}{d[8:10]}")
    return eps


def queue_head(upcoming_doc: dict) -> str:
    q = upcoming_doc.get("queue") or []
    return q[0] if q else ""


def apply_advance(
    state: dict,
    upcoming_doc: dict,
    ep: str,
    *,
    json_file: str,
    title: str,
    note: str = "State advance — lesson JSON already on main",
    skipped_duplicate: bool = False,
    existing_source: str = "",
    existing_file: str = "",
) -> bool:
    yymmdd = yymmdd_from_ep(ep)
    if not yymmdd:
        return False

    queue: list[str] = list(upcoming_doc.get("queue") or [])
    changed = False

    if ep in sent_eps(state):
        new_q = [x for x in queue if x != yymmdd]
        if new_q != queue:
            upcoming_doc["queue"] = new_q
            changed = True
        return changed

    if yymmdd not in queue:
        return False

    idx = queue.index(yymmdd)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    row = {
        "url": bbc_url_from_yymmdd(yymmdd),
        "title": title,
        "episodeDate": iso_date_from_yymmdd(yymmdd),
        "processedAt": now,
        "jsonFile": json_file,
    }
    if skipped_duplicate:
        row["skippedDuplicate"] = True
        row["existingSource"] = existing_source
        row["existingFile"] = existing_file
    else:
        row["repairedAt"] = now
        row["repairNote"] = note

    state.setdefault("sent", []).append(row)
    upcoming_doc["queue"] = queue[:idx] + queue[idx + 1 :]
    return True


def apply_pending_advance() -> bool:
    if not ADVANCE_PATH.is_file():
        return False
    pending = load_json(ADVANCE_PATH)
    ep = pending.get("ep") or ""
    if not ep.startswith("ep-"):
        ep = f"ep-{ep}" if ep else ""
    if not ep:
        ADVANCE_PATH.unlink(missing_ok=True)
        return False

    state, upcoming_doc = load_bbc_state()
    ok = apply_advance(
        state,
        upcoming_doc,
        ep,
        json_file=pending.get("jsonFile") or "",
        title=pending.get("title") or ep,
        note=pending.get("repairNote") or "Applied state-advance.json",
        skipped_duplicate=bool(pending.get("skippedDuplicate")),
        existing_source=pending.get("existingSource") or "",
        existing_file=pending.get("existingFile") or "",
    )
    if ok:
        save_bbc_state(state, upcoming_doc)
    ADVANCE_PATH.unlink(missing_ok=True)
    return ok
