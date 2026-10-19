"""Shared FIND multi-agent HTTP server.

Mirrors the shared MCP (16050) and RAG (16070) servers: a thin HTTP/JSON wrapper
deployed as a container (docker-compose service ``multi-agent-server``, default
port 16080), where student backends reach it at
``http://find-multi-agent-server:16080`` (and in the cloud at the app's internal
FQDN). When run instead as a local host process, containerised backends reach it
via ``http://host.docker.internal:16080``. The student backends proxy to it
through ``services/multi_agent_api.py``; the browser never talks to this server
directly.

Endpoints:
    GET  /health                    -> {"status": "ok", "service": "multi-agent-server"}
    POST /workflow                  -> run_workflow(user_request, caller, user_id, evidence_domain)
    GET  /workflow/status            -> workflow_status()
    POST /workflow/<id>/decision     -> record_decision(workflow_id, decision, reason, evidence_used)
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from coordinator import record_decision, run_workflow, workflow_status


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
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {"status": "ok", "service": "multi-agent-server"})
            return
        if parsed.path == "/workflow/status":
            caller = parse_qs(parsed.query).get("caller", [None])[0]
            self._send_json(200, workflow_status(caller))
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
            user_id = payload.get("user_id")
            evidence_domain = (payload.get("evidence_domain") or "").strip()
            try:
                result = run_workflow(
                    user_request=user_request, caller=caller, user_id=user_id, evidence_domain=evidence_domain
                )
                self._send_json(200, result)
            except Exception as exc:  # noqa: BLE001
                self._send_json(500, {"status": "error", "error": str(exc)})
            return

        if self.path.startswith("/workflow/") and self.path.endswith("/decision"):
            workflow_id = self.path[len("/workflow/"):-len("/decision")].strip("/")
            decision = (payload.get("decision") or "").strip()
            reason = (payload.get("reason") or "").strip()
            evidence_used = (payload.get("evidence_used") or "").strip()
            if not workflow_id or not decision:
                self._send_json(400, {"status": "error", "error": "workflow_id and decision are required"})
                return
            try:
                result = record_decision(
                    workflow_id=workflow_id, decision=decision, reason=reason, evidence_used=evidence_used
                )
                self._send_json(200 if result.get("status") == "success" else 404, result)
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
