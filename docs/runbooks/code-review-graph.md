# Code Review Graph runbook

ShreeNexa pins Code Review Graph 2.3.8 as optional local development tooling.
The graph narrows discovery and review context; it does not prove correctness
and does not replace reading the selected implementation and tests.

## Build and inspect

Run from `F:\ShreeNexa`:

```powershell
python -m uv sync --locked
.\.venv\Scripts\code-review-graph.exe build --repo F:\ShreeNexa
.\.venv\Scripts\code-review-graph.exe status --repo F:\ShreeNexa
```

The graph is stored below `.code-review-graph/` and is local runtime state.
Do not commit or publish it; exports can contain absolute paths and structural
source metadata.

## Token-efficient workflow

1. Check graph freshness with `status` or refresh it with `update`.
2. Start an MCP task with `get_minimal_context_tool`.
3. Use `detail_level="minimal"` and a specific symbol or changed-file list.
4. Use no more than five graph calls unless the result identifies a concrete
   reason to expand.
5. Read the selected implementation and its tests before any non-trivial edit.
6. Prefer source when it disagrees with the graph. Treat an empty result as
   possibly stale, ignored, unsupported, or unindexed.

On Windows, CLI file queries should use the repository-absolute path with
forward slashes, for example `F:/ShreeNexa/backend/app/main.py`.

For a branch review, obtain the file list explicitly and pass it to the review
tool when needed:

```powershell
git diff --name-only main...HEAD
.\.venv\Scripts\code-review-graph.exe detect-changes --repo F:\ShreeNexa --base main --brief
```

The CLI token-savings panel is an estimate, not an acceptance result. Review
the full Git diff and run every applicable gate after using the graph.

## Deliberately disabled

- Embeddings and every cloud embedding provider.
- Auto-watch, daemon, and Codex lifecycle hooks.
- GitHub Action/CI comments.
- Automatic edits or refactors through the graph server.
- User-level or global client configuration.

The MCP server is launched on demand by each trusted project client. Its
allowlist contains five read-only discovery/review tools. Antigravity currently
uses user-level MCP configuration, so it is not changed by this repository
setup; add it only through a separately reviewed user-level action.

## Recovery

If the graph is stale or corrupt, stop all clients using it, remove only the
resolved `F:\ShreeNexa\.code-review-graph` directory after verifying that exact
path, and rebuild. Never use recursive cleanup against the repository or data
root.
