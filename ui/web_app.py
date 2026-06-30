from __future__ import annotations

import argparse
import json
import mimetypes
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from dotenv import load_dotenv

from core import ArtifactStore, DatasetTools
from core.planning import PlanningError


WEB_ROOT = Path(__file__).parent / "web"


def _json_bytes(payload: dict, status: int = 200) -> tuple[int, bytes]:
    return status, json.dumps(payload, indent=2).encode("utf-8")


def _column_summary(metadata: dict) -> list[dict]:
    columns = metadata.get("columns", [])
    summary = []
    for column in columns[:8]:
        summary.append(
            {
                "name": column.get("name"),
                "semantic_type": column.get("semantic_type"),
                "missing_ratio": column.get("missing_ratio"),
                "unique_count": column.get("unique_count"),
            }
        )
    return summary


def _supported_question_examples() -> list[str]:
    return [
        "How many rows are there?",
        "What is the total revenue?",
        "What is the average revenue?",
        "Count by region",
    ]


def _ingestion_response_payload(tools: DatasetTools, result) -> dict:
    preview = tools.preview_for_session(result.session_id, rows=8)
    metadata = result.metadata.model_dump()
    return {
        "dataset_id": result.dataset_id,
        "session_id": result.session_id,
        "filename": metadata.get("source_file"),
        "row_count": metadata.get("row_count"),
        "column_count": metadata.get("column_count"),
        "quality": metadata.get("quality", {}),
        "columns": _column_summary(metadata),
        "suggested_questions": [suggestion.__dict__ for suggestion in result.suggested_questions],
        "preview": preview.get("preview_rows", []),
    }


def _parse_multipart_form(content_type: str, body: bytes) -> dict[str, dict[str, bytes | str]]:
    message = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: " + content_type.encode("utf-8") + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    )
    fields: dict[str, dict[str, bytes | str]] = {}
    if not message.is_multipart():
        return fields
    for part in message.iter_parts():
        name = part.get_param("name", header="content-disposition")
        if not name:
            continue
        filename = part.get_filename() or ""
        payload = part.get_payload(decode=True) or b""
        fields[str(name)] = {
            "filename": filename,
            "bytes": payload,
            "text": payload.decode(part.get_content_charset() or "utf-8", errors="replace"),
        }
    return fields


class AnalystWebHandler(BaseHTTPRequestHandler):
    tools: DatasetTools

    def log_message(self, format: str, *args):  # noqa: A002
        return

    def do_GET(self):  # noqa: N802
        path = unquote(self.path.split("?", 1)[0])
        if path == "/":
            path = "/index.html"
        requested = (WEB_ROOT / path.lstrip("/")).resolve()
        if not str(requested).startswith(str(WEB_ROOT.resolve())) or not requested.exists():
            self._send_text("Not found", status=404)
            return

        content_type = mimetypes.guess_type(str(requested))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(requested.read_bytes())

    def do_POST(self):  # noqa: N802
        try:
            if self.path == "/api/upload":
                status, payload = self._handle_upload()
            elif self.path == "/api/kaggle":
                status, payload = self._handle_kaggle_import()
            elif self.path == "/api/ask":
                status, payload = self._handle_ask()
            else:
                status, payload = _json_bytes({"error": "Unknown endpoint"}, status=404)
        except Exception as exc:
            status, payload = _json_bytes(
                {"error": f"{type(exc).__name__}: {exc}"},
                status=500,
            )
        self._send_json(payload, status=status)

    def _handle_upload(self) -> tuple[int, bytes]:
        content_length = int(self.headers.get("Content-Length", "0"))
        fields = _parse_multipart_form(
            self.headers.get("Content-Type", ""),
            self.rfile.read(content_length),
        )
        file_field = fields.get("csv_file")
        filename = str(file_field.get("filename", "")) if file_field else ""
        if file_field is None or not filename:
            return _json_bytes({"error": "Choose a CSV file first."}, status=400)

        raw_bytes = bytes(file_field.get("bytes", b""))
        description = str(fields.get("description", {}).get("text", ""))

        result = self.tools.ingest_csv_bytes(
            raw_bytes,
            Path(filename).name,
            dataset_description=description,
        )
        return _json_bytes(_ingestion_response_payload(self.tools, result))

    def _handle_kaggle_import(self) -> tuple[int, bytes]:
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8") or "{}")
        dataset_ref = str(payload.get("dataset_ref") or "").strip()
        requested_file = str(payload.get("requested_file") or "").strip()
        description = str(payload.get("description") or "").strip()
        if not dataset_ref:
            return _json_bytes({"error": "Paste a Kaggle dataset link or owner/dataset reference first."}, status=400)

        result = self.tools.ingest_kaggle_dataset(
            dataset_ref=dataset_ref,
            requested_file=requested_file,
            dataset_description=description,
        )
        response_payload = _ingestion_response_payload(self.tools, result)
        response_payload["kaggle_ref"] = dataset_ref
        response_payload["requested_file"] = requested_file
        return _json_bytes(response_payload)

    def _handle_ask(self) -> tuple[int, bytes]:
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8") or "{}")
        session_id = str(payload.get("session_id") or "").strip()
        question = str(payload.get("question") or "").strip()
        allow_llm = bool(payload.get("allow_llm", False))
        if not session_id:
            return _json_bytes({"error": "Upload a dataset first."}, status=400)
        if not question:
            return _json_bytes({"error": "Ask a question first."}, status=400)

        try:
            turn = self.tools.run_planned_turn(session_id, question, allow_llm=allow_llm)
        except PlanningError as exc:
            return _json_bytes(
                {
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "supported_questions": _supported_question_examples(),
                    "attempts": [attempt.model_dump(exclude={"plan"}) for attempt in exc.result.attempts],
                },
                status=422,
            )
        return _json_bytes(
            {
                "turn_id": turn.turn_id,
                "answer": turn.assistant_answer,
                "status": turn.execution_result.status,
                "analysis_plan": turn.analysis_plan.model_dump() if turn.analysis_plan else None,
                "trace": turn.trace,
                "output_key": turn.execution_result.output_key,
                "serialized_output": (
                    turn.execution_result.serialized_output.model_dump()
                    if turn.execution_result.serialized_output
                    else None
                ),
            }
        )

    def _send_json(self, payload: bytes, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _send_text(self, text: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))


def build_server(host: str, port: int, artifacts: Path) -> ThreadingHTTPServer:
    tools = DatasetTools(ArtifactStore(artifacts))

    class Handler(AnalystWebHandler):
        pass

    Handler.tools = tools
    return ThreadingHTTPServer((host, port), Handler)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run the Conversational Dataset Analyst web UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--artifacts", type=Path, default=Path("artifacts"))
    args = parser.parse_args(argv)

    server = build_server(args.host, args.port, args.artifacts)
    print(f"Dataset Analyst UI running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
