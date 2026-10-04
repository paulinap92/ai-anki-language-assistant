"""Prompt templates for vocabulary, conversation, and grammar features."""

from __future__ import annotations


VOCABULARY_PROMPT_VERSION = "v11-semantic-target-usage-validation"
GRAMMAR_BATCH_PROMPT_VERSION = "v3-smart-grammar-generated-example-contract"
SENTENCE_BASED_CARD_PROMPT_VERSION = "v1-provided-example-card"
CONVERSATION_PROMPT_VERSION = "v3-direct-reply-history-card-back"
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
- Set example_uses_target to true only if the example contains the target item itself or a correct inflected/conjugated/declined/reflexive form of that SAME lexical target.
- Set target_usage to exactly one of: "exact", "valid_inflection", "mismatch", "uncertain".
- Use target_usage="exact" when the requested target appears unchanged in the example.
- Use target_usage="valid_inflection" when the example uses a grammatically transformed form of the SAME target, e.g. Spanish "adherirse a" → "se adhiere a", "darse cuenta de" → "me di cuenta de", English "go" → "went", or equivalent morphology in any language.
- Use target_usage="mismatch" when the example uses a synonym, different lexeme, typo, or visually similar word instead of the requested target.
- Use target_usage="uncertain" only when you genuinely cannot determine whether the surface form belongs to the requested target.
- Put the EXACT surface form copied from the example into used_form_in_example. It must be a literal substring of example, not the dictionary/headword form unless that exact form appears.
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
  "target_usage": "exact | valid_inflection | mismatch | uncertain",
  "collocation_naturalness": "ok",
  "translation_naturalness": "ok"
}}
"""


def build_vocabulary_batch_prompt(
    words_or_phrases: list[str],
    target_language: str,
    explanation_language: str,
    topic_context: str = "",
) -> str:
    """Build one request that returns several independent vocabulary cards."""
    items = [str(item).strip() for item in words_or_phrases if str(item).strip()]
    if not items:
        raise ValueError("At least one vocabulary item is required.")
    explanation_language = explanation_language.strip()
    if not explanation_language:
        raise ValueError("Explanation language must be selected explicitly.")
    effective_explanation_language = (
        target_language if explanation_language == "Same as target" else explanation_language
    )
    no_translation = explanation_language == "No translation"
    explanation_rules = _language_quality_rules(effective_explanation_language, target_language)
    topic_rules = _topic_rules(topic_context)
    numbered_items = "\n".join(
        f'{index + 1}. "{item}"' for index, item in enumerate(items)
    )

    return f"""
You are a professional {target_language} language teacher and flashcard quality reviewer.

Create EXACTLY {len(items)} independent vocabulary flashcards, one for each input below.

INPUTS — preserve this order:
{numbered_items}

Target language: {target_language}
Explanation language: {effective_explanation_language}

Critical batch rules:
- Return exactly one card per input, in exactly the same order as INPUTS.
- For every valid card, word_or_phrase MUST exactly equal its corresponding input.
- Never merge, skip, reorder, or replace inputs.
- Treat each complete input as one learning item before analysing individual words.
- Accept useful words, phrases, collocations, sentence fragments, idioms, grammar patterns, and lesson/context expressions.
- Set is_valid=false only for true garbage, wrong-language text, malformed/nonexistent wording, or an unusable obvious typo.
- For invalid input, keep word_or_phrase equal to the original input and leave flashcard content empty.
- Definition is short, clear, and written in {target_language}.
{explanation_rules}
{topic_rules}
Example and quality rules for EVERY card:
- Use the target itself or a correct inflected/conjugated form of the SAME lexical target.
- Do not substitute a synonym or visually similar word.
- Prefer natural, common, realistic usage and established collocations.
- used_form_in_example must be the exact surface form copied from example.
- example_uses_target is true only when the example really uses the target or its valid inflection.
- target_usage is exactly: exact, valid_inflection, mismatch, or uncertain.
- collocation_naturalness and translation_naturalness are exactly: ok, weak, or bad.
- topic_fit is exactly: ok, weak, mismatch, or not_applicable.
- Put any uncertainty or quality problem into quality_warnings instead of hiding it.
- Run the same quality self-check independently for every item.

Return ONLY valid JSON. No markdown and no comments.
Return this exact top-level structure:

