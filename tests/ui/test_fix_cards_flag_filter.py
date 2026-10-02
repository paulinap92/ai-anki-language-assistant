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


def test_any_flag_means_any_nonzero_anki_flag() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._existing_flag_var = _Var("Any flag (flagged only)")

    assert gui._existing_flag_query() == "-flag:0"


def test_no_flag_filter_keeps_search_unrestricted_by_flags() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._existing_flag_var = _Var("No flag filter")

    assert gui._existing_flag_query() == ""


def test_specific_and_no_flag_filters_keep_anki_syntax() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._existing_flag_var = _Var("Blue flag (flag:4)")
    assert gui._existing_flag_query() == "flag:4"

    gui._existing_flag_var.set("No flag (flag:0)")
    assert gui._existing_flag_query() == "flag:0"


def test_load_flagged_switches_no_filter_to_any_flag() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._existing_flag_var = _Var("No flag filter")
    called = []
    gui._load_existing_cards = lambda: called.append(True)  # type: ignore[method-assign]

    gui._load_flagged_existing_cards()

    assert gui._existing_flag_var.get() == "Any flag (flagged only)"
    assert called == [True]
