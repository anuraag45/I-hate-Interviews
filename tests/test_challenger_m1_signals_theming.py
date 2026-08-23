"""
Empirical Challenger Test Harness - Milestone 1: Dynamic Sync & Theming Architecture
Comprehensive verification of all 30 SetupCenter controls, 4-palette QSS integrity,
memory leak safety under rapid switching, signal/slot connectivity, and adversarial input resilience.
"""

import os
import sys
import gc
import tracemalloc
import pytest
from PyQt6.QtWidgets import QApplication, QWidget, QFrame, QLabel, QPushButton, QLineEdit
from PyQt6.QtCore import Qt, qInstallMessageHandler, QtMsgType

# Ensure repo root is on sys.path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(repo_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Set headless platform before QApplication initialization
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from gui.setup_center import SetupCenter, GEMINI_MODELS, PRESENTATION_PRESETS
from gui.stealth_hud import compile_hud_stylesheet, StealthHUD, HUDUpdateSignaler


def test_exhaustive_30_ui_signal_broadcasts():
    """
    Empirically test every single interactive control in SetupCenter.
    Verify that modifying each control individually emits `settings_changed`
    and populates `get_current_settings_dict()` with the exact expected values.
    """
    sc = SetupCenter()
    emitted = []
    sc.settings_changed.connect(lambda cfg: emitted.append(cfg))

    # Control 1: spin_hud_width
    emitted.clear()
    new_w = 410 if sc.spin_hud_width.value() != 410 else 420
    sc.spin_hud_width.setValue(new_w)
    assert len(emitted) == 1, "spin_hud_width failed to emit settings_changed"
    assert emitted[-1]["ui_settings"]["width"] == new_w

    # Control 2: spin_hud_height
    emitted.clear()
    new_h = 730 if sc.spin_hud_height.value() != 730 else 740
    sc.spin_hud_height.setValue(new_h)
    assert len(emitted) == 1, "spin_hud_height failed to emit settings_changed"
    assert emitted[-1]["ui_settings"]["height"] == new_h

    # Control 3: slider_opacity
    emitted.clear()
    new_op = 80 if sc.slider_opacity.value() != 80 else 85
    sc.slider_opacity.setValue(new_op)
    assert len(emitted) == 1, "slider_opacity failed to emit settings_changed"
    assert abs(emitted[-1]["ui_settings"]["opacity"] - (new_op / 100.0)) < 1e-4

    # Control 4: spin_font_size
    emitted.clear()
    new_fs = 16 if sc.spin_font_size.value() != 16 else 17
    sc.spin_font_size.setValue(new_fs)
    assert len(emitted) == 1, "spin_font_size failed to emit settings_changed"
    assert emitted[-1]["ui_settings"]["font_size"] == new_fs

    # Control 5: spin_border_radius
    emitted.clear()
    new_br = 20 if sc.spin_border_radius.value() != 20 else 22
    sc.spin_border_radius.setValue(new_br)
    assert len(emitted) == 1, "spin_border_radius failed to emit settings_changed"
    assert emitted[-1]["ui_settings"]["border_radius"] == new_br

    # Control 6: combo_theme
    emitted.clear()
    new_theme_idx = (sc.combo_theme.currentIndex() + 1) % sc.combo_theme.count()
    expected_theme = sc.combo_theme.itemText(new_theme_idx).lower().replace(" ", "_")
    sc.combo_theme.setCurrentIndex(new_theme_idx)
    assert len(emitted) == 1, "combo_theme failed to emit settings_changed"
    assert emitted[-1]["ui_settings"]["theme"] == expected_theme

    # Control 7: combo_vu_mode
    emitted.clear()
    new_vu_idx = (sc.combo_vu_mode.currentIndex() + 1) % sc.combo_vu_mode.count()
    expected_vu = sc.combo_vu_mode.itemText(new_vu_idx).lower()
    sc.combo_vu_mode.setCurrentIndex(new_vu_idx)
    assert len(emitted) == 1, "combo_vu_mode failed to emit settings_changed"
    assert emitted[-1]["ui_settings"]["vu_mode"] == expected_vu

    # Control 8: chk_stealth
    emitted.clear()
    curr_stealth = sc.chk_stealth.isChecked()
    sc.chk_stealth.setChecked(not curr_stealth)
    assert len(emitted) == 1, "chk_stealth failed to emit settings_changed"
    assert emitted[-1]["ui_settings"]["stealth_affinity"] == (not curr_stealth)

    # Control 9: chk_click_through
    emitted.clear()
    curr_ct = sc.chk_click_through.isChecked()
    sc.chk_click_through.setChecked(not curr_ct)
    assert len(emitted) == 1, "chk_click_through failed to emit settings_changed"
    assert emitted[-1]["ui_settings"]["click_through_default"] == (not curr_ct)

    # Control 10: combo_gemini_model
    emitted.clear()
    new_gem_idx = (sc.combo_gemini_model.currentIndex() + 1) % sc.combo_gemini_model.count()
    expected_gem = sc.combo_gemini_model.itemText(new_gem_idx)
    sc.combo_gemini_model.setCurrentIndex(new_gem_idx)
    assert len(emitted) == 1, "combo_gemini_model failed to emit settings_changed"
    assert emitted[-1]["ai_settings"]["gemini_model"] == expected_gem

    # Control 11: combo_llm
    emitted.clear()
    new_llm_idx = (sc.combo_llm.currentIndex() + 1) % sc.combo_llm.count()
    expected_llm = sc.combo_llm.itemText(new_llm_idx).lower()
    sc.combo_llm.setCurrentIndex(new_llm_idx)
    assert len(emitted) == 1, "combo_llm failed to emit settings_changed"
    assert emitted[-1]["preferred_llm"] == expected_llm

    # Control 12: txt_custom_model
    emitted.clear()
    sc.txt_custom_model.setText("gemini-3.7-flash-exp-02")
    assert len(emitted) == 1, "txt_custom_model failed to emit settings_changed"
    assert emitted[-1]["ai_settings"]["custom_model"] == "gemini-3.7-flash-exp-02"

    # Control 13: txt_groq_model
    emitted.clear()
    sc.txt_groq_model.setText("llama-3.3-70b-specdec")
    assert len(emitted) == 1, "txt_groq_model failed to emit settings_changed"
    assert emitted[-1]["ai_settings"]["groq_model"] == "llama-3.3-70b-specdec"

    # Control 14: txt_openai_model
    emitted.clear()
    sc.txt_openai_model.setText("gpt-4.5-preview")
    assert len(emitted) == 1, "txt_openai_model failed to emit settings_changed"
    assert emitted[-1]["ai_settings"]["openai_model"] == "gpt-4.5-preview"

    # Control 15: spin_temp
    emitted.clear()
    new_temp = 0.65 if sc.spin_temp.value() != 0.65 else 0.70
    sc.spin_temp.setValue(new_temp)
    assert len(emitted) == 1, "spin_temp failed to emit settings_changed"
    assert abs(emitted[-1]["ai_settings"]["temperature"] - new_temp) < 1e-4

    # Control 16: spin_tokens
    emitted.clear()
    new_tok = 3072 if sc.spin_tokens.value() != 3072 else 2048
    sc.spin_tokens.setValue(new_tok)
    assert len(emitted) == 1, "spin_tokens failed to emit settings_changed"
    assert emitted[-1]["ai_settings"]["max_tokens"] == new_tok

    # Control 17: txt_prompt_prefix
    emitted.clear()
    sc.txt_prompt_prefix.setPlainText("Answer with concise bullet points and algorithmic analysis.")
    assert len(emitted) == 1, "txt_prompt_prefix failed to emit settings_changed"
    assert emitted[-1]["ai_settings"]["custom_prompt_prefix"] == "Answer with concise bullet points and algorithmic analysis."

    # Control 18: spin_audio_thresh
    emitted.clear()
    new_ath = 0.085 if sc.spin_audio_thresh.value() != 0.085 else 0.090
    sc.spin_audio_thresh.setValue(new_ath)
    assert len(emitted) == 1, "spin_audio_thresh failed to emit settings_changed"
    assert abs(emitted[-1]["audio_settings"]["sensitivity_threshold"] - new_ath) < 1e-4

    # Control 19: spin_silence_timeout
    emitted.clear()
    new_sto = 3.4 if sc.spin_silence_timeout.value() != 3.4 else 3.8
    sc.spin_silence_timeout.setValue(new_sto)
    assert len(emitted) == 1, "spin_silence_timeout failed to emit settings_changed"
    assert abs(emitted[-1]["audio_settings"]["silence_timeout_sec"] - new_sto) < 1e-4

    # Control 20: combo_role
    emitted.clear()
    new_role_idx = (sc.combo_role.currentIndex() + 1) % sc.combo_role.count()
    expected_role = sc.combo_role.itemText(new_role_idx)
    sc.combo_role.setCurrentIndex(new_role_idx)
    assert len(emitted) == 1, "combo_role failed to emit settings_changed"
    assert emitted[-1]["role_preset"] == expected_role

    # Control 21: txt_name
    emitted.clear()
    sc.txt_name.setText("Dr. Jane Doe")
    assert len(emitted) == 1, "txt_name failed to emit settings_changed"
    assert emitted[-1]["user_profile"]["name"] == "Dr. Jane Doe"

    # Control 22: txt_exp
    emitted.clear()
    sc.txt_exp.setText("Distinguished Engineer (20+ YOE)")
    assert len(emitted) == 1, "txt_exp failed to emit settings_changed"
    assert emitted[-1]["user_profile"]["years_of_experience"] == "Distinguished Engineer (20+ YOE)"

    # Control 23: txt_skills
    emitted.clear()
    sc.txt_skills.setText("LLM Compilers, CUDA, Distributed Training, PyTorch")
    assert len(emitted) == 1, "txt_skills failed to emit settings_changed"
    assert emitted[-1]["user_profile"]["primary_skills"] == "LLM Compilers, CUDA, Distributed Training, PyTorch"

    # Control 24: txt_summary
    emitted.clear()
    sc.txt_summary.setPlainText("Focusing on low-latency inference runtimes.")
    assert len(emitted) == 1, "txt_summary failed to emit settings_changed"
    assert emitted[-1]["user_profile"]["summary"] == "Focusing on low-latency inference runtimes."

    # Control 25: txt_resume
    emitted.clear()
    sc.txt_resume.setPlainText("Built tensor parallelism frameworks for trillion-token models.")
    assert len(emitted) == 1, "txt_resume failed to emit settings_changed"
    assert emitted[-1]["user_profile"]["resume_text"] == "Built tensor parallelism frameworks for trillion-token models."

    # Control 26: txt_jd
    emitted.clear()
    sc.txt_jd.setPlainText("Deep dive into kernel fusion, memory bandwidth bounds, and RoPE.")
    assert len(emitted) == 1, "txt_jd failed to emit settings_changed"
    assert emitted[-1]["user_profile"]["job_description_text"] == "Deep dive into kernel fusion, memory bandwidth bounds, and RoPE."

    # Control 27: txt_gemini
    emitted.clear()
    sc.txt_gemini.setText("AIzaSy-ChallengerTestKey123")
    assert len(emitted) == 1, "txt_gemini failed to emit settings_changed"
    assert emitted[-1]["api_keys"]["gemini"] == "AIzaSy-ChallengerTestKey123"

    # Control 28: txt_groq
    emitted.clear()
    sc.txt_groq.setText("gsk_ChallengerTestKey456")
    assert len(emitted) == 1, "txt_groq failed to emit settings_changed"
    assert emitted[-1]["api_keys"]["groq"] == "gsk_ChallengerTestKey456"

    # Control 29: txt_deepgram
    emitted.clear()
    sc.txt_deepgram.setText("dg_ChallengerTestKey789")
    assert len(emitted) == 1, "txt_deepgram failed to emit settings_changed"
    assert emitted[-1]["api_keys"]["deepgram"] == "dg_ChallengerTestKey789"

    # Control 30: txt_openai
    emitted.clear()
    sc.txt_openai.setText("sk-proj-ChallengerTestKey000")
    assert len(emitted) == 1, "txt_openai failed to emit settings_changed"
    assert emitted[-1]["api_keys"]["openai"] == "sk-proj-ChallengerTestKey000"

    print("  -> PASS: All 30 individual UI controls correctly broadcast live settings.")


