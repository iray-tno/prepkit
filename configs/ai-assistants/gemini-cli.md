# Gemini CLI Configuration for PrepKit

## Setup

Install and configure Gemini CLI:
```bash
pip install google-generativeai
export GOOGLE_API_KEY="your-api-key"
```

## Custom Commands for Competitive Programming

Create shell aliases for common tasks:

```bash
# ~/.bashrc or ~/.zshrc
alias gem-analyze='gemini-cli "Analyze this competitive programming code for correctness and efficiency:"'
alias gem-optimize='gemini-cli "Optimize this C++ code for competitive programming, focusing on performance:"'
alias gem-debug='gemini-cli "Debug this competitive programming solution. Check for common issues:"'
alias gem-explain='gemini-cli "Explain this algorithm step by step for competitive programming:"'
```

## Prompt Templates

### Code Analysis Template
```bash
#!/bin/bash
# gem-analyze-cp.sh - Analyze competitive programming code

if [ $# -ne 1 ]; then
    echo "Usage: $0 <cpp_file>"
    exit 1
fi

gemini-cli "
As an expert in competitive programming, analyze this C++ code:

$(cat $1)

Please check:
1. Algorithm correctness and complexity
2. Edge cases and boundary conditions  
3. Input/output format correctness
4. Potential optimization opportunities
5. PrepKit preprocessing compatibility (constexpr usage, include patterns)

Provide specific improvements and explain your reasoning.
"
```

### Test Case Generation
```bash
#!/bin/bash
# gem-testcases.sh - Generate test cases

gemini-cli "
Generate comprehensive test cases for this competitive programming problem:

$(cat problem_statement.txt)

Include:
- Sample input/output from problem statement
- Edge cases (minimum/maximum constraints)
- Corner cases (empty input, single elements)
- Stress test cases (large inputs)
- Expected algorithmic behavior verification

Format as:
INPUT:
[test case]
EXPECTED OUTPUT:
[expected result]
"
```

### Algorithm Template Generation
```bash
#!/bin/bash
# gem-template.sh - Generate algorithm template

ALGORITHM=$1
shift
CONSTRAINTS="$@"

gemini-cli "
Generate a C++ competitive programming template for: $ALGORITHM

Constraints: $CONSTRAINTS

Requirements:
- Optimized for competitive programming
- Include necessary headers and using namespace std
- Use constexpr for constants that won't change
- Add comments explaining key parts
- Include main() function with fast I/O setup
- Make it compatible with PrepKit preprocessing (single-file output)

Template should be production-ready for contests.
"
```

## Integration Scripts

### Preprocessing Analysis
```bash
#!/bin/bash  
# gem-preprocess.sh - Analyze preprocessing results

ORIGINAL=$1
PREPROCESSED=$2

gemini-cli "
Compare these two C++ files - original vs preprocessed by PrepKit:

ORIGINAL:
$(cat $ORIGINAL)

PREPROCESSED: 
$(cat $PREPROCESSED)

Analyze:
1. What transformations were applied?
2. Are there any issues with the preprocessing?
3. Is the functionality preserved?
4. Can the code be further optimized?
5. Any potential runtime issues?
"
```

### Experiment Analysis
```bash
#!/bin/bash
# gem-experiment.sh - Analyze ML experiment results

gemini-cli "
Analyze this machine learning experiment configuration and results:

CONFIG:
$(cat conf/config.yaml)

WANDB LOGS:
$(cat experiment_logs.txt)

Please provide:
1. Hyperparameter optimization suggestions
2. Potential overfitting/underfitting issues
3. Recommendations for next experiments
4. Kaggle submission strategy based on validation scores
"
```

## VS Code Integration

Create `.vscode/tasks.json`:
```json
{
    "version": "2.0.0", 
    "tasks": [
        {
            "label": "Gemini Analyze Code",
            "type": "shell",
            "command": "gem-analyze",
            "args": ["${file}"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always"
            }
        },
        {
            "label": "Gemini Generate Tests", 
            "type": "shell",
            "command": "gem-testcases.sh",
            "group": "test"
        },
        {
            "label": "Gemini Optimize Code",
            "type": "shell", 
            "command": "gem-optimize",
            "args": ["${file}"]
        }
    ]
}
```

## Batch Processing Scripts

### Contest Preparation
```bash
#!/bin/bash
# contest-prep.sh - Prepare for contest with Gemini analysis

echo "Analyzing contest problems with Gemini..."

for problem in problems/*.cpp; do
    echo "=== Analyzing $(basename $problem) ==="
    gem-analyze $problem > analyses/$(basename $problem .cpp)_analysis.txt
    
    echo "Generating test cases..."
    gem-testcases.sh < problems/$(basename $problem .cpp)_statement.txt > tests/$(basename $problem .cpp)_tests.txt
done

echo "Contest preparation complete! Check analyses/ and tests/ directories."
```

### Experiment Review
```bash
#!/bin/bash
# review-experiments.sh - Review recent experiments

echo "Analyzing recent experiments..."

for run_dir in wandb/latest-run/files/; do
    if [ -f "$run_dir/config.yaml" ]; then
        echo "=== Reviewing $(basename $run_dir) ==="
        gem-experiment.sh $run_dir > reviews/$(basename $run_dir)_review.txt
    fi
done
```

## Best Practices

1. **Context Setting**: Always provide problem constraints and requirements
2. **Iterative Refinement**: Use follow-up prompts to drill down on specific issues
3. **Code Validation**: Cross-check Gemini suggestions with actual testing
4. **Performance Focus**: Emphasize competitive programming performance requirements
5. **Integration**: Combine with PrepKit tools for complete workflow automation

## Performance Tips

- Use specific, detailed prompts for better results
- Include problem constraints and time limits
- Reference competitive programming best practices
- Validate suggestions through testing
- Save effective prompts as templates for reuse