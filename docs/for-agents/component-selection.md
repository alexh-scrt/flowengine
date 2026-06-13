# Component Selection

Get the catalog with `flowengine components --json` (or
`flowengine.agent.build_catalog(registry)`). Each entry:

```json
{
  "type": "web_search",
  "name": "web_search",
  "description": "Searches the web and returns ranked results.",
  "inputs":  { "query": {"type": "string"} },
  "outputs": { "search_results": {"type": "array"} },
  "ports": ["success", "no_results"],
  "tags": ["search", "web"],
  "cost": "low",
  "risk_level": "low",
  "effects": ["read_web"],
  "requires_approval": false,
  "requires_llm": false,
  "safe_for_agents": true
}
```

## How to choose

1. **Match the contract.** Pick components whose `outputs` provide the keys your
   downstream components `consume`, and whose `inputs` are satisfied by flow
   `inputs` or upstream outputs. The compiler flags gaps
   (`MISSING_INPUT_PRODUCER`, `OUTPUT_NOT_PRODUCED`).
2. **Wire ports correctly.** Only branch on ports listed in `ports`.
3. **Prefer `safe_for_agents: true`.** Low-risk, no-approval components compose
   freely. High-risk or approval-gated components need a human or a permissive
   policy (see `safety-policy.md`).
4. **Mind cost.** Prefer `cost: low` where adequate; reserve `high` for steps
   that need it.
5. **Compose with subflows.** A whole worker can be reused as a component via
   `flowengine.contrib.subflow.SubflowComponent` (or called as a tool with
   `FlowTool`). Its derived metadata still participates in validation.

## Data flow

Components read/write a shared context by key. A component declaring
`outputs: {search_results: ...}` writes `context["search_results"]`; a downstream
component declaring `inputs: {search_results: ...}` reads it. Keep key names
consistent across the chain.
