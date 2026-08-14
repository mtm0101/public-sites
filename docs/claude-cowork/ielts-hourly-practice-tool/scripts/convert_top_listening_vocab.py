"""Merge ranked IELTS Listening CSVs into stable topic-grouped lessons."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


TOOL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = TOOL_ROOT / "data" / "chatgpt" / "vocabulary"
MERGED_CSV_NAME = "ielts-listening-vocabulary-merged.csv"

TOPICS = {
    1: "Environment, Climate Change & Wildlife",
    2: "Health & Lifestyle",
    3: "Crime, Law & Public Policy",
    4: "Housing, Architecture & Urban Planning",
    5: "Education",
    6: "Travel & Tourism",
    7: "Traffic, Transport & Infrastructure",
    8: "Media, Advertising & Social Media",
    9: "Work & Careers",
    10: "Technology & AI",
    11: "Government & Society",
    12: "Culture, History, Traditions & Language",
    13: "Economy, Business & Money",
    14: "Science, Research, Space & Archaeology",
    15: "Family, Relationships & Social Issues",
    16: "Sports, Hobbies, Arts & Entertainment",
    17: "Globalization, Migration & Future Society",
}
TOPICS_VI = {
    1: "Môi trường, Biến đổi khí hậu & Động vật hoang dã",
    2: "Sức khỏe & Lối sống",
    3: "Tội phạm, Pháp luật & Chính sách công",
    4: "Nhà ở, Kiến trúc & Quy hoạch đô thị",
    5: "Giáo dục",
    6: "Du lịch & Lữ hành",
    7: "Giao thông, Vận tải & Cơ sở hạ tầng",
    8: "Truyền thông, Quảng cáo & Mạng xã hội",
    9: "Việc làm & Sự nghiệp",
    10: "Công nghệ & Trí tuệ nhân tạo",
    11: "Chính phủ & Xã hội",
    12: "Văn hóa, Lịch sử, Truyền thống & Ngôn ngữ",
    13: "Kinh tế, Kinh doanh & Tiền tệ",
    14: "Khoa học, Nghiên cứu, Không gian & Khảo cổ học",
    15: "Gia đình, Các mối quan hệ & Vấn đề xã hội",
    16: "Thể thao, Sở thích, Nghệ thuật & Giải trí",
    17: "Toàn cầu hóa, Di cư & Xã hội tương lai",
}

TOPIC_SEEDS = {
    1: "environment climate wildlife animal forest pollution emission carbon conservation ecology ecological species habitat ocean river reservoir soil waste disposal sustainable energy weather agricultural agriculture grain pine",
    2: "health healthy medical medicine disease infection respiratory coronary dental nutrition vitamin dose injection immune immunity tumor glucose metabolism physiology exercise lifestyle diet sleep patient treatment",
    3: "crime criminal law legal court jury testimony custody abuse execution justice police prison punishment legislation clause denial discrimination equality equity exclusion",
    4: "housing house home architecture urban planning building construction apartment property lease accommodation interior room flooring gravel width",
    5: "education school university college student teacher lecturer faculty scholarship curriculum learning assessment questionnaire classroom academic competence eligibility certified catalog",
    6: "travel tourism tourist hotel holiday destination booking reservation visitor journey airport landing hospitality courtesy",
    7: "traffic transport transportation infrastructure road railway train bus vehicle transit highway interstate route bridge tunnel parking adaptive",
    8: "media advertising advertisement social television radio broadcasting newspaper journalism audience campaign internet platform content",
    9: "work career job employment employer employee personnel workplace occupation occupational salary profession operator headquarters staff",
    10: "technology artificial intelligence ai digital computer computation binary software hardware circuit cable laser node data automation online device",
    11: "government society political politics federal commission parliament cabinet regime public policy authority authorize deputy treaty administration legislative",
    12: "culture history tradition traditional language linguistic morphology religion philosophy philosophical heritage ancient convention revolution art literature",
    13: "economy economic business money finance financial commerce corporation capitalist fiscal dividend manufacturing manufacture acquisition market trade incorporated incorporation",
    14: "science scientific research space archaeology experiment laboratory theory variable parameter acid particle axis fluid beam alloy aluminum amplitude conduction cone friction mercury oxidation phosphate paradigm mathematical",
    15: "family relationship marriage divorce parent child children youth elderly community social friendship discrimination equality",
    16: "sport sports hobby hobbies art arts entertainment game music film theatre exhibit collector performance exercise dominance",
    17: "global globalization migration migrant international future alliance territory geographic population border overseas integration integrated",
}
TOPIC_SEEDS = {number: set(words.split()) for number, words in TOPIC_SEEDS.items()}


def pos_label(value: str) -> str:
    labels = {"n": "noun", "n pl.": "plural noun", "adj": "adjective", "adv": "adverb"}
    return labels.get(value.strip().lower(), value.strip().lower())


def text_tokens(value: str) -> list[str]:
    clean = html.unescape(re.sub(r"<[^>]+>", " ", str(value))).casefold()
    return re.findall(r"[a-z]+(?:'[a-z]+)?", clean)


def example_is_public_safe(value: str) -> bool:
    """Reject obvious personal-name examples inherited from third-party cards."""
    common_names = {
        "anthony", "anna", "david", "emily", "george", "jack", "james", "jane", "jennifer",
        "john", "johnson", "kate", "lisa", "mark", "mary", "michael", "paul", "peter",
        "robert", "sam", "sarah", "smith", "thuy", "tien", "tom", "william",
    }
    if any(token in common_names for token in text_tokens(value)):
        return False
    words = re.findall(r"[^\W\d_]+", value, flags=re.UNICODE)
    title_run = 0
    for word in words:
        if len(word) > 1 and word[0].isupper() and word[1:].islower():
            title_run += 1
            if title_run >= 2:
                return False
        else:
            title_run = 0
    return True


def load_app_context(target_words: set[str]) -> tuple[dict[int, Counter], dict[str, dict[str, str]]]:
    """Use the app's own IELTS lessons for topics and DOL cards for examples."""
    manifest = json.loads((TOOL_ROOT / "manifest.json").read_text(encoding="utf-8"))["lessons"]
    topic_terms: dict[int, Counter] = defaultdict(Counter)
    examples: dict[str, dict[str, str]] = {}

    for entry in manifest:
        if entry.get("category") == "ielts-listening-top-1000":
            continue
        path = TOOL_ROOT / entry["file"]
        try:
            item = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue

        topic_number = item.get("topicNumber", 0)
        if topic_number in TOPICS:
            content = [item.get("title", "")]
            # Published lesson vocabulary is a stronger signal than incidental prose.
            content.extend(word for word in item.get("words", []) for _ in range(4))
            content.extend(section.get("html", "") for section in item.get("sections", []))
            topic_terms[topic_number].update(text_tokens(" ".join(map(str, content))))

        if item.get("format") == "dol-vocab":
            for vocab in item.get("items", []):
                word = str(vocab.get("text", "")).strip().casefold()
                example = str(vocab.get("example", "")).strip()
                if word in target_words and example and example_is_public_safe(example) and word not in examples:
                    examples[word] = {
                        "example": example,
                        "context": " ".join(filter(None, [
                            str(vocab.get("passageLabel", "")),
                            str(vocab.get("passageName", "")),
                            example,
                        ])),
                    }

    return topic_terms, examples


