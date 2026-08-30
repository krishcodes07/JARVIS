"""
Unit tests for AskUserModal in TUI.
"""

from jarvis.ui.tui.screens.modals.ask_user_modal import AskUserModal


def test_ask_user_modal_single_init():
    questions = [
        {
            "id": "q_0",
            "question": "Which theme do you prefer?",
            "options": ["Cyberpunk", "Minimalist Dark", "Matrix"],
            "header": "Theme Selection",
        }
    ]
    modal = AskUserModal(questions=questions)
    assert len(modal.questions) == 1
    assert modal.dialog._title_text == "✦ JARVIS INQUIRY"
    assert modal.current_idx == 0


def test_ask_user_modal_multi_init():
    questions = [
        {"question": "Q1", "options": ["A", "B"]},
        {"question": "Q2", "options": ["C", "D"]},
    ]
    modal = AskUserModal(questions=questions)
    assert len(modal.questions) == 2
    assert modal.current_idx == 0


def test_ask_user_modal_record_answer():
    questions = [
        {"question": "Language?", "options": ["Python", "TypeScript"]},
        {"question": "Framework?", "options": ["FastAPI", "Express"]},
    ]
    modal = AskUserModal(questions=questions)
    modal._record_answer("Python")
    assert modal.answers == {"Language?": "Python"}
    assert modal.current_idx == 1
