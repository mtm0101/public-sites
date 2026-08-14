#!/usr/bin/env python3
"""Offline video -> audio -> bilingual transcript -> detailed app lesson pipeline."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".webm"}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d .()-]{7,}\d)(?!\d)")
URL_USER_RE = re.compile(r"https?://(?:www\.)?(?:facebook|instagram|linkedin|tiktok)\.com/[^\s<]+", re.I)
VIETNAMESE_RE = re.compile(
    r"[ăâđêôơưĂÂĐÊÔƠƯàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]"
    r"|\b(?:là|và|của|các|mình|mọi|thì|được|không|cho|chúng|bạn|này|một|có|với|những|trong|khi)\b",
    re.I,
)
DLL_DIRECTORY_HANDLES: list[Any] = []
ARGOS_TRANSLATIONS: dict[tuple[str, str], Any] = {}


def log(message: str) -> None:
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def slugify(value: str) -> str:
    import unicodedata

    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value[:90] or "lesson"


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def iso_now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def seconds_label(value: float) -> str:
    value = max(0, int(value))
    hours, rem = divmod(value, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def public_redact(text: str) -> str:
    text = EMAIL_RE.sub("[email removed]", text)
    text = PHONE_RE.sub("[phone removed]", text)
    text = URL_USER_RE.sub("[profile removed]", text)
    return text.strip()


def ffmpeg_executable() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def extract_audio(video: Path, audio: Path, force: bool) -> None:
    if audio.exists() and audio.stat().st_size > 100_000 and not force:
        log(f"Audio exists, skipping: {audio.name}")
        return
    log(f"Extracting audio: {audio.name}")
    audio.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
        "-codec:a", "libmp3lame", "-b:a", "48k", str(audio),
    ]
    subprocess.run(command, check=True)


def load_whisper(model_name: str, requested_device: str):
    if os.name == "nt":
        import site

        for site_root in site.getsitepackages():
            for relative in ("nvidia/cublas/bin", "nvidia/cudnn/bin", "nvidia/cuda_nvrtc/bin"):
                dll_dir = Path(site_root) / relative
                if dll_dir.is_dir():
                    # Keep the handle alive for the life of the process; otherwise
                    # Windows removes the directory from the DLL search path.
                    DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(dll_dir)))
    from faster_whisper import WhisperModel

    choices = [requested_device] if requested_device != "auto" else ["cuda", "cpu"]
    last_error: Exception | None = None
    for device in choices:
        compute_type = "int8_float16" if device == "cuda" else "int8"
        try:
            log(f"Loading Whisper {model_name} on {device} ({compute_type})")
            return WhisperModel(model_name, device=device, compute_type=compute_type), device
        except Exception as exc:  # CUDA wheels frequently lack a matching runtime on Windows.
            last_error = exc
            log(f"Whisper could not use {device}: {exc}")
    raise RuntimeError(f"Could not load Whisper model: {last_error}")


def transcribe(model, audio: Path, transcript_path: Path, video: Path, force: bool) -> dict[str, Any]:
    if transcript_path.exists() and not force:
        log(f"Raw transcript exists, skipping: {transcript_path.name}")
        return json.loads(transcript_path.read_text(encoding="utf-8"))

    log(f"Transcribing: {audio.name}")
    segments_iter, info = model.transcribe(
        str(audio),
        language="vi",
        beam_size=1,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=True,
        initial_prompt=(
            "Đây là bài giảng IELTS Speaking bằng tiếng Việt có xen kẽ ví dụ tiếng Anh. "
            "Giữ nguyên chính xác thuật ngữ, câu hỏi và câu trả lời tiếng Anh."
        ),
    )
    segments: list[dict[str, Any]] = []
    for index, segment in enumerate(segments_iter):
        text = segment.text.strip()
        if not text:
            continue
        segments.append({
            "id": index,
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "timestamp": seconds_label(segment.start),
            "textOriginal": text,
        })
        if len(segments) % 100 == 0:
            log(f"  transcribed {len(segments)} segments")
    result = {
        "schema": 1,
        "sourceVideo": video.name,
        "audioFile": audio.name,
        "detectedLanguage": info.language,
        "languageProbability": round(info.language_probability, 4),
        "durationSeconds": round(info.duration, 3),
        "generatedAt": iso_now(),
        "segments": segments,
    }
    atomic_json(transcript_path, result)
    return result


def ollama_request(model: str, prompt: str, retries: int = 3, num_predict: int = 2048) -> Any:
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.15, "num_ctx": 16384, "num_predict": num_predict},
    }).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=1800) as response:
                outer = json.loads(response.read().decode("utf-8"))
                raw = outer.get("response", "").strip()
                return json.loads(raw)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries:
                raise RuntimeError(f"Local model request failed: {exc}") from exc
            log(f"  local model retry {attempt}/{retries}: {exc}")
            time.sleep(3 * attempt)
    raise AssertionError("unreachable")


def free_translate(text: str, target: str, source: str = "auto", retries: int = 2) -> str:
    """Use the no-key Google Translate endpoint already used by the web app."""
    data = urllib.parse.urlencode({
        "client": "gtx", "sl": source, "tl": target, "dt": "t", "q": text,
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://translate.googleapis.com/translate_a/single",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Mozilla/5.0"},
        method="POST",
    )
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
                return "".join(str(part[0] or "") for part in (payload[0] or [])).strip()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries:
                raise RuntimeError(f"Free translation request failed: {exc}") from exc
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def free_translate_batch(batch: list[dict[str, Any]], target: str, source: str = "auto") -> dict[int, str]:
    marker = lambda value: f"ZXQSEG{int(value):06d}QXZ"
    combined = "\n".join(f"{marker(x['id'])}\n{x['textOriginal']}" for x in batch)
    translated = free_translate(combined, target, source)
    pattern = re.compile(r"ZXQSEG\s*0*(\d+)\s*QXZ", re.I)
    matches = list(pattern.finditer(translated))
    output: dict[int, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(translated)
        output[int(match.group(1))] = translated[match.end():end].strip()
    if len(output) != len(batch):
        # Marker preservation can vary by language; fall back only for missing items.
        for item in batch:
            if int(item["id"]) not in output:
                output[int(item["id"])] = free_translate(str(item["textOriginal"]), target, source)
    return output


def looks_vietnamese(text: str) -> bool:
    return bool(VIETNAMESE_RE.search(text))


def get_argos_translation(source: str, target: str):
    key = (source, target)
    if key in ARGOS_TRANSLATIONS:
        return ARGOS_TRANSLATIONS[key]
    from argostranslate import package, settings, translate

    settings.chunk_type = settings.ChunkType.MINISBD
    installed = translate.get_installed_languages()
    source_language = next((x for x in installed if x.code == source), None)
    target_language = next((x for x in installed if x.code == target), None)
    if source_language is None or target_language is None:
        package.update_package_index()
        candidate = next(
            (x for x in package.get_available_packages() if x.from_code == source and x.to_code == target),
            None,
        )
        if candidate is None:
            raise RuntimeError(f"No Argos package for {source}->{target}")
        package.install_from_path(candidate.download())
        installed = translate.get_installed_languages()
        source_language = next(x for x in installed if x.code == source)
        target_language = next(x for x in installed if x.code == target)
    translation = source_language.get_translation(target_language)
    ARGOS_TRANSLATIONS[key] = translation
    return translation


def argos_translate_batch(batch: list[dict[str, Any]], source: str, target: str) -> dict[int, str]:
    translation = get_argos_translation(source, target)
    marker = lambda value: f"ZXQSEG{int(value):06d}QXZ"
    combined = "\n".join(f"{marker(x['id'])}\n{x['textOriginal']}" for x in batch)
    translated = translation.translate(combined)
    pattern = re.compile(r"ZXQSEG\s*0*(\d+)\s*QXZ", re.I)
    matches = list(pattern.finditer(translated))
    output: dict[int, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(translated)
        output[int(match.group(1))] = translated[match.end():end].strip()
    for item in batch:
        if int(item["id"]) not in output:
            output[int(item["id"])] = translation.translate(str(item["textOriginal"]))
    return output


def ollama_translate_batch(batch: list[dict[str, Any]], model: str) -> tuple[dict[int, str], dict[int, str]]:
    compact = [{"id": x["id"], "text": x["textOriginal"]} for x in batch]
    prompt = f"""