def fallback_example(row: dict[str, str]) -> str:
    word = row["word"].strip()
    pos = pos_label(row["part_of_speech"])
    if pos in {"noun", "plural noun"}:
        return f"The lecturer explained why {word} was important to the topic."
    if pos == "adjective":
        return f"The speaker described the situation as {word}."
    # A metalinguistic sentence stays grammatical for verbs and adverbs whose
    # argument structure cannot be inferred from the source CSV.
    return f"The lecturer used the term “{word}” while explaining the procedure."


def assign_topic(
    row: dict[str, str],
    topic_terms: dict[int, Counter],
    example_info: dict[str, str],
    group_sizes: Counter,
) -> int:
    word = row["word"].strip().casefold()
    context = " ".join([
        word,
        row["vietnamese_meaning"],
        example_info.get("context", ""),
    ])
    context_tokens = set(text_tokens(context))
    scores = {}
    for number in TOPICS:
        score = topic_terms[number][word] * 6
        if word in TOPIC_SEEDS[number]:
            score += 120
        score += len(context_tokens & TOPIC_SEEDS[number]) * 4
        scores[number] = score
    best_score = max(scores.values())
    if best_score:
        return min(number for number, score in scores.items() if score == best_score)
    # Truly cross-topic linking words have no semantic home. Spread only these
    # few neutral terms across the smallest groups to avoid a misleading bucket.
    return min(TOPICS, key=lambda number: (group_sizes[number], number))


