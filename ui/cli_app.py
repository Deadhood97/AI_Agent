from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from core import ArtifactStore, DatasetTools
from core.langsmith_tracing import end_langsmith_span, langsmith_span, summarize_suggestions_for_langsmith
from core.planning import PlanningError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a simple dataset analyst smoke workflow.")
    parser.add_argument("csv_path", nargs="?", type=Path, help="Path to a CSV file.")
    parser.add_argument("--kaggle", help="Kaggle dataset reference or URL, for example `owner/dataset-slug`.")
    parser.add_argument("--kaggle-file", default="", help="Optional CSV filename/path inside the Kaggle dataset.")
    parser.add_argument("--description", default="", help="Optional dataset notes to append to metadata.")
    parser.add_argument("--question", help="Simple analytical question to ask.")
    parser.add_argument("--allow-llm-planner", action="store_true", help="Allow optional LLM planner fallback.")
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=Path("artifacts"),
        help="Artifact directory to use.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = build_parser().parse_args(argv)

    if args.csv_path is None and not args.kaggle:
        print("Provide a CSV path or use --kaggle owner/dataset-slug.")
        return 2
    if args.csv_path is not None and args.kaggle:
        print("Use either a CSV path or --kaggle, not both.")
        return 2
    if args.csv_path is not None and not args.csv_path.exists():
        print(f"CSV file not found: {args.csv_path}")
        return 2

    source_label = args.kaggle or args.csv_path.name
    with langsmith_span(
        "CLI dataset analyst workflow",
        run_type="chain",
        inputs={
            "source": source_label,
            "source_type": "kaggle" if args.kaggle else "csv",
            "kaggle_file": args.kaggle_file,
            "question": args.question,
            "question_provided": bool(args.question),
            "allow_llm_planner": args.allow_llm_planner,
        },
        metadata={"surface": "cli"},
    ) as span:
        tools = DatasetTools(ArtifactStore(args.artifacts))
        try:
            if args.kaggle:
                result = tools.ingest_kaggle_dataset(
                    dataset_ref=args.kaggle,
                    requested_file=args.kaggle_file,
                    dataset_description=args.description,
                )
            else:
                result = tools.ingest_csv_bytes(
                    args.csv_path.read_bytes(),
                    args.csv_path.name,
                    dataset_description=args.description,
                )
        except Exception as exc:
            print(f"Dataset import failed: {type(exc).__name__}: {exc}")
            end_langsmith_span(
                span,
                {
                    "status": "dataset_import_failed",
                    "source": source_label,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                },
            )
            return 1
        suggestions = tools.suggest_questions_for_session(result.session_id)

        print("Suggested questions:")
        for index, suggestion in enumerate(suggestions, start=1):
            print(f"{index}. {suggestion.question}")

        if not args.question:
            print(f"session_id: {result.session_id}")
            end_langsmith_span(
                span,
                {
                    "status": "suggestions_shown",
                    "session_id": result.session_id,
                    "dataset_id": result.dataset_id,
                    "suggested_questions": summarize_suggestions_for_langsmith(suggestions),
                },
            )
            return 0

        try:
            turn = tools.run_planned_turn(
                result.session_id,
                args.question,
                allow_llm=args.allow_llm_planner,
            )
        except PlanningError as exc:
            print(f"Could not plan that question: {exc}")
            end_langsmith_span(
                span,
                {
                    "status": "planning_failed",
                    "session_id": result.session_id,
                    "dataset_id": result.dataset_id,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "suggested_questions": summarize_suggestions_for_langsmith(suggestions),
                },
            )
            return 1

        print()
        print(turn.assistant_answer)
        print(f"session_id: {result.session_id}")
        print(f"turn_id: {turn.turn_id}")
        exit_code = 0 if turn.execution_result.status == "succeeded" else 1
        end_langsmith_span(
            span,
            {
                "status": turn.execution_result.status,
                "exit_code": exit_code,
                "session_id": result.session_id,
                "dataset_id": result.dataset_id,
                "turn_id": turn.turn_id,
                "answer": turn.assistant_answer,
                "suggested_questions": summarize_suggestions_for_langsmith(suggestions),
            },
        )
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
