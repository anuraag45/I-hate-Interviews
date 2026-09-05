import os
import re
import sys
import ctypes
from typing import Optional, Dict
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPoint
from PyQt6.QtGui import QFont, QColor, QPalette, QMouseEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy, QApplication, QLineEdit
)

from stealth.win32_affinity import (
    apply_stealth_affinity,
    apply_non_activating_styles,
    set_click_through
)
from gui.markdown_renderer import render_markdown_to_qt_html
from engine.shared_audio_ring import SharedAudioRing, SHM_NAME

class ClickFocusLineEdit(QLineEdit):
    """
    QLineEdit that safely claims focus upon direct mouse click
    without permanently activating the tool window or triggering meeting app shortcuts.
    """
    def mousePressEvent(self, event: QMouseEvent):
        super().mousePressEvent(event)
        try:
            hwnd = int(self.window().winId())
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            self.setFocus()
        except Exception:
            pass

class HUDUpdateSignaler(QObject):
    transcript_updated = pyqtSignal(str)
    qa_token_stream = pyqtSignal(str)
    qa_card_complete = pyqtSignal(str)
    stage_token_stream = pyqtSignal(int, str)
    stage_card_complete = pyqtSignal(int, str)
    action_smart_next = pyqtSignal()
    action_stage_1 = pyqtSignal()
    action_stage_2 = pyqtSignal()
    action_stage_3 = pyqtSignal()
    action_vision_snip = pyqtSignal()
    action_custom_query = pyqtSignal(str)
    action_simulate_speech = pyqtSignal(str)
    clear_triggered = pyqtSignal()
    toggle_visibility_signal = pyqtSignal()
    toggle_click_through_signal = pyqtSignal()

THEME_PALETTES: Dict[str, dict] = {
    "calm_buttercup": {
        "name": "Calm Buttercup",
        "bg_hex": "#12151C",
        "bg_rgb": "18, 21, 28",
        "card_hex": "#181C26",
        "card_rgb": "24, 28, 38",
        "input_hex": "#1E2332",
        "input_rgb": "30, 35, 50",
        "accent": "#F6D860",
        "accent_hover": "#FBEA8D",
        "accent_pressed": "#ECC94B",
        "accent_text": "#12151C",
        "ans_color": "#F6D860",
        "code_color": "#9F7AEA",
        "text_primary": "#FFFFFF",
        "text_secondary": "#E2E8F0",
        "text_muted": "#8E95A5",
        "border_subtle": "rgba(255, 255, 255, 0.08)",
        "border_accent": "rgba(246, 216, 96, 0.35)",
        "badge_bg": "#181C26",
        "badge_border": "rgba(246, 216, 96, 0.35)",
    },
    "gentle_sage": {
        "name": "Gentle Sage",
        "bg_hex": "#111815",
        "bg_rgb": "17, 24, 21",
        "card_hex": "#16201B",
        "card_rgb": "22, 32, 27",
        "input_hex": "#1C2923",
        "input_rgb": "28, 41, 35",
        "accent": "#68D391",
        "accent_hover": "#9AE6B4",
        "accent_pressed": "#48BB78",
        "accent_text": "#111815",
        "ans_color": "#68D391",
        "code_color": "#81E6D9",
        "text_primary": "#F0FFF4",
        "text_secondary": "#C6F6D5",
        "text_muted": "#718096",
        "border_subtle": "rgba(255, 255, 255, 0.08)",
        "border_accent": "rgba(104, 211, 145, 0.35)",
        "badge_bg": "#16201B",
        "badge_border": "rgba(104, 211, 145, 0.35)",
    },
    "muted_slate": {
        "name": "Muted Slate",
        "bg_hex": "#13171F",
        "bg_rgb": "19, 23, 31",
        "card_hex": "#1A202C",
        "card_rgb": "26, 32, 44",
        "input_hex": "#232B3B",
        "input_rgb": "35, 43, 59",
        "accent": "#63B3ED",
        "accent_hover": "#90CDF4",
        "accent_pressed": "#4299E1",
        "accent_text": "#13171F",
        "ans_color": "#63B3ED",
        "code_color": "#B794F4",
        "text_primary": "#EBF8FF",
        "text_secondary": "#BEE3F8",
        "text_muted": "#718096",
        "border_subtle": "rgba(255, 255, 255, 0.08)",
        "border_accent": "rgba(99, 179, 237, 0.35)",
        "badge_bg": "#1A202C",
        "badge_border": "rgba(99, 179, 237, 0.35)",
    },
    "oled_pure_black": {
        "name": "OLED Pure Black",
        "bg_hex": "#000000",
        "bg_rgb": "0, 0, 0",
        "card_hex": "#080808",
        "card_rgb": "8, 8, 8",
        "input_hex": "#121212",
        "input_rgb": "18, 18, 18",
        "accent": "#ECC94B",
        "accent_hover": "#F6D860",
        "accent_pressed": "#D69E2E",
        "accent_text": "#000000",
        "ans_color": "#ECC94B",
        "code_color": "#D6BCFA",
        "text_primary": "#FFFFFF",
        "text_secondary": "#E2E8F0",
        "text_muted": "#4A5568",
        "border_subtle": "rgba(255, 255, 255, 0.12)",
        "border_accent": "rgba(236, 201, 75, 0.40)",
        "badge_bg": "#080808",
        "badge_border": "rgba(236, 201, 75, 0.40)",
    }
}

