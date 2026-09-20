"""Shared, non-containerised FIND RAG pipeline (Lab 08).

ONE local RAG pipeline is shared by all five student features. It builds an
authority-tiered corpus from real FIND evidence, indexes it in a local vector
store, and answers questions grounded ONLY in retrieved context — every answer
carries citations and a confidence category.

Authority tiers (higher tier wins ties during ranking):
    tier_1  live database + platform facts   (most authoritative)
    tier_2  CI evidence reports
    tier_3  repository file index             (least authoritative)

The three public tools mirror the lab contract and are unit-testable directly:
    refresh_corpus(caller)        -> rebuild corpus + vector index
    retrieve_context(query, k)    -> top-k grounded chunks
    answer_question(query, k)     -> grounded answer + citations + confidence

This module is intentionally NOT containerised. It runs as a local host process
(see ``rag_http_server.py`` / ``rag_server.py``) so the Release 0 containerised
feature microservices keep running unchanged and reach it via
``host.docker.internal``.

ChromaDB is optional: when it is unavailable the pipeline transparently falls
back to a deterministic lexical retriever so the server still runs offline / in
environments without the vector store installed.
"""

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

try:  # ChromaDB is optional — degrade to the lexical fallback when absent.
    import chromadb
except Exception:  # noqa: BLE001 - any import failure disables the vector store
    chromadb = None

# --- Paths ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent          # rag-server/
APP_DIR = BASE_DIR.parent                             # FIND repository root
REPORTS_DIR = APP_DIR / "docs" / "release-0" / "reports"
README_PATH = APP_DIR / "README.md"
COMPOSE_PATH = APP_DIR / "docker-compose.yml"
CORPUS_PATH = BASE_DIR / "corpus" / "corpus.jsonl"
AUDIT_PATH = BASE_DIR / "rag-audit.jsonl"
CHROMA_PATH = BASE_DIR / "chroma"

# CI evidence file names produced by each student feature workflow.
REPORT_FILES = ["report.json", "report.md", "run-view.md"]

# --- Database microservice locations (host-mapped ports per the README) --
# The RAG server is a host process, so it reaches each containerised database
# service through its host-mapped port (mirrors mcp-server/config.py).
DB_SERVICE_URLS: dict[str, str] = {
    "shared": os.getenv("SHARED_DB_URL", "http://localhost:16003"),
    "student-1": os.getenv("STUDENT_1_DB_URL", "http://localhost:16006"),
    "student-2": os.getenv("STUDENT_2_DB_URL", "http://localhost:16009"),
    "student-3": os.getenv("STUDENT_3_DB_URL", "http://localhost:16012"),
    "student-4": os.getenv("STUDENT_4_DB_URL", "http://localhost:16015"),
    "student-5": os.getenv("STUDENT_5_DB_URL", "http://localhost:16018"),
}
DB_PROBE_TIMEOUT = int(os.getenv("RAG_DB_PROBE_TIMEOUT", "2"))

COLLECTION_NAME = "find_enterprise_context"
EMBED_VECTOR_SIZE = 256

_collection = None
_last_corpus_chunks: list[dict[str, Any]] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Embeddings (dependency-free, deterministic) -------------------------
def embed_texts(texts: list[str]) -> list[list[float]]:
    """Hash-based bag-of-tokens embedding (no external model required)."""
    vectors: list[list[float]] = []
    for text in texts:
        values = [0.0] * EMBED_VECTOR_SIZE
        tokens = (text or "").lower().split()
        if not tokens:
            vectors.append(values)
            continue
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i, byte in enumerate(digest):
                idx = i % EMBED_VECTOR_SIZE
                values[idx] += (byte / 255.0) - 0.5
        norm = sum(v * v for v in values) ** 0.5
        if norm > 0:
            values = [v / norm for v in values]
        vectors.append(values)
    return vectors


