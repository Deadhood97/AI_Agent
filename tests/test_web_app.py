from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib import request

from ui.web_app import build_server


class WebAppTests(unittest.TestCase):
    def _start_server(self, artifacts: Path):
        server = build_server("127.0.0.1", 0, artifacts)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        return server, thread, base_url

    def _post_json(self, url: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        response = request.urlopen(
            request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        )
        return json.loads(response.read().decode("utf-8"))

    def test_web_app_serves_frontend(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server, thread, base_url = self._start_server(Path(temp_dir))
            try:
                response = request.urlopen(f"{base_url}/")
                html = response.read().decode("utf-8")
                self.assertIn("Dataset Analyst", html)
                self.assertIn("composerForm", html)
                self.assertIn("left-rail", html)
                self.assertIn("tab-plan", html)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_web_app_upload_and_ask_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server, thread, base_url = self._start_server(Path(temp_dir))
            try:
                boundary = "----dataset-analyst-test"
                csv_text = "region,revenue\nNorth,10\nSouth,20\n"
                multipart = (
                    f"--{boundary}\r\n"
                    'Content-Disposition: form-data; name="csv_file"; filename="sales.csv"\r\n'
                    "Content-Type: text/csv\r\n\r\n"
                    f"{csv_text}\r\n"
                    f"--{boundary}\r\n"
                    'Content-Disposition: form-data; name="description"\r\n\r\n'
                    "Sales sample\r\n"
                    f"--{boundary}--\r\n"
                ).encode("utf-8")
                upload_response = request.urlopen(
                    request.Request(
                        f"{base_url}/api/upload",
                        data=multipart,
                        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                        method="POST",
                    )
                )
                upload_payload = json.loads(upload_response.read().decode("utf-8"))
                self.assertEqual(upload_payload["row_count"], 2)
                self.assertEqual(upload_payload["suggested_questions"][0]["question"], "What is the total revenue?")

                answer_payload = self._post_json(
                    f"{base_url}/api/ask",
                    {
                        "session_id": upload_payload["session_id"],
                        "question": "What is the total revenue?",
                    },
                )
                self.assertEqual(answer_payload["status"], "succeeded")
                self.assertIn("30.0", answer_payload["answer"])
                self.assertEqual(answer_payload["analysis_plan"]["planner"], "deterministic")
                self.assertEqual(answer_payload["serialized_output"]["kind"], "scalar")
                self.assertEqual(answer_payload["serialized_output"]["value"], 30.0)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

    def test_web_app_planning_failure_returns_examples(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            server, thread, base_url = self._start_server(Path(temp_dir))
            try:
                boundary = "----dataset-analyst-test"
                csv_text = "region,revenue\nNorth,10\nSouth,20\n"
                multipart = (
                    f"--{boundary}\r\n"
                    'Content-Disposition: form-data; name="csv_file"; filename="sales.csv"\r\n'
                    "Content-Type: text/csv\r\n\r\n"
                    f"{csv_text}\r\n"
                    f"--{boundary}--\r\n"
                ).encode("utf-8")
                upload_response = request.urlopen(
                    request.Request(
                        f"{base_url}/api/upload",
                        data=multipart,
                        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                        method="POST",
                    )
                )
                upload_payload = json.loads(upload_response.read().decode("utf-8"))

                with self.assertRaises(HTTPError) as raised:
                    self._post_json(
                        f"{base_url}/api/ask",
                        {
                            "session_id": upload_payload["session_id"],
                            "question": "Why did revenue change?",
                        },
                    )
                error_payload = json.loads(raised.exception.read().decode("utf-8"))

                self.assertEqual(raised.exception.code, 422)
                self.assertEqual(error_payload["error_type"], "PlanningError")
                self.assertIn("What is the total revenue?", error_payload["supported_questions"])
                self.assertEqual(error_payload["attempts"][0]["planner"], "deterministic")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
