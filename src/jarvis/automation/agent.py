"""
Automation Agent — Autonomous Desktop Agent Execution Loop.

Orchestrates the continuous Observe -> Plan -> Safety Check -> Act -> Verify loop
to accomplish complex multi-step Windows desktop tasks.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from jarvis.automation.controller import DesktopController
from jarvis.automation.grounding.uia import UIAGrounder
from jarvis.automation.grounding.vision import VisualGrounder
from jarvis.automation.prompts import AUTOMATION_SYSTEM_PROMPT, build_agent_step_prompt
from jarvis.automation.safety import AutomationAbortedError, SafetyGuard, SafetyViolationError
from jarvis.automation.schemas import (
    ActionType,
    AutomationAction,
    AutomationGoal,
    AutomationGoalStatus,
    AutomationObservation,
    AutomationStep,
)
from jarvis.providers.base import GenerationConfig, Message

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.providers.manager import ProviderManager

logger = logging.getLogger(__name__)


class AutomationAgent:
    """Autonomous Desktop Control Agent."""

    def __init__(
        self,
        config: JarvisConfig | None = None,
        provider_manager: ProviderManager | None = None,
    ) -> None:
        self.config = config
        self.automation_config = config.automation if config else None
        self.provider_manager = provider_manager

        self.safety_guard = SafetyGuard(self.automation_config)
        self.controller = DesktopController(self.automation_config, self.safety_guard)
        self.uia_grounder = UIAGrounder()
        self.visual_grounder = VisualGrounder()
        self._current_goal: AutomationGoal | None = None

    def set_provider_manager(self, provider_manager: ProviderManager) -> None:
        """Set or update the LLM provider manager."""
        self.provider_manager = provider_manager

    async def execute_goal(
        self,
        goal_text: str,
        max_steps: int | None = None,
        on_step_callback: Callable[[AutomationStep], Any] | None = None,
        on_status_callback: Callable[[str], Any] | None = None,
    ) -> AutomationGoal:
        """Execute an autonomous goal on the desktop.

        Args:
            goal_text: Natural language instruction (e.g. "Open Notepad, write Hello World and save").
            max_steps: Maximum steps allowed before aborting.
            on_step_callback: Callback triggered after each step execution.
            on_status_callback: Callback triggered when agent status updates.

        Returns:
            Completed or failed AutomationGoal trace.
        """
        effective_max_steps = max_steps or (
            self.automation_config.max_steps if self.automation_config else 30
        )
        step_delay = self.automation_config.step_delay if self.automation_config else 0.5

        goal = AutomationGoal(
            goal_id=str(uuid.uuid4())[:8],
            goal=goal_text,
            max_steps=effective_max_steps,
            status=AutomationGoalStatus.RUNNING,
        )
        self._current_goal = goal

        logger.info(f"Starting desktop automation goal [{goal.goal_id}]: '{goal_text}'")
        if on_status_callback:
            on_status_callback(f"Starting automation goal: {goal_text}")

        # Start emergency abort listener
        self.safety_guard.reset_abort()
        self.safety_guard.start()

        try:
            for step_num in range(1, effective_max_steps + 1):
                self.safety_guard.assert_not_aborted()
                goal.current_step = step_num
                start_time = time.time()

                # 1. Observe Environment
                obs = await self._capture_observation()

                # 2. Plan Action with LLM
                if on_status_callback:
                    on_status_callback(f"Planning Step {step_num}/{effective_max_steps}...")

                action = await self._plan_action(goal_text, step_num, effective_max_steps, obs, goal.steps)

                # 3. Check for terminal states
                if action.action_type == ActionType.DONE:
                    logger.info(f"Automation goal [{goal.goal_id}] marked DONE: {action.reason}")
                    goal.status = AutomationGoalStatus.COMPLETED
                    goal.final_output = action.reason or "Goal completed successfully."
                    goal.completed_at = datetime.now().isoformat()
                    return goal

                if action.action_type == ActionType.FAIL:
                    logger.warning(f"Automation goal [{goal.goal_id}] marked FAIL: {action.reason}")
                    goal.status = AutomationGoalStatus.FAILED
                    goal.error_message = action.reason or "Agent reported inability to complete goal."
                    goal.completed_at = datetime.now().isoformat()
                    return goal

                # 4. Safety Verification
                is_safe, safety_err = self.safety_guard.check_action_safety(action, obs.active_window)
                if not is_safe:
                    logger.warning(f"Safety restriction triggered at step {step_num}: {safety_err}")
                    step = AutomationStep(
                        step_number=step_num,
                        action=action,
                        action_result=f"Blocked: {safety_err}",
                        success=False,
                        duration_seconds=round(time.time() - start_time, 2),
                    )
                    goal.steps.append(step)
                    goal.status = AutomationGoalStatus.FAILED
                    goal.error_message = safety_err
                    return goal

                # 5. Execute Action
                logger.info(f"Executing step {step_num}: {action.action_type.value} -> {action.target or action.element_id or action.text or action.keys}")
                action_result, success = await self._execute_action(action, obs)

                # 6. Pacing delay
                if step_delay > 0:
                    await asyncio.sleep(step_delay)

                duration = round(time.time() - start_time, 2)
                step = AutomationStep(
                    step_number=step_num,
                    observation_summary=f"Window: {obs.active_window.title if obs.active_window else 'None'}",
                    action=action,
                    action_result=action_result,
                    success=success,
                    duration_seconds=duration,
                )
                goal.steps.append(step)

                if on_step_callback:
                    try:
                        res = on_step_callback(step)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as cb_err:
                        logger.debug(f"on_step_callback error: {cb_err}")

            # Reached max turns without explicit done
            goal.status = AutomationGoalStatus.FAILED
            goal.error_message = f"Reached maximum allowed steps ({effective_max_steps}) without completion."
            goal.completed_at = datetime.now().isoformat()
            return goal

        except AutomationAbortedError as abort_err:
            logger.warning(f"Goal [{goal.goal_id}] aborted: {abort_err}")
            goal.status = AutomationGoalStatus.ABORTED
            goal.error_message = "Execution aborted by emergency stop hotkey."
            goal.completed_at = datetime.now().isoformat()
            return goal

        except Exception as err:
            logger.exception(f"Unexpected error in automation goal [{goal.goal_id}]: {err}")
            goal.status = AutomationGoalStatus.FAILED
            goal.error_message = str(err)
            goal.completed_at = datetime.now().isoformat()
            return goal

        finally:
            self.safety_guard.stop()

    async def _capture_observation(self) -> AutomationObservation:
        """Capture the current screen observation (active window, open windows, UIA elements)."""
        active_win = await asyncio.to_thread(self.uia_grounder.get_active_window_info)
        open_wins = await asyncio.to_thread(self.uia_grounder.list_open_windows)

        hwnd = active_win.handle if active_win else None
        elements = await asyncio.to_thread(self.uia_grounder.extract_interactive_elements, hwnd)

        res = self.controller.screen.get_primary_resolution()
        cursor = self.controller.get_cursor_position()

        # Capture screenshot if logging is enabled
        screen_path = None
        if self.automation_config and self.automation_config.log_screenshots:
            try:
                p = await asyncio.to_thread(self.visual_grounder.capture_screenshot)
                screen_path = str(p)
            except Exception:
                pass

        return AutomationObservation(
            active_window=active_win,
            open_windows=open_wins,
            uia_elements=elements,
            screenshot_path=screen_path,
            screen_resolution=res,
            cursor_position=cursor,
        )

    async def _plan_action(
        self,
        goal: str,
        step_number: int,
        max_steps: int,
        obs: AutomationObservation,
        step_history: list[AutomationStep],
    ) -> AutomationAction:
        """Send screen observation to LLM and parse the planned action."""
        if not self.provider_manager:
            raise RuntimeError("ProviderManager not configured for AutomationAgent.")

        prompt = build_agent_step_prompt(goal, step_number, max_steps, obs, step_history)

        messages = [
            Message(role="system", content=AUTOMATION_SYSTEM_PROMPT),
            Message(role="user", content=prompt),
        ]

        gen_config = GenerationConfig(
            model=self.config.provider.model if self.config else "llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=1024,
        )

        response = await self.provider_manager.generate(messages, gen_config)
        raw_text = response.content.strip()

        return self._parse_action_response(raw_text)

    def _parse_action_response(self, raw_text: str) -> AutomationAction:
        """Parse LLM output into an AutomationAction."""
        # Try finding json block inside ```json ... ``` or direct json { ... }
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
        candidate = json_match.group(1) if json_match else raw_text

        if "{" in candidate and "}" in candidate:
            start = candidate.find("{")
            end = candidate.rfind("}") + 1
            candidate = candidate[start:end]

        try:
            data = json.loads(candidate)
            act_type_str = data.get("action_type", "").lower()
            return AutomationAction(
                action_type=ActionType(act_type_str),
                element_id=data.get("element_id"),
                coordinates=tuple(data["coordinates"]) if data.get("coordinates") else None,
                text=data.get("text"),
                keys=data.get("keys"),
                direction=data.get("direction"),
                amount=data.get("amount"),
                target=data.get("target"),
                reason=data.get("reason", ""),
            )
        except Exception as e:
            logger.warning(f"Failed to parse LLM action response '{raw_text}': {e}")
            # Safe fallback wait action
            return AutomationAction(
                action_type=ActionType.WAIT,
                amount=1.0,
                reason=f"Action parse recovery: {e}",
            )

    async def _execute_action(
        self,
        action: AutomationAction,
        obs: AutomationObservation,
    ) -> tuple[str, bool]:
        """Execute the planned action using the DesktopController."""
        try:
            # 1. Resolve coordinates from element_id if specified
            x, y = None, None
            if action.element_id:
                for el in obs.uia_elements:
                    if el.id == action.element_id:
                        x, y = el.center_point
                        break

            if action.coordinates and x is None:
                x, y = action.coordinates

            # 2. Match Action Types
            act = action.action_type

            if act == ActionType.CLICK:
                cx, cy = await asyncio.to_thread(self.controller.click, x=x, y=y)
                return f"Clicked at ({cx}, {cy})", True

            elif act == ActionType.DOUBLE_CLICK:
                cx, cy = await asyncio.to_thread(self.controller.double_click, x=x, y=y)
                return f"Double-clicked at ({cx}, {cy})", True

            elif act == ActionType.RIGHT_CLICK:
                cx, cy = await asyncio.to_thread(self.controller.right_click, x=x, y=y)
                return f"Right-clicked at ({cx}, {cy})", True

            elif act == ActionType.TYPE:
                if x is not None and y is not None:
                    await asyncio.to_thread(self.controller.click, x=x, y=y)
                    await asyncio.sleep(0.1)
                text_to_type = action.text or ""
                await asyncio.to_thread(self.controller.type_text, text_to_type)
                return f"Typed text ({len(text_to_type)} chars)", True

            elif act == ActionType.PRESS_HOTKEY:
                keys = action.keys or []
                await asyncio.to_thread(self.controller.press_hotkey, *keys)
                return f"Pressed hotkey: {'+'.join(keys)}", True

            elif act == ActionType.PRESS_KEY:
                key = (action.keys[0] if action.keys else action.text) or "enter"
                await asyncio.to_thread(self.controller.press_key, key)
                return f"Pressed key: {key}", True

            elif act == ActionType.SCROLL:
                dir_str = action.direction or "down"
                amount = int(action.amount or 3)
                await asyncio.to_thread(self.controller.scroll, amount=amount, direction=dir_str, x=x, y=y)
                return f"Scrolled {dir_str} by {amount} units", True

            elif act == ActionType.LAUNCH_APP:
                target = action.target or ""
                res = await asyncio.to_thread(self.controller.launch_app, target)
                return res, True

            elif act == ActionType.FOCUS_WINDOW:
                target = action.target or ""
                ok = await asyncio.to_thread(self.controller.focus_window, target)
                return f"Focus window '{target}': {'Success' if ok else 'Not found'}", ok

            elif act == ActionType.SNAP_WINDOW:
                target = action.target or "left"
                ok = await asyncio.to_thread(self.controller.snap_window, direction=target)
                return f"Snap window '{target}': {'Success' if ok else 'Failed'}", ok

            elif act == ActionType.CLOSE_WINDOW:
                target = action.target or (obs.active_window.handle if obs.active_window else "")
                ok = await asyncio.to_thread(self.controller.close_window, target)
                return f"Close window: {'Success' if ok else 'Failed'}", ok

            elif act == ActionType.SET_VOLUME:
                vol = int(action.amount if action.amount is not None else 50)
                res_vol = await asyncio.to_thread(self.controller.set_master_volume, vol)
                return f"Set volume to {res_vol}%", (res_vol >= 0)

            elif act == ActionType.WAIT:
                sec = float(action.amount or 1.0)
                await asyncio.sleep(min(sec, 5.0))
                return f"Waited {sec}s", True

            else:
                return f"Unhandled action type: {act}", False

        except Exception as e:
            logger.warning(f"Action execution failure ({action.action_type}): {e}")
            return f"Action failed: {e}", False
