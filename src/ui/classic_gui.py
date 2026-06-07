"""Tkinter interface for the AI language learning application."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from src.anki.client import AnkiClient
from src.ai.base import VocabularyAiClient
from src.domain.languages import LANGUAGE_TAGS
from src.domain.models import ConversationFeedback, VocabularyCard


IMPROVEMENT_LEVELS = [
    "Natural B1/B2",
    "Strong B2/C1",
    "Professional / Interview",
]

BG = "#F5F7FB"
SURFACE = "#FFFFFF"
TEXT = "#22324A"
MUTED = "#65748B"
ACCENT = "#2F6FE4"
ACCENT_HOVER = "#245BBE"
BORDER = "#DDE5F0"
INPUT_BG = "#FFFFFF"
SELECTION = "#DCEAFF"


class VocabularyGui:
    """Desktop user interface for flashcards and conversation practice."""

    def __init__(
        self,
        root: tk.Tk,
        ai_clients: dict[str, VocabularyAiClient],
        anki_client: AnkiClient,
        default_target_language: str,
    ) -> None:
        """Initialize the application window."""
        self._root = root
        self._ai_clients = ai_clients
        self._anki_client = anki_client

        self._generated_card: VocabularyCard | None = None
        self._generated_provider_name: str | None = None
        self._conversation_question: str | None = None
        self._conversation_feedback: ConversationFeedback | None = None

        default_provider = next(iter(ai_clients))
        self._provider_var = tk.StringVar(value=default_provider)
        self._language_var = tk.StringVar(value=default_target_language)
        self._deck_var = tk.StringVar(value=anki_client.deck_name)
        self._word_var = tk.StringVar()
        self._flashcard_status_var = tk.StringVar(
            value="Open Anki, choose a language and generate a card."
        )

        self._conversation_provider_var = tk.StringVar(value=default_provider)
        self._conversation_language_var = tk.StringVar(value=default_target_language)
        self._improvement_level_var = tk.StringVar(value="Strong B2/C1")
        self._topic_var = tk.StringVar()
        self._conversation_status_var = tk.StringVar(
            value="Choose a language, enter your own topic and start practising."
        )
        self._custom_vocabulary_var = tk.StringVar()
        self._conversation_deck_var = tk.StringVar(value=anki_client.deck_name)

        self._configure_window()
        self._build_widgets()
        self._load_decks()

    def _configure_window(self) -> None:
        """Configure the main window."""
        self._root.title("LingoCards · AI Learning Assistant")
        self._root.geometry("1060x860")
        self._root.minsize(820, 650)
        self._root.configure(background=BG)
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)
        self._configure_styles()

    def _configure_styles(self) -> None:
        """Apply a calm, light visual style without changing application flow."""
        style = ttk.Style(self._root)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background=BG, foreground=TEXT)
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("TLabelframe", background=BG, foreground=TEXT)
        style.configure("TLabelframe.Label", background=BG, foreground=TEXT)
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 22), foreground=TEXT)
        style.configure("Subheader.TLabel", font=("Segoe UI", 10), foreground=MUTED)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            padding=(18, 11),
            background="#E9EEF7",
            foreground=MUTED,
            font=("Segoe UI Semibold", 10),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", SURFACE)],
            foreground=[("selected", ACCENT)],
        )
        style.configure(
            "TButton",
            background="#E9EEF7",
            foreground=TEXT,
            padding=(12, 8),
            borderwidth=0,
            font=("Segoe UI Semibold", 10),
        )
        style.map("TButton", background=[("active", "#DCE5F3")])
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#FFFFFF",
            padding=(14, 9),
            borderwidth=0,
            font=("Segoe UI Semibold", 10),
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_HOVER), ("disabled", "#A7BDE7")],
        )
        style.configure(
            "TEntry",
            padding=8,
            fieldbackground=INPUT_BG,
            background=INPUT_BG,
            foreground=TEXT,
            insertcolor=TEXT,
            bordercolor=BORDER,
        )
        style.configure(
            "TCombobox",
            padding=7,
            fieldbackground=INPUT_BG,
            background=INPUT_BG,
            foreground=TEXT,
            selectforeground=TEXT,
            selectbackground=SELECTION,
            bordercolor=BORDER,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", INPUT_BG)],
            foreground=[("readonly", TEXT)],
            selectforeground=[("readonly", TEXT)],
            selectbackground=[("readonly", INPUT_BG)],
        )

    def _build_widgets(self) -> None:
        """Create the tabbed interface."""
        container = ttk.Frame(self._root, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        ttk.Label(
            container,
            text="LingoCards",
            style="Header.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            container,
            text="Conversation practice and full AI vocabulary cards for Anki",
            style="Subheader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 18))

        self._notebook = ttk.Notebook(container)
        self._notebook.grid(row=2, column=0, sticky="nsew")

        self._flashcard_tab = ttk.Frame(self._notebook, padding=18)
        self._conversation_tab = ttk.Frame(self._notebook)
        self._notebook.add(self._flashcard_tab, text="Create Flashcard")
        self._notebook.add(self._conversation_tab, text="Practice Conversation")

        self._build_flashcard_tab()
        self._build_conversation_tab()

    def _update_conversation_scrollregion(self, _event: tk.Event) -> None:
        """Update the scrollable height after widgets change size."""
        self._conversation_canvas.configure(
            scrollregion=self._conversation_canvas.bbox("all")
        )

    def _resize_conversation_content(self, event: tk.Event) -> None:
        """Keep the scrollable conversation content as wide as its viewport."""
        self._conversation_canvas.itemconfigure(
            self._conversation_canvas_window,
            width=event.width,
        )

    def _enable_conversation_mousewheel(self, _event: tk.Event) -> None:
        """Enable mouse-wheel scrolling while the pointer is over the conversation tab."""
        self._root.bind_all("<MouseWheel>", self._scroll_conversation)

    def _disable_conversation_mousewheel(self, _event: tk.Event) -> None:
        """Stop handling mouse-wheel events after leaving the conversation tab."""
        self._root.unbind_all("<MouseWheel>")

    def _scroll_conversation(self, event: tk.Event) -> None:
        """Scroll the conversation tab on Windows mouse-wheel events."""
        self._conversation_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _build_flashcard_tab(self) -> None:
        """Create widgets used to generate and save a flashcard."""
        frame = self._flashcard_tab
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

        ttk.Label(frame, text="AI provider:").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Combobox(
            frame,
            textvariable=self._provider_var,
            values=list(self._ai_clients.keys()),
            state="readonly",
            width=28,
        ).grid(row=0, column=1, sticky="ew", pady=6, padx=(10, 10))

        ttk.Label(frame, text="Language:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(
            frame,
            textvariable=self._language_var,
            values=list(LANGUAGE_TAGS.keys()),
            state="readonly",
            width=28,
        ).grid(row=1, column=1, sticky="ew", pady=6, padx=(10, 10))

        ttk.Label(frame, text="Anki deck:").grid(row=2, column=0, sticky="w", pady=6)
        self._deck_box = ttk.Combobox(frame, textvariable=self._deck_var, width=50)
        self._deck_box.grid(row=2, column=1, sticky="ew", pady=6, padx=(10, 10))
        ttk.Button(frame, text="Refresh decks", command=self._load_decks).grid(
            row=2, column=2, sticky="ew", pady=6
        )

        ttk.Label(frame, text="Word or phrase:").grid(row=3, column=0, sticky="w", pady=6)
        word_entry = ttk.Entry(frame, textvariable=self._word_var)
        word_entry.grid(row=3, column=1, sticky="ew", pady=6, padx=(10, 10))
        word_entry.bind("<Return>", lambda _event: self._generate_card())
        ttk.Button(frame, text="Generate", command=self._generate_card, style="Accent.TButton").grid(
            row=3, column=2, sticky="ew", pady=6
        )

        ttk.Label(frame, text="Preview:").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(18, 6)
        )
        self._preview = tk.Text(
            frame, wrap="word", state="disabled", font=("Segoe UI", 10),
            background=SURFACE, foreground=TEXT, relief="flat",
            highlightthickness=1, highlightbackground=BORDER, padx=14, pady=14,
        )
        self._preview.grid(row=5, column=0, columnspan=3, sticky="nsew")

        ttk.Button(
            frame,
            text="Prepare style for old AI cards",
            command=self._prepare_old_cards_migration,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(16, 10))
        ttk.Button(frame, text="Add to Anki", command=self._add_to_anki, style="Accent.TButton").grid(
            row=6, column=2, sticky="e", pady=(16, 10)
        )
        ttk.Label(frame, textvariable=self._flashcard_status_var).grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )

    def _build_conversation_tab(self) -> None:
        """Create a scrollable workspace used for guided conversation practice."""
        outer = self._conversation_tab
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(0, weight=1)

        self._conversation_canvas = tk.Canvas(outer, highlightthickness=0, background=BG)
        scrollbar = ttk.Scrollbar(
            outer,
            orient="vertical",
            command=self._conversation_canvas.yview,
        )
        self._conversation_canvas.configure(yscrollcommand=scrollbar.set)
        self._conversation_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        frame = ttk.Frame(self._conversation_canvas, padding=18)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(6, minsize=92)
        frame.rowconfigure(10, minsize=180)

        self._conversation_canvas_window = self._conversation_canvas.create_window(
            (0, 0),
            window=frame,
            anchor="nw",
        )
        frame.bind("<Configure>", self._update_conversation_scrollregion)
        self._conversation_canvas.bind("<Configure>", self._resize_conversation_content)
        self._conversation_canvas.bind("<Enter>", self._enable_conversation_mousewheel)
        self._conversation_canvas.bind("<Leave>", self._disable_conversation_mousewheel)

        ttk.Label(frame, text="AI provider:").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Combobox(
            frame,
            textvariable=self._conversation_provider_var,
            values=list(self._ai_clients.keys()),
            state="readonly",
            width=28,
        ).grid(row=0, column=1, sticky="ew", pady=6, padx=(10, 0))

        ttk.Label(frame, text="Language:").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Combobox(
            frame,
            textvariable=self._conversation_language_var,
            values=list(LANGUAGE_TAGS.keys()),
            state="readonly",
            width=28,
        ).grid(row=1, column=1, sticky="ew", pady=6, padx=(10, 0))

        ttk.Label(frame, text="Model answer level:").grid(row=2, column=0, sticky="w", pady=6)
        ttk.Combobox(
            frame,
            textvariable=self._improvement_level_var,
            values=IMPROVEMENT_LEVELS,
            state="readonly",
            width=28,
        ).grid(row=2, column=1, sticky="ew", pady=6, padx=(10, 0))

        ttk.Label(frame, text="Your topic:").grid(row=3, column=0, sticky="w", pady=6)
        ttk.Entry(frame, textvariable=self._topic_var).grid(
            row=3, column=1, sticky="ew", pady=6, padx=(10, 0)
        )

        self._start_conversation_button = ttk.Button(
            frame,
            text="Start conversation",
            command=self._start_conversation,
            style="Accent.TButton",
        )
        self._start_conversation_button.grid(row=4, column=1, sticky="e", pady=(8, 16))
        ttk.Label(frame, textvariable=self._conversation_status_var).grid(
            row=4, column=0, sticky="w", pady=(8, 16)
        )

        ttk.Label(frame, text="AI question:").grid(row=5, column=0, columnspan=2, sticky="w")
        self._question_text = tk.Text(
            frame, height=4, wrap="word", state="disabled", font=("Segoe UI Semibold", 11),
            background="#EFF5FF", foreground=TEXT, relief="flat",
            highlightthickness=1, highlightbackground="#D8E5FA", padx=14, pady=12,
        )
        self._question_text.grid(row=6, column=0, columnspan=2, sticky="nsew", pady=(6, 12))

        ttk.Label(frame, text="Your answer:").grid(row=7, column=0, columnspan=2, sticky="w")
        self._answer_text = tk.Text(frame, height=5, wrap="word")
        self._answer_text.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(6, 10))
        ttk.Button(frame, text="Send answer", command=self._submit_answer).grid(
            row=8, column=2, sticky="se", padx=(10, 0), pady=(6, 10)
        )

        ttk.Label(frame, text="Feedback, corrected version and model answer:").grid(
            row=9, column=0, columnspan=2, sticky="sw", pady=(4, 0)
        )
        self._feedback_text = tk.Text(
            frame, height=14, wrap="word", state="disabled", font=("Segoe UI", 10),
            background=SURFACE, foreground=TEXT, relief="flat",
            highlightthickness=1, highlightbackground=BORDER, padx=14, pady=12,
        )
        self._feedback_text.grid(row=10, column=0, columnspan=2, sticky="nsew", pady=(6, 12))

        vocab_frame = ttk.Frame(frame)
        vocab_frame.grid(row=11, column=0, columnspan=3, sticky="ew")
        vocab_frame.columnconfigure(0, weight=1)
        ttk.Label(vocab_frame, text="Suggested vocabulary for flashcards:").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        self._vocabulary_list = tk.Listbox(
            vocab_frame, height=5, exportselection=False, selectmode=tk.EXTENDED,
            font=("Segoe UI", 10), background=SURFACE, foreground=TEXT,
            selectbackground=SELECTION, selectforeground=TEXT, relief="flat",
            highlightthickness=1, highlightbackground=BORDER, activestyle="none",
        )
        self._vocabulary_list.grid(row=1, column=0, sticky="ew", pady=(6, 8))
        ttk.Button(
            vocab_frame,
            text="Select all",
            command=self._select_all_vocabulary,
        ).grid(row=1, column=1, sticky="n", padx=(10, 0), pady=(6, 0))
        ttk.Button(
            vocab_frame,
            text="Preview one",
            command=self._move_vocabulary_to_flashcards,
        ).grid(row=1, column=2, sticky="n", padx=(10, 0), pady=(6, 0))

        ttk.Label(vocab_frame, text="Add your own word or phrase:").grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Entry(vocab_frame, textvariable=self._custom_vocabulary_var).grid(
            row=3, column=0, sticky="ew", pady=(6, 10)
        )
        ttk.Button(
            vocab_frame,
            text="Add to selection",
            command=self._add_custom_vocabulary,
        ).grid(row=3, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(6, 10))

        ttk.Label(
            vocab_frame,
            text="Selected words will be saved as full explained flashcards, like before.",
        ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 8))
        ttk.Label(vocab_frame, text="Anki deck for selected cards:").grid(
            row=5, column=0, sticky="w", pady=(4, 0)
        )
        self._conversation_deck_box = ttk.Combobox(
            vocab_frame,
            textvariable=self._conversation_deck_var,
            width=45,
        )
        self._conversation_deck_box.grid(row=6, column=0, sticky="ew", pady=(6, 0))
        ttk.Button(
            vocab_frame,
            text="Generate full cards and add to Anki",
            command=self._add_selected_vocabulary_to_anki,
            style="Accent.TButton",
        ).grid(row=6, column=1, columnspan=2, sticky="ew", padx=(10, 0), pady=(6, 0))

        ttk.Label(frame, textvariable=self._conversation_status_var).grid(
            row=12, column=0, columnspan=3, sticky="w", pady=(14, 0)
        )

    def _load_decks(self) -> None:
        """Load existing decks from Anki into the deck selection field."""
        try:
            decks = self._anki_client.list_decks()
        except Exception as exc:
            self._deck_box["values"] = [self._anki_client.deck_name]
            self._conversation_deck_box["values"] = [self._anki_client.deck_name]
            self._flashcard_status_var.set("Could not load decks. Open Anki and use Refresh decks.")
            messagebox.showwarning("Anki connection", str(exc))
            return

        if self._anki_client.deck_name not in decks:
            decks.append(self._anki_client.deck_name)

        self._deck_box["values"] = sorted(decks)
        self._conversation_deck_box["values"] = sorted(decks)
        try:
            self._anki_client.ensure_vocabulary_model_exists()
        except Exception:
            pass
        self._flashcard_status_var.set(
            "Ready. You can select an existing deck or type a new deck name."
        )

    def _generate_card(self) -> None:
        """Generate a flashcard and show it in the preview area."""
        word_or_phrase = self._word_var.get().strip()
        target_language = self._language_var.get()
        provider_name = self._provider_var.get()

        if not word_or_phrase:
            messagebox.showerror("Missing word", "Enter a word or phrase first.")
            return

        self._flashcard_status_var.set(f"Generating flashcard with {provider_name}...")
        self._root.update_idletasks()

        try:
            card = self._ai_clients[provider_name].generate_card(
                word_or_phrase=word_or_phrase,
                target_language=target_language,
            )
        except Exception as exc:
            self._flashcard_status_var.set("Card generation failed.")
            messagebox.showerror("Generation error", str(exc))
            return

        self._generated_card = card
        self._generated_provider_name = provider_name
        self._show_preview(card)
        self._flashcard_status_var.set(
            f"Card generated with {provider_name}. Review it and click Add to Anki."
        )

    def _show_preview(self, card: VocabularyCard) -> None:
        """Display the generated flashcard."""
        content = (
            f"Word: {card.word_or_phrase}\n"
            f"Language: {card.target_language}\n"
            f"Part of speech: {card.part_of_speech}\n\n"
            f"Definition: {card.definition}\n"
            f"Polish translation: {card.translation_pl}\n\n"
            f"Example: {card.example}\n"
            f"Example PL: {card.example_pl}\n\n"
            f"Synonyms / alternatives: {', '.join(card.synonyms)}\n\n"
            f"Collocations / usage:\n- " + "\n- ".join(card.collocations) + "\n\n"
            f"Grammar note: {card.grammar_note}"
        )
        self._set_text(self._preview, content)

    def _add_to_anki(self) -> None:
        """Add the currently previewed card to the selected Anki deck."""
        if self._generated_card is None:
            messagebox.showerror("No card", "Generate a card before adding it to Anki.")
            return

        deck_name = self._deck_var.get().strip()
        if not deck_name:
            messagebox.showerror("Missing deck", "Select or type an Anki deck name.")
            return

        try:
            self._anki_client.set_deck(deck_name)
            self._anki_client.add_card(
                self._generated_card,
                provider_name=self._generated_provider_name or self._provider_var.get(),
            )
        except Exception as exc:
            self._flashcard_status_var.set("Could not add the card to Anki.")
            messagebox.showerror("Anki error", str(exc))
            return

        self._flashcard_status_var.set(f"Added to Anki deck: {self._anki_client.deck_name}")
        messagebox.showinfo(
            "Added",
            f"Flashcard added to deck: {self._anki_client.deck_name}.\n\n"
            "It may appear in Browse before it appears in today's study session.",
        )
        self._word_var.set("")
        self._generated_card = None
        self._generated_provider_name = None

    def _prepare_old_cards_migration(self) -> None:
        """Prepare a styled legacy note type and open only old application cards."""
        proceed = messagebox.askokcancel(
            "Prepare old cards",
            "This will create a light card type for older LingoCards notes and "
            "open only old app-created Basic cards in Anki Browse.\n\n"
            "The final Change Note Type action is performed manually in Anki "
            "so your review history remains attached to the existing cards.",
        )
        if not proceed:
            return

        try:
            count = self._anki_client.prepare_legacy_card_migration()
        except Exception as exc:
            self._flashcard_status_var.set("Could not prepare migration.")
            messagebox.showerror("Migration error", str(exc))
            return

        if count == 0:
            messagebox.showinfo(
                "No old cards found",
                "No old Basic cards created by this application were found. "
                "Your new styled cards are already using the light model.",
            )
            return

        self._flashcard_status_var.set(
            f"Found {count} old app card(s). Complete Change Note Type in Anki Browse."
        )
        messagebox.showinfo(
            "Finish migration in Anki",
            f"Found {count} old app card(s) and opened them in Anki Browse.\n\n"
            "Now in Anki:\n"
            "1. Press Ctrl+A to select the shown cards.\n"
            "2. Choose Notes → Change Note Type.\n"
            "3. Select: AI Vocabulary Light Card · Migrated.\n"
            "4. Map Front → Front and Back → Back.\n"
            "5. Confirm.\n\n"
            "The cards will get the light layout while keeping their study history.",
        )

    def _start_conversation(self) -> None:
        """Start a conversation without blocking the Tkinter window."""
        topic = self._topic_var.get().strip()
        if not topic:
            messagebox.showerror("Missing topic", "Enter a conversation topic first.")
            return

        provider_name = self._conversation_provider_var.get()
        language = self._conversation_language_var.get()
        self._conversation_status_var.set(f"Starting conversation with {provider_name}...")
        self._start_conversation_button.configure(state="disabled")

        threading.Thread(
            target=self._request_conversation_start,
            args=(provider_name, topic, language),
            daemon=True,
        ).start()

    def _request_conversation_start(
        self,
        provider_name: str,
        topic: str,
        language: str,
    ) -> None:
        """Run the remote AI request in a worker thread."""
        try:
            start = self._ai_clients[provider_name].start_conversation(topic, language)
        except Exception as exc:
            self._root.after(0, self._show_conversation_start_error, str(exc))
            return

        self._root.after(0, self._show_conversation_start, start.question)

    def _show_conversation_start_error(self, error: str) -> None:
        """Display a conversation-start failure in the main UI thread."""
        self._start_conversation_button.configure(state="normal")
        self._conversation_status_var.set("Could not start conversation.")
        messagebox.showerror("Conversation error", error)

    def _show_conversation_start(self, question: str) -> None:
        """Display the generated first question in the main UI thread."""
        self._start_conversation_button.configure(state="normal")
        self._conversation_question = question
        self._conversation_feedback = None
        self._set_text(self._question_text, question)
        self._set_text(self._feedback_text, "")
        self._answer_text.delete("1.0", tk.END)
        self._vocabulary_list.delete(0, tk.END)
        self._conversation_status_var.set("Conversation started. Write your answer and send it.")
        self._answer_text.focus_set()

    def _submit_answer(self) -> None:
        """Review the learner answer and display feedback and the next question."""
        if not self._conversation_question:
            messagebox.showerror("No conversation", "Start a conversation first.")
            return

        answer = self._answer_text.get("1.0", tk.END).strip()
        if not answer:
            messagebox.showerror("Missing answer", "Write your answer before sending it.")
            return

        topic = self._topic_var.get().strip()
        provider_name = self._conversation_provider_var.get()
        language = self._conversation_language_var.get()
        improvement_level = self._improvement_level_var.get()
        self._conversation_status_var.set(f"Reviewing your answer with {provider_name}...")
        self._root.update_idletasks()

        try:
            feedback = self._ai_clients[provider_name].review_conversation_answer(
                topic=topic,
                question=self._conversation_question,
                answer=answer,
                target_language=language,
                improvement_level=improvement_level,
            )
        except Exception as exc:
            self._conversation_status_var.set("Could not review the answer.")
            messagebox.showerror("Conversation error", str(exc))
            return

        self._conversation_feedback = feedback
        feedback_content = (
            f"Feedback (PL):\n{feedback.feedback_pl}\n\n"
            f"Your corrected version:\n{feedback.corrected_version}\n\n"
            f"Stronger model answer ({improvement_level}):\n{feedback.advanced_answer}\n\n"
            f"Next question:\n{feedback.next_question}"
        )
        self._set_text(self._feedback_text, feedback_content)
        self._conversation_question = feedback.next_question
        self._set_text(self._question_text, feedback.next_question)
        self._answer_text.delete("1.0", tk.END)
        self._vocabulary_list.delete(0, tk.END)
        for expression in feedback.suggested_vocabulary:
            self._vocabulary_list.insert(tk.END, expression)
        self._conversation_status_var.set(
            "Feedback ready. Select several expressions, add your own if needed, and save them to Anki."
        )

    def _select_all_vocabulary(self) -> None:
        """Select every suggested or manually added expression."""
        self._vocabulary_list.selection_set(0, tk.END)

    def _add_custom_vocabulary(self) -> None:
        """Append a learner-provided expression and select it for saving."""
        expression = self._custom_vocabulary_var.get().strip()
        if not expression:
            messagebox.showerror("Missing expression", "Type your own word or phrase first.")
            return

        existing = self._vocabulary_list.get(0, tk.END)
        if expression not in existing:
            self._vocabulary_list.insert(tk.END, expression)

        index = self._vocabulary_list.get(0, tk.END).index(expression)
        self._vocabulary_list.selection_set(index)
        self._custom_vocabulary_var.set("")
        self._conversation_status_var.set(
            f'Added "{expression}" to the selected expressions.'
        )

    def _add_selected_vocabulary_to_anki(self) -> None:
        """Generate cards for all selected expressions and send them to one Anki deck."""
        indexes = self._vocabulary_list.curselection()
        if not indexes:
            messagebox.showerror(
                "No selection",
                "Select one or more expressions, or add your own expression first.",
            )
            return

        deck_name = self._conversation_deck_var.get().strip()
        if not deck_name:
            messagebox.showerror("Missing deck", "Select or type an Anki deck name.")
            return

        provider_name = self._conversation_provider_var.get()
        language = self._conversation_language_var.get()
        expressions = list(dict.fromkeys(self._vocabulary_list.get(index) for index in indexes))

        try:
            self._anki_client.set_deck(deck_name)
        except Exception as exc:
            self._conversation_status_var.set("Could not connect to Anki.")
            messagebox.showerror("Anki error", str(exc))
            return

        added: list[str] = []
        failed: list[str] = []
        for number, expression in enumerate(expressions, start=1):
            self._conversation_status_var.set(
                f"Creating card {number}/{len(expressions)}: {expression}"
            )
            self._root.update_idletasks()
            try:
                card = self._ai_clients[provider_name].generate_card(
                    word_or_phrase=expression,
                    target_language=language,
                )
                self._anki_client.add_card(card, provider_name=provider_name)
                added.append(expression)
            except Exception as exc:
                failed.append(f"{expression}: {exc}")

        if failed:
            self._conversation_status_var.set(
                f"Added {len(added)} card(s). {len(failed)} card(s) could not be added."
            )
            messagebox.showwarning(
                "Cards partially added",
                f"Added to {self._anki_client.deck_name}: {len(added)}\n\n"
                "Not added:\n- " + "\n- ".join(failed),
            )
            return

        self._conversation_status_var.set(
            f"Added {len(added)} card(s) to Anki deck: {self._anki_client.deck_name}"
        )
        messagebox.showinfo(
            "Cards added",
            f"Added {len(added)} flashcard(s) to deck: {self._anki_client.deck_name}.",
        )

    def _move_vocabulary_to_flashcards(self) -> None:
        """Move the first selected expression into the review-first flashcard workflow."""
        selection = self._vocabulary_list.curselection()
        if not selection:
            messagebox.showerror("No selection", "Select one suggested word or phrase first.")
            return

        selected_expression = self._vocabulary_list.get(selection[0])
        self._word_var.set(selected_expression)
        self._language_var.set(self._conversation_language_var.get())
        self._provider_var.set(self._conversation_provider_var.get())
        self._notebook.select(self._flashcard_tab)
        self._flashcard_status_var.set(
            f'Expression copied from conversation: "{selected_expression}". Click Generate to preview it.'
        )

    @staticmethod
    def _set_text(widget: tk.Text, content: str) -> None:
        """Replace the content of a read-only text widget."""
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert("1.0", content)
        widget.configure(state="disabled")
