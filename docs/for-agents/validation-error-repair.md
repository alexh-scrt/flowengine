# Validation & Error Repair

Validation returns a `CompileResult`:

```json
{
  "valid": false,
  "errors": [ { "code": "...", "path": "...", "message": "...",
               "suggestion": "...", "repair": { "yaml_patch": [...] } } ],
  "warnings": [ ... ],
  "normalized_yaml": null
}
```

Only `errors` block execution. `warnings` are advisory (e.g. a high-risk
component, an unreachable node, an unmet output contract) — review them but they
do not stop a run.

## Repair algorithm

```
while not result.valid:
    for issue in result.errors:
        if issue.repair:
            document = apply_json_patch(document, issue.repair.yaml_patch)
        else:
            fix manually using issue.message + issue.suggestion
    result = compile(document)
```

`apply_json_patch` is available as `flowengine.agent.apply_patch(doc, ops)` or
`flowengine apply-patch FILE PATCH.json`.

## Issue codes (stable, machine-matchable)

| code | meaning | typical fix |
|------|---------|-------------|
| `YAML_PARSE_ERROR` | not valid YAML | fix syntax |
| `SCHEMA_INVALID` | wrong top-level shape | top level must be a mapping |
| `MISSING_FIELD` | required field absent | add the field (patch provided) |
| `INVALID_VALUE` | value fails schema | correct the value |
| `UNKNOWN_COMPONENT` | type not registered/importable | use a cataloged type (patch suggests nearest) |
| `UNDEFINED_COMPONENT_REF` | step/node references unknown component | fix the name |
| `DUPLICATE_NAME` | duplicate component/node id | rename |
| `UNKNOWN_EDGE_NODE` | edge points at missing node | fix source/target |
| `UNDECLARED_PORT` | edge uses a port the source doesn't expose | use a declared port |
| `MISSING_INPUT_PRODUCER` | a consumed key has no producer/input | add an input or producer |
| `OUTPUT_NOT_PRODUCED` | declared output never produced | add a producing component |
| `UNREACHABLE_NODE` | node has no path from a root | add an edge |
| `CYCLE_WITHOUT_EXIT` | loop can only stop at max_iterations | add an exit port edge |
| `NO_TERMINAL_OUTPUT` | graph has no terminal node | add a leaf |
| `DENIED_COMPONENT` / `NOT_ALLOWLISTED` | blocked by policy | choose an allowed component |
| `APPROVAL_REQUIRED` | needs human approval | request approval / swap component |
| `RISK_EXCEEDS_POLICY` | risk or resource cap exceeded | lower limit (patch) or swap component |

## Example

```json
{
  "code": "UNKNOWN_COMPONENT",
  "path": "components[2].type",
  "message": "Component type 'web_serch' is not registered or importable.",
  "suggestion": "Did you mean 'web_search'?",
  "repair": { "explanation": "Replace components[2].type with 'web_search'.",
              "yaml_patch": [ {"op":"replace","path":"/components/2/type","value":"web_search"} ],
              "confidence": 0.7 }
}
```