SAMPLE_PROMPTS = [
    ("💡 Two Sum O(N)", "Find two numbers in array that add up to target in O(N) time"),
    ("💡 LRU Cache", "Implement an LRU Cache with strict O(1) get and put operations"),
    ("💡 Reverse List", "Write in-place reversal of a singly linked list with O(1) memory"),
    ("💡 SQL Window Func", "Write SQL query to find top 3 earners per department using DENSE_RANK()")
]

BRAILLE_WAVE_PATTERNS = ["⣀", "⣄", "⣆", "⣇", "⣧", "⣷", "⣿", "⣾", "⣶", "⣤", "⣀", "⡀"]

def compile_hud_stylesheet(theme_key: str = "calm_buttercup", border_radius: int = 14, font_size: int = 13, opacity: float = 0.96) -> dict:
    pal = THEME_PALETTES.get(theme_key, THEME_PALETTES["calm_buttercup"])
    r_card = max(6, border_radius - 4)
    r_input = max(6, border_radius - 6)
    r_btn = max(4, border_radius - 8)

    card_alpha = round(min(0.98, max(0.50, opacity * 0.90)), 2)
    input_alpha = round(min(0.98, max(0.45, opacity * 0.95)), 2)

    return {
        "palette": pal,
        "opacity": opacity,
        "card_alpha": card_alpha,
        "input_alpha": input_alpha,
        "border_radius": border_radius,
        "font_size": font_size,
        "modern_frame": f"""
            QFrame#ModernFrame {{
                background-color: rgba({pal['bg_rgb']}, {opacity});
                border: 1px solid {pal['border_accent']};
                border-radius: {border_radius}px;
            }}
        """,
        "card_ans": f"""
            QFrame#CardAns {{
                background: rgba({pal['card_rgb']}, {card_alpha});
                border: 1px solid {pal['border_subtle']};
                border-left: 3px solid {pal['ans_color']};
                border-radius: {r_card}px;
                padding: 6px;
            }}
        """,
        "card_code": f"""
            QFrame#CardCode {{
                background: rgba({pal['card_rgb']}, {card_alpha});
                border: 1px solid {pal['border_subtle']};
                border-left: 3px solid {pal['code_color']};
                border-radius: {r_card}px;
                padding: 6px;
            }}
        """,
        "transcript_box": f"""
            QLabel#TranscriptBox {{
                background: rgba({pal['card_rgb']}, {card_alpha});
                border: 1px solid {pal['border_subtle']};
                border-left: 3px solid {pal['accent']};
                border-radius: {r_card}px;
                padding: 6px 8px;
                color: {pal['text_primary']};
                font-size: {max(10.0, font_size - 1.5):.1f}px;
                line-height: 1.3;
            }}
        """,
        "query_input": f"""
            QLineEdit#QueryInput {{
                background: rgba({pal['input_rgb']}, {input_alpha});
                border: 1px solid {pal['border_subtle']};
                border-radius: {r_input}px;
                padding: 6px 10px;
                color: #FFFFFF;
                font-size: {max(10.0, font_size - 1.5):.1f}px;
            }}
            QLineEdit#QueryInput:focus {{
                border: 1px solid {pal['accent']};
                background: rgba({pal['input_rgb']}, 1.0);
            }}
        """,
        "send_btn": f"""
            QPushButton#SendBtn {{
                background: {pal['accent']};
                color: {pal['accent_text']};
                border: none;
                border-radius: {r_btn}px;
                padding: 6px 12px;
                font-weight: 800;
                font-size: {max(10, font_size - 2)}px;
            }}
            QPushButton#SendBtn:hover {{
                background: {pal['accent_hover']};
            }}
            QPushButton#SendBtn:pressed {{
                background: {pal['accent_pressed']};
            }}
        """,
        "chip_btn": f"""
            QPushButton {{
                background: rgba({pal['input_rgb']}, {input_alpha});
                color: {pal['accent']};
                border: 1px solid {pal['border_accent']};
                border-radius: {r_btn}px;
                padding: 4px 8px;
                font-size: {max(9, font_size - 3)}px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: rgba({pal['card_rgb']}, 1.0);
                color: #FFFFFF;
                border-color: {pal['accent']};
            }}
            QPushButton:pressed {{
                background: {pal['accent']};
                color: {pal['accent_text']};
            }}
        """,
        "btn_header": f"""
            QPushButton {{
                background: rgba({pal['input_rgb']}, {input_alpha});
                color: {pal['text_muted']};
                border: 1px solid {pal['border_subtle']};
                border-radius: 5px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background: rgba({pal['card_rgb']}, 1.0);
                border-color: {pal['accent']};
                color: {pal['text_primary']};
            }}
            QPushButton:pressed {{
                background: {pal['accent']};
                color: {pal['accent_text']};
            }}
        """,
        "btn_hide": f"""
            QPushButton {{
                background: rgba({pal['input_rgb']}, {input_alpha});
                color: #E53E3E;
                border: 1px solid {pal['border_subtle']};
                border-radius: 5px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: rgba(229, 62, 62, 0.2);
                border-color: #E53E3E;
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background: #E53E3E;
                color: #FFFFFF;
            }}
        """,
        "model_badge": f"""
            background: {pal['badge_bg']};
            color: {pal['accent']};
            border: 1px solid {pal['badge_border']};
            border-radius: 6px;
            padding: 3px 6px;
            font-size: 10px;
            font-weight: 700;
        """
    }

