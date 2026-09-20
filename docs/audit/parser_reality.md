# Parser Reality Check

- **Parsing Mechanism**: The analyzer uses the official `tree-sitter-c` package, which is a precompiled C grammar for the `tree-sitter` Python bindings. It is loaded via `C_LANG = Language(tsc.language())` at `src/firmware_agent/analyzer/parser.py:15`.
- **Self-Verification**: At import time, `src/firmware_agent/analyzer/parser.py:18` verifies the grammar by parsing `int x = 5;` and asserting that the resulting node type is `declaration`.
- **Regex/String Based**: The parsing is NOT regex or string-based. It fully traverses the AST produced by `tree-sitter`.
- **Generators**: The generators (e.g. `BoundaryTestGenerator` in `src/firmware_agent/generators/boundary.py:11`) consume the structured `BehaviorGraph` produced by the analyzer, traversing `behavior_graph.boundary_conditions`. They do not fall back to hardcoded defaults.
- **Parse Failures**: If the analyzer cannot parse a C file, `tree_sitter` creates `ERROR` nodes in the AST. The current logic ignores unrecognized nodes, resulting in an empty model if the file is completely malformed, which causes test generation to yield 0 tests.