# --- Vector store --------------------------------------------------------
def get_collection():
    global _collection
    if chromadb is None:
        raise RuntimeError("chromadb_unavailable")
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def reset_collection() -> None:
    global _collection
    if chromadb is None:
        raise RuntimeError("chromadb_unavailable")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:  # noqa: BLE001 - collection may not exist yet
        pass
    _collection = client.get_or_create_collection(name=COLLECTION_NAME)


# --- Audit logging -------------------------------------------------------
def append_audit(
    tool_name: str,
    tool_input: dict[str, Any],
    tool_output: dict[str, Any],
    validation_status: str,
    outcome: str,
    start_time: float,
) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int((time.time() - start_time) * 1000)
    record = {
        "request_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "tool_name": tool_name,
        "tool_input": tool_input,
        "tool_output": tool_output,
        "timestamp": now_iso(),
        "duration_ms": duration_ms,
        "validation_status": validation_status,
        "outcome": outcome,
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


# --- Chunking ------------------------------------------------------------
def chunk_text(text: str, max_words: int = 80) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i : i + max_words]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


# --- Corpus sources ------------------------------------------------------
def load_platform_chunks() -> list[dict[str, Any]]:
    """tier_1 facts from on-disk platform sources (README + docker-compose).

    Always available (no network), so grounded answers about the FIND platform
    stay auditable even when the containerised services are stopped.
    """
    chunks: list[dict[str, Any]] = []

    if README_PATH.exists():
        for i, line in enumerate(
            README_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
        ):
            stripped = line.strip()
            # Repository-convention table rows: "| `path` | responsibility |".
            if stripped.startswith("| `") and stripped.endswith("|"):
                text = stripped.strip("|").replace("`", "").strip()
                if text and "---" not in text:
                    chunks.append(
                        {
                            "chunk_id": f"readme_row_{i}",
                            "source_id": "README.md",
                            "authority_tier": "tier_1",
                            "text": f"FIND repository convention: {text}",
                            "metadata": {"source_type": "platform", "file": "README.md"},
                            "indexed_at": now_iso(),
                        }
                    )

    if COMPOSE_PATH.exists():
        for i, line in enumerate(
            COMPOSE_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
        ):
            if "container_name:" in line:
                service = line.split("container_name:", 1)[1].strip()
                chunks.append(
                    {
                        "chunk_id": f"compose_service_{i}",
                        "source_id": "docker-compose.yml",
                        "authority_tier": "tier_1",
                        "text": f"Docker Compose runs the containerised service '{service}'.",
                        "metadata": {"source_type": "platform", "service": service},
                        "indexed_at": now_iso(),
                    }
                )
    return chunks


def load_db_service_chunks() -> list[dict[str, Any]]:
    """tier_1 facts probed live from each FIND database microservice.

    Best-effort and resilient: unreachable services (e.g. containers stopped)
    are simply skipped so corpus refresh never fails on network state.
    """
    chunks: list[dict[str, Any]] = []
    for feature, base_url in DB_SERVICE_URLS.items():
        try:
            response = requests.get(f"{base_url}/health", timeout=DB_PROBE_TIMEOUT)
            healthy = response.status_code == 200
        except Exception:  # noqa: BLE001 - unreachable service is not an error here
            continue

        service_name = feature
        try:
            index = requests.get(f"{base_url}/", timeout=DB_PROBE_TIMEOUT).json()
            service_name = index.get("service", feature)
        except Exception:  # noqa: BLE001 - index route is optional
            pass

        chunks.append(
            {
                "chunk_id": f"db_service_{feature}",
                "source_id": f"{feature}:/health",
                "authority_tier": "tier_1",
                "text": (
                    f"The {feature} database microservice '{service_name}' is "
                    f"{'healthy' if healthy else 'unhealthy'} and reachable at {base_url}."
                ),
                "metadata": {"source_type": "database_service", "feature": feature},
                "indexed_at": now_iso(),
            }
        )
    return chunks


