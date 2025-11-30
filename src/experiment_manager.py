import click
from typing import Any, Dict, Optional

@click.group()
def experiment() -> None:
    """Experiment management tools."""
    pass

@experiment.command()
@click.argument('config_path', type=click.Path(exists=True))
@click.argument('config_name', type=str)
def run(config_path: str, config_name: str) -> None:
    """Runs an experiment based on a configuration file."""
    import hydra
    from omegaconf import DictConfig, OmegaConf

    click.echo(f"Running experiment with config: {config_path}/{config_name}")

    @hydra.main(config_path=config_path, config_name=config_name, version_base=None)
    def run_experiment_hydra(cfg: DictConfig) -> None:
        click.echo(f"Hydra config: {OmegaConf.to_yaml(cfg)}")
        # Placeholder for actual experiment run logic
        click.echo("Experiment run placeholder.")

    run_experiment_hydra()

@experiment.command()
@click.argument('config_path', type=click.Path(exists=True))
@click.argument('config_name', type=str)
def optimize(config_path: str, config_name: str) -> None:
    """Optimizes hyperparameters for an experiment using Optuna and WandB."""
    import hydra
    from omegaconf import DictConfig, OmegaConf
    import optuna
    from optuna_integration.wandb import WeightsAndBiasesCallback
    import wandb

    click.echo(f"Optimizing hyperparameters with config: {config_path}/{config_name}")

    @hydra.main(config_path=config_path, config_name=config_name, version_base=None)
    def objective(cfg: DictConfig) -> float:
        # Initialize WandB for this trial
        # Convert OmegaConf.DictConfig to a plain dict for wandb.init
        wandb_config: Dict[str, Any] = OmegaConf.to_container(cfg, resolve=True)
        wandb.init(project=cfg.wandb.project, entity=cfg.wandb.entity, config=wandb_config)

        # Placeholder for actual training/evaluation logic
        # Ensure cfg.params.a and cfg.params.b exist and are numeric for this example
        metric: float = float(cfg.params.a) * float(cfg.params.b) # Example metric
        wandb.log({"metric": metric})

        wandb.finish()
        return metric

    # Create an Optuna study
    study: optuna.Study = optuna.create_study(direction="maximize")

    # Add WandB callback for Optuna
    wandb_callback: WeightsAndBiasesCallback = WeightsAndBiasesCallback(metric_name="metric", as_multirun=True)

    # Run optimization
    study.optimize(objective, n_trials=10, callbacks=[wandb_callback])

    click.echo("Optimization complete.")
    click.echo(f"Best trial: {study.best_trial.value}")
    click.echo(f"Best params: {study.best_trial.params}")