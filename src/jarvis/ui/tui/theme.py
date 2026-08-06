"""
TUI Theme & Styling — Textual CSS for the JARVIS Terminal UI.
Professional design with balanced spacing and visual hierarchy.
"""

JARVIS_CSS = """
Screen {
    background: #000000;
    color: #f5f5f5;
    layout: vertical;
}

/* ─── Header ─── */
#header-container {
    height: 1fr;
    content-align: center middle;
    align: center middle;
    margin: 0;
    padding: 0;
}

#header-container.hidden {
    display: none;
}

/* ─── Chat Scroll Area ─── */
#chat-scroll {
    height: 1fr;
    border: none;
    padding: 1 1 1 1;
    overflow-y: auto;
    scrollbar-size-vertical: 0;
    scrollbar-size-horizontal: 0;
    background: #000000;
}

/* User message — dark grey card with blue accent ─── */
.chat-message-user {
    background: #1e1e1e;
    color: #ffffff;
    padding: 1 2;
    margin: 1 0 1 0;
    border-left: tall #3b82f6;
}

/* Assistant message — clean ─── */
.chat-message-jarvis {
    color: #e5e5e5;
    padding: 0 2;
    margin: 1 0 0 0;
}

.assistant-footer-badge {
    color: #737373;
    padding: 0 2;
    margin: 0 0 1 0;
    text-style: dim;
}

.chat-thought-block {
    color: #ff9a4f;
    text-style: bold;
    padding: 0 2;
    margin: 1 0 0 0;
}

.chat-tool-command {
    background: #1e1e1e;
    color: #ffffff;
    padding: 1 2;
    margin: 1 0 0 0;
    border-left: tall #fbbf24;
}

.chat-tool-output {
    color: #737373;
    padding: 0 2;
    margin: 0 0 0 1;
    text-style: italic;
}

.chat-error-message {
    background: #2d1a1a;
    color: #ff9999;
    padding: 1 2;
    margin: 1 0 1 0;
    border-left: tall #ef4444;
}

/* ─── Modals ─── */
ModalScreen {
    align: center middle;
    background: rgba(0, 0, 0, 0.95);
}

/* ─── Command Popover ─── */
#command-popover {
    margin: 0 4 0 4;
    padding: 0 1;
    background: #1e1e1e;
    border-left: tall #3b82f6;
    height: auto;
    display: none;
}

#command-popover.visible {
    display: block;
}

#popover-option-list {
    background: transparent;
    border: none;
    max-height: 8;
    padding: 0;
}

OptionList {
    background: transparent;
    border: none;
    height: auto;
}

OptionList > .option-list--option {
    padding: 0 1;
    margin: 0;
}

OptionList > .option-list--option-highlighted {
    background: #2b2b2b;
    color: #3b82f6;
    text-style: bold;
}
"""
