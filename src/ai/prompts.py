"""Prompt templates for vocabulary, conversation, and grammar features."""

from __future__ import annotations


VOCABULARY_PROMPT_VERSION = "v5-topic-quality-validation"
EXPLANATION_LANGUAGES = ["Polish", "English", "Spanish", "German", "Italian", "No translation"]


TOPIC_PRESET_HINTS = {
    "character": (
        "When the topic is character/personality, the example MUST describe a person's "
        "personality, behaviour, attitude, emotional tendency, or interpersonal reaction."
    ),
    "personality": (
        "When the topic is character/personality, the example MUST describe a person's "
        "personality, behaviour, attitude, emotional tendency, or interpersonal reaction."
    ),
    "charakter": (
        "When the topic is character/personality, the example MUST describe a person's "
        "personality, behaviour, attitude, emotional tendency, or interpersonal reaction."
    ),
    "work": "When the topic is work, keep examples in professional, office, factory, interview, or career contexts.",
    "laboral": "When the topic is work, keep examples in professional, office, factory, interview, or career contexts.",
    "travel": "When the topic is travel, keep examples in trips, transport, accommodation, holidays, or local exploration contexts.",
    "health": "When the topic is health, keep examples in body, wellbeing, habits, symptoms, medical appointments, or lifestyle contexts.",
    "food": "When the topic is food, keep examples in restaurants, cooking, taste, meals, or food culture contexts.",
    "technology": "When the topic is technology, keep examples in software, data, AI, devices, tools, or digital workflows.",
    "education": "When the topic is education, keep examples in learning, courses, studying, exams, or academic contexts.",
}


def _language_quality_rules(explanation_language: str, target_language: str) -> str:
    """Return language-specific output rules for translations/explanations."""
    language = explanation_language.strip().casefold()
    if language == "no translation":
        return (
            "Explanation-language rules:\n"
            "- No translation mode is selected.\n"
            "- Return empty strings for translation_pl, example_pl, and grammar_note.\n"
            "- Do not sneak translations or bilingual explanations into other fields.\n"
        )

    base = (
        "Explanation-language rules:\n"
        f"- Write translation_pl, example_pl, and grammar_note in {explanation_language}.\n"
        f"- Do not mix {explanation_language} with Polish, Spanish, English, German, Italian, Russian, or Ukrainian unless the expression itself requires a quoted foreign word.\n"
        "- Do not use Cyrillic characters unless the selected explanation language explicitly uses Cyrillic.\n"
        "- Use natural, idiomatic wording, not literal machine translation.\n"
    )
    if language == "polish":
        return base + (
            "- Polish must be natural and correctly spelled.\n"
            "- Hard bad examples to avoid: 'nostalgja' (use 'nostalgia'), 'głęboka smutek' (use 'głęboki smutek'), 'область живота' (use 'okolica brzucha' if that meaning is intended).\n"
            "- Check adjective-noun agreement and basic case/gender agreement in Polish.\n"
        )
    if language == "spanish":
        return base + (
            "- Spanish must sound natural for a Spanish learner context.\n"
            "- Do not use Polish explanations or Polish diacritics in Spanish explanation fields.\n"
        )
    if language == "english":
        return base + (
            "- English explanations must be simple, natural, and learner-friendly.\n"
            "- Do not use Polish or Spanish translations in English explanation fields.\n"
        )
    if language == "german":
        return base + "- German explanations must use natural German wording and correct capitalization.\n"
    if language == "italian":
        return base + "- Italian explanations must use natural Italian wording.\n"
    return base + f"- If you cannot reliably write in {explanation_language}, add a warning in quality_warnings.\n"


def _topic_rules(topic_context: str) -> str:
    """Return user-topic rules plus optional preset hints.

    The topic is always user-defined. Presets are only extra hints when the text
    clearly contains a known domain.
    """
    topic_context = topic_context.strip()
    if not topic_context:
        return ""
    lowered = topic_context.casefold()
    hints: list[str] = []
    for token, hint in TOPIC_PRESET_HINTS.items():
        if token in lowered and hint not in hints:
            hints.append(hint)

    extra = "\n".join(f"- {hint}" for hint in hints)
    if extra:
        extra = "\nOptional preset hints detected from the user topic:\n" + extra

    return f"""
Topic / section rules:
Topic/context rules:
- User topic/context: "{topic_context}".
- Treat the user topic as a hard constraint / hard context constraint for the example sentence and usage notes.
- The user can type any topic. Do not reject unknown topics just because they are not in a preset list.
- The example must clearly fit the user topic, unless the input phrase genuinely cannot be used naturally in that topic.
- If the input does not naturally fit the topic, still keep the exact input, generate the most natural card, and set topic_fit to "weak" or "mismatch" with a short topic_warning.
- Do not drift into generic business, travel, technology, food, health, or abstract contexts unless the user topic points there.
{extra}
"""


