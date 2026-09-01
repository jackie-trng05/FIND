from pathlib import Path

from dotenv import load_dotenv

from config.review_config import build_modes
from core.ai_runner import AIRunner
from core.orchestrator import run_mode
from core.prompt_registry import PromptRegistry
from core.reporter import print_menu, print_prompt_map, print_result


def _resolve_roots() -> tuple[Path, Path, Path]:
    module_dir = Path(__file__).resolve().parent  # agentic_loop package (holds prompts/)
    app_dir = module_dir.parent  # FIND repository root (collector evidence source)
    repo_root = app_dir
    return module_dir, app_dir, repo_root


def _print_mode_mapping(prompts_base: Path) -> None:
    prompt_map = {
        "Shared DB": prompts_base / "prompts" / "service",
        "Shared Endpoints": prompts_base / "prompts" / "service",
        "Architecture": prompts_base / "prompts" / "architecture",
        "Student Architecture": prompts_base / "prompts" / "architecture" / "students",
        "Student DevOps": prompts_base / "prompts" / "devops",
    }
    print_prompt_map({key: str(path) for key, path in prompt_map.items()})


def main() -> None:
    module_dir, app_dir, repo_root = _resolve_roots()
    load_dotenv(dotenv_path=app_dir / ".env")

    prompts = PromptRegistry(module_dir)
    ai = AIRunner()

    print("FIND AGENTIC LOOP (MODULAR)")
    print("PLAN -> OBSERVE -> IMPLEMENT -> REVIEW -> ADAPT")
    _print_mode_mapping(module_dir)

    while True:
        # Re-discover each loop so student prompts added at runtime appear immediately.
        modes = build_modes(module_dir)
        print_menu(modes)
        choice = input("Choose a review target: ").strip().lower()

        if choice == "0":
            print("Loop closed.")
            break

        if choice == "a":
            for mode in modes:
                result = run_mode(mode, app_dir, repo_root, prompts, ai)
                print_result(mode.label, result)
            continue

        if not choice.isdigit():
            print("Invalid choice. Enter a listed number, 'A' to run all, or '0' to exit.")
            continue

        index = int(choice)
        if index < 1 or index > len(modes):
            print("Invalid choice. Enter a listed number, 'A' to run all, or '0' to exit.")
            continue

        mode = modes[index - 1]
        result = run_mode(mode, app_dir, repo_root, prompts, ai)
        print_result(mode.label, result)


if __name__ == "__main__":
    main()
