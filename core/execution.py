from __future__ import annotations

import ast
import textwrap
from typing import Any

import numpy as np
import pandas as pd


def sanitize_generated_code(code: str) -> str:
    cleaned = textwrap.dedent(code).strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    allowed_imports = {"import pandas as pd", "import numpy as np"}
    return "\n".join(line for line in textwrap.dedent(cleaned).splitlines() if line.strip() not in allowed_imports).strip()


def validate_generated_code(code: str) -> None:
    tree = ast.parse(code)
    blocked_names = {"open", "exec", "eval", "compile", "__import__", "input"}
    blocked_roots = {"os", "sys", "subprocess", "socket", "requests", "pathlib", "shutil"}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            raise ValueError("Generated code may not import modules.")
        if isinstance(node, (ast.While, ast.With, ast.AsyncWith)):
            raise ValueError("Generated code may not use while/with blocks.")
        if isinstance(node, ast.Name) and node.id in {"__builtins__", "__loader__", "__spec__"}:
            raise ValueError("Generated code may not access interpreter internals.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in blocked_names:
            raise ValueError(f"Generated code may not call {node.func.id}.")
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__"):
                raise ValueError("Generated code may not access dunder attributes.")
            root = node
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name) and root.id in blocked_roots:
                raise ValueError(f"Generated code may not access {root.id}.")


def execute_dataframe_code(df: pd.DataFrame, code: str) -> dict[str, Any]:
    sanitized = sanitize_generated_code(code)
    validate_generated_code(sanitized)
    safe_builtins = {
        "ValueError": ValueError,
        "TypeError": TypeError,
        "Exception": Exception,
        "len": len,
        "range": range,
        "sorted": sorted,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "sum": sum,
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "enumerate": enumerate,
        "isinstance": isinstance,
        "zip": zip,
        "all": all,
        "any": any,
    }
    globals_dict = {"__builtins__": safe_builtins, "pd": pd, "np": np}
    locals_dict: dict[str, Any] = {"df": df.copy()}
    exec(compile(sanitized, "<generated_dataframe_code>", "exec"), globals_dict, locals_dict)
    analysis_outputs = locals_dict.get("analysis_outputs")
    if not isinstance(analysis_outputs, dict):
        raise ValueError("Generated code must create analysis_outputs as a dictionary.")
    return analysis_outputs

