# Codex Project Configuration

This directory contains narrow, reviewed defaults for interactive work in ShreeNexa. Codex loads a project `.codex/config.toml` only when the project is trusted. CLI flags, managed requirements, and higher-precedence configuration may further restrict or override these defaults.

The project layer deliberately:

- keeps approval interactive;
- limits shell writes to the workspace-write sandbox;
- disables outbound network inside that sandbox by default;
- retains the documented 32 KiB project-instruction limit;
- does not set a model/provider, credentials, MCP servers, hooks, external writable roots, or danger-full-access.

Behavioral instructions and review rules live in root `AGENTS.md`; this TOML file is not a substitute for OS permissions, sandbox enforcement, protected-path review, or user approval.

Official references checked for M0.4:

- [Custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [Config basics](https://developers.openai.com/codex/config-basic)
- [Configuration reference](https://developers.openai.com/codex/config-reference)
