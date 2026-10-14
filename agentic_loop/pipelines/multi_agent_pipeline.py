"""Prompt builders for multi-agent workflow validation."""


def build_implementation_prompt(task_prompt: str, evidence: str) -> str:
    return f"""{task_prompt}

Review Scope:
Multi-Agent Workflow Coordination

Observed Evidence:
{evidence}

Validate that:
1. Planner, Worker, and Reviewer agents are each implemented with their required entry function
2. The Coordinator wires all three agents into a single governed workflow
3. At least one student backend exposes a Multi-Agent-Mode route for UI integration

Reply in at most 40 words and stay evidence-based.""".strip()


def build_review_prompt(implementation_output: str, evidence: str) -> str:
    return f"""Implementation Recommendation:
{implementation_output}

Observed Evidence:
{evidence}

Validate the multi-agent coordination assessment against the evidence.
Identify any gaps or risks in agent sequencing, evidence grounding, or the
human approval gate before workflow outputs are accepted.

Reply in at most 40 words and stay evidence-based.""".strip()
