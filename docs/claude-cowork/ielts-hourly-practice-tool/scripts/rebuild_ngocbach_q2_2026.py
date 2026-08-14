from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


TOPIC_RE = re.compile(r"^(3[4-9]|[45]\d|6[0-2])\.\s+(.+)$")
VOCAB_ENTRY_RE = re.compile(
    r"^(?:\d+\.\s+)?(.+?)(?:\s+\[([^\]]+)\])?\s*:\s*(.+)$"
)
EXAMPLE_RE = re.compile(r"^(?:Eg|Example)\s*:\s*(.*)$", re.IGNORECASE)
MEANING_RE = re.compile(r"^Meaning\s*:\s*(.+)$", re.IGNORECASE)
NUMBERED_TERM_RE = re.compile(r"^\d+\.\s+(.+)$")
QUESTION_RE = re.compile(r"^(?:Q\s*:\s*|\d+\.\s+)(.+\?)$", re.IGNORECASE)
SECTION_LABELS = {"You should say:", "Sample Answer", "Vocabulary", "Part 3", "Additional Vocabulary"}
PAGE_NOISE = {
    "Page",
    "IELTS Speaking Sample Answers • Topics 34–62",
}


def clean(value: str) -> str:
    return " ".join((value or "").replace("\u00a0", " ").split())


def normalized_lines(text: str) -> list[str]:
    return [clean(line) for line in text.splitlines() if clean(line)]


def body_topic_blocks(lines: list[str]) -> list[tuple[int, str, list[str]]]:
    starts: list[tuple[int, int, str]] = []
    cursor = 0
    for expected in range(34, 63):
        matches = []
        for index in range(cursor, len(lines)):
            match = TOPIC_RE.match(lines[index])
            if match and int(match.group(1)) == expected:
                matches.append((index, match.group(2)))
        if not matches:
            raise ValueError(f"Topic {expected} was not found in the Word preview")
        # Topic 34 appears once in the contents and once at the start of the body.
        # Starting from its final occurrence avoids treating the contents as data.
        index, title = matches[-1] if expected == 34 else matches[0]
        starts.append((index, expected, title))
        cursor = index + 1

    blocks = []
    for position, (index, number, title) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        content = [line for line in lines[index + 1 : end] if line not in PAGE_NOISE]
        blocks.append((number, title, content))
    return blocks


def section_positions(lines: list[str]) -> list[tuple[int, str]]:
    return [(index, line) for index, line in enumerate(lines) if line in SECTION_LABELS]


def section_ranges(lines: list[str]) -> list[tuple[str, list[str]]]:
    positions = section_positions(lines)
    ranges: list[tuple[str, list[str]]] = []
    for offset, (index, label) in enumerate(positions):
        end = positions[offset + 1][0] if offset + 1 < len(positions) else len(lines)
        ranges.append((label, lines[index + 1 : end]))
    return ranges


def cue_and_sample(lines: list[str]) -> tuple[list[str], list[dict]]:
    ranges = section_ranges(lines)
    cue = next((body for label, body in ranges if label == "You should say:"), [])
    sample = next((body for label, body in ranges if label == "Sample Answer"), [])
    cue_keys = {clean(value).casefold() for value in cue}

    segments: list[dict] = []
    pending_label = ""
    for index, paragraph in enumerate(sample):
        next_paragraph = sample[index + 1] if index + 1 < len(sample) else ""
        is_short_prompt = len(paragraph.split()) <= 14 and len(next_paragraph.split()) >= 20
        if paragraph.casefold() in cue_keys or is_short_prompt:
            pending_label = paragraph
            continue
        english = f"({pending_label}) {paragraph}" if pending_label else paragraph
        pending_label = ""
        segments.append({"english": english, "vietnamese": ""})
    if pending_label:
        segments.append({"english": f"({pending_label})", "vietnamese": ""})
    return cue, segments


