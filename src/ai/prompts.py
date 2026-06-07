"""Prompt templates for vocabulary flashcard generation."""

from __future__ import annotations

import random


EXAMPLE_CONTEXTS = [
    # Home and everyday life
    "an ordinary situation at home",
    "cleaning, organising, or fixing something at home",
    "preparing for a busy day",
    "relaxing after a tiring day",
    "talking with a partner at home",
    "buying something practical for the house",
    "dealing with a delivery, package, or small household problem",
    "getting ready for a short trip",

    # Food and cooking
    "cooking dinner at home",
    "trying a new recipe",
    "preparing a healthy meal",
    "using an air fryer or baking something",
    "ordering food in a restaurant",
    "talking about Italian food",
    "choosing ingredients in a supermarket",
    "having coffee or breakfast in a café",
    "talking about a dish that tasted surprisingly good or bad",
    "planning what to eat after exercise or after travelling",

    # Travel and places
    "travelling in Italy",
    "planning a trip to the Canary Islands",
    "spending time near the sea",
    "walking around a lake or coastal town",
    "asking for directions while travelling",
    "using a train, bus, airport, or ferry",
    "booking accommodation or an activity",
    "discovering a beautiful viewpoint or hiking route",
    "talking about a holiday that has just ended",
    "coming back home after a trip",
    "visiting a small town, market, or local café",
    "dealing with a small travel inconvenience",

    # Nature and outdoor life
    "walking by the sea",
    "going on a mountain or coastal hike",
    "watching a sunset or beautiful landscape",
    "taking care of herbs or plants on a balcony",
    "talking about weather during an outdoor plan",
    "spending a peaceful day outdoors",
    "choosing a route for a weekend walk",
    "describing a place that feels relaxing",

    # Sport and wellbeing
    "going swimming",
    "training at the gym",
    "doing yoga or stretching",
    "going for a long walk",
    "feeling tired after an active week",
    "trying to sleep better and recover",
    "choosing a manageable exercise plan",
    "talking about motivation to stay active",
    "taking care of wellbeing without overdoing things",

    # Photography, hobbies, and creativity
    "taking photos during a trip",
    "choosing the best photo from a beautiful place",
    "planning a photography blog post",
    "playing guitar or piano at home",
    "learning a song or practising a hobby",
    "reading a book or listening to a podcast",
    "talking about an interesting story or documentary",
    "creating something for a personal project",

    # Friends and social situations
    "chatting with a friend about recent plans",
    "meeting someone for coffee",
    "telling a funny story from a trip",
    "making weekend plans with another person",
    "expressing excitement, disappointment, or relief",
    "asking someone for advice",
    "explaining a misunderstanding",
    "meeting new people in a relaxed situation",

    # Languages and learning
    "learning English or Spanish vocabulary",
    "trying to explain something in a foreign language",
    "forgetting a word during a conversation",
    "practising how to speak more naturally",
    "studying a technical topic step by step",
    "learning something that initially seemed difficult",
    "preparing for a challenging question",

    # Technology and personal projects
    "working on a small Python project",
    "debugging a frustrating technical problem",
    "building a machine learning portfolio project",
    "analysing data or checking model results",
    "creating a useful automation tool",
    "working on a travel-planning application",
    "building a local AI assistant or RAG prototype",
    "organising files, logs, or project documentation",
    "solving a problem after several failed attempts",

    # Work and career — present, but not dominant
    "a realistic situation at work",
    "explaining a technical issue to a colleague",
    "discussing a machine vision or production problem",
    "preparing for a job interview",
    "describing a project during an interview",
    "receiving feedback on a job application",
    "talking about career plans and next steps",
    "handling stress during a professional conversation",

    # Opinions, emotions, and normal conversations
    "expressing an honest opinion about something",
    "being pleasantly surprised by an experience",
    "feeling annoyed because something stopped working",
    "feeling relieved after solving a problem",
    "deciding whether something is worth the money",
    "changing plans because the original idea was not good",
    "talking about something that seems more difficult than it really is",
    "realising that a small change makes a big difference",
]


