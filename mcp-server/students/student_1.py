"""Student 1 — Applicant Profile MCP tool registration.

Exposes the ``applicant_profile`` retrieval tool over the student-1 profile
domain. The tool body lives in ``tools.get_applicant_profile`` so it can be
unit tested directly; ``register`` only wires it onto the shared MCP server.
"""

import tools


def register(server) -> None:
    """Register the applicant_profile tool on the shared FIND MCP server."""

    @server.tool()
    def applicant_profile(user_id: int) -> dict:
        """Retrieve an applicant's profile fields and resume text/metadata.

        Args:
            user_id: The user whose profile should be retrieved.

        Returns a grounded retrieval-context object with the profile fields
        (phone, location, professional_title, summary, interests) and the
        linked resume's metadata plus its extracted text (best-effort PDF
        extraction, truncated), citations to each ``profiles``/``resumes``
        field, and a confidence category based on field completeness (all
        core fields + a readable resume -> High, partially complete ->
        Medium, no profile on record -> Low).
        """
        return tools.get_applicant_profile(user_id)
