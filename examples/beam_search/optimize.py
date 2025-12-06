#!/usr/bin/env python3
"""
Beam Search Hyperparameter Optimization Example

This script demonstrates how to optimize beam search parameters
for a job scheduling problem using Optuna and PrepKit.

The parameters being tuned:
- BEAM_WIDTH: Number of states to keep at each level
- SEARCH_DEPTH: How deep to search
- RANDOMNESS: Probability of skipping greedy choices
- GREEDY_WEIGHT: Balance between greedy and total score
"""

import sys
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from plugins.cpp_plugin import CppPreprocessor

try:
    import optuna
except ImportError:
    print("Error: optuna not installed")
    print("Install with: pip install optuna")
    sys.exit(1)


class BeamSearchOptimizer:
    def __init__(self, source_file: str):
        self.source_file = Path(source_file)
        self.preprocessor = CppPreprocessor()

    def compile_and_run(self, preprocessed_code: str) -> float:
        """Compile and run the code, return the score (lower is better)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write preprocessed code
            source_path = Path(tmpdir) / "solution.cpp"
            source_path.write_text(preprocessed_code)

            # Compile
            binary_path = Path(tmpdir) / "solution"
            compile_result = subprocess.run(
                ["g++", "-std=c++17", "-O2", "-o", str(binary_path), str(source_path)],
                capture_output=True,
                text=True
            )

            if compile_result.returncode != 0:
                print(f"Compilation error:\n{compile_result.stderr}")
                return float('inf')

            # Run
            run_result = subprocess.run(
                [str(binary_path)],
                capture_output=True,
                text=True,
                timeout=10
            )

            if run_result.returncode != 0:
                print(f"Runtime error:\n{run_result.stderr}")
                return float('inf')

            # Parse score from output
            try:
                for line in run_result.stdout.strip().split('\n'):
                    if 'Score:' in line:
                        score = float(line.split(':')[1].strip())
                        return score
                return float('inf')
            except (ValueError, IndexError):
                return float('inf')

    def objective(self, trial: optuna.Trial) -> float:
        """Optuna objective function."""
        # Define search space
        beam_width = trial.suggest_int("BEAM_WIDTH", 10, 200, step=10)
        search_depth = trial.suggest_int("SEARCH_DEPTH", 10, 50)
        randomness = trial.suggest_float("RANDOMNESS", 0.0, 0.3)
        greedy_weight = trial.suggest_float("GREEDY_WEIGHT", 0.3, 1.0)

        # Inject parameters
        defines = {
            "BEAM_WIDTH": str(beam_width),
            "SEARCH_DEPTH": str(search_depth),
            "RANDOMNESS": str(randomness),
            "GREEDY_WEIGHT": str(greedy_weight)
        }

        try:
            preprocessed = self.preprocessor.preprocess(
                str(self.source_file), [], defines=defines
            )
        except Exception as e:
            print(f"Preprocessing error: {e}")
            return float('inf')

        # Compile and run
        score = self.compile_and_run(preprocessed)

        # Report intermediate values
        trial.report(score, step=0)

        return score  # Optuna minimizes by default

    def optimize(self, n_trials: int = 100) -> optuna.Study:
        """Run optimization."""
        study = optuna.create_study(
            direction="minimize",
            study_name="beam-search-scheduling",
            sampler=optuna.samplers.TPESampler(seed=42)
        )

        study.optimize(self.objective, n_trials=n_trials, show_progress_bar=True)

        print("\n" + "="*60)
        print("Optimization Results")
        print("="*60)
        print(f"Best score: {study.best_value:.2f}")
        print(f"Best parameters:")
        for key, value in study.best_params.items():
            print(f"  {key}: {value}")
        print("="*60)

        # Show parameter importance
        try:
            importance = optuna.importance.get_param_importances(study)
            print("\nParameter Importance:")
            for key, value in sorted(importance.items(), key=lambda x: x[1], reverse=True):
                print(f"  {key}: {value:.3f}")
        except Exception:
            pass

        return study


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Optimize beam search parameters with Optuna"
    )
    parser.add_argument(
        "solution",
        nargs="?",
        default="solution.cpp",
        help="Path to solution file (default: solution.cpp)"
    )
    parser.add_argument(
        "--n-trials",
        type=int,
        default=100,
        help="Number of optimization trials (default: 100)"
    )

    args = parser.parse_args()

    if not Path(args.solution).exists():
        print(f"Error: Solution file '{args.solution}' not found")
        sys.exit(1)

    # Run optimization
    optimizer = BeamSearchOptimizer(args.solution)
    study = optimizer.optimize(n_trials=args.n_trials)

    # Save results
    results_file = Path("beam_search_results.json")
    import json
    with open(results_file, 'w') as f:
        json.dump({
            "best_score": study.best_value,
            "best_params": study.best_params,
            "n_trials": len(study.trials)
        }, f, indent=2)

    print(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()
