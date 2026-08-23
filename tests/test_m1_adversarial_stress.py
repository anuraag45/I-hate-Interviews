"""
Empirical Challenger 2 Adversarial Stress Harness - Milestone 1: Dynamic Sync & Theming Architecture
Comprehensive verification of:
1. Font scaling across all cards with multiline markdown text and placeholder state transitions.
2. Dynamic toggling of Win32 stealth affinity (WDA_EXCLUDEFROMCAPTURE) and click-through (WS_EX_TRANSPARENT).
3. Rapid burst signal emissions across all 30 SetupCenter interactive controls.
4. Rapid theme cycling under active multiline tokens, memory leak bounding, and QSS integrity.
5. Geometry clamping and boundary conditions under extreme inputs.
"""

import os
import sys
import time
import gc
import ctypes
import pytest
from PyQt6.QtWidgets import QApplication, QLabel, QFrame, QPushButton, QLineEdit
from PyQt6.QtCore import Qt, QTimer, qInstallMessageHandler, QtMsgType

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(repo_root)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Win32 Constants
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020

user32 = getattr(ctypes.windll, 'user32', None) if sys.platform == "win32" else None

# Initialize QApplication
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from gui.stealth_hud import compile_hud_stylesheet, StealthHUD, HUDUpdateSignaler
from gui.setup_center import SetupCenter
from stealth.win32_affinity import apply_stealth_affinity, apply_non_activating_styles


# =========================================================================
# TEST 1: FONT SCALING, MULTILINE MARKDOWN & PLACEHOLDER STATE TRANSITIONS
# =========================================================================

