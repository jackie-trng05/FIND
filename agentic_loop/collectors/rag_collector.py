"""Collect structural evidence for the shared FIND RAG server."""

from pathlib import Path


REQUIRED_TOOLS = ("refresh_corpus", "retrieve_context", "answer_question")


def collect(app_dir: Path, repo_root: Path) -> tuple[bool, str]:
    server_dir = app_dir / "rag-server"
    required_paths = (
        server_dir / "rag_pipeline.py",
        server_dir / "rag_server.py",
        server_dir / "rag_http_server.py",
        server_dir / "requirements.txt",
    )
    missing = [str(path.relative_to(app_dir)) for path in required_paths if not path.exists()]
    if missing:
        return False, "RAG evidence incomplete. Missing: " + ", ".join(missing)

    pipeline_text = (server_dir / "rag_pipeline.py").read_text(encoding="utf-8")
    missing_tools = [tool for tool in REQUIRED_TOOLS if f"def {tool}" not in pipeline_text]
    if missing_tools:
        return False, "rag_pipeline.py is missing tools: " + ", ".join(missing_tools)

    return True, (
        "RAG evidence: rag-server contains the pipeline, MCP server, HTTP server, and requirements; "
        "3 required tools are defined (refresh_corpus, retrieve_context, answer_question)."
    )