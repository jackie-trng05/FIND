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
- Output: `status`, `retrieval_mode` (`vector` | `lexical_fallback`),
  `results[]` with `chunk_id`, `source_id`, `authority_tier`, `distance`, `text`.
- Policy class: read.

## answer_question
- Purpose: answer strictly from retrieved context (no invention).
- Input: `query` (required), `k` (optional, default 5), `caller` (optional).
- Output: `answer`, `citations[]` (`chunk_id`, `source_id`, `authority_tier`),
  `confidence_category` (`High` | `Medium` | `Low`), `retrieval_summary` or `error`.
- Policy class: read + grounded response.

## Authority tiers

| Tier | Source | Meaning |
| --- | --- | --- |
| tier_1 | live database services + platform facts (README, docker-compose) | most authoritative |
| tier_2 | CI evidence reports (`docs/release-0/reports/`) | supporting |
| tier_3 | repository file index | least authoritative |

Confidence is derived from retrieval quality: `High` needs >=2 tier_1 chunks in
>=3 results; `Medium` needs >=1 tier_1 or >=2 tier_2; otherwise `Low`.
