import base64
import ctypes
from ctypes import wintypes
from typing import Optional

crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32

# Win32 DATA_BLOB structure for DPAPI
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte))
    ]

# DPAPI Flags
CRYPTPROTECT_UI_FORBIDDEN = 0x01

def dpapi_encrypt_string(plaintext: str) -> str:
    """
    Encrypts a string using Windows Data Protection API (DPAPI).
    The ciphertext is tied strictly to the current Windows user SID.
    Returns base64-encoded ciphertext.
    """
    if not plaintext:
        return ""

    try:
        raw_bytes = plaintext.encode("utf-8")
        data_in = DATA_BLOB()
        data_in.cbData = len(raw_bytes)
        data_in.pbData = (ctypes.c_byte * len(raw_bytes))(*raw_bytes)

        data_out = DATA_BLOB()

        res = crypt32.CryptProtectData(
            ctypes.byref(data_in),
            "MeetingCopilotCredential", # description
            None,                       # optional entropy
            None,                       # reserved
            None,                       # prompt struct
            CRYPTPROTECT_UI_FORBIDDEN,  # flags
            ctypes.byref(data_out)
        )

        if not res:
            # Fallback if DPAPI call fails
            return plaintext

        encrypted_bytes = ctypes.string_at(data_out.pbData, data_out.cbData)
        kernel32.LocalFree(data_out.pbData)
        return "dpapi:" + base64.b64encode(encrypted_bytes).decode("ascii")
    except Exception as e:
        print(f"[CryptoStorage] DPAPI Encryption error: {e}")
        return plaintext

def dpapi_decrypt_string(ciphertext_b64: str) -> str:
    """
    Decrypts a base64-encoded DPAPI ciphertext string using the current Windows user SID.
    Returns the original plaintext string.
    """
    if not ciphertext_b64:
        return ""

    if not ciphertext_b64.startswith("dpapi:"):
        return ciphertext_b64 # Already plaintext

    try:
        raw_b64 = ciphertext_b64[6:]
        encrypted_bytes = base64.b64decode(raw_b64)

        data_in = DATA_BLOB()
        data_in.cbData = len(encrypted_bytes)
        data_in.pbData = (ctypes.c_byte * len(encrypted_bytes))(*encrypted_bytes)

        data_out = DATA_BLOB()

        res = crypt32.CryptUnprotectData(
            ctypes.byref(data_in),
            None,                       # description out
            None,                       # optional entropy
            None,                       # reserved
            None,                       # prompt struct
            CRYPTPROTECT_UI_FORBIDDEN,  # flags
            ctypes.byref(data_out)
        )

        if not res:
            return ""

        decrypted_bytes = ctypes.string_at(data_out.pbData, data_out.cbData)
        kernel32.LocalFree(data_out.pbData)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        print(f"[CryptoStorage] DPAPI Decryption error: {e}")
        return ""
