from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.speech import voice_library
from src.speech.voice_library import VoiceLibraryItem


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200):
        self._payload = payload
        self.status_code = status
        self.content = b"audio"

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_fetch_piper_catalog_filters_language_and_builds_download_urls(monkeypatch):
    payload = {
        "es_ES-demo-medium": {
            "key": "es_ES-demo-medium",
            "name": "demo",
            "language": {
                "code": "es_ES",
                "family": "es",
                "name_english": "Spanish",
                "country_english": "Spain",
            },
            "quality": "medium",
            "files": {
                "es/es_ES/demo/medium/es_ES-demo-medium.onnx": {"size_bytes": 10},
                "es/es_ES/demo/medium/es_ES-demo-medium.onnx.json": {"size_bytes": 2},
                "es/es_ES/demo/medium/MODEL_CARD": {"size_bytes": 2},
            },
        },
        "en_US-other-low": {
            "key": "en_US-other-low",
            "name": "other",
            "language": {"code": "en_US", "family": "en", "name_english": "English"},
            "quality": "low",
            "files": {
                "en/en_US/other/low/en_US-other-low.onnx": {},
                "en/en_US/other/low/en_US-other-low.onnx.json": {},
            },
        },
    }
    monkeypatch.setattr(voice_library.requests, "get", lambda *a, **k: FakeResponse(payload))

    items = voice_library.fetch_piper_catalog(language_name="Spanish")

    assert len(items) == 1
    item = items[0]
    assert item.key == "es_ES-demo-medium"
    assert item.preview_url.endswith("/es/es_ES/demo/medium/samples/speaker_0.mp3")
    assert item.model_url.endswith("/es/es_ES/demo/medium/es_ES-demo-medium.onnx")
    assert item.config_url.endswith("/es/es_ES/demo/medium/es_ES-demo-medium.onnx.json")


