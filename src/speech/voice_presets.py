"""Reusable TTS voice presets.

This module gives readable labels to provider-specific voice identifiers so the
GUI can display names instead of raw ElevenLabs IDs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VoicePreset:
    """User-facing TTS voice preset."""

    label: str
    provider: str
    voice: str
    language: str | None = None
    accent: str | None = None
    gender: str | None = None
    notes: str = ""


ELEVENLABS_VOICE_PRESETS: list[VoicePreset] = [
    VoicePreset(
        "ElevenLabs default verified",
        "ElevenLabs",
        "JBFqnCBsd6RMkjVDRZzb",
        None,
        None,
        None,
        "Known working default voice. Treat ElevenLabs presets as account-dependent until verified via API.",
    ),
    VoicePreset("British male 1", "ElevenLabs", "lUTamkMw7gOzZbFIwmq4", "English", "British", "male"),
    VoicePreset("British male 2", "ElevenLabs", "NNl6r8mD7vthiJatiJt1", "English", "British", "male"),
    VoicePreset("British female", "ElevenLabs", "4CrZuIW9am7gYAxgo2Af", "English", "British", "female"),
    VoicePreset(
        "American male 1 (unverified)",
        "ElevenLabs",
        "bfGb7JTLUnZebZRiFYyq",
        "English",
        "American",
        "male",
        "Previously returned provider errors on at least one account.",
    ),
    VoicePreset("American female", "ElevenLabs", "lxYfHSkYm1EzQzGhdbfc", "English", "American", "female"),
    VoicePreset("American male 2", "ElevenLabs", "6xPz2opT0y5qtoRh1U1Y", "English", "American", "male"),
    VoicePreset("Spanish male", "ElevenLabs", "ZCh4e9eZSUf41K4cmCEL", "Spanish", "Spain", "male"),
    VoicePreset("Spanish Andalusian 2", "ElevenLabs", "EFzULmfYG2shJLXWKyj5", "Spanish", "Andalusian", None),
    VoicePreset("Spanish Andalusian 3", "ElevenLabs", "fqmp7Cu3N7PDtpzRpxhz", "Spanish", "Andalusian", None),
    VoicePreset("Spanish Andalusian 4", "ElevenLabs", "syjZiIvIUSwKREBfMpKZ", "Spanish", "Andalusian", None),
    VoicePreset("Spanish Andalusian 5", "ElevenLabs", "LcMajEnHqf3tUTha5ppa", "Spanish", "Andalusian", None),
    VoicePreset("Spanish Peninsular 1", "ElevenLabs", "gc61tTk93h3LBXPxew2V", "Spanish", "Peninsular", None),
    VoicePreset("Spanish Peninsular 2", "ElevenLabs", "D7dkYvH17OKLgp4SLulf", "Spanish", "Peninsular", None),
    VoicePreset("Spanish Peninsular 3", "ElevenLabs", "IL7GIOA2FIurcXETHVY7", "Spanish", "Peninsular", None),
    VoicePreset("Spanish Peninsular 4 (female)", "ElevenLabs", "KHCvMklQZZo0O30ERnVn", "Spanish", "Peninsular", "female"),
    VoicePreset("Spanish Peninsular 5 (female)", "ElevenLabs", "BXtvkfRgOYGPQKVRgufE", "Spanish", "Peninsular", "female"),
    VoicePreset("Spanish Canarian 2", "ElevenLabs", "Thkz4r8fshqG13klONQh", "Spanish", "Canarian", None),
    VoicePreset("Colombian Spanish male", "ElevenLabs", "851ejYcv2BoNPjrkw93G", "Spanish", "Colombian", "male"),
    VoicePreset("Mexican Spanish female", "ElevenLabs", "22dcXdsgE2CBQsk9cnTY", "Spanish", "Mexican", "female"),
    VoicePreset("Canarian Spanish male", "ElevenLabs", "nBwP3V9cnubnfoXiV64G", "Spanish", "Canarian", "male"),
    VoicePreset("Chilean Spanish female", "ElevenLabs", "oJIuRMopN0sojGjwD6rQ", "Spanish", "Chilean", "female"),
]


OPENAI_VOICE_PRESETS: list[VoicePreset] = [
    VoicePreset("OpenAI · Alloy", "OpenAI TTS", "alloy", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Ash", "OpenAI TTS", "ash", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Ballad", "OpenAI TTS", "ballad", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Coral", "OpenAI TTS", "coral", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Echo", "OpenAI TTS", "echo", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Fable", "OpenAI TTS", "fable", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Nova", "OpenAI TTS", "nova", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Onyx", "OpenAI TTS", "onyx", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Sage", "OpenAI TTS", "sage", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Shimmer", "OpenAI TTS", "shimmer", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Verse", "OpenAI TTS", "verse", notes="Built-in OpenAI TTS voice."),
    VoicePreset("OpenAI · Marin", "OpenAI TTS", "marin", notes="Built-in OpenAI TTS voice; recommended by OpenAI for quality."),
    VoicePreset("OpenAI · Cedar", "OpenAI TTS", "cedar", notes="Built-in OpenAI TTS voice; recommended by OpenAI for quality."),
]

GEMINI_VOICE_PRESETS: list[VoicePreset] = [
    VoicePreset("Gemini · Zephyr — Bright", "Gemini TTS", "Zephyr"),
    VoicePreset("Gemini · Puck — Upbeat", "Gemini TTS", "Puck"),
    VoicePreset("Gemini · Charon — Informative", "Gemini TTS", "Charon"),
    VoicePreset("Gemini · Kore — Firm", "Gemini TTS", "Kore"),
    VoicePreset("Gemini · Fenrir — Excitable", "Gemini TTS", "Fenrir"),
    VoicePreset("Gemini · Leda — Youthful", "Gemini TTS", "Leda"),
    VoicePreset("Gemini · Orus — Firm", "Gemini TTS", "Orus"),
    VoicePreset("Gemini · Aoede — Breezy", "Gemini TTS", "Aoede"),
    VoicePreset("Gemini · Callirrhoe — Easy-going", "Gemini TTS", "Callirrhoe"),
    VoicePreset("Gemini · Autonoe — Bright", "Gemini TTS", "Autonoe"),
    VoicePreset("Gemini · Enceladus — Breathy", "Gemini TTS", "Enceladus"),
    VoicePreset("Gemini · Iapetus — Clear", "Gemini TTS", "Iapetus"),
    VoicePreset("Gemini · Umbriel — Easy-going", "Gemini TTS", "Umbriel"),
    VoicePreset("Gemini · Algieba — Smooth", "Gemini TTS", "Algieba"),
    VoicePreset("Gemini · Despina — Smooth", "Gemini TTS", "Despina"),
    VoicePreset("Gemini · Erinome — Clear", "Gemini TTS", "Erinome"),
    VoicePreset("Gemini · Algenib — Gravelly", "Gemini TTS", "Algenib"),
    VoicePreset("Gemini · Rasalgethi — Informative", "Gemini TTS", "Rasalgethi"),
    VoicePreset("Gemini · Laomedeia — Upbeat", "Gemini TTS", "Laomedeia"),
    VoicePreset("Gemini · Achernar — Soft", "Gemini TTS", "Achernar"),
    VoicePreset("Gemini · Alnilam — Firm", "Gemini TTS", "Alnilam"),
    VoicePreset("Gemini · Schedar — Even", "Gemini TTS", "Schedar"),
    VoicePreset("Gemini · Gacrux — Mature", "Gemini TTS", "Gacrux"),
    VoicePreset("Gemini · Pulcherrima — Forward", "Gemini TTS", "Pulcherrima"),
    VoicePreset("Gemini · Achird — Friendly", "Gemini TTS", "Achird"),
    VoicePreset("Gemini · Zubenelgenubi — Casual", "Gemini TTS", "Zubenelgenubi"),
    VoicePreset("Gemini · Vindemiatrix — Gentle", "Gemini TTS", "Vindemiatrix"),
    VoicePreset("Gemini · Sadachbia — Lively", "Gemini TTS", "Sadachbia"),
    VoicePreset("Gemini · Sadaltager — Knowledgeable", "Gemini TTS", "Sadaltager"),
    VoicePreset("Gemini · Sulafat — Warm", "Gemini TTS", "Sulafat"),
]

def get_voice_presets(provider: str, language: str | None = None) -> list[VoicePreset]:
    """Return voice presets for a provider."""
    normalized_provider = provider.strip().lower()
    if normalized_provider == "elevenlabs":
        presets = ELEVENLABS_VOICE_PRESETS
    elif normalized_provider in {"openai", "openai tts"}:
        presets = OPENAI_VOICE_PRESETS
    elif normalized_provider in {"gemini", "gemini tts"}:
        presets = GEMINI_VOICE_PRESETS
    else:
        presets = []

    if language is None:
        return presets

    normalized_language = language.strip().lower()
    exact = [
        preset
        for preset in presets
        if preset.language is not None and preset.language.lower() == normalized_language
    ]
    if exact:
        return exact
    # Generic voices are a fallback only. They must not silently outrank a
    # language-specific ElevenLabs voice (for example English/British in Spanish).
    return [preset for preset in presets if preset.language is None]


def get_voice_labels(provider: str, language: str | None = None) -> list[str]:
    """Return readable voice labels for a provider."""
    return [preset.label for preset in get_voice_presets(provider, language)]


def get_voice_by_label(provider: str, label: str) -> str:
    """Return provider-specific voice identifier for a readable label."""
    for preset in get_voice_presets(provider):
        if preset.label == label:
            return preset.voice
    raise ValueError(f"Unknown voice label for {provider}: {label}")


def get_default_voice_label(provider: str, language: str) -> str | None:
    """Return a default voice label for a provider and language."""
    presets = get_voice_presets(provider, language)
    if not presets:
        return None
    return presets[0].label