Translate every input item into both natural English and natural Vietnamese without summarizing or combining.
Preserve IELTS terminology and English examples. Return the same integer ids.
Return JSON only: {{"segments":[{{"id":0,"en":"...","vi":"..."}}]}}
INPUT: {json.dumps(compact, ensure_ascii=False)}
""".strip()
    response = ollama_request(model, prompt, num_predict=1600)
    values = {int(x["id"]): x for x in response.get("segments", []) if "id" in x}
    return (
        {key: str(value.get("en", "")) for key, value in values.items()},
        {key: str(value.get("vi", "")) for key, value in values.items()},
    )


def chunked(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i:i + size] for i in range(0, len(items), size)]


def bilingualize(transcript: dict[str, Any], model: str, bilingual_path: Path, force: bool) -> dict[str, Any]:
    output_segments: list[dict[str, Any]] = []
    if bilingual_path.exists() and not force:
        existing = json.loads(bilingual_path.read_text(encoding="utf-8"))
        if existing.get("complete"):
            log(f"Bilingual transcript exists, skipping: {bilingual_path.name}")
            return existing
        output_segments = existing.get("segments", [])
        log(f"Resuming bilingual transcript at {len(output_segments)} segments")

    completed_ids = {int(x["id"]) for x in output_segments if "id" in x}
    remaining = [x for x in transcript["segments"] if int(x["id"]) not in completed_ids]
    batches = chunked(remaining, 28)
    for batch_number, batch in enumerate(batches, 1):
        log(f"  translating transcript batch {batch_number}/{len(batches)}")
        try:
            english = free_translate_batch(batch, "en", "vi")
        except RuntimeError as exc:
            log(f"  free translation throttled; using offline Argos for English: {exc}")
            try:
                english = argos_translate_batch(batch, "vi", "en")
            except Exception as argos_exc:
                log(f"  Argos fallback failed; using local Qwen: {argos_exc}")
                english, _ = ollama_translate_batch(batch, model)
        english_only = [x for x in batch if not looks_vietnamese(str(x["textOriginal"]))]
        vietnamese = {int(x["id"]): str(x["textOriginal"]) for x in batch}
        if english_only:
            try:
                vietnamese.update(free_translate_batch(english_only, "vi", "en"))
            except RuntimeError:
                try:
                    vietnamese.update(argos_translate_batch(english_only, "en", "vi"))
                except Exception:
                    _, local_vi = ollama_translate_batch(english_only, model)
                    vietnamese.update(local_vi)
        for source in batch:
            original = public_redact(str(source["textOriginal"]))
            en = public_redact(str(english.get(int(source["id"])) or original))
            vi = public_redact(str(vietnamese.get(int(source["id"])) or original))
            output_segments.append({**source, "textOriginal": original, "textEnglish": en, "textVietnamese": vi})
        output_segments.sort(key=lambda x: int(x["id"]))
        atomic_json(bilingual_path, {
            **transcript, "generatedAt": iso_now(), "complete": False, "segments": output_segments,
        })

    result = {**transcript, "generatedAt": iso_now(), "complete": True, "segments": output_segments}
    atomic_json(bilingual_path, result)
    return result


def summarize_chapters(
    bilingual: dict[str, Any], model: str, checkpoint_path: Path, monolingual: bool = False
) -> list[dict[str, Any]]:
    chapters: list[dict[str, Any]] = []
    if checkpoint_path.exists():
        chapters = json.loads(checkpoint_path.read_text(encoding="utf-8")).get("chapters", [])
        log(f"Resuming chapter summaries at {len(chapters)} chapters")
    # Keep each prompt comfortably below the 16K local context window. Sending
    # both translations here can crowd out the model's answer on dense lessons;
    # the original text is enough because Qwen understands both EN and VI.
    batches = chunked(bilingual["segments"], 180)
    for batch_number, batch in enumerate(batches[len(chapters):], len(chapters) + 1):
        log(f"  summarizing chapter {batch_number}/{len(batches)}")
        transcript_text = "\n".join(
            f"[{x['timestamp']}] {x['textOriginal']}" for x in batch
        )
        prompt = f"""
