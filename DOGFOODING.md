# PrepKit Dogfooding Guide

This guide shows how to use PrepKit during its own development to ensure it works well in practice.

## Quick Start Dogfooding

### 1. Daily Development Validation

```bash
# Run the full test suite
poetry run pytest -v

# Quick smoke test
poetry run pytest tests/test_cpp_preprocessor.py -q

# Performance check
poetry run pytest --benchmark-only
```

### 2. Manual CLI Testing

```bash
# Test C++ preprocessing (from src directory)
cd src
echo '#include <iostream>
constexpr int MOD = 1000000007;
int main() { std::cout << MOD << std::endl; return 0; }' > test.cpp

python main.py cpp preprocess test.cpp
python main.py cpp minify test.cpp
```

### 3. AI Assistant Integration Testing

```bash
# Set up AI assistants for better development experience
poetry run python -m main ai-config setup claude-code
poetry run python -m main ai-config status

# Use the generated prompts during coding sessions
cat .prepkit/claude-code/setup.md
```

### 4. Real Competitive Programming Practice

Create competitive programming solutions using PrepKit:

```cpp
// practice_solution.cpp
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

constexpr int MOD = 1000000007;
constexpr int MAXN = 200005;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    cin >> n;
    vector<int> a(n);
    
    for (int i = 0; i < n; i++) {
        cin >> a[i];
    }
    
    // Your solution here
    
    return 0;
}
```

Then process with PrepKit:
```bash
cd src
python main.py cpp preprocess practice_solution.cpp
g++ -o solution <(python main.py cpp preprocess practice_solution.cpp)
./solution < input.txt
```

### 5. WandB Integration Testing

If you have WandB set up:

```bash
# Test experiment tracking (requires wandb login)
cd src
python main.py kaggle submit-competition submission.csv --competition test --log-wandb
```

## Development Workflow Integration

### Morning Routine
```bash
# 1. Check test health
poetry run pytest --tb=short -q

# 2. Verify AI assistant configs
poetry run python -m main ai-config status

# 3. Quick preprocessing test with new changes
cd src && python main.py cpp preprocess --help
```

### During Feature Development
```bash
# Test new features as you build them
poetry run pytest tests/test_cpp_preprocessor.py::test_cpp_preprocess_float_constexpr -v

# Use PrepKit for the code you're writing
python main.py cpp preprocess your_test_file.cpp -I ./includes
```

### Before Committing
```bash
# Full validation
poetry run pytest
git add -A && git commit -m "your message"
```

## Practical Tips

### 1. Use PrepKit for Contest Participation
- Set up contest directories with `project new` (when implemented)
- Process solutions through the preprocessing pipeline
- Test minification for size-constrained contests

### 2. Monitor Performance
- Track preprocessing times with the benchmark tests
- Test with increasingly complex solutions
- Profile memory usage on large codebases

### 3. AI Assistant Integration
- Use Claude Code with the PrepKit context prompts
- Test Copilot snippets during actual development
- Validate Gemini CLI scripts with real problems

### 4. Edge Case Discovery
- Test with unusual C++ constructs
- Try complex include hierarchies
- Test constexpr with edge cases

## Quality Metrics to Track

- **Build Success Rate**: Percentage of preprocessed files that compile
- **Processing Time**: Time to preprocess typical contest solutions  
- **Minification Ratio**: Code size reduction achieved
- **AI Assistant Effectiveness**: Usefulness of generated suggestions

## Common Issues and Solutions

### Import Errors in CLI
```bash
# Run from src directory for development
cd src
python main.py <command>

# Or install in development mode
pip install -e .
```

### Missing Dependencies
```bash
# Install all dependencies
poetry install

# Install system dependencies (Ubuntu/Debian)
sudo apt-get install libclang-18 clang-format g++
```

### Test Failures
```bash
# Update snapshots when constexpr behavior changes
poetry run pytest --snapshot-update

# Run specific test categories
poetry run pytest -m build  # Build verification tests
```

## Success Indicators

You know dogfooding is working when:
- ✅ You naturally reach for PrepKit during competitive programming
- ✅ Processing is fast enough not to interrupt your flow
- ✅ Generated code compiles and runs correctly
- ✅ AI assistants provide helpful, context-aware suggestions
- ✅ You discover edge cases through real usage

## Feedback Loop

Track what works and what doesn't:
- Keep notes on preprocessing failures
- Document AI assistant suggestion quality
- Monitor your own workflow efficiency improvements
- Report issues you discover through dogfooding

This dogfooding approach ensures PrepKit evolves to be genuinely useful for competitive programming and ML workflows.