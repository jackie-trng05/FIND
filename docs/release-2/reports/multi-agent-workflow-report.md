# Release 2 Multi-Agent Workflow Report

**Status:** COMPLETE

Evidence: [workflow history](../../../multi-agent-server/workflow_history.jsonl)
and [coordination audit](../../../multi-agent-server/coordination_audit.jsonl).

PASS means the student is present as a caller in workflow history and has a
coordination audit record, identified directly or by a matching workflow ID.

| Student | Workflow history | Coordination audit |
| --- | --- | --- |
| student-1 | PASS | PASS |
| student-2 | PASS | PASS |
| student-3 | PASS | PASS |
| student-4 | PASS | PASS |
| student-5 | PASS | PASS |

## Human Decision Examples

One recorded example per decision type per student is listed below. All five
students have Accept, Reject, and Correction records.

| Student | Status (Accept/Reject/Correction) | Workflow ID | Reason | Evidence | Workflow history | Coordination audit |
| --- | --- | --- | --- | --- | --- | --- |
| student-1 | Accept | 04d3a611-4ea1-4fad-a0ca-12a0bb7dc2db | The summary is grounded and uses both profile and resume information. | '7 years of experience' in the summary, plus the job at FIND, are both text from the resume. | [Line 39](../../../multi-agent-server/workflow_history.jsonl#L39) | [Line 73](../../../multi-agent-server/coordination_audit.jsonl#L73) |
| student-1 | Reject | cb2257d6-5602-488f-8aa3-6bbc4136c8d6 | The summary is accurate but too short to summarise Emily's resume highlights | Only uses "7 years of experience building software services" from the resume | [Line 35](../../../multi-agent-server/workflow_history.jsonl#L35) | [Line 69](../../../multi-agent-server/coordination_audit.jsonl#L69) |
| student-1 | Correction | 66d4bd02-a0ac-4567-af80-6321e570fbdb | Summary is correct but places some information from the resume under the 'applicant profile' section without clarification. | States the applicant profile summary includes "7 years of experience as a full-stack developer" when this is information from the resume. | [Line 36](../../../multi-agent-server/workflow_history.jsonl#L36) | [Line 71](../../../multi-agent-server/coordination_audit.jsonl#L71) |
| student-2 | Accept | 320f1f72-4c11-45b1-bbc2-19df46e96b0a | Summary matches the applicant pool and highlights top candidates. | 12 application records for posting 1 | [Line 20](../../../multi-agent-server/workflow_history.jsonl#L20) | [Line 40](../../../multi-agent-server/coordination_audit.jsonl#L40) |
| student-2 | Reject | c04ec9be-0dfe-45bd-8a81-a8838f8ac376 | The flags were inaccurate; several flagged applicants do list Docker. | Application skill tags for posting 5 | [Line 23](../../../multi-agent-server/workflow_history.jsonl#L23) | [Line 46](../../../multi-agent-server/coordination_audit.jsonl#L46) |
| student-2 | Correction | 7a77b93e-72a3-4e65-8b72-dd541d8ebb4e | Ranking ignored the HTMX experience requirement; re-rank by HTMX skill. | Applicant resumes for posting 2 | [Line 21](../../../multi-agent-server/workflow_history.jsonl#L21) | [Line 42](../../../multi-agent-server/coordination_audit.jsonl#L42) |
| student-3 | Accept | 99dec42e-ce90-4837-8a63-a99d57e356e7 | Summary matches the two grounded application records. | Application 20 (User 6, Job 4), Application 8 (User 8, Job 4). | [Line 1](../../../multi-agent-server/workflow_history.jsonl#L1) | [Line 2](../../../multi-agent-server/coordination_audit.jsonl#L2) |
| student-3 | Reject | 3f0f8286-f540-44a0-8413-c3a990736616 | Output drew conclusions not supported by the resume evidence. | Resume 6 text; application 20 for User 6. | [Line 4](../../../multi-agent-server/workflow_history.jsonl#L4) | [Line 8](../../../multi-agent-server/coordination_audit.jsonl#L8) |
| student-3 | Correction | c05734d8-5b95-4689-a93c-605d326610ab | Status for one applicant was stated without a supporting record. | Application 20 status: Shortlisted (grounded). | [Line 2](../../../multi-agent-server/workflow_history.jsonl#L2) | [Line 4](../../../multi-agent-server/coordination_audit.jsonl#L4) |
| student-4 | Accept | 4d8feda9-dae0-4074-a8a8-837b55eb2dd0 | All scheduled interviews are listed with their correct times from the records. | Interviews 1-10 (interview_datetime fields). | [Line 14](../../../multi-agent-server/workflow_history.jsonl#L14) | [Line 28](../../../multi-agent-server/coordination_audit.jsonl#L28) |
| student-4 | Reject | f731733f-e646-4157-97e3-1b942576cd73 | Output claimed notes were missing where interview_notes were present. | Interview records with populated interview_notes. | [Line 17](../../../multi-agent-server/workflow_history.jsonl#L17) | [Line 34](../../../multi-agent-server/coordination_audit.jsonl#L34) |
| student-4 | Correction | bfbf0d26-4e92-4be9-bce2-51b0b340258a | One interview with a blank meeting link was omitted; list corrected. | Interview records; interview_link empty on at least one row. | [Line 15](../../../multi-agent-server/workflow_history.jsonl#L15) | [Line 30](../../../multi-agent-server/coordination_audit.jsonl#L30) |
| student-5 | Accept | abfa0273-0a0f-43d4-bdd5-ae026c407ea5 | Evidence matches application records | Applications 1 and 11 for posting 1 | [Line 33](../../../multi-agent-server/workflow_history.jsonl#L33) | [Line 66](../../../multi-agent-server/coordination_audit.jsonl#L66) |
| student-5 | Reject | ce7cbe00-af21-4100-9b70-7eff84426783 | Candidate's resume and cover letter evidence is not included in the summary. | Details are not provided, worker agent only states "submitted an application" | [Line 40](../../../multi-agent-server/workflow_history.jsonl#L40) | [Line 75](../../../multi-agent-server/coordination_audit.jsonl#L75) |
| student-5 | Correction | 8ad25253-eaf0-4d3c-b546-fd958c6d5c83 | Results are grounded but not detailed. | Job statuses are correct and mentioned, but not much other detail is provided, e.g worker agent states "Shortlisted", "Submitted", "Draft". | [Line 41](../../../multi-agent-server/workflow_history.jsonl#L41) | [Line 77](../../../multi-agent-server/coordination_audit.jsonl#L77) |