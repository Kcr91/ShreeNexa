# Development tooling — Code Review Graph

## Scope

Install Code Review Graph as optional, local-only development tooling for
token-efficient code discovery and branch review. It is advisory context and
does not replace source inspection, tests, independent review, or any
ShreeNexa safety gate.

## Acceptance criteria

1. `code-review-graph==2.3.8` is pinned in the development dependency group and
   reproducibly locked by `uv.lock`.
2. Codex, Claude Code, Gemini CLI, and the existing VS Code extension launch
   the executable from `F:\ShreeNexa\.venv`; no ShreeNexa configuration relies
   on another project's environment or a global executable.
3. MCP clients expose only `get_minimal_context_tool`,
   `detect_changes_tool`, `get_review_context_tool`,
   `get_impact_radius_tool`, and `query_graph_tool`.
4. The graph database and all generated graph artifacts remain local and
   Git-ignored. No embeddings, cloud provider, credential, remote server,
   daemon, CI comment, or automatic hook is enabled.
5. The initial graph builds successfully on native Windows, reports a healthy
   non-empty index, and can find a known ShreeNexa symbol.
6. A changed-file review produces bounded output with `detail_level="minimal"`.
   On Windows, callers pass an explicit changed-file list when automatic Git
   change discovery is slow or unreliable.
7. Graph freshness is checked before use. Empty or conflicting graph results
   never establish absence; the implementation and its tests remain the source
   of truth.
8. TOML and JSON configuration parse successfully, documentation links resolve,
   the full applicable repository gates pass, and the diff contains no secret
   or protected-path change.
9. Repository guidance routes agents to the exact current status, manifest,
   plan, specification, architecture, and QA sections instead of requiring
   complete repeated reads, without weakening their authority or conflict
   stop condition.

## Non-goals

- Installing or modifying user-level Codex, Claude, Gemini, or Antigravity
  configuration.
- Enabling semantic embeddings or sending source-derived data to a cloud
  provider.
- Making graph output a merge gate or granting unattended integration rights.
- Replacing the approved specification, build plan, manifest, acceptance
  contract, or independent review.
