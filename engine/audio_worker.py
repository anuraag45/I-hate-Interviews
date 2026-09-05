import math
import multiprocessing
import sys
import time
import numpy as np
from scipy import signal
from typing import Optional, List, Tuple

from engine.shared_audio_ring import SharedAudioRing, SHM_NAME

TARGET_SAMPLE_RATE = 16000 # Deepgram / SpeechRecognition standard

def find_wasapi_loopback_device(pyaudio_instance):
    """Finds the default WASAPI loopback device in PyAudioWPatch."""
    wasapi_info = None
    try:
        for i in range(pyaudio_instance.get_host_api_count()):
            api_info = pyaudio_instance.get_host_api_info_by_index(i)
            if api_info["name"].find("WASAPI") != -1:
                wasapi_info = api_info
                break

        if wasapi_info is None:
            return None

        default_speakers = pyaudio_instance.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        if not default_speakers.get("isLoopbackDevice", False):
            for loopback in pyaudio_instance.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    return loopback
            for loopback in pyaudio_instance.get_loopback_device_info_generator():
                return loopback
        return default_speakers
    except Exception as e:
        print(f"[AudioWorker] Error querying WASAPI loopback devices: {e}")
        return None

def find_default_mic_device(pyaudio_instance):
    """Finds default microphone input device."""
    try:
        return pyaudio_instance.get_default_input_device_info()
    except Exception as e:
        print(f"[AudioWorker] Error getting default mic: {e}")
        return None

def calculate_dbfs(samples_np: np.ndarray) -> float:
    """
    Computes logarithmic audio level in dBFS (-60.0 dB to 0.0 dB).
    Accurately maps to human auditory perception.
    """
    if len(samples_np) == 0:
        return -60.0
    rms = np.sqrt(np.mean(samples_np ** 2))
    dbfs = 20.0 * np.log10(max(1e-6, float(rms)))
    return float(np.clip(dbfs, -60.0, 0.0))

