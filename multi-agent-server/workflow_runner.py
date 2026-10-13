"""Run a single multi-agent workflow from the terminal (no HTTP server).

Useful for Lab 10 terminal testing: it exercises planner -> worker -> reviewer
and prints the full workflow record (also appended to the jsonl evidence logs).
"""

import json

from coordinator import run_workflow


def main() -> None:
    result = run_workflow("Summarise the applications submitted for job posting 1.")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
