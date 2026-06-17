"""Prompt templates for vocabulary, conversation, and grammar features."""

from __future__ import annotations


VOCABULARY_PROMPT_VERSION = "v4-phrase-level-meaning"
EXPLANATION_LANGUAGES = ["Polish", "English", "Spanish", "German", "Italian", "No translation"]


def build_vocabulary_prompt(
    word_or_phrase: str,
    target_language: str,
    explanation_language: str = "Polish",
) -> str:
    """Build a validated, word-first vocabulary flashcard prompt."""
    no_translation = explanation_language == "No translation"
    explanation_rules = (
        f"Provide translations and the short grammar note in {explanation_language}."
        if not no_translation
        else (
            "Do not translate the word or example. Return empty strings for "
            '"translation_pl", "example_pl", and "grammar_note".'
        )
    )

    return f"""
You are a professional {target_language} language teacher.

Create ONE high-quality vocabulary flashcard for this exact user input:

"{word_or_phrase}"

Target language: {target_language}
Explanation language: {explanation_language}

Follow this process internally:
1. Validate whether the input is a real, correctly formed word or phrase in {target_language}.
2. Treat the complete input as one lexical unit before analysing individual words.
3. If valid, preserve the exact input and identify its established, context-appropriate meaning.
4. Identify natural collocations, grammar patterns, and normal usage of the complete expression.
5. Choose a realistic context based on that meaning.
6. Generate a simple, natural example that demonstrates the selected meaning.
7. Verify spelling, naturalness, collocations, phrase-level meaning, and JSON validity.

Validation rules:
- If the input is misspelled, malformed, invented, or not a valid expression, set "is_valid" to false.
- For invalid input, do not invent a definition or example.
- Explain the problem briefly in "validation_error" using {explanation_language if not no_translation else target_language}.
- Suggest a correction only when reasonably confident; otherwise return an empty string.
- For invalid input, return empty strings/lists for all flashcard content fields.

Exact-input rules:
- For valid input, "word_or_phrase" must exactly match: "{word_or_phrase}".
- Never replace it with a synonym, related expression, corrected phrase, or a different word.
- Corrections belong only in "suggested_correction" when "is_valid" is false.

Phrase-level meaning rules:
- Treat the entire user input as one lexical unit.
- For multi-word expressions, compounds, idioms, and fixed phrases, determine the established meaning of the complete expression before analysing individual words.
- Do not infer the meaning by translating or defining each component separately.
- Check whether the full phrase has a conventional meaning in educational, professional, cultural, regional, or idiomatic usage.
- Prefer the established phrase meaning over a literal interpretation.
- If more than one meaning is common, choose the one best supported by typical usage and keep the example consistent with that meaning.

Definition and explanation rules:
- The definition must be short, clear, and written in {target_language}.
- {explanation_rules}
- Never invent words, translations, or phonetic approximations.
- Any translation must match the exact meaning used in the example.

Example rules:
- Select context from the meaning and common usage of the expression.
- Context is optional and subordinate to natural usage.
- Do not use random categories or force the word into work, travel, food, technology, or any other domain.
- Prefer common, realistic usage over creative or unusual examples.
- Reject sentences that are grammatical but pragmatically unnatural.
- The sentence must sound natural to a native speaker and clearly demonstrate the meaning.

Synonym and collocation rules:
- Return only useful, established synonyms or close alternatives.
- Return only established, commonly used collocations or usage patterns.
- Do not create combinations merely because they are grammatically possible.
- Return fewer items when fewer reliable items exist.

Final self-check:
- Input validity is handled honestly.
- Exact input is preserved for valid cards.
- The example is natural and meaning-driven.
- The explanation language rule is followed.
- Translations are correctly spelled and semantically accurate.
- Collocations are established and natural.
- Output is valid JSON and contains no text outside JSON.

Return ONLY valid JSON. Do not use markdown.

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
  "grammar_note": "string"
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
