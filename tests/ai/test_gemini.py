"""Tests for the Gemini vocabulary client."""

# Mock pozwala stworzyć "udawany" obiekt.
# Dzięki temu nie łączymy się z prawdziwym Gemini API.
from unittest.mock import Mock

# pytest daje nam fixture i mechanizm monkeypatch.
import pytest

# Importujemy klasę, którą chcemy testować.
from src.ai.providers.gemini import GeminiVocabularyClient


@pytest.fixture
def mock_genai_client(monkeypatch):
    """Create a fake Google Gemini client for tests."""

    # Tworzymy udawanego klienta Google.
    # Ten obiekt będzie zachowywał się jak prawdziwy klient,
    # ale niczego nie wyśle do internetu.
    fake_google_client = Mock()

    # W kodzie produkcyjnym masz:
    #
    # genai.Client(api_key=api_key)
    #
    # Dlatego podmieniamy dokładnie:
    #
    # src.ai.providers.gemini.genai.Client
    #
    # na Mock, który po wywołaniu zwróci fake_google_client.
    monkeypatch.setattr(
        "src.ai.providers.gemini.genai.Client",
        Mock(return_value=fake_google_client),
    )

    # Zwracamy mock klienta Google,
    # żeby testy mogły ustawiać jego zachowanie.
    return fake_google_client


@pytest.fixture
def gemini_client(mock_genai_client):
    """Create our GeminiVocabularyClient for tests."""

    # Ta fixture korzysta z poprzedniej fixture.
    #
    # Ponieważ genai.Client został już podmieniony,
    # konstruktor nie tworzy prawdziwego połączenia z Gemini.
    #
    # Klucz i model są sztuczne.
    return GeminiVocabularyClient(
        api_key="fake-api-key",
        model="gemini-test-model",
    )


def test_provider_name_returns_gemini(gemini_client):
    """The provider name should be Gemini."""

    # Act:
    # Pobieramy property provider_name.
    result = gemini_client.provider_name

    # Assert:
    # Sprawdzamy, czy klasa zwraca dokładnie "Gemini".
    assert result == "Gemini"


def test_generate_text_returns_response_text(
    gemini_client,
    mock_genai_client,
):
    """_generate_text should return text received from Gemini."""

    # ARRANGE
    # Tworzymy udawaną odpowiedź Gemini.
    fake_response = Mock()

    # Udajemy, że Gemini zwróciło tekst:
    fake_response.text = "Generated response"

    # W kodzie produkcyjnym wykonywane jest:
    #
    # self._client.models.generate_content(...)
    #
    # Dlatego ustawiamy:
    #
    # gdy generate_content zostanie wywołane,
    # zwróć fake_response.
    mock_genai_client.models.generate_content.return_value = fake_response

    # ACT
    # Wywołujemy prawdziwą metodę naszej klasy.
    result = gemini_client._generate_text("Test prompt")

    # ASSERT
    # Metoda powinna zwrócić response.text.
    assert result == "Generated response"


def test_generate_text_calls_gemini_with_model_and_prompt(
    gemini_client,
    mock_genai_client,
):
    """_generate_text should pass the correct model and prompt."""

    # ARRANGE
    # Tworzymy udawaną odpowiedź.
    fake_response = Mock()
    fake_response.text = "Generated response"

    # Ustawiamy, co ma zwrócić generate_content.
    mock_genai_client.models.generate_content.return_value = fake_response

    # ACT
    # Wywołujemy metodę z konkretnym promptem.
    gemini_client._generate_text("Test prompt")

    # ASSERT
    # Sprawdzamy, czy generate_content zostało wywołane:
    # - dokładnie jeden raz,
    # - z poprawnym modelem,
    # - z poprawnym promptem.
    mock_genai_client.models.generate_content.assert_called_once_with(
        model="gemini-test-model",
        contents="Test prompt",
    )


def test_generate_text_returns_empty_string_when_response_has_no_text(
    gemini_client,
    mock_genai_client,
):
    """_generate_text should return an empty string when text is missing."""

    # ARRANGE
    # Tworzymy odpowiedź bez tekstu.
    fake_response = Mock()
    fake_response.text = None

    # Ustawiamy tę odpowiedź jako wynik generate_content.
    mock_genai_client.models.generate_content.return_value = fake_response

    # ACT
    result = gemini_client._generate_text("Test prompt")

    # ASSERT
    # W kodzie produkcyjnym masz:
    #
    # return response.text or ""
    #
    # więc gdy text == None, wynik powinien być pustym stringiem.
    assert result == ""