def split_definition_and_vi(value: str, additional: bool) -> tuple[str, str]:
    value = clean(value)
    if additional:
        return "", value
    if ":" not in value:
        return value, ""
    definition, meaning_vi = value.rsplit(":", 1)
    return clean(definition), clean(meaning_vi)


def is_vocab_boundary(line: str) -> bool:
    if line in SECTION_LABELS or TOPIC_RE.match(line):
        return True
    if QUESTION_RE.match(line) or line.startswith("Q:"):
        return True
    return False


def parse_vocab_block(lines: list[str], additional: bool) -> list[dict]:
    # Some Word tables are exposed as a sequence of paragraphs, while damaged
    # source rows may contain several numbered entries in one paragraph. Join
    # those rows and use the explicit Meaning/Example labels as delimiters.
    if any(MEANING_RE.match(line) or " Meaning:" in line for line in lines):
        useful = [
            line
            for line in lines
            if not re.match(r"^(?:T[uừ]\s+vựng thuộc chủ đề|Vocabulary$|Meaning$)", line, re.IGNORECASE)
        ]
        joined = " ".join(useful)
        pattern = re.compile(
            r"(?:^|\s)(\d+)\.\s+(.+?)\s+Meaning\s*:\s*(.+?)"
            r"(?:\s+Example\s*:\s*(.+?))?"
            r"(?=\s+\d+\.\s+|$)",
            re.IGNORECASE,
        )
        structured: list[dict] = []
        for match in pattern.finditer(joined):
            raw_term = clean(match.group(2))
            pos_match = re.match(r"^(.+?)\s+\[([^\]\}]+)[\]\}]$", raw_term)
            term = clean(pos_match.group(1) if pos_match else raw_term)
            entry = {
                "term": term,
                "meaning_vi": "",
                "definition_en": clean(match.group(3)),
            }
            if pos_match:
                entry["pos"] = clean(pos_match.group(2))
            if match.group(4):
                entry["example"] = clean(match.group(4))
            structured.append(entry)
        if structured:
            return structured

    items: list[dict] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        match = VOCAB_ENTRY_RE.match(line)
        if not match or EXAMPLE_RE.match(line):
            index += 1
            continue

        term = clean(match.group(1))
        pos = clean(match.group(2) or "")
        definition_en, meaning_vi = split_definition_and_vi(match.group(3), additional)
        entry = {
            "term": term,
            "meaning_vi": meaning_vi or definition_en,
        }
        if pos:
            entry["pos"] = pos
        if definition_en and meaning_vi:
            entry["definition_en"] = definition_en

        index += 1
        if index < len(lines):
            example_match = EXAMPLE_RE.match(lines[index])
            if example_match:
                example = clean(example_match.group(1))
                index += 1
                # Word sometimes places the example on the paragraph after a
                # bare "Example:" label instead of on the same line.
                if not example and index < len(lines):
                    candidate = lines[index]
                    if not is_vocab_boundary(candidate) and not VOCAB_ENTRY_RE.match(candidate):
                        example = candidate
                        index += 1
                if example:
                    entry["example"] = example
                translation_parts: list[str] = []
                while index < len(lines):
                    candidate = lines[index]
                    if is_vocab_boundary(candidate) or VOCAB_ENTRY_RE.match(candidate) or EXAMPLE_RE.match(candidate):
                        break
                    translation_parts.append(candidate)
                    index += 1
                if translation_parts:
                    entry["example_vi"] = clean(" ".join(translation_parts))
        items.append(entry)
    return items


def topic_vocabulary(lines: list[str]) -> list[dict]:
    vocabulary: list[dict] = []
    by_term: dict[str, dict] = {}
    for label, body in section_ranges(lines):
        if label not in {"Vocabulary", "Additional Vocabulary"}:
            continue
        for entry in parse_vocab_block(body, additional=label == "Additional Vocabulary"):
            key = entry["term"].casefold()
            if key in by_term:
                current = by_term[key]
                for field in ("meaning_vi", "definition_en", "example", "example_vi", "pos"):
                    if not current.get(field) and entry.get(field):
                        current[field] = entry[field]
                continue
            by_term[key] = entry
            vocabulary.append(entry)
    return vocabulary


