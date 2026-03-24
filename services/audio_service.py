"""
services/audio_service.py
==========================
Text-to-Speech (TTS) and optionally Speech-to-Text (STT).

TTS: pyttsx3 (always available, uses Windows SAPI voices)
STT: SpeechRecognition + pyaudio (optional — degrades gracefully)
"""
from __future__ import annotations
import logging
import threading

logger = logging.getLogger(__name__)

_engine_lock = threading.Lock()


def speak(text: str, rate: int = 160, volume: float = 1.0) -> None:
    """
    Speak *text* asynchronously in a background thread so the UI stays responsive.

    Args:
        text:   The string to speak.
        rate:   Words per minute (default 160).
        volume: Volume 0.0 – 1.0 (default 1.0).
    """
    if not text or not text.strip():
        return

    def _run() -> None:
        try:
            import pyttsx3
            with _engine_lock:
                engine = pyttsx3.init()
                engine.setProperty("rate", rate)
                engine.setProperty("volume", volume)
                engine.say(text)
                engine.runAndWait()
                engine.stop()
        except Exception as exc:
            logger.error("TTS error: %s", exc)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def listen_once(timeout: int = 5) -> str | None:
    """
    Listen via microphone and return the recognised text (or None on failure).
    Requires PyAudio. Returns None gracefully if PyAudio isn't installed.

    Args:
        timeout: Max seconds to wait for speech.
    """
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            logger.debug("Listening for speech…")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=10)
        result = recognizer.recognize_google(audio)
        logger.info("STT result: %s", result)
        return result
    except ImportError:
        logger.warning("PyAudio not installed; STT unavailable.")
        return None
    except Exception as exc:
        logger.warning("STT failed: %s", exc)
        return None


def is_stt_available() -> bool:
    """Return True only if both SpeechRecognition and PyAudio are importable."""
    try:
        import speech_recognition as sr  # noqa: F401
        import pyaudio  # noqa: F401
        return True
    except ImportError:
        return False
