"""Launcher for the FIND modular agentic loop.

Implements the PLAN -> OBSERVE -> IMPLEMENT -> REVIEW -> ADAPT workflow for the
integrated FIND recruitment platform. Deterministic collectors gather live
evidence from the running Docker services, then a local Ollama LLM reviews it.

The real engine lives alongside this launcher in the ``agentic_loop`` package.
Run the stack first (docker-compose up --build), then:

    python agentic_loop/agentic_loop.py
"""

from pathlib import Path
import sys


ENGINE_DIR = Path(__file__).resolve().parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))

from main import main


if __name__ == "__main__":
    main()
