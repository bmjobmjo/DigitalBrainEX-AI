"""
Modern Theme System for DigitalBrainEX AI.
Supports high-contrast crisp Light Theme (default) and refined Dark Theme.
"""
from typing import Dict, Any

LIGHT_PALETTE: Dict[str, str] = {
    "bg_window": "#f0f0f0",
    "bg_sidebar": "#e0e0e0",
    "bg_banner": "#707070",
    "bg_surface": "#ffffff",
    "bg_card": "#ffffff",
    "bg_hover": "#e5f1fb",
    "bg_selected": "#0078d7",
    "border": "#707070",
    "border_light": "#c0c0c0",
    "border_input": "#7f9db9",
    "border_focus": "#0078d7",
    "text_primary": "#000000",
    "text_secondary": "#000000",
    "text_muted": "#505050",
    "accent": "#0078d7",
    "accent_hover": "#0063b1",
    "accent_text": "#ffffff",
    "btn_sec_bg": "#ffffff",
    "btn_sec_hover": "#e5f1fb",
    "btn_sec_text": "#000000",
    "success": "#16a34a",
    "warning": "#d97706",
    "danger": "#dc2626",
    "danger_hover": "#b91c1c",
    "info": "#0078d7",
    "badge_bg": "#e0e0e0",
    "badge_text": "#000000",
    "table_alt_row": "#e0e0e0",
}

DARK_PALETTE: Dict[str, str] = {
    "bg_window": "#181926",
    "bg_sidebar": "#12131c",
    "bg_banner": "#25273a",
    "bg_surface": "#1e2030",
    "bg_card": "#25273a",
    "bg_hover": "#2f3249",
    "bg_selected": "#3b4261",
    "border": "#363a4f",
    "border_light": "#494d64",
    "border_input": "#494d64",
    "border_focus": "#8aadf4",
    "text_primary": "#cad3f5",
    "text_secondary": "#a5adcb",
    "text_muted": "#6e738d",
    "accent": "#8aadf4",
    "accent_hover": "#7dc4e4",
    "accent_text": "#12131c",
    "btn_sec_bg": "#25273a",
    "btn_sec_hover": "#2f3249",
    "btn_sec_text": "#cad3f5",
    "success": "#a6da95",
    "warning": "#eed49f",
    "danger": "#ed8796",
    "danger_hover": "#ee99a0",
    "info": "#91d7e3",
    "badge_bg": "#363a4f",
    "badge_text": "#a6da95",
    "table_alt_row": "#1b1d2c",
}

CURRENT_THEME = "light"


