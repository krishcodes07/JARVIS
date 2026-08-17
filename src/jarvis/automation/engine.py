"""
Automation Engine — Lifecycle Manager for Desktop Automation & Computer Control.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from jarvis.automation.agent import AutomationAgent
from jarvis.automation.controller import DesktopController
from jarvis.automation.grounding.uia import UIAGrounder
from jarvis.automation.grounding.vision import VisualGrounder
from jarvis.automation.safety import SafetyGuard
from jarvis.automation.schemas import AutomationGoal, AutomationStep

if TYPE_CHECKING:
    from jarvis.core.config import JarvisConfig
    from jarvis.providers.manager import ProviderManager

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Subsystem coordinator for PC Control and Desktop Automation."""

    def __init__(self, config: JarvisConfig | None = None) -> None:
        self.config = config
        self.safety_guard: SafetyGuard = SafetyGuard(config.automation if config else None)
        self.controller: DesktopController = DesktopController(
            config.automation if config else None,
            self.safety_guard,
        )
        self.uia_grounder: UIAGrounder = UIAGrounder()
        self.visual_grounder: VisualGrounder = VisualGrounder()
        self.agent: AutomationAgent | None = None
        self._initialized = False

    async def initialize(
        self,
        config: JarvisConfig,
        provider_manager: ProviderManager | None = None,
    ) -> None:
        """Initialize automation components."""
        self.config = config
        self.safety_guard = SafetyGuard(config.automation)
        self.controller = DesktopController(config.automation, self.safety_guard)
        self.uia_grounder = UIAGrounder()
        self.visual_grounder = VisualGrounder()
        self.agent = AutomationAgent(config, provider_manager)
        self._initialized = True
        logger.info("Automation Engine initialized successfully.")

    def set_provider_manager(self, provider_manager: ProviderManager) -> None:
        """Set the provider manager on the automation agent."""
        if self.agent:
            self.agent.set_provider_manager(provider_manager)

    async def execute_task(
        self,
        goal: str,
        max_steps: int | None = None,
        on_step_callback: Callable[[AutomationStep], Any] | None = None,
        on_status_callback: Callable[[str], Any] | None = None,
    ) -> AutomationGoal:
        """Run an autonomous multi-step desktop task."""
        if not self.agent:
            raise RuntimeError("AutomationEngine not initialized or agent unavailable.")
        return await self.agent.execute_goal(
            goal_text=goal,
            max_steps=max_steps,
            on_step_callback=on_step_callback,
            on_status_callback=on_status_callback,
        )

    async def shutdown(self) -> None:
        """Shutdown automation resources."""
        if self.safety_guard:
            self.safety_guard.stop()
        self._initialized = False
        logger.info("Automation Engine shut down.")
