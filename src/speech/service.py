"""Application service for cached text-to-speech generation."""

from __future__ import annotations

from pathlib import Path

from src.speech.cache import AudioCache
from datetime import datetime

from src.speech.models import TtsDiagnostic, TtsRequest, TtsResult
from src.speech.tts.base import TextToSpeechProvider


class SpeechService:
    """Coordinate configured TTS providers and deterministic caching."""

    def __init__(
        self,
        providers: dict[str, TextToSpeechProvider],
        cache_directory: Path,
    ) -> None:
        self._providers = providers
        self._cache = AudioCache(cache_directory)

    @property
    def providers(self) -> dict[str, TextToSpeechProvider]:
        return self._providers

    def diagnose_provider(
        self,
        provider_name: str,
        language: str,
        model: str,
        voice: str,
    ) -> TtsDiagnostic:
        """Run a tiny provider preflight check without exposing secrets.

        This centralises the Preview/Batch/Fix-audio diagnostic path so a TTS
        provider is tested consistently before long audio work starts.
        """
        try:
            provider = self._providers[provider_name]
        except KeyError as exc:
            return TtsDiagnostic(
                ok=False,
                provider_name=provider_name or "",
                model=model or "",
                voice=voice or "",
                api_key_status="unknown",
                auth_status="provider not configured",
                error_message=f"Unknown TTS provider: {provider_name}",
            )

        api_key_status = "not required / local"
        if provider.provider_name == "ElevenLabs":
            api_key_status = "found" if str(getattr(provider, "_api_key", "") or "").strip() else "missing"
            if api_key_status == "missing":
                return TtsDiagnostic(
                    ok=False,
                    provider_name=provider.provider_name,
                    model=model or provider.default_model,
                    voice=voice or provider.default_voice,
                    api_key_status=api_key_status,
                    auth_status="not tested",
                    error_message="Check ELEVENLABS_API_KEY in .env or switch provider.",
                )

        sample_by_language = {
            "English": "This is a short TTS diagnostic sample.",
            "Spanish": "Esta es una breve prueba de voz.",
            "Polish": "To jest krótka próbka głosu.",
            "German": "Dies ist eine kurze Stimmprobe.",
            "Italian": "Questa è una breve prova vocale.",
        }
        base_sample = sample_by_language.get(language, "This is a short TTS diagnostic sample.")
        sample_text = f"{base_sample} {datetime.now().strftime('%H%M%S')}"
        try:
            result = self.generate(
                provider.provider_name,
                sample_text,
                language,
                model or provider.default_model,
                voice or provider.default_voice,
            )
        except Exception as exc:  # Provider-specific clients raise different exception types.
            return TtsDiagnostic(
                ok=False,
                provider_name=provider.provider_name,
                model=model or provider.default_model,
                voice=voice or provider.default_voice,
                api_key_status=api_key_status,
                auth_status="failed",
                error_message=str(exc) or exc.__class__.__name__,
            )

        return TtsDiagnostic(
            ok=True,
            provider_name=provider.provider_name,
            model=result.model,
            voice=result.voice,
            api_key_status=api_key_status,
            auth_status="OK",
            sample_path=result.path,
        )

    def generate(
        self,
        provider_name: str,
        text: str,
        language: str,
        model: str,
        voice: str,
    ) -> TtsResult:
        """Generate or reuse audio for an exact synthesis configuration."""
        clean_text = " ".join(text.split())
        if not clean_text:
            raise ValueError("Cannot generate audio from empty text.")
        try:
            provider = self._providers[provider_name]
        except KeyError as exc:
            raise ValueError(f"Unknown TTS provider: {provider_name}") from exc
        request = TtsRequest(
            text=clean_text,
            language=language,
            model=model.strip() or provider.default_model,
            voice=voice.strip() or provider.default_voice,
        )
        path = self._cache.path_for(
            provider.provider_name, request, provider.output_extension
        )
        cached = path.exists() and path.stat().st_size > 0
        if not cached:
            provider.synthesize(request, path)
        return TtsResult(
            path=path,
            provider_name=provider.provider_name,
            model=request.model,
            voice=request.voice,
            cached=cached,
        )
