# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Development Commands

```bash
# Install dependencies (uses uv)
uv sync

# Run all tests
uv run pytest

# Run a single test
uv run pytest tests/test_basic.py::test_config_parses_owner_repo

# Run tests with verbose output
uv run pytest -v
```

## v2 Redesign (in progress)

RepoCraft is being redesigned from a single-issue fixer into an **autonomous codebase maintenance agent**. See `TODOLIST.md` for the full design document including architecture, decisions, risks, and task breakdown.

### v2 Architecture Summary

```
Host: repocraft (Python CLI + scheduler + SQLite)
  └── Docker Container "repocraft-worker" (long-running)
      ├── Claude Code CLI (the agent — has Bash, Edit, Read, Write, Grep, Glob)
      ├── ~/.claude/CLAUDE.md         ← user-level rules (all repos)
      ├── /repos/{owner-repo}/
      │   ├── CLAUDE.md               ← repo-level knowledge (agent-generated)
      │   └── .claude/memory/         ← auto-memory (Claude Code native)
      └── git, gh, python, node, uv
```

**Key change**: Claude Code CLI (`claude -p`) IS the agent. RepoCraft is a thin scheduler that dispatches tasks and collects results. No custom MCP tools, no custom agent loop.

### Three Trigger Modes

1. **Human command**: `repocraft fix <issue_url>` / `repocraft ask <repo> "add caching"`
2. **GitHub events**: New issues, PR reviews, @mentions → auto-create activities
3. **Proactive scan**: Periodic codebase audit → find bugs, security issues, outdated deps

### Activity Kinds

| Kind | What agent does |
|------|----------------|
| `init` | Explore new repo, generate repo-specific CLAUDE.md |
| `fix_issue` | Understand → fix → test → PR |
| `task` | Execute arbitrary instruction (add feature, investigate, refactor) |
| `scan` | Full codebase audit → issues/PRs |
| `respond_review` | Address PR review comments |
| `triage` | Evaluate new issue → reply + label |

### Modules to keep

- `github/issue_fetcher.py` — reuse as-is

### Modules to delete (Claude Code replaces them)

- `agent/orchestrator.py`, `agent/prompts.py`
- `tools/container_tools.py`, `tools/evidence_tools.py`
- `evidence/models.py`, `evidence/collector.py`, `evidence/reporter.py`

### New modules to create

- `store.py` — SQLite (repos, activities, logs)
- `scheduler.py` — main loop + worker pool + event polling
- `dispatcher.py` — `claude -p` execution + log streaming
- `container/manager.py` — rewrite for long-running container + multi-repo
- `container/Dockerfile` — new image with Claude Code + Node + gh
- `templates/user_claude_md.py` — user-level CLAUDE.md template
- `templates/init_prompt.py` — repo init prompt
- `cli.py` — rewrite with subcommands: fix, submit, ask, daemon, status, logs, review, watch

### Implementation order

Start with M0 (container image + manager + SQLite) → M1 (dispatcher + CLI fix + end-to-end) → M2 (scheduler + daemon + ask). See TODOLIST.md for details.

## v1 Architecture (current code, to be replaced)

The existing code uses Claude Agent SDK with custom MCP tools in a 3-phase workflow (Reproduce → Fix → Verify). This will be replaced by the v2 architecture above.