def build_vocabulary_prompt(
    word_or_phrase: str,
    target_language: str,
    explanation_language: str = "Polish",
    topic_context: str = "",
) -> str:
    """Build a validated, word-first vocabulary flashcard prompt."""
    no_translation = explanation_language == "No translation"
    explanation_rules = _language_quality_rules(explanation_language, target_language)
    topic_rules = _topic_rules(topic_context)

    return f"""
You are a professional {target_language} language teacher and flashcard quality reviewer.

Create ONE high-quality vocabulary flashcard for this exact user input:

"{word_or_phrase}"

Target language: {target_language}
Explanation language: {explanation_language}

Internal process:
1. Validate whether the input is a real, correctly formed word, phrase, idiom, or fixed expression in {target_language}.
2. Treat the complete input as one lexical unit before analysing individual words.
3. Preserve the exact input for valid cards.
4. Identify the phrase-level meaning, natural collocations, grammar patterns, and normal usage.
5. Apply the user topic/context if provided.
6. Generate a simple, natural example that demonstrates the selected meaning.
7. Run a final quality self-check for spelling, language mixing, topic fit, naturalness, collocations, and JSON validity.

Validation rules:
- If the input is misspelled, malformed, invented, or not a valid expression, set is_valid to false.
- For invalid input, do not invent a definition or example.
- Explain the problem briefly in validation_error using {explanation_language if not no_translation else target_language}.
- Suggest a correction only when reasonably confident; otherwise return an empty string.
- For invalid input, return empty strings/lists for all flashcard content fields.

Exact-input rules:
- For valid input, word_or_phrase must exactly match: "{word_or_phrase}".
- Never replace it with a synonym, related expression, corrected phrase, or a different word.
- Corrections belong only in suggested_correction when is_valid is false.

Phrase-level meaning rules:
- Treat the entire user input as one lexical unit.
- For multi-word expressions, compounds, idioms, and fixed phrases, determine the established meaning of the complete expression before analysing individual words.
- Do not infer the meaning by translating or defining each component separately.
- Prefer the established phrase meaning over a literal interpretation.

Definition and explanation rules:
- The definition must be short, clear, and written in {target_language}.
- The definition must not be a translation into {explanation_language}.
{explanation_rules}

Example rules:
{topic_rules}- Select context from the meaning and common usage of the expression.
- Prefer common, realistic usage over creative or unusual examples.
- Reject sentences that are grammatical but pragmatically unnatural.
- The sentence must sound natural to a native speaker and clearly demonstrate the meaning.

Synonym and collocation rules:
- Return only useful, established synonyms or close alternatives.
- Return only established, commonly used collocations or usage patterns.
- Do not create combinations merely because they are grammatically possible.
- Return fewer items when fewer reliable items exist.

Quality self-check rules:
- Return quality_warnings as an array of short strings. Use [] if there are no warnings.
- Set topic_fit to one of: "ok", "weak", "mismatch", "not_applicable".
- If no user topic/context was provided, use topic_fit "not_applicable" and topic_warning "".
- If the topic fit is weak or mismatch, explain briefly in topic_warning.
- Add a warning for any suspected language mixing, spelling issue, unnatural example, weak topic fit, empty required field, or uncertain translation.
- Do not hide problems. If unsure, add a warning rather than pretending the card is perfect.

Return ONLY valid JSON. Do not use markdown. Do not include comments outside JSON.

Return this exact JSON structure:

{{
  "is_valid": true,
  "validation_error": "",
  "suggested_correction": "",
  "explanation_language": "{explanation_language}",
  "word_or_phrase": "{word_or_phrase}",
  "target_language": "{target_language}",
  "part_of_speech": "string",
  "definition": "string",
  "translation_pl": "string",
  "example": "string",
  "example_pl": "string",
  "synonyms": ["string"],
  "collocations": ["string"],
  "grammar_note": "string",
  "topic_fit": "ok",
  "topic_warning": "",
  "quality_warnings": []
}}
"""


def build_conversation_start_prompt(topic: str, target_language: str) -> str:
    """Build a prompt for the first question in conversation practice."""
    return f"""
You are a supportive {target_language} conversation teacher.
Start a short conversation in {target_language} about: "{topic}"
Ask ONE natural, open question suitable for a 2-5 sentence answer.
Return ONLY valid JSON without markdown:
{{"question": "string"}}
"""


def build_conversation_feedback_prompt(
    topic: str,
    question: str,
    answer: str,
    target_language: str,
    improvement_level: str,
) -> str:
    """Build a prompt for reviewing one answer and continuing a conversation."""
    return f"""
You are a supportive {target_language} conversation teacher helping a Polish speaker.
Conversation topic: "{topic}"
Question: "{question}"
Learner answer: "{answer}"
Requested level: "{improvement_level}"

Requirements:
- Give short practical feedback in Polish.
- Preserve the learner's idea in "corrected_version".
- Write a richer natural "advanced_answer" appropriate to {improvement_level}.
- Ask one natural follow-up question.
- Suggest exactly 3 useful words or phrases.
- Return ONLY valid JSON without markdown.

{{
  "feedback_pl": "string",
  "corrected_version": "string",
  "advanced_answer": "string",
  "next_question": "string",
  "suggested_vocabulary": ["string", "string", "string"]
}}
"""


def build_grammar_analysis_prompt(sentence: str, target_language: str) -> str:
    """Build a prompt for explaining grammar through one natural sentence."""
    return f"""
You are a professional {target_language} teacher.

Analyze this sentence for a learner:

"{sentence}"

Use ONLY {target_language} in every explanation. Do not translate the sentence
into Polish or any other language.

Requirements:
- Preserve the original sentence exactly in "sentence".
- Explain its meaning with a simple natural paraphrase in {target_language}.
- Identify the most useful grammar structure, not every possible grammar detail.
- Keep the explanation practical and suitable for a flashcard.
- Break the structure into 2-4 short, useful parts.
- Explain when and why a speaker would use this structure.
- Give ONE natural context containing the original sentence.
- Provide 1-3 concise contrasts with genuinely similar structures.
- Provide 1-3 common mistakes with corrected forms.
- Do not create a long academic grammar lesson.
- Return ONLY valid JSON.
- Do not use markdown or comments outside JSON.

Return this exact JSON structure:

{{
  "sentence": "{sentence}",
  "target_language": "{target_language}",
  "meaning": "string",
  "structure": "string",
  "breakdown": ["string", "string"],
  "usage": "string",
  "context_example": "string",
  "contrasts": ["string", "string"],
  "common_mistakes": ["string", "string"]
}}
"""
