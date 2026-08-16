"""Render a deterministic offscreen preview used during visual QA."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from PySide6.QtCore import QTimer  # noqa: E402

from jarvis_gui.app import create_application  # noqa: E402
from jarvis_gui.config import UIConfig  # noqa: E402
from jarvis_gui.conversation_store import ConversationStore  # noqa: E402
from jarvis_gui.main_window import JarvisWindow  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--settings", action="store_true")
    parser.add_argument("--speaking", action="store_true")
    parser.add_argument("--conversation", action="store_true")
    args = parser.parse_args()

    app = create_application([])
    preview_temp = tempfile.TemporaryDirectory() if args.conversation else None
    store = None
    conversation_id = None
    if preview_temp is not None:
        store = ConversationStore(Path(preview_temp.name) / "preview.db")
        conversation_id = store.create_conversation("Design the JARVIS interface")
        store.add_message(
            conversation_id,
            "user",
            "Can you make the interface remember all of my conversations?",
        )
        store.add_message(
            conversation_id,
            "assistant",
            "Conversation history is now saved locally and can be reopened from the sidebar.",
        )
    window = JarvisWindow(config=UIConfig(), conversation_store=store)
    window.resize(1280, 720)
    window.show()
    if args.settings:
        window.settings_button.click()
    if args.speaking:
        window.orb.set_speaking(True)
        window.orb.set_status("SPEAKING")
    if conversation_id is not None:
        window.open_conversation(conversation_id)
        window.menu_button.setChecked(True)

    def capture() -> None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        window.grab().save(str(args.output), "PNG")
        window.close()
        app.quit()

    QTimer.singleShot(350, capture)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
