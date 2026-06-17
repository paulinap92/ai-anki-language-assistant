"""Build interactive and printable exercises from Anki note fields."""

from __future__ import annotations

import html
import random
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def strip_html(value: str) -> str:
    """Convert an Anki HTML field to readable plain text."""
    parser = _TextExtractor()
    parser.feed(value or "")
    return html.unescape(" ".join(parser.parts)).strip()


@dataclass(frozen=True)
class PracticeItem:
    """Normalized data loaded from one supported Anki note."""

    note_id: int
    model_name: str
    item_type: str
    answer: str
    example: str
    definition: str
    part_of_speech: str = ""
    structure: str = ""
    meaning: str = ""

    @property
    def display_name(self) -> str:
        return self.answer


@dataclass(frozen=True)
class PracticeQuestion:
    """One multiple-choice practice question."""

    item: PracticeItem
    prompt: str
    options: list[str]
    correct_answer: str
    question_type: str


class PracticeService:
    """Normalize Anki cards and create exercises without calling an LLM."""

    VOCABULARY_MODEL = "AI Vocabulary Light Card"
    GRAMMAR_MODEL = "AI Grammar Light Card"

    @classmethod
    def from_anki_cards(cls, cards: Iterable[dict]) -> list[PracticeItem]:
        """Convert AnkiConnect ``cardsInfo`` records into practice items."""
        result: list[PracticeItem] = []
        seen_notes: set[int] = set()
        for card in cards:
            note_id = int(card.get("note", 0))
            if not note_id or note_id in seen_notes:
                continue
            seen_notes.add(note_id)
            model_name = str(card.get("modelName", ""))
            fields = card.get("fields", {}) or {}

            def field(name: str) -> str:
                raw = fields.get(name, {})
                return strip_html(str(raw.get("value", ""))) if isinstance(raw, dict) else ""

            if model_name == cls.VOCABULARY_MODEL:
                answer = field("Word")
                if not answer:
                    continue
                result.append(
                    PracticeItem(
                        note_id=note_id,
                        model_name=model_name,
                        item_type="vocabulary",
                        answer=answer,
                        example=field("Example"),
                        definition=field("Definition"),
                        part_of_speech=field("PartOfSpeech"),
                    )
                )
            elif model_name == cls.GRAMMAR_MODEL:
                sentence = field("Sentence")
                if not sentence:
                    continue
                result.append(
                    PracticeItem(
                        note_id=note_id,
                        model_name=model_name,
                        item_type="grammar",
                        answer=sentence,
                        example=field("ContextExample"),
                        definition=field("Usage"),
                        structure=field("Structure"),
                        meaning=field("Meaning"),
                    )
                )
        return result

    @classmethod
    def build_questions(
        cls,
        selected_items: list[PracticeItem],
        *,
        shuffle: bool = True,
        rng: random.Random | None = None,
    ) -> list[PracticeQuestion]:
        """Create one question for each selected item."""
        rng = rng or random.Random()
        questions = [cls._build_question(item, selected_items, rng) for item in selected_items]
        if shuffle:
            rng.shuffle(questions)
        return questions

    @classmethod
    def _build_question(
        cls,
        item: PracticeItem,
        pool: list[PracticeItem],
        rng: random.Random,
    ) -> PracticeQuestion:
        if item.item_type == "grammar":
            correct = item.structure or item.meaning or item.answer
            prompt = f"Which structure is used in this sentence?\n\n{item.answer}"
            candidates = [
                other.structure or other.meaning
                for other in pool
                if other.item_type == "grammar" and other.note_id != item.note_id
            ]
            return cls._multiple_choice(item, prompt, correct, candidates, "grammar_structure", rng)

        gap = cls._make_gap(item.example, item.answer)
        if gap:
            prompt = f"Complete the sentence:\n\n{gap}"
            question_type = "vocabulary_gap"
        else:
            prompt = f"Which word or phrase matches this definition?\n\n{item.definition}"
            question_type = "vocabulary_definition"

        same_pos = [
            other.answer
            for other in pool
            if other.item_type == "vocabulary"
            and other.note_id != item.note_id
            and item.part_of_speech
            and other.part_of_speech.casefold() == item.part_of_speech.casefold()
        ]
        fallback = [
            other.answer
            for other in pool
            if other.item_type == "vocabulary" and other.note_id != item.note_id
        ]
        candidates = same_pos + [word for word in fallback if word not in same_pos]
        return cls._multiple_choice(item, prompt, item.answer, candidates, question_type, rng)

    @staticmethod
    def _multiple_choice(
        item: PracticeItem,
        prompt: str,
        correct: str,
        candidates: list[str],
        question_type: str,
        rng: random.Random,
    ) -> PracticeQuestion:
        unique = []
        for candidate in candidates:
            candidate = candidate.strip()
            if candidate and candidate.casefold() != correct.casefold() and candidate not in unique:
                unique.append(candidate)
        rng.shuffle(unique)
        options = [correct, *unique[:3]]
        rng.shuffle(options)
        return PracticeQuestion(
            item=item,
            prompt=prompt,
            options=options,
            correct_answer=correct,
            question_type=question_type,
        )

    @staticmethod
    def _make_gap(example: str, answer: str) -> str | None:
        """Replace the exact word/phrase in an example, preserving punctuation."""
        if not example or not answer:
            return None
        pattern = re.compile(re.escape(answer), flags=re.IGNORECASE)
        if not pattern.search(example):
            return None
        return pattern.sub("________", example, count=1)

    @classmethod
    def export_printable_test(
        cls,
        questions: list[PracticeQuestion],
        test_path: Path,
        key_path: Path,
        title: str,
    ) -> None:
        """Write a printable HTML test and a separate answer key."""
        test_path.write_text(cls._render_html(questions, title, include_answers=False), encoding="utf-8")
        key_path.write_text(cls._render_html(questions, f"{title} — Answer Key", include_answers=True), encoding="utf-8")

    @staticmethod
    def _render_html(
        questions: list[PracticeQuestion],
        title: str,
        *,
        include_answers: bool,
    ) -> str:
        blocks: list[str] = []
        for number, question in enumerate(questions, start=1):
            prompt = html.escape(question.prompt).replace("\n", "<br>")
            option_rows = "".join(
                f'<div class="option">{chr(65 + index)}. {html.escape(option)}</div>'
                for index, option in enumerate(question.options)
            )
            answer = (
                f'<div class="answer">Answer: {html.escape(question.correct_answer)}</div>'
                if include_answers
                else ""
            )
            blocks.append(
                f'<section class="question"><div class="number">{number}.</div>'
                f'<div class="body"><div class="prompt">{prompt}</div>{option_rows}{answer}</div></section>'
            )
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
@page {{ size: A4; margin: 18mm; }}
body {{ font-family: Arial, sans-serif; color:#1f2937; max-width:850px; margin:0 auto; line-height:1.45; }}
h1 {{ margin-bottom:6px; }} .meta {{ color:#6b7280; margin-bottom:24px; }}
.question {{ display:flex; gap:10px; margin:0 0 24px; break-inside:avoid; }}
.number {{ font-weight:bold; }} .body {{ flex:1; }} .prompt {{ font-weight:600; margin-bottom:10px; }}
.option {{ margin:5px 0; padding-left:8px; }} .answer {{ margin-top:10px; font-weight:bold; color:#166534; }}
</style></head><body><h1>{html.escape(title)}</h1>
<div class="meta">Name: ______________________________ &nbsp;&nbsp; Date: ______________</div>
{''.join(blocks)}</body></html>"""
