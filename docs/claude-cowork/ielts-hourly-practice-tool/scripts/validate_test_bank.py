"""Validate the generic test bank without changing published data."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "chatgpt" / "tests"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    manifest = load(BASE / "manifest.json")
    taxonomy = load(BASE / manifest["taxonomyPath"])
    categories = {row["id"] for row in taxonomy["categories"]}
    questions: dict[str, dict] = {}
    fingerprints: set[str] = set()
    for pack_meta in manifest["packs"]:
        pack = load(BASE / pack_meta["path"])
        assert pack["questionCount"] == len(pack["questions"])
        for q in pack["questions"]:
            assert q["id"] not in questions, f"duplicate ID: {q['id']}"
            assert q["fingerprint"] not in fingerprints, f"duplicate content: {q['id']}"
            assert q["primaryCategoryId"] in categories
            assert q["cefr"] in {"B1", "B2", "C1", "C2"}
            assert 1 <= q["difficulty"] <= 5
            assert len(q["options"]) == 4
            assert {o["id"] for o in q["options"]} == {"A", "B", "C", "D"}
            assert sum(bool(o["correct"]) for o in q["options"]) == 1
            assert q["correctOptionId"] == next(o["id"] for o in q["options"] if o["correct"])
            assert q["prompt"]["en"] and q["prompt"]["vi"]
            assert q["explanation"]["rule"]["en"] and q["explanation"]["rule"]["vi"]
            assert all(o["text"]["en"] and o["text"]["vi"] and o["explanation"]["en"] and o["explanation"]["vi"] for o in q["options"])
            questions[q["id"]] = q
            fingerprints.add(q["fingerprint"])
    for test_meta in manifest["tests"]:
        definition = load(BASE / test_meta["path"])
        assert definition["questionCount"] == len(definition["questionIds"])
        assert len(definition["questionIds"]) == len(set(definition["questionIds"]))
        assert all(qid in questions for qid in definition["questionIds"])
    distribution = Counter(q["correctOptionId"] for q in questions.values())
    assert len(questions) == manifest["packs"][0]["questionCount"]
    print(f"OK: {len(questions)} questions · {len(categories)} categories · answers {dict(sorted(distribution.items()))}")


if __name__ == "__main__":
    main()