def card_html(row: dict[str, str], example: str, collection_size: int) -> str:
    word = html.escape(row["word"].strip())
    level = html.escape(row["cefr_level_estimate"].strip())
    pos = html.escape(pos_label(row["part_of_speech"]))
    meaning = html.escape(row["vietnamese_meaning"].strip())
    # Source examples occasionally include a presentation label. The card
    # layout already makes their purpose clear, so keep only the sentence.
    example = re.sub(r"^\s*(?:e\.g\.|ex(?:ample)?)\s*:\s*", "", example, flags=re.IGNORECASE)
    example = html.escape(example)
    example_vi = html.escape(row.get("example_vietnamese", "").strip())
    rank = int(row["rank"])
    basis = html.escape(row["ranking_basis"].replace("+", ", "))
    return (
        f'<div class="vocab" data-rank="{rank}" data-cefr="{level}" data-context-gloss="0" data-word="{word}">'
        f'<div class="head">{word}</div>'
        f'<p class="vn" data-fallback-vi="{meaning}">{meaning}</p>'
        f'<p class="en ex">{example}</p>'
        + (f'<p class="vn ex-translation">{example_vi}</p>' if example_vi else '') +
        f'<p class="note no-sound vocab-meta"><strong>Profile:</strong> {level} · {pos} · rank {rank} of {collection_size:,}. '
        f'<span class="vocab-ranking">· Ranking signals: {basis}.</span></p>'
        '</div>'
    )


def read_ranked_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    expected = {
        "rank", "word", "cefr_level_estimate", "part_of_speech",
        "vietnamese_meaning", "ranking_basis", "source_urls",
    }
    if not rows or not expected.issubset(rows[0]):
        raise ValueError(f"CSV is missing required columns: {sorted(expected - set(rows[0] if rows else []))}")
    rows.sort(key=lambda row: int(row["rank"]))
    ranks = [int(row["rank"]) for row in rows]
    words = [row["word"].strip().casefold() for row in rows]
    if ranks != list(range(1, len(rows) + 1)):
        raise ValueError(f"Ranks in {csv_path.name} must be contiguous from 1 through {len(rows):,}")
    if len(set(words)) != len(rows):
        raise ValueError("Words must be unique after case-insensitive normalization")
    return rows