{{
  "cards": [
    {{
      "is_valid": true,
      "validation_error": "",
      "suggested_correction": "",
      "explanation_language": "{effective_explanation_language}",
      "word_or_phrase": "EXACT corresponding input",
      "target_language": "{target_language}",
      "part_of_speech": "string",
      "definition": "string",
      "translation": "{'' if no_translation else 'string'}",
      "example": "string",
      "example_translation": "{'' if no_translation else 'string'}",
      "synonyms": ["string"],
      "collocations": ["string"],
      "grammar_note": "string",
      "topic_fit": "ok",
      "topic_warning": "",
      "quality_warnings": [],
      "used_form_in_example": "string",
      "example_uses_target": true,
      "target_usage": "exact",
      "collocation_naturalness": "ok",
      "translation_naturalness": "ok"
    }}
  ]
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
- Set example_uses_target to true only if the final example contains the selected target item or a correct inflected/conjugated/declined/reflexive form of that SAME lexical target.
- Set target_usage to exactly one of: "exact", "valid_inflection", "mismatch", "uncertain".
- Use "valid_inflection" for a grammatically transformed form of the same lexical target, not for a synonym.
- Put the EXACT surface form copied from the final example into used_form_in_example; it must occur literally in the example.
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
  "target_usage": "exact | valid_inflection | mismatch | uncertain",
  "collocation_naturalness": "ok",
  "translation_naturalness": "ok"
}}
"""


def build_sentence_based_cards_batch_prompt(
    raw_items: list[str],
    target_language: str,
    explanation_language: str,
    topic_context: str = "",
) -> str:
    """Build one request for several target + provided-sentence cards."""
    items = [str(item).strip() for item in raw_items if str(item).strip()]
    if not items:
        raise ValueError("At least one provided-example item is required.")

    parsed: list[tuple[str, str]] = []
    for raw_item in items:
        target_item, provided_sentence = _split_target_and_sentence(raw_item)
        if not target_item or not provided_sentence:
            raise ValueError(
                "Batched Provided examples require explicit 'target | sentence' rows."
            )
        parsed.append((target_item, provided_sentence))

    explanation_language = explanation_language.strip()
    if not explanation_language:
        raise ValueError("Explanation language must be selected explicitly.")
    effective_explanation_language = (
        target_language if explanation_language == "Same as target" else explanation_language
    )
    no_translation = explanation_language == "No translation"
    explanation_rules = _language_quality_rules(effective_explanation_language, target_language)
    topic_rules = _topic_rules(topic_context)

    numbered_items = "\n".join(
        f'{index + 1}. target="{target}" | sentence="{sentence}"'
        for index, (target, sentence) in enumerate(parsed)
    )

    return f"""
You are a professional {target_language} language teacher and flashcard quality reviewer.

Create EXACTLY {len(parsed)} independent sentence-based flashcards.

INPUTS — preserve this order and pairing:
{numbered_items}

Target language: {target_language}
Explanation language: {effective_explanation_language}

Critical batch rules:
- Return exactly one card per input and keep the same order.
- NEVER mix a target with another input's sentence.
- word_or_phrase MUST exactly equal the corresponding target.
- example MUST preserve the corresponding provided sentence.
- Do not invent a replacement example.
- Do not change the sentence meaning.
- Only a tiny obvious typo correction is allowed; if you make one, add a quality warning.
- Treat each target + sentence pair independently.
- Definition must explain that target in {target_language}.
{explanation_rules}
{topic_rules}
Quality rules for EVERY card:
- example_uses_target is true only when the example contains the target or a valid inflected form of the SAME lexical target.
- used_form_in_example must be copied literally from the example.
- target_usage is exactly: exact, valid_inflection, mismatch, or uncertain.
- collocation_naturalness and translation_naturalness are exactly: ok, weak, or bad.
- topic_fit is exactly: ok, weak, mismatch, or not_applicable.
- Put uncertainty, a typo correction, awkward usage, or any mismatch into quality_warnings.
- If the sentence is not in {target_language}, set is_valid=false rather than inventing content.

Return ONLY valid JSON. No markdown and no comments.
Return this exact top-level structure:

{{
  "cards": [
    {{
      "is_valid": true,
      "validation_error": "",
      "suggested_correction": "",
      "explanation_language": "{effective_explanation_language}",
      "word_or_phrase": "EXACT corresponding target",
      "target_language": "{target_language}",
      "part_of_speech": "string",
      "definition": "string",
      "translation": "{'' if no_translation else 'string'}",
      "example": "EXACT corresponding provided sentence",
      "example_translation": "{'' if no_translation else 'string'}",
      "synonyms": ["string"],
      "collocations": ["string"],
      "grammar_note": "string",
      "topic_fit": "ok",
      "topic_warning": "",
      "quality_warnings": [],
      "used_form_in_example": "string",
      "example_uses_target": true,
      "target_usage": "exact",
      "collocation_naturalness": "ok",
      "translation_naturalness": "ok"
    }}
  ]
}}
"""


def build_batch_grammar_prompt(
    grammar_item: str,
    target_language: str,
    topic_context: str = "",
    explanation_language: str = "Same as target",
) -> str:
    """Generate one Grammar card using the strict v12.4.5 contract."""
    effective_explanation_language = (
        target_language
        if not explanation_language.strip() or explanation_language == "Same as target"
        else explanation_language
    )
    context = topic_context.strip()
    context_block = f"\nSOURCE CONTEXT (use only to understand the requested grammar):\n{context}\n" if context else ""
    return f"""
