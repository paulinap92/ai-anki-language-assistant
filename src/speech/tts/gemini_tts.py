"""Gemini text-to-speech provider."""

from __future__ import annotations

from pathlib import Path
import wave

from google import genai
from google.genai import types

from src.speech.models import TtsRequest
from src.speech.tts.base import TextToSpeechProvider


class GeminiTtsProvider(TextToSpeechProvider):
    """Generate WAV speech through Gemini TTS models."""

    def __init__(self, api_key: str, model: str, voice: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._voice = voice

    @property
    def provider_name(self) -> str:
        return "Gemini TTS"

    @property
    def default_model(self) -> str:
        return self._model

    @property
    def default_voice(self) -> str:
        return self._voice

    @property
    def models(self) -> list[str]:
        return [
            "gemini-3.1-flash-tts-preview",
            "gemini-2.5-flash-preview-tts",
            "gemini-2.5-pro-preview-tts",
        ]

    @property
    def voices(self) -> list[str]:
        return ["Kore", "Puck", "Charon", "Fenrir", "Aoede"]

    @property
    def output_extension(self) -> str:
        return "wav"

    def synthesize(self, request: TtsRequest, output_path: Path) -> None:
        response = self._client.models.generate_content(
            model=request.model,
            contents=request.text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=request.voice
                        )
                    )
                ),
            ),
        )
        try:
            pcm = response.candidates[0].content.parts[0].inline_data.data
        except (AttributeError, IndexError, TypeError) as exc:
            raise ValueError("Gemini TTS returned no audio data.") from exc
        with wave.open(str(output_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.writeframes(pcm)
