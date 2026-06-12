# Antigravity CLI Configuration for PrepKit

PrepKit uses Antigravity CLI as an optional coding assistant for independent review and second-opinion workflows.

## Recommended Usage

Use PrepKit's generated second-opinion scripts rather than calling assistants ad hoc:

```bash
uv run prepkit ai-config setup antigravity-cli
uv run prepkit ai-config second-opinion
```

Before asking for a second opinion, update:

```text
.prepkit/second-opinion/context.md
```

Include:
- the current task and constraints
- files already inspected
- commands/tests already run
- ideas already rejected

Treat assistant output as a proposal. Verify recommendations with local tests, benchmarks, or direct code inspection.