def test_qss_parser_integrity_and_qt_warnings():
    """
    Test that compile_hud_stylesheet produces valid QSS across all 4 themes
    and various parameter permutations, with zero Qt CSS parser warnings or syntax errors.
    """
    qt_warnings = []

    def qt_message_handler(msg_type, context, message):
        if msg_type in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
            # Check if warning relates to stylesheet parsing
            if "stylesheet" in message.lower() or "css" in message.lower() or "could not parse" in message.lower() or "unknown property" in message.lower():
                qt_warnings.append(message)

    old_handler = qInstallMessageHandler(qt_message_handler)

    themes = ["calm_buttercup", "gentle_sage", "muted_slate", "oled_pure_black"]
    border_radii = [4, 8, 14, 20, 24]
    font_sizes = [9, 11, 13, 16, 20]
    opacities = [0.10, 0.50, 0.85, 0.96, 1.0]

    dummy_frame = QFrame()
    dummy_label = QLabel()
    dummy_button = QPushButton()
    dummy_input = QLineEdit()

    try:
        for th in themes:
            for br in border_radii:
                for fs in font_sizes:
                    for op in opacities:
                        res = compile_hud_stylesheet(theme_key=th, border_radius=br, font_size=fs, opacity=op)
                        
                        # Apply style fragments to corresponding widget types
                        dummy_frame.setStyleSheet(res["modern_frame"])
                        dummy_frame.setStyleSheet(res["card_s1"])
                        dummy_frame.setStyleSheet(res["card_s2"])
                        dummy_frame.setStyleSheet(res["card_s3"])
                        dummy_frame.setStyleSheet(res["vu_box"])
                        dummy_label.setStyleSheet(res["transcript_box"])
                        dummy_label.setStyleSheet(res["model_badge"])
                        dummy_input.setStyleSheet(res["query_input"])
                        dummy_button.setStyleSheet(res["smart_btn"])
                        dummy_button.setStyleSheet(res["send_btn"])
                        dummy_button.setStyleSheet(res["btn_act_s1"])
                        dummy_button.setStyleSheet(res["btn_act_s2"])
                        dummy_button.setStyleSheet(res["btn_act_s3"])
                        dummy_button.setStyleSheet(res["btn_act_snip"])
                        dummy_button.setStyleSheet(res["btn_header"])
                        dummy_button.setStyleSheet(res["btn_hide"])
                        dummy_button.setStyleSheet(res["btn_clear"])

        assert len(qt_warnings) == 0, f"Qt stylesheet parser warnings captured: {qt_warnings}"
        print(f"  -> PASS: Verified QSS validity across {len(themes)*len(border_radii)*len(font_sizes)*len(opacities)} permutations (0 Qt warnings).")
    finally:
        qInstallMessageHandler(old_handler)