def merge_ranked_rows(
    base_rows: list[dict[str, str]],
    incoming_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Keep every base word and append only incoming words not already present."""
    incoming = {row["word"].strip().casefold(): row for row in incoming_rows}
    base_words = {row["word"].strip().casefold() for row in base_rows}
    merged: list[dict[str, str]] = []

    for base in base_rows:
        key = base["word"].strip().casefold()
        if key not in incoming:
            merged.append(dict(base))
            continue
        updated = dict(base)
        updated.update(incoming[key])
        updated["rank"] = base["rank"]
        urls = list(dict.fromkeys(
            url.strip()
            for row in (base, incoming[key])
            for url in row.get("source_urls", "").split("|")
            if url.strip()
        ))
        updated["source_urls"] = "|".join(urls)
        merged.append(updated)

    next_rank = len(merged) + 1
    for row in incoming_rows:
        key = row["word"].strip().casefold()
        if key in base_words:
            continue
        appended = dict(row)
        appended["rank"] = str(next_rank)
        merged.append(appended)
        next_rank += 1
    return merged


def write_ranked_rows(csv_path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "rank", "word", "cefr_level_estimate", "part_of_speech",
        "vietnamese_meaning", "example", "example_vietnamese", "ranking_basis", "source_urls",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def convert(csv_path: Path, output_dir: Path, base_csv_path: Path | None = None) -> list[Path]:
    incoming_rows = read_ranked_rows(csv_path)
    rows = merge_ranked_rows(read_ranked_rows(base_csv_path), incoming_rows) if base_csv_path else incoming_rows
    collection_size = len(rows)
    words = [row["word"].strip().casefold() for row in rows]

    topic_terms, examples = load_app_context(set(words))
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    group_sizes: Counter = Counter()
    for row in rows:
        word = row["word"].strip().casefold()
        info = examples.get(word, {})
        row["example"] = row.get("example", "").strip() or info.get("example") or fallback_example(row)
        topic_number = assign_topic(row, topic_terms, info, group_sizes)
        grouped[topic_number].append(row)
        group_sizes[topic_number] += 1

    output_dir.mkdir(parents=True, exist_ok=True)
    write_ranked_rows(output_dir / MERGED_CSV_NAME, rows)
    generated: list[Path] = []
    base_time = datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc)
    generated_at = datetime.now(timezone.utc).isoformat()

    for topic_number, topic_name in TOPICS.items():
        batch = grouped[topic_number]
        stem = f"vocab-gpt-ielts-listening-top-1000-topic-{topic_number:02d}"
        title = f"IELTS Listening Vocabulary ({collection_size:,} words) — Topic {topic_number:02d}: {topic_name}"
        level_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in batch:
            level_groups[row["cefr_level_estimate"].strip().upper() or "Unspecified"].append(row)
        level_order = {level: index for index, level in enumerate(("A1", "A2", "B1", "B2", "C1", "C2", "Unspecified"))}
        sections = []
        for level in sorted(level_groups, key=lambda value: (level_order.get(value, 99), value)):
            level_rows = level_groups[level]
            word_label = "word" if len(level_rows) == 1 else "words"
            sections.append({
                "id": f"vocabulary-{level.lower()}",
                "title": f"{level} Vocabulary — {len(level_rows)} {word_label}",
                "level": 1,
                "html": "\n".join(card_html(row, row["example"], collection_size) for row in level_rows),
            })
        source_urls = sorted({url.strip() for row in batch for url in row["source_urls"].split("|") if url.strip()})
        item = {
            "schema": 2,
            "id": stem,
            "type": "vocabulary",
            "source": "chatgpt",
            "category": "ielts-listening-top-1000",
            "title": title,
            "titleVi": f"Bộ {collection_size:,} từ vựng IELTS Listening — Chủ đề {topic_number:02d}: {TOPICS_VI[topic_number]}",
            # Topic 1 is newest so the default Others ordering follows the Lessons list.
            "dateTime": (base_time + timedelta(minutes=18 - topic_number)).isoformat(),
            "contentUpdatedAt": generated_at,
            "topicGroupNumber": topic_number,
            "topicGroup": topic_name,
            "collectionWordCount": collection_size,
            "wordCount": len(batch),
            "words": [row["word"].strip() for row in batch],
            "sections": sections,
            "sources": source_urls,
            "notes": "Merged without removing any previously published words, then grouped by the app's 17 IELTS lesson topics. Existing ranks remain stable; new words follow them in updated-CSV rank order.",
            # Keep this collection under Others rather than mixing it into hourly Lessons.
            "topicNumber": 0,
        }
        path = output_dir / f"{stem}.json"
        if path.exists():
            try:
                previous = json.loads(path.read_text(encoding="utf-8-sig"))
                previous_stamp = previous.pop("contentUpdatedAt", "")
                current_without_stamp = dict(item)
                current_without_stamp.pop("contentUpdatedAt", None)
                if previous == current_without_stamp and previous_stamp:
                    item["contentUpdatedAt"] = previous_stamp
            except (OSError, json.JSONDecodeError):
                pass
        path.write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        generated.append(path)

    generated_set = {path.resolve() for path in generated}
    for stale in output_dir.glob("vocab-gpt-ielts-listening-top-1000-*.json"):
        if stale.resolve() not in generated_set:
            stale.unlink()

    return generated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--base-csv", type=Path, help="Existing ranked CSV whose words and ranks must be preserved")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output.resolve()
    canonical_base = output_dir / MERGED_CSV_NAME
    base_csv = args.base_csv.resolve() if args.base_csv else (canonical_base if canonical_base.exists() else None)
    files = convert(
        args.csv.resolve(),
        output_dir,
        base_csv,
    )
    total = sum(len(json.loads(path.read_text(encoding="utf-8"))["words"]) for path in files)
    print(f"Generated {len(files)} topic lessons with {total} vocabulary entries in {args.output.resolve()}")


if __name__ == "__main__":
    main()
