def build_user_prompt(
    task_prompt: str, context_prompt: str, evidence: str, review_target: str
) -> str:
    """Build the service-review user prompt, injecting placeholders."""
    task_with_evidence = task_prompt.replace("{{REVIEW_TARGET}}", review_target)
    task_with_evidence = task_with_evidence.replace("{{VALIDATION_EVIDENCE}}", evidence)

    return f"""
{task_with_evidence}

Application Context:
{context_prompt}
""".strip()
