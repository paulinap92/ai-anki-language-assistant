"""ElevenLabs text-to-speech provider."""

from __future__ import annotations

from pathlib import Path

import requests

from src.speech.models import TtsRequest
from src.speech.tts.base import TextToSpeechProvider


class ElevenLabsTtsProvider(TextToSpeechProvider):
    """Generate MP3 speech through the ElevenLabs REST API."""

    def __init__(self, api_key: str, model: str, voice: str) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice

    @property
    def provider_name(self) -> str:
        return "ElevenLabs"

    @property
    def default_model(self) -> str:
        return self._model

    @property
    def default_voice(self) -> str:
        return self._voice

    @property
    def models(self) -> list[str]:
        return ["eleven_flash_v2_5", "eleven_multilingual_v2"]

    @property
    def voices(self) -> list[str]:
        return [self._voice]

    @property
    def output_extension(self) -> str:
        return "mp3"

    def synthesize(self, request: TtsRequest, output_path: Path) -> None:
        if not request.voice.strip():
            raise ValueError("ElevenLabs requires a voice ID.")
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{request.voice}",
            params={"output_format": "mp3_44100_128"},
            headers={
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": request.text,
                "model_id": request.model,
            },
            timeout=90,
        )
        response.raise_for_status()
        output_path.write_bytes(response.content)
