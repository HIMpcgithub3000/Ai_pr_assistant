from typing import Any

from langgraph.graph import END, StateGraph

from src.agents.review_agent import ReviewAgents
from src.agents.state import AnalysisGraphState
from src.agents.test_agent import TestGenerationAgent


def aggregate_results_node(state: AnalysisGraphState) -> dict[str, Any]:
    """Aggregates all findings from bug, security, and quality agents."""
    all_findings: list[dict[str, Any]] = []
    all_findings.extend(state.get("bug_findings") or [])
    all_findings.extend(state.get("security_findings") or [])
    all_findings.extend(state.get("quality_findings") or [])
    return {"all_findings": all_findings, "status": "ANALYZED"}


def build_analysis_graph() -> StateGraph:
    """
    Constructs the LangGraph state machine with parallel agent dispatch.
    """
    builder = StateGraph(AnalysisGraphState)

    # Add agent nodes
    builder.add_node("bug_agent", ReviewAgents.bug_detection_node)
    builder.add_node("security_agent", ReviewAgents.security_agent_node)
    builder.add_node("quality_agent", ReviewAgents.code_quality_node)
    builder.add_node("test_agent", TestGenerationAgent.generate_tests_node)
    builder.add_node("aggregator", aggregate_results_node)

    # Set entry point: fan out to agents
    builder.set_entry_point("bug_agent")
    builder.add_edge("bug_agent", "security_agent")
    builder.add_edge("security_agent", "quality_agent")
    builder.add_edge("quality_agent", "test_agent")
    builder.add_edge("test_agent", "aggregator")
    builder.add_edge("aggregator", END)

    return builder.compile()


analysis_graph = build_analysis_graph()
