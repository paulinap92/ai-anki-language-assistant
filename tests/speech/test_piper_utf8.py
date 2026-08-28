from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from src.speech.models import TtsRequest
from src.speech.tts.piper import PiperExecutableTtsProvider


def test_piper_executable_sends_unicode_as_utf8(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "piper.exe"
    model = tmp_path / "voice.onnx"
    output = tmp_path / "out.wav"
    exe.write_bytes(b"exe")
    model.write_bytes(b"model")
    captured = {}

    def fake_run(command, **kwargs):
        captured.update(kwargs)
        output.write_bytes(b"RIFFfake")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("src.speech.tts.piper.subprocess.run", fake_run)
    provider = PiperExecutableTtsProvider(exe, [model])
    provider.synthesize(
        TtsRequest(
            text="🔗 Zażółć gęślą jaźń. ¡Hola, señor!",
            language="Polish",
            model=str(model),
            voice=str(model),
        ),
        output,
    )

    assert captured["encoding"] == "utf-8"
    assert captured["text"] is True
    assert captured["input"].startswith("🔗")
