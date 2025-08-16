# PrepKit Testing Guide

This guide covers PrepKit's comprehensive testing strategy and how to run tests during development.

## Test Architecture Overview

PrepKit uses a multi-layered testing approach to ensure reliability and correctness:

### Test Categories

1. **Unit Tests** (`tests/test_cpp_preprocessor.py`) - 7 focused tests
2. **Integration Tests** (`tests/test_cpp_integration.py`) - 13 comprehensive tests
3. **Build Verification Tests** - Ensure preprocessed code compiles with g++
4. **Snapshot Tests** - Regression testing with golden master files
5. **Property-Based Tests** - Fuzz testing with Hypothesis
6. **Performance Benchmarks** - Speed and efficiency validation

## Running Tests

### Quick Test Commands

```bash
# Run all tests
poetry run pytest

# Quick smoke test
poetry run pytest -q

# Verbose output with details
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_cpp_preprocessor.py

# Run specific test
poetry run pytest tests/test_cpp_preprocessor.py::test_cpp_preprocess_constexpr
```

### Test Categories

```bash
# Unit tests only (fast)
poetry run pytest tests/test_cpp_preprocessor.py

# Integration tests only
poetry run pytest tests/test_cpp_integration.py

# Build verification tests (requires g++)
poetry run pytest -m build

# Performance benchmarks
poetry run pytest --benchmark-only

# Property-based tests (fuzz testing)
poetry run pytest -k "property"
```

### Test Output Control

```bash
# Minimal output (just pass/fail)
poetry run pytest --tb=no -q

# Short traceback on failures
poetry run pytest --tb=short

# Stop on first failure
poetry run pytest -x

# Show local variables on failure
poetry run pytest -l
```

## Test Types in Detail

### 1. Unit Tests (Fast Validation)

**Purpose**: Test individual functions and basic functionality
**Location**: `tests/test_cpp_preprocessor.py`
**Runtime**: ~1 second

```bash
# Run unit tests
poetry run pytest tests/test_cpp_preprocessor.py -v

# Specific constexpr tests
poetry run pytest -k "constexpr"
```

**Coverage**:
- Include resolution
- Constexpr replacement (int/float/bool/string)
- Comment removal
- Basic minification

### 2. Integration Tests (Comprehensive Validation)

**Purpose**: Test complete workflows with realistic scenarios
**Location**: `tests/test_cpp_integration.py`
**Runtime**: ~20 seconds

```bash
# Run integration tests
poetry run pytest tests/test_cpp_integration.py -v

# Run only snapshot tests
poetry run pytest -k "snapshot"
```

**Coverage**:
- Algorithm templates (segment trees, etc.)
- Competitive programming solutions
- Complex constexpr scenarios
- Nested include hierarchies
- Error handling and edge cases

### 3. Build Verification Tests (Critical)

**Purpose**: Ensure preprocessed code compiles with g++
**Marker**: `@pytest.mark.build`
**Requirement**: g++ compiler installed

```bash
# Run build verification tests
poetry run pytest -m build

# Specific build test
poetry run pytest tests/test_cpp_integration.py::TestCppPreprocessorEnhanced::test_build_verification_segment_tree
```

**What it tests**:
- Preprocessed C++ code compiles without errors
- Multiple compiler flag combinations
- Real competitive programming scenarios
- Minified code compilation compatibility

### 4. Snapshot Testing (Regression Prevention)

**Purpose**: Detect unintended changes in preprocessing output
**Tool**: Syrupy snapshot testing
**Storage**: `tests/__snapshots__/`

```bash
# Update snapshots when behavior changes intentionally
poetry run pytest --snapshot-update

# Update specific snapshot
poetry run pytest tests/test_cpp_integration.py::TestCppPreprocessorEnhanced::test_complex_constexpr_snapshot --snapshot-update
```

**When to update snapshots**:
- ✅ Intentional improvement to constexpr replacement
- ✅ Better code formatting or minification
- ❌ Accidental regression in functionality

### 5. Property-Based Testing (Robustness)

**Purpose**: Test with randomly generated inputs
**Tool**: Hypothesis library
**Focus**: Edge cases and boundary conditions

