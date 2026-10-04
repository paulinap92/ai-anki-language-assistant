"""Functional checks used only by the packaged Windows release pipeline."""

from __future__ import annotations

import json
import shutil
import traceback
from pathlib import Path


def run_packaged_self_test() -> int:
    """Verify that packaged Whisper and Piper can actually initialize and run."""
    result_path = Path("packaging_self_test.json")
    work_dir = Path(".packaging_self_test")
    report: dict[str, object] = {
        "imports": False,
        "whisper_model": False,
        "piper_catalog": False,
        "piper_download": False,
        "piper_synthesis": False,
    }

    try:
        import ctranslate2  # noqa: F401
        import faster_whisper  # noqa: F401
        import piper  # noqa: F401
        import sounddevice  # noqa: F401
        import soundfile  # noqa: F401

        report["imports"] = True

        from faster_whisper import WhisperModel

        # Tiny is used only by CI so the release pipeline can prove that the
        # frozen EXE can load CTranslate2 and fetch a real Whisper model.
        WhisperModel("tiny", device="cpu", compute_type="int8")
        report["whisper_model"] = True

        from src.speech.models import TtsRequest
        from src.speech.tts.piper import PiperTtsProvider
        from src.speech.voice_library import download_piper_voice, fetch_piper_catalog

        voices = fetch_piper_catalog(language_name="English", query="lessac")
        if not voices:
            voices = fetch_piper_catalog(language_name="English")
        if not voices:
            raise RuntimeError("Piper catalog returned no English voices.")
        report["piper_catalog"] = True

        work_dir.mkdir(parents=True, exist_ok=True)
        voice_path = download_piper_voice(voices[0], work_dir / "voices")
        report["piper_download"] = True

        output_path = work_dir / "piper-test.wav"
        provider = PiperTtsProvider(voice_path)
        provider.synthesize(
            TtsRequest(
                text="Packaging test.",
                language="English",
                model=str(voice_path),
                voice=str(voice_path),
            ),
            output_path,
        )
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Piper synthesis produced no WAV output.")
        report["piper_synthesis"] = True
        report["ok"] = True
        return_code = 0
    except Exception as exc:
        report["ok"] = False
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["traceback"] = traceback.format_exc()
        return_code = 1
    finally:
        result_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        shutil.rmtree(work_dir, ignore_errors=True)

    return return_code
