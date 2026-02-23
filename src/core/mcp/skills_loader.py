from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def load_skills_md(path: str | Path) -> list[dict[str, Any]]:
    """Parse a SKILLS.md file into a list of tool descriptions.

    Expected SKILLS.md format:
    ```
    ## tool_name
    Description of what the tool does.

    **Parameters:**
    - `param1` (string, required): Description of param1
    - `param2` (integer, optional): Description of param2
    ```

    Returns a list of dicts with keys: name, description, parameters.
    """
    content = Path(path).read_text(encoding="utf-8")
    skills: list[dict[str, Any]] = []

    # Split by ## headings (level 2)
    sections = re.split(r"^## ", content, flags=re.MULTILINE)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.split("\n", 1)
        name = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""

        # Extract description (everything before **Parameters:**)
        params_match = re.split(r"\*\*Parameters:\*\*", body, maxsplit=1)
        description = params_match[0].strip()

        # Extract parameters
        parameters: list[dict[str, Any]] = []
        if len(params_match) > 1:
            param_block = params_match[1]
            param_pattern = re.compile(r"- `(\w+)`\s*\((\w+)(?:,\s*(required|optional))?\):\s*(.+)")
            for match in param_pattern.finditer(param_block):
                parameters.append(
                    {
                        "name": match.group(1),
                        "type": match.group(2),
                        "required": match.group(3) != "optional",
                        "description": match.group(4).strip(),
                    }
                )

        skills.append(
            {
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        )

    return skills
