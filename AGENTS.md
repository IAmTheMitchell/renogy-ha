# Background

renogy-ha is a Home Assistant integration written in Python and distributed via HACS. Its purpose is to allow Home Assistant to connect to Renogy devices over Bluetooth low energy and send and receive modbus commands. renogy-ha depends on the renogy-ble library to connect to the devices, send commands, and parse responses. renogy-ha itself is the "glue-layer" between Home Assistant and the renogy-ble library.

# Documentation

- Use Markdown for all documentation.
- Place documentation in the `docs/` directory.

# Code Style

- Add comments to code when it may be unclear what the code does or how it functions.
- Comments should be full sentences and end with a period.
- Maintainable and understandable code is preferred over complex code.

# Python

- Use uv to manage Python and all Python packages.
- Use 'uv add [package_name]' instead of 'uv pip install [package_name]'.

# Testing

- Use pytest for Python testing.
- Ensure all code is formatted and linted with Ruff.

# Files

- Do not create binary files, such as Lambda zip files.
- Do not modify CHANGELOG.md. This is handled by CI.

# Commits

- Use conventional commits for all changes
  - Prefix all commit messages with fix:; feat:; build:; chore:; ci:; docs:; style:; refactor:; perf:; or test: as appropriate.

# Before Checking In Code

- Fix all code formatting and quality issues in the entire codebase.
- Ensure all new code is covered by appropriate unit tests.

## Python

Fix all Python formatting and linting issues.

### Steps:

1. **Format with ruff**: `uv run ruff format .`
2. **Lint with ruff**: `uv run ruff check . --output-format=github`
3. **Type check with ty**: `uv run ty check . --output-format=github`
4. **Run unit tests**: `uv run pytest tests`
5. **Repeat 1-4 until all steps pass on a single run**

## General Process:

1. Run automated formatters first.
2. Fix remaining linting issues manually.
3. Resolve type checking errors.
4. Verify all tests pass with no errors.
5. Review changes before committing.

## Common Issues:

- Import order conflicts between tools
- Line length violations
- Unused imports/variables
- Type annotation requirements
- Missing return types
- Inconsistent quotes/semicolons

## Issue Tracking

This repo uses `bd` (Beads) for active task tracking.

- Run `bd ready` before starting work.
- Use `bd prime` when you need the current Beads workflow context.
- Track Home Assistant integration work here.
- When work belongs in `renogy-ble`, create it there explicitly with `bd create --repo ../renogy-ble ...` from this repo, or create it directly in the `renogy-ble` repo.
- For cross-repo work, create a coordinating issue here and link the `renogy-ble` implementation issue with a dependency.
- Do not use markdown TODO lists for active work.
