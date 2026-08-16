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
    VoicePreset("OpenAI Coral", "OpenAI", "coral"),
    VoicePreset("OpenAI Nova", "OpenAI", "nova"),
    VoicePreset("OpenAI Shimmer", "OpenAI", "shimmer"),
    VoicePreset("OpenAI Sage", "OpenAI", "sage"),
    VoicePreset("OpenAI Alloy", "OpenAI", "alloy"),
]


def get_voice_presets(provider: str, language: str | None = None) -> list[VoicePreset]:
    """Return voice presets for a provider."""
    normalized_provider = provider.strip().lower()
    if normalized_provider == "elevenlabs":
        presets = ELEVENLABS_VOICE_PRESETS
    elif normalized_provider == "openai":
        presets = OPENAI_VOICE_PRESETS
    else:
        presets = []

    if language is None:
        return presets

    normalized_language = language.strip().lower()
    return [
        preset
        for preset in presets
        if preset.language is None or preset.language.lower() == normalized_language
    ]


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
