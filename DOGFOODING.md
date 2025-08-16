# PrepKit Dogfooding Guide

This guide shows how to use PrepKit during its own development to ensure it works well in practice. Focus is on **actual usage** rather than testing (see [TESTING.md](TESTING.md) for testing workflows).

## Quick Start Dogfooding

### 1. Manual CLI Testing

```bash
# Test C++ preprocessing (from src directory)
cd src
echo '#include <iostream>
constexpr int MOD = 1000000007;
int main() { std::cout << MOD << std::endl; return 0; }' > test.cpp

python main.py cpp preprocess test.cpp
python main.py cpp minify test.cpp
```

### 2. AI Assistant Integration

```bash
# Set up AI assistants for better development experience
poetry run python -m main ai-config setup claude-code
poetry run python -m main ai-config status

# Use the generated prompts during coding sessions
cat .prepkit/claude-code/setup.md
```

### 3. Real Competitive Programming Practice

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

### 4. WandB Integration Testing

If you have WandB set up:

```bash
# Test experiment tracking (requires wandb login)
cd src
python main.py kaggle submit-competition submission.csv --competition test --log-wandb
```

## Development Workflow Integration

### Morning Routine
```bash
# 1. Verify AI assistant configs
poetry run python -m main ai-config status

# 2. Quick preprocessing test with new changes
cd src && python main.py cpp preprocess --help
```

### During Feature Development
```bash
# Use PrepKit for the code you're writing
cd src && python main.py cpp preprocess your_test_file.cpp -I ./includes

# Try new features with real competitive programming solutions
python main.py cpp minify complex_solution.cpp
```

### Before Committing
```bash
# Quick manual validation with real usage
cd src && python main.py cpp preprocess sample_solution.cpp
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

- **Processing Time**: Time to preprocess typical contest solutions  
- **Minification Ratio**: Code size reduction achieved
- **AI Assistant Effectiveness**: Usefulness of generated suggestions
- **Workflow Integration**: How naturally PrepKit fits into your coding practice

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

### Preprocessing Issues
```bash
# Check output manually
cd src && python main.py cpp preprocess problematic_file.cpp

# Verify compilation manually
g++ -o test_solution <(python main.py cpp preprocess solution.cpp)
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