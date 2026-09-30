import queue
import sys
import types

if "customtkinter" not in sys.modules:
    ctk_stub = types.ModuleType("customtkinter")
    ctk_stub.BooleanVar = object
    ctk_stub.StringVar = object
    sys.modules["customtkinter"] = ctk_stub

from src.ui.modern_gui import ModernVocabularyGui


class _Var:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _Root:
    def __init__(self):
        self.after_calls = []

    def after(self, delay_ms, callback):
        self.after_calls.append((delay_ms, callback))
        return "after-id"


def test_auto_queue_starts_provider_work_outside_tk_thread(monkeypatch):
    started = {}

    class FakeThread:
        def __init__(self, *, target, name, daemon):
            started["target"] = target
            started["name"] = name
            started["daemon"] = daemon

        def start(self):
            started["started"] = True

    monkeypatch.setattr("src.ui.modern_gui.threading.Thread", FakeThread)

    fake_client = object()
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._batch_generation_in_flight = False
    gui._batch_processing_index = None
    gui._batch_worker_results = queue.Queue()
    gui._batch_auto_generate_stop_requested = False
    gui._batch_auto_generate_paused = False
    gui._batch_auto_generate_running = True
    gui._batch_auto_provider_name = "Groq"
    gui._batch_auto_model_name = "openai/gpt-oss-20b"
    gui._batch_auto_target_language = "English"
    gui._batch_auto_explanation_language = "Polish"
    gui._batch_auto_mode = "Vocabulary"
    gui._batch_auto_topic_context = ""
    gui._batch_items = [
        {
            "word": "common",
            "status": "pending",
            "batch_mode": "Vocabulary",
            "mode_locked": True,
        }
    ]
    gui._batch_index = 0
    gui._ai_clients = {"Groq": fake_client}
    gui._provider_var = _Var("Groq")
    gui._language_var = _Var("English")
    gui._explanation_language_var = _Var("Polish")
    gui._batch_mode_var = _Var("Vocabulary")
    gui._batch_topic_var = _Var("")
    gui._batch_status_var = _Var("")
    gui._status_var = _Var("")
    gui._root = _Root()

    gui._auto_generate_next_pending_batch_card()

    assert started["started"] is True
    assert started["daemon"] is True
    assert started["name"] == "queue-ai-0"
    assert gui._batch_generation_in_flight is True
    assert gui._batch_processing_index == 0
    assert gui._root.after_calls
    delay_ms, callback = gui._root.after_calls[-1]
    assert delay_ms == 50
    assert callback == gui._poll_background_batch_generation
    # The provider target is only stored in the background thread; it was not
    # executed synchronously by the Tk/UI call above.
    assert callable(started["target"])