Analyze this chronological excerpt from an IELTS Speaking lesson. Do not add facts not present.
Return detailed bilingual JSON. Required fields are titleEn and titleVi strings;
summaryEn and summaryVi arrays with 4-8 paired, information-rich sentences;
techniques as an array of objects with nameEn, nameVi, explanationEn, and explanationVi;
examples as an array of objects with en and vi; and pitfalls as an array of objects with en and vi.
Use actual lesson content in every field. Never return field descriptions, placeholders, or a schema example.
Redact personal identities; use only [teacher], [student], or roles.

EXCERPT:
{transcript_text}
""".strip()
        if monolingual:
            prompt = f"""
Analyze this chronological excerpt from an IELTS Speaking lesson. Do not add facts not present.
Return detailed English JSON. Required fields are titleEn (a specific title);
summaryEn (4-8 information-rich sentences); techniques (objects with nameEn and explanationEn);
examples (objects with en); and pitfalls (objects with en).
Use actual lesson content in every field. Never return placeholders or a schema example.
Redact personal identities; use only [teacher], [student], or roles.

EXCERPT:
{transcript_text}
""".strip()
        chapter = ollama_request(model, prompt, num_predict=1200)
        if not isinstance(chapter.get("summaryEn"), list) or len(chapter.get("summaryEn", [])) < 3:
            log("    incomplete chapter response; retrying with a stricter instruction")
            chapter = ollama_request(
                model,
                prompt + "\nYour first attempt was incomplete. Fill every required field with specific content from the excerpt.",
                num_predict=1200,
            )
        if not isinstance(chapter.get("summaryEn"), list) or len(chapter.get("summaryEn", [])) < 3:
            # Preserve useful chronological detail even if the small model drifts.
            stride = max(1, len(batch) // 6)
            samples = batch[::stride][:6]
            chapter = {
                "titleEn": f"Lesson discussion from {batch[0]['timestamp']}",
                "summaryEn": [x["textEnglish"] for x in samples],
                "techniques": [],
                "examples": [{"en": x["textEnglish"]} for x in samples[:3]],
                "pitfalls": [],
            }
            if not monolingual:
                chapter["titleVi"] = f"Nội dung bài học từ {batch[0]['timestamp']}"
                chapter["summaryVi"] = [x["textVietnamese"] for x in samples]
                chapter["examples"] = [
                    {"en": x["textEnglish"], "vi": x["textVietnamese"]} for x in samples[:3]
                ]
        chapter["start"] = batch[0]["timestamp"]
        chapter["end"] = seconds_label(batch[-1]["end"])
        chapters.append(chapter)
        atomic_json(checkpoint_path, {"generatedAt": iso_now(), "chapters": chapters})
    return chapters


def synthesize_lesson(
    title_hint: str, chapters: list[dict[str, Any]], model: str, monolingual: bool = False
) -> dict[str, Any]:
    # The full chapter checkpoint includes examples and pitfalls that are already
    # rendered separately. Keep only the semantic spine for the final map-reduce
    # pass so a 16K local context can reliably return complete JSON.
    compact_chapters = [{
        "titleEn": chapter.get("titleEn"),
        "titleVi": chapter.get("titleVi"),
        "start": chapter.get("start"),
        "end": chapter.get("end"),
        "summaryEn": chapter.get("summaryEn", []),
        "summaryVi": chapter.get("summaryVi", []),
        "techniques": chapter.get("techniques", []),
    } for chapter in chapters]
    condensed = json.dumps(compact_chapters, ensure_ascii=False)
    prompt = f"""
