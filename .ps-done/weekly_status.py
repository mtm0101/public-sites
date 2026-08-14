#!/usr/bin/env python3
"""Weekly status update generator.

Scans a folder for recently modified files, extracts real snippets/TODOs
from a sample of them, drafts a bullet-point status update, and saves it
as a self-contained HTML file. Uses only the Python standard library.

Run manually:
    python weekly_status.py

Or schedule via Windows Task Scheduler:
    Program: python
    Arguments: <repo-root>\\.ps-done\\weekly_status.py
"""

import argparse
import html
import re
from datetime import datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_ROOT = REPO_ROOT.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "claude-cowork" / "weekly-status"

IGNORED_DIR_NAMES = {".git", "node_modules"}
LOOKBACK_DAYS = 7
MAX_SAMPLED_FILES = 10
MAX_COMPLETED_BULLETS = 6
MAX_NEXT_STEP_TODOS = 3
SNIPPET_MAX_CHARS = 140
READ_HEAD_BYTES = 8000

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".pdf", ".zip", ".7z",
    ".rar", ".exe", ".dll", ".so", ".dylib", ".woff", ".woff2", ".ttf",
    ".otf", ".mp3", ".mp4", ".mov", ".avi", ".pyc", ".class", ".bin",
    ".db", ".sqlite", ".pptx", ".docx", ".xlsx",
}

COMMENT_PREFIXES = ("#", "//", "/*", "*", "<!--", "--")


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def is_hidden(path: Path) -> bool:
    return path.name.startswith(".")


def iter_candidate_files(root: Path, cutoff: datetime):
    """Yield (path, mtime) for files under root modified after cutoff,
    skipping .git/, node_modules/, and hidden files/dirs."""
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except (PermissionError, OSError):
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name in IGNORED_DIR_NAMES or is_hidden(entry):
                    continue
                stack.append(entry)
            elif entry.is_file():
                if is_hidden(entry):
                    continue
                try:
                    mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                except OSError:
                    continue
                if mtime >= cutoff:
                    yield entry, mtime


def gather_recent_files(root: Path, days: int, limit: int):
    cutoff = datetime.now() - timedelta(days=days)
    files = list(iter_candidate_files(root, cutoff))
    files.sort(key=lambda pair: pair[1], reverse=True)
    return files[:limit]


# ---------------------------------------------------------------------------
# Content extraction (heuristic, no fabrication)
# ---------------------------------------------------------------------------

def strip_comment_marker(line: str) -> str:
    stripped = line.strip()
    for marker in COMMENT_PREFIXES:
        if stripped.startswith(marker):
            stripped = stripped[len(marker):].strip()
            break
    return stripped.lstrip("#").strip()


def read_text_head(path: Path) -> str | None:
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return None
    try:
        with path.open("rb") as fh:
            raw = fh.read(READ_HEAD_BYTES)
    except OSError:
        return None
    if b"\x00" in raw:
        return None
    return raw.decode("utf-8", errors="ignore")


def extract_snippet(text: str) -> str:
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("#!") or re.match(r"^#.*coding[:=]", stripped):
            continue
        candidate = strip_comment_marker(raw_line)
        if len(candidate) >= 8:
            if len(candidate) > SNIPPET_MAX_CHARS:
                candidate = candidate[:SNIPPET_MAX_CHARS].rstrip() + "..."
            return candidate
    return ""


def extract_todos(text: str, max_lines: int = 200):
    """Find real TODO/FIXME comments only (uppercase, inside an actual
    comment), so identifiers like a `todo` variable or a regex pattern
    string containing the word don't get flagged as false positives."""
    todos = []
    for raw_line in text.splitlines()[:max_lines]:
        stripped = raw_line.strip()
        if not stripped.startswith(COMMENT_PREFIXES):
            continue
        if re.search(r"\b(TODO|FIXME)\b", stripped):
            cleaned = strip_comment_marker(raw_line)
            if cleaned:
                if len(cleaned) > SNIPPET_MAX_CHARS:
                    cleaned = cleaned[:SNIPPET_MAX_CHARS].rstrip() + "..."
                todos.append(cleaned)
    return todos


# ---------------------------------------------------------------------------
# Drafting the status update (markdown text)
# ---------------------------------------------------------------------------

