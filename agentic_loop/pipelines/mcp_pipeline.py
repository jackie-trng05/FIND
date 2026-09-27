"""Prompt builders for MCP implementation validation."""


def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""{task_prompt}

Observed Evidence:
{evidence}

Validate the MCP server structure, tool coverage, backend boundary, and grounding contract.
Reply using only the evidence.""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""Implementation Assessment:
{implementation_output}

Observed Evidence:
{evidence}

Review the assessment for missing tools, boundary risks, or unsupported claims.
Reply using only the evidence.""".strip()