def load_report_chunks() -> list[dict[str, Any]]:
    """tier_2 chunks from the per-student CI evidence packs."""
    chunks: list[dict[str, Any]] = []
    if not REPORTS_DIR.exists():
        return chunks

    for report_path in sorted(REPORTS_DIR.rglob("*")):
        if not report_path.is_file() or report_path.name not in REPORT_FILES:
            continue
        rel = report_path.relative_to(APP_DIR).as_posix()
        try:
            if report_path.suffix == ".json":
                text = json.dumps(json.loads(report_path.read_text(encoding="utf-8")), indent=2)
            else:
                text = report_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001 - fall back to raw text
            text = report_path.read_text(encoding="utf-8", errors="ignore")

        for i, chunk in enumerate(chunk_text(text), start=1):
            chunks.append(
                {
                    "chunk_id": f"{report_path.parent.name}_{report_path.stem}_{i}",
                    "source_id": rel,
                    "authority_tier": "tier_2",
                    "text": chunk,
                    "metadata": {"source_type": "report", "file": report_path.name},
                    "indexed_at": now_iso(),
                }
            )
    return chunks


def load_repository_chunks() -> list[dict[str, Any]]:
    """tier_3 chunk: an index of repository files (structure questions)."""
    ignored = {".git", ".venv", "__pycache__", "node_modules", "chroma", ".pytest_cache"}
    files: list[str] = []

    for root, dirs, filenames in os.walk(
        APP_DIR, topdown=True, followlinks=False, onerror=lambda e: None
    ):
        pruned: list[str] = []
        for directory_name in dirs:
            if directory_name in ignored:
                continue
            directory_path = Path(root) / directory_name
            try:
                if directory_path.is_symlink():
                    continue
            except OSError:
                continue
            pruned.append(directory_name)
        dirs[:] = pruned

        for filename in filenames:
            file_path = Path(root) / filename
            try:
                if file_path.is_symlink():
                    continue
                rel = file_path.relative_to(APP_DIR)
                files.append(str(rel).replace("\\", "/"))
            except (OSError, ValueError):
                continue

    text = "Repository files include: " + ", ".join(sorted(files[:400]))
    return [
        {
            "chunk_id": "repo_index",
            "source_id": "repository",
            "authority_tier": "tier_3",
            "text": text,
            "metadata": {"source_type": "repository", "file_count": len(files)},
            "indexed_at": now_iso(),
        }
    ]


def build_corpus() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    chunks.extend(load_platform_chunks())
    chunks.extend(load_db_service_chunks())
    chunks.extend(load_report_chunks())
    chunks.extend(load_repository_chunks())
    return chunks


def write_corpus(chunks: list[dict[str, Any]]) -> None:
    CORPUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CORPUS_PATH.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk) + "\n")


def read_corpus() -> list[dict[str, Any]]:
    if not CORPUS_PATH.exists():
        return []
    chunks: list[dict[str, Any]] = []
    with CORPUS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return chunks


# --- Retrieval -----------------------------------------------------------
def lexical_fallback_retrieve(query: str, k: int) -> list[dict[str, Any]]:
    corpus = _last_corpus_chunks or read_corpus()
    query_tokens = set((query or "").lower().split())
    tier_weight = {"tier_1": 3, "tier_2": 2, "tier_3": 1}

    scored = []
    for chunk in corpus:
        text = chunk.get("text", "")
        text_tokens = set(text.lower().split())
        overlap = len(query_tokens.intersection(text_tokens))
        scored.append(
            {
                "rank": 0,
                "chunk_id": chunk.get("chunk_id"),
                "source_id": chunk.get("source_id"),
                "authority_tier": chunk.get("authority_tier"),
                "distance": None,
                "text": text,
                "_score": overlap,
            }
        )

    scored.sort(
        key=lambda r: (r.get("_score", 0), tier_weight.get(r.get("authority_tier"), 0)),
        reverse=True,
    )
    top = scored[: max(k, 1)]
    for i, row in enumerate(top, start=1):
        row["rank"] = i
        row.pop("_score", None)
    return top