You are a professional {target_language} grammar teacher.
Create exactly ONE grammar learning item from the input below.

INPUT:
{grammar_item}

Target language: {target_language}
Explanation language: {effective_explanation_language}
{context_block}
The output has exactly five learner-facing fields:

TARGET
A short name of the grammar construction itself. It must not be a rule, explanation,
heading, or example sentence.

STRUCTURE
A compact grammatical pattern/formula showing how the construction is formed.

RULE
What the construction does and/or when it is used.

EXAMPLE
Exactly one natural, real sentence that USES the construction.
A sentence that merely describes the rule is NOT an example.

EXPLANATION
A concise learner-friendly explanation written in {effective_explanation_language}.

Bad EXAMPLE:
"Third conditional sentences are used to talk about unreal past situations."
Reason: it talks ABOUT the construction but does not USE it.

Good EXAMPLE:
"If I had known about the meeting, I would have joined you."

Bad TARGET:
"have with this meaning is a dynamic (action) verb and can be used in continuous tenses"
Reason: this is a rule/explanation, not the name of the construction.

Good TARGET:
"have as a dynamic verb"

Good complete example:
TARGET: have as a dynamic verb
STRUCTURE: have + activity/experience -> continuous form possible
RULE: When have describes an activity or experience rather than possession, it can be used in continuous tenses.
EXAMPLE: We're having dinner at the moment.

Before returning JSON, verify the result semantically in this SAME request:
- example_demonstrates_structure = true ONLY if EXAMPLE actually contains and demonstrates STRUCTURE.
- target_is_structure = true ONLY if TARGET is a concise grammar construction, not a rule/explanation/sentence.
If either check would be false, FIX the learner-facing fields first and check again.
Do not use regex-style heuristics or keyword matching as a substitute for this semantic check.

Return ONLY valid JSON with EXACTLY these keys:
{{
  "target": "short grammar construction",
  "structure": "compact grammar pattern",
  "rule": "what it does / when to use it",
  "example": "one real sentence using the construction",
  "explanation": "explanation in {effective_explanation_language}",
  "example_demonstrates_structure": true,
  "target_is_structure": true
}}
"""

def build_batch_grammar_cards_prompt(
    grammar_items: list[str],
    target_language: str,
    topic_contexts: list[str] | None = None,
    explanation_language: str = "Same as target",
) -> str:
    """Generate several Grammar cards in one request with per-item context."""
    requested = [str(item).strip() for item in grammar_items]
    contexts = topic_contexts or [""] * len(requested)
    if len(contexts) != len(requested):
        raise ValueError("Grammar batch contexts must match grammar item count.")
    effective_explanation_language = (
        target_language
        if not explanation_language.strip() or explanation_language == "Same as target"
        else explanation_language
    )
    entries = []
    for index, (grammar_item, context) in enumerate(zip(requested, contexts), start=1):
        context_text = str(context or "").strip()
        context_block = (
            f"\nSOURCE CONTEXT (use only to understand this grammar item):\n{context_text}"
            if context_text
            else ""
        )
        entries.append(f"ITEM {index}\nINPUT:\n{grammar_item}{context_block}")
    items_block = "\n\n".join(entries)
    return f"""
You are a professional {target_language} grammar teacher.
Create exactly {len(requested)} grammar learning items, one for each input below, IN THE SAME ORDER.

Target language: {target_language}
Explanation language: {effective_explanation_language}

{items_block}

For EACH item use exactly this learner-facing contract:
- target: a short name of the grammar construction itself, never a rule/explanation/example sentence
- structure: a compact grammatical pattern/formula
- rule: what the construction does and/or when it is used
- example: exactly one natural sentence that actually USES the construction
- explanation: a concise learner-friendly explanation in {effective_explanation_language}
- example_demonstrates_structure: true only after semantic self-check
- target_is_structure: true only after semantic self-check

Important:
- Keep output order identical to input order.
- Do not merge, skip, duplicate, or reorder items.
- Each item's SOURCE CONTEXT belongs only to that item.
- A sentence describing a grammar rule is not a valid example.
- If either semantic check would be false, fix that item's learner-facing fields before returning JSON.

