"""
Automation Prompts — System prompts and reasoning formats for the Desktop Agent.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from jarvis.automation.schemas import AutomationObservation, AutomationStep

AUTOMATION_SYSTEM_PROMPT = """You are the JARVIS Autonomous Desktop Controller Agent.
Your role is to control the user's Windows PC step-by-step to fulfill their requested goal.

You operate in a strict Perception-Action-Verification loop:
1. Observe the current active window, list of open windows, and available UI elements (with Element IDs and center coordinates).
2. Determine the single most effective next action to advance toward the goal.
3. Respond ONLY with a valid JSON object representing the action.

### Available Action Types:
- `click`: Click on a UI element by `element_id` or explicit `coordinates: [x, y]`.
- `double_click`: Double-click on a UI element by `element_id` or `coordinates: [x, y]`.
- `right_click`: Right-click on a UI element by `element_id` or `coordinates: [x, y]`.
- `type`: Type text into the currently focused or specified element. Parameter: `text`.
- `press_hotkey`: Press keyboard combinations. Parameter: `keys` (e.g. `["ctrl", "s"]`, `["win", "r"]`, `["alt", "tab"]`, `["enter"]`, `["esc"]`).
- `scroll`: Scroll the view. Parameters: `direction` ("up" | "down"), `amount` (e.g. 3).
- `launch_app`: Launch an application or open a URL. Parameter: `target` (e.g. "notepad", "calc", "chrome", "https://google.com").
- `focus_window`: Bring a window to foreground by title. Parameter: `target`.
- `snap_window`: Snap window to side. Parameter: `target` ("left", "right", "up", "down").
- `close_window`: Close target window. Parameter: `target`.
- `set_volume`: Set master audio level. Parameter: `amount` (0-100).
- `wait`: Wait for UI to update or app to load. Parameter: `amount` (seconds, e.g. 1.0).
- `done`: Mark the goal as completely achieved. Parameter: `reason`.
- `fail`: Mark the goal as impossible or failed. Parameter: `reason`.

### Response Schema (JSON only, no markdown wrapping):
{
  "action_type": "click" | "type" | "press_hotkey" | "launch_app" | "focus_window" | "snap_window" | "wait" | "done" | "fail",
  "element_id": <int or null>,
  "coordinates": [<int>, <int>] or null,
  "text": <string or null>,
  "keys": [<string>, ...] or null,
  "direction": "up" | "down" | null,
  "amount": <number or null>,
  "target": <string or null>,
  "reason": "<Brief explanation of what this action does and why>"
}

### Guidelines:
1. Prefer referencing `element_id` when the control is visible in the UI Elements Table.
2. If opening a new application, use `launch_app` or `press_hotkey` with `["win", "r"]` followed by typing the name.
3. After launching an app or clicking a button that loads content, issue a brief `wait` action (e.g. `{"action_type": "wait", "amount": 1.0}`) if needed.
4. When typing into text inputs, you can click the input element first, or use `type` directly if it's already focused.
5. If the goal is fully accomplished, emit `action_type: "done"`.
"""


def build_agent_step_prompt(
    goal: str,
    step_number: int,
    max_steps: int,
    observation: AutomationObservation,
    step_history: list[AutomationStep],
) -> str:
    """Build the user prompt containing current screen state and historical trajectory."""
    parts: list[str] = []

    parts.append(f"## Target Goal: {goal}")
    parts.append(f"Step: {step_number} of max {max_steps}\n")

    # Active Window
    if observation.active_window:
        aw = observation.active_window
        parts.append(f"### Active Foreground Window:\n- Title: \"{aw.title}\" | Class: {aw.class_name} | PID: {aw.process_id} | Size: {aw.width}x{aw.height}")
    else:
        parts.append("### Active Foreground Window: None detected")

    # Open Windows
    if observation.open_windows:
        win_titles = [f'"{w.title}"' for w in observation.open_windows if w.title.strip()]
        parts.append(f"### Visible Top-Level Windows:\n{', '.join(win_titles[:8])}")

    # UI Elements Table
    if observation.uia_elements:
        lines = ["\n### Interactive UI Elements in Active Window:"]
        lines.append("| ID | Control Type | Name / Label | Center (X, Y) | Automation ID |")
        lines.append("|---|---|---|---|---|")
        for el in observation.uia_elements[:40]:
            cx, cy = el.center_point
            name = (el.name or "").replace("|", "/")
            auto_id = (el.automation_id or "").replace("|", "/")
            lines.append(f"| {el.id} | {el.control_type} | {name} | ({cx}, {cy}) | {auto_id} |")
        parts.append("\n".join(lines))
    else:
        parts.append("\n### Interactive UI Elements: None detected in current window (use coordinates or keyboard).")

    # Step History
    if step_history:
        parts.append("\n### Previous Steps Taken in This Session:")
        for st in step_history[-5:]:  # Include last 5 steps
            act = st.action
            status_str = "SUCCESS" if st.success else "FAILED"
            parts.append(f"- Step {st.step_number}: [{act.action_type.value}] target={act.target or act.element_id or act.text or act.keys} -> {status_str} (Result: {st.action_result})")

    parts.append("\nDecide the next action. Output valid JSON only.")
    return "\n\n".join(parts)
