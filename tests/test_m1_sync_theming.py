import os
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ensure CWD and sys.path is repo root
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(repo_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Ensure QApplication exists for testing GUI widgets
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from gui.stealth_hud import compile_hud_stylesheet, StealthHUD, HUDUpdateSignaler
from gui.setup_center import SetupCenter

def test_compile_hud_stylesheet_all_palettes():
    """Verify that compile_hud_stylesheet produces correct styles for all 4 themes."""
    themes = ["calm_buttercup", "gentle_sage", "muted_slate", "oled_pure_black"]
    
    for th in themes:
        res = compile_hud_stylesheet(theme_key=th, border_radius=14, font_size=13, opacity=0.95)
        assert "palette" in res
        assert "modern_frame" in res
        assert "card_s1" in res
        assert "card_s2" in res
        assert "card_s3" in res
        assert "transcript_box" in res
        assert "query_input" in res
        assert "smart_btn" in res
        assert "send_btn" in res
        assert "vu_box" in res
        assert "model_badge" in res
        
        pal = res["palette"]
        assert "accent" in pal
        assert "accent_hover" in pal
        assert "accent_pressed" in pal
        assert "bg_rgb" in pal
        assert "card_rgb" in pal
        assert "input_rgb" in pal
        assert "s1_color" in pal
        assert "s2_color" in pal
        assert "s3_color" in pal
        assert "text_primary" in pal
        assert "text_muted" in pal

        # Check theme-specific properties
        if th == "calm_buttercup":
            assert pal["accent"] == "#F6D860"
        elif th == "gentle_sage":
            assert pal["accent"] == "#38A169"
            assert pal["text_primary"] == "#E6FFFA"
        elif th == "muted_slate":
            assert pal["accent"] == "#63B3ED"
        elif th == "oled_pure_black":
            assert pal["bg_rgb"] == "0, 0, 0"

def test_compile_hud_stylesheet_clamping_and_scaling():
    """Verify that compile_hud_stylesheet clamps border_radius, font_size, and opacity."""
    # Test boundary below minimums
    res_low = compile_hud_stylesheet(theme_key="calm_buttercup", border_radius=1, font_size=4, opacity=0.01)
    assert res_low["border_radius"] == 4
    assert res_low["font_size"] == 9
    assert res_low["opacity"] == 0.10

    # Test boundary above maximums
    res_high = compile_hud_stylesheet(theme_key="calm_buttercup", border_radius=50, font_size=40, opacity=2.5)
    assert res_high["border_radius"] == 24
    assert res_high["font_size"] == 20
    assert res_high["opacity"] == 1.0

def test_setup_center_all_inputs_emit_live_change():
    """Verify that all 25+ UI controls in SetupCenter trigger settings_changed signal."""
    sc = SetupCenter()
    emitted_configs = []
    sc.settings_changed.connect(lambda cfg: emitted_configs.append(cfg))

    # 1. Appearance & Geometry
    sc.spin_hud_width.setValue(420)
    assert len(emitted_configs) >= 1
    assert emitted_configs[-1]["ui_settings"]["width"] == 420

    sc.spin_hud_height.setValue(700)
    assert emitted_configs[-1]["ui_settings"]["height"] == 700

    sc.slider_opacity.setValue(85)
    assert abs(emitted_configs[-1]["ui_settings"]["opacity"] - 0.85) < 0.01

    sc.spin_font_size.setValue(15)
    assert emitted_configs[-1]["ui_settings"]["font_size"] == 15

    sc.spin_border_radius.setValue(18)
    assert emitted_configs[-1]["ui_settings"]["border_radius"] == 18

    sc.combo_theme.setCurrentIndex(1) # Gentle Sage
    assert emitted_configs[-1]["ui_settings"]["theme"] == "gentle_sage"

    sc.combo_vu_mode.setCurrentIndex(1) # Wave
    assert emitted_configs[-1]["ui_settings"]["vu_mode"] == "wave"

    # 2. Win32 Flags
    sc.chk_stealth.setChecked(False)
    assert emitted_configs[-1]["ui_settings"]["stealth_affinity"] is False

    sc.chk_click_through.setChecked(True)
    assert emitted_configs[-1]["ui_settings"]["click_through_default"] is True

    # 3. AI Models & Tuning
    sc.combo_gemini_model.setCurrentIndex(2) # gemini-2.5-flash
    assert emitted_configs[-1]["ai_settings"]["gemini_model"] == "gemini-2.5-flash"

    sc.combo_llm.setCurrentIndex(1) # Groq
    assert emitted_configs[-1]["preferred_llm"] == "groq"

    sc.txt_custom_model.setText("gemini-3.7-custom-preview")
    assert emitted_configs[-1]["ai_settings"]["custom_model"] == "gemini-3.7-custom-preview"

    sc.txt_groq_model.setText("llama-3.3-70b-spec")
    assert emitted_configs[-1]["ai_settings"]["groq_model"] == "llama-3.3-70b-spec"

    sc.txt_openai_model.setText("gpt-4o-mini")
    assert emitted_configs[-1]["ai_settings"]["openai_model"] == "gpt-4o-mini"

    sc.spin_temp.setValue(0.45)
    assert abs(emitted_configs[-1]["ai_settings"]["temperature"] - 0.45) < 0.01

    sc.spin_tokens.setValue(2048)
    assert emitted_configs[-1]["ai_settings"]["max_tokens"] == 2048

    sc.txt_prompt_prefix.setPlainText("Focus on high-throughput microservices.")
    assert emitted_configs[-1]["ai_settings"]["custom_prompt_prefix"] == "Focus on high-throughput microservices."

    # 4. Audio Thresholds
    sc.spin_audio_thresh.setValue(0.045)
    assert abs(emitted_configs[-1]["audio_settings"]["sensitivity_threshold"] - 0.045) < 0.001

    sc.spin_silence_timeout.setValue(2.2)
    assert abs(emitted_configs[-1]["audio_settings"]["silence_timeout_sec"] - 2.2) < 0.01

    # 5. Persona & Profile
    sc.combo_role.setCurrentIndex(1) # Live Coding & Algorithm Walkthrough
    assert emitted_configs[-1]["role_preset"] == "Live Coding & Algorithm Walkthrough"

    sc.txt_name.setText("Lead Architect")
    assert emitted_configs[-1]["user_profile"]["name"] == "Lead Architect"

    sc.txt_exp.setText("Principal Staff Engineer")
    assert emitted_configs[-1]["user_profile"]["years_of_experience"] == "Principal Staff Engineer"

    sc.txt_skills.setText("Distributed Systems, Kubernetes, Kafka")
    assert emitted_configs[-1]["user_profile"]["primary_skills"] == "Distributed Systems, Kubernetes, Kafka"

    sc.txt_summary.setPlainText("Leading platform scale initiatives.")
    assert emitted_configs[-1]["user_profile"]["summary"] == "Leading platform scale initiatives."

    sc.txt_resume.setPlainText("15+ years building distributed consensus engines.")
    assert emitted_configs[-1]["user_profile"]["resume_text"] == "15+ years building distributed consensus engines."

    sc.txt_jd.setPlainText("Technical discussion on event streaming architectures.")
    assert emitted_configs[-1]["user_profile"]["job_description_text"] == "Technical discussion on event streaming architectures."

    # 6. API Keys
    sc.txt_gemini.setText("test-gemini-key-12345")
    assert emitted_configs[-1]["api_keys"]["gemini"] == "test-gemini-key-12345"

    sc.txt_groq.setText("test-groq-key-67890")
    assert emitted_configs[-1]["api_keys"]["groq"] == "test-groq-key-67890"

    sc.txt_deepgram.setText("test-deepgram-key-abcde")
    assert emitted_configs[-1]["api_keys"]["deepgram"] == "test-deepgram-key-abcde"

    sc.txt_openai.setText("test-openai-key-fghij")
    assert emitted_configs[-1]["api_keys"]["openai"] == "test-openai-key-fghij"

    print("  -> ALL 28 UI INPUT CONNECTIONS EMIT REAL-TIME SETTINGS ACCURATELY")

def test_stealth_hud_apply_live_settings():
    """Verify that StealthHUD.apply_live_settings correctly updates geometry, theme, opacity, and badge."""
    cfg = {
        "ui_settings": {
            "theme": "gentle_sage",
            "opacity": 0.88,
            "font_size": 14,
            "border_radius": 16,
            "width": 400,
            "height": 680,
            "stealth_affinity": True,
            "click_through_default": False,
            "vu_mode": "dots"
        },
        "ai_settings": {
            "gemini_model": "gemini-3.7-flash",
            "custom_model": ""
        }
    }

    hud = StealthHUD(cfg)
    assert hud.width() == 400
    assert hud.height() == 680
    assert hud.current_font_size == 14
    assert "GEMINI-3.7-FLASH" in hud.lbl_model_badge.text()

    # Apply new live settings with OLED Black theme and custom model
    new_cfg = {
        "ui_settings": {
            "theme": "oled_pure_black",
            "opacity": 0.70,
            "font_size": 16,
            "border_radius": 20,
            "width": 500,
            "height": 800,
            "stealth_affinity": False,
            "click_through_default": True,
            "vu_mode": "wave"
        },
        "ai_settings": {
            "gemini_model": "gemini-2.5-pro",
            "custom_model": "gemini-2.5-pro-preview"
        }
    }
    hud.apply_live_settings(new_cfg)

    assert hud.width() == 500
    assert hud.height() == 800
    assert hud.current_font_size == 16
    assert abs(hud.windowOpacity() - 0.70) < 0.01
    assert "GEMINI-2.5-PRO-PRE" in hud.lbl_model_badge.text()
    assert hud.vu_mode == "wave"
    assert hud.is_click_through is True
    assert hud.stealth_enabled is False

    # Test geometry clamping
    clamped_cfg = {
        "ui_settings": {
            "theme": "calm_buttercup",
            "opacity": 0.96,
            "font_size": 12,
            "border_radius": 14,
            "width": 100, # Below min 280
            "height": 2000, # Above max 1080
            "stealth_affinity": True,
            "click_through_default": False,
            "vu_mode": "dots"
        },
        "ai_settings": {
            "gemini_model": "gemini-3.6-flash"
        }
    }
    hud.apply_live_settings(clamped_cfg)
    assert hud.width() == 280
    assert hud.height() == 1080

    print("  -> STEALTH HUD DYNAMIC LIVE SETTINGS APPLICATION VERIFIED")

def test_end_to_end_dashboard_to_hud_sync():
    """Verify that changing values in SetupCenter instantly reflects in StealthHUD via signal connection."""
    sc = SetupCenter()
    hud = StealthHUD(sc.get_current_settings_dict())

    # Wire signal as done in run.py
    sc.settings_changed.connect(hud.apply_live_settings)

    # Change theme in setup center
    sc.combo_theme.setCurrentIndex(2) # Muted Slate
    assert "muted_slate" in hud.config["ui_settings"]["theme"]

    # Change dimensions
    sc.spin_hud_width.setValue(450)
    assert hud.width() == 450

    sc.spin_hud_height.setValue(720)
    assert hud.height() == 720

    # Change font size
    sc.spin_font_size.setValue(15)
    assert hud.current_font_size == 15

    # Change model
    sc.txt_custom_model.setText("gemini-3.7-flash-hybrid")
    assert "GEMINI-3.7-FLASH-H" in hud.lbl_model_badge.text()

    print("  -> END-TO-END DASHBOARD TO HUD INSTANT DYNAMIC SYNC VERIFIED")

if __name__ == "__main__":
    print("Running Milestone 1 Verification Tests...")
    test_compile_hud_stylesheet_all_palettes()
    test_compile_hud_stylesheet_clamping_and_scaling()
    test_setup_center_all_inputs_emit_live_change()
    test_stealth_hud_apply_live_settings()
    test_end_to_end_dashboard_to_hud_sync()
    print(">>> ALL MILESTONE 1 TESTS PASSED PERFECTLY! <<<")
