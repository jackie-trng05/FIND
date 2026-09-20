"""Student 5 — Candidate Evaluation MCP tool registration.

Exposes the ``evaluation_scores`` retrieval tool over the student-5 evaluation
domain. The tool body lives in ``tools.get_evaluation_scores`` so it can be unit
tested directly; ``register`` only wires it onto the shared MCP server.
"""

import tools


def register(server) -> None:
    """Register the evaluation_scores tool on the shared FIND MCP server."""

    @server.tool()
    def evaluation_scores(application_id: int) -> dict:
        """Retrieve a candidate's evaluation scorecard for an application.

        Args:
            application_id: The application whose evaluation should be retrieved.

        Returns a grounded retrieval-context object with the five criteria
        scores, the overall score and the Hire/Reject recommendation, citations
        to each ``evaluations`` field, and a confidence category based on whether
        an evaluation exists (finalized -> High, draft -> Medium, none -> Low).
        """
        return tools.get_evaluation_scores(application_id)
