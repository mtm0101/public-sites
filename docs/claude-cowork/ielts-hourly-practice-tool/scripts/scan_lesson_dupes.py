#!/usr/bin/env python3
import json
from collections import defaultdict
from pathlib import Path

root = Path(__file__).resolve().parents[1]
skip = {"manifest.json", "state.json", "user-data.json", "0.speaking.json"}
lessons = []
for f in root.rglob("*.json"):
    if f.name in skip or "template" in f.name.lower() or "/ipa/" in str(f).replace("\\", "/"):
        continue
    if "bbc" in str(f).replace("\\", "/") and "ielts" not in f.name:
        continue
    try:
        o = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        continue
    if not (o.get("topicNumber") and o.get("topicNumber") > 0):
        continue
    lessons.append((f, o))

lessons.sort(key=lambda x: x[1].get("dateTime", ""), reverse=True)

print("=== Newest-first list (app order) ===")
for i, (f, o) in enumerate(lessons, 1):
    rel = f.relative_to(root)
    print(f"{i:3} T{o.get('topicNumber'):02d} {o.get('dateTime','')[:16]} {o.get('id','')[:55]}")
    print(f"     {rel}")

print(f"\nTotal: {len(lessons)}")

by_slot = defaultdict(list)
for f, o in lessons:
    key = (o.get("dateTime", "")[:13], o.get("topicNumber"))  # YYYY-MM-DDTHH
    by_slot[key].append((f, o))

print("\n=== Same hour + topic (duplicates) ===")
for key, items in sorted(by_slot.items()):
    if len(items) > 1:
        print(f"\n{key[0]} topic {key[1]}: {len(items)} files")
        for f, o in items:
            print(f"  {f.relative_to(root)}")

by_id_stem = defaultdict(list)
for f, o in lessons:
    by_id_stem[o.get("id", f.stem)].append(f)

print("\n=== Same id ===")
for k, files in by_id_stem.items():
    if len(files) > 1:
        print(k, [str(x.relative_to(root)) for x in files])
