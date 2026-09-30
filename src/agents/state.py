from typing import Any, TypedDict


class AnalysisGraphState(TypedDict):
    analysis_id: str
    repository_id: str
    pr_number: int
    head_sha: str
    base_sha: str
    code_diff: str
    changed_files: list[str]
    checkout_dir: str

    # Inputs from deterministic layer
    static_findings: list[dict[str, Any]]
    rag_context: list[dict[str, Any]]

    # Outputs from LangGraph parallel agents
    bug_findings: list[dict[str, Any]]
    security_findings: list[dict[str, Any]]
    quality_findings: list[dict[str, Any]]
    generated_test_code: str | None

    # Aggregated results
    all_findings: list[dict[str, Any]]
    circuit_broken: bool
    status: str