def refresh_corpus(caller: str = "student") -> dict[str, Any]:
    global _last_corpus_chunks
    start = time.time()
    try:
        chunks = build_corpus()
        _last_corpus_chunks = chunks
        write_corpus(chunks)
        vector_store_status = "ready"
        vector_store_error = None

        try:
            reset_collection()
            collection = get_collection()
            if chunks:
                ids = [c["chunk_id"] for c in chunks]
                docs = [c["text"] for c in chunks]
                metas = [
                    {
                        "source_id": c["source_id"],
                        "authority_tier": c["authority_tier"],
                        "indexed_at": c["indexed_at"],
                    }
                    for c in chunks
                ]
                embeddings = embed_texts(docs)
                collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)
        except Exception as exc:  # noqa: BLE001 - vector store optional
            vector_store_status = "degraded"
            vector_store_error = str(exc)

        output = {
            "status": "success",
            "caller": caller,
            "chunk_count": len(chunks),
            "collection": COLLECTION_NAME,
            "corpus_path": str(CORPUS_PATH),
            "vector_store_status": vector_store_status,
        }
        if vector_store_error:
            output["vector_store_error"] = vector_store_error
        append_audit("refresh_corpus", {"caller": caller}, output, "pass", "corpus_refreshed", start)
        return output
    except Exception as exc:  # noqa: BLE001
        output = {"status": "error", "error": str(exc)}
        append_audit("refresh_corpus", {"caller": caller}, output, "fail", "error", start)
        return output


def retrieve_context(query: str, k: int = 5, caller: str = "student") -> dict[str, Any]:
    start = time.time()
    try:
        retrieval_mode = "vector"
        ranked: list[dict[str, Any]] = []

        try:
            if chromadb is None:
                raise RuntimeError("chromadb_unavailable")
            collection = get_collection()
            if collection.count() == 0:
                refreshed = refresh_corpus(caller="auto_refresh")
                if refreshed.get("status") != "success":
                    raise RuntimeError("empty_collection")

            query_embedding = embed_texts([query])
            results = collection.query(query_embeddings=query_embedding, n_results=k)

            ids = (results.get("ids") or [[]])[0]
            docs = (results.get("documents") or [[]])[0]
            metas = (results.get("metadatas") or [[]])[0]
            distances = (results.get("distances") or [[]])[0]

            for i, chunk_id in enumerate(ids):
                row_meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
                ranked.append(
                    {
                        "rank": i + 1,
                        "chunk_id": chunk_id,
                        "source_id": row_meta.get("source_id"),
                        "authority_tier": row_meta.get("authority_tier"),
                        "distance": distances[i] if i < len(distances) else None,
                        "text": docs[i] if i < len(docs) else "",
                    }
                )

            tier_weight = {"tier_1": 3, "tier_2": 2, "tier_3": 1}
            ranked.sort(
                key=lambda x: (
                    tier_weight.get(x.get("authority_tier"), 0),
                    -(x.get("distance") if isinstance(x.get("distance"), (int, float)) else 1e9),
                ),
                reverse=True,
            )
        except Exception:  # noqa: BLE001 - fall back to lexical retrieval
            retrieval_mode = "lexical_fallback"
            if not _last_corpus_chunks and not CORPUS_PATH.exists():
                refreshed = refresh_corpus(caller="auto_refresh")
                if refreshed.get("status") != "success":
                    return {"status": "error", "error": "corpus_unavailable"}
            ranked = lexical_fallback_retrieve(query, k)

        output = {
            "status": "success",
            "query": query,
            "caller": caller,
            "k": k,
            "retrieval_mode": retrieval_mode,
            "results": ranked,
        }
        append_audit(
            "retrieve_context",
            {"query": query, "k": k, "caller": caller},
            {"result_count": len(ranked), "chunk_ids": [r["chunk_id"] for r in ranked]},
            "pass",
            "context_retrieved",
            start,
        )
        return output
    except Exception as exc:  # noqa: BLE001
        output = {"status": "error", "error": str(exc), "query": query}
        append_audit(
            "retrieve_context",
            {"query": query, "k": k, "caller": caller},
            output,
            "fail",
            "error",
            start,
        )
        return output


