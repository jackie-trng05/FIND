from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModeConfig:
    key: str  # collector selector: "db" | "endpoints" | "architecture" | "devops"
    label: str
    kind: str  # pipeline selector: "service" | "architecture" | "devops"
    prompt_family: str
    review_target: str = ""
    scope: str | None = None  # student directory name for scoped architecture/devops evidence


def build_base_modes() -> list[ModeConfig]:
    return [
        ModeConfig(
            key="db",
            label="Shared DB",
            kind="service",
            prompt_family="service",
            review_target="Shared Database",
        ),
        ModeConfig(
            key="endpoints",
            label="Shared Endpoints",
            kind="service",
            prompt_family="service",
            review_target="Shared API Endpoints",
        ),
        ModeConfig(
            key="architecture",
            label="Platform Architecture",
            kind="architecture",
            prompt_family="architecture",
            scope=None,
        ),
    ]


def discover_student_arch_modes(prompts_base: Path) -> list[ModeConfig]:
    """Auto-discover per-student architecture review prompts.

    Each student owns a folder under prompts/architecture/students/<student-id>/
    containing at least architecture_task_prompt.txt. A folder is only picked up
    once that task prompt exists, so students self-register by adding their prompt.
    """
    modes: list[ModeConfig] = []
    students_root = prompts_base / "prompts" / "architecture" / "students"
    if not students_root.exists():
        return modes

    for child in sorted(students_root.iterdir()):
        if child.is_dir() and (child / "architecture_task_prompt.txt").exists():
            student_id = child.name
            modes.append(
                ModeConfig(
                    key="architecture",
                    label=f"Architecture: {student_id}",
                    kind="architecture",
                    prompt_family=f"architecture/students/{student_id}",
                    scope=student_id,
                )
            )
    return modes


def discover_student_devops_modes(prompts_base: Path) -> list[ModeConfig]:
    """Auto-discover per-student DevOps review targets.

    Each student owns a CI workflow at .github/workflows/<student>-ci.yml and a downloaded
    evidence pack (report.json, report.md, run-view.md, pytest artifacts) under
    docs/release-0/reports/<student>/. A student is only picked up once both exist, so students
    self-register by landing their evidence pack.
    """
    modes: list[ModeConfig] = []
    repo_root = prompts_base.parent
    reports_root = repo_root / "docs" / "release-0" / "reports"
    workflows_root = repo_root / ".github" / "workflows"
    if not reports_root.exists():
        return modes

    for child in sorted(reports_root.iterdir()):
        if not child.is_dir():
            continue
        student_id = child.name
        workflow_path = workflows_root / f"{student_id}-ci.yml"
        if workflow_path.exists() and (child / "report.json").exists():
            modes.append(
                ModeConfig(
                    key="devops",
                    label=f"DevOps: {student_id}",
                    kind="devops",
                    prompt_family="devops",
                    scope=student_id,
                )
            )
    return modes


def build_modes(prompts_base: Path) -> list[ModeConfig]:
    return (
        build_base_modes()
        + discover_student_arch_modes(prompts_base)
        + discover_student_devops_modes(prompts_base)
    )
