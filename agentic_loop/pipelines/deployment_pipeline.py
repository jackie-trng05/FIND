"""Prompt builders for Azure cloud deployment validation (cloud)."""


def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""{task_prompt}

Review Scope:
Azure Cloud Deployment

Observed Evidence:
{evidence}

Reply in at most 80 words and stay evidence-based.""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""Implementation Recommendation:
{implementation_output}

Observed Evidence:
{evidence}

Validate the deployment assessment against the evidence.
Identify any gaps or risks in managed identity, ingress isolation, or deployment validation.

Reply in at most 40 words and stay evidence-based.""".strip()
