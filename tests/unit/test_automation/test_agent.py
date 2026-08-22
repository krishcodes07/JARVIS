"""
Unit tests for AutomationAgent action parsing and execution flow.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from jarvis.automation.agent import AutomationAgent
from jarvis.automation.schemas import (
    ActionType,
    AutomationGoalStatus,
    AutomationObservation,
)
from jarvis.core.config import JarvisConfig
from jarvis.providers.base import GenerationResponse


def test_agent_action_response_parsing() -> None:
    agent = AutomationAgent(JarvisConfig())

    # Raw JSON
    raw_json = json.dumps({
        "action_type": "click",
        "element_id": 3,
        "reason": "Clicking the OK button",
    })
    action = agent._parse_action_response(raw_json)
    assert action.action_type == ActionType.CLICK
    assert action.element_id == 3
    assert action.reason == "Clicking the OK button"

    # Markdown wrapped JSON
    md_json = """Here is my plan:
```json
{
    "action_type": "type",
    "text": "Hello from test",
    "reason": "Typing test message"
}
```"""
    action2 = agent._parse_action_response(md_json)
    assert action2.action_type == ActionType.TYPE
    assert action2.text == "Hello from test"


@pytest.mark.asyncio
async def test_agent_execution_done_cycle() -> None:
    config = JarvisConfig()
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(
        return_value=GenerationResponse(
            content=json.dumps({
                "action_type": "done",
                "reason": "All tasks completed successfully.",
            })
        )
    )

    agent = AutomationAgent(config, provider_manager=mock_provider)

    with patch.object(agent, "_capture_observation", return_value=AutomationObservation()):
        goal_result = await agent.execute_goal("Test Goal", max_steps=5)

    assert goal_result.status == AutomationGoalStatus.COMPLETED
    assert "All tasks completed" in goal_result.final_output
