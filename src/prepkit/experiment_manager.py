import click
import hydra
from omegaconf import DictConfig, OmegaConf
import optuna
from optuna.integration.wandb import WeightsAndBiasesCallback
import wandb

@click.group()
def experiment():
    """Experiment management tools."""
    pass

@experiment.command()
@click.argument('config_path')
@click.argument('config_name')
def run(config_path, config_name):
    """Runs an experiment based on a configuration file."""
    click.echo(f"Running experiment with config: {config_path}/{config_name}")

    @hydra.main(config_path=config_path, config_name=config_name, version_base=None)
    def run_experiment_hydra(cfg: DictConfig):
        click.echo(f"Hydra config: {OmegaConf.to_yaml(cfg)}")
        # Placeholder for actual experiment run logic
        click.echo("Experiment run placeholder.")

    run_experiment_hydra()

@experiment.command()
@click.argument('config_path')
@click.argument('config_name')
def optimize(config_path, config_name):
    """Optimizes hyperparameters for an experiment using Optuna and WandB."""
    click.echo(f"Optimizing hyperparameters with config: {config_path}/{config_name}")

    @hydra.main(config_path=config_path, config_name=config_name, version_base=None)
    def objective(cfg: DictConfig):
        # Initialize WandB for this trial
        wandb.init(project=cfg.wandb.project, entity=cfg.wandb.entity, config=OmegaConf.to_container(cfg, resolve=True))

        # Placeholder for actual training/evaluation logic
        metric = cfg.params.a * cfg.params.b # Example metric
        wandb.log({"metric": metric})

        wandb.finish()
        return metric

    # Create an Optuna study
    study = optuna.create_study(direction="maximize")

    # Add WandB callback for Optuna
    wandb_callback = WeightsAndBiasesCallback(metric_name="metric", as_multirun=True)

    # Run optimization
    study.optimize(objective, n_trials=10, callbacks=[wandb_callback])

    click.echo("Optimization complete.")
    click.echo(f"Best trial: {study.best_trial.value}")
    click.echo(f"Best params: {study.best_trial.params}")