def run_audio_worker(stop_event: multiprocessing.Event, config: dict):
    """
    High-Priority Dual Audio Stream Capture:
    Captures BOTH Microphone (Speaker) and WASAPI Loopback (Interviewer / System Audio).
    Mixes and streams 16kHz PCM into SharedAudioRing with real-time dBFS levels.
    """
    print("[AudioWorker] Starting Dual Microphone + Loopback Audio Capture Process...")
    try:
        import pyaudiowpatch as pyaudio
    except ImportError:
        import pyaudio

    shm_ring = SharedAudioRing(name=SHM_NAME, create=True)
    silence_50ms = b"\x00" * 1600
    last_audio_time = time.time()

    while not stop_event.is_set():
        p = None
        stream_loopback = None
        stream_mic = None

        try:
            p = pyaudio.PyAudio()
            loop_dev = find_wasapi_loopback_device(p)
            mic_dev = find_default_mic_device(p)

            # Open loopback stream (System audio / Interviewer)
            loop_rate = 48000
            loop_channels = 2
            loop_chunk = 2400
            if loop_dev:
                loop_rate = int(loop_dev.get("defaultSampleRate", 48000))
                loop_channels = max(1, int(loop_dev.get("maxInputChannels", 2)))
                loop_chunk = int(loop_rate * 0.05)
                try:
                    stream_loopback = p.open(
                        format=pyaudio.paFloat32,
                        channels=loop_channels,
                        rate=loop_rate,
                        input=True,
                        input_device_index=loop_dev["index"],
                        frames_per_buffer=loop_chunk
                    )
                    print(f"[AudioWorker] Connected Loopback: '{loop_dev['name']}' ({loop_rate}Hz, {loop_channels}ch)")
                except Exception as e:
                    print(f"[AudioWorker] Could not open loopback: {e}")

            # Open mic stream (User voice)
            mic_rate = 44100
            mic_channels = 1
            mic_chunk = 2205
            if mic_dev:
                mic_rate = int(mic_dev.get("defaultSampleRate", 44100))
                mic_channels = max(1, int(mic_dev.get("maxInputChannels", 1)))
                mic_chunk = int(mic_rate * 0.05)
                try:
                    stream_mic = p.open(
                        format=pyaudio.paFloat32,
                        channels=mic_channels,
                        rate=mic_rate,
                        input=True,
                        input_device_index=mic_dev["index"],
                        frames_per_buffer=mic_chunk
                    )
                    print(f"[AudioWorker] Connected Microphone: '{mic_dev['name']}' ({mic_rate}Hz, {mic_channels}ch)")
                except Exception as e:
                    print(f"[AudioWorker] Could not open microphone: {e}")

            if not stream_loopback and not stream_mic:
                print("[AudioWorker] No audio devices opened. Retrying in 2s...")
                time.sleep(2.0)
                continue

            while not stop_event.is_set():
                sys_dbfs = -60.0
                mic_dbfs = -60.0
                loop_np = None
                mic_np = None

                # 1. Read Loopback (System / Interviewer) - non-blocking
                if stream_loopback:
                    try:
                        avail_loop = stream_loopback.get_read_available()
                        if avail_loop >= loop_chunk:
                            raw_loop = stream_loopback.read(loop_chunk, exception_on_overflow=False)
                            if raw_loop:
                                l_data = np.frombuffer(raw_loop, dtype=np.float32)
                                if loop_channels > 1:
                                    l_data = l_data.reshape(-1, loop_channels).mean(axis=1)
                                sys_dbfs = calculate_dbfs(l_data)
                                if loop_rate != TARGET_SAMPLE_RATE:
                                    gcd = math.gcd(TARGET_SAMPLE_RATE, loop_rate)
                                    l_data = signal.resample_poly(l_data, TARGET_SAMPLE_RATE // gcd, loop_rate // gcd)
                                loop_np = l_data
                    except Exception:
                        pass

                # 2. Read Microphone (User / Candidate) - non-blocking
                if stream_mic:
                    try:
                        avail_mic = stream_mic.get_read_available()
                        if avail_mic >= mic_chunk:
                            raw_mic = stream_mic.read(mic_chunk, exception_on_overflow=False)
                            if raw_mic:
                                m_data = np.frombuffer(raw_mic, dtype=np.float32)
                                if mic_channels > 1:
                                    m_data = m_data.reshape(-1, mic_channels).mean(axis=1)
                                mic_dbfs = calculate_dbfs(m_data)
                                if mic_rate != TARGET_SAMPLE_RATE:
                                    gcd = math.gcd(TARGET_SAMPLE_RATE, mic_rate)
                                    m_data = signal.resample_poly(m_data, TARGET_SAMPLE_RATE // gcd, mic_rate // gcd)
                                mic_np = m_data
                    except Exception:
                        pass

                # 3. Combine & Mix (with length matching)
                mixed_audio = None
                if loop_np is not None and mic_np is not None:
                    min_len = min(len(loop_np), len(mic_np))
                    mixed_audio = (loop_np[:min_len] * 0.7) + (mic_np[:min_len] * 0.7)
                elif mic_np is not None:
                    mixed_audio = mic_np
                elif loop_np is not None:
                    mixed_audio = loop_np

                # 4. Write mixed 16kHz PCM to shared memory
                if mixed_audio is not None and len(mixed_audio) > 0:
                    pcm_16 = np.clip(mixed_audio * 32767.0, -32768, 32767).astype(np.int16)
                    shm_ring.write_pcm_chunk(pcm_16.tobytes(), system_dbfs=sys_dbfs, mic_dbfs=mic_dbfs)
                    last_audio_time = time.time()
                else:
                    if time.time() - last_audio_time > 0.5:
                        shm_ring.write_pcm_chunk(silence_50ms, system_dbfs=-60.0, mic_dbfs=-60.0)
                        last_audio_time = time.time()
                    time.sleep(0.005)

        except Exception as e:
            print(f"[AudioWorker] Audio stream glitch: {e}. Reconnecting in 1.5s...")
            time.sleep(1.5)
        finally:
            if stream_loopback:
                try:
                    stream_loopback.stop_stream()
                    stream_loopback.close()
                except Exception:
                    pass
            if stream_mic:
                try:
                    stream_mic.stop_stream()
                    stream_mic.close()
                except Exception:
                    pass
            if p:
                try:
                    p.terminate()
                except Exception:
                    pass

    shm_ring.close()
    print("[AudioWorker] Audio Capture Process stopped cleanly.")
