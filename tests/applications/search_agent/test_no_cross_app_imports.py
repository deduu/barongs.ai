from __future__ import annotations

import ast
from pathlib import Path

_SEARCH_AGENT_DIR = Path(__file__).resolve().parents[3] / "src" / "applications" / "search_agent"


def _collect_imports(directory: Path) -> list[str]:
    """Return all import strings from .py files in *directory* (recursive)."""
    imports: list[str] = []
    for py_file in directory.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
    return imports


class TestNoCrossAppImports:
    def test_search_agent_does_not_import_deep_search(self):
        imports = _collect_imports(_SEARCH_AGENT_DIR)
        violations = [i for i in imports if "src.applications.deep_search" in i]
        assert violations == [], (
            f"search_agent must not import from deep_search: {violations}"
        )
