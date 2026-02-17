import json
from pathlib import Path

from src.schemas.context_bundle import ContextBundleV1


def test_node0_context_bundle_schema_example() -> None:
    base = Path(__file__).resolve().parents[2] / "contracts" / "examples"
    payload = json.loads((base / "node0_topic_initialization.response.json").read_text(encoding="utf-8"))
    ContextBundleV1.model_validate(payload["context_bundle"])



