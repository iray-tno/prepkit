# Contributing to PrepKit

Thank you for your interest in contributing to PrepKit! This document provides guidelines and best practices.

## Development Environment

### Prerequisites

- Python 3.11 or 3.12
- [uv](https://github.com/astral-sh/uv) for dependency management
- System dependencies:
  - `libclang-dev` (for C++ parsing)
  - `clang-format` (for code formatting)
  - `g++` (for C++ compilation)
  - `rustc` (for Rust compilation)

### Setup

```bash
# Clone the repository
git clone https://github.com/iray-tno/prepkit.git
cd prepkit

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest
```

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings for public functions and classes
- Keep functions focused and single-purpose

## Testing

- **All tests must pass** before submitting a PR
- Add tests for new features
- Maintain or improve test coverage
- Run the full test suite: `uv run pytest -v`
- Run with coverage: `uv run pytest --cov=src`

### Test Categories

- Unit tests: `tests/test_*.py`
- Integration tests: `tests/test_*_integration.py`
- Build verification: Tests marked with `@pytest.mark.build`
- Snapshot tests: Tests using syrupy

## Issue-First Workflow

PrepKit follows an **issue-first workflow**: every change traces back to a
GitHub issue, so the branch, commits, and PR all reference the same number.
This keeps history easy to follow and ties each PR to its motivation.

The lifecycle of a change is:

1. **Start from an issue.** Open (or pick up) a GitHub issue describing the
   bug or feature. If you're about to send a PR for something that has no
   issue yet, create the issue first.

2. **Create a branch** from `main`, named
   `feature/<issue-number>_<short_snake_case_description>`:
   ```bash
   git checkout main && git pull
   git checkout -b feature/12_add_kotlin_preprocessor
   ```

3. **Make your changes**
   - Write clean, documented code
   - Add tests for new functionality
   - Update documentation as needed

4. **Test locally**
   ```bash
   # Run all tests
   uv run pytest -v

   # Check a specific test file
   uv run pytest tests/test_your_feature.py -v
   ```

5. **Commit**, prefixing the subject with the issue reference
   `#<num> <type>: <summary>` (see Commit Message Guidelines):
   ```bash
   git commit -m "#12 feat: add Kotlin preprocessor"
   ```

6. **Push and open a PR** targeting `main`. Include `Closes #<num>` in the
   PR body so the issue closes automatically when the PR is merged:
   ```bash
   git push -u origin feature/12_add_kotlin_preprocessor
   ```

7. **Wait for CI.** GitHub Actions runs the full test suite — fix any
   failures before requesting review.

> Stacked work: if a change naturally builds on another that isn't merged
> yet, branch off that branch instead of `main` and rebase onto `main`
> once the base PR lands.

## Commit Message Guidelines

Commit subjects start with the issue reference, followed by a
[conventional commits](https://www.conventionalcommits.org/) type:

```
#<issue-number> <type>: <summary>
```

Types:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `ci:` - CI/CD changes
- `chore:` - Maintenance tasks

Examples:
```
#12 feat: add Kotlin preprocessor support
#8 fix: resolve include path resolution on Windows
#5 docs: sync README.ja.md with current Rust support
#2 test: add integration tests for Rust preprocessor
```

## Keeping Your Repo Clean

The `.gitignore` file handles most cleanup automatically, but you may want to manually clean:

```bash
# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Remove test artifacts
rm -rf .pytest_cache .hypothesis htmlcov

# Remove build artifacts
rm -rf dist build *.egg-info

# Remove coverage files
rm -f .coverage coverage.xml
```

## Code Review

- Be respectful and constructive
- Explain your reasoning
- Be open to feedback
- Focus on code quality and maintainability

## Need Help?

- Check existing issues and discussions
- Read the documentation in README.md
- Ask questions in issue comments
- Be specific about your problem and environment

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.
