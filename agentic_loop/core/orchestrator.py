from collectors import architecture_collector, db_collector, devops_collector, endpoints_collector
from config.review_config import ModeConfig
from core.ai_runner import AIRunner
from core.prompt_registry import PromptRegistry
from pipelines import architecture_pipeline, devops_pipeline, service_pipeline


COLLECTORS = {
    "db": db_collector.collect,
    "endpoints": endpoints_collector.collect,
    "architecture": architecture_collector.collect,
    "devops": devops_collector.collect,
}

ARCH_SYSTEM_PROMPT = "implementation/architecture_system_prompt.txt"
ARCH_TASK_PROMPT = "implementation/architecture_task_prompt.txt"
ARCH_REVIEW_PROMPT = "review/agent_review_prompt.txt"

DEVOPS_TASK_PROMPT = "implementation/devops_pipeline_review_prompt.txt"
DEVOPS_REVIEW_PROMPT = "review/devops_evidence_review_prompt.txt"
DEVOPS_SYSTEM_PROMPT = (
    "You are a precise DevOps review assistant. "
    "Use only supplied evidence and reply in at most 30 words."
)


def _stage(mode_label: str, step: str, message: str) -> None:
    print(f"[{mode_label}][{step}] {message}")


def _read_or_default(prompts: PromptRegistry, family: str, relative_file: str, default: str) -> str:
    try:
        return prompts.read(family, relative_file)
    except FileNotFoundError:
        return default


def _run_service_mode(mode: ModeConfig, prompts: PromptRegistry, ai: AIRunner, evidence: str) -> str:
    _stage(mode.label, "PROMPTS", "Loading service prompt family")
    system_prompt = prompts.read("service", "implementation/system_prompt.txt")
    task_prompt = prompts.read("service", "implementation/task_prompt.txt")
    context_prompt = prompts.read("service", "implementation/context_prompt.txt")
    _stage(mode.label, "PROMPTS", "Loaded implementation prompt set")

    user_prompt = service_pipeline.build_user_prompt(
        task_prompt, context_prompt, evidence, mode.review_target
    )

    _stage(mode.label, "LLM", "Running implementation model")
    output, err = ai.call(system_prompt, user_prompt, review=False)
    if err:
        _stage(mode.label, "LLM", "Failed")
        return f"MODEL FAILED: {err}"
    _stage(mode.label, "LLM", "Complete")
    _stage(mode.label, "DONE", "Review complete")
    return f"OBSERVE: {evidence}\n\nREVIEW: {output}"


def _resolve_architecture_prompts(mode: ModeConfig, prompts: PromptRegistry) -> tuple[str, str, str]:
    shared_system = prompts.read("architecture", ARCH_SYSTEM_PROMPT)
    shared_review = prompts.read("architecture", ARCH_REVIEW_PROMPT)

    if mode.prompt_family == "architecture":
        task_prompt = prompts.read("architecture", ARCH_TASK_PROMPT)
        return shared_system, task_prompt, shared_review

    # Student-owned family: their task prompt is required; system/review prompts
    # fall back to the shared platform prompts unless a student overrides them.
    system_prompt = _read_or_default(
        prompts, mode.prompt_family, "architecture_system_prompt.txt", shared_system
    )
    task_prompt = prompts.read(mode.prompt_family, "architecture_task_prompt.txt")
    review_prompt = _read_or_default(
        prompts, mode.prompt_family, "agent_review_prompt.txt", shared_review
    )
    return system_prompt, task_prompt, review_prompt


def _run_architecture_mode(mode: ModeConfig, prompts: PromptRegistry, ai: AIRunner, evidence: str) -> str:
    _stage(mode.label, "PROMPTS", f"Loading architecture prompts: {mode.prompt_family}")
    system_prompt, task_prompt, review_system_prompt = _resolve_architecture_prompts(mode, prompts)
    _stage(mode.label, "PROMPTS", "Loaded architecture prompts")

    implementation_user_prompt = architecture_pipeline.build_implementation_prompt(task_prompt, evidence)

    _stage(mode.label, "LLM", "Running architecture model")
    implementation_output, err = ai.call(system_prompt, implementation_user_prompt, review=False)
    if err:
        _stage(mode.label, "LLM", "Failed")
        return f"MODEL FAILED: {err}"
    _stage(mode.label, "LLM", "Architecture model complete")

    review_user_prompt = architecture_pipeline.build_review_prompt(implementation_output, evidence)
    _stage(mode.label, "LLM", "Running review model")
    review_output, review_err = ai.call(review_system_prompt, review_user_prompt, review=True)
    if review_err:
        review_output = review_err
        _stage(mode.label, "LLM", "Review model failed")
    else:
        _stage(mode.label, "LLM", "Review model complete")

    _stage(mode.label, "DONE", "Review complete")
    return (
        f"OBSERVE: {evidence}\n\n"
        f"ARCHITECTURE: {implementation_output}\n"
        f"REVIEW: {review_output}"
    )


def _run_devops_mode(mode: ModeConfig, prompts: PromptRegistry, ai: AIRunner, evidence: str) -> str:
    _stage(mode.label, "PROMPTS", "Loading DevOps prompt family")
    task_prompt = prompts.read("devops", DEVOPS_TASK_PROMPT)
    implementation_user_prompt = devops_pipeline.build_implementation_prompt(task_prompt, evidence)
    _stage(mode.label, "PROMPTS", "Loaded DevOps implementation prompt")

    _stage(mode.label, "LLM", "Running DevOps implementation model")
    implementation_output, err = ai.call(DEVOPS_SYSTEM_PROMPT, implementation_user_prompt, review=False)
    if err:
        _stage(mode.label, "LLM", "Failed")
        return f"MODEL FAILED: {err}"
    _stage(mode.label, "LLM", "DevOps implementation model complete")

    review_system_prompt = prompts.read("devops", DEVOPS_REVIEW_PROMPT)
    review_user_prompt = devops_pipeline.build_review_prompt(implementation_output, evidence)
    _stage(mode.label, "PROMPTS", "Loaded DevOps review prompt")
    _stage(mode.label, "LLM", "Running DevOps review model")
    review_output, review_err = ai.call(review_system_prompt, review_user_prompt, review=True)
    if review_err:
        review_output = review_err
        _stage(mode.label, "LLM", "DevOps review model failed")
    else:
        _stage(mode.label, "LLM", "DevOps review model complete")

    _stage(mode.label, "DONE", "Review complete")
    return (
        f"OBSERVE: {evidence}\n\n"
        f"DEVOPS: {implementation_output}\n"
        f"REVIEW: {review_output}"
    )


def run_mode(mode: ModeConfig, app_dir, repo_root, prompts: PromptRegistry, ai: AIRunner) -> str:
    _stage(mode.label, "START", "Starting review flow")
    _stage(mode.label, "OBSERVE", "Collecting evidence")

    collector = COLLECTORS[mode.key]
    if mode.key in ("architecture", "devops"):
        ok, evidence = collector(app_dir, repo_root, mode.scope)
    else:
        ok, evidence = collector(app_dir, repo_root)

    if not ok:
        _stage(mode.label, "OBSERVE", "Failed")
        return f"OBSERVE FAILED: {evidence}"
    _stage(mode.label, "OBSERVE", "Complete")

    if mode.kind == "service":
        return _run_service_mode(mode, prompts, ai, evidence)
    if mode.kind == "architecture":
        return _run_architecture_mode(mode, prompts, ai, evidence)
    if mode.kind == "devops":
        return _run_devops_mode(mode, prompts, ai, evidence)
    return "Unknown mode."
