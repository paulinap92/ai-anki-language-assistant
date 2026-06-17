"""Modern CustomTkinter GUI for the AI Anki Vocabulary Generator.

This module keeps the existing application logic and adds a modern interface with
both the single flashcard generator and Conversation Practice workflow.
"""

from __future__ import annotations

import csv
import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from src.ai.base import VocabularyAiClient
from src.anki.client import AnkiClient
from src.domain.languages import LANGUAGE_TAGS
from src.domain.models import ConversationFeedback, GrammarAnalysis, VocabularyCard


EXPLANATION_LANGUAGES = ["Polish", "English", "Spanish", "German", "Italian", "No translation"]
IMPROVEMENT_LEVELS = ["Natural B1/B2", "Strong B2/C1", "Professional / Interview"]


class ModernVocabularyGui:
    """Modern desktop GUI for vocabulary cards and conversation practice."""

    def __init__(
        self,
        root: ctk.CTk,
        ai_clients: dict[str, VocabularyAiClient],
        anki_client: AnkiClient,
        default_target_language: str,
    ) -> None:
        self._root = root
        self._ai_clients = ai_clients
        self._anki_client = anki_client

        self._provider_var = ctk.StringVar(value=next(iter(ai_clients)))
        self._language_var = ctk.StringVar(value=default_target_language)
        self._explanation_language_var = ctk.StringVar(value="Polish")
        self._improvement_level_var = ctk.StringVar(value="Strong B2/C1")
        self._deck_var = ctk.StringVar(value=anki_client.deck_name)
        self._status_var = ctk.StringVar(value="Ready. Open Anki and choose a deck.")

        self._word_var = ctk.StringVar()
        self._generated_card: VocabularyCard | None = None
        self._generated_provider_name: str | None = None

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
        self._activity_var = ctk.StringVar(value="")

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
        tabs.tab("Single flashcard").grid_columnconfigure(0, weight=1)
        tabs.tab("Single flashcard").grid_rowconfigure(0, weight=1)
        tabs.tab("Grammar").grid_columnconfigure(0, weight=1)
        tabs.tab("Grammar").grid_rowconfigure(0, weight=1)
        tabs.tab("Conversation Practice").grid_columnconfigure(0, weight=1)
        tabs.tab("Conversation Practice").grid_rowconfigure(0, weight=1)
        tabs.tab("Batch / Queue").grid_columnconfigure(0, weight=1)
        tabs.tab("Batch / Queue").grid_rowconfigure(0, weight=1)

        self._build_single_flashcard_tab(tabs.tab("Single flashcard"))
        self._build_grammar_tab(tabs.tab("Grammar"))
        self._build_conversation_tab(tabs.tab("Conversation Practice"))
        self._build_batch_tab(tabs.tab("Batch / Queue"))

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
        ctk.CTkButton(
            left,
            text="Add reviewed card to Anki",
            height=42,
            command=self._add_single_card_to_anki,
        ).grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 18))

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
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        self._show_current_batch_item(generate=True)
        self._record_activity(f"Loaded {len(clean_words)} batch item(s)")

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
        self._update_batch_progress()
        self._set_batch_preview(
            f"WORD / PHRASE\n{item['word']}\n\nStatus: {item['status']}"
        )
        if generate and item["status"] not in {"added", "skipped"}:
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
            item["status"] = "invalid"
            item["error"] = str(exc)
            self._batch_generated_card = None
            self._batch_status_var.set(f"Invalid: {word} — {exc}")
            self._set_batch_preview(f"WORD / PHRASE\n{word}\n\nERROR\n{exc}")
            self._update_batch_progress()
            return
        if not card.is_valid:
            item["status"] = "invalid"
            detail = card.validation_error or "Invalid word or phrase."
            if card.suggested_correction:
                detail += f" Suggested correction: {card.suggested_correction}"
            item["error"] = detail
            self._batch_generated_card = None
            self._batch_status_var.set(f"Invalid: {word}")
            self._set_batch_preview(
                f"WORD / PHRASE\n{word}\n\nVALIDATION ERROR\n{detail}"
            )
            self._update_batch_progress()
            return
        item["status"] = "ready"
        item.pop("error", None)
        self._batch_generated_card = card
        self._batch_generated_provider_name = provider_name
        self._set_batch_preview(self._format_card_preview(card))
        self._batch_status_var.set(f"Ready to review: {word}")
        self._status_var.set(self._batch_status_var.get())
        self._update_batch_progress()

    def _add_current_batch_card(self) -> None:
        if self._batch_generated_card is None:
            messagebox.showerror("No card", "Generate and review the current card first.")
            return
        try:
            deck = self._set_selected_deck()
            self._anki_client.add_card(
                self._batch_generated_card,
                self._batch_generated_provider_name or self._provider_var.get(),
            )
        except Exception as exc:
            self._batch_status_var.set(f"Could not add card: {exc}")
            messagebox.showerror("Anki error", str(exc))
            return
        word = self._batch_generated_card.word_or_phrase
        self._batch_items[self._batch_index]["status"] = "added"
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
        self._show_current_batch_item()
        self._set_batch_preview("Load a list to start reviewing cards.")
        self._record_activity("Batch cleared")

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
        data = {
            "items": self._batch_items,
            "index": self._batch_index,
            "provider": self._provider_var.get(),
            "target_language": self._language_var.get(),
            "explanation_language": self._explanation_language_var.get(),
            "deck": self._deck_var.get(),
        }
        try:
            Path(filename).write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            messagebox.showerror("Save error", str(exc))
            return
        self._record_activity("Batch session saved")
        self._batch_status_var.set("Batch session saved.")

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
    def _format_card_preview(card: VocabularyCard) -> str:
        return (
            f"WORD / PHRASE\n{card.word_or_phrase}\n\n"
            f"LANGUAGE\n{card.target_language} · {card.part_of_speech}\n\n"
            f"DEFINITION\n{card.definition}\n\n"
            f"EXPLANATION LANGUAGE\n{card.explanation_language}\n\n"
            f"TRANSLATION\n{card.translation_pl or '—'}\n\n"
            f"EXAMPLE\n{card.example}\n{card.example_pl or '—'}\n\n"
            f"SYNONYMS / ALTERNATIVES\n{', '.join(card.synonyms)}\n\n"
            f"COLLOCATIONS / USAGE\n- " + "\n- ".join(card.collocations) + "\n\n"
            f"GRAMMAR NOTE\n{card.grammar_note}"
        )

    def _add_single_card_to_anki(self) -> None:
        if self._generated_card is None:
            messagebox.showerror("No card", "Generate a card before adding it to Anki.")
            return
        try:
            deck = self._set_selected_deck()
            self._anki_client.add_card(self._generated_card, self._generated_provider_name or self._provider_var.get())
        except Exception as exc:
            self._status_var.set("Could not add card to Anki.")
            messagebox.showerror("Anki error", str(exc))
            return
        self._status_var.set(f"✓ Added to Anki deck {deck}: {self._generated_card.word_or_phrase}")
        self._record_activity(f"✓ {self._generated_card.word_or_phrase} added")
        self._word_var.set("")
        self._generated_card = None
        self._generated_provider_name = None

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

        try:
            deck = self._set_selected_deck()
            self._anki_client.add_grammar_card(
                self._generated_grammar,
                self._generated_grammar_provider_name or self._provider_var.get(),
            )
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
                self._anki_client.add_card(card, provider_name=provider_name)
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