Create a very detailed, practical bilingual study guide for an IELTS Speaking lesson.
Use only the chapter analyses supplied. Preserve the lesson's methods, reasoning, demonstrations, examples, and cautions.
Return JSON only with this exact top-level shape:
{{
  "titleEn":"...", "titleVi":"...",
  "overviewEn":["6-10 substantial sentences"],
  "overviewVi":["paired Vietnamese translations"],
  "objectives":[{{"en":"...","vi":"..."}}],
  "keyLessons":[{{"titleEn":"...","titleVi":"...","explanationEn":["..."],"explanationVi":["..."],"applicationEn":"...","applicationVi":"..."}}],
  "vocabulary":[{{"term":"...","meaningEn":"...","meaningVi":"...","exampleEn":"...","exampleVi":"..."}}],
  "practicePlan":[{{"step":1,"en":"...","vi":"..."}}],
  "reviewQuestions":[{{"questionEn":"...","questionVi":"...","answerEn":"...","answerVi":"..."}}]
}}
Requirements: 6-12 key lessons, 8-15 vocabulary items, 6-10 practice steps, and 6-10 review questions.
Use complete sentences. Make English and Vietnamese fields faithful pairs. Redact all personal identities.
Filename title hint: {title_hint}

CHAPTER ANALYSES:
{condensed}
""".strip()
    if monolingual:
        prompt = f"""
Create a very detailed, practical English study guide for an IELTS Speaking lesson.
Use only the chapter analyses supplied. Preserve methods, reasoning, demonstrations, examples, and cautions.
Return JSON with these fields: titleEn; overviewEn (6-10 substantial sentences);
objectives (objects with en); keyLessons (objects with titleEn, explanationEn array, applicationEn);
vocabulary (objects with term, meaningEn, exampleEn); practicePlan (objects with step and en);
and reviewQuestions (objects with questionEn and answerEn).
Requirements: 6-12 key lessons, 8-15 vocabulary items, 6-10 practice steps, and 6-10 review questions.
Use complete sentences, actual lesson content, and no placeholders. Redact personal identities.
Filename title hint: {title_hint}

