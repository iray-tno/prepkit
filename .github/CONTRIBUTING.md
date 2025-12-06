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

## Pull Request Process

1. **Create a feature branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Add tests for new functionality
   - Update documentation as needed

3. **Test locally**
   ```bash
   # Run all tests
   uv run pytest -v

   # Check specific test file
   uv run pytest tests/test_your_feature.py -v
   ```

4. **Commit with clear messages**
   ```bash
   git commit -m "feat: add new feature X"
   # or
   git commit -m "fix: resolve issue with Y"
   # or
   git commit -m "docs: update README for Z"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then open a pull request on GitHub

6. **Wait for CI**
   - GitHub Actions will run all tests
   - Fix any failing tests before requesting review

## Commit Message Guidelines

We follow conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding or updating tests
- `refactor:` - Code refactoring
- `ci:` - CI/CD changes
- `chore:` - Maintenance tasks

Examples:
```
feat: add Kotlin preprocessor support
fix: resolve include path resolution on Windows
docs: update installation instructions
test: add integration tests for Rust preprocessor
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
