# PrepKit Development Instructions for Claude Code

## Project Overview
PrepKit is a competitive programming and ML workflow automation tool that:
- Preprocesses and minifies C++ code for contests
- Automates Kaggle competition submissions
- Tracks experiments with WandB integration
- Generates project templates for quick setup
- Supports multiple programming languages through plugins

## Development Guidelines

### Code Style
- Follow existing patterns in the codebase
- Use type hints for all Python functions
- Keep C++ templates optimized for competitive programming
- Maintain plugin architecture for language support

### Testing Strategy
- Run `poetry run pytest` for all tests
- Use `--snapshot-update` when output formats change
- Test C++ compilation with actual contest scenarios
- Validate preprocessing pipeline end-to-end

### Key Commands
```bash
# Development testing
poetry run python -m main --help
poetry run python -m main preprocess path/to/file.cpp
poetry run python -m main project new test --lang cpp --type atcoder-algorithm

# Testing
poetry run pytest
poetry run pytest tests/test_cpp_integration.py -v
poetry run pytest --snapshot-update

# Building
poetry build
poetry install
```

### File Structure
- `src/main.py` - CLI entry point
- `src/plugins/` - Language-specific processors
- `src/boilerplate/` - Project templates
- `tests/` - Comprehensive test suite
- `configs/` - AI assistant configurations

### Common Tasks
1. **Adding new contest types**: Update `src/boilerplate/project_configs.yaml`
2. **Extending C++ preprocessing**: Modify `src/plugins/cpp_plugin.py`
3. **Adding language support**: Create new plugin in `src/plugins/`
4. **Kaggle integration**: Enhance `src/kaggle_automation.py`

### Safety Notes
- Always test C++ compilation after preprocessing changes
- Validate constexpr replacement doesn't break code logic
- Ensure minification preserves functionality
- Test template generation end-to-end

## Permissions Granted
- Read/write all project files
- Execute build and test commands
- Create new files for features/tests
- Modify configuration files
- Run C++ compilation for testing