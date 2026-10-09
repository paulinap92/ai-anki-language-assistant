import sys
import types
from pathlib import Path

if "customtkinter" not in sys.modules:
    stub = types.ModuleType("customtkinter")
    stub.BooleanVar = object
    stub.StringVar = object
    sys.modules["customtkinter"] = stub

from src.ui.modern_gui import ModernVocabularyGui
from src.speech.playback import AudioPlaybackError, InternalAudioPlayer, OutputDevice
from src.core.config import get_settings
from src.core.user_setup import import_env_file


class Var:
    def __init__(self):
        self.value = ""
    def set(self, value):
        self.value = value


class Root:
    def __init__(self):
        self.callbacks = []
    def after(self, delay, callback):
        self.callbacks.append(callback)


def test_audio_io_runs_outside_ui_and_callbacks_are_polled_on_ui(monkeypatch):
    threads = []
    class Thread:
        def __init__(self, **kwargs):
            threads.append(kwargs)
        def start(self):
            pass
    monkeypatch.setattr("src.ui.modern_gui.threading.Thread", Thread)
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._root = Root()
    events = []
    gui._run_audio_task(lambda: events.append("io") or "done", events.append, events.append)
    assert events == []
    threads[0]["target"]()
    assert events == ["io"]
    gui._root.callbacks.pop(0)()
    assert events == ["io", "done"]


def test_selection_is_saved_importable_and_applied_to_both_players(tmp_path, monkeypatch):
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._setup_env_path = tmp_path / ".env"
    gui._speech_progress_var = Var()
    gui._speech_preview_player = InternalAudioPlayer()
    gui._conversation_audio_player = InternalAudioPlayer()
    device = OutputDevice(13, "Słuchawki USB", "Windows WASAPI")
    gui._audio_output_devices = {device.label: device}
    monkeypatch.setenv("AUDIO_OUTPUT_DEVICE_NAME", "")
    monkeypatch.setenv("AUDIO_OUTPUT_HOST_API", "")
    gui._save_audio_output_selection(device.label)
    settings = get_settings()
    assert settings.audio_output_device_name == device.name
    assert settings.audio_output_host_api == device.host_api
    assert gui._conversation_audio_player._device_name == device.name
    assert gui._speech_preview_player._host_api == device.host_api
    destination = tmp_path / "imported.env"
    _, _, count = import_env_file(gui._setup_env_path, destination)
    assert count == 2
    assert "13" not in destination.read_text()
    gui._save_audio_output_selection("Automatic")
    assert get_settings().audio_output_device_name == ""
    assert gui._conversation_audio_player._device_name == ""


def test_conversation_playback_error_is_not_reported_as_tts_error(monkeypatch):
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._conversation_audio_request_id = 7
    gui._conversation_audio_player = object()
    gui._conversation_audio_status_var = Var()
    gui._status_var = Var()
    messages = []
    monkeypatch.setattr("src.ui.modern_gui.messagebox.showerror", lambda *args: messages.append(args))
    gui._start_audio_playback = lambda player, path, success, error: error(AudioPlaybackError("Choose an output device."))
    gui._play_generated_conversation_audio(Path("voice.wav"), request_id=7, label="Tutor")
    assert messages == [("Audio playback", "Choose an output device.")]
    assert "generation succeeded" in gui._conversation_audio_status_var.value


def test_raw_host_error_is_hidden_and_stale_playback_callback_ignored():
    assert "-9999" not in ModernVocabularyGui._friendly_playback_error(RuntimeError("PortAudio -9999"))
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    player = InternalAudioPlayer()
    callbacks = []
    gui._run_audio_task = lambda worker, success, error: callbacks.extend([success, error])
    events = []
    gui._start_audio_playback(player, Path("voice.wav"), events.append, events.append)
    player.reserve_request()  # Stop or a newer Play invalidates these callbacks.
    callbacks[0](object())
    callbacks[1](RuntimeError("old error"))
    assert events == []


def test_voice_lab_generation_is_queued_and_stop_discards_result():
    import threading
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    class Input:
        def __init__(self, value):
            self.value = value
        def get(self):
            return self.value
    gui._tts_provider_var = Input("Fake")
    gui._tts_model_var = Input("model")
    gui._tts_voice_var = Input("voice")
    gui._speech_preview_text_var = Input("Hello")
    gui._speech_progress_var = Var()
    gui._speech_preview_generation_id = 0
    gui._speech_preview_generation_lock = threading.Lock()
    gui._current_tts_default_language = lambda: "English"
    gui._selected_tts_voice = lambda: "voice"
    gui._piper_voice_missing = lambda *args: False
    calls = []
    gui._speech_service = types.SimpleNamespace(
        providers={"Fake": object()},
        generate=lambda *args: calls.append(args) or types.SimpleNamespace(path=Path("voice.wav")),
    )
    tasks = []
    gui._run_audio_task = lambda *args: tasks.append(args)
    gui._play_audio_in_app = lambda *args, **kwargs: calls.append("play")
    gui._record_activity = lambda *args: None
    gui._speech_preview_player = InternalAudioPlayer()
    gui._stop_audio_player = lambda *args: None
    gui._preview_tts_voice_sample()
    assert not calls  # Provider generation did not run on the UI thread.
    worker, success, error = tasks[0]
    result = worker()
    gui._stop_speech_preview()
    success(result)
    assert "play" not in calls