```bash
# Run property-based tests
poetry run pytest -k "property"

# With verbose hypothesis output
poetry run pytest -k "property" -s
```

**Test patterns**:
- Random C++ identifiers and values
- Various constexpr combinations
- File size and complexity variations

### 6. Performance Benchmarks

**Purpose**: Monitor processing speed and detect performance regressions
**Tool**: pytest-benchmark
**Target**: <1 second for typical contest solutions

```bash
# Run performance benchmarks
poetry run pytest --benchmark-only

# Save benchmark results
poetry run pytest --benchmark-only --benchmark-save=baseline

# Compare with baseline
poetry run pytest --benchmark-only --benchmark-compare=baseline
```

**Monitored metrics**:
- Preprocessing time for typical files (~730ms)
- Memory usage patterns
- Large file handling performance

## Test Development Guidelines

### Writing New Tests

```python
# Unit test example
def test_new_feature(cpp_preprocessor, temp_files):
    """Test description following convention."""
    # Arrange
    test_file = temp_files / "test.cpp"
    
    # Act
    output = cpp_preprocessor.preprocess(str(test_file), [])
    
    # Assert
    assert "expected_output" in output
    assert "unwanted_output" not in output
```

### Integration Test Patterns

```python
# Integration test with build verification
@pytest.mark.build
def test_complex_scenario_build(cpp_preprocessor, test_cases_dir):
    """Test complex scenario compiles correctly."""
    # Process file
    output = cpp_preprocessor.preprocess(file_path, include_paths)
    
    # Verify compilation
    with tempfile.NamedTemporaryFile(suffix='.cpp', mode='w', delete=False) as f:
        f.write(output)
        result = subprocess.run(['g++', '-o', '/dev/null', f.name])
        assert result.returncode == 0
```

### Snapshot Test Guidelines

```python
def test_feature_snapshot(cpp_preprocessor, snapshot):
    """Test with snapshot for regression detection."""
    output = cpp_preprocessor.preprocess(file_path, [])
    
    # Functional assertions first
    assert basic_functionality_works(output)
    
    # Then snapshot for regression detection
    assert output == snapshot(name="feature_name_processed")
```

## Continuous Integration

### Pre-commit Hooks

```bash
# Run before each commit
poetry run pytest --tb=short -q

# Full validation before push
poetry run pytest
```

### Test Quality Metrics

Track these metrics over time:
- **Test Coverage**: Aim for >90% line coverage
- **Build Success Rate**: 100% for build verification tests
- **Performance Stability**: <10% variance in benchmark times
- **Snapshot Stability**: Minimal unexpected snapshot changes

## Troubleshooting Tests

### Common Issues

```bash
# Hypothesis database conflicts
rm -rf .hypothesis/

# Snapshot mismatches after intentional changes
poetry run pytest --snapshot-update

# Build verification failures
# Check g++ installation: g++ --version
# Check libclang: find /usr -name "*libclang*" 2>/dev/null

# Performance regression
poetry run pytest --benchmark-only --benchmark-compare=baseline

# Property-based test failures
# Check the generated example in test output
# Add assumes() statements to constrain input space
```

### Test Environment Setup

```bash
# Install all test dependencies
poetry install

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install libclang-18 clang-format g++

# Verify test environment
poetry run pytest --collect-only  # Should show ~20 tests
```

### Test Data Management

```bash
# Test file locations
tests/cpp_test_cases/          # Integration test files
tests/__snapshots__/           # Snapshot baselines
.hypothesis/                   # Hypothesis database
.pytest_cache/                 # Pytest cache

# Clean test artifacts
rm -rf .pytest_cache .hypothesis
```

## Test-Driven Development

### Adding New Features

1. **Write failing test** for new functionality
2. **Implement minimal** code to make test pass
3. **Add integration test** with realistic scenario
4. **Add build verification** if touching preprocessing
5. **Update snapshots** if output format changes
6. **Add performance test** if affecting speed

### Refactoring Workflow

1. **Run full test suite** before changes
2. **Make incremental changes** with frequent test runs
3. **Update snapshots** only for intentional changes
4. **Verify performance** hasn't regressed
5. **Add tests** for any new edge cases discovered

This testing strategy ensures PrepKit remains reliable and performant while supporting rapid development and refactoring.