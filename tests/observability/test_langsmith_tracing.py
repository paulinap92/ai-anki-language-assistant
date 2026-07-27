from src.ai.base import VocabularyAiClient
from src.domain.models import ConversationFeedback, ConversationStart, GrammarAnalysis, VocabularyCard
from src.observability import configure_llmops, get_llmops_tracer, wrap_ai_client


class DummyClient(VocabularyAiClient):
    _model = "dummy-model"

    @property
    def provider_name(self) -> str:
        return "Dummy"

    def generate_card(self, word_or_phrase, target_language, explanation_language, topic_context=""):
        return VocabularyCard(
            word_or_phrase=word_or_phrase,
            target_language=target_language,
            part_of_speech="phrase",
            definition="test definition",
            translation="test",
            example=f"This is {word_or_phrase}.",
            example_translation="test",
            synonyms=[],
            collocations=[],
            grammar_note="",
            explanation_language=explanation_language,
        )

    def start_conversation(self, topic, target_language):
        return ConversationStart(question=f"Question about {topic}?")

    def analyze_grammar(self, sentence, target_language):
        return GrammarAnalysis(
            sentence=sentence,
            target_language=target_language,
            meaning="meaning",
            structure="structure",
            breakdown=[],
            usage="usage",
            context_example=sentence,
            contrasts=[],
            common_mistakes=[],
        )

    def generate_grammar_card(self, grammar_item, target_language, topic_context=""):
        return self.analyze_grammar(f"Example for {grammar_item}.", target_language)

    def generate_sentence_card(self, raw_item, target_language, explanation_language, topic_context=""):
        return self.generate_card(raw_item.split("|")[0].strip(), target_language, explanation_language, topic_context)

    def review_conversation_answer(self, topic, question, answer, target_language, improvement_level, feedback_language):
        return ConversationFeedback(
            feedback_language=feedback_language,
            feedback="ok",
            corrections=[],
            corrected_version=answer,
            advanced_answer=answer,
            mini_practice="",
            next_question="Next?",
            suggested_vocabulary=["useful phrase"],
        )


def test_wrapper_logs_local_event_when_langsmith_disabled():
    configure_llmops(
        enabled=False,
        project_name="test-project",
        api_key=None,
        redact_inputs=True,
    )
    tracer = get_llmops_tracer()
    tracer.clear_events()

    client = wrap_ai_client(DummyClient())
    card = client.generate_card("short fuse", "English", "Polish")

    assert card.word_or_phrase == "short fuse"
    events = tracer.snapshot_events()
    assert events
    assert events[0].feature == "vocabulary_card_generation"
    assert events[0].provider == "Dummy"
    assert events[0].sent_to_langsmith is False


def test_redaction_summarizes_text_values():
    configure_llmops(
        enabled=False,
        project_name="test-project",
        api_key=None,
        redact_inputs=True,
    )
    tracer = get_llmops_tracer()

    sanitized = tracer.sanitize_value({"source_text": "one two three"})

    assert sanitized["source_text"].startswith("<redacted text")
    assert "words=3" in sanitized["source_text"]