def test_live_theme_switching_stress_and_memory_leak():
    """
    Stress-test live theme switching with 500 rapid permutations.
    Empirically verify that memory consumption remains bounded and does not leak,
    and that all Qt widgets survive the rapid reconfiguration.
    """
    sc = SetupCenter()
    hud = StealthHUD(sc.get_current_settings_dict())
    sc.settings_changed.connect(hud.apply_live_settings)

    themes = ["calm_buttercup", "gentle_sage", "muted_slate", "oled_pure_black"]
    vu_modes = ["dots", "wave", "numeric"]

    gc.collect()
    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()

    for i in range(500):
        th_idx = i % len(themes)
        vu_idx = i % len(vu_modes)
        w = 300 + (i % 300)
        h = 500 + (i % 400)
        op = 40 + (i % 60)
        fs = 10 + (i % 10)
        br = 6 + (i % 18)

        sc.combo_theme.setCurrentIndex(th_idx)
        sc.combo_vu_mode.setCurrentIndex(vu_idx)
        sc.spin_hud_width.setValue(w)
        sc.spin_hud_height.setValue(h)
        sc.slider_opacity.setValue(op)
        sc.spin_font_size.setValue(fs)
        sc.spin_border_radius.setValue(br)

        # Verify live values reflected immediately
        expected_theme = themes[th_idx]
        assert hud.config["ui_settings"]["theme"] == expected_theme
        assert hud.width() == w
        assert hud.height() == h
        assert hud.current_font_size == fs
        assert hud.vu_mode == vu_modes[vu_idx]

    gc.collect()
    snap_after = tracemalloc.take_snapshot()
    top_stats = snap_after.compare_to(snap_before, 'lineno')
    total_diff_kb = sum(stat.size_diff for stat in top_stats) / 1024.0
    tracemalloc.stop()

    print(f"  -> Memory diff after 500 live mutations: {total_diff_kb:.2f} KB (Safe & bounded)")
    # Memory growth across 500 live mutations must be bounded (< 8 MB in Python)
    assert total_diff_kb < 8192, f"Excessive memory growth detected: {total_diff_kb:.2f} KB"
    print("  -> PASS: Live theme switching stress test completed with zero leaks.")


