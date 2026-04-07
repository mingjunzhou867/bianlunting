"""Agent factory helpers."""

from agents.agent_auditor import AuditChallengeAgent
from agents.agent_empirical import EmpiricalReasoningAgent
from agents.agent_explorer import ExploratoryAgent
from agents.agent_lenient import LenientBusinessAgent
from agents.agent_strict import StrictComplianceAgent
from agents.base_agent import AgentJudgment, BaseAgent, format_evidence_bundle


def create_all_agents() -> list[BaseAgent]:
    """Return the default five debate agents in a stable order."""

    return [
        StrictComplianceAgent(),
        LenientBusinessAgent(),
        ExploratoryAgent(),
        EmpiricalReasoningAgent(),
        AuditChallengeAgent(),
    ]


__all__ = [
    "BaseAgent",
    "AgentJudgment",
    "format_evidence_bundle",
    "StrictComplianceAgent",
    "LenientBusinessAgent",
    "ExploratoryAgent",
    "EmpiricalReasoningAgent",
    "AuditChallengeAgent",
    "create_all_agents",
]
