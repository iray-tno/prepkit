# PrepKit

A comprehensive tool to streamline competitive programming and machine learning workflows, written in Python. PrepKit automates code management, experiment tracking, and submission processes for platforms like Atcoder, Codingame, and Kaggle.

## Table of Contents
- [Installation](#installation)
  - [Python Dependencies](#python-dependencies)
  - [System Dependencies](#system-dependencies)
- [Usage](#usage)
  - [C++ Preprocessor](#c-preprocessor)
  - [C++ Minifier](#c-minifier)
  - [Project Management](#project-management)
  - [Kaggle Automation](#kaggle-automation)
  - [Experiment Management](#experiment-management)
- [Testing](#testing)
- [Plugin Architecture](#plugin-architecture)
- [Contributing](#contributing)

## Installation

### Python Dependencies

PrepKit uses [Poetry](https://python-poetry.org/) for dependency management.

1.  **Install Poetry** (if you haven't already):
    ```bash
    pip install poetry
    ```
2.  **Install Project Dependencies**: Navigate to the project root and run:
    ```bash
    poetry install
    ```
    This will create a virtual environment and install all required Python packages.

### System Dependencies

PrepKit relies on `libclang` for C++ parsing and `clang-format` for code formatting and minification.

1.  **Install `libclang`**:
    *   **For Debian/Ubuntu**:
        ```bash
        sudo apt-get update
        sudo apt-get install -y libclang-18 # Or the latest available version like libclang-16, libclang-17
        ```
    *   **For other Linux distributions**: Consult your distribution's package manager documentation for the correct `libclang` package name.

2.  **Install `clang-format`**:
    *   **For Debian/Ubuntu**:
        ```bash
        sudo apt-get update
        sudo apt-get install -y clang-format
        ```
    *   **For other Linux distributions**: Consult your distribution's package manager documentation for the correct `clang-format` package name.

## Usage

All commands are executed via `poetry run prepkit <command>`.

### C++ Preprocessor

The `cpp preprocess` command integrates multiple C++ files into a single file, replaces `constexpr` variables with their values, removes comments, and formats the code.

```bash
poetry run prepkit cpp preprocess <file_path> [-I <include_path>]...
```

*   `<file_path>`: The path to the main C++ file to preprocess.
*   `-I <include_path>` / `--include-path <include_path>`: Optional. Specifies additional directories to search for included files. Can be used multiple times.

**Example:**

```bash
poetry run prepkit cpp preprocess my_project/main.cpp -I my_project/headers -I /usr/local/include
```

### C++ Minifier

The `cpp minify` command aggressively removes whitespace and comments from a C++ file, making it suitable for platforms with strict code size limits.

```bash
poetry run prepkit cpp minify <file_path>
```

*   `<file_path>`: The path to the C++ file to minify.

**Example:**

```bash
poetry run prepkit cpp minify my_solution.cpp
```

### Project Management

PrepKit provides project scaffolding to quickly create boilerplate code for different competitive programming platforms.

#### Create New Project

```bash
poetry run prepkit project new <project_name> [--lang <language>] [--type <project_type>]
```

*   `<project_name>`: Name of the project directory to create
*   `--lang <language>`: Programming language (default: `cpp`)
*   `--type <project_type>`: Project template type (default: `atcoder-algorithm`)

**Available project types:**
- `atcoder-algorithm`: AtCoder competitive programming setup
- `codingame`: Codingame setup with minification enabled
- `kaggle`: Kaggle competition setup

**Example:**

```bash
poetry run prepkit project new my_contest --lang cpp --type atcoder-algorithm
```

This creates a new directory with boilerplate code and a `prepkit_config.yaml` file configured for the specified platform.

### Kaggle Automation

PrepKit provides commands to automate common Kaggle workflows.

#### Push Notebook

Pushes a Jupyter notebook or Python script to Kaggle Kernels.

```bash
poetry run prepkit kaggle push-notebook <notebook_file> [--title <title>] [--slug <slug>] [--language <language>] [--private|--public]
```

*   `<notebook_file>`: Path to the `.ipynb` or `.py` file.
*   `--title`: Optional. Title of the Kaggle notebook. Defaults to a derived name from the filename.
*   `--slug`: Optional. Slug for the Kaggle notebook. Defaults to a derived slug from the title.
*   `--language`: Optional. Programming language of the notebook (default: `python`).
*   `--private` / `--public`: Optional. Sets the visibility of the notebook (default: `private`).

**Important:** After running this command, a `kernel-metadata.json` file will be generated in the notebook's directory. You **must** manually replace `<KAGGLE_USERNAME>` in the `id` field of this JSON file with your actual Kaggle username before the first successful push.

**Example:**

```bash
poetry run prepkit kaggle push-notebook my_notebook.ipynb --title "My Kaggle Analysis" --public
```

#### Submit Competition

Submits a prediction file to a Kaggle competition.

```bash
poetry run prepkit kaggle submit-competition <submission_file> --competition <competition_name> [--message <message>]
```

*   `<submission_file>`: Path to the submission CSV or other required file.
*   `--competition <competition_name>`: **Required**. The Kaggle competition URL slug (e.g., `titanic`).
*   `--message <message>`: Optional. A message for your submission (default: `From PrepKit`).

**Example:**

```bash
poetry run prepkit kaggle submit-competition submission.csv --competition titanic --message "First submission with new model"
```

### Experiment Management

PrepKit integrates with Hydra, Optuna, and Weights & Biases (WandB) for structured experiment configuration, hyperparameter optimization, and tracking.

#### Run Experiment

Runs an experiment based on a Hydra configuration file.

```bash
poetry run prepkit experiment run <config_path> <config_name>
```

*   `<config_path>`: The path to your Hydra configuration directory (relative to the project root).
*   `<config_name>`: The name of the main configuration file (e.g., `config.yaml`).

**Example:**

Assuming you have `conf/config.yaml`:

```yaml
# conf/config.yaml
params:
  learning_rate: 0.01
  epochs: 10
wandb:
  project: my_ml_project
  entity: your_wandb_entity
```

Run the experiment:

```bash
poetry run prepkit experiment run conf config
```

You can override parameters from the command line:

```bash
poetry run prepkit experiment run conf config params.learning_rate=0.005
```

#### Optimize Hyperparameters

Performs hyperparameter optimization using Optuna, tracking results with WandB.

```bash
poetry run prepkit experiment optimize <config_path> <config_name>
```

*   `<config_path>`: The path to your Hydra configuration directory (relative to the project root). This config should define the search space for Optuna.
*   `<config_name>`: The name of the main configuration file.

**Example:**

Assuming you have `conf/optuna_config.yaml` defining your search space:

```yaml
# conf/optuna_config.yaml
# Example for Optuna search space
params:
  learning_rate: ??? # To be optimized by Optuna
  epochs: 10
wandb:
  project: my_ml_project_optuna
  entity: your_wandb_entity
```

And an Optuna sweeper configuration (e.g., `conf/hydra/sweeper/optuna.yaml`):

```yaml
# conf/hydra/sweeper/optuna.yaml
# @package _group_
_target_: hydra_plugins.hydra_optuna_sweeper.optuna_sweeper.OptunaSweeper
optuna_create_study_args:
  direction: maximize
optuna_optimize_args:
  n_trials: 10
  timeout: 600
sampler:
  _target_: optuna.samplers.TPESampler
search_space:
  params.learning_rate:
    type: float
    low: 0.0001
    high: 0.1
    log: true
```

Run the optimization:

```bash
poetry run prepkit experiment optimize conf optuna_config hydra.sweeper.sampler.seed=42
```

## Testing

PrepKit includes a comprehensive test suite with multiple testing strategies to ensure reliability and correctness.

### Running Tests

**Run all tests:**
```bash
poetry run pytest
```

**Run specific test categories:**
```bash
# Unit tests only
poetry run pytest tests/test_cpp_preprocessor.py

# Integration tests only  
poetry run pytest tests/test_cpp_integration.py

# Build verification tests (requires g++)
poetry run pytest -m build

# Performance benchmarks
poetry run pytest --benchmark-only
```

### Test Structure

#### Unit Tests (`tests/test_cpp_preprocessor.py`)
- **4 focused tests** for core C++ preprocessor functionality
- Tests include resolution, constexpr replacement, comment removal, and minification
- **Fast execution** (~1 second) for quick development feedback

#### Integration Tests (`tests/test_cpp_integration.py`)
- **13 comprehensive tests** covering real-world scenarios
- **Snapshot testing** with regression baselines using realistic competitive programming code
- **Build verification** - Ensures preprocessed code compiles with `g++` (most critical)
- **Property-based testing** with Hypothesis for robustness validation
- **Performance benchmarks** - Validates processing speed (~730ms for typical files)

#### Test Categories
- **Snapshot Tests**: Regression testing with golden master files
- **Build Verification**: Compilation testing with multiple compiler flags
- **Property-Based**: Fuzz testing with random inputs using Hypothesis
- **Performance**: Benchmarking with `pytest-benchmark`
- **Error Handling**: Edge case and failure mode testing

### Test Dependencies

The test suite includes advanced testing libraries:

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.4"
syrupy = "^4.6.0"         # Snapshot testing
hypothesis = "^6.0.0"     # Property-based testing
pytest-xdist = "^3.0.0"   # Parallel execution
pytest-benchmark = "^4.0.0" # Performance testing
```

### Test Data

Realistic test cases include:
- **Algorithm templates**: Segment tree implementations
- **Competitive examples**: Full AtCoder/Codingame solutions
- **Include scenarios**: Multi-level header dependencies
- **Constexpr examples**: Complex constant declarations

## Plugin Architecture

PrepKit is designed with a plugin-based architecture, allowing easy extension for new programming languages or functionalities.

Plugins are discovered via Python's `entry_points` mechanism. New preprocessors or minifiers for different languages can be added by creating a Python class that inherits from `BasePreprocessor` or `BaseMinifier` (defined in `src/base_interfaces.py`) and registering it in your `pyproject.toml` under the `[tool.poetry.plugins."prepkit.preprocessors"]` or `[tool.poetry.plugins."prepkit.minifiers"]` sections.

### Current Plugin Support

**Implemented:**
- **C++**: Full preprocessor and minifier with libclang integration
  - Include resolution for local headers
  - Constexpr replacement (integer literals)
  - Comment removal and code minification
  - Build verification with g++

**Planned:**
- **Rust**: Basic preprocessor and minifier (plugin structure ready)
- **Kotlin**: Basic preprocessor and minifier (plugin structure ready)

**Example `pyproject.toml` entry for a custom plugin:**

```toml
[tool.poetry.plugins."prepkit.preprocessors"]
my_lang = "my_plugin_package.my_module:MyLangPreprocessor"

[tool.poetry.plugins."prepkit.minifiers"]
my_lang = "my_plugin_package.my_module:MyLangMinifier"
```

## Current Status & Limitations

### ✅ Fully Implemented
- **C++ Preprocessor**: Include resolution, integer constexpr replacement, comment removal
- **C++ Minifier**: Size-optimized output while preserving compilation compatibility
- **Project Scaffolding**: Boilerplate generation for AtCoder, Codingame, Kaggle
- **Comprehensive Testing**: 17 tests including build verification and performance benchmarks

### ⚠️ Known Limitations
- **Constexpr Support**: Currently limited to integer literals (no floating-point, boolean, or complex expressions)
- **String Constexpr**: String constant replacement not yet implemented
- **Rust/Kotlin Plugins**: Placeholder implementations only

### 🔮 Future Enhancements
- Extended constexpr support (floating-point, boolean, string literals)
- Full Rust and Kotlin preprocessor implementations
- Advanced optimization techniques
- Integration with more competitive programming platforms

## Development Guides

### Dogfooding During Development

PrepKit is designed to be used during its own development. See [DOGFOODING.md](DOGFOODING.md) for practical usage guidelines:

- **Real competitive programming practice integration**
- **AI assistant workflow optimization** 
- **Daily development routines**
- **Performance monitoring through actual usage**

```bash
# Use PrepKit for your own competitive programming solutions
cd src && python main.py cpp preprocess solution.cpp

# Set up AI assistants for enhanced development
poetry run python -m main ai-config setup claude-code
```

### Testing Strategy

For comprehensive testing workflows, see [TESTING.md](TESTING.md):

- **Multi-layered testing approach** (unit, integration, build verification)
- **Performance benchmarking** and regression detection
- **Test-driven development** patterns for new features
- **Continuous integration** best practices

```bash
# Run comprehensive test suite
poetry run pytest -v

# Quick development validation
poetry run pytest --tb=short -q
```

This dual approach ensures PrepKit evolves based on real-world usage while maintaining high code quality.

## Contributing

Contributions are welcome! Please refer to the development plan (`競技プログラミング支援ツール開発計画.md`) for detailed architectural decisions and future roadmap.

### Development Setup

1. **Clone the repository**
2. **Install dependencies**: `poetry install`
3. **Install system dependencies**: `libclang-18` and `clang-format`
4. **Run tests**: `poetry run pytest`
5. **Check build verification**: `poetry run pytest -m build`

### Pull Request Guidelines

- Ensure all tests pass, including build verification tests
- Add appropriate test coverage for new features
- Update documentation for user-facing changes
- Follow the existing code style and patterns