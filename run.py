import asyncio
import ctypes
import json
import multiprocessing
import os
import sys
import threading
import time
import traceback

# Force Working Directory to script folder to prevent UAC CWD shift
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication

from stealth.win32_affinity import init_dpi_awareness
from stealth.win32_hotkeys import (
    Win32HotkeyManager, MOD_CONTROL, MOD_ALT, MOD_SHIFT,
    VK_SPACE, VK_1, VK_2, VK_3, VK_S, VK_H, VK_T, VK_C, VK_Q
)
from stealth.crypto_storage import dpapi_decrypt_string
from engine.audio_worker import run_audio_worker
from engine.stt_deepgram import DeepgramStreamer
from engine.transcript_reconciler import TranscriptReconciler
from engine.stage_manager import StageManager, InterviewStage
from engine.vision_capture import capture_and_preprocess_webp
from engine.llm_orchestrator import LLMOrchestrator
from server.companion_server import start_server_in_thread, threadsafe_broadcast
from gui.stealth_hud import StealthHUD, HUDUpdateSignaler
from gui.setup_center import SetupCenter

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def scrub_sensitive_text(text: str) -> str:
    import re
    text = re.sub(r"(AIza[0-9A-Za-z-_]{35})", "[REDACTED_GEMINI_KEY]", text)
    text = re.sub(r"(gsk_[0-9A-Za-z]{48,})", "[REDACTED_GROQ_KEY]", text)
    text = re.sub(r"(sk-[0-9A-Za-z]{40,})", "[REDACTED_OPENAI_KEY]", text)
    text = re.sub(r"(Token\s+[0-9a-fA-F]{30,})", "Token [REDACTED_DEEPGRAM_KEY]", text)
    return text

def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    err_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    scrubbed = scrub_sensitive_text("".join(err_lines))
    print(f"[CRITICAL UNHANDLED ERROR]\n{scrubbed}", file=sys.stderr)

sys.excepthook = global_exception_handler

def check_admin_privileges() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                keys = cfg.get("api_keys", {})
                for k in ["gemini", "groq", "openai", "deepgram"]:
                    if k in keys:
                        keys[k] = dpapi_decrypt_string(keys[k])
                cfg["api_keys"] = keys
                return cfg
        except Exception as e:
            print(f"[MeetingCopilot] Error loading config: {e}")
    return {}

