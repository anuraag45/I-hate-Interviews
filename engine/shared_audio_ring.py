import ctypes
import struct
import time
from multiprocessing import shared_memory
from typing import Optional, Tuple
from stealth.win32_affinity import atomic_exchange_u32

# Hardened SPSC Shared Memory Layout
# Header (24 bytes):
# [ 0: 4] uint32 write_offset
# [ 4: 8] uint32 read_offset
# [ 8:16] uint64 last_timestamp_ns
# [16:20] float32 system_dbfs (dBFS: -60.0 to 0.0)
# [20:24] float32 mic_dbfs    (dBFS: -60.0 to 0.0)
# [24:  ] PCM Ring Buffer Payload

HEADER_SIZE = 24
DEFAULT_RING_SIZE = 512 * 1024 # 512 KB (~16 seconds of 16kHz 16-bit mono PCM)
SHM_NAME = "GhostInterviewAudioRing_v2"

class SharedAudioRing:
    def __init__(self, name: str = SHM_NAME, size: int = DEFAULT_RING_SIZE, create: bool = True):
        self.name = name
        self.payload_size = size
        self.total_size = HEADER_SIZE + size
        self.shm: Optional[shared_memory.SharedMemory] = None
        self._buf = None

        if create:
            try:
                self.shm = shared_memory.SharedMemory(name=self.name, create=True, size=self.total_size)
                self._buf = self.shm.buf
                self._buf[0:HEADER_SIZE] = b"\x00" * HEADER_SIZE
                struct.pack_into("<f", self._buf, 16, -60.0)
                struct.pack_into("<f", self._buf, 20, -60.0)
            except FileExistsError:
                # Attach to existing block and reset header
                self.shm = shared_memory.SharedMemory(name=self.name, create=False)
                self._buf = self.shm.buf
                self._buf[0:HEADER_SIZE] = b"\x00" * HEADER_SIZE
                struct.pack_into("<f", self._buf, 16, -60.0)
                struct.pack_into("<f", self._buf, 20, -60.0)
        else:
            self.shm = shared_memory.SharedMemory(name=self.name, create=False)
            self._buf = self.shm.buf

    def write_pcm_chunk(self, pcm_bytes: bytes, system_dbfs: float = -60.0, mic_dbfs: float = -60.0) -> int:
        """
        Lock-Free SPSC atomic write.
        Writes raw PCM bytes into the circular buffer, updates VU meters, and flushes memory fence.
        """
        chunk_len = len(pcm_bytes)
        if chunk_len == 0 or chunk_len > self.payload_size:
            return 0

        write_idx = struct.unpack_from("<I", self._buf, 0)[0]
        read_idx = struct.unpack_from("<I", self._buf, 4)[0]

        end_idx = write_idx + chunk_len
        if end_idx <= self.payload_size:
            self._buf[HEADER_SIZE + write_idx : HEADER_SIZE + end_idx] = pcm_bytes
            new_write_idx = end_idx % self.payload_size
        else:
            first_part = self.payload_size - write_idx
            second_part = chunk_len - first_part
            self._buf[HEADER_SIZE + write_idx : HEADER_SIZE + self.payload_size] = pcm_bytes[:first_part]
            self._buf[HEADER_SIZE : HEADER_SIZE + second_part] = pcm_bytes[first_part:]
            new_write_idx = second_part

        ts_ns = time.time_ns()
        struct.pack_into("<Q", self._buf, 8, ts_ns)
        struct.pack_into("<f", self._buf, 16, float(system_dbfs))
        struct.pack_into("<f", self._buf, 20, float(mic_dbfs))

        atomic_exchange_u32(self._buf, 0, new_write_idx)
        return chunk_len

    def read_available_pcm(self, max_bytes: int = 16384) -> bytes:
        """
        Lock-Free SPSC atomic read.
        Reads all available unread PCM bytes up to max_bytes.
        """
        write_idx = struct.unpack_from("<I", self._buf, 0)[0]
        read_idx = struct.unpack_from("<I", self._buf, 4)[0]

        if write_idx == read_idx:
            return b""

        available = (write_idx - read_idx) % self.payload_size
        to_read = min(available, max_bytes)

        end_idx = read_idx + to_read
        if end_idx <= self.payload_size:
            data = bytes(self._buf[HEADER_SIZE + read_idx : HEADER_SIZE + end_idx])
            new_read_idx = end_idx % self.payload_size
        else:
            first_part = self.payload_size - read_idx
            second_part = to_read - first_part
            data = bytes(self._buf[HEADER_SIZE + read_idx : HEADER_SIZE + self.payload_size]) + \
                   bytes(self._buf[HEADER_SIZE : HEADER_SIZE + second_part])
            new_read_idx = second_part

        atomic_exchange_u32(self._buf, 4, new_read_idx)
        return data

    def get_vu_levels(self) -> Tuple[float, float]:
        """Reads real-time logarithmic audio VU levels from shared memory header."""
        if self._buf is None:
            return -60.0, -60.0
        try:
            sys_db = struct.unpack_from("<f", self._buf, 16)[0]
            mic_db = struct.unpack_from("<f", self._buf, 20)[0]
            return float(sys_db), float(mic_db)
        except Exception:
            return -60.0, -60.0

    def close(self):
        if self.shm:
            try:
                self.shm.close()
            except Exception:
                pass
            self.shm = None

    def unlink(self):
        if self.shm:
            try:
                self.shm.unlink()
            except Exception:
                pass
            self.shm = None
