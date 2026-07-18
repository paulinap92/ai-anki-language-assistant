"""Modern CustomTkinter GUI for the AI Anki Vocabulary Generator.

This module keeps the existing application logic and adds a modern interface with
both the single flashcard generator and Conversation Practice workflow.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import subprocess
import sys
import threading
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
        self._speech_progress_var = ctk.StringVar(value="Load existing cards with missing audio.")

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
        self._batch_progress_var = ctk.StringVar(value="No list loaded.")
        self._batch_status_var = ctk.StringVar(value="Load a TXT/CSV file or paste a list.")
        self._batch_autosave_path: Path | None = None
        self._batch_auto_generate_running = False
        self._batch_add_all_running = False
        self._batch_add_all_indexes: list[int] = []
        self._batch_add_all_position = 0
        self._batch_add_all_duplicate_policy: bool | None = None
        self._batch_add_all_existing_notes: dict[str, int] = {}
        self._batch_add_all_counts = {"added": 0, "updated": 0, "duplicates": 0, "failed": 0}
        self._activity_var = ctk.StringVar(value="")

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

        self._build_single_flashcard_tab(tabs.tab("Single flashcard"))
        self._build_grammar_tab(tabs.tab("Grammar"))
        self._build_conversation_tab(tabs.tab("Conversation Practice"))
        self._build_batch_tab(tabs.tab("Batch / Queue"))
        self._build_practice_tab(tabs.tab("Practice & Print"))
        self._build_speech_tab(tabs.tab("Speech / Audio"))

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
        left.grid_rowconfigure(5, weight=1)

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

        session_buttons = ctk.CTkFrame(left, fg_color="transparent")
        session_buttons.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 8))
        session_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(session_buttons, text="Save session", command=self._save_batch_session).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(session_buttons, text="Resume session", command=self._resume_batch_session).grid(
            row=0, column=1, sticky="ew", padx=(5, 0)
        )
        ctk.CTkButton(left, text="Clear batch", command=self._clear_batch).grid(
            row=7, column=0, sticky="ew", padx=18, pady=(0, 18)
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
            command=self._generate_current_batch_card,
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
        self._batch_preview.configure(state="disabled")

        buttons = ctk.CTkFrame(right, fg_color="transparent")
        buttons.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 18))
        buttons.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        ctk.CTkButton(buttons, text="Previous", command=self._batch_previous).grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )
        ctk.CTkButton(buttons, text="Skip", command=self._skip_current_batch_item).grid(
            row=0, column=1, sticky="ew", padx=4
        )
        ctk.CTkButton(buttons, text="Add to Anki", command=self._add_current_batch_card).grid(
            row=0, column=2, sticky="ew", padx=4
        )
        ctk.CTkButton(buttons, text="Regenerate", command=self._generate_current_batch_card).grid(
            row=0, column=3, sticky="ew", padx=4
        )
        ctk.CTkButton(buttons, text="Next", command=self._batch_next).grid(
            row=0, column=4, sticky="ew", padx=(4, 0)
        )

        bulk_buttons = ctk.CTkFrame(right, fg_color="transparent")
        bulk_buttons.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 18))
        bulk_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            bulk_buttons,
            text="Auto-generate pending",
            command=self._auto_generate_pending_batch_cards,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(
            bulk_buttons,
            text="Add all ready",
            command=self._start_add_all_ready_batch_cards,
        ).grid(row=0, column=1, sticky="ew", padx=(5, 0))

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
        self._batch_items = [{"word": word, "status": "pending"} for word in clean_words]
        self._batch_index = 0
        self._batch_autosave_path = None
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        self._show_current_batch_item(generate=True)
        self._record_activity(f"Loaded {len(clean_words)} batch item(s)")
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
        self._batch_word_var.set(str(item["word"]))
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        stored_card = self._card_from_batch_payload(item.get("card"))
        if stored_card is not None:
            self._batch_generated_card = stored_card
            self._batch_generated_provider_name = str(item.get("provider_name") or self._provider_var.get())
        self._update_batch_progress()
        if stored_card is not None:
            self._set_batch_preview(self._format_card_preview(stored_card, audio_status=item.get("audio_status")))
        else:
            self._set_batch_status_card(
                title="BATCH ITEM",
                word=str(item.get("word", "")),
                status=str(item.get("status", "pending")),
                detail=str(item.get("error", "")),
            )
        if generate and item["status"] not in {"added", "skipped", "error", "invalid", "rate_limited"}:
            self._generate_current_batch_card()

    def _update_batch_progress(self) -> None:
        total = len(self._batch_items)
        counts = {name: 0 for name in ("added", "skipped", "invalid", "pending", "ready")}
        for item in self._batch_items:
            status = str(item.get("status", "pending"))
            counts[status] = counts.get(status, 0) + 1
        current = self._batch_index + 1 if total else 0
        remaining = counts.get("pending", 0) + counts.get("ready", 0)
        self._batch_progress_var.set(
            f"{current}/{total} · Added {counts.get('added', 0)} · "
            f"Skipped {counts.get('skipped', 0)} · Invalid {counts.get('invalid', 0)} · "
            f"Remaining {remaining}"
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

    def _stop_batch_on_rate_limit(self, word: str, detail: str) -> None:
        """Stop Auto Batch and keep one stable UI state after provider rate limits."""
        self._batch_auto_generate_running = False
        self._autosave_batch_session(f"rate limit: {word}")
        autosave = str(self._batch_autosave_path) if self._batch_autosave_path else "not available"
        message = (
            "Auto Batch stopped: provider rate limit. "
            "The session was autosaved. Resume later or switch provider."
        )
        self._batch_status_var.set(f"{message} Autosave: {autosave}")
        self._status_var.set(message)
        self._set_batch_status_card(
            title="AUTO BATCH STOPPED",
            word=word,
            status="rate_limited",
            detail=f"{detail}\n\nAutosave: {autosave}",
            actions=(
                "- Wait and resume later\n"
                "- Add all ready cards now\n"
                "- Switch provider and regenerate pending items later"
            ),
        )
        self._record_activity("Auto Batch stopped: rate limit")
        LOGGER.warning("Auto Batch stopped because of rate limit for word=%s detail=%s", word, detail)

    def _generate_current_batch_card(self) -> None:
        if not self._batch_items:
            messagebox.showerror("No list", "Load a vocabulary list first.")
            return
        word = self._batch_word_var.get().strip()
        if not word:
            messagebox.showerror("Missing word", "Enter a word or phrase.")
            return
        item = self._batch_items[self._batch_index]
        item["word"] = word
        provider_name = self._provider_var.get()
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
            )
        except Exception as exc:
            detail = str(exc)
            item["status"] = "error"
            item["error"] = detail
            self._batch_generated_card = None
            if "429" in detail or "Too Many Requests" in detail:
                item["status"] = "rate_limited"
                message = f"Rate limit while generating: {word}. Session autosaved."
                self._batch_status_var.set(message)
                self._update_batch_progress()
                self._stop_batch_on_rate_limit(word, detail)
            else:
                message = f"Generation error: {word} — {exc}"
                self._batch_status_var.set(message)
                self._set_batch_status_card("GENERATION ERROR", word, "error", detail)
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
        self._batch_generated_card = card
        self._batch_generated_provider_name = provider_name
        self._set_batch_preview(self._format_card_preview(card))
        self._batch_status_var.set(f"Ready to review: {word}")
        self._status_var.set(self._batch_status_var.get())
        self._update_batch_progress()
        self._autosave_batch_session(f"generated: {word}")

    def _add_current_batch_card(self) -> None:
        if self._batch_generated_card is None:
            messagebox.showerror("No card", "Generate and review the current card first.")
            return
        provider_name = self._batch_generated_provider_name or self._provider_var.get()
        try:
            deck = self._set_selected_deck()
            self._anki_client.add_card(
                self._batch_generated_card,
                provider_name,
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
                self._anki_client.update_card(self._batch_generated_card, provider_name)
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
            self._show_current_batch_item(generate=True)
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
            self._show_current_batch_item(generate=True)

    def _clear_batch(self) -> None:
        self._batch_items.clear()
        self._batch_index = 0
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        self._batch_autosave_path = None
        self._batch_auto_generate_running = False
        self._batch_add_all_running = False
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
            "audio": card.audio,
        }

    @staticmethod
    def _normalise_anki_value(value: str) -> str:
        """Normalize a value for exact duplicate checks."""
        import html
        plain = re.sub(r"<[^>]+>", "", html.unescape(value or ""))
        return " ".join(plain.split()).casefold()

    def _auto_generate_pending_batch_cards(self) -> None:
        """Generate pending Batch cards one by one using Tk after()."""
        if self._batch_auto_generate_running:
            self._batch_status_var.set("Auto-generation is already running.")
            return
        if not self._batch_items:
            messagebox.showerror("No list", "Load a vocabulary list first.")
            return

        self._batch_auto_generate_running = True
        self._record_activity("Auto-generation started")
        self._autosave_batch_session("before auto-generation")
        self._root.after(50, self._auto_generate_next_pending_batch_card)

    def _auto_generate_next_pending_batch_card(self) -> None:
        """Generate the next pending Batch card and schedule the following one."""
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
            self._generate_current_batch_card()
        except Exception as exc:
            LOGGER.exception("Auto-generation failed for %s", word)
            item = self._batch_items[next_index]
            item["status"] = "error"
            item["error"] = str(exc)
            self._autosave_batch_session(f"auto-generation exception: {word}")

            if "429" in str(exc) or "Too Many Requests" in str(exc):
                item["status"] = "rate_limited"
                self._stop_batch_on_rate_limit(word, str(exc))
                return

        current_item = self._batch_items[next_index]
        current_status = str(current_item.get("status"))
        if current_status == "rate_limited":
            self._stop_batch_on_rate_limit(word, str(current_item.get("error", "Provider rate limit.")))
            return
        if current_status == "error":
            # A failed item must not be retried immediately. It remains for manual review.
            LOGGER.info("Skipping failed batch item after one attempt: %s", word)

        self._root.after(1600, self._auto_generate_next_pending_batch_card)

    def _start_add_all_ready_batch_cards(self) -> None:
        """Start safe step-by-step adding of all ready Batch cards."""
        if self._batch_add_all_running:
            self._batch_status_var.set("Add all ready is already running.")
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
        self._autosave_batch_session("before add all ready")
        self._record_activity(f"Add all ready started: {len(indexes)} cards")
        LOGGER.info("Add all ready started: ready=%s", len(indexes))
        self._root.after(50, self._add_next_ready_batch_card)

    def _add_next_ready_batch_card(self) -> None:
        """Add one ready Batch card, then schedule the next one."""
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
                    self._anki_client.update_card_by_note_id(existing_note_id, card, provider_name)
                    item["status"] = "added"
                    self._batch_add_all_counts["updated"] += 1
                else:
                    item["status"] = "duplicate"
                    item["error"] = "Existing Anki card was not updated."
                    self._batch_add_all_counts["duplicates"] += 1
            else:
                self._anki_client.add_card_without_duplicate_scan(card, provider_name)
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

    def _build_speech_tab(self, parent: ctk.CTkFrame) -> None:
        """Build TTS controls for new and existing vocabulary cards."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(2, weight=1)

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

        actions = ctk.CTkFrame(frame, corner_radius=18)
        actions.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(actions, text="Load cards with missing audio", command=self._load_speech_notes).pack(side="left", padx=16, pady=14)
        ctk.CTkButton(actions, text="Select all", command=lambda: [v.set(True) for v in self._speech_note_vars]).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkButton(actions, text="Generate audio for selected", command=self._generate_audio_for_existing).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkLabel(actions, textvariable=self._speech_progress_var).pack(side="right", padx=16, pady=14)

        self._speech_scroll = ctk.CTkScrollableFrame(frame, corner_radius=18)
        self._speech_scroll.grid(row=2, column=0, sticky="nsew")
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
            self._status_var.set("Card generation failed.")
            messagebox.showerror("Generation error", str(exc))
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

    def _load_speech_notes(self) -> None:
        try:
            self._set_selected_deck()
            self._speech_notes = self._anki_client.list_vocabulary_notes_for_audio(
                missing_only=True
            )
        except Exception as exc:
            messagebox.showerror("Anki error", str(exc))
            return
        for widget in self._speech_scroll.winfo_children():
            widget.destroy()
        self._speech_note_vars = []
        for index, note in enumerate(self._speech_notes):
            var = ctk.BooleanVar(value=True)
            self._speech_note_vars.append(var)
            label = f"{note['word']} — {note['example']}"
            ctk.CTkCheckBox(self._speech_scroll, text=label, variable=var).grid(
                row=index, column=0, sticky="w", padx=12, pady=6
            )
        self._speech_progress_var.set(
            f"{len(self._speech_notes)} cards without audio"
        )

    def _generate_audio_for_existing(self) -> None:
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
        match = re.search(r"\b(401|402|403|429|5\d\d)\b", str(exc))
        return int(match.group(1)) if match else None

    @staticmethod
    def _is_fatal_tts_error(exc: Exception) -> bool:
        return ModernVocabularyGui._http_status_from_exception(exc) in {401, 402, 403, 429}

    @staticmethod
    def _friendly_tts_error_message(exc: Exception) -> str:
        status = ModernVocabularyGui._http_status_from_exception(exc)
        if status == 401:
            return "ElevenLabs API key was rejected. Check the API key or switch provider."
        if status == 402:
            return "ElevenLabs payment/credits/voice access problem. Use a verified voice or switch provider."
        if status == 403:
            return "The selected ElevenLabs voice or model is not allowed on this account. Switch voice/provider."
        if status == 429:
            return "TTS provider rate limit. Wait before retrying or switch provider."
        return f"TTS error: {exc}"

    def _existing_audio_worker(
        self,
        notes: list[dict[str, object]],
        provider_name: str,
        model_name: str,
        voice_label: str,
        voice_value: str,
    ) -> None:
        completed = 0
        errors = 0
        stopped = False
        stop_message = ""
        for index, note in enumerate(notes, start=1):
            try:
                result = self._speech_service.generate(
                    provider_name,
                    str(note["example"]),
                    str(note["language"]),
                    model_name,
                    voice_value,
                )
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
                self._anki_client.attach_audio_to_note(int(note["note_id"]), media_name)
                completed += 1
            except Exception as exc:
                errors += 1
                stop_message = self._friendly_tts_error_message(exc)
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
                        "Stopping existing-card TTS batch after fatal provider error: provider=%s model=%s voice_label=%s voice_value=%s status=%s",
                        provider_name,
                        model_name,
                        voice_label,
                        voice_value,
                        self._http_status_from_exception(exc),
                    )
                    break
            self._root.after(
                0, self._speech_progress_var.set,
                f"Generating {index}/{len(notes)} · Added {completed} · Errors {errors}",
            )
        if stopped:
            final_message = (
                f"Stopped after fatal TTS error. Added {completed}. Errors {errors}. "
                f"{stop_message} See logs/ai_anki_app.log"
            )
            self._root.after(0, self._speech_progress_var.set, final_message)
            self._root.after(0, self._record_activity, final_message)
            return
        self._root.after(0, self._load_speech_notes)
        self._root.after(
            0,
            self._record_activity,
            f"♪ Audio added to {completed} cards · Errors {errors} · See logs/ai_anki_app.log",
        )

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
