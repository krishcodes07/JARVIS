"""
Ask User Tool — Solicit user input, clarification, or decisions.

Allows JARVIS to ask one or more questions with selectable options and an
automatic fixed "Custom" option where the user can type freeform responses.
Works seamlessly across Textual TUI, React Web UI, and CLI.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import sys
from typing import Any

from jarvis.tools.base import BaseTool, ToolParameter, ToolSchema

logger = logging.getLogger(__name__)


def _normalize_questions(kwargs: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize input arguments into a consistent list of question dicts.

    Supports both:
    1. Multi-question: questions=[{"question": "...", "options": [...]}]
    2. Single-question convenience: question="...", options=[...]
    """
    raw_questions = kwargs.get("questions")
    if isinstance(raw_questions, str):
        try:
            raw_questions = json.loads(raw_questions)
        except Exception:
            raw_questions = None

    if isinstance(raw_questions, list) and raw_questions:
        normalized = []
        for idx, item in enumerate(raw_questions):
            if isinstance(item, dict):
                q_text = str(item.get("question", "")).strip()
                opts = item.get("options") or []
                if isinstance(opts, str):
                    try:
                        opts = json.loads(opts)
                    except Exception:
                        opts = [opts]
                opts = [str(o).strip() for o in opts if str(o).strip()]
                is_multi = bool(item.get("is_multi_select", False))
                header = str(item.get("header") or item.get("title") or f"Question {idx + 1}").strip()
                if q_text:
                    normalized.append({
                        "id": f"q_{idx}",
                        "question": q_text,
                        "options": opts,
                        "is_multi_select": is_multi,
                        "header": header,
                    })
        if normalized:
            return normalized

    # Single question convenience
    single_q = str(kwargs.get("question", "")).strip()
    if single_q:
        single_opts = kwargs.get("options") or []
        if isinstance(single_opts, str):
            try:
                single_opts = json.loads(single_opts)
            except Exception:
                single_opts = [single_opts]
        single_opts = [str(o).strip() for o in single_opts if str(o).strip()]
        is_multi = bool(kwargs.get("is_multi_select", False))
        title = str(kwargs.get("title") or "Question").strip()
        return [{
            "id": "q_0",
            "question": single_q,
            "options": single_opts,
            "is_multi_select": is_multi,
            "header": title,
        }]

    return []


class AskUserTool(BaseTool):
    """Tool for asking the user clarifying questions or decisions."""

    schema = ToolSchema(
        name="ask_user",
        description=(
            "Ask the user one or more multiple-choice questions when you need clarification, "
            "design feedback, user preferences, or decisions before proceeding. "
            "You can specify a single question or multiple questions at once. "
            "Each question has a list of suggested options. A 'Custom' option is always provided "
            "automatically by the UI so the user can type their own free-form response."
        ),
        category="basic",
        aliases=["ask_question", "prompt_user"],
        keywords=["ask", "question", "prompt", "user", "input", "clarify", "choose", "options"],
        parameters=[
            ToolParameter(
                name="questions",
                type="array",
                description=(
                    "List of questions to ask the user. Each question is an object with: "
                    "'question' (string, required), 'options' (array of strings, required), "
                    "'header' (optional string title), and 'is_multi_select' (optional boolean). "
                    "Use this when you need to ask 2 or more questions in a single turn."
                ),
                required=False,
            ),
            ToolParameter(
                name="question",
                type="string",
                description="Single question text to ask the user (convenience parameter if asking only 1 question).",
                required=False,
            ),
            ToolParameter(
                name="options",
                type="array",
                description="List of selectable option strings for the single question.",
                required=False,
            ),
            ToolParameter(
                name="is_multi_select",
                type="boolean",
                description="Whether multiple options can be chosen (default: false).",
                required=False,
                default=False,
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Optional header or category title for the question dialog.",
                required=False,
            ),
        ],
    )

    async def execute(self, **kwargs: Any) -> str:
        """Execute the ask_user tool."""
        questions = _normalize_questions(kwargs)
        if not questions:
            return "Error: No question provided. Please provide 'question' and 'options', or a list of 'questions'."

        # 1. Look for registered UI callback
        callback = kwargs.get("ask_user_callback")
        if not callback and hasattr(self, "engine") and self.engine:
            callback = getattr(self.engine, "ask_user_callback", None)

        if callback is not None:
            try:
                res = callback(questions)
                if inspect.isawaitable(res):
                    answers = await res
                else:
                    answers = res

                return self._format_answers(questions, answers)
            except Exception as e:
                logger.exception("Error in ask_user UI callback: %s", e)
                return f"Error gathering user response: {e}"

        # 2. CLI / Terminal fallback
        if sys.stdin.isatty():
            return await self._cli_fallback(questions)

        # 3. Non-interactive fallback
        return self._non_interactive_fallback(questions)

    def _format_answers(
        self, questions: list[dict[str, Any]], raw_answers: Any
    ) -> str:
        """Format the gathered answers into a clean, LLM-digestible summary."""
        if not raw_answers:
            return "User dismissed the question dialog without providing an answer."

        # If raw_answers is a simple string (e.g. from single question modal)
        if isinstance(raw_answers, str):
            q_text = questions[0]["question"] if questions else "Question"
            return f"User response to '{q_text}': {raw_answers}"

        # If raw_answers is a dictionary mapping question or id to answer
        if isinstance(raw_answers, dict):
            lines = ["User responses:"]
            for q in questions:
                q_id = q.get("id", "")
                q_text = q["question"]
                ans = raw_answers.get(q_id) or raw_answers.get(q_text)
                if ans is None and len(questions) == 1 and len(raw_answers) == 1:
                    ans = next(iter(raw_answers.values()))

                if isinstance(ans, list):
                    ans_str = ", ".join(str(a) for a in ans)
                else:
                    ans_str = str(ans) if ans is not None else "(No answer provided)"

                lines.append(f"- {q_text}: {ans_str}")
            return "\n".join(lines)

        return f"User response: {raw_answers}"

    async def _cli_fallback(self, questions: list[dict[str, Any]]) -> str:
        """Interactive CLI fallback when running without a GUI/TUI/Web event loop."""
        answers: dict[str, Any] = {}

        def _prompt_user() -> dict[str, Any]:
            cli_answers: dict[str, Any] = {}
            for idx, q in enumerate(questions, start=1):
                print(f"\n[JARVIS Question {idx}/{len(questions)}]: {q['question']}")
                opts = list(q.get("options", []))
                for o_idx, opt in enumerate(opts, start=1):
                    print(f"  [{o_idx}] {opt}")
                print("  [C] Custom (Type your own response)")

                while True:
                    choice = input("\nSelect an option (1-N or C): ").strip()
                    if choice.lower() == "c":
                        custom_val = input("Enter custom response: ").strip()
                        cli_answers[q["question"]] = custom_val or "(Blank custom response)"
                        break
                    elif choice.isdigit() and 1 <= int(choice) <= len(opts):
                        cli_answers[q["question"]] = opts[int(choice) - 1]
                        break
                    else:
                        print("Invalid choice, please enter option number or 'C'.")
            return cli_answers

        raw = await asyncio.to_thread(_prompt_user)
        return self._format_answers(questions, raw)

    def _non_interactive_fallback(self, questions: list[dict[str, Any]]) -> str:
        """Fallback for automated tests or headless execution."""
        lines = ["User responses (automated fallback):"]
        for q in questions:
            opts = q.get("options", [])
            default_val = opts[0] if opts else "Custom option selected"
            lines.append(f"- {q['question']}: {default_val}")
        return "\n".join(lines)