CHAPTER ANALYSES:
{condensed}
""".strip()
    return ollama_request(model, prompt, num_predict=3200)


def normalize_lesson_output(lesson: dict[str, Any], chapters: list[dict[str, Any]]) -> dict[str, Any]:
    """Repair common small-model schema drift without another expensive model call."""
    overview_en = lesson.get("overviewEn") if isinstance(lesson.get("overviewEn"), list) else []
    overview_vi = lesson.get("overviewVi") if isinstance(lesson.get("overviewVi"), list) else []
    for chapter in chapters:
        if len(overview_en) >= 6:
            break
        en_values = chapter.get("summaryEn") if isinstance(chapter.get("summaryEn"), list) else []
        vi_values = chapter.get("summaryVi") if isinstance(chapter.get("summaryVi"), list) else []
        if en_values:
            overview_en.append(str(en_values[0]))
            overview_vi.append(str(vi_values[0] if vi_values else chapter.get("titleVi", "")))
    lesson["overviewEn"], lesson["overviewVi"] = overview_en, overview_vi

    normalized_objectives = []
    for index, value in enumerate(lesson.get("objectives", []) if isinstance(lesson.get("objectives"), list) else []):
        if isinstance(value, dict):
            normalized_objectives.append({"en": str(value.get("en", "")), "vi": str(value.get("vi", ""))})
        else:
            chapter = chapters[index % len(chapters)] if chapters else {}
            vi_values = chapter.get("summaryVi") if isinstance(chapter.get("summaryVi"), list) else []
            normalized_objectives.append({"en": str(value), "vi": str(vi_values[0] if vi_values else "Mục tiêu học tập của bài học này.")})
    if not normalized_objectives:
        for chapter in chapters[:4]:
            en_values = chapter.get("summaryEn", [])
            vi_values = chapter.get("summaryVi", [])
            if en_values:
                normalized_objectives.append({"en": str(en_values[0]), "vi": str(vi_values[0] if vi_values else "")})
    lesson["objectives"] = normalized_objectives

    key_lessons = lesson.get("keyLessons") if isinstance(lesson.get("keyLessons"), list) else []
    used_titles = {str(x.get("titleEn", "")) for x in key_lessons if isinstance(x, dict)}
    for chapter in chapters:
        if len(key_lessons) >= 6:
            break
        title_en = str(chapter.get("titleEn", "Key lesson"))
        if title_en in used_titles:
            continue
        key_lessons.append({
            "titleEn": title_en,
            "titleVi": str(chapter.get("titleVi", "Trọng tâm bài học")),
            "explanationEn": list(chapter.get("summaryEn", []))[:5],
            "explanationVi": list(chapter.get("summaryVi", []))[:5],
            "applicationEn": "Apply this technique in timed IELTS Speaking practice and review the recording for clarity, accuracy, and fluency.",
            "applicationVi": "Áp dụng kỹ thuật này khi luyện IELTS Speaking có bấm giờ và nghe lại bản ghi để kiểm tra độ rõ ràng, chính xác và trôi chảy.",
        })
        used_titles.add(title_en)
    lesson["keyLessons"] = key_lessons
    return lesson


def paired_paragraphs(en_values: list[str], vi_values: list[str]) -> str:
    parts: list[str] = []
    for index in range(max(len(en_values), len(vi_values))):
        en = en_values[index] if index < len(en_values) else ""
        vi = vi_values[index] if index < len(vi_values) else ""
        if en:
            parts.append(f'<p class="en">{html.escape(public_redact(str(en)))}</p>')
        if vi:
            parts.append(f'<p class="vn">{html.escape(public_redact(str(vi)))}</p>')
    return "\n".join(parts)


def pair(en: Any, vi: Any) -> str:
    return paired_paragraphs([str(en or "")], [str(vi or "")])


def build_app_json(
    video: Path,
    audio: Path,
    bilingual: dict[str, Any],
    chapters: list[dict[str, Any]],
    lesson: dict[str, Any],
    output_path: Path,
    item_no: int,
    write_output: bool = True,
    monolingual: bool = False,
) -> tuple[Path, dict[str, Any]]:
    stem_without_date = re.sub(r"\s*-\s*\d{8}_\d{6}$", "", video.stem).strip()
    source_slug = slugify(stem_without_date)
    lesson_id = f"dol-speaking-recording-gpt-{item_no:02d}-{source_slug}"
    sections: list[dict[str, Any]] = []

    sections.append({
        "id": "overview", "title": "Lesson Overview" if monolingual else "Lesson Overview · Tổng quan bài học", "level": 1,
        "html": paired_paragraphs(lesson.get("overviewEn", []), lesson.get("overviewVi", [])),
    })

    objective_html = []
    for objective in lesson.get("objectives", []):
        objective_html.append('<div class="card">' + pair(objective.get("en"), objective.get("vi")) + "</div>")
    sections.append({
        "id": "objectives", "title": "Learning Objectives" if monolingual else "Learning Objectives · Mục tiêu", "level": 2,
        "html": "\n".join(objective_html) or pair("Review the complete lesson.", "Ôn tập toàn bộ bài học."),
    })

    for index, chapter in enumerate(chapters, 1):
        body = [f'<p class="note">{html.escape(chapter.get("start", ""))}–{html.escape(chapter.get("end", ""))}</p>']
        body.append(paired_paragraphs(chapter.get("summaryEn", []), chapter.get("summaryVi", [])))
        for technique in chapter.get("techniques", []):
            body.append('<div class="card"><div class="head">' + html.escape(str(technique.get("nameEn", ""))) + "</div>")
            body.append(pair(technique.get("explanationEn"), technique.get("explanationVi")) + "</div>")
        sections.append({
            "id": f"chapter-{index}",
            "title": str(chapter.get('titleEn', f'Chapter {index}')) if monolingual else f"{chapter.get('titleEn', f'Chapter {index}')} · {chapter.get('titleVi', '')}",
            "level": 1 if index == 1 else 2,
            "html": "\n".join(body),
        })

    key_html: list[str] = []
    for value in lesson.get("keyLessons", []):
        key_html.append('<div class="card"><div class="head">' + html.escape(str(value.get("titleEn", ""))) + "</div>")
        if not monolingual:
            key_html.append(f'<p class="vn">{html.escape(str(value.get("titleVi", "")))}</p>')
        key_html.append(paired_paragraphs(value.get("explanationEn", []), value.get("explanationVi", [])))
        key_html.append(pair(value.get("applicationEn"), value.get("applicationVi")) + "</div>")
    sections.append({"id": "key-lessons", "title": "Key Lessons" if monolingual else "Key Lessons · Trọng tâm", "level": 1, "html": "\n".join(key_html)})

    vocab_html: list[str] = []
    words: list[str] = []
    for value in lesson.get("vocabulary", []):
        term = public_redact(str(value.get("term", "")))
        if term:
            words.append(term)
        vocab_html.append(f'<div class="vocab"><div class="head">{html.escape(term)}</div>')
        vocab_html.append(pair(value.get("meaningEn"), value.get("meaningVi")))
        vocab_html.append(pair(value.get("exampleEn"), value.get("exampleVi")) + "</div>")
    sections.append({"id": "vocabulary", "title": "Vocabulary & Expressions" if monolingual else "Vocabulary & Expressions · Từ vựng", "level": 1, "html": "\n".join(vocab_html)})

    practice_html: list[str] = ["<ol class=\"q\">"]
    for value in lesson.get("practicePlan", []):
        practice_html.append("<li>" + pair(value.get("en"), value.get("vi")) + "</li>")
    practice_html.append("</ol>")
    sections.append({"id": "practice", "title": "Practice Plan" if monolingual else "Practice Plan · Kế hoạch luyện tập", "level": 1, "html": "\n".join(practice_html)})

    review_html: list[str] = ["<ol class=\"q\">"]
    for value in lesson.get("reviewQuestions", []):
        review_html.append("<li>" + pair(value.get("questionEn"), value.get("questionVi")))
        review_html.append('<div class="key"><span class="label">Answer · Đáp án</span>' + pair(value.get("answerEn"), value.get("answerVi")) + "</div></li>")
    review_html.append("</ol>")
    sections.append({"id": "review", "title": "Review Questions" if monolingual else "Review Questions · Câu hỏi ôn tập", "level": 1, "html": "\n".join(review_html)})

    transcript_html: list[str] = []
    for segment in bilingual["segments"]:
        transcript_html.append(f'<p class="note">{html.escape(segment["timestamp"])}</p>')
        transcript_html.append(pair(segment.get("textEnglish"), segment.get("textVietnamese")))
    sections.append({
        "id": "transcript", "title": "Full Transcript" if monolingual else "Full Bilingual Transcript · Bản chép lời song ngữ", "level": 1,
        "html": "\n".join(transcript_html),
    })

    source_note = (
        f"Local source video: {video.name}. Extracted audio: {audio.name}. "
        + ("The transcript was generated locally with open-source speech recognition and may contain errors."
           if monolingual else
           "Transcript and translation were generated locally with open-source models and may contain recognition errors.")
    )
    source_note_vi = "" if monolingual else (
        f"Video nguồn cục bộ: {video.name}. Âm thanh đã trích xuất: {audio.name}. "
        "Bản chép lời và bản dịch được tạo bằng mô hình mã nguồn mở chạy cục bộ và có thể có lỗi nhận dạng."
    )
    sections.append({"id": "source", "title": "Source & Accuracy" if monolingual else "Source & Accuracy · Nguồn và độ chính xác", "level": 2, "html": pair(source_note, source_note_vi)})

    date_match = re.search(r"(20\d{6})_\d{6}$", video.stem)
    date_time = ""
    if date_match:
        try:
            date_time = dt.datetime.strptime(date_match.group(1), "%Y%m%d").strftime("%Y-%m-%dT00:00")
        except ValueError:
            pass
    public = {
        "schema": 2,
        "id": lesson_id,
        "type": "recording",
        "source": "chatgpt",
        "category": "dol-speaking-recordings",
        "title": public_redact(str(lesson.get("titleEn") or stem_without_date)),
        "titleVi": "" if monolingual else public_redact(str(lesson.get("titleVi") or "Bài học IELTS Speaking")),
        "dateTime": date_time,
        "contentUpdatedAt": iso_now(),
        "words": words,
        "recording": {
            "itemNo": item_no,
            "durationSeconds": bilingual.get("durationSeconds"),
            "audioFile": audio.name,
            "transcriptSegments": len(bilingual["segments"]),
        },
        "sections": sections,
    }
    if output_path.stem != lesson_id:
        output_path = output_path.with_name(lesson_id + ".json")
    if write_output:
        atomic_json(output_path, public)
        log(f"Imported app lesson: {output_path.name}")
    return output_path, public


def build_standalone_html(video: Path, audio: Path, app_item: dict[str, Any], output_path: Path) -> None:
    title = html.escape(str(app_item.get("title", "DOL Speaking Recording")))
    title_vi = html.escape(str(app_item.get("titleVi") or ""))
    monolingual = not bool(title_vi)
    duration = seconds_label(float(app_item.get("recording", {}).get("durationSeconds") or 0))
    nav = []
    content = []
    for section in app_item["sections"]:
        sid = html.escape(str(section["id"]), quote=True)
        section_title = html.escape(str(section["title"]))
        nav.append(f'<a href="#{sid}" data-section-link>{section_title}</a>')
        content.append(
            f'<section id="{sid}" data-study-section>'
            f'<h2>{section_title}</h2>{section["html"]}</section>'
        )

    sprint_days = [
        ("1", "Understand", "Read the overview and first half of the transcript. Mark unfamiliar speaking concepts."),
        ("2", "Shadow", "Listen at 0.85× speed and repeat short chunks. Match rhythm, stress, and linking."),
        ("3", "Extract", "Turn the lesson’s key techniques into a one-page checklist in your own words."),
        ("4", "Part 1", "Answer ten Part 1 questions using direct responses plus one controlled extension."),
        ("5", "Part 2", "Prepare three cue cards in one minute each; speak for the full two minutes."),
        ("6", "Part 3", "Build five answers as idea → reason → example → consequence."),
        ("7", "Review", "Redo the review questions and record one full mock without pausing."),
        ("8", "Repair", "Identify repeated grammar, fluency, and pronunciation problems from your recording."),
        ("9", "Vocabulary", "Use ten lesson expressions in new answers; prioritize accuracy over rarity."),
        ("10", "Fluency", "Practice 4/3/2: deliver the same answer in four, three, then two minutes."),
        ("11", "Precision", "Replace vague claims with specific people, places, reasons, and outcomes."),
        ("12", "Pressure", "Complete a timed mock with unfamiliar questions and no restarts."),
        ("13", "Polish", "Review only high-impact corrections; avoid adding untested memorized language."),
        ("14", "Taper", "Do a light warm-up, review your checklist, and protect sleep and confidence."),
    ]
    sprint_html = "".join(
        f'<article><span>Day {day}</span><h3>{html.escape(label)}</h3><p>{html.escape(detail)}</p></article>'
        for day, label, detail in sprint_days
    )
    audio_name = html.escape(audio.name, quote=True)
    generated = html.escape(str(app_item.get("contentUpdatedAt", "")))
    subtitle_html = "" if monolingual else f'<p class="subtitle">{title_vi}</p>'
    search_placeholder = "Search this lesson…" if monolingual else "Search this lesson / Tìm trong bài học…"
    audio_translation = "" if monolingual else '<p class="vn">Âm thanh bài học</p>'
    description = "English DOL Speaking lesson for IELTS Band 7.5 preparation" if monolingual else "Bilingual DOL Speaking lesson for IELTS Band 7.5 preparation"
    footer_note = "Local speech recognition can make mistakes; verify important wording against the audio." if monolingual else "Local speech recognition and translation can make mistakes; verify important wording against the audio."
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{description}">
<title>{title} · DOL Speaking Recordings</title>
<style>
:root{{--ink:#17202a;--muted:#637083;--paper:#f5f3ee;--card:#fff;--line:#dcd8ce;--brand:#173f5f;--accent:#d2673f;--vi:#6b2c74;--good:#146c5a;--shadow:0 16px 50px rgba(28,39,49,.09)}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.72 Georgia,'Times New Roman',serif}}
button,input,audio{{font:inherit}}a{{color:var(--brand)}}.top{{background:linear-gradient(135deg,#102f49,#1d567b 58%,#b85737);color:#fff;padding:54px max(24px,calc((100vw - 1180px)/2)) 48px}}
.eyebrow{{font:700 12px/1.4 system-ui;letter-spacing:.16em;text-transform:uppercase;color:#ffd8ad}}h1{{max-width:950px;margin:.45rem 0 .2rem;font-size:clamp(2rem,5vw,4rem);line-height:1.08;letter-spacing:-.035em}}
.subtitle{{font:italic 1.15rem/1.5 system-ui;color:#f0dff2;margin:0 0 1.4rem}}.meta{{display:flex;gap:12px;flex-wrap:wrap;font:600 13px system-ui}}.meta span{{background:#ffffff18;border:1px solid #ffffff32;padding:7px 11px;border-radius:99px}}
.toolbar{{position:sticky;top:0;z-index:10;display:flex;gap:10px;align-items:center;padding:10px max(18px,calc((100vw - 1180px)/2));background:#fffefbeF;border-bottom:1px solid var(--line);backdrop-filter:blur(10px)}}
.toolbar input{{min-width:0;flex:1;border:1px solid var(--line);border-radius:9px;padding:9px 12px;background:var(--card)}}.toolbar button{{border:1px solid var(--line);background:var(--card);padding:8px 12px;border-radius:9px;cursor:pointer}}
.layout{{display:grid;grid-template-columns:260px minmax(0,820px);gap:42px;max-width:1180px;margin:34px auto;padding:0 24px}}aside{{position:sticky;top:72px;align-self:start;max-height:calc(100vh - 90px);overflow:auto}}
.audio-card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:var(--shadow);margin-bottom:16px}}audio{{width:100%}}nav a{{display:block;padding:7px 10px;border-left:2px solid var(--line);font:600 13px/1.35 system-ui;text-decoration:none;color:var(--muted)}}nav a:hover,nav a.active{{border-color:var(--accent);color:var(--accent);background:#d2673f0b}}
main section{{scroll-margin-top:75px;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:clamp(20px,4vw,38px);margin-bottom:24px;box-shadow:var(--shadow)}}h2{{font-size:clamp(1.45rem,3vw,2rem);line-height:1.25;margin:0 0 1.25rem;color:var(--brand)}}h3,h4,.head{{font-family:system-ui;color:var(--brand)}}
.en{{margin:.65rem 0 .15rem}}.vn,.vi{{margin:.15rem 0 .8rem;color:var(--vi);font:italic .96rem/1.65 system-ui}}.note{{display:inline-block;margin:1rem 0 .2rem;color:var(--muted);font:700 11px system-ui;letter-spacing:.05em}}
.card,.vocab,.key{{border-left:4px solid var(--accent);background:#faf8f3;padding:14px 18px;margin:14px 0;border-radius:0 10px 10px 0}}.vocab{{border-color:var(--good)}}.head{{font-weight:800}}ol.q>li{{margin-bottom:1.3rem;padding-left:.35rem}}
.sprint{{grid-column:1/-1;background:#102f49;color:#fff;border-radius:18px;padding:30px;margin-bottom:10px}}.sprint h2{{color:#fff}}.sprint-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}}.sprint article{{background:#ffffff0d;border:1px solid #ffffff24;border-radius:12px;padding:14px}}.sprint article span{{font:800 11px system-ui;color:#ffbf91;text-transform:uppercase}}.sprint h3{{color:#fff;margin:.25rem 0;font-size:1rem}}.sprint p{{font:14px/1.5 system-ui;color:#dce9f1;margin:0}}
.hidden-by-search{{display:none!important}}footer{{max-width:820px;margin:20px auto 60px;padding:0 24px;color:var(--muted);font:13px system-ui}}
body.dark{{--ink:#e8edf2;--muted:#aab5c2;--paper:#111820;--card:#17212b;--line:#34404b;--brand:#85c4ef;--accent:#ff936c;--vi:#e0a5e8;--good:#65cdb7;--shadow:none}}body.dark .toolbar{{background:#17212bef}}body.dark .card,body.dark .vocab,body.dark .key{{background:#111820}}
@media(max-width:820px){{.layout{{display:block;padding:0 14px}}aside{{position:static;max-height:none;margin-bottom:20px}}nav{{display:none}}.top{{padding:38px 20px}}main section{{border-radius:12px}}}}
@media print{{.toolbar,aside,.sprint{{display:none}}.layout{{display:block;max-width:none;margin:0;padding:0}}main section{{box-shadow:none;break-inside:avoid;border-color:#bbb}}body{{background:#fff;font-size:11pt}}}}
</style>
</head>
<body>
<header class="top"><div class="eyebrow">DOL Speaking Recordings · IELTS Band 7.5 Sprint</div><h1>{title}</h1>{subtitle_html}<div class="meta"><span>Duration {duration}</span><span>{len(app_item['recording'] and app_item['sections'])} study sections</span><span>Generated locally · no API fee</span></div></header>
<div class="toolbar"><input id="search" type="search" placeholder="{search_placeholder}" aria-label="Search lesson"><button id="theme" type="button">◐ Theme</button><button type="button" onclick="print()">Print / PDF</button></div>
<div class="layout">
<aside><div class="audio-card"><strong>Lesson audio</strong>{audio_translation}<audio controls preload="metadata" src="{audio_name}"></audio></div><nav>{''.join(nav)}</nav></aside>
<main>{''.join(content)}</main>
<section class="sprint"><div class="eyebrow">Your final two weeks</div><h2>14-Day Band 7.5 Speaking Sprint</h2><div class="sprint-grid">{sprint_html}</div></section>
</div>
<footer>Source: {html.escape(video.name)} · Generated {generated}. {footer_note}</footer>
<script>
const search=document.querySelector('#search');
search.addEventListener('input',()=>{{const q=search.value.trim().toLocaleLowerCase();document.querySelectorAll('[data-study-section]').forEach(s=>s.classList.toggle('hidden-by-search',q&&!s.innerText.toLocaleLowerCase().includes(q)))}});
document.querySelector('#theme').addEventListener('click',()=>document.body.classList.toggle('dark'));
const links=[...document.querySelectorAll('[data-section-link]')], sections=[...document.querySelectorAll('[data-study-section]')];
new IntersectionObserver(es=>es.forEach(e=>{{if(e.isIntersecting){{links.forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id))}}}}),{{rootMargin:'-15% 0px -75%'}}).observe;
const observer=new IntersectionObserver(es=>es.forEach(e=>{{if(e.isIntersecting)links.forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id))}}),{{rootMargin:'-15% 0px -75%'}});sections.forEach(s=>observer.observe(s));
</script>
</body>
</html>
"""
    output_path.write_text(document, encoding="utf-8")
    log(f"Created standalone lesson: {output_path.name}")


