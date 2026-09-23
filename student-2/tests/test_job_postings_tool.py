"""Contract tests for the shared ``job_postings`` MCP tool (student-2 domain).

These assert the retrieval-context shape the student-2 backend relies on:
confidence category, cited posting records, and the Low-confidence fallbacks.
The tool talks to the database service over HTTP, so ``requests.get`` is mocked.
"""

import os
import sys
from unittest.mock import MagicMock, patch

# Make the shared MCP server's ``tools`` module importable.
_MCP_SERVER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "mcp-server")
)
if _MCP_SERVER not in sys.path:
    sys.path.insert(0, _MCP_SERVER)

import tools  # noqa: E402


def _response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


SAMPLE = [
    {
        "JobPosting_Id": 7,
        "Job_Title": "Backend Engineer",
        "Job_Type": "Full time",
        "Location": "Sydney",
        "JobPosting_Status": "Published",
        "Requirements": "Python, Flask, REST APIs",
        "Job_Description": "Build and maintain backend services.",
    }
]


@patch("tools.requests.get")
def test_targeted_query_is_high_confidence_with_citations(mock_get):
    mock_get.return_value = _response(SAMPLE)
    ctx = tools.get_job_postings(query="python")
    assert ctx["confidence"] == "High"
    assert ctx["answer_data"]["count"] == 1
    assert ctx["answer_data"]["postings"][0]["job_posting_id"] == 7
    fields = {(s.get("record_id"), s.get("field")) for s in ctx["sources"]}
    assert (7, "Requirements") in fields
    assert (7, "Job_Description") in fields


@patch("tools.requests.get")
def test_broad_status_listing_is_medium(mock_get):
    mock_get.return_value = _response(SAMPLE)
    ctx = tools.get_job_postings()  # only the default status filter, no query
    assert ctx["confidence"] == "Medium"
    assert ctx["answer_data"]["returned"] == 1


@patch("tools.requests.get")
def test_no_matches_is_low(mock_get):
    mock_get.return_value = _response([])
    ctx = tools.get_job_postings(query="doesnotexist")
    assert ctx["confidence"] == "Low"
    assert ctx["answer_data"]["count"] == 0
    assert ctx["answer_data"]["postings"] == []


@patch("tools.requests.get", side_effect=Exception("connection refused"))
def test_service_unreachable_is_low(mock_get):
    ctx = tools.get_job_postings(query="python")
    assert ctx["confidence"] == "Low"
    assert "error" in ctx["answer_data"]
