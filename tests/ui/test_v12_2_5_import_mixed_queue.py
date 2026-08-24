from __future__ import annotations

import sys
import types

# CI for the clean source package may not install the desktop-only CustomTkinter
# dependency. The tests below exercise pure/import-routing methods without
# constructing a GUI, so a minimal import stub is sufficient.
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


class _Tabs:
    def __init__(self):
        self.selected = None

    def set(self, value):
        self.selected = value


def _bare_gui(candidates: list[dict[str, str]]) -> ModernVocabularyGui:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._ocr_candidate_items = candidates
    gui._ocr_candidate_vars = [_Var(True) for _ in candidates]
    gui._batch_topic_var = _Var("")
    gui._language_var = _Var("English")
    gui._explanation_language_var = _Var("Polish")
    gui._batch_mode_var = _Var("Provided examples")
    gui._batch_mode_help_var = _Var("")
    gui._batch_source_summary_var = _Var("")
    gui._ocr_candidate_status_var = _Var("")
    gui._tabs = _Tabs()
    gui._batch_items = []
    gui._batch_index = 0
    gui._batch_autosave_path = None
    gui._batch_generated_card = None
    gui._batch_generated_provider_name = None
    gui._batch_generated_grammar = None
    gui._show_current_batch_item = lambda generate=False: None
    gui._update_batch_mode_help = lambda: None
    gui._autosave_batch_session = lambda *args, **kwargs: None
    gui._cleanup_runtime_memory = lambda *args, **kwargs: None
    gui._record_activity = lambda *args, **kwargs: None
    return gui


def test_long_import_is_split_without_losing_tail() -> None:
    tail = "UNIQUE_END_OF_SOURCE_918273"
    text = ("paragraph one words " * 1800) + "\n\n" + ("paragraph two words " * 1800) + tail
    chunks = ModernVocabularyGui._split_import_text_for_ai(text)
    assert len(chunks) >= 2
    assert tail in chunks[-1]
    assert sum(len(chunk) for chunk in chunks) >= len(text)


def test_material_size_summary_says_entire_source_is_analysed() -> None:
    text = "word " * 10000
    summary = ModernVocabularyGui._import_material_size_summary(text)
    assert "AI candidate search will analyse the entire source" in summary
    assert "Nothing will be silently cut off" in summary
    assert "No fixed candidate count" in summary


def test_smart_vocab_merge_does_not_force_a_fixed_candidate_count() -> None:
    explicit = [
        {"type": "vocabulary", "target": f"explicit-{i}", "sentence": "", "source_section": "vocabulary_list"}
        for i in range(10)
    ]
    prose = [
        {"type": "vocabulary", "target": f"prose-{i}", "sentence": "", "source_section": "reading_text"}
        for i in range(150)
    ]
    merged, note = ModernVocabularyGui._limit_merged_import_candidates(explicit + prose, "Smart vocabulary")
    assert len(merged) == 160
    assert all(any(item["target"] == f"explicit-{i}" for item in merged) for i in range(10))
    assert note == ""


def test_definition_is_not_treated_as_source_example() -> None:
    assert not ModernVocabularyGui._import_source_sentence_uses_target(
        "cronyism",
        "The practice of favouring close friends, associates, or political allies when appointing people to positions of power.",
    )
    assert ModernVocabularyGui._import_source_sentence_uses_target(
        "cronyism",
        "Cronyism in public appointments can undermine trust in government.",
    )


def test_import_material_keeps_per_item_types_in_queue() -> None:
    gui = _bare_gui(
        [
            {
                "type": "vocabulary",
                "target": "cronyism",
                "sentence": "Cronyism in politics can undermine trust.",
                "source": "AI all text",
            },
            {
                "type": "grammar",
                "target": "used to + infinitive",
                "sentence": "I used to live near the sea.",
                "source": "AI all text",
                "source_type": "structure_sentence",
            },
            {
                "type": "provided_example",
                "target": "bounce back",
                "sentence": "She bounced back quickly after the setback.",
                "source": "AI all text",
            },
        ]
    )

    gui._send_ocr_candidates_to_batch()

    assert [item["batch_mode"] for item in gui._batch_items] == [
        "Vocabulary",
        "Grammar",
        "Provided examples",
    ]
    assert all(item["mode_locked"] is True for item in gui._batch_items)
    assert gui._batch_items[0]["generation_strategy"] == "preserve_source_sentence"
    assert gui._batch_items[0]["word"] == "cronyism"
    assert "Each imported item keeps its own type" in gui._batch_source_summary_var.get()


