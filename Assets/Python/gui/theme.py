"""
gui/theme.py
__________________
Centralised colour palette.  Import THEME in any panel:

    from gui.theme import THEME
    tk.Label(self, bg=THEME["PANEL"], fg=THEME["GREEN"], ...)

Changing a colour here updates every panel automatically.
"""

THEME: dict[str, str] = {
    "BG":         "#1a1a2e",
    "PANEL":      "#16213e",
    "ACCENT":     "#0f3460",
    "GREEN":      "#4ecca3",
    "GREEN_DARK": "#3ab88f",
    "RED":        "#e94560",
    "RED_DARK":   "#c73a52",
    "TEXT_LIGHT": "#eaeaea",
    "TEXT_DIM":   "#888888",
    "LOG_BG":     "#0d0d1a",
    "LOG_FG":     "#7ecfa0",
}