def build_stylesheet(p: Dict[str, str]) -> str:
    """Generates a complete, high-DPI modern stylesheet from a palette dictionary."""
    return f"""
QMainWindow, QDialog, QStackedWidget, QScrollArea {{
    background-color: {p["bg_window"]};
    color: {p["text_primary"]};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
}}

QWidget {{
    color: {p["text_primary"]};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12px;
}}

#ViewContentWidget, #CentralWidget, #BodyWidget, #ViewStack, QStackedWidget > QWidget {{
    background-color: {p["bg_window"]};
    color: {p["text_primary"]};
}}

QLabel {{
    background-color: transparent;
    color: {p["text_primary"]};
}}

/* Top Bar Banner */
#TopBarWidget {{
    background-color: {p["bg_banner"]};
    border-bottom: 1px solid #707070;
    padding: 3px 8px;
}}

#TopBarLogoLabel {{
    background-color: transparent;
}}

#TopBarModuleTitle {{
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
    font-family: 'Modern No. 20', 'Segoe UI', serif;
}}

#TopBarProjText {{
    color: #ffffff;
    font-weight: normal;
    font-size: 12px;
}}

#TopBarWidget QPushButton {{
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #707070;
    border-radius: 2px;
    padding: 3px 10px;
    font-size: 12px;
}}

#TopBarWidget QPushButton:hover {{
    background-color: #e5f1fb;
    border-color: #0078d7;
}}

#TopBarWidget QComboBox {{
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #707070;
    border-radius: 0px;
    padding: 2px 6px;
    font-size: 12px;
}}

#TopBarWidget QLineEdit {{
    background-color: #ffffff;
    color: #000000;
    border: 1px solid #707070;
    border-radius: 0px;
    padding: 3px 6px;
    font-size: 12px;
}}

/* Bottom Status Banner */
#FooterBanner {{
    background-color: {p["bg_banner"]};
    border-top: 1px solid #707070;
}}

#FooterBrandLabel {{
    color: #ffffff;
    font-size: 14px;
    font-weight: bold;
    letter-spacing: 2px;
    font-family: 'Modern No. 20', 'Segoe UI', serif;
}}

#FooterVersionLabel {{
    color: #ffffff;
    font-size: 10px;
    font-weight: normal;
}}

QLabel#BrandLabel {{
    font-size: 15px;
    font-weight: bold;
    color: {p["text_primary"]};
}}

QLabel#HeaderLabel {{
    color: {p["text_primary"]};
    font-weight: normal;
}}

QLabel#ViewTitleLabel {{
    font-size: 15px;
    font-weight: normal;
    color: #000000;
}}

/* Sidebar - Styled as Desktop Buttons matching reference */
#SidebarWidget {{
    background-color: {p["bg_sidebar"]};
    border-right: 1px solid #707070;
    min-width: 190px;
    max-width: 210px;
}}

QListWidget#SidebarList {{
    border: none;
    background-color: transparent;
    outline: none;
    padding: 4px;
}}

QListWidget#SidebarList::item {{
    height: 38px;
    background-color: #ffffff;
    border: 1px solid #c0c0c0;
    border-radius: 2px;
    margin: 3px 4px;
    color: #000000;
    font-weight: normal;
    padding-left: 10px;
}}

QListWidget#SidebarList::item:hover {{
    background-color: #f5f5f5;
    border-color: #707070;
}}

QListWidget#SidebarList::item:selected {{
    background-color: #ffffff;
    border: 2px solid #0078d7;
    color: #000000;
    font-weight: bold;
}}

/* Buttons */
QPushButton {{
    background-color: {p["btn_sec_bg"]};
    color: {p["btn_sec_text"]};
    border: 1px solid {p["border"]};
    border-radius: 2px;
    padding: 3px 12px;
    min-height: 22px;
    font-size: 12px;
    font-weight: normal;
}}

QPushButton:hover {{
    background-color: {p["btn_sec_hover"]};
    border-color: {p["border_focus"]};
}}

QPushButton:pressed {{
    background-color: #cce4f7;
}}

QPushButton#PrimaryButton, QPushButton#DangerButton {{
    background-color: #ffffff;
    color: #000000;
    border: 1px solid {p["border"]};
    font-weight: normal;
}}

QPushButton#PrimaryButton:hover, QPushButton#DangerButton:hover {{
    background-color: {p["btn_sec_hover"]};
    border-color: {p["border_focus"]};
}}

/* Tables */
QTableWidget {{
    background-color: {p["bg_surface"]};
    alternate-background-color: {p["table_alt_row"]};
    color: {p["text_primary"]};
    gridline-color: #a0a0a0;
    border: 1px solid {p["border"]};
    border-radius: 0px;
    selection-background-color: {p["accent"]};
    selection-color: {p["accent_text"]};
    outline: none;
    font-size: 12px;
}}

QTableWidget::item {{
    padding: 3px 6px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {p["accent"]};
    color: {p["accent_text"]};
}}

QHeaderView::section {{
    background-color: #f0f0f0;
    color: {p["text_primary"]};
    font-weight: normal;
    font-size: 12px;
    padding: 3px 6px;
    border: 1px solid {p["border"]};
}}

QHeaderView::section:vertical {{
    background-color: #f0f0f0;
    color: {p["text_primary"]};
    border: 1px solid {p["border_light"]};
    padding: 0px 4px;
    min-width: 25px;
}}

/* Form Controls & Inputs */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDateEdit, QDateTimeEdit, QTimeEdit {{
    background-color: {p["bg_surface"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_input"]};
    border-radius: 2px;
    padding: 3px 6px;
    selection-background-color: {p["accent"]};
    selection-color: {p["accent_text"]};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus, QTimeEdit:focus {{
    border: 2px solid {p["border_focus"]};
}}

QComboBox {{
    background-color: {p["bg_surface"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border_input"]};
    border-radius: 6px;
    padding: 5px 12px;
    min-height: 22px;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {p["bg_surface"]};
    color: {p["text_primary"]};
    border: 1px solid {p["border"]};
    selection-background-color: {p["bg_selected"]};
    selection-color: {p["text_primary"]};
    border-radius: 6px;
    padding: 4px;
}}

/* Tabs */
QTabWidget::pane {{
    border: 1px solid {p["border"]};
    background-color: {p["bg_surface"]};
    border-radius: 8px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: {p["bg_sidebar"]};
    color: {p["text_secondary"]};
    padding: 8px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 4px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background-color: {p["bg_surface"]};
    color: {p["accent"]};
    font-weight: 600;
    border-top: 2px solid {p["accent"]};
}}

QTabBar::tab:hover:!selected {{
    background-color: {p["bg_hover"]};
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background-color: transparent;
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background-color: {p["border_input"]};
    border-radius: 4px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {p["text_muted"]};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background-color: transparent;
    height: 8px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background-color: {p["border_input"]};
    border-radius: 4px;
    min-width: 20px;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Splitters */
QSplitter::handle {{
    background-color: {p["border"]};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

/* Group Boxes */
QGroupBox {{
    font-weight: 600;
    border: 1px solid {p["border"]};
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 14px;
    background-color: {p["bg_surface"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 4px;
    color: {p["accent"]};
}}

/* Status Bar */
QStatusBar {{
    background-color: {p["bg_sidebar"]};
    color: {p["text_muted"]};
    border-top: 1px solid {p["border"]};
}}

/* Radio and CheckBox */
QRadioButton, QCheckBox {{
    spacing: 8px;
    color: {p["text_primary"]};
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {p["border_input"]};
    background-color: {p["bg_surface"]};
    border-radius: 9px;
}}

QRadioButton::indicator:hover {{
    border-color: {p["accent"]};
}}

QRadioButton::indicator:checked {{
    background-color: {p["accent"]};
    border: 3px solid {p["bg_surface"]};
    border-radius: 9px;
}}

QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1px solid {p["border_input"]};
    background-color: {p["bg_surface"]};
    border-radius: 4px;
}}

QCheckBox::indicator:hover {{
    border-color: {p["accent"]};
}}

QCheckBox::indicator:checked {{
    background-color: {p["accent"]};
    border-color: {p["accent"]};
}}
"""


def get_theme_stylesheet(theme_name: str = "light") -> str:
    """Returns the CSS stylesheet string for the requested theme ('light' or 'dark')."""
    palette = DARK_PALETTE if theme_name.lower() == "dark" else LIGHT_PALETTE
    return build_stylesheet(palette)


def apply_theme(app, theme_name: str = "light"):
    """Applies modern styling to the QApplication instance."""
    global CURRENT_THEME
    CURRENT_THEME = theme_name.lower()
    app.setProperty("theme_name", CURRENT_THEME)
    app.setStyleSheet(get_theme_stylesheet(CURRENT_THEME))
