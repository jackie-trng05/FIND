"""Retrieval quality evaluation for the shared FIND RAG pipeline.

Computes P@5 (precision at 5) and R@5 (recall at 5) over a small set of
benchmark queries and writes the results to ``retrieval-metrics.md``. Retrieval
quality is the safety property behind grounded answers: high precision/recall
means citations point at genuinely relevant evidence.

The benchmarks target FIND platform evidence (student feature microservices, CI
reports, repository structure) so the evaluation runs offline against the corpus
built by ``rag_pipeline.refresh_corpus`` — no containers or Ollama required.
"""

from pathlib import Path

from rag_pipeline import retrieve_context

METRICS_PATH = Path(__file__).resolve().parent / "retrieval-metrics.md"

BENCHMARKS = [
    {
        "query": "student feature microservices",
        "relevant_keywords": ["student", "service"],
        "expected_relevant": 3,
    },
    {
        "query": "CI report testing status passed",
        "relevant_keywords": ["report", "tests", "workflow", "passed"],
        "expected_relevant": 2,
    },
    {
        "query": "repository files project structure",
        "relevant_keywords": ["repository", "files"],
        "expected_relevant": 1,
    },
]


def is_relevant(text: str, keywords: list[str]) -> bool:
    lowered = (text or "").lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def evaluate_query(benchmark: dict) -> dict:
    response = retrieve_context(benchmark["query"], 5)
    results = response.get("results", [])[:5]
    relevant = [r for r in results if is_relevant(r.get("text", ""), benchmark["relevant_keywords"])]

    precision_at_5 = len(relevant) / 5
    raw_recall_at_5 = len(relevant) / max(benchmark["expected_relevant"], 1)
    recall_at_5 = min(1.0, raw_recall_at_5)

    return {
        "query": benchmark["query"],
        "retrieved_chunk_ids": [r.get("chunk_id") for r in results],
        "relevant_chunk_ids": [r.get("chunk_id") for r in relevant],
        "p_at_5": precision_at_5,
        "r_at_5": recall_at_5,
    }


def write_metrics_report(results: list[dict]) -> None:
    lines = ["# Retrieval Metrics", ""]
    for result in results:
        lines.append(f"## {result['query']}")
        lines.append(f"- Retrieved: {result['retrieved_chunk_ids']}")
        lines.append(f"- Relevant: {result['relevant_chunk_ids']}")
        lines.append(f"- P@5: {result['p_at_5']}")
        lines.append(f"- R@5: {result['r_at_5']}")
        lines.append("")
    METRICS_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    results = []
    for benchmark in BENCHMARKS:
        result = evaluate_query(benchmark)
        results.append(result)
        print("Query:", result["query"])
        print("Retrieved:", result["retrieved_chunk_ids"])
        print("Relevant:", result["relevant_chunk_ids"])
        print("P@5:", result["p_at_5"])
        print("R@5:", result["r_at_5"])
        print("---")
    write_metrics_report(results)


if __name__ == "__main__":
    main()
