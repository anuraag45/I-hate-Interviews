import os
import sys
import time
import random
import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QCoreApplication

# Ensure CWD and sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(repo_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Set headless Qt
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance() or QApplication(sys.argv)

from gui.stealth_hud import compile_hud_stylesheet, StealthHUD, HUDUpdateSignaler
from gui.setup_center import SetupCenter

def test_compile_hud_stylesheet_fuzzing():
    """Fuzzing compile_hud_stylesheet with extreme, negative, and invalid parameters."""
    print("\n[CHALLENGE 1] Fuzzing Theme Compiler with Adversarial Inputs...")
    
    # 1. Invalid theme names and string formats
    invalid_themes = [
        "", "unknown_palette", "NEON_CYBERPUNK", "   ", 
        "calm-buttercup", "GENTLE SAGE", "oled_pure_black", "🎨_theme"
    ]
    for th in invalid_themes:
        res = compile_hud_stylesheet(theme_key=th, border_radius=14, font_size=13, opacity=0.96)
        assert isinstance(res, dict), f"Failed for theme {th}"
        assert "palette" in res
        assert "modern_frame" in res
        assert "card_s1" in res

    # 2. Extreme and boundary values
    test_cases = [
        # (border_radius, font_size, opacity, exp_r, exp_font, exp_op)
        (-100, -10, -5.0, 4, 9, 0.10),
        (0, 0, 0.0, 4, 9, 0.10),
        (1, 4, 0.05, 4, 9, 0.10),
        (4, 9, 0.10, 4, 9, 0.10),
        (14, 13, 0.96, 14, 13, 0.96),
        (24, 20, 1.0, 24, 20, 1.0),
        (25, 21, 1.05, 24, 20, 1.0),
        (500, 100, 50.0, 24, 20, 1.0),
        ("16", "14", "0.85", 16, 14, 0.85), # stringified inputs
    ]

    for br, fs, op, exp_r, exp_fs, exp_op in test_cases:
        res = compile_hud_stylesheet(theme_key="calm_buttercup", border_radius=br, font_size=fs, opacity=op)
        assert res["border_radius"] == exp_r, f"Expected radius {exp_r}, got {res['border_radius']}"
        assert res["font_size"] == exp_fs, f"Expected font {exp_fs}, got {res['font_size']}"
        assert abs(res["opacity"] - exp_op) < 0.001, f"Expected opacity {exp_op}, got {res['opacity']}"
        assert 0.35 <= res["card_alpha"] <= 0.98
        assert 0.45 <= res["input_alpha"] <= 0.98

    print("  -> PASSED: Theme compiler survives all adversarial inputs & strictly clamps bounds.")

def test_extreme_geometry_and_opacity_clamping():
    """Verify StealthHUD geometry and opacity strictly clamp to spec boundaries under stress."""
    print("\n[CHALLENGE 2] Testing StealthHUD Boundary Clamping Under Extreme Geometry...")
    
    hud = StealthHUD({})

    extreme_payloads = [
        # Width clamping: [280, 650], Height clamping: [400, 1080], Opacity clamping: [0.10, 1.0]
        ({"width": -500, "height": -100, "opacity": -2.0}, 280, 400, 0.10),
        ({"width": 0, "height": 0, "opacity": 0.0}, 280, 400, 0.10),
        ({"width": 10, "height": 10, "opacity": 0.05}, 280, 400, 0.10),
        ({"width": 279, "height": 399, "opacity": 0.09}, 280, 400, 0.10),
        ({"width": 280, "height": 400, "opacity": 0.10}, 280, 400, 0.10),
        ({"width": 370, "height": 640, "opacity": 0.96}, 370, 640, 0.96),
        ({"width": 650, "height": 1080, "opacity": 1.0}, 650, 1080, 1.0),
        ({"width": 651, "height": 1081, "opacity": 1.5}, 650, 1080, 1.0),
        ({"width": 50000, "height": 100000, "opacity": 99.0}, 650, 1080, 1.0),
    ]

    for ui_dict, exp_w, exp_h, exp_op in extreme_payloads:
        hud.apply_live_settings({"ui_settings": ui_dict})
        QCoreApplication.processEvents()
        assert hud.width() == exp_w, f"Width clamped incorrectly: expected {exp_w}, got {hud.width()}"
        assert hud.height() == exp_h, f"Height clamped incorrectly: expected {exp_h}, got {hud.height()}"
        assert abs(hud.windowOpacity() - exp_op) < 0.01, f"Opacity clamped incorrectly: expected {exp_op}, got {hud.windowOpacity()}"

    print("  -> PASSED: StealthHUD geometry and opacity strictly enforced within safe bounds.")

