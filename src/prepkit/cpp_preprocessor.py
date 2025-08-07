import click
import os
import re

def resolve_includes_re(file_path, processed_files=None, include_paths=None):
    if processed_files is None:
        processed_files = set()

    # To prevent circular dependencies
    abs_file_path = os.path.abspath(file_path)
    if abs_file_path in processed_files:
        return ""
    processed_files.add(abs_file_path)

    if include_paths is None:
        include_paths = [os.path.dirname(file_path)]

    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return f"// File not found: {file_path}"

    # This regex will find #include "..."
    include_regex = re.compile(r'#include\s+"([^"]+)"')

    def replace_include(match):
        include_file = match.group(1)
        
        found = False
        for path in include_paths:
            full_path = os.path.join(path, include_file)
            if os.path.exists(full_path):
                # Prepend a comment to indicate where the code came from
                included_content = resolve_includes_re(full_path, processed_files, include_paths)
                return f"// From {include_file}\n{included_content}\n// End of {include_file}"
        
        # If not found, keep the original #include line
        return match.group(0)

    return include_regex.sub(replace_include, content)


@click.group()
def cpp():
    """C++ preprocessor and minifier."""
    pass

@cpp.command()
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
@click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True))
def preprocess(file, include_paths):
    """
    Preprocesses a C++ file by resolving #include directives.
    """
    click.echo(f"Preprocessing {file}")
    
    all_include_paths = list(include_paths)
    file_dir = os.path.dirname(file)
    if file_dir not in all_include_paths:
        all_include_paths.insert(0, file_dir)
        
    output = resolve_includes_re(file, include_paths=all_include_paths)
    click.echo(output)


@cpp.command()
@click.argument('file', type=click.Path(exists=True))
def minify(file):
    """Minifies a C++ file."""
    click.echo(f"Minifying {file}")