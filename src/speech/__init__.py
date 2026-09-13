"""Speech services for text-to-speech and speech-to-text workflows."""

from src.speech.factory import build_stt_service
from src.speech.service import SpeechService
from src.speech.stt import LocalWhisperSttService, OpenAiSttService, RecordedSttService, SttResult

__all__ = [
    "SpeechService",
    "RecordedSttService",
    "LocalWhisperSttService",
    "OpenAiSttService",
    "SttResult",
    "build_stt_service",
]
