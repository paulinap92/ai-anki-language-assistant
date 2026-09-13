"""Discreet CustomTkinter GUI launcher for local/private testing."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import traceback

import customtkinter as ctk
from tkinter import messagebox

from src.ai.factory import build_ai_clients
from src.anki.client import AnkiClient
from src.core.config import get_settings
from src.speech import SpeechService, build_stt_service
from src.speech.tts.factory import build_tts_providers
from src.ui.modern_gui import ModernVocabularyGui


STARTUP_LOG = Path("logs") / "startup_private.log"


def _startup_trace(message: str) -> None:
    try:
        STARTUP_LOG.parent.mkdir(parents=True, exist_ok=True)
        with STARTUP_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")
    except Exception:
        pass


def main() -> None:
    _startup_trace("START launcher entered")
    root = ctk.CTk()
    root.title(" ")
    root.geometry("620x220")
    startup_label = ctk.CTkLabel(root, text="Starting…", font=ctk.CTkFont(size=18, weight="bold"))
    startup_label.pack(expand=True, padx=30, pady=30)
    root.update_idletasks()
    try:
        root.deiconify()
        root.lift()
    except Exception:
        pass

    try:
        settings = get_settings()
        _startup_trace("CONFIG loaded")
        ai_clients = build_ai_clients(settings)
        _startup_trace(f"AI providers loaded: {','.join(ai_clients) or 'none'}")
        anki_client = AnkiClient(
            anki_connect_url=settings.anki_connect_url,
            deck_name=settings.anki_deck_name,
        )
        tts_providers = build_tts_providers(settings)
        speech_service = SpeechService(tts_providers, Path(settings.audio_cache_dir)) if tts_providers else None
        stt_service = build_stt_service(settings)
        startup_label.destroy()
        ModernVocabularyGui(
            root=root,
            ai_clients=ai_clients,
            anki_client=anki_client,
            default_target_language=settings.default_target_language,
            speech_service=speech_service,
            stt_service=stt_service,
            window_title=" ",
            show_public_header=False,
        )
        _startup_trace("GUI construction completed; entering mainloop")
        root.mainloop()
    except SystemExit:
        raise
    except Exception as exc:
        _startup_trace(f"STARTUP ERROR {type(exc).__name__}: {exc}\n{traceback.format_exc()}")
        try:
            messagebox.showerror("Application startup", f"{type(exc).__name__}: {exc}\n\nSee {STARTUP_LOG}.", parent=root)
        finally:
            try:
                root.destroy()
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
