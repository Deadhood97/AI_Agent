from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from contracts.planning import AnalysisPlan
from core.execution import validate_generated_code
from core.langsmith_tracing import compact_metadata_for_langsmith, end_langsmith_span, langsmith_span


LLM_PLANNER_VERSION = "openai-structured-v0"


class LLMPlannerUnavailable(RuntimeError):
    """Raised when the optional LLM planner cannot run in the current environment."""


def llm_plan_question(question: str, metadata: dict[str, Any]) -> AnalysisPlan:
    load_dotenv(".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your_key_here":
        raise LLMPlannerUnavailable("OPENAI_API_KEY is not configured.")

    try:
        from openai import OpenAI
    except Exception as exc:
        raise LLMPlannerUnavailable(
            "The `openai` package is not installed. Install agent dependencies before enabling LLM planning."
        ) from exc

    model = os.getenv("OPENAI_CODE_MODEL") or os.getenv("OPENAI_MODEL") or "gpt-4.1"
    compact_metadata = compact_metadata_for_langsmith(metadata)
    system_prompt = (
        "You are a careful data analyst planner. Return an AnalysisPlan JSON object only. "
        "The generated Python code must use the existing dataframe variable `df` and create "
        "`analysis_outputs` as a dictionary. Do not import modules, read files, call network APIs, "
        "or use unsafe Python features. Set planner to `llm` and planner_version to "
        f"`{LLM_PLANNER_VERSION}`. If the question cannot be answered from the metadata, set "
        "needs_clarification to true and provide a clarification_question."
    )
    user_prompt = {
        "question": question,
        "metadata": compact_metadata,
        "analysis_plan_schema": AnalysisPlan.model_json_schema(),
        "planner": "llm",
        "planner_version": LLM_PLANNER_VERSION,
    }

    with langsmith_span(
        "llm_plan_question",
        run_type="llm",
        inputs={"question": question, "metadata": compact_metadata, "model": model},
    ) as span:
        client = OpenAI(api_key=api_key)
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": repr(user_prompt)},
            ],
            text_format=AnalysisPlan,
        )
        plan = response.output_parsed
        if plan is None:
            raise ValueError("OpenAI response did not include a parsed AnalysisPlan.")
        plan = plan.model_copy(update={"planner": "llm", "planner_version": LLM_PLANNER_VERSION})
        validate_generated_code(plan.code)
        end_langsmith_span(
            span,
            {
                "planner": plan.planner,
                "planner_version": plan.planner_version,
                "columns_needed": plan.columns_needed,
                "metrics": plan.metrics,
                "grouping": plan.grouping,
                "needs_clarification": plan.needs_clarification,
            },
        )
        return plan
