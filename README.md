# 🎙️ MeetingCopilot AI - Real-Time Presentation & Meeting Assistant

**MeetingCopilot AI** is an ultra-low-latency, multi-process Windows assistant designed for technical presentations, system design reviews, webinars, live coding walkthroughs, and client discussions.

---

## ⚡ Core Architecture & Guarantees

1. **Presenter-Display Window Exclusion (`WDA_EXCLUDEFROMCAPTURE`)**:
   - Uses Windows Win32 API `SetWindowDisplayAffinity(hwnd, 0x00000011)` (`WDA_EXCLUDEFROMCAPTURE`).
   - Speaker notes and HUD controls are rendered locally on your physical screen but remain **completely invisible** to audience screen shares on Zoom, Microsoft Teams, Google Meet, Discord, and OBS.
2. **Bank-Grade Credential Protection (Windows DPAPI)**:
   - All stored API keys (Gemini, Groq, Deepgram, OpenAI) are encrypted at rest using Windows Data Protection API (`CryptProtectData`), cryptographically tied strictly to your current Windows User SID.
3. **Streamlined Direct QA & Production Code Engine**:
   - Fast, high-accuracy answers designed for a 2-second glance (zero conversational fluff, zero unsolicited architecture dumps).
   - Clean, production-grade code snippets with proper typing, boundary checks, and $O(N)$ time/space complexity analysis.
4. **Collapsible Section Card Layout**:
   - **Section 1: 💬 Direct Answer & Key Points**: Direct concise takeaways.
   - **Section 2: 💻 Production Code Panel**: Collapsible accordion with `[▲ / ▼ Code]` toggle and 1-click focus-safe copy.
5. **Dual Audio Stream Capture & Universal Speech-To-Text**:
   - Captures **both** your Microphone (headset/mic) and System Audio (WASAPI loopback from Zoom/Teams/Meet).
   - Dual-mode STT: Ultra-fast Deepgram Nova-2 WebSocket or built-in free Google Speech Recognition with Voice Activity Detection (VAD).
   - Voice-to-Solution Auto-Trigger: Speaking a question automatically streams the solution without touching a key.
6. **Ephemeral Token-Authenticated Mobile Companion**:
   - Built-in local WebSocket server with token authentication (`/ws?token=...`).
   - Scan the on-screen QR code from your phone and place it directly below your webcam for 100% natural eye contact with zero horizontal eye saccades.
7. **Hardware-Accelerated Slide / Code Snip (`Ctrl+Alt+S`)**:
   - Silent capture of the active window using `PrintWindow(..., 0x2)` + Adaptive Contrast boost and WebP compression ($<250\text{ KB}$) for sub-150ms Gemini 2.5/3.7 Vision analysis.
8. **Zero Meeting App Shortcut Conflicts**:
   - All global shortcuts use `Ctrl + Alt + ...` to prevent collisions with Zoom, Teams, or Google Meet defaults.

---

## 🚀 Quick Start

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Launch the Application
```powershell
python run.py
```

### 3. Configure Your Profile & API Keys in Setup Center
- **API Keys**: Enter your **Google Gemini API Key** (Gemini 3.7 / 3.6 / 2.5 Flash) and/or **Deepgram Nova-2** key.
- **Preset**: Select your presentation preset or paste custom talking points.
- Click **🚀 Launch Live Presenter HUD**.

---

## ⌨️ Global Presenter Hotkeys

| Hotkey | Action | Description |
| :--- | :--- | :--- |
| **`Ctrl + Alt + Q`** | **Direct QA Solve** | Solves currently transcribed or typed technical question. |
| **`Ctrl + Alt + S`** | **Slide Snip & Solve** | Instantly captures active presentation window and streams Gemini Vision analysis. |
| **`Ctrl + Alt + H`** | **Visibility Toggle** | Instantly shows/hides the floating desktop HUD. |
| **`Ctrl + Alt + T`** | **Click-Through Toggle** | Toggles click-through mode (clicks pass directly through to slide deck). |
| **`Ctrl + Alt + C`** | **Clear Overlay** | Clears active transcript buffer and Q&A content. |

---

## 📱 Mobile Pairing

1. Ensure your phone is connected to the same Wi-Fi network as your laptop.
2. In the **Mobile Teleprompter** tab of the Setup Center, scan the displayed QR code.
3. Place your phone propped up directly below your laptop screen/webcam for natural eye contact.
4. *Isolated Wi-Fi Fallback*: Connect via USB and run:
   ```bash
   adb reverse tcp:8000 tcp:8000
   ```
   then open `http://localhost:8000` on your mobile browser.

---

## 🧪 Verification & Testing

To run the full automated verification test suite:
```powershell
python test_suite.py
```