Return ONLY valid JSON, no markdown:
{{
  "cards": [
    {{
      "target": "short grammar construction",
      "structure": "compact grammar pattern",
      "rule": "what it does / when to use it",
      "example": "one real sentence using the construction",
      "explanation": "explanation in {effective_explanation_language}",
      "example_demonstrates_structure": true,
      "target_is_structure": true
    }}
  ]
}}
"""


def _conversation_flashcard_instructions(flashcard_context: str) -> str:
    """Return strict teaching rules for flashcard-based conversation mode."""
    context = (flashcard_context or "").strip()
    if not context:
        return ""
    return f"""

FLASHCARD-BASED CONVERSATION MODE
The learner selected flashcards as the basis of this conversation.
Use the material below as the learning syllabus, not as a quiz answer key.
The card content is authoritative. Do not invent a conflicting meaning.

Teaching rules:
- Lead a natural conversation rather than asking for definitions or reading a list.
- Ask questions that create a realistic opportunity to use 1-3 target items.
- The FIRST question in a flashcard session must be clearly grounded in 1-2 exact targets from FLASHCARD MATERIAL. Never open with a generic question unrelated to the selected targets.
- Every next question should normally create an opportunity to use at least one NOT USED YET target until the session has given unused targets a fair chance.
- Prefer flashcards marked NOT USED YET before recycling cards marked ALREADY USED.
- Do not base two consecutive questions on the same target unless the learner asks about it or clearly needs clarification.
- Recycle already-used targets only after giving unused session targets a fair chance.
- Do not force all flashcards into one answer.
- Respect the meanings, definitions, card backs, examples, and usage supplied with the cards.
- CARD BACK is the original reverse side of a generic Anki card. It may contain a translation,
  definition, explanation, or example. Use it faithfully and infer its role conservatively.
- If the learner says they do not know a target, asks what it means, or asks how it differs
  from something else, answer that content question directly using the matching card material.
- If the matching card does not contain enough information, say so briefly instead of inventing
  a precise definition.
- Existing flashcard targets are practice material, not new-card suggestions.
- Use exact targets only as speaking cues in "expressions_to_use_next".
- Put an item in "new_flashcard_candidates" only when it is a genuinely new expression
  discovered in the current exchange. A longer collocation may contain an existing target,
  but the exact target itself must never be proposed as a new card.
- Keep all learner-facing tutor replies and questions in the selected target language.

FLASHCARD MATERIAL
<<<FLASHCARDS
{context}
FLASHCARDS>>>
"""


def build_conversation_start_prompt(
    topic: str,
    target_language: str,
    flashcard_context: str = "",
) -> str:
    """Build the first question for topic or flashcard-based conversation."""
    flashcard_rules = _conversation_flashcard_instructions(flashcard_context)
    if flashcard_context:
        # Flashcard mode is intentionally isolated from topic mode. A stale topic
        # value must never steer the tutor away from the selected cards.
        topic_instruction = "Use the flashcard material as the only conversation focus. Ignore any stale topic value."
    else:
        topic_instruction = f'Conversation topic: "{topic}".'
    return f"""