def monolingual_transcript(raw: dict[str, Any]) -> dict[str, Any]:
    """Adapt the raw Whisper checkpoint to the renderer without translation."""
    result = dict(raw)
    result["complete"] = True
    result["segments"] = [
        {
            **segment,
            "textEnglish": segment.get("textOriginal", ""),
            "textVietnamese": "",
        }
        for segment in raw.get("segments", [])
    ]
    return result


def process_video(video: Path, args: argparse.Namespace, whisper_model) -> None:
    item_match = re.match(r"\s*(\d+)\.", video.name)
    item_no = int(item_match.group(1)) if item_match else 0
    # Do not use Path.with_suffix here: recording titles contain several periods
    # (for example "22. S1. Lesson"), and with_suffix would truncate the title.
    artifact_stem = video.parent / video.stem
    audio = Path(str(artifact_stem) + ".audio.mp3")
    raw_path = Path(str(artifact_stem) + ".transcript.raw.json")
    bilingual_path = Path(str(artifact_stem) + ".transcript.en-vi.json")
    summary_path = Path(str(artifact_stem) + ".lesson-summary.json")
    chapter_checkpoint = Path(str(artifact_stem) + ".chapters.partial.json")
    html_path = Path(str(artifact_stem) + ".lesson.html")
    output_dir = Path(args.app_root) / "data" / "chatgpt" / "recordings"
    provisional = output_dir / f"dol-speaking-recording-gpt-{item_no:02d}-{slugify(video.stem)}.json"

    extract_audio(video, audio, args.force)
    raw = transcribe(whisper_model, audio, raw_path, video, args.force)
    html_only = bool(args.html_only_from and item_no >= args.html_only_from)
    if html_only:
        if html_path.exists() and not args.force:
            log(f"English HTML exists, skipping: {html_path.name}")
            return
        transcript = monolingual_transcript(raw)
        chapters = summarize_chapters(
            transcript, args.ollama_model, chapter_checkpoint, monolingual=True
        )
        lesson = synthesize_lesson(video.stem, chapters, args.ollama_model, monolingual=True)
        lesson = normalize_lesson_output(lesson, chapters)
        _, page_item = build_app_json(
            video, audio, transcript, chapters, lesson, provisional, item_no,
            write_output=False, monolingual=True,
        )
        build_standalone_html(video, audio, page_item, html_path)
        chapter_checkpoint.unlink(missing_ok=True)
        return

    bilingual = bilingualize(raw, args.ollama_model, bilingual_path, args.force)

    if summary_path.exists() and not args.force:
        log(f"Detailed summary exists, skipping model synthesis: {summary_path.name}")
        summary_bundle = json.loads(summary_path.read_text(encoding="utf-8"))
        chapters = summary_bundle["chapters"]
        lesson = summary_bundle["lesson"]
    else:
        chapters = summarize_chapters(bilingual, args.ollama_model, chapter_checkpoint)
        lesson = synthesize_lesson(video.stem, chapters, args.ollama_model)
        summary_bundle = {
            "schema": 1,
            "sourceVideo": video.name,
            "generatedAt": iso_now(),
            "chapters": chapters,
            "lesson": lesson,
        }
        atomic_json(summary_path, summary_bundle)
        chapter_checkpoint.unlink(missing_ok=True)

    lesson = normalize_lesson_output(lesson, chapters)
    summary_bundle["lesson"] = lesson
    atomic_json(summary_path, summary_bundle)

    _, app_item = build_app_json(video, audio, bilingual, chapters, lesson, provisional, item_no)
    build_standalone_html(video, audio, app_item, html_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--app-root", required=True)
    parser.add_argument("--whisper-model", default="small")
    parser.add_argument("--ollama-model", default="qwen2.5:3b")
    parser.add_argument("--device", choices=["auto", "cuda", "cpu"], default="auto")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--html-only-from", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source).resolve()
    videos = sorted((p for p in source.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS), key=lambda p: p.name.lower())
    if not videos:
        raise RuntimeError(f"No videos found in {source}")
    model, actual_device = load_whisper(args.whisper_model, args.device)
    log(f"Whisper ready on {actual_device}; {len(videos)} video(s) queued")
    failures: list[tuple[str, str]] = []
    for index, video in enumerate(videos, 1):
        log(f"Recording {index}/{len(videos)}: {video.name}")
        try:
            process_video(video, args, model)
        except Exception as exc:
            failures.append((video.name, str(exc)))
            log(f"FAILED: {video.name}: {exc}")
    if failures:
        log("Failures:")
        for name, error in failures:
            log(f"  {name}: {error}")
        return 1
    log("All recordings processed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
