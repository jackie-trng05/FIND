"""Workflow coordinator for the shared FIND multi-agent server.

Runs the three agents in a governed sequence and records evidence:

    Planner + Worker (concurrent) -> Reviewer -> human decision (pending)

Every workflow run is appended to ``workflow_history.jsonl`` (full record) and
``coordination_audit.jsonl`` (compact audit line). Each agent step is bounded by
``AGENT_STEP_TIMEOUT_SECONDS`` so a slow local model can never hang the workflow;
a timed-out step is replaced with a safe placeholder result and the human is
still asked to decide.
"""

import json
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from agents.planner_agent import plan_workflow
from agents.worker_agent import generate_output
from agents.reviewer_agent import review_output

BASE_DIR = Path(__file__).resolve().parent
HISTORY_PATH = BASE_DIR / "workflow_history.jsonl"
AUDIT_PATH = BASE_DIR / "coordination_audit.jsonl"
AGENT_STEP_TIMEOUT_SECONDS = float(os.getenv("AGENT_STEP_TIMEOUT_SECONDS", "120"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


def read_jsonl(path: Path) -> list[Dict[str, Any]]:
    if not path.exists():
        return []
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))
    return records


def run_workflow(user_request: str, caller: str = "student") -> Dict[str, Any]:
    start_time = time.time()
    workflow_id = str(uuid.uuid4())

    # Planner and worker do not depend on each other; run them concurrently.
    executor = ThreadPoolExecutor(max_workers=2)
    planner_future = executor.submit(plan_workflow, user_request)
    worker_future = executor.submit(generate_output, user_request)

    try:
        try:
            planner_result = planner_future.result(timeout=AGENT_STEP_TIMEOUT_SECONDS)
        except FutureTimeoutError:
            planner_future.cancel()
            planner_result = {
                "status": "timeout",
                "agent": "planner_agent",
                "plan": "Planner timed out. Continue with worker evidence and human review.",
                "human_approval_required": True,
            }

        try:
            worker_result = worker_future.result(timeout=AGENT_STEP_TIMEOUT_SECONDS)
        except FutureTimeoutError:
            worker_future.cancel()
            worker_result = {
                "status": "timeout",
                "agent": "worker_agent",
                "job_posting_id": None,
                "evidence_count": 0,
                "evidence": [],
                "output": "Worker timed out before generating output.",
                "human_approval_required": True,
            }
    finally:
        # Do not wait for straggler model calls after timeout.
        executor.shutdown(wait=False, cancel_futures=True)

    reviewer_executor = ThreadPoolExecutor(max_workers=1)
    reviewer_future = reviewer_executor.submit(review_output, user_request, worker_result)
    try:
        try:
            reviewer_result = reviewer_future.result(timeout=AGENT_STEP_TIMEOUT_SECONDS)
        except FutureTimeoutError:
            reviewer_future.cancel()
            reviewer_result = {
                "status": "timeout",
                "agent": "reviewer_agent",
                "review": "Reviewer timed out. Human must decide based on available evidence.",
                "human_approval_required": True,
            }
    finally:
        reviewer_executor.shutdown(wait=False, cancel_futures=True)

    duration_ms = int((time.time() - start_time) * 1000)

    workflow_result = {
        "status": "success",
        "workflow_id": workflow_id,
        "timestamp": now_iso(),
        "duration_ms": duration_ms,
        "caller": caller,
        "user_request": user_request,
        "participating_agents": ["planner_agent", "worker_agent", "reviewer_agent"],
        "planner_result": planner_result,
        "worker_result": worker_result,
        "reviewer_result": reviewer_result,
        "human_decision": {
            "required": True,
            "status": "pending",
            "allowed_values": ["Accept", "Partially Accept", "Reject"],
        },
    }

    audit_record = {
        "workflow_id": workflow_id,
        "timestamp": workflow_result["timestamp"],
        "duration_ms": duration_ms,
        "status": workflow_result["status"],
        "caller": caller,
        "participating_agents": workflow_result["participating_agents"],
        "human_approval_required": True,
        "worker_status": worker_result.get("status"),
        "evidence_count": worker_result.get("evidence_count", 0),
    }

    append_jsonl(HISTORY_PATH, workflow_result)
    append_jsonl(AUDIT_PATH, audit_record)

    return workflow_result


def workflow_status() -> Dict[str, Any]:
    history = read_jsonl(HISTORY_PATH)
    audit = read_jsonl(AUDIT_PATH)
    return {
        "status": "success",
        "workflow_history_count": len(history),
        "audit_record_count": len(audit),
        "latest_workflow": history[-1] if history else None,
    }


if __name__ == "__main__":
    result = run_workflow("Summarise the applications submitted for job posting 1.")
    print(json.dumps(result, indent=2))