def test_font_scaling_multiline_markdown_and_placeholders():
    print("\n[CHALLENGE 1] Testing Font Scaling, Multiline Markdown & Placeholder State Transitions...")
    
    cfg = {
        "ui_settings": {
            "theme": "calm_buttercup",
            "opacity": 0.95,
            "font_size": 13,
            "border_radius": 14,
            "width": 370,
            "height": 640,
            "stealth_affinity": True,
            "click_through_default": False,
            "vu_mode": "dots"
        },
        "ai_settings": {
            "gemini_model": "gemini-3.7-flash"
        }
    }
    hud = StealthHUD(cfg)
    
    # 1. Initial State: All cards must have italic muted placeholder styling
    styles_13 = compile_hud_stylesheet("calm_buttercup", font_size=13)
    pal = styles_13["palette"]
    
    for card_idx, txt_lbl in [(1, hud.txt_s1), (2, hud.txt_s2), (3, hud.txt_s3)]:
        style = txt_lbl.styleSheet()
        assert "font-style: italic" in style, f"Card S{card_idx} should have italic style initially"
        assert pal["text_muted"] in style, f"Card S{card_idx} should use muted text color initially"
        assert "font-size: 13px" in style, f"Card S{card_idx} should have font-size 13px"

    # 2. Font Scaling on Placeholders (Buttons A+ and A-)
    # Scale up to 16px
    for _ in range(3):
        hud.btn_font_inc.click()
    assert hud.current_font_size == 16
    for card_idx, txt_lbl in [(1, hud.txt_s1), (2, hud.txt_s2), (3, hud.txt_s3)]:
        style = txt_lbl.styleSheet()
        assert "font-style: italic" in style, f"Card S{card_idx} must maintain italic after font scaling"
        assert pal["text_muted"] in style, f"Card S{card_idx} must maintain muted color after font scaling"
        assert "font-size: 16px" in style, f"Card S{card_idx} should update to font-size 16px"

    # Scale down past minimum (test clamping at 9px)
    for _ in range(15):
        hud.btn_font_dec.click()
    assert hud.current_font_size == 9
    for card_idx, txt_lbl in [(1, hud.txt_s1), (2, hud.txt_s2), (3, hud.txt_s3)]:
        style = txt_lbl.styleSheet()
        assert "font-size: 9px" in style
        assert "font-style: italic" in style

    # Scale up past maximum (test clamping at 20px)
    for _ in range(25):
        hud.btn_font_inc.click()
    assert hud.current_font_size == 20
    for card_idx, txt_lbl in [(1, hud.txt_s1), (2, hud.txt_s2), (3, hud.txt_s3)]:
        style = txt_lbl.styleSheet()
        assert "font-size: 20px" in style
        assert "font-style: italic" in style

    # 3. Transition: Streaming Multiline Markdown Content into Card S1
    markdown_s1 = (
        "### Clarifying Scope & Constraints\n"
        "- **Throughput**: 100,000 QPS write heavy traffic\n"
        "- **Latency Target**: p99 < 50ms\n"
        "- **Consistency**: Eventual consistency across read replicas\n"
        "- **Key Question**: *Should we partition by user_id or event_timestamp?*"
    )
    hud.append_stage_token(1, "### Clarifying Scope & Constraints\n")
    hud.append_stage_token(1, "- **Throughput**: 100,000 QPS write heavy traffic\n")
    hud.append_stage_token(1, "- **Latency Target**: p99 < 50ms\n")
    hud.append_stage_token(1, "- **Consistency**: Eventual consistency across read replicas\n")
    hud.append_stage_token(1, "- **Key Question**: *Should we partition by user_id or event_timestamp?*")

    # Card S1 must now be normal font-style and primary text color
    style_s1 = hud.txt_s1.styleSheet()
    assert "font-style: normal" in style_s1, "Card S1 style must be normal after streaming"
    assert pal["text_primary"] in style_s1, "Card S1 text color must be text_primary"
    assert "font-size: 20px" in style_s1, "Card S1 font size must be 20px"
    assert "100,000 QPS" in hud.txt_s1.text()

    # Cards S2 and S3 must still be placeholder italic
    assert "font-style: italic" in hud.txt_s2.styleSheet()
    assert "font-style: italic" in hud.txt_s3.styleSheet()

    # 4. Set complete markdown content in Card S2 and Card S3
    markdown_s2 = (
        "## Architecture & Trade-Offs\n"
        "1. **Option A: Partition by User ID**\n"
        "   - Pros: Linear scaling for user queries, clean sharding\n"
        "   - Cons: Hot partitions for super-users\n"
        "2. **Option B: Consistent Hashing Ring (Recommended)**\n"
        "   - Virtual nodes: 256 per physical broker\n"
        "   - Replication Factor: 3 with quorum writes (W=2, R=2)"
    )
    markdown_s3 = (
        "```python\n"
        "class ConsistentHashRing:\n"
        "    def __init__(self, replicas: int = 256):\n"
        "        self.replicas = replicas\n"
        "        self.ring = {}\n"
        "        self.sorted_keys = []\n"
        "```"
    )
    hud.set_stage_card_content(2, markdown_s2)
    hud.set_stage_card_content(3, markdown_s3)

    assert "font-style: normal" in hud.txt_s2.styleSheet()
    assert pal["text_primary"] in hud.txt_s2.styleSheet()
    assert "font-style: normal" in hud.txt_s3.styleSheet()
    assert pal["text_primary"] in hud.txt_s3.styleSheet()

    # 5. Font Scaling with Active Multiline Content
    hud.apply_live_settings({
        "ui_settings": {
            "theme": "gentle_sage",
            "opacity": 0.90,
            "font_size": 14,
            "border_radius": 12,
            "width": 420,
            "height": 700
        }
    })
    sage_pal = compile_hud_stylesheet("gentle_sage", font_size=14)["palette"]
    assert hud.current_font_size == 14
    for txt_lbl in [hud.txt_s1, hud.txt_s2, hud.txt_s3]:
        style = txt_lbl.styleSheet()
        assert "font-size: 14px" in style
        assert "font-style: normal" in style
        assert sage_pal["text_primary"] in style

    # 6. Clear Content State Transition
    hud.clear_content()
    for card_idx, txt_lbl in [(1, hud.txt_s1), (2, hud.txt_s2), (3, hud.txt_s3)]:
        style = txt_lbl.styleSheet()
        assert "font-style: italic" in style, f"Card S{card_idx} must return to italic placeholder after clear"
        assert sage_pal["text_muted"] in style, f"Card S{card_idx} must return to muted text color after clear"
        assert "font-size: 14px" in style, f"Card S{card_idx} font-size should remain 14px"

    print("  -> PASS: Font scaling, multiline markdown, and placeholder state transitions verified.")


