"""Tests for ComponentMeta / IOFieldSpec / PortSpec."""

from flowengine.agent.meta import ComponentMeta, IOFieldSpec, PortSpec
from flowengine.core.component import BaseComponent


def test_io_field_to_json_schema():
    spec = IOFieldSpec(type="string", required=True, description="the query")
    schema = spec.to_json_schema()
    assert schema["type"] == "string"
    assert schema["description"] == "the query"


def test_io_field_any_omits_type():
    assert "type" not in IOFieldSpec(type="any").to_json_schema()


def test_component_meta_helpers():
    meta = ComponentMeta(
        name="web_search",
        inputs={"query": IOFieldSpec(type="string")},
        outputs={"results": IOFieldSpec(type="array")},
        ports=[PortSpec(name="ok"), PortSpec(name="empty")],
    )
    assert meta.input_keys == ["query"]
    assert meta.output_keys == ["results"]
    assert meta.port_names == ["ok", "empty"]
    assert meta.is_safe_for_agents is True


def test_component_meta_risk_marks_unsafe():
    meta = ComponentMeta(name="shell", risk_level="high")
    assert meta.is_safe_for_agents is False


def test_component_meta_catalog_entry():
    meta = ComponentMeta(
        name="web_search",
        description="searches",
        outputs={"results": IOFieldSpec(type="array")},
        ports=[PortSpec(name="ok")],
        effects=["read_web"],
    )
    entry = meta.to_catalog_entry()
    assert entry["name"] == "web_search"
    assert entry["ports"] == ["ok"]
    assert entry["effects"] == ["read_web"]
    assert entry["safe_for_agents"] is True


def test_base_component_meta_defaults_none():
    class C(BaseComponent):
        def process(self, context):
            return context

    assert C("x").get_meta() is None


def test_base_component_get_meta_returns_class_meta():
    class C(BaseComponent):
        meta = ComponentMeta(name="thing")

        def process(self, context):
            return context

    assert C("x").get_meta().name == "thing"
