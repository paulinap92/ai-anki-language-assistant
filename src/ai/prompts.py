"""Prompt templates for vocabulary, conversation, and grammar features."""

from __future__ import annotations


VOCABULARY_PROMPT_VERSION = "v10-lesson-context-validation"
GRAMMAR_BATCH_PROMPT_VERSION = "v2-topic-variety-grammar"
SENTENCE_BASED_CARD_PROMPT_VERSION = "v1-provided-example-card"
EXPLANATION_LANGUAGES = ["Polish", "English", "Spanish", "German", "Italian", "Same as target", "No translation"]


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
    "writing": "When the topic is writing, vary examples across emails, formal letters, opinion texts, reports, complaints, applications, arguments, and written communication. Do not overuse essay/ensayo.",
    "essay": "When the topic is writing/essays, essay may be one subcontext, but do not force the word essay into every example.",
    "ensayo": "When the topic is writing/ensayo, vary contexts and do not repeat ensayo in every example.",
    "dele": "When the topic is DELE/writing, vary examples across emails, letters, opinion texts, reports, complaints, applications, and arguments.",
}


def _language_quality_rules(explanation_language: str, target_language: str) -> str:
    """Return language-specific output rules for translations/explanations."""
    language = explanation_language.strip().casefold()
    if language == "no translation":
        return (
            "Explanation-language rules:\n"
            "- No translation mode is selected.\n"
            "- Return empty strings for translation, example_translation, and grammar_note.\n"
            "- Do not sneak translations or bilingual explanations into other fields.\n"
        )

    base = (
        "Explanation-language rules:\n"
        f"- Write translation, example_translation, and grammar_note in {explanation_language}.\n"
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
- Treat the user topic as a hard constraint / context guide and quality guide, not as a noun that must appear literally in every example.
- The user can type any topic. Do not reject unknown topics just because they are not in a preset list.
- The example must clearly fit the user topic, unless the input phrase genuinely cannot be used naturally in that topic.
- If the input does not naturally fit the topic, still keep the exact input, generate the most natural card, and set topic_fit to "weak" or "mismatch" with a short topic_warning.
- Do not drift into generic business, travel, technology, food, health, or abstract contexts unless the user topic points there.
- Avoid repeating the same topic keyword or scenario across many Batch cards. Use varied subcontexts inside the topic.
- If the topic is writing/DELE/essays, vary examples across emails, formal letters, opinions, arguments, reports, complaints, applications, and written communication. Do not overuse words such as "essay" or "ensayo".
{extra}
"""


def build_vocabulary_prompt(
    word_or_phrase: str,
    target_language: str,
    explanation_language: str,
    topic_context: str = "",
) -> str:
    """Build a validated, word-first vocabulary flashcard prompt."""
    explanation_language = explanation_language.strip()
    if not explanation_language:
        raise ValueError("Explanation language must be selected explicitly.")
    effective_explanation_language = target_language if explanation_language == "Same as target" else explanation_language
    no_translation = explanation_language == "No translation"
    explanation_rules = _language_quality_rules(effective_explanation_language, target_language)
    topic_rules = _topic_rules(topic_context)

    return f"""
You are a professional {target_language} language teacher and flashcard quality reviewer.

Create ONE high-quality vocabulary flashcard for this exact user input:

"{word_or_phrase}"

Target language: {target_language}
Explanation language: {effective_explanation_language}

Internal process:
1. Validate whether the input is usable learning material in {target_language}: a word, phrase, collocation, sentence fragment, idiom, grammar pattern, or context-specific lesson expression.
2. Treat the complete input as one learning item before analysing individual words.
3. Preserve the exact input for valid cards.
4. Identify the phrase-level meaning, natural collocations, grammar patterns, and normal usage.
5. Apply the user topic/context if provided.
6. Generate a simple, natural example that demonstrates the selected meaning.
7. Verify that the example uses the target item itself, not a synonym or visually similar word.
8. Verify that the collocation and translation sound natural, not merely grammatically possible.
9. Run a final quality self-check for spelling, language mixing, topic fit, naturalness, collocations, and JSON validity.

Validation rules — lesson/context mode by default:
- Accept useful lesson phrases, collocations, sentence fragments, verb + object patterns, and context-specific expressions, even if they are not idioms or dictionary headwords.
- Do NOT mark an item invalid merely because it is not a fixed expression or established idiom.
- Examples of valid context phrases: "shell rebel positions", "raise concerns", "submit an application", "address the issue", "take legal action".
- If an item is context-specific, keep is_valid true and explain it as a contextual phrase/pattern. Optionally add a SOFT warning, not invalid.
- Set is_valid false only for true garbage: OCR noise, wrong-language text, malformed/nonexistent wording, obvious typo with no reliable meaning, or an item that cannot be explained naturally.
- For invalid input, do not invent a definition or example.
- Explain the problem briefly in validation_error using {effective_explanation_language if not no_translation else target_language}.
- Suggest a correction only when reasonably confident; otherwise return an empty string.
- For invalid input, return empty strings/lists for all flashcard content fields.

Exact-input rules:
- For valid input, word_or_phrase must exactly match: "{word_or_phrase}".
- Never replace it with a synonym, related expression, corrected phrase, or a different word.
- Corrections belong only in suggested_correction when is_valid is false.

Phrase/context meaning rules:
- Treat the entire user input as one learning item.
- For multi-word expressions, compounds, idioms, fixed phrases, collocations, and context-specific phrase fragments, determine the phrase/context meaning before analysing individual words.
- Do not reject useful verb-object or context phrases just because they are not dictionary entries.
- Prefer the established phrase meaning when one exists; otherwise explain the natural contextual meaning.

Definition and explanation rules:
- The definition must be short, clear, and written in {target_language}.
- The definition must not be a translation into {effective_explanation_language}.
{explanation_rules}

Example rules:
{topic_rules}- Select context from the meaning and common usage of the expression.
- The example sentence MUST use the target word/phrase itself or a correct inflected/conjugated form.
- Do not replace the target with a synonym, near-synonym, correction, or visually similar word.
- Do not use a different word just because it is semantically close.
- Do not use a misspelled or visually similar form of the target.
- For verbs in any language, use a real inflected/conjugated form of the target verb.
- For reflexive/pronominal verbs, use a correct reflexive/pronominal form when appropriate.
- Prefer common, realistic usage over creative or unusual examples.
- Reject sentences that are grammatical but pragmatically unnatural.
- The target should be used in a natural collocation. Avoid awkward literal combinations such as using "come across" with weather, "wear down" with abstract doubts, or "flow" with an object that does not naturally have a flow.
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
- Set example_uses_target to true only if the example contains the target item itself or a correct inflected/conjugated form.
- Put the exact target form used in the example into used_form_in_example.
- Set collocation_naturalness to one of: "ok", "weak", "bad".
- Set translation_naturalness to one of: "ok", "weak", "bad".
- Add a warning for any suspected language mixing, spelling issue, unnatural example, weak topic fit, empty required field, uncertain translation, or example that does not use the target item.
- If the example uses a synonym or a visually similar but different word instead of the target item, mark it as a serious warning.
- If the example technically uses the target but the collocation is strange, mark collocation_naturalness as "weak" or "bad" and explain in quality_warnings.
- If the translation is literal, awkward, or unnatural in the explanation language, mark translation_naturalness as "weak" or "bad" and explain in quality_warnings.
- Do not hide problems. If unsure, add a warning rather than pretending the card is perfect.

Return ONLY valid JSON. Do not use markdown. Do not include comments outside JSON.

Return this exact JSON structure:

{{
  "is_valid": true,
  "validation_error": "",
  "suggested_correction": "",
  "explanation_language": "{effective_explanation_language}",
  "word_or_phrase": "{word_or_phrase}",
  "target_language": "{target_language}",
  "part_of_speech": "string",
  "definition": "string",
  "translation": "string",
  "example": "string",
  "example_translation": "string",
  "synonyms": ["string"],
  "collocations": ["string"],
  "grammar_note": "string",
  "topic_fit": "ok",
  "topic_warning": "",
  "quality_warnings": [],
  "used_form_in_example": "string",
  "example_uses_target": true,
  "collocation_naturalness": "ok",
  "translation_naturalness": "ok"
}}
"""


def _split_target_and_sentence(raw_item: str) -> tuple[str, str]:
    """Split an optional `target | sentence` Batch input."""
    value = raw_item.strip()
    for separator in ("|", "\t"):
        if separator in value:
            left, right = value.split(separator, 1)
            return left.strip(), right.strip()
    return "", value


def build_sentence_based_card_prompt(
    raw_item: str,
    target_language: str,
    explanation_language: str,
    topic_context: str = "",
) -> str:
    """Build a prompt for Batch cards based on a user-provided example sentence.

    Accepted input formats:
    - target item | provided sentence
    - provided sentence only (provider chooses the most useful target item)
    """
    explanation_language = explanation_language.strip()
    if not explanation_language:
        raise ValueError("Explanation language must be selected explicitly.")
    effective_explanation_language = target_language if explanation_language == "Same as target" else explanation_language
    no_translation = explanation_language == "No translation"
    explanation_rules = _language_quality_rules(effective_explanation_language, target_language)
    topic_rules = _topic_rules(topic_context)
    target_item, provided_sentence = _split_target_and_sentence(raw_item)
    target_instruction = (
        f'Target item selected by the user: "{target_item}". Use this exact item as word_or_phrase.'
        if target_item else
        "No explicit target item was provided. Select the single most useful word, phrase, connector, idiom, or grammar chunk from the provided sentence and put it in word_or_phrase."
    )
    return f"""
You are a professional {target_language} language teacher and flashcard quality reviewer.

Create ONE sentence-based flashcard from this user-provided example.

Raw input:
"{raw_item}"

Provided sentence:
"{provided_sentence}"

{target_instruction}

Target language: {target_language}
Explanation language: {effective_explanation_language}

Core rule:
- Use the provided sentence as the main example.
- Do NOT replace it with a new invented example.
- Do NOT change its meaning.
- Do NOT rewrite the sentence except for tiny obvious typo fixes, and only if needed for correctness.
- If you make a tiny correction, mention it in quality_warnings.

Card rules:
- word_or_phrase must be the explicit user target if one was provided.
- If no target was provided, choose a useful expression from the sentence, not a random word.
- The example field must contain the provided sentence, or the minimally corrected version of it.
- Definition must explain the selected target item in {target_language}.
- Translation/example_translation/grammar_note follow the selected explanation language.
- Useful phrases/collocations should come from the sentence or closely related natural usage.
- The card should help the learner remember the target in this real sentence context.
{explanation_rules}
{topic_rules}
Quality self-check:
- Set example_uses_target to true only if the final example contains the selected target item or a valid inflected form.
- Put the exact target form used in the example into used_form_in_example.
- Set collocation_naturalness to ok/weak/bad.
- Set translation_naturalness to ok/weak/bad.
- Add quality_warnings for any target mismatch, sentence rewrite, awkward translation, weak topic fit, or uncertainty.
- If the provided sentence is not in {target_language}, set is_valid false and explain why.

Return ONLY valid JSON. Do not use markdown or comments outside JSON.

{{
  "is_valid": true,
  "validation_error": "",
  "suggested_correction": "",
  "explanation_language": "{effective_explanation_language}",
  "word_or_phrase": "{target_item if target_item else 'string'}",
  "target_language": "{target_language}",
  "part_of_speech": "string",
  "definition": "string",
  "translation": "string",
  "example": "{provided_sentence}",
  "example_translation": "string",
  "synonyms": ["string"],
  "collocations": ["string"],
  "grammar_note": "string",
  "topic_fit": "ok",
  "topic_warning": "",
  "quality_warnings": [],
  "used_form_in_example": "string",
  "example_uses_target": true,
  "collocation_naturalness": "ok",
  "translation_naturalness": "ok"
}}
"""


def build_batch_grammar_prompt(
    grammar_item: str,
    target_language: str,
    topic_context: str = "",
) -> str:
    """Build a prompt for Batch grammar cards from structures/connectors/patterns.

    This is different from sentence analysis: the input may be a grammar
    construction such as ``aunque + subjuntivo`` or a discourse connector such
    as ``por consiguiente``. The output reuses ``GrammarAnalysis`` because the
    Anki grammar template is sentence/structure-first.
    """
    topic_rules = _topic_rules(topic_context)
    return f"""
You are a professional {target_language} grammar teacher and flashcard quality reviewer.

Create ONE grammar flashcard for this exact user input:

"{grammar_item}"

Target language: {target_language}

The input may be a grammar structure, connector, discourse phrase, verb pattern,
exam-writing expression, or a complete example sentence.

Requirements:
- Preserve the input exactly in the "sentence" field.
- Identify the useful grammar structure or writing function.
- Explain the meaning/use in simple {target_language}.
- Keep it practical for learners, not a long academic lesson.
- Give a natural context example in {target_language} that uses the structure correctly.
- Include 2-4 short breakdown points.
- Include 1-3 contrasts with similar structures or common alternatives.
- Include 1-3 common mistakes with corrected forms.
- For DELE/writing topics, vary contexts: letters, emails, arguments, reports, opinions, complaints, applications, and written communication. Do not overuse one noun such as "ensayo".
{topic_rules}
Return ONLY valid JSON. Do not use markdown or comments outside JSON.

Return this exact JSON structure:

{{
  "sentence": "{grammar_item}",
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
    feedback_language: str,
) -> str:
    """Build a prompt for reviewing one answer and continuing a conversation."""
    feedback_language = feedback_language.strip()
    if not feedback_language:
        raise ValueError("Feedback language must be selected explicitly.")
    effective_feedback_language = target_language if feedback_language == "Same as target" else feedback_language
    return f"""
You are a warm, practical {target_language} conversation teacher.
Conversation topic: "{topic}"
Question: "{question}"
Learner answer: "{answer}"
Requested level: "{improvement_level}"
Feedback language: {effective_feedback_language}

Teaching style:
- Be positive first, like a good human teacher.
- Highlight mistakes clearly, but kindly.
- Always explain HOW to improve, not only what is wrong.
- Keep feedback practical and not too long.
- Use {effective_feedback_language} for feedback, explanations, and mini_practice.
- Use {target_language} for corrected_version, advanced_answer, next_question, and suggested_vocabulary.
- Do not switch to another language or writing system.

Output requirements:
- "feedback" must start with one encouraging sentence, then briefly summarize the main improvement.
- "corrections" must contain 1-4 important corrections. If the answer is already excellent, include one useful style improvement.
- Each correction must show: learner's original fragment, corrected fragment, and a short explanation in {effective_feedback_language}.
- "corrected_version" must preserve the learner's idea but fix errors.
- "advanced_answer" must be a richer natural version at {improvement_level}.
- "suggested_vocabulary" must contain 4 useful reusable words, phrases, or chunks from the answer/topic.
- "mini_practice" must be one short practice task in {effective_feedback_language}.
- Ask one natural follow-up question in {target_language}.
- Return ONLY valid JSON without markdown.

{{
  "feedback_language": "{effective_feedback_language}",
  "feedback": "Good attempt — your meaning was clear. The main thing to improve is ...",
  "corrections": [
    {{
      "original": "learner fragment",
      "correction": "corrected fragment",
      "explanation": "short explanation in {effective_feedback_language}"
    }}
  ],
  "corrected_version": "string in {target_language}",
  "advanced_answer": "string in {target_language}",
  "mini_practice": "short task in {effective_feedback_language}",
  "next_question": "string in {target_language}",
  "suggested_vocabulary": ["chunk 1", "chunk 2", "chunk 3", "chunk 4"]
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


def build_ocr_candidate_extraction_prompt(
    extracted_text: str,
    target_language: str,
    explanation_language: str,
    extraction_mode: str,
    topic_context: str = "",
    max_candidates: int = 35,
) -> str:
    """Build a prompt that extracts Batch-ready candidates from OCR text.

    This is not a card-generation prompt. It only produces candidate rows that
    the user can review and send to Batch.
    """
    mode = (extraction_mode or "Provided examples").strip()
    effective_explanation_language = target_language if explanation_language == "Same as target" else explanation_language
    topic_hint = f'User topic/context: "{topic_context}".' if topic_context.strip() else "No user topic/context was provided."
    return f"""
You are extracting language-learning candidates from OCR / imported lesson text.

Target language: {target_language}
Explanation language for later cards: {effective_explanation_language}
Extraction mode: {mode}
{topic_hint}

OCR / imported text:
<<<TEXT
{extracted_text}
TEXT>>>

Your task:
- Do NOT generate full flashcards.
- Extract useful candidates that can be reviewed before sending to Batch.
- Preserve useful source sentences exactly when they are natural and readable.
- Skip OCR garbage, page numbers, exercise labels, random headers, and duplicate items.
- Prefer useful words, phrases, collocations, grammar chunks, highlighted/bold items, and textbook example sentences.
- Keep at most {max_candidates} candidates.

Candidate types:
- vocabulary: a word/phrase only. Use when there is no useful source sentence.
- provided_example: target + exact source sentence. Best for textbook sentences.
- grammar: a grammar structure/pattern + optional source sentence.

Mode-specific rules:
- If mode is Vocabulary, return mostly vocabulary candidates with target only.
- If mode is Provided examples, return provided_example candidates in target + sentence form.
- If mode is Grammar, return grammar candidates such as prefixes, verb patterns, connectors, tense patterns, or structures.
- If mode is Mixed, return a careful mix, but do not over-extract.

For provided_example:
- target must be the word/phrase/chunk to learn.
- sentence must be a complete useful source sentence from the OCR text.
- Do not choose a random word from the sentence when a bold/highlighted/lesson item is obvious.

Return ONLY valid JSON, no markdown, no comments.

Return this exact structure:
{{
  "candidates": [
    {{
      "type": "provided_example",
      "target": "string",
      "sentence": "string",
      "reason": "short reason"
    }}
  ]
}}
"""
