"""Rust preprocessing and minification commands."""
import click
from plugins.rust_plugin import RustPreprocessor, RustMinifier
from config import load_config


@click.group(name="rust")
def rust_group():
    """Rust preprocessor and minifier."""
    pass


@rust_group.command(name="preprocess")
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
@click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True), help='Include paths (can be specified multiple times)')
@click.option('-D', '--define', 'defines', multiple=True, help='Define tunable parameter (format: NAME=VALUE, can be specified multiple times)')
@click.option('-o', '--output', 'output_file', type=click.Path(), help='Output file (default: stdout)')
def rust_preprocess_cmd(file, include_paths, defines, output_file):
    """Preprocess Rust code: flatten modules and optionally inject tunable parameters."""
    # Load config and merge with CLI options (CLI takes precedence)
    config = load_config()
    config_include_paths = config.get("rust_preprocess", {}).get("include_paths", [])
    config_defines = config.get("rust_preprocess", {}).get("defines", {})

    # CLI flags override config: start with config paths, then add CLI paths
    all_include_paths = list(config_include_paths) + list(include_paths)

    # Parse CLI defines (format: NAME=VALUE)
    defines_dict = dict(config_defines)  # Start with config defines
    for define in defines:
        if '=' in define:
            name, value = define.split('=', 1)
            defines_dict[name] = value
        else:
            click.echo(f"Warning: Invalid define format '{define}', expected NAME=VALUE", err=True)

    if config_include_paths:
        click.echo(f"Using include paths from config: {', '.join(config_include_paths)}")

    rust_preprocessor_instance = RustPreprocessor()
    result = rust_preprocessor_instance.preprocess(file, all_include_paths, defines=defines_dict if defines_dict else None)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(result)
        click.echo(f"✓ Preprocessed output written to: {output_file}")
    else:
        click.echo(result)


@rust_group.command(name="minify")
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
@click.option('-o', '--output', 'output_file', type=click.Path(), help='Output file (default: stdout)')
def rust_minify_cmd(file, output_file):
    """Minify Rust code by removing comments and excess whitespace."""
    rust_minifier_instance = RustMinifier()
    result = rust_minifier_instance.minify(file)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(result)
        click.echo(f"✓ Minified output written to: {output_file}")
    else:
        click.echo(result)
