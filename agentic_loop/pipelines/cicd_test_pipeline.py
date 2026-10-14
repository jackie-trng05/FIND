"""Prompt builders for post-commit (CI/CD) test validation (cloud)."""


def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""{task_prompt}

Review Scope:
Post-Commit (CI/CD) Test Results

Observed Evidence:
{evidence}

Reply in at most 60 words and stay evidence-based.""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""Implementation Recommendation:
{implementation_output}

Observed Evidence:
{evidence}

Validate the CI/CD test results assessment against the evidence.
Identify any gaps or risks in test coverage or evidence completeness.

Reply in at most 40 words and stay evidence-based.""".strip()