# --- Answering -----------------------------------------------------------
def confidence_from_results(results: list[dict[str, Any]]) -> str:
    """Map retrieval quality onto a confidence category (retrieval = safety)."""
    if not results:
        return "Low"
    tier_1 = sum(1 for r in results if r.get("authority_tier") == "tier_1")
    tier_2 = sum(1 for r in results if r.get("authority_tier") == "tier_2")
    if tier_1 >= 2 and len(results) >= 3:
        return "High"
    if tier_1 >= 1 or tier_2 >= 2:
        return "Medium"
    return "Low"


def generate_with_ollama(query: str, context: str) -> str:
    model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    ollama_generate_url = os.getenv(
        "OLLAMA_GENERATE_URL", "http://host.docker.internal:11434/api/generate"
    )
    prompt = f"""
You are a retrieval-grounded assistant for the FIND platform.
Use ONLY the provided context. If evidence is missing, return exactly: Insufficient evidence.

QUESTION:
{query}

CONTEXT:
{context}

Return exactly:
Answer:
<answer>

Evidence:
<summary>
"""
    try:
        resp = requests.post(
            ollama_generate_url,
            json={"model": model_name, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "Insufficient evidence.")
    except Exception as exc:  # noqa: BLE001 - Ollama is optional / disabled in CI
        return f"Ollama unavailable: {exc}"


def deterministic_answer(query: str, results: list[dict[str, Any]]) -> str | None:
    """Grounded, LLM-free answer for common structural questions.

    Keeps the endpoint useful when AI-Mode is disabled (e.g. in CI) by
    summarising the retrieved evidence without inventing anything.
    """
    q = (query or "").lower()
    if not results:
        return None
    if any(term in q for term in ("which files", "repository files", "project structure", "list files")):
        repo = next((r for r in results if r.get("source_id") == "repository"), None)
        if repo:
            return "Answer:\n" + repo.get("text", "")
    if any(term in q for term in ("healthy", "service status", "which services", "reachable")):
        services = [r.get("text", "") for r in results if (r.get("source_id") or "").endswith(":/health")]
        if services:
            return "Answer:\n" + "\n".join(services)
    return None


def answer_question(query: str, k: int = 5, caller: str = "student") -> dict[str, Any]:
    start = time.time()
    retrieval = retrieve_context(query=query, k=k, caller=caller)
    if retrieval.get("status") != "success":
        output = {
            "status": "error",
            "query": query,
            "error": retrieval.get("error", "retrieval_failed"),
        }
        append_audit(
            "answer_question",
            {"query": query, "k": k, "caller": caller},
            output,
            "fail",
            "retrieval_failed",
            start,
        )
        return output

    results = retrieval.get("results", [])
    context = "\n\n".join(r.get("text", "") for r in results)

    answer = deterministic_answer(query, results)
    if answer is None:
        if os.getenv("AI_MODE_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on"):
            answer = generate_with_ollama(query, context)
        else:
            answer = "Answer:\n" + (results[0].get("text", "") if results else "Insufficient evidence.")

    citations = [
        {
            "chunk_id": r.get("chunk_id"),
            "source_id": r.get("source_id"),
            "authority_tier": r.get("authority_tier"),
        }
        for r in results
    ]
    confidence = confidence_from_results(results)
    output = {
        "status": "success",
        "query": query,
        "answer": answer,
        "citations": citations,
        "confidence_category": confidence,
        "retrieval_summary": {
            "k": k,
            "retrieved_count": len(results),
            "top_chunk": results[0].get("chunk_id") if results else None,
        },
    }
    append_audit(
        "answer_question",
        {"query": query, "k": k, "caller": caller},
        {"confidence_category": confidence, "citation_count": len(citations)},
        "pass",
        "answer_generated",
        start,
    )
    return output


if __name__ == "__main__":
    print(json.dumps(refresh_corpus(), indent=2))
    print(json.dumps(retrieve_context("which student feature microservices exist", 5), indent=2))
    print(json.dumps(answer_question("Which repository files make up the FIND platform?", 5), indent=2))