def test_vocabulary_definition_stays_context_not_provided_example() -> None:
    gui = _bare_gui(
        [
            {
                "type": "vocabulary",
                "target": "cronyism",
                "sentence": "The practice of favouring close friends or allies regardless of merit.",
                "source": "AI all text",
            }
        ]
    )

    gui._send_ocr_candidates_to_batch()

    item = gui._batch_items[0]
    assert item["batch_mode"] == "Vocabulary"
    assert item["source_definition"].startswith("The practice of favouring")
    assert "provided_sentence" not in item
    assert item["generation_strategy"] == "generate_example_from_definition"


def test_queue_wide_mode_change_does_not_reclassify_imported_items() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    gui._batch_mode_var = _Var("Provided examples")
    gui._batch_mode_help_var = _Var("")
    gui._batch_items = [
        {"word": "cronyism", "batch_mode": "Vocabulary", "mode_locked": True, "status": "pending"},
        {"word": "used to + infinitive", "batch_mode": "Grammar", "mode_locked": True, "status": "pending"},
    ]
    gui._update_batch_mode_help = lambda: None
    gui._show_current_batch_item = lambda generate=False: None
    gui._autosave_batch_session = lambda *args, **kwargs: None
    gui._record_activity = lambda *args, **kwargs: None

    gui._on_batch_mode_changed("Provided examples")

    assert [item["batch_mode"] for item in gui._batch_items] == ["Vocabulary", "Grammar"]

class _Root:
    def update_idletasks(self):
        return None


class _Ai:
    def __init__(self):
        self.sentence_requests: list[str] = []

    def generate_sentence_card(self, value, target_language, explanation_language, topic_context):
        from src.domain.models import VocabularyCard

        self.sentence_requests.append(value)
        target, sentence = [part.strip() for part in value.split("|", 1)]
        return VocabularyCard(
            word_or_phrase=target,
            target_language=target_language,
            explanation_language=explanation_language,
            part_of_speech="noun",
            definition="definition",
            translation="translation",
            example=sentence,
            example_translation="translation",
            synonyms=[],
            collocations=[],
            grammar_note="",
            used_form_in_example=target,
            example_uses_target=True,
        )


def test_vocabulary_with_source_sentence_uses_sentence_prompt_but_stays_vocabulary() -> None:
    gui = ModernVocabularyGui.__new__(ModernVocabularyGui)
    ai = _Ai()
    item = {
        "word": "cronyism",
        "status": "pending",
        "batch_mode": "Vocabulary",
        "mode_locked": True,
        "duplicate_prechecked": True,
        "provided_target": "cronyism",
        "source_sentence": "Cronyism in politics can undermine trust.",
        "provided_sentence": "Cronyism in politics can undermine trust.",
        "generation_strategy": "preserve_source_sentence",
        "target_language": "English",
        "explanation_language": "Polish",
    }
    gui._batch_items = [item]
    gui._batch_index = 0
    gui._batch_word_var = _Var("cronyism")
    gui._batch_topic_var = _Var("")
    gui._language_var = _Var("English")
    gui._explanation_language_var = _Var("Polish")
    gui._batch_mode_var = _Var("Provided examples")
    gui._provider_var = _Var("Dummy")
    gui._batch_status_var = _Var("")
    gui._status_var = _Var("")
    gui._root = _Root()
    gui._current_ai_client = lambda: ai
    gui._current_ai_model_name = lambda *args, **kwargs: "dummy-model"
    gui._current_batch_topic = lambda: ""
    gui._quality_warnings_for_card = lambda *args, **kwargs: []
    gui._set_batch_preview = lambda *args, **kwargs: None
    gui._update_batch_progress = lambda: None
    gui._autosave_batch_session = lambda *args, **kwargs: None

    gui._generate_current_batch_card()

    assert ai.sentence_requests == ["cronyism | Cronyism in politics can undermine trust."]
    assert item["batch_mode"] == "Vocabulary"
    assert item["resolved_mode"] == "Vocabulary"
    assert item["status"] == "ready"
