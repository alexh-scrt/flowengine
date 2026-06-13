"""Tests for templates and deterministic replay."""

import pytest

from flowengine.agent import templates
from flowengine.agent.replay import InMemoryRunStore, RunRecord, replay
from flowengine.config.loader import ConfigLoader
from flowengine.core.context import FlowContext
from flowengine.core.engine import FlowEngine

EXPECTED_TEMPLATES = {
    "sequential-task",
    "graph-branching-task",
    "plan-act-evaluate-loop",
    "human-approval-task",
    "map-reduce-research",
    "tool-use-worker",
    "supervisor-worker",
}


# ── templates ──


def test_list_templates():
    names = set(templates.list_templates())
    assert EXPECTED_TEMPLATES.issubset(names)


def test_get_template_returns_yaml():
    text = templates.get_template("plan-act-evaluate-loop")
    assert "max_iterations" in text


def test_get_missing_template_raises():
    with pytest.raises(FileNotFoundError):
        templates.get_template("does-not-exist")


def test_templates_are_valid_yaml():
    import yaml

    for name in EXPECTED_TEMPLATES:
        data = yaml.safe_load(templates.get_template(name))
        assert "name" in data and "components" in data and "flow" in data


# ── replay ──

RUNNABLE_YAML = """
name: replayable
inputs:
  msg: {type: string}
outputs:
  msg: {type: string}
components:
  - name: log
    type: flowengine.contrib.logging.LoggingComponent
    config: {message: "ran"}
flow:
  type: sequential
  steps:
    - component: log
"""


def test_run_record_roundtrip_and_replay():
    config = ConfigLoader.loads(RUNNABLE_YAML)
    ctx = FlowContext()
    ctx.set("msg", "hello")
    engine = FlowEngine.from_config(config)
    result = engine.execute(ctx)

    record = RunRecord.from_run(config, {"msg": "hello"}, result)
    assert record.normalized_yaml
    assert record.input_data == {"msg": "hello"}
    assert record.outputs == {"msg": "hello"}

    store = InMemoryRunStore()
    rid = store.save(record)
    assert rid in store.list_runs()

    replayed = replay(rid, store)
    assert replayed.get("msg") == "hello"


def test_replay_unknown_run_raises():
    store = InMemoryRunStore()
    with pytest.raises(KeyError):
        replay("nope", store)


def test_run_record_to_config():
    config = ConfigLoader.loads(RUNNABLE_YAML)
    record = RunRecord(flow_config=config.model_dump(mode="json"))
    rebuilt = record.to_config()
    assert rebuilt.name == "replayable"
