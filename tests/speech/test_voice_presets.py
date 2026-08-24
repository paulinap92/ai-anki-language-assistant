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


def test_spanish_voice_filter_does_not_put_generic_default_before_spanish_voices() -> None:
    labels = get_voice_labels("ElevenLabs", "Spanish")
    assert labels
    assert "ElevenLabs default verified" not in labels
    assert all(label.startswith(("Spanish", "Colombian", "Mexican", "Canarian", "Chilean")) for label in labels)


def test_english_voice_filter_does_not_include_spanish_presets() -> None:
    labels = get_voice_labels("ElevenLabs", "English")
    assert labels
    assert all("Spanish" not in label for label in labels)
