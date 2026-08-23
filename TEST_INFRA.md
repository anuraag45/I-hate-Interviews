# E2E Test Infra: MeetingCopilot AI

## Test Philosophy
- Requirement-driven, high-fidelity verification derived from `ORIGINAL_REQUEST.md`.
- Verifies UI interactivity, Win32 window flags, live synchronization, multi-model AI streaming, vision processing, audio VU metering, and test suite execution.

## Feature Inventory Mapping
| # | Feature | Source (Requirement) | Tier 1 (Feature Coverage) | Tier 2 (Boundary & Corner) | Tier 3 (Cross-Feature) | Tier 4 (Real-World) |
|---|---------|----------------------|:-------------------------:|:--------------------------:|:----------------------:|:-------------------:|
| 1 | Real-Time Live Sync | R1, ORIGINAL_REQUEST §R1 | 5 | 5 | ✓ | ✓ |
| 2 | HUD Theme & Alpha Compiler | R1, R4 | 5 | 5 | ✓ | ✓ |
| 3 | HUD Geometry & Property Sync | R1 | 5 | 5 | ✓ | ✓ |
| 4 | Click-Through & Win32 Interactivity | R2 | 5 | 5 | ✓ | ✓ |
| 5 | Interactive Button & Input Dispatch | R2 | 5 | 5 | ✓ | ✓ |
| 6 | Status Badge Transition Engine | R2, R3 | 5 | 5 | ✓ | ✓ |
| 7 | Stage Streaming & Placeholder Cleanup | R2, R3 | 5 | 5 | ✓ | ✓ |
| 8 | Multi-Model Gemini & Groq Streaming | R3 | 5 | 5 | ✓ | ✓ |
| 9 | Multimodal Vision Slide Capture & Solver | R3 | 5 | 5 | ✓ | ✓ |
| 10 | Multi-Mode Audio VU Equalizer | R4 | 5 | 5 | ✓ | ✓ |
| 11 | Polished UI & 3-Step Tracker | R4 | 5 | 5 | ✓ | ✓ |
| 12 | Automated Verification & Test Suite | Acceptance Criteria | 5 | 5 | ✓ | ✓ |

## Test Architecture
- Test Runner: `test_suite.py` + dedicated milestone verification scripts.
- Execution:
  ```powershell
  & "C:\Users\anura\AppData\Local\Programs\Python\Python314\python.exe" test_suite.py
  ```
- Pass/Fail Criteria: All 8 core suites + expanded coverage suites pass with exit code 0 and 0 regressions.

## Real-World Application Scenarios (Tier 4)
1. **Live Interview Session Scenario**: User configures presenter profile in SetupCenter, adjusts HUD size/opacity on the fly, speaks interview problem, audio VU pulses, Deepgram captures transcript, Gemini 3.7 streams Stage 1 Scope, Stage 2 Arch, and Stage 3 Code, user clicks copy button to copy code.
2. **Screen Snip Coding Scenario**: User presents code slide, clicks `[📷 Snip]`, system captures DWM window, pre-processes CLAHE/WebP (<250KB), sends to Gemini Vision, tokens stream into Stage 3 card.
3. **Live Theme & Customization Scenario**: User switches between Warm Buttercup, Gentle Sage, Muted Slate, and OLED Black while adjusting opacity and border radius; HUD elements update instantly without reload.
4. **Offline / Resilience Scenario**: Network glitch or missing API keys trigger simulated dynamic preview streams, circuit breakers trip safely without UI freezes.
5. **Ghost Mode & Click-Through Scenario**: User toggles Ghost mode (`Alt+T` or button); clicks fall through to underlying presentation; toggling back restores full clickability.