def part3_questions(lines: list[str]) -> list[dict]:
    questions: list[dict] = []
    for label, body in section_ranges(lines):
        if label != "Part 3":
            continue
        current: dict | None = None
        for paragraph in body:
            match = QUESTION_RE.match(paragraph)
            if not match and paragraph.startswith("Q:"):
                match = re.match(r"^Q\s*:\s*(.+)$", paragraph, re.IGNORECASE)
            if match:
                current = {
                    "question_no": len(questions) + 2,
                    "question": clean(match.group(1)),
                    "question_vi": "",
                    "answers": [],
                }
                questions.append(current)
                continue
            if current is None:
                continue
            if not current["answers"]:
                current["answers"].append(
                    {
                        "label": "Part 3 Answer",
                        "english": paragraph,
                        "vietnamese": "",
                        "segments": [{"english": paragraph, "vietnamese": ""}],
                    }
                )
            else:
                answer = current["answers"][0]
                answer["english"] = clean(answer["english"] + " " + paragraph)
                answer["segments"].append({"english": paragraph, "vietnamese": ""})
    return questions


def build_item(number: int, title: str, lines: list[str], item_no: int) -> dict:
    cue, segments = cue_and_sample(lines)
    part2_text = " ".join(segment["english"] for segment in segments)
    part2 = {
        "question_no": 1,
        "question": title,
        "question_vi": "",
        "cue_card": cue,
        "answers": [
            {
                "label": "Part 2 Sample Answer",
                "english": part2_text,
                "vietnamese": "",
                "segments": segments,
            }
        ],
    }
    return {
        "item_no": item_no,
        "source_question_no": number,
        "topic": f"{number}. {title}",
        "title": f"{number}. {title}",
        "questions": [part2, *part3_questions(lines)],
        "vocabulary": topic_vocabulary(lines),
    }


def audit(items: list[dict]) -> None:
    expected = list(range(34, 63))
    actual = [item["source_question_no"] for item in items]
    if actual != expected:
        raise ValueError(f"Expected topics 34–62, got {actual}")
    for item in items:
        number = item["source_question_no"]
        sample = item["questions"][0]["answers"][0]
        if not sample["english"]:
            raise ValueError(f"Topic {number} has no Part 2 sample answer")
        if not item["vocabulary"]:
            raise ValueError(f"Topic {number} has no vocabulary")
        for entry in item["vocabulary"]:
            if len(entry["term"].split()) > 20:
                raise ValueError(f"Topic {number} has a suspicious vocabulary term: {entry['term']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild the Ngoc Bach Q2 2026 All speaking source from the exact Word preview text."
    )
    parser.add_argument("preview_text", type=Path)
    parser.add_argument("output_json", type=Path)
    args = parser.parse_args()

    lines = normalized_lines(args.preview_text.read_text(encoding="utf-8"))
    blocks = body_topic_blocks(lines)
    items = [build_item(number, title, body, index) for index, (number, title, body) in enumerate(blocks, 1)]
    audit(items)

    existing = json.loads(args.output_json.read_text(encoding="utf-8"))
    existing["contentUpdatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    existing["items"] = items
    args.output_json.write_text(json.dumps(existing, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    vocab_count = sum(len(item["vocabulary"]) for item in items)
    question_count = sum(len(item["questions"]) for item in items)
    print(f"Rebuilt {len(items)} topics, {question_count} questions, and {vocab_count} vocabulary items")
    for item in items:
        print(
            f"{item['source_question_no']}: {len(item['questions'])} questions, "
            f"{len(item['vocabulary'])} vocabulary items"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
