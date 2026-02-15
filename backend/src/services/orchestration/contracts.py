from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class NodeExecutionContext:
    project_id: str
    run_id: str
    input_payload: dict
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class NodeExecutionResult:
    status: str
    output_payload: dict