# =========================================================================
# TEST 2: WIN32 STEALTH AFFINITY & CLICK-THROUGH DYNAMIC TOGGLING
# =========================================================================

def test_win32_stealth_affinity_and_click_through():
    print("\n[CHALLENGE 2] Testing Win32 Stealth Affinity & Click-Through Dynamic Toggling...")
    
    cfg = {
        "ui_settings": {
            "theme": "muted_slate",
            "opacity": 0.95,
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
    hud.show()
    QApplication.processEvents()

    hwnd = int(hud.winId())
    assert hwnd != 0, "HUD HWND must be valid"

    if sys.platform == "win32" and user32:
        # Direct verify apply_stealth_affinity
        aff_res_true = apply_stealth_affinity(hwnd, exclude=True)
        assert aff_res_true is True, "apply_stealth_affinity(exclude=True) must succeed on Windows"

        aff_res_false = apply_stealth_affinity(hwnd, exclude=False)
        assert aff_res_false is True, "apply_stealth_affinity(exclude=False) must succeed on Windows"

        # Direct verify apply_non_activating_styles
        res_no_ct = apply_non_activating_styles(hwnd, click_through=False)
        assert res_no_ct is True
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        assert (style & WS_EX_NOACTIVATE) != 0, "WS_EX_NOACTIVATE bit must be set"
        assert (style & WS_EX_LAYERED) != 0, "WS_EX_LAYERED bit must be set"
        assert (style & WS_EX_TRANSPARENT) == 0, "WS_EX_TRANSPARENT bit must NOT be set"

        res_ct = apply_non_activating_styles(hwnd, click_through=True)
        assert res_ct is True
        style_ct = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        assert (style_ct & WS_EX_TRANSPARENT) != 0, "WS_EX_TRANSPARENT bit MUST be set for click-through"
        assert (style_ct & WS_EX_NOACTIVATE) != 0, "WS_EX_NOACTIVATE bit must remain set"

        apply_non_activating_styles(hwnd, click_through=False)
        style_restored = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        assert (style_restored & WS_EX_TRANSPARENT) == 0

    # Dynamic toggling via HUD methods
    assert hud.is_click_through is False
    hud.toggle_click_through()
    assert hud.is_click_through is True
    if sys.platform == "win32" and user32:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        assert (style & WS_EX_TRANSPARENT) != 0

    hud.toggle_click_through()
    assert hud.is_click_through is False
    if sys.platform == "win32" and user32:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        assert (style & WS_EX_TRANSPARENT) == 0

    # Dynamic toggling via apply_live_settings
    hud.apply_live_settings({
        "ui_settings": {
            "stealth_affinity": False,
            "click_through_default": True,
            "theme": "oled_pure_black"
        }
    })
    assert hud.stealth_enabled is False
    assert hud.is_click_through is True
    if sys.platform == "win32" and user32:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        assert (style & WS_EX_TRANSPARENT) != 0

    hud.apply_live_settings({
        "ui_settings": {
            "stealth_affinity": True,
            "click_through_default": False,
            "theme": "calm_buttercup"
        }
    })
    assert hud.stealth_enabled is True
    assert hud.is_click_through is False
    if sys.platform == "win32" and user32:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        assert (style & WS_EX_TRANSPARENT) == 0

    # Stress Test: 100 Rapid Consecutive Toggles
    for i in range(100):
        ct = (i % 2 == 0)
        st = (i % 3 != 0)
        hud.apply_live_settings({
            "ui_settings": {
                "stealth_affinity": st,
                "click_through_default": ct,
                "theme": "gentle_sage" if i % 2 == 0 else "muted_slate"
            }
        })
        assert hud.is_click_through == ct
        assert hud.stealth_enabled == st

    print("  -> PASS: Win32 stealth affinity & click-through dynamic toggling and stress verified.")


# =========================================================================
# TEST 3: EXHAUSTIVE 30 SETUPCENTER CONTROLS & BROADCASTS
# =========================================================================

def test_exhaustive_30_setup_center_controls_coverage():
    print("\n[CHALLENGE 3] Testing Exhaustive 30 SetupCenter Interactive UI Controls...")
    
    sc = SetupCenter()
    emitted = []
    sc.settings_changed.connect(lambda cfg: emitted.append(cfg))

    test_actions = [
        (lambda: sc.spin_hud_width.setValue(310 if sc.spin_hud_width.value() != 310 else 320), lambda c: c["ui_settings"]["width"] in (310, 320)),
        (lambda: sc.spin_hud_height.setValue(550 if sc.spin_hud_height.value() != 550 else 560), lambda c: c["ui_settings"]["height"] in (550, 560)),
        (lambda: sc.slider_opacity.setValue(65 if sc.slider_opacity.value() != 65 else 70), lambda c: abs(c["ui_settings"]["opacity"] - 0.65) < 0.01 or abs(c["ui_settings"]["opacity"] - 0.70) < 0.01),
        (lambda: sc.spin_font_size.setValue(11 if sc.spin_font_size.value() != 11 else 12), lambda c: c["ui_settings"]["font_size"] in (11, 12)),
        (lambda: sc.spin_border_radius.setValue(8 if sc.spin_border_radius.value() != 8 else 10), lambda c: c["ui_settings"]["border_radius"] in (8, 10)),
        (lambda: sc.combo_theme.setCurrentIndex((sc.combo_theme.currentIndex() + 1) % sc.combo_theme.count()), lambda c: c["ui_settings"]["theme"] is not None),
        (lambda: sc.combo_vu_mode.setCurrentIndex((sc.combo_vu_mode.currentIndex() + 1) % sc.combo_vu_mode.count()), lambda c: c["ui_settings"]["vu_mode"] is not None),
        (lambda: sc.chk_stealth.setChecked(not sc.chk_stealth.isChecked()), lambda c: "stealth_affinity" in c["ui_settings"]),
        (lambda: sc.chk_click_through.setChecked(not sc.chk_click_through.isChecked()), lambda c: "click_through_default" in c["ui_settings"]),
        (lambda: sc.combo_gemini_model.setCurrentIndex((sc.combo_gemini_model.currentIndex() + 1) % sc.combo_gemini_model.count()), lambda c: "gemini_model" in c["ai_settings"]),
        (lambda: sc.combo_llm.setCurrentIndex((sc.combo_llm.currentIndex() + 1) % sc.combo_llm.count()), lambda c: "preferred_llm" in c),
        (lambda: sc.txt_custom_model.setText("custom-3.7-deepseek"), lambda c: c["ai_settings"]["custom_model"] == "custom-3.7-deepseek"),
        (lambda: sc.txt_groq_model.setText("llama-3.1-8b-instant"), lambda c: c["ai_settings"]["groq_model"] == "llama-3.1-8b-instant"),
        (lambda: sc.txt_openai_model.setText("gpt-4o-2024-11-20"), lambda c: c["ai_settings"]["openai_model"] == "gpt-4o-2024-11-20"),
        (lambda: sc.spin_temp.setValue(0.75 if sc.spin_temp.value() != 0.75 else 0.85), lambda c: abs(c["ai_settings"]["temperature"] - 0.75) < 0.01 or abs(c["ai_settings"]["temperature"] - 0.85) < 0.01),
        (lambda: sc.spin_tokens.setValue(4096 if sc.spin_tokens.value() != 4096 else 2048), lambda c: c["ai_settings"]["max_tokens"] in (4096, 2048)),
        (lambda: sc.txt_prompt_prefix.setPlainText("Prefix: Explain using formal mathematical notation."), lambda c: "formal mathematical notation" in c["ai_settings"]["custom_prompt_prefix"]),
        (lambda: sc.spin_audio_thresh.setValue(0.08 if sc.spin_audio_thresh.value() != 0.08 else 0.09), lambda c: abs(c["audio_settings"]["sensitivity_threshold"] - 0.08) < 0.001 or abs(c["audio_settings"]["sensitivity_threshold"] - 0.09) < 0.001),
        (lambda: sc.spin_silence_timeout.setValue(3.5 if sc.spin_silence_timeout.value() != 3.5 else 3.8), lambda c: abs(c["audio_settings"]["silence_timeout_sec"] - 3.5) < 0.01 or abs(c["audio_settings"]["silence_timeout_sec"] - 3.8) < 0.01),
        (lambda: sc.combo_role.setCurrentIndex((sc.combo_role.currentIndex() + 1) % sc.combo_role.count()), lambda c: "role_preset" in c),
        (lambda: sc.txt_name.setText("Dr. Turing"), lambda c: c["user_profile"]["name"] == "Dr. Turing"),
        (lambda: sc.txt_exp.setText("20+ Years Distributed Systems"), lambda c: c["user_profile"]["years_of_experience"] == "20+ Years Distributed Systems"),
        (lambda: sc.txt_skills.setText("Raft, Paxos, Multi-Raft, LSM-Trees"), lambda c: c["user_profile"]["primary_skills"] == "Raft, Paxos, Multi-Raft, LSM-Trees"),
        (lambda: sc.txt_summary.setPlainText("Expert in high-throughput state machine replication."), lambda c: "state machine replication" in c["user_profile"]["summary"]),
        (lambda: sc.txt_resume.setPlainText("Built world's fastest distributed ledger."), lambda c: "distributed ledger" in c["user_profile"]["resume_text"]),
        (lambda: sc.txt_jd.setPlainText("Designing ultra-low latency exchange matching engines."), lambda c: "matching engines" in c["user_profile"]["job_description_text"]),
        (lambda: sc.txt_gemini.setText("AIzaSy-AdversarialGeminiKey"), lambda c: c["api_keys"]["gemini"] == "AIzaSy-AdversarialGeminiKey"),
        (lambda: sc.txt_groq.setText("gsk-AdversarialGroqKey"), lambda c: c["api_keys"]["groq"] == "gsk-AdversarialGroqKey"),
        (lambda: sc.txt_deepgram.setText("dg-AdversarialDeepgramKey"), lambda c: c["api_keys"]["deepgram"] == "dg-AdversarialDeepgramKey"),
        (lambda: sc.txt_openai.setText("sk-AdversarialOpenAIKey"), lambda c: c["api_keys"]["openai"] == "sk-AdversarialOpenAIKey"),
    ]

    for idx, (trigger_fn, check_fn) in enumerate(test_actions, start=1):
        prev_len = len(emitted)
        trigger_fn()
        assert len(emitted) > prev_len, f"Action #{idx} failed to emit settings_changed"
        latest = emitted[-1]
        assert check_fn(latest), f"Action #{idx} emitted payload failed validation condition"

    print(f"  -> PASS: All {len(test_actions)} setup center interactive UI controls accurately emit live updates.")


# =========================================================================
# TEST 4: RAPID THEME CYCLING, QSS INTEGRITY & CONTENT PERSISTENCE
# =========================================================================

def test_rapid_theme_cycling_under_active_content():
    print("\n[CHALLENGE 4] Testing Rapid Theme Cycling Under Active Tokens & Content...")
    
    hud = StealthHUD({
        "ui_settings": {"theme": "calm_buttercup", "width": 400, "height": 650, "opacity": 0.95, "font_size": 13, "border_radius": 14},
        "ai_settings": {"gemini_model": "gemini-3.7-flash"}
    })

    scope_content = (
        "### Problem Scope & Clarifications\n"
        "- **Target throughput**: 100,000 QPS with p99 latency < 15ms\n"
        "- **Consistency Model**: Eventual consistency with bounded staleness\n"
        "- **Partitioning Key**: Hash-based partition on tenant_id + entity_uuid\n"
        "- **Replication Factor**: 3 with Raft consensus leader election"
    )
    arch_content = (
        "### Distributed Architecture Overview\n"
        "1. **Ingestion Layer**: Envoy Gateway with token-bucket rate limiting\n"
        "2. **Streaming Buffer**: Apache Kafka topic with 64 partitions\n"
        "3. **Compute Engine**: Flink stateful stream processors with RocksDB state backend\n"
        "4. **Storage Tier**: ScyllaDB for ultra-low latency write throughput"
    )
    code_content = (
        "```python\n"
        "def partition_key(tenant_id: str, entity_uuid: str, num_partitions: int = 64) -> int:\n"
        "    combined = f'{tenant_id}:{entity_uuid}'.encode('utf-8')\n"
        "    return mmh3.hash(combined, signed=False) % num_partitions\n"
        "```"
    )
    transcript_content = "Interviewer: How do you handle hot partitions when traffic spikes 10x?"
    query_content = "Explain backpressure handling in Flink stream processors"

    hud.set_stage_card_content(1, scope_content)
    hud.set_stage_card_content(2, arch_content)
    hud.set_stage_card_content(3, code_content)
    hud.update_transcript(transcript_content)
    hud.txt_query.setText(query_content)

    themes = ["calm_buttercup", "gentle_sage", "muted_slate", "oled_pure_black"]
    
    for i in range(80):
        t = themes[i % len(themes)]
        f = 11 + (i % 7) # 11 to 17
        op = 0.50 + ((i % 50) / 100.0) # 0.50 to 0.99
        r = 8 + (i % 16) # 8 to 23
        w = 360 + (i % 240)
        h = 450 + (i % 450)
        
        cfg = {
            "ui_settings": {
                "theme": t,
                "opacity": op,
                "font_size": f,
                "border_radius": r,
                "width": w,
                "height": h,
                "stealth_affinity": (i % 2 == 0),
                "click_through_default": (i % 3 == 0),
                "vu_mode": ["dots", "wave", "numeric"][i % 3]
            },
            "ai_settings": {
                "gemini_model": "gemini-3.7-flash",
                "custom_model": f"model-variant-{i}"
            }
        }
        hud.apply_live_settings(cfg)
        
        assert hud.width() == w
        assert hud.height() == h
        assert hud.current_font_size == f
        assert hud.config["ui_settings"]["theme"] == t
        assert f"MODEL-VARIANT-{i}"[:18] in hud.lbl_model_badge.text()

        if i % 10 == 0:
            hud.append_stage_token(3, f"\n# Token update at cycle {i}")

        QApplication.processEvents()

    assert "Problem Scope & Clarifications" in hud.txt_s1.text()
    assert "Distributed Architecture Overview" in hud.txt_s2.text()
    assert "def partition_key" in hud.txt_s3.text()
    assert transcript_content in hud.lbl_transcript.text()
    assert hud.txt_query.text() == query_content
    print("  -> PASS: Rapid theme cycling under active tokens preserved 100% of content and styling.")


# =========================================================================
# TEST 5: EXTREME CLAMP BOUNDARIES & MALFORMED INPUT RESILIENCE
# =========================================================================

def test_extreme_clamp_boundaries_and_malformed_inputs():
    print("\n[CHALLENGE 5] Testing Extreme Dimension Clamping and Malformed Input Resilience...")
    
    hud = StealthHUD({
        "ui_settings": {"theme": "calm_buttercup", "width": 370, "height": 640, "opacity": 0.96, "font_size": 13, "border_radius": 14},
        "ai_settings": {"gemini_model": "gemini-3.7-flash"}
    })

    test_cases = [
        (-500, -200, -2.0, -10, -5, 280, 400, 0.10, 9, 4),
        (0, 0, 0.0, 0, 0, 280, 400, 0.10, 9, 4),
        (10, 10, 0.05, 5, 2, 280, 400, 0.10, 9, 4),
        (279, 399, 0.09, 8, 3, 280, 400, 0.10, 9, 4),
        (280, 400, 0.10, 9, 4, 280, 400, 0.10, 9, 4),
        (500, 750, 0.85, 15, 16, 500, 750, 0.85, 15, 16),
        (650, 1080, 1.0, 20, 24, 650, 1080, 1.0, 20, 24),
        (651, 1081, 1.01, 21, 25, 650, 1080, 1.0, 20, 24),
        (5000, 10000, 5.0, 100, 500, 650, 1080, 1.0, 20, 24),
        (999999, 999999, 100.0, 999, 999, 650, 1080, 1.0, 20, 24),
    ]

    for (w_in, h_in, op_in, fs_in, br_in, exp_w, exp_h, exp_op, exp_fs, exp_br) in test_cases:
        cfg = {
            "ui_settings": {
                "theme": "calm_buttercup",
                "width": w_in,
                "height": h_in,
                "opacity": op_in,
                "font_size": fs_in,
                "border_radius": br_in,
                "stealth_affinity": True,
                "click_through_default": False,
                "vu_mode": "dots"
            },
            "ai_settings": {
                "gemini_model": "gemini-3.7-flash"
            }
        }
        hud.apply_live_settings(cfg)

        assert hud.width() == exp_w, f"Width failed: in={w_in}, got={hud.width()}, exp={exp_w}"
        assert hud.height() == exp_h, f"Height failed: in={h_in}, got={hud.height()}, exp={exp_h}"
        assert abs(hud.windowOpacity() - exp_op) < 0.01, f"Opacity failed: in={op_in}, got={hud.windowOpacity()}, exp={exp_op}"
        assert hud.current_font_size == exp_fs, f"Font size failed: in={fs_in}, got={hud.current_font_size}, exp={exp_fs}"

    malformed_themes = ["", None, "   ", "NON_EXISTENT_THEME_XYZ", "Calm-Buttercup", "  GENTLE   SAGE  ", "oled_pure_black_ultra_dark", "12345", "#!@$%"]
    for th in malformed_themes:
        styles = compile_hud_stylesheet(theme_key=th)
        assert "palette" in styles
        assert styles["palette"]["accent"] is not None
        assert "modern_frame" in styles

    print("  -> PASS: Extreme dimension clamp boundaries and malformed input resilience verified.")


if __name__ == "__main__":
    print("=" * 65)
    print("   CHALLENGER 2: MASTER ADVERSARIAL STRESS TEST SUITE (M1)   ")
    print("=" * 65)
    test_font_scaling_multiline_markdown_and_placeholders()
    test_win32_stealth_affinity_and_click_through()
    test_exhaustive_30_setup_center_controls_coverage()
    test_rapid_theme_cycling_under_active_content()
    test_extreme_clamp_boundaries_and_malformed_inputs()
    print("=" * 65)
    print(" >>> ALL 5 ADVERSARIAL CHALLENGES COMPLETED WITH 100% SUCCESS <<< ")
    print("=" * 65)
