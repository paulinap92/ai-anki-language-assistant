from src.ui.modern_gui import ModernVocabularyGui


def test_local_target_sentence_pairs_parse_pipe_format():
    text = """pick up | I think things pick up then.\nlined up | Have you got anything lined up or any interviews?\nhit the nail on the head | I think you hit the nail on the head."""
    assert ModernVocabularyGui._local_target_sentence_pairs(text) == [
        ("pick up", "I think things pick up then."),
        ("lined up", "Have you got anything lined up or any interviews?"),
        ("hit the nail on the head", "I think you hit the nail on the head."),
    ]


def test_local_target_sentence_pairs_parse_tsv_format():
    assert ModernVocabularyGui._local_target_sentence_pairs(
        "context window\tI think it has a bigger context window."
    ) == [("context window", "I think it has a bigger context window.")]


def test_local_target_sentence_pairs_preserve_repeated_target_with_different_examples():
    text = """in your own words | Can you describe it in your own words?\nin your own words | Explain it in your own words."""
    assert ModernVocabularyGui._local_target_sentence_pairs(text) == [
        ("in your own words", "Can you describe it in your own words?"),
        ("in your own words", "Explain it in your own words."),
    ]


def test_local_target_sentence_pairs_deduplicate_exact_rows_only():
    text = """make sure | You need to make sure it's practical.\nmake sure | You need to make sure it's practical."""
    assert ModernVocabularyGui._local_target_sentence_pairs(text) == [
        ("make sure", "You need to make sure it's practical."),
    ]


def test_plain_sentences_are_not_misparsed_as_pairs():
    assert ModernVocabularyGui._local_target_sentence_pairs(
        "The model makes a prediction.\nThe system calculates the error."
    ) == []
