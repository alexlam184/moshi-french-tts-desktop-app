"""Shared visual tokens for the desktop UI.

Qt stylesheets use sRGB values, so these are the sRGB equivalents of the
OKLCH design tokens documented in the project-level tokens.css.
"""

APP_STYLESHEET = """
/* Hallmark · component: transport controls · genre: modern-minimal · theme: Cobalt study desk
 * states: default · hover · focus · active · disabled · loading · error/success n/a
 * studied: yes · DNA-source: user reference image · contrast: pass */
QWidget#appRoot {
    background: #f6f8fb;
    color: #18212f;
    font-family: "Avenir Next", "Segoe UI", sans-serif;
    font-size: 15px;
}
QLabel#brandTitle { font-size: 25px; font-weight: 700; color: #111a27; }
QLabel#brandSubtitle, QLabel#helperText, QLabel#inputStats { color: #5a687b; }
QLabel#sectionLabel { color: #375a86; font-size: 12px; font-weight: 700; }
QLabel#panelTitle { color: #111a27; font-size: 19px; font-weight: 700; }
QFrame#workspacePanel {
    background: transparent;
    border: 0;
}
QTextEdit, QComboBox, QDoubleSpinBox, QLineEdit {
    background: #ffffff;
    color: #18212f;
    border: 1px solid #bec9d7;
    border-radius: 7px;
    padding: 9px 11px;
    selection-background-color: #285f9e;
    selection-color: #ffffff;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #18212f;
    border: 1px solid #bec9d7;
    selection-background-color: #d9e9fb;
    selection-color: #18212f;
}
QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 4px 8px;
}
QComboBox QAbstractItemView::item:selected,
QComboBox QAbstractItemView::item:selected:!active {
    background: #d9e9fb;
    color: #18212f;
}
QTextEdit:focus, QComboBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {
    border: 1px solid #285f9e;
}
QComboBox { min-height: 26px; }
QPushButton {
    min-height: 28px;
    padding: 8px 14px;
    border: 1px solid #aebbc9;
    border-radius: 7px;
    background: #edf1f6;
    color: #18212f;
    font-weight: 600;
}
QPushButton:hover { background: #e2e8f0; }
QPushButton:pressed { background: #d5dde7; }
QPushButton:focus { border: 1px solid #285f9e; }
QPushButton:disabled { color: #8793a3; background: #e9edf2; border-color: #d5dce5; }
QPushButton#primaryButton {
    background: #172438;
    color: #f7f9fc;
    border-color: #172438;
}
QPushButton#primaryButton:hover { background: #24344c; }
QPushButton#primaryButton:pressed { background: #0f1928; }
QPushButton#playAllButton {
    min-width: 64px;
    max-width: 64px;
    min-height: 64px;
    max-height: 64px;
    padding: 0;
    border-radius: 32px;
    background: #285f9e;
    color: #ffffff;
    border-color: #285f9e;
    font-size: 22px;
    font-weight: 700;
}
QPushButton#playAllButton:hover { background: #214f84; }
QPushButton#playAllButton:pressed { background: #193e69; }
QPushButton#playAllButton:disabled { background: #a5b5c8; border-color: #a5b5c8; }
QPushButton#transportButton {
    min-width: 48px;
    max-width: 48px;
    min-height: 48px;
    max-height: 48px;
    padding: 0;
    border-radius: 24px;
    background: #f6f8fb;
    border: 1px solid #bec9d7;
    color: #43536a;
    font-size: 16px;
}
QPushButton#transportButton:hover {
    background: #e2e8f0;
    border-color: #8fa1b6;
}
QPushButton#transportButton:pressed {
    background: #d5dde7;
    border-color: #5a687b;
}
QPushButton#settingsButton { background: transparent; }
QScrollArea { border: 0; background: transparent; }
QTextBrowser#sentenceWords {
    background: transparent;
    border: 0;
    border-radius: 0;
    padding: 0;
}
QListWidget#historyList {
    background: #ffffff;
    color: #18212f;
    border: 1px solid #bec9d7;
    border-radius: 7px;
    padding: 3px;
}
QListWidget#historyList::item {
    padding: 6px 8px;
    border-radius: 4px;
}
QListWidget#historyList::item:hover,
QListWidget#historyList::item:selected {
    background: #d9e9fb;
    color: #18212f;
}
QListWidget#historyList::item:selected:!active {
    background: #d9e9fb;
    color: #18212f;
}
QWidget#cardsViewport { background: transparent; }
QFrame#sentenceCard {
    background: transparent;
    border: 0;
    border-radius: 6px;
}
QFrame#sentenceCard[playbackState="playing"] {
    background: #edf1f6;
    color: #18212f;
}
QToolButton#sentenceToggle {
    min-width: 36px;
    max-width: 36px;
    min-height: 44px;
    max-height: 44px;
    padding: 0;
    border: 1px solid transparent;
    border-radius: 18px;
    background: transparent;
    color: #5a687b;
    font-size: 10px;
    font-weight: 700;
}
QToolButton#sentenceToggle:hover { background: #e2e8f0; }
QToolButton#sentenceToggle:pressed { background: #d5dde7; }
QToolButton#sentenceToggle:focus { border: 1px solid #285f9e; }
QToolButton#sentenceToggle:disabled { color: #a5b5c8; }
QPushButton#sentencePlay {
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
    padding: 0;
    border-radius: 18px;
}
QPushButton#sentencePlay[playbackState="playing"] {
    background: #172438;
    color: #f7f9fc;
    border-color: #172438;
}
QPushButton#sentencePlay[playbackState="paused"] {
    background: #d9e9fb;
    color: #18212f;
    border-color: #285f9e;
}
QLabel#statusMessage {
    color: #43536a;
    background: #edf2f8;
    border-radius: 6px;
    padding: 8px 10px;
}
QSplitter::handle { background: transparent; width: 10px; height: 10px; }
"""

ACCENT = "#285f9e"
INK = "#18212f"
MUTED = "#5a687b"
ACTIVE_WORD = "#d9e9fb"
# Warm amber is deliberately distinct from the blue speaking highlight.
HOVER_WORD = "#ffe2a8"
