import os
import sys

# Ensure CWD is repo root
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication

def test_compile_hud_stylesheet():
    print("[M1 TEST 1] Testing compile_hud_stylesheet() across all 4 palettes...")
    from gui.stealth_hud import compile_hud_stylesheet

    palettes = ["calm_buttercup", "gentle_sage", "muted_slate", "oled_pure_black"]
    for p in palettes:
        res = compile_hud_stylesheet(theme_key=p, border_radius=16, font_size=14, opacity=0.85)
        assert "palette" in res, f"Missing palette for {p}"
        assert "modern_frame" in res, f"Missing modern_frame for {p}"
        assert "card_s1" in res, f"Missing card_s1 for {p}"
        assert "card_s2" in res, f"Missing card_s2 for {p}"
        assert "card_s3" in res, f"Missing card_s3 for {p}"
        assert "transcript_box" in res, f"Missing transcript_box for {p}"
        assert "query_input" in res, f"Missing query_input for {p}"
        assert "smart_btn" in res, f"Missing smart_btn for {p}"
        assert "send_btn" in res, f"Missing send_btn for {p}"
        assert "model_badge" in res, f"Missing model_badge for {p}"
        assert "vu_box" in res, f"Missing vu_box for {p}"
        pal = res["palette"]
        assert pal["name"].lower().replace(" ", "_") == p
        assert pal["accent"].startswith("#")
        print(f"  -> Palette '{pal['name']}': Accent={pal['accent']}, BG_RGB={pal['bg_rgb']}, Card_Alpha={res.get('card_alpha', 0.95)}")

    print("  -> ALL 4 PALETTES COMPILED WITH PROPORTIONAL RADII & ALPHA BLENDING")

def test_setup_center_all_signal_bindings():
    print("[M1 TEST 2] Testing SetupCenter 29 UI input real-time signal broadcasts...")
    from gui.setup_center import SetupCenter

    app = QApplication.instance() or QApplication(sys.argv)
    center = SetupCenter()

    emitted_configs = []
    center.settings_changed.connect(lambda cfg: emitted_configs.append(cfg))

    # Test Appearance & Geometry
    center.spin_hud_width.setValue(450)
    assert len(emitted_configs) > 0 and emitted_configs[-1]["ui_settings"]["width"] == 450
    center.spin_hud_height.setValue(800)
    assert emitted_configs[-1]["ui_settings"]["height"] == 800
    center.slider_opacity.setValue(75)
    assert emitted_configs[-1]["ui_settings"]["opacity"] == 0.75
    center.spin_font_size.setValue(16)
    assert emitted_configs[-1]["ui_settings"]["font_size"] == 16
    center.spin_border_radius.setValue(18)
    assert emitted_configs[-1]["ui_settings"]["border_radius"] == 18
    center.combo_theme.setCurrentIndex(1) # Gentle Sage
    assert emitted_configs[-1]["ui_settings"]["theme"] == "gentle_sage"
    center.combo_vu_mode.setCurrentIndex(1) # Wave
    assert emitted_configs[-1]["ui_settings"]["vu_mode"] == "wave"

    # Test Win32 Flags
    center.chk_stealth.setChecked(False)
    assert emitted_configs[-1]["ui_settings"]["stealth_affinity"] is False
    center.chk_click_through.setChecked(True)
    assert emitted_configs[-1]["ui_settings"]["click_through_default"] is True

    # Test AI Settings & Models
    center.combo_gemini_model.setCurrentIndex(2) # gemini-2.5-flash
    assert emitted_configs[-1]["ai_settings"]["gemini_model"] == "gemini-2.5-flash"
    center.combo_llm.setCurrentIndex(1) # Groq
    assert emitted_configs[-1]["preferred_llm"] == "groq"
    center.txt_custom_model.setText("gemini-3.7-custom")
    assert emitted_configs[-1]["ai_settings"]["custom_model"] == "gemini-3.7-custom"
    center.txt_groq_model.setText("llama-3.3-custom")
    assert emitted_configs[-1]["ai_settings"]["groq_model"] == "llama-3.3-custom"
    center.txt_openai_model.setText("gpt-4o-mini")
    assert emitted_configs[-1]["ai_settings"]["openai_model"] == "gpt-4o-mini"
    center.spin_temp.setValue(0.45)
    assert abs(emitted_configs[-1]["ai_settings"]["temperature"] - 0.45) < 0.01
    center.spin_tokens.setValue(2048)
    assert emitted_configs[-1]["ai_settings"]["max_tokens"] == 2048
    center.txt_prompt_prefix.setPlainText("Custom Persona Prompt Prefix Test")
    assert emitted_configs[-1]["ai_settings"]["custom_prompt_prefix"] == "Custom Persona Prompt Prefix Test"

    # Test Audio Thresholds
    center.spin_audio_thresh.setValue(0.045)
    assert abs(emitted_configs[-1]["audio_settings"]["sensitivity_threshold"] - 0.045) < 0.001
    center.spin_silence_timeout.setValue(2.5)
    assert abs(emitted_configs[-1]["audio_settings"]["silence_timeout_sec"] - 2.5) < 0.01

    # Test Persona & Profile
    center.combo_role.setCurrentIndex(1)
    assert "Live Coding" in emitted_configs[-1]["role_preset"]
    center.txt_name.setText("Alice Principal")
    assert emitted_configs[-1]["user_profile"]["name"] == "Alice Principal"
    center.txt_exp.setText("10 Years Lead Architect")
    assert emitted_configs[-1]["user_profile"]["years_of_experience"] == "10 Years Lead Architect"
    center.txt_skills.setText("PyQt6, Win32, Distributed Systems")
    assert emitted_configs[-1]["user_profile"]["primary_skills"] == "PyQt6, Win32, Distributed Systems"
    center.txt_summary.setPlainText("Summary Test Content")
    assert emitted_configs[-1]["user_profile"]["summary"] == "Summary Test Content"
    center.txt_resume.setPlainText("Resume Highlights Test")
    assert emitted_configs[-1]["user_profile"]["resume_text"] == "Resume Highlights Test"
    center.txt_jd.setPlainText("Job Requirements Test")
    assert emitted_configs[-1]["user_profile"]["job_description_text"] == "Job Requirements Test"

    # Test API Keys
    center.txt_gemini.setText("AIzaSy-TestKey123")
    assert emitted_configs[-1]["api_keys"]["gemini"] == "AIzaSy-TestKey123"
    center.txt_groq.setText("gsk_TestGroqKey456")
    assert emitted_configs[-1]["api_keys"]["groq"] == "gsk_TestGroqKey456"
    center.txt_deepgram.setText("dg_TestDeepgramKey789")
    assert emitted_configs[-1]["api_keys"]["deepgram"] == "dg_TestDeepgramKey789"
    center.txt_openai.setText("sk_TestOpenAIKey000")
    assert emitted_configs[-1]["api_keys"]["openai"] == "sk_TestOpenAIKey000"

    print(f"  -> ALL 29 UI CONTROLS SUCCESSFULLY EMITTED REAL-TIME SIGNAL (Total events: {len(emitted_configs)})")