def build_vocabulary_prompt(word_or_phrase: str, target_language: str) -> str:
    """Build a prompt for generating one vocabulary flashcard.

    Args:
        word_or_phrase: Word or phrase provided by the user.
        target_language: Language being learned, for example English or Spanish.

    Returns:
        Prompt string for the language model.
    """
    example_context = random.choice(EXAMPLE_CONTEXTS)

    return f"""
You are a professional {target_language} teacher helping a Polish speaker learn {target_language} vocabulary.

Create ONE high-quality flashcard for this {target_language} word or phrase:

"{word_or_phrase}"

Requirements:
- The definition must be short, clear, and written in {target_language}.
- The Polish translation must be natural and useful.
- The example sentence must be natural, practical, and useful for real communication.
- Use this situation for the example sentence: {example_context}.
- The example sentence must clearly demonstrate the meaning of the word or phrase.
- Do not default to remote jobs, recruitment, software projects, office meetings, or data work unless they naturally fit the selected situation.
- Keep examples varied, realistic, and appropriate for normal everyday communication.
- Synonyms must be useful. If exact synonyms do not exist, provide close alternatives or useful related expressions.
- Collocations must show how the word or phrase is commonly used.
- The grammar note must be short and written in Polish.
- Return ONLY valid JSON.
- Do not use markdown.
- Do not add comments outside JSON.

Return this exact JSON structure:

{{
  "word_or_phrase": "string",
  "target_language": "{target_language}",
  "part_of_speech": "string",
  "definition": "string",
  "translation_pl": "string",
  "example": "string",
  "example_pl": "string",
  "synonyms": ["string", "string", "string"],
  "collocations": ["string", "string", "string"],
  "grammar_note": "string"
}}
"""

def build_conversation_start_prompt(topic: str, target_language: str) -> str:
    """Build a prompt for the first question in conversation practice."""
    return f"""
You are a supportive {target_language} conversation teacher helping a Polish speaker practise speaking naturally.

Start a short conversation in {target_language} about the learner's chosen topic:
"{topic}"

Requirements:
- Ask ONE natural, open question in {target_language}.
- Keep it appropriate for everyday conversation unless the topic is professional.
- The question should invite a 2-5 sentence answer.
- Do not give explanations or corrections yet.
- Return ONLY valid JSON.
- Do not use markdown.

Return this exact JSON structure:

{{
  "question": "string"
}}
"""


def build_conversation_feedback_prompt(
    topic: str,
    question: str,
    answer: str,
    target_language: str,
    improvement_level: str,
) -> str:
    """Build a prompt for reviewing one answer and giving a stronger model version."""
    return f"""
You are a supportive {target_language} conversation teacher helping a Polish speaker improve spontaneous communication.

Conversation topic: "{topic}"
Your question in {target_language}: "{question}"
Learner's answer in {target_language}: "{answer}"
Requested model-answer level: "{improvement_level}"

Requirements:
- Give short, practical feedback in Polish. Mention the most important corrections and one useful upgrade.
- Provide "corrected_version": preserve the learner's original idea and vocabulary as much as possible; only fix mistakes and obvious unnatural wording.
- Provide "advanced_answer": answer the same question again in {target_language}, but in a richer, more natural and more expressive way appropriate to the selected level.
- The advanced answer must add useful phrasing and detail, not merely reword the corrected version.
- For "Natural B1/B2", make the answer accessible, clear and naturally conversational.
- For "Strong B2/C1", use richer vocabulary, more varied sentence structure and useful idiomatic phrasing without sounding artificial.
- For "Professional / Interview", make the answer structured, confident and professional, suitable when the topic is work-related; if the topic is not professional, still make it polished rather than corporate.
- Ask ONE natural follow-up question in {target_language} to continue the same conversation.
- Suggest exactly 3 useful words or phrases in {target_language}, preferably drawn from the advanced answer and worth learning as flashcards.
- Do not produce a long grammar lesson.
- Return ONLY valid JSON.
- Do not use markdown.

Return this exact JSON structure:

{{
  "feedback_pl": "string",
  "corrected_version": "string",
  "advanced_answer": "string",
  "next_question": "string",
  "suggested_vocabulary": ["string", "string", "string"]
}}
"""