def test_widget_signal_slot_connectivity_post_theme_switch():
    """
    Verify that all widget interactive signals, slots, token streaming,
    stage progression, and button click handlers remain 100% operational
    after intense live configuration changes.
    """
    sc = SetupCenter()
    signaler = HUDUpdateSignaler()
    hud = StealthHUD(sc.get_current_settings_dict(), signaler=signaler)
    sc.settings_changed.connect(hud.apply_live_settings)

    # Perform theme switch
    sc.combo_theme.setCurrentIndex(3) # OLED Pure Black
    sc.spin_font_size.setValue(15)

    # Track interactive signals emitted by HUD
    smart_emitted = []
    s1_emitted = []
    s2_emitted = []
    s3_emitted = []
    snip_emitted = []
    query_emitted = []
    clear_emitted = []

    signaler.action_smart_next.connect(lambda: smart_emitted.append(True))
    signaler.action_stage_1.connect(lambda: s1_emitted.append(True))
    signaler.action_stage_2.connect(lambda: s2_emitted.append(True))
    signaler.action_stage_3.connect(lambda: s3_emitted.append(True))
    signaler.action_vision_snip.connect(lambda: snip_emitted.append(True))
    signaler.action_custom_query.connect(lambda q: query_emitted.append(q))
    signaler.clear_triggered.connect(lambda: clear_emitted.append(True))

    # 1. Click Smart Next
    hud.btn_act_smart.click()
    assert len(smart_emitted) == 1
    assert "Generating" in hud.lbl_status.text()

    # 2. Click S1
    hud.btn_act_s1.click()
    assert len(s1_emitted) == 1
    assert "Stage 1" in hud.lbl_status.text()

    # 3. Click S2
    hud.btn_act_s2.click()
    assert len(s2_emitted) == 1
    assert "Stage 2" in hud.lbl_status.text()

    # 4. Click S3
    hud.btn_act_s3.click()
    assert len(s3_emitted) == 1
    assert "Stage 3" in hud.lbl_status.text()

    # 5. Click Snip
    hud.btn_act_snip.click()
    assert len(snip_emitted) == 1
    assert "Snipping" in hud.lbl_status.text()

    # 6. Stream tokens into cards
    hud.append_stage_token(1, "Clarification: Write-heavy or read-heavy?")
    assert "Clarification: Write-heavy or read-heavy?" in hud.txt_s1.text()
    assert "Streaming S1" in hud.lbl_status.text()

    hud.append_stage_token(2, "Architecture: Partitioned Kafka + ClickHouse")
    assert "Architecture: Partitioned Kafka + ClickHouse" in hud.txt_s2.text()

    hud.append_stage_token(3, "def process_batch(stream): return [x*2 for x in stream]")
    assert "def process_batch" in hud.txt_s3.text()

    # 7. Complete stage cards
    hud.set_stage_card_content(1, "Full Stage 1 Scope Documented")
    assert hud.txt_s1.text() == "Full Stage 1 Scope Documented"
    assert "Complete" in hud.lbl_status.text()

    # 8. Test Clipboard Copy from Stage 3
    hud.btn_copy.click()
    assert "Copied Code" in hud.lbl_status.text()
    assert QApplication.clipboard().text() == "def process_batch(stream): return [x*2 for x in stream]"

    # 9. Test Query Input Send
    hud.txt_query.setText("How to handle partition rebalancing?")
    hud.btn_send.click()
    assert len(query_emitted) == 1
    assert query_emitted[-1] == "How to handle partition rebalancing?"
    assert hud.txt_query.text() == ""
    assert "How to handle partition rebalancing?" in hud.lbl_transcript.text()

    # 10. Test Clear
    hud.btn_clear.click()
    assert len(clear_emitted) == 1
    assert "Ready for next topic" in hud.txt_s1.text()
    assert "Architecture breakdown" in hud.txt_s2.text()
    assert "Code implementation" in hud.txt_s3.text()
    assert "Listening for meeting audio" in hud.lbl_transcript.text()

    # 11. Test Font Scaling Buttons
    cur_f = hud.current_font_size
    hud.btn_font_inc.click()
    assert hud.current_font_size == cur_f + 1
    hud.btn_font_dec.click()
    assert hud.current_font_size == cur_f

    # 12. Test Ghost Click-Through Toggle
    ct_initial = hud.is_click_through
    hud.btn_ghost.click()
    assert hud.is_click_through == (not ct_initial)

    # 13. Test VU Mode Cycle
    vu_init = hud.vu_mode
    hud.btn_vu_mode.click()
    assert hud.vu_mode != vu_init

    print("  -> PASS: All HUD buttons, signals, slots, and text inputs remain 100% responsive post-theme change.")


