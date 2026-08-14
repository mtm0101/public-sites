# Reading Test

## Purpose

The `#/reading-test` section exposes interactive IELTS Reading tests sourced from the same DOL catalog used by the existing Reading section. It preserves the separate passage-reading experience while adding timed testing and review.

## Data

- Manifest: `data/chatgpt/dol/reading-test/manifest.json`
- Test payload: `data/chatgpt/dol/reading-test/<test-id>/questions.json`
- Importer: `scripts/fetch_dol_reading.py --download-tests`

Each payload contains the real DOL passages, question groups, correct answers, and detailed source explanations. Do not generate or hard-code substitute questions, answers, examples, or explanations.

## App contract

- Listing route: `#/reading-test`
- Test route: `#/reading-test/<test-id>/<full|part-N>`
- The listing offers History before Full test, followed by Part 1–3 actions where available.
- Full tests use the source duration (normally 60 minutes). Part practice is capped at 20 minutes.
- Passage and questions appear side by side on larger screens and stack on mobile.
- English passage paragraphs, instructions, questions, and options receive their Vietnamese study line directly beneath the matching English line.
- Submission marks each response correct or incorrect and shows the correct answer plus DOL's detailed explanation beneath the question.
- Answers, timer, section, result, and separate full/part progress persist in IndexedDB.
- Attempt history stores the timestamp, mode, answers, score, and estimated band. Every row links to a read-only full result with the same per-question feedback available immediately after submission.
- Supported source shapes include completion, true/false/not given, yes/no/not given, single and multiple choice, matching features/headings/sentence endings, and matching paragraph information.

## Source

- Catalog: `https://tuhoc.dolenglish.vn/luyen-thi-ielts/free-ielts-online-test`
- Every payload records its DOL question/solution URL in `testUrl`, `answerKeyUrl`, and `sourceUrl` where available.
