"""Prompt builders for pre-commit security-scan validation (cloud)."""


def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""{task_prompt}

Review Scope:
Pre-Commit Test Implementation

Observed Evidence:
{evidence}

Reply in at most 60 words and stay evidence-based.""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""Implementation Recommendation:
{implementation_output}

Observed Evidence:
{evidence}

Validate the pre-commit test assessment against the evidence.
Identify any gaps or risks in scan coverage or commit-blocking behavior.

Reply in at most 40 words and stay evidence-based.""".strip()
