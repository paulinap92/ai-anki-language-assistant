from src.conversation import (
    build_anki_note_conversation_material,
    build_flashcard_conversation_material,
)
from src.domain.models import VocabularyCard


def test_flashcard_context_uses_generated_vocabulary_card():
    card = VocabularyCard(
        word_or_phrase="dar cuenta de",
        target_language="Spanish",
        part_of_speech="phrase",
        definition="Informar sobre algo.",
        translation="relacjonować",
        example="El informe da cuenta de los avances.",
        example_translation="Raport przedstawia postępy.",
        synonyms=[],
        collocations=["dar cuenta de los resultados"],
        grammar_note="",
        explanation_language="Polish",
    )

    rows, targets, total = build_flashcard_conversation_material([
        {"word": "dar cuenta de", "status": "ready", "card": card.model_dump()}
    ])

    assert total == 1
    assert targets == ["dar cuenta de"]
    assert "EXAMPLE: El informe da cuenta de los avances." in rows[0]
    assert "MEANING: relacjonować" in rows[0]


def test_flashcard_context_splits_pending_provided_example():
    rows, targets, total = build_flashcard_conversation_material([
        {
            "word": "aunar | Debemos aunar la Filología y la Informática.",
            "status": "pending",
            "batch_mode": "Provided examples",
        }
    ])

    assert total == 1
    assert targets == ["aunar"]
    assert "SOURCE EXAMPLE: Debemos aunar la Filología y la Informática." in rows[0]


def test_flashcard_context_skips_failed_items_and_respects_limit():
    rows, targets, total = build_flashcard_conversation_material(
        [
            {"word": "skip me", "status": "error", "batch_mode": "Vocabulary"},
            {"word": "uno", "status": "pending", "batch_mode": "Vocabulary"},
            {"word": "dos", "status": "pending", "batch_mode": "Vocabulary"},
        ],
        limit=1,
    )

    assert total == 2
    assert len(rows) == 1
    assert targets == ["uno"]


def test_anki_deck_context_uses_vocabulary_fields():
    rows, targets, total = build_anki_note_conversation_material([
        {
            "model": "AI Vocabulary Light Card",
            "word": "dar cuenta de",
            "fields": {
                "Word": "dar cuenta de",
                "Translation": "relacjonować",
                "Definition": "Informar sobre algo.",
                "Example": "El informe da cuenta de los avances.",
                "Collocations": "dar cuenta de los resultados",
            },
        }
    ])

    assert total == 1
    assert targets == ["dar cuenta de"]
    assert "MEANING: relacjonować" in rows[0]
    assert "EXAMPLE: El informe da cuenta de los avances." in rows[0]


def test_anki_deck_context_supports_grammar_cards():
    rows, targets, total = build_anki_note_conversation_material([
        {
            "model": "AI Grammar Light Card",
            "word": "Está en nuestra mano que + subjuntivo",
            "fields": {
                "Sentence": "Está en nuestra mano que el futuro no se pinte de negro.",
                "Structure": "estar en manos de alguien que + subjuntivo",
                "Meaning": "zależeć od kogoś",
                "Usage": "Se usa para expresar responsabilidad o control.",
            },
        }
    ])

    assert total == 1
    assert targets == ["estar en manos de alguien que + subjuntivo"]
    assert "GRAMMAR TARGET:" in rows[0]
    assert "USE: Se usa para expresar responsabilidad" in rows[0]


def test_anki_deck_context_strips_html_and_deduplicates():
    notes = [
        {"model": "Basic", "word": "aunar", "fields": {"Front": "<b>aunar</b>", "Back": "połączyć"}},
        {"model": "Basic", "word": "aunar", "fields": {"Front": "aunar", "Back": "scalać"}},
    ]

    rows, targets, total = build_anki_note_conversation_material(notes)

    assert total == 1
    assert targets == ["aunar"]
    assert "<b>" not in rows[0]



def test_anki_basic_back_is_preserved_as_card_back_not_example():
    rows, targets, total = build_anki_note_conversation_material([
        {
            "model": "Basic",
            "word": "clase magistral",
            "fields": {
                "Front": "clase magistral",
                "Back": "wykład akademicki",
            },
        }
    ])

    assert total == 1
    assert targets == ["clase magistral"]
    assert "CARD BACK: wykład akademicki" in rows[0]
    assert "EXAMPLE: wykład akademicki" not in rows[0]
