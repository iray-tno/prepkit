# Claude Code Configuration for Competitive Programming

## Context Prompts

Use these prompts to provide Claude Code with optimal context for competitive programming tasks:

### Initial Setup Prompt

```
I'm working on competitive programming problems using PrepKit, a Python tool for C++ preprocessing, Kaggle automation, and experiment management. The project structure:

- `src/`: Main source code with plugins (cpp_plugin.py, kaggle_automation.py, experiment_manager.py)
- `tests/`: Comprehensive test suite including integration tests and benchmarks  
- `configs/`: Project templates and boilerplate configurations
- Key features: C++ include resolution, constexpr replacement, code minification, WandB integration

When helping with competitive programming:
- Focus on performance and memory efficiency
- Use standard algorithms and data structures
- Ensure single-file output compatibility
- Consider constexpr optimizations for constants
```

### Code Review Prompt

```
Please review this competitive programming solution with focus on:
1. Algorithm correctness and edge cases
2. Time/space complexity analysis
3. Opportunities for constexpr optimization
4. PrepKit compatibility (include patterns, constexpr usage)
5. Potential for code minification improvements
```

### Debugging Prompt

```
Help debug this competitive programming code. Check for:
- Off-by-one errors and boundary conditions
- Integer overflow issues
- Input/output format mismatches
- Algorithm implementation bugs
- Preprocessing compatibility issues
```

## Quick Actions

### Generate Boilerplate
Use Copilot with tab completion for:
- `prepkit_cpp_template` → Full AtCoder template
- `prepkit_contest` → Contest-specific setup
- `prepkit_debug` → Debug utilities

### Common Code Patterns

Claude Code understands these competitive programming patterns:
- Segment trees, Fenwick trees
- Graph algorithms (DFS, BFS, shortest path)
- Dynamic programming templates
- Modular arithmetic utilities
- Fast I/O optimizations

## Project Management

### Suggested Claude Code Commands
```bash
# Analyze preprocessing efficiency
claude-code analyze cpp-preprocessing --performance

# Review test coverage
claude-code test --coverage --focus=integration

# Optimize for specific platform
claude-code optimize --platform=codingame --size-limit=100kb
```

## Best Practices

1. **Preprocessing Context**: Always mention if code will be preprocessed
2. **Platform Constraints**: Specify target platform (AtCoder/Codingame/Kaggle)
3. **Performance Goals**: State time/memory requirements upfront
4. **Testing Strategy**: Include edge cases and large input scenarios