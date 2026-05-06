# Contributing to CPublishr

Thank you for your interest in contributing! Here is everything you need to get started.

## Getting Started

1. Fork the repository and clone your fork
2. Follow the setup steps in [Development.md](developer-guide/Development.md)
3. Create a branch for your change: `git checkout -b feat/your-feature-name`

## Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/<name>` | `feat/twitter-adapter` |
| Bug fix | `fix/<name>` | `fix/sas-url-refresh` |
| Docs | `docs/<name>` | `docs/deployment-guide` |
| Refactor | `refactor/<name>` | `refactor/voice-profile-service` |

## Making Changes

- Keep changes focused — one concern per PR
- Add or update tests for any logic you change
- Run the linter before pushing: `ruff check backend/src/`
- Ensure the backend starts cleanly: `uvicorn src.main:app --reload`

## Pull Request Process

1. Push your branch and open a PR against `main`
2. Fill in the PR description explaining **what** changed and **why**
3. A maintainer will review and may request changes
4. Once approved and CI passes, your PR will be merged

## Adding a Platform Adapter

CPublishr supports pluggable platform adapters (LinkedIn, Instagram, etc.). To add a new one, follow the guide in [Generate_Adapter.md](developer-guide/SolutionUnderstanding/Generate_Adapter.md).

## Code Style

- **Python**: [Ruff](https://docs.astral.sh/ruff/) for linting (`ruff check src/`)
- **React**: Standard ESLint config (included in `ui/react`)
- Type hints on all new Python functions
- Docstrings on public service methods

## Reporting Issues

Use the GitHub Issues tab. Please include:
- Steps to reproduce
- Expected vs actual behaviour
- Python / Node version
- Relevant log output

## Security Vulnerabilities

Please do **not** open a public issue for security bugs. Email the maintainers directly or use GitHub's private vulnerability reporting.
