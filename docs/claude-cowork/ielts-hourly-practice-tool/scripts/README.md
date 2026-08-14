# Scripts — automation

| Script | Purpose |
|--------|---------|
| [convert_lessons.py](./convert_lessons.py) | Index all `data/**/*.json` → `manifest.json` |
| [convert_bbc_html.py](./convert_bbc_html.py) | `bbc-lessons/*.html` → `data/claude-cowork/bbc/` |
| [upload-to-s3.ps1](./upload-to-s3.ps1) | **Deprecated** — old S3 content sync |
| [cleanup-s3.ps1](./cleanup-s3.ps1) | One-time bucket orphan cleanup |

Run from **tool root**:

```powershell
python scripts/convert_lessons.py
python scripts/convert_bbc_html.py
```

Repo root pipeline: `update-index-and-push.ps1` (pull → convert → push).
