#!/usr/bin/env python3
"""
Example: Hyperparameter optimization with Optuna and PrepKit

This script demonstrates how to use PrepKit's tunable parameter injection
for hyperparameter optimization in competitive programming / heuristic contests.

Usage:
    python optimize.py [--n-trials 50] [--wandb]

Features:
    - Automatic parameter injection via PrepKit
    - Optuna hyperparameter optimization
    - Optional WandB experiment tracking
    - Support for both C++ and Rust solutions
"""

import sys
import os
import subprocess
import tempfile
import argparse
from pathlib import Path

# Add src to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from plugins.cpp_plugin import CppPreprocessor

try:
    import optuna
except ImportError:
    print("Error: optuna not installed. Install with: pip install optuna")
    sys.exit(1)

# Optional WandB integration
try:
    import wandb
    WANDB_AVAILABLE = True
except ImportError:
    WANDB_AVAILABLE = False


class PrepKitOptunaOptimizer:
    """Optimize competitive programming solutions using Optuna and PrepKit."""

    def __init__(self, source_file: str, use_wandb: bool = False):
        self.source_file = Path(source_file)
        self.preprocessor = CppPreprocessor()
        self.use_wandb = use_wandb and WANDB_AVAILABLE

        if self.use_wandb:
            wandb.init(project="prepkit-optimization", name=self.source_file.stem)

    def compile_and_run(self, preprocessed_code: str) -> float:
        """Compile and run the code, return the score."""
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
                return float('inf')  # Penalize compilation failures

            # Run the program
            run_result = subprocess.run(
                [str(binary_path)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if run_result.returncode != 0:
                print(f"Runtime error:\n{run_result.stderr}")
                return float('inf')

            # Parse score from output (assumes last line contains "Final score: X")
            try:
                for line in run_result.stdout.strip().split('\n'):
                    if 'Final score:' in line:
                        score = float(line.split(':')[1].strip())
                        return score
                return float('inf')  # No score found
            except (ValueError, IndexError):
                return float('inf')

    def objective(self, trial: optuna.Trial) -> float:
        """Optuna objective function."""
        # Define search space
        temp_start = trial.suggest_float("TEMP_START", 500.0, 2000.0, log=True)
        temp_end = trial.suggest_float("TEMP_END", 1.0, 50.0, log=True)
        beam_width = trial.suggest_int("BEAM_WIDTH", 20, 100)
        cooling_rate = trial.suggest_float("COOLING_RATE", 0.98, 0.999)

        # Inject parameters using PrepKit
        defines = {
            "TEMP_START": str(temp_start),
            "TEMP_END": str(temp_end),
            "BEAM_WIDTH": str(beam_width),
            "COOLING_RATE": str(cooling_rate)
        }

        try:
            preprocessed = self.preprocessor.preprocess(
                str(self.source_file),
                [],
                defines=defines
            )
        except Exception as e:
            print(f"Preprocessing error: {e}")
            return float('inf')

        # Compile and run
        score = self.compile_and_run(preprocessed)

        # Log to WandB
        if self.use_wandb:
            wandb.log({
                "score": score,
                "TEMP_START": temp_start,
                "TEMP_END": temp_end,
                "BEAM_WIDTH": beam_width,
                "COOLING_RATE": cooling_rate,
                "trial": trial.number
            })

        return score  # Optuna minimizes by default

    def optimize(self, n_trials: int = 50) -> optuna.Study:
        """Run optimization."""
        study = optuna.create_study(
            direction="minimize",
            study_name=f"prepkit-{self.source_file.stem}",
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

        return study


def main():
    parser = argparse.ArgumentParser(
        description="Optimize competitive programming solutions with Optuna and PrepKit"
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
        default=50,
        help="Number of optimization trials (default: 50)"
    )
    parser.add_argument(
        "--wandb",
        action="store_true",
        help="Enable WandB experiment tracking"
    )

    args = parser.parse_args()

    if not Path(args.solution).exists():
        print(f"Error: Solution file '{args.solution}' not found")
        sys.exit(1)

    if args.wandb and not WANDB_AVAILABLE:
        print("Warning: WandB not installed, disabling WandB tracking")
        print("Install with: pip install wandb")
        args.wandb = False

    # Run optimization
    optimizer = PrepKitOptunaOptimizer(args.solution, use_wandb=args.wandb)
    study = optimizer.optimize(n_trials=args.n_trials)

    # Optionally save results
    results_file = Path("optimization_results.json")
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
