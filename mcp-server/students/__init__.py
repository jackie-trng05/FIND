"""Per-student MCP retrieval tools for the FIND platform.

Each module here registers ONE retrieval tool over its student feature's domain
(applicant_profile, job_postings, applications_for_job, interview_details,
evaluation_scores). ``server.register_student_tools`` imports each module and
calls its ``register(server)`` so students self-register their tool without
touching the shared server wiring.
"""
