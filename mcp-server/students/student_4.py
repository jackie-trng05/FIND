"""Student 4 — Interview Scheduling MCP tool registration.

Exposes the ``interview_details`` retrieval tool over the student-4 interview
domain. The tool body lives in ``tools.get_interview_details`` so it can be unit
tested directly; ``register`` only wires it onto the shared MCP server.
"""

import tools


def register(server) -> None:
    """Register the interview_details tool on the shared FIND MCP server."""

    @server.tool()
    def interview_details(application_id: int) -> dict:
        """Retrieve the interview scheduled for an application.

        Args:
            application_id: The application whose interview should be retrieved.

        Returns a grounded retrieval-context object with the interview datetime,
        meeting link and the structured ``interview_notes`` feedback, citations
        to each ``interviews`` field, and a confidence category based on whether
        an interview exists and its feedback has been written up (feedback
        written -> High, scheduled only -> Medium, none -> Low).
        """
        return tools.get_interview_details(application_id)
