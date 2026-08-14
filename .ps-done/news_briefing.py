#!/usr/bin/env python3
"""Daily bilingual (English + Vietnamese) news briefing generator.

Uses the Claude API with the server-side web search tool to research
today's top stories across four categories (Vietnam, US, Tech/AI, and
Atlanta & Lilburn GA), then writes a single self-contained HTML file.

Requires:
    pip install anthropic
    ANTHROPIC_API_KEY environment variable set

Run manually:
    python news_briefing.py

Or schedule via Windows Task Scheduler:
    Program:   run_briefing.bat
    Start in:  <repo-root>
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import anthropic
except ImportError:
    sys.exit("Missing dependency. Run: pip install anthropic")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = REPO_ROOT / "docs" / "claude-cowork" / "news-briefing"

MODEL = "claude-opus-4-8"
MAX_TOKENS = 16000
MAX_CONTINUATION_ROUNDS = 6

CSS_SPEC = """\
  Font: 'Be Vietnam Pro' (Google Fonts, weights 400/600/700 incl. italic).
  body background: #f9f9f9; max-width: 800px; margin: 0 auto;
  padding: 20px 16px (12px 10px on screens <= 600px); line-height: 1.75.
  All Vietnamese text is inline, styled with color: #5a3e00; font-style: italic
  (use <em> or a class that applies this color+italic).
  h2 section headers: border-left: 4px solid #c0141b; padding-left: 12px;
  color: #c0141b; text-transform: uppercase; letter-spacing: 0.03em;
  margin: 32px 0 16px; font-weight: 700.
  Each story is a card: background: #fff; border-radius: 8px;
  padding: 16px 18px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.07).
  <meta charset="UTF-8"> and a responsive viewport meta tag are required.
"""


def build_prompt(today: datetime) -> str:
    date_human = today.strftime("%A, %B %-d, %Y") if os.name != "nt" else today.strftime("%A, %B %d, %Y").replace(" 0", " ")
    date_iso = today.strftime("%Y-%m-%d")
    date_search = today.strftime("%B %-d, %Y") if os.name != "nt" else today.strftime("%B %d, %Y").replace(" 0", " ")

    return f"""You are an automated bilingual (English + Vietnamese) daily news briefing \
generator. Use the web_search tool to research today's real news, then output a single \
self-contained HTML document. Work autonomously and do not ask clarifying questions.

TODAY'S DATE: {date_human} ({date_iso})

Research today's top news across these four categories, running multiple targeted \
searches per category (do not stop after one search per category — verify with at \
least 2 searches each):

1. Vietnam news — politics, economy, society, international relations.
   Search: "Vietnam news today {date_search}" and "tin tuc Viet Nam hom nay"
2. US news — national politics, economy, major events.
   Search: "US news today top stories {date_search}"
3. Tech/AI news — AI models, big tech, startups, cybersecurity.
   Search: "tech industry AI news today {date_search}"
4. Atlanta & Lilburn, GA — local events, public safety, government, World Cup if relevant.
   Search: "Atlanta Georgia news today {date_search}" and "Lilburn GA news"

For each category, pick 3-4 of the most significant, current stories you find from real \
search results. Do not fabricate stories, sources, or URLs — every headline, source name, \
date, and link must come directly from an actual web search result.

For EACH story, produce:
- A bold English headline
- A bold italic Vietnamese headline (translation of the English headline)
- 2-3 sentence pairs: one English sentence, IMMEDIATELY followed by its Vietnamese \
translation (styled in the italic/brown Vietnamese style described below)
- A line with: source name, the article's date (DD/MM/YYYY), and a link to the original \
article (real URL from the search result, target="_blank")

HTML STYLING (match exactly):
{CSS_SPEC}

DOCUMENT STRUCTURE:
- <!DOCTYPE html>, <html lang="en">, <head> with charset, viewport, title \
"Daily News Briefing – {today.strftime('%B %-d, %Y') if os.name != 'nt' else today.strftime('%B %d, %Y').replace(' 0', ' ')}", \
and the Be Vietnam Pro Google Font link/preconnect tags.
- A <header> with an <h1> containing the English title "Daily News Briefing — \
{date_human}" and a nested Vietnamese translation of that title/date styled per the \
Vietnamese text rule above.
- Four <h2> sections in this exact order, each with a flag/theme emoji prefix and an \
English + Vietnamese label:
  1. "🇻🇳 Vietnam News / Tin Tức Việt Nam"
  2. "🇺🇸 United States News / Tin Tức Hoa Kỳ"
  3. "💻 Tech & AI News / Tin Tức Công Nghệ & Trí Tuệ Nhân Tạo"
  4. "🍑 Atlanta & Lilburn, GA News / Tin Tức Atlanta & Lilburn, Georgia"
- Each story inside its section as a "story" card per the styling spec.
- A <footer> with: a line linking to https://www.weather.gov/ffc/ for the Atlanta \
weather forecast (English + Vietnamese), and a small generated-by line noting the date.

Output ONLY the complete raw HTML document, starting with <!DOCTYPE html> and ending \
with </html>. Do not wrap it in markdown code fences. Do not include any explanation, \
preamble, or commentary before or after the HTML."""


# ---------------------------------------------------------------------------
# Claude API call
# ---------------------------------------------------------------------------

def generate_html(client: "anthropic.Anthropic", user_prompt: str) -> str:
    messages = [{"role": "user", "content": user_prompt}]
    tools = [
        {
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": 30,
        }
    ]

    for round_num in range(1, MAX_CONTINUATION_ROUNDS + 1):
        print(f"Requesting from {MODEL} (round {round_num})...")
        with client.messages.stream(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            tools=tools,
            output_config={"effort": "high"},
            messages=messages,
        ) as stream:
            response = stream.get_final_message()

        if response.stop_reason == "pause_turn":
            # Server-side tool loop hit its internal iteration cap.
            # Re-send the conversation as-is to let Claude continue.
            messages.append({"role": "assistant", "content": response.content})
            continue

        if response.stop_reason == "refusal":
            raise RuntimeError("Request was refused by the model's safety classifiers.")

        text = "".join(block.text for block in response.content if block.type == "text")
        if not text.strip():
            raise RuntimeError(f"Empty response text (stop_reason={response.stop_reason!r}).")
        return text

    raise RuntimeError(
        f"Exceeded {MAX_CONTINUATION_ROUNDS} continuation rounds without finishing."
    )


def clean_html(text: str) -> str:
    """Strip any markdown fencing or stray preamble/postscript around the HTML."""
    text = text.strip()
    match = re.search(r"<!DOCTYPE html>.*</html>", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(0).strip()
    text = re.sub(r"^```(?:html)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ERROR: ANTHROPIC_API_KEY environment variable is not set.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now()
    output_path = OUTPUT_DIR / f"news-{today.strftime('%Y-%m-%d')}.html"

    client = anthropic.Anthropic(api_key=api_key, timeout=1200.0, max_retries=3)

    try:
        raw_text = generate_html(client, build_prompt(today))
    except anthropic.RateLimitError as e:
        sys.exit(f"Rate limited: {e}")
    except anthropic.APIStatusError as e:
        sys.exit(f"API error ({e.status_code}): {e.message}")
    except anthropic.APIConnectionError as e:
        sys.exit(f"Connection error: {e}")

    html_doc = clean_html(raw_text)
    output_path.write_text(html_doc, encoding="utf-8")

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
