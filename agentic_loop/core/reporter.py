def print_prompt_map(mapping: dict[str, str]) -> None:
    print("PROMPT PATH MAP")
    for label, path in mapping.items():
        print(f"- {label}: {path}")


def print_menu(modes) -> None:
    print()
    print("=" * 70)
    print("FIND AGENTIC REVIEW MENU")
    for index, mode in enumerate(modes, start=1):
        print(f"{index} - {mode.label}")
    print("A - Run All")
    print("0 - Exit")
    print("=" * 70)


def print_result(title: str, text: str) -> None:
    print()
    print(f"RUNNING: {title}")
    print(text)
