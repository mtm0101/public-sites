# Listening Test

## Purpose

The `#/listening-test` section exposes interactive IELTS Listening tests sourced from the DOL Listening catalog. Every test must use its **Làm bài** page as the canonical source, never the vocabulary or answer-explanation page.

## Data

- Manifest: `data/chatgpt/dol/listening/manifest.json`
- Test payload: `data/chatgpt/dol/listening/<test-id>/questions.json`
- Audio metadata: `data/chatgpt/dol/listening/<test-id>/meta.json`
- Importer: `scripts/fetch_dol_listening_assets.py --download-questions`

Each manifest row includes `questionsPath`, `questionCount`, and `testUrl`. The `testUrl` must resolve to the matching DOL **Làm bài** page.

Question examples, correct answers, transcript excerpts, timestamps, and explanations must come from DOL's related **Đề và đáp án** source payload. Do not generate or hard-code substitute examples. When the practice payload is incomplete, the importer follows the page's related `VIEW_SOLUTION` URL and uses that authoritative question model.

## App contract

- Listing route: `#/listening-test`
- Test route: `#/listening-test/<test-id>`
- Listing actions use the Vietnamese label `Làm bài`.
- Test UI follows the source layout: header and timer, white question paper, four-section navigator, question status dots, and sticky section audio.
- User answers, current section, timer, and result persist locally in IndexedDB.
- The listing offers History, Full test, and Part 1–4 actions. Part mode is capped at ten minutes and stores progress separately from Full test mode.
- Full-test audio advances continuously to the next part; playback speed uses the same speed choices and saved preference as the Listening section.
- Submission shows correct/incorrect state, correct answer, DOL explanation, and timestamped source transcript beneath each question.
- Attempt history stores mode, timestamp, answers, score, and estimated band locally.
- Question instructions and study text continue to use the shared English/Vietnamese translation system.
- Vietnamese text is paired directly beneath its corresponding English instruction, example, question, or option.
- The renderer supports completion fields, single and multiple choice, matching, tables, flow charts, and diagram/map labelling represented in the source data.

## Source

- Catalog: `https://tuhoc.dolenglish.vn/luyen-thi-ielts/free-ielts-online-test`
- Reference test: `https://tuhoc.dolenglish.vn/luyen-thi-ielts/ielts-online-test-luyen-tap-mock-test-ielts-14-test-1-listening`
