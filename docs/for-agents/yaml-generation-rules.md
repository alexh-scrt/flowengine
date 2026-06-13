# YAML Generation Rules

## Top-level shape

```yaml
name: my-worker            # required
version: "1.0"             # quote version strings
description: ...           # recommended
inputs:                    # the worker's input contract (recommended)
  query: {type: string, required: true}
outputs:                   # the worker's output contract (recommended)
  answer: {type: string}
components:                # required, >= 1
  - name: search          # unique within the flow
    type: web_search      # a type from the catalog (or an importable path)
    config: {}            # component-specific config
flow:                     # required
  type: sequential        # sequential | conditional | graph
  settings: {}
  steps: [...]            # for sequential/conditional
  nodes: [...]            # for graph
  edges: [...]            # for graph
```

## Flow types

- **sequential** — runs every step in order; a step's `condition` (a safe Python
  expression over context) can skip it. All matching steps run.
- **conditional** — first-match branching: stops after the first step whose
  `condition` is true.
- **graph** — DAG (or cyclic) with `nodes` + `edges` and port-based routing.

## Field types

`IOFieldSpec` types: `string | number | integer | boolean | array | object | any`.
Each field: `{type, required, description, default}`.

## Graph rules

- Each node: `{id, component, on_error?, max_visits?}`. `id` is unique.
- Each edge: `{source, target, port?}`. `port: null` is an unconditional edge.
- Root nodes (no incoming edge) are entry points and always run.
- A node is skipped if no incoming edge activated it.
- Cyclic graphs **must** set `settings.max_iterations` (1–1000) and should set
  `on_max_iterations: exit` to stop gracefully, plus an explicit exit port.

## Settings (common)

```yaml
settings:
  fail_fast: true
  timeout_seconds: 120
  max_iterations: 3            # cyclic graphs
  on_max_iterations: exit      # fail | exit | warn
  on_condition_error: fail     # fail | skip | warn
```

## Style

- Quote ambiguous scalars (versions, "yes"/"no", numeric-looking strings).
- Prefer running `flowengine normalize` on output: it fills defaults, orders
  keys, drops unknown fields, and emits canonical, diff-friendly YAML.
