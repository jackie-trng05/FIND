"""Shared FIND RAG HTTP server (non-containerised).

The containerised student backends cannot depend on the MCP stdio transport, so
this thin HTTP wrapper exposes the same three RAG tools over JSON. It runs as a
local host process (default port 16070) and is reached from the student backend
containers via ``http://host.docker.internal:16070``.

Endpoints:
    GET  /health    -> {"status": "ok", "service": "rag-server"}
    POST /refresh   -> refresh_corpus(caller)
    POST /retrieve  -> retrieve_context(query, k, caller)
    POST /answer    -> answer_question(query, k, caller)

This server is intentionally NOT added to docker-compose: the Release 0
containerised feature microservices keep running unchanged, and AI-Mode / RAG /
the agentic loop stay local host processes.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from rag_pipeline import answer_question, refresh_corpus, retrieve_context


class RAGHandler(BaseHTTPRequestHandler):
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
            self._send_json(200, {"status": "ok", "service": "rag-server"})
            return
        self._send_json(404, {"status": "error", "error": "not_found"})

    def do_POST(self) -> None:
        try:
            payload = self._read_json()
        except Exception as exc:  # noqa: BLE001
            self._send_json(400, {"status": "error", "error": f"invalid_json: {exc}"})
            return

        try:
            if self.path == "/refresh":
                caller = (payload.get("caller") or "student").strip() or "student"
                result = refresh_corpus(caller=caller)
                self._send_json(200 if result.get("status") == "success" else 500, result)
                return

            if self.path == "/retrieve":
                query = (payload.get("query") or "").strip()
                if not query:
                    self._send_json(400, {"status": "error", "error": "query is required"})
                    return
                k = int(payload.get("k", 5))
                caller = (payload.get("caller") or "student").strip() or "student"
                result = retrieve_context(query=query, k=k, caller=caller)
                self._send_json(200 if result.get("status") == "success" else 500, result)
                return

            if self.path == "/answer":
                query = (payload.get("query") or "").strip()
                if not query:
                    self._send_json(400, {"status": "error", "error": "query is required"})
                    return
                k = int(payload.get("k", 5))
                caller = (payload.get("caller") or "student").strip() or "student"
                result = answer_question(query=query, k=k, caller=caller)
                self._send_json(200 if result.get("status") == "success" else 500, result)
                return

            self._send_json(404, {"status": "error", "error": "not_found"})
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"status": "error", "error": str(exc)})


def main() -> None:
    host = os.getenv("RAG_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("RAG_PORT", "16070")))
    server = ThreadingHTTPServer((host, port), RAGHandler)
    print(f"RAG HTTP server running on {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