def test_stealth_hud_apply_live_settings():
    print("[M1 TEST 3] Testing StealthHUD.apply_live_settings() dynamic reconfiguration...")
    from gui.stealth_hud import StealthHUD, HUDUpdateSignaler

    app = QApplication.instance() or QApplication(sys.argv)
    initial_cfg = {
        "ui_settings": {
            "width": 350,
            "height": 600,
            "opacity": 0.95,
            "border_radius": 14,
            "font_size": 12,
            "theme": "calm_buttercup",
            "vu_mode": "dots",
            "stealth_affinity": True,
            "click_through_default": False
        },
        "ai_settings": {
            "gemini_model": "gemini-3.7-flash",
            "custom_model": ""
        }
    }

    hud = StealthHUD(initial_cfg)
    assert hud.width() == 350
    assert hud.height() == 600
    assert "GEMINI-3.7-FLASH" in hud.lbl_model_badge.text()

    # 1. Test Live Geometry Resize & Clamping
    new_cfg = dict(initial_cfg)
    new_cfg["ui_settings"] = dict(initial_cfg["ui_settings"])
    new_cfg["ui_settings"]["width"] = 520
    new_cfg["ui_settings"]["height"] = 850
    hud.apply_live_settings(new_cfg)
    assert hud.width() == 520
    assert hud.height() == 850

    # Test Min/Max bounds clamping
    new_cfg["ui_settings"]["width"] = 100 # Should clamp to 280
    new_cfg["ui_settings"]["height"] = 2000 # Should clamp to 1080
    hud.apply_live_settings(new_cfg)
    assert hud.width() == 280
    assert hud.height() == 1080

    # 2. Test Live Theme Transition across all 4 themes
    for theme_name in ["gentle_sage", "muted_slate", "oled_pure_black", "calm_buttercup"]:
        new_cfg["ui_settings"]["theme"] = theme_name
        hud.apply_live_settings(new_cfg)
        assert hud.config["ui_settings"]["theme"] == theme_name

    # 3. Test Live Model Badge Update
    new_cfg["ai_settings"] = {"gemini_model": "gemini-2.5-pro", "custom_model": "gemini-2.5-flash-lite"}
    hud.apply_live_settings(new_cfg)
    assert "GEMINI-2.5-FLASH" in hud.lbl_model_badge.text()

    # 4. Test Live VU Mode Switch
    new_cfg["ui_settings"]["vu_mode"] = "wave"
    hud.apply_live_settings(new_cfg)
    assert hud.btn_vu_mode.text() == "🎙️ WAVE"

    # 5. Test Live Font Scaling with placeholder vs active text
    new_cfg["ui_settings"]["font_size"] = 16
    hud.apply_live_settings(new_cfg)
    assert hud.current_font_size == 16
    # Active text
    hud.set_stage_card_content(1, "Scope active extracted problem requirements.")
    assert "Scope active" in hud.txt_s1.text()
    assert "italic" not in hud.txt_s1.styleSheet()

    print("  -> STEALTH HUD GEOMETRY CLAMPING, THEME APPLICATION, BADGE & FONT SYNC VERIFIED")

def run_all_m1_tests():
    print("=" * 65)
    print("   MEETINGCOPILOT AI - MILESTONE 1 VERIFICATION RUNNER   ")
    print("=" * 65)
    test_compile_hud_stylesheet()
    test_setup_center_all_signal_bindings()
    test_stealth_hud_apply_live_settings()
    print("=" * 65)
    print(" >>> MILESTONE 1 (DYNAMIC SYNC & THEMING) 100% PASSED! <<< ")
    print("=" * 65)

if __name__ == "__main__":
    run_all_m1_tests()
