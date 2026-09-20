"""Shared FIND RAG MCP server (stdio transport).

Exposes the three RAG tools over MCP so an MCP client (VS Code MCP extension,
Claude Desktop, or the agentic loop) can drive the shared, non-containerised RAG
pipeline. The tool bodies live in ``rag_pipeline`` so they can be unit tested and
reused by ``rag_http_server`` (the transport the containerised student backends
call through ``host.docker.internal``).
"""

from mcp.server.fastmcp import FastMCP

from rag_pipeline import answer_question as answer_question_impl
from rag_pipeline import refresh_corpus as refresh_corpus_impl
from rag_pipeline import retrieve_context as retrieve_context_impl

mcp = FastMCP("FIND RAG MCP")
AVAILABLE_TOOLS = ["refresh_corpus", "retrieve_context", "answer_question"]


@mcp.tool()
def refresh_corpus(caller: str = "student") -> dict:
    """Rebuild the shared corpus and vector index from FIND evidence."""
    return refresh_corpus_impl(caller=caller)


@mcp.tool()
def retrieve_context(query: str, k: int = 5, caller: str = "student") -> dict:
    """Retrieve the top-k grounded chunks for a query."""
    return retrieve_context_impl(query=query, k=k, caller=caller)


@mcp.tool()
def answer_question(query: str, k: int = 5, caller: str = "student") -> dict:
    """Answer a question grounded only in retrieved context (with citations)."""
    return answer_question_impl(query=query, k=k, caller=caller)


if __name__ == "__main__":
    print("Starting FIND RAG MCP Server (shared, non-containerised)...")
    print("Server status: RUNNING")
    print("Interact with RAG tools from a second terminal.")
    print("Available tools:")
    for tool in AVAILABLE_TOOLS:
        print(f"- {tool}")
    mcp.run()
