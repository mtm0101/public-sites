# AI guide — add test-bank questions

Read `specs/12-test-simulator.md`, `data/chatgpt/tests/taxonomy.json`, the latest pack, and `data/templates/test-template.json` before generating anything.

## Non-negotiable rules

1. Never edit, delete, renumber, or reuse a published question ID or version. Create the next pack and new IDs.
2. Search all existing prompts and fingerprints before writing. Do not paraphrase an existing item by only changing a company, object, or answer order.
3. Give each question exactly one precise primary category from the taxonomy. Add secondary categories only when genuinely tested.
4. Supply English and natural Vietnamese for the prompt, every option, the rule, summary, and every correct/wrong explanation. Explanations must say why that option works or fails in this exact sentence.
5. Use four plausible options A–D and one unambiguous correct answer. Balance correct letters across the new pack.
6. Keep workplace contexts original, neutral, and free of real personal/company names, emails, or private data.
7. For TOEIC grammar, use original Part 5-style incomplete sentences. Do not copy ETS questions. Cover the full taxonomy before adding excess items to one category.
8. Assign CEFR and difficulty honestly. Advanced sets should emphasize B2/C1 and difficulty 3–5; do not imply an official per-question TOEIC scaled score.
9. Store no IPA in source JSON. The app generates US/UK IPA and sound controls at runtime.
10. Update the manifest and generated stats, then run `python scripts/validate_test_bank.py` and `python scripts/convert_lessons.py`.

## Recommended expansion cycle

Add 100–200 questions per pack. First fill the least-represented category × difficulty × CEFR cells. Vary grammar mechanism, sentence structure, workplace topic, vocabulary, distractor logic, and answer position. For a 5,000-question bank, keep packs small enough for lazy loading and never make an existing test depend on random selection at review time: every created attempt stores its chosen IDs.
