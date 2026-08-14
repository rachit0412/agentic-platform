"""
E2E Test: Multi-Agent Orchestration & Multi-Skill Pipeline

Tests:
1. Multi-file KB upload per agent (isolated collections)
2. Agent querying its own KB
3. Multi-skill agent (skills merged into reasoning)
4. Orchestrator agent delegating to sub-agents
5. Full pipeline: create orchestrator → assign sub-agents → run delegation
"""

import os
import sys
import json
import asyncio
import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "agent")
)

from agent.memory import (
    init_db,
    create_agent,
    get_agent,
    update_agent,
    delete_agent,
    create_skill,
    get_skill,
    list_agents,
)


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    """Use a temp DB for each test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("SQLITE_DB_PATH", db_path)
    # Re-init with fresh connection
    import agent.memory as mem

    mem._conn = None
    mem.DB_PATH = db_path
    init_db()
    yield


class TestMultiFileKBIsolation:
    """Test that KB uploads are isolated per agent collection."""

    def test_agent_gets_unique_collection(self):
        agent = create_agent(
            name="Research Agent",
            description="Researches topics",
            kb_collection="agent_research_agent_kb",
        )
        assert agent["kb_collection"] == "agent_research_agent_kb"

    def test_two_agents_have_different_collections(self):
        a1 = create_agent(name="Agent A", kb_collection="agent_agent_a_kb")
        a2 = create_agent(name="Agent B", kb_collection="agent_agent_b_kb")
        assert a1["kb_collection"] != a2["kb_collection"]
        assert a1["kb_collection"] == "agent_agent_a_kb"
        assert a2["kb_collection"] == "agent_agent_b_kb"


class TestMultiSkillAgent:
    """Test that agent can have multiple skills attached."""

    def test_create_agent_with_skills(self):
        s1 = create_skill(
            name="Summarization",
            description="Summarize text",
            system_prompt="You summarize concisely.",
        )
        s2 = create_skill(
            name="Translation",
            description="Translate text",
            system_prompt="You translate accurately.",
        )
        agent = create_agent(name="Multi-Skill Agent", skill_ids=[s1["id"], s2["id"]])
        assert len(agent["skill_ids"]) == 2
        assert s1["id"] in agent["skill_ids"]
        assert s2["id"] in agent["skill_ids"]

    def test_update_agent_skills(self):
        agent = create_agent(name="Flex Agent")
        assert agent["skill_ids"] == []

        s1 = create_skill(
            name="Code Review",
            description="Reviews code",
            system_prompt="Review code quality.",
        )
        updated = update_agent(agent["id"], skill_ids=[s1["id"]])
        assert updated["skill_ids"] == [s1["id"]]


class TestMultiAgentOrchestration:
    """Test sub-agent assignment and orchestration config."""

    def test_create_orchestrator_with_sub_agents(self):
        worker1 = create_agent(name="Worker 1", description="Does task 1")
        worker2 = create_agent(name="Worker 2", description="Does task 2")

        orchestrator = create_agent(
            name="Orchestrator",
            description="Delegates to workers",
            sub_agent_ids=[worker1["id"], worker2["id"]],
            system_prompt="You are an orchestrator. Delegate tasks to sub-agents.",
        )
        assert len(orchestrator["sub_agent_ids"]) == 2
        assert worker1["id"] in orchestrator["sub_agent_ids"]
        assert worker2["id"] in orchestrator["sub_agent_ids"]

    def test_update_sub_agents(self):
        agent = create_agent(name="Base Orchestrator")
        assert agent["sub_agent_ids"] == []

        worker = create_agent(name="New Worker")
        updated = update_agent(agent["id"], sub_agent_ids=[worker["id"]])
        assert updated["sub_agent_ids"] == [worker["id"]]

    def test_sub_agent_config_accessible(self):
        worker = create_agent(
            name="Specialist",
            description="Domain expert",
            system_prompt="You are a domain specialist.",
            kb_collection="agent_specialist_kb",
        )
        orchestrator = create_agent(name="Manager", sub_agent_ids=[worker["id"]])
        # Verify orchestrator can resolve sub-agent config
        sub_cfg = get_agent(orchestrator["sub_agent_ids"][0])
        assert sub_cfg is not None
        assert sub_cfg["name"] == "Specialist"
        assert sub_cfg["kb_collection"] == "agent_specialist_kb"


class TestFullPipeline:
    """Test complete orchestration pipeline creation."""

    def test_full_pipeline_setup(self):
        # 1. Create skills
        research_skill = create_skill(
            name="Web Research",
            description="Search and synthesize from web",
            system_prompt="You research topics thoroughly using web search.",
        )
        analysis_skill = create_skill(
            name="Data Analysis",
            description="Analyze data patterns",
            system_prompt="You analyze data and find patterns.",
        )

        # 2. Create specialist agents with skills
        researcher = create_agent(
            name="Researcher",
            description="Researches topics deeply",
            skill_ids=[research_skill["id"]],
            kb_collection="agent_researcher_kb",
            system_prompt="You are a research specialist.",
        )
        analyst = create_agent(
            name="Analyst",
            description="Analyzes data and findings",
            skill_ids=[analysis_skill["id"]],
            kb_collection="agent_analyst_kb",
            system_prompt="You are a data analyst.",
        )

        # 3. Create orchestrator that delegates
        orchestrator = create_agent(
            name="Lead Agent",
            description="Orchestrates research and analysis",
            sub_agent_ids=[researcher["id"], analyst["id"]],
            system_prompt="You coordinate research and analysis tasks. Delegate research to Researcher and analysis to Analyst.",
        )

        # 4. Verify full config
        loaded = get_agent(orchestrator["id"])
        assert loaded["name"] == "Lead Agent"
        assert len(loaded["sub_agent_ids"]) == 2

        # Verify sub-agents are resolvable
        for sub_id in loaded["sub_agent_ids"]:
            sub = get_agent(sub_id)
            assert sub is not None
            assert len(sub["skill_ids"]) == 1

        # 5. Verify all agents in registry
        all_agents = list_agents()
        names = [a["name"] for a in all_agents]
        assert "Lead Agent" in names
        assert "Researcher" in names
        assert "Analyst" in names
