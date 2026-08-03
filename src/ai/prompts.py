"""Prompt templates for vocabulary, conversation, and grammar features."""

from __future__ import annotations


VOCABULARY_PROMPT_VERSION = "v10-lesson-context-validation"
GRAMMAR_BATCH_PROMPT_VERSION = "v3-smart-grammar-generated-example-contract"
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
    Anki grammar template is sentence/structure-first and audio-ready.
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
- SOURCE-FOCUS RULE: preserve the exact grammar/word-form target from the input. Do not replace a specific target with a broader lesson label.
- If the input uses the review format "grammar target | source sentence", put ONLY the source sentence, the part after "|", in the "sentence" field, and use the left side as the structure/pattern clue by putting it in "structure" or at the start of "structure".
- In "grammar target | source sentence" rows, the right side is the sentence/audio target. Never use a textbook rule, explanation, or abstract heading as the sentence/audio field.
- If the left side is a concrete structure such as "used to + base verb", "Can I + base verb", "should have + past participle", or a word-form transformation such as "un hippi -> hippies", the card must visibly teach that exact target.
- For word-form or transformation targets, keep the transformation in "structure" and use/generate a sentence that contains the transformed form.
- If the input is only a real learner example sentence, preserve that sentence exactly in the "sentence" field and infer the most useful structure.
- If the input is a grammar rule, definition, explanation, textbook note, or meta-sentence about the grammar structure, do NOT preserve it as the "sentence" field. Instead, infer the grammar structure, generate ONE short natural learner example that uses it, and explain the original rule in meaning/usage.
- If the input is only a connector/discourse word such as "therefore", the "sentence" field may be that connector itself, and "structure" should describe its writing/connector function.
- If the input is only a grammar pattern with no source sentence, create ONE natural example sentence for the "sentence" field and put the pattern itself in "structure".
- If the input includes source context such as "Source rule/note, not audio", use it only to understand the target. Do not copy that source rule into "sentence" or "context_example".
- A natural example sentence using the grammar item is always required unless the target itself is a connector/discourse word to be learned.
- Identify the useful grammar structure or writing function.
- Explain the meaning/use in simple {target_language}.
- Keep it practical for learners, not a long academic lesson.
- Give a natural context example in {target_language} that uses the structure correctly.
- Do not create two competing example sentences. If "sentence" is a full learner-visible example, "context_example" must either be the same sentence or include that exact sentence unchanged.
- If you generate an example from a rule-only source, use the same best natural example as both "sentence" and "context_example" unless the source explicitly provides a different sentence.
- Include 2-4 short breakdown points.
- Include 1-3 contrasts with similar structures or common alternatives.
- Include 1-3 common mistakes with corrected forms.
- For DELE/writing topics, vary contexts: letters, emails, arguments, reports, opinions, complaints, applications, and written communication. Do not overuse one noun such as "ensayo".

Final sentence/audio contract:
- The "sentence" field is the learner-visible/audio sentence.
- It must be a natural example that uses the structure in communication.
- It must not define, explain, describe, or teach the grammar item.
- It must not be a textbook rule, exercise instruction, abstract heading, or meta-sentence about the grammar item itself.
- If the current candidate sentence is a rule/definition, replace it with a generated natural example and keep the rule information in meaning/usage.
- context_example must be the same sentence or contain that exact sentence unchanged.
{topic_rules}
Return ONLY valid JSON. Do not use markdown or comments outside JSON.

Return this exact JSON structure:

