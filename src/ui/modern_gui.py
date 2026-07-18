"""Modern CustomTkinter GUI for the AI Anki Vocabulary Generator.

This module keeps the existing application logic and adds a modern interface with
both the single flashcard generator and Conversation Practice workflow.
"""

from __future__ import annotations

import csv
import html
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.ai.base import VocabularyAiClient
from src.anki.client import AnkiClient, DuplicateNoteError
from src.domain.languages import LANGUAGE_TAGS
from src.domain.models import ConversationFeedback, GrammarAnalysis, VocabularyCard
from src.practice import PracticeItem, PracticeQuestion, PracticeService
from src.speech import SpeechService
from src.speech.models import TtsResult
from src.speech.voice_presets import get_voice_by_label, get_voice_labels


EXPLANATION_LANGUAGES = ["Polish", "English", "Spanish", "German", "Italian", "No translation"]
IMPROVEMENT_LEVELS = ["Natural B1/B2", "Strong B2/C1", "Professional / Interview"]
TOPIC_PRESETS = [
    "",
    "character / personality traits",
    "work / professional life",
    "health / body / wellbeing",
    "travel / holidays",
    "daily life / routines",
    "relationships / social life",
    "AI / technology",
    "education / learning",
]

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "ai_anki_app.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)


class ModernVocabularyGui:
    """Modern desktop GUI for vocabulary cards and conversation practice."""

    def __init__(
        self,
        root: ctk.CTk,
        ai_clients: dict[str, VocabularyAiClient],
        anki_client: AnkiClient,
        default_target_language: str,
        speech_service: SpeechService | None = None,
    ) -> None:
        self._root = root
        self._ai_clients = ai_clients
        self._anki_client = anki_client
        self._speech_service = speech_service

        self._provider_var = ctk.StringVar(value=next(iter(ai_clients)))
        self._language_var = ctk.StringVar(value=default_target_language)
        self._explanation_language_var = ctk.StringVar(value="Polish")
        self._improvement_level_var = ctk.StringVar(value="Strong B2/C1")
        self._deck_var = ctk.StringVar(value=anki_client.deck_name)
        self._status_var = ctk.StringVar(value="Ready. Open Anki and choose a deck.")

        self._word_var = ctk.StringVar()
        self._generated_card: VocabularyCard | None = None
        self._generated_provider_name: str | None = None
        self._generated_audio: TtsResult | None = None

        tts_names = list(speech_service.providers) if speech_service else []
        self._tts_provider_var = ctk.StringVar(value=tts_names[0] if tts_names else "")
        self._tts_model_var = ctk.StringVar(value="")
        self._tts_voice_var = ctk.StringVar(value="")
        self._speech_notes: list[dict[str, object]] = []
        self._speech_note_vars: list[ctk.BooleanVar] = []
        self._speech_search_var = ctk.StringVar(value="")
        self._speech_progress_var = ctk.StringVar(value="Load cards with missing audio from the selected Anki deck.")
        self._speech_audio_status_by_note_id: dict[int, str] = {}
        self._speech_audio_error_by_note_id: dict[int, str] = {}
        self._speech_audio_path_by_note_id: dict[int, str] = {}

        self._grammar_sentence_var = ctk.StringVar()
        self._generated_grammar: GrammarAnalysis | None = None
        self._generated_grammar_provider_name: str | None = None

        self._topic_var = ctk.StringVar()
        self._conversation_question: str | None = None
        self._conversation_history: list[tuple[str, str]] = []
        self._latest_suggestions: list[str] = []
        self._suggestion_vars: list[ctk.BooleanVar] = []
        self._flashcard_queue: list[str] = []

        # Batch / Queue mode state.
        self._batch_items: list[dict[str, object]] = []
        self._batch_index = 0
        self._batch_generated_card: VocabularyCard | None = None
        self._batch_generated_provider_name: str | None = None
        self._batch_word_var = ctk.StringVar()
        self._batch_topic_var = ctk.StringVar(value="")
        self._batch_progress_var = ctk.StringVar(value="No list loaded.")
        self._batch_status_var = ctk.StringVar(value="Load a TXT/CSV file or paste a list.")
        self._batch_autosave_path: Path | None = None
        self._batch_auto_generate_running = False
        self._batch_auto_generate_paused = False
        self._batch_auto_generate_stop_requested = False
        self._batch_add_all_running = False
        self._batch_add_all_paused = False
        self._batch_add_all_stop_requested = False
        self._batch_add_all_indexes: list[int] = []
        self._batch_add_all_position = 0
        self._batch_add_all_duplicate_policy: bool | None = None
        self._batch_add_all_existing_notes: dict[str, int] = {}
        self._batch_add_all_counts = {"added": 0, "updated": 0, "duplicates": 0, "failed": 0}
        self._activity_var = ctk.StringVar(value="")

        # Existing cards workflow state. This is deliberately separate from
        # Batch autosave because old Anki notes may have been created before
        # the app had Batch/audio metadata.
        self._existing_cards: list[dict[str, object]] = []
        self._existing_card_vars: list[ctk.BooleanVar] = []
        self._existing_search_var = ctk.StringVar(value="")
        self._existing_tag_var = ctk.StringVar(value="")
        self._existing_flag_var = ctk.StringVar(value="Any flag")
        self._existing_leech_var = ctk.BooleanVar(value=False)
        self._existing_topic_var = ctk.StringVar(value="character / personality traits")
        self._existing_progress_var = ctk.StringVar(value="Load flagged/leech/tagged cards, then fix or tag selected notes.")

        # Existing-card audio generation state. The worker runs in a background
        # thread, so pause/stop flags use threading.Event.
        self._speech_audio_running = False
        self._speech_audio_pause_requested = threading.Event()
        self._speech_audio_stop_requested = threading.Event()
        self._speech_audio_autosave_path: Path | None = None

        # Practice and printable-test state.
        self._practice_scope_var = ctk.StringVar(value="All supported cards")
        self._practice_progress_var = ctk.StringVar(value="Load cards from Anki.")
        self._practice_feedback_var = ctk.StringVar(value="")
        self._practice_selected_answer = ctk.StringVar(value="")
        self._practice_items: list[PracticeItem] = []
        self._practice_item_vars: list[ctk.BooleanVar] = []
        self._practice_questions: list[PracticeQuestion] = []
        self._practice_index = 0
        self._practice_correct = 0
        self._practice_incorrect = 0
        self._practice_checked = False

        self._configure_window()
        self._build_widgets()
        self._load_decks()

    def _configure_window(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self._root.title("AI Anki Language Assistant")
        self._root.geometry("1120x780")
        self._root.minsize(980, 680)
        self._root.grid_columnconfigure(0, weight=1)
        self._root.grid_rowconfigure(0, weight=1)

    def _build_widgets(self) -> None:
        main = ctk.CTkFrame(self._root, corner_radius=0)
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        ctk.CTkLabel(
            header,
            text="AI Anki Language Assistant",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Practice conversations, review AI suggestions, and save selected expressions to Anki.",
            font=ctk.CTkFont(size=14),
            text_color=("gray35", "gray75"),
        ).pack(anchor="w", pady=(4, 0))

        self._build_top_settings(main)

        tabs = ctk.CTkTabview(main)
        tabs.grid(row=2, column=0, sticky="nsew", padx=24, pady=12)
        tabs.add("Single flashcard")
        tabs.add("Grammar")
        tabs.add("Conversation Practice")
        tabs.add("Batch / Queue")
        tabs.add("Practice & Print")
        tabs.add("Speech / Audio")
        tabs.add("Fix Cards")
        tabs.tab("Single flashcard").grid_columnconfigure(0, weight=1)
        tabs.tab("Single flashcard").grid_rowconfigure(0, weight=1)
        tabs.tab("Grammar").grid_columnconfigure(0, weight=1)
        tabs.tab("Grammar").grid_rowconfigure(0, weight=1)
        tabs.tab("Conversation Practice").grid_columnconfigure(0, weight=1)
        tabs.tab("Conversation Practice").grid_rowconfigure(0, weight=1)
        tabs.tab("Batch / Queue").grid_columnconfigure(0, weight=1)
        tabs.tab("Batch / Queue").grid_rowconfigure(0, weight=1)
        tabs.tab("Practice & Print").grid_columnconfigure(0, weight=1)
        tabs.tab("Practice & Print").grid_rowconfigure(0, weight=1)
        tabs.tab("Speech / Audio").grid_columnconfigure(0, weight=1)
        tabs.tab("Speech / Audio").grid_rowconfigure(0, weight=1)
        tabs.tab("Fix Cards").grid_columnconfigure(0, weight=1)
        tabs.tab("Fix Cards").grid_rowconfigure(0, weight=1)

        self._build_single_flashcard_tab(tabs.tab("Single flashcard"))
        self._build_grammar_tab(tabs.tab("Grammar"))
        self._build_conversation_tab(tabs.tab("Conversation Practice"))
        self._build_batch_tab(tabs.tab("Batch / Queue"))
        self._build_practice_tab(tabs.tab("Practice & Print"))
        self._build_speech_tab(tabs.tab("Speech / Audio"))
        self._build_existing_cards_tab(tabs.tab("Fix Cards"))

        footer = ctk.CTkFrame(main, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 16))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, textvariable=self._status_var, anchor="w").grid(
            row=0, column=0, sticky="ew"
        )
        ctk.CTkLabel(
            footer,
            textvariable=self._activity_var,
            anchor="e",
            text_color=("gray40", "gray70"),
        ).grid(row=0, column=1, sticky="e", padx=(16, 0))

    def _build_top_settings(self, parent: ctk.CTkFrame) -> None:
        settings = ctk.CTkFrame(parent, corner_radius=18)
        settings.grid(row=1, column=0, sticky="ew", padx=24, pady=(8, 4))
        settings.grid_columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(settings, text="AI provider").grid(row=0, column=0, padx=(16, 8), pady=14, sticky="w")
        self._provider_box = ctk.CTkComboBox(
            settings,
            variable=self._provider_var,
            values=list(self._ai_clients.keys()),
            state="readonly",
        )
        self._provider_box.grid(row=0, column=1, padx=(0, 16), pady=14, sticky="ew")

        ctk.CTkLabel(settings, text="Language").grid(row=0, column=2, padx=(0, 8), pady=14, sticky="w")
        self._language_box = ctk.CTkComboBox(
            settings,
            variable=self._language_var,
            values=list(LANGUAGE_TAGS.keys()),
            state="readonly",
            command=lambda _value: self._sync_tts_defaults(),
        )
        self._language_box.grid(row=0, column=3, padx=(0, 16), pady=14, sticky="ew")

        ctk.CTkLabel(settings, text="Anki deck").grid(row=0, column=4, padx=(0, 8), pady=14, sticky="w")
        self._deck_box = ctk.CTkComboBox(settings, variable=self._deck_var, values=[])
        self._deck_box.grid(row=0, column=5, padx=(0, 8), pady=14, sticky="ew")
        ctk.CTkButton(settings, text="Refresh", width=90, command=self._load_decks).grid(
            row=0, column=6, padx=(0, 16), pady=14
        )

    def _build_single_flashcard_tab(self, parent: ctk.CTkFrame) -> None:
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)
        layout.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(layout, corner_radius=18, width=340)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_propagate(False)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Create flashcard", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 8)
        )
        ctk.CTkLabel(left, text="Word or phrase").grid(row=1, column=0, sticky="w", padx=18, pady=(12, 4))
        entry = ctk.CTkEntry(left, textvariable=self._word_var, height=40)
        entry.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        entry.bind("<Return>", lambda _event: self._generate_single_card())
        ctk.CTkLabel(left, text="Explanation / translation language").grid(
            row=3, column=0, sticky="w", padx=18, pady=(4, 4)
        )
        ctk.CTkComboBox(
            left,
            variable=self._explanation_language_var,
            values=EXPLANATION_LANGUAGES,
            state="readonly",
        ).grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 12))
        ctk.CTkButton(left, text="Generate preview", height=42, command=self._generate_single_card).grid(
            row=5, column=0, sticky="ew", padx=18, pady=(6, 8)
        )
        speech_frame = ctk.CTkFrame(left, fg_color="transparent")
        speech_frame.grid(row=6, column=0, sticky="ew", padx=18, pady=(2, 8))
        speech_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            speech_frame, text="Generate example audio",
            command=self._generate_single_audio,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(
            speech_frame, text="Preview audio",
            command=self._preview_generated_audio,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        ctk.CTkButton(
            left,
            text="Add reviewed card to Anki",
            height=42,
            command=self._add_single_card_to_anki,
        ).grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 18))

        right = ctk.CTkFrame(layout, corner_radius=18)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(right, text="Flashcard preview", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 8)
        )
        self._preview = ctk.CTkTextbox(right, wrap="word", font=ctk.CTkFont(size=14))
        self._preview.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self._preview.insert("1.0", "Generate a card to preview it here.")
        self._preview.configure(state="disabled")

    def _build_grammar_tab(self, parent: ctk.CTkFrame) -> None:
        """Build the sentence-first grammar analysis tab."""
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)
        layout.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(layout, corner_radius=18, width=340)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_propagate(False)
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left,
            text="Analyze a sentence",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        ctk.CTkLabel(
            left,
            text="Enter a natural sentence in the selected language.",
            wraplength=300,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

        grammar_entry = ctk.CTkEntry(
            left,
            textvariable=self._grammar_sentence_var,
            height=42,
            placeholder_text="He might have gone out.",
        )
        grammar_entry.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        grammar_entry.bind("<Return>", lambda _event: self._analyze_grammar_sentence())

        ctk.CTkButton(
            left,
            text="Analyze grammar",
            height=42,
            command=self._analyze_grammar_sentence,
        ).grid(row=3, column=0, sticky="ew", padx=18, pady=(6, 8))

        ctk.CTkButton(
            left,
            text="Add grammar card to Anki",
            height=42,
            command=self._add_grammar_card_to_anki,
        ).grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 18))

        right = ctk.CTkFrame(layout, corner_radius=18)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            right,
            text="Grammar card preview",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        self._grammar_preview = ctk.CTkTextbox(
            right,
            wrap="word",
            font=ctk.CTkFont(size=14),
        )
        self._grammar_preview.grid(
            row=1, column=0, sticky="nsew", padx=18, pady=(0, 18)
        )
        self._grammar_preview.insert(
            "1.0",
            "Enter a sentence to see its meaning, structure, usage, context, "
            "contrasts, and common mistakes.",
        )
        self._grammar_preview.configure(state="disabled")

    def _build_conversation_tab(self, parent: ctk.CTkFrame) -> None:
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=3)
        layout.grid_columnconfigure(1, weight=2)
        layout.grid_rowconfigure(1, weight=1)

        topic = ctk.CTkFrame(layout, corner_radius=18)
        topic.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        topic.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(topic, text="Conversation topic", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=(18, 10), pady=14, sticky="w"
        )
        ctk.CTkEntry(
            topic,
            textvariable=self._topic_var,
            placeholder_text="e.g. daily life, travel, an interview, cooking...",
            height=38,
        ).grid(row=0, column=1, padx=(0, 10), pady=14, sticky="ew")
        ctk.CTkLabel(topic, text="Answer level").grid(
            row=0, column=2, padx=(4, 6), pady=14, sticky="e"
        )
        ctk.CTkComboBox(
            topic,
            variable=self._improvement_level_var,
            values=IMPROVEMENT_LEVELS,
            state="readonly",
            width=190,
        ).grid(row=0, column=3, padx=(0, 10), pady=14)
        ctk.CTkButton(topic, text="Start topic", width=120, command=self._start_conversation_topic).grid(
            row=0, column=4, padx=(0, 10), pady=14
        )
        ctk.CTkButton(topic, text="Reset", width=80, command=self._reset_conversation).grid(
            row=0, column=5, padx=(0, 18), pady=14
        )

        chat_panel = ctk.CTkFrame(layout, corner_radius=18)
        chat_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        chat_panel.grid_columnconfigure(0, weight=1)
        chat_panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(chat_panel, text="Conversation", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 8)
        )
        self._chat_text = ctk.CTkTextbox(chat_panel, wrap="word", font=ctk.CTkFont(size=14))
        self._chat_text.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))
        self._chat_text.insert("1.0", "Choose a topic and click Start topic. Then continue the conversation here.\n")
        self._chat_text.configure(state="disabled")

        input_row = ctk.CTkFrame(chat_panel, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        input_row.grid_columnconfigure(0, weight=1)
        self._message_input = ctk.CTkTextbox(input_row, height=78, wrap="word", font=ctk.CTkFont(size=14))
        self._message_input.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(input_row, text="Send", width=120, height=78, command=self._send_conversation_message).grid(
            row=0, column=1, sticky="e"
        )

        vocab_panel = ctk.CTkFrame(layout, corner_radius=18)
        vocab_panel.grid(row=1, column=1, sticky="nsew")
        vocab_panel.grid_columnconfigure(0, weight=1)
        vocab_panel.grid_rowconfigure(1, weight=1)
        vocab_panel.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(vocab_panel, text="Suggested expressions", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 8)
        )
        self._suggestions_frame = ctk.CTkScrollableFrame(vocab_panel, height=170, corner_radius=14)
        self._suggestions_frame.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self._render_suggestions([])

        buttons = ctk.CTkFrame(vocab_panel, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(buttons, text="Add selected", command=self._add_selected_suggestions_to_queue).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ctk.CTkButton(buttons, text="Add all", command=self._add_all_suggestions_to_queue).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

        ctk.CTkLabel(vocab_panel, text="Custom word or phrase").grid(row=3, column=0, sticky="w", padx=18, pady=(2, 4))
        custom = ctk.CTkFrame(vocab_panel, fg_color="transparent")
        custom.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 12))
        custom.grid_columnconfigure(0, weight=1)
        self._custom_phrase_var = ctk.StringVar()
        ctk.CTkEntry(custom, textvariable=self._custom_phrase_var, height=36).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ctk.CTkButton(custom, text="Add", width=70, command=self._add_custom_phrase_to_queue).grid(row=0, column=1)

        ctk.CTkLabel(vocab_panel, text="Flashcard queue", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=5, column=0, sticky="sw", padx=18, pady=(0, 6)
        )
        self._queue_text = ctk.CTkTextbox(vocab_panel, wrap="word", height=130, font=ctk.CTkFont(size=13))
        self._queue_text.grid(row=6, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self._refresh_queue_text()

        queue_buttons = ctk.CTkFrame(vocab_panel, fg_color="transparent")
        queue_buttons.grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 18))
        queue_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(queue_buttons, text="Clear queue", command=self._clear_queue).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ctk.CTkButton(
            queue_buttons,
            text="Generate queue + add to Anki",
            command=self._generate_queue_and_add_to_anki,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    def _build_batch_tab(self, parent: ctk.CTkFrame) -> None:
        """Build the batch vocabulary review workflow."""
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)
        layout.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(layout, corner_radius=18, width=360)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_propagate(False)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            left,
            text="Load vocabulary list",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        file_buttons = ctk.CTkFrame(left, fg_color="transparent")
        file_buttons.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        file_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(file_buttons, text="Load TXT", command=self._load_batch_txt).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(file_buttons, text="Load CSV", command=self._load_batch_csv).grid(
            row=0, column=1, sticky="ew", padx=(5, 0)
        )

        ctk.CTkLabel(left, text="Or paste one word / phrase per line").grid(
            row=2, column=0, sticky="w", padx=18, pady=(4, 4)
        )
        self._batch_paste_text = ctk.CTkTextbox(left, height=180, wrap="word")
        self._batch_paste_text.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 10))
        ctk.CTkButton(left, text="Load pasted list", command=self._load_pasted_batch).grid(
            row=4, column=0, sticky="ew", padx=18, pady=(0, 10)
        )

        ctk.CTkLabel(left, text="Batch topic / dział (optional)").grid(
            row=5, column=0, sticky="w", padx=18, pady=(4, 4)
        )
        self._batch_topic_box = ctk.CTkComboBox(
            left, variable=self._batch_topic_var, values=TOPIC_PRESETS
        )
        self._batch_topic_box.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 10))

        session_buttons = ctk.CTkFrame(left, fg_color="transparent")
        session_buttons.grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 8))
        session_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(session_buttons, text="Save session", command=self._save_batch_session).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(session_buttons, text="Resume session", command=self._resume_batch_session).grid(
            row=0, column=1, sticky="ew", padx=(5, 0)
        )
        ctk.CTkButton(left, text="Clear batch", command=self._clear_batch).grid(
            row=8, column=0, sticky="ew", padx=18, pady=(0, 18)
        )

        right = ctk.CTkFrame(layout, corner_radius=18)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Batch review",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, textvariable=self._batch_progress_var).grid(
            row=0, column=1, sticky="e"
        )

        ctk.CTkLabel(right, text="Current word / phrase").grid(
            row=1, column=0, sticky="w", padx=18, pady=(4, 4)
        )
        current_row = ctk.CTkFrame(right, fg_color="transparent")
        current_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        current_row.grid_columnconfigure(0, weight=1)
        self._batch_word_entry = ctk.CTkEntry(
            current_row, textvariable=self._batch_word_var, height=40
        )
        self._batch_word_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            current_row,
            text="Generate / Regenerate",
            width=170,
            command=lambda: self._generate_current_batch_card("generate_selected"),
        ).grid(row=0, column=1)

        ctk.CTkLabel(
            right,
            textvariable=self._batch_status_var,
            text_color=("gray35", "gray75"),
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 6))

        self._batch_preview = ctk.CTkTextbox(right, wrap="word", font=ctk.CTkFont(size=14))
        self._batch_preview.grid(row=4, column=0, sticky="nsew", padx=18, pady=(0, 12))
        self._batch_preview.insert("1.0", "Load a list to start reviewing cards.")
        self._batch_preview.bind("<Double-Button-1>", lambda _event: self._open_batch_card_editor())
        self._batch_preview.configure(state="disabled")

        buttons = ctk.CTkFrame(right, fg_color="transparent")
        buttons.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 18))
        buttons.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        ctk.CTkButton(buttons, text="Previous", command=self._batch_previous).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ctk.CTkButton(buttons, text="Skip", command=self._skip_current_batch_item).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ctk.CTkButton(buttons, text="Add to Anki", command=self._add_current_batch_card).grid(
            row=0, column=2, sticky="ew", padx=4
        )
        ctk.CTkButton(
            buttons,
            text="Regenerate",
            command=lambda: self._generate_current_batch_card("regenerate_selected"),
        ).grid(row=0, column=3, sticky="ew", padx=4)
        ctk.CTkButton(
            buttons,
            text="Edit card",
            command=self._open_batch_card_editor,
        ).grid(row=0, column=4, sticky="ew", padx=4)
        ctk.CTkButton(buttons, text="Next", command=self._batch_next).grid(
            row=0, column=5, sticky="ew", padx=(4, 0)
        )

        bulk_buttons = ctk.CTkFrame(right, fg_color="transparent")
        bulk_buttons.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 18))
        bulk_buttons.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        ctk.CTkButton(
            bulk_buttons,
            text="Auto-generate pending",
            command=self._auto_generate_pending_batch_cards,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(
            bulk_buttons,
            text="Retry failed/rate-limited",
            command=self._retry_failed_or_rate_limited_batch_cards,
        ).grid(row=0, column=1, sticky="ew", padx=5)
        ctk.CTkButton(
            bulk_buttons,
            text="Add all ready",
            command=self._start_add_all_ready_batch_cards,
        ).grid(row=0, column=2, sticky="ew", padx=(5, 0))
        ctk.CTkButton(
            bulk_buttons,
            text="Pause",
            command=self._pause_batch_process,
        ).grid(row=0, column=3, sticky="ew", padx=(8, 4))
        ctk.CTkButton(
            bulk_buttons,
            text="Stop",
            command=self._stop_batch_process,
        ).grid(row=0, column=4, sticky="ew", padx=(4, 0))

    def _build_practice_tab(self, parent: ctk.CTkFrame) -> None:
        """Build interactive practice and printable test controls."""
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)
        layout.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(layout, corner_radius=18, width=370)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_propagate(False)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(6, weight=1)

        ctk.CTkLabel(left, text="Choose cards", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 8)
        )
        ctk.CTkLabel(left, text="Scope").grid(row=1, column=0, sticky="w", padx=18, pady=(4, 4))
        ctk.CTkComboBox(
            left,
            variable=self._practice_scope_var,
            values=["All supported cards", "Due + overdue", "Overdue", "New"],
            state="readonly",
        ).grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))
        ctk.CTkButton(left, text="Load from selected Anki deck", command=self._load_practice_cards).grid(
            row=3, column=0, sticky="ew", padx=18, pady=(0, 8)
        )
        select_buttons = ctk.CTkFrame(left, fg_color="transparent")
        select_buttons.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 8))
        select_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(select_buttons, text="Select all", command=lambda: self._set_all_practice_items(True)).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(select_buttons, text="Select none", command=lambda: self._set_all_practice_items(False)).grid(
            row=0, column=1, sticky="ew", padx=(5, 0)
        )
        ctk.CTkLabel(left, text="Cards").grid(row=5, column=0, sticky="w", padx=18, pady=(4, 4))
        self._practice_selection_frame = ctk.CTkScrollableFrame(left, height=300)
        self._practice_selection_frame.grid(row=6, column=0, sticky="nsew", padx=18, pady=(0, 8))
        self._practice_selection_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(left, text="Start interactive practice", command=self._start_practice).grid(
            row=7, column=0, sticky="ew", padx=18, pady=(4, 6)
        )
        ctk.CTkButton(left, text="Create printable test + key", command=self._export_print_test).grid(
            row=8, column=0, sticky="ew", padx=18, pady=(0, 18)
        )

        right = ctk.CTkFrame(layout, corner_radius=18)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Practice", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(header, textvariable=self._practice_progress_var).grid(row=0, column=1, sticky="e")

        self._practice_prompt = ctk.CTkTextbox(right, height=145, wrap="word", font=ctk.CTkFont(size=16))
        self._practice_prompt.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        self._practice_prompt.insert("1.0", "Load and select cards, then start a practice session.")
        self._practice_prompt.configure(state="disabled")

        self._practice_options_frame = ctk.CTkFrame(right, fg_color="transparent")
        self._practice_options_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 8))
        self._practice_options_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, textvariable=self._practice_feedback_var, anchor="w").grid(
            row=3, column=0, sticky="ew", padx=18, pady=(2, 8)
        )
        actions = ctk.CTkFrame(right, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 18))
        actions.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(actions, text="Check", command=self._check_practice_answer).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(actions, text="Next", command=self._next_practice_question).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ctk.CTkButton(actions, text="End session", command=self._end_practice).grid(
            row=0, column=2, sticky="ew", padx=(5, 0)
        )

    @staticmethod
    def _normalise_batch_words(words: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in words:
            cleaned = value.strip()
            key = cleaned.casefold()
            if cleaned and key not in seen:
                result.append(cleaned)
                seen.add(key)
        return result

    def _set_batch_words(self, words: list[str]) -> None:
        clean_words = self._normalise_batch_words(words)
        if not clean_words:
            messagebox.showwarning("Empty list", "No words or phrases were found.")
            return
        topic = self._batch_topic_var.get().strip()
        self._batch_items = [
            {"word": word, "status": "pending", "topic": topic} for word in clean_words
        ]
        self._batch_index = 0
        self._batch_autosave_path = None
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        self._show_current_batch_item(generate=False)
        self._record_activity(f"Loaded {len(clean_words)} batch item(s) without generation")
        self._autosave_batch_session("list loaded")

    def _load_batch_txt(self) -> None:
        filename = filedialog.askopenfilename(
            title="Load vocabulary TXT",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            words = Path(filename).read_text(encoding="utf-8-sig").splitlines()
        except Exception as exc:
            messagebox.showerror("File error", str(exc))
            return
        self._set_batch_words(words)

    def _load_batch_csv(self) -> None:
        filename = filedialog.askopenfilename(
            title="Load vocabulary CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            with open(filename, "r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.reader(handle))
        except Exception as exc:
            messagebox.showerror("File error", str(exc))
            return
        words: list[str] = []
        for index, row in enumerate(rows):
            if not row:
                continue
            value = row[0].strip()
            if index == 0 and value.casefold() in {"word", "word_or_phrase", "phrase", "vocabulary"}:
                continue
            words.append(value)
        self._set_batch_words(words)

    def _load_pasted_batch(self) -> None:
        words = self._batch_paste_text.get("1.0", "end").splitlines()
        self._set_batch_words(words)

    def _show_current_batch_item(self, generate: bool = False) -> None:
        if not self._batch_items:
            self._batch_word_var.set("")
            self._batch_progress_var.set("No list loaded.")
            self._batch_status_var.set("Load a TXT/CSV file or paste a list.")
            return
        self._batch_index = max(0, min(self._batch_index, len(self._batch_items) - 1))
        item = self._batch_items[self._batch_index]
        if item.get("topic") and not self._batch_topic_var.get().strip():
            self._batch_topic_var.set(str(item.get("topic", "")))
        self._batch_word_var.set(str(item["word"]))
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        stored_card = self._card_from_batch_payload(item.get("card"))
        if stored_card is not None:
            self._batch_generated_card = stored_card
            self._batch_generated_provider_name = str(item.get("provider_name") or self._provider_var.get())
        self._update_batch_progress()
        if stored_card is not None:
            self._set_batch_preview(self._format_batch_card_preview(item, stored_card))
        else:
            self._set_batch_status_card(
                title="BATCH ITEM",
                word=str(item.get("word", "")),
                status=str(item.get("status", "pending")),
                detail=self._friendly_batch_item_detail(item),
            )
        # Important: showing/selecting an item must never call an AI provider.
        # Generation is allowed only through explicit buttons such as
        # Generate selected, Auto-generate pending, or Retry failed/rate-limited.

    def _format_batch_card_preview(self, item: dict[str, object], card: VocabularyCard) -> str:
        preview = self._format_card_preview(card, audio_status=item.get("audio_status"))
        topic = str(item.get("topic") or self._batch_topic_var.get()).strip()
        if topic:
            preview += f"\n\nTOPIC / DZIAŁ\n{topic}"
        topic_status = str(item.get("topic_status", "")).strip()
        if topic_status:
            preview += f"\nTopic status: {topic_status}"
        warnings = item.get("quality_warnings")
        if isinstance(warnings, list) and warnings:
            preview += "\n\nQUALITY WARNINGS\n" + "\n".join(f"  • {warning}" for warning in warnings)
        return preview

    def _open_batch_card_editor(self) -> None:
        """Open a small editor for the currently generated Batch card."""
        if not self._batch_items:
            return
        card = self._batch_generated_card or self._card_from_batch_payload(
            self._batch_items[self._batch_index].get("card")
        )
        if card is None:
            messagebox.showinfo(
                "No generated card",
                "Not generated yet. Click Generate selected or Auto-generate pending.",
            )
            return

        editor = tk.Toplevel(self._root)
        editor.title(f"Edit card: {card.word_or_phrase}")
        editor.geometry("720x720")
        editor.transient(self._root)
        editor.grid_columnconfigure(1, weight=1)

        entries: dict[str, tk.Widget] = {}

        def add_entry(row: int, label: str, key: str, value: str) -> int:
            tk.Label(editor, text=label, anchor="w").grid(row=row, column=0, sticky="nw", padx=10, pady=6)
            widget = tk.Entry(editor)
            widget.insert(0, value or "")
            widget.grid(row=row, column=1, sticky="ew", padx=10, pady=6)
            entries[key] = widget
            return row + 1

        def add_text(row: int, label: str, key: str, value: str, height: int = 3) -> int:
            tk.Label(editor, text=label, anchor="w").grid(row=row, column=0, sticky="nw", padx=10, pady=6)
            widget = tk.Text(editor, height=height, wrap="word")
            widget.insert("1.0", value or "")
            widget.grid(row=row, column=1, sticky="nsew", padx=10, pady=6)
            entries[key] = widget
            return row + 1

        row = 0
        row = add_entry(row, "Language", "target_language", card.target_language)
        row = add_entry(row, "Part of speech", "part_of_speech", card.part_of_speech)
        row = add_entry(row, "Word / phrase", "word_or_phrase", card.word_or_phrase)
        row = add_text(row, "Definition", "definition", card.definition, height=3)
        row = add_text(row, "Translation / explanation", "translation_pl", card.translation_pl, height=3)
        row = add_text(row, "Example", "example", card.example, height=3)
        row = add_text(row, "Example translation", "example_pl", card.example_pl, height=3)
        row = add_text(row, "Collocations\n(one per line)", "collocations", "\n".join(card.collocations), height=5)
        row = add_text(row, "Synonyms\n(one per line)", "synonyms", "\n".join(card.synonyms), height=4)
        row = add_text(row, "Grammar note", "grammar_note", card.grammar_note, height=4)

        def value(key: str) -> str:
            widget = entries[key]
            if isinstance(widget, tk.Text):
                return widget.get("1.0", "end").strip()
            return str(widget.get()).strip()  # type: ignore[attr-defined]

        def save() -> None:
            updated_card = card.model_copy(
                update={
                    "target_language": value("target_language") or card.target_language,
                    "part_of_speech": value("part_of_speech"),
                    "word_or_phrase": value("word_or_phrase") or card.word_or_phrase,
                    "definition": value("definition"),
                    "translation_pl": value("translation_pl"),
                    "example": value("example"),
                    "example_pl": value("example_pl"),
                    "collocations": [line.strip() for line in value("collocations").splitlines() if line.strip()],
                    "synonyms": [line.strip() for line in value("synonyms").splitlines() if line.strip()],
                    "grammar_note": value("grammar_note"),
                }
            )
            item = self._batch_items[self._batch_index]
            item["card"] = self._card_to_batch_payload(updated_card)
            item["word"] = updated_card.word_or_phrase
            item["status"] = "ready"
            self._batch_generated_card = updated_card
            self._batch_generated_provider_name = str(item.get("provider_name") or self._provider_var.get())
            self._batch_word_var.set(updated_card.word_or_phrase)
            warnings = self._quality_warnings_for_card(updated_card)
            if warnings:
                item["quality_warnings"] = warnings
            else:
                item.pop("quality_warnings", None)
            self._set_batch_preview(self._format_batch_card_preview(item, updated_card))
            self._autosave_batch_session(f"edited: {updated_card.word_or_phrase}")
            self._batch_status_var.set(f"Edited and autosaved: {updated_card.word_or_phrase}")
            self._status_var.set(self._batch_status_var.get())
            self._record_activity(f"Edited: {updated_card.word_or_phrase}")
            editor.destroy()

        button_row = tk.Frame(editor)
        button_row.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=12)
        tk.Button(button_row, text="Save changes", command=save).pack(side="left")
        tk.Button(button_row, text="Cancel", command=editor.destroy).pack(side="left", padx=(8, 0))

    def _update_batch_progress(self) -> None:
        total = len(self._batch_items)
        counts = {
            name: 0
            for name in (
                "added",
                "skipped",
                "invalid",
                "pending",
                "ready",
                "error",
                "rate_limited",
                "provider_failed",
                "duplicate",
            )
        }
        for item in self._batch_items:
            status = str(item.get("status", "pending"))
            counts[status] = counts.get(status, 0) + 1
        current = self._batch_index + 1 if total else 0
        remaining = counts.get("pending", 0) + counts.get("ready", 0) + counts.get("rate_limited", 0)
        self._batch_progress_var.set(
            f"{current}/{total} · Added {counts.get('added', 0)} · "
            f"Skipped {counts.get('skipped', 0)} · Invalid {counts.get('invalid', 0)} · "
            f"Failed {counts.get('error', 0) + counts.get('provider_failed', 0)} · "
            f"Rate limited {counts.get('rate_limited', 0)} · Remaining {remaining}"
        )

    def _set_batch_preview(self, content: str) -> None:
        self._batch_preview.configure(state="normal")
        self._batch_preview.delete("1.0", "end")
        self._batch_preview.insert("1.0", content)
        self._batch_preview.configure(state="disabled")

    def _set_batch_status_card(
        self,
        title: str,
        word: str,
        status: str,
        detail: str = "",
        actions: str = "",
    ) -> None:
        """Show a stable card-like Batch preview for non-ready states."""
        blocks = [
            "╭────────────────────────────────────────╮",
            f"  {title}",
            "╰────────────────────────────────────────╯",
            "",
            f"WORD / PHRASE",
            f"{word or '—'}",
            "",
            "STATUS",
            status,
        ]
        if detail:
            blocks.extend(["", "DETAILS", detail])
        if actions:
            blocks.extend(["", "SAFE NEXT ACTIONS", actions])
        self._set_batch_preview("\n".join(blocks))

    @staticmethod
    def _http_status_from_detail(detail: str) -> int | None:
        match = re.search(r"\b(400|401|402|403|404|422|429|5\d\d)\b", detail)
        return int(match.group(1)) if match else None

    @staticmethod
    def _is_provider_rate_limit_detail(detail: str) -> bool:
        lowered = detail.lower()
        return any(
            token in lowered
            for token in (
                "429",
                "too many requests",
                "resource_exhausted",
                "quota exceeded",
                "rate limit",
            )
        )

    @staticmethod
    def _is_timeout_detail(detail: str) -> bool:
        lowered = detail.lower()
        return "timeout" in lowered or "timed out" in lowered or "read timed out" in lowered

    @staticmethod
    def _is_fatal_long_generation_detail(detail: str) -> bool:
        status = ModernVocabularyGui._http_status_from_detail(detail)
        return status in {401, 402, 403, 429} or (status is not None and 500 <= status <= 599) or ModernVocabularyGui._is_timeout_detail(detail)

    @staticmethod
    def _friendly_generation_error_detail(
        detail: str,
        provider_name: str = "Provider",
        model_name: str = "",
    ) -> str:
        """Convert provider raw errors into concise UI text.

        The raw exception remains in logs/autosave; this summary is for the
        Batch preview/status area so users are not shown huge JSON payloads.
        """
        lowered = detail.lower()
        provider = provider_name or "Provider"
        model = model_name or ""
        model_match = re.search(r"model[:=]\s*['\"]?([\w.\-]+)", detail)
        if model_match:
            model = model_match.group(1)
        elif "gemini-2.5-flash" in lowered:
            model = "gemini-2.5-flash"
        if not model:
            model = provider

        retry_match = re.search(r"retry(?:delay| in)?[^0-9]*(\d+(?:\.\d+)?)\s*s", detail, re.IGNORECASE)
        retry_hint = f" Retry suggested in about {retry_match.group(1)} seconds." if retry_match else ""

        if "resource_exhausted" in lowered or "quota exceeded" in lowered or "429" in lowered:
            if provider.lower() == "gemini" or "gemini" in lowered:
                return (
                    f"Gemini quota reached for {model}. "
                    "The current item was saved as rate_limited. "
                    "Switch provider and retry failed/rate-limited items, or resume later."
                    f"{retry_hint}"
                )
            return (
                f"{provider} quota/rate limit reached for {model}. "
                "The current item was saved as rate_limited. "
                "Switch provider and retry failed/rate-limited items, or resume later."
                f"{retry_hint}"
            )
        status = ModernVocabularyGui._http_status_from_detail(detail)
        if status == 400:
            return f"{provider} rejected this request as invalid. This item was saved; edit it or retry manually."
        if status == 401 or "unauthorized" in lowered:
            return f"{provider} API key was rejected. Check the API key or switch provider."
        if status == 402 or "payment required" in lowered:
            return f"{provider} billing/credits problem. Switch provider or check the provider dashboard."
        if status == 403 or "forbidden" in lowered:
            return f"{provider} rejected access to this model or account. Switch provider/model."
        if status == 404:
            return f"{provider} model or endpoint was not found. Check the configured model or switch provider."
        if status == 422:
            return f"{provider} could not process this item. It was saved for manual review; no automatic retry was started."
        if status is not None and 500 <= status <= 599:
            return f"{provider} server error. Progress was saved; retry later or switch provider."
        if ModernVocabularyGui._is_timeout_detail(detail):
            return f"{provider} timed out. Progress was saved; retry later or switch provider."
        return "Generation failed. Raw provider details were saved in logs/autosave."

    def _friendly_batch_item_detail(self, item: dict[str, object]) -> str:
        status = str(item.get("status", "pending"))
        raw_error = str(item.get("error", ""))
        if raw_error:
            return self._friendly_generation_error_detail(
                raw_error,
                str(item.get("provider_name") or self._provider_var.get()),
                self._current_ai_model_name(),
            )
        if status == "pending":
            return "Not generated yet. Click Generate selected or Auto-generate pending."
        if status == "ready":
            return "Generated and ready for review."
        if status == "rate_limited":
            return "Provider rate limit. Switch provider and retry this item, or resume later."
        if status == "provider_failed":
            return "Provider stopped the process. Switch provider and retry failed/rate-limited items."
        return ""

    def _stop_batch_on_provider_error(
        self,
        word: str,
        detail: str,
        provider_name: str,
        model_name: str = "",
    ) -> None:
        """Stop Auto Batch and keep one stable UI state after fatal provider errors."""
        self._batch_auto_generate_running = False
        self._batch_auto_generate_paused = False
        self._batch_auto_generate_stop_requested = True
        self._autosave_batch_session(f"rate limit: {word}")
        autosave = str(self._batch_autosave_path) if self._batch_autosave_path else "not available"
        friendly_detail = self._friendly_generation_error_detail(detail, provider_name, model_name)
        message = (
            "Auto Batch stopped: provider error. "
            "Progress saved. Switch provider and retry failed/rate-limited items, or resume later."
        )
        self._batch_status_var.set(f"{message} Autosave: {autosave}")
        self._status_var.set(message)
        status_name = "rate_limited" if self._is_provider_rate_limit_detail(detail) else "provider_failed"
        self._set_batch_status_card(
            title="AUTO BATCH STOPPED",
            word=word,
            status=status_name,
            detail=f"{friendly_detail}\n\nAutosave: {autosave}",
            actions=(
                "- Switch provider\n"
                "- Retry failed/rate-limited\n"
                "- Add all ready cards now\n"
                "- Resume later from autosave"
            ),
        )
        self._record_activity("Auto Batch stopped: provider error")
        LOGGER.warning("Auto Batch stopped because of provider error for word=%s detail=%s", word, detail)

    def _stop_batch_on_rate_limit(self, word: str, detail: str) -> None:
        """Backward-compatible wrapper for older call sites."""
        self._stop_batch_on_provider_error(word, detail, self._provider_var.get(), self._current_ai_model_name())

    def _generate_current_batch_card(self, generation_trigger: str = "generate_selected") -> None:
        if not self._batch_items:
            messagebox.showerror("No list", "Load a vocabulary list first.")
            return
        word = self._batch_word_var.get().strip()
        if not word:
            messagebox.showerror("Missing word", "Enter a word or phrase.")
            return
        item = self._batch_items[self._batch_index]
        topic_context = self._current_batch_topic()
        item["word"] = word
        item["topic"] = topic_context
        provider_name = self._provider_var.get()
        model_name = self._current_ai_model_name()
        LOGGER.info(
            "Batch generation start: trigger=%s index=%s word=%s provider=%s",
            generation_trigger,
            self._batch_index,
            word,
            provider_name,
        )
        self._batch_status_var.set(
            f"Generating {self._batch_index + 1}/{len(self._batch_items)}: {word}..."
        )
        self._status_var.set(self._batch_status_var.get())
        self._root.update_idletasks()
        try:
            card = self._current_ai_client().generate_card(
                word,
                self._language_var.get(),
                self._explanation_language_var.get(),
                topic_context,
            )
        except Exception as exc:
            detail = str(exc)
            item["status"] = "error"
            item["error"] = detail
            self._batch_generated_card = None
            if self._is_provider_rate_limit_detail(detail):
                item["status"] = "rate_limited"
                message = f"Rate limit while generating: {word}. Session autosaved."
                self._batch_status_var.set(message)
                self._update_batch_progress()
                self._stop_batch_on_provider_error(word, detail, provider_name, model_name)
            elif self._is_fatal_long_generation_detail(detail):
                item["status"] = "provider_failed"
                message = f"Provider stopped while generating: {word}. Session autosaved."
                self._batch_status_var.set(message)
                self._update_batch_progress()
                self._stop_batch_on_provider_error(word, detail, provider_name, model_name)
            else:
                message = f"Generation error: {word}. Raw details saved in logs/autosave."
                self._batch_status_var.set(message)
                self._set_batch_status_card(
                    "GENERATION ERROR",
                    word,
                    "error",
                    self._friendly_generation_error_detail(detail, provider_name, model_name),
                )
                self._update_batch_progress()
                self._autosave_batch_session(f"generation error: {word}")
            LOGGER.exception("Batch generation failed for word=%s", word)
            return
        if not card.is_valid:
            item["status"] = "invalid"
            detail = card.validation_error or "Invalid word or phrase."
            if card.suggested_correction:
                detail += f" Suggested correction: {card.suggested_correction}"
            item["error"] = detail
            self._batch_generated_card = None
            self._batch_status_var.set(f"Invalid: {word}")
            self._set_batch_status_card("VALIDATION ERROR", word, "invalid", detail)
            self._update_batch_progress()
            self._autosave_batch_session(f"invalid item: {word}")
            return
        item["status"] = "ready"
        item["card"] = self._card_to_batch_payload(card)
        item["provider_name"] = provider_name
        item.pop("error", None)
        quality_warnings = self._quality_warnings_for_card(card)
        topic_warnings = self._topic_warnings_for_card(card, topic_context)
        quality_warnings.extend(topic_warnings)
        item["topic_status"] = "topic_warning" if topic_warnings else ("topic_ok" if topic_context else "")
        if quality_warnings:
            item["quality_warnings"] = quality_warnings
        else:
            item.pop("quality_warnings", None)
        self._batch_generated_card = card
        self._batch_generated_provider_name = provider_name
        self._set_batch_preview(self._format_batch_card_preview(item, card))
        if quality_warnings:
            self._batch_status_var.set(f"Ready with quality warning(s): {word}")
        else:
            self._batch_status_var.set(f"Ready to review: {word}")
        self._status_var.set(self._batch_status_var.get())
        self._update_batch_progress()
        self._autosave_batch_session(f"generated: {word}")

    def _add_current_batch_card(self) -> None:
        if self._batch_generated_card is None:
            messagebox.showerror("No card", "Generate and review the current card first.")
            return
        if not self._confirm_quality_warnings(self._batch_generated_card):
            self._batch_status_var.set("Add to Anki cancelled because of quality warnings.")
            return
        provider_name = self._batch_generated_provider_name or self._provider_var.get()
        try:
            deck = self._set_selected_deck()
            self._anki_client.add_card(
                self._batch_generated_card,
                provider_name,
                extra_tags=self._topic_tags_for_batch_item(self._batch_items[self._batch_index]),
            )
        except DuplicateNoteError:
            replace = messagebox.askyesno(
                "Card already exists",
                f"A card for '{self._batch_generated_card.word_or_phrase}' already exists.\n\n"
                "Replace it with this reviewed version?",
            )
            if not replace:
                self._batch_status_var.set("Existing card was not changed.")
                return
            try:
                self._anki_client.update_card(
                    self._batch_generated_card,
                    provider_name,
                    extra_tags=self._topic_tags_for_batch_item(self._batch_items[self._batch_index]),
                )
            except Exception as update_exc:
                self._batch_status_var.set(f"Could not update card: {update_exc}")
                messagebox.showerror("Anki update error", str(update_exc))
                return
            deck = self._anki_client.deck_name
        except Exception as exc:
            self._batch_status_var.set(f"Could not add card: {exc}")
            messagebox.showerror("Anki error", str(exc))
            return
        word = self._batch_generated_card.word_or_phrase
        self._batch_items[self._batch_index]["status"] = "added"
        self._autosave_batch_session(f"added: {word}")
        self._batch_status_var.set(f"✓ Added to {deck}: {word}")
        self._status_var.set(self._batch_status_var.get())
        self._record_activity(f"✓ {word} added")
        self._update_batch_progress()
        self._root.after(350, self._advance_batch_after_action)

    def _skip_current_batch_item(self) -> None:
        if not self._batch_items:
            return
        word = str(self._batch_items[self._batch_index]["word"])
        self._batch_items[self._batch_index]["status"] = "skipped"
        self._autosave_batch_session(f"skipped: {word}")
        self._batch_status_var.set(f"Skipped: {word}")
        self._status_var.set(self._batch_status_var.get())
        self._record_activity(f"↷ {word} skipped")
        self._update_batch_progress()
        self._root.after(250, self._advance_batch_after_action)

    def _advance_batch_after_action(self) -> None:
        if self._batch_index < len(self._batch_items) - 1:
            self._batch_index += 1
            self._show_current_batch_item(generate=False)
        else:
            self._batch_status_var.set("Batch finished. Review progress or save the session.")
            self._status_var.set(self._batch_status_var.get())

    def _batch_previous(self) -> None:
        if self._batch_items and self._batch_index > 0:
            self._batch_index -= 1
            self._show_current_batch_item(generate=False)

    def _batch_next(self) -> None:
        if self._batch_items and self._batch_index < len(self._batch_items) - 1:
            self._batch_index += 1
            self._show_current_batch_item(generate=False)

    def _clear_batch(self) -> None:
        self._batch_items.clear()
        self._batch_index = 0
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        self._batch_autosave_path = None
        self._batch_auto_generate_running = False
        self._batch_auto_generate_paused = False
        self._batch_auto_generate_stop_requested = False
        self._batch_add_all_running = False
        self._batch_add_all_paused = False
        self._batch_add_all_stop_requested = False
        self._show_current_batch_item()
        self._set_batch_preview("Load a list to start reviewing cards.")
        self._record_activity("Batch cleared")


    def _batch_session_data(self) -> dict[str, object]:
        """Return the current Batch session payload."""
        return {
            "items": self._batch_items,
            "index": self._batch_index,
            "provider": self._provider_var.get(),
            "target_language": self._language_var.get(),
            "explanation_language": self._explanation_language_var.get(),
            "batch_topic": self._batch_topic_var.get(),
            "deck": self._deck_var.get(),
            "autosaved_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _ensure_batch_autosave_path(self) -> Path:
        """Create and return the autosave path for the current Batch session."""
        if self._batch_autosave_path is None:
            autosave_dir = Path("batch_autosaves")
            autosave_dir.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._batch_autosave_path = autosave_dir / f"batch_autosave_{stamp}.json"
        return self._batch_autosave_path

    def _autosave_batch_session(self, reason: str) -> None:
        """Save the current Batch session automatically."""
        if not self._batch_items:
            return
        path = self._ensure_batch_autosave_path()
        try:
            path.write_text(
                json.dumps(self._batch_session_data(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            LOGGER.info("Batch autosaved: reason=%s path=%s", reason, path)
        except Exception as exc:
            LOGGER.exception("Batch autosave failed: reason=%s", reason)
            self._record_activity(f"Autosave failed: {exc}")
            return

    def _card_from_batch_payload(self, payload: object) -> VocabularyCard | None:
        """Rebuild a vocabulary card stored inside a Batch item."""
        if not isinstance(payload, dict):
            return None
        try:
            return VocabularyCard(**payload)
        except Exception:
            return None

    @staticmethod
    def _card_to_batch_payload(card: VocabularyCard) -> dict[str, object]:
        """Serialize a generated card into the Batch session."""
        return {
            "word_or_phrase": card.word_or_phrase,
            "target_language": card.target_language,
            "part_of_speech": card.part_of_speech,
            "translation_pl": card.translation_pl,
            "definition": card.definition,
            "example": card.example,
            "example_pl": card.example_pl,
            "synonyms": list(card.synonyms),
            "collocations": list(card.collocations),
            "grammar_note": card.grammar_note,
            "is_valid": card.is_valid,
            "validation_error": card.validation_error,
            "suggested_correction": card.suggested_correction,
            "explanation_language": card.explanation_language,
            "audio": card.audio,
        }

    @staticmethod
    def _normalise_anki_value(value: str) -> str:
        """Normalize a value for exact duplicate checks."""
        import html
        plain = re.sub(r"<[^>]+>", "", html.unescape(value or ""))
        return " ".join(plain.split()).casefold()

    @staticmethod
    def _slugify_topic(value: str) -> str:
        value = value.strip().casefold()
        replacements = {
            "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
            "ó": "o", "ś": "s", "ż": "z", "ź": "z",
        }
        for source, target in replacements.items():
            value = value.replace(source, target)
        value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
        return value[:48] or "general"

    def _topic_tag_from_value(self, value: str) -> str:
        return f"topic_{self._slugify_topic(value)}"

    def _current_batch_topic(self) -> str:
        return self._batch_topic_var.get().strip()

    def _topic_tags_for_batch_item(self, item: dict[str, object] | None = None) -> list[str]:
        topic = str((item or {}).get("topic") or self._current_batch_topic()).strip()
        return [self._topic_tag_from_value(topic)] if topic else []

    def _topic_warnings_for_card(self, card: VocabularyCard, topic: str) -> list[str]:
        topic_l = topic.casefold()
        example_l = card.example.casefold()
        warnings: list[str] = []
        if not topic_l:
            return warnings
        if any(token in topic_l for token in ("character", "personality", "charakter")):
            person_markers = [
                " he ", " she ", " they ", " person ", " people ", " friend ",
                " colleague ", " mother ", " father ", " sister ", " brother ",
                " teacher ", " manager ", "someone", " her ", " his ", " their ",
            ]
            padded = f" {example_l} "
            if not any(marker in padded for marker in person_markers):
                warnings.append(
                    "Topic warning: example may not clearly describe a person's character/personality."
                )
        return warnings

    @staticmethod
    def _contains_cyrillic(value: str) -> bool:
        return bool(re.search(r"[\u0400-\u04FF]", value or ""))

    @staticmethod
    def _looks_like_mixed_polish_translation(value: str) -> bool:
        lowered = (value or "").casefold()
        suspicious_tokens = [" el ", " la ", " los ", " las ", " una ", " un ", " de ", " que "]
        return any(token in f" {lowered} " for token in suspicious_tokens) and any(
            char in lowered for char in "ąćęłńóśźż"
        )

    def _quality_warnings_for_card(self, card: VocabularyCard) -> list[str]:
        """Return lightweight warnings before sending a generated card to Anki."""
        warnings: list[str] = []
        target_language = self._language_var.get().strip()
        if card.target_language.strip().casefold() != target_language.casefold():
            warnings.append(
                f"Target language mismatch: expected {target_language}, got {card.target_language}."
            )

        polish_fields = {
            "translation/explanation": card.translation_pl,
            "example translation": card.example_pl,
            "grammar note": card.grammar_note,
        }
        if card.explanation_language.strip().casefold() == "polish":
            for field_name, value in polish_fields.items():
                if self._contains_cyrillic(value):
                    warnings.append(f"Cyrillic characters detected in Polish {field_name}.")
                if self._looks_like_mixed_polish_translation(value):
                    warnings.append(f"Possible mixed-language text in Polish {field_name}.")

        checks = {
            "word/phrase": card.word_or_phrase,
            "translation/explanation": card.translation_pl,
            "example translation": card.example_pl,
            "grammar note": card.grammar_note,
            "definition": card.definition,
            "example": card.example,
        }
        for field_name, value in checks.items():
            lowered = (value or "").casefold()
            if "nostalgja" in lowered:
                warnings.append(f"Possible typo in {field_name}: 'nostalgja' → 'nostalgia'.")
            if "głęboka smutek" in lowered:
                warnings.append(f"Possible grammar error in {field_name}: 'głęboka smutek' → 'głęboki smutek'.")
            if "область живота" in lowered:
                warnings.append(f"Cyrillic phrase detected in {field_name}: 'область живота'.")

        return warnings

    def _quality_warnings_for_batch_indexes(self, indexes: list[int]) -> list[str]:
        warnings: list[str] = []
        for index in indexes:
            card = self._card_from_batch_payload(self._batch_items[index].get("card"))
            if card is None:
                continue
            card_warnings = self._quality_warnings_for_card(card)
            if card_warnings:
                warnings.append(f"{index + 1}. {card.word_or_phrase}: " + "; ".join(card_warnings[:3]))
        return warnings

    def _confirm_quality_warnings(self, card: VocabularyCard) -> bool:
        warnings = self._quality_warnings_for_card(card)
        if not warnings:
            return True
        return messagebox.askyesno(
            "Quality warnings",
            "This card has quality warnings. Add it to Anki anyway?\n\n"
            + "\n".join(f"• {warning}" for warning in warnings),
        )

    def _auto_generate_pending_batch_cards(self) -> None:
        """Generate pending Batch cards one by one using Tk after()."""
        if self._batch_auto_generate_running:
            self._batch_status_var.set("Auto-generation is already running.")
            return
        if not self._batch_items:
            messagebox.showerror("No list", "Load a vocabulary list first.")
            return

        resume = self._batch_auto_generate_paused
        self._batch_auto_generate_running = True
        self._batch_auto_generate_paused = False
        self._batch_auto_generate_stop_requested = False
        self._record_activity("Auto-generation resumed" if resume else "Auto-generation started")
        self._autosave_batch_session("before auto-generation resume" if resume else "before auto-generation")
        self._root.after(50, self._auto_generate_next_pending_batch_card)

    def _auto_generate_next_pending_batch_card(self) -> None:
        """Generate the next pending Batch card and schedule the following one."""
        if self._batch_auto_generate_stop_requested:
            self._batch_auto_generate_running = False
            self._batch_auto_generate_stop_requested = False
            self._autosave_batch_session("auto-generation stopped")
            message = f"Auto-generation stopped. Progress saved: {self._batch_autosave_path}"
            self._batch_status_var.set(message)
            self._status_var.set(message)
            self._record_activity(message)
            return
        if self._batch_auto_generate_paused or not self._batch_auto_generate_running:
            return
        next_index = None
        for index, item in enumerate(self._batch_items):
            if str(item.get("status", "pending")) == "pending":
                if not item.get("card"):
                    next_index = index
                    break

        if next_index is None:
            self._batch_auto_generate_running = False
            self._update_batch_progress()
            self._autosave_batch_session("auto-generation finished")
            self._batch_status_var.set(f"Auto-generation finished. Autosave: {self._batch_autosave_path}")
            self._status_var.set(self._batch_status_var.get())
            self._record_activity("Auto-generation finished")
            return

        self._batch_index = next_index
        word = str(self._batch_items[next_index].get("word", "")).strip()
        self._batch_word_var.set(word)
        self._batch_status_var.set(f"Auto-generating {next_index + 1}/{len(self._batch_items)}: {word}")
        self._status_var.set(self._batch_status_var.get())
        self._show_current_batch_item(generate=False)
        self._root.update_idletasks()

        try:
            self._generate_current_batch_card("auto_generate_pending")
        except Exception as exc:
            LOGGER.exception("Auto-generation failed for %s", word)
            item = self._batch_items[next_index]
            item["status"] = "error"
            item["error"] = str(exc)
            self._autosave_batch_session(f"auto-generation exception: {word}")

            if self._is_provider_rate_limit_detail(str(exc)):
                item["status"] = "rate_limited"
                self._stop_batch_on_rate_limit(word, str(exc))
                return

        current_item = self._batch_items[next_index]
        current_status = str(current_item.get("status"))
        if current_status == "rate_limited":
            self._stop_batch_on_provider_error(
                word,
                str(current_item.get("error", "Provider rate limit.")),
                self._provider_var.get(),
                self._current_ai_model_name(),
            )
            return
        if current_status == "provider_failed":
            self._stop_batch_on_provider_error(
                word,
                str(current_item.get("error", "Provider error.")),
                self._provider_var.get(),
                self._current_ai_model_name(),
            )
            return
        if current_status == "error":
            # A failed item must not be retried immediately. It remains for manual review.
            LOGGER.info("Skipping failed batch item after one attempt: %s", word)

        self._root.after(1600, self._auto_generate_next_pending_batch_card)

    def _pause_batch_process(self) -> None:
        """Pause the currently running Batch operation without clearing results."""
        if self._batch_auto_generate_running:
            self._batch_auto_generate_paused = True
            self._batch_auto_generate_running = False
            self._autosave_batch_session("auto-generation paused")
            message = f"Auto-generation paused. Progress saved: {self._batch_autosave_path}"
        elif self._batch_add_all_running:
            self._batch_add_all_paused = True
            self._batch_add_all_running = False
            self._autosave_batch_session("add all ready paused")
            message = f"Add all ready paused. Progress saved: {self._batch_autosave_path}"
        else:
            message = "No Batch process is currently running."
        self._batch_status_var.set(message)
        self._status_var.set(message)
        self._record_activity(message)

    def _stop_batch_process(self) -> None:
        """Stop the current Batch operation while preserving generated results."""
        if self._batch_auto_generate_running or self._batch_auto_generate_paused:
            self._batch_auto_generate_stop_requested = True
            self._batch_auto_generate_paused = False
            self._batch_auto_generate_running = False
            self._autosave_batch_session("auto-generation stopped")
            message = f"Auto-generation stopped. Progress saved: {self._batch_autosave_path}"
        elif self._batch_add_all_running or self._batch_add_all_paused:
            self._batch_add_all_stop_requested = True
            self._batch_add_all_paused = False
            self._batch_add_all_running = False
            self._autosave_batch_session("add all ready stopped")
            counts = self._batch_add_all_counts
            message = (
                f"Add all ready stopped: {counts['added']} added, {counts['updated']} updated, "
                f"{counts['duplicates']} duplicates left, {counts['failed']} failed. "
                f"Progress saved: {self._batch_autosave_path}"
            )
        else:
            message = "No Batch process is currently running."
        self._batch_status_var.set(message)
        self._status_var.set(message)
        self._record_activity(message)

    def _retry_failed_or_rate_limited_batch_cards(self) -> None:
        """Retry failed/rate-limited Batch items with the currently selected provider."""
        if not self._batch_items:
            messagebox.showerror("No list", "Load a vocabulary list first.")
            return

        retryable_statuses = {"error", "rate_limited", "provider_failed"}
        retryable_indexes = [
            index
            for index, item in enumerate(self._batch_items)
            if str(item.get("status")) in retryable_statuses
        ]
        if not retryable_indexes:
            self._batch_status_var.set("No failed or rate-limited items to retry.")
            return

        for index in retryable_indexes:
            item = self._batch_items[index]
            item["status"] = "pending"
            item["previous_error"] = item.pop("error", "")
            item["retry_provider"] = self._provider_var.get()

        self._batch_index = retryable_indexes[0]
        self._show_current_batch_item(generate=False)
        self._autosave_batch_session("retry failed/rate-limited prepared")
        self._batch_status_var.set(
            f"Prepared {len(retryable_indexes)} failed/rate-limited item(s) for retry with {self._provider_var.get()}."
        )
        self._auto_generate_pending_batch_cards()

    def _start_add_all_ready_batch_cards(self) -> None:
        """Start safe step-by-step adding of all ready Batch cards."""
        if self._batch_add_all_running:
            self._batch_status_var.set("Add all ready is already running.")
            return

        if self._batch_add_all_paused and self._batch_add_all_indexes:
            self._batch_add_all_running = True
            self._batch_add_all_paused = False
            self._batch_add_all_stop_requested = False
            self._autosave_batch_session("add all ready resumed")
            self._record_activity("Add all ready resumed")
            self._root.after(50, self._add_next_ready_batch_card)
            return

        indexes = [
            index
            for index, item in enumerate(self._batch_items)
            if str(item.get("status")) == "ready"
            and self._card_from_batch_payload(item.get("card")) is not None
        ]
        if not indexes:
            self._batch_status_var.set("No ready cards to add.")
            self._status_var.set(self._batch_status_var.get())
            return

        warnings = self._quality_warnings_for_batch_indexes(indexes)
        if warnings:
            confirmed = messagebox.askyesno(
                "Quality warnings",
                "Some ready cards have quality warnings. Continue adding them to Anki?\n\n"
                + "\n".join(warnings[:12])
                + ("\n..." if len(warnings) > 12 else ""),
            )
            if not confirmed:
                self._batch_status_var.set("Add all ready cancelled because of quality warnings.")
                return

        duplicate_policy = messagebox.askyesnocancel(
            "Duplicate handling",
            "If duplicate cards are found, update the existing Anki cards?\n\n"
            "Yes = update duplicates\n"
            "No = leave duplicates for manual review\n"
            "Cancel = stop",
        )
        if duplicate_policy is None:
            return

        try:
            self._set_selected_deck()
            self._batch_add_all_existing_notes = self._anki_client.existing_vocabulary_note_map()
        except Exception as exc:
            LOGGER.exception("Could not prepare Add all ready")
            messagebox.showerror("Anki error", str(exc))
            return

        self._batch_add_all_indexes = indexes
        self._batch_add_all_position = 0
        self._batch_add_all_duplicate_policy = bool(duplicate_policy)
        self._batch_add_all_counts = {"added": 0, "updated": 0, "duplicates": 0, "failed": 0}
        self._batch_add_all_running = True
        self._batch_add_all_paused = False
        self._batch_add_all_stop_requested = False
        self._autosave_batch_session("before add all ready")
        self._record_activity(f"Add all ready started: {len(indexes)} cards")
        LOGGER.info("Add all ready started: ready=%s", len(indexes))
        self._root.after(50, self._add_next_ready_batch_card)

    def _add_next_ready_batch_card(self) -> None:
        """Add one ready Batch card, then schedule the next one."""
        if self._batch_add_all_stop_requested:
            self._batch_add_all_running = False
            self._batch_add_all_stop_requested = False
            self._autosave_batch_session("add all ready stopped")
            counts = self._batch_add_all_counts
            message = (
                f"Add all ready stopped: {counts['added']} added, {counts['updated']} updated, "
                f"{counts['duplicates']} duplicates left, {counts['failed']} failed. "
                f"Progress saved: {self._batch_autosave_path}"
            )
            self._batch_status_var.set(message)
            self._status_var.set(message)
            self._record_activity(message)
            return
        if self._batch_add_all_paused:
            return
        if not self._batch_add_all_running:
            return

        if self._batch_add_all_position >= len(self._batch_add_all_indexes):
            self._batch_add_all_running = False
            self._update_batch_progress()
            self._show_current_batch_item(generate=False)
            self._autosave_batch_session("add all ready finished")
            counts = self._batch_add_all_counts
            message = (
                f"Add all ready finished: {counts['added']} added, "
                f"{counts['updated']} updated, {counts['duplicates']} duplicates left, "
                f"{counts['failed']} failed. Autosave: {self._batch_autosave_path}"
            )
            self._batch_status_var.set(message)
            self._status_var.set(message)
            self._record_activity(message)
            LOGGER.info(message)
            return

        item_index = self._batch_add_all_indexes[self._batch_add_all_position]
        self._batch_add_all_position += 1
        item = self._batch_items[item_index]
        card = self._card_from_batch_payload(item.get("card"))
        total = len(self._batch_add_all_indexes)

        if card is None:
            item["status"] = "error"
            item["error"] = "Stored card payload could not be rebuilt."
            self._batch_add_all_counts["failed"] += 1
            self._autosave_batch_session("add all invalid payload")
            self._root.after(100, self._add_next_ready_batch_card)
            return

        provider_name = str(item.get("provider_name") or self._provider_var.get())
        self._batch_index = item_index
        self._batch_status_var.set(
            f"Adding {self._batch_add_all_position}/{total}: {card.word_or_phrase}"
        )
        self._status_var.set(self._batch_status_var.get())
        self._update_batch_progress()
        self._root.update_idletasks()

        try:
            normalized = self._normalise_anki_value(card.word_or_phrase)
            existing_note_id = self._batch_add_all_existing_notes.get(normalized)
            if existing_note_id is not None:
                if self._batch_add_all_duplicate_policy:
                    self._anki_client.update_card_by_note_id(
                        existing_note_id, card, provider_name,
                        extra_tags=self._topic_tags_for_batch_item(item),
                    )
                    item["status"] = "added"
                    self._batch_add_all_counts["updated"] += 1
                else:
                    item["status"] = "duplicate"
                    item["error"] = "Existing Anki card was not updated."
                    self._batch_add_all_counts["duplicates"] += 1
            else:
                self._anki_client.add_card_without_duplicate_scan(
                    card, provider_name, extra_tags=self._topic_tags_for_batch_item(item)
                )
                self._batch_add_all_existing_notes[normalized] = -1
                item["status"] = "added"
                self._batch_add_all_counts["added"] += 1

        except Exception as exc:
            LOGGER.exception("Add all ready failed for %s", card.word_or_phrase)
            item["status"] = "error"
            item["error"] = str(exc)
            self._batch_add_all_counts["failed"] += 1

        self._autosave_batch_session(f"add all {self._batch_add_all_position}/{total}")
        self._root.after(120, self._add_next_ready_batch_card)

    def _save_batch_session(self) -> None:
        if not self._batch_items:
            messagebox.showwarning("No session", "There is no batch session to save.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save batch session",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not filename:
            return
        data = self._batch_session_data()
        try:
            Path(filename).write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            messagebox.showerror("Save error", str(exc))
            return
        self._batch_autosave_path = Path(filename)
        self._record_activity("Batch session saved")
        self._batch_status_var.set(f"Batch session saved: {filename}")

    def _resume_batch_session(self) -> None:
        filename = filedialog.askopenfilename(
            title="Resume batch session",
            filetypes=[("JSON files", "*.json")],
        )
        if not filename:
            return
        try:
            data = json.loads(Path(filename).read_text(encoding="utf-8"))
            self._batch_items = list(data["items"])
            self._batch_index = int(data.get("index", 0))
            self._batch_autosave_path = Path(filename)
            if data.get("provider") in self._ai_clients:
                self._provider_var.set(data["provider"])
            self._language_var.set(data.get("target_language", self._language_var.get()))
            self._explanation_language_var.set(
                data.get("explanation_language", self._explanation_language_var.get())
            )
            self._batch_topic_var.set(data.get("batch_topic", self._batch_topic_var.get()))
            self._deck_var.set(data.get("deck", self._deck_var.get()))
        except Exception as exc:
            messagebox.showerror("Resume error", str(exc))
            return
        self._show_current_batch_item(generate=False)
        self._record_activity("Batch session resumed")
        self._batch_status_var.set("Batch session resumed.")

    def _practice_query(self) -> str:
        deck = self._deck_var.get().strip().replace('"', '\"')
        base = f'deck:"{deck}"'
        scope = self._practice_scope_var.get()
        if scope == "Due + overdue":
            return f"{base} is:due"
        if scope == "Overdue":
            return f"{base} is:due prop:due<0"
        if scope == "New":
            return f"{base} is:new"
        return base

    def _load_practice_cards(self) -> None:
        try:
            self._set_selected_deck()
            cards = self._anki_client.find_cards_for_practice(self._practice_query())
            self._practice_items = PracticeService.from_anki_cards(cards)
        except Exception as exc:
            messagebox.showerror("Anki error", str(exc))
            return
        for widget in self._practice_selection_frame.winfo_children():
            widget.destroy()
        self._practice_item_vars = []
        for row, item in enumerate(self._practice_items):
            var = ctk.BooleanVar(value=True)
            self._practice_item_vars.append(var)
            label = f"{item.display_name}  ·  {item.item_type}"
            ctk.CTkCheckBox(self._practice_selection_frame, text=label, variable=var).grid(
                row=row, column=0, sticky="w", padx=6, pady=4
            )
        self._practice_progress_var.set(f"Loaded {len(self._practice_items)} supported cards.")
        self._practice_feedback_var.set(
            "Select the material. The app randomizes only the question order."
        )

    def _set_all_practice_items(self, selected: bool) -> None:
        for var in self._practice_item_vars:
            var.set(selected)

    def _selected_practice_items(self) -> list[PracticeItem]:
        return [
            item
            for item, var in zip(self._practice_items, self._practice_item_vars)
            if var.get()
        ]

    def _start_practice(self) -> None:
        selected = self._selected_practice_items()
        if not selected:
            messagebox.showwarning("No cards selected", "Select at least one card.")
            return
        self._practice_questions = PracticeService.build_questions(selected)
        self._practice_index = 0
        self._practice_correct = 0
        self._practice_incorrect = 0
        self._show_practice_question()

    def _show_practice_question(self) -> None:
        if not self._practice_questions:
            return
        if self._practice_index >= len(self._practice_questions):
            self._end_practice()
            return
        question = self._practice_questions[self._practice_index]
        self._practice_checked = False
        self._practice_selected_answer.set("")
        self._practice_feedback_var.set("")
        self._practice_prompt.configure(state="normal")
        self._practice_prompt.delete("1.0", "end")
        self._practice_prompt.insert("1.0", question.prompt)
        self._practice_prompt.configure(state="disabled")
        for widget in self._practice_options_frame.winfo_children():
            widget.destroy()
        for row, option in enumerate(question.options):
            ctk.CTkRadioButton(
                self._practice_options_frame,
                text=option,
                variable=self._practice_selected_answer,
                value=option,
                font=ctk.CTkFont(size=15),
            ).grid(row=row, column=0, sticky="w", padx=10, pady=8)
        self._practice_progress_var.set(
            f"{self._practice_index + 1}/{len(self._practice_questions)} · "
            f"Correct {self._practice_correct} · Incorrect {self._practice_incorrect}"
        )

    def _check_practice_answer(self) -> None:
        if not self._practice_questions or self._practice_checked:
            return
        selected = self._practice_selected_answer.get().strip()
        if not selected:
            self._practice_feedback_var.set("Choose an answer first.")
            return
        question = self._practice_questions[self._practice_index]
        self._practice_checked = True
        if selected.casefold() == question.correct_answer.casefold():
            self._practice_correct += 1
            self._practice_feedback_var.set(f"✓ Correct: {question.correct_answer}")
        else:
            self._practice_incorrect += 1
            self._practice_feedback_var.set(
                f"✕ Incorrect. Correct answer: {question.correct_answer}"
            )
        self._practice_progress_var.set(
            f"{self._practice_index + 1}/{len(self._practice_questions)} · "
            f"Correct {self._practice_correct} · Incorrect {self._practice_incorrect}"
        )


    def _build_existing_cards_tab(self, parent: ctk.CTkFrame) -> None:
        """Build quality-maintenance workflows for cards that already exist in Anki."""
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)
        layout.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(layout, corner_radius=18, width=390)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_propagate(False)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(12, weight=1)

        ctk.CTkLabel(
            left,
            text="Fix / Improve existing cards",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            left,
            text="For flagged/leech/tagged cards and manual fixes. Missing audio backfill lives in Speech / Audio.",
            wraplength=335,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        ctk.CTkLabel(left, text="Extra Anki query").grid(
            row=2, column=0, sticky="w", padx=18, pady=(4, 4)
        )
        ctk.CTkEntry(
            left,
            textvariable=self._existing_search_var,
            placeholder_text='e.g. tag:needs_fix, is:due, word text',
        ).grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 8))

        ctk.CTkLabel(left, text="Tag filter").grid(row=4, column=0, sticky="w", padx=18, pady=(4, 4))
        ctk.CTkEntry(
            left,
            textvariable=self._existing_tag_var,
            placeholder_text='e.g. topic_character or needs_example_fix',
        ).grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 8))

        ctk.CTkLabel(left, text="Flag filter").grid(row=6, column=0, sticky="w", padx=18, pady=(4, 4))
        self._existing_flag_box = ctk.CTkComboBox(
            left,
            variable=self._existing_flag_var,
            values=[
                "Any flag",
                "Red flag (flag:1)",
                "Orange flag (flag:2)",
                "Green flag (flag:3)",
                "Blue flag (flag:4)",
                "No flag (flag:0)",
            ],
            state="readonly",
        )
        self._existing_flag_box.grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 8))

        ctk.CTkCheckBox(left, text="Only leech cards / tag:leech", variable=self._existing_leech_var).grid(
            row=8, column=0, sticky="w", padx=18, pady=(0, 8)
        )

        query_buttons = ctk.CTkFrame(left, fg_color="transparent")
        query_buttons.grid(row=9, column=0, sticky="ew", padx=18, pady=(0, 8))
        query_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(query_buttons, text="Find cards", command=self._find_existing_cards).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(query_buttons, text="Load flagged", command=self._load_flagged_existing_cards).grid(
            row=0, column=1, sticky="ew", padx=(5, 0)
        )
        ctk.CTkButton(query_buttons, text="Load leech", command=self._load_leech_existing_cards).grid(
            row=1, column=0, sticky="ew", padx=(0, 5), pady=(8, 0)
        )
        ctk.CTkButton(query_buttons, text="Load needs_fix", command=self._load_needs_fix_existing_cards).grid(
            row=1, column=1, sticky="ew", padx=(5, 0), pady=(8, 0)
        )

        ctk.CTkLabel(left, text="Words list for dry topic tagging").grid(
            row=10, column=0, sticky="w", padx=18, pady=(8, 4)
        )
        self._existing_words_text = ctk.CTkTextbox(left, height=105, wrap="word")
        self._existing_words_text.grid(row=11, column=0, sticky="nsew", padx=18, pady=(0, 8))
        ctk.CTkButton(
            left,
            text="Find words from list",
            command=self._find_existing_words_from_list,
        ).grid(row=12, column=0, sticky="new", padx=18, pady=(0, 10))

        ctk.CTkLabel(left, text="Topic / dział tag").grid(
            row=13, column=0, sticky="w", padx=18, pady=(8, 4)
        )
        self._existing_topic_box = ctk.CTkComboBox(
            left, variable=self._existing_topic_var, values=TOPIC_PRESETS[1:]
        )
        self._existing_topic_box.grid(row=14, column=0, sticky="ew", padx=18, pady=(0, 10))

        tag_buttons = ctk.CTkFrame(left, fg_color="transparent")
        tag_buttons.grid(row=15, column=0, sticky="ew", padx=18, pady=(0, 8))
        tag_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(tag_buttons, text="Select all", command=lambda: self._set_existing_selection(True)).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(tag_buttons, text="Clear", command=lambda: self._set_existing_selection(False)).grid(
            row=0, column=1, sticky="ew", padx=(5, 0)
        )

        ctk.CTkButton(
            left,
            text="Apply topic tag to selected",
            command=self._apply_topic_to_existing_selected,
        ).grid(row=16, column=0, sticky="ew", padx=18, pady=(0, 8))
        ctk.CTkButton(
            left,
            text="Fix selected card",
            command=self._fix_selected_existing_card,
        ).grid(row=17, column=0, sticky="ew", padx=18, pady=(0, 18))

        right = ctk.CTkFrame(layout, corner_radius=18)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=2)
        right.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Fix cards queue", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(header, textvariable=self._existing_progress_var).grid(row=0, column=1, sticky="e")

        self._existing_scroll = ctk.CTkScrollableFrame(right, corner_radius=18)
        self._existing_scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self._existing_scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right, text="Preview selected card", anchor="w").grid(
            row=2, column=0, sticky="w", padx=18, pady=(0, 4)
        )
        self._existing_preview = ctk.CTkTextbox(right, wrap="word", height=180, font=ctk.CTkFont(size=14))
        self._existing_preview.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self._existing_preview.insert("1.0", "Load flagged/leech/tagged cards, then preview and fix one selected card.")
        self._existing_preview.configure(state="disabled")

    def _find_existing_cards(self) -> None:
        self._load_existing_cards()

    def _load_flagged_existing_cards(self) -> None:
        if self._existing_flag_var.get() == "Any flag":
            self._existing_flag_var.set("Red flag (flag:1)")
        self._load_existing_cards()

    def _load_leech_existing_cards(self) -> None:
        self._existing_leech_var.set(True)
        self._load_existing_cards()

    def _load_needs_fix_existing_cards(self) -> None:
        current = self._existing_tag_var.get().strip()
        self._existing_tag_var.set(current or "needs_fix")
        self._load_existing_cards()

    def _find_existing_words_from_list(self) -> None:
        words = self._existing_words_text.get("1.0", "end").splitlines()
        clean_words = self._normalise_batch_words(words)
        if not clean_words:
            messagebox.showwarning("Empty list", "Paste one word or phrase per line first.")
            return
        self._load_existing_cards(words=clean_words)

    def _existing_flag_query(self) -> str:
        value = self._existing_flag_var.get()
        match = re.search(r"flag:(\d)", value)
        return f"flag:{match.group(1)}" if match else ""

    def _compose_existing_cards_query(self) -> str:
        query_parts: list[str] = []
        extra_query = self._existing_search_var.get().strip()
        tag = self._existing_tag_var.get().strip()
        flag_query = self._existing_flag_query()
        if extra_query:
            query_parts.append(extra_query)
        if tag:
            query_parts.append(f"tag:{tag}")
        if flag_query:
            query_parts.append(flag_query)
        if self._existing_leech_var.get():
            query_parts.append("tag:leech")
        return " ".join(query_parts)

    def _load_existing_cards(self, words: list[str] | None = None) -> None:
        try:
            self._set_selected_deck()
            query = self._compose_existing_cards_query()
            self._existing_cards = self._anki_client.list_existing_notes(
                search_query=query,
                missing_audio_only=False,
                words=words,
            )
        except Exception as exc:
            LOGGER.exception("Existing-card search failed")
            messagebox.showerror("Anki error", str(exc))
            return
        suffix = " from pasted words" if words else ""
        query_label = self._compose_existing_cards_query() or "selected deck"
        self._render_existing_cards(
            f"Loaded {len(self._existing_cards)} card(s){suffix}. Filter: {query_label}"
        )

    def _render_existing_cards(self, progress_message: str | None = None) -> None:
        for widget in self._existing_scroll.winfo_children():
            widget.destroy()
        self._existing_card_vars = []
        for index, note in enumerate(self._existing_cards):
            var = ctk.BooleanVar(value=False)
            self._existing_card_vars.append(var)
            tags = note.get("tags") or []
            topic_tags = [tag for tag in tags if str(tag).startswith("topic_") or str(tag).startswith("topic::")]
            quality_tags = [tag for tag in tags if str(tag) in {"leech", "needs_fix", "needs_audio_fix", "needs_example_fix", "needs_topic_fix"}]
            tag_text = ", ".join([*topic_tags[:2], *quality_tags[:3]])
            tag_suffix = f" · {tag_text}" if tag_text else ""
            label = (
                f"{note.get('word', '—')} · {note.get('model', 'unknown model')}"
                f" · audio:{note.get('audio_status', 'unknown')}"
                f"{tag_suffix}"
            )
            checkbox = ctk.CTkCheckBox(
                self._existing_scroll,
                text=label,
                variable=var,
                command=lambda i=index: self._preview_existing_card(i),
            )
            checkbox.grid(row=index, column=0, sticky="w", padx=12, pady=5)
        if progress_message is not None:
            self._existing_progress_var.set(progress_message)
        if self._existing_cards:
            self._preview_existing_card(0)
        else:
            self._set_existing_preview("No matching cards found. Try a broader tag/query or use Speech / Audio for missing-audio search.")

    def _set_existing_selection(self, selected: bool) -> None:
        for var in self._existing_card_vars:
            var.set(selected)

    def _selected_existing_cards(self) -> list[dict[str, object]]:
        return [
            note
            for note, var in zip(self._existing_cards, self._existing_card_vars)
            if var.get()
        ]

    def _preview_existing_card(self, index: int) -> None:
        if not (0 <= index < len(self._existing_cards)):
            return
        note = self._existing_cards[index]
        fields = note.get("fields") if isinstance(note.get("fields"), dict) else {}
        blocks = [
            "╭────────────────────────────────────────╮",
            f"  {note.get('word', '—')}",
            "╰────────────────────────────────────────╯",
            "",
            f"NOTE ID\n{note.get('note_id')}",
            "",
            f"MODEL\n{note.get('model', '—')}",
            "",
            f"AUDIO STATUS\n{note.get('audio_status', '—')}",
            "",
            f"AUDIO FIELD\n{note.get('audio_field') or '—'}",
            "",
            f"EXAMPLE\n{note.get('example') or '—'}",
            "",
            f"TAGS\n{', '.join(note.get('tags') or []) or '—'}",
            "",
            "FIELDS",
        ]
        for name, value in list(fields.items())[:16]:
            blocks.append(f"- {name}: {self._plain_text(value)[:220]}")
        self._set_existing_preview("\n".join(blocks))

    def _set_existing_preview(self, content: str) -> None:
        self._existing_preview.configure(state="normal")
        self._existing_preview.delete("1.0", "end")
        self._existing_preview.insert("1.0", content)
        self._existing_preview.configure(state="disabled")

    def _apply_topic_to_existing_selected(self) -> None:
        selected = self._selected_existing_cards()
        if not selected:
            messagebox.showwarning("No cards selected", "Select at least one existing card.")
            return
        topic = self._existing_topic_var.get().strip()
        if not topic:
            messagebox.showwarning("Missing topic", "Choose or type a topic/dział first.")
            return
        tag = self._topic_tag_from_value(topic)
        note_ids = [int(note["note_id"]) for note in selected]
        try:
            self._anki_client.add_tags_to_notes(note_ids, tag)
        except Exception as exc:
            LOGGER.exception("Could not apply topic tag to existing notes")
            messagebox.showerror("Anki tag error", str(exc))
            return
        for note in selected:
            tags = list(note.get("tags") or [])
            if tag not in tags:
                tags.append(tag)
            note["tags"] = tags
        self._render_existing_cards(f"Applied {tag} to {len(note_ids)} card(s).")
        self._record_activity(f"Applied topic tag: {tag}")

    def _card_from_existing_note(self, note: dict[str, object]) -> VocabularyCard:
        fields = note.get("fields") if isinstance(note.get("fields"), dict) else {}
        def field(*names: str) -> str:
            for name in names:
                if name in fields:
                    return self._plain_text(fields.get(name, ""))
            return ""
        return VocabularyCard(
            is_valid=True,
            explanation_language=self._explanation_language_var.get(),
            word_or_phrase=field("Word", "Front", "Expression", "Phrase", "Term") or str(note.get("word", "")),
            target_language=field("Language") or self._language_var.get(),
            part_of_speech=field("PartOfSpeech", "Part of Speech"),
            definition=field("Definition", "Meaning", "Back"),
            translation_pl=field("TranslationPL", "Translation", "PL"),
            example=field("Example", "Sentence", "ExampleSentence") or str(note.get("example", "")),
            example_pl=field("ExamplePL", "ExampleTranslation"),
            synonyms=[part.strip() for part in field("Synonyms").split(",") if part.strip()],
            collocations=[part.strip() for part in re.split(r"\n|,|•", field("Collocations")) if part.strip()],
            grammar_note=field("GrammarNote", "Grammar", "Usage"),
            audio=str(note.get("audio", "")),
        )

    def _backup_existing_note_update(
        self,
        note: dict[str, object],
        new_fields: dict[str, str],
        reason: str,
    ) -> Path:
        backup_dir = Path("existing_card_backups")
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = backup_dir / f"note_{note.get('note_id')}_{stamp}.json"
        payload = {
            "kind": "existing_card_update_backup",
            "reason": reason,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "note_id": note.get("note_id"),
            "deck": self._deck_var.get(),
            "before_update": note,
            "after_update_fields": new_fields,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _fix_selected_existing_card(self) -> None:
        selected = self._selected_existing_cards()
        if len(selected) != 1:
            messagebox.showwarning("Select one card", "Select exactly one existing card to fix.")
            return
        note = selected[0]
        try:
            card = self._card_from_existing_note(note)
        except Exception as exc:
            messagebox.showerror("Card parse error", str(exc))
            return
        self._open_existing_card_editor(note, card)

    def _open_existing_card_editor(self, note: dict[str, object], card: VocabularyCard) -> None:
        editor = tk.Toplevel(self._root)
        editor.title(f"Fix existing card: {card.word_or_phrase}")
        editor.geometry("760x760")
        editor.transient(self._root)
        editor.grid_columnconfigure(1, weight=1)

        entries: dict[str, tk.Widget] = {}

        def add_entry(row: int, label: str, key: str, value: str) -> int:
            tk.Label(editor, text=label, anchor="w").grid(row=row, column=0, sticky="nw", padx=10, pady=6)
            widget = tk.Entry(editor)
            widget.insert(0, value or "")
            widget.grid(row=row, column=1, sticky="ew", padx=10, pady=6)
            entries[key] = widget
            return row + 1

        def add_text(row: int, label: str, key: str, value: str, height: int = 3) -> int:
            tk.Label(editor, text=label, anchor="w").grid(row=row, column=0, sticky="nw", padx=10, pady=6)
            widget = tk.Text(editor, height=height, wrap="word")
            widget.insert("1.0", value or "")
            widget.grid(row=row, column=1, sticky="nsew", padx=10, pady=6)
            entries[key] = widget
            return row + 1

        row = 0
        row = add_entry(row, "Language", "target_language", card.target_language)
        row = add_entry(row, "Part of speech", "part_of_speech", card.part_of_speech)
        row = add_entry(row, "Word / phrase", "word_or_phrase", card.word_or_phrase)
        row = add_text(row, "Definition", "definition", card.definition, height=3)
        row = add_text(row, "Translation / explanation", "translation_pl", card.translation_pl, height=3)
        row = add_text(row, "Example", "example", card.example, height=3)
        row = add_text(row, "Example translation", "example_pl", card.example_pl, height=3)
        row = add_text(row, "Collocations\n(one per line)", "collocations", "\n".join(card.collocations), height=4)
        row = add_text(row, "Synonyms\n(one per line)", "synonyms", "\n".join(card.synonyms), height=3)
        row = add_text(row, "Grammar note", "grammar_note", card.grammar_note, height=3)

        def value(key: str) -> str:
            widget = entries[key]
            if isinstance(widget, tk.Text):
                return widget.get("1.0", "end").strip()
            return str(widget.get()).strip()  # type: ignore[attr-defined]

        def build_updated_card() -> VocabularyCard:
            return card.model_copy(
                update={
                    "target_language": value("target_language") or card.target_language,
                    "part_of_speech": value("part_of_speech"),
                    "word_or_phrase": value("word_or_phrase") or card.word_or_phrase,
                    "definition": value("definition"),
                    "translation_pl": value("translation_pl"),
                    "example": value("example"),
                    "example_pl": value("example_pl"),
                    "collocations": [line.strip() for line in value("collocations").splitlines() if line.strip()],
                    "synonyms": [line.strip() for line in value("synonyms").splitlines() if line.strip()],
                    "grammar_note": value("grammar_note"),
                }
            )

        def save_to_anki() -> None:
            updated_card = build_updated_card()
            fields_map = note.get("fields") if isinstance(note.get("fields"), dict) else {}
            raw_fields: dict[str, str] = {}
            mapping = {
                "Word": updated_card.word_or_phrase,
                "Language": updated_card.target_language,
                "PartOfSpeech": updated_card.part_of_speech,
                "TranslationPL": updated_card.translation_pl,
                "Definition": updated_card.definition,
                "Example": updated_card.example,
                "ExamplePL": updated_card.example_pl,
                "Synonyms": ", ".join(updated_card.synonyms),
                "Collocations": "\n".join(updated_card.collocations),
                "GrammarNote": updated_card.grammar_note,
            }
            for field_name, field_value in mapping.items():
                if field_name in fields_map:
                    raw_fields[field_name] = field_value
            # Basic/legacy notes often only have Front/Back. Update what exists,
            # never create new fields on an unrelated note type.
            if "Front" in fields_map:
                raw_fields.setdefault("Front", updated_card.word_or_phrase)
            if "Back" in fields_map and not any(name in fields_map for name in ("Definition", "Example")):
                raw_fields.setdefault(
                    "Back",
                    f"Definition: {updated_card.definition}\n\nExample: {updated_card.example}\n{updated_card.example_pl}",
                )
            if not raw_fields:
                messagebox.showerror("Unsupported note", "This note has no editable supported fields.")
                return
            try:
                backup_path = self._backup_existing_note_update(note, raw_fields, "manual fix")
                self._anki_client.update_note_fields(int(note["note_id"]), raw_fields)
            except Exception as exc:
                LOGGER.exception("Could not update existing note")
                messagebox.showerror("Anki update error", str(exc))
                return
            note_fields = note.get("fields") if isinstance(note.get("fields"), dict) else {}
            note_fields.update(raw_fields)
            note["fields"] = note_fields
            note["word"] = updated_card.word_or_phrase
            note["example"] = updated_card.example
            self._render_existing_cards(f"Updated existing card. Backup: {backup_path}")
            self._record_activity(f"Fixed existing card: {updated_card.word_or_phrase}")
            editor.destroy()

        def regenerate_full_preview() -> None:
            provider_name = self._provider_var.get()
            topic = self._existing_topic_var.get().strip()
            try:
                regenerated = self._current_ai_client().generate_card(
                    value("word_or_phrase") or card.word_or_phrase,
                    value("target_language") or self._language_var.get(),
                    self._explanation_language_var.get(),
                    topic,
                )
            except Exception as exc:
                LOGGER.exception("Existing-card regeneration failed")
                messagebox.showerror(
                    "Generation error",
                    self._friendly_generation_error_detail(str(exc), provider_name, self._current_ai_model_name()),
                )
                return
            for key, val in {
                "target_language": regenerated.target_language,
                "part_of_speech": regenerated.part_of_speech,
                "word_or_phrase": regenerated.word_or_phrase,
                "definition": regenerated.definition,
                "translation_pl": regenerated.translation_pl,
                "example": regenerated.example,
                "example_pl": regenerated.example_pl,
                "collocations": "\n".join(regenerated.collocations),
                "synonyms": "\n".join(regenerated.synonyms),
                "grammar_note": regenerated.grammar_note,
            }.items():
                widget = entries[key]
                if isinstance(widget, tk.Text):
                    widget.delete("1.0", "end")
                    widget.insert("1.0", val)
                else:
                    widget.delete(0, "end")  # type: ignore[attr-defined]
                    widget.insert(0, val)  # type: ignore[attr-defined]

        button_row = tk.Frame(editor)
        button_row.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=12)
        tk.Button(button_row, text="Save to Anki", command=save_to_anki).pack(side="left")
        tk.Button(button_row, text="Regenerate full preview", command=regenerate_full_preview).pack(side="left", padx=(8, 0))
        tk.Button(button_row, text="Cancel", command=editor.destroy).pack(side="left", padx=(8, 0))

    def _build_speech_tab(self, parent: ctk.CTkFrame) -> None:
        """Build the central TTS/audio backfill workflow."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(3, weight=1)

        controls = ctk.CTkFrame(frame, corner_radius=18)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls.grid_columnconfigure((1, 3, 5), weight=1)
        ctk.CTkLabel(controls, text="TTS provider").grid(row=0, column=0, padx=(16, 8), pady=14)
        self._tts_provider_box = ctk.CTkComboBox(
            controls, variable=self._tts_provider_var,
            values=list(self._speech_service.providers) if self._speech_service else [],
            state="readonly", command=lambda _value: self._sync_tts_defaults(),
        )
        self._tts_provider_box.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=14)
        ctk.CTkLabel(controls, text="Model").grid(row=0, column=2, padx=(0, 8), pady=14)
        self._tts_model_box = ctk.CTkComboBox(controls, variable=self._tts_model_var, values=[])
        self._tts_model_box.grid(row=0, column=3, sticky="ew", padx=(0, 16), pady=14)
        ctk.CTkLabel(controls, text="Voice").grid(row=0, column=4, padx=(0, 8), pady=14)
        self._tts_voice_box = ctk.CTkComboBox(controls, variable=self._tts_voice_var, values=[])
        self._tts_voice_box.grid(row=0, column=5, sticky="ew", padx=(0, 16), pady=14)

        search = ctk.CTkFrame(frame, corner_radius=18)
        search.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        search.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(search, text="Extra Anki query").grid(row=0, column=0, padx=(16, 8), pady=12)
        ctk.CTkEntry(
            search,
            textvariable=self._speech_search_var,
            placeholder_text='optional, e.g. tag:topic_character, note:Basic, is:due',
        ).grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=12)
        ctk.CTkLabel(
            search,
            text="Audio scans all note types in the selected deck and filters missing/malformed audio fields.",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 12))

        actions = ctk.CTkFrame(frame, corner_radius=18)
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(actions, text="Find missing audio", command=self._load_speech_notes).pack(side="left", padx=16, pady=14)
        ctk.CTkButton(actions, text="Select all", command=lambda: [v.set(True) for v in self._speech_note_vars]).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkButton(actions, text="Clear", command=lambda: [v.set(False) for v in self._speech_note_vars]).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkButton(actions, text="Generate audio for selected", command=self._generate_audio_for_existing).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkButton(actions, text="Pause audio", command=self._pause_existing_audio_batch).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkButton(actions, text="Stop audio", command=self._stop_existing_audio_batch).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkButton(actions, text="Preview voice", command=self._preview_tts_voice_sample).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkLabel(actions, textvariable=self._speech_progress_var).pack(side="right", padx=16, pady=14)

        self._speech_scroll = ctk.CTkScrollableFrame(frame, corner_radius=18)
        self._speech_scroll.grid(row=3, column=0, sticky="nsew")
        self._speech_scroll.grid_columnconfigure(0, weight=1)
        self._sync_tts_defaults()

    def _next_practice_question(self) -> None:
        if not self._practice_questions:
            return
        if not self._practice_checked:
            self._practice_feedback_var.set("Check the current answer before continuing.")
            return
        self._practice_index += 1
        self._show_practice_question()

    def _end_practice(self) -> None:
        total_answered = self._practice_correct + self._practice_incorrect
        summary = (
            f"Session finished · Answered {total_answered} · "
            f"Correct {self._practice_correct} · Incorrect {self._practice_incorrect}"
        )
        self._practice_progress_var.set(summary)
        self._practice_feedback_var.set(summary)
        self._practice_questions = []
        self._practice_index = 0
        self._practice_checked = False

    def _export_print_test(self) -> None:
        selected = self._selected_practice_items()
        if not selected:
            messagebox.showwarning("No cards selected", "Select at least one card.")
            return
        directory = filedialog.askdirectory(title="Choose folder for test and answer key")
        if not directory:
            return
        questions = PracticeService.build_questions(selected)
        deck_slug = "".join(ch if ch.isalnum() else "_" for ch in self._deck_var.get()).strip("_") or "anki"
        test_path = Path(directory) / f"{deck_slug}_test.html"
        key_path = Path(directory) / f"{deck_slug}_answer_key.html"
        PracticeService.export_printable_test(
            questions,
            test_path=test_path,
            key_path=key_path,
            title=f"Vocabulary and Grammar Test — {self._deck_var.get()}",
        )
        self._practice_feedback_var.set(
            f"Created: {test_path.name} and {key_path.name}"
        )
        self._record_activity("Printable test and answer key created")

    def _record_activity(self, text: str) -> None:
        previous = [part.strip() for part in self._activity_var.get().split(" | ") if part.strip()]
        previous.append(text)
        self._activity_var.set(" | ".join(previous[-3:]))

    def _current_ai_client(self) -> VocabularyAiClient:
        return self._ai_clients[self._provider_var.get()]

    def _current_ai_model_name(self) -> str:
        return str(getattr(self._current_ai_client(), "_model", ""))

    def _load_decks(self) -> None:
        try:
            decks = self._anki_client.list_decks()
        except Exception as exc:
            self._deck_box.configure(values=[self._anki_client.deck_name])
            self._status_var.set("Could not load decks. Open Anki and click Refresh.")
            messagebox.showwarning("Anki connection", str(exc))
            return

        if self._anki_client.deck_name not in decks:
            decks.append(self._anki_client.deck_name)
        self._deck_box.configure(values=sorted(decks))
        self._status_var.set("Decks loaded. Select the target deck before adding cards.")

    def _set_selected_deck(self) -> str:
        deck_name = self._deck_var.get().strip()
        if not deck_name:
            raise ValueError("Select or type an Anki deck name.")
        self._anki_client.set_deck(deck_name)
        return deck_name

    def _generate_single_card(self) -> None:
        word_or_phrase = self._word_var.get().strip()
        if not word_or_phrase:
            messagebox.showerror("Missing word", "Enter a word or phrase first.")
            return

        provider_name = self._provider_var.get()
        self._status_var.set(f"Generating card with {provider_name}...")
        self._root.update_idletasks()
        try:
            card = self._current_ai_client().generate_card(
                word_or_phrase, self._language_var.get(), self._explanation_language_var.get()
            )
        except Exception as exc:
            LOGGER.exception("Single-card generation failed: provider=%s word=%s", provider_name, word_or_phrase)
            friendly = self._friendly_generation_error_detail(
                str(exc), provider_name, self._current_ai_model_name()
            )
            self._status_var.set("Card generation failed. Raw details saved in logs.")
            messagebox.showerror("Generation error", friendly)
            return

        if not card.is_valid:
            correction = ("\nSuggested correction: " + card.suggested_correction) if card.suggested_correction else ""
            self._status_var.set("Input validation failed.")
            messagebox.showwarning("Invalid word or phrase", f"{card.validation_error}{correction}")
            return

        self._generated_card = card
        self._generated_audio = None
        self._generated_provider_name = provider_name
        self._show_single_preview(card)
        self._status_var.set("Card generated. Review it before adding to Anki.")

    def _show_single_preview(self, card: VocabularyCard) -> None:
        content = self._format_card_preview(card)
        self._preview.configure(state="normal")
        self._preview.delete("1.0", "end")
        self._preview.insert("1.0", content)
        self._preview.configure(state="disabled")

    @staticmethod
    def _format_card_preview(card: VocabularyCard, audio_status: object | None = None) -> str:
        """Return a readable pseudo-card preview for single and Batch workflows."""
        synonyms = ", ".join(card.synonyms) if card.synonyms else "—"
        collocations = "\n".join(f"  • {item}" for item in card.collocations) if card.collocations else "—"
        audio_line = str(audio_status or card.audio or "not generated")
        return (
            "╭────────────────────────────────────────╮\n"
            f"  {card.word_or_phrase}\n"
            "╰────────────────────────────────────────╯\n\n"
            f"LANGUAGE / TYPE\n{card.target_language} · {card.part_of_speech or '—'}\n\n"
            f"DEFINITION\n{card.definition or '—'}\n\n"
            f"EXPLANATION LANGUAGE\n{card.explanation_language or '—'}\n\n"
            f"TRANSLATION / EXPLANATION\n{card.translation_pl or '—'}\n\n"
            f"EXAMPLE\n{card.example or '—'}\n{card.example_pl or '—'}\n\n"
            f"SYNONYMS / ALTERNATIVES\n{synonyms}\n\n"
            f"COLLOCATIONS / USAGE\n{collocations}\n\n"
            f"GRAMMAR NOTE\n{card.grammar_note or '—'}\n\n"
            f"AUDIO\n{audio_line}"
        )

    def _add_single_card_to_anki(self) -> None:
        if self._generated_card is None:
            messagebox.showerror("No card", "Generate a card before adding it to Anki.")
            return
        if not self._confirm_quality_warnings(self._generated_card):
            self._status_var.set("Add to Anki cancelled because of quality warnings.")
            return
        provider_name = self._generated_provider_name or self._provider_var.get()
        try:
            deck = self._set_selected_deck()
            if self._generated_audio is not None:
                LOGGER.info(
                    "Storing generated audio in Anki media: path=%s word=%s",
                    self._generated_audio.path,
                    self._generated_card.word_or_phrase,
                )
                try:
                    media_name = self._anki_client.store_media_file(self._generated_audio.path)
                except Exception as media_exc:
                    LOGGER.exception(
                        "Could not store generated audio in Anki media: path=%s word=%s",
                        self._generated_audio.path,
                        self._generated_card.word_or_phrase,
                    )
                    raise RuntimeError(f"Audio was generated but could not be stored in Anki media: {media_exc}") from media_exc

                self._generated_card = self._generated_card.model_copy(
                    update={"audio": f"[sound:{media_name}]"}
                )
                LOGGER.info(
                    "Generated card audio field set: word=%s media=%s",
                    self._generated_card.word_or_phrase,
                    media_name,
                )
            self._anki_client.add_card(self._generated_card, provider_name)
        except DuplicateNoteError:
            replace = messagebox.askyesno(
                "Card already exists",
                f"A card for '{self._generated_card.word_or_phrase}' already exists.\n\n"
                "Replace it with this reviewed version?",
            )
            if not replace:
                self._status_var.set("Existing card was not changed.")
                return
            try:
                self._anki_client.update_card(self._generated_card, provider_name)
            except Exception as update_exc:
                LOGGER.exception(
                    "Could not update existing single card: word=%s audio=%s",
                    self._generated_card.word_or_phrase,
                    self._generated_card.audio,
                )
                message = f"Could not update the existing card: {update_exc}"
                self._status_var.set(message)
                messagebox.showerror("Anki update error", message)
                return
            deck = self._anki_client.deck_name
            self._status_var.set(
                f"✓ Updated existing card in {deck}: {self._generated_card.word_or_phrase}"
            )
            self._record_activity(f"↻ {self._generated_card.word_or_phrase} updated")
            self._word_var.set("")
            self._generated_card = None
            self._generated_provider_name = None
            self._generated_audio = None
            return
        except Exception as exc:
            LOGGER.exception(
                "Could not add single card to Anki: word=%s audio_cache=%s",
                self._generated_card.word_or_phrase if self._generated_card else "",
                self._generated_audio.path if self._generated_audio else "",
            )
            message = f"Could not add card to Anki: {exc}"
            self._status_var.set(message)
            self._record_activity("Add to Anki failed")
            messagebox.showerror("Anki error", message)
            return
        self._status_var.set(f"✓ Added to Anki deck {deck}: {self._generated_card.word_or_phrase}")
        self._record_activity(f"✓ {self._generated_card.word_or_phrase} added")
        self._word_var.set("")
        self._generated_card = None
        self._generated_provider_name = None
        self._generated_audio = None

    def _sync_tts_defaults(self) -> None:
        if not self._speech_service or not self._tts_provider_var.get():
            self._tts_model_var.set("")
            self._tts_voice_var.set("")
            return

        provider_name = self._tts_provider_var.get()
        provider = self._speech_service.providers[provider_name]
        self._tts_model_box.configure(values=provider.models) if hasattr(self, "_tts_model_box") else None

        voice_labels = get_voice_labels(provider_name, self._language_var.get())
        if not voice_labels:
            voice_labels = get_voice_labels(provider_name)
        if not voice_labels:
            voice_labels = list(provider.voices)

        self._tts_voice_box.configure(values=voice_labels) if hasattr(self, "_tts_voice_box") else None
        self._tts_model_var.set(provider.default_model)

        if voice_labels:
            self._tts_voice_var.set(voice_labels[0])
        else:
            self._tts_voice_var.set(provider.default_voice)
        if provider_name == "ElevenLabs":
            self._speech_progress_var.set(
                "ElevenLabs is optional/premium. Presets are not guaranteed; use Preview voice or switch to OpenAI/Gemini/Piper."
            )

    def _selected_tts_voice(self) -> str:
        """Return the provider-specific voice ID/name selected in the GUI."""
        provider_name = self._tts_provider_var.get()
        selected = self._tts_voice_var.get()
        try:
            return get_voice_by_label(provider_name, selected)
        except ValueError:
            return selected

    def _generate_single_audio(self) -> None:
        if self._generated_card is None:
            messagebox.showerror("No card", "Generate a vocabulary card first.")
            return
        if not self._speech_service or not self._tts_provider_var.get():
            messagebox.showerror("TTS unavailable", "Configure at least one TTS provider.")
            return
        self._status_var.set("Generating example audio...")
        self._root.update_idletasks()
        try:
            self._generated_audio = self._speech_service.generate(
                self._tts_provider_var.get(),
                self._generated_card.example,
                self._generated_card.target_language,
                self._tts_model_var.get(),
                self._selected_tts_voice(),
            )
        except Exception as exc:
            LOGGER.exception(
                "Single-card TTS generation failed: provider=%s model=%s voice=%s word=%s",
                self._tts_provider_var.get(),
                self._tts_model_var.get(),
                self._tts_voice_var.get(),
                self._generated_card.word_or_phrase,
            )
            message = f"Audio generation failed: {exc}"
            self._status_var.set(message)
            self._record_activity("Audio generation failed")
            messagebox.showerror("TTS error", message)
            return
        source = "cache" if self._generated_audio.cached else "provider"
        self._status_var.set(f"✓ Example audio ready from {source}: {self._generated_audio.path.name}")
        self._record_activity(f"♪ Example audio ready: {self._generated_audio.path.name}")
        LOGGER.info(
            "Single-card TTS ready: source=%s path=%s provider=%s model=%s voice_label=%s voice_value=%s",
            source,
            self._generated_audio.path,
            self._tts_provider_var.get(),
            self._tts_model_var.get(),
            self._tts_voice_var.get(),
            self._selected_tts_voice(),
        )

    def _preview_generated_audio(self) -> None:
        if self._generated_audio is None:
            messagebox.showwarning("No audio", "Generate example audio first.")
            return
        self._open_audio_file(self._generated_audio.path)

    @staticmethod
    def _open_audio_file(path: Path) -> None:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _preview_tts_voice_sample(self) -> None:
        """Generate and play a short voice sample after explicit user action."""
        if not self._speech_service or not self._tts_provider_var.get():
            messagebox.showerror("TTS unavailable", "Configure at least one TTS provider.")
            return

        sample_by_language = {
            "English": "This is a short pronunciation sample.",
            "Spanish": "Esta es una pequeña muestra de pronunciación.",
            "Polish": "To jest krótka próbka wymowy.",
        }
        language = self._language_var.get()
        sample_text = sample_by_language.get(language, "This is a short pronunciation sample.")
        provider_name = self._tts_provider_var.get()
        model_name = self._tts_model_var.get()
        voice_label = self._tts_voice_var.get()
        voice_value = self._selected_tts_voice()

        LOGGER.info(
            "TTS voice preview start: provider=%s model=%s voice_label=%s voice_value=%s language=%s",
            provider_name,
            model_name,
            voice_label,
            voice_value,
            language,
        )
        self._speech_progress_var.set(f"Previewing voice: {voice_label}...")
        self._root.update_idletasks()
        try:
            result = self._speech_service.generate(
                provider_name,
                sample_text,
                language,
                model_name,
                voice_value,
            )
        except Exception as exc:
            LOGGER.exception(
                "TTS voice preview failed: provider=%s model=%s voice_label=%s voice_value=%s",
                provider_name,
                model_name,
                voice_label,
                voice_value,
            )
            message = self._friendly_tts_error_message(exc)
            self._speech_progress_var.set(message)
            messagebox.showerror("TTS preview error", message)
            return

        self._speech_progress_var.set(f"Voice preview ready: {result.path.name}")
        self._record_activity(f"♪ Voice preview: {voice_label}")
        self._open_audio_file(result.path)

    def _load_speech_notes(self) -> None:
        """Load missing/malformed audio from all supported note types in the deck."""
        try:
            self._set_selected_deck()
            self._speech_notes = self._anki_client.list_existing_notes(
                search_query=self._speech_search_var.get().strip(),
                missing_audio_only=True,
            )
        except Exception as exc:
            LOGGER.exception("Speech/audio missing-audio scan failed")
            messagebox.showerror("Anki error", str(exc))
            return
        self._speech_audio_status_by_note_id = {}
        self._speech_audio_error_by_note_id = {}
        self._speech_audio_path_by_note_id = {}
        for note in self._speech_notes:
            note_id = int(note["note_id"])
            self._speech_audio_status_by_note_id[note_id] = str(note.get("audio_status") or "pending_audio")
        extra = self._speech_search_var.get().strip()
        suffix = f" · filter: {extra}" if extra else ""
        self._render_speech_notes(f"{len(self._speech_notes)} cards with missing/malformed audio{suffix}")

    def _render_speech_notes(self, progress_message: str | None = None) -> None:
        """Render the current existing-card audio list without reloading from Anki."""
        for widget in self._speech_scroll.winfo_children():
            widget.destroy()
        self._speech_note_vars = []
        for index, note in enumerate(self._speech_notes):
            note_id = int(note["note_id"])
            self._speech_audio_status_by_note_id.setdefault(
                note_id, str(note.get("audio_status") or "pending_audio")
            )
            status = self._speech_audio_status_by_note_id.get(note_id, "pending_audio")
            audio_field = str(note.get("audio_field") or "").strip()
            can_generate = bool(audio_field) and status not in {"audio_ready", "updated_in_anki", "skipped", "has_audio"}
            var = ctk.BooleanVar(value=can_generate)
            self._speech_note_vars.append(var)
            audio_label = audio_field or "no supported audio field"
            example = str(note.get("example") or "")
            label = f"[{status}] {note['word']} · {audio_label} — {example}"
            ctk.CTkCheckBox(self._speech_scroll, text=label, variable=var).grid(
                row=index, column=0, sticky="w", padx=12, pady=6
            )
        if progress_message is not None:
            self._speech_progress_var.set(progress_message)

    def _ensure_audio_autosave_path(self) -> Path:
        if self._speech_audio_autosave_path is None:
            autosave_dir = Path("batch_autosaves")
            autosave_dir.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._speech_audio_autosave_path = autosave_dir / f"audio_progress_{stamp}.json"
        return self._speech_audio_autosave_path

    def _audio_session_data(
        self,
        provider_name: str = "",
        model_name: str = "",
        voice_label: str = "",
        voice_value: str = "",
    ) -> dict[str, object]:
        notes_payload: list[dict[str, object]] = []
        for note in self._speech_notes:
            note_id = int(note["note_id"])
            notes_payload.append(
                {
                    "note_id": note_id,
                    "word": note.get("word", ""),
                    "example": note.get("example", ""),
                    "language": note.get("language", ""),
                    "audio_field": note.get("audio_field", "Audio"),
                    "status": self._speech_audio_status_by_note_id.get(note_id, "pending_audio"),
                    "audio_path": self._speech_audio_path_by_note_id.get(note_id, ""),
                    "error": self._speech_audio_error_by_note_id.get(note_id, ""),
                }
            )
        return {
            "kind": "existing_card_audio_progress",
            "provider": provider_name,
            "model": model_name,
            "voice_label": voice_label,
            "voice_value": voice_value,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "notes": notes_payload,
        }

    def _autosave_audio_progress(
        self,
        reason: str,
        provider_name: str = "",
        model_name: str = "",
        voice_label: str = "",
        voice_value: str = "",
    ) -> None:
        path = self._ensure_audio_autosave_path()
        try:
            path.write_text(
                json.dumps(
                    self._audio_session_data(provider_name, model_name, voice_label, voice_value),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            LOGGER.info("Audio progress autosaved: reason=%s path=%s", reason, path)
        except Exception:
            LOGGER.exception("Audio progress autosave failed: reason=%s", reason)

    def _pause_existing_audio_batch(self) -> None:
        if not self._speech_audio_running:
            self._speech_progress_var.set("No audio batch is currently running.")
            return
        self._speech_audio_pause_requested.set()
        self._autosave_audio_progress("audio paused")
        message = f"Audio paused. Progress saved: {self._speech_audio_autosave_path}"
        self._speech_progress_var.set(message)
        self._record_activity(message)

    def _stop_existing_audio_batch(self) -> None:
        if not self._speech_audio_running:
            self._speech_progress_var.set("No audio batch is currently running.")
            return
        self._speech_audio_stop_requested.set()
        self._speech_audio_pause_requested.clear()
        self._autosave_audio_progress("audio stopped")
        message = f"Audio stop requested. Progress saved: {self._speech_audio_autosave_path}"
        self._speech_progress_var.set(message)
        self._record_activity(message)

    def _generate_audio_for_existing(self) -> None:
        if self._speech_audio_running and self._speech_audio_pause_requested.is_set():
            self._speech_audio_pause_requested.clear()
            message = "Audio resumed."
            self._speech_progress_var.set(message)
            self._record_activity(message)
            return
        if self._speech_audio_running:
            self._speech_progress_var.set("Audio generation is already running.")
            return
        selected = [
            note for note, var in zip(self._speech_notes, self._speech_note_vars) if var.get()
        ]
        if not selected:
            messagebox.showwarning("No cards selected", "Select at least one card.")
            return
        if not self._speech_service or not self._tts_provider_var.get():
            messagebox.showerror("TTS unavailable", "Configure at least one TTS provider.")
            return
        provider_name = self._tts_provider_var.get()
        model_name = self._tts_model_var.get()
        voice_label = self._tts_voice_var.get()
        voice_value = self._selected_tts_voice()
        self._speech_audio_stop_requested.clear()
        self._speech_audio_pause_requested.clear()
        self._speech_audio_running = True
        self._speech_audio_autosave_path = None
        self._autosave_audio_progress("before audio generation", provider_name, model_name, voice_label, voice_value)
        self._speech_progress_var.set(f"Generating 0/{len(selected)}...")
        threading.Thread(
            target=self._existing_audio_worker,
            args=(selected, provider_name, model_name, voice_label, voice_value),
            daemon=True,
        ).start()

    @staticmethod
    def _http_status_from_exception(exc: Exception) -> int | None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)
        if isinstance(status_code, int):
            return status_code
        match = re.search(r"\b(400|401|402|403|404|422|429|5\d\d)\b", str(exc))
        return int(match.group(1)) if match else None

    @staticmethod
    def _is_fatal_tts_error(exc: Exception) -> bool:
        status = ModernVocabularyGui._http_status_from_exception(exc)
        return status in {401, 402, 403, 429} or (status is not None and 500 <= status <= 599) or ModernVocabularyGui._is_timeout_detail(str(exc))

    @staticmethod
    def _http_status_label(status: int | None) -> str:
        labels = {
            400: "400 Bad Request",
            401: "401 Unauthorized",
            402: "402 Payment Required",
            403: "403 Forbidden",
            404: "404 Not Found",
            422: "422 Unprocessable Entity",
            429: "429 Rate Limited",
        }
        if status is None:
            return ""
        if 500 <= status <= 599:
            return f"{status} Server Error"
        return labels.get(status, str(status))

    @staticmethod
    def _friendly_tts_error_message(exc: Exception) -> str:
        status = ModernVocabularyGui._http_status_from_exception(exc)
        if status == 401:
            return "TTS provider 401 Unauthorized. Check the API key or switch provider."
        if status == 402:
            return "TTS provider 402 payment/credits problem. Use a verified voice or switch provider."
        if status == 403:
            return "TTS provider 403 forbidden. The selected voice/model may not be allowed. Switch voice/provider."
        if status == 400:
            return "TTS provider 400 bad request. Check text/model/voice; this item was not retried automatically."
        if status == 404:
            return "TTS provider 404 not found. Check the configured model/voice or switch provider."
        if status == 422:
            return "TTS provider 422 could not process this item. Edit the input or switch provider."
        if status == 429:
            return "TTS provider rate limit. Wait before retrying or switch provider."
        if status is not None and 500 <= status <= 599:
            return "TTS provider server error. Progress was saved; retry later or switch provider."
        if ModernVocabularyGui._is_timeout_detail(str(exc)):
            return "TTS provider timed out. Progress was saved; retry later or switch provider."
        return "TTS error. Raw provider details were saved in logs/autosave."

    def _existing_audio_worker(
        self,
        notes: list[dict[str, object]],
        provider_name: str,
        model_name: str,
        voice_label: str,
        voice_value: str,
    ) -> None:
        completed = 0
        skipped_done = 0
        errors = 0
        stopped = False
        stop_message = ""
        failed_index = None
        stop_status = ""

        try:
            for index, note in enumerate(notes, start=1):
                if self._speech_audio_stop_requested.is_set():
                    stopped = True
                    failed_index = index
                    stop_message = "User stopped audio batch."
                    break

                while self._speech_audio_pause_requested.is_set():
                    self._autosave_audio_progress(
                        "audio paused",
                        provider_name,
                        model_name,
                        voice_label,
                        voice_value,
                    )
                    self._root.after(
                        0,
                        self._speech_progress_var.set,
                        f"Audio paused at item {index}/{len(notes)}. Progress saved: {self._speech_audio_autosave_path}",
                    )
                    if self._speech_audio_stop_requested.is_set():
                        stopped = True
                        failed_index = index
                        stop_message = "User stopped audio batch."
                        break
                    time.sleep(0.25)
                if stopped:
                    break

                note_id = int(note["note_id"])
                current_status = self._speech_audio_status_by_note_id.get(note_id, "pending_audio")
                audio_field = str(note.get("audio_field") or "").strip()
                example_text = str(note.get("example") or "").strip()
                if current_status in {"audio_ready", "updated_in_anki", "has_audio"}:
                    skipped_done += 1
                    self._root.after(
                        0,
                        self._speech_progress_var.set,
                        f"Skipping already generated {index}/{len(notes)} · Updated {completed} · Skipped {skipped_done} · Failed {errors}",
                    )
                    continue
                if not audio_field or not example_text:
                    skipped_done += 1
                    self._speech_audio_status_by_note_id[note_id] = "skipped"
                    self._speech_audio_error_by_note_id[note_id] = (
                        "Missing supported audio field." if not audio_field else "Missing example text for TTS."
                    )
                    self._root.after(
                        0,
                        self._speech_progress_var.set,
                        f"Skipping not-ready note {index}/{len(notes)} · Updated {completed} · Skipped {skipped_done} · Failed {errors}",
                    )
                    continue

                self._speech_audio_status_by_note_id[note_id] = "pending_audio"
                self._autosave_audio_progress(
                    f"before audio item {index}",
                    provider_name,
                    model_name,
                    voice_label,
                    voice_value,
                )
                try:
                    result = self._speech_service.generate(
                        provider_name,
                        str(note["example"]),
                        str(note["language"]),
                        model_name,
                        voice_value,
                    )
                    self._speech_audio_status_by_note_id[note_id] = "audio_ready"
                    self._speech_audio_path_by_note_id[note_id] = str(result.path)
                    LOGGER.info(
                        "Existing-card TTS ready: note_id=%s word=%s path=%s cached=%s provider=%s model=%s voice_label=%s voice_value=%s",
                        note.get("note_id"),
                        note.get("word"),
                        result.path,
                        result.cached,
                        provider_name,
                        model_name,
                        voice_label,
                        voice_value,
                    )
                    media_name = self._anki_client.store_media_file(result.path)
                    self._anki_client.attach_audio_to_note(note_id, media_name, audio_field)
                    self._speech_audio_status_by_note_id[note_id] = "updated_in_anki"
                    completed += 1
                except Exception as exc:
                    errors += 1
                    failed_index = index
                    stop_message = self._friendly_tts_error_message(exc)
                    http_status = self._http_status_from_exception(exc)
                    stop_status = self._http_status_label(http_status)
                    if not stop_status and self._is_timeout_detail(str(exc)):
                        stop_status = "timeout"
                    status = "provider_failed" if self._is_fatal_tts_error(exc) else "audio_error"
                    self._speech_audio_status_by_note_id[note_id] = status
                    self._speech_audio_error_by_note_id[note_id] = str(exc)
                    self._autosave_audio_progress(
                        f"audio error item {index}",
                        provider_name,
                        model_name,
                        voice_label,
                        voice_value,
                    )
                    LOGGER.exception(
                        "Existing-card audio generation/update failed: note_id=%s word=%s example=%s fatal=%s error=%s",
                        note.get("note_id"),
                        note.get("word"),
                        note.get("example"),
                        self._is_fatal_tts_error(exc),
                        exc,
                    )
                    if self._is_fatal_tts_error(exc):
                        stopped = True
                        LOGGER.warning(
                            "Stopping existing-card TTS batch after fatal provider error: provider=%s model=%s voice_label=%s voice_value=%s status=%s failed_index=%s note_id=%s",
                            provider_name,
                            model_name,
                            voice_label,
                            voice_value,
                            http_status,
                            index,
                            note_id,
                        )
                        break

                self._root.after(
                    0,
                    self._speech_progress_var.set,
                    f"Generating {index}/{len(notes)} · Updated {completed} · Skipped {skipped_done} · Failed {errors}",
                )

            self._autosave_audio_progress(
                "audio batch finished" if not stopped else "audio batch stopped",
                provider_name,
                model_name,
                voice_label,
                voice_value,
            )

            if stopped:
                if stop_message == "User stopped audio batch.":
                    final_message = (
                        f"Audio stopped by user at item {failed_index}. Progress saved. "
                        f"Summary: {completed} updated, {errors} failed, {skipped_done} skipped."
                    )
                else:
                    final_message = (
                        f"Audio stopped: {provider_name} {stop_status} at item {failed_index}. "
                        f"Progress saved. {stop_message}"
                    )
                self._root.after(0, self._render_speech_notes, final_message)
                self._root.after(0, self._record_activity, final_message)
                return

            final_message = f"Audio completed: {completed} updated, {errors} failed, {skipped_done} skipped."
            self._root.after(0, self._render_speech_notes, final_message)
            self._root.after(0, self._record_activity, final_message)
        finally:
            self._speech_audio_running = False
            self._speech_audio_pause_requested.clear()
            self._speech_audio_stop_requested.clear()

    def _analyze_grammar_sentence(self) -> None:
        """Generate and preview a sentence-first grammar analysis."""
        sentence = self._grammar_sentence_var.get().strip()
        if not sentence:
            messagebox.showerror("Missing sentence", "Enter a sentence to analyze.")
            return

        provider_name = self._provider_var.get()
        self._status_var.set(f"Analyzing grammar with {provider_name}...")
        self._root.update_idletasks()

        try:
            analysis = self._current_ai_client().analyze_grammar(
                sentence=sentence,
                target_language=self._language_var.get(),
            )
        except Exception as exc:
            self._status_var.set("Grammar analysis failed.")
            messagebox.showerror("Grammar error", str(exc))
            return

        self._generated_grammar = analysis
        self._generated_grammar_provider_name = provider_name
        self._set_grammar_preview(self._format_grammar_preview(analysis))
        self._status_var.set("Grammar analysis ready. Review it before adding to Anki.")

    def _set_grammar_preview(self, content: str) -> None:
        """Replace the read-only grammar preview content."""
        self._grammar_preview.configure(state="normal")
        self._grammar_preview.delete("1.0", "end")
        self._grammar_preview.insert("1.0", content)
        self._grammar_preview.configure(state="disabled")

    @staticmethod
    def _format_grammar_preview(analysis: GrammarAnalysis) -> str:
        """Format a grammar analysis for the desktop preview."""
        return (
            f"SENTENCE\n{analysis.sentence}\n\n"
            f"LANGUAGE\n{analysis.target_language} · grammar structure\n\n"
            f"MEANING\n{analysis.meaning}\n\n"
            f"STRUCTURE\n{analysis.structure}\n\n"
            f"HOW IT WORKS\n- " + "\n- ".join(analysis.breakdown) + "\n\n"
            f"WHEN TO USE IT\n{analysis.usage}\n\n"
            f"NATURAL CONTEXT\n{analysis.context_example}\n\n"
            f"CONTRAST\n- " + "\n- ".join(analysis.contrasts) + "\n\n"
            f"COMMON MISTAKES\n- " + "\n- ".join(analysis.common_mistakes)
        )

    def _add_grammar_card_to_anki(self) -> None:
        """Add the reviewed grammar analysis to Anki."""
        if self._generated_grammar is None:
            messagebox.showerror(
                "No grammar card",
                "Analyze a sentence before adding it to Anki.",
            )
            return

        provider_name = self._generated_grammar_provider_name or self._provider_var.get()
        try:
            deck = self._set_selected_deck()
            self._anki_client.add_grammar_card(
                self._generated_grammar,
                provider_name,
            )
        except DuplicateNoteError:
            replace = messagebox.askyesno(
                "Grammar card already exists",
                "A grammar card for this sentence already exists.\n\n"
                "Replace it with this reviewed version?",
            )
            if not replace:
                self._status_var.set("Existing grammar card was not changed.")
                return
            try:
                self._anki_client.update_grammar_card(self._generated_grammar, provider_name)
            except Exception as update_exc:
                self._status_var.set("Could not update the grammar card.")
                messagebox.showerror("Anki update error", str(update_exc))
                return
            deck = self._anki_client.deck_name
            self._status_var.set(
                f"✓ Updated grammar card in {deck}: {self._generated_grammar.sentence}"
            )
            self._record_activity("↻ Grammar card updated")
            self._grammar_sentence_var.set("")
            self._generated_grammar = None
            self._generated_grammar_provider_name = None
            return
        except Exception as exc:
            self._status_var.set("Could not add grammar card to Anki.")
            messagebox.showerror("Anki error", str(exc))
            return

        self._status_var.set(f"✓ Added grammar card to Anki deck {deck}: {self._generated_grammar.sentence}")
        self._record_activity("✓ Grammar card added")
        self._grammar_sentence_var.set("")
        self._generated_grammar = None
        self._generated_grammar_provider_name = None

    def _start_conversation_topic(self) -> None:
        """Start a new conversation topic using the shared AI client interface."""
        topic = self._topic_var.get().strip()
        if not topic:
            messagebox.showerror("Missing topic", "Enter a conversation topic first.")
            return

        provider_name = self._provider_var.get()
        self._conversation_history.clear()
        self._conversation_question = None
        self._clear_chat()
        self._append_chat("TOPIC", topic)
        self._status_var.set(f"Starting conversation with {provider_name}...")
        self._root.update_idletasks()

        try:
            start = self._current_ai_client().start_conversation(
                topic=topic,
                target_language=self._language_var.get(),
            )
        except Exception as exc:
            self._status_var.set("Conversation start failed.")
            messagebox.showerror("Conversation error", str(exc))
            return

        self._conversation_question = start.question
        self._append_chat("AI TUTOR", start.question)
        self._status_var.set("Conversation started. Write your answer and send it.")

    def _send_conversation_message(self) -> None:
        """Send the learner answer, request feedback, and continue the conversation."""
        if not self._conversation_question:
            messagebox.showerror("No conversation", "Start a conversation topic first.")
            return

        answer = self._message_input.get("1.0", "end").strip()
        if not answer:
            return

        self._message_input.delete("1.0", "end")
        self._append_chat("YOU", answer)

        provider_name = self._provider_var.get()
        self._status_var.set(f"Reviewing answer with {provider_name}...")
        self._root.update_idletasks()
        try:
            feedback = self._current_ai_client().review_conversation_answer(
                topic=self._topic_var.get().strip(),
                question=self._conversation_question,
                answer=answer,
                target_language=self._language_var.get(),
                improvement_level=self._improvement_level_var.get(),
            )
        except Exception as exc:
            self._status_var.set("Conversation reply failed.")
            messagebox.showerror("Conversation error", str(exc))
            return

        self._conversation_history.append(("user", answer))
        self._conversation_history.append(("ai", feedback.advanced_answer))
        self._append_conversation_feedback(feedback)
        self._conversation_question = feedback.next_question
        self._render_suggestions(feedback.suggested_vocabulary)
        self._status_var.set("Feedback ready. Select expressions or continue the conversation.")

    def _build_history_text(self, max_turns: int = 8) -> str:
        recent = self._conversation_history[-max_turns:]
        return "\n".join(f"{speaker}: {message}" for speaker, message in recent)

    def _append_conversation_feedback(self, feedback: ConversationFeedback) -> None:
        """Render AI feedback and the next question in the chat panel."""
        self._append_chat("FEEDBACK", feedback.feedback_pl)
        self._append_chat("CORRECTED VERSION", feedback.corrected_version)
        self._append_chat("STRONGER ANSWER", feedback.advanced_answer)
        self._append_chat("AI TUTOR", feedback.next_question)

    def _append_chat(self, speaker: str, text: str) -> None:
        self._chat_text.configure(state="normal")
        self._chat_text.insert("end", f"\n{speaker}\n{text}\n")
        self._chat_text.see("end")
        self._chat_text.configure(state="disabled")

    def _clear_chat(self) -> None:
        self._chat_text.configure(state="normal")
        self._chat_text.delete("1.0", "end")
        self._chat_text.configure(state="disabled")

    def _render_suggestions(self, suggestions: list[str]) -> None:
        for widget in self._suggestions_frame.winfo_children():
            widget.destroy()
        self._latest_suggestions = suggestions
        self._suggestion_vars = []
        if not suggestions:
            ctk.CTkLabel(
                self._suggestions_frame,
                text="No suggestions yet. Start or continue the conversation.",
                text_color=("gray35", "gray75"),
                wraplength=330,
            ).pack(anchor="w", padx=8, pady=8)
            return
        for expression in suggestions:
            var = ctk.BooleanVar(value=True)
            self._suggestion_vars.append(var)
            ctk.CTkCheckBox(
                self._suggestions_frame,
                text=expression,
                variable=var,
                wraplength=330,
            ).pack(anchor="w", fill="x", padx=8, pady=5)

    def _add_selected_suggestions_to_queue(self) -> None:
        selected = [
            expression
            for expression, var in zip(self._latest_suggestions, self._suggestion_vars)
            if var.get()
        ]
        self._add_phrases_to_queue(selected)

    def _add_all_suggestions_to_queue(self) -> None:
        self._add_phrases_to_queue(self._latest_suggestions)

    def _add_custom_phrase_to_queue(self) -> None:
        phrase = self._custom_phrase_var.get().strip()
        if not phrase:
            return
        self._add_phrases_to_queue([phrase])
        self._custom_phrase_var.set("")

    def _add_phrases_to_queue(self, phrases: list[str]) -> None:
        added = 0
        existing_lower = {item.lower() for item in self._flashcard_queue}
        for phrase in phrases:
            cleaned = phrase.strip()
            if cleaned and cleaned.lower() not in existing_lower:
                self._flashcard_queue.append(cleaned)
                existing_lower.add(cleaned.lower())
                added += 1
        self._refresh_queue_text()
        self._status_var.set(f"Added {added} expression(s) to the flashcard queue.")

    def _refresh_queue_text(self) -> None:
        self._queue_text.configure(state="normal")
        self._queue_text.delete("1.0", "end")
        if not self._flashcard_queue:
            self._queue_text.insert("1.0", "Queue is empty.")
        else:
            self._queue_text.insert(
                "1.0",
                "\n".join(f"{idx}. {item}" for idx, item in enumerate(self._flashcard_queue, start=1)),
            )
        self._queue_text.configure(state="disabled")

    def _clear_queue(self) -> None:
        self._flashcard_queue.clear()
        self._refresh_queue_text()
        self._status_var.set("Flashcard queue cleared.")

    def _generate_queue_and_add_to_anki(self) -> None:
        if not self._flashcard_queue:
            messagebox.showerror("Empty queue", "Add at least one expression to the queue first.")
            return
        try:
            deck = self._set_selected_deck()
        except Exception as exc:
            messagebox.showerror("Missing deck", str(exc))
            return

        provider_name = self._provider_var.get()
        target_language = self._language_var.get()
        added = 0
        failed: list[str] = []

        for phrase in list(self._flashcard_queue):
            self._status_var.set(f"Generating and adding: {phrase}")
            self._root.update_idletasks()
            try:
                card = self._current_ai_client().generate_card(
                    phrase, target_language, self._explanation_language_var.get()
                )
                if not card.is_valid:
                    detail = card.validation_error or "Invalid word or phrase."
                    if card.suggested_correction:
                        detail += f" Suggested correction: {card.suggested_correction}"
                    raise ValueError(detail)
                try:
                    self._anki_client.add_card(card, provider_name=provider_name)
                except DuplicateNoteError:
                    replace = messagebox.askyesno(
                        "Card already exists",
                        f"A card for '{phrase}' already exists. Replace it?",
                    )
                    if not replace:
                        raise ValueError("Existing card was not changed.")
                    self._anki_client.update_card(card, provider_name=provider_name)
                added += 1
            except Exception as exc:
                failed.append(f"{phrase}: {exc}")

        if failed:
            self._status_var.set(f"Added {added} card(s), {len(failed)} failed.")
            messagebox.showwarning("Finished with errors", "\n\n".join(failed[:5]))
        else:
            self._status_var.set(f"✓ Added {added} card(s) to Anki deck: {deck}")
            self._record_activity(f"✓ {added} queued card(s) added")
            self._clear_queue()

    def _reset_conversation(self) -> None:
        self._conversation_history.clear()
        self._conversation_question = None
        self._latest_suggestions = []
        self._suggestion_vars = []
        self._clear_chat()
        self._chat_text.configure(state="normal")
        self._chat_text.insert("1.0", "Choose a topic and click Start topic. Then continue the conversation here.\n")
        self._chat_text.configure(state="disabled")
        self._render_suggestions([])
        self._status_var.set("Conversation reset.")
