# Codex Project Configuration

This directory contains narrow, reviewed defaults for interactive work in ShreeNexa. Codex loads a project `.codex/config.toml` only when the project is trusted. CLI flags, managed requirements, and higher-precedence configuration may further restrict or override these defaults.

The project layer deliberately:

- keeps approval interactive;
- limits shell writes to the workspace-write sandbox;
- disables outbound network inside that sandbox by default;
- retains the documented 32 KiB project-instruction limit;
- does not set a model/provider, credentials, hooks, external writable roots, or danger-full-access;
- enables one optional project-local Code Review Graph MCP server with five
  read-only discovery/review tools and no cloud embeddings.

Behavioral instructions and review rules live in root `AGENTS.md`; this TOML file is not a substitute for OS permissions, sandbox enforcement, protected-path review, or user approval.

Official references checked for M0.4:

- [Custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [Config basics](https://developers.openai.com/codex/config-basic)
- [Configuration reference](https://developers.openai.com/codex/config-reference)
- [Model Context Protocol](https://learn.chatgpt.com/docs/extend/mcp)

The graph server runs from the repository's pinned `.venv` only after
`python -m uv sync --locked`. It is non-required so a missing or stale graph
cannot block Codex startup; follow `docs/runbooks/code-review-graph.md` and
prefer implementation source whenever graph output differs.
