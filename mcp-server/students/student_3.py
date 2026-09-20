"""Student 3 — Applications / Screening MCP tool registration.

Exposes the ``applications_for_job`` retrieval tool over the student-3 application
domain. The tool body lives in ``tools.get_applications_for_job`` so it can be unit
tested directly; ``register`` only wires it onto the shared MCP server.
"""

import tools


def register(server) -> None:
    """Register the applications_for_job tool on the shared FIND MCP server."""

    @server.tool()
    def applications_for_job(job_posting_id: int, status: str = "") -> dict:
        """Retrieve the applications submitted for a job posting.

        Args:
            job_posting_id: The job posting whose applications should be retrieved.
            status: Optional application status filter (e.g. "Submitted").

        Returns a grounded retrieval-context object listing the matching
        applications (with their soft ``resume_id`` link), citations to each
        ``applications`` record, and a confidence category based on the query
        (filtered -> High, unfiltered-with-records -> Medium, none -> Low).
        """
        return tools.get_applications_for_job(job_posting_id, status or None)