def test_rapid_burst_signal_emissions():
    """Stress test: Simulate rapid burst signal emissions from SetupCenter (320 guaranteed distinct events)."""
    print("\n[CHALLENGE 3] Stress Testing Rapid Burst Signal Emissions (320 updates)...")

    sc = SetupCenter()
    hud = StealthHUD(sc.get_current_settings_dict())
    sc.settings_changed.connect(hud.apply_live_settings)

    received_events = []
    hud_states = []

    def on_settings_received(cfg):
        received_events.append(cfg)
        hud_states.append({
            "w": hud.width(),
            "h": hud.height(),
            "op": hud.windowOpacity(),
            "font": hud.current_font_size,
            "badge": hud.lbl_model_badge.text(),
            "theme": hud.config.get("ui_settings", {}).get("theme")
        })

    sc.settings_changed.connect(on_settings_received)

    start_time = time.perf_counter()

    # Perform 320 distinct value alterations across all 28 controls
    for i in range(320):
        choice = i % 8
        round_num = i // 8
        if choice == 0:
            sc.spin_hud_width.setValue(300 + ((round_num * 17) % 300))
        elif choice == 1:
            sc.spin_hud_height.setValue(450 + ((round_num * 23) % 500))
        elif choice == 2:
            sc.slider_opacity.setValue(30 + ((round_num * 7) % 70))
        elif choice == 3:
            sc.spin_font_size.setValue(10 + (round_num % 10))
        elif choice == 4:
            sc.combo_theme.setCurrentIndex((round_num + 1) % 4)
        elif choice == 5:
            sc.combo_gemini_model.setCurrentIndex((round_num + 1) % 4)
        elif choice == 6:
            sc.txt_custom_model.setText(f"burst-model-v{i}")
        elif choice == 7:
            sc.chk_click_through.setChecked(not sc.chk_click_through.isChecked())

        QCoreApplication.processEvents()

    elapsed = time.perf_counter() - start_time
    print(f"  -> Processed 320 distinct rapid bursts in {elapsed * 1000:.2f} ms ({len(received_events)} signal dispatches)")

    assert len(received_events) == 320, f"Expected 320 dispatches, got {len(received_events)}"
    assert len(hud_states) == 320

    # Verify final state consistency
    final_cfg = sc.get_current_settings_dict()
    assert hud.config["ui_settings"]["theme"] == final_cfg["ui_settings"]["theme"]
    assert hud.current_font_size == max(9, min(20, final_cfg["ui_settings"]["font_size"]))
    assert hud.width() == max(280, min(650, final_cfg["ui_settings"]["width"]))
    assert hud.height() == max(400, min(1080, final_cfg["ui_settings"]["height"]))
    print("  -> PASSED: Rapid burst emissions handled cleanly without dropped state or UI desync.")

