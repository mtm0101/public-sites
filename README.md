# public-sites

Static site repo for hosting docs and HTML pages via GitHub Pages.

## Structure

```
docs/
  index.html                        # Main landing page
  claude-cowork/                    # Content folders (one subfolder per topic)
    <topic>/
      *.html / *.pdf / *.md
  index-claude-cowork-13571357.html # Auto-generated index for claude-cowork
```

## Scripts

| Script | Purpose |
|---|---|
| `update-index-and-push.ps1` | Rebuild `index-claude-cowork-*.html` from current folders, then commit & push |
| `reset-history.ps1` | Squash all git history to a single commit and force-push |

## Workflow

1. Drop files into the relevant `docs/claude-cowork/<topic>/` folder.
2. Run `.\update-index-and-push.ps1` — it rebuilds the index and pushes to GitHub.
