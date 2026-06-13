"""Canonical flow templates for agent generation.

Agents generate far more reliable flows when seeded with a known-good skeleton
("use the plan-act-evaluate-loop template and fill in the components") than from
free-form generation. Templates are shipped as YAML files under
``flowengine/templates/`` and surfaced via ``flowengine template list|show``.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

_PACKAGE = "flowengine.templates"


def _templates_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "templates"


def list_templates() -> list[str]:
    """Return the names (without extension) of all available templates."""
    directory = _templates_dir()
    if not directory.is_dir():
        return []
    return sorted(p.stem for p in directory.glob("*.yaml"))


def get_template(name: str) -> str:
    """Return the raw YAML text of a named template.

    Raises:
        FileNotFoundError: If the template does not exist.
    """
    # Prefer importlib.resources so this works from an installed wheel too.
    try:
        resource = resources.files(_PACKAGE).joinpath(f"{name}.yaml")
        if resource.is_file():
            return resource.read_text(encoding="utf-8")
    except (ModuleNotFoundError, FileNotFoundError):
        pass
    path = _templates_dir() / f"{name}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"No such template: {name!r}")
    return path.read_text(encoding="utf-8")