You are a supportive {target_language} conversation teacher.
{topic_instruction}
{flashcard_rules}
Start a short conversation in {target_language}.
Ask ONE natural, open question suitable for a 2-5 sentence answer.
Do not assume the learner already knows every flashcard; be ready to explain one naturally.
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
    flashcard_context: str = "",
    conversation_history: str = "",
) -> str:
    """Build feedback plus a real conversational response and next question."""
    feedback_language = feedback_language.strip()
    if not feedback_language:
        raise ValueError("Feedback language must be selected explicitly.")
    effective_feedback_language = target_language if feedback_language == "Same as target" else feedback_language
    flashcard_rules = _conversation_flashcard_instructions(flashcard_context)
    history = (conversation_history or "").strip()
    history_block = (
        f"""
RECENT CONVERSATION HISTORY
<<<HISTORY
{history}
HISTORY>>>
"""
        if history
        else "\nNo earlier conversation history is available.\n"
    )

    if flashcard_context:
        suggestion_contract = f"""
FLASHCARD-MODE VOCABULARY OUTPUT CONTRACT
- "suggested_vocabulary" must be an empty list. Existing flashcards are not new suggestions.
- "expressions_to_use_next" must contain 2-4 relevant speaking cues for the learner's next
  answer. These MAY reuse exact flashcard targets or useful collocations based on them.
- "new_flashcard_candidates" may contain 0-3 genuinely new reusable expressions worth saving.
  Never include an exact target already present in FLASHCARD MATERIAL.
- A longer expression such as "impartir una clase magistral" is allowed when the existing
  target is "clase magistral", because the longer collocation adds new learning value.
- Every new_flashcard_candidate must be copied exactly from the learner answer, a correction,
  corrected_version, advanced_answer, mini_practice, or tutor_reply in THIS exchange.
- When the exchange naturally produces a useful new collocation or reusable chunk that genuinely
  improves the learner's language, include it rather than returning an empty list by default.
- Do not seed a random expression into next_question merely to justify proposing it.
- If no genuinely new expression appeared, return an empty new_flashcard_candidates list.
"""
        suggestion_json = '''
  "suggested_vocabulary": [],
  "expressions_to_use_next": ["relevant existing target", "useful speaking cue"],
  "new_flashcard_candidates": ["new grounded collocation"]
'''
    else:
        suggestion_contract = f"""
TOPIC-MODE VOCABULARY OUTPUT CONTRACT
- "suggested_vocabulary" must contain 4 useful reusable words, phrases, or chunks from the
  current exchange that are suitable for staging as new flashcards.
- "expressions_to_use_next" and "new_flashcard_candidates" must both be empty lists.
"""
        suggestion_json = '''
  "suggested_vocabulary": ["chunk 1", "chunk 2", "chunk 3", "chunk 4"],
  "expressions_to_use_next": [],
  "new_flashcard_candidates": []
'''

    return f"""
You are a warm, practical {target_language} conversation teacher.
{("Conversation focus: flashcard targets only. Ignore any stale topic value." if flashcard_context else f'Conversation topic/focus: "{topic}"')}
{flashcard_rules}
{history_block}
Current tutor question: "{question}"
Current learner answer: "{answer}"
Requested level: "{improvement_level}"
Feedback language: {effective_feedback_language}

Two-layer response rule:
1. Language coaching: correct and improve the learner's wording.
2. Real conversation: answer or react to the CONTENT of what the learner said before asking
   another question. Never ignore a learner's direct question or request for an explanation.

Teaching style:
- Be positive but concise, like a good human teacher in a real conversation.
- Highlight important mistakes clearly, but do not label a correct sentence as wrong merely because
  a more sophisticated alternative exists.
- Separate genuine language errors from optional naturalness/style improvements.
- Always explain HOW to improve, not only what is wrong.
- Keep feedback compact so the learner can continue speaking instead of reading a long lesson.
- The learner may use speech-to-text. If RECENT CONVERSATION HISTORY contains an INPUT SOURCE note
  for the current answer, treat obviously garbled proper names, impossible words, or phonetic-looking
  fragments as possible transcription errors rather than grammar/vocabulary mistakes. Do not invent
  a transcription correction unless the intended wording is reasonably clear from context.
- Use {effective_feedback_language} for feedback, explanations, and mini_practice.
- Use {target_language} for corrected_version, advanced_answer, tutor_reply, next_question,
  suggested_vocabulary, expressions_to_use_next, and new_flashcard_candidates.
- Do not switch to another language or writing system.
- Use RECENT CONVERSATION HISTORY to stay coherent and avoid repeating questions already answered.

Output requirements:
- "feedback" must be ONE concise encouraging sentence that names only the main improvement.
- "corrections" must contain 0-3 high-value items. Do not manufacture an error when the answer is correct.
- Each correction must include "kind":
  * "error" for a genuine grammar, vocabulary, spelling, or syntax error;
  * "improvement" for wording that is already acceptable but could sound more natural/advanced;
  * "possible_transcription" only when the current answer came from STT and a fragment strongly looks
    like a recognition glitch (especially malformed proper names or nonsensical phonetic fragments).
- Each correction must show: learner's original fragment, corrected/more natural fragment, and a short
  explanation in {effective_feedback_language}.
- Never present an "improvement" as if the learner's original wording were incorrect.
- Never count a "possible_transcription" item as a learner language mistake.
- "corrected_version" must preserve the learner's idea but fix errors.
- "advanced_answer" must be a richer natural version at {improvement_level}.
- "tutor_reply" must be a direct 1-3 sentence conversational response in {target_language}.
  It must answer clarification questions and explain an unknown flashcard before moving on.
  Stay primarily a language-conversation tutor: answer relevant factual questions briefly, but do not
  turn the exchange into a long technical/legal/domain lecture or present uncertain specialist advice
  as authoritative fact.
- When explaining a flashcard, use its exact MEANING, DEFINITION, CARD BACK, EXAMPLE, or USAGE
  from FLASHCARD MATERIAL. Do not confidently invent details that contradict or exceed the card.
- "next_question" must contain ONE natural follow-up question in {target_language}.
  Keep it separate from tutor_reply. In flashcard mode, create an opportunity to use a relevant
  target item, but do not jump abruptly to an unrelated expression.
{suggestion_contract}
- "mini_practice" may be empty. Use one short task in {effective_feedback_language} only when it adds
  clear value; do not force a mini exercise after every turn.
- Return ONLY valid JSON without markdown.

{{
  "feedback_language": "{effective_feedback_language}",
  "feedback": "Good attempt — your meaning was clear. The main thing to improve is ...",
  "corrections": [
    {{
      "kind": "error | improvement | possible_transcription",
      "original": "learner fragment",
      "correction": "corrected or more natural fragment",
      "explanation": "short explanation in {effective_feedback_language}"
    }}
  ],
  "corrected_version": "string in {target_language}",
  "advanced_answer": "string in {target_language}",
  "mini_practice": "short task in {effective_feedback_language}",
  "tutor_reply": "direct conversational response in {target_language}",
  "next_question": "one question in {target_language}",
{suggestion_json}
}}
"""


