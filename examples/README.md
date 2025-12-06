# PrepKit Examples

This directory contains practical examples demonstrating PrepKit's tunable parameter system for competitive programming and heuristic contests.

## Overview

All examples showcase:
- **Tunable parameters** marked with `// @tune` comments
- **Optuna integration** for hyperparameter optimization
- **WandB tracking** for experiment management
- **Real-world patterns** from AtCoder Marathon and heuristic contests

## Examples

### 1. Beam Search (`beam_search/`)

**Problem:** Job Scheduling with Beam Search
**Tunable Parameters:**
- `BEAM_WIDTH` - Number of states to keep (10-200)
- `SEARCH_DEPTH` - Search depth (10-50)
- `RANDOMNESS` - Exploration vs exploitation (0.0-0.3)
- `GREEDY_WEIGHT` - Balance greedy and total score (0.3-1.0)

**Usage:**
```bash
cd beam_search

# Manual test with specific parameters
prepkit cpp preprocess solution.cpp \
  -D BEAM_WIDTH=100 \
  -D SEARCH_DEPTH=20 \
  -o test.cpp && g++ -std=c++17 -O2 test.cpp && ./a.out

# Automatic optimization with Optuna (100 trials)
python optimize.py --n-trials 100
```

**Expected Output:**
```
Study statistics:
  Number of finished trials:  100
  Number of pruned trials:  0
  Number of complete trials:  100

Best trial:
  Value:  245.67
  Params:
    BEAM_WIDTH: 150
    SEARCH_DEPTH: 35
    RANDOMNESS: 0.12
    GREEDY_WEIGHT: 0.75
```

### 2. WandB Sweeps (`wandb_sweeps/`)

**Integration:** Weights & Biases hyperparameter sweeps
**Features:**
- Bayesian optimization
- Early stopping with Hyperband
- Parallel sweep agents
- Visual dashboards

**Setup:**
```bash
cd wandb_sweeps

# Login to WandB
wandb login

# Initialize sweep
wandb sweep sweep_config.yaml

# Run sweep agent (use the sweep ID from above)
wandb agent <SWEEP_ID>

# Run multiple agents in parallel
wandb agent <SWEEP_ID> &
wandb agent <SWEEP_ID> &
wandb agent <SWEEP_ID> &
```

**Sweep Configuration:**
- Method: Bayesian optimization
- Metric: Minimize score
- Early termination: Hyperband
- Run cap: 100 trials

### 3. AtCoder Marathon (`atcoder_marathon/`)

**Problem:** Traveling Salesman Problem (TSP)
**Algorithm:** Simulated Annealing with 2-opt local search
**Tunable Parameters:**
- `TEMP_START` - Initial temperature (500-2000)
- `TEMP_END` - Final temperature (1-50)
- `COOLING_RATE` - Temperature decay (0.95-0.999)
- `MAX_ITERATIONS` - Iteration limit
- `ACCEPT_THRESHOLD` - Acceptance threshold

**Usage:**
```bash
cd atcoder_marathon

# Test with default parameters
prepkit cpp preprocess tsp_solver.cpp -o test.cpp
g++ -std=c++17 -O2 test.cpp && ./a.out

# Optimize with Optuna (similar to beam_search example)
# (Create optimize.py following the beam_search pattern)
```

**Pattern:** This example demonstrates a typical marathon contest solution:
1. Generate problem instance (50 random cities)
2. Initialize with nearest neighbor heuristic
3. Improve with simulated annealing
4. Output score and timing

### 4. Optuna Integration (`optuna_integration/`)

**Complete Optuna workflow** - see detailed README in that directory.

Features:
- Simulated annealing example
- Full Optuna script with TPE sampler
- WandB integration
- Results persistence

## Common Workflows

### Quick Parameter Testing

Test single parameter values:

```bash
# C++
prepkit cpp preprocess solution.cpp \
  -D TEMP_START=1500.0 \
  -D BEAM_WIDTH=100 \
  -o test.cpp

g++ -std=c++17 -O2 test.cpp && ./a.out

# Rust
prepkit rust preprocess solution.rs \
  -D TEMP_START=1500.0 \
  -D BEAM_WIDTH=100 \
  -o test.rs

rustc -C opt-level=2 test.rs && ./test
```

