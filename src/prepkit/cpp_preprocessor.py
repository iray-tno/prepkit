import click
import os
import re
from collections import defaultdict, deque
import clang.cindex

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

def get_tokens_without_comments(translation_unit):
    return [t for t in translation_unit.get_tokens(extent=translation_unit.cursor.extent) if t.kind != clang.cindex.TokenKind.COMMENT]

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

        index = clang.cindex.Index.create()
        temp_file_path = "temp_combined.cpp"
        with open(temp_file_path, "w") as f:
            f.write(combined_content)

        clang_include_paths = [f'-I{path}' for path in all_include_paths]
        tu = index.parse(temp_file_path, args=clang_include_paths)

        constexpr_values = {}
        for c in tu.cursor.walk_preorder():
            if c.kind == clang.cindex.CursorKind.VAR_DECL and c.is_const_expr():
                name = c.spelling
                value = None
                for child in c.get_children():
                    if child.kind.is_literal():
                        value = next(child.get_tokens(), None)
                        if value:
                            value = value.spelling
                            break
                if value:
                    constexpr_values[name] = value

        tokens = get_tokens_without_comments(tu)
        output = ""
        for token in tokens:
            if token.kind == clang.cindex.TokenKind.IDENTIFIER and token.spelling in constexpr_values:
                output += constexpr_values[token.spelling] + " "
            else:
                output += token.spelling + " "
        
        click.echo(output)
        os.remove(temp_file_path)
    else:
        click.echo("Error: Circular dependency detected.", err=True)


@cpp.command()
@click.argument('file', type=click.Path(exists=True))
def minify(file):
    """Minifies a C++ file."""
    click.echo(f"Minifying {file}")