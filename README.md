# 😤 I Hate Interviews — Real-Time Live Copilot For Crushing Tech Calls

> [!WARNING]
> ### 🚧 ACTIVE DEVELOPMENT & EXPERIMENTAL PREVIEW 🚧
> **This project is currently under heavy active development.** Features, UI modules, audio drivers, and model routing pipelines are being rapidly shipped and battle-tested. Expect frequent updates, experimental improvements, and new superpowers. Star & watch the repo to stay updated!

> *"Look, let's keep it 100 — technical interviews are cooked. We got you locked in. No cap, straight heat, zero sweat."*

**I Hate Interviews** is the ultimate ultra-low-latency, invisible Windows wingman built so you can breeze through technical interviews, live coding rounds, and system design grillings without breaking a sweat.

---

## 🔥 Why This Tool Hits Different

1. **Ghost Stealth Mode (Invisible on Screen Shares)**:
   - Uses low-level Windows API `SetWindowDisplayAffinity(hwnd, 0x00000011)` (`WDA_EXCLUDEFROMCAPTURE`).
   - The HUD floats on your physical screen, but Zoom, Microsoft Teams, Google Meet, Discord, and OBS see **absolutely nothing**. Pure stealth.
2. **Straight-to-the-Point Answers (Zero Fluff, 100% Signal)**:
   - No lengthy bedtime stories or unsolicited essays. 
   - Instant, 2-second glanceable bullet points with bold key takeaways and optimal complexities ($O(N)$).
3. **Prod-Grade Code on Lock**:
   - Spits clean, typed, idiomatic production snippets with boundary checks.
   - 1-click focus-safe copy with an expandable/collapsible code drawer.
4. **Dual Ear Live Listening (Mic + Interviewer Audio)**:
   - Listens to **both** your microphone and the interviewer's voice over Zoom/Teams/Meet in real time.
   - Free built-in speech recognition with automatic Voice Activity Detection (VAD) — when they ask a question, the solution drops automatically without you touching a single key.
5. **Locked-Down Bank-Grade Security (Windows DPAPI)**:
   - Your Google Gemini API keys are encrypted at rest using Windows DPAPI, cryptographically tied strictly to your user profile.
6. **Mobile Teleprompter Companion**:
   - Scan the QR code with your phone, prop it right below your webcam, and maintain 100% natural eye contact with zero eye wandering.
7. **Zero Shortcut Clashes**:
   - All global triggers are mapped to `Ctrl + Alt + ...` so you never accidentally mute yourself or drop video on Zoom/Teams/Meet.

---

## ⚡ Quick Start (Get In The Game)

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Run the App
```powershell
python run.py
```

### 3. Set Your Keys & Roll
- Drop in your **Google Gemini API Key** (Gemini 3.8 / 3.7 / 3.6 / 2.5 series) in the Control Hub.
- Hit **🚀 Launch Presenter HUD** and you're good to go.


---

## ⌨️ Controller Bindings (Global Hotkeys)

| Hotkey | Action | What It Does |
| :--- | :--- | :--- |
| **`Ctrl + Alt + Q`** | **Instant QA Solve** | Immediately generates the direct answer + code for the active topic. |
| **`Ctrl + Alt + S`** | **Screen Snip & Solve** | Silently snips the active problem/slide and drops the solution. |
| **`Ctrl + Alt + H`** | **Ghost HUD Toggle** | Instantly pops the HUD in or out of view. |
| **`Ctrl + Alt + T`** | **Click-Through Toggle** | Clicks pass right through the HUD to whatever window is behind it. |
| **`Ctrl + Alt + C`** | **Wipe Clean** | Clears the transcript and cards for the next question. |

---

## 📱 Phone Teleprompter Setup

1. Make sure your phone is on the same Wi-Fi.
2. In the **Mobile Teleprompter** tab, scan the QR code.
3. Prop your phone up under your camera and read your notes with natural eye contact.
4. *Strict Corporate Wi-Fi Fallback*: Plug in USB, run:
   ```bash
   adb reverse tcp:8000 tcp:8000
   ```
   and open `http://localhost:8000` on your mobile browser.

---

## 🧪 Battle-Tested Verification

Run the full automated test suite to ensure all engines are running 100%:
```powershell
python test_suite.py
```