def test_generate_card_uses_prompt_generator_and_parser(
    gemini_client,
    monkeypatch,
):
    """generate_card should build a prompt, generate text, and parse a card."""

    # ARRANGE

    # Udajemy funkcję build_vocabulary_prompt.
    #
    # Zamiast budować prawdziwy długi prompt,
    # ma po prostu zwrócić tekst "Vocabulary prompt".
    fake_prompt_builder = Mock(
        return_value="Vocabulary prompt"
    )

    # Udajemy metodę _generate_text.
    #
    # Nie chcemy tutaj testować API Gemini.
    # Chcemy tylko sprawdzić przepływ generate_card.
    fake_generate_text = Mock(
        return_value='{"word_or_phrase": "thorough"}'
    )

    # Tworzymy udawaną gotową kartę.
    fake_card = Mock()
    fake_card.is_valid = True
    fake_card.word_or_phrase = "thorough"

    # Udajemy parser.
    #
    # Gdy parser dostanie tekst JSON,
    # ma zwrócić fake_card.
    fake_parser = Mock(
        return_value=fake_card
    )

    # Podmieniamy prawdziwy build_vocabulary_prompt
    # w module gemini.py.
    monkeypatch.setattr(
        "src.ai.providers.gemini.build_vocabulary_prompt",
        fake_prompt_builder,
    )

    # Podmieniamy metodę _generate_text tylko na tym obiekcie.
    monkeypatch.setattr(
        gemini_client,
        "_generate_text",
        fake_generate_text,
    )

    # Podmieniamy parser tylko na tym obiekcie.
    monkeypatch.setattr(
        gemini_client,
        "_parse_card_response",
        fake_parser,
    )

    # ACT
    # Wywołujemy prawdziwą metodę generate_card.
    result = gemini_client.generate_card(
        word_or_phrase="thorough",
        target_language="English",
    )

    # ASSERT 1
    # Wynik powinien być dokładnie tym samym obiektem,
    # który zwrócił parser.
    assert result is fake_card

    # ASSERT 2
    # Sprawdzamy, czy prompt builder dostał poprawne argumenty.
    fake_prompt_builder.assert_called_once_with(
        "thorough",
        "English",
        "Polish",
    )

    # ASSERT 3
    # Sprawdzamy, czy wygenerowany prompt
    # został przekazany do _generate_text.
    fake_generate_text.assert_called_once_with(
        "Vocabulary prompt",
    )

    # ASSERT 4
    # Sprawdzamy, czy tekst z Gemini
    # został przekazany do parsera razem z nazwą providera.
    fake_parser.assert_called_once_with(
        '{"word_or_phrase": "thorough"}',
        "Gemini",
    )


def test_start_conversation_uses_prompt_generator_and_parser(
    gemini_client,
    monkeypatch,
):
    """start_conversation should build a prompt and parse the first question."""

    # ARRANGE

    # Udajemy builder promptu do rozpoczęcia rozmowy.
    fake_prompt_builder = Mock(
        return_value="Conversation start prompt"
    )

    # Udajemy odpowiedź Gemini.
    fake_generate_text = Mock(
        return_value='{"question": "How was your day?"}'
    )

    # Tworzymy udawany obiekt ConversationStart.
    fake_conversation_start = Mock()

    # Udajemy parser.
    fake_parser = Mock(
        return_value=fake_conversation_start
    )

    # Podmieniamy prawdziwe zależności.
    monkeypatch.setattr(
        "src.ai.providers.gemini.build_conversation_start_prompt",
        fake_prompt_builder,
    )

    monkeypatch.setattr(
        gemini_client,
        "_generate_text",
        fake_generate_text,
    )

    monkeypatch.setattr(
        gemini_client,
        "_parse_conversation_start",
        fake_parser,
    )

    # ACT
    result = gemini_client.start_conversation(
        topic="daily life",
        target_language="English",
    )

    # ASSERT 1
    # Metoda powinna zwrócić wynik parsera.
    assert result is fake_conversation_start

    # ASSERT 2
    # Prompt builder powinien dostać temat i język.
    fake_prompt_builder.assert_called_once_with(
        "daily life",
        "English",
    )

    # ASSERT 3
    # _generate_text powinno dostać prompt.
    fake_generate_text.assert_called_once_with(
        "Conversation start prompt",
    )

    # ASSERT 4
    # Parser powinien dostać surowy tekst i nazwę providera.
    fake_parser.assert_called_once_with(
        '{"question": "How was your day?"}',
        "Gemini",
    )


def test_review_conversation_answer_uses_prompt_generator_and_parser(
    gemini_client,
    monkeypatch,
):
    """review_conversation_answer should build a prompt and parse feedback."""

    # ARRANGE

    # Udajemy builder promptu do feedbacku.
    fake_prompt_builder = Mock(
        return_value="Conversation feedback prompt"
    )

    # Udajemy surową odpowiedź Gemini.
    fake_generate_text = Mock(
        return_value='{"feedback_pl": "Good answer."}'
    )

    # Tworzymy udawany obiekt ConversationFeedback.
    fake_feedback = Mock()

    # Udajemy parser.
    fake_parser = Mock(
        return_value=fake_feedback
    )

    # Podmieniamy prawdziwe zależności.
    monkeypatch.setattr(
        "src.ai.providers.gemini.build_conversation_feedback_prompt",
        fake_prompt_builder,
    )

    monkeypatch.setattr(
        gemini_client,
        "_generate_text",
        fake_generate_text,
    )

    monkeypatch.setattr(
        gemini_client,
        "_parse_conversation_feedback",
        fake_parser,
    )

    # ACT
    # Wywołujemy prawdziwą metodę.
    result = gemini_client.review_conversation_answer(
        topic="travel",
        question="Where did you go?",
        answer="I went to Tenerife.",
        target_language="English",
        improvement_level="Natural B1/B2",
    )

    # ASSERT 1
    # Metoda powinna zwrócić wynik parsera.
    assert result is fake_feedback

    # ASSERT 2
    # Prompt builder powinien dostać wszystkie dane rozmowy.
    fake_prompt_builder.assert_called_once_with(
        "travel",
        "Where did you go?",
        "I went to Tenerife.",
        "English",
        "Natural B1/B2",
    )

    # ASSERT 3
    # _generate_text powinno dostać gotowy prompt.
    fake_generate_text.assert_called_once_with(
        "Conversation feedback prompt",
    )

    # ASSERT 4
    # Parser powinien dostać tekst z modelu i nazwę providera.
    fake_parser.assert_called_once_with(
        '{"feedback_pl": "Good answer."}',
        "Gemini",
    )