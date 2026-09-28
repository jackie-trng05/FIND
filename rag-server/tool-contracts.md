# FIND RAG Tool Contracts

The shared FIND RAG server exposes three tools. Every tool returns structured
JSON with a `status` field; grounded answers additionally carry citations and a
confidence category so responses stay auditable.

## refresh_corpus
- Purpose: rebuild the shared corpus and vector index from FIND evidence.
- Input: `caller` (optional).
- Output: `status`, `chunk_count`, `collection`, `corpus_path`,
  `vector_store_status` (`ready` | `degraded`) or `error`.
- Policy class: read + index update.

## retrieve_context
- Purpose: retrieve the most relevant chunks for a query.
- Input: `query` (required), `k` (optional, default 5), `caller` (optional).
- Output: `status`, `retrieval_mode` (`chromadb` | `lexical-hash`),
  `query_coverage`, `results[]` with `rank`, `chunk_id`, `source_id`,
  `authority_tier`, `score`, `text`.
- Ranking (Lab 08 hybrid): text is tokenised (`[a-z0-9]+`, stop words removed);
  score = `0.65 * BM25 + 0.35 * ChromaDB cosine similarity`, or
  `0.8 * BM25 + 0.2 * hashed-vector similarity` when ChromaDB is absent. BM25 is
  boosted 1.5x for tier_1 and 0.7x for tier_3.
- Policy class: read.

## answer_question
- Purpose: answer strictly from retrieved context (no invention).
- Input: `query` (required), `k` (optional, default 5), `caller` (optional),
  `model` (optional Ollama model; each student backend sends its own
  `OLLAMA_MODEL`, otherwise the server's `OLLAMA_MODEL` / `qwen2.5:0.5b`).
- Output: `answer`, `citations[]` (`chunk_id`, `source_id`, `authority_tier`),
  `confidence_category` (`High` | `Medium` | `Low`), `retrieval_summary` or `error`.
  When `query_coverage` is 0 (no query term matches any retrieved chunk) the
  answer is `Insufficient evidence.` with no citations and `Low` confidence.
- Policy class: read + grounded response.

## Authority tiers

| Tier | Source | Meaning |
| --- | --- | --- |
| tier_1 | live database records read through the shared MCP server + platform facts (README, docker-compose) | most authoritative |
| tier_2 | CI evidence reports (`docs/release-0/reports/`) | supporting |
| tier_3 | repository file index | least authoritative |

Confidence is derived from retrieval quality: `High` needs >=2 tier_1 chunks in
>=3 results; `Medium` needs >=1 tier_1 or >=2 tier_2; otherwise `Low`.
