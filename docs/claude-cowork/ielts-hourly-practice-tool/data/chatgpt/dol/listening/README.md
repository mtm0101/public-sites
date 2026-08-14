# DOL listening local cache

This folder is for IELTS listening test assets cloned from DOL pages.

Tracking files:

- `catalog.json` lists every DOL listening test in the same priority/order as `../catalog.json`.
- `upcoming.json` stores the remaining queue; `queue[0]` is processed next.
- `state.json` stores completed tests in `sent`, retryable/current work in `current`, and errors in `failed`.
- `manifest.json` lists completed tests that the dashboard can play.

Per-test layout:

- `<test-id>/meta.json` stores one test's sections, source URLs, local paths, and cue counts.
- `<test-id>/audio/section-N.m4a` stores local section audio when downloaded.
- `<test-id>/transcripts/section-N.json` stores normalized subtitle cues for realtime highlighting.
- `<test-id>/transcripts/section-N.vtt` stores the original VTT when downloaded.

Run from the repo root:

```powershell
powershell -File .\dol-listening-download-all.ps1
```

That downloads one test at a time and continues until the queue is empty. It is safe to stop with Ctrl+C or close the window; rerun the same command to resume. To test only one item:

```powershell
powershell -File .\dol-listening-download-all.ps1 -MaxTests 1
```

Useful maintenance:

```powershell
powershell -File .\dol-listening-download-all.ps1 -InitOnly
powershell -File .\dol-listening-download-all.ps1 -Force -MaxTests 1
```

Future test cloning can add sibling folders such as `questions/` and `answer-keys/` under each `<test-id>` without conflicting with the listening player.