def build_grammar_analysis_prompt(
    sentence: str,
    target_language: str,
    explanation_language: str = "Same as target",
) -> str:
    """Analyze one sentence using the same strict Grammar contract as Batch generation."""
    effective_explanation_language = (
        target_language
        if not explanation_language.strip() or explanation_language == "Same as target"
        else explanation_language
    )
    return f"""
You are a professional {target_language} grammar teacher.
Create exactly ONE grammar learning item from this source sentence:

{sentence}

Target language: {target_language}
Explanation language: {effective_explanation_language}

Use this exact learner-facing contract:
TARGET = short name of the grammar construction.
STRUCTURE = compact grammatical pattern/formula.
RULE = what the construction does / when it is used.
EXAMPLE = exactly one natural sentence that uses the construction. Preserve the source sentence exactly as EXAMPLE.
EXPLANATION = concise explanation in {effective_explanation_language}.

The TARGET must not be a prose rule or sentence.
The EXAMPLE must demonstrate the selected STRUCTURE; a sentence describing grammar is not a valid example.
Choose a structure that the supplied source sentence genuinely demonstrates.

In this SAME request, verify semantically:
- example_demonstrates_structure = true only if EXAMPLE genuinely demonstrates STRUCTURE.
- target_is_structure = true only if TARGET names a concise grammar construction.
If either would be false, fix TARGET/STRUCTURE selection before returning the answer.

Return ONLY valid JSON with EXACTLY these keys:
{{
  "target": "short grammar construction",
  "structure": "compact grammar pattern",
  "rule": "what it does / when to use it",
  "example": "{sentence}",
  "explanation": "explanation in {effective_explanation_language}",
  "example_demonstrates_structure": true,
  "target_is_structure": true
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
- Candidate count must be driven by the source content, not by a fixed quota. Return every genuinely useful grammar candidate and do not add weak items to reach a number.
- A short source may yield only a few candidates; a dense grammar lesson may legitimately yield many.
- Preserve useful source focus exactly: grammar pattern, connector, word form, transformation, or lesson structure.
- Preserve slash alternatives such as "Actually / Incidentally" as one visible target unless the source clearly separates them.
- Skip OCR garbage, page numbers, isolated headers, and duplicate items.

Core field contract:
- target = a SHORT, teachable grammar focus/pattern. It must never be a full textbook rule, definition, explanatory sentence, or example sentence.
- If a source rule is long (for example "have with this meaning is a dynamic verb and can be used in continuous tenses"), normalize target to a concise label such as "have as a dynamic verb" and keep the original wording in source_rule.
- Prefer a conventional grammar name when one exists (for example "Third conditional"), otherwise use a compact descriptive label.
- sentence = ONLY a learner-visible example sentence suitable for audio.
- source_rule = ONLY the original rule, definition, explanation, use note, or exercise instruction.
- reason = short reason why this candidate was extracted.
- sentence must never be a grammar definition, textbook rule, exercise instruction, heading, or meta-sentence about the grammar item.
- source_rule must never be used as the audio sentence.
- Never put the rule itself in sentence; when a rule has no source example, generate a natural learner-visible example and keep the rule in source_rule.

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


Review metadata (for UI ranking only; NEVER use it to invent or drop candidates):
- advancedness = advanced | normal | basic. Judge lexical/grammar sophistication, not mere rarity.
- topic_relevance = high | medium | low. High means the item expresses a central concept/theme of this lesson/source, not merely that it appears once.
- reusability = high | medium | low. High means the learner can naturally reuse it in many real situations.
- learning_value = high | medium | low. High means it is especially worth active learning.
- document_specificity = high | medium | low. High means a proper name, organisation, regulation/title, one-off label, or source-specific wording.
- Do not force a distribution. A source may have many or few items in any tier.

Final self-check before returning JSON:
- target MUST be a concise grammar item. If target reads like a complete rule/explanation sentence, rewrite it before returning JSON.
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
      "confidence": "high | medium | low",
      "advancedness": "advanced | normal | basic",
      "topic_relevance": "high | medium | low",
      "reusability": "high | medium | low",
      "learning_value": "high | medium | low",
      "document_specificity": "high | medium | low"
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
- words, terms, phrases, idioms, collocations, specialist vocabulary, expression headings, and explicit vocabulary-list items when there is NO good exact source usage sentence to preserve.
- glossary/definition/context items where nearby text explains the target but does not actually use the target in a complete learner example.

Use type="provided_example" automatically ONLY when source_role="usage_example" and:
- the source contains a complete useful sentence that is worth preserving as the learning context,
- the sentence clearly contains the selected target phrase/idiom/collocation (or a normal inflected form),
- the sentence is a real usage example rather than a heading, label, definition, list item, fragment, exercise, or task.

Before choosing the type, classify the visible fragment semantically as source_role:
- usage_example = a complete natural sentence that actually demonstrates the target in context.
- heading_label = a title, heading, category label, contrast label, personality-type label, table label, or similar non-sentence text.
- definition_context = text that defines/explains the target rather than demonstrating it in use.
- list_item = a vocabulary/list entry or compact paired/alternative item, not a learner sentence.
- fragment = incomplete or elliptical text that is not a standalone natural sentence.
- exercise = a question, instruction, gap-fill, transformation task, or other exercise material.
- unknown = use only when the fragment genuinely cannot be classified.

A fragment can contain the target and still NOT be a usage example. For example, "A PLANNER or SPONTANEOUS" is a heading/contrast label, so target="planner" must remain type="vocabulary" and must NOT preserve that fragment as the learner example.

Do not return a vocabulary candidate with a real source usage sentence merely because the target itself is vocabulary. In Smart vocabulary, a strong exact source usage example should be routed as provided_example so Queue preserves that sentence automatically.

Never return type="grammar" in Smart vocabulary mode.
Do not turn exercises/questions/tasks into provided examples.
"""
        source_example_rule = """
Source example rules:
- For Smart vocabulary, first classify source_role semantically. Only source_role="usage_example" may become type="provided_example".
- If a complete source sentence actually USES the target and is suitable as the learner example, return source_role="usage_example", type="provided_example", and put that exact sentence in sentence.
- For heading_label, definition_context, list_item, fragment, exercise, or unknown, keep type="vocabulary". Do not preserve that fragment as the learner example even if it contains the target.
- Keep type="vocabulary" when there is no good usage example. A definition/context fragment that explains the target without using it may stay in source_sentence as source context; it is NOT a provided example.
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

Your job is FULL-COVERAGE candidate extraction with lexical consolidation:
- Scan the ENTIRE source from beginning to end. Do not stop early and do not analyze only the first section.
- Candidate count must be driven by the source content, never by a fixed quota or target number.
- Extract all genuinely learnable intermediate/advanced vocabulary, but consolidate aggressively so the output is a clean study list rather than a token dump.
- Return ONE candidate per underlying lexical item or fixed expression.
- Do not return the same lemma in several inflected forms unless the forms have different meanings or are independently learnable expressions.
- Do not return both a single word and multiple trivial phrases built around that same word unless the phrase is a real collocation, idiom, phrasal verb or fixed expression worth learning separately.
- Deduplicate repeated occurrences across the document before returning JSON.
- Prefer the canonical dictionary form for ordinary verbs/nouns/adjectives when the source uses an inflected form.
- Explicit vocabulary lists, idioms, collocations and lesson expressions should all be preserved.
- In continuous prose, include non-basic transferable words, phrasal verbs, idioms, collocations, fixed/semi-fixed phrases, useful academic/descriptive vocabulary and specialist terms.
- Exclude basic/function vocabulary, grammatical glue, dates/numbers, names, headings with no lexical value, OCR garbage, repeated boilerplate, legal/administrative formulae that are too document-specific to be useful, and near-duplicate paraphrases.
- Review metadata is for ranking only, but an item that is merely incidental, document-specific or not useful for active learning should not become a candidate at all.
- A dense lesson may still yield dozens of candidates, but hundreds of near-duplicates or trivial variants indicate failed extraction.

Priority order:
1. Extract every explicit bullet/list item under headings such as Vocabulario, Vocabulary, Léxico, Lexique, Wortschatz, Expresiones, Expresiones coloquiales, Idioms, Expressions when it is suitable for learning.
2. Extract every numbered idiom/expression heading from expression sections.
3. Scan reading text sentence by sentence from start to finish and extract useful intermediate/advanced lexical candidates, consolidating repeated/inflected variants into one canonical target.
4. Skip exercises, questions, tasks, page footers, emails, websites, image filenames, copyright/footer text, tutor IDs, page numbers and repetitive legal/administrative boilerplate unless they contain a genuinely reusable lexical target.
5. When uncertain between two near-duplicate candidates, keep the more canonical/reusable one. Do not manufacture Optional rows just for coverage.

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
- source_role = usage_example | heading_label | definition_context | list_item | fragment | exercise | unknown
- reason = short reason or source heading
- needs_review = true only for uncertain, OCR-damaged, or expanded variants

Review metadata (for UI ranking only; NEVER use it to invent or drop candidates):
- advancedness = advanced | normal | basic. Judge lexical/grammar sophistication, not mere rarity.
- topic_relevance = high | medium | low. High means the item expresses a central concept/theme of this lesson/source, not merely that it appears once.
- reusability = high | medium | low. High means the learner can naturally reuse it in many real situations.
- learning_value = high | medium | low. High means it is especially worth active learning.
- document_specificity = high | medium | low. High means a proper name, organisation, regulation/title, one-off label, or source-specific wording.
- Do not force a distribution. A source may have many or few items in any tier.

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
      "source_role": "usage_example | heading_label | definition_context | list_item | fragment | exercise | unknown",
      "reason": "short reason or source heading",
      "source_type": "vocabulary_list | colloquial_expression | reading_text_collocation | dialogue_example | highlighted_item | table_row | expanded_variant | provided_example",
      "strategy": "vocabulary_candidate | vocabulary_with_source_sentence | expanded_vocabulary_variant | preserve_source_sentence",
      "needs_review": false,
      "confidence": "high | medium | low",
      "advancedness": "advanced | normal | basic",
      "topic_relevance": "high | medium | low",
      "reusability": "high | medium | low",
      "learning_value": "high | medium | low",
      "document_specificity": "high | medium | low"
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
- Candidate count must be driven by the source content, not by a fixed quota. Return every genuinely useful candidate and do not pad or truncate to a target number.
- A short source may yield only a few candidates; a dense lesson may legitimately yield 100+ candidates.

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

Review metadata (for UI ranking only; NEVER use it to invent or drop candidates):
- advancedness = advanced | normal | basic. Judge lexical/grammar sophistication, not mere rarity.
- topic_relevance = high | medium | low. High means the item expresses a central concept/theme of this lesson/source, not merely that it appears once.
- reusability = high | medium | low. High means the learner can naturally reuse it in many real situations.
- learning_value = high | medium | low. High means it is especially worth active learning.
- document_specificity = high | medium | low. High means a proper name, organisation, regulation/title, one-off label, or source-specific wording.
- Do not force a distribution. A source may have many or few items in any tier.

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
      "source_rule": "short original rule/exercise text when relevant",
      "advancedness": "advanced | normal | basic",
      "topic_relevance": "high | medium | low",
      "reusability": "high | medium | low",
      "learning_value": "high | medium | low",
      "document_specificity": "high | medium | low"
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
- Candidate count must be driven by what is actually present on the page, never by a fixed quota. Return every genuinely useful candidate and do not pad or truncate to a target number.
- A sparse page may yield only a few candidates; a dense vocabulary/grammar page may legitimately yield many.
- Do NOT extract every word from continuous prose. For ordinary paragraphs, scan sentence by sentence and extract every clearly learnable non-basic item that is useful for an intermediate/advanced learner: phrasal verbs, idioms, collocations, fixed/semi-fixed phrases, useful academic/descriptive vocabulary, specialist terms, and transferable single words with meaningful learning value.
- If the page has explicit lists/tables, extract those first. If it is mostly prose, do not collapse the result to a tiny "top few" subset: a dense reading passage can legitimately yield dozens of useful vocabulary candidates. Omit only genuinely basic, one-off/proper-name, OCR-garbage, or low-learning-value items.

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
- In Smart vocabulary mode, after explicit lists/headings are handled, scan reading prose systematically for reusable learner vocabulary. Include useful single words as well as collocations/phrases; do not restrict prose extraction to only a handful of standout items.
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

Review metadata (for UI ranking only; NEVER use it to invent or drop candidates):
- advancedness = advanced | normal | basic. Judge lexical/grammar sophistication, not mere rarity.
- topic_relevance = high | medium | low. High means the item expresses a central concept/theme of this lesson/source, not merely that it appears once.
- reusability = high | medium | low. High means the learner can naturally reuse it in many real situations.
- learning_value = high | medium | low. High means it is especially worth active learning.
- document_specificity = high | medium | low. High means a proper name, organisation, regulation/title, one-off label, or source-specific wording.
- Do not force a distribution. A source may have many or few items in any tier.

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
      "confidence": "high | medium | low",
      "advancedness": "advanced | normal | basic",
      "topic_relevance": "high | medium | low",
      "reusability": "high | medium | low",
      "learning_value": "high | medium | low",
      "document_specificity": "high | medium | low"
    }}
  ]
}}
"""
