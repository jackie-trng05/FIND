"""Prompt builders for RAG implementation validation."""


def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""{task_prompt}

Observed Evidence:
{evidence}

Validate the RAG server, required tools, grounding, citations, and confidence contract.
Reply using only the evidence.""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""Implementation Assessment:
{implementation_output}

Observed Evidence:
{evidence}

Review the assessment for retrieval, citation, confidence, or unsupported-answer risks.
Reply using only the evidence.""".strip()