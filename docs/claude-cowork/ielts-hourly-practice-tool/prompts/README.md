# Scheduler prompts

**Specs** ([../specs/](../specs/README.md)) define *what* to build.  
**Prompts** here define *how* each automation runs.

| Folder | Agent | Pattern |
|--------|-------|---------|
| [chatgpt/](./chatgpt/README.md) | ChatGPT scheduled tasks | Task `.md` (fetched) + [schedulers/*.scheduler.md](./chatgpt/schedulers/README.md) (human copy-paste) |
| [claude/](./claude/README.md) | Claude Cowork | Task `.md` from Pages or local path |

Pages base: `https://mtm0101.github.io/public-sites/claude-cowork/ielts-hourly-practice-tool/prompts/`
