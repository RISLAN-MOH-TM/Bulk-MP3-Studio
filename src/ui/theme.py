"""
Modern Dark Theme stylesheets and design tokens for Bulk MP3 Studio.
"""

COLORS = {
    "bg_main": "#0b0f19",
    "bg_sidebar": "#0f172a",
    "bg_card": "#161f30",
    "bg_card_hover": "#1e293b",
    "bg_input": "#0d1322",
    "border": "#22314e",
    "border_focus": "#38bdf8",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "accent_cyan": "#06b6d4",
    "accent_cyan_hover": "#0891b2",
    "accent_indigo": "#6366f1",
    "accent_indigo_hover": "#4f46e5",
    "success": "#10b981",
    "success_bg": "rgba(16, 185, 129, 0.15)",
    "warning": "#f59e0b",
    "warning_bg": "rgba(245, 158, 11, 0.15)",
    "danger": "#ef4444",
    "danger_bg": "rgba(239, 68, 68, 0.15)",
    "info": "#38bdf8",
    "info_bg": "rgba(56, 189, 248, 0.15)",
}

DARK_STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {COLORS["bg_main"]};
    color: {COLORS["text_primary"]};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
}}

QWidget {{
    color: {COLORS["text_primary"]};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: {COLORS["bg_main"]};
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #334155;
    min-height: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #475569;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background: {COLORS["bg_main"]};
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: #334155;
    min-width: 24px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #475569;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Cards and Panels */
QFrame#cardFrame {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
}}

QFrame#sidebarFrame {{
    background-color: {COLORS["bg_sidebar"]};
    border-right: 1px solid {COLORS["border"]};
}}

/* Push Buttons */
QPushButton {{
    background-color: #1e293b;
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #27354f;
    border-color: #3b4d6b;
}}
QPushButton:pressed {{
    background-color: #172033;
}}
QPushButton:disabled {{
    background-color: #111827;
    color: {COLORS["text_muted"]};
    border-color: #1f2937;
}}

QPushButton#primaryBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #06b6d4);
    color: #ffffff;
    border: none;
    font-weight: 600;
}}
QPushButton#primaryBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #0891b2);
}}

QPushButton#successBtn {{
    background-color: #059669;
    color: #ffffff;
    border: none;
    font-weight: 600;
}}
QPushButton#successBtn:hover {{
    background-color: #047857;
}}

QPushButton#dangerBtn {{
    background-color: #dc2626;
    color: #ffffff;
    border: none;
    font-weight: 600;
}}
QPushButton#dangerBtn:hover {{
    background-color: #b91c1c;
}}

/* Inputs & Text Edits */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {COLORS["bg_input"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 8px 10px;
    selection-background-color: #0284c7;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {COLORS["border_focus"]};
    background-color: #0f182c;
}}

/* Combo Box */
QComboBox {{
    background-color: {COLORS["bg_input"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 6px 10px;
    min-height: 24px;
}}
QComboBox:focus {{
    border: 1px solid {COLORS["border_focus"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS["bg_card"]};
    color: {COLORS["text_primary"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}}

/* Table Widget */
QTableWidget {{
    background-color: {COLORS["bg_card"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    gridline-color: #1e293b;
    color: {COLORS["text_primary"]};
    selection-background-color: rgba(6, 182, 212, 0.2);
    selection-color: #ffffff;
}}
QHeaderView::section {{
    background-color: #131b2c;
    color: {COLORS["text_secondary"]};
    border: none;
    border-bottom: 1px solid {COLORS["border"]};
    padding: 8px 10px;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid #1a2436;
}}

/* Progress Bar */
QProgressBar {{
    background-color: #101726;
    border: 1px solid #1e293b;
    border-radius: 5px;
    height: 10px;
    text-align: center;
    font-size: 10px;
    color: {COLORS["text_secondary"]};
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #06b6d4);
    border-radius: 4px;
}}

/* Tooltips */
QToolTip {{
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    padding: 6px 8px;
    border-radius: 4px;
    font-size: 12px;
}}
"""