def top_level_project(root: Path, path: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return path.parent.name
    parts = rel.parts
    return parts[0] if parts else path.parent.name


def build_draft(root: Path, sampled, date_range: str) -> str:
    completed_bullets = []
    todo_bullets = []
    projects_touched = []

    for path, mtime in sampled:
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        project = top_level_project(root, path)
        if project not in projects_touched:
            projects_touched.append(project)

        text = read_text_head(path)
        if text is not None:
            snippet = extract_snippet(text)
            for todo in extract_todos(text):
                todo_bullets.append((rel, todo))
        else:
            snippet = "binary/asset file update"

        date_str = mtime.strftime("%b %d")
        if snippet:
            bullet = f"Updated `{rel}` in `{project}` ({date_str}) — {html.escape(snippet)}"
        else:
            bullet = f"Updated `{rel}` in `{project}` ({date_str})"
        completed_bullets.append(bullet)

    completed_bullets = completed_bullets[:MAX_COMPLETED_BULLETS]

    next_steps = []
    seen_todo_text = set()
    for rel, todo in todo_bullets:
        if todo in seen_todo_text:
            continue
        seen_todo_text.add(todo)
        next_steps.append(f"Follow up on TODO in `{rel}`: \"{html.escape(todo)}\"")
        if len(next_steps) >= MAX_NEXT_STEP_TODOS:
            break

    if not next_steps:
        next_steps.append(
            "No explicit TODO/FIXME markers found in this week's sampled files; "
            "review the changes above for follow-up items."
        )

    if projects_touched:
        next_steps.append(
            "Continue work next week in: " + ", ".join(f"`{p}`" for p in projects_touched) + "."
        )

    if not completed_bullets:
        completed_bullets.append(
            f"No files under `{root}` were modified in the last {LOOKBACK_DAYS} days "
            "(excluding .git/, node_modules/, and hidden files)."
        )

    lines = [f"## Weekly Status Update — {date_range}", ""]
    lines.append("**Completed / In Progress:**")
    for bullet in completed_bullets:
        lines.append(f"- {bullet}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**Notes / Next Steps:**")
    for bullet in next_steps:
        lines.append(f"- {bullet}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Minimal markdown -> HTML conversion (subset used by the draft above)
# ---------------------------------------------------------------------------

def inline_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r'<em style="color:#5a3e00">\1</em>', text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def markdown_to_html(md_text: str) -> str:
    html_lines = []
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            html_lines.append("</ul>")
            in_list = False

    for raw_line in md_text.split("\n"):
        line = raw_line.rstrip()

        if line.strip() == "---":
            close_list()
            html_lines.append("<hr>")
            continue

        if line.startswith("## "):
            close_list()
            html_lines.append(f"<h2>{inline_markdown(line[3:].strip())}</h2>")
            continue

        if line.startswith("- "):
            if not in_list:
                html_lines.append("<ul>")
                in_list = True
            html_lines.append(f"<li>{inline_markdown(line[2:].strip())}</li>")
            continue

        close_list()
        if line.strip():
            html_lines.append(f"<p>{inline_markdown(line.strip())}</p>")

    close_list()
    return "\n".join(html_lines)


# ---------------------------------------------------------------------------
# HTML document assembly
# ---------------------------------------------------------------------------

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:ital,wght@0,400;0,600;0,700;1,400&display=swap" rel="stylesheet">
<style>
  body {{
    font-family: 'Be Vietnam Pro', sans-serif;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px 16px;
    line-height: 1.75;
    font-size: 16px;
    background: #f9f9f9;
    color: #222;
  }}
  h2 {{
    font-size: 1.3em;
    margin-top: 1.4em;
    margin-bottom: 0.5em;
  }}
  ul {{
    margin: 0.4em 0 1em 0;
    padding-left: 1.4em;
  }}
  li {{
    margin-bottom: 0.4em;
  }}
  hr {{
    border: none;
    border-top: 1px solid #ddd;
    margin: 1.5em 0;
  }}
  code {{
    background: #eee;
    padding: 1px 5px;
    border-radius: 4px;
    font-size: 0.92em;
  }}
  @media (max-width: 640px) {{
    body {{
      padding: 12px 10px;
    }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def build_html_document(date_range: str, body_html: str) -> str:
    title = f"Weekly Status Update — {date_range}"
    return PAGE_TEMPLATE.format(title=html.escape(title), body=body_html)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate a weekly status update HTML file.")
    parser.add_argument("--root", type=Path, default=DEFAULT_SCAN_ROOT, help="Folder to scan.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    parser.add_argument("--days", type=int, default=LOOKBACK_DAYS, help="Lookback window in days.")
    args = parser.parse_args()

    root = args.root.resolve()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now()
    start_date = today - timedelta(days=args.days)
    date_range = f"{start_date.strftime('%B %d')} – {today.strftime('%B %d, %Y')}"

    sampled = gather_recent_files(root, args.days, MAX_SAMPLED_FILES)

    draft_md = build_draft(root, sampled, date_range)
    body_html = markdown_to_html(draft_md)
    document = build_html_document(date_range, body_html)

    output_path = output_dir / f"status-{today.strftime('%Y-%m-%d')}.html"
    output_path.write_text(document, encoding="utf-8")

    print(f"Scanned: {root}")
    print(f"Files sampled: {len(sampled)}")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
