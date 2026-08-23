# Project: MeetingCopilot AI Production Overhaul

## Architecture
MeetingCopilot AI is an ultra-low-latency, real-time AI assistant for live presentations, interviews, and coding sessions.
The architecture comprises:
- **Presentation HUD (`gui/stealth_hud.py`)**: A non-activating, screen-share-excluded (via `WDA_EXCLUDEFROMCAPTURE`) transparent desktop overlay with 3-step stage cards, audio VU meter, model badges, and interactive controls.
- **Setup Dashboard (`gui/setup_center.py`)**: A comprehensive configuration hub with live signal emission (`settings_changed`) for instant dynamic sync to the HUD without restarts.
- **Application Controller (`run.py`)**: Orchestrates the HUD, Dashboard, System Tray, Global Hotkeys, Audio Worker Process, and LLM Orchestrator.
- **AI Engine (`engine/llm_orchestrator.py`, `engine/prompt_templates.py`, `engine/rate_limiter.py`)**: Multi-provider streaming engine supporting Gemini 3.7 Flash, 3.6 Flash, 2.5 Flash, 2.5 Flash-Lite, 2.5 Pro, and Groq Llama 3.3 with rate limiting and circuit breakers.
- **Multimodal Vision (`engine/vision_capture.py`)**: Screen snip capture using Win32 DWM bounds, hybrid `PrintWindow(0x2)` + ImageGrab, CLAHE contrast enhancement, and WebP compression (<250 KB) for Gemini Vision.
- **Audio DSP & Shared Memory (`engine/audio_worker.py`, `engine/shared_audio_ring.py`)**: Polyphase 48kHz->16kHz decimation, logarithmic dBFS calculation (-60.0 to 0.0 dBFS), and lock-free atomic SPSC shared memory ring buffer.
- **Stealth & OS Integration (`stealth/win32_affinity.py`, `stealth/win32_hotkeys.py`)**: Win32 window display affinity, `WS_EX_NOACTIVATE`, `WS_EX_LAYERED`, `WS_EX_TRANSPARENT` (ghost mode toggle), and low-level keyboard hooks.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| F1 | Real-Time Live Sync Signal Wiring | Connect all 25 SetupCenter UI inputs (models, themes, dimensions, sliders, profile, keys) to `_emit_live_change()` | M1 | R1, Explorer 2 |
| F2 | Centralized HUD Theme & Alpha Compiler | Unified `compile_hud_stylesheet()` supporting 4 color palettes (`calm_buttercup`, `gentle_sage`, `muted_slate`, `oled_pure_black`) with proper alpha blending and proportional corner radii | M1 | R1, R4, Explorer 2 |
| F3 | Dynamic HUD Geometry & Property Sync | `StealthHUD.apply_live_settings()` updates size, opacity, font size, theme, and model badge instantly without window recreation or flicker | M1 | R1, Explorer 2 |
| F4 | Click-Through Default & Win32 Interactivity | Default `"click_through_default": false` in `config.json`, dynamic `apply_non_activating_styles` and `apply_stealth_affinity` on live sync, and ghost toggle sync | M2 | R2, Explorer 1 |
| F5 | 100% Interactive HUD Button & Input Dispatch | Full `:hover` and `:pressed` visual feedback, active state cues, and focus handling on Quick Query `QLineEdit` under `WS_EX_NOACTIVATE` | M2 | R2, Explorer 1 |
| F6 | Status Badge Transition Engine | Clean transitions (`🟢 Ready` ➔ `🟡 Generating...` ➔ `⚡ Streaming Tokens` ➔ `✓ Complete` / `✓ Copied Code!`) without race conditions or premature reset | M2 | R2, R3, Explorer 1 |
| F7 | Stage Streaming & Placeholder Cleanup | Fix token concatenation bug after clearing, support Stage 4 (Glance) streaming, and clean ready state action cues | M2 | R2, R3, Explorer 1 |
| F8 | Multi-Model Gemini & Groq Streaming Engine | Support Gemini 3.7 Flash, 3.6 Flash, 2.5 Flash, 2.5 Flash-Lite, 2.5 Pro, and Groq Llama 3.3 with SDK/REST fallback, circuit breakers, and rate limiters | M3 | R3, Explorer 3 |
| F9 | Multimodal Vision Slide Capture & Solver | Hybrid Win32 capture, CLAHE contrast boost, WebP compression (<250 KB), and Gemini Vision streaming directly to Stage 3 Code Card | M3 | R3, Explorer 3 |
| F10 | Multi-Mode Audio VU Equalizer | 3 equalizer modes (Dots, Wave/Braille, Meter/dBFS) running at 25 Hz over SPSC atomic shared memory ring buffer | M4 | R4, Explorer 3 |
| F11 | Polished Modern Consumer-Tech UI & 3-Step Tracker | Soft warm buttercup (#F6D860), gentle sage (#38A169), navy slate (#181C26/#1E2332), 3-step stage progress tracker, and 1-click clipboard copy with animation | M4 | R4, Explorer 1, 2, 3 |
| F12 | Automated Verification & E2E Test Suite | 100% pass on `test_suite.py` (8 core test suites + comprehensive integration suites) covering all requirements with zero regressions | M5 | Acceptance, Explorer 3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Dynamic Sync & Theming Architecture | Wire all 25 SetupCenter signals, implement centralized `compile_hud_stylesheet()` for 4 palettes, and dynamic `apply_live_settings()` | none | PLANNED |
| M2 | HUD Interactivity, Win32 Styles & Status Engine | Fix click-through default in `config.json`, Win32 live style re-application, status badge state machine, placeholder text clearing, Stage 4 streaming, and QLineEdit focus | M1 | PLANNED |
| M3 | AI Pipeline, Multimodal Vision & Streaming Engine | Verify and solidify Gemini 3.7/3.6/2.5 Flash & Pro, Groq Llama 3.3, REST SSE fallback, vision snip preprocessing, and token streaming | M1, M2 | PLANNED |
| M4 | Polished Modern UI, Stage Tracker & VU Equalizer | 3-step stage tracker ([1. Scope] ➔ [2. Arch] ➔ [3. Code]), Dots/Wave/Meter VU visualizer, animated copy feedback, and button hover/active polish | M1, M2, M3 | PLANNED |
| M5 | E2E Test Suite Verification & Coverage Hardening | Run complete `test_suite.py`, perform adversarial testing, verify 100% pass on all test tiers, and achieve forensic audit signoff | M1, M2, M3, M4 | PLANNED |

## Interface Contracts
### `SetupCenter` (`gui/setup_center.py`) ↔ `ApplicationController` (`run.py`) ↔ `StealthHUD` (`gui/stealth_hud.py`)
- Signal: `settings_changed = pyqtSignal(dict)` emitted on any user input change in SetupCenter.
- Handler: `run.py::_on_settings_live_sync(new_config: dict)` updates `LLMOrchestrator` and calls `hud.apply_live_settings(new_config)`.
- Method: `StealthHUD.apply_live_settings(cfg: dict)` executes:
  - `setGeometry(x, y, w, h)` with clamped bounds `(280 <= w <= 650, 400 <= h <= 1080)`.
  - `setWindowOpacity(opacity_float)`.
  - `setStyleSheet(compile_hud_stylesheet(theme_key, border_radius, font_size, opacity))`.
  - `apply_non_activating_styles(hwnd, click_through=is_click_through)`.
  - `apply_stealth_affinity(hwnd, enabled=stealth_enabled)`.
  - Update `lbl_model_badge`, `btn_ghost`, `btn_vu_mode`.

### `LLMOrchestrator` (`engine/llm_orchestrator.py`) ↔ `HUDUpdateSignaler` ↔ `StealthHUD`
- Signal: `stage_token_stream = pyqtSignal(int, str)` emitted during token streaming.
- Signal: `stage_card_complete = pyqtSignal(int, str)` emitted when stage generation completes with full markdown.
- Method: `StealthHUD.append_stage_token(stage: int, token: str)` appends token to target card (Stage 1/4 -> `txt_s1`, Stage 2 -> `txt_s2`, Stage 3 -> `txt_s3`).
- Method: `StealthHUD.set_stage_card_content(stage: int, content: str)` updates card markdown and displays `"✓ Complete"` badge ONLY when `content.strip()` is non-empty.

## Code Layout
- `config.json`: Persistent application settings (DPAPI encrypted API keys, UI settings, AI settings, audio settings).
- `run.py`: Application entry point, controller, tray icon, hotkey registration, worker process lifecycle.
- `gui/stealth_hud.py`: Presenter HUD widget, stage cards, action buttons, status badge, VU meter, stylesheets.
- `gui/setup_center.py`: Setup Dashboard widget, configuration tabs, live sync signals.
- `engine/llm_orchestrator.py`: LLM routing, Gemini SDK/REST streaming, Groq SSE streaming, rate limiting, circuit breaker.
- `engine/prompt_templates.py`: System prompt templates for interview stages and vision solver.
- `engine/vision_capture.py`: Win32 DWM window capture, CLAHE contrast enhancement, WebP compression.
- `engine/audio_worker.py`: WASAPI loopback audio capture, polyphase resampling, dBFS calculation.
- `engine/shared_audio_ring.py`: Atomic SPSC shared memory ring buffer.
- `engine/stage_manager.py`: Interview stage enumeration and progression logic.
- `stealth/win32_affinity.py`: Win32 `SetWindowDisplayAffinity`, `WS_EX_NOACTIVATE`, `WS_EX_TRANSPARENT`.
- `stealth/win32_hotkeys.py`: Win32 global keyboard hooks.
- `test_suite.py`: Comprehensive test runner covering all core modules and subsystems.
