# Repository Guidance

## Purpose and boundaries
- Maintain typed, theme-driven Plotly chart constructors for library consumers.
- Keep chart construction here; publication layout belongs to `wood-reports`.

## Development
- Put reusable chart APIs in `src/`, theme behavior in the package, and focused tests in `tests/`.
- Treat exported figure dimensions and theme defaults as consumer-visible behavior.

## Validation
- Run `uv sync --frozen --group dev`, `uv run ruff check src tests`, `uv run mypy`, and `uv run pytest`.
- Run configured pre-commit hooks for a full repository check.
- Use `scripts/check_canonical_notebooks.py` when canonical gallery notebooks change.

## Architecture constraints
- Keep notebook and gallery artifacts derived from package code, not as competing implementations.
- Preserve public constructor compatibility when extending chart types.

## Safety
- Keep generated artifacts and local data out of source changes unless intentionally updating examples.

## Branching strategy

- This repository uses **trunk-based development**. Create short-lived change branches from current `main` and target PRs to `main`.
- Follow the [canonical branching and delivery policy](https://github.com/SpencerRWood/codex-config/blob/main/docs/branching-policy.md), available through the installed codex-config source path. Verify the strategy, release association, fetched base and PR target before implementation and record them in Story evidence. Story completion does not authorize publication or deployment; retain existing review, CI, security and rollback requirements.
