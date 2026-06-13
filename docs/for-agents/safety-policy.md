# Safety Policy

An agent may generate any YAML, but FlowEngine decides what may **run**. An
`ExecutionPolicy` is the sandbox. Honor it when generating flows.

## Policy shape

```yaml
policy:
  max_runtime_seconds: 120
  max_iterations: 5
  max_component_calls: 50
  max_parallel_nodes: 4
  allowed_components: [web_search, summarize, critique, final_answer]
  denied_components: [shell, file_delete, send_email]
  require_approval_for: [external_write, payment, email_send, shell_exec]
  approved: []            # component names/types a human pre-approved
  allow_high_risk: false
```

## How it is enforced

- **Statically** at compile time: pass the policy to
  `FlowCompiler.compile_yaml(text, policy=...)` or `flowengine validate FILE
  --policy policy.yaml`. Violations are errors:
  `DENIED_COMPONENT`, `NOT_ALLOWLISTED`, `APPROVAL_REQUIRED`,
  `RISK_EXCEEDS_POLICY`.
- **At runtime** via `policy.apply_to_config(config)`: tightens
  `timeout_seconds` and `max_iterations` to the policy, and switches
  `on_max_iterations` to `exit` so loops stop gracefully.

## Risk model

Each component declares a `risk_level` (`low|medium|high|critical`), an `effects`
list (e.g. `read_web`, `write_file`, `send_email`, `execute_code`, `spend_money`,
`modify_repo`), and `requires_approval`.

Rules you should follow when generating:

1. Stay within `allowed_components`; never use anything in `denied_components`.
2. If a needed component has an effect in `require_approval_for` or
   `requires_approval: true`, either request human approval (so it joins
   `approved`) or pick a lower-risk alternative.
3. Do not raise `max_iterations` above the policy's cap; the compiler will reject
   it and offer a patch lowering it.
4. Treat high/critical-risk components as blocked unless `allow_high_risk` is
   true or the component is in `approved`.