def test_imported_piper_voice_requires_matching_json_and_is_discovered(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    model = source / "es_ES-demo-medium.onnx"
    model.write_bytes(b"onnx")
    config = source / "es_ES-demo-medium.onnx.json"
    config.write_text(json.dumps({"dataset": "demo", "language": {"name_english": "Spanish", "family": "es", "code": "es_ES"}, "audio": {"quality": "medium"}}), encoding="utf-8")
    library = tmp_path / "library"

    installed = voice_library.import_piper_voice(model, library)

    assert installed.exists()
    assert installed.with_name(installed.name + ".json").exists()
    assert voice_library.installed_piper_models(library) == [installed]
    meta = voice_library.piper_voice_metadata(installed)
    assert meta["language"] == "Spanish"
    assert "demo" in meta["label"]


def test_import_piper_voice_rejects_model_without_config(tmp_path: Path):
    model = tmp_path / "broken.onnx"
    model.write_bytes(b"onnx")
    with pytest.raises(FileNotFoundError):
        voice_library.import_piper_voice(model, tmp_path / "library")


def test_elevenlabs_shared_voice_parsing_and_add(monkeypatch):
    shared_payload = {
        "voices": [
            {
                "public_owner_id": "owner-1",
                "voice_id": "voice-1",
                "name": "Canaria",
                "language": "es",
                "accent": "canarian",
                "gender": "Female",
                "category": "professional",
                "preview_url": "https://example.test/preview.mp3",
                "description": "Warm Spanish voice",
            }
        ]
    }

    def fake_get(url, **kwargs):
        assert url.endswith("/v1/shared-voices")
        assert kwargs["headers"]["xi-api-key"] == "secret"
        return FakeResponse(shared_payload)

    monkeypatch.setattr(voice_library.requests, "get", fake_get)
    items = voice_library.fetch_elevenlabs_shared_voices("secret", language_name="Spanish")
    assert items[0].voice_id == "voice-1"
    assert items[0].public_owner_id == "owner-1"

    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return FakeResponse({"voice_id": "saved-voice-1"})

    monkeypatch.setattr(voice_library.requests, "post", fake_post)
    saved_id = voice_library.add_elevenlabs_shared_voice("secret", items[0])
    assert saved_id == "saved-voice-1"
    assert captured["url"].endswith("/v1/voices/add/owner-1/voice-1")
    assert captured["json"]["new_name"] == "Canaria"


def test_elevenlabs_my_voices_can_be_used_without_shared_owner(monkeypatch):
    payload = {
        "voices": [
            {
                "voice_id": "mine-1",
                "name": "My Voice",
                "category": "professional",
                "labels": {"language": "es", "accent": "peninsular", "gender": "female"},
                "verified_languages": [
                    {"language": "es", "locale": "es-ES", "preview_url": "https://example.test/mine.mp3"}
                ],
            }
        ]
    }
    monkeypatch.setattr(voice_library.requests, "get", lambda *a, **k: FakeResponse(payload))
    items = voice_library.fetch_elevenlabs_my_voices("secret")
    assert items == [
        VoiceLibraryItem(
            provider="ElevenLabs mine",
            key="mine-1",
            name="My Voice",
            language="es",
            locale="es-ES",
            accent="peninsular",
            gender="female",
            quality="professional",
            description="",
            preview_url="https://example.test/mine.mp3",
            voice_id="mine-1",
            source_label="ElevenLabs My Voices",
        )
    ]


def test_elevenlabs_registry_persists_non_secret_voice_selection(tmp_path: Path):
    registry = tmp_path / "voices.json"
    voice_library.save_elevenlabs_registry_voice("ElevenLabs · Canaria", "voice-1", "es", registry)
    voice_library.save_elevenlabs_registry_voice("ElevenLabs · Canaria", "voice-2", "es", registry)

    assert voice_library.load_elevenlabs_registry(registry) == [
        {"label": "ElevenLabs · Canaria", "voice_id": "voice-2", "language": "es"}
    ]



def test_openai_builtin_voice_library_has_current_builtin_set():
    items = voice_library.openai_builtin_voice_items()
    ids = {item.voice_id for item in items}
    assert len(items) == 13
    assert {"nova", "shimmer", "marin", "cedar"} <= ids
    assert next(item for item in items if item.voice_id == "marin").quality == "recommended"


def test_gemini_builtin_voice_library_has_all_30_and_search():
    items = voice_library.gemini_builtin_voice_items()
    assert len(items) == 30
    assert any(item.voice_id == "Zephyr" and item.quality == "Bright" for item in items)
    filtered = voice_library.gemini_builtin_voice_items(query="warm")
    assert [item.voice_id for item in filtered] == ["Sulafat"]


def test_piper_catalog_supports_languages_outside_original_shortlist(monkeypatch):
    payload = {
        "uk_UA-demo-medium": {
            "name": "demo",
            "language": {
                "code": "uk_UA",
                "family": "uk",
                "name_english": "Ukrainian",
                "country_english": "Ukraine",
            },
            "quality": "medium",
            "files": {
                "uk/uk_UA/demo/medium/uk_UA-demo-medium.onnx": {},
                "uk/uk_UA/demo/medium/uk_UA-demo-medium.onnx.json": {},
            },
        },
        "de_DE-demo-medium": {
            "name": "demo-de",
            "language": {"code": "de_DE", "family": "de", "name_english": "German"},
            "quality": "medium",
            "files": {
                "de/de_DE/demo/medium/de_DE-demo-medium.onnx": {},
                "de/de_DE/demo/medium/de_DE-demo-medium.onnx.json": {},
            },
        },
    }
    monkeypatch.setattr(voice_library.requests, "get", lambda *a, **k: FakeResponse(payload))

    assert voice_library.fetch_piper_language_names() == ["German", "Ukrainian"]
    items = voice_library.fetch_piper_catalog(language_name="Ukrainian")
    assert [item.locale for item in items] == ["uk_UA"]


def test_voice_library_language_families_include_russian_and_japanese():
    assert voice_library.LANGUAGE_FAMILY_BY_NAME["Russian"] == "ru"
    assert voice_library.LANGUAGE_FAMILY_BY_NAME["Japanese"] == "ja"