### Automated Optimization

All examples include `optimize.py` scripts:

```python
from plugins.cpp_plugin import CppPreprocessor
import optuna

preprocessor = CppPreprocessor()

def objective(trial):
    # Define search space
    temp_start = trial.suggest_float("TEMP_START", 500, 2000, log=True)
    beam_width = trial.suggest_int("BEAM_WIDTH", 10, 200)

    # Inject parameters
    code = preprocessor.preprocess(
        "solution.cpp", [],
        defines={
            "TEMP_START": str(temp_start),
            "BEAM_WIDTH": str(beam_width)
        }
    )

    # Compile, run, evaluate
    score = compile_and_run(code)
    return score

study = optuna.create_study(direction="minimize")
study.optimize(objective, n_trials=100)
```

### Config File Approach

Use `prepkit_config.yaml` for fixed parameters:

```yaml
cpp_preprocess:
  defines:
    TEMP_START: "1500.0"
    BEAM_WIDTH: "100"
    COOLING_RATE: "0.995"
```

Then simply:
```bash
prepkit cpp preprocess solution.cpp -o test.cpp
```

## Parameter Search Strategy

### 1. Coarse Search
Start with wide ranges, fewer trials:
```python
study.optimize(objective, n_trials=20)
```

### 2. Fine Tuning
Narrow ranges around best parameters:
```python
# From coarse search: BEAM_WIDTH=120 worked best
beam_width = trial.suggest_int("BEAM_WIDTH", 100, 140, step=5)
```

### 3. Multi-Objective
Optimize for both score and runtime:
```python
def objective(trial):
    # ...
    return score, runtime  # Tuple for multi-objective

study = optuna.create_study(
    directions=["minimize", "minimize"]
)
```

## Tips for Contest Success

### Parameter Selection
- **Start small**: Test with small problem instances first
- **Focus on critical**: Not all parameters matter equally
- **Check Optuna importance**: Use `get_param_importances()`

### Time Management
- **Quick validation**: Use small n_trials (10-20) for sanity check
- **During contest**: Run optimization in background while coding
- **Pre-contest**: Optimize on practice problems

### Debugging
```bash
# Verify preprocessing
prepkit cpp preprocess solution.cpp -D BEAM_WIDTH=100 | grep "BEAM_WIDTH"

# Should NOT find "BEAM_WIDTH" (replaced with 100)
# Should find "100" in the code
```

### Common Pitfalls
❌ **Don't** optimize on single test case
✅ **Do** use multiple test cases or average

❌ **Don't** over-tune (overfitting)
✅ **Do** validate on unseen instances

❌ **Don't** ignore compilation errors
✅ **Do** check preprocessed code compiles

## Performance Notes

Typical optimization times:
- **20 trials**: ~2-5 minutes
- **100 trials**: ~10-30 minutes
- **Parallel**: 3-4x speedup with multiple cores

Speedup tips:
- Use faster compilers: `-O2` instead of `-O3` during search
- Reduce problem size for initial search
- Use Optuna pruning for poor trials

## Integration with Contest Platforms

### AtCoder
```bash
# 1. Optimize locally
python optimize.py --n-trials 50

# 2. Use best parameters
prepkit cpp preprocess solution.cpp \
  -D TEMP_START=1234.5 \
  -D BEAM_WIDTH=87 \
  -o submit.cpp

# 3. Submit
# Copy submit.cpp to AtCoder submission box
```

### Codingame
```bash
# Optimize with size constraints
prepkit cpp preprocess solution.cpp \
  -D PARAMS... | \
prepkit cpp minify - -o submit.cpp

# Check size
wc -c submit.cpp
```

## Further Reading

- [Optuna Documentation](https://optuna.readthedocs.io/)
- [WandB Documentation](https://docs.wandb.ai/)
- [PrepKit Main README](../README.md)
- [AtCoder Marathon Guide](https://atcoder.jp/contests/intro-heuristics)

## Contributing

Have a good example? Submit a PR!
- Follow existing pattern
- Include `optimize.py` script
- Add clear documentation
- Test with real problem if possible
