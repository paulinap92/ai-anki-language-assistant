"""Speech services for text-to-speech and future speech-to-text workflows."""

from src.speech.service import SpeechService
from src.speech.stt import LocalWhisperSttService, SttResult

__all__ = ["SpeechService", "LocalWhisperSttService", "SttResult"]
