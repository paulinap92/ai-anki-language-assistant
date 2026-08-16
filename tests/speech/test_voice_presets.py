from src.speech.voice_presets import get_voice_by_label, get_voice_labels


def test_selected_spanish_elevenlabs_presets_are_available() -> None:
    labels = get_voice_labels("ElevenLabs", "Spanish")
    expected = {
        "Spanish Andalusian 2": "EFzULmfYG2shJLXWKyj5",
        "Spanish Andalusian 3": "fqmp7Cu3N7PDtpzRpxhz",
        "Spanish Andalusian 4": "syjZiIvIUSwKREBfMpKZ",
        "Spanish Andalusian 5": "LcMajEnHqf3tUTha5ppa",
        "Spanish Peninsular 1": "gc61tTk93h3LBXPxew2V",
        "Spanish Peninsular 2": "D7dkYvH17OKLgp4SLulf",
        "Spanish Peninsular 3": "IL7GIOA2FIurcXETHVY7",
        "Spanish Peninsular 4 (female)": "KHCvMklQZZo0O30ERnVn",
        "Spanish Peninsular 5 (female)": "BXtvkfRgOYGPQKVRgufE",
        "Spanish Canarian 2": "Thkz4r8fshqG13klONQh",
    }

    for label, voice_id in expected.items():
        assert label in labels
        assert get_voice_by_label("ElevenLabs", label) == voice_id
