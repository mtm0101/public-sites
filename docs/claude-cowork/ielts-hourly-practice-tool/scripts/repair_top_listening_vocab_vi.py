"""Create concise contextual Vietnamese glosses for the imported listening vocabulary."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


TOOL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = TOOL_ROOT / "data" / "chatgpt" / "vocabulary" / "ielts-listening-vocabulary-merged.csv"
TOPIC_GLOB = "vocab-gpt-ielts-listening-top-1000-topic-*.json"


def plain(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def load_cards(folder: Path) -> dict[str, str]:
    cards: dict[str, str] = {}
    pattern = re.compile(
        r'<div class="vocab"[^>]*data-word="([^"]+)"[^>]*>.*?'
        r'<p class="en ex">(.*?)</p>', re.S
    )
    for path in sorted(folder.glob(TOPIC_GLOB)):
        lesson = json.loads(path.read_text(encoding="utf-8-sig"))
        for section in lesson.get("sections", []):
            for word, example in pattern.findall(section.get("html", "")):
                cards[html.unescape(word).casefold()] = plain(example)
    return cards


def google_translate(text: str) -> str:
    params = urllib.parse.urlencode({
        "client": "gtx", "sl": "en", "tl": "vi", "dt": "t", "q": text,
    })
    request = urllib.request.Request(
        "https://translate.googleapis.com/translate_a/single?" + params,
        headers={"User-Agent": "Mozilla/5.0"},
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return "".join(part[0] for part in payload[0] if part and part[0]).strip()
        except Exception as exc:
            last_error = exc
            time.sleep(0.6 * (2**attempt))
    raise RuntimeError(str(last_error or "translation failed"))


def clean_gloss(value: str) -> str:
    value = html.unescape(value).strip(" \t\r\n.,;:!?\"'“”‘’")
    # A POS hint selects the intended dictionary sense, but Google echoes its
    # Vietnamese POS label. Keep the gloss and discard that helper suffix.
    value = re.sub(r"\s*\([^()]{1,40}\)\s*$", "", value).strip()
    value = re.sub(r"^(?:một|các|những)\s+", "", value, flags=re.I)
    parts = [part.strip() for part in re.split(r"\s*[,;]\s*", value) if part.strip()]
    unique: list[str] = []
    for part in parts:
        if part.casefold() not in {item.casefold() for item in unique}:
            unique.append(part)
    value = "; ".join(unique)
    return value if 0 < len(value) <= 100 else ""


def generic_example_vi(word: str, gloss: str, example: str) -> str:
    """Make generated fallback sentences use the same, POS-aware headword sense."""
    normalized = example.strip()
    if normalized.casefold() == f"The lecturer explained why {word} was important to the topic.".casefold():
        return f"Giảng viên giải thích tại sao {gloss} lại quan trọng đối với chủ đề này."
    if normalized.casefold() == f"The speaker described the situation as {word}.".casefold():
        return f"Người nói mô tả tình huống này là {gloss}."
    expected = f"The lecturer used the term “{word}” while explaining the procedure."
    if normalized.casefold() == expected.casefold():
        return f"Giảng viên đã dùng từ “{gloss}” khi giải thích quy trình."
    return ""


def translate_card(
    word: str,
    part_of_speech: str,
    example: str,
    existing_gloss: str = "",
    preserve_example: bool = False,
) -> tuple[str, str, str]:
    # Headwords and sentences are deliberately translated separately. A POS
    # hint selects the dictionary sense without borrowing a mistranslation
    # from a synthetic example sentence.
    example_vi = "" if preserve_example else google_translate(example)
    if existing_gloss:
        return word, clean_gloss(existing_gloss), example_vi
    prompt = f"{word} ({part_of_speech})" if part_of_speech else word
    gloss = clean_gloss(google_translate(prompt))
    return word, gloss, example_vi


def repair(
    csv_path: Path,
    workers: int,
    examples_only: bool = False,
    glosses_only: bool = False,
    templates_only: bool = False,
) -> None:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    cards = load_cards(csv_path.parent)
    jobs = [(
        row["word"].strip(), row.get("part_of_speech", "").strip(),
        cards.get(row["word"].strip().casefold(), row.get("example", "").strip())
    ) for row in rows]
    missing = [word for word, _, example in jobs if not example]
    if missing:
        raise ValueError(f"Missing examples for {len(missing)} words: {', '.join(missing[:8])}")

    results: dict[str, tuple[str, str]] = {}
    if not templates_only:
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            row_by_word = {row["word"].strip().casefold(): row for row in rows}
            futures = {
                pool.submit(
                    translate_card, word, part_of_speech, example,
                    row_by_word[word.casefold()].get("vietnamese_meaning", "") if examples_only else "",
                    glosses_only,
                ): (word, example)
                for word, part_of_speech, example in jobs
            }
            for done, future in enumerate(as_completed(futures), 1):
                word, _ = futures[future]
                try:
                    _, gloss, example_vi = future.result()
                    results[word.casefold()] = (gloss, example_vi)
                except Exception as exc:
                    print(f"WARN {word}: {exc}")
                    results[word.casefold()] = ("", "")
                if done % 100 == 0 or done == len(futures):
                    print(f"Translated {done}/{len(futures)}")

    for row in rows:
        word = row["word"].strip()
        example = cards[word.casefold()]
        gloss, example_vi = results.get(word.casefold(), (
            row.get("vietnamese_meaning", ""), row.get("example_vietnamese", "")
        ))
        row["example"] = example
        if gloss:
            row["vietnamese_meaning"] = gloss
        templated_vi = generic_example_vi(word, row.get("vietnamese_meaning", ""), example)
        if templated_vi or example_vi:
            row["example_vietnamese"] = templated_vi or example_vi

    fields = [
        "rank", "word", "cefr_level_estimate", "part_of_speech", "vietnamese_meaning",
        "example", "example_vietnamese", "ranking_basis", "source_urls",
    ]
    temp = csv_path.with_suffix(".tmp.csv")
    with temp.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(csv_path)
    repaired = sum(bool(row.get("example_vietnamese")) for row in rows)
    concise = sum(len(row.get("vietnamese_meaning", "")) <= 100 for row in rows)
    print(f"Repaired {repaired}/{len(rows)} example translations; {concise}/{len(rows)} concise glosses")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", nargs="?", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--examples-only", action="store_true", help="Preserve repaired glosses and refresh natural example translations")
    parser.add_argument("--glosses-only", action="store_true", help="Refresh POS-aware headword glosses and preserve example translations")
    parser.add_argument("--templates-only", action="store_true", help="Refresh generated fallback sentences without network calls")
    args = parser.parse_args()
    if sum((args.examples_only, args.glosses_only, args.templates_only)) > 1:
        parser.error("choose at most one repair mode")
    repair(args.csv.resolve(), args.workers, args.examples_only, args.glosses_only, args.templates_only)


if __name__ == "__main__":
    main()
