# Contributing to renogy-ha

Thanks for contributing.

Start here:

- Read [`AGENTS.md`](AGENTS.md) for repository-specific guardrails.
- Read [`README.md`](README.md) for integration capabilities, prerequisites, and user-facing behavior.

## Scope and Boundaries

`renogy-ha` is the Home Assistant integration layer.

- Include Home Assistant lifecycle, config flow, coordinator/entity behavior, and platform wiring changes here.
- Keep BLE transport, Modbus command construction, and response parsing logic in `renogy-ble`.
- `renogy-ha` depends on `renogy-ble`; dependency direction should remain one-way.

If your fix is protocol/parsing/BLE-transport specific, implement it in `renogy-ble` and then bump/update usage here as needed.

## Development Setup

This repository uses `uv` for environment and dependency management.

1. Install dependencies: `uv sync --all-groups`
2. Run tests: `uv run pytest tests`

## Quality Gates

Before opening a PR, run:

1. `uv run ruff format .`
2. `uv run ruff check . --output-format=github`
3. `uv run ty check . --output-format=github`
4. `uv run pytest tests`

## Documentation

- Use Markdown.
- Put project documentation under `docs/`.

## Pull Requests

- Add or update tests for behavior changes.
- Keep changes focused and clearly scoped.
- Use conventional commit prefixes (`fix:`, `feat:`, `docs:`, etc.).
- Do not edit `CHANGELOG.md` or manually update the version (release automation handles it).

## Reporting Issues

When filing a bug, include:

- Home Assistant version
- Integration version
- Device model and BT module (BT-1/BT-2)
- Relevant Home Assistant logs (debug logs help)
- Clear reproduction steps