{{
  "sentence": "the exact source sentence after |, the connector itself, or a natural example sentence using the grammar target; never a long rule/explanation",
  "target_language": "{target_language}",
  "meaning": "string",
  "structure": "the exact source grammar target/pattern/word-form transformation whenever one is provided",
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



def build_smart_grammar_candidate_extraction_prompt(
    extracted_text: str,
    target_language: str,
    explanation_language: str,
    topic_context: str = "",
    max_candidates: int = 35,
) -> str:
    """Build a focused Smart Grammar extraction prompt.

    This prompt is intentionally separate from the general OCR candidate prompt.
    It makes the model decide the semantic source role before filling fields,
    so rule/definition text cannot become the learner-visible audio sentence.
    """
    effective_explanation_language = target_language if explanation_language == "Same as target" else explanation_language
    topic_hint = f'User topic/context: "{topic_context}".' if topic_context.strip() else "No user topic/context was provided."
    return f"""
You are extracting Smart Grammar candidate drafts from OCR / imported lesson text.

Target language: {target_language}
Explanation language for later cards: {effective_explanation_language}
Extraction mode: Smart grammar import
{topic_hint}

OCR / imported text:
<<<TEXT
{extracted_text}
TEXT>>>

Your task:
- Do NOT generate final Anki cards.
- Return grammar candidate drafts only.
- Keep at most {max_candidates} candidates.
- Preserve useful source focus exactly: grammar pattern, connector, word form, transformation, or lesson structure.
- Preserve slash alternatives such as "Actually / Incidentally" as one visible target unless the source clearly separates them.
- Skip OCR garbage, page numbers, isolated headers, and duplicate items.

Core field contract:
- target = the grammar focus/pattern/source target to learn.
- sentence = ONLY a learner-visible example sentence suitable for audio.
- source_rule = ONLY the original rule, definition, explanation, use note, or exercise instruction.
- reason = short reason why this candidate was extracted.
- sentence must never be a grammar definition, textbook rule, exercise instruction, heading, or meta-sentence about the grammar item.
- source_rule must never be used as the audio sentence.

First classify each useful source fragment semantically.

Allowed source_role values:
- usage_example: a natural sentence that uses the target structure in communication.
- grammar_rule: a rule, definition, explanation, use note, or sentence about the grammar structure itself.
- grammar_rule_with_example: a rule/use note plus a separate real example sentence.
- transformation: a word-form or grammar transformation.
- exercise: a gap-fill, multiple-choice item, or task instruction.
- sentence_only: a useful source sentence where the grammar focus is unclear.
- unknown: unclear or risky fragment.

Routing contract:
1. usage_example
   - type="grammar"
   - source_role="usage_example"
   - source_type="structure_sentence"
   - strategy="preserve_source_sentence"
   - target = the grammar focus if clear, otherwise ""
   - sentence = the exact source example sentence
   - source_rule = ""
   - example_origin="preserved_from_source"
   - needs_review=false when target and sentence are both clear

2. grammar_rule
   - type="grammar"
   - source_role="grammar_rule"
   - source_type="rule"
   - strategy="generated_example_from_rule"
   - target = the concrete grammar structure/use being taught
   - source_rule = the original rule/definition/use note from the source
   - sentence = ONE newly generated natural learner example that actually uses the target grammar
   - example_origin="generated_from_rule"
   - needs_review=true

3. grammar_rule_with_example
   - type="grammar"
   - source_role="grammar_rule_with_example"
   - source_type="structure_sentence"
   - strategy="preserve_source_sentence"
   - target = the grammar focus
   - source_rule = the original rule/use note
   - sentence = the separate real example sentence from the source
   - example_origin="preserved_from_source"
   - needs_review=true unless the mapping is obvious

4. transformation
   - type="grammar"
   - source_role="transformation"
   - source_type="transformation"
   - strategy="word_form_example"
   - target = the exact transformation
   - source_rule = original transformation text if useful
   - sentence = a natural example using the transformed form
   - example_origin="generated_from_rule" or "preserved_from_source"
   - needs_review=true

5. exercise
   - type="grammar"
   - source_role="exercise"
   - source_type="exercise"
   - strategy="exercise_draft_review_answer"
   - target = grammar focus if clear
   - source_rule = raw exercise/instruction
   - sentence = completed answer only if clearly available, otherwise ""
   - example_origin="missing" when no completed answer is available
   - needs_review=true

6. sentence_only
   - type="grammar"
   - source_role="sentence_only"
   - source_type="sentence_only"
   - strategy="infer_later"
   - target=""
   - sentence = exact source sentence
   - source_rule=""
   - example_origin="preserved_from_source"
   - needs_review=true

Final self-check before returning JSON:
- If source_role="grammar_rule", sentence MUST be newly generated, not copied from source_rule.
- If source_type="rule" and strategy="generated_example_from_rule", sentence MUST NOT equal source_rule.
- If sentence defines, explains, describes, names, or teaches the grammar item, it belongs in source_rule, not sentence.
- If you cannot create a natural example for a rule, leave sentence empty, set example_origin="missing", needs_review=true, confidence="low".
- The audio sentence must be a real usage example, not a sentence about grammar.

Return ONLY valid JSON, no markdown, no comments.

Return this exact structure:
{{
  "candidates": [
    {{
      "type": "grammar",
      "target": "string",
      "source_role": "usage_example | grammar_rule | grammar_rule_with_example | transformation | exercise | sentence_only | unknown",
      "sentence": "learner-visible example sentence for audio; empty only when review is needed",
      "source_rule": "original rule/definition/use note/exercise instruction when relevant",
      "example_origin": "preserved_from_source | generated_from_rule | extracted_from_table | missing",
      "needs_review": true,
      "reason": "short reason",
      "source_type": "structure_sentence | rule | transformation | exercise | sentence_only",
      "strategy": "preserve_source_sentence | generated_example_from_rule | word_form_example | exercise_draft_review_answer | infer_later",
      "confidence": "high | medium | low"
    }}
  ]
}}
"""


def build_vocabulary_candidate_extraction_prompt(
    extracted_text: str,
    target_language: str,
    explanation_language: str,
    extraction_mode: str,
    topic_context: str = "",
) -> str:
    """Build a focused vocabulary extraction prompt for OCR/imported lessons.

    Vocabulary has three deliberately separate modes:
    - Vocabulary: only target words/phrases, no examples.
    - Vocabulary + source examples: vocabulary candidates with optional source sentences.
    - Smart vocabulary: may mix vocabulary candidates and provided_example candidates,
      but still never returns grammar unless the user selected Mixed outside this prompt.
    """
    mode = (extraction_mode or "Vocabulary").strip()
    mode_key = mode.casefold()
    effective_explanation_language = target_language if explanation_language == "Same as target" else explanation_language
    topic_hint = f'User topic/context: "{topic_context}".' if topic_context.strip() else "No user topic/context was provided."

    if mode_key == "smart vocabulary":
        allowed_types = "- vocabulary\n- provided_example"
        mode_contract = """
SMART VOCABULARY CONTRACT

This mode may mix vocabulary candidates and provided_example candidates.

Use type="vocabulary" for:
- words, terms, phrases, idioms, collocations, specialist vocabulary, expression headings, and explicit vocabulary-list items.
- vocabulary items that optionally have a useful source sentence/context.

Use type="provided_example" only when:
- the source contains a complete useful sentence that is worth preserving as the learning context,
- the sentence clearly contains the selected target phrase/idiom/collocation,
- the sentence is better learned as target + exact source sentence than as a word-only item.

Never return type="grammar" in Smart vocabulary mode.
Do not turn exercises/questions/tasks into provided examples.
"""
        source_example_rule = """
Source example rules:
- For vocabulary candidates, put a clear source context sentence in source_sentence when useful.
- For provided_example candidates, put the exact source sentence in sentence and the target phrase in target.
- If a useful context sentence contains blanks/underscores and the missing answer is obvious, return the completed clean sentence, set strategy="completed_gap_source_sentence", needs_review=true, and mention the filled gap in reason.
- If the gap is not obvious, do not use the incomplete sentence as sentence/source_sentence.
- Do not invent examples during extraction. Final Batch generation can create examples later.
"""
        output_type_schema = "vocabulary | provided_example"
        sentence_schema = '"sentence": "exact source sentence only for provided_example; empty for vocabulary unless the model uses source_sentence",\n      "source_sentence": "optional exact source context for vocabulary candidates",'
    elif mode_key == "vocabulary + source examples":
        allowed_types = "- vocabulary"
        mode_contract = """
VOCABULARY + SOURCE EXAMPLES CONTRACT

This mode returns vocabulary candidates only, but it should attach source examples when they are clearly available.

Use type="vocabulary" for every candidate.
Never return type="provided_example" or type="grammar" in this mode.

A source example is optional context for the vocabulary item; it does not change the candidate type.
"""
        source_example_rule = """
Source example rules:
- If a clear source sentence from the material contains the exact target or a normal inflected form, put it in source_sentence.
- If no clear source sentence exists, leave source_sentence empty.
- For dialogues under idioms/expressions, attach the best short source sentence that demonstrates the idiom.
- If the only available context is a gap-fill sentence with blanks/underscores and the missing word is obvious, return the completed clean sentence in source_sentence, set strategy="completed_gap_source_sentence", needs_review=true, and mention the filled gap in reason.
- If the gap is not obvious, do not use that sentence as source_sentence; leave source_sentence empty or return it only as source_rule/reason for review.
- Do not invent examples during extraction. Final Batch generation can create examples later.
"""
        output_type_schema = "vocabulary"
        sentence_schema = '"source_sentence": "optional exact source example/context",'
    else:
        allowed_types = "- vocabulary"
        mode_contract = """
VOCABULARY CONTRACT

This mode returns vocabulary candidates only.
Use type="vocabulary" for every candidate.
Never return type="provided_example" or type="grammar" in this mode.

The goal is a clean list of targets for Batch.
"""
        source_example_rule = """
Source example rules:
- Do not attach examples by default.
- If an explicit expression heading has a very short directly attached example, you may put it in source_sentence, but keep type="vocabulary".
- Do not invent examples during extraction. Final Batch generation can create examples later.
"""
        output_type_schema = "vocabulary"
        sentence_schema = '"source_sentence": "usually empty; optional short source context only",'

    return f"""
You are extracting vocabulary candidate drafts from OCR / imported lesson text.

Target language: {target_language}
Explanation language for later cards: {effective_explanation_language}
Extraction mode: {mode}
{topic_hint}

OCR / imported text:
<<<TEXT
{extracted_text}
TEXT>>>

ALLOWED OUTPUT TYPES
{allowed_types}

{mode_contract}

Your job is controlled recall, not runaway word mining:
- Do NOT choose only the best 30 items from explicit lesson vocabulary lists.
- Extract every explicit vocabulary item from clearly marked lesson vocabulary lists when they are present.
- Extract every explicit idiom/expression from clearly marked expression sections when they are present.
- Do NOT extract every possible word from continuous prose.
- Do NOT create one candidate for every noun, verb, adjective, symptom, body part, or repeated word in ordinary paragraphs.
- If the source contains explicit vocabulary/expression sections, process those sections first and keep reading-text mining minimal.
- If the source is mostly continuous prose, return only high-value reusable items: idioms, collocations, specialist terms, and lesson-relevant phrases.
- Hard output budgets: Vocabulary <= 300, Vocabulary + source examples <= 250, Smart vocabulary <= 180.
- For continuous prose without explicit vocabulary lists, keep Vocabulary + source examples <= 60 and Smart vocabulary <= 80.
- If there are more possible items than the budget, prioritize explicit list items, idioms, collocations, and repeated lesson-relevant expressions.

Priority order:
1. Extract every explicit bullet/list item under headings such as Vocabulario, Vocabulary, Léxico, Lexique, Wortschatz, Expresiones, Expresiones coloquiales, Idioms, Expressions.
2. Extract every numbered idiom/expression heading from expression sections.
3. Extract a small, selective set of useful collocations from reading text only after explicit lists and expression headings are complete.
4. Skip exercises, questions, tasks, page footers, emails, websites, image filenames, copyright/footer text, tutor IDs, and page numbers.
5. When in doubt, prefer fewer high-quality reusable candidates over a massive list.

Slash and parenthesis rules:
- If a slash-separated item is a list of separate words, split it into separate vocabulary candidates.
- If a slash-separated item represents alternatives inside one fixed expression, preserve the full expression or create clean variants.
- Expand useful parenthetical variants when they make natural standalone candidates.
- Examples:
  - "Cólico / eccema / jaqueca" -> "cólico", "eccema", "jaqueca".
  - "poner la carne / piel de gallina" -> "poner la carne de gallina", "poner la piel de gallina".
  - "batido (de proteínas / de frutas)" -> "batido", "batido de proteínas", "batido de frutas".
  - "amputar (un brazo / una pierna)" -> "amputar", "amputar un brazo", "amputar una pierna".

{source_example_rule}

Candidate metadata:
- candidate_kind = word | phrase | idiom | collocation | specialist_term | expression | body_part | disease | profession | medication | other
- source_section = vocabulary_list | colloquial_expressions | reading_text | dialogue | table | highlighted_item | other
- source_sentence = exact source sentence/context when useful and readable, otherwise empty
- reason = short reason or source heading
- needs_review = true only for uncertain, OCR-damaged, or expanded variants

Return ONLY valid JSON, no markdown, no comments.

Return this exact structure:
{{
  "candidates": [
    {{
      "type": "{output_type_schema}",
      "target": "string",
      {sentence_schema}
      "candidate_kind": "word | phrase | idiom | collocation | specialist_term | expression | body_part | disease | profession | medication | other",
      "source_section": "vocabulary_list | colloquial_expressions | reading_text | dialogue | table | highlighted_item | other",
      "reason": "short reason or source heading",
      "source_type": "vocabulary_list | colloquial_expression | reading_text_collocation | dialogue_example | highlighted_item | table_row | expanded_variant | provided_example",
      "strategy": "vocabulary_candidate | vocabulary_with_source_sentence | expanded_vocabulary_variant | preserve_source_sentence",
      "needs_review": false,
      "confidence": "high | medium | low"
    }}
  ]
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
    mode_key = mode.casefold()
    if mode_key == "smart grammar import":
        return build_smart_grammar_candidate_extraction_prompt(
            extracted_text=extracted_text,
            target_language=target_language,
            explanation_language=explanation_language,
            topic_context=topic_context,
            max_candidates=max_candidates,
        )
    if mode_key in {"vocabulary", "vocabulary + source examples", "smart vocabulary"}:
        return build_vocabulary_candidate_extraction_prompt(
            extracted_text=extracted_text,
            target_language=target_language,
            explanation_language=explanation_language,
            extraction_mode=mode,
            topic_context=topic_context,
        )
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
- For table-like material, preserve row relationships such as Expression | Example | Use. Do not mix cells from different rows.
- Skip OCR garbage, page numbers, exercise labels, random headers, and duplicate items.
- Prefer useful words, phrases, collocations, grammar chunks, highlighted/bold items, and textbook example sentences.
- Keep at most {max_candidates} candidates.

Candidate types:
- vocabulary: a word/phrase only. Use when there is no useful source sentence.
- provided_example: target + exact source sentence. Best for textbook sentences.
- grammar: a grammar target/pattern/structure + optional source sentence. If there is only a sentence and no target, mark it as grammar with an empty target; the UI will show it as Grammar from sentence.

Mode-specific rules:
- If mode is Vocabulary, return ONLY vocabulary candidates with target only. Never return provided_example or grammar in Vocabulary mode.
- If mode is Provided examples, return provided_example candidates in target + sentence form.
- If mode is Grammar, return grammar candidates with a clear target whenever possible, e.g. verb pattern, tense pattern, connector, prefix, or structure. Preserve the source sentence as sentence. If you cannot identify the target, return the sentence with type grammar and an empty target; do not label it as provided_example.
- If mode is Smart grammar import, every returned candidate MUST use type="grammar". Do not return provided_example in this mode.
- If mode is Smart grammar import or Mixed, first classify each useful fragment, then choose the card strategy:
  1. structure_sentence: source has a clear grammar structure plus a readable example sentence. Return type="grammar", target=the structure, sentence=the exact source sentence, source_type="structure_sentence", strategy="preserve_source_sentence".
  2. rule: source is a grammar rule/explanation without a good example sentence. Return type="grammar", target=a concrete structure, sentence=ONE natural generated example sentence that uses the structure, source_type="rule", strategy="generated_example_from_rule", source_rule=the short source rule. Never put the rule itself in sentence. Rule-like text includes lines such as "have with this meaning is a stative verb", "we use have to to express obligation", "have is also a stative verb", or "have as an auxiliary verb". For these, INVENT a short natural example sentence.
  3. transformation: source is a word-form or grammar transformation, e.g. "un hippi -> hippies". Return type="grammar", target=the exact transformation, sentence=a natural sentence using the transformed form, source_type="transformation", strategy="word_form_example".
  4. exercise: source is a gap-fill or multiple-choice exercise. Return type="grammar", source_type="exercise", strategy="exercise_draft_review_answer". If the correct completed sentence is very clear, put it in sentence; otherwise preserve the raw exercise in reason/source_rule and leave sentence empty for user review.
  5. sentence_only: source is only a useful sentence and the grammar focus is unclear. Return type="grammar", target="", sentence=the exact source sentence, source_type="sentence_only", strategy="infer_later".
- If mode is Mixed, return a careful mix, but do not over-extract.

For provided_example:
- target must be the word/phrase/chunk to learn.
- sentence must be a complete useful source sentence from the OCR text.
- Do not choose a random word from the sentence when a bold/highlighted/lesson item is obvious.

For grammar candidates:
- target must be the grammar focus/pattern/source target, not the whole sentence.
- If the source has slash-separated alternatives such as "Actually / Incidentally" or "As regards / Regarding", do not silently drop alternatives. Preserve the full alternative group as target, or create one candidate per alternative.
- For discourse-marker tables with Expression / Example / Use columns, target = Expression, sentence = Example, source_rule/reason = Use.
- Preserve the exact source focus from headings, highlighted items, structure boxes, word-form transformations, or exercise prompts.
- If the source focus is a concrete structure or transformation, e.g. "used to + base verb", "Can I + base verb", "un hippi -> hippies", target must contain that structure/transformation, not a broad topic such as "repeated actions in the past".
- sentence should be the exact source example if available; this sentence becomes the audio/readable sentence later.
- If the source only gives a rule, generate a short natural example sentence for sentence and put the original rule in source_rule/reason. Do not use the rule itself as the audio sentence.
- For rule-only grammar lines, sentence MUST look like a learner-friendly example, not a definition. Bad sentence: "have with this meaning is a stative verb". Good sentence: "I have two older brothers."
- Do not put textbook rules or explanations in sentence. Put rules only in source_rule/reason/context.
- If target is known, return type="grammar", target="...", sentence="...".
- If only a useful sentence is found and no grammar target is clear, return type="grammar", target="", sentence="...".
- Add source_type and strategy for grammar candidates whenever possible so the UI can show why the card was created.

Return ONLY valid JSON, no markdown, no comments. Never output schema fragments as standalone candidate text.

Return this exact structure:
{{
  "candidates": [
    {{
      "type": "vocabulary | provided_example | grammar",
      "target": "string",
      "sentence": "string",
      "reason": "short reason",
      "source_type": "vocabulary | provided_example | structure_sentence | rule | transformation | exercise | sentence_only",
      "strategy": "preserve_source_sentence | generated_example_from_rule | word_form_example | exercise_draft_review_answer | infer_later | vocabulary_candidate",
      "source_rule": "short original rule/exercise text when relevant"
    }}
  ]
}}
"""


def build_multimodal_ocr_prompt() -> str:
    """Build a strict vision-OCR prompt that transcribes only visible text.

    This prompt is intentionally separate from multimodal candidate extraction.
    It must never create candidate JSON, flashcards or Batch-ready rows.
    """
    return """
You are an OCR transcription engine for language-learning source material.

Task:
- Extract ONLY the visible text from the supplied image/PDF page(s).
- Preserve headings, section labels, bullets, numbering, line breaks and paragraph order.
- Preserve tables as readable Markdown tables when possible.
- Preserve slash alternatives, accents/diacritics, punctuation and capitalization.
- If text is unreadable, mark it as [unclear] instead of guessing.

Strict prohibitions:
- Do NOT create flashcards.
- Do NOT extract vocabulary candidates.
- Do NOT classify candidate types.
- Do NOT output JSON.
- Do NOT translate unless the translation is visibly present in the source.
- Do NOT explain grammar, summarize, correct, complete exercises, or generate examples.
- Do NOT add comments before or after the transcription.

Return only the transcribed text.
""".strip()


def build_multimodal_import_extraction_prompt(
    target_language: str,
    explanation_language: str,
    extraction_mode: str,
    topic_context: str = "",
    max_candidates: int = 45,
) -> str:
    """Build a table-aware multimodal extraction prompt for screenshots/book photos.

    This is not a card-generation prompt. The vision model should read the
    visual layout and return candidate drafts only.
    """
    mode = (extraction_mode or "Smart grammar import").strip()
    effective_explanation_language = target_language if explanation_language == "Same as target" else explanation_language
    topic_hint = f'User topic/context: "{topic_context}".' if topic_context.strip() else "No user topic/context was provided."
    return f"""
You are extracting editable language-learning candidate drafts from an image/PDF page.

Target language: {target_language}
Explanation language for later cards: {effective_explanation_language}
Extraction mode: {mode}
{topic_hint}

Important:
- You are looking at the image/layout directly. Use visual structure: tables, columns, rows, highlights, underlines, bold text, examples and notes.
- Do NOT generate final Anki cards.
- Do NOT translate unless translation is explicitly present in the source.
- Return candidate drafts only. The app will review/edit/send them to Batch later.
- Keep at most {max_candidates} candidates unless the source is a clearly marked vocabulary list; even then do not exceed the app safety budget.
- Do NOT extract every word from continuous prose. For ordinary paragraphs, return only high-value lesson vocabulary, idioms, collocations, and clearly marked/highlighted items.
- If the page has explicit lists/tables, extract those first. If it is mostly prose, be selective.

Table-aware rules:
- If the page contains a table, preserve row relationships. Never mix cells from different rows.
- For discourse/grammar tables with Expression / Example / Use columns:
  - target = Expression cell
  - sentence = Example cell, one clean readable sentence for later audio
  - source_rule = Use cell
  - source_type = "structure_sentence"
  - strategy = "preserve_source_sentence"
- Do not turn table headers such as Expression, Example or Use into candidates.
- If an expression has slash alternatives such as "Actually / Incidentally" or "As regards / Regarding", preserve the full alternative group as target. Do not silently drop alternatives.

Highlighted-book-photo rules:
- If words/phrases are visibly highlighted, underlined, circled or boxed by the learner, extract only those marked items.
- For each marked item, include the full source sentence containing it when readable.
- Do not extract every word on the page.
- Preserve multi-word phrases as one target when the marking covers a phrase.

Mode-specific rules:
- Vocabulary: return words/phrases/collocations as type="vocabulary". Use sentence when a clear source sentence is visible.
- Provided examples: return type="provided_example" with target + exact source sentence.
- Grammar: return type="grammar" with a clear target/structure and source sentence when available.
- Smart grammar import: every returned candidate MUST use type="grammar" unless it is clearly a vocabulary-only item in Mixed mode. Do not return provided_example in Smart grammar import.
- Mixed: return vocabulary and grammar candidates, but preserve per-item type.

Vocabulary image contract:
- In Vocabulary mode, return type="vocabulary" only. Do not return provided_example or grammar.
- In Vocabulary + source examples mode, return type="vocabulary" only, but attach source_sentence when a clear visible example belongs to that expression.
- In Smart vocabulary mode, you may return type="vocabulary" and type="provided_example". Use provided_example only for complete useful source sentences with a clear target; never return grammar in Smart vocabulary mode.
- Extract all explicit list items from visible Vocabulario/Vocabulary/Léxico/Expresiones sections before extracting anything from prose.
- Extract numbered idiom/expression headings as vocabulary/idiom candidates.
- Split slash-separated word lists into separate candidates; preserve or expand slash alternatives inside fixed expressions.
- Skip footers, websites, emails, tutor IDs, page numbers, image filenames, questions and exercise instructions.

Grammar rules:
- target must be the grammar/discourse marker/source focus, not a broad textbook heading.
- sentence must be a readable example sentence. This becomes the audio sentence later.
- textbook rules/explanations must go to source_rule/reason, never to sentence.
- If the source gives only a grammar rule and no example, create one short natural example sentence and keep the original rule in source_rule.
- For word-form transformations such as "un hippi -> hippies", preserve the transformation as target and create/preserve a sentence using the transformed form.

Smart grammar image contract:
- Before creating a grammar candidate, classify the visible fragment semantically as source_role.
- source_role values: usage_example, grammar_rule, grammar_rule_with_example, transformation, exercise, sentence_only, unknown.
- sentence = only a real learner example suitable for audio.
- source_rule = only the visible rule/use note/definition/instruction.
- If source_role="grammar_rule", return source_type="rule", strategy="generated_example_from_rule", source_rule=the visible rule, sentence=ONE newly generated natural example, example_origin="generated_from_rule", needs_review=true.
- If source_role="usage_example", preserve the visible source sentence as sentence and set example_origin="preserved_from_source".
- If the page has a table row with a real Example cell, sentence = Example cell and source_rule = Use/Note cell.
- Never put a visible grammar definition or use note into sentence/audio.

Return ONLY valid JSON, no markdown and no comments. Never output schema fragments as candidate text.

Return this exact structure:
{{
  "candidates": [
    {{
      "type": "vocabulary | provided_example | grammar",
      "target": "string",
      "source_role": "usage_example | grammar_rule | grammar_rule_with_example | transformation | exercise | sentence_only | table_row | highlighted_item | vocabulary | unknown",
      "sentence": "learner-visible example sentence for audio",
      "source_rule": "short original rule/use/exercise text when relevant",
      "example_origin": "preserved_from_source | generated_from_rule | extracted_from_table | highlighted_source_sentence | missing",
      "needs_review": true,
      "reason": "short reason or source/use note",
      "source_type": "vocabulary | provided_example | structure_sentence | rule | transformation | exercise | sentence_only | table_row | highlighted_item",
      "strategy": "preserve_source_sentence | generated_example_from_rule | word_form_example | exercise_draft_review_answer | infer_later | vocabulary_candidate | preserve_table_row | highlighted_source_sentence",
      "confidence": "high | medium | low"
    }}
  ]
}}
"""
