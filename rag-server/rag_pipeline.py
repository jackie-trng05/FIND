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
import math
import os
import re
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
REPORTS_DIR = APP_DIR / "docs"
README_PATH = APP_DIR / "README.md"
COMPOSE_PATH = APP_DIR / "docker-compose.yml"
CORPUS_PATH = BASE_DIR / "corpus" / "corpus.jsonl"
AUDIT_PATH = BASE_DIR / "rag-audit.jsonl"
CHROMA_PATH = BASE_DIR / "chroma"

# Text file extensions indexed from the docs folder as tier_2 evidence.
REPORT_FILE_SUFFIXES = {".json", ".md", ".txt", ".xml"}

# Report files excluded from the corpus: these document the RAG/MCP run itself,
# so ingesting them would ground answers on self-referential evidence.
EXCLUDED_REPORT_FILES = {"rag-report.md", "rag-validation-report.md"}

# --- Shared MCP server (the live-database source for tier_1 chunks) ------
# Both AI modes read the same records: MCP Mode calls these tools per request,
# and the RAG corpus is built by walking them at refresh time. Both the RAG
# server and the MCP server are local host processes, so this is localhost.
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:16050/mcp")
# job_postings caps each response, so the catalogue is walked per status.
MCP_POSTING_STATUSES = ("Published", "Draft", "Closed", "Archived")
# Columns that must never enter the corpus (credentials / session secrets).
SENSITIVE_COLUMN_MARKERS = ("password", "hash", "token", "secret", "salt")

COLLECTION_NAME = "find_enterprise_context"
EMBED_VECTOR_SIZE = 384
# Tokeniser (Lab 08 rag_pipeline._TOKEN_PATTERN / _STOP_WORDS).
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "how", "i", "in", "is", "it", "of", "on", "or", "that", "the",
    "to", "what", "which", "who", "with",
}

_collection = None
_last_corpus_chunks: list[dict[str, Any]] = []


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Tokenisation + embeddings (Lab 08) ---------------------------------
def _tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in _TOKEN_PATTERN.findall(text or "")
        if token.lower() not in _STOP_WORDS
    ]


def _embedding(text: str) -> list[float]:
    """Signed feature-hash embedding (no external model required)."""
    vector = [0.0] * EMBED_VECTOR_SIZE
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % EMBED_VECTOR_SIZE
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]
    return vector


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [_embedding(text) for text in texts]


# --- Vector store --------------------------------------------------------
def get_collection():
    global _collection
    if chromadb is None:
        raise RuntimeError("chromadb_unavailable")
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )
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
    _collection = client.get_or_create_collection(
            name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
        )


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


def _db_record_chunk(
    feature: str, table: str, key: str, record: dict[str, Any], tool: str = ""
) -> dict[str, Any]:
    record_id = record.get(key, "?")
    fields = []
    for column, value in record.items():
        if any(marker in column.lower() for marker in SENSITIVE_COLUMN_MARKERS):
            continue
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        fields.append(f"{column} = {value}")
    return {
        "chunk_id": f"db_{feature}_{table}_{record_id}",
        "source_id": f"{feature}-db:/{table}/{record_id}",
        "authority_tier": "tier_1",
        "text": f"{feature} database, {table} record {record_id}: " + "; ".join(fields) + ".",
        "metadata": {
            "source_type": "database_record",
            "feature": feature,
            "table": table,
            "record_id": str(record_id),
            "retrieved_via": f"mcp:{tool}" if tool else "mcp",
        },
        "indexed_at": now_iso(),
    }


def _mcp_answer_data(result: Any) -> dict[str, Any]:
    """Unwrap an MCP CallToolResult into its retrieval-context answer_data."""
    payload: Any = getattr(result, "structuredContent", None)
    if isinstance(payload, dict):
        payload = payload.get("result", payload)
    else:
        payload = None
        for item in getattr(result, "content", None) or []:
            text = getattr(item, "text", None)
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            break
    if not isinstance(payload, dict):
        return {}
    answer_data = payload.get("answer_data")
    return answer_data if isinstance(answer_data, dict) else {}


