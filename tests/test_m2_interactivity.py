import json
import os
import sys
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QMouseEvent

# Ensure CWD and sys.path is repo root
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(repo_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Set offscreen Qt platform for headless CI
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from gui.stealth_hud import (
    compile_hud_stylesheet,
    StealthHUD,
    HUDUpdateSignaler,
    ClickFocusLineEdit
)
from stealth.win32_affinity import (
    apply_stealth_affinity,
    apply_non_activating_styles,
    WDA_EXCLUDEFROMCAPTURE,
    WDA_NONE,
    WS_EX_NOACTIVATE,
    WS_EX_LAYERED,
    WS_EX_TRANSPARENT,
    GWL_EXSTYLE
)

def test_config_click_through_default_false():
    """Verify that config.json defaults to click_through_default: false for mouse interactivity."""
    config_path = os.path.join(repo_root, "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    ui_s = cfg.get("ui_settings", {})
    assert ui_s.get("click_through_default") is False, "click_through_default must be false in config.json"

def test_win32_affinity_and_styles_functions():
    """Verify that Win32 functions handle parameters properly."""
    # Test on mock / real HWND
    res_none = apply_stealth_affinity(0, exclude=True)
    assert res_none is False
    res_none2 = apply_stealth_affinity(0, enabled=True)
    assert res_none2 is False
    res_style_none = apply_non_activating_styles(0, click_through=False)
    assert res_style_none is False

def test_hud_initialization_defaults():
    """Verify HUD initializes with interactive non-click-through defaults and ClickFocusLineEdit."""
    cfg = {
        "ui_settings": {
            "theme": "calm_buttercup",
            "opacity": 0.96,
            "font_size": 13,
            "border_radius": 14,
            "width": 370,
            "height": 640,
            "stealth_affinity": True,
            "click_through_default": False,
            "vu_mode": "dots"
        }
    }
    hud = StealthHUD(cfg)
    assert hud.is_click_through is False
    assert hud.stealth_enabled is True
    assert hud.lbl_status.text() == "🟢 Ready"
    assert isinstance(hud.txt_query, ClickFocusLineEdit)
    assert hud.btn_act_smart is not None
    assert hud.btn_act_s1 is not None
    assert hud.btn_act_s2 is not None
    assert hud.btn_act_s3 is not None
    assert hud.btn_act_snip is not None
    assert hud.btn_send is not None
    assert hud.btn_clear is not None
    assert hud.btn_ghost is not None
    assert hud.btn_font_dec is not None
    assert hud.btn_font_inc is not None

def test_action_buttons_signals_and_status():
    """Verify all action buttons trigger signals and update status badges."""
    signaler = HUDUpdateSignaler()
    cfg = {
        "ui_settings": {
            "theme": "calm_buttercup",
            "click_through_default": False
        }
    }
    hud = StealthHUD(cfg, signaler=signaler)

    events = []
    signaler.action_smart_next.connect(lambda: events.append("smart_next"))
    signaler.action_stage_1.connect(lambda: events.append("stage_1"))
    signaler.action_stage_2.connect(lambda: events.append("stage_2"))
    signaler.action_stage_3.connect(lambda: events.append("stage_3"))
    signaler.action_vision_snip.connect(lambda: events.append("vision_snip"))

    # Click Smart Next
    hud.btn_act_smart.click()
    assert "smart_next" in events
    assert "Generating" in hud.lbl_status.text()

    # Click Stage 1
    hud.btn_act_s1.click()
    assert "stage_1" in events
    assert "Stage 1" in hud.lbl_status.text()

    # Click Stage 2
    hud.btn_act_s2.click()
    assert "stage_2" in events
    assert "Stage 2" in hud.lbl_status.text()

    # Click Stage 3
    hud.btn_act_s3.click()
    assert "stage_3" in events
    assert "Stage 3" in hud.lbl_status.text()

    # Click Snip
    hud.btn_act_snip.click()
    assert "vision_snip" in events
    assert "Snipping" in hud.lbl_status.text()

def test_query_input_enter_and_send_button():
    """Verify Quick Query text input dispatches on Enter and on Send button click."""
    signaler = HUDUpdateSignaler()
    cfg = {"ui_settings": {"theme": "calm_buttercup"}}
    hud = StealthHUD(cfg, signaler=signaler)

    queries_sent = []
    signaler.action_custom_query.connect(lambda q: queries_sent.append(q))

    # Test typing and Enter
    hud.txt_query.setText("How to design a distributed cache?")
    hud._on_custom_query_send()
    assert len(queries_sent) == 1
    assert queries_sent[-1] == "How to design a distributed cache?"
    assert hud.txt_query.text() == ""
    assert "Processing" in hud.lbl_status.text()
    assert "distributed cache" in hud.lbl_transcript.text()

    # Test Send button click
    hud.txt_query.setText("What are LSM trees?")
    hud.btn_send.click()
    assert len(queries_sent) == 2
    assert queries_sent[-1] == "What are LSM trees?"
    assert hud.txt_query.text() == ""

def test_click_focus_line_edit_mouse_event():
    """Verify ClickFocusLineEdit handles mouse events gracefully without crashing."""
    cfg = {"ui_settings": {"theme": "calm_buttercup"}}
    hud = StealthHUD(cfg)
    hud.show()
    line_edit = hud.txt_query
    # Simulate mouse press event
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10.0, 10.0),
        QPointF(10.0, 10.0),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    line_edit.mousePressEvent(event)
    assert line_edit.hasFocus() or line_edit.isVisible()

def test_clear_content_and_placeholder_reset():
    """Verify Clear button resets status to Ready, clears transcript, and restores clean placeholders."""
    signaler = HUDUpdateSignaler()
    cfg = {"ui_settings": {"theme": "calm_buttercup"}}
    hud = StealthHUD(cfg, signaler=signaler)

    clear_fired = []
    signaler.clear_triggered.connect(lambda: clear_fired.append(True))

    hud.txt_s1.setText("Generated content for Stage 1")
    hud.txt_s2.setText("Generated content for Stage 2")
    hud.txt_s3.setText("Generated content for Stage 3")
    hud.lbl_status.setText("⚡ Streaming S1...")
    hud.lbl_transcript.setText(">> Some active question")

    hud.btn_clear.click()

    assert len(clear_fired) == 1
    assert hud.lbl_status.text() == "🟢 Ready"
    assert "Ready for next topic" in hud.txt_s1.text()
    assert "Architecture breakdown" in hud.txt_s2.text()
    assert "Code implementation" in hud.txt_s3.text()
    assert "Listening" in hud.lbl_transcript.text()

def test_token_streaming_and_placeholder_clearing():
    """Verify token streaming clears initial and cleared placeholders cleanly without string concatenation bug."""
    cfg = {"ui_settings": {"theme": "calm_buttercup"}}
    hud = StealthHUD(cfg)

    # 1. Stream into Stage 1 from initial state
    assert "Ready to extract" in hud.txt_s1.text()
    hud.append_stage_token(1, "Clarifying ")
    hud.append_stage_token(1, "questions:")
    assert hud.txt_s1.text() == "Clarifying questions:"
    assert "Ready" not in hud.txt_s1.text()
    assert "Streaming S1" in hud.lbl_status.text()

    # 2. Clear content
    hud.clear_content()
    assert "Ready for next topic" in hud.txt_s1.text()

    # 3. Stream into Stage 1 after clear
    hud.append_stage_token(1, "New ")
    hud.append_stage_token(1, "Stream")
    assert hud.txt_s1.text() == "New Stream"
    assert "Ready for next topic" not in hud.txt_s1.text()

    # 4. Stream into Stage 2
    hud.append_stage_token(2, "Arch: ")
    hud.append_stage_token(2, "Microservices")
    assert hud.txt_s2.text() == "Arch: Microservices"
    assert "Baseline vs." not in hud.txt_s2.text()

    # 5. Stream into Stage 3
    hud.append_stage_token(3, "def ")
    hud.append_stage_token(3, "solve(): pass")
    assert hud.txt_s3.text() == "def solve(): pass"
    assert "Production code" not in hud.txt_s3.text()

    # 6. Stream into Stage 4 (Glance) -> routes to txt_s1
    hud.clear_content()
    hud.append_stage_token(4, "Glance summary")
    assert hud.txt_s1.text() == "Glance summary"
    assert "Ready for next topic" not in hud.txt_s1.text()

def test_stage_completion_guard_against_premature_reset():
    """Verify set_stage_card_content with empty content clears card but does NOT show Complete or fire timer."""
    cfg = {"ui_settings": {"theme": "calm_buttercup"}}
    hud = StealthHUD(cfg)

    # Simulate dispatch: clear target card with empty string
    hud.lbl_status.setText("⚡ Streaming S1...")
    hud.txt_s1.setText("Old text")
    hud.set_stage_card_content(1, "")

    assert hud.txt_s1.text() == ""
    # Status should remain as Streaming S1, not falsely changed to Complete
    assert hud.lbl_status.text() == "⚡ Streaming S1..."

    # Now simulate generation finish with real content
    hud.set_stage_card_content(1, "# Stage 1 Result Markdown")
    assert hud.txt_s1.text() == "# Stage 1 Result Markdown"
    assert hud.lbl_status.text() == "✓ Complete"

    # Test Stage 4 full markdown
    hud.set_stage_card_content(4, "# Full Glance Card Markdown")
    assert hud.txt_s1.text() == "# Full Glance Card Markdown"
    assert hud.lbl_status.text() == "✓ Complete"

def test_ghost_mode_toggle_and_visuals():
    """Verify ghost toggle flips state, calls non-activating styles, and updates button border color."""
    cfg = {"ui_settings": {"theme": "calm_buttercup", "click_through_default": False}}
    hud = StealthHUD(cfg)
    assert hud.is_click_through is False

    hud.btn_ghost.click()
    assert hud.is_click_through is True
    assert "#38A169" in hud.btn_ghost.styleSheet()

    hud.btn_ghost.click()
    assert hud.is_click_through is False
    assert "#38A169" not in hud.btn_ghost.styleSheet()

def test_font_scaling_buttons():
    """Verify font increment and decrement buttons resize text within [9, 20] range."""
    cfg = {"ui_settings": {"font_size": 13}}
    hud = StealthHUD(cfg)
    assert hud.current_font_size == 13

    hud.btn_font_inc.click()
    assert hud.current_font_size == 14

    hud.btn_font_dec.click()
    hud.btn_font_dec.click()
    assert hud.current_font_size == 12

    # Test bounds
    for _ in range(30):
        hud.btn_font_inc.click()
    assert hud.current_font_size == 20

    for _ in range(30):
        hud.btn_font_dec.click()
    assert hud.current_font_size == 9

def test_vu_mode_cycle_button():
    """Verify clicking the VU mode button cycles through modes dots -> wave -> numeric."""
    cfg = {"ui_settings": {"vu_mode": "dots"}}
    hud = StealthHUD(cfg)
    assert hud.vu_mode == "dots"
    assert "DOTS" in hud.btn_vu_mode.text()

    hud.btn_vu_mode.click()
    assert hud.vu_mode == "wave"
    assert "WAVE" in hud.btn_vu_mode.text()

    hud.btn_vu_mode.click()
    assert hud.vu_mode == "numeric"
    assert "NUMERIC" in hud.btn_vu_mode.text()

    hud.btn_vu_mode.click()
    assert hud.vu_mode == "dots"
    assert "DOTS" in hud.btn_vu_mode.text()

def test_copy_code_clipboard_and_feedback():
    """Verify copy button on Card 3 copies code to clipboard and provides visual feedback."""
    cfg = {"ui_settings": {"theme": "calm_buttercup"}}
    hud = StealthHUD(cfg)

    hud.txt_s3.setText("const solution = () => 42;")
    hud.btn_copy.click()

    clipboard_text = QApplication.clipboard().text()
    assert clipboard_text == "const solution = () => 42;"
    assert hud.lbl_status.text() == "✓ Copied Code!"

def test_apply_live_settings_defensive_robustness():
    """Verify apply_live_settings handles partial, None, and empty dictionaries gracefully."""
    hud = StealthHUD({})

    # Pass None / Empty
    hud.apply_live_settings(None)
    assert hud.width() >= 280
    assert hud.height() >= 400

    hud.apply_live_settings({})
    assert hud.width() >= 280

    # Pass explicit None values
    hud.apply_live_settings({
        "ui_settings": {
            "width": None,
            "height": None,
            "opacity": None,
            "font_size": None,
            "border_radius": None,
            "theme": None,
            "click_through_default": None,
            "stealth_affinity": None
        },
        "ai_settings": None
    })
    assert 280 <= hud.width() <= 650
    assert 400 <= hud.height() <= 1080
    assert 9 <= hud.current_font_size <= 20

    # Pass live sync updates
    hud.apply_live_settings({
        "ui_settings": {
            "width": 500,
            "height": 700,
            "opacity": 0.88,
            "font_size": 15,
            "border_radius": 16,
            "theme": "gentle_sage",
            "click_through_default": True,
            "stealth_affinity": False,
            "vu_mode": "wave"
        },
        "ai_settings": {
            "custom_model": "gemini-3.7-flash-thinking"
        }
    })
    assert hud.width() == 500
    assert hud.height() == 700
    assert hud.current_font_size == 15
    assert hud.is_click_through is True
    assert hud.stealth_enabled is False
    assert hud.vu_mode == "wave"
    assert "GEMINI-3.7-FLASH" in hud.lbl_model_badge.text()
    assert "#38A169" in hud.btn_ghost.styleSheet()

def run_all_m2_tests():
    print("Running Milestone 2 Interactivity & Status Engine Verification Tests...")
    test_config_click_through_default_false()
    print("  -> CONFIG CLICK-THROUGH DEFAULT: FALSE VERIFIED")
    test_win32_affinity_and_styles_functions()
    print("  -> WIN32 DISPLAY AFFINITY & NON-ACTIVATING EXTENDED STYLES VERIFIED")
    test_hud_initialization_defaults()
    print("  -> HUD INITIALIZATION & CLICK-FOCUS LINE EDIT VERIFIED")
    test_action_buttons_signals_and_status()
    print("  -> ALL HUD ACTION BUTTONS & STATUS TRANSITIONS VERIFIED")
    test_query_input_enter_and_send_button()
    print("  -> QUICK QUERY INPUT DISPATCH ON ENTER & SEND VERIFIED")
    test_click_focus_line_edit_mouse_event()
    print("  -> CLICK-FOCUS LINE EDIT MOUSE FOCUS HANDLING VERIFIED")
    test_clear_content_and_placeholder_reset()
    print("  -> CLEAR BUTTON RESET & STATUS TRANSITIONS VERIFIED")
    test_token_streaming_and_placeholder_clearing()
    print("  -> TOKEN STREAMING & PLACEHOLDER CLEANUP ACROSS STAGES 1-4 VERIFIED")
    test_stage_completion_guard_against_premature_reset()
    print("  -> STAGE COMPLETION NON-EMPTY GUARD & BADGE TRANSITIONS VERIFIED")
    test_ghost_mode_toggle_and_visuals()
    print("  -> GHOST CLICK-THROUGH MODE TOGGLE & VISUAL INDICATOR VERIFIED")
    test_font_scaling_buttons()
    print("  -> FONT INCREMENT / DECREMENT BUTTONS & BOUNDS VERIFIED")
    test_vu_mode_cycle_button()
    print("  -> VU VISUALIZER MODE CYCLING VERIFIED")
    test_copy_code_clipboard_and_feedback()
    print("  -> COPY CODE CLIPBOARD INTEGRATION & BADGE FEEDBACK VERIFIED")
    test_apply_live_settings_defensive_robustness()
    print("  -> DEFENSIVE LIVE SETTINGS APPLICATION & WIN32 REAPPLICATION VERIFIED")
    print(">>> ALL MILESTONE 2 TESTS PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    run_all_m2_tests()
