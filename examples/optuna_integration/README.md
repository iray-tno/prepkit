# Optuna Integration Example

This example demonstrates how to use PrepKit's tunable parameter injection feature for hyperparameter optimization in competitive programming and heuristic contests.

## Overview

PrepKit allows you to mark parameters with `// @tune` comments and automatically inject different values during preprocessing. This is perfect for:

- **Heuristic contests** (AtCoder Marathon, CodinGame Optimization)
- **Simulated annealing** parameter tuning
- **Beam search** optimization
- **Machine learning** hyperparameter search

## Files

- `solution.cpp` - Example C++ solution with tunable parameters
- `optimize.py` - Optuna optimization script using PrepKit
- `README.md` - This file

## Setup

Install dependencies:

```bash
# Required
pip install optuna

# Optional (for experiment tracking)
pip install wandb
```

## Usage

### Basic Optimization

Run 50 optimization trials:

```bash
python optimize.py --n-trials 50
```

### With WandB Tracking

Track experiments in Weights & Biases:

```bash
# Login to WandB first
wandb login

# Run with tracking enabled
python optimize.py --n-trials 100 --wandb
```

### Custom Solution File

Optimize your own solution:

```bash
python optimize.py my_solution.cpp --n-trials 30
```

## How It Works

### 1. Mark Tunable Parameters

In your C++ source code, mark parameters you want to optimize with `// @tune`:

```cpp
constexpr double TEMP_START = 1000.0;    // @tune
constexpr double TEMP_END = 10.0;        // @tune
constexpr int BEAM_WIDTH = 50;           // @tune
constexpr double COOLING_RATE = 0.995;   // @tune

// Fixed parameters (not marked) won't be changed
constexpr int MAX_ITERATIONS = 1000;
```

### 2. Define Search Space

In `optimize.py`, define the search space for each parameter:

```python
def objective(self, trial: optuna.Trial) -> float:
    # Optuna suggests values from search space
    temp_start = trial.suggest_float("TEMP_START", 500.0, 2000.0, log=True)
    temp_end = trial.suggest_float("TEMP_END", 1.0, 50.0, log=True)
    beam_width = trial.suggest_int("BEAM_WIDTH", 20, 100)
    cooling_rate = trial.suggest_float("COOLING_RATE", 0.98, 0.999)

    # PrepKit injects these values into the source code
    defines = {
        "TEMP_START": str(temp_start),
        "TEMP_END": str(temp_end),
        "BEAM_WIDTH": str(beam_width),
        "COOLING_RATE": str(cooling_rate)
    }

    preprocessed = self.preprocessor.preprocess(
        str(self.source_file), [], defines=defines
    )
```

### 3. Run & Evaluate

The script:
1. Injects trial parameters using PrepKit
2. Compiles the preprocessed code with g++
3. Runs the binary and extracts the score
4. Optuna learns and suggests better parameters
5. Results are saved to `optimization_results.json`

## Example Output

```
[I 2024-12-06 10:00:00,000] A new study created in memory with name: prepkit-solution
[I 2024-12-06 10:00:01,234] Trial 0 finished with value: 1250.5 and parameters: {'TEMP_START': 1200.0, 'TEMP_END': 15.0, 'BEAM_WIDTH': 45, 'COOLING_RATE': 0.99}
[I 2024-12-06 10:00:02,456] Trial 1 finished with value: 980.3 and parameters: {'TEMP_START': 850.0, 'TEMP_END': 8.5, 'BEAM_WIDTH': 60, 'COOLING_RATE': 0.985}
...
[I 2024-12-06 10:10:00,000] Trial 49 finished with value: 520.1 and parameters: {'TEMP_START': 1450.0, 'TEMP_END': 5.2, 'BEAM_WIDTH': 75, 'COOLING_RATE': 0.992}

============================================================
Optimization Results
============================================================
Best score: 520.12
Best parameters:
  TEMP_START: 1450.3
  TEMP_END: 5.18
  BEAM_WIDTH: 75
  COOLING_RATE: 0.9921
============================================================

Results saved to: optimization_results.json
```

## Adapting for Your Problem

### 1. Update `solution.cpp`

Replace the scoring logic with your actual problem:

```cpp
double evaluate_solution(const std::vector<int>& solution) {
    // Replace with your problem's scoring function
    // Return value to minimize (lower = better)
    return your_score;
}
```

### 2. Update Score Extraction

Modify `compile_and_run()` to parse your program's output:

```python
# Parse score from output
try:
    for line in run_result.stdout.strip().split('\n'):
        if 'Final score:' in line:  # Adjust this pattern
            score = float(line.split(':')[1].strip())
            return score
```

### 3. Add Input Files (if needed)

If your solution reads from stdin:

```python
# In compile_and_run():
with open('input.txt') as f:
    run_result = subprocess.run(
        [str(binary_path)],
        stdin=f,
        capture_output=True,
        text=True,
        timeout=5
    )
```

## Rust Support

PrepKit also supports Rust! Just use `.rs` files:

```rust
const TEMP_START: f64 = 1000.0;  // @tune
const BEAM_WIDTH: i32 = 50;      // @tune
```

And update `optimize.py` to use `RustPreprocessor`:

```python
from plugins.rust_plugin import RustPreprocessor

class PrepKitOptunaOptimizer:
    def __init__(self, source_file: str, use_wandb: bool = False):
        self.preprocessor = RustPreprocessor()  # Use Rust preprocessor
        # ... rest of the code
```

## Advanced Features

### Multiple Test Cases

Run each trial against multiple test inputs and average scores:

```python
def objective(self, trial: optuna.Trial) -> float:
    # ... inject parameters ...

    total_score = 0
    for test_file in ["input1.txt", "input2.txt", "input3.txt"]:
        score = self.compile_and_run(preprocessed, input_file=test_file)
        total_score += score

    return total_score / 3  # Average score
```

### Pruning

Enable early stopping of unpromising trials:

```python
study = optuna.create_study(
    direction="minimize",
    pruner=optuna.pruners.MedianPruner()  # Add pruner
)
```

### Parallel Optimization

Run trials in parallel:

```python
study.optimize(self.objective, n_trials=100, n_jobs=4)  # 4 parallel workers
```

## Tips

1. **Start with wide ranges** - Let Optuna explore the space
2. **Use log scale** for parameters spanning orders of magnitude
3. **Monitor WandB** - Visualize parameter importance and correlations
4. **Save best config** - Use the best parameters in your final submission
5. **Test locally first** - Verify your scoring function works correctly

## References

- [Optuna Documentation](https://optuna.readthedocs.io/)
- [WandB Documentation](https://docs.wandb.ai/)
- [PrepKit Documentation](../../README.md)