async def _walk_mcp_records() -> list[tuple[str, str, str, dict[str, Any], str]]:
    """Walk every MCP retrieval tool and return the records they ground.

    The MCP tools are keyed lookups, so the walk is driven from the job
    postings outwards: postings -> applications -> interviews / evaluations,
    and the applicants behind those applications -> profiles.
    """
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client

    records: list[tuple[str, str, str, dict[str, Any], str]] = []

    async with streamablehttp_client(MCP_SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            async def call(tool: str, **arguments: Any) -> dict[str, Any]:
                return _mcp_answer_data(await session.call_tool(tool, arguments))

            # Student 2 — job postings. The tool caps each response, so the
            # catalogue is collected one status at a time and merged by id.
            postings: dict[Any, dict[str, Any]] = {}
            for status in MCP_POSTING_STATUSES:
                data = await call("job_postings", status=status)
                for posting in data.get("postings", []) or []:
                    if isinstance(posting, dict) and posting.get("job_posting_id") is not None:
                        postings[posting["job_posting_id"]] = posting
            for posting in postings.values():
                records.append(
                    ("student-2", "job_postings", "job_posting_id", posting, "job_postings")
                )

            # Student 3 — the applications submitted for each posting.
            application_ids: list[Any] = []
            user_ids: list[Any] = []
            for posting_id in postings:
                data = await call("applications_for_job", job_posting_id=posting_id)
                for application in data.get("applications", []) or []:
                    if not isinstance(application, dict):
                        continue
                    application = {"job_posting_id": posting_id, **application}
                    records.append(
                        (
                            "student-3",
                            "applications",
                            "application_id",
                            application,
                            "applications_for_job",
                        )
                    )
                    app_id = application.get("application_id")
                    if app_id is not None and app_id not in application_ids:
                        application_ids.append(app_id)
                    user_id = application.get("user_id")
                    if user_id is not None and user_id not in user_ids:
                        user_ids.append(user_id)

            # Students 4 and 5 — the interview and evaluation for each application.
            for app_id in application_ids:
                interview = await call("interview_details", application_id=app_id)
                if interview.get("interview_id") is not None:
                    records.append(
                        ("student-4", "interviews", "interview_id", interview, "interview_details")
                    )
                evaluation = await call("evaluation_scores", application_id=app_id)
                if evaluation.get("evaluation_id") is not None:
                    scores = evaluation.pop("scores", None)
                    if isinstance(scores, dict):
                        evaluation.update(scores)
                    records.append(
                        (
                            "student-5",
                            "evaluations",
                            "evaluation_id",
                            evaluation,
                            "evaluation_scores",
                        )
                    )

            # Student 1 — the profile and resume behind each applicant.
            for user_id in user_ids:
                data = await call("applicant_profile", user_id=user_id)
                profile = data.get("profile")
                if not isinstance(profile, dict):
                    continue
                record = {"user_id": user_id, **profile}
                resume = data.get("resume")
                if isinstance(resume, dict):
                    record.update(
                        {f"resume_{field}": value for field, value in resume.items()}
                    )
                records.append(
                    ("student-1", "profiles", "user_id", record, "applicant_profile")
                )

    return records


def load_db_service_chunks() -> list[dict[str, Any]]:
    """tier_1 records read live through the shared FIND MCP server.

    The RAG corpus is grounded in exactly the records the MCP retrieval tools
    expose, so both AI modes cite the same data. One chunk per record, so rows
    created through the UI are grounded on the next refresh. If the MCP server
    is not running the database chunks are skipped rather than failing the
    refresh.
    """
    try:
        import anyio

        records = anyio.run(_walk_mcp_records)
    except Exception:  # noqa: BLE001 - MCP server down/SDK missing is not fatal here
        return []

    return [
        _db_record_chunk(feature, table, key, record, tool)
        for feature, table, key, record, tool in records
    ]


def load_report_chunks() -> list[dict[str, Any]]:
    """tier_2 chunks from the per-student CI evidence packs."""
    chunks: list[dict[str, Any]] = []
    if not REPORTS_DIR.exists():
        return chunks

    for report_path in sorted(REPORTS_DIR.rglob("*")):
        if not report_path.is_file() or report_path.suffix.lower() not in REPORT_FILE_SUFFIXES:
            continue
        if report_path.name in EXCLUDED_REPORT_FILES:
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
                    "chunk_id": f"{report_path.parent.name}_{report_path.name}_{i}",
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
def _lexical_scores(query: str, chunks: list[dict[str, Any]]) -> dict[str, float]:
    """BM25 keyword scores, normalised to 0..1 (Lab 08 _lexical_scores)."""
    query_terms = _tokens(query)
    if not query_terms:
        return {}
    tokenized = [_tokens(chunk.get("text", "")) for chunk in chunks]
    average_length = sum(map(len, tokenized)) / max(len(tokenized), 1)
    document_frequency = {
        term: sum(term in set(terms) for terms in tokenized)
        for term in set(query_terms)
    }
    scores: dict[str, float] = {}
    for chunk, terms in zip(chunks, tokenized):
        frequencies = {term: terms.count(term) for term in set(query_terms)}
        score = 0.0
        for term, frequency in frequencies.items():
            if not frequency:
                continue
            inverse_frequency = math.log(
                1 + (len(chunks) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            denominator = frequency + 1.2 * (
                1 - 0.75 + 0.75 * len(terms) / max(average_length, 1)
            )
            score += inverse_frequency * frequency * 2.2 / denominator
        # Authority boosts (Lab 08: authoritative 1.5x, specification 0.7x).
        if chunk.get("authority_tier") == "tier_1" and score:
            score *= 1.5
        elif chunk.get("authority_tier") == "tier_3" and score:
            score *= 0.7
        scores[chunk["chunk_id"]] = score
    max_score = max(scores.values(), default=0.0)
    if max_score:
        return {chunk_id: score / max_score for chunk_id, score in scores.items()}
    return scores


def _hashed_vector_scores(query: str, chunks: list[dict[str, Any]]) -> dict[str, float]:
    query_vector = _embedding(query)
    return {
        chunk["chunk_id"]: max(
            0.0,
            sum(
                left * right
                for left, right in zip(query_vector, _embedding(chunk.get("text", "")))
            ),
        )
        for chunk in chunks
    }


def _chroma_scores(query: str, k: int) -> dict[str, float] | None:
    if chromadb is None:
        return None
    try:
        collection = get_collection()
        count = collection.count()
        if not count:
            return {}
        result = collection.query(
            query_embeddings=[_embedding(query)],
            n_results=min(k, count),
            include=["distances"],
        )
    except Exception:  # noqa: BLE001 - vector store optional
        return None
    ids = result["ids"][0]
    distances = result["distances"][0]
    return {
        chunk_id: max(0.0, min(1.0, 1.0 - float(distance)))
        for chunk_id, distance in zip(ids, distances)
    }


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
    """Hybrid retrieval (Lab 08): BM25 keyword score + vector similarity."""
    start = time.time()
    try:
        chunks = _last_corpus_chunks or read_corpus()
        if not chunks:
            refreshed = refresh_corpus(caller="auto_refresh")
            if refreshed.get("status") != "success":
                return {"status": "error", "error": "corpus_unavailable", "query": query}
            chunks = _last_corpus_chunks

        lexical_scores = _lexical_scores(query, chunks)
        vector_scores = _chroma_scores(query, k)
        if vector_scores is None:
            retrieval_mode = "lexical-hash"
            hash_scores = _hashed_vector_scores(query, chunks)
            combined = {
                c["chunk_id"]: 0.8 * lexical_scores.get(c["chunk_id"], 0.0)
                + 0.2 * hash_scores.get(c["chunk_id"], 0.0)
                for c in chunks
            }
        else:
            retrieval_mode = "chromadb"
            combined = {
                c["chunk_id"]: 0.65 * lexical_scores.get(c["chunk_id"], 0.0)
                + 0.35 * vector_scores.get(c["chunk_id"], 0.0)
                for c in chunks
            }
        top = sorted(
            chunks,
            key=lambda c: (combined.get(c["chunk_id"], 0.0), c["chunk_id"]),
            reverse=True,
        )[:k]
        ranked = [
            {
                "rank": i,
                "chunk_id": c.get("chunk_id"),
                "source_id": c.get("source_id"),
                "authority_tier": c.get("authority_tier"),
                "score": round(combined.get(c["chunk_id"], 0.0), 4),
                "text": c.get("text", ""),
            }
            for i, c in enumerate(top, start=1)
        ]
        query_terms = set(_tokens(query))
        matched_terms = query_terms & {t for r in ranked for t in _tokens(r["text"])}
        coverage = len(matched_terms) / max(len(query_terms), 1)

        output = {
            "status": "success",
            "query": query,
            "caller": caller,
            "k": k,
            "retrieval_mode": retrieval_mode,
            "query_coverage": round(coverage, 4),
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
# Chunk text is prefixed/tagged for retrieval grounding (e.g. "student-1 database,
# profiles record 6: user_id = 6; ...") but that internal labelling must never
# reach the user-facing answer — citations already carry the same provenance.
# Prompt instructions alone are not reliable (small local models still copy
# whatever is in their context), so this is stripped deterministically before
# the text ever reaches the LLM or the non-AI fallback.
_INTERNAL_CHUNK_PREFIX = re.compile(r"^[\w-]+\s+database,\s+[\w-]+\s+record\s+[\w-]+:\s*", re.IGNORECASE)
_INTERNAL_ID_FIELD = re.compile(r"\b(?:\w+_id|id)\s*=\s*[^;]+;\s*", re.IGNORECASE)


def _sanitize_for_display(text: str) -> str:
    """Strip internal grounding labels before a chunk is shown/generated for a user."""
    text = _INTERNAL_CHUNK_PREFIX.sub("", text)
    text = _INTERNAL_ID_FIELD.sub("", text)
    return text


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


def generate_with_ollama(query: str, context: str, model: str | None = None) -> str:
    model_name = model or os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    ollama_generate_url = os.getenv(
        "OLLAMA_GENERATE_URL", "http://localhost:11434/api/generate"
    )
    prompt = f"""
You are a friendly, user-facing, retrieval-grounded assistant for the FIND platform.
Use ONLY the provided context. If evidence is missing, return exactly: Insufficient evidence.
Never mention database names, table names, or internal record/chunk identifiers in the answer.

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
    return None


def answer_question(
    query: str, k: int = 5, caller: str = "student", model: str | None = None
) -> dict[str, Any]:
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
    # Lab 08: no query term matched anything -> refuse instead of guessing.
    if retrieval.get("query_coverage", 0) == 0:
        results = []
    context = "\n\n".join(_sanitize_for_display(r.get("text", "")) for r in results)

    answer = deterministic_answer(query, results)
    if not results:
        answer = "Insufficient evidence."
    elif answer is None:
        if os.getenv("AI_MODE_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on"):
            answer = generate_with_ollama(query, context, model)
        else:
            answer = "Answer:\n" + (_sanitize_for_display(results[0].get("text", "")) if results else "Insufficient evidence.")

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
            "query_coverage": retrieval.get("query_coverage"),
            "retrieval_mode": retrieval.get("retrieval_mode"),
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
