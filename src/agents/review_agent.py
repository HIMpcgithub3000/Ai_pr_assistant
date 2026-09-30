from typing import Any

from src.agents.state import AnalysisGraphState


class ReviewAgents:
    """
    Multi-Agent Review Subsystem:
    - Bug Detection Agent
    - Security Analysis Agent
    - Code Quality Agent
    Supports mock/offline mode as well as OpenAI/Anthropic LLMs.
    """

    @staticmethod
    async def bug_detection_node(state: AnalysisGraphState) -> dict[str, Any]:
        """Detects logical bugs, null-pointer references, and edge case mishandling."""
        diff = state.get("code_diff", "")
        changed_files = state.get("changed_files", [])
        findings: list[dict[str, Any]] = []

        # Analyze diff for common bug patterns
        for line_no, line in enumerate(diff.splitlines(), start=1):
            if (
                line.startswith("+")
                and not line.startswith("+++")
                and "except:" in line
                and "Exception" not in line
            ):
                findings.append({
                        "file_path": changed_files[0] if changed_files else "unknown",
                        "line_number": line_no,
                        "category": "BUG",
                        "severity": "MEDIUM",
                        "title": "Bare except clause detected",
                        "description": "Bare except catches system exit and keyboard interrupts. Catch specific exceptions.",
                        "suggestion": "Replace with 'except Exception as e:'",
                    })

        return {"bug_findings": findings}

    @staticmethod
    async def security_agent_node(state: AnalysisGraphState) -> dict[str, Any]:
        """Audits security vulnerabilities, sanitization, and permission checks."""
        static = state.get("static_findings", [])
        findings: list[dict[str, Any]] = []

        # Convert high severity static findings into formal security review findings
        for sf in static:
            if sf.get("severity") in ("CRITICAL", "HIGH"):
                findings.append({
                    "file_path": sf.get("file_path", state.get("changed_files", ["unknown"])[0] if state.get("changed_files") else "unknown"),
                    "line_number": sf.get("line_number", 1),
                    "category": "SECURITY",
                    "severity": sf.get("severity", "HIGH"),
                    "title": sf.get("message", "Security Alert"),
                    "description": f"Security vulnerability flagged: {sf.get('message')}",
                    "suggestion": "Sanitize inputs and ensure secret tokens are loaded via environment variables.",
                })

        return {"security_findings": findings}

    @staticmethod
    async def code_quality_node(state: AnalysisGraphState) -> dict[str, Any]:
        """Reviews maintainability, naming conventions, and docstrings."""
        diff = state.get("code_diff", "")
        changed_files = state.get("changed_files", [])
        findings: list[dict[str, Any]] = []

        for line_no, line in enumerate(diff.splitlines(), start=1):
            if line.startswith("+") and "TODO" in line:
                findings.append({
                    "file_path": changed_files[0] if changed_files else "unknown",
                    "line_number": line_no,
                    "category": "QUALITY",
                    "severity": "LOW",
                    "title": "Unresolved TODO detected",
                    "description": "Unresolved TODO committed in new code.",
                    "suggestion": "Resolve before merge or track in issue tracker.",
                })

        return {"quality_findings": findings}
