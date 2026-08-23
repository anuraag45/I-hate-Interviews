# Original User Request

## 2026-08-17T13:42:00Z

Comprehensive end-to-end production overhaul of MeetingCopilot AI to fix all non-functional UI states, establish real-time dynamic synchronization between the Dashboard and the Presenter HUD, ensure all buttons and text inputs are 100% interactive and responsive, and deliver a rock-solid Gemini 3.7/3.6/2.5 streaming intelligence experience.

Working directory: c:/Users/anura/OneDrive/Desktop/cheat
Integrity mode: development

## Requirements

### R1. Real-Time Dynamic Dashboard-to-HUD Synchronization
- When the user modifies ANY setting in the Setup Dashboard (theme, colors, opacity, width/height, font size, border radius, model selection), the changes must dynamically and immediately reflect on the live HUD in real-time without requiring application restarts or reopening windows.

### R2. 100% Interactive HUD Click Handlers & Input Dispatch
- All buttons on the HUD (Smart Next, Scope, Arch, Code, Snip, Clear, Font A+/A-, Ghost toggle, Close) and the Quick Query text input box must receive clicks, give immediate visual feedback (active states, live status badges), and trigger the AI generation pipeline with live streaming tokens.
- Fix Win32 window styles so mouse clicks are cleanly processed by Qt widgets while preserving screen-share capture exclusion (WDA_EXCLUDEFROMCAPTURE 0x11) and optional ghost click-through mode (WS_EX_TRANSPARENT).

### R3. Flawless AI Pipeline & Multimodal Vision Execution
- Full integration with Gemini 3.7 Flash, 3.6 Flash, 2.5 Flash, 2.5 Flash-Lite, 2.5 Pro, and Groq Llama 3.3 for both text questions and screen snip queries with live token streaming and error recovery.
- When the user types or speaks a question, tokens must stream live directly into the stage cards with a live status badge (🟢 Ready ➔ 🟡 Generating... ➔ ⚡ Streaming Tokens ➔ ✓ Complete).

### R4. Polished Modern Consumer-Tech UI
- Clean, calm visual design inspired by modern consumer tech (soft warm buttercup #F6D860, gentle sage #38A169, elevated navy slate #181C26 / #1E2332).
- 3-step live stage progress tracker ([ 🟡 1. Scope ] ➔ [ 🟢 2. Arch ] ➔ [ 🚀 3. Code ]), multi-mode audio VU equalizer (Dots, Wave, Meter), and 1-click focus-safe clipboard copy with animated feedback.

## Acceptance Criteria

### Live Responsiveness & Interactivity
- [ ] Modifying HUD width, height, opacity, font size, or theme in the Dashboard instantly updates the active HUD window geometry and stylesheet without restart.
- [ ] Clicking any stage button or sending a query from the HUD input box immediately transitions the status badge to streaming and displays generated tokens in real time.
- [ ] No dummy static placeholder text; clean ready states with interactive action cues.
- [ ] Screen snip captures the active presentation slide and triggers Gemini Vision analysis.
- [ ] The automated test suite (python test_suite.py) passes 100% with no regressions.
