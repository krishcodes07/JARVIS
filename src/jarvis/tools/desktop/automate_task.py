"""
Automate Task Tool — Autonomous PC Control & Desktop Agent Delegator.
"""

from __future__ import annotations

import logging
from typing import Any

from jarvis.automation.agent import AutomationAgent
from jarvis.automation.schemas import AutomationGoalStatus
from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


class AutomateTaskTool(BaseTool):
    """Delegate complex multi-step Windows desktop tasks to the Autonomous Desktop Agent."""

    schema = ToolSchema(
        name="automate_task",
        description="Execute a multi-step autonomous PC goal (e.g. 'Open Spotify and play lofi beats', 'Open Notepad, write a memo, and save to desktop').",
        category="desktop",
        parameters=[
            ToolParameter(
                name="goal",
                type="string",
                description="Natural language instruction for the autonomous desktop agent.",
                required=True,
            ),
            ToolParameter(
                name="max_steps",
                type="integer",
                description="Maximum steps allowed (default: 20).",
                required=False,
                default=20,
            ),
        ],
        keywords=["automate", "control pc", "computer use", "automate task", "macro", "desktop workflow"],
    )

    def __init__(self) -> None:
        super().__init__()
        self.agent: AutomationAgent | None = None
        self._provider_manager: Any = None

    def set_provider_manager(self, provider_manager: Any) -> None:
        """Set or update the LLM provider manager."""
        self._provider_manager = provider_manager
        if self.agent:
            self.agent.set_provider_manager(provider_manager)

    async def execute(self, **kwargs: Any) -> str:
        """Execute autonomous desktop task."""
        goal_text = kwargs.get("goal", "").strip()
        max_steps = int(kwargs.get("max_steps", 20))

        if not goal_text:
            return "Error: 'goal' parameter is required for automate_task."

        if not self.agent:
            self.agent = AutomationAgent(self.config)

        # Ensure provider manager is wired from engine if available
        if self._provider_manager:
            self.agent.set_provider_manager(self._provider_manager)

        try:
            goal_res = await self.agent.execute_goal(goal_text=goal_text, max_steps=max_steps)

            lines = [f"### Automation Goal Result: {goal_res.status.value.upper()}"]
            lines.append(f"**Goal**: {goal_res.goal}")
            lines.append(f"**Steps Taken**: {len(goal_res.steps)} / {goal_res.max_steps}")

            if goal_res.status == AutomationGoalStatus.COMPLETED:
                lines.append(f"\n**Outcome**: {goal_res.final_output or 'Goal successfully accomplished.'}")
            else:
                lines.append(f"\n**Error / Status**: {goal_res.error_message or 'Goal could not be completed.'}")

            if goal_res.steps:
                lines.append("\n**Step Execution Summary**:")
                for st in goal_res.steps:
                    act = st.action
                    res_status = "OK" if st.success else "FAILED"
                    lines.append(f"- Step {st.step_number}: [{act.action_type.value}] {act.target or act.element_id or act.text or act.keys} -> {res_status} ({st.action_result})")

            return "\n".join(lines)

        except Exception as e:
            logger.exception(f"automate_task execution error: {e}")
            return f"Error executing desktop automation task: {e}"
