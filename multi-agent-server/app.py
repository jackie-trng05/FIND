"""Shared FIND multi-agent HTTP server (non-containerised).

Mirrors the shared MCP (16050) and RAG (16070) servers: a thin HTTP/JSON wrapper
that runs as a local host process (default port 16080) and is reached from the
containerised student backends via ``http://host.docker.internal:16080``. The
student backends proxy to it through ``services/multi_agent_api.py``; the browser
never talks to this server directly.

Endpoints:
    GET  /health            -> {"status": "ok", "service": "multi-agent-server"}
    POST /workflow          -> run_workflow(user_request, caller)
    GET  /workflow/status   -> workflow_status()

This server is intentionally NOT added to docker-compose: the Release 0
containerised feature microservices keep running unchanged, and MCP / RAG / the
multi-agent workflow stay local host processes.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from coordinator import run_workflow, workflow_status


class MultiAgentHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code: int, payload: dict) -> None:
        response = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length)
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def log_message(self, *args) -> None:  # noqa: D401 - quieten default logging
        return

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "multi-agent-server"})
            return
        if self.path == "/workflow/status":
            self._send_json(200, workflow_status())
            return
        self._send_json(404, {"status": "error", "error": "not_found"})

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json(400, {"status": "error", "error": f"invalid_json: {exc}"})
            return

        if self.path == "/workflow":
            user_request = (payload.get("user_request") or "").strip()
            if not user_request:
                self._send_json(400, {"status": "error", "error": "user_request is required"})
                return
            caller = (payload.get("caller") or "student").strip() or "student"
            try:
                result = run_workflow(user_request=user_request, caller=caller)
                self._send_json(200, result)
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"status": "error", "error": str(exc)})
            return

        self._send_json(404, {"status": "error", "error": "not_found"})


def main() -> None:
    host = os.getenv("MULTI_AGENT_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("MULTI_AGENT_PORT", "16080")))
    server = ThreadingHTTPServer((host, port), MultiAgentHandler)
    print(f"Multi-Agent HTTP server running on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