def test_theme_cycling_under_active_content_and_token_streaming():
    """Verify theme cycling does not corrupt active text, token streams, or font styling."""
    print("\n[CHALLENGE 4] Testing Rapid Theme Cycling Under Active Token Streams...")

    signaler = HUDUpdateSignaler()
    hud = StealthHUD({"ui_settings": {"theme": "calm_buttercup", "font_size": 14}}, signaler=signaler)

    # Populate cards with multi-line content
    s1_text = "### Clarifying Scope\n- Expected QPS: 100,000 writes/sec\n- Strict Partition Ordering: Required"
    s2_text = "### Architecture\n- Sharded Ring Buffer with Kafka event log\n- Memory-mapped IPC for low latency"
    s3_text = "def handle_stream(msg: bytes) -> bool:\n    return process_event(msg)"

    hud.set_stage_card_content(1, s1_text)
    hud.set_stage_card_content(2, s2_text)
    hud.set_stage_card_content(3, s3_text)
    hud.update_transcript("How do we partition the event stream when write throughput hits 100k QPS?")

    # Verify content set
    assert hud.txt_s1.text() == s1_text
    assert hud.txt_s2.text() == s2_text
    assert hud.txt_s3.text() == s3_text

    themes = ["calm_buttercup", "gentle_sage", "muted_slate", "oled_pure_black"]

    # Stream tokens while rapidly cycling themes
    for cycle in range(20):
        for th in themes:
            hud.apply_live_settings({"ui_settings": {"theme": th, "font_size": 12 + (cycle % 6)}})
            # Stream a token to each stage
            hud.append_stage_token(1, f" [token-{th}-s1]")
            hud.append_stage_token(2, f" [token-{th}-s2]")
            hud.append_stage_token(3, f" [token-{th}-s3]")
            QCoreApplication.processEvents()

    # Verify all content is preserved and appended cleanly
    assert s1_text in hud.txt_s1.text()
    assert s2_text in hud.txt_s2.text()
    assert s3_text in hud.txt_s3.text()
    assert "[token-oled_pure_black-s3]" in hud.txt_s3.text()
    assert "How do we partition" in hud.lbl_transcript.text()

    # Verify clear operation restores italic placeholders
    hud.clear_content()
    assert "Ready for next topic" in hud.txt_s1.text()
    assert "Architecture breakdown" in hud.txt_s2.text()
    assert "Code implementation" in hud.txt_s3.text()

    print("  -> PASSED: Text content, token streams, and typography remain intact through rapid theme transitions.")

def test_malformed_and_missing_payload_resilience():
    """Verify StealthHUD handles partial, empty, and omitted config payloads gracefully."""
    print("\n[CHALLENGE 5] Testing Resilience Against Partial and Missing Payloads...")

    hud = StealthHUD({})

    partial_configs = [
        {},
        {"ui_settings": {}},
        {"ai_settings": {}},
        {"ui_settings": {"theme": "gentle_sage"}},
        {"ui_settings": {"width": 450}},
        {"ui_settings": {"opacity": 0.80}},
        {"ai_settings": {"custom_model": "gemini-test"}},
        {"ui_settings": {"stealth_affinity": False, "vu_mode": "wave"}}
    ]

    for idx, cfg in enumerate(partial_configs):
        hud.apply_live_settings(cfg)
        QCoreApplication.processEvents()
        assert 280 <= hud.width() <= 650
        assert 400 <= hud.height() <= 1080
        assert 0.10 <= hud.windowOpacity() <= 1.0

    print("  -> PASSED: StealthHUD gracefully survived all empty and partial payloads.")

def test_vu_modes_dynamic_switch():
    """Verify VU mode cycling dynamically updates widget styling and display formats."""
    print("\n[CHALLENGE 6] Testing VU Equalizer Modes Dynamic Switching...")
    hud = StealthHUD({})

    for mode in ["dots", "wave", "numeric", "dots"]:
        hud.apply_live_settings({"ui_settings": {"vu_mode": mode}})
        assert hud.vu_mode == mode
        assert mode.upper() in hud.btn_vu_mode.text()

    print("  -> PASSED: VU Equalizer styles and modes switch dynamically without lag.")

def run_adversarial_suite():
    print("=" * 70)
    print("      MILESTONE 1 - ADVERSARIAL CHALLENGER EMPIRICAL SUITE       ")
    print("=" * 70)
    test_compile_hud_stylesheet_fuzzing()
    test_extreme_geometry_and_opacity_clamping()
    test_rapid_burst_signal_emissions()
    test_theme_cycling_under_active_content_and_token_streaming()
    test_malformed_and_missing_payload_resilience()
    test_vu_modes_dynamic_switch()
    print("\n" + "=" * 70)
    print("  >>> ALL ADVERSARIAL CHALLENGE STRESS TESTS PASSED WITH 100% SUCCESS <<<")
    print("=" * 70)

if __name__ == "__main__":
    run_adversarial_suite()
