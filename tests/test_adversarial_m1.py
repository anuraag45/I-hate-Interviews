import sys
import os
import pytest
from PyQt6.QtWidgets import QApplication

# Ensure CWD and sys.path is repo root
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(repo_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

app = QApplication.instance() or QApplication(sys.argv)

from gui.stealth_hud import compile_hud_stylesheet, StealthHUD, HUDUpdateSignaler
from gui.setup_center import SetupCenter

def test_theme_keys_normalization():
    test_cases = [
        ("calm_buttercup", "Calm Buttercup"),
        ("Calm Buttercup", "Calm Buttercup"),
        ("CALM_BUTTERCUP", "Calm Buttercup"),
        ("gentle_sage", "Gentle Sage"),
        ("Gentle Sage", "Gentle Sage"),
        ("gentle-sage", "Gentle Sage"),
        ("muted_slate", "Muted Slate"),
        ("Muted Slate", "Muted Slate"),
        ("oled_pure_black", "OLED Pure Black"),
        ("OLED Pure Black", "OLED Pure Black"),
        ("OLED-Pure-Black", "OLED Pure Black"),
        ("", "Calm Buttercup"),
        (None, "Calm Buttercup"),
        ("invalid_theme_name_xyz", "Calm Buttercup"),
    ]
    for key, expected_name in test_cases:
        res = compile_hud_stylesheet(theme_key=key)
        assert res["palette"]["name"] == expected_name, f"Failed for key: {key}"

def test_extreme_numerical_boundaries():
    # Negative/zero values
    res_min = compile_hud_stylesheet("calm_buttercup", border_radius=-50, font_size=-10, opacity=-2.0)
    assert res_min["border_radius"] == 4
    assert res_min["font_size"] == 9
    assert res_min["opacity"] == 0.10
    assert res_min["card_alpha"] == 0.35
    assert res_min["input_alpha"] == 0.45

    # Gigantic values
    res_max = compile_hud_stylesheet("oled_pure_black", border_radius=1000, font_size=500, opacity=10.0)
    assert res_max["border_radius"] == 24
    assert res_max["font_size"] == 20
    assert res_max["opacity"] == 1.0
    assert res_max["card_alpha"] == 0.92
    assert res_max["input_alpha"] == 0.95

def test_apply_live_settings_robustness():
    hud = StealthHUD({})

    # 1. Empty dict
    hud.apply_live_settings({})
    assert hud.width() == 370
    assert hud.height() == 640
    assert hud.current_font_size == 13

    # 2. Extreme geometry
    hud.apply_live_settings({"ui_settings": {"width": 10, "height": 5000}})
    assert hud.width() == 280
    assert hud.height() == 1080

    # 3. Missing / None AI settings
    hud.apply_live_settings({"ai_settings": {"custom_model": None, "gemini_model": None}})
    assert "GEMINI-3.7-FLASH" in hud.lbl_model_badge.text()

    # 4. Partial settings
    hud.apply_live_settings({"ui_settings": {"theme": "gentle_sage"}})
    assert hud.lbl_status.text() == "🟢 Ready"

    # 5. Font size changes and placeholder check
    hud.apply_live_settings({"ui_settings": {"font_size": 18}})
    assert hud.current_font_size == 18
    # Default placeholder should still be italic
    assert "italic" in hud.txt_s1.styleSheet()

    # Set real text and check font size re-application
    hud.txt_s1.setText("Real generated content for stage 1")
    hud.apply_live_settings({"ui_settings": {"font_size": 16}})
    assert "normal" in hud.txt_s1.styleSheet()

def test_all_child_widgets_styled_in_all_palettes():
    hud = StealthHUD({})
    themes = ["calm_buttercup", "gentle_sage", "muted_slate", "oled_pure_black"]

    for th in themes:
        hud.apply_live_settings({
            "ui_settings": {
                "theme": th,
                "border_radius": 14,
                "font_size": 13,
                "opacity": 0.95
            },
            "ai_settings": {
                "gemini_model": "gemini-3.7-pro"
            }
        })
        styles = compile_hud_stylesheet(th, border_radius=14, font_size=13, opacity=0.95)
        pal = styles["palette"]

        # Container
        assert hud.card_container.styleSheet() == styles["modern_frame"]
        # Cards
        assert hud.card_s1.styleSheet() == styles["card_s1"]
        assert hud.card_s2.styleSheet() == styles["card_s2"]
        assert hud.card_s3.styleSheet() == styles["card_s3"]
        # Transcript & Query
        assert hud.lbl_transcript.styleSheet() == styles["transcript_box"]
        assert hud.txt_query.styleSheet() == styles["query_input"]
        # Buttons
        assert hud.btn_act_smart.styleSheet() == styles["smart_btn"]
        assert hud.btn_send.styleSheet() == styles["send_btn"]
        assert hud.btn_act_s1.styleSheet() == styles["btn_act_s1"]
        assert hud.btn_act_s2.styleSheet() == styles["btn_act_s2"]
        assert hud.btn_act_s3.styleSheet() == styles["btn_act_s3"]
        assert hud.btn_act_snip.styleSheet() == styles["btn_act_snip"]
        assert hud.btn_font_dec.styleSheet() == styles["btn_header"]
        assert hud.btn_font_inc.styleSheet() == styles["btn_header"]
        assert hud.btn_hide.styleSheet() == styles["btn_hide"]
        assert hud.btn_clear.styleSheet() == styles["btn_clear"]
        assert hud.vu_box.styleSheet() == styles["vu_box"]
        assert hud.lbl_model_badge.styleSheet() == styles["model_badge"]
        assert "GEMINI-3.7-PRO" in hud.lbl_model_badge.text()

if __name__ == "__main__":
    test_theme_keys_normalization()
    test_extreme_numerical_boundaries()
    test_apply_live_settings_robustness()
    test_all_child_widgets_styled_in_all_palettes()
    print("ALL ADVERSARIAL STRESS TESTS PASSED!")
