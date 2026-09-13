from pathlib import Path
from types import SimpleNamespace

from src.speech.tts import factory


def test_tts_factory_accepts_explicit_piper_paths_for_all_learning_languages(monkeypatch, tmp_path: Path):
    paths = {}
    for code in ("en", "es", "pl", "de", "fr", "it", "pt"):
        model = tmp_path / f"{code}.onnx"
        model.write_bytes(b"x")
        paths[code] = str(model)

    class _FakePiper:
        provider_name = "Piper (local)"
        def __init__(self, model_paths):
            self.model_paths = [Path(p) for p in model_paths]

    import src.speech.tts.piper as piper_mod
    monkeypatch.setattr(piper_mod, "PiperTtsProvider", _FakePiper)
    monkeypatch.setattr(factory, "installed_piper_models", lambda: [])

    settings = SimpleNamespace(
        setup_mode="local",
        openai_api_key=None,
        gemini_api_key=None,
        elevenlabs_api_key=None,
        piper_exe_path=None,
        piper_voice_en=paths["en"],
        piper_voice_es=paths["es"],
        piper_voice_pl=paths["pl"],
        piper_voice_de=paths["de"],
        piper_voice_fr=paths["fr"],
        piper_voice_it=paths["it"],
        piper_voice_pt=paths["pt"],
        piper_model_path=None,
    )

    providers = factory.build_tts_providers(settings)
    provider = providers["Piper (local)"]
    assert {path.name for path in provider.model_paths} == {f"{code}.onnx" for code in paths}
