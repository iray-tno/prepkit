import click
import os
import re
from collections import defaultdict, deque
import clang.cindex
import subprocess

def build_dependency_graph(files, include_paths):
    graph = defaultdict(list)
    in_degree = defaultdict(int)
    
    include_regex = re.compile(r'#include\s+"([^"]+)"')

    for file_path in files:
        if not os.path.exists(file_path):
            continue

        with open(file_path, 'r') as f:
            content = f.read()

        for match in include_regex.finditer(content):
            include_file = match.group(1)
            found = False
            for path in include_paths:
                full_path = os.path.abspath(os.path.join(path, include_file))
                if os.path.exists(full_path):
                    graph[full_path].append(os.path.abspath(file_path))
                    in_degree[os.path.abspath(file_path)] += 1
                    found = True
                    break
            if not found:
                click.echo(f"Warning: Could not find include file {include_file} in {file_path}", err=True)

    return graph, in_degree

def topological_sort(graph, in_degree, all_files):
    queue = deque([f for f in all_files if in_degree[os.path.abspath(f)] == 0])
    sorted_order = []

    while queue:
        node = queue.popleft()
        sorted_order.append(node)

        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_order) == len(all_files):
        return sorted_order
    else:
        return None

# Removed get_tokens_without_comments as it will no longer be used for output generation

@click.group()
def cpp():
    """C++ preprocessor and minifier."""
    pass

@cpp.command()
@click.argument('file', type=click.Path(exists=True, resolve_path=True))
@click.option('-I', '--include-path', 'include_paths', multiple=True, type=click.Path(exists=True, file_okay=False, resolve_path=True))
def preprocess(file, include_paths):
    """
    Preprocesses a C++ file using topological sort, handling includes, constexpr, and comments.
    """
    click.echo(f"Preprocessing {file}")
    
    all_include_paths = list(include_paths)
    file_dir = os.path.dirname(file)
    if file_dir not in all_include_paths:
        all_include_paths.insert(0, file_dir)

    all_files = {os.path.abspath(file)}
    include_regex = re.compile(r'#include\s+"([^"]+)"')
    files_to_scan = [file]

    while files_to_scan:
        current_file = files_to_scan.pop(0)
        with open(current_file, 'r') as f:
            content = f.read()
        
        for match in include_regex.finditer(content):
            include_file = match.group(1)
            for path in all_include_paths:
                full_path = os.path.abspath(os.path.join(path, include_file))
                if os.path.exists(full_path) and full_path not in all_files:
                    all_files.add(full_path)
                    files_to_scan.append(full_path)

    graph, in_degree = build_dependency_graph(list(all_files), all_include_paths)
    sorted_files = topological_sort(graph, in_degree, list(all_files))

    if sorted_files:
        combined_content = ""
        for f in sorted_files:
            with open(f, 'r') as source_file:
                source_content = source_file.read()
                source_content = include_regex.sub("", source_content)
                combined_content += source_content

        temp_file_path = "temp_combined.cpp"
        with open(temp_file_path, "w") as f:
            f.write(combined_content)

        # First clang-format pass for initial formatting
        subprocess.run(['clang-format', '-i', temp_file_path])
        
        with open(temp_file_path, "r") as f:
            formatted_content = f.read()

        clang.cindex.Config.set_library_file("/lib/x86_64-linux-gnu/libclang-18.so.18")
        index = clang.cindex.Index.create()
        clang_include_paths = [f'-I{path}' for path in all_include_paths]
        tu = index.parse(temp_file_path, args=clang_include_paths, unsaved_files=[(temp_file_path, formatted_content)])

        # Collect constexpr values
        constexpr_values = {}
        for c in tu.cursor.walk_preorder():
            if c.kind == clang.cindex.CursorKind.VAR_DECL:
                tokens = {t.spelling for t in c.get_tokens()}
                if 'constexpr' in tokens:
                    name = c.spelling
                    value = None
                    literal_kinds = [clang.cindex.CursorKind.INTEGER_LITERAL, clang.cindex.CursorKind.FLOATING_LITERAL, clang.cindex.CursorKind.IMAGINARY_LITERAL, clang.cindex.CursorKind.STRING_LITERAL, clang.cindex.CursorKind.CHARACTER_LITERAL]
                    for child in c.get_children():
                        if child.kind in literal_kinds:
                            value = next(child.get_tokens(), None)
                            if value:
                                value = value.spelling
                                break
                    if value:
                        constexpr_values[name] = value

        # Perform text-based constexpr replacement
        processed_content = formatted_content
        for name, value in constexpr_values.items():
            processed_content = re.sub(r'\b' + re.escape(name) + r'\b', value, processed_content)

        # Remove comments using regex
        processed_content = re.sub(r'//.*\n', '\n', processed_content)  # Single-line comments
        processed_content = re.sub(r'/\*.*?\*/', '', processed_content, flags=re.DOTALL)  # Multi-line comments

        # Final clang-format pass
        with open(temp_file_path, "w") as f:
            f.write(processed_content)

        subprocess.run(['clang-format', '-i', temp_file_path])

        with open(temp_file_path, "r") as f:
            final_output = f.read()

        click.echo(final_output)
        os.remove(temp_file_path)
    else:
        click.echo("Error: Circular dependency detected.", err=True)


@cpp.command()
@click.argument('file', type=click.Path(exists=True))
def minify(file):
    """Minifies a C++ file."""
    click.echo(f"Minifying {file}")
