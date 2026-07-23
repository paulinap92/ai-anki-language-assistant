"""OpenAI text-to-speech provider."""

from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from src.speech.models import TtsRequest
from src.speech.tts.base import TextToSpeechProvider


class OpenAiTtsProvider(TextToSpeechProvider):
    """Generate MP3 speech through OpenAI Audio Speech."""

    def __init__(self, api_key: str, model: str, voice: str) -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._voice = voice

    @property
    def provider_name(self) -> str:
        return "OpenAI TTS"

    @property
    def default_model(self) -> str:
        return self._model

    @property
    def default_voice(self) -> str:
        return self._voice

    @property
    def models(self) -> list[str]:
        return ["gpt-4o-mini-tts", "tts-1"]

    @property
    def voices(self) -> list[str]:
        return ["coral", "alloy", "nova", "sage", "shimmer"]

    @property
    def output_extension(self) -> str:
        return "mp3"

    def synthesize(self, request: TtsRequest, output_path: Path) -> None:
        with self._client.audio.speech.with_streaming_response.create(
            model=request.model,
            voice=request.voice,
            input=request.text,
            response_format="mp3",
        ) as response:
            response.stream_to_file(output_path)