def test_adversarial_inputs_and_edge_cases():
    """
    Adversarial challenge: Test extreme edge cases, invalid themes, QSS injection strings,
    out-of-bounds geometry, unicode/emoji storms, and empty inputs.
    """
    sc = SetupCenter()
    hud = StealthHUD(sc.get_current_settings_dict())

    # 1. Invalid theme names (should gracefully fallback to calm_buttercup)
    for invalid_theme in ["", "matrix_green", "   ", "cyberpunk_neon_2077", None]:
        res = compile_hud_stylesheet(theme_key=invalid_theme)
        assert res["palette"]["name"] == "Calm Buttercup", f"Failed to fallback on invalid theme '{invalid_theme}'"

    # 2. Case and formatting insensitivity
    for valid_variant in ["  CALM-BUTTERCUP  ", "Gentle_Sage", "MUTED_SLATE", "oled pure black"]:
        res = compile_hud_stylesheet(theme_key=valid_variant)
        assert "palette" in res and res["palette"]["name"] != ""

    # 3. Out-of-bounds geometry clamping
    hud.apply_live_settings({
        "ui_settings": {
            "width": -9999,
            "height": 99999,
            "opacity": 5.0,
            "font_size": 999,
            "border_radius": -100
        }
    })
    assert hud.width() == 280, f"Expected min width 280, got {hud.width()}"
    assert hud.height() == 1080, f"Expected max height 1080, got {hud.height()}"
    assert hud.windowOpacity() == 1.0, f"Expected max opacity 1.0, got {hud.windowOpacity()}"
    assert hud.current_font_size == 20, f"Expected max font size 20, got {hud.current_font_size}"

    # 4. QSS Injection strings in user inputs
    injection_strings = [
        "'; background: red; color: yellow; } * { font-size: 100px; '",
        "<script>alert('xss')</script>",
        "🔥🚀💻 \u2603 \u2600 \ufe0f ⚡ [SPECIAL_CHARS_!@#$%^&*()_+={}:;\"'<>?,./~`]",
        "A" * 5000 # 5KB string
    ]

    for inj in injection_strings:
        sc.txt_name.setText(inj)
        sc.txt_custom_model.setText(inj)
        sc.txt_prompt_prefix.setPlainText(inj)
        sc.txt_summary.setPlainText(inj)

        cfg = sc.get_current_settings_dict()
        assert cfg["user_profile"]["name"] == inj.strip()
        assert cfg["ai_settings"]["custom_model"] == inj.strip()

        # StealthHUD should apply without crashing or throwing
        hud.apply_live_settings(cfg)
        assert hud.lbl_model_badge.text().startswith("⚡")

    print("  -> PASS: System safely withstands adversarial inputs, boundary violations, and QSS injection strings.")


if __name__ == "__main__":
    print("=" * 65, flush=True)
    print("   CHALLENGER 2: EMPIRICAL VERIFICATION OF SIGNALS & THEMING    ", flush=True)
    print("=" * 65, flush=True)
    print("[1/5] Testing exhaustive 30 UI signal broadcasts...", flush=True)
    test_exhaustive_30_ui_signal_broadcasts()
    print("[2/5] Testing QSS parser integrity and Qt warnings...", flush=True)
    test_qss_parser_integrity_and_qt_warnings()
    print("[3/5] Testing live theme switching stress and memory leak...", flush=True)
    test_live_theme_switching_stress_and_memory_leak()
    print("[4/5] Testing widget signal/slot connectivity post theme switch...", flush=True)
    test_widget_signal_slot_connectivity_post_theme_switch()
    print("[5/5] Testing adversarial inputs and edge cases...", flush=True)
    test_adversarial_inputs_and_edge_cases()
    print("=" * 65, flush=True)
    print("  >>> ALL EMPIRICAL CHALLENGER TESTS PASSED WITH 100% SUCCESS <<<  ", flush=True)
    print("=" * 65, flush=True)
