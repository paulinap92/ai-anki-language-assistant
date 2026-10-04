"""Modern CustomTkinter GUI entry point for the AI Anki Language Assistant."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import traceback

import customtkinter as ctk
from tkinter import messagebox

from src.ai.factory import build_ai_clients
from src.anki.client import AnkiClient
from src.core.config import get_settings
from src.ui.modern_gui import ModernVocabularyGui
from src.speech import SpeechService, build_stt_service
from src.speech.tts.factory import build_tts_providers


STARTUP_LOG = Path("logs") / "startup.log"


def _startup_trace(message: str) -> None:
    """Persist startup milestones so a silent Windows launch can be diagnosed."""
    try:
        STARTUP_LOG.parent.mkdir(parents=True, exist_ok=True)
        with STARTUP_LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat(timespec='seconds')} {message}\n")
    except Exception:
        pass


def main() -> None:
    """Run the modern desktop application without hiding startup work."""
    if "--packaging-self-test" in sys.argv:
        from src.core.packaged_self_test import run_packaged_self_test

        raise SystemExit(run_packaged_self_test())
    _startup_trace("START launcher entered")

    # Create and paint a real window before provider/Anki setup.  Previously all
    # setup happened before CTk existed, so any slow local initialization looked
    # exactly like "nothing happens" to the user.
    root = ctk.CTk()
    root.title("AI Anki Language Assistant")
    root.geometry("620x220")
    root.minsize(540, 180)
    startup_label = ctk.CTkLabel(
        root,
        text="Starting AI Anki Language Assistant…",
        font=ctk.CTkFont(size=20, weight="bold"),
    )
    startup_label.pack(expand=True, padx=30, pady=30)
    root.update_idletasks()
    try:
        root.deiconify()
        root.lift()
    except Exception:
        pass
    _startup_trace("WINDOW first paint requested")

    try:
        startup_label.configure(text="Loading configuration…")
        root.update_idletasks()
        settings = get_settings()
        _startup_trace("CONFIG loaded")

        startup_label.configure(text="Loading AI providers…")
        root.update_idletasks()
        ai_clients = build_ai_clients(settings)
        _startup_trace(f"AI providers loaded: {','.join(ai_clients) or 'none'}")

        anki_client = AnkiClient(
            anki_connect_url=settings.anki_connect_url,
            deck_name=settings.anki_deck_name,
        )
        _startup_trace("ANKI client created (no connection attempted yet)")

        startup_label.configure(text="Loading speech providers…")
        root.update_idletasks()
        tts_providers = build_tts_providers(settings)
        speech_service = SpeechService(tts_providers, Path(settings.audio_cache_dir)) if tts_providers else None
        _startup_trace(f"TTS providers loaded: {','.join(tts_providers) or 'none'}")

        stt_service = build_stt_service(settings)
        _startup_trace("STT service configured")

        startup_label.destroy()
        _startup_trace("GUI construction started")
        ModernVocabularyGui(
            root=root,
            ai_clients=ai_clients,
            anki_client=anki_client,
            default_target_language=settings.default_target_language,
            speech_service=speech_service,
            stt_service=stt_service,
        )
        _startup_trace("GUI construction completed; entering mainloop")
        root.mainloop()
    except SystemExit:
        _startup_trace("STARTUP exited by user")
        raise
    except Exception as exc:
        _startup_trace(f"STARTUP ERROR {type(exc).__name__}: {exc}\n{traceback.format_exc()}")
        try:
            messagebox.showerror(
                "AI Anki Language Assistant",
                f"The application could not finish starting.\n\n{type(exc).__name__}: {exc}\n\n"
                f"Details were saved to {STARTUP_LOG}.",
                parent=root,
            )
        finally:
            try:
                root.destroy()
            except Exception:
                pass
        raise


if __name__ == "__main__":
    main()
