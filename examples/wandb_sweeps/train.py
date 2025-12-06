#!/usr/bin/env python3
"""
WandB Sweeps Integration for PrepKit

This script demonstrates how to use WandB sweeps with PrepKit's
tunable parameter system for hyperparameter optimization.

Usage:
    # Initialize sweep
    wandb sweep sweep_config.yaml

    # Run sweep agent (copy the sweep ID from above)
    wandb agent <SWEEP_ID>
"""

import sys
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from plugins.cpp_plugin import CppPreprocessor

try:
    import wandb
except ImportError:
    print("Error: wandb not installed")
    print("Install with: pip install wandb")
    sys.exit(1)


def compile_and_run(preprocessed_code: str) -> dict:
    """Compile and run the solution, return metrics."""
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
            return {"score": float('inf'), "status": "compile_error"}

        # Run
        run_result = subprocess.run(
            [str(binary_path)],
            capture_output=True,
            text=True,
            timeout=10
        )

        if run_result.returncode != 0:
            return {"score": float('inf'), "status": "runtime_error"}

        # Parse output
        try:
            metrics = {}
            for line in run_result.stdout.strip().split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    try:
                        metrics[key.strip().lower()] = float(value.strip())
                    except ValueError:
                        pass

            return {
                "score": metrics.get("score", float('inf')),
                "makespan": metrics.get("makespan", 0),
                "status": "success"
            }
        except Exception:
            return {"score": float('inf'), "status": "parse_error"}


def train():
    """Training function called by WandB sweep agent."""
    # Initialize WandB
    wandb.init()

    # Get parameters from WandB config
    config = wandb.config

    # Prepare defines for PrepKit
    defines = {
        "BEAM_WIDTH": str(config.BEAM_WIDTH),
        "SEARCH_DEPTH": str(config.SEARCH_DEPTH),
        "RANDOMNESS": str(config.RANDOMNESS),
        "GREEDY_WEIGHT": str(config.GREEDY_WEIGHT)
    }

    # Add optional parameters if present
    if hasattr(config, 'TEMP_START'):
        defines["TEMP_START"] = str(config.TEMP_START)
    if hasattr(config, 'TEMP_END'):
        defines["TEMP_END"] = str(config.TEMP_END)
    if hasattr(config, 'COOLING_RATE'):
        defines["COOLING_RATE"] = str(config.COOLING_RATE)

    # Preprocess solution
    preprocessor = CppPreprocessor()
    solution_file = Path("../beam_search/solution.cpp")  # Adjust path as needed

    if not solution_file.exists():
        print(f"Error: {solution_file} not found")
        wandb.log({"score": float('inf'), "status": "file_not_found"})
        return

    try:
        preprocessed = preprocessor.preprocess(
            str(solution_file), [], defines=defines
        )
    except Exception as e:
        print(f"Preprocessing error: {e}")
        wandb.log({"score": float('inf'), "status": "preprocess_error"})
        return

    # Compile and run
    metrics = compile_and_run(preprocessed)

    # Log metrics to WandB
    wandb.log(metrics)

    # Log summary
    wandb.summary["best_score"] = metrics["score"]
    wandb.summary["status"] = metrics["status"]


if __name__ == "__main__":
    train()
