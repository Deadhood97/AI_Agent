from __future__ import annotations

from contracts.analysis import AnalysisExecutionResult, SerializedAnalysisOutput


def _format_scalar(output: SerializedAnalysisOutput) -> str:
    return f"Computed result: {output.value}"


def _format_mapping(output: SerializedAnalysisOutput) -> str:
    if not isinstance(output.value, dict) or not output.value:
        return "Computed result: no values were returned."
    parts = [f"{key}: {value}" for key, value in output.value.items()]
    return "Computed result: " + "; ".join(parts)


def _format_table(output: SerializedAnalysisOutput, max_rows: int = 5) -> str:
    if not output.rows:
        return "Computed table result: no rows were returned."
    preview_rows = output.rows[:max_rows]
    lines = [f"Computed table result with {output.row_count or len(output.rows)} rows."]
    for index, row in enumerate(preview_rows, start=1):
        rendered = ", ".join(f"{key}: {value}" for key, value in row.items())
        lines.append(f"{index}. {rendered}")
    if output.truncated or len(output.rows) > max_rows:
        lines.append("The displayed preview is truncated.")
    return "\n".join(lines)


def format_analysis_answer(result: AnalysisExecutionResult) -> str:
    if result.status == "failed":
        message = result.error_message or "Unknown error."
        return f"I could not compute the answer. {result.error_type or 'Error'}: {message}"

    if result.serialized_output is None:
        return "The code ran successfully, but it did not return a selected output."

    output = result.serialized_output
    if output.kind == "scalar":
        return _format_scalar(output)
    if output.kind == "mapping":
        return _format_mapping(output)
    if output.kind == "table":
        return _format_table(output)
    return "The code ran successfully, but the output format is not recognized."
