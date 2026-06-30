from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from core import ArtifactStore, DatasetTools


DATASET_NAME = "ai-analyst-smoke"

SMOKE_EXAMPLES = [
    {
        "inputs": {
            "filename": "sales.csv",
            "csv_text": "region,revenue\nEast,10\nWest,20\n",
            "question": "How many rows are there?",
        },
        "outputs": {"expected_kind": "scalar", "expected_value": 2},
    },
    {
        "inputs": {
            "filename": "sales.csv",
            "csv_text": "region,revenue\nEast,10\nWest,20\n",
            "question": "What is the total revenue?",
        },
        "outputs": {"expected_kind": "scalar", "expected_value": 30.0},
    },
    {
        "inputs": {
            "filename": "sales.csv",
            "csv_text": "region,revenue\nEast,10\nWest,20\n",
            "question": "What is the average revenue?",
        },
        "outputs": {"expected_kind": "scalar", "expected_value": 15.0},
    },
    {
        "inputs": {
            "filename": "sales.csv",
            "csv_text": "region,revenue\nEast,10\nWest,20\n",
            "question": "Count by region",
        },
        "outputs": {
            "expected_kind": "table",
            "expected_rows": [{"region": "East", "count": 1}, {"region": "West", "count": 1}],
        },
    },
]


def target(inputs: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        tools = DatasetTools(ArtifactStore(Path(temp_dir)))
        result = tools.ingest_csv_bytes(
            inputs["csv_text"].encode("utf-8"),
            inputs.get("filename", "dataset.csv"),
        )
        turn = tools.run_planned_turn(result.session_id, inputs["question"])
        output = turn.execution_result.serialized_output
        return {
            "status": turn.execution_result.status,
            "answer": turn.assistant_answer,
            "output_key": turn.execution_result.output_key,
            "output": output.model_dump() if output is not None else None,
            "error_type": turn.execution_result.error_type,
            "error_message": turn.execution_result.error_message,
        }


def execution_succeeded_evaluator(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    succeeded = outputs.get("status") == "succeeded"
    return {
        "key": "execution_succeeded",
        "score": 1 if succeeded else 0,
        "comment": "Execution succeeded." if succeeded else f"Execution failed: {outputs.get('error_message')}",
    }


def expected_output_evaluator(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    reference_outputs: dict[str, Any],
) -> dict[str, Any]:
    output = outputs.get("output") or {}
    expected_kind = reference_outputs.get("expected_kind")
    if output.get("kind") != expected_kind:
        return {
            "key": "expected_output",
            "score": 0,
            "comment": f"Expected {expected_kind}, got {output.get('kind')}.",
        }

    if expected_kind == "scalar":
        expected_value = reference_outputs.get("expected_value")
        actual_value = output.get("value")
        passed = actual_value == expected_value
        return {
            "key": "expected_output",
            "score": 1 if passed else 0,
            "comment": f"Expected {expected_value}, got {actual_value}.",
        }

    if expected_kind == "table":
        expected_rows = reference_outputs.get("expected_rows", [])
        actual_rows = output.get("rows", [])
        passed = all(row in actual_rows for row in expected_rows)
        return {
            "key": "expected_output",
            "score": 1 if passed else 0,
            "comment": f"Expected rows present: {passed}.",
        }

    return {"key": "expected_output", "score": 0, "comment": f"Unsupported expected kind: {expected_kind}."}


def ensure_dataset(client: Any) -> Any:
    try:
        return client.read_dataset(dataset_name=DATASET_NAME)
    except Exception:
        dataset = client.create_dataset(
            dataset_name=DATASET_NAME,
            description="Smoke tests for the conversational dataset analyst learning project.",
        )
        client.create_examples(dataset_id=dataset.id, examples=SMOKE_EXAMPLES)
        return dataset


def main() -> int:
    load_dotenv()
    try:
        from langsmith import Client
    except Exception:
        print("LangSmith is not installed. Run:")
        print(".\\.venv\\Scripts\\python.exe -m pip install -r requirements-tracing.txt")
        return 2

    client = Client()
    dataset = ensure_dataset(client)
    print(f"Using LangSmith dataset: {dataset.name}")
    results = client.evaluate(
        target,
        data=DATASET_NAME,
        evaluators=[execution_succeeded_evaluator, expected_output_evaluator],
        experiment_prefix="ai-analyst-smoke",
        max_concurrency=1,
        metadata={"project": "AI analyst", "learning_lab": "LangSmith Evaluation Smoke"},
    )
    print(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
