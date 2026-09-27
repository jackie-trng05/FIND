"""Prompt builders for MCP implementation validation."""


def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""{task_prompt}

Observed Evidence:
{evidence}

Assess every student row against the Release 1 requirements. A shared MCP server alone
does not satisfy a student's integration. Treat every MISSING item as an incomplete
requirement and name the exact student and missing evidence. Do not infer success.
Reply using only the evidence.""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""Implementation Assessment:
{implementation_output}

Observed Evidence:
{evidence}

Reject any claim that MCP is complete when a student row has MISSING evidence. Identify
the exact student gaps across frontend request wiring, backend route/client presence, or
CI disablement. Reply using only the evidence.""".strip()