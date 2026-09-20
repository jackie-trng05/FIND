"""Student 2 — Job Posting Management MCP tool registration.

Exposes the ``job_postings`` retrieval tool over the student-2 job-posting
domain. The tool body lives in ``tools.get_job_postings`` so it can be unit
tested directly; ``register`` only wires it onto the shared MCP server.
"""

import tools


def register(server) -> None:
    """Register the job_postings tool on the shared FIND MCP server."""

    @server.tool()
    def job_postings(
        query: str = "", job_type: str = "", location: str = "", status: str = "Published"
    ) -> dict:
        """Retrieve job postings matching an optional filter.

        Args:
            query: Free-text match over title / description / requirements.
            job_type: Exact job type (e.g. "Full time").
            location: Location substring match.
            status: Posting status (defaults to "Published").

        Returns a grounded retrieval-context object listing the matching
        postings (title, type, location, requirements, description) with a
        citation per posting to its ``job_postings`` Requirements/Job_Description
        fields, and a confidence category (targeted match -> High, broad listing
        -> Medium, no match -> Low).
        """
        return tools.get_job_postings(
            query=query, job_type=job_type, location=location, status=status
        )
