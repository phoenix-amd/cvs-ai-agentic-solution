---
name: cvs-dev
description: Development workflow for contributing to CVS codebase. Covers TDD, file structure, testing, linting, and plugin development.
user_invocable: false
---

# CVS Developer Guide

This skill is auto-loaded when working on CVS source code.

## Repository Layout

```
cvs/
  main.py                     # CLI entry point (plugin-based)
  cli_plugins/                # Each subcommand is a plugin class
    base.py                   # SubcommandPlugin ABC
    run_plugin.py             # cvs run
    list_plugin.py            # cvs list
    exec_plugin.py            # cvs exec
    generate_plugin.py        # cvs generate
    ...
  core/
    orchestrators/            # baremetal.py, container.py
    runtimes/                 # docker.py, enroot.py
  lib/                        # Shared libraries
    parallel/                 # Parallel SSH engine
    preflight/                # Preflight check modules
    rccl_lib.py
    utils_lib.py
  tests/                      # PyTest test suites
    platform/                 # Host config checks
    health/                   # GPU health (AGFHC, TransferBench, RVS)
    preflight/                # Network/GPU preflight
    rccl/                     # RCCL performance
    training/                 # JAX, Megatron
    inference/                # vLLM, SGLang, xDiT
  input/                      # Config templates
    cluster_file/             # Cluster JSON templates
    config_file/              # Per-suite configs
  monitors/                   # Monitoring dashboards
  parsers/                    # Result parsers
  reports/                    # Report generators
```

## Development Workflow

### 1. Test-Driven Development
- Write the test FIRST in the appropriate `unittests/` directory
- Run the test to see it fail
- Implement the feature
- Run the test to see it pass
- Refactor if needed

### 2. Adding a New CLI Plugin
```python
# cvs/cli_plugins/my_plugin.py
from cvs.cli_plugins.base import SubcommandPlugin

class MyPlugin(SubcommandPlugin):
    name = "my-command"
    help = "Description of what it does"

    def add_arguments(self, parser):
        parser.add_argument("--flag", help="...")

    def execute(self, args):
        # Implementation
        pass
```

### 3. Lint and Format
```bash
ruff check cvs/          # Lint
ruff format cvs/          # Format
ruff check --fix cvs/     # Auto-fix
```

### 4. Run Tests
```bash
# All unit tests
pytest cvs/cli_plugins/unittests/ -v
pytest cvs/lib/unittests/ -v

# Specific test file
pytest cvs/cli_plugins/unittests/test_my_plugin.py -v

# With coverage
pytest --cov=cvs --cov-report=html
```

### 5. File Size Rule
Keep fork-owned files under **500 lines**. If a file grows beyond that, split it into logical modules.

## Code Style

- Python 3.9+ compatible
- Use `ruff` for linting and formatting
- Type hints encouraged but not required on existing code
- Docstrings only on public APIs
- No trailing whitespace, UTF-8 encoding
