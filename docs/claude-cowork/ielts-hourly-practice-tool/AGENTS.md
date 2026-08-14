# AGENTS.md — IELTS Hourly Practice Tool

**Any AI coding agent (Cursor, Claude Code, ChatGPT, Codex) must read this file first.**

## Start here

1. **[README.md](./README.md)** — folder map  
2. **[specs/README.md](./specs/README.md)** — reading order + task catalog  
3. **[specs/INDEX.json](./specs/INDEX.json)** — machine-readable spec index  
4. Pick the task spec for your assignment (see catalog in README)

## Tool root

```
docs/claude-cowork/ielts-hourly-practice-tool/
```

Local: `C:\Users\USERNAME\Downloads\gpt-codex\public-sites\docs\claude-cowork\ielts-hourly-practice-tool\`

## Rules

### Stable system-wide baseline

The common contracts below apply to **every existing page, every new page/view, every importer/converter, and every generated or newly added data file in the Study app**. They are persistent defaults, not requirements limited to the task that introduced them. All future AI agents must preserve and extend them consistently. Do not weaken, bypass, or redesign these contracts unless the user explicitly requests a permanent contract change; ordinary feature work and content generation do not authorize changing them.

- **Specs win** over prompts and over chat memory. If unsure, read the spec — do not ask the user.
- **New session?** Paste the bootstrap block from [specs/README.md § New session bootstrap](./specs/README.md#new-session-bootstrap-copy-into-a-fresh-chat).
- **Publishing content?** Read [specs/00-platform.md](./specs/00-platform.md) + [specs/08-agent-workflows.md](./specs/08-agent-workflows.md).
- **Editing the app?** Only file to change: [index.html](./index.html). Read [specs/07-app-features.md](./specs/07-app-features.md).
- **Never** commit secrets, personal names, or emails in public JSON/HTML.
- **Never** edit `manifest.json` from content agents — owner runs `scripts/convert_lessons.py`.
- **ChatGPT schedulers MAX LIMIT:** behavior → `prompts/chatgpt/<task>.md` only; **never** edit `schedulers/` for queue/skip/schema; **never** tell owner to re-paste on behavior change ([schedulers/README.md](./prompts/chatgpt/schedulers/README.md#max-limit--what-may-change-in-schedulers)).

### Vocabulary example policy (mandatory, whole Study app)

- Treat a vocabulary item as one canonical item across lessons, Words, Cards, Dictionary, and every other view. Reuse its source-owned example; do not copy examples into user-progress records.
- Never create, accept, render, cache, or persist metalinguistic filler such as `The term “democracy” appeared in a discussion about people, family & relationships.` Also reject equivalent templates that merely say a word/term appeared, was used, or came up in a discussion.
- An example must demonstrate the vocabulary naturally in a meaningful sentence.
- Resolve examples in this exact order: (1) dictionary examples or dictionary quotations; (2) DOL Cambridge Reading/Listening data; (3) DOL Actual Test and Practice Test Plus/Test Plus data; (4) other DOL sources; (5) other local JSON sources; (6) generate a genuine contextual usage sentence only as the final fallback.
- Apply the rejection check at ingestion and at runtime, so legacy or future JSON cannot reintroduce a prohibited example. Generated fallbacks must use the headword in context and must never describe the word as a term.
- Keep `exampleOrigin`/source metadata when available. An example and its translation remain maintained only in their original JSON source; confidence is canonical and synchronized live across views.

### IPA, Vietnamese, formatting, and audio contract (mandatory)

- Preserve source IPA. Store/display main-vocabulary IPA in the canonical US/UK fields used by the schema (`ipaUS`, `ipaUK`, or the existing equivalent); use the app's local IPA shards first and dictionary IPA only as fallback. Never invent phonetic transcription. A view of the same vocabulary must resolve the same IPA rather than create a duplicate copy.
- When sentence/example IPA is available, keep it attached to that exact source sentence and accent. Do not reuse an IPA string after the English sentence changes. Respect the global default accent and alternate-accent controls everywhere.
- English/Vietnamese content is paired: each vocabulary meaning and each maintained example must have its Vietnamese counterpart. Preserve a source translation when present; otherwise use the app translation resolver and cache, without overwriting the source JSON. Do not present machine-generated Vietnamese as original-source text.
- Required vocabulary-card formatting is semantic and stable: English uses `.en`; Vietnamese uses `.vi` (legacy `.vn` may be read but new content uses `.vi`); IPA uses `.ipa`; cards use `.vocab`/`.vocab-card`/`.dol-card`; the main meaning uses `.main-meaning`; English examples use `.ex`/`.exline`; translated examples use `.ex-vi`. Do not add literal `Meaning:`/`Example:` labels or inline styles. Keep one sentence per English paragraph and its Vietnamese line immediately adjacent.
- The parent/page reader control is labeled exactly **`Non-vocab sound`**. Off means speak only each main vocabulary headword. On means speak all reader units: vocabulary, meaning, example, translated/non-vocabulary lines, headings, and section sentences. Page-level reading must never skip a section sentence when this control is on.
- `Non-vocab sound` is the single authoritative reader filter. Do not add a second stale `main only` gate. Synchronize its state in real time across page, section, dock, and preference controls.
- Keep audio controls available at vocabulary, sentence, section, and page level. Main-vocabulary pronunciation follows the selected US/UK accent; sentence audio uses the sentence TTS cascade. Pause/resume, stop, previous/next, one-item mode, speed, gap, and highlighting must operate on the same shared reader queue and must not duplicate progress or vocabulary records.
- Hidden examples must not sound. When non-vocabulary sound is off, meanings/examples/section prose must not sound; when it is on, visible eligible lines sound in DOM order. Any new view must use the shared reader/example/IPA resolvers rather than its own divergent implementation.

### Confidence, completion, filters, and shared-state contract (mandatory)

- A vocabulary headword has one canonical review identity based on its normalized word key, even if it appears in many lessons/sources/views. Lesson occurrences may keep occurrence IDs for navigation, but confidence, review count, last-viewed state, and completion resolve through the canonical ID. Never duplicate progress to simulate synchronization.
- Confidence uses the app's supported scale `0 / 25 / 50 / 75 / 100`. A change in any lesson, Words, Cards, Dictionary, search, or review view must update every currently rendered occurrence in real time and persist once to IndexedDB. `0` is an explicit rating; distinguish it internally from unrated even if their visual treatment is similar.
- Whole-item **Complete / 100%** actions set every eligible child section/question/canonical vocabulary item to 100% in one operation. If the entire target is already 100%, the same action clears those ratings to unrated. Do not change unrelated items, source JSON, bookmarks, flags, examples, IPA, or translations.
- Completion summaries and average confidence must use canonical items once, not count repeated displays. Recompute visible totals, progress bars, badges, and filter results immediately after rating, import, merge, reload, or completion actions.
- Filters are composable AND-filters: source/L1, book/L2, band/L3, topic/L4, skill, lesson/test/passage, confidence, difficulty, seen/unseen, flagged, completed/incomplete, and text search must all remain active together. Changing one filter must not silently reset another unless an explicit Reset action is used.
- Every vocabulary detail page places a Seen filter directly above Confidence with `All`, `Seen`, `Unseen`, and `Unseen OR Confidence filter`. `All`/`Seen`/`Unseen` combine with Confidence using the normal AND rule. The explicit OR option is the sole exception: include a word when it is unseen **or** it passes the currently selected Confidence filter. Persist both selections and update the shown count immediately.
- Filter values come from canonical normalized metadata, while result rows retain occurrence navigation. Counts must match the deduplicated result set shown. Sorting/shuffling changes order only; it must never change membership, confidence, examples, or stable IDs.
- Empty-filter results show a clear empty state and retain controls. Persist supported filter preferences, restore them defensively when values still exist, and ignore stale values without breaking rendering.
- Reloading content may update only source/content caches. It must never overwrite user stores (`progress`, canonical vocabulary confidence, flags, sentences, bookmarks, sessions, or preferences). Export/import and cloud merge preserve canonical IDs and use the existing newer-record-wins rule.
- Source JSON is immutable study content at runtime. User state belongs in IndexedDB; source examples/translations/IPA are resolved by reference. Any migration from legacy occurrence IDs must merge deterministically (keep the newest record and strongest available study metadata), then remove obsolete duplicates only after the canonical record is safely written.
- Any new feature or view must reuse the shared canonical vocabulary, confidence, completion, filtering, example, IPA, translation, and reader services. Test cross-view updates, reload persistence, duplicate headwords, explicit 0%, 100%-toggle clearing, combined filters, and empty states before delivery.

### Sub-navigation contract (mandatory)

- Every multi-section/detail page uses the shared sub-navigation system. Build it from the page's actual visible section hierarchy and stable section IDs; do not maintain a separate hard-coded list that can drift from rendered content.
- Preserve L1 → L2 → L3 → L4 hierarchy and section `level` indentation. Parent labels expand/collapse or navigate consistently, children remain scoped to their parent, and the current item/section is visually and accessibly identified (`aria-current` where appropriate).
- Keep the sticky top table of contents and fixed bottom **previous / current / next** section navigation synchronized with scroll position, programmatic navigation, filtering, collapsing, and rerendering. Previous/next operate only within the current page's eligible visible section order and disable cleanly at boundaries.
- Routes start with `#/`. Never use plain `href="#section-id"` anchors because they can be mistaken for app routes. Navigate within a page through the shared `scrollToSec(sectionId)`/equivalent helper, update history without losing the lesson route, focus the destination heading when appropriate, and honor reduced-motion preferences.
- Deep links and navigation from search, Words, Cards, Dictionary, bookmarks, filters, or duplicate vocabulary occurrences must open the correct source occurrence and section, then highlight/scroll to it. Canonical review identity must not erase occurrence-specific navigation metadata.
- Preserve per-route and per-section scroll position across safe rerenders, back/forward, and returning from another view. Content reload may invalidate a missing target gracefully but must not jump to an unrelated page/section.
- Recompute sub-navigation after asynchronous content load, filter changes, or visibility/collapse changes. Skip hidden/ineligible sections, avoid duplicate IDs, and show a clear current label even when previous or next is unavailable.
- Desktop and mobile use the same ordered model. Controls must remain reachable without covering lesson content, support keyboard activation and screen readers, use adequate touch targets, and keep long labels readable/truncated without losing their accessible name.
- New pages must use this shared model and be tested for first/last boundaries, nested levels, duplicate headings, filtered/hidden sections, deep links, rerender position, browser back/forward, mobile layout, and keyboard navigation.

## Quick links

| Need | File |
|------|------|
| Platform contract (JSON) | [data/templates/template-spec.json](./data/templates/template-spec.json) |
| Human docs for maintainers | [CLAUDE.md](./CLAUDE.md) |
| ChatGPT schedulers | [prompts/chatgpt/schedulers/](./prompts/chatgpt/schedulers/README.md) (frozen bootstrap — **never** edit for behavior) |
| ChatGPT task prompts | [prompts/chatgpt/](./prompts/chatgpt/README.md) (fetched each run) |
| Content by agent | [data/README.md](./data/README.md) |
| Claude Cowork IELTS hourly | [prompts/claude/ielts-hourly.md](prompts/claude/ielts-hourly.md) |

## Repo

`mtm0101/public-sites` · branch **`main`** · GitHub Pages serves `docs/`