def _split_qa_response(raw_text: str) -> tuple[str, str]:
    """Splits full response markdown into direct answer bullet points and code block."""
    if not raw_text:
        return "", ""
    
    code_match = re.search(r'```([a-zA-Z0-9_-]*)\n(.*?)```', raw_text, flags=re.DOTALL)
    if code_match:
        lang = code_match.group(1) or "python"
        code_body = code_match.group(2).strip()
        ans_part = (raw_text[:code_match.start()] + "\n" + raw_text[code_match.end():]).strip()
        code_part = f"```{lang}\n{code_body}\n```"
        return ans_part, code_part
    
    # If currently streaming an unclosed code block
    if "```" in raw_text:
        parts = raw_text.split("```", 1)
        ans_part = parts[0].strip()
        code_part = "```" + parts[1]
        return ans_part, code_part

    return raw_text.strip(), ""

class StealthHUD(QWidget):
    def __init__(self, config: dict = None, signaler: HUDUpdateSignaler = None):
        super().__init__()
        self.config = config or {}
        self.signaler = signaler or HUDUpdateSignaler()

        self.stealth_enabled = bool(self.config.get("ui_settings", {}).get("stealth_affinity", True))
        self.is_click_through = bool(self.config.get("ui_settings", {}).get("click_through_default", False))
        self.vu_mode = self.config.get("ui_settings", {}).get("vu_mode", "dots")
        self.current_font_size = int(self.config.get("ui_settings", {}).get("font_size", 13))
        self.wave_phase = 0
        self.is_collapsed = False
        self.is_code_collapsed = False
        self._styles_applied = False
        self._affinity_applied = False
        self._drag_pos = QPoint()

        # Buffers
        self.raw_content_ans = ""
        self.raw_content_code = ""
        self.full_stream_buffer = ""
        self.shm_ring = None

        self._init_window_flags()
        self._init_ui()
        self._connect_signals()
        self.apply_live_settings(self.config)
        self._init_vu_timer()


    def _init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        ui_s = self.config.get("ui_settings", {})
        w = max(280, min(650, int(ui_s.get("width", 380))))
        h = max(400, min(1080, int(ui_s.get("height", 640))))
        self.resize(w, h)
        
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = (screen_geo.width() - w) // 2
            y = 35
            self.move(x, y)

    def showEvent(self, event):
        super().showEvent(event)
        try:
            hwnd = int(self.winId())
            if self.stealth_enabled:
                apply_stealth_affinity(hwnd, exclude=True)
            apply_non_activating_styles(hwnd, click_through=self.is_click_through)
        except Exception:
            pass

    def apply_live_settings(self, cfg: dict):
        self.config = cfg
        ui_s = cfg.get("ui_settings", {})
        ai_s = cfg.get("ai_settings", {})

        w = max(280, min(650, int(ui_s.get("width", 380))))
        h = max(400, min(1080, int(ui_s.get("height", 640))))
        if not self.is_collapsed and (self.width() != w or self.height() != h):
            self.resize(w, h)
            self.updateGeometry()

        op = float(ui_s.get("opacity", 0.96))
        r = int(ui_s.get("border_radius", 14))
        font_size = int(ui_s.get("font_size", 13))
        self.current_font_size = font_size
        self.vu_mode = ui_s.get("vu_mode", "dots")
        theme_key = ui_s.get("theme", "calm_buttercup")

        self.setWindowOpacity(op)
        styles = compile_hud_stylesheet(theme_key, border_radius=r, font_size=font_size, opacity=op)
        pal = styles["palette"]

        self.card_container.setStyleSheet(styles["modern_frame"])
        self.card_ans.setStyleSheet(styles["card_ans"])
        self.card_code.setStyleSheet(styles["card_code"])
        self.lbl_transcript.setStyleSheet(styles["transcript_box"])
        self.txt_query.setStyleSheet(styles["query_input"])
        self.btn_send.setStyleSheet(styles["send_btn"])
        
        for btn in self.chip_buttons:
            btn.setStyleSheet(styles["chip_btn"])

        model_name = (ai_s.get("custom_model") or ai_s.get("gemini_model") or "gemini-3.7-flash").upper()
        self.lbl_model_badge.setText(f"⚡ {model_name[:18]}")
        self.lbl_model_badge.setStyleSheet(styles["model_badge"])

        self._refresh_rendered_cards(pal)
        self.update()

    def _init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(6, 6, 6, 6)
        self.main_layout.setSpacing(6)

        self.card_container = QFrame(self)
        self.card_container.setObjectName("ModernFrame")
        self.card_container.setStyleSheet("""
            QFrame#ModernFrame {
                background-color: rgba(18, 21, 28, 0.96);
                border: 1px solid rgba(246, 216, 96, 0.35);
                border-radius: 14px;
            }
        """)

        self.container_layout = QVBoxLayout(self.card_container)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.setSpacing(6)

        # 1. Top Header Bar
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        self.lbl_drag_handle = QLabel("⠿", self)
        self.lbl_drag_handle.setStyleSheet("color: #718096; font-size: 13px; font-weight: 800; padding: 0 2px;")

        self.lbl_model_badge = QLabel("⚡ GEMINI-3.7-FLASH", self)
        self.lbl_model_badge.setStyleSheet("background: #181C26; color: #F6D860; border: 1px solid rgba(246, 216, 96, 0.35); border-radius: 6px; padding: 3px 6px; font-size: 10px; font-weight: 700;")

        self.lbl_status = QLabel("🟢 Ready", self)
        self.lbl_status.setStyleSheet("color: #38A169; font-size: 10px; font-weight: 700;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Controls
        self.btn_op_dec = QPushButton("🔅", self)
        self.btn_op_dec.setFixedSize(20, 20)
        self.btn_op_dec.clicked.connect(self._decrease_opacity)

        self.btn_op_inc = QPushButton("🔆", self)
        self.btn_op_inc.setFixedSize(20, 20)
        self.btn_op_inc.clicked.connect(self._increase_opacity)

        self.btn_collapse = QPushButton("▲", self)
        self.btn_collapse.setFixedSize(20, 20)
        self.btn_collapse.setToolTip("Minimize / Collapse HUD")
        self.btn_collapse.clicked.connect(self._toggle_collapse)

        self.btn_ghost = QPushButton("👻", self)
        self.btn_ghost.setFixedSize(20, 20)
        self.btn_ghost.setToolTip("Toggle Click-Through Mode (Ctrl+Alt+T)")
        self.btn_ghost.clicked.connect(self.toggle_click_through)

        self.btn_hide = QPushButton("✕", self)
        self.btn_hide.setFixedSize(20, 20)
        self.btn_hide.setToolTip("Hide HUD (Ctrl+Alt+H)")
        self.btn_hide.clicked.connect(self.hide)

        header_layout.addWidget(self.lbl_drag_handle)
        header_layout.addWidget(self.lbl_model_badge)
        header_layout.addWidget(self.lbl_status, 1)
        header_layout.addWidget(self.btn_op_dec)
        header_layout.addWidget(self.btn_op_inc)
        header_layout.addWidget(self.btn_collapse)
        header_layout.addWidget(self.btn_ghost)
        header_layout.addWidget(self.btn_hide)
        self.container_layout.addLayout(header_layout)

        # 2. Live Audio VU Meter
        self.vu_box = QFrame(self)
        vu_layout = QHBoxLayout(self.vu_box)
        vu_layout.setContentsMargins(4, 2, 4, 2)
        
        self.lbl_vu_dots = QLabel("• • • • • • • • ◦ ◦ ◦ ◦ ◦ ◦ ◦ ◦", self.vu_box)
        self.lbl_vu_dots.setStyleSheet("color: #38A169; font-size: 11px; font-weight: 700; font-family: monospace;")
        self.btn_vu_mode = QPushButton("🎙️ MIC + SYSTEM", self.vu_box)
        self.btn_vu_mode.setStyleSheet("background: transparent; color: #F6D860; border: none; font-size: 10px; font-weight: 700;")
        
        vu_layout.addWidget(self.lbl_vu_dots, 1)
        vu_layout.addWidget(self.btn_vu_mode)
        self.container_layout.addWidget(self.vu_box)

        # 3. Live Speech Transcript Pill
        self.lbl_transcript = QLabel(">> Listening to meeting audio stream...", self)
        self.lbl_transcript.setObjectName("TranscriptBox")
        self.lbl_transcript.setWordWrap(True)
        self.lbl_transcript.setStyleSheet("""
            background: #181C26;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-left: 3px solid #F6D860;
            border-radius: 8px;
            padding: 6px 8px;
            color: #FFFFFF;
            font-size: 11px;
        """)
        self.container_layout.addWidget(self.lbl_transcript)

        # 4. Scrollable Collapsible Dual-Section View
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_widget = QWidget()
        self.content_layout = QVBoxLayout(scroll_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)

        # SECTION 1: 💬 Direct Answer & Key Takeaways
        self.card_ans = QFrame(self)
        self.card_ans.setObjectName("CardAns")
        self.card_ans.setStyleSheet("""
            QFrame#CardAns {
                background: #181C26;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-left: 3px solid #F6D860;
                border-radius: 10px;
                padding: 6px;
            }
        """)
        ans_layout = QVBoxLayout(self.card_ans)
        ans_layout.setContentsMargins(8, 6, 8, 6)
        ans_layout.setSpacing(4)

        ans_hdr_layout = QHBoxLayout()
        self.lbl_ans_title = QLabel("💬 Direct Answer & Key Points", self.card_ans)
        self.lbl_ans_title.setStyleSheet("color: #F6D860; font-size: 11px; font-weight: 700;")
        ans_hdr_layout.addWidget(self.lbl_ans_title, 1)
        ans_layout.addLayout(ans_hdr_layout)

        self.txt_ans = QLabel("", self.card_ans)
        self.txt_ans.setWordWrap(True)
        self.txt_ans.setTextFormat(Qt.TextFormat.RichText)
        self.txt_ans.setStyleSheet("color: #E2E8F0; font-size: 12px; line-height: 1.4;")
        ans_layout.addWidget(self.txt_ans)
        self.content_layout.addWidget(self.card_ans)

        # SECTION 2: 💻 Production Code Panel (Collapsible)
        self.card_code = QFrame(self)
        self.card_code.setObjectName("CardCode")
        self.card_code.setStyleSheet("""
            QFrame#CardCode {
                background: #181C26;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-left: 3px solid #9F7AEA;
                border-radius: 10px;
                padding: 6px;
            }
        """)
        code_layout = QVBoxLayout(self.card_code)
        code_layout.setContentsMargins(8, 6, 8, 6)
        code_layout.setSpacing(4)

        code_hdr_layout = QHBoxLayout()
        self.lbl_code_title = QLabel("💻 Production Code", self.card_code)
        self.lbl_code_title.setStyleSheet("color: #9F7AEA; font-size: 11px; font-weight: 700;")

        self.btn_collapse_code = QPushButton("▲ Code", self.card_code)
        self.btn_collapse_code.setFixedHeight(20)
        self.btn_collapse_code.setStyleSheet("background: #222838; color: #8E95A5; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; font-size: 10px; padding: 0 6px;")
        self.btn_collapse_code.clicked.connect(self._toggle_code_collapse)

        self.btn_copy = QPushButton("📋 Copy", self.card_code)
        self.btn_copy.setFixedHeight(20)
        self.btn_copy.setStyleSheet("background: #222838; color: #F0F2F7; border: 1px solid rgba(255,255,255,0.1); border-radius: 4px; font-size: 10px; padding: 0 6px;")
        self.btn_copy.clicked.connect(self._copy_code_to_clipboard)

        code_hdr_layout.addWidget(self.lbl_code_title, 1)
        code_hdr_layout.addWidget(self.btn_collapse_code)
        code_hdr_layout.addWidget(self.btn_copy)
        code_layout.addLayout(code_hdr_layout)

        self.txt_code = QLabel("", self.card_code)
        self.txt_code.setWordWrap(True)
        self.txt_code.setTextFormat(Qt.TextFormat.RichText)
        self.txt_code.setStyleSheet("color: #E2E8F0; font-size: 12px; line-height: 1.4;")
        code_layout.addWidget(self.txt_code)
        self.content_layout.addWidget(self.card_code)

        self.scroll_area.setWidget(scroll_widget)
        self.container_layout.addWidget(self.scroll_area, 1)

        # 5. Interactive Sample Prompt Pills
        self.chips_frame = QFrame(self)
        chips_layout = QHBoxLayout(self.chips_frame)
        chips_layout.setContentsMargins(0, 2, 0, 2)
        chips_layout.setSpacing(4)

        self.chip_buttons = []
        for label, full_prompt in SAMPLE_PROMPTS:
            btn_chip = QPushButton(label, self.chips_frame)
            btn_chip.setToolTip(f"Click to immediately test: \"{full_prompt}\"")
            btn_chip.setStyleSheet("background: #1E2332; color: #F6D860; border: 1px solid rgba(246,216,96,0.3); border-radius: 6px; padding: 4px 8px; font-size: 10px; font-weight: 700;")
            btn_chip.clicked.connect(lambda _, p=full_prompt: self._on_chip_clicked(p))
            chips_layout.addWidget(btn_chip)
            self.chip_buttons.append(btn_chip)

        self.container_layout.addWidget(self.chips_frame)

        # 6. Quick Query Input Bar
        input_box = QHBoxLayout()
        input_box.setSpacing(4)

        self.txt_query = ClickFocusLineEdit(self)
        self.txt_query.setObjectName("QueryInput")
        self.txt_query.setPlaceholderText("💬 Type question & hit Enter...")
        self.txt_query.setStyleSheet("""
            QLineEdit#QueryInput {
                background: #181C26;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 6px 10px;
                color: #FFFFFF;
                font-size: 11.5px;
            }
        """)
        self.txt_query.returnPressed.connect(self._on_custom_query_send)

        self.btn_send = QPushButton("🚀 Send", self)
        self.btn_send.setObjectName("SendBtn")
        self.btn_send.setStyleSheet("""
            QPushButton#SendBtn {
                background: #F6D860;
                color: #12151C;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 800;
                font-size: 11px;
            }
        """)
        self.btn_send.clicked.connect(self._on_custom_query_send)

        self.btn_clear = QPushButton("🗑️", self)
        self.btn_clear.setFixedSize(28, 28)
        self.btn_clear.setToolTip("Clear All Content (Ctrl+Alt+C)")
        self.btn_clear.setStyleSheet("background: #1E2332; color: #8E95A5; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;")
        self.btn_clear.clicked.connect(self.clear_content)

        input_box.addWidget(self.txt_query, 1)
        input_box.addWidget(self.btn_send)
        input_box.addWidget(self.btn_clear)
        self.container_layout.addLayout(input_box)

        self.main_layout.addWidget(self.card_container)
        self._refresh_rendered_cards()

    def _connect_signals(self):
        self.signaler.transcript_updated.connect(self.set_transcript_text)
        self.signaler.qa_token_stream.connect(self.append_qa_token)
        self.signaler.qa_card_complete.connect(self.set_qa_complete)
        self.signaler.stage_token_stream.connect(lambda s, t: self.append_qa_token(t))
        self.signaler.stage_card_complete.connect(lambda s, c: self.set_qa_complete(c))
        self.signaler.clear_triggered.connect(self.clear_content)
        self.signaler.toggle_visibility_signal.connect(self.toggle_visibility)
        self.signaler.toggle_click_through_signal.connect(self.toggle_click_through)

    def set_transcript_text(self, text: str):
        if text:
            self.lbl_transcript.setText(f">> {text}")
        else:
            self.lbl_transcript.setText(">> Listening to meeting audio stream...")

    def append_qa_token(self, token: str):
        self.full_stream_buffer += token
        ans_part, code_part = _split_qa_response(self.full_stream_buffer)
        self.raw_content_ans = ans_part
        self.raw_content_code = code_part
        self._refresh_rendered_cards()

    def set_qa_complete(self, full_text: str):
        self.full_stream_buffer = full_text or ""
        ans_part, code_part = _split_qa_response(self.full_stream_buffer)
        self.raw_content_ans = ans_part
        self.raw_content_code = code_part
        self.lbl_status.setText("🟢 Complete")
        self._refresh_rendered_cards()
        QTimer.singleShot(2500, lambda: self.lbl_status.setText("🟢 Ready"))

    def set_stage_card_content(self, stage: int, content: str):
        self.set_qa_complete(content)

    def _refresh_rendered_cards(self, pal: dict = None):
        if pal is None:
            ui_s = self.config.get("ui_settings") or {}
            styles = compile_hud_stylesheet(ui_s.get("theme") or "calm_buttercup", font_size=self.current_font_size)
            pal = styles["palette"]

        # 1. Render Direct Answer
        if self.raw_content_ans.strip():
            html_ans = render_markdown_to_qt_html(
                self.raw_content_ans,
                accent_color=pal["ans_color"],
                text_color=pal["text_primary"],
                bg_card=pal["card_hex"],
                font_size=self.current_font_size
            )
            self.txt_ans.setText(html_ans)
        else:
            self.txt_ans.setText(f"<div style='color:{pal['text_muted']}; font-style:italic;'>Direct, concise answer will stream here...</div>")

        # 2. Render Production Code
        if self.raw_content_code.strip():
            self.card_code.show()
            html_code = render_markdown_to_qt_html(
                self.raw_content_code,
                accent_color=pal["code_color"],
                text_color=pal["text_primary"],
                bg_card=pal["card_hex"],
                font_size=self.current_font_size
            )
            self.txt_code.setText(html_code)
        else:
            self.txt_code.setText(f"<div style='color:{pal['text_muted']}; font-style:italic;'>Production code snippet will appear here...</div>")

    def _on_chip_clicked(self, prompt: str):
        self.txt_query.setText(prompt)
        self._on_custom_query_send()

    def _on_custom_query_send(self):
        query = self.txt_query.text().strip()
        if query:
            self.lbl_transcript.setText(f">> Query: \"{query}\"")
            self.lbl_status.setText("⚡ Solving...")
            self.raw_content_ans = ""
            self.raw_content_code = ""
            self.full_stream_buffer = ""
            self.signaler.action_custom_query.emit(query)
            self.txt_query.clear()

    def _copy_code_to_clipboard(self):
        code_text = self.raw_content_code
        if code_text:
            clean_code = re.sub(r'```[a-zA-Z0-9_-]*\n(.*?)```', r'\1', code_text, flags=re.DOTALL).strip()
            QApplication.clipboard().setText(clean_code)
            self.lbl_status.setText("✓ Copied Code!")
            self.lbl_status.setStyleSheet("color: #38A169; font-size: 10px; font-weight: 700;")
            QTimer.singleShot(1400, lambda: self.lbl_status.setText("🟢 Ready"))

    def _toggle_code_collapse(self):
        self.is_code_collapsed = not self.is_code_collapsed
        if self.is_code_collapsed:
            self.txt_code.hide()
            self.btn_collapse_code.setText("▼ Code")
        else:
            self.txt_code.show()
            self.btn_collapse_code.setText("▲ Code")

    def _toggle_collapse(self):
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.scroll_area.hide()
            self.chips_frame.hide()
            self.resize(self.width(), 120)
            self.btn_collapse.setText("▼")
        else:
            self.scroll_area.show()
            self.chips_frame.show()
            ui_s = self.config.get("ui_settings", {})
            h = max(400, min(1080, int(ui_s.get("height", 640))))
            self.resize(self.width(), h)
            self.btn_collapse.setText("▲")

    def _increase_opacity(self):
        op = min(1.0, self.windowOpacity() + 0.05)
        self.setWindowOpacity(op)
        self.config.setdefault("ui_settings", {})["opacity"] = op

    def _decrease_opacity(self):
        op = max(0.20, self.windowOpacity() - 0.05)
        self.setWindowOpacity(op)
        self.config.setdefault("ui_settings", {})["opacity"] = op

    def toggle_click_through(self):
        self.is_click_through = not self.is_click_through
        hwnd = int(self.winId())
        set_click_through(hwnd, self.is_click_through)
        ghost_color = "#38A169" if self.is_click_through else "#8E95A5"
        self.btn_ghost.setStyleSheet(f"background: #1E2332; color: {ghost_color}; border: 1px solid {ghost_color}; border-radius: 5px; font-size: 11px;")

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def clear_content(self):
        self.raw_content_ans = ""
        self.raw_content_code = ""
        self.full_stream_buffer = ""
        self.lbl_transcript.setText(">> Listening to meeting audio stream...")
        self.txt_ans.setText("")
        self.txt_code.setText("")
        self._refresh_rendered_cards()

    def _init_vu_timer(self):
        self.vu_timer = QTimer(self)
        self.vu_timer.timeout.connect(self._update_live_vu)
        self.vu_timer.start(40)

    def _update_live_vu(self):
        if self.shm_ring is None:
            try:
                self.shm_ring = SharedAudioRing(name=SHM_NAME, create=False)
            except Exception:
                return

        try:
            sys_dbfs, mic_dbfs = self.shm_ring.get_vu_levels()
            active_dbfs = max(sys_dbfs, mic_dbfs)
            normalized = max(0.0, min(100.0, (active_dbfs + 60.0) / 60.0 * 100.0))

            cur_mode = self.vu_mode.lower() if hasattr(self, 'vu_mode') else "dots"
            if cur_mode == "dots":
                total_dots = 16
                active_dots = int((normalized / 100.0) * total_dots)
                dot_str = ("• " * active_dots) + ("◦ " * (total_dots - active_dots))
                color = "#E53E3E" if active_dbfs > -6.0 else ("#ECC94B" if active_dbfs > -18.0 else "#38A169")
                self.lbl_vu_dots.setText(dot_str.strip())
                self.lbl_vu_dots.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700; font-family: monospace;")
            elif cur_mode == "wave":
                self.wave_phase = (self.wave_phase + 1) % len(BRAILLE_WAVE_PATTERNS)
                num_bars = 16
                height_factor = max(1, int((normalized / 100.0) * 8))
                wave_str = "".join([BRAILLE_WAVE_PATTERNS[(self.wave_phase + i * height_factor) % len(BRAILLE_WAVE_PATTERNS)] for i in range(num_bars)])
                self.lbl_vu_dots.setText(f"[ {wave_str} ]")
                self.lbl_vu_dots.setStyleSheet("color: #F6D860; font-size: 11px; font-weight: 700; font-family: monospace;")
            else:
                self.lbl_vu_dots.setText(f"{active_dbfs:.1f} dBFS ({int(normalized)}%)")
        except Exception:
            pass

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.is_click_through:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
