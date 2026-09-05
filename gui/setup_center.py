import asyncio
import ctypes
import json
import os
import sys
import threading
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QImage, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QComboBox, QSlider,
    QTabWidget, QGroupBox, QCheckBox, QFrame, QMessageBox, QListWidget,
    QStackedWidget, QDoubleSpinBox, QSpinBox
)

from server.companion_server import get_local_ip, generate_pairing_url, generate_qr_code_image_bytes
from stealth.crypto_storage import dpapi_encrypt_string, dpapi_decrypt_string
from engine.shared_audio_ring import SharedAudioRing, SHM_NAME
from engine.llm_orchestrator import LLMOrchestrator

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro"
]


PRESENTATION_PRESETS = [
    "Technical Architecture Review & System Design",
    "Live Coding & Algorithm Walkthrough",
    "Client Presentation & Technical Pitch",
    "Executive Overview & Project Demo",
    "Behavioral & STAR Format Discussion",
    "DevOps & Incident Management Briefing"
]

BRAILLE_WAVE_PATTERNS = ["⣀", "⣄", "⣆", "⣇", "⣧", "⣷", "⣿", "⣾", "⣶", "⣤", "⣀", "⡀"]

class SetupCenter(QMainWindow):
    settings_changed = pyqtSignal(dict)

    def __init__(self, on_launch_callback=None):
        super().__init__()
        self.on_launch_callback = on_launch_callback
        self.config = self.load_config()
        self.shm_ring = None
        self.wave_phase = 0

        self.setWindowTitle("I Hate Interviews — Live AI Copilot")
        self.resize(920, 740)
        self.setMinimumSize(840, 660)
        self._apply_calm_modern_theme()
        self._init_ui()
        self._connect_live_sync_signals()
        self._init_vu_timer()

    def load_config(self) -> dict:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    keys = cfg.get("api_keys", {})
                    for k in ["gemini", "deepgram"]:
                        if k in keys:
                            keys[k] = dpapi_decrypt_string(keys[k])
                    cfg["api_keys"] = keys
                    return cfg
            except Exception as e:
                print(f"[SetupCenter] Error reading config: {e}")
        return {}

    def get_current_settings_dict(self) -> dict:
        gemini_raw = self.txt_gemini.text().strip()
        deepgram_raw = self.txt_deepgram.text().strip()

        cfg = dict(self.config)
        cfg["api_keys"] = {
            "gemini": gemini_raw,
            "deepgram": deepgram_raw
        }
        cfg["preferred_llm"] = "gemini"
        cfg["ai_settings"] = {
            "gemini_model": self.combo_gemini_model.currentText(),
            "custom_model": self.txt_custom_model.text().strip(),
            "temperature": float(self.spin_temp.value()),
            "max_tokens": int(self.spin_tokens.value()),
            "custom_prompt_prefix": self.txt_prompt_prefix.toPlainText().strip()
        }
        cfg["role_preset"] = self.combo_role.currentText()
        cfg["user_profile"] = {
            "name": self.txt_name.text().strip(),
            "years_of_experience": self.txt_exp.text().strip(),
            "primary_skills": self.txt_skills.text().strip(),
            "summary": self.txt_summary.toPlainText().strip(),
            "resume_text": self.txt_resume.toPlainText().strip(),
            "job_description_text": self.txt_jd.toPlainText().strip()
        }
        cfg["ui_settings"] = {
            "theme": self.combo_theme.currentText().lower().replace(" ", "_"),
            "opacity": float(self.slider_opacity.value()) / 100.0,
            "font_size": int(self.spin_font_size.value()),
            "border_radius": int(self.spin_border_radius.value()),
            "width": int(self.spin_hud_width.value()),
            "height": int(self.spin_hud_height.value()),
            "stealth_affinity": self.chk_stealth.isChecked(),
            "click_through_default": self.chk_click_through.isChecked(),
            "vu_mode": self.combo_vu_mode.currentText().lower()
        }
        cfg["audio_settings"] = {
            "sensitivity_threshold": float(self.spin_audio_thresh.value()),
            "silence_timeout_sec": float(self.spin_silence_timeout.value())
        }
        return cfg

    def save_config(self):
        cfg = self.get_current_settings_dict()
        cfg_to_save = dict(cfg)
        cfg_to_save["api_keys"] = {
            "gemini": dpapi_encrypt_string(cfg["api_keys"]["gemini"]),
            "deepgram": dpapi_encrypt_string(cfg["api_keys"]["deepgram"])
        }
        self.config = cfg

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg_to_save, f, indent=2)
            self._emit_live_change()
            self.btn_save.setText("✓ Settings Saved!")
            QTimer.singleShot(1500, lambda: self.btn_save.setText("💾 Save All Settings"))
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Failed to write config.json: {e}")

    def _connect_live_sync_signals(self):
        self.spin_hud_width.valueChanged.connect(self._emit_live_change)
        self.spin_hud_height.valueChanged.connect(self._emit_live_change)
        self.slider_opacity.valueChanged.connect(self._emit_live_change)
        self.spin_font_size.valueChanged.connect(self._emit_live_change)
        self.spin_border_radius.valueChanged.connect(self._emit_live_change)
        self.combo_theme.currentIndexChanged.connect(self._emit_live_change)
        self.combo_vu_mode.currentIndexChanged.connect(self._emit_live_change)

        self.chk_stealth.toggled.connect(self._emit_live_change)
        self.chk_click_through.toggled.connect(self._emit_live_change)

        self.combo_gemini_model.currentIndexChanged.connect(self._emit_live_change)
        self.txt_custom_model.textChanged.connect(self._emit_live_change)
        self.spin_temp.valueChanged.connect(self._emit_live_change)
        self.spin_tokens.valueChanged.connect(self._emit_live_change)
        self.txt_prompt_prefix.textChanged.connect(self._emit_live_change)

        self.spin_audio_thresh.valueChanged.connect(self._emit_live_change)
        self.spin_silence_timeout.valueChanged.connect(self._emit_live_change)

        self.combo_role.currentIndexChanged.connect(self._emit_live_change)
        self.txt_name.textChanged.connect(self._emit_live_change)
        self.txt_exp.textChanged.connect(self._emit_live_change)
        self.txt_skills.textChanged.connect(self._emit_live_change)
        self.txt_summary.textChanged.connect(self._emit_live_change)
        self.txt_resume.textChanged.connect(self._emit_live_change)
        self.txt_jd.textChanged.connect(self._emit_live_change)

        self.txt_gemini.textChanged.connect(self._emit_live_change)
        self.txt_deepgram.textChanged.connect(self._emit_live_change)


    def _emit_live_change(self):
        cfg = self.get_current_settings_dict()
        self.settings_changed.emit(cfg)

    def _apply_calm_modern_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #12151C;
                color: #F0F2F7;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
            }
            QGroupBox {
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                margin-top: 14px;
                padding-top: 14px;
                font-weight: 700;
                font-size: 12px;
                color: #F6D860;
                background-color: #181C26;
            }
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #1E2332;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
                padding: 7px 10px;
                color: #FFFFFF;
                font-size: 12px;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #F6D860;
                background-color: #222838;
            }
            QPushButton {
                background-color: #1E2332;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 8px 16px;
                color: #F0F2F7;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #262D40;
                border-color: #F6D860;
                color: #FFFFFF;
            }
            QPushButton#LaunchBtn {
                background-color: #F6D860;
                border: none;
                color: #12151C;
                font-size: 14px;
                font-weight: 800;
                padding: 12px;
                border-radius: 10px;
                letter-spacing: 0.5px;
            }
            QPushButton#LaunchBtn:hover {
                background-color: #FBEA8D;
            }
            QPushButton#HeroLaunchBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F6D860, stop:1 #ECC94B);
                border: none;
                color: #12151C;
                font-size: 16px;
                font-weight: 900;
                padding: 16px 24px;
                border-radius: 12px;
                letter-spacing: 0.5px;
            }
            QPushButton#HeroLaunchBtn:hover {
                background: #FBEA8D;
            }
            QListWidget {
                background-color: #151822;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: #8E95A5;
                font-size: 12px;
                font-weight: 600;
                padding: 4px;
            }
            QListWidget::item {
                padding: 12px 10px;
                border-radius: 8px;
                margin-bottom: 3px;
            }
            QListWidget::item:selected {
                background-color: #1E2332;
                color: #F6D860;
                border-left: 3px solid #F6D860;
                font-weight: 700;
            }
            QCheckBox {
                color: #E2E8F0;
                font-size: 12px;
            }
        """)

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        # Header Console Bar with Live Audio Visualizer
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            background: #181C26;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 8px 14px;
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(4, 2, 4, 2)

        title_box = QVBoxLayout()
        title_lbl = QLabel("🎙️ I HATE INTERVIEWS // CONTROL HUB", self)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 800; color: #F6D860; letter-spacing: 0.5px;")
        sub_lbl = QLabel("Ultra-low-latency real-time live AI copilot powered by Gemini 3.7 / 3.6 / 2.5", self)
        sub_lbl.setStyleSheet("font-size: 11px; color: #8E95A5;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_layout.addLayout(title_box)

        # Live VU Level Indicator
        vu_box = QVBoxLayout()
        vu_box.setSpacing(2)
        vu_title = QLabel("LOOPBACK AUDIO LEVEL:")
        vu_title.setStyleSheet("font-size: 9px; font-weight: 700; color: #8E95A5; text-align: right;")
        self.lbl_vu_header = QLabel("• • • • • • • • ◦ ◦ ◦ ◦ ◦ ◦ ◦ ◦")
        self.lbl_vu_header.setStyleSheet("font-size: 11px; color: #38A169; font-weight: 700; font-family: monospace;")
        self.lbl_vu_header.setAlignment(Qt.AlignmentFlag.AlignRight)
        vu_box.addWidget(vu_title)
        vu_box.addWidget(self.lbl_vu_header)
        header_layout.addLayout(vu_box)

        root_layout.addWidget(header_frame)

        # Main Body: Left Sidebar + Right Stacked Pages
        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(210)
        self.nav_list.addItem("⚡ Quick Start & Playground")
        self.nav_list.addItem("🤖 AI Engine & Models")
        self.nav_list.addItem("🎙️ Voice & Audio Capture")
        self.nav_list.addItem("🎨 HUD Customization")
        self.nav_list.addItem("⌨️ Hotkeys & Shortcuts")
        self.nav_list.addItem("👤 Presenter Profile")
        self.nav_list.addItem("📱 Mobile Teleprompter")
        self.nav_list.setCurrentRow(0)
        self.nav_list.currentRowChanged.connect(self._on_nav_change)
        body_layout.addWidget(self.nav_list)

        self.stack = QStackedWidget()
        self.page_playground = QWidget()
        self.page_ai = QWidget()
        self.page_audio = QWidget()
        self.page_appearance = QWidget()
        self.page_hotkeys = QWidget()
        self.page_profile = QWidget()
        self.page_mobile = QWidget()

        self._setup_page_playground()
        self._setup_page_ai()
        self._setup_page_audio()
        self._setup_page_appearance()
        self._setup_page_hotkeys()
        self._setup_page_profile()
        self._setup_page_mobile()

        self.stack.addWidget(self.page_playground)
        self.stack.addWidget(self.page_ai)
        self.stack.addWidget(self.page_audio)
        self.stack.addWidget(self.page_appearance)
        self.stack.addWidget(self.page_hotkeys)
        self.stack.addWidget(self.page_profile)
        self.stack.addWidget(self.page_mobile)
        body_layout.addWidget(self.stack, 1)

        root_layout.addLayout(body_layout, 1)

        # Footer Actions
        footer_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 Save All Settings", self)
        self.btn_save.clicked.connect(self.save_config)
        self.btn_save.setFixedHeight(42)

        self.btn_launch = QPushButton("🚀 Launch Presenter HUD", self)
        self.btn_launch.setObjectName("LaunchBtn")
        self.btn_launch.setFixedHeight(42)
        self.btn_launch.clicked.connect(self._handle_launch)

        footer_layout.addWidget(self.btn_save, 1)
        footer_layout.addWidget(self.btn_launch, 2)
        root_layout.addLayout(footer_layout)

    def _on_nav_change(self, idx: int):
        self.stack.setCurrentIndex(idx)

    def _setup_page_playground(self):
        layout = QVBoxLayout(self.page_playground)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(12)

        # Hero Launch Card
        hero_card = QFrame()
        hero_card.setStyleSheet("""
            background: #181C26;
            border: 1px solid rgba(246, 216, 96, 0.35);
            border-radius: 14px;
            padding: 16px;
        """)
        hc_layout = QVBoxLayout(hero_card)
        hc_layout.setSpacing(10)

        h_title = QLabel("Ready to crush this technical interview?")
        h_title.setStyleSheet("font-size: 16px; font-weight: 800; color: #FFFFFF;")
        h_desc = QLabel("The floating HUD stays locked on top of all windows, is 100% invisible to screen shares (Zoom/Meet/Teams), and drops direct answers + prod-grade code in real time.")
        h_desc.setWordWrap(True)
        h_desc.setStyleSheet("font-size: 12px; color: #8E95A5; line-height: 1.4;")
        hc_layout.addWidget(h_title)
        hc_layout.addWidget(h_desc)

        btn_hero_launch = QPushButton("🚀 Open Floating Presenter HUD", hero_card)
        btn_hero_launch.setObjectName("HeroLaunchBtn")
        btn_hero_launch.clicked.connect(self._handle_launch)
        hc_layout.addWidget(btn_hero_launch)
        layout.addWidget(hero_card)

        # Quick Test & Interactive Features
        test_group = QGroupBox("🧪 Instant Playground & Subsystem Verification", self.page_playground)
        tg_layout = QVBoxLayout(test_group)
        tg_layout.setSpacing(10)

        # 1-Click Topic Simulator
        tg_layout.addWidget(QLabel("1-Click Simulated Questions (Test the LLM Streaming Engine):"))
        chips_box = QHBoxLayout()
        test_prompts = [
            ("💡 Rate Limiter", "Design a distributed rate limiter with Redis token bucket"),
            ("💡 LRU Cache", "Implement an LRU Cache with O(1) get/put operations"),
            ("💡 Raft Consensus", "Explain leader election and log replication in Raft")
        ]
        for lbl, prompt in test_prompts:
            btn = QPushButton(lbl)
            btn.setStyleSheet("background: #1E2332; color: #F6D860; border: 1px solid rgba(246,216,96,0.3); border-radius: 8px; padding: 6px 10px; font-weight: 700;")
            btn.clicked.connect(lambda _, p=prompt: self._run_playground_query(p))
            chips_box.addWidget(btn)
        tg_layout.addLayout(chips_box)

        # Live Results Box
        self.lbl_play_results = QLabel("Click any sample question above to test live generation.")
        self.lbl_play_results.setWordWrap(True)
        self.lbl_play_results.setStyleSheet("""
            background: #12151C;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 10px;
            color: #E2E8F0;
            font-size: 11.5px;
            line-height: 1.4;
        """)
        self.lbl_play_results.setMinimumHeight(100)
        tg_layout.addWidget(self.lbl_play_results)

        layout.addWidget(test_group)
        layout.addStretch()

    def _run_playground_query(self, query: str):
        self.lbl_play_results.setText(f"⚡ Streaming response for: \"{query}\"...\n")
        cfg = self.get_current_settings_dict()
        orch = LLMOrchestrator(cfg)

        def worker():
            async def run_probe():
                from engine.stage_manager import InterviewStage
                def on_tok(tok):
                    cur = self.lbl_play_results.text()
                    self.lbl_play_results.setText(cur + tok)

                await orch.stream_stage_response(
                    stage=InterviewStage.STAGE_1_CLARIFY,
                    interviewer_input=query,
                    on_token=on_tok
                )

            asyncio.run(run_probe())

        threading.Thread(target=worker, daemon=True).start()

    def _setup_page_ai(self):
        layout = QVBoxLayout(self.page_ai)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(14)

        # 1. API Credentials Group
        cred_group = QGroupBox("🔑 Google Gemini Credentials (DPAPI Encrypted at Rest)", self.page_ai)
        cg_layout = QVBoxLayout(cred_group)
        cg_layout.setContentsMargins(14, 18, 14, 14)
        cg_layout.setSpacing(10)

        lbl_g = QLabel("Google Gemini API Key (Gemini 3.8 / 3.7 / 3.6 / 2.5 Series):")
        lbl_g.setStyleSheet("font-weight: 600; color: #F0F2F7; font-size: 12px;")
        cg_layout.addWidget(lbl_g)
        self.txt_gemini = QLineEdit(self.config.get("api_keys", {}).get("gemini", ""))
        self.txt_gemini.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_gemini.setPlaceholderText("Enter your Google Gemini API key (AIzaSy...)")
        self.txt_gemini.setFixedHeight(38)
        cg_layout.addWidget(self.txt_gemini)

        self.lbl_gemini_hint = QLabel("")
        self.lbl_gemini_hint.setStyleSheet("font-size: 11px; color: #8E95A5; margin-top: -4px;")
        cg_layout.addWidget(self.lbl_gemini_hint)
        self.txt_gemini.textChanged.connect(self._validate_gemini_key_live)
        self._validate_gemini_key_live(self.txt_gemini.text())


        lbl_dg = QLabel("Deepgram Nova-2 API Key (Optional — Free Speech Recognition with VAD is built-in):")
        lbl_dg.setStyleSheet("font-weight: 600; color: #8E95A5; font-size: 11px;")
        cg_layout.addWidget(lbl_dg)
        self.txt_deepgram = QLineEdit(self.config.get("api_keys", {}).get("deepgram", ""))
        self.txt_deepgram.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_deepgram.setPlaceholderText("Leave empty to use the built-in free speech recognition engine")
        self.txt_deepgram.setFixedHeight(38)
        cg_layout.addWidget(self.txt_deepgram)

        layout.addWidget(cred_group)

        # 2. Model Selection & Hyperparameters
        model_group = QGroupBox("🧠 Google Gemini Model & Generation Settings", self.page_ai)
        mg_layout = QVBoxLayout(model_group)
        mg_layout.setContentsMargins(14, 18, 14, 14)
        mg_layout.setSpacing(12)

        # Row 1: Gemini Model Selector & Custom Override
        m_row = QHBoxLayout()
        m_row.setSpacing(14)

        v_m1 = QVBoxLayout()
        v_m1.setSpacing(6)
        lbl_m1 = QLabel("Active Gemini Model:")
        lbl_m1.setStyleSheet("font-weight: 600; color: #F0F2F7; font-size: 12px;")
        v_m1.addWidget(lbl_m1)
        self.combo_gemini_model = QComboBox()
        self.combo_gemini_model.addItems(GEMINI_MODELS)
        self.combo_gemini_model.setFixedHeight(38)
        cur_m = self.config.get("ai_settings", {}).get("gemini_model", "gemini-3.7-flash")
        m_idx = self.combo_gemini_model.findText(cur_m)
        if m_idx >= 0:
            self.combo_gemini_model.setCurrentIndex(m_idx)
        v_m1.addWidget(self.combo_gemini_model)
        m_row.addLayout(v_m1, 1)

        v_m2 = QVBoxLayout()
        v_m2.setSpacing(6)
        lbl_m2 = QLabel("Custom Model Override (Optional):")
        lbl_m2.setStyleSheet("font-weight: 600; color: #8E95A5; font-size: 12px;")
        v_m2.addWidget(lbl_m2)
        self.txt_custom_model = QLineEdit(self.config.get("ai_settings", {}).get("custom_model", ""))
        self.txt_custom_model.setPlaceholderText("e.g. gemini-3.8-flash or custom endpoint")
        self.txt_custom_model.setFixedHeight(38)
        v_m2.addWidget(self.txt_custom_model)
        m_row.addLayout(v_m2, 1)
        mg_layout.addLayout(m_row)

        # Row 2: Temperature and Max Tokens
        t_row = QHBoxLayout()
        t_row.setSpacing(14)

        v_t1 = QVBoxLayout()
        v_t1.setSpacing(6)
        lbl_t1 = QLabel("Temperature (0.0 = Precise / Code, 0.7 = Creative):")
        lbl_t1.setStyleSheet("font-weight: 600; color: #F0F2F7; font-size: 12px;")
        v_t1.addWidget(lbl_t1)
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 1.0)
        self.spin_temp.setSingleStep(0.05)
        self.spin_temp.setFixedHeight(38)
        self.spin_temp.setValue(float(self.config.get("ai_settings", {}).get("temperature", 0.2)))
        v_t1.addWidget(self.spin_temp)
        t_row.addLayout(v_t1, 1)

        v_t2 = QVBoxLayout()
        v_t2.setSpacing(6)
        lbl_t2 = QLabel("Max Output Tokens:")
        lbl_t2.setStyleSheet("font-weight: 600; color: #F0F2F7; font-size: 12px;")
        v_t2.addWidget(lbl_t2)
        self.spin_tokens = QSpinBox()
        self.spin_tokens.setRange(256, 4096)
        self.spin_tokens.setSingleStep(128)
        self.spin_tokens.setFixedHeight(38)
        self.spin_tokens.setValue(int(self.config.get("ai_settings", {}).get("max_tokens", 1200)))
        v_t2.addWidget(self.spin_tokens)
        t_row.addLayout(v_t2, 1)
        mg_layout.addLayout(t_row)

        # Row 3: Custom Persona Prompt Prefix
        v_p = QVBoxLayout()
        v_p.setSpacing(6)
        lbl_p = QLabel("Custom Persona Prompt Prefix (Optional):")
        lbl_p.setStyleSheet("font-weight: 600; color: #8E95A5; font-size: 12px;")
        v_p.addWidget(lbl_p)
        self.txt_prompt_prefix = QTextEdit()
        self.txt_prompt_prefix.setFixedHeight(50)
        self.txt_prompt_prefix.setPlaceholderText("Extra instructions to guide Gemini before every answer...")
        self.txt_prompt_prefix.setPlainText(self.config.get("ai_settings", {}).get("custom_prompt_prefix", ""))
        v_p.addWidget(self.txt_prompt_prefix)
        mg_layout.addLayout(v_p)

        layout.addWidget(model_group)

        # 3. Latency Diagnostics
        diag_group = QGroupBox("⚡ 1-Click Streaming TTFT Latency Probing", self.page_ai)
        dg_layout = QVBoxLayout(diag_group)
        dg_layout.setContentsMargins(14, 18, 14, 14)
        dg_layout.setSpacing(10)

        d_top = QHBoxLayout()
        self.btn_benchmark = QPushButton("⚡ Benchmark Gemini API")
        self.btn_benchmark.setFixedHeight(38)
        self.btn_benchmark.clicked.connect(self._run_live_diagnostics)
        self.lbl_diag_status = QLabel("Ready for streaming probe.")
        self.lbl_diag_status.setStyleSheet("color: #8E95A5; font-size: 11px;")
        d_top.addWidget(self.btn_benchmark)
        d_top.addWidget(self.lbl_diag_status, 1)
        dg_layout.addLayout(d_top)

        self.lbl_diag_results = QLabel("")
        self.lbl_diag_results.setWordWrap(True)
        self.lbl_diag_results.setStyleSheet("font-family: monospace; font-size: 11px; line-height: 1.4;")
        dg_layout.addWidget(self.lbl_diag_results)

        layout.addWidget(diag_group)
        layout.addStretch()

    def _validate_gemini_key_live(self, text: str):
        t = text.strip()
        if not t:
            self.lbl_gemini_hint.setText("ℹ️ Free offline knowledge engine will answer queries until Gemini API key is configured.")
            self.lbl_gemini_hint.setStyleSheet("font-size: 11px; color: #8E95A5; margin-top: -4px;")
        elif not (t.startswith("AIza") or t.startswith("AQ.")):
            self.lbl_gemini_hint.setText(f"⚠️ Warning: Key starts with '{t[:6]}...'. Google Gemini keys must start with 'AIzaSy' or 'AQ.'.")
            self.lbl_gemini_hint.setStyleSheet("font-size: 11px; color: #ECC94B; font-weight: 700; margin-top: -4px;")
        else:
            self.lbl_gemini_hint.setText("✅ Valid Google Gemini key format")
            self.lbl_gemini_hint.setStyleSheet("font-size: 11px; color: #38A169; font-weight: 700; margin-top: -4px;")


    def _run_live_diagnostics(self):

        self.lbl_diag_status.setText("Probing streaming latency...")
        self.btn_benchmark.setEnabled(False)

        cfg = self.get_current_settings_dict()
        orch = LLMOrchestrator(cfg)

        def worker():
            async def run_probes():
                gem_ok, gem_ttft, gem_msg = await orch.benchmark_provider_ttft("gemini", timeout=3.5)
                dg_ok, dg_ttft, dg_msg = await orch.benchmark_provider_ttft("deepgram", timeout=3.5)

                lines = []
                if gem_ok:
                    lines.append(f'<span style="color:#48BB78;"><b>• GOOGLE GEMINI ({orch.get_gemini_model_name().upper()}):</b> ✅ {gem_msg}</span>')
                else:
                    lines.append(f'<span style="color:#FC8181;"><b>• GOOGLE GEMINI ({orch.get_gemini_model_name().upper()}):</b> ❌ {gem_msg}</span>')

                if self.txt_deepgram.text().strip():
                    if dg_ok:
                        lines.append(f'<span style="color:#48BB78;"><b>• DEEPGRAM NOVA-2:</b> ✅ {dg_msg}</span>')
                    else:
                        lines.append(f'<span style="color:#FC8181;"><b>• DEEPGRAM NOVA-2:</b> ❌ {dg_msg}</span>')
                else:
                    lines.append('<span style="color:#68D391;"><b>• SPEECH ENGINE:</b> ✅ Universal Free Engine Active (VAD)</span>')
                return "<br>".join(lines)

            res_text = asyncio.run(run_probes())
            self.lbl_diag_results.setText(res_text)
            self.lbl_diag_status.setText("Diagnostics complete.")
            self.btn_benchmark.setEnabled(True)

        threading.Thread(target=worker, daemon=True).start()


    def _setup_page_audio(self):
        layout = QVBoxLayout(self.page_audio)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        audio_group = QGroupBox("🎙️ Voice & Audio Subsystem", self.page_audio)
        ag_layout = QVBoxLayout(audio_group)
        ag_layout.setSpacing(8)

        t_row = QHBoxLayout()
        t_row.addWidget(QLabel("Audio Activity Sensitivity Threshold:"))
        self.spin_audio_thresh = QDoubleSpinBox()
        self.spin_audio_thresh.setDecimals(3)
        self.spin_audio_thresh.setRange(0.001, 0.2)
        self.spin_audio_thresh.setSingleStep(0.005)
        self.spin_audio_thresh.setValue(float(self.config.get("audio_settings", {}).get("sensitivity_threshold", 0.02)))
        t_row.addWidget(self.spin_audio_thresh)
        ag_layout.addLayout(t_row)

        s_row = QHBoxLayout()
        s_row.addWidget(QLabel("Silence Heartbeat Interval (Seconds):"))
        self.spin_silence_timeout = QDoubleSpinBox()
        self.spin_silence_timeout.setRange(0.5, 5.0)
        self.spin_silence_timeout.setSingleStep(0.2)
        self.spin_silence_timeout.setValue(float(self.config.get("audio_settings", {}).get("silence_timeout_sec", 1.5)))
        s_row.addWidget(self.spin_silence_timeout)
        ag_layout.addLayout(s_row)

        layout.addWidget(audio_group)
        layout.addStretch()

    def _setup_page_appearance(self):
        layout = QVBoxLayout(self.page_appearance)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        ui_group = QGroupBox("🎨 HUD Appearance & Dimensions (Live Dynamic Sync)", self.page_appearance)
        ug_layout = QVBoxLayout(ui_group)
        ug_layout.setSpacing(8)

        th_row = QHBoxLayout()
        th_row.addWidget(QLabel("Color Palette & Theme:"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Calm Buttercup", "Gentle Sage", "Muted Slate", "OLED Pure Black"])
        cur_th = self.config.get("ui_settings", {}).get("theme", "calm_buttercup").replace("_", " ").title()
        th_idx = self.combo_theme.findText(cur_th)
        if th_idx >= 0:
            self.combo_theme.setCurrentIndex(th_idx)
        th_row.addWidget(self.combo_theme, 1)
        ug_layout.addLayout(th_row)

        vu_row = QHBoxLayout()
        vu_row.addWidget(QLabel("Audio VU Equalizer Style:"))
        self.combo_vu_mode = QComboBox()
        self.combo_vu_mode.addItems(["Dots", "Wave", "Numeric"])
        cur_vum = self.config.get("ui_settings", {}).get("vu_mode", "dots").capitalize()
        v_idx = self.combo_vu_mode.findText(cur_vum)
        if v_idx >= 0:
            self.combo_vu_mode.setCurrentIndex(v_idx)
        vu_row.addWidget(self.combo_vu_mode, 1)
        ug_layout.addLayout(vu_row)

        dim_row = QHBoxLayout()
        v_w = QVBoxLayout()
        v_w.addWidget(QLabel("HUD Width (px):"))
        self.spin_hud_width = QSpinBox()
        self.spin_hud_width.setRange(280, 650)
        self.spin_hud_width.setValue(int(self.config.get("ui_settings", {}).get("width", 370)))
        v_w.addWidget(self.spin_hud_width)
        dim_row.addLayout(v_w)

        v_h = QVBoxLayout()
        v_h.addWidget(QLabel("HUD Height (px):"))
        self.spin_hud_height = QSpinBox()
        self.spin_hud_height.setRange(400, 1080)
        self.spin_hud_height.setValue(int(self.config.get("ui_settings", {}).get("height", 640)))
        v_h.addWidget(self.spin_hud_height)
        dim_row.addLayout(v_h)
        ug_layout.addLayout(dim_row)

        f_row = QHBoxLayout()
        v_f = QVBoxLayout()
        v_f.addWidget(QLabel("Font Size (px):"))
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(9, 20)
        self.spin_font_size.setValue(int(self.config.get("ui_settings", {}).get("font_size", 13)))
        v_f.addWidget(self.spin_font_size)
        f_row.addLayout(v_f)

        v_b = QVBoxLayout()
        v_b.addWidget(QLabel("Corner Radius (px):"))
        self.spin_border_radius = QSpinBox()
        self.spin_border_radius.setRange(4, 24)
        self.spin_border_radius.setValue(int(self.config.get("ui_settings", {}).get("border_radius", 14)))
        v_b.addWidget(self.spin_border_radius)
        f_row.addLayout(v_b)
        ug_layout.addLayout(f_row)

        op_row = QHBoxLayout()
        op_row.addWidget(QLabel("HUD Opacity:"))
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_opacity.setRange(20, 100)
        cur_op = int(self.config.get("ui_settings", {}).get("opacity", 0.96) * 100)
        self.slider_opacity.setValue(cur_op)
        self.lbl_op_val = QLabel(f"{cur_op}%")
        self.slider_opacity.valueChanged.connect(lambda v: self.lbl_op_val.setText(f"{v}%"))
        op_row.addWidget(self.slider_opacity, 1)
        op_row.addWidget(self.lbl_op_val)
        ug_layout.addLayout(op_row)

        self.chk_stealth = QCheckBox("Exclude HUD from Screen Shares (WDA_EXCLUDEFROMCAPTURE 0x11)")
        self.chk_stealth.setChecked(self.config.get("ui_settings", {}).get("stealth_affinity", True))
        ug_layout.addWidget(self.chk_stealth)

        self.chk_click_through = QCheckBox("Enable Ghost Click-Through HUD (Pass mouse clicks to desktop)")
        self.chk_click_through.setChecked(self.config.get("ui_settings", {}).get("click_through_default", False))
        ug_layout.addWidget(self.chk_click_through)

        layout.addWidget(ui_group)
        layout.addStretch()

    def _setup_page_hotkeys(self):
        layout = QVBoxLayout(self.page_hotkeys)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        hk_group = QGroupBox("⌨️ Global Hotkeys & Action Mapping", self.page_hotkeys)
        hkg_layout = QVBoxLayout(hk_group)
        hkg_layout.setSpacing(8)

        hotkeys_info = [
            ("Ctrl + Alt + Q", "Direct QA Solve", "Solves currently transcribed or typed technical question"),
            ("Ctrl + Alt + S", "Slide Snip & Solve", "Captures active presentation window silently with CLAHE"),
            ("Ctrl + Alt + H", "Visibility Toggle", "Shows or hides the floating presenter HUD"),
            ("Ctrl + Alt + T", "Click-Through Toggle", "Passes mouse clicks directly through to slide decks"),
            ("Ctrl + Alt + C", "Clear Overlay", "Clears transcript buffer and Q&A answer cards")
        ]


        for hk, name, desc in hotkeys_info:
            row = QHBoxLayout()
            lbl_k = QLabel(hk)
            lbl_k.setStyleSheet("background: #1E2332; border: 1px solid rgba(255,255,255,0.12); border-radius: 6px; padding: 4px 8px; font-weight: 700; color: #F6D860; font-family: monospace;")
            lbl_n = QLabel(name)
            lbl_n.setStyleSheet("font-weight: 600; color: #FFFFFF;")
            lbl_d = QLabel(f"— {desc}")
            lbl_d.setStyleSheet("color: #8E95A5; font-size: 11px;")
            row.addWidget(lbl_k)
            row.addWidget(lbl_n)
            row.addWidget(lbl_d, 1)
            hkg_layout.addLayout(row)

        layout.addWidget(hk_group)
        layout.addStretch()

    def _setup_page_profile(self):
        layout = QVBoxLayout(self.page_profile)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        preset_box = QHBoxLayout()
        preset_box.addWidget(QLabel("Presentation Preset:"))
        self.combo_role = QComboBox()
        self.combo_role.addItems(PRESENTATION_PRESETS)
        cur_role = self.config.get("role_preset", PRESENTATION_PRESETS[0])
        idx = self.combo_role.findText(cur_role)
        if idx >= 0:
            self.combo_role.setCurrentIndex(idx)
        preset_box.addWidget(self.combo_role, 1)
        layout.addLayout(preset_box)

        grid_box = QHBoxLayout()
        v1 = QVBoxLayout()
        v1.addWidget(QLabel("Speaker Name:"))
        self.txt_name = QLineEdit(self.config.get("user_profile", {}).get("name", "Speaker"))
        v1.addWidget(self.txt_name)
        grid_box.addLayout(v1)

        v2 = QVBoxLayout()
        v2.addWidget(QLabel("Experience / Domain Role:"))
        self.txt_exp = QLineEdit(self.config.get("user_profile", {}).get("years_of_experience", "Senior Staff Engineer"))
        v2.addWidget(self.txt_exp)
        grid_box.addLayout(v2)
        layout.addLayout(grid_box)

        layout.addWidget(QLabel("Core Topics / Tech Focus:"))
        self.txt_skills = QLineEdit(self.config.get("user_profile", {}).get("primary_skills", "Distributed Systems, Microservices, Cloud Architecture, Scalability"))
        layout.addWidget(self.txt_skills)

        layout.addWidget(QLabel("Overview / Elevator Thesis:"))
        self.txt_summary = QTextEdit()
        self.txt_summary.setFixedHeight(45)
        self.txt_summary.setPlainText(self.config.get("user_profile", {}).get("summary", ""))
        layout.addWidget(self.txt_summary)

        r_box = QHBoxLayout()
        r_col = QVBoxLayout()
        r_col.addWidget(QLabel("Speaker Background / Talking Points:"))
        self.txt_resume = QTextEdit()
        self.txt_resume.setPlaceholderText("Paste speaker notes, resume highlights, or talking points...")
        self.txt_resume.setPlainText(self.config.get("user_profile", {}).get("resume_text", ""))
        r_col.addWidget(self.txt_resume)
        r_box.addLayout(r_col)

        jd_col = QVBoxLayout()
        jd_col.addWidget(QLabel("Meeting Agenda & Requirements:"))
        self.txt_jd = QTextEdit()
        self.txt_jd.setPlaceholderText("Paste meeting agenda, client requirements, or discussion topics...")
        self.txt_jd.setPlainText(self.config.get("user_profile", {}).get("job_description_text", ""))
        jd_col.addWidget(self.txt_jd)
        r_box.addLayout(jd_col)

        layout.addLayout(r_box, 1)

    def _setup_page_mobile(self):
        layout = QVBoxLayout(self.page_mobile)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        port = self.config.get("server_settings", {}).get("port", 8000)
        pairing_url = generate_pairing_url(port=port)

        info_box = QFrame()
        info_box.setStyleSheet("background: #181C26; border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 10px;")
        ib_layout = QVBoxLayout(info_box)
        
        ib_title = QLabel("📱 Secure Teleprompter Companion (Token Authenticated)")
        ib_title.setStyleSheet("font-weight: 700; color: #38A169; font-size: 13px;")
        ib_desc = QLabel("Scan this QR code from your phone and place it directly beneath your webcam for natural eye contact with zero horizontal eye saccades.")
        ib_desc.setWordWrap(True)
        ib_desc.setStyleSheet("color: #8E95A5; font-size: 12px;")
        
        ib_layout.addWidget(ib_title)
        ib_layout.addWidget(ib_desc)
        layout.addWidget(info_box)

        qr_container = QHBoxLayout()
        self.lbl_qr = QLabel()
        self.lbl_qr.setFixedSize(160, 160)
        self.lbl_qr.setStyleSheet("background: #FFFFFF; border-radius: 8px; padding: 4px;")
        self.lbl_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)

        qr_bytes = generate_qr_code_image_bytes(pairing_url)
        qimg = QImage.fromData(qr_bytes)
        self.lbl_qr.setPixmap(QPixmap.fromImage(qimg).scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio))

        qr_container.addWidget(self.lbl_qr)

        url_box = QVBoxLayout()
        url_lbl = QLabel(f"Secure Pairing URL: <a href='{pairing_url}' style='color: #F6D860;'>{pairing_url[:38]}...</a>")
        url_lbl.setOpenExternalLinks(True)
        url_lbl.setStyleSheet("font-size: 12px; font-weight: 700;")
        
        usb_info = QLabel("🔒 Corporate Wi-Fi Isolation Fallback:\nConnect via USB & run:\n<code>adb reverse tcp:8000 tcp:8000</code>\nthen open <b>http://localhost:8000</b> on mobile.")
        usb_info.setWordWrap(True)
        usb_info.setStyleSheet("color: #8E95A5; font-size: 11px; margin-top: 4px;")

        url_box.addWidget(url_lbl)
        url_box.addWidget(usb_info)
        qr_container.addLayout(url_box, 1)

        layout.addLayout(qr_container)
        layout.addStretch()

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
            sys_dbfs, _ = self.shm_ring.get_vu_levels()
            normalized = max(0.0, min(100.0, (sys_dbfs + 60.0) / 60.0 * 100.0))

            cur_mode = self.combo_vu_mode.currentText().lower()
            if cur_mode == "dots":
                total_dots = 16
                active_dots = int((normalized / 100.0) * total_dots)
                dot_str = ("• " * active_dots) + ("◦ " * (total_dots - active_dots))
                color = "#E53E3E" if sys_dbfs > -6.0 else "#38A169"
                self.lbl_vu_header.setText(dot_str.strip())
                self.lbl_vu_header.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: 700;")
            elif cur_mode == "wave":
                self.wave_phase = (self.wave_phase + 1) % len(BRAILLE_WAVE_PATTERNS)
                num_bars = 16
                height_factor = max(1, int((normalized / 100.0) * 8))
                wave_str = "".join([BRAILLE_WAVE_PATTERNS[(self.wave_phase + i * height_factor) % len(BRAILLE_WAVE_PATTERNS)] for i in range(num_bars)])
                self.lbl_vu_header.setText(f"[ {wave_str} ]")
                self.lbl_vu_header.setStyleSheet("font-size: 11px; color: #F6D860; font-weight: 700;")
            else:
                self.lbl_vu_header.setText(f"{sys_dbfs:.1f} dBFS ({int(normalized)}%)")
                self.lbl_vu_header.setStyleSheet("font-size: 11px; color: #F0F2F7; font-weight: 700;")
        except Exception:
            pass

    def _handle_launch(self):
        self.save_config()
        if self.on_launch_callback:
            self.on_launch_callback()
        self.hide()