class MeetingCopilotApp:
    def __init__(self):
        self.config = load_config()
        self.reconciler = TranscriptReconciler()
        self.stage_mgr = StageManager()
        self.llm_orch = LLMOrchestrator(self.config)
        self.hud_signaler = HUDUpdateSignaler()

        self.audio_stop_event = multiprocessing.Event()
        self.audio_process: multiprocessing.Process = None
        self.stt_streamer: DeepgramStreamer = None
        self.hotkey_mgr = Win32HotkeyManager()
        self.async_loop = None

    def start(self):
        init_dpi_awareness()

        port = self.config.get("server_settings", {}).get("port", 8000)
        start_server_in_thread(port=port)
        print(f"[MeetingCopilot] Companion server started at http://127.0.0.1:{port}")

        def run_async_engine():
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)
            self.async_loop.run_forever()

        async_thread = threading.Thread(target=run_async_engine, name="AsyncEngineThread", daemon=True)
        async_thread.start()

        deepgram_key = self.config.get("api_keys", {}).get("deepgram", "")
        self.stt_streamer = DeepgramStreamer(
            api_key=deepgram_key,
            on_interim=self._on_stt_interim,
            on_final=self._on_stt_final,
            on_auto_question_detected=self._on_live_question_detected
        )
        if self.async_loop:
            asyncio.run_coroutine_threadsafe(self.stt_streamer.start(), self.async_loop)

        self.audio_process = multiprocessing.Process(
            target=run_audio_worker,
            args=(self.audio_stop_event, self.config),
            name="MeetingCopilotAudioWorker",
            daemon=True
        )
        self.audio_process.start()

        self._init_hotkeys()

        qt_app = QApplication(sys.argv)
        self.hud = StealthHUD(self.config, signaler=self.hud_signaler)
        self.setup_center = SetupCenter(on_launch_callback=self._on_setup_launch)

        self.setup_center.settings_changed.connect(self._on_settings_live_sync)
        self._connect_hud_action_signals()

        self.setup_center.show()

        try:
            sys.exit(qt_app.exec())
        finally:
            self.cleanup()

    def _on_settings_live_sync(self, new_config: dict):
        self.config = new_config
        self.llm_orch.update_config(new_config)
        if self.stt_streamer:
            dg_key = new_config.get("api_keys", {}).get("deepgram", "")
            self.stt_streamer.update_key(dg_key)
        self.hud.apply_live_settings(new_config)

    def _connect_hud_action_signals(self):
        self.hud_signaler.action_smart_next.connect(self.trigger_smart_next)
        self.hud_signaler.action_stage_1.connect(lambda: self.trigger_stage(1))
        self.hud_signaler.action_stage_2.connect(lambda: self.trigger_stage(2))
        self.hud_signaler.action_stage_3.connect(lambda: self.trigger_stage(3))
        self.hud_signaler.action_vision_snip.connect(self.trigger_vision_solve)
        self.hud_signaler.action_custom_query.connect(self.trigger_custom_query)
        self.hud_signaler.action_simulate_speech.connect(self.trigger_simulated_speech)

    def _init_hotkeys(self):
        # Conflict-Free Hotkeys (Safe from Zoom, Teams, Meet default shortcuts)
        self.hotkey_mgr.add_hotkey(
            hotkey_id=1,
            name="Direct QA Solve",
            primary_mod=MOD_CONTROL | MOD_ALT, primary_vk=VK_Q,
            callback=self.trigger_smart_next
        )
        self.hotkey_mgr.add_hotkey(
            hotkey_id=2,
            name="Screen Snip & Solve",
            primary_mod=MOD_CONTROL | MOD_ALT, primary_vk=VK_S,
            callback=self.trigger_vision_solve
        )
        self.hotkey_mgr.add_hotkey(
            hotkey_id=3,
            name="Presenter Visibility Toggle",
            primary_mod=MOD_CONTROL | MOD_ALT, primary_vk=VK_H,
            callback=lambda: self.hud_signaler.toggle_visibility_signal.emit()
        )
        self.hotkey_mgr.add_hotkey(
            hotkey_id=4,
            name="Click-Through Toggle",
            primary_mod=MOD_CONTROL | MOD_ALT, primary_vk=VK_T,
            callback=lambda: self.hud_signaler.toggle_click_through_signal.emit()
        )
        self.hotkey_mgr.add_hotkey(
            hotkey_id=5,
            name="Clear Content",
            primary_mod=MOD_CONTROL | MOD_ALT, primary_vk=VK_C,
            callback=self.trigger_clear
        )

        self.hotkey_mgr.start()

    def _on_stt_interim(self, text: str):
        self.reconciler.set_interim(text)
        live_txt = self.reconciler.get_live_display_text()
        self.hud_signaler.transcript_updated.emit(live_txt)
        threadsafe_broadcast({"type": "transcript", "text": live_txt})

    def _on_stt_final(self, text: str):
        self.reconciler.add_final(text, speaker="Speaker")
        live_txt = self.reconciler.get_live_display_text()
        self.hud_signaler.transcript_updated.emit(live_txt)
        threadsafe_broadcast({"type": "transcript", "text": live_txt})

    def _on_live_question_detected(self, question: str):
        """Automatically called when live conversation question is spoken."""
        print(f"[MeetingCopilot] Auto-answering detected conversation question: '{question}'")
        self.trigger_direct_qa(question)

    def trigger_simulated_speech(self, sample_text: str):
        """Simulates real-time live speaker speech arriving incrementally."""
        async def run_sim():
            words = sample_text.split(" ")
            accum = ""
            for w in words:
                accum += w + " "
                self._on_stt_interim(accum.strip())
                await asyncio.sleep(0.06)
            self._on_stt_final(sample_text)
            await asyncio.sleep(0.1)
            self.trigger_direct_qa(sample_text)

        if self.async_loop:
            asyncio.run_coroutine_threadsafe(run_sim(), self.async_loop)

    def trigger_smart_next(self):
        question = self.reconciler.get_reconciled_question()
        if not question:
            question = "Explain optimal data structures, algorithms, and production implementation."
        self.trigger_direct_qa(question)

    def trigger_stage(self, stage_num: int):
        question = self.reconciler.get_reconciled_question() or "Technical Problem Solving"
        self.trigger_direct_qa(question)

    def trigger_custom_query(self, query_text: str):
        """Runs the direct QA pipeline for the user's typed question."""
        print(f"[MeetingCopilot] Custom Query Triggered: '{query_text}'")
        self.reconciler.add_final(query_text, speaker="User")
        self.trigger_direct_qa(query_text)

    def trigger_direct_qa(self, question: str):
        """Streams direct concise answer and production code for the question."""
        print(f"[MeetingCopilot] Streaming Direct QA for: '{question[:60]}...'")

        async def run_qa():
            self.hud_signaler.qa_card_complete.emit("")
            threadsafe_broadcast({"type": "qa_start", "query": question})

            def on_tok(token: str):
                self.hud_signaler.qa_token_stream.emit(token)
                threadsafe_broadcast({"type": "qa_token", "token": token})

            full_res = await self.llm_orch.stream_direct_qa(
                question=question,
                on_token=on_tok
            )
            self.hud_signaler.qa_card_complete.emit(full_res)
            threadsafe_broadcast({"type": "qa_complete", "content": full_res})

        if self.async_loop:
            asyncio.run_coroutine_threadsafe(run_qa(), self.async_loop)

    def trigger_vision_solve(self):
        print("[MeetingCopilot] Capturing active presentation slide for Vision OCR...")
        webp_bytes = capture_and_preprocess_webp()
        if not webp_bytes:
            print("[MeetingCopilot] Failed to capture window.")
            return

        async def run_vis():
            self.hud_signaler.qa_card_complete.emit("")
            
            def on_token(token: str):
                self.hud_signaler.qa_token_stream.emit(token)
                threadsafe_broadcast({"type": "qa_token", "token": token})

            full_res = await self.llm_orch.stream_vision_solution(
                image_webp_bytes=webp_bytes,
                on_token=on_token
            )
            self.hud_signaler.qa_card_complete.emit(full_res)
            threadsafe_broadcast({"type": "qa_complete", "content": full_res})

        if self.async_loop:
            asyncio.run_coroutine_threadsafe(run_vis(), self.async_loop)

    def trigger_clear(self):
        self.reconciler.clear_current()
        self.hud_signaler.clear_triggered.emit()
        threadsafe_broadcast({"type": "clear"})

    def _on_setup_launch(self):
        self.config = load_config()
        self.llm_orch.update_config(self.config)
        self.hud.apply_live_settings(self.config)
        self.hud.show()

    def cleanup(self):
        print("[MeetingCopilot] Cleaning up processes and volatile memory...")
        self.hotkey_mgr.stop()
        self.audio_stop_event.set()
        if self.stt_streamer:
            self.stt_streamer.stop()
        if self.audio_process and self.audio_process.is_alive():
            self.audio_process.terminate()
            self.audio_process.join(timeout=1.0)
        if self.async_loop:
            self.async_loop.stop()

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = MeetingCopilotApp()
    app.start()
