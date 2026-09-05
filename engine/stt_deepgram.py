import asyncio
import io
import json
import time
import wave
import websockets
from typing import Callable, Optional
import numpy as np

from engine.shared_audio_ring import SharedAudioRing, SHM_NAME

DEEPGRAM_WS_URL = (
    "wss://api.deepgram.com/v1/listen?"
    "encoding=linear16&sample_rate=16000&channels=1&"
    "interim_results=true&smart_format=true&endpointing=300&punctuate=true"
)

QUESTION_STARTERS = (
    "how", "what", "why", "where", "when", "who", "which", "can you",
    "could you", "design", "explain", "implement", "solve", "tell me",
    "describe", "compare", "write", "difference between"
)

class DeepgramStreamer:
    def __init__(self, api_key: str = "",
                 on_interim: Optional[Callable[[str], None]] = None,
                 on_final: Optional[Callable[[str], None]] = None,
                 on_auto_question_detected: Optional[Callable[[str], None]] = None):
        self.api_key = api_key
        self.on_interim = on_interim
        self.on_final = on_final
        self.on_auto_question_detected = on_auto_question_detected
        self._running = False
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._shm_ring: Optional[SharedAudioRing] = None

    def update_key(self, api_key: str):
        self.api_key = api_key

    async def start(self):
        """Starts either Deepgram Nova-2 WebSocket or Free Local/Google VAD Speech Recognizer."""
        self._running = True
        self._shm_ring = SharedAudioRing(name=SHM_NAME, create=False)

        while self._running:
            if self.api_key:
                try:
                    await self._run_deepgram_loop()
                except Exception as e:
                    print(f"[SpeechSTT] Deepgram disconnect: {e}. Falling back to Universal Recognizer...")
                    await self._run_universal_vad_loop()
            else:
                await self._run_universal_vad_loop()

    async def _run_deepgram_loop(self):
        headers = {"Authorization": f"Token {self.api_key}"}
        print("[SpeechSTT] Connecting to Deepgram Nova-2 WebSocket...")
        async with websockets.connect(DEEPGRAM_WS_URL, extra_headers=headers, ping_interval=15, ping_timeout=20) as ws:
            self._ws = ws
            print("[SpeechSTT] Deepgram WebSocket Connected & Listening.")
            sender_task = asyncio.create_task(self._send_audio_loop(ws))
            receiver_task = asyncio.create_task(self._receive_transcript_loop(ws))
            keepalive_task = asyncio.create_task(self._keepalive_loop(ws))

            done, pending = await asyncio.wait(
                [sender_task, receiver_task, keepalive_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()

    async def _send_audio_loop(self, ws):
        while self._running:
            if self._shm_ring:
                pcm_data = self._shm_ring.read_available_pcm(max_bytes=3200)
                if pcm_data:
                    await ws.send(pcm_data)
                else:
                    await asyncio.sleep(0.02)
            else:
                await asyncio.sleep(0.05)

    async def _receive_transcript_loop(self, ws):
        async for message in ws:
            try:
                data = json.loads(message)
                if "channel" in data and "alternatives" in data["channel"]:
                    alt = data["channel"]["alternatives"][0]
                    transcript = alt.get("transcript", "").strip()
                    is_final = data.get("is_final", False)
                    speech_final = data.get("speech_final", False)

                    if transcript:
                        if is_final or speech_final:
                            if self.on_final:
                                self.on_final(transcript)
                            self._check_auto_question(transcript)
                        else:
                            if self.on_interim:
                                self.on_interim(transcript)
            except Exception as ex:
                print(f"[SpeechSTT] Error parsing transcript JSON: {ex}")

    async def _keepalive_loop(self, ws):
        while self._running:
            try:
                await asyncio.sleep(5.0)
                await ws.send(json.dumps({"type": "KeepAlive"}))
            except Exception:
                break

    async def _run_universal_vad_loop(self):
        """
        Universal Speech Recognition with Voice Activity Detection (VAD).
        Transcribes speech continuously from the shared audio ring even without Deepgram.
        """
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 180
        recognizer.dynamic_energy_threshold = True

        print("[SpeechSTT] Universal Live Speech Engine Active (Listening to mic & system audio)...")
        audio_buffer = bytearray()
        silence_start = None
        speech_detected = False

        while self._running and not self.api_key:
            if not self._shm_ring:
                await asyncio.sleep(0.1)
                continue

            chunk = self._shm_ring.read_available_pcm(max_bytes=3200) # 100ms
            if not chunk:
                await asyncio.sleep(0.02)
                continue

            # Calculate RMS energy
            samples = np.frombuffer(chunk, dtype=np.int16)
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2)) if len(samples) > 0 else 0

            # VAD threshold: speech typically > 160 RMS
            if rms > 160:
                audio_buffer.extend(chunk)
                speech_detected = True
                silence_start = None
                if self.on_interim and len(audio_buffer) % 16000 == 0:
                    self.on_interim("🎙️ Hearing speech...")
            elif speech_detected:
                audio_buffer.extend(chunk)
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > 0.7: # 700ms silence ends utterance
                    if len(audio_buffer) >= 12000: # at least ~0.4s audio
                        pcm_bytes = bytes(audio_buffer)
                        audio_buffer.clear()
                        speech_detected = False
                        silence_start = None
                        
                        # Transcribe in worker thread
                        def transcribe_worker(raw_pcm):
                            try:
                                audio_data = sr.AudioData(raw_pcm, 16000, 2)
                                text = recognizer.recognize_google(audio_data)
                                if text and text.strip():
                                    print(f"[SpeechSTT] Transcribed: \"{text}\"")
                                    if self.on_final:
                                        self.on_final(text)
                                    self._check_auto_question(text)
                            except sr.UnknownValueError:
                                pass
                            except Exception as ex:
                                print(f"[SpeechSTT] Recognition notice: {ex}")

                        try:
                            loop = asyncio.get_running_loop()
                            loop.run_in_executor(None, transcribe_worker, pcm_bytes)
                        except Exception:
                            import threading
                            threading.Thread(target=transcribe_worker, args=(pcm_bytes,), daemon=True).start()
                    else:
                        audio_buffer.clear()
                        speech_detected = False
                        silence_start = None
            else:
                # Keep small circular buffer for pre-speech window
                if len(audio_buffer) > 4800:
                    audio_buffer = audio_buffer[-4800:]
                audio_buffer.extend(chunk)

            await asyncio.sleep(0.015)

    def _check_auto_question(self, text: str):
        """Detects if finalized speech is a question / topic to automatically trigger solution."""
        t_clean = text.strip()
        t_lower = t_clean.lower()

        is_question = (
            "?" in t_clean or
            any(t_lower.startswith(q) for q in QUESTION_STARTERS) or
            "how to" in t_lower or
            "what is" in t_lower or
            "can we" in t_lower
        )

        if is_question and len(t_clean.split()) >= 3:
            print(f"[SpeechSTT] Detected Live Question: \"{t_clean}\" -> Auto-Triggering Full Solution!")
            if self.on_auto_question_detected:
                self.on_auto_question_detected(t_clean)

    def stop(self):
        self._running = False
        if self._shm_ring:
            self._shm_ring.close()
