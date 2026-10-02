"""Modern CustomTkinter GUI for the AI Anki Vocabulary Generator.

This module keeps the existing application logic and adds a modern interface with
both the single flashcard generator and Conversation workflow.
"""

from __future__ import annotations

import csv
import gc
import html
import json
import logging
import os
import queue
import re
import subprocess
import sys
import shutil
import tempfile
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from src.ai.base import VocabularyAiClient
from src.ai.prompts import build_ocr_candidate_extraction_prompt, build_multimodal_import_extraction_prompt, build_multimodal_ocr_prompt
from src.anki.client import AnkiClient, DuplicateNoteError
from src.anki.templates import GRAMMAR_MODEL_NAME, MODEL_NAME
from src.domain.languages import LANGUAGE_TAGS
from src.domain.models import ConversationFeedback, GrammarAnalysis, VocabularyCard
from src.core.config import get_settings
from src.core.learning_profile import (
    LearningProfile,
    load_learning_profile,
    save_learning_profile,
)
from src.core.user_setup import (
    SETUP_MODE_LABELS,
    check_ollama,
    configured_status,
    create_or_update_starter_env,
    import_env_file,
    normalize_setup_mode,
    read_env_values,
    merge_env_values,
)
from src.conversation import (
    SELECTION_ANKI_DUE,
    SELECTION_CONTINUE_ROTATION,
    SELECTION_MODES,
    SELECTION_RANDOM,
    SELECTION_REPEAT_LAST,
    build_anki_note_conversation_material,
    build_flashcard_conversation_material,
    dedupe_expressions,
    expression_is_grounded_in_exchange,
    filter_new_flashcard_candidates,
    load_rotation_state,
    normalize_expression,
    save_rotation_state,
    select_session_keys,
)
from src.conversation.audio import build_auto_read_text
from src.conversation.export import (
    default_conversation_export_name,
    write_conversation_export,
)
from src.practice import PracticeItem, PracticeQuestion, PracticeService
from src.quality import validate_vocabulary_card
from src.ocr import HTML_EXTENSIONS, TEXT_EXTENSIONS, OcrExtractionError, clean_ocr_text, extract_text_from_paths, extract_text_with_mistral, extract_candidates_with_multimodal, extract_text_with_multimodal
from src.speech import RecordedSttService, SpeechService, build_stt_service
from src.speech.playback import InternalAudioPlayer
from src.speech.models import TtsResult
from src.speech.voice_presets import get_voice_by_label, get_voice_labels
from src.speech.voice_library import (
    VoiceLibraryItem,
    add_elevenlabs_shared_voice,
    download_piper_voice,
    download_preview_audio,
    fetch_elevenlabs_my_voices,
    fetch_elevenlabs_shared_voices,
    fetch_elevenlabs_voice_preview,
    fetch_piper_catalog,
    fetch_piper_language_names,
    gemini_builtin_voice_items,
    openai_builtin_voice_items,
    import_piper_voice,
    installed_piper_models,
    load_elevenlabs_registry,
    piper_voice_directory,
    piper_voice_metadata,
    save_elevenlabs_registry_voice,
)
from src.observability import get_llmops_tracer


EXPLANATION_LANGUAGES = ["Polish", "English", "Spanish", "German", "Italian", "Same as target", "No translation"]
PROFILE_SUPPORT_LANGUAGES = ["Polish", *list(LANGUAGE_TAGS.keys()), "Same as target"]
IMPROVEMENT_LEVELS = ["Natural B1/B2", "Strong B2/C1", "Professional / Interview"]
CONVERSATION_MODE_TOPIC = "Talk about a topic"
CONVERSATION_MODE_FLASHCARDS = "Talk based on flashcards"
CONVERSATION_MODES = [CONVERSATION_MODE_TOPIC, CONVERSATION_MODE_FLASHCARDS]
CONVERSATION_FLASHCARD_SOURCE_ANKI = "Anki deck"
CONVERSATION_FLASHCARD_SOURCE_BATCH = "Current Queue"
CONVERSATION_FLASHCARD_SOURCES = [
    CONVERSATION_FLASHCARD_SOURCE_ANKI,
    CONVERSATION_FLASHCARD_SOURCE_BATCH,
]
CONVERSATION_FLASHCARD_LIMIT = 30
STT_PROVIDER_LABELS = {
    "local_whisper": "Local Whisper",
    "groq": "Groq Cloud",
    "openai": "OpenAI Cloud",
}
STT_PROVIDER_KEYS = {label: key for key, label in STT_PROVIDER_LABELS.items()}

STT_LANGUAGE_CODES = {
    "English": "en",
    "Spanish": "es",
    "German": "de",
    "French": "fr",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Japanese": "ja",
}
TTS_SAMPLE_TEXTS = {
    "English": "Hello! This is a quick voice test for your flashcards.",
    "Spanish": "Hola. Esta es una prueba rápida de voz para tus tarjetas.",
    "Polish": "Cześć. To jest krótki test głosu do twoich fiszek.",
    "German": "Hallo. Dies ist ein kurzer Stimmtest für deine Lernkarten.",
    "French": "Bonjour. Voici un court test de voix pour vos cartes mémoire.",
    "Italian": "Ciao. Questo è un breve test della voce per le tue flashcard.",
    "Portuguese": "Olá. Este é um pequeno teste de voz para os seus cartões.",
    "Russian": "Здравствуйте. Это короткая проверка голоса для ваших карточек.",
    "Japanese": "こんにちは。これはフラッシュカード用の短い音声テストです。",
}
CREATE_CARD_MODES = ["Vocabulary", "Grammar"]
BATCH_MODES = ["Vocabulary", "Grammar", "Mixed", "Provided examples"]
QUEUE_AI_BATCH_SIZE = 4
AUDIO_ANKI_BATCH_SIZE = 4
OCR_EXTRACTION_MODES = [
    "Provided examples",
    "Vocabulary",
    "Vocabulary + source examples",
    "Smart vocabulary",
    "Grammar",
    "Smart grammar import",
    "Mixed",
]
OCR_EXTRACTION_MODE_INTERNAL = {
    # The original mature Import Material modes are user-facing again.
    # Keep only aliases from the short-lived simplified UI for compatibility.
    "Vocabulary & expressions": "Vocabulary + source examples",
    "Examples / sentences": "Provided examples",
    "Auto": "Mixed",
}
OCR_EXTRACTION_MODE_HELP = {
    "Provided examples": "Find target + exact source-sentence pairs. Use only when the source really contains useful example sentences.",
    "Vocabulary": "Extract vocabulary targets only. Source examples are normally left for final card generation.",
    "Vocabulary + source examples": "Extract vocabulary targets and attach a useful source sentence when one is clearly present.",
    "Smart vocabulary": "Recommended. Keep explicit lesson vocabulary and expressions, then add only a selective set of high-value reusable items from continuous text.",
    "Grammar": "Extract clear grammar targets and structures from the source.",
    "Smart grammar import": "Interpret rules, transformations, exercises and examples intelligently before sending them to Queue.",
    "Mixed": "Allow vocabulary, grammar and provided-example candidates in the same import.",
    # Backward-compatible aliases from the simplified product UI.
    "Vocabulary & expressions": "Same as Vocabulary + source examples.",
    "Examples / sentences": "Same as Provided examples.",
    "Auto": "Same as Mixed.",
}
OCR_IMPORT_METHODS = ["Local extraction (free)", "Mistral OCR (cloud text only)", "OpenAI Vision OCR (text only)", "Gemini Vision OCR (text only)"]
OCR_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

# Runtime-only runaway guards for a *single* provider response. They are not
# extraction targets and are never exposed to the model. Candidate count is
# determined by source content; these guards only catch malformed/extreme
# responses before Tkinter is asked to render thousands of rows at once.
OCR_AI_CANDIDATE_HARD_LIMITS = {
    "vocabulary": 600,
    "vocabulary + source examples": 600,
    "smart vocabulary": 600,
    "provided examples": 600,
    "grammar": 600,
    "smart grammar import": 600,
    "mixed": 600,
}
OCR_CANDIDATE_AUTOSELECT_ALL_LIMIT = 25

# Source-size guardrails protect users from accidentally sending an entire book
# through many AI calls. These limits apply to source size, never to the number
# of useful candidates found. Large sources can still be reviewed section by
# section by selecting text in the Source text panel.
IMPORT_SOURCE_SOFT_CHAR_LIMIT = 60000
IMPORT_SOURCE_SOFT_WORD_LIMIT = 10000
IMPORT_SOURCE_HARD_CHAR_LIMIT = 180000
IMPORT_SOURCE_HARD_WORD_LIMIT = 30000
IMPORT_SOURCE_SOFT_PART_LIMIT = 4
IMPORT_SOURCE_HARD_PART_LIMIT = 8
IMPORT_REVIEW_PAGE_SIZE = 25

# Import Material never silently truncates a source. Long source text is split
# into bounded AI requests and merged back into one reviewed candidate set.
IMPORT_AI_CHUNK_SIZE = 20000
IMPORT_AI_CHUNK_OVERLAP = 500

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
        stt_service: RecordedSttService | None = None,
        window_title: str = "AI Anki Language Assistant",
        show_public_header: bool = True,
    ) -> None:
        LOGGER.info("APP PROCESS STARTED: pid=%s python=%s", os.getpid(), sys.version.split()[0])
        self._root = root
        self._window_title = window_title
        self._show_public_header = show_public_header
        self._top_settings_grid_row = 1
        self._ai_clients = ai_clients
        self._anki_client = anki_client
        self._speech_service = speech_service
        self._stt_service = stt_service

        provider_names = list(ai_clients)
        initial_provider = provider_names[0] if provider_names else "Not configured"
        self._provider_var = ctk.StringVar(value=initial_provider)
        current_settings = get_settings()
        self._setup_mode_var = ctk.StringVar(value=SETUP_MODE_LABELS.get(current_settings.setup_mode, "Hybrid / BYOK"))
        self._setup_status_var = ctk.StringVar(value="Configuration not checked yet.")
        stt_key = (current_settings.stt_provider or "local_whisper").strip().casefold()
        if stt_key in {"whisper", "faster_whisper", "local"}:
            stt_key = "local_whisper"
        elif stt_key in {"openai_cloud", "openai_stt", "cloud_openai"}:
            stt_key = "openai"
        elif stt_key in {"groq_cloud", "groq_stt", "cloud_groq"}:
            stt_key = "groq"
        self._setup_stt_provider_var = ctk.StringVar(value=STT_PROVIDER_LABELS.get(stt_key, "Local Whisper"))
        self._setup_ollama_status_var = ctk.StringVar(value="Ollama status not checked yet.")
        self._setup_env_path = Path(".env")
        self._learning_profile_path = Path("user_profile.json")
        self._learning_profile = load_learning_profile(self._learning_profile_path)
        profile_seed = self._learning_profile or LearningProfile(
            learning_language=default_target_language,
            level="Strong B2/C1",
            support_language="Polish",
        )
        self._language_var = ctk.StringVar(value=profile_seed.learning_language)
        self._explanation_language_var = ctk.StringVar(value=profile_seed.support_language)
        self._feedback_language_var = ctk.StringVar(value=profile_seed.support_language)
        self._improvement_level_var = ctk.StringVar(value=profile_seed.level)
        self._profile_summary_var = ctk.StringVar(value=profile_seed.summary)
        self._profile_language_var = ctk.StringVar(value=profile_seed.learning_language)
        self._profile_level_var = ctk.StringVar(value=profile_seed.level)
        self._profile_support_language_var = ctk.StringVar(value=profile_seed.support_language)
        self._deck_var = ctk.StringVar(value=anki_client.deck_name)
        # Speech & Audio must not depend on the hidden card-generation top bar.
        # Keep an explicit deck and language selector inside the audio tab.
        self._speech_deck_var = ctk.StringVar(value=anki_client.deck_name)
        self._speech_language_var = ctk.StringVar(value=profile_seed.learning_language)
        self._status_var = ctk.StringVar(value="Ready. Open Anki and choose a deck.")
        self._llmops_cost_var = ctk.StringVar(value="Cost summary: no events yet.")
        self._ocr_ai_running = False
        self._ocr_ai_search_serial = 0
        self._ocr_active_ai_search_id = 0

        self._create_card_mode_var = ctk.StringVar(value="Vocabulary")
        self._create_preview_title_var = ctk.StringVar(value="Vocabulary card preview")
        self._word_var = ctk.StringVar()
        self._generated_card: VocabularyCard | None = None
        self._generated_provider_name: str | None = None
        self._generated_audio: TtsResult | None = None

        tts_names = list(speech_service.providers) if speech_service else []
        self._single_tts_provider_var = ctk.StringVar(value=tts_names[0] if tts_names else "Off")
        self._tts_provider_var = ctk.StringVar(value=tts_names[0] if tts_names else "")
        self._tts_model_var = ctk.StringVar(value="")
        self._tts_voice_var = ctk.StringVar(value="")
        self._speech_notes: list[dict[str, object]] = []
        self._speech_note_vars: list[ctk.BooleanVar] = []
        self._speech_scan_loaded = False
        self._speech_search_var = ctk.StringVar(value="")
        self._speech_source_field_var = ctk.StringVar(value="Auto: Example/ContextExample/Back/Word")
        self._speech_target_field_var = ctk.StringVar(value="Audio")
        self._speech_write_mode_var = ctk.StringVar(value="Use dedicated audio field")
        self._speech_progress_var = ctk.StringVar(value="Load cards with missing audio from the selected Anki deck.")
        self._speech_summary_var = ctk.StringVar(value="No audio scan loaded yet.")
        initial_preview_text = TTS_SAMPLE_TEXTS.get(profile_seed.learning_language, TTS_SAMPLE_TEXTS["English"])
        self._speech_preview_text_var = ctk.StringVar(value=initial_preview_text)
        self._speech_preview_last_auto_text = initial_preview_text
        self._runtime_voice_values: dict[str, dict[str, str]] = {}
        self._runtime_voice_languages: dict[str, dict[str, str]] = {}
        for saved_voice in load_elevenlabs_registry():
            self._runtime_voice_values.setdefault("ElevenLabs", {})[saved_voice["label"]] = saved_voice["voice_id"]
            self._runtime_voice_languages.setdefault("ElevenLabs", {})[saved_voice["label"]] = saved_voice.get("language", "")
        self._voice_library_results: list[VoiceLibraryItem] = []
        self._voice_library_result_by_iid: dict[str, VoiceLibraryItem] = {}
        self._voice_library_window: ctk.CTkToplevel | None = None
        self._voice_library_tree: ttk.Treeview | None = None
        self._voice_library_language_box: ctk.CTkComboBox | None = None
        self._voice_library_source_var = ctk.StringVar(value="Piper online catalog")
        self._voice_library_search_var = ctk.StringVar(value="")
        self._voice_library_language_var = ctk.StringVar(value=profile_seed.learning_language)
        self._voice_library_status_var = ctk.StringVar(value="Open a catalog and search for voices.")
        self._speech_audio_status_by_note_id: dict[int, str] = {}
        self._speech_audio_error_by_note_id: dict[int, str] = {}
        self._speech_audio_path_by_note_id: dict[int, str] = {}

        self._grammar_sentence_var = ctk.StringVar()
        self._generated_grammar: GrammarAnalysis | None = None
        self._generated_grammar_provider_name: str | None = None

        self._topic_var = ctk.StringVar()
        self._conversation_mode_var = ctk.StringVar(value=CONVERSATION_MODE_TOPIC)
        self._conversation_flashcard_source_var = ctk.StringVar(
            value=CONVERSATION_FLASHCARD_SOURCE_ANKI
        )
        self._conversation_deck_var = ctk.StringVar(value=anki_client.deck_name)
        self._conversation_selection_var = ctk.StringVar(value=SELECTION_CONTINUE_ROTATION)
        self._conversation_rotation_state_path = Path("conversation_rotation_state.json")
        self._conversation_rotation_state = load_rotation_state(self._conversation_rotation_state_path)
        self._conversation_pending_rotation_state: tuple[str, dict[str, object]] | None = None
        self._conversation_selection_summary = SELECTION_CONTINUE_ROTATION
        self._conversation_flashcard_context = ""
        self._conversation_flashcard_rows: list[str] = []
        self._conversation_flashcard_targets: list[str] = []
        self._conversation_all_flashcard_targets: list[str] = []
        self._conversation_practised_targets: set[str] = set()
        self._conversation_expressions_to_use_next: list[str] = []
        self._conversation_new_candidate_pool: list[str] = []
        self._conversation_session_expanded = False
        self._conversation_session_title_var = ctk.StringVar(value="Flashcards in this session")
        self._conversation_flashcard_status_var = ctk.StringVar(
            value="Choose an Anki deck or use the current Queue."
        )
        self._conversation_language_var = ctk.StringVar(value=profile_seed.learning_language)
        preferred_conversation_provider = (
            "OpenAI" if "OpenAI" in ai_clients
            else "Gemini" if "Gemini" in ai_clients
            else "Ollama Local (experimental)" if "Ollama Local (experimental)" in ai_clients
            else initial_provider
        )
        self._conversation_provider_var = ctk.StringVar(value=preferred_conversation_provider)
        self._conversation_topic_draft = ""
        self._conversation_tts_provider_var = ctk.StringVar(value=tts_names[0] if tts_names else "")
        self._conversation_tts_model_var = ctk.StringVar(value="")
        self._conversation_tts_voice_var = ctk.StringVar(value="")
        self._conversation_detailed_feedback_var = ctk.BooleanVar(value=False)
        self._conversation_auto_read_tutor_var = ctk.BooleanVar(value=bool(speech_service))
        self._conversation_auto_read_question_var = ctk.BooleanVar(value=bool(speech_service))
        self._conversation_current_input_from_stt = False
        self._stt_status_var = ctk.StringVar(value="Speech input: ready." if stt_service else "Speech input: not configured.")
        self._conversation_audio_status_var = ctk.StringVar(
            value="Conversation audio: ready." if speech_service else "Conversation audio: TTS not configured."
        )
        self._conversation_audio_player = InternalAudioPlayer()
        self._speech_preview_player = InternalAudioPlayer()
        self._conversation_audio_request_id = 0
        self._conversation_audio_generation_lock = threading.Lock()
        self._recording_timer_after_id: str | None = None
        self._conversation_question: str | None = None
        self._conversation_tutor_reply: str | None = None
        self._conversation_history: list[tuple[str, str]] = []
        self._conversation_export_entries: list[tuple[str, str]] = []
        self._latest_suggestions: list[str] = []
        self._suggestion_items: list[dict[str, str]] = []
        self._suggestion_vars: list[ctk.BooleanVar] = []
        self._suggestion_entry_vars: list[ctk.StringVar] = []
        self._flashcard_queue: list[str] = []
        self._conversation_last_batch_send: list[str] = []
        self._conversation_queue_log_var = ctk.StringVar(
            value="Select AI suggestions, edit them if needed, then stage them here. Nothing is added to Anki from this panel."
        )

        # Queue mode state.
        self._batch_items: list[dict[str, object]] = []
        self._batch_index = 0
        self._batch_generated_card: VocabularyCard | None = None
        self._batch_generated_provider_name: str | None = None
        self._batch_word_var = ctk.StringVar()
        self._batch_mode_var = ctk.StringVar(value="Vocabulary")
        self._batch_generated_grammar: GrammarAnalysis | None = None
        self._batch_topic_var = ctk.StringVar(value="")
        self._batch_progress_var = ctk.StringVar(value="No list loaded.")
        self._batch_status_var = ctk.StringVar(value="Choose an input type first, then load a clean TXT/CSV file or paste a list.")
        self._batch_mode_help_var = ctk.StringVar(value="Vocabulary: one clean word or phrase per row.")
        self._batch_source_summary_var = ctk.StringVar(value="No source loaded yet.")
        self._batch_autosave_path: Path | None = None
        self._batch_autosave_after_id: str | None = None
        self._batch_auto_generate_running = False
        self._batch_auto_generate_paused = False
        self._batch_auto_generate_stop_requested = False
        self._batch_generation_in_flight = False
        self._batch_processing_index: int | None = None
        self._batch_worker_results: queue.Queue[dict[str, object]] = queue.Queue()
        self._batch_auto_provider_name = ""
        self._batch_auto_model_name = ""
        self._batch_auto_target_language = ""
        self._batch_auto_explanation_language = ""
        self._batch_auto_mode = ""
        self._batch_auto_topic_context = ""
        self._batch_perf_active = False
        self._batch_perf_started_at: float | None = None
        self._batch_perf_precheck_s = 0.0
        self._batch_perf_ai_s = 0.0
        self._batch_perf_apply_s = 0.0
        self._batch_perf_autosave_s = 0.0
        self._batch_perf_items = 0
        self._batch_add_all_running = False
        self._batch_add_all_paused = False
        self._batch_add_all_stop_requested = False
        self._batch_add_all_indexes: list[int] = []
        self._batch_add_all_position = 0
        self._batch_add_all_duplicate_strategy: str | None = None
        self._batch_add_all_existing_notes: dict[str, dict[str, object]] = {}
        self._batch_add_all_counts = {"added": 0, "updated": 0, "duplicates": 0, "uncertain": 0, "failed": 0}
        self._batch_add_all_failed_details: list[str] = []
        self._activity_var = ctk.StringVar(value="")

        # LLMOps / LangSmith observability state. The real tracing is optional
        # and configured through environment variables; the tab shows status and
        # a small local event log even when external LangSmith is disabled.
        self._llmops_status_var = ctk.StringVar(value="LLMOps status: not checked yet.")
        self._llmops_project_var = ctk.StringVar(value="Project: ai-anki-language-assistant")

        # OCR / Import workflow state. OCR prepares candidate rows only; Queue
        # remains the place where cards are generated, reviewed, and added.
        self._ocr_source_paths: list[Path] = []
        self._ocr_status_var = ctk.StringVar(value="Load a PDF, image, TXT/HTML, or paste text to start.")
        self._ocr_size_var = ctk.StringVar(value="No material loaded yet.")
        self._ocr_mode_var = ctk.StringVar(value="Smart vocabulary")
        self._ocr_mode_help_var = ctk.StringVar(value=OCR_EXTRACTION_MODE_HELP["Smart vocabulary"])
        self._ocr_method_var = ctk.StringVar(value="Local extraction (free)")
        self._ocr_ai_provider_var = ctk.StringVar(value=initial_provider)
        self._ocr_manual_candidate_type_var = ctk.StringVar(value="vocabulary")
        self._ocr_manual_target_var = ctk.StringVar(value="")
        self._ocr_manual_example_var = ctk.StringVar(value="")
        self._ocr_candidate_status_var = ctk.StringVar(value="No candidates yet.")
        self._ocr_candidate_items: list[dict[str, str]] = []
        self._ocr_candidate_vars: list[ctk.BooleanVar] = []
        self._ocr_review_priority_filter_var = ctk.StringVar(value="All priorities")
        self._ocr_review_type_filter_var = ctk.StringVar(value="All types")
        self._ocr_review_search_var = ctk.StringVar(value="")
        self._ocr_review_page = 0
        self._ocr_review_page_var = ctk.StringVar(value="Page 0 of 0")
        self._ocr_large_source_notified_signature: tuple[int, int] | None = None
        self._ocr_large_source_approved_signature: tuple[int, int] | None = None
        self._ocr_route_var = ctk.StringVar(value="TXT/HTML → read locally (no AI/model) → find candidates. Images/scans → OCR/vision → find candidates.")
        self._ocr_last_ai_request: tuple[str, str] | None = None
        self._shutdown_started = False

        # Existing cards workflow state. This is deliberately separate from
        # Queue autosave because old Anki notes may have been created before
        # the app had Queue/audio metadata.
        self._existing_cards: list[dict[str, object]] = []
        self._existing_card_vars: list[ctk.BooleanVar] = []
        self._existing_search_var = ctk.StringVar(value="")
        self._existing_scope_var = ctk.StringVar(value="Selected deck only")
        self._existing_tag_var = ctk.StringVar(value="")
        self._existing_flag_var = ctk.StringVar(value="No flag filter")
        self._existing_leech_var = ctk.BooleanVar(value=False)
        self._existing_topic_var = ctk.StringVar(value="character / personality traits")
        self._existing_progress_var = ctk.StringVar(value="Load flagged/leech/tagged cards, then fix or tag selected notes.")

        # Existing-card audio generation state. The worker runs in a background
        # thread, so pause/stop flags use threading.Event.
        self._speech_audio_running = False
        self._speech_audio_pause_requested = threading.Event()
        self._speech_audio_stop_requested = threading.Event()
        self._speech_audio_autosave_path: Path | None = None
        self._speech_audio_write_mode = ""

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
        if self._learning_profile is None:
            # First-run onboarding must not enter a nested Tk wait loop before
            # the application's real mainloop starts.  On Windows/PyCharm that
            # could leave a live Python process with no visible window.
            LOGGER.info("STARTUP PROFILE REQUIRED: showing non-blocking onboarding")
            self._show_first_learning_profile_setup(profile_seed)
            return

        LOGGER.info("STARTUP PROFILE LOADED: %s", self._learning_profile.summary)
        self._build_widgets()
        LOGGER.info("STARTUP MAIN UI BUILT")
        # Do not block first paint on AnkiConnect. Schedule deck discovery only
        # after Tk has entered its event loop so the window/profile screen is
        # visible even when Anki is closed or AnkiConnect is slow.
        self._root.after(100, self._load_decks)

    @staticmethod
    def _resource_path(relative_path: str) -> Path:
        """Resolve assets from source or a PyInstaller bundle."""
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / relative_path
        return Path(__file__).resolve().parents[2] / relative_path

    def _apply_window_icon(self) -> None:
        """Best-effort app icon; failure must never block local testing."""
        icon_path = self._resource_path("assets/app_icon.ico")
        if not icon_path.exists():
            return
        try:
            self._root.iconbitmap(str(icon_path))
        except Exception:
            LOGGER.debug("Could not set app icon", exc_info=True)

    def _configure_window(self) -> None:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self._root.title(self._window_title)
        self._apply_window_icon()
        self._root.geometry("1120x780")
        self._root.minsize(980, 680)
        self._root.grid_columnconfigure(0, weight=1)
        self._root.grid_rowconfigure(0, weight=1)
        self._root.report_callback_exception = self._report_tk_callback_exception
        self._root.protocol("WM_DELETE_WINDOW", lambda: self._on_app_close(source="wm_delete_window"))

    def _show_first_learning_profile_setup(self, seed: LearningProfile) -> None:
        """Show mandatory first-run onboarding without blocking Tk startup.

        The previous implementation used ``wait_variable`` before the outer
        ``mainloop`` had started.  That nested wait could leave a live Python
        process with no usable window on Windows/PyCharm.  This screen now
        behaves like a normal first page: the constructor returns, Tk enters
        its mainloop, and the Save button builds the main application.
        """
        self._root.title(f"{self._window_title} · Learning profile")
        self._root.geometry("760x590")
        self._root.minsize(700, 540)

        language_var = ctk.StringVar(value=seed.learning_language)
        level_var = ctk.StringVar(value=seed.level)
        support_var = ctk.StringVar(value=seed.support_language)

        frame = ctk.CTkFrame(self._root, corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        card = ctk.CTkFrame(frame, corner_radius=22)
        card.grid(row=0, column=0, sticky="nsew", padx=70, pady=55)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Set up your learning profile",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=26, pady=(26, 6))
        ctk.CTkLabel(
            card,
            text=(
                "Choose these once. Create Card, Import Material, Queue, Conversation, "
                "speech recognition and voice selection will all use the same profile."
            ),
            wraplength=570,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="ew", padx=26, pady=(0, 20))

        ctk.CTkLabel(card, text="Learning language", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=26, pady=(0, 5)
        )
        ctk.CTkComboBox(
            card,
            variable=language_var,
            values=list(LANGUAGE_TAGS.keys()),
            state="readonly",
            height=38,
        ).grid(row=3, column=0, sticky="ew", padx=26, pady=(0, 14))

        ctk.CTkLabel(card, text="Level / answer target", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=4, column=0, sticky="w", padx=26, pady=(0, 5)
        )
        ctk.CTkComboBox(
            card,
            variable=level_var,
            values=IMPROVEMENT_LEVELS,
            state="readonly",
            height=38,
        ).grid(row=5, column=0, sticky="ew", padx=26, pady=(0, 14))

        ctk.CTkLabel(card, text="Explanation & feedback language", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=6, column=0, sticky="w", padx=26, pady=(0, 5)
        )
        ctk.CTkComboBox(
            card,
            variable=support_var,
            values=PROFILE_SUPPORT_LANGUAGES,
            state="readonly",
            height=38,
        ).grid(row=7, column=0, sticky="ew", padx=26, pady=(0, 8))
        ctk.CTkLabel(
            card,
            text="AI providers and API keys are configured separately in Setup.",
            text_color=("gray35", "gray75"),
        ).grid(row=8, column=0, sticky="w", padx=26, pady=(0, 18))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=9, column=0, sticky="ew", padx=26, pady=(0, 26))
        actions.grid_columnconfigure(0, weight=1)

        def save_and_continue() -> None:
            profile = LearningProfile(
                learning_language=language_var.get().strip(),
                level=level_var.get().strip(),
                support_language=support_var.get().strip(),
            )
            if not profile.is_complete:
                messagebox.showerror("Learning profile", "Complete all profile fields before continuing.", parent=self._root)
                return
            try:
                save_learning_profile(profile, self._learning_profile_path)
            except Exception as exc:
                messagebox.showerror("Learning profile", f"Could not save the profile: {exc}", parent=self._root)
                return

            self._learning_profile = profile
            self._apply_learning_profile(profile, refresh_widgets=False)
            frame.destroy()
            self._root.title(self._window_title)
            self._root.geometry("1120x780")
            self._root.minsize(980, 680)
            self._root.protocol("WM_DELETE_WINDOW", lambda: self._on_app_close(source="wm_delete_window"))
            LOGGER.info("STARTUP PROFILE SAVED: %s", profile.summary)
            try:
                self._build_widgets()
                LOGGER.info("STARTUP MAIN UI BUILT AFTER PROFILE")
                self._root.after(100, self._load_decks)
            except Exception:
                LOGGER.exception("STARTUP FAILED WHILE BUILDING MAIN UI AFTER PROFILE")
                messagebox.showerror(
                    "Application startup",
                    "The learning profile was saved, but the main interface could not be built. "
                    "See logs/ai_anki_app.log for details.",
                    parent=self._root,
                )
                raise

        ctk.CTkButton(
            actions,
            text="Save profile & continue",
            height=44,
            command=save_and_continue,
        ).grid(row=0, column=0, sticky="ew")

        self._root.protocol("WM_DELETE_WINDOW", lambda: self._on_app_close(source="profile_onboarding_close"))

        def reveal() -> None:
            try:
                self._root.deiconify()
                self._root.lift()
                self._root.focus_force()
            except Exception:
                pass
            LOGGER.info("STARTUP PROFILE WINDOW PAINTED")

        # Let the real Tk mainloop perform the paint.  No wait_variable/update
        # loop is used here.
        self._root.after_idle(reveal)

    def _apply_learning_profile(self, profile: LearningProfile, *, refresh_widgets: bool = True) -> None:
        """Apply one learner profile as the source of truth for language-aware workflows."""
        previous_language = self._language_var.get().strip()
        self._learning_profile = profile
        self._language_var.set(profile.learning_language)
        self._speech_language_var.set(profile.learning_language)
        self._conversation_language_var.set(profile.learning_language)
        self._voice_library_language_var.set(profile.learning_language)
        self._explanation_language_var.set(profile.support_language)
        self._feedback_language_var.set(profile.support_language)
        self._improvement_level_var.set(profile.level)
        self._profile_summary_var.set(profile.summary)
        self._profile_language_var.set(profile.learning_language)
        self._profile_level_var.set(profile.level)
        self._profile_support_language_var.set(profile.support_language)

        if not refresh_widgets:
            return
        if previous_language and previous_language != profile.learning_language:
            if getattr(self, "_ocr_candidate_items", None):
                self._ocr_candidate_items = []
                self._ocr_candidate_vars = []
                self._ocr_review_page = 0
                self._render_ocr_candidate_cards()
                self._ocr_candidate_status_var.set(
                    "Learning language changed. Previous candidates were cleared; run Find candidates again for the active profile."
                )
        self._sync_speech_preview_text()
        self._sync_tts_defaults()
        self._sync_conversation_tts_defaults(preserve_voice=False)
        self._refresh_conversation_flashcard_status()
        self._status_var.set(f"Learning profile applied: {profile.summary}")

    def _save_learning_profile_from_ui(self) -> None:
        profile = LearningProfile(
            learning_language=self._profile_language_var.get().strip(),
            level=self._profile_level_var.get().strip(),
            support_language=self._profile_support_language_var.get().strip(),
        )
        if not profile.is_complete:
            messagebox.showerror("Learning profile", "Complete all profile fields.")
            return
        try:
            save_learning_profile(profile, self._learning_profile_path)
        except Exception as exc:
            messagebox.showerror("Learning profile", f"Could not save the profile: {exc}")
            return
        self._apply_learning_profile(profile)

    def _open_profile_tab(self) -> None:
        profile = self._learning_profile
        if profile is not None:
            self._profile_language_var.set(profile.learning_language)
            self._profile_level_var.set(profile.level)
            self._profile_support_language_var.set(profile.support_language)
        tabs = getattr(self, "_tabs", None)
        if tabs is not None:
            tabs.set("Profile")
            self._on_tab_changed()

    def _build_widgets(self) -> None:
        main = ctk.CTkFrame(self._root, corner_radius=0)
        main.grid(row=0, column=0, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        tabs_row = 2 if self._show_public_header else 1
        footer_row = tabs_row + 1
        main.grid_rowconfigure(tabs_row, weight=1)

        if self._show_public_header:
            header = ctk.CTkFrame(main, fg_color="transparent")
            header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
            header.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(
                header,
                text="AI Anki Language Assistant",
                font=ctk.CTkFont(size=28, weight="bold"),
            ).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                header,
                text="Practice conversations, review AI suggestions, and save selected expressions to Anki.",
                font=ctk.CTkFont(size=14),
                text_color=("gray35", "gray75"),
            ).grid(row=1, column=0, sticky="w", pady=(4, 0))
            profile_chip = ctk.CTkFrame(header, corner_radius=12)
            profile_chip.grid(row=0, column=1, rowspan=2, sticky="e", padx=(18, 0))
            ctk.CTkLabel(
                profile_chip,
                textvariable=self._profile_summary_var,
                font=ctk.CTkFont(size=12, weight="bold"),
            ).grid(row=0, column=0, padx=(12, 8), pady=8)
            ctk.CTkButton(
                profile_chip,
                text="Edit profile",
                width=92,
                command=self._open_profile_tab,
            ).grid(row=0, column=1, padx=(0, 8), pady=6)

        self._build_top_settings(main, row=1 if self._show_public_header else 0)

        tabs = ctk.CTkTabview(main, command=self._on_tab_changed)
        self._tabs = tabs
        tabs.grid(row=tabs_row, column=0, sticky="nsew", padx=24, pady=12)
        # Workflow order: create cards first, then audio/fixes, then practice tools.
        tab_order = [
            "Profile",
            "Setup",
            "Create Card",
            "Queue",
            "Import Material",
            "Speech & Audio",
            "Fix Cards",
            "Practice & Print",
            "Conversation",
            "Advanced",
        ]
        for tab_name in tab_order:
            tabs.add(tab_name)
            tabs.tab(tab_name).grid_columnconfigure(0, weight=1)
            tabs.tab(tab_name).grid_rowconfigure(0, weight=1)

        self._build_profile_tab(tabs.tab("Profile"))
        self._build_setup_tab(tabs.tab("Setup"))
        self._build_single_flashcard_tab(tabs.tab("Create Card"))
        self._build_batch_tab(tabs.tab("Queue"))
        self._build_ocr_tab(tabs.tab("Import Material"))
        self._build_speech_tab(tabs.tab("Speech & Audio"))
        self._build_existing_cards_tab(tabs.tab("Fix Cards"))
        self._build_practice_tab(tabs.tab("Practice & Print"))
        self._build_conversation_tab(tabs.tab("Conversation"))
        self._build_llmops_tab(tabs.tab("Advanced"))
        if not self._ai_clients:
            tabs.set("Setup")
        else:
            tabs.set("Create Card")
        self._on_tab_changed()

        footer = ctk.CTkFrame(main, fg_color="transparent")
        footer.grid(row=footer_row, column=0, sticky="ew", padx=24, pady=(0, 16))
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

    def _build_top_settings(self, parent: ctk.CTkFrame, row: int = 1) -> None:
        settings = ctk.CTkFrame(parent, corner_radius=18)
        self._top_settings = settings
        self._top_settings_grid_row = row
        settings.grid(row=row, column=0, sticky="ew", padx=24, pady=(8, 4))
        settings.grid_columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(settings, text="Card AI provider").grid(row=0, column=0, padx=(16, 8), pady=14, sticky="w")
        self._provider_box = ctk.CTkComboBox(
            settings,
            variable=self._provider_var,
            values=list(self._ai_clients.keys()) or ["Not configured"],
            state="readonly" if self._ai_clients else "disabled",
        )
        self._provider_box.grid(row=0, column=1, padx=(0, 16), pady=14, sticky="ew")

        ctk.CTkLabel(settings, text="Learning profile").grid(row=0, column=2, padx=(0, 8), pady=14, sticky="w")
        profile_frame = ctk.CTkFrame(settings, fg_color="transparent")
        profile_frame.grid(row=0, column=3, padx=(0, 16), pady=10, sticky="ew")
        profile_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            profile_frame,
            textvariable=self._profile_summary_var,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            profile_frame,
            text="Edit",
            width=56,
            command=self._open_profile_tab,
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(settings, text="Anki deck").grid(row=0, column=4, padx=(0, 8), pady=14, sticky="w")
        self._deck_box = ctk.CTkComboBox(settings, variable=self._deck_var, values=[])
        self._deck_box.grid(row=0, column=5, padx=(0, 8), pady=14, sticky="ew")
        ctk.CTkButton(settings, text="Refresh", width=90, command=self._load_decks).grid(
            row=0, column=6, padx=(0, 8), pady=14
        )
        ctk.CTkButton(
            settings,
            text="Clean runtime",
            width=120,
            command=self._manual_runtime_cleanup,
        ).grid(row=0, column=7, padx=(0, 16), pady=14)


    def _safe_destroy_children(self, widget: object | None) -> int:
        """Destroy direct child widgets and ignore already-destroyed Tk objects."""
        if widget is None:
            return 0
        destroyed = 0
        try:
            children = list(widget.winfo_children())  # type: ignore[attr-defined]
        except Exception:
            return 0
        for child in children:
            try:
                child.destroy()
                destroyed += 1
            except Exception:
                continue
        return destroyed

    def _folder_size_mb(self, path: Path) -> float:
        """Best-effort folder size helper for diagnostics, not for core flow."""
        total = 0
        try:
            for item in path.rglob("*"):
                try:
                    if item.is_file():
                        total += item.stat().st_size
                except OSError:
                    continue
        except OSError:
            return 0.0
        return round(total / (1024 * 1024), 2)

    def _windows_pagefile_summary(self) -> str:
        """Return a short pagefile summary on Windows without requiring psutil."""
        if os.name != "nt":
            return "pagefile: n/a"
        command = (
            "$p=Get-CimInstance Win32_PageFileUsage; "
            "if($p){($p|ForEach-Object{\"$($_.Name): current=$($_.CurrentUsage) MB, peak=$($_.PeakUsage) MB\"}) -join '; '}"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
        except Exception:
            return "pagefile: unavailable"
        output = (result.stdout or "").strip()
        return output or "pagefile: unavailable"

    def _process_memory_summary(self) -> str:
        """Return current process working-set memory without extra dependencies."""
        if os.name == "nt":
            command = (
                "$p=Get-Process -Id "
                + str(os.getpid())
                + "; if($p){[math]::Round($p.WorkingSet64/1MB,1)}"
            )
            try:
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=4,
                    check=False,
                )
                value = (result.stdout or "").strip()
                if value:
                    return f"App RAM: {value} MB"
            except Exception:
                pass
        try:
            import resource
            usage = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            if sys.platform == "darwin":
                usage /= 1024 * 1024
            else:
                usage /= 1024
            return f"App RAM: {usage:.1f} MB"
        except Exception:
            return "App RAM: unavailable"

    def _runtime_collection_summary(self) -> str:
        """Show sizes of the main in-memory collections that can grow during a session."""
        return (
            f"Queue: {len(getattr(self, '_batch_items', []))} item(s)\n"
            f"Import candidates: {len(getattr(self, '_ocr_candidate_items', []))}\n"
            f"Audio scan: {len(getattr(self, '_speech_notes', []))} note(s)\n"
            f"Existing cards: {len(getattr(self, '_existing_cards', []))}\n"
            f"Practice items: {len(getattr(self, '_practice_items', []))}\n"
            f"Conversation rows: {len(getattr(self, '_conversation_flashcard_rows', []))}"
        )

    def _clear_current_import_cache_files(self) -> int:
        """Delete only app-created import-cache files referenced by current OCR sources."""
        cache_root = Path(".import_cache").resolve()
        removed = 0
        for source_path in list(getattr(self, "_ocr_source_paths", [])):
            try:
                resolved = Path(source_path).resolve()
                if not resolved.is_file() or not resolved.is_relative_to(cache_root):
                    continue
                resolved.unlink(missing_ok=True)
                removed += 1
            except Exception:
                continue
        if removed:
            LOGGER.info("Import cache cleanup removed %s current file(s)", removed)
        return removed

    def _runtime_diagnostics_summary(self) -> str:
        """Summarise the sizes that explain most temporary disk pressure."""
        try:
            disk = shutil.disk_usage(Path.cwd().anchor or ".")
            free_gb = disk.free / (1024 ** 3)
        except Exception:
            free_gb = 0.0
        temp_mb = self._folder_size_mb(Path(tempfile.gettempdir()))
        import_mb = self._folder_size_mb(Path(".import_cache"))
        audio_mb = self._folder_size_mb(Path(".audio_cache"))
        pagefile = self._windows_pagefile_summary()
        process_memory = self._process_memory_summary()
        collections = self._runtime_collection_summary()
        return (
            f"{process_memory}\n"
            f"{collections}\n\n"
            f"C: free approx: {free_gb:.2f} GB\n"
            f"TEMP: {temp_mb:.2f} MB\n"
            f".import_cache: {import_mb:.2f} MB\n"
            f".audio_cache: {audio_mb:.2f} MB\n"
            f"{pagefile}"
        )

    def _cleanup_runtime_memory(self, reason: str = "runtime cleanup", *, aggressive: bool = False) -> int:
        """Release app-owned references and ask Python to collect garbage.

        This intentionally does not touch C:\\pagefile.sys. It only clears app
        state that can keep large OCR/import/queue objects alive. In non-aggressive
        mode it keeps current user data; aggressive mode is used on app close.
        """
        if aggressive:
            self._generated_card = None
            self._generated_provider_name = None
            self._generated_audio = None
            self._generated_grammar = None
            self._generated_grammar_provider_name = None
            self._batch_generated_card = None
            self._batch_generated_provider_name = None
            self._batch_generated_grammar = None
            self._latest_suggestions = []
            self._suggestion_items = []
            self._suggestion_vars = []
            self._suggestion_entry_vars = []
            self._flashcard_queue = []
            self._conversation_last_batch_send = []
            self._ocr_source_paths = []
            self._ocr_candidate_items = []
            self._ocr_candidate_vars = []
            self._batch_items = []
            self._batch_add_all_indexes = []
            self._batch_add_all_existing_notes = {}
            self._batch_add_all_failed_details = []
            self._speech_notes = []
            self._speech_note_vars = []
            self._speech_audio_status_by_note_id = {}
            self._speech_audio_error_by_note_id = {}
            self._speech_audio_path_by_note_id = {}
            self._existing_cards = []
            self._existing_card_vars = []
            self._practice_items = []
            self._practice_item_vars = []
            self._practice_questions = []
        else:
            # Safe cleanup: clear stale generated payloads only when there is no
            # active Queue item using them. Current visible user data stays intact.
            if not self._batch_items:
                self._batch_generated_card = None
                self._batch_generated_provider_name = None
                self._batch_generated_grammar = None
                self._batch_add_all_indexes = []
                self._batch_add_all_existing_notes = {}
                self._batch_add_all_failed_details = []
                try:
                    self._batch_paste_text.delete("1.0", "end")
                except Exception:
                    pass
            if not self._ocr_candidate_items and not self._get_ocr_text().strip():
                self._ocr_source_paths = []
            if not self._flashcard_queue:
                self._latest_suggestions = []
        collected = gc.collect()
        LOGGER.info("Runtime cleanup completed: reason=%s aggressive=%s collected=%s", reason, aggressive, collected)
        try:
            self._record_activity(f"Runtime cleanup: {collected} object(s) collected")
        except Exception:
            pass
        return collected

    def _manual_runtime_cleanup(self) -> None:
        collected = self._cleanup_runtime_memory("manual button", aggressive=False)
        summary = self._runtime_diagnostics_summary()
        self._status_var.set(f"Runtime cleanup completed. Collected {collected} object(s).")
        messagebox.showinfo("Runtime cleanup", f"Runtime cleanup completed.\nCollected objects: {collected}\n\n{summary}")

    def _report_tk_callback_exception(self, exc_type, exc_value, exc_traceback) -> None:
        """Log otherwise-easy-to-miss Tk callback failures with a real traceback."""
        LOGGER.critical(
            "Unhandled Tk callback exception; app remains open unless Tk/OS closes it",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        try:
            self._status_var.set("Unexpected UI error. Technical details were saved to logs/ai_anki_app.log.")
        except Exception:
            pass

    def _on_app_close(self, source: str = "unknown") -> None:
        """Stop background loops, release app state, and close the Tk root safely.

        The source is logged *before* cleanup so a future unexpected close can
        be distinguished from a provider failure or ordinary Queue completion.
        WM_DELETE_WINDOW can be triggered by the user or by the window manager,
        so the log deliberately says exactly what Tk reported instead of guessing.
        """
        if getattr(self, "_shutdown_started", False):
            LOGGER.warning("Duplicate shutdown request ignored: source=%s", source)
            return
        self._shutdown_started = True
        LOGGER.warning(
            "APP SHUTDOWN REQUESTED: source=%s queue_index=%s queue_items=%s auto_generate_running=%s add_all_running=%s",
            source,
            getattr(self, "_batch_index", None),
            len(getattr(self, "_batch_items", []) or []),
            getattr(self, "_batch_auto_generate_running", False),
            getattr(self, "_batch_add_all_running", False),
        )
        self._batch_auto_generate_stop_requested = True
        self._batch_add_all_stop_requested = True
        try:
            self._speech_audio_stop_requested.set()
        except Exception:
            pass
        after_id = getattr(self, "_recording_timer_after_id", None)
        if after_id:
            try:
                self._root.after_cancel(after_id)
            except Exception:
                pass
            self._recording_timer_after_id = None
        self._cleanup_runtime_memory(f"app close ({source})", aggressive=True)
        try:
            self._root.destroy()
            LOGGER.warning("APP ROOT DESTROYED: source=%s", source)
        except Exception:
            LOGGER.exception("APP ROOT DESTROY FAILED: source=%s", source)


    def _on_tab_changed(self) -> None:
        """Keep global card-generation settings out of audio-only workflow.

        The top bar controls Card AI provider / target deck for card creation.
        Language comes from the global learner profile, so language selectors are
        intentionally not duplicated in individual workflows.
        """
        tabs = getattr(self, "_tabs", None)
        top_settings = getattr(self, "_top_settings", None)
        if tabs is None or top_settings is None:
            return
        try:
            current_tab = tabs.get()
        except Exception:
            return
        if current_tab in {"Profile", "Setup", "Speech & Audio", "Conversation", "Advanced"}:
            top_settings.grid_remove()
        else:
            top_settings.grid(row=getattr(self, "_top_settings_grid_row", 1), column=0, sticky="ew", padx=24, pady=(8, 4))

        if current_tab == "Conversation":
            self._refresh_conversation_flashcard_status()

        # Avoid stale global messages from a previous workflow, for example
        # Conversation status still visible in Speech & Audio.
        context_status = {
            "Profile": "Learning profile ready. One profile controls language, level and support language across the app.",
            "Setup": "Setup ready. Choose Local, Hybrid/BYOK or API/BYOK and configure your own providers.",
            "Create Card": "Create Card ready. Choose Vocabulary or Grammar.",
            "Queue": "Queue ready. Choose an input type before loading clean structured input.",
            "Import Material": "Import Material ready.",
            "Speech & Audio": "Speech & Audio ready.",
            "Fix Cards": "Fix Cards ready.",
            "Practice & Print": "Practice & Print ready.",
            "Conversation": "Conversation ready.",
            "Advanced": "Advanced ready.",
        }.get(current_tab)
        if context_status and not any(
            token in self._status_var.get().lower()
            for token in ("generating", "recording", "transcribing", "adding", "scanning")
        ):
            self._status_var.set(context_status)

    def _build_profile_tab(self, parent: ctk.CTkFrame) -> None:
        """Build the single global learner-profile editor."""
        layout = ctk.CTkScrollableFrame(parent, corner_radius=18)
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            layout,
            text="Learning profile",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(
            layout,
            text=(
                "This is the single source of truth for language-aware workflows. "
                "Change it here once instead of choosing a language separately in every tab."
            ),
            wraplength=1000,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 14))

        card = ctk.CTkFrame(layout, corner_radius=16)
        card.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(card, text="Learning language", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=(14, 8), pady=(14, 5)
        )
        ctk.CTkLabel(card, text="Level / answer target", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=1, sticky="w", padx=(8, 14), pady=(14, 5)
        )
        ctk.CTkComboBox(
            card,
            variable=self._profile_language_var,
            values=list(LANGUAGE_TAGS.keys()),
            state="readonly",
        ).grid(row=1, column=0, sticky="ew", padx=(14, 8), pady=(0, 12))
        ctk.CTkComboBox(
            card,
            variable=self._profile_level_var,
            values=IMPROVEMENT_LEVELS,
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", padx=(8, 14), pady=(0, 12))

        ctk.CTkLabel(card, text="Explanation & feedback language", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=(14, 8), pady=(0, 5)
        )
        ctk.CTkComboBox(
            card,
            variable=self._profile_support_language_var,
            values=PROFILE_SUPPORT_LANGUAGES,
            state="readonly",
        ).grid(row=3, column=0, sticky="ew", padx=(14, 8), pady=(0, 14))
        ctk.CTkButton(
            card,
            text="Save & apply profile",
            height=42,
            command=self._save_learning_profile_from_ui,
        ).grid(row=3, column=1, sticky="ew", padx=(8, 14), pady=(0, 14))

        behavior = ctk.CTkFrame(layout, corner_radius=16)
        behavior.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        behavior.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            behavior,
            text="What changes with the profile?",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(
            behavior,
            text=(
                "Create Card, Import Material, Queue, Conversation, STT language, Voice Lab samples and "
                "Piper voice filtering all follow the active learning language. Explanation and tutor feedback use the support language.\n\n"
                "Provider/API configuration stays separate in Setup."
            ),
            wraplength=980,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))



    def _build_setup_tab(self, parent: ctk.CTkFrame) -> None:
        """Build the user-facing Local / Hybrid / BYOK setup workspace."""
        layout = ctk.CTkScrollableFrame(parent, corner_radius=18)
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            layout,
            text="AI setup",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(
            layout,
            text=(
                "Choose how the app should run. API keys stay in your local .env file. "
                "They are never bundled into clean releases or exported conversations/cards."
            ),
            wraplength=1000,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 14))

        modes = ctk.CTkFrame(layout, corner_radius=16)
        modes.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        modes.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkLabel(modes, text="1 · Choose a provider mode", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 6)
        )
        descriptions = [
            ("Fully local", "Ollama for AI, local Whisper for speech-to-text and Piper for TTS. No cloud API keys required."),
            ("Hybrid / BYOK", "Mix local tools with your own OpenAI, Gemini, OpenRouter, Claude, Groq, ElevenLabs or OCR API keys; STT can be local, Groq Cloud or OpenAI Cloud."),
            ("API / BYOK", "Use your own cloud AI/TTS keys. Speech input can use Groq Cloud or OpenAI Cloud STT instead of local Whisper."),
        ]
        for index, (label, description) in enumerate(descriptions):
            card = ctk.CTkFrame(modes, corner_radius=12)
            card.grid(row=1, column=index, sticky="nsew", padx=(14 if index == 0 else 6, 14 if index == 2 else 6), pady=(0, 12))
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkRadioButton(
                card,
                text=label,
                variable=self._setup_mode_var,
                value=label,
                font=ctk.CTkFont(size=13, weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
            ctk.CTkLabel(
                card,
                text=description,
                wraplength=280,
                justify="left",
                text_color=("gray35", "gray75"),
            ).grid(row=1, column=0, sticky="nw", padx=12, pady=(0, 12))

        env_card = ctk.CTkFrame(layout, corner_radius=16)
        env_card.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12))
        env_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(env_card, text="2 · Configure providers", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 4)
        )
        ctk.CTkLabel(
            env_card,
            text=(
                "Technical users can import an existing .env. Otherwise create a starter file for the selected profile, "
                "open it, paste your own keys/paths and reload configuration."
            ),
            wraplength=1000,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        actions = ctk.CTkFrame(env_card, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        for col in range(5):
            actions.grid_columnconfigure(col, weight=1)
        ctk.CTkButton(actions, text="Create / update .env", command=self._create_setup_env).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(actions, text="Import .env", command=self._import_setup_env).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ctk.CTkButton(actions, text="Open .env", command=self._open_setup_env).grid(
            row=0, column=2, sticky="ew", padx=5
        )
        ctk.CTkButton(actions, text="Reload configuration", command=self._reload_provider_configuration).grid(
            row=0, column=3, sticky="ew", padx=5
        )
        ctk.CTkButton(actions, text="Check Ollama", command=self._check_setup_ollama).grid(
            row=0, column=4, sticky="ew", padx=(5, 0)
        )

        speech_card = ctk.CTkFrame(layout, corner_radius=16)
        speech_card.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 12))
        speech_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(speech_card, text="3 · Speech-to-text", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=14, pady=(12, 4)
        )
        ctk.CTkLabel(
            speech_card,
            text="Choose local Whisper or cloud transcription. Groq Cloud uses GROQ_API_KEY; OpenAI Cloud uses OPENAI_API_KEY. Neither cloud option loads a local Whisper model.",
            wraplength=900,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, columnspan=3, sticky="ew", padx=14, pady=(0, 8))
        ctk.CTkLabel(speech_card, text="STT provider").grid(row=2, column=0, sticky="w", padx=(14, 8), pady=(0, 12))
        ctk.CTkComboBox(
            speech_card,
            variable=self._setup_stt_provider_var,
            values=list(STT_PROVIDER_KEYS),
            state="readonly",
            width=220,
        ).grid(row=2, column=1, sticky="w", padx=(0, 8), pady=(0, 12))
        ctk.CTkButton(speech_card, text="Save STT choice", command=self._save_setup_stt_provider).grid(
            row=2, column=2, sticky="e", padx=(8, 14), pady=(0, 12)
        )

        status_card = ctk.CTkFrame(layout, corner_radius=16)
        status_card.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 20))
        status_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(status_card, text="4 · Current configuration", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(12, 4)
        )
        ctk.CTkLabel(
            status_card,
            textvariable=self._setup_status_var,
            wraplength=1000,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 4))
        ctk.CTkLabel(
            status_card,
            textvariable=self._setup_ollama_status_var,
            wraplength=1000,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))

        ctk.CTkLabel(
            layout,
            text=(
                "Local install: requirements-local.txt. Hybrid: requirements-hybrid.txt. API/cloud-only: requirements-cloud.txt. "
                "AnkiConnect still runs locally in every profile."
            ),
            wraplength=1000,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=6, column=0, sticky="ew", padx=20, pady=(0, 20))
        self._refresh_setup_status()

    @staticmethod
    def _setup_mode_key_from_label(label: str) -> str:
        return normalize_setup_mode(label)

    def _refresh_setup_status(self) -> None:
        values = read_env_values(self._setup_env_path)
        status = configured_status(values)
        settings = get_settings()
        file_mode = normalize_setup_mode(values.get("AI_SETUP_MODE") or settings.setup_mode)
        self._setup_mode_var.set(SETUP_MODE_LABELS.get(file_mode, "Hybrid / BYOK"))
        stt_key = (values.get("STT_PROVIDER") or settings.stt_provider or "local_whisper").strip().casefold()
        if stt_key in {"whisper", "faster_whisper", "local"}:
            stt_key = "local_whisper"
        elif stt_key in {"openai_cloud", "openai_stt", "cloud_openai"}:
            stt_key = "openai"
        elif stt_key in {"groq_cloud", "groq_stt", "cloud_groq"}:
            stt_key = "groq"
        self._setup_stt_provider_var.set(STT_PROVIDER_LABELS.get(stt_key, "Local Whisper"))
        def flag(name: str) -> str:
            return "✓" if status.get(name) else "—"
        self._setup_status_var.set(
            "Provider mode in .env: " + SETUP_MODE_LABELS.get(file_mode, file_mode) + "\n"
            f"Local: {flag('ollama')} Ollama · {flag('whisper')} Whisper STT · {flag('piper')} Piper\n"
            f"Cloud STT: {flag('groq_stt')} Groq Whisper · {flag('openai_stt')} OpenAI transcription\n"
            f"BYOK: {flag('openai')} OpenAI · {flag('gemini')} Gemini · {flag('openrouter')} OpenRouter · "
            f"{flag('groq')} Groq · {flag('claude')} Claude · {flag('elevenlabs')} ElevenLabs · {flag('mistral')} Mistral OCR\n"
            f"Active AI providers in this session: {', '.join(self._ai_clients) if self._ai_clients else 'none'}"
        )

    def _save_setup_stt_provider(self) -> None:
        """Persist the selected STT provider and reload it immediately."""
        label = self._setup_stt_provider_var.get().strip()
        provider = STT_PROVIDER_KEYS.get(label, "local_whisper")
        try:
            merge_env_values(
                self._setup_env_path,
                {
                    "STT_PROVIDER": provider,
                    "OPENAI_STT_MODEL": "gpt-4o-mini-transcribe",
                    "GROQ_STT_MODEL": "whisper-large-v3-turbo",
                },
            )
        except Exception as exc:
            messagebox.showerror("Speech-to-text", f"Could not save STT provider: {exc}")
            return
        self._reload_provider_configuration()
        settings = get_settings()
        if provider == "openai" and not settings.openai_api_key:
            self._status_var.set("OpenAI Cloud STT selected. Add OPENAI_API_KEY in Setup, then reload configuration.")
        elif provider == "groq" and not settings.groq_api_key:
            self._status_var.set("Groq Cloud STT selected. Add GROQ_API_KEY in Setup, then reload configuration.")
        else:
            self._status_var.set(f"Speech-to-text provider saved: {label}.")

    def _create_setup_env(self) -> None:
        mode = self._setup_mode_key_from_label(self._setup_mode_var.get())
        try:
            path = create_or_update_starter_env(mode, self._setup_env_path)
        except Exception as exc:
            messagebox.showerror("AI setup", f"Could not create .env: {exc}")
            return
        self._status_var.set(f"Starter configuration saved to {path}. Add your own keys/paths, then reload configuration.")
        self._refresh_setup_status()

    def _import_setup_env(self) -> None:
        selected = filedialog.askopenfilename(
            title="Import AI Anki .env",
            filetypes=[("Environment file", "*.env"), ("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not selected:
            return
        try:
            destination, backup, count = import_env_file(selected, self._setup_env_path)
            create_or_update_starter_env(self._setup_mode_key_from_label(self._setup_mode_var.get()), destination)
        except Exception as exc:
            messagebox.showerror("Import .env", str(exc))
            return
        backup_text = f" Backup: {backup.name}." if backup else ""
        self._status_var.set(f"Imported {count} supported setting(s) into {destination}.{backup_text} Reload configuration to apply them.")
        self._refresh_setup_status()

    def _open_setup_env(self) -> None:
        if not self._setup_env_path.exists():
            self._create_setup_env()
        try:
            if os.name == "nt":
                os.startfile(str(self._setup_env_path.resolve()))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self._setup_env_path.resolve())])
            else:
                subprocess.Popen(["xdg-open", str(self._setup_env_path.resolve())])
        except Exception as exc:
            messagebox.showerror("Open .env", f"Could not open .env automatically: {exc}\n\nPath: {self._setup_env_path.resolve()}")

    def _check_setup_ollama(self) -> None:
        values = read_env_values(self._setup_env_path)
        base_url = values.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        model = (values.get("OLLAMA_MODEL") or "").strip() or None
        ok, detail = check_ollama(base_url, model)
        self._setup_ollama_status_var.set(("✓ " if ok else "⚠ ") + detail)

    def _reload_provider_configuration(self) -> None:
        """Reload .env and rebuild configured AI/TTS/STT services in-place."""
        try:
            from dotenv import load_dotenv
            from src.ai.factory import build_ai_clients
            from src.speech.tts.factory import build_tts_providers

            load_dotenv(self._setup_env_path, override=True)
            settings = get_settings()
            ai_clients = build_ai_clients(settings)
            tts_providers = build_tts_providers(settings)
        except Exception as exc:
            messagebox.showerror("Reload configuration", f"Could not reload configuration: {exc}")
            return

        self._ai_clients = ai_clients
        provider_names = list(ai_clients)
        provider_values = provider_names or ["Not configured"]
        selected = self._provider_var.get() if self._provider_var.get() in ai_clients else (provider_names[0] if provider_names else "Not configured")
        self._provider_var.set(selected)
        self._ocr_ai_provider_var.set(selected)
        conversation_selected = self._conversation_provider_var.get()
        if conversation_selected not in ai_clients:
            conversation_selected = selected
        self._conversation_provider_var.set(conversation_selected)

        for box_name in ("_provider_box", "_ocr_ai_provider_box", "_conversation_provider_box"):
            box = getattr(self, box_name, None)
            if box is not None:
                box.configure(values=provider_values, state="readonly" if ai_clients else "disabled")
        if hasattr(self, "_ocr_ai_button"):
            self._ocr_ai_button.configure(state="normal" if ai_clients else "disabled")

        self._speech_service = SpeechService(tts_providers, Path(settings.audio_cache_dir)) if tts_providers else None
        tts_names = list(tts_providers)
        self._tts_provider_var.set(tts_names[0] if tts_names else "")
        single_values = ["Off", *tts_names]
        if hasattr(self, "_single_tts_provider_box"):
            self._single_tts_provider_box.configure(values=single_values, state="readonly")
        self._single_tts_provider_var.set(tts_names[0] if tts_names else "Off")
        if hasattr(self, "_tts_provider_box"):
            self._tts_provider_box.configure(values=tts_names, state="readonly" if tts_names else "disabled")

        if hasattr(self, "_ocr_method_box"):
            ocr_methods = self._available_ocr_methods()
            self._ocr_method_box.configure(values=ocr_methods)
            if self._ocr_method_var.get() not in ocr_methods:
                self._ocr_method_var.set(ocr_methods[0])
            self._update_ocr_method_ui()

        self._stt_service = build_stt_service(settings)
        if self._stt_service:
            self._stt_status_var.set(
                f"Speech input: {self._stt_service.provider_name} ({self._stt_service.model_name}) ready."
            )
        elif (settings.stt_provider or "").strip().casefold() in {"openai", "openai_cloud", "openai_stt", "cloud_openai"}:
            self._stt_status_var.set("Speech input: OpenAI Cloud selected, but OPENAI_API_KEY is missing.")
        elif (settings.stt_provider or "").strip().casefold() in {"groq", "groq_cloud", "groq_stt", "cloud_groq"}:
            self._stt_status_var.set("Speech input: Groq Cloud selected, but GROQ_API_KEY is missing.")
        else:
            self._stt_status_var.set("Speech input: not configured.")

        self._conversation_audio_status_var.set(
            "Conversation audio: ready." if self._speech_service else "Conversation audio: TTS not configured."
        )
        if not self._speech_service:
            self._conversation_auto_read_tutor_var.set(False)
            self._conversation_auto_read_question_var.set(False)
        self._sync_tts_defaults()
        self._sync_conversation_tts_defaults(preserve_voice=True)
        self._refresh_setup_status()
        if ai_clients:
            self._status_var.set(f"Configuration reloaded. Active AI providers: {', '.join(ai_clients)}")
        else:
            self._status_var.set("Configuration reloaded, but no AI provider is active yet. Finish Setup before generating cards.")


    def _build_llmops_tab(self, parent: ctk.CTkFrame) -> None:
        """Build a small LangSmith/LLMOps status and event-log tab."""
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=1)
        layout.grid_rowconfigure(3, weight=1)

        header = ctk.CTkFrame(layout, corner_radius=18)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="LLMOps / LangSmith",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            header,
            text="Optional tracing layer for AI calls: provider, model, latency, token/cost estimates, validation flow and safe input/output summaries.",
            text_color=("gray35", "gray75"),
            wraplength=1000,
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 18))

        status = ctk.CTkFrame(layout, corner_radius=18)
        status.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        status.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(status, text="Status", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 4)
        )
        ctk.CTkLabel(status, textvariable=self._llmops_status_var, anchor="w").grid(
            row=1, column=0, columnspan=4, sticky="ew", padx=18, pady=(0, 4)
        )
        ctk.CTkLabel(status, textvariable=self._llmops_project_var, anchor="w").grid(
            row=2, column=0, columnspan=4, sticky="ew", padx=18, pady=(0, 4)
        )
        ctk.CTkLabel(status, textvariable=self._llmops_cost_var, anchor="w", justify="left", text_color=("gray30", "gray75")).grid(
            row=3, column=0, columnspan=4, sticky="ew", padx=18, pady=(0, 12)
        )
        ctk.CTkButton(status, text="Refresh status", width=130, command=self._refresh_llmops_status).grid(
            row=4, column=0, sticky="w", padx=(18, 8), pady=(0, 16)
        )
        ctk.CTkButton(status, text="Test trace", width=110, command=self._send_llmops_test_trace).grid(
            row=4, column=1, sticky="w", padx=(0, 8), pady=(0, 16)
        )
        ctk.CTkButton(status, text="Copy .env setup", width=140, command=self._copy_llmops_setup).grid(
            row=4, column=2, sticky="w", padx=(0, 8), pady=(0, 16)
        )
        ctk.CTkButton(status, text="Open LangSmith app", width=160, command=self._open_langsmith).grid(
            row=4, column=3, sticky="w", padx=(0, 18), pady=(0, 16)
        )

        info = ctk.CTkFrame(layout, corner_radius=18)
        info.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        info.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(info, text="What is traced", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 4)
        )
        ctk.CTkLabel(
            info,
            text=(
                "Current MVP traces vocabulary cards, grammar cards, provided-example cards, conversation start/feedback, "
                "raw AI candidate search calls used by Import Material, and lightweight token/cost estimates. Redaction is ON by default, "
                "so source text is summarized instead of being sent in full unless you disable LANGSMITH_REDACT_INPUTS."
            ),
            wraplength=1000,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 16))

        log_panel = ctk.CTkFrame(layout, corner_radius=18)
        log_panel.grid(row=3, column=0, sticky="nsew")
        log_panel.grid_columnconfigure(0, weight=1)
        log_panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(log_panel, text="Recent AI events", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 8)
        )
        self._llmops_log_text = ctk.CTkTextbox(log_panel, wrap="word", font=ctk.CTkFont(size=13))
        self._llmops_log_text.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))
        buttons = ctk.CTkFrame(log_panel, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        ctk.CTkButton(buttons, text="Refresh log", width=120, command=self._refresh_llmops_log).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        ctk.CTkButton(buttons, text="Clear local log", width=130, command=self._clear_llmops_log).grid(
            row=0, column=1, sticky="w"
        )
        self._refresh_llmops_status()
        self._refresh_llmops_log()

    def _refresh_llmops_status(self) -> None:
        tracer = get_llmops_tracer()
        package_status = "available" if tracer.langsmith_available else "missing"
        if tracer.langsmith_available is None:
            package_status = "not checked"
        api_status = "configured" if tracer.api_key_configured else "missing"
        redact_status = "ON" if tracer.redact_inputs else "OFF"
        self._llmops_status_var.set(
            f"LangSmith: {tracer.status_text()} | package: {package_status} | API key: {api_status} | redaction: {redact_status}"
        )
        self._llmops_project_var.set(f"Project: {tracer.project_name}")
        self._llmops_cost_var.set(tracer.cost_summary_text())
        self._refresh_llmops_log()

    def _format_llmops_events(self) -> str:
        tracer = get_llmops_tracer()
        events = tracer.snapshot_events()
        if not events:
            return (
                "No AI events yet. Generate a card, run Import Material with AI, or click Test trace.\n\n"
                "If LangSmith is disabled, this tab still shows a local event log. If enabled, successful events are also sent to LangSmith."
            )
        lines = []
        for event in events[:40]:
            sent = "sent" if event.sent_to_langsmith else "local"
            quality_bits = []
            if event.outcome:
                quality_bits.append(f"outcome={event.outcome}")
            if event.validation_passed is not None:
                quality_bits.append(f"validation={event.validation_passed}")
            if event.red_flags_count is not None:
                quality_bits.append(f"red_flags={event.red_flags_count}")
            if event.issue_type:
                quality_bits.append(f"issue={event.issue_type}")
            if event.total_tokens:
                quality_bits.append(f"tokens={event.total_tokens}")
            if event.estimated_cost is not None:
                quality_bits.append(f"cost={event.estimated_cost:.6f} {event.cost_currency}")
            elif event.total_tokens:
                quality_bits.append("cost=rate not configured")
            quality = " | " + " · ".join(quality_bits) if quality_bits else ""
            lines.append(
                f"[{event.timestamp}] {event.feature} | {event.provider} {event.model} | "
                f"{event.status} | {event.latency_ms} ms | {sent}{quality}"
            )
            if event.prompt_version or event.source:
                lines.append(f"    prompt={event.prompt_version} | source={event.source}")
            if event.detail:
                lines.append(f"    {event.detail}")
        return "\n".join(lines)

    def _refresh_llmops_log(self) -> None:
        text_widget = getattr(self, "_llmops_log_text", None)
        if text_widget is None:
            return
        text_widget.configure(state="normal")
        text_widget.delete("1.0", "end")
        text_widget.insert("1.0", self._format_llmops_events())
        text_widget.configure(state="disabled")
        cost_var = getattr(self, "_llmops_cost_var", None)
        if cost_var is not None:
            cost_var.set(get_llmops_tracer().cost_summary_text())

    def _clear_llmops_log(self) -> None:
        get_llmops_tracer().clear_events()
        self._refresh_llmops_log()
        self._record_activity("LLMOps log cleared")

    def _send_llmops_test_trace(self) -> None:
        tracer = get_llmops_tracer()
        try:
            result = tracer.trace_call(
                feature="llmops_test_trace",
                provider="system",
                model="none",
                inputs={"message": "Manual Test trace from AI Anki desktop UI"},
                metadata={"source": "LLMOps tab", "app": "AI Anki Language Assistant"},
                call_fn=lambda: "LangSmith test trace OK",
            )
        except Exception as exc:
            self._refresh_llmops_status()
            messagebox.showerror("LangSmith test trace", f"Test trace failed: {exc}")
            return
        self._refresh_llmops_status()
        self._status_var.set(f"LLMOps test trace completed: {result}")
        messagebox.showinfo("LangSmith test trace", "Test trace completed. Check the local log and LangSmith project if tracing is enabled.")

    def _copy_llmops_setup(self) -> None:
        setup = (
            "# LangSmith / LLMOps tracing\n"
            "LANGSMITH_TRACING=true\n"
            "LANGSMITH_API_KEY=your_langsmith_api_key_here\n"
            "LANGSMITH_PROJECT=ai-anki-language-assistant\n"
            "LANGSMITH_REDACT_INPUTS=true\n"
            "# Optional estimated-cost rates. Leave empty to track tokens without local cost estimates.\n"
            "OPENAI_INPUT_COST_PER_1M_TOKENS=\n"
            "OPENAI_OUTPUT_COST_PER_1M_TOKENS=\n"
            "GEMINI_INPUT_COST_PER_1M_TOKENS=\n"
            "GEMINI_OUTPUT_COST_PER_1M_TOKENS=\n"
            "CLAUDE_INPUT_COST_PER_1M_TOKENS=\n"
            "CLAUDE_OUTPUT_COST_PER_1M_TOKENS=\n"
            "ELEVENLABS_COST_PER_1000_CHARS=\n"
        )
        self._root.clipboard_clear()
        self._root.clipboard_append(setup)
        self._status_var.set("LangSmith .env setup copied to clipboard.")
        self._record_activity("LangSmith setup copied")

    def _open_langsmith(self) -> None:
        webbrowser.open("https://smith.langchain.com/")

    def _build_single_flashcard_tab(self, parent: ctk.CTkFrame) -> None:
        """Build one compact Create Card workspace for Vocabulary and Grammar."""
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)
        layout.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(layout, corner_radius=18, width=360)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Create one card", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 4)
        )
        ctk.CTkLabel(
            left,
            text="Vocabulary and Grammar live in one place. Choose the card type, generate a preview, review it, then add it to Anki.",
            wraplength=315, justify="left", text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

        ctk.CTkLabel(left, text="Card type", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=18, pady=(0, 4)
        )
        self._create_card_mode_box = ctk.CTkComboBox(
            left, variable=self._create_card_mode_var, values=CREATE_CARD_MODES, state="readonly",
            command=self._on_create_card_mode_changed,
        )
        self._create_card_mode_box.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 12))

        self._single_vocab_controls = ctk.CTkFrame(left, fg_color="transparent")
        self._single_vocab_controls.grid(row=4, column=0, sticky="ew")
        self._single_vocab_controls.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self._single_vocab_controls, text="Word or phrase").grid(row=0, column=0, sticky="w", padx=18, pady=(4, 4))
        entry = ctk.CTkEntry(self._single_vocab_controls, textvariable=self._word_var, height=40, placeholder_text="e.g. cut through the noise")
        entry.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        entry.bind("<Return>", lambda _event: self._generate_single_card())
        ctk.CTkLabel(
            self._single_vocab_controls,
            textvariable=self._profile_summary_var,
            text_color=("gray35", "gray75"),
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(2, 10))
        ctk.CTkButton(self._single_vocab_controls, text="Generate vocabulary preview", height=42, command=self._generate_single_card).grid(
            row=4, column=0, sticky="ew", padx=18, pady=(4, 8)
        )
        speech_frame = ctk.CTkFrame(self._single_vocab_controls, corner_radius=12)
        speech_frame.grid(row=5, column=0, sticky="ew", padx=18, pady=(4, 10))
        speech_frame.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(speech_frame, text="Optional example audio", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 4)
        )
        self._single_tts_provider_box = ctk.CTkComboBox(
            speech_frame, variable=self._single_tts_provider_var,
            values=(["Off"] + list(self._speech_service.providers.keys())) if self._speech_service else ["Off"],
            state="readonly", command=lambda _value: self._sync_single_tts_provider(),
        )
        self._single_tts_provider_box.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))
        ctk.CTkButton(speech_frame, text="Generate audio", command=self._generate_single_audio).grid(
            row=2, column=0, sticky="ew", padx=(12, 4), pady=(0, 10)
        )
        ctk.CTkButton(speech_frame, text="Play in app", command=self._preview_generated_audio).grid(
            row=2, column=1, sticky="ew", padx=(4, 12), pady=(0, 10)
        )
        ctk.CTkButton(
            self._single_vocab_controls, text="Add reviewed vocabulary card to Anki", height=42,
            command=self._add_single_card_to_anki,
        ).grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 18))

        self._single_grammar_controls = ctk.CTkFrame(left, fg_color="transparent")
        self._single_grammar_controls.grid(row=4, column=0, sticky="ew")
        self._single_grammar_controls.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self._single_grammar_controls, text="Sentence to analyse",
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(4, 4))
        grammar_entry = ctk.CTkEntry(
            self._single_grammar_controls, textvariable=self._grammar_sentence_var, height=42,
            placeholder_text="He might have gone out.",
        )
        grammar_entry.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        grammar_entry.bind("<Return>", lambda _event: self._analyze_grammar_sentence())
        ctk.CTkLabel(
            self._single_grammar_controls,
            text="The sentence is the example. AI extracts one concise grammar target, pattern and learner explanation for the card.",
            wraplength=315, justify="left", text_color=("gray35", "gray75"),
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 10))
        ctk.CTkButton(
            self._single_grammar_controls, text="Analyze grammar", height=42, command=self._analyze_grammar_sentence,
        ).grid(row=3, column=0, sticky="ew", padx=18, pady=(4, 8))
        ctk.CTkButton(
            self._single_grammar_controls, text="Add reviewed grammar card to Anki", height=42, command=self._add_grammar_card_to_anki,
        ).grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 18))

        right = ctk.CTkFrame(layout, corner_radius=18)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(right, textvariable=self._create_preview_title_var, font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 4)
        )
        ctk.CTkLabel(
            right, text="Review before saving. Nothing is written to Anki until you use the Add button.",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 8))

        self._single_vocab_preview_panel = ctk.CTkFrame(right, fg_color="transparent")
        self._single_vocab_preview_panel.grid(row=2, column=0, sticky="nsew")
        self._single_vocab_preview_panel.grid_columnconfigure(0, weight=1)
        self._single_vocab_preview_panel.grid_rowconfigure(0, weight=1)
        self._preview = ctk.CTkTextbox(self._single_vocab_preview_panel, wrap="word", font=ctk.CTkFont(size=14))
        self._preview.grid(row=0, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self._preview.insert("1.0", "Generate a vocabulary card to preview it here.")
        self._preview.configure(state="disabled")

        self._single_grammar_preview_panel = ctk.CTkFrame(right, fg_color="transparent")
        self._single_grammar_preview_panel.grid(row=2, column=0, sticky="nsew")
        self._single_grammar_preview_panel.grid_columnconfigure(0, weight=1)
        self._single_grammar_preview_panel.grid_rowconfigure(0, weight=1)
        self._grammar_preview = ctk.CTkTextbox(self._single_grammar_preview_panel, wrap="word", font=ctk.CTkFont(size=14))
        self._grammar_preview.grid(row=0, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self._grammar_preview.insert(
            "1.0",
            "Enter a sentence to see its meaning, structure, usage, context, contrasts, and common mistakes.",
        )
        self._grammar_preview.configure(state="disabled")
        self._on_create_card_mode_changed(self._create_card_mode_var.get())

    def _on_create_card_mode_changed(self, selected: str | None = None) -> None:
        mode = (selected or self._create_card_mode_var.get() or "Vocabulary").strip()
        if mode not in CREATE_CARD_MODES:
            mode = "Vocabulary"
        self._create_card_mode_var.set(mode)
        if not all(hasattr(self, name) for name in (
            "_single_vocab_controls", "_single_grammar_controls",
            "_single_vocab_preview_panel", "_single_grammar_preview_panel",
        )):
            return
        if mode == "Grammar":
            self._single_vocab_controls.grid_remove()
            self._single_vocab_preview_panel.grid_remove()
            self._single_grammar_controls.grid()
            self._single_grammar_preview_panel.grid()
            self._create_preview_title_var.set("Grammar card preview")
            self._status_var.set("Create Card · Grammar mode ready.")
        else:
            self._single_grammar_controls.grid_remove()
            self._single_grammar_preview_panel.grid_remove()
            self._single_vocab_controls.grid()
            self._single_vocab_preview_panel.grid()
            self._create_preview_title_var.set("Vocabulary card preview")
            self._status_var.set("Create Card · Vocabulary mode ready.")

    def _build_grammar_tab(self, parent: ctk.CTkFrame) -> None:
        """Build the target-first grammar analysis tab."""
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


    def _available_ocr_methods(self) -> list[str]:
        """Return OCR/text methods that are actually configured for this profile."""
        methods = ["Local extraction (free)"]
        settings = get_settings()
        if settings.setup_mode in {"api", "hybrid"}:
            values = read_env_values(self._setup_env_path)
            if (values.get("MISTRAL_API_KEY") or "").strip():
                methods.append("Mistral OCR (cloud text only)")
            if any("openai" in name.casefold() for name in self._ai_clients):
                methods.append("OpenAI Vision OCR (text only)")
            if any("gemini" in name.casefold() for name in self._ai_clients):
                methods.append("Gemini Vision OCR (text only)")
        return methods


    def _build_ocr_tab(self, parent: ctk.CTkFrame) -> None:
        """Build the Import Material tab.

        This tab only prepares editable candidates. It never adds cards
        directly to Anki; Queue remains the review/generation step.
        """
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=2)
        layout.grid_columnconfigure(2, weight=2)
        layout.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(layout, corner_radius=18, width=330)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        # CTkScrollableFrame does not accept a boolean argument for grid_propagate
        # in some CustomTkinter versions. The explicit width is enough here.
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left,
            text="Import Material",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))
        ctk.CTkLabel(
            left,
            text="Use this for lessons, web pages, PDFs, screenshots and other raw material. TXT/HTML are simply read on your computer — no model or API is used. AI is only used later when you choose Find candidates with AI.",
            wraplength=280,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 10))

        self._ocr_method_label = ctk.CTkLabel(
            left, text="PDF / image reading method", font=ctk.CTkFont(size=12, weight="bold")
        )
        self._ocr_method_label.grid(row=2, column=0, sticky="w", padx=18, pady=(2, 4))
        self._ocr_method_box = ctk.CTkComboBox(
            left,
            variable=self._ocr_method_var,
            values=self._available_ocr_methods(),
            state="readonly",
            command=lambda _value: self._update_ocr_method_ui(),
        )
        self._ocr_method_box.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 10))

        file_buttons = ctk.CTkFrame(left, fg_color="transparent")
        file_buttons.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 8))
        file_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(file_buttons, text="Load TXT/HTML", command=self._ocr_load_txt).grid(
            row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 6)
        )
        ctk.CTkButton(file_buttons, text="Load PDF", command=self._ocr_load_pdf).grid(
            row=0, column=1, sticky="ew", padx=(5, 0), pady=(0, 6)
        )
        ctk.CTkButton(file_buttons, text="Load image", command=self._ocr_load_image).grid(
            row=1, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(file_buttons, text="Load images", command=self._ocr_load_images).grid(
            row=1, column=1, sticky="ew", padx=(5, 0), pady=(0, 6)
        )
        ctk.CTkButton(
            file_buttons,
            text="Paste text / screenshot",
            height=36,
            command=self._open_paste_material_dialog,
        ).grid(row=2, column=0, columnspan=2, sticky="ew")

        self._ocr_run_button = ctk.CTkButton(
            left,
            text="Read material locally",
            command=self._run_ocr_import_pipeline,
        )
        self._ocr_run_button.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 8))
        ctk.CTkButton(
            left,
            text="Clean source text",
            command=self._clean_ocr_preview_text,
        ).grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 10))

        ctk.CTkLabel(left, text="What do you want to find?", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=7, column=0, sticky="w", padx=18, pady=(6, 4)
        )
        ctk.CTkComboBox(
            left,
            variable=self._ocr_mode_var,
            values=OCR_EXTRACTION_MODES,
            state="readonly",
            command=lambda _value: self._update_ocr_mode_help(),
        ).grid(row=8, column=0, sticky="ew", padx=18, pady=(0, 4))
        ctk.CTkLabel(
            left,
            textvariable=self._ocr_mode_help_var,
            wraplength=280,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=9, column=0, sticky="w", padx=18, pady=(0, 8))
        ctk.CTkLabel(
            left,
            text="AI provider",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray35", "gray75"),
        ).grid(row=10, column=0, sticky="w", padx=18, pady=(0, 2))
        self._ocr_ai_provider_box = ctk.CTkComboBox(
            left,
            variable=self._ocr_ai_provider_var,
            values=list(self._ai_clients.keys()) or ["Not configured"],
            state="readonly" if self._ai_clients else "disabled",
        )
        self._ocr_ai_provider_box.grid(row=11, column=0, sticky="ew", padx=18, pady=(0, 6))
        self._ocr_ai_button = ctk.CTkButton(
            left,
            text="Find candidates with AI",
            height=38,
            command=self._extract_ocr_candidates_with_ai,
            state="normal" if self._ai_clients else "disabled",
        )
        self._ocr_ai_button.grid(row=12, column=0, sticky="ew", padx=18, pady=(0, 6))
        self._ocr_ai_selection_button = ctk.CTkButton(
            left,
            text="Find from selected text",
            command=self._extract_ocr_candidates_from_selection_with_ai,
            state="normal" if self._ai_clients else "disabled",
        )
        self._ocr_ai_selection_button.grid(row=13, column=0, sticky="ew", padx=18, pady=(0, 6))
        self._ocr_retry_button = ctk.CTkButton(
            left, text="Retry AI candidate search", command=self._retry_last_ocr_ai_extraction, state="disabled"
        )
        self._ocr_retry_button.grid(row=14, column=0, sticky="ew", padx=18, pady=(0, 10))

        ctk.CTkLabel(left, text="Basic local finder (optional)", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=15, column=0, sticky="w", padx=18, pady=(2, 3)
        )
        ctk.CTkLabel(
            left,
            text=(
                "No API call. For prepared examples, target | example and target<TAB>example "
                "are recognized directly."
            ),
            wraplength=280,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=16, column=0, sticky="w", padx=18, pady=(0, 5))
        local_buttons = ctk.CTkFrame(left, fg_color="transparent")
        local_buttons.grid(row=17, column=0, sticky="ew", padx=18, pady=(0, 8))
        local_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            local_buttons,
            text="Words / phrases",
            command=self._look_for_ocr_words_or_phrases,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(
            local_buttons,
            text="Examples / sentences",
            command=self._look_for_ocr_sentences,
        ).grid(row=0, column=1, sticky="ew", padx=(5, 0))

        ctk.CTkButton(left, text="Clear candidates", command=self._clear_ocr_candidates).grid(
            row=18, column=0, sticky="ew", padx=18, pady=(0, 6)
        )
        ctk.CTkButton(left, text="Clear import", command=self._clear_ocr_import).grid(
            row=19, column=0, sticky="ew", padx=18, pady=(2, 8)
        )

        ctk.CTkLabel(
            left,
            textvariable=self._ocr_size_var,
            wraplength=280,
            justify="left",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray30", "gray70"),
        ).grid(row=20, column=0, sticky="w", padx=18, pady=(2, 6))
        ctk.CTkLabel(
            left,
            textvariable=self._ocr_status_var,
            wraplength=280,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=21, column=0, sticky="w", padx=18, pady=(0, 18))

        text_panel = ctk.CTkFrame(layout, corner_radius=18)
        text_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        text_panel.grid_columnconfigure(0, weight=1)
        text_panel.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(
            text_panel,
            text="Source text",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))
        self._ocr_textbox = ctk.CTkTextbox(text_panel, wrap="word", font=ctk.CTkFont(size=13))
        self._ocr_textbox.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self._ocr_textbox.insert(
            "1.0",
            "Flow:\n"
            "1. Paste text/screenshot or load a file, then review and clean the source text here.\n"
            "2. Choose what you want to find, then use Find candidates with AI (recommended) or the basic local fallback.\n"
            "3. Edit/remove candidates and cherry-pick the useful rows.\n"
            "4. Send selected candidates to Queue.\n\n"
            "Manual additions are available only as + Add missing candidate.",
        )

        candidates_panel = ctk.CTkFrame(layout, corner_radius=18)
        candidates_panel.grid(row=0, column=2, sticky="nsew")
        candidates_panel.grid_columnconfigure(0, weight=1)
        candidates_panel.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(
            candidates_panel,
            text="Candidates to review",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        review_filters = ctk.CTkFrame(candidates_panel, fg_color="transparent")
        review_filters.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 8))
        review_filters.grid_columnconfigure(2, weight=1)
        ctk.CTkComboBox(
            review_filters,
            variable=self._ocr_review_priority_filter_var,
            values=["All priorities", "Recommended", "Useful", "Optional"],
            state="readonly",
            width=145,
            command=lambda _value: self._reset_ocr_review_page_and_render(),
        ).grid(row=0, column=0, sticky="w", padx=(0, 6))
        ctk.CTkComboBox(
            review_filters,
            variable=self._ocr_review_type_filter_var,
            values=["All types", "Vocabulary", "Grammar", "Provided example"],
            state="readonly",
            width=145,
            command=lambda _value: self._reset_ocr_review_page_and_render(),
        ).grid(row=0, column=1, sticky="w", padx=(0, 6))
        search_entry = ctk.CTkEntry(
            review_filters,
            textvariable=self._ocr_review_search_var,
            placeholder_text="Search candidates",
        )
        search_entry.grid(row=0, column=2, sticky="ew", padx=(0, 6))
        ctk.CTkButton(
            review_filters, text="Apply", width=62, command=self._reset_ocr_review_page_and_render
        ).grid(row=0, column=3, sticky="e")
        ctk.CTkLabel(
            review_filters,
            text="Recommended = advanced + central to the topic · Useful = good general language · Optional = niche/odd/document-specific. Nothing is deleted.",
            font=ctk.CTkFont(size=10),
            text_color=("gray40", "gray65"),
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(4, 0))

        self._ocr_candidates_frame = ctk.CTkScrollableFrame(candidates_panel, fg_color=("gray92", "gray13"))
        self._ocr_candidates_frame.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 8))
        self._ocr_candidates_frame.grid_columnconfigure(0, weight=1)

        pager = ctk.CTkFrame(candidates_panel, fg_color="transparent")
        pager.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 8))
        pager.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(pager, text="← Previous", width=90, command=lambda: self._change_ocr_review_page(-1)).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(pager, textvariable=self._ocr_review_page_var).grid(row=0, column=1)
        ctk.CTkButton(pager, text="Next →", width=90, command=lambda: self._change_ocr_review_page(1)).grid(
            row=0, column=2, sticky="e"
        )

        candidate_actions = ctk.CTkFrame(candidates_panel, fg_color="transparent")
        candidate_actions.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 8))
        candidate_actions.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(
            candidate_actions,
            text="Select all",
            command=self._select_all_ocr_candidates,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="Select recommended",
            command=self._select_recommended_ocr_candidates,
        ).grid(row=0, column=1, sticky="ew", padx=5, pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="Recommended + useful",
            command=self._select_recommended_and_useful_ocr_candidates,
        ).grid(row=0, column=2, sticky="ew", padx=5, pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="Deselect all",
            command=self._deselect_all_ocr_candidates,
        ).grid(row=0, column=3, sticky="ew", padx=(5, 0), pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="Select visible",
            command=self._select_visible_ocr_candidates,
        ).grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="Selected → Vocabulary",
            command=lambda: self._mark_selected_ocr_candidates_as("vocabulary"),
        ).grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="Selected → Grammar",
            command=lambda: self._mark_selected_ocr_candidates_as("grammar"),
        ).grid(row=1, column=2, sticky="ew", padx=5, pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="Selected → Example",
            command=lambda: self._mark_selected_ocr_candidates_as("provided_example"),
        ).grid(row=1, column=3, sticky="ew", padx=(5, 0), pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="Remove selected",
            command=self._remove_selected_ocr_candidates,
        ).grid(row=2, column=0, sticky="ew", padx=(0, 5), pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="Clear all",
            command=self._clear_ocr_candidates,
        ).grid(row=2, column=1, sticky="ew", padx=5, pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="+ Add missing candidate",
            command=self._open_missing_ocr_candidate_dialog,
        ).grid(row=2, column=2, columnspan=2, sticky="ew", padx=(5, 0), pady=(0, 6))
        ctk.CTkButton(
            candidate_actions,
            text="Send selected to Queue",
            height=40,
            command=self._send_ocr_candidates_to_batch,
        ).grid(row=3, column=0, columnspan=4, sticky="ew")

        ctk.CTkLabel(
            candidates_panel,
            textvariable=self._ocr_candidate_status_var,
            wraplength=560,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=5, column=0, sticky="w", padx=18, pady=(0, 18))
        self._render_ocr_candidate_cards()
        self._update_ocr_method_ui()

    def _build_conversation_tab(self, parent: ctk.CTkFrame) -> None:
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=3)
        layout.grid_columnconfigure(1, weight=2)
        layout.grid_rowconfigure(1, weight=1)

        controls = ctk.CTkFrame(layout, corner_radius=18)
        controls.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        controls.grid_columnconfigure((1, 3, 5), weight=1)

        # Step 1: choose the practice mode first. Everything irrelevant to that
        # mode is hidden rather than merely disabled, so the user cannot confuse
        # topic settings with flashcard practice.
        ctk.CTkLabel(
            controls, text="Practice with", font=ctk.CTkFont(size=17, weight="bold")
        ).grid(row=0, column=0, padx=(18, 8), pady=(16, 10), sticky="w")
        self._conversation_mode_box = ctk.CTkComboBox(
            controls,
            variable=self._conversation_mode_var,
            values=CONVERSATION_MODES,
            state="readonly",
            width=250,
            command=self._on_conversation_mode_changed,
        )
        self._conversation_mode_box.grid(row=0, column=1, padx=(0, 14), pady=(16, 10), sticky="w")
        self._conversation_start_button = ctk.CTkButton(
            controls, text="Start conversation", width=165, command=self._start_conversation_topic
        )
        self._conversation_start_button.grid(row=0, column=4, padx=(8, 8), pady=(16, 10), sticky="e")
        ctk.CTkButton(controls, text="Reset", width=82, command=self._reset_conversation).grid(
            row=0, column=5, padx=(0, 18), pady=(16, 10), sticky="e"
        )

        # Shared language/level settings come from the global Learning Profile.
        ctk.CTkLabel(controls, text="Learning profile").grid(
            row=1, column=0, padx=(18, 8), pady=(0, 10), sticky="w"
        )
        ctk.CTkLabel(
            controls,
            textvariable=self._profile_summary_var,
            anchor="w",
            text_color=("gray25", "gray80"),
        ).grid(row=1, column=1, columnspan=4, padx=(0, 14), pady=(0, 10), sticky="ew")
        ctk.CTkButton(
            controls,
            text="Edit profile",
            width=105,
            command=self._open_profile_tab,
        ).grid(row=1, column=5, padx=(0, 18), pady=(0, 10), sticky="e")

        self._conversation_topic_frame = ctk.CTkFrame(controls, fg_color="transparent")
        self._conversation_topic_frame.grid(row=2, column=0, columnspan=6, sticky="ew", padx=18, pady=(2, 10))
        self._conversation_topic_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            self._conversation_topic_frame, text="Topic", font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, padx=(0, 10), sticky="w")
        self._conversation_topic_entry = ctk.CTkEntry(
            self._conversation_topic_frame,
            textvariable=self._topic_var,
            placeholder_text="e.g. daily life, travel, an interview, cooking...",
            height=38,
        )
        self._conversation_topic_entry.grid(row=0, column=1, sticky="ew")

        self._conversation_flashcard_settings_frame = ctk.CTkFrame(controls, fg_color="transparent")
        self._conversation_flashcard_settings_frame.grid(
            row=2, column=0, columnspan=6, sticky="ew", padx=18, pady=(2, 10)
        )
        self._conversation_flashcard_settings_frame.grid_columnconfigure((1, 3, 5), weight=1)
        ctk.CTkLabel(
            self._conversation_flashcard_settings_frame, text="Flashcard source", font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, padx=(0, 8), pady=(0, 8), sticky="w")
        self._conversation_source_box = ctk.CTkComboBox(
            self._conversation_flashcard_settings_frame,
            variable=self._conversation_flashcard_source_var,
            values=CONVERSATION_FLASHCARD_SOURCES,
            state="readonly",
            width=180,
            command=self._on_conversation_source_changed,
        )
        self._conversation_source_box.grid(row=0, column=1, padx=(0, 12), pady=(0, 8), sticky="ew")
        ctk.CTkLabel(self._conversation_flashcard_settings_frame, text="Deck").grid(
            row=0, column=2, padx=(8, 8), pady=(0, 8), sticky="e"
        )
        self._conversation_deck_box = ctk.CTkComboBox(
            self._conversation_flashcard_settings_frame,
            variable=self._conversation_deck_var,
            values=[self._anki_client.deck_name],
            state="readonly",
            width=190,
            command=lambda _value: self._on_conversation_source_changed(),
        )
        self._conversation_deck_box.grid(row=0, column=3, padx=(0, 8), pady=(0, 8), sticky="ew")
        self._conversation_refresh_decks_button = ctk.CTkButton(
            self._conversation_flashcard_settings_frame, text="Refresh decks", width=125, command=self._refresh_conversation_decks
        )
        self._conversation_refresh_decks_button.grid(row=0, column=4, padx=(0, 8), pady=(0, 8), sticky="e")
        ctk.CTkLabel(self._conversation_flashcard_settings_frame, text="Selection").grid(
            row=1, column=0, padx=(0, 8), pady=(0, 4), sticky="w"
        )
        self._conversation_selection_box = ctk.CTkComboBox(
            self._conversation_flashcard_settings_frame,
            variable=self._conversation_selection_var,
            values=SELECTION_MODES,
            state="readonly",
            command=lambda _value: self._refresh_conversation_flashcard_status(),
        )
        self._conversation_selection_box.grid(row=1, column=1, padx=(0, 12), pady=(0, 4), sticky="ew")
        ctk.CTkLabel(
            self._conversation_flashcard_settings_frame,
            textvariable=self._conversation_flashcard_status_var,
            text_color=("gray35", "gray75"),
            wraplength=760,
            justify="left",
        ).grid(row=1, column=2, columnspan=4, padx=(8, 0), pady=(0, 4), sticky="w")

        audio = ctk.CTkFrame(controls, corner_radius=12)
        audio.grid(row=3, column=0, columnspan=6, sticky="ew", padx=18, pady=(0, 10))
        audio.grid_columnconfigure((1, 3, 5), weight=1)
        ctk.CTkLabel(audio, text="Tutor audio", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, padx=(12, 8), pady=10, sticky="w"
        )
        self._conversation_tts_provider_box = ctk.CTkComboBox(
            audio,
            variable=self._conversation_tts_provider_var,
            values=list(self._speech_service.providers) if self._speech_service else [],
            state="readonly" if self._speech_service else "disabled",
            width=170,
            command=lambda _value: self._sync_conversation_tts_defaults(),
        )
        self._conversation_tts_provider_box.grid(row=0, column=1, padx=(0, 12), pady=10, sticky="ew")
        ctk.CTkLabel(audio, text="Voice").grid(row=0, column=2, padx=(8, 8), pady=10, sticky="e")
        self._conversation_tts_voice_box = ctk.CTkComboBox(
            audio,
            variable=self._conversation_tts_voice_var,
            values=[],
            state="readonly" if self._speech_service else "disabled",
            width=210,
        )
        self._conversation_tts_voice_box.grid(row=0, column=3, padx=(0, 12), pady=10, sticky="ew")
        ctk.CTkLabel(audio, text="TTS model").grid(row=0, column=4, padx=(8, 8), pady=10, sticky="e")
        self._conversation_tts_model_box = ctk.CTkComboBox(
            audio,
            variable=self._conversation_tts_model_var,
            values=[],
            state="readonly" if self._speech_service else "disabled",
            width=180,
        )
        self._conversation_tts_model_box.grid(row=0, column=5, padx=(0, 12), pady=10, sticky="ew")

        advanced = ctk.CTkFrame(controls, fg_color="transparent")
        advanced.grid(row=4, column=0, columnspan=6, sticky="ew", padx=18, pady=(0, 14))
        advanced.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(advanced, text="Advanced", text_color=("gray35", "gray75")).grid(
            row=0, column=0, padx=(0, 8), sticky="w"
        )
        self._conversation_provider_box = ctk.CTkComboBox(
            advanced,
            variable=self._conversation_provider_var,
            values=list(self._ai_clients.keys()) or ["Not configured"],
            state="readonly" if self._ai_clients else "disabled",
            width=180,
        )
        self._conversation_provider_box.grid(row=0, column=1, padx=(0, 12), sticky="w")
        ctk.CTkSwitch(
            advanced,
            text="Detailed coaching",
            variable=self._conversation_detailed_feedback_var,
            onvalue=True,
            offvalue=False,
        ).grid(row=0, column=2, sticky="e")

        self._sync_conversation_tts_defaults()

        chat_panel = ctk.CTkFrame(layout, corner_radius=18)
        chat_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        chat_panel.grid_columnconfigure(0, weight=1)
        chat_panel.grid_rowconfigure(1, weight=1)
        chat_header = ctk.CTkFrame(chat_panel, fg_color="transparent")
        chat_header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        chat_header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            chat_header,
            text="Conversation",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            chat_header,
            text="Export conversation",
            width=165,
            command=self._export_conversation,
        ).grid(row=0, column=1, sticky="e")
        self._chat_text = ctk.CTkTextbox(chat_panel, wrap="word", font=ctk.CTkFont(size=14))
        self._chat_text.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))
        self._chat_text.insert(
            "1.0",
            "Choose a mode. Start with a topic or use flashcards from an Anki deck or Queue.\n",
        )
        self._chat_text.configure(state="disabled")

        input_row = ctk.CTkFrame(chat_panel, fg_color="transparent")
        input_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        input_row.grid_columnconfigure(0, weight=1)
        self._message_input = ctk.CTkTextbox(input_row, height=78, wrap="word", font=ctk.CTkFont(size=14))
        self._message_input.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ctk.CTkButton(input_row, text="Send", width=120, height=78, command=self._send_conversation_message).grid(
            row=0, column=1, sticky="e"
        )

        speech_row = ctk.CTkFrame(chat_panel, fg_color="transparent")
        speech_row.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 18))
        speech_row.grid_columnconfigure(4, weight=1)
        self._record_button = ctk.CTkButton(
            speech_row,
            text="Record answer",
            width=130,
            command=self._start_conversation_recording,
        )
        self._record_button.grid(row=0, column=0, padx=(0, 8), pady=(0, 6), sticky="w")
        self._stop_record_button = ctk.CTkButton(
            speech_row,
            text="Stop & transcribe",
            width=150,
            command=self._stop_conversation_recording,
        )
        self._stop_record_button.grid(row=0, column=1, padx=(0, 8), pady=(0, 6), sticky="w")
        ctk.CTkButton(
            speech_row,
            text="Play last recording",
            width=150,
            command=self._play_last_conversation_recording,
        ).grid(row=0, column=2, padx=(0, 8), pady=(0, 6), sticky="w")
        ctk.CTkButton(
            speech_row,
            text="Open recording folder",
            width=165,
            command=self._open_last_conversation_recording,
        ).grid(row=0, column=3, padx=(0, 12), pady=(0, 6), sticky="w")
        ctk.CTkLabel(
            speech_row,
            textvariable=self._stt_status_var,
            text_color=("gray35", "gray70"),
            anchor="w",
        ).grid(row=0, column=4, sticky="ew", pady=(0, 6))

        ctk.CTkButton(
            speech_row,
            text="Read tutor reply",
            width=140,
            command=self._read_conversation_tutor_reply_aloud,
        ).grid(row=1, column=0, padx=(0, 8), pady=(2, 6), sticky="w")
        ctk.CTkButton(
            speech_row,
            text="Read question",
            width=130,
            command=self._read_conversation_question_aloud,
        ).grid(row=1, column=1, padx=(0, 8), pady=(2, 6), sticky="w")
        ctk.CTkButton(
            speech_row,
            text="Stop audio",
            width=110,
            command=self._stop_conversation_audio,
        ).grid(row=1, column=2, padx=(0, 8), pady=(2, 6), sticky="w")
        audio_options = ctk.CTkFrame(speech_row, fg_color="transparent")
        audio_options.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(2, 0))
        ctk.CTkSwitch(
            audio_options,
            text="Auto-read tutor",
            variable=self._conversation_auto_read_tutor_var,
            onvalue=True,
            offvalue=False,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkSwitch(
            audio_options,
            text="Auto-read question",
            variable=self._conversation_auto_read_question_var,
            onvalue=True,
            offvalue=False,
        ).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(
            audio_options,
            textvariable=self._conversation_audio_status_var,
            text_color=("gray35", "gray70"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        vocab_panel = ctk.CTkScrollableFrame(layout, corner_radius=18)
        vocab_panel.grid(row=1, column=1, sticky="nsew")
        vocab_panel.grid_columnconfigure(0, weight=1)

        self._conversation_suggestions_title_label = ctk.CTkLabel(
            vocab_panel,
            text="AI suggestions",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        self._conversation_suggestions_title_label.grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 4)
        )
        self._conversation_suggestions_help_label = ctk.CTkLabel(
            vocab_panel,
            text="Checkbox → edit/remove → stage here → send to Queue. No direct Anki write here.",
            text_color=("gray35", "gray75"),
            wraplength=430,
            justify="left",
        )
        self._conversation_suggestions_help_label.grid(
            row=1, column=0, sticky="w", padx=18, pady=(0, 8)
        )

        self._conversation_use_next_label = ctk.CTkLabel(
            vocab_panel,
            text="Expressions to use next — practice cues, not new cards",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self._conversation_use_next_label.grid(
            row=2, column=0, sticky="w", padx=18, pady=(2, 4)
        )
        self._conversation_use_next_text = ctk.CTkTextbox(
            vocab_panel,
            wrap="word",
            height=82,
            font=ctk.CTkFont(size=12),
        )
        self._conversation_use_next_text.grid(
            row=3, column=0, sticky="ew", padx=18, pady=(0, 8)
        )
        self._set_conversation_readonly_text(
            self._conversation_use_next_text,
            "The tutor will place relevant speaking cues here after your answer.",
        )

        self._conversation_candidates_label = ctk.CTkLabel(
            vocab_panel,
            text="New flashcard candidates — accumulated this session",
            font=ctk.CTkFont(size=15, weight="bold"),
        )
        self._conversation_candidates_label.grid(
            row=4, column=0, sticky="w", padx=18, pady=(2, 4)
        )
        self._suggestions_frame = ctk.CTkScrollableFrame(vocab_panel, height=150, corner_radius=14)
        self._suggestions_frame.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 10))
        self._render_suggestions([])

        self._conversation_suggestion_buttons = ctk.CTkFrame(vocab_panel, fg_color="transparent")
        self._conversation_suggestion_buttons.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 10))
        self._conversation_suggestion_buttons.grid_columnconfigure((0, 1, 2), weight=1)
        self._conversation_stage_selected_button = ctk.CTkButton(
            self._conversation_suggestion_buttons,
            text="Stage selected",
            command=self._add_selected_suggestions_to_queue,
        )
        self._conversation_stage_selected_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self._conversation_stage_all_button = ctk.CTkButton(
            self._conversation_suggestion_buttons,
            text="Stage all",
            command=self._add_all_suggestions_to_queue,
        )
        self._conversation_stage_all_button.grid(row=0, column=1, sticky="ew", padx=4)
        self._conversation_clear_candidates_button = ctk.CTkButton(
            self._conversation_suggestion_buttons,
            text="Clear candidates",
            command=self._clear_conversation_candidates,
        )
        self._conversation_clear_candidates_button.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        ctk.CTkLabel(vocab_panel, text="Custom word or phrase").grid(
            row=7, column=0, sticky="w", padx=18, pady=(2, 4)
        )
        custom = ctk.CTkFrame(vocab_panel, fg_color="transparent")
        custom.grid(row=8, column=0, sticky="ew", padx=18, pady=(0, 12))
        custom.grid_columnconfigure(0, weight=1)
        self._custom_phrase_var = ctk.StringVar()
        ctk.CTkEntry(custom, textvariable=self._custom_phrase_var, height=36).grid(
            row=0, column=0, sticky="ew", padx=(0, 8)
        )
        ctk.CTkButton(custom, text="Add", width=70, command=self._add_custom_phrase_to_queue).grid(
            row=0, column=1
        )

        ctk.CTkLabel(
            vocab_panel,
            text="Staged for Queue",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=9, column=0, sticky="sw", padx=18, pady=(0, 4))
        ctk.CTkLabel(
            vocab_panel,
            textvariable=self._conversation_queue_log_var,
            text_color=("gray35", "gray75"),
            wraplength=430,
            justify="left",
        ).grid(row=10, column=0, sticky="ew", padx=18, pady=(0, 6))
        self._queue_text = ctk.CTkTextbox(vocab_panel, wrap="word", height=140, font=ctk.CTkFont(size=13))
        self._queue_text.grid(row=11, column=0, sticky="ew", padx=18, pady=(0, 10))
        self._refresh_queue_text()

        queue_buttons = ctk.CTkFrame(vocab_panel, fg_color="transparent")
        queue_buttons.grid(row=12, column=0, sticky="ew", padx=18, pady=(0, 14))
        queue_buttons.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(queue_buttons, text="Clear staged", command=self._clear_queue).grid(
            row=0, column=0, sticky="ew", pady=(0, 6)
        )
        ctk.CTkButton(
            queue_buttons,
            text="Send to Queue",
            command=self._send_conversation_queue_to_batch,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkButton(
            queue_buttons,
            text="Open Queue",
            command=self._open_batch_queue_tab,
        ).grid(row=2, column=0, sticky="ew")

        self._conversation_session_toggle_button = ctk.CTkButton(
            vocab_panel,
            textvariable=self._conversation_session_title_var,
            anchor="w",
            fg_color="transparent",
            border_width=1,
            command=self._toggle_conversation_session_cards,
        )
        self._conversation_session_toggle_button.grid(
            row=13, column=0, sticky="ew", padx=18, pady=(2, 6)
        )
        self._conversation_session_label = self._conversation_session_toggle_button
        self._conversation_session_text = ctk.CTkTextbox(
            vocab_panel,
            wrap="word",
            height=130,
            font=ctk.CTkFont(size=12),
        )
        self._conversation_session_text.grid(
            row=14, column=0, sticky="ew", padx=18, pady=(0, 18)
        )
        self._set_conversation_readonly_text(
            self._conversation_session_text,
            "Start a flashcard conversation to load the session targets.",
        )
        self._conversation_session_text.grid_remove()

        self._on_conversation_mode_changed(self._conversation_mode_var.get())

    def _open_batch_queue_tab(self) -> None:
        try:
            self._tabs.set("Queue")
            self._status_var.set("Queue opened. Review staged conversation items there before adding to Anki.")
        except Exception:
            self._status_var.set("Could not switch to Queue automatically.")

    def _build_batch_tab(self, parent: ctk.CTkFrame) -> None:
        """Build the structured Queue workflow."""
        layout = ctk.CTkFrame(parent, fg_color="transparent")
        layout.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        layout.grid_columnconfigure(0, weight=0)
        layout.grid_columnconfigure(1, weight=1)
        layout.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(layout, corner_radius=18, width=395)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left, text="Queue", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=18, pady=(18, 4)
        )
        ctk.CTkLabel(
            left,
            text="Fast path for clean, structured input. Choose the input type BEFORE loading. For lessons, HTML, PDFs, screenshots or messy material, use Import Material instead.",
            wraplength=345, justify="left", text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

        mode_card = ctk.CTkFrame(left, corner_radius=12)
        mode_card.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 12))
        mode_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(mode_card, text="1 · Choose input type", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 4)
        )
        ctk.CTkComboBox(
            mode_card, variable=self._batch_mode_var, values=BATCH_MODES, state="readonly",
            command=self._on_batch_mode_changed,
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        ctk.CTkLabel(
            mode_card, textvariable=self._batch_mode_help_var, wraplength=325, justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=2, column=0, sticky="w", padx=12, pady=(0, 10))

        load_card = ctk.CTkFrame(left, corner_radius=12)
        load_card.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 12))
        load_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(load_card, text="2 · Load clean input", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=12, pady=(10, 6)
        )
        file_buttons = ctk.CTkFrame(load_card, fg_color="transparent")
        file_buttons.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        file_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(file_buttons, text="Load TXT", command=self._load_batch_txt).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(file_buttons, text="Load CSV", command=self._load_batch_csv).grid(
            row=0, column=1, sticky="ew", padx=(5, 0)
        )
        self._batch_paste_label = ctk.CTkLabel(
            load_card, text="Paste one clean item per line.", wraplength=325, justify="left"
        )
        self._batch_paste_label.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 4))
        self._batch_paste_text = ctk.CTkTextbox(load_card, height=105, wrap="word")
        self._batch_paste_text.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        ctk.CTkButton(load_card, text="Load pasted list", command=self._load_pasted_batch).grid(
            row=4, column=0, sticky="ew", padx=12, pady=(0, 8)
        )
        ctk.CTkLabel(
            load_card, textvariable=self._batch_source_summary_var, wraplength=325, justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=5, column=0, sticky="w", padx=12, pady=(0, 10))

        ctk.CTkLabel(left, text="Queue topic / context (optional)").grid(
            row=4, column=0, sticky="w", padx=18, pady=(2, 4)
        )
        self._batch_topic_box = ctk.CTkComboBox(left, variable=self._batch_topic_var, values=TOPIC_PRESETS)
        self._batch_topic_box.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 8))
        ctk.CTkLabel(
            left, textvariable=self._profile_summary_var,
            text_color=("gray35", "gray75"),
        ).grid(row=6, column=0, sticky="w", padx=18, pady=(2, 10))
        ctk.CTkLabel(
            left, text="Language/level come from your Learning Profile; the final Anki deck comes from the top bar.",
            wraplength=345,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=7, column=0, sticky="w", padx=18, pady=(0, 10))

        session_buttons = ctk.CTkFrame(left, fg_color="transparent")
        session_buttons.grid(row=8, column=0, sticky="ew", padx=18, pady=(0, 8))
        session_buttons.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(session_buttons, text="Save session", command=self._save_batch_session).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(session_buttons, text="Resume latest", command=self._resume_latest_batch_session).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ctk.CTkButton(session_buttons, text="Load file…", command=self._resume_batch_session).grid(
            row=0, column=2, sticky="ew", padx=(5, 0)
        )
        ctk.CTkButton(left, text="Clear queue", command=self._clear_batch).grid(
            row=9, column=0, sticky="ew", padx=18, pady=(0, 18)
        )

        right = ctk.CTkFrame(layout, corner_radius=18)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Review before generation", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(
            header, textvariable=self._batch_progress_var, justify="right", anchor="e", wraplength=640
        ).grid(row=0, column=1, sticky="e")
        self._batch_progress_bar = ctk.CTkProgressBar(header, height=8)
        self._batch_progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self._batch_progress_bar.set(0)

        ctk.CTkLabel(right, text="Current parsed item").grid(row=1, column=0, sticky="w", padx=18, pady=(4, 4))
        current_row = ctk.CTkFrame(right, fg_color="transparent")
        current_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        current_row.grid_columnconfigure(0, weight=1)
        self._batch_word_entry = ctk.CTkEntry(current_row, textvariable=self._batch_word_var, height=40)
        self._batch_word_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(current_row, text="Save item edit", width=130, command=self._save_current_batch_item_edit).grid(
            row=0, column=1, padx=(0, 8)
        )
        ctk.CTkButton(
            current_row, text="Generate card", width=160,
            command=lambda: self._generate_current_batch_card("generate_selected"),
        ).grid(row=0, column=2)

        ctk.CTkLabel(
            right, textvariable=self._batch_status_var, text_color=("gray35", "gray75"), anchor="w",
        ).grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 6))

        self._batch_preview = ctk.CTkTextbox(right, wrap="word", font=ctk.CTkFont(size=14))
        self._batch_preview.grid(row=4, column=0, sticky="nsew", padx=18, pady=(0, 12))
        self._batch_preview.insert("1.0", "Choose a mode, load clean input, and review the parsed rows before generating anything.")
        self._batch_preview.bind("<Double-Button-1>", lambda _event: self._open_batch_card_editor())
        self._batch_preview.configure(state="disabled")

        ctk.CTkLabel(right, text="Current card actions", text_color=("gray35", "gray75")).grid(
            row=5, column=0, sticky="w", padx=18, pady=(0, 4)
        )
        buttons = ctk.CTkFrame(right, fg_color="transparent")
        buttons.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 12))
        buttons.grid_columnconfigure((0, 1, 2, 3), weight=1)
        current_actions = [
            ("Previous", self._batch_previous),
            ("Skip", self._skip_current_batch_item),
            ("Add this card", self._add_current_batch_card),
            ("Regenerate", lambda: self._generate_current_batch_card("regenerate_selected")),
            ("Edit card", self._open_batch_card_editor),
            ("Approve warning", self._approve_current_quality_warning),
            ("Remove item", self._remove_current_batch_item),
            ("Next", self._batch_next),
        ]
        for index, (label, command) in enumerate(current_actions):
            row, col = divmod(index, 4)
            ctk.CTkButton(buttons, text=label, command=command).grid(
                row=row, column=col, sticky="ew", padx=4, pady=4
            )

        ctk.CTkLabel(right, text="All queue actions", text_color=("gray35", "gray75")).grid(
            row=7, column=0, sticky="w", padx=18, pady=(0, 4)
        )
        bulk_buttons = ctk.CTkFrame(right, fg_color="transparent")
        bulk_buttons.grid(row=8, column=0, sticky="ew", padx=18, pady=(0, 12))
        bulk_buttons.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        for col, (label, command) in enumerate([
            ("Generate pending", self._auto_generate_pending_batch_cards),
            ("Retry problems", self._retry_failed_or_rate_limited_batch_cards),
            ("Add all ready", self._start_add_all_ready_batch_cards),
            ("Pause", self._pause_batch_process),
            ("Stop", self._stop_batch_process),
        ]):
            ctk.CTkButton(bulk_buttons, text=label, command=command).grid(
                row=0, column=col, sticky="ew", padx=4
            )

        self._batch_issue_label = ctk.CTkLabel(right, text="Problems", text_color=("gray35", "gray75"))
        self._batch_issue_label.grid(row=9, column=0, sticky="w", padx=18, pady=(0, 4))
        issue_buttons = ctk.CTkFrame(right, fg_color="transparent")
        self._batch_issue_buttons_frame = issue_buttons
        issue_buttons.grid(row=10, column=0, sticky="ew", padx=18, pady=(0, 18))
        issue_buttons.grid_columnconfigure((0, 1, 2), weight=1)
        ctk.CTkButton(issue_buttons, text="Go to first problem", command=self._go_to_first_blocked_batch_item).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(issue_buttons, text="Next problem", command=self._go_to_next_batch_issue).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ctk.CTkButton(issue_buttons, text="Show issue summary", command=self._show_batch_issue_summary).grid(
            row=0, column=2, sticky="ew", padx=(5, 0)
        )
        self._update_batch_mode_help()
        self._refresh_batch_issue_visibility()

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

    def _update_batch_mode_help(self) -> None:
        mode = (self._batch_mode_var.get() or "Vocabulary").strip()
        help_text = {
            "Vocabulary": "Vocabulary: one clean word or phrase per row. CSV uses the first column as the Word target.",
            "Grammar": "Grammar: use a natural sentence, or target | sentence when you already know the grammar focus.",
            "Provided examples": "Provided examples: target | exact source sentence. For CSV, column 1 = target and column 2 = sentence.",
            "Mixed": "Mixed: for already prepared rows only. If your source needs interpretation, use Import Material instead.",
        }.get(mode, "Choose the format that matches your clean input.")
        self._batch_mode_help_var.set(help_text)
        paste_label = getattr(self, "_batch_paste_label", None)
        if paste_label is not None:
            if mode == "Provided examples":
                paste_label.configure(text="Paste one row per line: target | exact source sentence")
            elif mode == "Grammar":
                paste_label.configure(text="Paste one sentence per line, or grammar target | sentence")
            elif mode == "Mixed":
                paste_label.configure(text="Paste already prepared rows. Use Import Material for raw/messy sources.")
            else:
                paste_label.configure(text="Paste one clean word or phrase per line.")

    @staticmethod
    def _batch_rows_from_csv(rows: list[list[str]], mode: str) -> list[str]:
        """Convert clean CSV rows into Queue text rows without guessing after load."""
        result: list[str] = []
        mode = (mode or "Vocabulary").strip()
        for index, row in enumerate(rows):
            cells = [str(cell).strip() for cell in row]
            if not any(cells):
                continue
            first = cells[0] if cells else ""
            second = cells[1] if len(cells) > 1 else ""
            if index == 0:
                first_key = first.casefold()
                second_key = second.casefold()
                if first_key in {"word", "word_or_phrase", "phrase", "vocabulary", "target", "term", "grammar target"}:
                    if not second or second_key in {"sentence", "example", "source sentence", "provided example", "example sentence"}:
                        continue
            if mode in {"Provided examples", "Grammar"} and second:
                result.append(f"{first} | {second}" if first else second)
            elif mode == "Mixed" and second:
                result.append(" | ".join(cell for cell in cells[:2] if cell))
            elif first:
                result.append(first)
        return result

    @staticmethod
    def _queue_mode_from_imported_item_types(items: list[dict[str, object]]) -> str | None:
        """Return the Queue-wide display mode implied by typed Import Material rows.

        Import Material owns the type of each imported row.  The Queue-wide selector
        is only a display/default for that structured import and must never collapse a
        heterogeneous import to the type of whichever item happens to be selected.
        """
        modes = {
            str(item.get("batch_mode") or "").strip()
            for item in items
            if bool(item.get("mode_locked"))
            and str(item.get("batch_mode") or "").strip() in BATCH_MODES
        }
        if not modes:
            return None
        if len(modes) == 1:
            return next(iter(modes))
        return "Mixed"

    def _on_batch_mode_changed(self, selected: str | None = None) -> None:
        """Apply a user-selected Queue mode to not-yet-generated items.

        The Queue mode combobox is a session-level setting. In v8.1.5.3 it
        could be overwritten by the currently selected item's stored
        ``batch_mode`` after loading a list, so clicking Grammar and then
        Generate appeared to switch back to Vocabulary. This handler makes
        the user's explicit choice authoritative for pending/not-generated
        rows. Generated/reviewed rows keep their stored mode.
        """
        mode = (selected or self._batch_mode_var.get() or "Vocabulary").strip()
        if mode not in BATCH_MODES:
            mode = "Vocabulary"
        self._batch_mode_var.set(mode)
        self._update_batch_mode_help()

        changed = 0
        for item in self._batch_items:
            if bool(item.get("mode_locked")):
                # Import Material already classified this row. The Queue-wide
                # input type is only for manually loaded clean files.
                continue
            status = str(item.get("status", "pending"))
            has_generated_payload = bool(item.get("card") or item.get("grammar_card"))
            if has_generated_payload or status in {
                "ready",
                "added_to_anki",
                "updated_in_anki",
                "duplicate_found",
                "duplicate_uncertain",
                "duplicate_skipped",
                "blocked_quality_warning",
                "invalid",
                "skipped",
            }:
                continue
            item["batch_mode"] = mode
            item.pop("resolved_mode", None)
            changed += 1

        if self._batch_items:
            self._show_current_batch_item(generate=False)
            self._autosave_batch_session("queue mode changed")
            if changed:
                self._record_activity(f"Queue mode set to {mode} for {changed} pending item(s)")


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

    def _set_batch_words(self, words: list[str], source_label: str = "manual input") -> None:
        clean_words = self._normalise_batch_words(words)
        if not clean_words:
            messagebox.showwarning("Empty list", "No words or phrases were found.")
            return
        topic = self._batch_topic_var.get().strip()
        batch_mode = self._batch_mode_var.get().strip() or "Vocabulary"
        self._batch_items = [
            {
                "word": word,
                "status": "pending",
                "topic": topic,
                "batch_mode": batch_mode,
                "target_language": self._language_var.get(),
                "explanation_language": self._explanation_language_var.get(),
            }
            for word in clean_words
        ]
        self._batch_index = 0
        self._batch_autosave_path = None
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        self._batch_generated_grammar = None
        self._show_current_batch_item(generate=False)
        self._cleanup_runtime_memory("queue list loaded", aggressive=False)
        self._batch_source_summary_var.set(
            f"Loaded {len(clean_words)} row(s) from {source_label} as {batch_mode}. Review the parsed rows before Generate pending."
        )
        self._batch_status_var.set(
            f"Loaded {len(clean_words)} row(s) as {batch_mode}. Nothing has been generated yet."
        )
        self._record_activity(f"Loaded {len(clean_words)} queue item(s) as {batch_mode} without generation")
        self._autosave_batch_session("list loaded")

    def _load_batch_txt(self) -> None:
        filename = filedialog.askopenfilename(
            title="Load clean Queue TXT",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not filename:
            return
        try:
            words = Path(filename).read_text(encoding="utf-8-sig").splitlines()
        except Exception as exc:
            messagebox.showerror("File error", str(exc))
            return
        self._set_batch_words(words, source_label=Path(filename).name)

    def _load_batch_csv(self) -> None:
        filename = filedialog.askopenfilename(
            title="Load clean Queue CSV",
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
        mode = self._batch_mode_var.get().strip() or "Vocabulary"
        words = self._batch_rows_from_csv(rows, mode)
        self._set_batch_words(words, source_label=f"{Path(filename).name} ({mode})")

    def _load_pasted_batch(self) -> None:
        words = self._batch_paste_text.get("1.0", "end").splitlines()
        self._set_batch_words(words, source_label="pasted text")

    def _ocr_set_source_paths(self, paths: list[str]) -> None:
        self._ocr_source_paths = [Path(path) for path in paths]
        if not self._ocr_source_paths:
            method_label = getattr(self, "_ocr_method_label", None)
            method_box = getattr(self, "_ocr_method_box", None)
            if method_label is not None:
                method_label.grid()
            if method_box is not None:
                method_box.grid()
            self._ocr_status_var.set("No import source selected.")
            self._ocr_route_var.set("Choose a source to see how it will be read.")
            return
        names = ", ".join(path.name for path in self._ocr_source_paths[:3])
        if len(self._ocr_source_paths) > 3:
            names += f" + {len(self._ocr_source_paths) - 3} more"
        suffixes = {path.suffix.casefold() for path in self._ocr_source_paths}
        text_like = bool(suffixes) and suffixes <= (TEXT_EXTENSIONS | HTML_EXTENSIONS)
        method_label = getattr(self, "_ocr_method_label", None)
        method_box = getattr(self, "_ocr_method_box", None)
        if text_like:
            # Reading plain text is not an OCR/model choice. Hide those controls
            # completely so the user cannot mistake local file reading for AI.
            if method_label is not None:
                method_label.grid_remove()
            if method_box is not None:
                method_box.grid_remove()
            # TXT/HTML are already text sources. Never make the user route them
            # through OCR just because an OCR provider was selected earlier.
            self._ocr_method_var.set("Local extraction (free)")
            self._ocr_route_var.set("TXT/HTML → read locally → review text → find candidates. No model, OCR or API is used to read the file.")
            action = "Read material locally"
            self._ocr_status_var.set(f"Text source selected: {names}. It will be read locally; no AI/model is used. Click {action}.")
            button = getattr(self, "_ocr_run_button", None)
            if button is not None:
                button.configure(text=action)
        elif suffixes and suffixes <= OCR_IMAGE_EXTENSIONS:
            if method_label is not None:
                method_label.grid()
            if method_box is not None:
                method_box.grid()
            action = self._ocr_import_action_label()
            self._ocr_route_var.set("Image/scan → selected OCR/vision method → review text → candidate finder.")
            self._ocr_status_var.set(
                f"Image loaded: {names}. No OCR has started. Choose an OCR method, then click {action}."
            )
        else:
            if method_label is not None:
                method_label.grid()
            if method_box is not None:
                method_box.grid()
            action = self._ocr_import_action_label()
            self._ocr_route_var.set("PDF/mixed source → read text locally when possible, otherwise OCR/vision → review → candidate search.")
            self._ocr_status_var.set(f"Selected: {names}. Nothing has been read yet. Click {action}.")
        self._ocr_candidate_status_var.set("Source selected. Read/load the material first, then choose what candidates to find.")
        self._scroll_import_text_to_top()

    def _open_paste_material_dialog(self) -> None:
        """Paste raw text or a clipboard screenshot into the Import Material flow.

        Text is written directly to Source text. Clipboard images are
        saved into .import_cache and staged only. OCR/import must be started by
        an explicit button click, so loading a screenshot never spends credits or
        freezes the UI by surprise.
        """
        dialog = tk.Toplevel(self._root)
        dialog.title("Paste text or screenshot")
        dialog.geometry("780x560")
        dialog.transient(self._root)
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(2, weight=1)

        staged_paths: list[Path] = []
        info_var = tk.StringVar(
            value="Paste text, paste a screenshot from the clipboard, or open a file."
        )

        tk.Label(
            dialog,
            text="Paste or import material",
            font=("TkDefaultFont", 12, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        tk.Label(
            dialog,
            textvariable=info_var,
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        material_box = tk.Text(dialog, height=14, wrap="word")
        material_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        material_box.insert(
            "1.0",
            "Paste plain text here, or click 'Paste text from clipboard'.\n"
            "For screenshots, copy a screenshot first, then click 'Paste screenshot from clipboard'.",
        )
        material_box.tag_add("hint", "1.0", "end")
        material_box.tag_configure("hint", foreground="gray")

        def clear_hint_if_needed() -> None:
            if material_box.tag_ranges("hint"):
                material_box.delete("1.0", "end")
                material_box.tag_remove("hint", "1.0", "end")

        material_box.bind("<FocusIn>", lambda _event: clear_hint_if_needed())
        material_box.bind("<Key>", lambda _event: clear_hint_if_needed())

        def paste_text_from_clipboard() -> None:
            try:
                value = self._root.clipboard_get()
            except tk.TclError:
                messagebox.showwarning("Paste material", "Clipboard does not contain plain text.")
                return
            value = clean_ocr_text(value)
            if not value.strip():
                messagebox.showwarning("Paste material", "Clipboard text is empty.")
                return
            staged_paths.clear()
            material_box.delete("1.0", "end")
            material_box.tag_remove("hint", "1.0", "end")
            material_box.insert("1.0", value)
            info_var.set(f"Text pasted: {len(value.split())} word(s). Click Use this material.")

        def save_clipboard_image_to_cache() -> list[Path]:
            try:
                from PIL import ImageGrab  # type: ignore[import-not-found]
            except ImportError as exc:
                raise OcrExtractionError(
                    "Clipboard screenshot import needs Pillow. Install it with: pip install pillow"
                ) from exc

            try:
                clipboard_value = ImageGrab.grabclipboard()
            except Exception as exc:
                raise OcrExtractionError(f"Could not read an image from clipboard: {exc}") from exc

            if clipboard_value is None:
                raise OcrExtractionError(
                    "Clipboard does not contain a screenshot/image. Copy a screenshot first."
                )

            if isinstance(clipboard_value, list):
                paths = [Path(value) for value in clipboard_value]
                supported = [
                    path for path in paths
                    if path.suffix.casefold() in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".pdf"}
                ]
                if not supported:
                    raise OcrExtractionError("Clipboard contains files, but not supported image/PDF files.")
                return supported

            if not hasattr(clipboard_value, "save"):
                raise OcrExtractionError("Clipboard item is not a supported image.")

            cache_dir = Path(".import_cache")
            cache_dir.mkdir(exist_ok=True)
            image_path = cache_dir / f"clipboard_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            image = clipboard_value
            try:
                if getattr(image, "mode", "RGB") not in {"RGB", "RGBA"}:
                    image = image.convert("RGB")
                image.save(image_path)
            except Exception as exc:
                raise OcrExtractionError(f"Could not save clipboard screenshot: {exc}") from exc
            return [image_path]

        def paste_screenshot_from_clipboard() -> None:
            try:
                paths = save_clipboard_image_to_cache()
            except OcrExtractionError as exc:
                messagebox.showwarning("Paste screenshot", str(exc))
                return
            staged_paths[:] = paths
            material_box.delete("1.0", "end")
            material_box.tag_remove("hint", "1.0", "end")
            names = ", ".join(path.name for path in staged_paths[:3])
            if len(staged_paths) > 3:
                names += f" + {len(staged_paths) - 3} more"
            info_var.set(f"Screenshot/file staged: {names}. Click Use this material to load it; OCR will not run yet.")

        def open_file_for_material() -> None:
            filenames = filedialog.askopenfilenames(
                title="Open material file",
                filetypes=[
                    ("Supported files", "*.txt *.md *.html *.htm *.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"),
                    ("All files", "*.*"),
                ],
            )
            if not filenames:
                return
            staged_paths[:] = [Path(filename) for filename in filenames]
            material_box.delete("1.0", "end")
            material_box.tag_remove("hint", "1.0", "end")
            names = ", ".join(path.name for path in staged_paths[:3])
            if len(staged_paths) > 3:
                names += f" + {len(staged_paths) - 3} more"
            info_var.set(f"File(s) staged: {names}. Click Use this material to load it; extraction will not run yet.")

        def clear_material() -> None:
            staged_paths.clear()
            material_box.delete("1.0", "end")
            material_box.tag_remove("hint", "1.0", "end")
            info_var.set("Cleared. Paste text or stage a screenshot/file.")

        def use_material() -> None:
            text_value = material_box.get("1.0", "end").strip()
            if material_box.tag_ranges("hint"):
                text_value = ""
            text_value = clean_ocr_text(text_value)
            if text_value.strip():
                self._ocr_source_paths = []
                self._set_ocr_text(text_value)
                label, reason = self._ocr_quality_label(text_value)
                self._ocr_status_var.set(
                    f"Pasted {len(text_value.split())} word(s). OCR quality: {label} — {reason}. "
                    "Review text, then find candidates."
                )
                self._ocr_candidate_status_var.set("Source text updated. Find candidates next.")
                self._record_activity("Import material pasted as text")
                dialog.destroy()
                return

            if staged_paths:
                self._ocr_set_source_paths([str(path) for path in staged_paths])
                names = ", ".join(path.name for path in staged_paths[:3])
                if len(staged_paths) > 3:
                    names += f" + {len(staged_paths) - 3} more"
                action = self._ocr_import_action_label()
                self._ocr_status_var.set(
                    f"Staged from paste/import: {names}. No OCR has started. Click {action} when ready."
                )
                self._ocr_candidate_status_var.set("Screenshot/file loaded only. No API call or OCR was started.")
                self._record_activity("Import material staged without auto OCR")
                dialog.destroy()
                return

            messagebox.showwarning("Paste material", "Paste text or stage a screenshot/file first.")

        button_row = tk.Frame(dialog)
        button_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        tk.Button(button_row, text="Paste text from clipboard", command=paste_text_from_clipboard).pack(side="left")
        tk.Button(button_row, text="Paste screenshot from clipboard", command=paste_screenshot_from_clipboard).pack(side="left", padx=(8, 0))
        tk.Button(button_row, text="Open image/PDF/TXT", command=open_file_for_material).pack(side="left", padx=(8, 0))
        tk.Button(button_row, text="Clear", command=clear_material).pack(side="left", padx=(8, 0))
        tk.Button(button_row, text="Use this material", command=use_material).pack(side="right")
        tk.Button(button_row, text="Cancel", command=dialog.destroy).pack(side="right", padx=(0, 8))

    def _scroll_widget_to_top(self, widget: object | None, *, delay_ms: int = 60) -> None:
        """Best-effort reset for CTk/Tk scrollable widgets after new content appears."""
        if widget is None:
            return

        def scroll_now() -> None:
            try:
                see = getattr(widget, "see", None)
                if callable(see):
                    see("1.0")
            except Exception:
                pass
            try:
                yview_moveto = getattr(widget, "yview_moveto", None)
                if callable(yview_moveto):
                    yview_moveto(0.0)
            except Exception:
                pass
            try:
                canvas = getattr(widget, "_parent_canvas", None)
                if canvas is not None:
                    canvas.yview_moveto(0.0)
            except Exception:
                pass

        try:
            self._root.after(delay_ms, scroll_now)
            self._root.after(delay_ms + 120, scroll_now)
        except Exception:
            scroll_now()

    def _scroll_import_text_to_top(self) -> None:
        self._scroll_widget_to_top(getattr(self, "_ocr_textbox", None))

    def _scroll_import_candidates_to_top(self) -> None:
        self._scroll_widget_to_top(getattr(self, "_ocr_candidates_frame", None))

    def _scroll_batch_preview_to_top(self) -> None:
        self._scroll_widget_to_top(getattr(self, "_batch_preview", None))

    def _ocr_load_txt(self) -> None:
        filename = filedialog.askopenfilename(
            title="Load TXT / HTML / markdown text",
            filetypes=[
                ("Text and HTML files", "*.txt *.md *.html *.htm"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            self._ocr_set_source_paths([filename])

    def _ocr_load_pdf(self) -> None:
        filename = filedialog.askopenfilename(
            title="Load PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if filename:
            self._ocr_set_source_paths([filename])

    def _ocr_load_image(self) -> None:
        filename = filedialog.askopenfilename(
            title="Load image for import",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if filename:
            self._ocr_set_source_paths([filename])

    def _ocr_load_images(self) -> None:
        filenames = filedialog.askopenfilenames(
            title="Load multiple images for import",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"),
                ("All files", "*.*"),
            ],
        )
        if filenames:
            self._ocr_set_source_paths(list(filenames))

    def _update_ocr_method_ui(self) -> None:
        """Keep the main import button in sync with the selected pipeline."""
        method = self._ocr_method_var.get()
        button = getattr(self, "_ocr_run_button", None)
        if button is not None:
            button.configure(text=self._ocr_import_action_label())
        if self._ocr_source_paths:
            self._ocr_set_source_paths([str(path) for path in self._ocr_source_paths])

    def _ocr_import_action_label(self) -> str:
        """Return the main Import Material button label for the selected pipeline."""
        method = self._ocr_method_var.get()
        if "Mistral" in method:
            return "Run Mistral OCR"
        if "OpenAI" in method and ("Vision OCR" in method or "multimodal" in method):
            return "Run OpenAI Vision OCR"
        if "Gemini" in method and ("Vision OCR" in method or "multimodal" in method):
            return "Run Gemini Vision OCR"
        return "Read material locally"

    @staticmethod
    def _split_import_text_for_ai(text: str, max_chars: int = IMPORT_AI_CHUNK_SIZE, overlap: int = IMPORT_AI_CHUNK_OVERLAP) -> list[str]:
        """Split long import text without silently dropping the tail.

        Prefer paragraph/newline boundaries and keep a small overlap so a
        phrase crossing a chunk boundary is still visible. Candidate merge
        deduplication removes duplicates caused by that overlap.
        """
        value = (text or "").strip()
        if not value:
            return []
        if len(value) <= max_chars:
            return [value]
        chunks: list[str] = []
        start = 0
        length = len(value)
        while start < length:
            end = min(length, start + max_chars)
            if end < length:
                floor = start + max_chars // 2
                boundary = max(value.rfind("\n\n", floor, end), value.rfind("\n", floor, end))
                if boundary > start:
                    end = boundary
            chunk = value[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= length:
                break
            next_start = max(start + 1, end - overlap)
            if next_start <= start:
                next_start = end
            start = next_start
        return chunks

    @classmethod
    def _import_source_size_level(cls, text: str) -> str:
        value = (text or "").strip()
        chars = len(value)
        words = len(value.split())
        parts = len(cls._split_import_text_for_ai(value)) if value else 0
        if (
            chars > IMPORT_SOURCE_HARD_CHAR_LIMIT
            or words > IMPORT_SOURCE_HARD_WORD_LIMIT
            or parts > IMPORT_SOURCE_HARD_PART_LIMIT
        ):
            return "hard"
        if (
            chars > IMPORT_SOURCE_SOFT_CHAR_LIMIT
            or words > IMPORT_SOURCE_SOFT_WORD_LIMIT
            or parts > IMPORT_SOURCE_SOFT_PART_LIMIT
        ):
            return "soft"
        return "normal"

    @staticmethod
    def _import_source_signature(text: str) -> tuple[int, int]:
        value = (text or "").strip()
        return len(value), len(value.split())

    @classmethod
    def _import_material_size_summary(cls, text: str) -> str:
        value = (text or "").strip()
        if not value:
            return "No material loaded yet."
        chunks = cls._split_import_text_for_ai(value)
        chars = len(value)
        words = len(value.split())
        level = cls._import_source_size_level(value)
        if level == "hard":
            guard = "Very large source: full-source AI search is blocked. Select a chapter/section in Source text and use Find from selected text."
        elif level == "soft":
            guard = "Large source: review the size before AI search. A chapter/section is recommended, but full-source analysis can be confirmed."
        else:
            guard = "Source size is suitable for one import workflow."
        if len(chunks) <= 1:
            parts = "AI candidate search will analyse the entire source in 1 part."
        else:
            parts = f"AI candidate search will analyse the entire source in {len(chunks)} parts. Nothing will be silently cut off."
        safety = f"Full-source safety limit: {IMPORT_SOURCE_HARD_PART_LIMIT} AI analysis parts."
        return (
            f"Material: {chars:,} characters · ~{words:,} words · {parts} "
            f"{guard} {safety} No fixed candidate count: the result depends on the material."
        )

    def _notify_large_import_source(self, text: str) -> None:
        value = (text or "").strip()
        if not value:
            return
        level = self._import_source_size_level(value)
        if level == "normal":
            return
        signature = self._import_source_signature(value)
        if getattr(self, "_ocr_large_source_notified_signature", None) == signature:
            return
        self._ocr_large_source_notified_signature = signature
        chars, words = signature
        chunks = len(self._split_import_text_for_ai(value))
        if level == "hard":
            title = "Very large source loaded"
            message = (
                f"This material contains about {words:,} words ({chars:,} characters).\n\n"
                "Full-source AI candidate search is blocked so an entire book cannot accidentally create many AI calls and an unmanageable review list.\n\n"
                "Highlight one chapter/section in Source text and click 'Find from selected text'."
            )
        else:
            title = "Large source loaded"
            message = (
                f"This material contains about {words:,} words ({chars:,} characters) and would require about {chunks} AI analysis parts.\n\n"
                "For cleaner results, one lesson/chapter at a time is recommended. You can still confirm full-source analysis when you click Find candidates with AI."
            )
        try:
            messagebox.showwarning(title, message)
        except Exception:
            pass

    def _set_ocr_text(self, text: str) -> None:
        textbox = getattr(self, "_ocr_textbox", None)
        if textbox is None:
            return
        textbox.delete("1.0", "end")
        textbox.insert("1.0", text or "")
        size_var = getattr(self, "_ocr_size_var", None)
        if size_var is not None:
            size_var.set(self._import_material_size_summary(text or ""))
        self._notify_large_import_source(text or "")
        self._scroll_import_text_to_top()

    def _get_ocr_text(self) -> str:
        textbox = getattr(self, "_ocr_textbox", None)
        if textbox is None:
            return ""
        return textbox.get("1.0", "end").strip()

    def _set_ocr_candidates_text(self, text: str) -> None:
        """Replace the candidate basket from editable text rows.

        Older versions displayed candidates in a plain textbox. The new UI keeps
        structured candidate records and renders them as cherry-pick cards.
        This method remains as a compatibility bridge for AI responses/tests.
        """
        default_mode = self._ocr_internal_mode(self._ocr_mode_var.get().strip() or "Smart vocabulary")
        items: list[dict[str, str]] = []
        for line in (text or "").splitlines():
            parsed = self._parse_ocr_candidate_row(line, default_mode)
            if parsed is None:
                continue
            candidate_type, target, sentence = parsed
            item = self._make_ocr_candidate_item(candidate_type, target, sentence, source="basket")
            if item is not None:
                items.append(item)
        self._set_ocr_candidate_items(items)

    def _get_ocr_candidates_text(self) -> str:
        """Return the current basket as machine-readable rows."""
        return "\n".join(
            self._format_ocr_candidate_row(
                item.get("type", "vocabulary"),
                item.get("target", ""),
                item.get("sentence", ""),
            )
            for item in self._ocr_candidate_items
        )

    @staticmethod
    def _candidate_review_priority(item: dict[str, str]) -> str:
        """Return an educational review tier, not a source-location tier.

        Recommended means the item is both relatively advanced and central to
        the lesson/topic. Useful is normal reusable language worth keeping.
        Optional is intentionally the bucket for odd, document-specific, weak,
        overly long, or low-reusability material. No quota is used.
        """
        def norm(key: str) -> str:
            return str(item.get(key) or "").strip().casefold().replace("-", "_").replace(" ", "_")

        needs_review = norm("needs_review") in {"true", "yes", "1"}
        confidence = norm("confidence")
        target = " ".join(str(item.get("target") or "").split())
        source_section = norm("source_section")
        source_type = norm("source_type")
        advancedness = norm("advancedness")
        topic_relevance = norm("topic_relevance")
        reusability = norm("reusability")
        document_specificity = norm("document_specificity")
        learning_value = norm("learning_value")

        if needs_review or confidence in {"low", "0", "0.0"}:
            return "Optional"

        words = target.split()
        word_count = len(words)
        if word_count >= 9:
            return "Optional"
        if document_specificity in {"high", "very_high"} or reusability == "low":
            return "Optional"

        # Proper names, regulation titles, organisations, etc. are normally
        # reference material rather than vocabulary to actively learn.
        capitalized = sum(1 for word in words if word[:1].isupper())
        explicit_language_section = source_section in {
            "vocabulary_list", "colloquial_expressions", "highlighted_item",
            "key_terms", "expressions",
        } or source_type in {"vocabulary_list", "colloquial_expression", "highlighted_item"}
        if word_count >= 2 and capitalized >= 2 and not explicit_language_section:
            return "Optional"

        advanced = advancedness in {"advanced", "high", "c1", "c2"}
        topic_high = topic_relevance in {"high", "central", "core", "strong"}
        topic_medium = topic_relevance in {"medium", "moderate"}
        reusable = reusability not in {"low", "one_off", "document_only"}
        learning_high = learning_value in {"high", "very_high", "strong"}
        learning_ok = learning_value not in {"low", "weak"}
        kind = norm("candidate_kind")

        # Educational meaning of Recommended:
        # - clearly advanced language that is at least relevant to the lesson, OR
        # - a strongly topic-defining item with high learning value, OR
        # - a strong advanced idiom/collocation/expression worth active recall.
        # This intentionally avoids quotas while also avoiding the old overly
        # strict advanced+topic-high conjunction that often produced 1/50.
        if reusable and learning_ok:
            if advanced and (topic_high or topic_medium):
                return "Recommended"
            if topic_high and learning_high and advancedness not in {"basic", "a1", "a2"}:
                return "Recommended"

        # Older providers may omit the new metadata. In that case we prefer the
        # safe middle bucket instead of pretending the item is Recommended.
        return "Useful"

    @staticmethod
    def _candidate_review_type_label(item: dict[str, str]) -> str:
        kind = ModernVocabularyGui._normalize_ocr_candidate_type(item.get("type", "vocabulary"))
        return {
            "vocabulary": "Vocabulary",
            "grammar": "Grammar",
            "provided_example": "Provided example",
        }.get(kind, "Vocabulary")

    def _ocr_filtered_candidate_indices(self) -> list[int]:
        priority_filter = getattr(self, "_ocr_review_priority_filter_var", None)
        type_filter = getattr(self, "_ocr_review_type_filter_var", None)
        search_var = getattr(self, "_ocr_review_search_var", None)
        wanted_priority = priority_filter.get().strip() if priority_filter is not None else "All priorities"
        wanted_type = type_filter.get().strip() if type_filter is not None else "All types"
        search = search_var.get().strip().casefold() if search_var is not None else ""
        indices: list[int] = []
        for index, item in enumerate(self._ocr_candidate_items):
            priority = self._candidate_review_priority(item)
            type_label = self._candidate_review_type_label(item)
            if wanted_priority != "All priorities" and priority != wanted_priority:
                continue
            if wanted_type != "All types" and type_label != wanted_type:
                continue
            if search:
                haystack = " ".join(
                    str(item.get(key) or "")
                    for key in ("target", "sentence", "source", "reason", "candidate_kind", "source_section")
                ).casefold()
                if search not in haystack:
                    continue
            indices.append(index)
        return indices

    def _ocr_visible_candidate_indices(self) -> list[int]:
        filtered = self._ocr_filtered_candidate_indices()
        if not filtered:
            return []
        page_count = max(1, (len(filtered) + IMPORT_REVIEW_PAGE_SIZE - 1) // IMPORT_REVIEW_PAGE_SIZE)
        self._ocr_review_page = max(0, min(getattr(self, "_ocr_review_page", 0), page_count - 1))
        start = self._ocr_review_page * IMPORT_REVIEW_PAGE_SIZE
        return filtered[start : start + IMPORT_REVIEW_PAGE_SIZE]

    def _reset_ocr_review_page_and_render(self) -> None:
        self._ocr_review_page = 0
        self._render_ocr_candidate_cards()
        self._update_ocr_candidate_status()

    def _change_ocr_review_page(self, delta: int) -> None:
        filtered = self._ocr_filtered_candidate_indices()
        page_count = max(1, (len(filtered) + IMPORT_REVIEW_PAGE_SIZE - 1) // IMPORT_REVIEW_PAGE_SIZE)
        self._ocr_review_page = max(0, min(getattr(self, "_ocr_review_page", 0) + int(delta), page_count - 1))
        self._render_ocr_candidate_cards()
        self._update_ocr_candidate_status()
        self._scroll_import_candidates_to_top()

    def _set_ocr_candidate_items(self, items: list[dict[str, str]]) -> None:
        # AI candidate search can return the same grammar point twice: once as a
        # grammar target/rule and once as a provided example. Keep one editable
        # grammar draft and attach the real example sentence to it instead of
        # showing duplicate candidates.
        items = self._merge_ocr_grammar_candidate_items(items)
        for item in items:
            item["review_priority"] = self._candidate_review_priority(item)
        self._ocr_candidate_items = items
        # Small reviews stay convenient: select Recommended + Useful, but never
        # auto-select Optional. Larger reviews start with Recommended only so a
        # 100+ candidate import does not immediately flood the Queue.
        small_review = len(items) <= OCR_CANDIDATE_AUTOSELECT_ALL_LIMIT
        selected_flags: list[bool] = []
        for item in items:
            priority = self._candidate_review_priority(item)
            selected_flags.append(priority in ({"Recommended", "Useful"} if small_review else {"Recommended"}))
        self._ocr_candidate_vars = [ctk.BooleanVar(value=value) for value in selected_flags]
        self._ocr_review_page = 0
        self._render_ocr_candidate_cards()
        self._scroll_import_candidates_to_top()
        self._update_ocr_candidate_status()
        if items and not small_review:
            selected = sum(1 for value in selected_flags if value)
            self._ocr_candidate_status_var.set(
                f"Found {len(items)} candidates. Large review: {selected} Recommended selected by default. "
                "Useful items remain available; Optional is for niche/odd/document-specific material."
            )

    def _make_ocr_candidate_item(
        self,
        candidate_type: str,
        target: str = "",
        sentence: str = "",
        source: str = "manual",
    ) -> dict[str, str] | None:
        kind = self._normalize_ocr_candidate_type(candidate_type)
        target = clean_ocr_text(str(target or "")).replace("\n", " ").strip()
        sentence = clean_ocr_text(str(sentence or "")).replace("\n", " ").strip()
        if self._looks_like_json_fragment(target):
            target = ""
        if self._looks_like_json_fragment(sentence):
            sentence = ""
        if not target and not sentence:
            return None
        return {
            "type": kind,
            "target": target,
            "sentence": sentence,
            "source": source,
        }

    @staticmethod
    def _ocr_normalized_match_text(value: str) -> str:
        """Normalize candidate text for fuzzy grammar merge checks."""
        normalized = clean_ocr_text(str(value or "")).casefold()
        normalized = normalized.replace("’", "'").replace("`", "'")
        normalized = re.sub(r"[^a-z0-9áéíóúüñ'/-]+", " ", normalized)
        return re.sub(r"\s+", " ", normalized).strip()

    @classmethod
    def _ocr_grammar_fragments_for_merge(cls, target: str) -> list[str]:
        """Return useful fragments from a grammar target for merge matching.

        Examples:
        - "should have / ought to have + past participle" ->
          ["should have", "ought to have"]
        - "be supposed / meant to + infinitive" ->
          ["be supposed", "meant to"]
        """
        normalized = cls._ocr_normalized_match_text(target)
        normalized = re.sub(r"^target\s*[:\-]\s*", "", normalized)
        normalized = re.split(r"\s+\+\s+|\s+to talk about\s+", normalized, maxsplit=1)[0].strip()
        if not normalized:
            return []

        pieces = [piece.strip(" -/") for piece in re.split(r"\s*/\s*", normalized) if piece.strip(" -/")]
        fragments: list[str] = []
        for piece in pieces or [normalized]:
            # Remove lesson labels but keep the actual modal/structure words.
            piece = re.sub(r"\b(past participle|infinitive|base form|verb phrase)\b", "", piece).strip()
            piece = re.sub(r"\s+", " ", piece).strip()
            if len(piece) >= 5:
                fragments.append(piece)

        # Also keep the pre-slashed pattern as a weak fallback when it is clean.
        if "/" not in normalized and len(normalized) >= 5:
            fragments.append(normalized)

        result: list[str] = []
        seen: set[str] = set()
        for fragment in fragments:
            key = fragment.casefold()
            if key not in seen:
                result.append(fragment)
                seen.add(key)
        return result

    @classmethod
    def _ocr_grammar_target_matches_example(cls, grammar_target: str, example_target: str, example_sentence: str) -> bool:
        fragments = cls._ocr_grammar_fragments_for_merge(grammar_target)
        if not fragments:
            return False
        haystack = cls._ocr_normalized_match_text(f"{example_target} {example_sentence}")
        if not haystack:
            return False
        matches = 0
        for fragment in fragments:
            fragment_norm = cls._ocr_normalized_match_text(fragment)
            if not fragment_norm:
                continue
            # Direct match catches "should have", "ought to have", "permitted to", etc.
            if fragment_norm in haystack:
                matches += 1
                continue
            # Modal/passive grammar targets often use dictionary "be", while examples
            # contain am/is/are/was/were. Match the meaningful tail as a fallback.
            tail = re.sub(r"^be\s+", "", fragment_norm).strip()
            if len(tail) >= 5 and tail in haystack:
                matches += 1
        # One strong fragment is enough for paired alternatives like
        # "should have / ought to have" because OCR/AI examples may include only one.
        return matches >= 1

    @staticmethod
    def _ocr_looks_like_rule_explanation(text: str) -> bool:
        value = clean_ocr_text(str(text or "")).casefold()
        if not value:
            return False
        rule_markers = (
            "we use ",
            "we can use ",
            "we often use ",
            "you can use ",
            "is used to ",
            "are used to ",
            "used to express",
            "used for ",
            "to talk about ",
            "to say that ",
            "to express ",
            "means to ",
            "is stronger",
            "the negative is",
            "normally refers",
            "the most common",
            "completely different",
            "stative",
            "dynamic",
            "continuous tense",
            "continuous tenses",
            "main verb",
            "auxiliary verb",
            "past participle",
            "base verb",
            "object + past",
            "obligation",
            "possession",
            "relationships or illnesses",
            "rules and regulations",
        )
        if any(marker in value for marker in rule_markers):
            return True
        # Textbook rules often begin with a grammar item and then explain it,
        # e.g. "have with this meaning is a stative verb...". These are not
        # audio/example sentences and should be kept as notes/source rules.
        if re.search(r"\b(have|be|do|can|could|must|should|ought to|need|used to)\b.{0,45}\bis\b.{0,80}\b(verb|tense|form|structure|meaning|used|stative|dynamic)\b", value):
            return True
        return False

    @classmethod
    def _merge_ocr_grammar_candidate_items(cls, items: list[dict[str, str]]) -> list[dict[str, str]]:
        """Convert duplicated grammar rule + example pairs into target-aware drafts.

        Grammar import keeps one concrete sentence/audio example per candidate while
        preserving the grammar target separately for final target-first cards. AI candidate search can return both:
        1. a rule-like Grammar target, for example ``should have + past participle``;
        2. one or more Provided example rows that use that target.

        Do not collapse multiple examples into one candidate. Instead, convert
        every matching provided example into its own Grammar candidate with the
        shared target and that exact source sentence. A rule-only candidate is
        removed only when examples were found for it, so the UI avoids duplicate
        rule cards while preserving one card per readable sentence.
        """
        if not items:
            return []

        merged: list[dict[str, str]] = [dict(item) for item in items]
        remove_indexes: set[int] = set()
        grammar_used_by_examples: set[int] = set()

        grammar_indexes = [
            idx for idx, item in enumerate(merged)
            if cls._normalize_ocr_candidate_type(item.get("type", "")) == "grammar" and item.get("target", "").strip()
        ]
        if not grammar_indexes:
            return merged

        for idx, item in enumerate(merged):
            if idx in remove_indexes:
                continue
            if cls._normalize_ocr_candidate_type(item.get("type", "")) != "provided_example":
                continue

            example_target = item.get("target", "").strip()
            example_sentence = item.get("sentence", "").strip()
            incoming_sentence = example_sentence or example_target
            if not incoming_sentence:
                continue

            match_idx: int | None = None
            for grammar_idx in grammar_indexes:
                if grammar_idx == idx or grammar_idx in remove_indexes:
                    continue
                grammar_item = merged[grammar_idx]
                if cls._ocr_grammar_target_matches_example(
                    grammar_item.get("target", ""),
                    example_target,
                    example_sentence,
                ):
                    match_idx = grammar_idx
                    break
            if match_idx is None:
                continue

            grammar_item = merged[match_idx]
            grammar_target = grammar_item.get("target", "").strip()
            source_bits = [bit for bit in [grammar_item.get("source", ""), item.get("source", "")] if bit]
            item["type"] = "grammar"
            item["target"] = grammar_target
            item["sentence"] = incoming_sentence
            item["source"] = (
                " + ".join(dict.fromkeys(source_bits)) + " + sentence grammar"
                if source_bits
                else "sentence grammar"
            )
            grammar_used_by_examples.add(match_idx)

        for grammar_idx in grammar_used_by_examples:
            grammar_item = merged[grammar_idx]
            current_sentence = grammar_item.get("sentence", "").strip()
            target = grammar_item.get("target", "").strip()
            if (
                not current_sentence
                or cls._ocr_looks_like_rule_explanation(current_sentence)
                or current_sentence.casefold() == target.casefold()
            ):
                remove_indexes.add(grammar_idx)

        if not remove_indexes:
            return merged
        return [item for idx, item in enumerate(merged) if idx not in remove_indexes]

    def _render_ocr_candidate_cards(self) -> None:
        frame = getattr(self, "_ocr_candidates_frame", None)
        if frame is None:
            return
        for child in frame.winfo_children():
            child.destroy()

        if not self._ocr_candidate_items:
            if hasattr(self, "_ocr_review_page_var"):
                self._ocr_review_page_var.set("Page 0 of 0")
            ctk.CTkLabel(
                frame,
                text=(
                    "No candidates yet.\n\n"
                    "Load/read material first, then use Find candidates with AI or the basic local finder."
                ),
                justify="left",
                wraplength=420,
                text_color=("gray35", "gray75"),
            ).grid(row=0, column=0, sticky="nw", padx=12, pady=12)
            return

        while len(self._ocr_candidate_vars) < len(self._ocr_candidate_items):
            self._ocr_candidate_vars.append(ctk.BooleanVar(value=True))
        if len(self._ocr_candidate_vars) > len(self._ocr_candidate_items):
            self._ocr_candidate_vars = self._ocr_candidate_vars[: len(self._ocr_candidate_items)]

        filtered = self._ocr_filtered_candidate_indices()
        page_count = max(1, (len(filtered) + IMPORT_REVIEW_PAGE_SIZE - 1) // IMPORT_REVIEW_PAGE_SIZE) if filtered else 0
        if page_count:
            self._ocr_review_page = max(0, min(getattr(self, "_ocr_review_page", 0), page_count - 1))
            start = self._ocr_review_page * IMPORT_REVIEW_PAGE_SIZE
            visible_indices = filtered[start : start + IMPORT_REVIEW_PAGE_SIZE]
            if hasattr(self, "_ocr_review_page_var"):
                self._ocr_review_page_var.set(
                    f"Page {self._ocr_review_page + 1} of {page_count} · showing {start + 1}-{start + len(visible_indices)} of {len(filtered)} filtered"
                )
        else:
            visible_indices = []
            if hasattr(self, "_ocr_review_page_var"):
                self._ocr_review_page_var.set("No matching candidates")

        if not visible_indices:
            ctk.CTkLabel(
                frame,
                text="No candidates match the current filters. Clear or change the filters to see the rest.",
                justify="left",
                wraplength=440,
                text_color=("gray35", "gray75"),
            ).grid(row=0, column=0, sticky="nw", padx=12, pady=12)
            return

        for display_row, index in enumerate(visible_indices):
            item = self._ocr_candidate_items[index]
            card = ctk.CTkFrame(frame, corner_radius=12)
            card.grid(row=display_row, column=0, sticky="ew", padx=8, pady=(8, 4))
            card.grid_columnconfigure(1, weight=1)

            var = self._ocr_candidate_vars[index]
            ctk.CTkCheckBox(card, text="", variable=var, width=22, command=self._update_ocr_candidate_status).grid(
                row=0, column=0, rowspan=7, sticky="nw", padx=(10, 4), pady=10
            )

            label = self._ocr_candidate_display_type(item.get("type", "vocabulary"), item.get("target", ""), item.get("sentence", ""))
            priority = self._candidate_review_priority(item)
            item["review_priority"] = priority
            ctk.CTkLabel(
                card,
                text=f"{label} · {priority}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray30", "gray70"),
            ).grid(row=0, column=1, sticky="w", padx=(4, 10), pady=(8, 0))

            target = item.get("target", "").strip()
            sentence = item.get("sentence", "").strip()
            source = item.get("source", "").strip()
            source_type = str(item.get("source_type") or "").strip()
            strategy = str(item.get("strategy") or "").strip()
            candidate_kind = self._normalize_ocr_candidate_type(item.get("type", ""))

            if candidate_kind == "grammar":
                target_label = "Grammar focus"
                example_label = "Example / audio"
            elif candidate_kind == "provided_example":
                target_label = "Target phrase"
                example_label = "Source sentence"
            else:
                target_label = "Word / phrase"
                example_label = "Example"

            target_text = f"{target_label}: {target}" if target else f"{target_label}: —"
            ctk.CTkLabel(card, text=target_text, anchor="w", justify="left", wraplength=520).grid(
                row=1, column=1, sticky="ew", padx=(4, 10), pady=(4, 0)
            )
            if sentence:
                example_text = f"{example_label}: {sentence}"
            elif candidate_kind == "grammar" and source_type == "rule":
                example_text = "Example / audio: AI will generate a natural example in Queue"
            elif candidate_kind == "grammar" and strategy == "generated_example_from_rule":
                example_text = "Example / audio: AI will generate a natural example in Queue"
            else:
                example_text = f"{example_label}: —"
            ctk.CTkLabel(
                card,
                text=example_text,
                anchor="w",
                justify="left",
                wraplength=520,
                text_color=("gray30", "gray75"),
            ).grid(row=2, column=1, sticky="ew", padx=(4, 10), pady=(2, 0))
            if source or item.get("edited"):
                source_label = f"Source: {source or 'manual'}"
                if item.get("edited"):
                    source_label += " · edited"
                ctk.CTkLabel(
                    card,
                    text=source_label,
                    font=ctk.CTkFont(size=11),
                    text_color=("gray40", "gray65"),
                ).grid(row=3, column=1, sticky="w", padx=(4, 10), pady=(2, 2))

            meta_bits: list[str] = []
            source_type = str(item.get("source_type") or "").strip()
            strategy = str(item.get("strategy") or "").strip()
            reason = str(item.get("reason") or "").strip()
            source_rule = str(item.get("source_rule") or "").strip()
            if source_type:
                meta_bits.append(f"Detected as: {source_type.replace('_', ' ')}")
            if strategy:
                meta_bits.append(f"Strategy: {strategy.replace('_', ' ')}")
            if reason:
                meta_bits.append(f"Why: {reason}")
            vocab_kind = str(item.get("candidate_kind") or "").strip()
            source_section = str(item.get("source_section") or "").strip()
            if vocab_kind:
                meta_bits.append(f"Kind: {vocab_kind.replace('_', ' ')}")
            if source_section:
                meta_bits.append(f"Section: {source_section.replace('_', ' ')}")
            advancedness = str(item.get("advancedness") or "").strip()
            topic_relevance = str(item.get("topic_relevance") or "").strip()
            reusability = str(item.get("reusability") or "").strip()
            learning_value = str(item.get("learning_value") or "").strip()
            document_specificity = str(item.get("document_specificity") or "").strip()
            learning_bits = []
            if advancedness:
                learning_bits.append(f"level: {advancedness}")
            if topic_relevance:
                learning_bits.append(f"topic: {topic_relevance}")
            if reusability:
                learning_bits.append(f"reusable: {reusability}")
            if learning_value:
                learning_bits.append(f"learning value: {learning_value}")
            if document_specificity:
                learning_bits.append(f"document-specific: {document_specificity}")
            if learning_bits:
                meta_bits.append("Review signals: " + " · ".join(learning_bits))
            example_origin = str(item.get("example_origin") or "").strip()
            needs_review = str(item.get("needs_review") or "").strip()
            if example_origin:
                meta_bits.append(f"Example origin: {example_origin.replace('_', ' ')}")
            if needs_review in {"true", "yes", "1"}:
                meta_bits.append("Needs review: yes")
            if source_rule:
                meta_bits.append(f"Rule/source note: {source_rule}")
            if meta_bits:
                ctk.CTkLabel(
                    card,
                    text="\n".join(meta_bits),
                    font=ctk.CTkFont(size=11),
                    justify="left",
                    wraplength=520,
                    text_color=("gray38", "gray68"),
                ).grid(row=4, column=1, sticky="ew", padx=(4, 10), pady=(2, 2))

            mark_buttons = ctk.CTkFrame(card, fg_color="transparent")
            mark_buttons.grid(row=5, column=1, sticky="ew", padx=(4, 10), pady=(4, 8))
            mark_buttons.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                mark_buttons, text="Type", font=ctk.CTkFont(size=11, weight="bold")
            ).grid(row=0, column=0, sticky="w", padx=(0, 6))
            display_type = {
                "vocabulary": "Vocabulary",
                "grammar": "Grammar",
                "provided_example": "Provided example",
            }.get(candidate_kind, "Vocabulary")
            type_box = ctk.CTkComboBox(
                mark_buttons,
                values=["Vocabulary", "Grammar", "Provided example"],
                state="readonly",
                width=180,
                command=lambda value, i=index: self._set_ocr_candidate_type_from_ui(i, value),
            )
            type_box.set(display_type)
            type_box.grid(row=0, column=1, sticky="w", padx=(0, 8))
            ctk.CTkButton(
                mark_buttons,
                text="Edit",
                width=68,
                height=28,
                command=lambda i=index: self._open_ocr_candidate_editor(i),
            ).grid(row=0, column=2, sticky="e", padx=4)
            ctk.CTkButton(
                mark_buttons,
                text="Remove",
                width=68,
                height=28,
                command=lambda i=index: self._remove_ocr_candidate(i),
            ).grid(row=0, column=3, sticky="e", padx=(4, 0))


    def _open_missing_ocr_candidate_dialog(self) -> None:
        """Small escape hatch for adding one candidate that the finders missed."""
        selected_text = clean_ocr_text(self._ocr_get_selected_text()).replace("\n", " ").strip()
        dialog = tk.Toplevel(self._root)
        dialog.title("Add missing candidate")
        dialog.geometry("720x430")
        dialog.transient(self._root)
        dialog.grid_columnconfigure(1, weight=1)
        dialog.grid_rowconfigure(2, weight=1)

        type_var = tk.StringVar(value=self._ocr_manual_candidate_type_var.get() or "vocabulary")
        target_var = tk.StringVar(value=selected_text)
        source_var = tk.StringVar(value="manual missing candidate")

        tk.Label(dialog, text="Type", anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Combobox(
            dialog,
            textvariable=type_var,
            values=["vocabulary", "grammar", "provided_example"],
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=10, pady=8)

        tk.Label(dialog, text="Target / candidate", anchor="w").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        tk.Entry(dialog, textvariable=target_var).grid(row=1, column=1, sticky="ew", padx=10, pady=8)

        tk.Label(dialog, text="Example / sentence", anchor="w").grid(row=2, column=0, sticky="nw", padx=10, pady=8)
        sentence_box = tk.Text(dialog, height=8, wrap="word")
        sentence_box.grid(row=2, column=1, sticky="nsew", padx=10, pady=8)

        tk.Label(dialog, text="Source", anchor="w").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        tk.Entry(dialog, textvariable=source_var).grid(row=3, column=1, sticky="ew", padx=10, pady=8)

        def fill_target_from_selection() -> None:
            selected = clean_ocr_text(self._ocr_get_selected_text()).replace("\n", " ").strip()
            if not selected:
                messagebox.showwarning("Add missing candidate", "Highlight text in Source text first.")
                return
            target_var.set(selected)

        def fill_example_from_selection() -> None:
            selected = clean_ocr_text(self._ocr_get_selected_text()).replace("\n", " ").strip()
            if not selected:
                messagebox.showwarning("Add missing candidate", "Highlight an example in Source text first.")
                return
            sentence_box.delete("1.0", "end")
            sentence_box.insert("1.0", selected)

        def save() -> None:
            kind = self._normalize_ocr_candidate_type(type_var.get())
            target = clean_ocr_text(target_var.get()).replace("\n", " ").strip()
            sentence = clean_ocr_text(sentence_box.get("1.0", "end")).replace("\n", " ").strip()
            target, sentence = self._ocr_fields_for_candidate_type(kind, target, sentence)
            if not target and not sentence:
                messagebox.showwarning("Add missing candidate", "Target or example cannot be empty.")
                return
            if kind == "vocabulary" and not target:
                messagebox.showwarning("Add missing candidate", "Vocabulary candidates need a target word or phrase.")
                return
            item = self._make_ocr_candidate_item(
                kind,
                target=target,
                sentence=sentence,
                source=source_var.get().strip() or "manual missing candidate",
            )
            if item is None:
                messagebox.showwarning("Add missing candidate", "Candidate could not be saved.")
                return
            item["edited"] = "true"
            self._ocr_candidate_items.append(item)
            self._ocr_candidate_vars.append(ctk.BooleanVar(value=True))
            self._render_ocr_candidate_cards()
            self._update_ocr_candidate_status()
            self._ocr_candidate_status_var.set("Missing candidate added. Cherry-pick uses this edited draft.")
            dialog.destroy()

        button_row = tk.Frame(dialog)
        button_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=12)
        tk.Button(button_row, text="Use selection as target", command=fill_target_from_selection).pack(side="left")
        tk.Button(button_row, text="Use selection as example", command=fill_example_from_selection).pack(side="left", padx=(8, 0))
        tk.Button(button_row, text="Add missing candidate", command=save).pack(side="right")
        tk.Button(button_row, text="Cancel", command=dialog.destroy).pack(side="right", padx=(0, 8))


    def _open_ocr_candidate_editor(self, index: int) -> None:
        """Edit a candidate draft before it becomes the final cherry-pick item."""
        if index < 0 or index >= len(self._ocr_candidate_items):
            return
        item = self._ocr_candidate_items[index]
        editor = tk.Toplevel(self._root)
        editor.title("Edit candidate draft")
        editor.geometry("720x420")
        editor.transient(self._root)
        editor.grid_columnconfigure(1, weight=1)
        editor.grid_rowconfigure(2, weight=1)

        type_var = tk.StringVar(value=self._normalize_ocr_candidate_type(item.get("type", "vocabulary")))
        tk.Label(editor, text="Type", anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        type_box = ttk.Combobox(
            editor,
            textvariable=type_var,
            values=["vocabulary", "grammar", "provided_example"],
            state="readonly",
        )
        type_box.grid(row=0, column=1, sticky="ew", padx=10, pady=8)

        target_var = tk.StringVar(value=item.get("target", ""))
        tk.Label(editor, text="Target / candidate", anchor="w").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        target_entry = tk.Entry(editor, textvariable=target_var)
        target_entry.grid(row=1, column=1, sticky="ew", padx=10, pady=8)

        tk.Label(editor, text="Example / sentence", anchor="w").grid(row=2, column=0, sticky="nw", padx=10, pady=8)
        sentence_box = tk.Text(editor, height=8, wrap="word")
        sentence_box.insert("1.0", item.get("sentence", ""))
        sentence_box.grid(row=2, column=1, sticky="nsew", padx=10, pady=8)

        tk.Label(editor, text="Source", anchor="w").grid(row=3, column=0, sticky="w", padx=10, pady=8)
        source_var = tk.StringVar(value=item.get("source", "manual"))
        source_entry = tk.Entry(editor, textvariable=source_var)
        source_entry.grid(row=3, column=1, sticky="ew", padx=10, pady=8)

        def save() -> None:
            kind = self._normalize_ocr_candidate_type(type_var.get())
            target = clean_ocr_text(target_var.get()).replace("\n", " ").strip()
            sentence = clean_ocr_text(sentence_box.get("1.0", "end")).replace("\n", " ").strip()
            target, sentence = self._ocr_fields_for_candidate_type(kind, target, sentence)
            if not target and not sentence:
                messagebox.showwarning("Edit candidate", "Target or example cannot be empty.")
                return
            item["type"] = kind
            item["target"] = target
            item["sentence"] = sentence
            item["source"] = (source_var.get().strip() or item.get("source") or "manual")
            item["edited"] = "true"
            if index < len(self._ocr_candidate_vars):
                self._ocr_candidate_vars[index].set(True)
            self._render_ocr_candidate_cards()
            self._update_ocr_candidate_status()
            self._ocr_candidate_status_var.set("Candidate draft saved. Cherry-pick uses the edited version.")
            editor.destroy()

        button_row = tk.Frame(editor)
        button_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=12)
        tk.Button(button_row, text="Save changes", command=save).pack(side="left")
        tk.Button(button_row, text="Cancel", command=editor.destroy).pack(side="left", padx=(8, 0))

    @staticmethod
    def _ocr_candidate_display_type(candidate_type: str, target: str = "", sentence: str = "") -> str:
        kind = ModernVocabularyGui._normalize_ocr_candidate_type(candidate_type)
        target = (target or "").strip()
        sentence = (sentence or "").strip()
        if kind == "provided_example":
            return "Provided example"
        if kind == "grammar":
            return "Grammar target" if target else "Grammar from sentence"
        return "Word / phrase"

    def _update_ocr_candidate_status(self) -> None:
        total = len(self._ocr_candidate_items)
        if not total:
            self._ocr_candidate_status_var.set("No candidates yet.")
            return
        selected = sum(1 for var in self._ocr_candidate_vars if var.get())
        priority_counts = {"Recommended": 0, "Useful": 0, "Optional": 0}
        type_counts = {"Vocabulary": 0, "Grammar": 0, "Provided example": 0}
        for item in self._ocr_candidate_items:
            priority_counts[self._candidate_review_priority(item)] += 1
            type_counts[self._candidate_review_type_label(item)] += 1
        filtered = self._ocr_filtered_candidate_indices()
        self._ocr_candidate_status_var.set(
            f"{total} candidates · {priority_counts['Recommended']} Recommended · {priority_counts['Useful']} Useful · "
            f"{priority_counts['Optional']} Optional · {selected} selected · {len(filtered)} match current filters. "
            f"Types: {type_counts['Vocabulary']} Vocabulary · {type_counts['Grammar']} Grammar · "
            f"{type_counts['Provided example']} Examples."
        )

    def _select_all_ocr_candidates(self) -> None:
        # Backward-compatible action used by older tests/UI callbacks.
        for var in self._ocr_candidate_vars:
            var.set(True)
        self._update_ocr_candidate_status()

    def _select_recommended_ocr_candidates(self) -> None:
        for var in self._ocr_candidate_vars:
            var.set(False)
        for index, item in enumerate(self._ocr_candidate_items):
            if self._candidate_review_priority(item) == "Recommended" and index < len(self._ocr_candidate_vars):
                self._ocr_candidate_vars[index].set(True)
        self._update_ocr_candidate_status()

    def _select_recommended_and_useful_ocr_candidates(self) -> None:
        for index, item in enumerate(self._ocr_candidate_items):
            if index < len(self._ocr_candidate_vars):
                self._ocr_candidate_vars[index].set(
                    self._candidate_review_priority(item) in {"Recommended", "Useful"}
                )
        self._update_ocr_candidate_status()

    def _select_visible_ocr_candidates(self) -> None:
        for index in self._ocr_visible_candidate_indices():
            if index < len(self._ocr_candidate_vars):
                self._ocr_candidate_vars[index].set(True)
        self._update_ocr_candidate_status()

    def _deselect_all_ocr_candidates(self) -> None:
        for var in self._ocr_candidate_vars:
            var.set(False)
        self._update_ocr_candidate_status()

    @staticmethod
    def _ocr_fields_for_candidate_type(candidate_type: str, target: str, sentence: str) -> tuple[str, str]:
        """Normalize candidate fields for the selected Queue intention.

        UX rule for Import Material:
        - If a grammar candidate already has a target/pattern, preserve it.
        - If it only has a sentence/example, treat it as "Grammar from sentence"
          and let Queue infer the grammar focus later.
        - Never destroy a useful AI-found target when the user marks an item for Grammar.
        """
        kind = ModernVocabularyGui._normalize_ocr_candidate_type(candidate_type)
        target = (target or "").strip()
        sentence = (sentence or "").strip()
        if kind == "provided_example":
            if not sentence and target:
                return "", target
            return target, sentence
        if kind == "vocabulary":
            if not target and sentence:
                return sentence, ""
            return target, sentence
        if kind == "grammar":
            # Preserve an explicit grammar target if AI/manual input provided one.
            # Empty target is allowed only for "Grammar from sentence".
            return target, sentence or ("" if target else target)
        return target, sentence

    def _set_ocr_candidate_type_from_ui(self, index: int, selected: str) -> None:
        mapping = {
            "Vocabulary": "vocabulary",
            "Grammar": "grammar",
            "Provided example": "provided_example",
        }
        self._mark_ocr_candidate_as(index, mapping.get(selected, "vocabulary"))
        if 0 <= index < len(self._ocr_candidate_items):
            visible = self._ocr_candidate_display_type(
                self._ocr_candidate_items[index].get("type", "vocabulary"),
                self._ocr_candidate_items[index].get("target", ""),
                self._ocr_candidate_items[index].get("sentence", ""),
            )
            self._ocr_candidate_status_var.set(f"Candidate type changed to {visible}. This type will be preserved in Queue.")

    def _mark_ocr_candidate_as(self, index: int, candidate_type: str) -> None:
        """Change a cherry-picked local candidate into a Queue intention."""
        if index < 0 or index >= len(self._ocr_candidate_items):
            return
        item = self._ocr_candidate_items[index]
        kind = self._normalize_ocr_candidate_type(candidate_type)
        target, sentence = self._ocr_fields_for_candidate_type(
            kind, item.get("target", ""), item.get("sentence", "")
        )

        item["type"] = kind
        item["target"] = target
        item["sentence"] = sentence
        if not item.get("source"):
            item["source"] = "manual mark"
        if index < len(self._ocr_candidate_vars):
            self._ocr_candidate_vars[index].set(True)
        self._render_ocr_candidate_cards()
        self._update_ocr_candidate_status()

    def _mark_selected_ocr_candidates_as(self, candidate_type: str) -> None:
        """Bulk-change selected candidates without re-rendering after every row."""
        if not self._ocr_candidate_items:
            return
        changed = 0
        kind = self._normalize_ocr_candidate_type(candidate_type)
        for index, item in enumerate(self._ocr_candidate_items):
            if index < len(self._ocr_candidate_vars) and not self._ocr_candidate_vars[index].get():
                continue
            target, sentence = self._ocr_fields_for_candidate_type(
                kind, item.get("target", ""), item.get("sentence", "")
            )
            item["type"] = kind
            item["target"] = target
            item["sentence"] = sentence
            if not item.get("source"):
                item["source"] = "manual mark"
            changed += 1
        self._render_ocr_candidate_cards()
        self._update_ocr_candidate_status()
        label = "Grammar candidate(s)" if kind == "grammar" else self._ocr_candidate_display_type(candidate_type)
        self._ocr_candidate_status_var.set(f"Marked {changed} selected candidate(s) as {label}.")

    def _remove_selected_ocr_candidates(self) -> None:
        if not self._ocr_candidate_items:
            return
        kept_items: list[dict[str, str]] = []
        kept_vars: list[ctk.BooleanVar] = []
        removed = 0
        for index, item in enumerate(self._ocr_candidate_items):
            is_selected = index >= len(self._ocr_candidate_vars) or self._ocr_candidate_vars[index].get()
            if is_selected:
                removed += 1
                continue
            kept_items.append(item)
            if index < len(self._ocr_candidate_vars):
                kept_vars.append(self._ocr_candidate_vars[index])
        self._ocr_candidate_items = kept_items
        self._ocr_candidate_vars = kept_vars
        self._render_ocr_candidate_cards()
        self._update_ocr_candidate_status()
        self._ocr_candidate_status_var.set(f"Removed {removed} selected candidate(s).")

    def _remove_ocr_candidate(self, index: int) -> None:
        if index < 0 or index >= len(self._ocr_candidate_items):
            return
        del self._ocr_candidate_items[index]
        if index < len(self._ocr_candidate_vars):
            del self._ocr_candidate_vars[index]
        self._render_ocr_candidate_cards()
        self._update_ocr_candidate_status()
        self._ocr_candidate_status_var.set("Removed candidate draft.")

    def _clear_ocr_candidates(self) -> None:
        self._ocr_candidate_items = []
        self._ocr_candidate_vars = []
        self._render_ocr_candidate_cards()
        self._ocr_candidate_status_var.set("Candidates cleared.")
        self._cleanup_runtime_memory("clear ocr candidates", aggressive=False)

    def _ocr_get_selected_text(self) -> str:
        textbox = getattr(self, "_ocr_textbox", None)
        if textbox is None:
            return ""
        try:
            return textbox.get("sel.first", "sel.last").strip()
        except Exception:
            return ""

    def _update_ocr_mode_help(self) -> None:
        mode = (self._ocr_mode_var.get() or "Smart vocabulary").strip()
        self._ocr_mode_help_var.set(OCR_EXTRACTION_MODE_HELP.get(mode, "Choose what AI should extract from the reviewed source."))

    @staticmethod
    def _ocr_internal_mode(mode: str) -> str:
        value = (mode or "Smart vocabulary").strip()
        return OCR_EXTRACTION_MODE_INTERNAL.get(value, value)

    @staticmethod
    def _is_grammar_import_mode(mode: str) -> bool:
        value = (mode or "").strip().casefold()
        return value in {"grammar", "smart grammar import"}

    @staticmethod
    def _is_vocabulary_import_mode(mode: str) -> bool:
        value = (mode or "").strip().casefold()
        return value in {"vocabulary", "vocabulary + source examples", "smart vocabulary", "vocabulary & expressions"}

    @staticmethod
    def _normalize_ocr_candidate_type(candidate_type: str, default_mode: str = "") -> str:
        raw = (candidate_type or default_mode or "vocabulary").strip().casefold().replace("_", " ")
        default_raw = (default_mode or "").strip().casefold().replace("_", " ")
        if default_raw in {"vocabulary", "vocabulary + source examples"}:
            # Strict vocabulary modes must stay vocabulary-only. Source
            # examples are context metadata, not Provided Examples mode.
            return "vocabulary"
        if raw in {"smart grammar import", "smart grammar", "grammar import"}:
            return "grammar"
        if raw in {"provided", "provided example", "provided examples", "sentence", "source sentence", "example"}:
            # Smart Grammar and Grammar modes must never silently downgrade to
            # Provided example. A sentence-only grammar candidate is still a
            # grammar candidate; Queue will infer the focus later.
            if default_raw in {"grammar", "smart grammar import", "smart grammar", "grammar import"}:
                return "grammar"
            return "provided_example"
        if raw in {"grammar", "grammar target", "grammar from sentence", "structure", "pattern", "verb pattern", "tense pattern"}:
            return "grammar"
        return "vocabulary"

    @staticmethod
    def _looks_like_json_fragment(value: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        lowered = text.strip().casefold().strip(',')
        if lowered in {"{", "}", "[", "]", "type", "target", "sentence", "source_type", "strategy", "source_role", "example_origin", "needs_review", "candidates"}:
            return True
        if re.fullmatch(r'"?(type|target|sentence|source_type|strategy|source_role|example_origin|needs_review|reason|candidates|source_rule)"?\s*:\s*"?[^"{}\[\]]*"?,?', lowered):
            return True
        if re.match(r'^"?(type|source_type|strategy|source_role|example_origin|needs_review|target|sentence|reason|source_rule)"?\s*:', lowered):
            return True
        if lowered.startswith('{') or lowered.endswith('}'):
            return True
        return False

    @staticmethod
    def _format_ocr_candidate_row(candidate_type: str, target: str = "", sentence: str = "") -> str:
        kind = ModernVocabularyGui._normalize_ocr_candidate_type(candidate_type)
        label = "provided example" if kind == "provided_example" else kind
        target = clean_ocr_text(str(target or "")).replace("\n", " ").strip()
        sentence = clean_ocr_text(str(sentence or "")).replace("\n", " ").strip()
        if kind == "provided_example":
            if target and sentence:
                return f"{label} | {target} | {sentence}"
            return f"{label} | {sentence or target}"
        if kind == "grammar":
            if target and sentence:
                return f"grammar | {target} | {sentence}"
            return f"grammar | {target or sentence}"
        if target and sentence:
            # Vocabulary + source examples must keep the source sentence when
            # candidates are serialized/reparsed. Older versions returned only
            # the target here, so Queue later regenerated a new example and
            # wasted a provider call.
            return f"{label} | {target} | {sentence}"
        return f"{label} | {target or sentence}"

    def _ocr_append_candidate(self, candidate_type: str, target: str = "", sentence: str = "") -> None:
        item = self._make_ocr_candidate_item(candidate_type, target, sentence, source="manual")
        if item is None:
            return
        self._ocr_candidate_items.append(item)
        self._ocr_candidate_vars.append(ctk.BooleanVar(value=True))
        self._render_ocr_candidate_cards()
        self._update_ocr_candidate_status()

    def _ocr_append_candidate_row(self, row: str) -> None:
        parsed = self._parse_ocr_candidate_row(row, self._ocr_internal_mode(self._ocr_mode_var.get().strip() or "Smart vocabulary"))
        if parsed is None:
            return
        candidate_type, target, sentence = parsed
        self._ocr_append_candidate(candidate_type, target, sentence)

    def _ocr_text_for_local_search(self) -> tuple[str, str]:
        """Return selected text when present, otherwise all extracted text."""
        selected = self._ocr_get_selected_text().strip()
        if selected:
            return selected, "selection"
        return self._get_ocr_text(), "all text"

    @staticmethod
    def _ocr_candidate_hard_limit(mode: str) -> int:
        """Return the maximum AI candidates allowed before refusing to render.

        Explicit vocabulary lists can be legitimately large, but continuous
        prose should never become hundreds or thousands of cards. This is a
        runtime safety net independent of prompt wording.
        """
        key = (mode or "").strip().casefold()
        return OCR_AI_CANDIDATE_HARD_LIMITS.get(key, 180)

    @staticmethod
    def _count_ai_json_candidates(raw_text: str) -> int | None:
        """Count JSON candidates without fully rendering them.

        Returns None when the provider did not return parseable JSON. The
        caller still runs the normal parser fallback, which has its own cap.
        """
        try:
            cleaned = ModernVocabularyGui._ocr_clean_json_text(raw_text)
            data = json.loads(cleaned)
            candidates = data.get("candidates", data) if isinstance(data, dict) else data
            if isinstance(candidates, list):
                return len(candidates)
        except Exception:
            return None
        return None

    def _reject_runaway_ai_candidates(self, count: int, limit: int, mode: str, source: str) -> None:
        """Refuse a runaway AI candidate search result before it breaks the UI."""
        message = (
            f"AI returned {count} candidate(s), above the safety limit of {limit} for {mode}. "
            "Nothing was imported. Use a smaller selected section, explicit Vocabulary mode, or split the lesson."
        )
        self._ocr_status_var.set("Large extraction blocked to protect the UI.")
        self._ocr_candidate_status_var.set(message)
        LOGGER.warning("Blocked runaway OCR candidate search: count=%s limit=%s mode=%s source=%s", count, limit, mode, source)
        try:
            messagebox.showwarning("Large extraction blocked", message)
        except Exception:
            pass
        self._record_activity(f"OCR candidate search blocked: {count}>{limit}")

    @classmethod
    def _import_candidate_identity(cls, item: dict[str, str]) -> str:
        """Return the card identity used to deduplicate Import Material candidates.

        Vocabulary / provided-example cards are one card per lexical target.
        Target-first grammar cards are one card per grammar target.  The source
        sentence is context/example content and must not create another card for
        the same front-side target.
        """
        kind = cls._normalize_ocr_candidate_type(item.get("type", "vocabulary"))
        identity_kind = "vocabulary" if kind in {"vocabulary", "provided_example"} else kind
        target = " ".join(str(item.get("target") or "").split()).casefold()
        sentence = " ".join(str(item.get("sentence") or "").split()).casefold()
        if target:
            return f"{identity_kind}::target::{target}"
        return f"{identity_kind}::sentence::{sentence}"

    def _add_ocr_candidate_items(self, items: list[dict[str, str]]) -> int:
        """Append new candidates while avoiding duplicate card identities."""
        if not items:
            return 0
        seen = {self._import_candidate_identity(item) for item in self._ocr_candidate_items}
        added = 0
        for item in items:
            key = self._import_candidate_identity(item)
            if not key or key in seen:
                continue
            self._ocr_candidate_items.append(item)
            self._ocr_candidate_vars.append(ctk.BooleanVar(value=True))
            seen.add(key)
            added += 1
        if added:
            self._ocr_candidate_items = self._merge_ocr_grammar_candidate_items(self._ocr_candidate_items)
            self._ocr_candidate_vars = [ctk.BooleanVar(value=True) for _ in self._ocr_candidate_items]
        self._render_ocr_candidate_cards()
        if added:
            self._scroll_import_candidates_to_top()
        self._update_ocr_candidate_status()
        return added

    @staticmethod
    def _ocr_quality_label(text: str) -> tuple[str, str]:
        """Return a lightweight OCR quality estimate for local candidate search.

        This does not judge the lesson content. It only catches obvious OCR
        garbage before the app creates dozens of useless candidate rows. Short,
        clean vocabulary lists are valid Import Material input and should not
        be blocked just because they contain fewer than 20 words.
        """
        cleaned = clean_ocr_text(text or "")
        tokens = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'’-]+", cleaned)
        if len(tokens) < 3:
            return "Poor", "too little readable text was extracted"

        suspicious = 0
        for token in tokens:
            lower = token.casefold().strip("'’-")
            has_vowel = bool(re.search(r"[aeiouáéíóúü]", lower))
            if len(lower) <= 1:
                suspicious += 1
            elif len(lower) >= 4 and not has_vowel:
                suspicious += 1
            elif re.search(r"(.)\1\1", lower):
                suspicious += 1
        suspicious_ratio = suspicious / max(len(tokens), 1)
        sentence_like = len(re.findall(r"[.!?¿¡]", cleaned))
        avg_len = sum(len(token.strip("'’-") or token) for token in tokens) / max(len(tokens), 1)

        # OCR screenshots of vocabulary tables often become short word lists
        # with no sentence punctuation. That is useful material, not poor OCR.
        list_like_separators = len(re.findall(r"[,;•\t]|\n", cleaned))
        short_clean_list = (
            4 <= len(tokens) < 20
            and suspicious_ratio <= 0.22
            and avg_len >= 2.6
            and sentence_like == 0
        )
        if short_clean_list:
            if len(tokens) >= 8 or list_like_separators:
                return "Good", "short clean word/phrase list looks readable"
            return "Medium", "short clean list; review candidates manually"

        if len(tokens) < 8:
            return "Medium", "short text; review candidates manually"
        if suspicious_ratio > 0.35 or avg_len < 2.6:
            return "Poor", "many tokens look like OCR noise"
        if suspicious_ratio > 0.22:
            return "Medium", "text may need manual review before candidate search"
        if sentence_like < 2 and len(tokens) >= 20:
            return "Medium", "word-list style text; review candidates manually"
        return "Good", "text looks readable enough for local cherry-pick"

    def _confirm_ocr_quality_for_candidates(self, text: str) -> bool:
        label, reason = self._ocr_quality_label(text)
        if label == "Good":
            self._ocr_status_var.set("OCR quality: Good — ready for local cherry-pick.")
            return True
        if label == "Medium":
            self._ocr_status_var.set(f"OCR quality: Medium — review candidates carefully ({reason}).")
            return True
        self._ocr_status_var.set(f"OCR quality: Poor — candidate search may produce garbage ({reason}).")
        return messagebox.askyesno(
            "OCR quality looks poor",
            "The extracted text looks unreliable. Candidate extraction may produce garbage.\n\n"
            "Recommended:\n"
            "- use a higher-resolution image,\n"
            "- crop the relevant area,\n"
            "- split two-column pages,\n"
            "- use Mistral OCR,\n"
            "- or paste text manually.\n\n"
            "Continue anyway?",
        )

    def _look_for_ocr_words_or_phrases(self) -> None:
        """Free local extraction: propose short lines/chunks as word/phrase candidates."""
        text, source = self._ocr_text_for_local_search()
        if not text.strip():
            messagebox.showwarning("Import Material", "There is no text to search. Load/extract text or paste it first.")
            return
        if source == "all text" and self._import_source_size_level(text) == "hard":
            self._ocr_candidate_status_var.set(
                "Source is too large for one review run. Highlight a chapter/section in Source text first."
            )
            messagebox.showwarning(
                "Source too large",
                "This source is too large for one candidate review. Highlight a chapter/section in Source text, then run the local finder again.",
            )
            return
        if not self._confirm_ocr_quality_for_candidates(text):
            self._ocr_candidate_status_var.set("Word/phrase extraction cancelled because OCR quality looked poor.")
            return
        phrases = self._local_word_phrase_candidates(text)
        items: list[dict[str, str]] = []
        for phrase in phrases:
            item = self._make_ocr_candidate_item("vocabulary", target=phrase, sentence="", source=f"local words ({source})")
            if item is not None:
                items.append(item)
        added = self._add_ocr_candidate_items(items)
        if added:
            self._ocr_candidate_status_var.set(f"Added {added} local word/phrase candidate(s). Cherry-pick and mark type if needed.")
            self._record_activity(f"Local word candidates: {added}")
        else:
            self._ocr_candidate_status_var.set("No new word/phrase candidates found. Try selecting a smaller fragment or use manual builder.")

    def _look_for_ocr_sentences(self) -> None:
        """Free local extraction for examples and complete sentences.

        Prepared ``target | example`` / TSV rows are a first-class local input
        format and must not require AI.  If such rows are present, preserve both
        fields as Provided Example candidates.  Otherwise fall back to the
        ordinary sentence splitter.
        """
        text, source = self._ocr_text_for_local_search()
        if not text.strip():
            messagebox.showwarning("Import Material", "There is no text to search. Load/extract text or paste it first.")
            return
        if source == "all text" and self._import_source_size_level(text) == "hard":
            self._ocr_candidate_status_var.set(
                "Source is too large for one review run. Highlight a chapter/section in Source text first."
            )
            messagebox.showwarning(
                "Source too large",
                "This source is too large for one candidate review. Highlight a chapter/section in Source text, then run the local finder again.",
            )
            return
        if not self._confirm_ocr_quality_for_candidates(text):
            self._ocr_candidate_status_var.set("Sentence extraction cancelled because OCR quality looked poor.")
            return

        pairs = self._local_target_sentence_pairs(text)
        items: list[dict[str, str]] = []
        if pairs:
            for target, sentence in pairs:
                item = self._make_ocr_candidate_item(
                    "provided_example",
                    target=target,
                    sentence=sentence,
                    source=f"local target/example pairs ({source})",
                )
                if item is not None:
                    items.append(item)
            added = self._add_ocr_candidate_items(items)
            if added:
                self._ocr_candidate_status_var.set(
                    f"Added {added} target + example pair(s) locally. No AI was used."
                )
                self._record_activity(f"Local target/example pairs: {added}")
            else:
                self._ocr_candidate_status_var.set("No new target + example pairs found; all parsed rows are already in Review.")
            return

        sentences = self._local_sentence_candidates(text)
        for sentence in sentences:
            item = self._make_ocr_candidate_item(
                "provided_example", target="", sentence=sentence, source=f"local sentences ({source})"
            )
            if item is not None:
                items.append(item)
        added = self._add_ocr_candidate_items(items)
        if added:
            self._ocr_candidate_status_var.set(
                f"Added {added} local sentence candidate(s). Cherry-pick; use Grammar type if needed."
            )
            self._record_activity(f"Local sentence candidates: {added}")
        else:
            self._ocr_candidate_status_var.set(
                "No local examples found. For prepared examples use one row per line: target | example."
            )

    @staticmethod
    def _local_target_sentence_pairs(text: str) -> list[tuple[str, str]]:
        """Parse prepared ``target | example`` or TSV rows without AI.

        Line boundaries are intentionally preserved.  This is the canonical
        clean input format used by the app, so the local finder must recognize
        it directly instead of trying to rediscover sentences heuristically.
        """
        cleaned = clean_ocr_text(text or "")
        pairs: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            separator = "|" if "|" in line else ("\t" if "\t" in line else "")
            if not separator:
                continue
            target, sentence = line.split(separator, 1)
            target = re.sub(r"\s+", " ", target).strip(" \"'“”‘’")
            sentence = re.sub(r"\s+", " ", sentence).strip(" \"'“”‘’")
            if not target or not sentence:
                continue
            key = (target.casefold(), sentence.casefold())
            if key in seen:
                continue
            seen.add(key)
            pairs.append((target, sentence))
        return pairs

    @staticmethod
    def _local_word_phrase_candidates(text: str) -> list[str]:
        """Heuristic local candidate finder for short vocabulary chunks.

        This deliberately avoids AI calls. It favors list-like lesson material:
        bullet points, short lines, table cells, comma/semicolon-separated chunks.
        """
        cleaned = clean_ocr_text(text or "")
        candidates: list[str] = []
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = re.sub(r"^[\s\-–—•*●○▪▫·]+", "", line).strip()
            line = re.sub(r"^\(?\d+[\.)]\s*", "", line).strip()
            if not line or line.endswith(":"):
                continue

            # Split obvious list/table separators. Avoid splitting regular prose too aggressively.
            pieces = re.split(r"\t|;|•|,|\s{2,}", line)
            expanded: list[str] = []
            for piece in pieces:
                piece = piece.strip(" -–—|,;:()[]{}\t")
                if not piece:
                    continue
                if " - " in piece and len(piece) <= 120:
                    expanded.extend(part.strip() for part in piece.split(" - ") if part.strip())
                elif " – " in piece and len(piece) <= 120:
                    expanded.extend(part.strip() for part in piece.split(" – ") if part.strip())
                else:
                    expanded.append(piece)

            for piece in expanded:
                piece = re.sub(r"\s+", " ", piece).strip(" \"'“”‘’.,;:()[]{}")
                if not piece:
                    continue
                word_count = len(piece.split())
                has_sentence_punctuation = bool(re.search(r"[.!?¿¡]$", piece))

                # Common OCR case: a vocabulary table becomes one clean line
                # such as "creepy fast-moving gripping haunting". Split that
                # into individual word candidates instead of treating the whole
                # line as one strange phrase or returning nothing useful.
                tokens = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ'’-]+", piece)
                clean_word_list = (
                    2 <= len(tokens) <= 14
                    and (len(tokens) >= 3 or any("-" in token or "–" in token or "—" in token for token in tokens))
                    and len(tokens) == word_count
                    and not has_sentence_punctuation
                    and all(2 <= len(token.strip("'’-") or token) <= 28 for token in tokens)
                )
                if clean_word_list:
                    candidates.extend(token.strip("'’-") for token in tokens if token.strip("'’-"))
                    continue

                if 1 <= word_count <= 8 and 2 <= len(piece) <= 90 and not has_sentence_punctuation:
                    candidates.append(piece)

        return ModernVocabularyGui._dedupe_local_candidates(candidates, limit=120)

    @staticmethod
    def _local_sentence_candidates(text: str) -> list[str]:
        """Heuristic local sentence splitter for free cherry-picking."""
        cleaned = clean_ocr_text(text or "")
        normalized = re.sub(r"\s+", " ", cleaned).strip()
        if not normalized:
            return []

        pieces = re.split(r"(?<=[.!?])\s+(?=[¿¡A-ZÁÉÍÓÚÜÑ0-9])", normalized)
        candidates: list[str] = []
        for piece in pieces:
            sentence = piece.strip(" \"'“”‘’")
            if not sentence:
                continue
            # Split very long OCR blobs again on question starts.
            subpieces = re.split(r"\s+(?=¿)", sentence) if len(sentence) > 220 else [sentence]
            for subpiece in subpieces:
                value = subpiece.strip(" \"'“”‘’")
                word_count = len(value.split())
                if 4 <= word_count <= 45 and 12 <= len(value) <= 260:
                    candidates.append(value)
        return ModernVocabularyGui._dedupe_local_candidates(candidates, limit=120)

    @staticmethod
    def _dedupe_local_candidates(values: list[str], limit: int = 120) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = re.sub(r"\s+", " ", value).strip()
            key = cleaned.casefold()
            if not cleaned or key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
            if len(result) >= limit:
                break
        return result

    def _ocr_use_selection_as_target(self) -> None:
        selected = self._ocr_get_selected_text()
        if not selected:
            messagebox.showwarning("Import Material", "Highlight a word or phrase in the source text first.")
            return
        target = clean_ocr_text(selected).replace("\n", " ").strip()
        self._ocr_manual_target_var.set(target)
        self._ocr_candidate_status_var.set("Target filled. Add an example or click Add candidate.")

    def _ocr_use_selection_as_example(self) -> None:
        selected = self._ocr_get_selected_text()
        if not selected:
            messagebox.showwarning("Import Material", "Highlight an example sentence or context first.")
            return
        sentence = clean_ocr_text(selected).replace("\n", " ").strip()
        self._ocr_manual_example_var.set(sentence)
        self._ocr_candidate_status_var.set("Example filled. Click Add candidate when ready.")

    def _ocr_manual_target(self) -> str:
        value = self._ocr_manual_target_var.get().strip()
        lower = value.casefold()
        if lower.startswith("target:") or lower.startswith("saved target:"):
            return value.split(":", 1)[1].strip()
        return value

    def _ocr_add_manual_candidate(self) -> None:
        candidate_type = self._ocr_manual_candidate_type_var.get().strip() or "vocabulary"
        target = self._ocr_manual_target()
        sentence = self._ocr_manual_example_var.get().strip()
        if not target and not sentence:
            messagebox.showwarning("Import Material", "Fill target/example first, or use selected text.")
            return
        if candidate_type == "vocabulary" and not target:
            messagebox.showwarning("Import Material", "Vocabulary candidates need a target word or phrase.")
            return
        self._ocr_append_candidate(candidate_type, target, sentence)
        self._ocr_clear_manual_candidate_fields()

    def _ocr_clear_manual_candidate_fields(self) -> None:
        self._ocr_manual_target_var.set("")
        self._ocr_manual_example_var.set("")
        self._cleanup_runtime_memory("clear manual import candidate fields", aggressive=False)

    # Backward-compatible callbacks from previous OCR buttons.
    def _ocr_add_selection_as_provided_example(self) -> None:
        self._ocr_use_selection_as_example()
        self._ocr_manual_candidate_type_var.set("provided_example")
        self._ocr_add_manual_candidate()

    def _ocr_add_selection_as_vocabulary(self) -> None:
        self._ocr_use_selection_as_target()
        self._ocr_manual_candidate_type_var.set("vocabulary")
        self._ocr_add_manual_candidate()

    def _ocr_add_selection_as_grammar(self) -> None:
        self._ocr_use_selection_as_target()
        self._ocr_manual_candidate_type_var.set("grammar")
        self._ocr_add_manual_candidate()

    def _run_ocr_import_pipeline(self) -> None:
        method = self._ocr_method_var.get()
        if "Mistral" in method:
            self._run_mistral_ocr_auto_candidates()
            return
        if "OpenAI" in method and ("Vision OCR" in method or "multimodal" in method):
            self._run_multimodal_ocr_text("OpenAI")
            return
        if "Gemini" in method and ("Vision OCR" in method or "multimodal" in method):
            self._run_multimodal_ocr_text("Gemini")
            return
        self._run_local_ocr_import()

    def _run_ocr_import(self) -> None:
        """Backward-compatible callback name for older buttons/autosaves."""
        self._run_ocr_import_pipeline()

    def _run_local_ocr_import(self) -> None:
        if not self._ocr_source_paths:
            # Allow pasted text as a valid source for candidate search.
            pasted = self._get_ocr_text()
            if pasted.strip():
                self._ocr_status_var.set("Pasted text is already loaded. Choose what you want to find next.")
                return
            messagebox.showwarning("Import Material", "Load a TXT/HTML, PDF, image, or paste text first.")
            return
        self._ocr_status_var.set("Reading material locally...")
        self._root.update_idletasks()
        try:
            text = extract_text_from_paths(self._ocr_source_paths)
        except OcrExtractionError as exc:
            self._ocr_status_var.set("Local reading failed.")
            messagebox.showerror("Import Material", str(exc))
            return
        except Exception as exc:
            self._ocr_status_var.set("Local reading failed.")
            messagebox.showerror("Import Material", f"Unexpected import error: {exc}")
            return
        if not text.strip():
            self._ocr_status_var.set("No text extracted. Try Mistral extraction or a clearer image.")
            messagebox.showwarning("Import Material", "No text was extracted.")
            return
        self._set_ocr_text(text)
        label, reason = self._ocr_quality_label(text)
        self._ocr_status_var.set(
            f"Read {len(text.split())} word(s) locally. Text quality: {label} — {reason}. "
            "Now choose what you want to find, then use AI search or the local finder."
        )
        self._record_activity("Import material read locally")

    def _run_mistral_ocr_auto_candidates(self) -> None:
        """Run cloud OCR through Mistral only. Candidate picking stays local/manual by default."""
        if not self._ocr_source_paths:
            pasted = self._get_ocr_text()
            if pasted.strip():
                self._ocr_status_var.set("Using pasted text. Mistral OCR is not needed. Click Look for words/sentences.")
                return
            messagebox.showwarning("Mistral OCR", "Load a PDF/image or paste text first.")
            return

        text_like_paths = [path for path in self._ocr_source_paths if path.suffix.casefold() in (TEXT_EXTENSIONS | HTML_EXTENSIONS)]
        image_or_pdf_paths = [path for path in self._ocr_source_paths if path not in text_like_paths]

        # TXT/HTML files do not need Mistral OCR. Read them locally and let the
        # user use the free local cherry-pick buttons. This path never calls
        # local Tesseract or Card AI.
        if text_like_paths and not image_or_pdf_paths:
            self._ocr_status_var.set("Reading TXT/HTML locally...")
            self._root.update_idletasks()
            try:
                text = extract_text_from_paths(text_like_paths)
            except Exception as exc:
                self._ocr_status_var.set("TXT/HTML import failed.")
                messagebox.showerror("Import Material", f"Text import failed: {exc}")
                return
            self._set_ocr_text(text)
            self._ocr_status_var.set(f"Read {len(text.split())} word(s) locally. Choose what you want to find next.")
            return

        if text_like_paths and image_or_pdf_paths:
            messagebox.showwarning(
                "Mistral OCR",
                "For Mistral mode, load either PDF/images or TXT/HTML, not both at once.",
            )
            return

        self._ocr_status_var.set("Running Mistral OCR. This uses Mistral API credits for text extraction only...")
        self._ocr_candidate_status_var.set("Mistral OCR running. After text is returned, use free local cherry-pick buttons.")
        self._root.update_idletasks()
        try:
            text = extract_text_with_mistral(self._ocr_source_paths)
        except OcrExtractionError as exc:
            self._ocr_status_var.set("Mistral extraction failed.")
            messagebox.showerror("Mistral OCR", str(exc))
            return
        except Exception as exc:
            self._ocr_status_var.set("Mistral extraction failed.")
            messagebox.showerror("Mistral OCR", f"Unexpected Mistral OCR error: {exc}")
            return
        if not text.strip():
            self._ocr_status_var.set("Mistral returned no text.")
            messagebox.showwarning("Mistral OCR", "No text was extracted.")
            return
        self._set_ocr_text(text)
        self._ocr_status_var.set(
            f"Mistral extracted {len(text.split())} word(s). Click Look for words/phrases or Look for sentences."
        )

    def _run_multimodal_ocr_text(self, provider: str) -> None:
        """Use a vision-capable model as OCR only: image/PDF -> editable text box."""
        if self._ocr_ai_running:
            self._ocr_candidate_status_var.set("Vision OCR is already running. Wait for it to finish.")
            return
        if not self._ocr_source_paths:
            pasted = self._get_ocr_text()
            if pasted.strip():
                self._ocr_status_var.set("Pasted text is already loaded. Click Find candidates with selected strategy if needed.")
                return
            messagebox.showwarning("Vision OCR", "Load an image or PDF first.")
            return

        text_like_paths = [
            path for path in self._ocr_source_paths
            if path.suffix.casefold() in (TEXT_EXTENSIONS | HTML_EXTENSIONS)
        ]
        if text_like_paths:
            messagebox.showwarning(
                "Vision OCR",
                "Vision OCR is for image/PDF material. Use Local extraction for TXT/HTML files.",
            )
            return

        self._ocr_ai_running = True
        run_button = getattr(self, "_ocr_run_button", None)
        ai_button = getattr(self, "_ocr_ai_button", None)
        raw_text = ""
        try:
            if run_button is not None:
                run_button.configure(state="disabled", text=f"Running {provider} Vision OCR...")
            if ai_button is not None:
                ai_button.configure(state="disabled")
            names = ", ".join(path.name for path in self._ocr_source_paths[:3])
            if len(self._ocr_source_paths) > 3:
                names += f" + {len(self._ocr_source_paths) - 3} more"
            self._ocr_status_var.set(f"Running {provider} Vision OCR on: {names}")
            self._ocr_candidate_status_var.set(
                f"{provider} Vision OCR will return text only. It will not create candidates or Queue items."
            )
            self._root.update_idletasks()
            raw_text = extract_text_with_multimodal(
                self._ocr_source_paths,
                provider=provider,
                prompt=build_multimodal_ocr_prompt(),
                model=self._multimodal_model_name(provider),
            )
        except OcrExtractionError as exc:
            LOGGER.exception("Vision OCR failed")
            self._ocr_status_var.set(f"{provider} Vision OCR failed.")
            self._ocr_candidate_status_var.set("Vision OCR failed; try Mistral OCR or crop the image.")
            messagebox.showerror("Vision OCR", str(exc))
            return
        except Exception as exc:
            LOGGER.exception("Unexpected Vision OCR failed")
            self._ocr_status_var.set(f"{provider} Vision OCR failed.")
            self._ocr_candidate_status_var.set("Vision OCR failed; try another OCR provider.")
            messagebox.showerror("Vision OCR", f"Unexpected Vision OCR error: {exc}")
            return
        finally:
            self._ocr_ai_running = False
            if run_button is not None:
                run_button.configure(state="normal", text=self._ocr_import_action_label())
            if ai_button is not None:
                ai_button.configure(state="normal")

        text = self._ocr_clean_json_text(raw_text).strip()
        if not text:
            self._ocr_status_var.set(f"{provider} Vision OCR returned no text.")
            self._ocr_candidate_status_var.set("No text was extracted. Try Mistral OCR or a clearer crop.")
            return

        self._set_ocr_text(text)
        self._set_ocr_candidate_items([])
        label, reason = self._ocr_quality_label(text)
        self._ocr_status_var.set(
            f"{provider} Vision OCR extracted {len(text.split())} word(s). OCR quality: {label} — {reason}."
        )
        self._ocr_candidate_status_var.set(
            "Vision OCR produced text only. Review/clean the text, then click Find candidates with selected strategy."
        )
        self._record_activity(f"{provider} Vision OCR text extracted")


    def _run_multimodal_import_candidates(self, provider: str) -> None:
        """Advanced: extract structured candidates directly from images/PDF pages.

        This is intentionally not used by the OCR button. Normal Vision OCR
        returns only text and requires a separate Find candidates click.
        """
        if self._ocr_ai_running:
            self._ocr_candidate_status_var.set("Direct image candidate search is already running. Wait for it to finish.")
            return
        if not self._ocr_source_paths:
            pasted = self._get_ocr_text()
            if pasted.strip():
                self._ocr_status_var.set("Pasted text does not need direct image extraction. Use Find candidates with selected strategy.")
                return
            messagebox.showwarning("Multimodal import", "Load an image or PDF first.")
            return

        text_like_paths = [
            path for path in self._ocr_source_paths
            if path.suffix.casefold() in (TEXT_EXTENSIONS | HTML_EXTENSIONS)
        ]
        if text_like_paths:
            messagebox.showwarning(
                "Multimodal import",
                "Direct image extraction is for image/PDF material. Use Local extraction for TXT/HTML files.",
            )
            return

        ui_mode = self._ocr_mode_var.get().strip() or "Smart vocabulary"
        mode = self._ocr_internal_mode(ui_mode)
        self._ocr_ai_running = True
        run_button = getattr(self, "_ocr_run_button", None)
        ai_button = getattr(self, "_ocr_ai_button", None)
        try:
            if run_button is not None:
                run_button.configure(state="disabled", text="Running direct image extraction...")
            if ai_button is not None:
                ai_button.configure(state="disabled")
            names = ", ".join(path.name for path in self._ocr_source_paths[:3])
            if len(self._ocr_source_paths) > 3:
                names += f" + {len(self._ocr_source_paths) - 3} more"
            self._ocr_status_var.set(f"Running direct image candidate search with {provider} on: {names}")
            self._ocr_candidate_status_var.set(
                f"{provider} is extracting candidates directly from the image. This is an advanced API workflow."
            )
            self._root.update_idletasks()
            prompt = build_multimodal_import_extraction_prompt(
                target_language=self._language_var.get(),
                explanation_language=self._explanation_language_var.get(),
                extraction_mode=mode,
                topic_context=self._batch_topic_var.get(),
            )
            raw_text = extract_candidates_with_multimodal(
                self._ocr_source_paths,
                provider=provider,
                prompt=prompt,
                model=self._multimodal_model_name(provider),
            )
            raw_count = self._count_ai_json_candidates(raw_text)
            hard_limit = self._ocr_candidate_hard_limit(mode)
            if raw_count is not None and raw_count > hard_limit:
                self._reject_runaway_ai_candidates(raw_count, hard_limit, mode, f"{provider} multimodal")
                return
            items = self._ocr_candidate_items_from_ai_response(
                raw_text, default_mode=mode, source=f"{provider} multimodal"
            )
            if len(items) > hard_limit:
                self._reject_runaway_ai_candidates(len(items), hard_limit, mode, f"{provider} multimodal")
                return
        except OcrExtractionError as exc:
            LOGGER.exception("Multimodal import failed")
            self._ocr_status_var.set(f"{provider} direct image extraction failed.")
            self._ocr_candidate_status_var.set("Direct image extraction failed; try Vision OCR or Mistral OCR first.")
            messagebox.showerror("Direct image extraction", str(exc))
            return
        except Exception as exc:
            LOGGER.exception("Unexpected multimodal import failed")
            self._ocr_status_var.set(f"{provider} direct image extraction failed.")
            self._ocr_candidate_status_var.set("Multimodal import failed; try another import provider.")
            messagebox.showerror("Direct image extraction", f"Unexpected direct image extraction error: {exc}")
            return
        finally:
            self._ocr_ai_running = False
            if run_button is not None:
                run_button.configure(state="normal", text=self._ocr_import_action_label())
            if ai_button is not None:
                ai_button.configure(state="normal")

        if not items:
            self._set_ocr_text(self._ocr_clean_json_text(raw_text))
            self._set_ocr_candidate_items([])
            self._ocr_status_var.set(f"{provider} direct image extraction returned text but no usable candidates.")
            self._ocr_candidate_status_var.set("No usable candidates found. Try another provider, crop, or use manual picker.")
            return

        total = len(items)
        self._ocr_status_var.set(f"{provider} direct image extraction found {total} candidate(s).")
        self._set_ocr_text(self._ocr_review_text_from_candidate_items(items, provider=provider))
        self._set_ocr_candidate_items(items)
        selected = sum(1 for var in self._ocr_candidate_vars if var.get())
        self._ocr_candidate_status_var.set(
            f"{provider} direct image extraction found {total} candidate(s); {selected} selected by default based on review priority. "
            "Review before Queue."
        )
        self._record_activity(f"{provider} direct image candidates: {len(items)}")

    @staticmethod
    def _ocr_review_text_from_candidate_items(items: list[dict[str, str]], provider: str = "Multimodal") -> str:
        """Create a readable reviewed-source summary from structured multimodal candidates."""
        lines = [f"--- {provider} multimodal structured extraction ---"]
        for index, item in enumerate(items, start=1):
            kind = item.get("type", "")
            target = item.get("target", "")
            sentence = item.get("sentence", "")
            source_rule = item.get("source_rule", "") or item.get("reason", "")
            source_type = item.get("source_type", "")
            strategy = item.get("strategy", "")
            lines.append(f"\n[{index}] {kind}")
            if target:
                lines.append(f"Target: {target}")
            if sentence:
                lines.append(f"Example/audio: {sentence}")
            if source_rule:
                lines.append(f"Use/source note: {source_rule}")
            if source_type or strategy:
                lines.append(f"Detected as: {source_type or '-'} | Strategy: {strategy or '-'}")
        return "\n".join(lines).strip()

    def _clean_ocr_preview_text(self) -> None:
        original = self._get_ocr_text()
        if not original.strip():
            self._ocr_status_var.set("No source text to clean.")
            self._ocr_candidate_status_var.set("No source text to clean.")
            return
        text = clean_ocr_text(original)
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
        text = re.sub(r"<img\b[^>]*>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        self._set_ocr_text(text)
        removed_chars = max(0, len(original) - len(text))
        if text == original.strip():
            message = f"Text already looks clean: {len(text.split())} word(s)."
        else:
            message = f"Cleaned source text: {len(text.split())} word(s), removed {removed_chars} character(s)/artifact(s)."
        self._ocr_status_var.set(message)
        self._ocr_candidate_status_var.set(message)
        self._scroll_import_text_to_top()

    def _extract_ocr_candidates_with_ai(self) -> None:
        self._extract_ocr_candidates_with_ai_from_text(self._get_ocr_text(), source="all text")

    def _extract_ocr_candidates_from_selection_with_ai(self) -> None:
        selected = self._ocr_get_selected_text()
        if not selected.strip():
            messagebox.showwarning("Import Material", "Highlight a fragment in the source text first.")
            return
        self._extract_ocr_candidates_with_ai_from_text(selected, source="selection")

    def _retry_last_ocr_ai_extraction(self) -> None:
        request = self._ocr_last_ai_request
        if request is None:
            self._ocr_candidate_status_var.set("No previous AI candidate search request is available.")
            return
        text, source = request
        self._extract_ocr_candidates_with_ai_from_text(text, source=source, retry_attempt=0)

    @staticmethod
    def _is_retryable_import_error(exc: Exception) -> bool:
        status = ModernVocabularyGui._http_status_from_exception(exc)
        return status == 429 or (status is not None and 500 <= status <= 599) or ModernVocabularyGui._is_timeout_detail(str(exc))

    @staticmethod
    def _friendly_import_error_message(exc: Exception, provider_name: str) -> str:
        status = ModernVocabularyGui._http_status_from_exception(exc)
        if status == 429:
            return f"{provider_name} is rate-limited right now. Your source text is still here; retry later or use another provider."
        if status is not None and 500 <= status <= 599:
            return f"{provider_name} is temporarily unavailable (HTTP {status}). Your source text and previous candidates were preserved."
        if ModernVocabularyGui._is_timeout_detail(str(exc)):
            return f"{provider_name} timed out. Your source text and previous candidates were preserved."
        return f"Candidate extraction failed with {provider_name}. The technical details were saved to the log."

    @classmethod
    def _dedupe_import_candidate_items(cls, items: list[dict[str, str]]) -> list[dict[str, str]]:
        """Deduplicate merged candidates using the final card identity."""
        result: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in items:
            key = cls._import_candidate_identity(item)
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result

    @classmethod
    def _limit_merged_import_candidates(
        cls,
        items: list[dict[str, str]],
        mode: str,
    ) -> tuple[list[dict[str, str]], str]:
        """Deduplicate whole-document results without imposing a target count.

        Candidate count is content-driven. A short page may legitimately yield
        only a few useful items, while a dense glossary or advanced lesson may
        yield well over one hundred. The model is responsible for quality
        selection; this merge step only removes exact duplicates created by
        overlapping chunks.
        """
        clean = cls._dedupe_import_candidate_items(items)
        return clean, ""

    def _extract_ocr_candidates_with_ai_from_text(
        self,
        text: str,
        source: str,
        retry_attempt: int = 0,
        *,
        run_id: int | None = None,
        run_settings: dict[str, str] | None = None,
    ) -> None:
        # Delayed retries carry the original generation id so an old retry can
        # never overwrite a newer user-started search.
        if run_id is not None and run_id != self._ocr_active_ai_search_id:
            LOGGER.info(
                "Ignoring stale Import Material retry: run_id=%s active_run_id=%s",
                run_id,
                self._ocr_active_ai_search_id,
            )
            return

        if not self._ai_clients:
            messagebox.showwarning("Import Material", "No AI provider is configured. Open Setup and configure Local, Hybrid/BYOK or API/BYOK first.")
            self._ocr_candidate_status_var.set("AI candidate search unavailable until a provider is configured in Setup.")
            return
        if self._ocr_ai_running:
            self._ocr_candidate_status_var.set("Candidate extraction is already running. Wait for it to finish.")
            return

        if run_id is None:
            self._ocr_ai_search_serial += 1
            run_id = self._ocr_ai_search_serial
            self._ocr_active_ai_search_id = run_id

        full_text = text or ""
        if not full_text.strip():
            messagebox.showwarning("Import Material", "There is no source text to analyze.")
            return

        size_level = self._import_source_size_level(full_text)
        signature = self._import_source_signature(full_text)
        chars, words = signature
        if size_level == "hard":
            message = (
                f"This {source} contains about {words:,} words ({chars:,} characters). "
                "It is too large for one candidate-search run. Highlight a smaller chapter/section in Source text "
                "and use Find from selected text."
            )
            self._ocr_candidate_status_var.set(message)
            messagebox.showwarning("Source too large", message)
            return
        if (
            size_level == "soft"
            and retry_attempt == 0
            and getattr(self, "_ocr_large_source_approved_signature", None) != signature
        ):
            chunks_for_warning = len(self._split_import_text_for_ai(full_text))
            proceed = messagebox.askyesno(
                "Analyse large source?",
                f"This {source} contains about {words:,} words ({chars:,} characters) and will require about "
                f"{chunks_for_warning} AI analysis calls.\n\n"
                "For cleaner review, analysing one lesson/chapter at a time is recommended.\n\n"
                "Analyse the entire source anyway?",
            )
            if not proceed:
                self._ocr_candidate_status_var.set(
                    "Large-source analysis cancelled. Highlight a chapter/section and use Find from selected text."
                )
                return
            self._ocr_large_source_approved_signature = signature

        if run_settings is None:
            ui_mode = self._ocr_mode_var.get().strip() or "Smart vocabulary"
            mode = self._ocr_internal_mode(ui_mode)
            provider_name = (self._ocr_ai_provider_var.get().strip() or self._provider_var.get()).strip()
            if provider_name not in self._ai_clients:
                provider_name = self._provider_var.get()
            run_settings = {
                "ui_mode": ui_mode,
                "mode": mode,
                "provider_name": provider_name,
                "target_language": self._language_var.get(),
                "explanation_language": self._explanation_language_var.get(),
                "topic_context": self._batch_topic_var.get(),
            }
        else:
            ui_mode = run_settings.get("ui_mode", "Smart vocabulary")
            mode = run_settings.get("mode") or self._ocr_internal_mode(ui_mode)
            provider_name = run_settings.get("provider_name") or self._provider_var.get()
            if provider_name not in self._ai_clients:
                provider_name = self._provider_var.get()
                run_settings["provider_name"] = provider_name

        chunks = self._split_import_text_for_ai(full_text)
        if not chunks:
            return
        LOGGER.info(
            "Import AI source coverage: run_id=%s mode=%s source_chars=%s source_words=%s chunks=%s chunk_chars=%s",
            run_id,
            mode,
            len(full_text),
            len(full_text.split()),
            len(chunks),
            [len(chunk) for chunk in chunks],
        )

        # A deliberate new search replaces the previous result set. Keeping old
        # cards visible after a blocked/failed rerun made it look as if English
        # results belonged to a later Spanish search.
        if retry_attempt == 0:
            self._ocr_review_priority_filter_var.set("All priorities")
            self._ocr_review_type_filter_var.set("All types")
            self._ocr_review_search_var.set("")
            self._set_ocr_candidate_items([])
            self._ocr_candidate_status_var.set(
                f"Starting fresh candidate search · {run_settings['target_language']} · {ui_mode}."
            )

        self._ocr_last_ai_request = (full_text, source)
        retry_button = getattr(self, "_ocr_retry_button", None)
        if retry_button is not None:
            retry_button.configure(state="normal")
        previous_provider = self._provider_var.get()
        model_name = self._current_ai_model_name(provider_name, workflow="import")
        LOGGER.info(
            "Import candidate search start: run_id=%s retry=%s language=%s mode=%s provider=%s "
            "source=%s chars=%s words=%s chunks=%s",
            run_id,
            retry_attempt,
            run_settings["target_language"],
            mode,
            provider_name,
            source,
            chars,
            words,
            len(chunks),
        )
        attempt_label = f" · attempt {retry_attempt + 1}/3" if retry_attempt else ""
        part_label = f" · {len(chunks)} part(s)" if len(chunks) > 1 else ""
        self._ocr_candidate_status_var.set(
            f"Finding candidates from the entire {source} with {provider_name} import model {model_name}{part_label}{attempt_label}..."
        )
        self._ocr_ai_running = True
        ai_button = getattr(self, "_ocr_ai_button", None)
        merged_items: list[dict[str, str]] = []
        try:
            if ai_button is not None:
                ai_button.configure(state="disabled", text="Finding...")
            self._root.update_idletasks()
            client = self._ai_clients[provider_name]
            generate_text = getattr(client, "_generate_text", None)
            if generate_text is None:
                messagebox.showerror("Import Material", f"{provider_name} client does not expose text generation.")
                return

            per_request_hard_limit = self._ocr_candidate_hard_limit(mode)
            for part_index, chunk in enumerate(chunks, start=1):
                self._ocr_candidate_status_var.set(
                    f"Analysing part {part_index} of {len(chunks)} · {len(chunk):,} characters · {provider_name} {model_name}..."
                )
                self._root.update_idletasks()
                prompt = build_ocr_candidate_extraction_prompt(
                    extracted_text=chunk,
                    target_language=run_settings["target_language"],
                    explanation_language=run_settings["explanation_language"],
                    extraction_mode=mode,
                    topic_context=run_settings["topic_context"],
                )
                try:
                    raw_text = generate_text(prompt, workflow="import")
                except TypeError:
                    raw_text = generate_text(prompt)
                raw_count = self._count_ai_json_candidates(raw_text)
                LOGGER.info(
                    "Import candidate search part raw result: run_id=%s part=%s/%s raw_candidates=%s raw_chars=%s",
                    run_id,
                    part_index,
                    len(chunks),
                    raw_count,
                    len(raw_text or ""),
                )
                if raw_count is not None and raw_count > per_request_hard_limit:
                    self._reject_runaway_ai_candidates(raw_count, per_request_hard_limit, mode, f"{source} part {part_index}")
                    return
                part_items = self._ocr_candidate_items_from_ai_response(
                    raw_text,
                    default_mode=mode,
                    source=f"{source} · part {part_index}/{len(chunks)}",
                )
                LOGGER.info(
                    "Import candidate search part parsed: run_id=%s part=%s/%s parsed_candidates=%s",
                    run_id,
                    part_index,
                    len(chunks),
                    len(part_items),
                )
                if len(part_items) > per_request_hard_limit:
                    self._reject_runaway_ai_candidates(len(part_items), per_request_hard_limit, mode, f"{source} part {part_index}")
                    return

                for item in part_items:
                    item.setdefault("source_part", f"{part_index}/{len(chunks)}")
                merged_items.extend(part_items)
        except Exception as exc:
            LOGGER.exception("Candidate extraction failed")
            friendly = self._friendly_import_error_message(exc, provider_name)
            if self._is_retryable_import_error(exc) and retry_attempt < 2:
                delay_seconds = (60, 90)[retry_attempt]
                self._ocr_candidate_status_var.set(
                    f"{friendly} Automatic retry in {delay_seconds}s ({retry_attempt + 1}/2 retries). You can also click Retry AI candidate search."
                )
                self._root.after(
                    delay_seconds * 1000,
                    lambda t=full_text, src=source, attempt=retry_attempt + 1, rid=run_id, settings=dict(run_settings): self._extract_ocr_candidates_with_ai_from_text(
                        t,
                        source=src,
                        retry_attempt=attempt,
                        run_id=rid,
                        run_settings=settings,
                    ),
                )
            else:
                self._ocr_candidate_status_var.set(friendly + " Use Retry AI candidate search when ready.")
                messagebox.showerror("Import Material", friendly)
            return
        finally:
            self._provider_var.set(previous_provider)
            self._ocr_ai_running = False
            if ai_button is not None:
                ai_button.configure(state="normal", text="Find candidates with AI")

        if run_id != self._ocr_active_ai_search_id:
            LOGGER.info(
                "Discarding stale Import Material result before render: run_id=%s active_run_id=%s",
                run_id,
                self._ocr_active_ai_search_id,
            )
            return

        items, limit_note = self._limit_merged_import_candidates(merged_items, mode)
        LOGGER.info(
            "Import candidate search merged: run_id=%s raw_merged=%s deduped=%s language=%s mode=%s",
            run_id,
            len(merged_items),
            len(items),
            run_settings["target_language"],
            mode,
        )
        if not items:
            self._ocr_candidate_status_var.set("No candidates found. Edit the source text, try another mode, or use the basic local finder.")
            self._set_ocr_candidate_items([])
            return
        total = len(items)
        self._set_ocr_candidate_items(items)
        selected = sum(1 for var in self._ocr_candidate_vars if var.get())
        suffix = f" {limit_note}" if limit_note else ""
        self._ocr_candidate_status_var.set(
            f"AI analysed all {len(chunks)} part(s) and found {total} reviewed candidate(s); "
            f"{selected} selected by default based on review priority.{suffix}"
        )
        self._record_activity(f"Import candidates: {len(items)} from {len(chunks)} part(s)")

    @staticmethod
    def _ocr_clean_json_text(raw_text: str) -> str:
        value = (raw_text or "").strip()
        value = value.replace("```json", "").replace("```", "").strip()
        return value

    @staticmethod
    def _normalize_smart_grammar_source_type(value: str) -> str:
        """Normalize AI source-type labels for Smart grammar import."""
        text = (value or "").strip().casefold().replace("-", "_").replace(" ", "_")
        aliases = {
            "structure": "structure_sentence",
            "structure_example": "structure_sentence",
            "structure_sentence": "structure_sentence",
            "pattern_sentence": "structure_sentence",
            "usage_example": "structure_sentence",
            "grammar_rule_with_example": "structure_sentence",
            "rule": "rule",
            "grammar_rule": "rule",
            "source_rule": "rule",
            "definition": "rule",
            "explanation": "rule",
            "transformation": "transformation",
            "word_form": "transformation",
            "wordform": "transformation",
            "exercise": "exercise",
            "gap_fill": "exercise",
            "multiple_choice": "exercise",
            "sentence": "sentence_only",
            "sentence_only": "sentence_only",
            "provided_example": "provided_example",
            "table_row": "table_row",
            "table": "table_row",
            "highlighted_item": "highlighted_item",
            "highlighted": "highlighted_item",
            "marked_item": "highlighted_item",
            "vocabulary": "vocabulary",
            "vocabulary_list": "vocabulary_list",
            "vocab_list": "vocabulary_list",
            "colloquial_expression": "colloquial_expression",
            "colloquial_expressions": "colloquial_expression",
            "reading_text_collocation": "reading_text_collocation",
            "dialogue_example": "dialogue_example",
            "expanded_variant": "expanded_variant",
        }
        return aliases.get(text, text or "")

    @staticmethod
    def _normalize_vocabulary_source_role(value: str) -> str:
        """Normalize semantic source roles returned by Smart Vocabulary extraction.

        This role answers a different question from candidate type: it describes
        what the *visible source fragment* is. Only ``usage_example`` is safe to
        preserve as the learner example.
        """
        text = clean_ocr_text(str(value or "")).strip().casefold().replace("-", "_").replace(" ", "_")
        aliases = {
            "example": "usage_example",
            "provided_example": "usage_example",
            "learner_example": "usage_example",
            "usage_sentence": "usage_example",
            "heading": "heading_label",
            "title": "heading_label",
            "label": "heading_label",
            "category_label": "heading_label",
            "definition": "definition_context",
            "glossary_definition": "definition_context",
            "context_definition": "definition_context",
            "list": "list_item",
            "vocabulary_list": "list_item",
            "exercise_task": "exercise",
            "task": "exercise",
            "question": "exercise",
        }
        normalized = aliases.get(text, text)
        allowed = {
            "usage_example",
            "heading_label",
            "definition_context",
            "list_item",
            "fragment",
            "exercise",
            "unknown",
        }
        return normalized if normalized in allowed else ""

    @classmethod
    def _infer_smart_grammar_source_type(cls, candidate_type: str, target: str, sentence: str, source_rule: str = "") -> str:
        """Best-effort classifier for AI/fallback candidate rows.

        This only drives UI labels and Queue metadata. It should not block the
        user from editing/cherry-picking the candidate.
        """
        kind = cls._normalize_ocr_candidate_type(candidate_type)
        target = clean_ocr_text(str(target or "")).strip()
        sentence = clean_ocr_text(str(sentence or "")).strip()
        source_rule = clean_ocr_text(str(source_rule or "")).strip()
        combined = f"{target} {sentence} {source_rule}".casefold()
        if kind == "vocabulary":
            return "vocabulary"
        if kind == "provided_example":
            return "provided_example"
        if re.search(r"_{2,}|\b___\b|\b(blank|gap[- ]?fill|choose|circle|complete)\b", combined):
            return "exercise"
        if "->" in target or "→" in target:
            return "transformation"
        if source_rule or cls._ocr_looks_like_rule_explanation(sentence):
            return "rule"
        if target and sentence:
            return "structure_sentence"
        if sentence and not target:
            return "sentence_only"
        return "rule" if target else ""

    @classmethod
    def _smart_grammar_strategy_for_source_type(cls, source_type: str) -> str:
        mapping = {
            "structure_sentence": "preserve_source_sentence",
            "rule": "generated_example_from_rule",
            "transformation": "word_form_example",
            "exercise": "exercise_draft_review_answer",
            "sentence_only": "infer_later",
            "provided_example": "preserve_source_sentence",
            "table_row": "preserve_table_row",
            "highlighted_item": "highlighted_source_sentence",
            "vocabulary": "vocabulary_candidate",
            "vocabulary_list": "vocabulary_candidate",
            "colloquial_expression": "vocabulary_with_source_sentence",
            "reading_text_collocation": "vocabulary_candidate",
            "dialogue_example": "vocabulary_with_source_sentence",
            "expanded_variant": "expanded_vocabulary_variant",
        }
        return mapping.get(source_type, "review_candidate")

    def _ocr_candidate_items_from_ai_response(self, raw_text: str, default_mode: str, source: str) -> list[dict[str, str]]:
        """Convert AI JSON into structured candidates with Smart Grammar metadata.

        v11.2 keeps the candidate basket editable, but no longer throws away
        why AI chose a candidate. Grammar candidates can now show:
        detected source type + chosen strategy + optional source rule.
        """
        cleaned = self._ocr_clean_json_text(raw_text)
        items: list[dict[str, str]] = []
        try:
            data = json.loads(cleaned)
            candidates = data.get("candidates", data) if isinstance(data, dict) else data
            if not isinstance(candidates, list):
                raise ValueError("candidates is not a list")
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                raw_type = str(candidate.get("type") or default_mode or "vocabulary")
                candidate_type = self._normalize_ocr_candidate_type(raw_type, default_mode)
                default_mode_key = (default_mode or "").strip().casefold()
                if default_mode_key in {"vocabulary", "vocabulary + source examples"}:
                    # Strict vocabulary modes never produce Provided Examples.
                    # Any source sentence stays attached as context metadata.
                    candidate_type = "vocabulary"
                elif default_mode_key == "smart vocabulary" and candidate_type == "grammar":
                    # Smart Vocabulary may mix vocabulary and provided_example,
                    # but grammar belongs only to Grammar/Smart Grammar/Mixed.
                    candidate_type = "vocabulary"
                elif self._is_grammar_import_mode(default_mode) and candidate_type == "provided_example":
                    candidate_type = "grammar"
                target = str(
                    candidate.get("target")
                    or candidate.get("word")
                    or candidate.get("phrase")
                    or candidate.get("structure")
                    or candidate.get("grammar")
                    or ""
                ).strip()
                sentence = str(
                    candidate.get("sentence")
                    or candidate.get("provided_example")
                    or candidate.get("example")
                    or candidate.get("source_sentence")
                    or candidate.get("context")
                    or ""
                ).strip()
                source_rule = str(
                    candidate.get("source_rule")
                    or candidate.get("rule")
                    or candidate.get("source_note")
                    or candidate.get("use_note")
                    or candidate.get("exercise")
                    or ""
                ).strip()
                source_role = str(candidate.get("source_role") or "").strip()
                vocabulary_source_role = self._normalize_vocabulary_source_role(source_role)
                example_origin = str(candidate.get("example_origin") or "").strip()
                needs_review_value = candidate.get("needs_review", "")
                needs_review = ""
                if isinstance(needs_review_value, bool):
                    needs_review = "true" if needs_review_value else "false"
                elif needs_review_value not in (None, ""):
                    needs_review = str(needs_review_value).strip().casefold()
                candidate_kind_meta = str(candidate.get("candidate_kind") or candidate.get("kind") or "").strip()
                source_section_meta = str(candidate.get("source_section") or candidate.get("section") or "").strip()
                advancedness_meta = str(candidate.get("advancedness") or "").strip()
                topic_relevance_meta = str(candidate.get("topic_relevance") or "").strip()
                reusability_meta = str(candidate.get("reusability") or "").strip()
                learning_value_meta = str(candidate.get("learning_value") or "").strip()
                document_specificity_meta = str(candidate.get("document_specificity") or "").strip()

                if self._looks_like_json_fragment(target):
                    target = ""
                if self._looks_like_json_fragment(sentence):
                    sentence = ""
                if self._looks_like_json_fragment(source_rule):
                    source_rule = ""
                if self._looks_like_json_fragment(source_role):
                    source_role = ""
                if self._looks_like_json_fragment(example_origin):
                    example_origin = ""
                if self._looks_like_json_fragment(candidate_kind_meta):
                    candidate_kind_meta = ""
                if self._looks_like_json_fragment(source_section_meta):
                    source_section_meta = ""
                if not target and not sentence and not source_rule:
                    continue

                # Smart Vocabulary now separates *candidate type* from the
                # semantic role of the visible source fragment. Containing the
                # target is not enough: headings/labels/definitions/fragments must
                # never be preserved as learner examples.
                smart_vocab_source_example = False
                if default_mode_key == "smart vocabulary":
                    non_example_roles = {
                        "heading_label",
                        "definition_context",
                        "list_item",
                        "fragment",
                        "exercise",
                        "unknown",
                    }
                    if candidate_type == "provided_example" and vocabulary_source_role in non_example_roles:
                        candidate_type = "vocabulary"
                    if candidate_type == "vocabulary" and target and sentence:
                        source_is_real_usage = (
                            self._looks_like_complete_sentence(sentence)
                            and self._import_source_sentence_uses_target(target, sentence)
                        )
                        if vocabulary_source_role == "usage_example" and source_is_real_usage:
                            candidate_type = "provided_example"
                            smart_vocab_source_example = True
                        elif not vocabulary_source_role:
                            # Backward compatibility for older provider payloads
                            # that predate source_role. New prompts always request
                            # source_role, so this path is not the primary classifier.
                            target_cf = clean_ocr_text(target).strip().casefold()
                            sentence_cf = clean_ocr_text(sentence).strip().casefold()
                            definition_starts = (
                                f"{target_cf} is ",
                                f"{target_cf} are ",
                                f"{target_cf} means ",
                                f"{target_cf} refers to ",
                                f"{target_cf} refers to a ",
                                f"{target_cf} refers to an ",
                            )
                            definition_like = any(sentence_cf.startswith(prefix) for prefix in definition_starts)
                            if source_is_real_usage and not definition_like:
                                candidate_type = "provided_example"
                                smart_vocab_source_example = True

                normalized_role = self._normalize_smart_grammar_source_type(source_role)
                if candidate_type == "grammar" and normalized_role:
                    if not candidate.get("source_type") and normalized_role in {"structure_sentence", "rule", "transformation", "exercise", "sentence_only"}:
                        candidate["source_type"] = normalized_role

                # A rule/exercise must never become the audio sentence. The new
                # Smart Grammar contract relies on model-declared source_role and
                # example_origin instead of language-specific rule markers.
                if candidate_type == "grammar" and normalized_role == "rule" and example_origin != "generated_from_rule":
                    source_rule = source_rule or sentence
                    sentence = ""
                elif candidate_type == "grammar" and sentence and self._ocr_looks_like_rule_explanation(sentence):
                    # Backward-compatible safety for older prompts/provider output.
                    source_rule = source_rule or sentence
                    sentence = ""

                item = self._make_ocr_candidate_item(candidate_type, target, sentence, source=f"AI {source}")
                if item is None:
                    continue
                source_type = self._normalize_smart_grammar_source_type(
                    str(candidate.get("source_type") or candidate.get("source_role") or candidate.get("detected_as") or "")
                )
                # If the provider claimed structure_sentence but the alleged
                # sentence was actually a textbook rule, downgrade to rule.
                # This prevents candidates like "have with this meaning is a
                # stative verb..." from becoming audio/example text.
                if candidate_type == "grammar" and source_rule and not sentence and source_type == "structure_sentence":
                    source_type = "rule"
                if not source_type:
                    source_type = self._infer_smart_grammar_source_type(candidate_type, target, sentence, source_rule)
                strategy = str(candidate.get("strategy") or "").strip() or self._smart_grammar_strategy_for_source_type(source_type)
                if smart_vocab_source_example:
                    source_type = "provided_example"
                    strategy = "preserve_source_sentence"
                elif default_mode_key == "smart vocabulary" and vocabulary_source_role:
                    source_type = vocabulary_source_role
                    strategy = {
                        "usage_example": "preserve_source_sentence",
                        "definition_context": "generate_example_from_definition",
                        "heading_label": "generate_example_from_target",
                        "list_item": "generate_example_from_target",
                        "fragment": "generate_example_from_target",
                        "exercise": "generate_example_from_target",
                        "unknown": "vocabulary_candidate",
                    }.get(vocabulary_source_role, "vocabulary_candidate")
                if candidate_type == "grammar" and source_type == "rule" and strategy == "preserve_source_sentence":
                    strategy = "generated_example_from_rule"
                if (
                    candidate_type == "grammar"
                    and source_type == "rule"
                    and strategy == "generated_example_from_rule"
                    and example_origin != "generated_from_rule"
                    and item.get("sentence")
                ):
                    # The model classified this as a rule but did not explicitly
                    # mark the sentence as a generated learner example. Keep the
                    # text as rule/context instead of showing it as audio.
                    source_rule = source_rule or str(item.get("sentence") or "")
                    item["sentence"] = ""
                reason = str(candidate.get("reason") or "").strip()
                confidence = str(candidate.get("confidence") or "").strip()
                answer = str(candidate.get("answer") or candidate.get("completed_answer") or "").strip()

                if source_type:
                    item["source_type"] = source_type
                if vocabulary_source_role:
                    item["source_role"] = vocabulary_source_role
                if strategy:
                    item["strategy"] = strategy
                if source_rule:
                    item["source_rule"] = clean_ocr_text(source_rule).replace("\n", " ").strip()
                if reason:
                    item["reason"] = clean_ocr_text(reason).replace("\n", " ").strip()
                if example_origin:
                    item["example_origin"] = example_origin
                if needs_review:
                    item["needs_review"] = needs_review
                if candidate_kind_meta:
                    item["candidate_kind"] = clean_ocr_text(candidate_kind_meta).replace("\n", " ").strip()
                if source_section_meta:
                    item["source_section"] = clean_ocr_text(source_section_meta).replace("\n", " ").strip()
                for meta_key, meta_value in (
                    ("advancedness", advancedness_meta),
                    ("topic_relevance", topic_relevance_meta),
                    ("reusability", reusability_meta),
                    ("learning_value", learning_value_meta),
                    ("document_specificity", document_specificity_meta),
                ):
                    if meta_value and not self._looks_like_json_fragment(meta_value):
                        item[meta_key] = clean_ocr_text(meta_value).replace("\n", " ").strip()
                if confidence:
                    item["confidence"] = confidence
                if answer:
                    item["answer"] = clean_ocr_text(answer).replace("\n", " ").strip()
                items.append(item)
        except Exception:
            # Fallback for a provider that ignored JSON and returned lines.
            for row in self._ocr_candidate_rows_from_ai_response(cleaned, default_mode):
                parsed = self._parse_ocr_candidate_row(row, default_mode)
                if parsed is None:
                    continue
                candidate_type, target, sentence = parsed
                item = self._make_ocr_candidate_item(candidate_type, target, sentence, source=f"AI {source}")
                if item is None:
                    continue
                source_type = self._infer_smart_grammar_source_type(candidate_type, target, sentence)
                if source_type:
                    item["source_type"] = source_type
                    item["strategy"] = self._smart_grammar_strategy_for_source_type(source_type)
                items.append(item)
        return items

    def _ocr_candidate_rows_from_ai_response(self, raw_text: str, default_mode: str) -> list[str]:
        """Convert an AI response into readable, editable candidate rows."""
        cleaned = self._ocr_clean_json_text(raw_text)
        rows: list[str] = []
        try:
            data = json.loads(cleaned)
            candidates = data.get("candidates", data) if isinstance(data, dict) else data
            if not isinstance(candidates, list):
                raise ValueError("candidates is not a list")
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                raw_type = str(candidate.get("type") or default_mode or "vocabulary")
                candidate_type = self._normalize_ocr_candidate_type(raw_type, default_mode)
                default_mode_key = (default_mode or "").strip().casefold()
                if default_mode_key in {"vocabulary", "vocabulary + source examples"}:
                    # Strict vocabulary modes never produce Provided Examples.
                    # Any source sentence stays attached as context metadata.
                    candidate_type = "vocabulary"
                elif default_mode_key == "smart vocabulary" and candidate_type == "grammar":
                    # Smart Vocabulary may mix vocabulary and provided_example,
                    # but grammar belongs only to Grammar/Smart Grammar/Mixed.
                    candidate_type = "vocabulary"
                elif self._is_grammar_import_mode(default_mode) and candidate_type == "provided_example":
                    candidate_type = "grammar"
                target = str(
                    candidate.get("target")
                    or candidate.get("word")
                    or candidate.get("phrase")
                    or candidate.get("structure")
                    or candidate.get("grammar")
                    or ""
                ).strip()
                sentence = str(
                    candidate.get("sentence")
                    or candidate.get("provided_example")
                    or candidate.get("example")
                    or candidate.get("source_sentence")
                    or candidate.get("context")
                    or ""
                ).strip()

                if self._looks_like_json_fragment(target):
                    target = ""
                if self._looks_like_json_fragment(sentence):
                    sentence = ""
                if not target and not sentence:
                    continue
                rows.append(self._format_ocr_candidate_row(candidate_type, target, sentence))
        except Exception:
            # Fallback for a provider that ignored JSON and returned lines.
            for line in cleaned.splitlines():
                value = line.strip().lstrip("-•0123456789. )\t")
                if not value:
                    continue
                parsed = self._parse_ocr_candidate_row(value, default_mode)
                if parsed is None:
                    continue
                candidate_type, target, sentence = parsed
                rows.append(self._format_ocr_candidate_row(candidate_type, target, sentence))
        return rows

    @staticmethod
    def _parse_ocr_candidate_row(line: str, default_mode: str) -> tuple[str, str, str] | None:
        """Parse an editable OCR candidate row into (type, target, sentence)."""
        value = line.strip()
        if not value or ModernVocabularyGui._looks_like_json_fragment(value):
            return None

        candidate_names = {
            "vocabulary",
            "grammar",
            "grammar target",
            "grammar from sentence",
            "provided_example",
            "provided example",
            "provided examples",
            "sentence",
        }

        # New readable display format: "provided example | target | sentence".
        if "|" in value:
            parts = [part.strip() for part in value.split("|")]
            if parts and parts[0].casefold().replace("_", " ") in candidate_names:
                candidate_type = ModernVocabularyGui._normalize_ocr_candidate_type(parts[0], default_mode)
                if candidate_type == "provided_example":
                    if len(parts) >= 3:
                        return candidate_type, parts[1], " | ".join(parts[2:]).strip()
                    if len(parts) == 2:
                        return candidate_type, "", parts[1]
                    return candidate_type, "", ""
                target = parts[1] if len(parts) > 1 else ""
                sentence = " | ".join(parts[2:]).strip() if len(parts) > 2 else ""
                return candidate_type, target, sentence

        # Backward-compatible TSV format from v9.1.
        parts = [part.strip() for part in value.split("\t")]
        if len(parts) >= 2 and parts[0].casefold().replace("_", " ") in candidate_names:
            candidate_type = ModernVocabularyGui._normalize_ocr_candidate_type(parts[0], default_mode)
            target = parts[1] if len(parts) > 1 else ""
            sentence = parts[2] if len(parts) > 2 else ""
            return candidate_type, target, sentence

        lower = value.casefold()
        for prefix in (
            "provided_example:",
            "provided example:",
            "provided examples:",
            "sentence:",
            "grammar:",
            "vocabulary:",
        ):
            if lower.startswith(prefix):
                candidate_type = ModernVocabularyGui._normalize_ocr_candidate_type(prefix.rstrip(":"), default_mode)
                rest = value[len(prefix):].strip()
                if candidate_type == "provided_example":
                    target, sentence = ModernVocabularyGui._parse_provided_example_item(rest)
                    return candidate_type, target, sentence
                return candidate_type, rest, ""

        # Robust fallback for raw lines like "provided_example ¿Qué teléfono...?"
        for prefix in (
            "provided_example ",
            "provided example ",
            "provided examples ",
            "sentence ",
            "grammar ",
            "vocabulary ",
        ):
            if lower.startswith(prefix):
                candidate_type = ModernVocabularyGui._normalize_ocr_candidate_type(prefix.strip(), default_mode)
                rest = value[len(prefix):].strip()
                if candidate_type == "provided_example":
                    target, sentence = ModernVocabularyGui._parse_provided_example_item(rest)
                    return candidate_type, target, sentence
                return candidate_type, rest, ""

        if default_mode == "Provided examples":
            target, sentence = ModernVocabularyGui._parse_provided_example_item(value)
            return "provided_example", target, sentence
        if ModernVocabularyGui._is_grammar_import_mode(default_mode):
            return "grammar", value, ""
        return "vocabulary", value, ""

    @classmethod
    def _import_source_sentence_uses_target(cls, target: str, sentence: str) -> bool:
        """Conservatively distinguish a real usage example from a definition.

        Smart Vocabulary sometimes receives glossary definitions in the same
        JSON field as source examples. A definition such as "The practice of
        favouring close friends..." for *cronyism* is useful context, but it is
        not a Provided Example because it never uses the target.
        """
        target = clean_ocr_text(str(target or "")).strip()
        sentence = clean_ocr_text(str(sentence or "")).strip()
        if not target or not sentence:
            return False
        if cls._text_contains_any_focus_fragment(sentence, target):
            return True
        # Light morphology fallback for single lexical anchors (amputar -> amputó,
        # prescribe -> prescribed). It is intentionally conservative.
        target_tokens = [
            token for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿĄ-ž]+", target.casefold())
            if len(token) >= 5 and token not in {"someone", "something", "alguien", "algo"}
        ]
        sentence_tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿĄ-ž]+", sentence.casefold())
        for token in target_tokens:
            prefix = token[: max(5, min(7, len(token) - 2))]
            if len(prefix) >= 5 and any(candidate.startswith(prefix) for candidate in sentence_tokens):
                return True
        return False

    @classmethod
    def _queue_item_identity(cls, item: dict[str, object]) -> str:
        """Return one Queue identity aligned with the final Anki card front."""
        mode = str(item.get("batch_mode") or "Vocabulary")
        identity_mode = "Vocabulary" if mode in {"Vocabulary", "Provided examples"} else mode
        if mode == "Grammar":
            identity_value = str(item.get("grammar_target") or item.get("word") or "").strip()
            if "|" in identity_value:
                identity_value = identity_value.split("|", 1)[0].strip()
        else:
            identity_value = cls._batch_duplicate_target_for_item(item) or str(item.get("word") or "").strip()
        return f"{identity_mode.casefold()}::{cls._normalise_anki_value(identity_value)}"

    def _send_ocr_candidates_to_batch(self) -> None:
        if not self._ocr_candidate_items:
            messagebox.showwarning("Import Material", "There are no candidates to send to Queue.")
            return
        topic = self._batch_topic_var.get().strip()
        target_language = self._language_var.get()
        explanation_language = self._explanation_language_var.get()
        items: list[dict[str, object]] = []
        for index, candidate in enumerate(self._ocr_candidate_items):
            is_selected = index >= len(self._ocr_candidate_vars) or self._ocr_candidate_vars[index].get()
            if not is_selected:
                continue
            candidate_type = self._normalize_ocr_candidate_type(candidate.get("type", "vocabulary"))
            target = candidate.get("target", "").strip()
            sentence = candidate.get("sentence", "").strip()
            item_extra: dict[str, object] = {}
            source_type = str(candidate.get("source_type") or "").strip()
            strategy = str(candidate.get("strategy") or "").strip()
            example_origin = str(candidate.get("example_origin") or "").strip()
            needs_review = str(candidate.get("needs_review") or "").strip()
            source_rule_meta = str(candidate.get("source_rule") or "").strip()
            reason_meta = str(candidate.get("reason") or "").strip()
            candidate_kind_meta = str(candidate.get("candidate_kind") or "").strip()
            source_section_meta = str(candidate.get("source_section") or "").strip()
            vocabulary_source_role = self._normalize_vocabulary_source_role(candidate.get("source_role", ""))
            if source_type:
                item_extra["source_type"] = source_type
            if strategy:
                item_extra["strategy"] = strategy
            if example_origin:
                item_extra["example_origin"] = example_origin
            if needs_review:
                item_extra["needs_review"] = needs_review
            if source_rule_meta:
                item_extra["source_rule"] = source_rule_meta
            if reason_meta:
                item_extra["source_reason"] = reason_meta
            if candidate_kind_meta:
                item_extra["candidate_kind"] = candidate_kind_meta
            if source_section_meta:
                item_extra["source_section"] = source_section_meta
            if vocabulary_source_role:
                item_extra["source_role"] = vocabulary_source_role
            if candidate_type == "provided_example":
                word = f"{target} | {sentence}" if target and sentence else (sentence or target)
                batch_mode = "Provided examples"
                if target:
                    item_extra["provided_target"] = target
                if sentence:
                    item_extra["provided_sentence"] = sentence
            elif candidate_type == "grammar":
                batch_mode = "Grammar"
                target_is_sentence = self._looks_like_complete_sentence(target)
                target_is_rule = self._ocr_looks_like_rule_explanation(target)
                sentence_is_rule = self._ocr_looks_like_rule_explanation(sentence)
                if target_is_rule and target and not source_rule_meta:
                    # A long explanatory rule is source context, not the card title.
                    # Let the grammar-generation model infer a concise learner target.
                    item_extra["source_rule"] = target
                if source_type == "exercise" and not self._looks_like_complete_sentence(sentence):
                    item_extra["source_focus_warning"] = "Exercise draft: verify or complete the answer before generation."

                rule_generated_example = (
                    source_type == "rule"
                    and strategy == "generated_example_from_rule"
                    and example_origin == "generated_from_rule"
                    and bool(sentence)
                )

                if rule_generated_example and target and not target_is_sentence:
                    # Smart Grammar rule candidate with a model-generated usage example.
                    word = f"{target} | {sentence}"
                    if not target_is_rule:
                        item_extra["grammar_target"] = target
                    item_extra["provided_sentence"] = sentence
                elif source_type == "rule" and strategy == "generated_example_from_rule" and target:
                    # Do not trust a rule candidate's sentence unless the Smart
                    # Grammar contract explicitly marks it as generated_from_rule.
                    # Queue will generate the natural example from target + source_rule.
                    word = target
                    if not target_is_rule:
                        item_extra["grammar_target"] = target
                    if sentence and not source_rule_meta:
                        item_extra["source_rule"] = sentence
                    item_extra.setdefault("source_focus_warning", "Rule-only candidate: Queue must generate the learner example/audio sentence.")
                elif target and sentence and not sentence_is_rule and not target_is_sentence:
                    # Best case: compact grammar target + one real sentence. If the
                    # "target" is actually a textbook rule, keep it as source context
                    # and let final generation normalize the title.
                    word = f"{target} | {sentence}"
                    if not target_is_rule:
                        item_extra["grammar_target"] = target
                    item_extra["provided_sentence"] = sentence
                elif target and sentence and target_is_sentence:
                    # The AI/local finder sometimes stores a sentence in target and
                    # a fuller example in sentence. For grammar, prefer the readable
                    # sentence as the audio target and let the model infer structure.
                    word = sentence
                    item_extra["provided_sentence"] = sentence
                elif target and sentence_is_rule:
                    # Do not send a long textbook rule as the audio sentence. Keep it
                    # only as source context and generate a natural example later.
                    word = target
                    if not target_is_rule:
                        item_extra["grammar_target"] = target
                    item_extra["source_rule"] = source_rule_meta or sentence or target
                else:
                    word = target or sentence
                    if target and not target_is_sentence and not target_is_rule:
                        item_extra["grammar_target"] = target
                    if sentence and self._looks_like_complete_sentence(sentence):
                        item_extra["provided_sentence"] = sentence
            else:
                # Vocabulary remains Vocabulary even when Smart Vocabulary found
                # a source example. Type is a property of the candidate, not of
                # the generation prompt used later.
                word = target or sentence
                batch_mode = "Vocabulary"
                if target:
                    item_extra["provided_target"] = target
                if sentence and target:
                    uses_target = self._import_source_sentence_uses_target(target, sentence)
                    preserve_source = (
                        vocabulary_source_role == "usage_example"
                        or (not vocabulary_source_role and uses_target)
                    )
                    if preserve_source and uses_target:
                        item_extra["source_sentence"] = sentence
                        item_extra["provided_sentence"] = sentence
                        item_extra["generation_strategy"] = "preserve_source_sentence"
                    else:
                        # Headings, labels, definitions, list items, fragments and
                        # exercises are source context only, never learner examples.
                        item_extra["source_definition"] = sentence
                        item_extra["generation_strategy"] = (
                            "generate_example_from_definition"
                            if vocabulary_source_role == "definition_context" or not vocabulary_source_role
                            else "generate_example_from_target"
                        )
                        item_extra.setdefault(
                            "source_reason",
                            reason_meta or "Imported source is context, not a natural usage example; Queue must generate the example.",
                        )
            word = word.strip()
            if not word:
                continue
            batch_item = {
                "word": word,
                "status": "pending",
                "topic": topic,
                "batch_mode": batch_mode,
                "mode_locked": True,
                "candidate_type": candidate_type,
                "target_language": target_language,
                "explanation_language": explanation_language,
                "source": f"ocr_import/{candidate.get('source', 'candidate')}",
                "candidate_source": candidate.get("source", ""),
                "edited": bool(candidate.get("edited")),
            }
            batch_item.update(item_extra)
            items.append(batch_item)
        if not items:
            messagebox.showwarning("Import Material", "No selected usable candidates were found.")
            return
        # Queue identity must match the final Anki card identity.  Source/example
        # sentences are context and must not fan one target out into many cards.
        clean_items: list[dict[str, object]] = []
        seen: set[str] = set()
        for item in items:
            key = self._queue_item_identity(item)
            if key not in seen:
                clean_items.append(item)
                seen.add(key)
        self._batch_items = clean_items
        self._batch_index = 0
        self._batch_autosave_path = None
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        self._batch_generated_grammar = None
        modes = sorted({str(item.get("batch_mode") or "Vocabulary") for item in clean_items})
        imported_queue_mode = self._queue_mode_from_imported_item_types(clean_items)
        if imported_queue_mode in BATCH_MODES:
            self._batch_mode_var.set(imported_queue_mode)
        self._show_current_batch_item(generate=False)
        mode_counts = {mode: sum(1 for item in clean_items if str(item.get("batch_mode") or "Vocabulary") == mode) for mode in modes}
        mode_summary = " · ".join(f"{mode_counts[mode]} {mode}" for mode in modes)
        mixed_note = " Each imported item keeps its own type." if len(modes) > 1 else " Imported item type is preserved."
        self._batch_source_summary_var.set(
            f"Received {len(clean_items)} reviewed candidate(s) from Import Material · {mode_summary}.{mixed_note}"
        )
        self._update_batch_mode_help()
        if len(modes) > 1:
            self._batch_mode_help_var.set(
                "Mixed import from Import Material: each Queue item keeps its own Vocabulary / Grammar / Provided example type. "
                "The Input type selector is only for clean TXT/CSV loaded directly into Queue."
            )
        else:
            self._batch_mode_help_var.set(
                f"Import Material classified these items as {modes[0]}. Their type is preserved in Queue; "
                "the Input type selector is for manually loaded clean files."
            )
        self._autosave_batch_session("ocr candidates sent to queue")
        self._ocr_candidate_status_var.set(f"Sent {len(clean_items)} selected candidate(s) to Queue.")
        self._cleanup_runtime_memory("ocr candidates sent to queue", aggressive=False)
        self._record_activity(f"OCR → Queue: {len(clean_items)}")
        try:
            self._tabs.set("Queue")
        except Exception:
            pass

    def _clear_ocr_import(self) -> None:
        removed_cache_files = self._clear_current_import_cache_files()
        self._ocr_source_paths = []
        self._set_ocr_text("")
        self._clear_ocr_candidates()
        self._ocr_status_var.set("Load a PDF, image, TXT/HTML, or paste text to start.")
        self._ocr_size_var.set("No material loaded yet.")
        self._ocr_route_var.set("TXT/HTML → read locally (no AI/model) → find candidates. Images/scans → OCR/vision → find candidates.")
        self._ocr_candidate_status_var.set("No candidates yet.")
        self._ocr_manual_target_var.set("")
        self._ocr_manual_example_var.set("")
        self._cleanup_runtime_memory("clear import material", aggressive=False)
        if removed_cache_files:
            self._ocr_status_var.set(f"Import cleared. Removed {removed_cache_files} cached screenshot/file(s).")

    def _show_current_batch_item(self, generate: bool = False) -> None:
        if not self._batch_items:
            self._batch_word_var.set("")
            self._batch_progress_var.set("No list loaded.")
            self._batch_status_var.set("Choose an input type first, then load clean TXT/CSV or paste prepared rows.")
            return
        self._batch_index = max(0, min(self._batch_index, len(self._batch_items) - 1))
        item = self._batch_items[self._batch_index]
        if item.get("topic") and not self._batch_topic_var.get().strip():
            self._batch_topic_var.set(str(item.get("topic", "")))
        item_mode = str(item.get("batch_mode") or "").strip()
        item_has_generated_payload = bool(item.get("card") or item.get("grammar_card"))
        item_status = str(item.get("status", "pending"))
        explicit_import_mode = str(item.get("source") or "").startswith("ocr_import/") or bool(
            item.get("source_type") or item.get("provided_target") or item.get("grammar_target")
        )
        if bool(item.get("mode_locked")):
            # Structured Import Material rows keep their own per-item type.  Do not
            # mirror the currently selected row back into the Queue-wide selector:
            # a mixed import must continue to show Mixed while the user browses
            # Vocabulary / Grammar / Provided Example rows.
            pass
        elif item_mode in BATCH_MODES and (item_has_generated_payload or item_status != "pending" or explicit_import_mode):
            self._batch_mode_var.set(item_mode)
        elif item_status == "pending":
            # Only manually loaded clean rows follow the Queue-wide input type.
            # Import Material rows already carry a per-item type.
            item["batch_mode"] = self._batch_mode_var.get().strip() or "Vocabulary"
            item.pop("resolved_mode", None)
        self._batch_word_var.set(str(item["word"]))
        self._batch_generated_card = None
        self._batch_generated_grammar = None
        self._batch_generated_provider_name = None
        stored_card = self._card_from_batch_payload(item.get("card"))
        stored_grammar = self._grammar_from_batch_payload(item.get("grammar_card"))
        if stored_card is not None:
            self._batch_generated_card = stored_card
            self._batch_generated_provider_name = str(item.get("provider_name") or self._provider_var.get())
        elif stored_grammar is not None:
            self._batch_generated_grammar = stored_grammar
            self._batch_generated_provider_name = str(item.get("provider_name") or self._provider_var.get())
        self._update_batch_progress()
        if stored_card is not None:
            self._set_batch_preview(self._format_batch_card_preview(item, stored_card))
        elif stored_grammar is not None:
            self._set_batch_preview(self._format_batch_grammar_preview(item, stored_grammar))
        else:
            mode = self._batch_mode_for_item(item)
            self._set_batch_status_card(
                title=f"QUEUE ITEM · {mode.upper()}",
                word=str(item.get("word", "")),
                status=str(item.get("status", "pending")),
                detail=self._friendly_batch_item_detail(item),
                mode=mode,
                item=item,
            )
        # Important: showing/selecting an item must never call an AI provider.
        # Generation is allowed only through explicit buttons such as
        # Generate selected, Auto-generate pending, or Retry failed/rate-limited.

    def _format_batch_card_preview(self, item: dict[str, object], card: VocabularyCard) -> str:
        # Revalidate before rendering. The preview and the Approve/Add logic must
        # use the same active warning list. Older versions showed
        # ``card.quality_warnings`` from the provider/payload at the top of the
        # preview, but Approve warning recomputed a different list from
        # ``item["quality_warnings"]``. That produced impossible UI states like
        # a visible HARD warning plus a "No hard warnings" popup.
        warnings = self._sync_quality_warnings_for_item(item, card)
        preview_card = card.model_copy(update={"quality_warnings": warnings})
        preview = self._format_card_preview(preview_card, audio_status=item.get("audio_status"))

        status = str(item.get("status", "")).strip()
        if status:
            preview += f"\n\nBATCH STATUS\n{status}"
        error = str(item.get("error", "")).strip()
        if error and (status.startswith("duplicate") or status == "blocked_quality_warning"):
            preview += f"\n{error}"
        provided_sentence = str(item.get("provided_sentence") or "").strip()
        if provided_sentence:
            preview += f"\n\nPROVIDED SENTENCE\n{provided_sentence}"
        topic = str(item.get("topic") or self._batch_topic_var.get()).strip()
        if topic:
            preview += f"\n\nTOPIC / CONTEXT\n{topic}"
        topic_status = str(item.get("topic_status", "")).strip()
        if topic_status:
            preview += f"\nTopic status: {topic_status}"
        # _format_card_preview() already renders the active QUALITY WARNINGS
        # from preview_card. Do not append the same warning list again here,
        # otherwise Queue cards show duplicated warnings in the preview.
        if item.get("quality_override"):
            preview += "\n\nQUALITY OVERRIDE\nApproved manually by user; hard warning will not block Add all ready."
        return preview

    def _format_batch_grammar_preview(self, item: dict[str, object], card: GrammarAnalysis) -> str:
        preview = self._format_grammar_preview(card)
        status = str(item.get("status", "")).strip()
        if status:
            preview += f"\n\nBATCH STATUS\n{status}"
        mode = str(item.get("resolved_mode") or item.get("batch_mode") or self._batch_mode_var.get()).strip()
        if mode:
            preview += f"\n\nBATCH MODE\n{mode}"
        topic = str(item.get("topic") or self._batch_topic_var.get()).strip()
        if topic:
            preview += f"\n\nTOPIC / CONTEXT\n{topic}"
        source_focus_warning = str(item.get("source_focus_warning", "")).strip()
        if source_focus_warning:
            preview += f"\n\nSOURCE FOCUS CHECK\n{source_focus_warning}"
        source_type = str(item.get("source_type", "")).strip()
        strategy = str(item.get("strategy", "")).strip()
        if source_type or strategy:
            route_lines = []
            if source_type:
                route_lines.append(f"Detected as: {source_type.replace('_', ' ')}")
            if strategy:
                route_lines.append(f"Strategy: {strategy.replace('_', ' ')}")
            preview += "\n\nSMART IMPORT ROUTING\n" + "\n".join(route_lines)
        source_rule = str(item.get("source_rule", "")).strip()
        if source_rule:
            preview += f"\n\nSOURCE RULE / NOTE\n{source_rule}"
        source_reason = str(item.get("source_reason", "")).strip()
        if source_reason:
            preview += f"\n\nWHY\n{source_reason}"
        grammar_target = str(item.get("grammar_target", "")).strip()
        if grammar_target:
            preview += f"\n\nSOURCE GRAMMAR TARGET\n{grammar_target}"
        provided_sentence = str(item.get("provided_sentence", "")).strip()
        if provided_sentence:
            preview += f"\n\nSOURCE SENTENCE / AUDIO\n{provided_sentence}"
        source_definition = str(item.get("source_definition", "")).strip()
        if source_definition:
            preview += f"\n\nSOURCE DEFINITION / CONTEXT\n{source_definition}"
        error = str(item.get("error", "")).strip()
        if error:
            preview += f"\n\nDETAILS\n{error}"
        return preview


    def _save_current_batch_item_edit(self) -> None:
        """Persist edits made in the Current item entry before generation.

        Older UX let the user edit the entry visually, but the saved Queue row
        could still keep stale generated payloads or old status. This makes the
        current entry the source of truth for the selected Queue item.
        """
        if not self._batch_items:
            messagebox.showwarning("Queue edit", "Load Queue items first.")
            return
        new_word = clean_ocr_text(self._batch_word_var.get()).replace("\n", " ").strip()
        if not new_word:
            messagebox.showwarning("Queue edit", "Current item cannot be empty.")
            return
        item = self._batch_items[self._batch_index]
        old_word = str(item.get("word", "")).strip()
        topic_context = self._current_batch_topic()
        item["word"] = new_word
        item["topic"] = topic_context
        item["target_language"] = self._language_var.get().strip()
        item["explanation_language"] = self._explanation_language_var.get().strip()
        if not bool(item.get("mode_locked")):
            item["batch_mode"] = self._batch_auto_mode or "Vocabulary"
        item["edited"] = True

        if new_word != old_word:
            # The generated card belongs to the old input. Clear it so a later
            # Add/Preview cannot accidentally use stale content.
            item["status"] = "pending"
            for key in (
                "card",
                "grammar_card",
                "provider_name",
                "quality_warnings",
                "error",
                "duplicate_prechecked",
                "duplicate_target",
                "duplicate_lookup_value",
                "resolved_mode",
                "provided_target",
                "provided_sentence",
            ):
                item.pop(key, None)
            self._batch_generated_card = None
            self._batch_generated_grammar = None
            self._batch_generated_provider_name = None

        self._show_current_batch_item(generate=False)
        self._autosave_batch_session(f"queue item edited: {new_word}")
        message = "Queue item saved. Generation will use the edited value."
        self._batch_status_var.set(message)
        self._status_var.set(message)
        self._record_activity(f"Queue item edited: {new_word}")

    def _open_batch_card_editor(self) -> None:
        """Open a small editor for the currently generated Queue card."""
        if not self._batch_items:
            return
        grammar_card = self._batch_generated_grammar or self._grammar_from_batch_payload(
            self._batch_items[self._batch_index].get("grammar_card")
        )
        if grammar_card is not None:
            self._open_batch_grammar_editor(grammar_card)
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
        row = add_text(row, "Translation / explanation", "translation", card.translation, height=3)
        row = add_text(row, "Example", "example", card.example, height=3)
        row = add_text(row, "Example translation", "example_translation", card.example_translation, height=3)
        row = add_text(row, "Collocations\n(one per line)", "collocations", "\n".join(card.collocations), height=5)
        row = add_text(row, "Synonyms\n(one per line)", "synonyms", "\n".join(card.synonyms), height=4)
        row = add_text(row, "Grammar note", "grammar_note", card.grammar_note, height=4)

        def value(key: str) -> str:
            widget = entries[key]
            if isinstance(widget, tk.Text):
                return widget.get("1.0", "end").strip()
            return str(widget.get()).strip()  # type: ignore[attr-defined]

        def save(close_editor: bool = True) -> bool:
            updated_card = card.model_copy(
                update={
                    "target_language": value("target_language") or card.target_language,
                    "part_of_speech": value("part_of_speech"),
                    "word_or_phrase": value("word_or_phrase") or card.word_or_phrase,
                    "definition": value("definition"),
                    "translation": value("translation"),
                    "example": value("example"),
                    "example_translation": value("example_translation"),
                    "collocations": [line.strip() for line in value("collocations").splitlines() if line.strip()],
                    "synonyms": [line.strip() for line in value("synonyms").splitlines() if line.strip()],
                    "grammar_note": value("grammar_note"),
                }
            )
            item = self._batch_items[self._batch_index]
            item["card"] = self._card_to_batch_payload(updated_card)
            item.pop("grammar_card", None)
            item["word"] = updated_card.word_or_phrase
            item["status"] = "ready"
            item["edited_card"] = True
            self._batch_generated_card = updated_card
            self._batch_generated_grammar = None
            self._batch_generated_provider_name = str(item.get("provider_name") or self._provider_var.get())
            self._batch_word_var.set(updated_card.word_or_phrase)
            warnings = self._quality_warnings_for_card(
                updated_card,
                expected_input=self._quality_expected_input_for_item(item, updated_card),
                topic_context=str(item.get("topic") or self._current_batch_topic()),
            )
            if warnings:
                item["quality_warnings"] = warnings
            else:
                item.pop("quality_warnings", None)
            self._set_batch_preview(self._format_batch_card_preview(item, updated_card))
            self._autosave_batch_session(f"edited: {updated_card.word_or_phrase}")
            self._batch_status_var.set(
                f"Edited and autosaved. You can add this card now: {updated_card.word_or_phrase}"
            )
            self._status_var.set(self._batch_status_var.get())
            self._record_activity(f"Edited: {updated_card.word_or_phrase}")
            if close_editor:
                editor.destroy()
            return True

        def save_and_add() -> None:
            if save(close_editor=False):
                editor.destroy()
                self._add_current_batch_card()

        button_row = tk.Frame(editor)
        button_row.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=12)
        tk.Button(button_row, text="Save changes", command=save).pack(side="left")
        tk.Button(button_row, text="Save + add to Anki", command=save_and_add).pack(side="left", padx=(8, 0))
        tk.Button(button_row, text="Cancel", command=editor.destroy).pack(side="left", padx=(8, 0))

    def _open_batch_grammar_editor(self, card: GrammarAnalysis) -> None:
        """Open a small editor for the currently generated Queue grammar card."""
        editor = tk.Toplevel(self._root)
        editor.title(f"Edit grammar card: {card.sentence}")
        editor.geometry("780x780")
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
        row = add_entry(row, "Explanation language", "explanation_language", card.explanation_language)
        row = add_entry(row, "Grammar target / title", "target", card.target)
        row = add_text(row, "Example sentence", "sentence", card.sentence, height=3)
        row = add_text(row, "Meaning / function", "meaning", card.meaning, height=3)
        row = add_text(row, "Structure / pattern", "structure", card.structure, height=3)
        row = add_text(row, "Breakdown\n(one per line)", "breakdown", "\n".join(card.breakdown), height=5)
        row = add_text(row, "Usage", "usage", card.usage, height=4)
        row = add_text(row, "Contrasts\n(one per line)", "contrasts", "\n".join(card.contrasts), height=4)
        row = add_text(row, "Common mistakes\n(one per line)", "common_mistakes", "\n".join(card.common_mistakes), height=4)

        def value(key: str) -> str:
            widget = entries[key]
            if isinstance(widget, tk.Text):
                return widget.get("1.0", "end").strip()
            return str(widget.get()).strip()  # type: ignore[attr-defined]

        def save(close_editor: bool = True) -> bool:
            updated_card = card.model_copy(
                update={
                    "target_language": value("target_language") or card.target_language,
                    "explanation_language": value("explanation_language") or card.explanation_language,
                    "target": value("target") or card.target,
                    "sentence": value("sentence") or card.sentence,
                    "meaning": value("meaning"),
                    "structure": value("structure"),
                    "breakdown": [line.strip() for line in value("breakdown").splitlines() if line.strip()],
                    "usage": value("usage"),
                    "context_example": value("sentence") or card.sentence,
                    "contrasts": [line.strip() for line in value("contrasts").splitlines() if line.strip()],
                    "common_mistakes": [line.strip() for line in value("common_mistakes").splitlines() if line.strip()],
                }
            )
            item = self._batch_items[self._batch_index]
            item["grammar_card"] = self._grammar_to_batch_payload(updated_card)
            item.pop("card", None)
            item["word"] = updated_card.sentence
            item["status"] = "ready"
            item["resolved_mode"] = "Grammar"
            item["batch_mode"] = "Grammar"
            item["edited_card"] = True
            self._batch_generated_grammar = updated_card
            self._batch_generated_card = None
            self._batch_generated_provider_name = str(item.get("provider_name") or self._provider_var.get())
            self._batch_word_var.set(updated_card.sentence)
            self._set_batch_preview(self._format_batch_grammar_preview(item, updated_card))
            self._autosave_batch_session(f"edited grammar: {updated_card.sentence}")
            self._batch_status_var.set(
                f"Edited grammar card and autosaved. You can add it now: {updated_card.sentence}"
            )
            self._status_var.set(self._batch_status_var.get())
            self._record_activity(f"Edited grammar: {updated_card.sentence}")
            if close_editor:
                editor.destroy()
            return True

        def save_and_add() -> None:
            if save(close_editor=False):
                editor.destroy()
                self._add_current_batch_card()

        button_row = tk.Frame(editor)
        button_row.grid(row=row, column=0, columnspan=2, sticky="ew", padx=10, pady=12)
        tk.Button(button_row, text="Save changes", command=save).pack(side="left")
        tk.Button(button_row, text="Save + add to Anki", command=save_and_add).pack(side="left", padx=(8, 0))
        tk.Button(button_row, text="Cancel", command=editor.destroy).pack(side="left", padx=(8, 0))

    def _update_batch_progress(self) -> None:
        """Show queue progress as human-readable stages instead of a developer counter dump."""
        total = len(self._batch_items)
        counts = {
            name: 0
            for name in (
                "added",
                "added_to_anki",
                "updated_in_anki",
                "skipped",
                "invalid",
                "pending",
                "ready",
                "error",
                "rate_limited",
                "provider_failed",
                "add_failed",
                "duplicate",
                "duplicate_found",
                "duplicate_uncertain",
                "duplicate_skipped",
                "blocked_quality_warning",
            )
        }
        for item in self._batch_items:
            status = str(item.get("status", "pending"))
            counts[status] = counts.get(status, 0) + 1

        if not total:
            self._batch_progress_var.set("No items in queue.")
            bar = getattr(self, "_batch_progress_bar", None)
            if bar is not None:
                bar.set(0)
            self._refresh_batch_issue_visibility()
            return

        waiting = counts.get("pending", 0)
        prepared = max(0, total - waiting)
        added_total = counts.get("added", 0) + counts.get("added_to_anki", 0)
        updated_total = counts.get("updated_in_anki", 0)
        duplicate_total = (
            counts.get("duplicate", 0)
            + counts.get("duplicate_found", 0)
            + counts.get("duplicate_uncertain", 0)
            + counts.get("duplicate_skipped", 0)
        )
        failed_total = (
            counts.get("error", 0)
            + counts.get("provider_failed", 0)
            + counts.get("add_failed", 0)
            + counts.get("blocked_quality_warning", 0)
        )

        summary = [f"Prepared {prepared} of {total}", f"{waiting} waiting"]
        results: list[str] = []
        if counts.get("ready", 0):
            results.append(f"Ready {counts['ready']}")
        if added_total:
            results.append(f"Added {added_total}")
        if updated_total:
            results.append(f"Updated {updated_total}")
        if duplicate_total:
            results.append(f"Duplicates {duplicate_total}")
        if counts.get("skipped", 0):
            results.append(f"Skipped {counts['skipped']}")
        if counts.get("invalid", 0):
            results.append(f"Invalid {counts['invalid']}")
        if failed_total:
            results.append(f"Failed {failed_total}")
        if counts.get("rate_limited", 0):
            results.append(f"Rate limited {counts['rate_limited']}")

        line = " · ".join(summary)
        if results:
            line += "\n" + " · ".join(results)
        self._batch_progress_var.set(line)

        bar = getattr(self, "_batch_progress_bar", None)
        if bar is not None:
            try:
                bar.set(prepared / total)
            except Exception:
                pass
        self._refresh_batch_issue_visibility()

    def _refresh_batch_issue_visibility(self) -> None:
        """Show problem navigation only when the current Queue actually has problems."""
        frame = getattr(self, "_batch_issue_buttons_frame", None)
        label = getattr(self, "_batch_issue_label", None)
        if frame is None or label is None:
            return
        if self._batch_issue_indexes():
            label.grid()
            frame.grid()
        else:
            label.grid_remove()
            frame.grid_remove()

    @staticmethod
    def _clean_batch_visible_message(message: str, max_chars: int = 360) -> str:
        """Keep Queue labels short and stop raw JSON/provider dumps from breaking the layout."""
        if not message:
            return ""
        clean = str(message).strip()
        for marker in ("Raw response:", "raw_response", "```json", "{\n", "{\r\n", "Autosave:"):
            index = clean.find(marker)
            if index != -1:
                clean = clean[:index].strip()
                break
        clean = re.sub(r"\s+", " ", clean).strip()
        if len(clean) > max_chars:
            clean = clean[:max_chars].rstrip() + "..."
        return clean

    @classmethod
    def _friendly_batch_detail(cls, detail: str, max_chars: int = 220) -> str:
        """Short user-facing error detail; raw payload stays in autosave/logs."""
        clean = cls._clean_batch_visible_message(detail, max_chars=max_chars)
        if not clean:
            return "Raw provider/Anki details saved in autosave/logs."
        return clean

    def _set_batch_preview(self, content: str) -> None:
        self._batch_preview.configure(state="normal")
        self._batch_preview.delete("1.0", "end")
        self._batch_preview.insert("1.0", content)
        self._batch_preview.see("1.0")
        self._batch_preview.configure(state="disabled")
        self._scroll_batch_preview_to_top()

    def _set_batch_status_card(
        self,
        title: str,
        word: str,
        status: str,
        detail: str = "",
        actions: str = "",
        mode: str = "",
        item: dict[str, object] | None = None,
    ) -> None:
        """Show a stable card-like Queue preview for non-ready states.

        Grammar items must not be rendered with the vocabulary label
        "WORD / PHRASE". Import Material often sends grammar rows as
        "target | sentence"; the preview should expose those two parts so the
        user can see what will become the audio sentence.
        """
        effective_mode = (mode or str((item or {}).get("resolved_mode") or (item or {}).get("batch_mode") or "")).strip()
        blocks = [
            "╭────────────────────────────────────────╮",
            f"  {title}",
            "╰────────────────────────────────────────╯",
            "",
        ]

        if effective_mode == "Grammar":
            raw_target, raw_sentence = self._split_batch_grammar_item(word)
            grammar_target = str((item or {}).get("grammar_target") or raw_target).strip()
            sentence_to_read = str((item or {}).get("provided_sentence") or raw_sentence).strip()
            source_rule = str((item or {}).get("source_rule") or "").strip()
            blocks.extend([
                "GRAMMAR TARGET",
                grammar_target or "—",
                "",
                "SENTENCE TO READ",
                sentence_to_read or "AI will generate a natural example sentence.",
            ])
            source_focus_warning = str((item or {}).get("source_focus_warning") or "").strip()
            source_type = str((item or {}).get("source_type") or "").strip()
            strategy = str((item or {}).get("strategy") or "").strip()
            source_reason = str((item or {}).get("source_reason") or "").strip()
            if source_type or strategy:
                meta = []
                if source_type:
                    meta.append(f"Detected as: {source_type.replace('_', ' ')}")
                if strategy:
                    meta.append(f"Strategy: {strategy.replace('_', ' ')}")
                blocks.extend(["", "SMART IMPORT ROUTING", "\n".join(meta)])
            if source_rule:
                blocks.extend(["", "SOURCE RULE / NOTE", source_rule])
            if source_reason:
                blocks.extend(["", "WHY", source_reason])
            if source_focus_warning:
                blocks.extend(["", "SOURCE FOCUS WARNING", source_focus_warning])
        elif effective_mode == "Provided examples":
            target, sentence = self._parse_provided_example_item(word)
            blocks.extend([
                "TARGET ITEM",
                target or "—",
                "",
                "PROVIDED SENTENCE",
                sentence or word or "—",
            ])
        else:
            blocks.extend([
                "WORD / PHRASE",
                f"{word or '—'}",
            ])

        blocks.extend(["", "STATUS", status])
        if detail:
            blocks.extend(["", "DETAILS", self._friendly_batch_detail(detail)])
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
    def _is_provider_billing_detail(detail: str) -> bool:
        """Return True for provider billing/credit errors hidden behind 400s.

        Some APIs, especially Anthropic, report exhausted credits as HTTP 400
        invalid_request_error instead of a 402. That is fatal for an Auto Queue
        run: retrying the next items will just burn time and spam logs.
        """
        lowered = detail.lower()
        return any(
            token in lowered
            for token in (
                "credit balance is too low",
                "credits are too low",
                "insufficient credits",
                "insufficient credit",
                "billing",
                "purchase credits",
                "plans & billing",
                "payment required",
                "insufficient_quota",
            )
        )

    @staticmethod
    def _is_timeout_detail(detail: str) -> bool:
        lowered = detail.lower()
        return "timeout" in lowered or "timed out" in lowered or "read timed out" in lowered

    @staticmethod
    def _is_fatal_long_generation_detail(detail: str) -> bool:
        status = ModernVocabularyGui._http_status_from_detail(detail)
        return (
            ModernVocabularyGui._is_provider_billing_detail(detail)
            or status in {401, 402, 403, 429}
            or (status is not None and 500 <= status <= 599)
            or ModernVocabularyGui._is_timeout_detail(detail)
        )

    @staticmethod
    def _friendly_generation_error_detail(
        detail: str,
        provider_name: str = "Provider",
        model_name: str = "",
    ) -> str:
        """Convert provider raw errors into concise UI text.

        The raw exception remains in logs/autosave; this summary is for the
        Queue preview/status area so users are not shown huge JSON payloads.
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
        if ModernVocabularyGui._is_provider_billing_detail(detail):
            return (
                f"{provider} credits/billing problem for {model}. "
                "Auto Queue was stopped and progress was saved. "
                "Add credits in the provider dashboard or switch Card AI provider, then retry failed/rate-limited items."
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
            mode = str(item.get("batch_mode") or "Vocabulary")
            if bool(item.get("mode_locked")):
                return f"Imported as {mode}. This item keeps its own type. Click Generate selected or Auto-generate pending."
            return "Not generated yet. Click Generate selected or Auto-generate pending."
        if status == "ready":
            return "Generated and ready for review."
        if status == "rate_limited":
            return "Provider rate limit. Switch provider and retry this item, or resume later."
        if status == "provider_failed":
            return "Provider stopped the process. Switch provider and retry failed/rate-limited items."
        if status == "duplicate_found":
            return "Duplicate found in Anki. Review it before adding or choose an explicit duplicate strategy."
        if status == "duplicate_uncertain":
            return "Legacy/uncertain duplicate found. It was not auto-updated; use Fix Cards to inspect it."
        if status == "duplicate_skipped":
            return "Duplicate was skipped. Existing Anki card was not changed."
        if status == "added_to_anki":
            return "Added to Anki."
        if status == "updated_in_anki":
            return "Existing Anki note was updated."
        return ""

    def _stop_batch_on_provider_error(
        self,
        word: str,
        detail: str,
        provider_name: str,
        model_name: str = "",
    ) -> None:
        """Stop Auto Queue and keep one stable UI state after fatal provider errors."""
        self._batch_auto_generate_running = False
        self._batch_auto_generate_paused = False
        self._batch_auto_generate_stop_requested = True
        self._autosave_batch_session(f"provider error: {word}")
        autosave = str(self._batch_autosave_path) if self._batch_autosave_path else "not available"
        friendly_detail = self._friendly_generation_error_detail(detail, provider_name, model_name)
        message = (
            "Auto Queue stopped: provider error. "
            "Progress saved. Switch provider and retry failed/rate-limited items, or resume later."
        )
        self._batch_status_var.set(f"{message} Autosaved.")
        self._status_var.set(message)
        status_name = "rate_limited" if self._is_provider_rate_limit_detail(detail) else "provider_failed"
        self._set_batch_status_card(
            title="QUEUE PROCESS STOPPED",
            word=word,
            status=status_name,
            detail=f"{friendly_detail}\n\nAutosaved.",
            actions=(
                "- Switch provider\n"
                "- Retry failed/rate-limited\n"
                "- Add all ready cards now\n"
                "- Resume later from autosave"
            ),
        )
        self._record_activity("Auto Queue stopped: provider error")
        LOGGER.warning("Auto Queue stopped because of provider error for word=%s detail=%s", word, detail)

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
        target_language = self._language_var.get().strip()
        explanation_language = self._explanation_language_var.get().strip()
        item["word"] = word
        item["topic"] = topic_context
        item["target_language"] = target_language
        item["explanation_language"] = explanation_language
        if not bool(item.get("mode_locked")):
            item["batch_mode"] = self._batch_mode_var.get().strip() or "Vocabulary"
        resolved_mode = self._batch_mode_for_item(item, word)
        item["resolved_mode"] = resolved_mode
        provider_name = self._provider_var.get()
        model_name = self._current_ai_model_name()

        # Last line of defence: Generate selected and resumed/old sessions must
        # check duplicates before any provider API call. This is especially
        # important for pasted table rows like "word<TAB>translation" or
        # "word    translation", where the generated card later normalizes to an
        # existing Anki note.
        if (
            str(item.get("status", "pending")) == "pending"
            and not item.get("card")
            and not item.get("grammar_card")
            and not item.get("duplicate_prechecked")
        ):
            self._batch_status_var.set(f"Checking duplicates before AI for {self._batch_index + 1}/{len(self._batch_items)}: {word}")
            self._status_var.set(self._batch_status_var.get())
            self._root.update_idletasks()
            try:
                duplicate_found = self._precheck_one_batch_duplicate(self._batch_index, reason="before generation")
            except Exception as exc:
                LOGGER.exception("Duplicate precheck before selected generation failed")
                message = (
                    "Generation cancelled before provider API call: duplicate precheck failed. "
                    + self._friendly_anki_error_message(exc)
                )
                self._batch_status_var.set(message)
                self._status_var.set(message)
                self._autosave_batch_session("generation cancelled: duplicate precheck failed")
                return
            if duplicate_found:
                self._batch_generated_card = None
                self._batch_generated_grammar = None
                self._update_batch_progress()
                self._show_current_batch_item(generate=False)
                self._batch_status_var.set(
                    f"Skipped before AI: '{word}' already exists in Anki. No provider API was used."
                )
                self._status_var.set(self._batch_status_var.get())
                self._autosave_batch_session(f"duplicate skipped before generation: {word}")
                return

        LOGGER.info(
            "Queue generation start: trigger=%s index=%s word=%s provider=%s",
            generation_trigger,
            self._batch_index,
            word,
            provider_name,
        )
        self._batch_status_var.set(
            f"Generating {resolved_mode.lower()} card {self._batch_index + 1}/{len(self._batch_items)}: {word}..."
        )
        self._status_var.set(self._batch_status_var.get())
        self._root.update_idletasks()
        preserve_vocab_source = (
            resolved_mode == "Vocabulary"
            and str(item.get("generation_strategy") or "") == "preserve_source_sentence"
            and bool(str(item.get("source_sentence") or "").strip())
        )
        if resolved_mode == "Provided examples" or preserve_vocab_source:
            if preserve_vocab_source:
                provided_target = str(item.get("provided_target") or word).strip()
                provided_sentence = str(item.get("source_sentence") or "").strip()
                sentence_request_word = f"{provided_target} | {provided_sentence}"
            else:
                provided_target, provided_sentence = self._parse_provided_example_item(word)
                sentence_request_word = word
            if not provided_sentence:
                item["status"] = "invalid"
                item["error"] = "Provided examples mode needs a sentence. Use: target | sentence, or paste a sentence."
                self._batch_status_var.set("Invalid provided example: missing sentence.")
                self._set_batch_status_card("INVALID PROVIDED EXAMPLE", word, "invalid", str(item["error"]))
                self._update_batch_progress()
                self._autosave_batch_session(f"invalid provided example: {word}")
                return
            item["provided_target"] = provided_target
            item["provided_sentence"] = provided_sentence
            try:
                card = self._current_ai_client().generate_sentence_card(
                    sentence_request_word,
                    target_language,
                    explanation_language,
                    topic_context,
                )
            except Exception as exc:
                detail = str(exc)
                item["status"] = "error"
                item["error"] = detail
                self._batch_generated_card = None
                if self._is_provider_rate_limit_detail(detail):
                    item["status"] = "rate_limited"
                    self._batch_status_var.set(f"Rate limit while generating provided-example card: {word}. Session autosaved.")
                    self._update_batch_progress()
                    self._stop_batch_on_provider_error(word, detail, provider_name, model_name)
                elif self._is_fatal_long_generation_detail(detail):
                    item["status"] = "provider_failed"
                    self._batch_status_var.set(f"Provider stopped while generating provided-example card: {word}. Session autosaved.")
                    self._update_batch_progress()
                    self._stop_batch_on_provider_error(word, detail, provider_name, model_name)
                else:
                    self._batch_status_var.set(f"Provided-example generation error: {word}. Raw details saved in logs/autosave.")
                    self._set_batch_status_card(
                        "PROVIDED EXAMPLE GENERATION ERROR",
                        word,
                        "error",
                        self._friendly_generation_error_detail(detail, provider_name, model_name),
                    )
                    self._update_batch_progress()
                    self._autosave_batch_session(f"provided-example generation error: {word}")
                if self._is_provider_rate_limit_detail(detail) or self._is_fatal_long_generation_detail(detail):
                    LOGGER.warning("Queue provided-example provider error for item=%s detail=%s", word, detail)
                else:
                    LOGGER.exception("Queue provided-example generation failed for item=%s", word)
                return
            if not card.is_valid:
                item["status"] = "invalid"
                detail = card.validation_error or "Invalid provided example."
                if card.suggested_correction:
                    detail += f" Suggested correction: {card.suggested_correction}"
                item["error"] = detail
                self._batch_generated_card = None
                self._batch_status_var.set(f"Invalid provided example: {word}")
                self._set_batch_status_card("VALIDATION ERROR", word, "invalid", detail)
                self._update_batch_progress()
                self._autosave_batch_session(f"invalid provided example: {word}")
                return
            item["status"] = "ready"
            item["card"] = self._card_to_batch_payload(card)
            item.pop("grammar_card", None)
            item["provider_name"] = provider_name
            item.pop("error", None)
            quality_warnings = self._quality_warnings_for_card(
                card,
                expected_input=provided_target or card.word_or_phrase,
                topic_context=topic_context,
            )
            item["topic_status"] = card.topic_fit or ("topic_ok" if topic_context and not quality_warnings else "")
            if quality_warnings:
                item["quality_warnings"] = quality_warnings
            else:
                item.pop("quality_warnings", None)
            self._batch_generated_card = card
            self._batch_generated_grammar = None
            self._batch_generated_provider_name = provider_name
            self._set_batch_preview(self._format_batch_card_preview(item, card))
            if preserve_vocab_source:
                item["resolved_mode"] = "Vocabulary"
                self._batch_status_var.set(f"Vocabulary card ready with preserved source example: {card.word_or_phrase}")
                autosave_label = "generated vocabulary with source example"
            else:
                self._batch_status_var.set(f"Provided-example card ready to review: {card.word_or_phrase}")
                autosave_label = "generated provided example"
            self._status_var.set(self._batch_status_var.get())
            self._update_batch_progress()
            self._autosave_batch_session(f"{autosave_label}: {card.word_or_phrase}")
            return

        if resolved_mode == "Grammar":
            grammar_topic_context = self._grammar_topic_context_for_item(item, topic_context)
            try:
                grammar_card = self._current_ai_client().generate_grammar_card(
                    word,
                    target_language,
                    grammar_topic_context,
                    explanation_language=explanation_language,
                )
            except Exception as exc:
                detail = str(exc)
                item["status"] = "error"
                item["error"] = detail
                self._batch_generated_card = None
                self._batch_generated_grammar = None
                if self._is_provider_rate_limit_detail(detail):
                    item["status"] = "rate_limited"
                    self._batch_status_var.set(f"Rate limit while generating grammar: {word}. Session autosaved.")
                    self._update_batch_progress()
                    self._stop_batch_on_provider_error(word, detail, provider_name, model_name)
                elif self._is_fatal_long_generation_detail(detail):
                    item["status"] = "provider_failed"
                    self._batch_status_var.set(f"Provider stopped while generating grammar: {word}. Session autosaved.")
                    self._update_batch_progress()
                    self._stop_batch_on_provider_error(word, detail, provider_name, model_name)
                else:
                    self._batch_status_var.set(f"Grammar generation error: {word}. Raw details saved in logs/autosave.")
                    self._set_batch_status_card(
                        "GRAMMAR GENERATION ERROR",
                        word,
                        "error",
                        self._friendly_generation_error_detail(detail, provider_name, model_name),
                    )
                    self._update_batch_progress()
                    self._autosave_batch_session(f"grammar generation error: {word}")
                if self._is_provider_rate_limit_detail(detail) or self._is_fatal_long_generation_detail(detail):
                    LOGGER.warning("Queue grammar provider error for item=%s detail=%s", word, detail)
                else:
                    LOGGER.exception("Queue grammar generation failed for item=%s", word)
                return
            grammar_card, focus_warnings = self._grammar_card_with_source_focus_guard(item, grammar_card)
            if focus_warnings:
                item["source_focus_warning"] = ", ".join(focus_warnings)
            else:
                item.pop("source_focus_warning", None)
            item["status"] = "ready"
            item["grammar_card"] = self._grammar_to_batch_payload(grammar_card)
            item.pop("card", None)
            item["provider_name"] = provider_name
            item.pop("error", None)
            self._batch_generated_card = None
            self._batch_generated_grammar = grammar_card
            self._batch_generated_provider_name = provider_name
            self._set_batch_preview(self._format_batch_grammar_preview(item, grammar_card))
            self._batch_status_var.set(f"Grammar card ready to review: {word}")
            self._status_var.set(self._batch_status_var.get())
            self._update_batch_progress()
            self._autosave_batch_session(f"generated grammar: {word}")
            return

        try:
            card = self._current_ai_client().generate_card(
                word,
                target_language,
                explanation_language,
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
            if self._is_provider_rate_limit_detail(detail) or self._is_fatal_long_generation_detail(detail):
                LOGGER.warning("Queue provider error for word=%s detail=%s", word, detail)
            else:
                LOGGER.exception("Queue generation failed for word=%s", word)
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
        quality_warnings = self._quality_warnings_for_card(
            card,
            expected_input=word,
            topic_context=topic_context,
        )
        item["topic_status"] = card.topic_fit or ("topic_ok" if topic_context and not quality_warnings else "")
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
        if self._batch_generated_grammar is not None:
            provider_name = self._batch_generated_provider_name or self._provider_var.get()
            was_update = False
            try:
                deck = self._set_selected_deck()
                self._anki_client.add_grammar_card(self._batch_generated_grammar, provider_name, extra_tags=self._batch_tags_for_item(self._batch_items[self._batch_index]))
            except DuplicateNoteError:
                grammar_target = (self._batch_generated_grammar.target or self._batch_generated_grammar.structure).strip()
                replace = messagebox.askyesno(
                    "Grammar card already exists",
                    f"A grammar card for '{grammar_target}' already exists in the Anki collection.\n\n"
                    "Replace it with this reviewed version?",
                )
                if not replace:
                    self._batch_status_var.set("Existing grammar card was not changed.")
                    return
                try:
                    self._anki_client.update_grammar_card(self._batch_generated_grammar, provider_name, extra_tags=self._batch_tags_for_item(self._batch_items[self._batch_index]))
                except Exception as update_exc:
                    self._batch_status_var.set(f"Could not update grammar card: {update_exc}")
                    messagebox.showerror("Anki update error", str(update_exc))
                    return
                deck = self._anki_client.deck_name
                was_update = True
            except Exception as exc:
                self._batch_status_var.set(f"Could not add grammar card: {exc}")
                messagebox.showerror("Anki error", str(exc))
                return
            sentence = self._batch_generated_grammar.sentence
            self._batch_items[self._batch_index]["status"] = "added_to_anki"
            self._batch_items[self._batch_index].pop("quality_warnings", None)
            self._batch_items[self._batch_index].pop("error", None)
            self._autosave_batch_session(f"added grammar: {sentence}")
            self._batch_status_var.set(f"✓ Added grammar card to {deck}: {sentence}")
            self._status_var.set(self._batch_status_var.get())
            self._record_activity(f"✓ Grammar added: {sentence}")
            self._record_llmops_outcome(
                outcome="updated_existing_note" if was_update else "added_to_anki",
                item=sentence,
                card_type="grammar",
                source="batch_queue",
                validation_passed=True,
            )
            self._update_batch_progress()
            self._root.after(350, self._advance_batch_after_action)
            return

        if self._batch_generated_card is None:
            messagebox.showerror("No card", "Generate and review the current card first.")
            return
        current_item = self._batch_items[self._batch_index]
        if not self._confirm_quality_warnings(
            self._batch_generated_card,
            expected_input=self._quality_expected_input_for_item(current_item, self._batch_generated_card),
            topic_context=str(current_item.get("topic") or self._current_batch_topic()),
            batch_item=current_item,
        ):
            self._batch_status_var.set("Add to Anki cancelled because of quality warnings.")
            return
        provider_name = self._batch_generated_provider_name or self._provider_var.get()
        was_update = False
        try:
            deck = self._set_selected_deck()
            self._anki_client.add_card(
                self._batch_generated_card,
                provider_name,
                extra_tags=self._batch_tags_for_item(self._batch_items[self._batch_index]),
            )
        except DuplicateNoteError as exc:
            if not exc.update_safe:
                model = exc.model_name or "another/legacy note type"
                self._batch_status_var.set("Duplicate found; existing card was left unchanged.")
                messagebox.showwarning(
                    "Card already exists",
                    f"A card for '{self._batch_generated_card.word_or_phrase}' already exists "
                    f"somewhere in the Anki collection ({model}).\n\n"
                    "It was not overwritten automatically because the existing note is not "
                    "a single current AI Vocabulary Light Card.",
                )
                return
            replace = messagebox.askyesno(
                "Card already exists",
                f"A card for '{self._batch_generated_card.word_or_phrase}' already exists "
                "in the Anki collection.\n\nReplace it with this reviewed version?",
            )
            if not replace:
                self._batch_status_var.set("Existing card was not changed.")
                return
            try:
                self._anki_client.update_card(
                    self._batch_generated_card,
                    provider_name,
                    extra_tags=self._batch_tags_for_item(self._batch_items[self._batch_index]),
                )
            except Exception as update_exc:
                self._batch_status_var.set(f"Could not update card: {update_exc}")
                messagebox.showerror("Anki update error", str(update_exc))
                return
            deck = self._anki_client.deck_name
            was_update = True
        except Exception as exc:
            self._batch_status_var.set(f"Could not add card: {exc}")
            messagebox.showerror("Anki error", str(exc))
            return
        word = self._batch_generated_card.word_or_phrase
        self._batch_items[self._batch_index]["status"] = "added"
        self._batch_items[self._batch_index].pop("quality_warnings", None)
        self._batch_items[self._batch_index].pop("error", None)
        self._autosave_batch_session(f"added: {word}")
        self._batch_status_var.set(f"✓ Added to {deck}: {word}")
        self._status_var.set(self._batch_status_var.get())
        self._record_activity(f"✓ {word} added")
        self._record_llmops_outcome(
            outcome="updated_existing_note" if was_update else "added_to_anki",
            item=word,
            card_type="vocabulary",
            source="batch_queue",
            validation_passed=True,
        )
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
        self._record_llmops_outcome(
            outcome="skipped",
            item=word,
            card_type=str(self._batch_items[self._batch_index].get("mode") or "batch_item"),
            source="batch_queue",
            detail="User skipped Queue item after review.",
        )
        self._update_batch_progress()
        self._root.after(250, self._advance_batch_after_action)

    def _advance_batch_after_action(self) -> None:
        if self._batch_index < len(self._batch_items) - 1:
            self._batch_index += 1
            self._show_current_batch_item(generate=False)
        else:
            self._batch_status_var.set("Queue finished. Review progress or save the session.")
            self._status_var.set(self._batch_status_var.get())

    def _batch_previous(self) -> None:
        if self._batch_items and self._batch_index > 0:
            self._batch_index -= 1
            self._show_current_batch_item(generate=False)

    def _batch_issue_indexes(self) -> list[int]:
        """Return indexes that need user attention in the current Queue queue."""
        issue_statuses = {
            "blocked_quality_warning",
            "invalid",
            "error",
            "provider_failed",
            "add_failed",
            "rate_limited",
            "duplicate_uncertain",
        }
        indexes: list[int] = []
        for index, item in enumerate(self._batch_items):
            status = str(item.get("status", "pending"))
            if status in {"added", "added_to_anki", "updated_in_anki", "skipped", "duplicate_skipped", "duplicate", "duplicate_found"}:
                continue
            warnings = item.get("quality_warnings")
            has_hard_warning = (
                not item.get("quality_override")
                and isinstance(warnings, list)
                and any(str(warning).startswith("HARD:") for warning in warnings)
            )
            if status in issue_statuses or has_hard_warning:
                indexes.append(index)
        return indexes

    def _go_to_batch_index(self, index: int, *, reason: str = "") -> None:
        """Safely navigate to a Queue item and show it in the preview."""
        if not self._batch_items:
            self._batch_status_var.set("No queue loaded.")
            return
        self._batch_index = max(0, min(index, len(self._batch_items) - 1))
        self._show_current_batch_item(generate=False)
        if reason:
            self._batch_status_var.set(reason)
            self._status_var.set(reason)

    def _go_to_first_blocked_batch_item(self) -> None:
        """Jump to the first blocked/invalid Queue item."""
        indexes = self._batch_issue_indexes()
        if not indexes:
            message = "No blocked, failed, invalid, rate-limited, or uncertain duplicate cards in this Queue."
            self._batch_status_var.set(message)
            self._status_var.set(message)
            return
        index = indexes[0]
        self._go_to_batch_index(index, reason=f"Showing issue {index + 1}/{len(self._batch_items)}. Use Edit card or Regenerate, then Add all ready again.")

    def _go_to_next_batch_issue(self) -> None:
        """Jump to the next blocked/failed/invalid Queue item after the current one."""
        indexes = self._batch_issue_indexes()
        if not indexes:
            message = "No blocked, failed, invalid, rate-limited, or uncertain duplicate cards in this Queue."
            self._batch_status_var.set(message)
            self._status_var.set(message)
            return
        later = [index for index in indexes if index > self._batch_index]
        index = later[0] if later else indexes[0]
        self._go_to_batch_index(index, reason=f"Showing issue {index + 1}/{len(self._batch_items)}. Use Edit card or Regenerate, then Add all ready again.")

    def _show_batch_issue_summary(self) -> None:
        """Show a concise issue summary for the current Queue.

        The progress line counts both real problems and safe duplicates that
        were skipped before provider calls. The old popup only listed blocking
        problems, so it could say "No issues" while the header still showed
        duplicates. Keep those concepts separate but visible.
        """
        problem_details = self._batch_issue_details({
            "blocked_quality_warning",
            "invalid",
            "error",
            "provider_failed",
            "add_failed",
            "rate_limited",
            "duplicate_uncertain",
        })
        duplicate_details = self._batch_issue_details({
            "duplicate",
            "duplicate_found",
            "duplicate_skipped",
        }, limit=25)

        if not problem_details and not duplicate_details:
            message = "No blocked, failed, invalid, rate-limited, or duplicate cards in this Queue."
            self._batch_status_var.set(message)
            self._status_var.set(message)
            messagebox.showinfo("Queue summary", message)
            return

        sections: list[str] = []
        if problem_details:
            body = "\n".join(problem_details[:25])
            if len(problem_details) > 25:
                body += f"\n... and {len(problem_details) - 25} more."
            sections.append(
                "Needs attention. Use 'Go to first problem' or 'Next problem' to open these cards:\n" + body
            )
        else:
            sections.append("No blocked, failed, invalid, rate-limited, or uncertain duplicate cards.")

        if duplicate_details:
            body = "\n".join(duplicate_details[:25])
            if len(duplicate_details) > 25:
                body += f"\n... and {len(duplicate_details) - 25} more."
            sections.append(
                "Safe duplicates / skipped before provider API calls:\n" + body
            )

        message = "\n\n".join(sections)
        self._batch_status_var.set("Queue summary shown.")
        self._status_var.set(self._batch_status_var.get())
        messagebox.showinfo("Queue summary", message)

    def _remove_current_batch_item(self) -> None:
        """Remove only the current Queue row without rebuilding expensive views."""
        if self._batch_generation_in_flight:
            messagebox.showinfo(
                "Queue busy",
                "One AI request is still running. Wait for it to finish, then remove the item.",
            )
            return
        if not self._batch_items:
            return
        index = max(0, min(self._batch_index, len(self._batch_items) - 1))
        removed = self._batch_items.pop(index)
        removed_word = str(removed.get("word", "")).strip() or "item"

        if self._batch_index >= len(self._batch_items):
            self._batch_index = max(0, len(self._batch_items) - 1)

        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        self._batch_generated_grammar = None

        if self._batch_items:
            self._show_current_batch_item(generate=False)
            message = f"Removed from Queue: {removed_word}."
        else:
            self._show_current_batch_item(generate=False)
            self._set_batch_preview("Queue is empty. Load or send candidates to start again.")
            message = f"Removed from Queue: {removed_word}. Queue is now empty."

        self._batch_status_var.set(message)
        self._status_var.set(message)
        self._record_activity(f"Queue item removed: {removed_word}")
        self._schedule_batch_autosave("queue item removed")

    def _batch_next(self) -> None:
        if self._batch_items and self._batch_index < len(self._batch_items) - 1:
            self._batch_index += 1
            self._show_current_batch_item(generate=False)

    def _clear_batch(self) -> None:
        if self._batch_generation_in_flight:
            messagebox.showinfo(
                "Queue busy",
                "One AI request is still running. Use Stop, wait for the current request to finish, then clear the Queue.",
            )
            return
        self._batch_items.clear()
        self._batch_index = 0
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        self._batch_generated_grammar = None
        self._batch_autosave_path = None
        self._batch_auto_generate_running = False
        self._batch_auto_generate_paused = False
        self._batch_auto_generate_stop_requested = False
        self._batch_generation_in_flight = False
        self._batch_processing_index = None
        self._batch_add_all_running = False
        self._batch_add_all_paused = False
        self._batch_add_all_stop_requested = False
        self._show_current_batch_item()
        self._set_batch_preview("Choose a mode, load clean structured input, and review parsed rows before generating.")
        self._batch_add_all_indexes = []
        self._batch_add_all_existing_notes = {}
        self._batch_add_all_failed_details = []
        try:
            self._batch_paste_text.delete("1.0", "end")
        except Exception:
            pass
        self._batch_source_summary_var.set("No source loaded yet.")
        self._update_batch_mode_help()
        self._cleanup_runtime_memory("clear queue", aggressive=False)
        self._record_activity("Queue cleared")


    def _batch_session_data(self) -> dict[str, object]:
        """Return the current Queue session payload."""
        return {
            "items": self._batch_items,
            "index": self._batch_index,
            "provider": self._provider_var.get(),
            "target_language": self._language_var.get(),
            "explanation_language": self._explanation_language_var.get(),
            "feedback_language": self._feedback_language_var.get(),
            "batch_topic": self._batch_topic_var.get(),
            "batch_mode": self._batch_mode_var.get(),
            "deck": self._deck_var.get(),
            "autosaved_at": datetime.now().isoformat(timespec="seconds"),
        }

    def _ensure_batch_autosave_path(self) -> Path:
        """Create and return the autosave path for the current Queue session."""
        if self._batch_autosave_path is None:
            autosave_dir = Path("batch_autosaves")
            autosave_dir.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._batch_autosave_path = autosave_dir / f"batch_autosave_{stamp}.json"
        return self._batch_autosave_path

    def _schedule_batch_autosave(self, reason: str, delay_ms: int = 800) -> None:
        """Debounce autosave for fast repeated UI actions such as deletions."""
        after_id = getattr(self, "_batch_autosave_after_id", None)
        if after_id:
            try:
                self._root.after_cancel(after_id)
            except Exception:
                pass
        if not self._batch_items:
            self._batch_autosave_after_id = None
            return

        def run() -> None:
            self._batch_autosave_after_id = None
            self._autosave_batch_session(reason)

        try:
            self._batch_autosave_after_id = self._root.after(delay_ms, run)
        except Exception:
            self._batch_autosave_after_id = None
            self._autosave_batch_session(reason)

    def _reset_batch_perf(self) -> None:
        """Reset Queue timing counters. Timing data is written only to the app log."""
        self._batch_perf_active = True
        self._batch_perf_started_at = time.perf_counter()
        self._batch_perf_precheck_s = 0.0
        self._batch_perf_ai_s = 0.0
        self._batch_perf_apply_s = 0.0
        self._batch_perf_autosave_s = 0.0
        self._batch_perf_items = 0

    def _record_batch_item_perf(
        self,
        payload: dict[str, object],
        *,
        status: str,
        apply_started_at: float,
    ) -> None:
        """Record one Queue item's timings without exposing them in the card/UI."""
        ai_s = float(payload.get("perf_ai_s") or 0.0)
        item_started_at = float(payload.get("perf_item_started_at") or apply_started_at)
        apply_s = max(0.0, time.perf_counter() - apply_started_at)
        total_s = max(0.0, time.perf_counter() - item_started_at)

        if getattr(self, "_batch_perf_active", False):
            self._batch_perf_ai_s += ai_s
            self._batch_perf_apply_s += apply_s
            self._batch_perf_items += 1

        LOGGER.info(
            "PERF queue_item index=%s mode=%s provider=%s model=%s status=%s "
            "ai_s=%.3f apply_s=%.3f total_s=%.3f word=%r",
            payload.get("index"),
            payload.get("resolved_mode"),
            payload.get("provider_name"),
            payload.get("model_name"),
            status,
            ai_s,
            apply_s,
            total_s,
            payload.get("word"),
        )

    def _log_batch_perf_summary(self, outcome: str) -> None:
        """Write one Queue-run performance summary to the log and reset counters."""
        if not getattr(self, "_batch_perf_active", False):
            return
        started_at = self._batch_perf_started_at
        total_s = max(0.0, time.perf_counter() - started_at) if started_at is not None else 0.0
        avg_s = total_s / self._batch_perf_items if self._batch_perf_items else 0.0
        LOGGER.info(
            "PERF queue_summary outcome=%s items=%s total_s=%.3f avg_s=%.3f "
            "precheck_s=%.3f ai_s=%.3f apply_s=%.3f autosave_s=%.3f",
            outcome,
            self._batch_perf_items,
            total_s,
            avg_s,
            self._batch_perf_precheck_s,
            self._batch_perf_ai_s,
            self._batch_perf_apply_s,
            self._batch_perf_autosave_s,
        )
        self._batch_perf_active = False
        self._batch_perf_started_at = None

    def _autosave_batch_session(self, reason: str) -> None:
        """Save the current Queue session automatically."""
        if not self._batch_items:
            return
        started_at = time.perf_counter()
        path = self._ensure_batch_autosave_path()
        try:
            path.write_text(
                json.dumps(self._batch_session_data(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            LOGGER.info("Queue autosaved: reason=%s path=%s", reason, path)
        except Exception as exc:
            LOGGER.exception("Queue autosave failed: reason=%s", reason)
            self._record_activity(f"Autosave failed: {exc}")
            return
        finally:
            elapsed = max(0.0, time.perf_counter() - started_at)
            if getattr(self, "_batch_perf_active", False):
                self._batch_perf_autosave_s += elapsed
            LOGGER.info(
                "PERF queue_autosave reason=%r seconds=%.3f items=%s",
                reason,
                elapsed,
                len(self._batch_items),
            )

    def _card_from_batch_payload(self, payload: object) -> VocabularyCard | None:
        """Rebuild a vocabulary card stored inside a Queue item."""
        if not isinstance(payload, dict):
            return None
        try:
            return VocabularyCard(**payload)
        except Exception:
            return None

    @staticmethod
    def _card_to_batch_payload(card: VocabularyCard) -> dict[str, object]:
        """Serialize a generated card into the Queue session."""
        return {
            "word_or_phrase": card.word_or_phrase,
            "target_language": card.target_language,
            "part_of_speech": card.part_of_speech,
            "translation": card.translation,
            "translation_pl": card.translation,  # legacy autosave compatibility
            "definition": card.definition,
            "example": card.example,
            "example_translation": card.example_translation,
            "example_pl": card.example_translation,  # legacy autosave compatibility
            "synonyms": list(card.synonyms),
            "collocations": list(card.collocations),
            "grammar_note": card.grammar_note,
            "is_valid": card.is_valid,
            "validation_error": card.validation_error,
            "suggested_correction": card.suggested_correction,
            "explanation_language": card.explanation_language,
            "audio": card.audio,
            "topic_fit": card.topic_fit,
            "topic_warning": card.topic_warning,
            "quality_warnings": list(card.quality_warnings),
            "used_form_in_example": card.used_form_in_example,
            "example_uses_target": card.example_uses_target,
            "collocation_naturalness": card.collocation_naturalness,
            "translation_naturalness": card.translation_naturalness,
        }

    def _grammar_from_batch_payload(self, payload: object) -> GrammarAnalysis | None:
        """Rebuild a grammar card stored inside a Queue item."""
        if not isinstance(payload, dict):
            return None
        try:
            return GrammarAnalysis(**payload)
        except Exception:
            return None

    @staticmethod
    def _grammar_to_batch_payload(card: GrammarAnalysis) -> dict[str, object]:
        """Serialize a generated grammar card into the Queue session."""
        return card.model_dump()

    @staticmethod
    def _parse_provided_example_item(value: str) -> tuple[str, str]:
        """Return (target_item, provided_sentence) for Provided examples mode."""
        text = value.strip()
        for separator in ("|", "\t"):
            if separator in text:
                left, right = text.split(separator, 1)
                return left.strip(), right.strip()
        return "", text

    @staticmethod
    def _looks_like_complete_sentence(value: str) -> bool:
        """Conservative check for real learner sentences, not grammar patterns."""
        text = clean_ocr_text(str(value or "")).strip()
        if not text or len(text.split()) < 2:
            return False
        if text.rstrip("\'\" )]").endswith((".", "!", "?")):
            return True
        # OCR often drops final punctuation. This catches obvious sentence starts
        # without treating compact grammar labels such as "should + infinitive"
        # as sentences.
        return bool(re.match(r"^(I|You|He|She|It|We|They|There|This|That|These|Those|The|A|An)\b", text)) and not any(
            marker in text for marker in (" + ", " / ", "+")
        )

    @classmethod
    def _split_batch_grammar_item(cls, value: str) -> tuple[str, str]:
        """Return (grammar_target, sentence_to_read) from a Queue grammar row.

        Queue grammar rows may be either:
        - "target | sentence" from Import Material, or
        - a plain sentence, or
        - a plain grammar pattern.
        """
        text = clean_ocr_text(str(value or "")).replace("\n", " ").strip()
        if not text:
            return "", ""
        target, sentence = cls._parse_provided_example_item(text)
        if target and sentence:
            return target, sentence
        if cls._looks_like_complete_sentence(text):
            return "", text
        return text, ""

    @staticmethod
    def _normalize_focus_for_contains(value: str) -> str:
        text = clean_ocr_text(str(value or "")).casefold()
        text = text.replace("→", " -> ").replace("—", "-").replace("–", "-")
        text = re.sub(r"[\"'“”‘’`]+", "", text)
        text = re.sub(r"[^a-z0-9áéíóúüñ+>/-]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _focus_fragments_for_guard(cls, target: str) -> list[str]:
        """Small, visible source-focus fragments used to protect OCR grammar cards.

        This is intentionally conservative: it should catch obvious targets
        like "used to", "Can I", "should have", "hippi -> hippies" without
        trying to validate every grammar topic semantically.
        """
        text = clean_ocr_text(str(target or "")).strip()
        if not text:
            return []
        normalized = cls._normalize_focus_for_contains(text)
        if not normalized:
            return []

        fragments: list[str] = []
        # Word-form transformations: keep both sides and the whole target.
        if "->" in normalized or "→" in text:
            pieces = [part.strip(" -") for part in re.split(r"\s*(?:->|→)\s*", normalized) if part.strip(" -")]
            fragments.extend(piece for piece in pieces if len(piece) >= 3)
            fragments.append(normalized)

        # Grammar alternatives / patterns.
        stem = re.split(r"\s+\+\s+|\s+to talk about\s+|\s+used to show\s+", normalized, maxsplit=1)[0].strip()
        pieces = [piece.strip(" -/") for piece in re.split(r"\s*/\s*", stem or normalized) if piece.strip(" -/")]
        for piece in pieces:
            piece = re.sub(r"\b(base verb|past participle|infinitive|object|complement|clause|adjective|noun|substantive)\b", "", piece).strip()
            piece = re.sub(r"\s+", " ", piece).strip(" -+")
            if len(piece) >= 3:
                fragments.append(piece)

        if len(normalized) <= 80:
            fragments.append(normalized)

        result: list[str] = []
        seen: set[str] = set()
        for fragment in fragments:
            key = fragment.casefold()
            if key and key not in seen:
                result.append(fragment)
                seen.add(key)
        return result

    @classmethod
    def _text_contains_any_focus_fragment(cls, text: str, target: str) -> bool:
        haystack = cls._normalize_focus_for_contains(text)
        if not haystack:
            return False
        for fragment in cls._focus_fragments_for_guard(target):
            frag = cls._normalize_focus_for_contains(fragment)
            if frag and frag in haystack:
                return True
        return False

    @classmethod
    def _grammar_sentence_needs_focus_warning(cls, target: str, sentence: str) -> bool:
        """Return True when an AI-generated grammar sentence looks like a topic label.

        If Import Material provided a concrete grammar target but no source
        sentence, the provider must create an actual example sentence. A short
        abstract title such as "repeated actions in the past" is not a good
        audio/readable sentence for the card.
        """
        target = clean_ocr_text(str(target or "")).strip()
        sentence = clean_ocr_text(str(sentence or "")).strip()
        if not target or not sentence:
            return False
        if cls._looks_like_complete_sentence(sentence):
            return False
        # Connectors and single discourse words can legitimately be the top item.
        if len(target.split()) <= 2 and cls._text_contains_any_focus_fragment(sentence, target):
            return False
        if not cls._text_contains_any_focus_fragment(sentence, target):
            return True
        return False

    @classmethod
    def _grammar_card_with_source_focus_guard(
        cls,
        item: dict[str, object],
        card: GrammarAnalysis,
    ) -> tuple[GrammarAnalysis, list[str]]:
        """Keep OCR/import grammar fields aligned after provider generation.

        The provider may return a fluent but badly mapped card: source sentence
        replaced by a rule, or exact target hidden inside a broad topic. This
        guard is intentionally small and deterministic:
        - exact source sentence from Import Material always wins for sentence/audio;
        - explicit source grammar target always remains visible in Structure;
        - suspicious abstract generated sentence gets a warning for review.
        """
        raw_target, raw_sentence = cls._split_batch_grammar_item(str(item.get("word") or ""))
        grammar_target = clean_ocr_text(str(item.get("grammar_target") or raw_target or "")).replace("\n", " ").strip()
        provided_sentence = clean_ocr_text(str(item.get("provided_sentence") or raw_sentence or "")).replace("\n", " ").strip()
        source_rule = clean_ocr_text(str(item.get("source_rule") or "")).replace("\n", " ").strip()
        update: dict[str, object] = {}
        warnings: list[str] = []

        if provided_sentence and clean_ocr_text(card.sentence).strip() != provided_sentence:
            update["sentence"] = provided_sentence
            warnings.append("audio_sentence_restored_from_source")

        compact_source_target = bool(
            grammar_target
            and not cls._ocr_looks_like_rule_explanation(grammar_target)
            and not cls._looks_like_complete_sentence(grammar_target)
            and len(grammar_target) <= 120
        )
        if compact_source_target and not cls._text_contains_any_focus_fragment(card.target, grammar_target):
            # Target is now the learner-facing identity of a grammar card.
            # Preserve a real compact source target, but never force a long
            # textbook rule back into the card title.
            update["target"] = grammar_target
            warnings.append("source_target_restored_in_target")

        if compact_source_target and not str(card.structure or "").strip():
            update["structure"] = grammar_target
            warnings.append("source_target_used_as_missing_structure")

        if not bool(card.target_is_valid):
            warnings.append("provider_target_self_check_failed")
        if not bool(card.example_demonstrates_target):
            warnings.append("provider_example_self_check_failed")
        if str(card.validation_note or "").strip() and (
            not bool(card.target_is_valid) or not bool(card.example_demonstrates_target)
        ):
            warnings.append(f"provider_validation_note: {card.validation_note.strip()}")

        effective_sentence = str(update.get("sentence") or card.sentence)
        context_example = clean_ocr_text(str(card.context_example or "")).replace("\n", " ").strip()

        # v12.4.4 grammar cards have one canonical example sentence.  Keep the
        # compatibility ContextExample field aligned to it so TTS/source scans
        # cannot pick a second competing sentence.
        if context_example != effective_sentence:
            update["context_example"] = effective_sentence
            warnings.append("context_example_aligned_to_main_example")

        if grammar_target and not provided_sentence and cls._grammar_sentence_needs_focus_warning(grammar_target, effective_sentence):
            warnings.append("unclear_card_focus_generated_sentence_does_not_show_target")

        if source_rule and source_rule not in card.usage and len(source_rule) <= 280:
            # Preserve source rule as context, but never as audio sentence.
            usage = (card.usage or "").strip()
            update["usage"] = f"{usage}\n\nSource note: {source_rule}".strip()
            warnings.append("source_rule_kept_as_note_not_audio")

        if not update:
            return card, warnings
        return card.model_copy(update=update), warnings

    def _grammar_topic_context_for_item(self, item: dict[str, object], base_topic_context: str) -> str:
        """Append source-focus hints to the prompt context for OCR grammar rows."""
        pieces = [base_topic_context.strip()] if base_topic_context.strip() else []
        grammar_target = str(item.get("grammar_target") or "").strip()
        provided_sentence = str(item.get("provided_sentence") or "").strip()
        source_rule = str(item.get("source_rule") or "").strip()
        source_type = str(item.get("source_type") or "").strip()
        strategy = str(item.get("strategy") or "").strip()
        example_origin = str(item.get("example_origin") or "").strip()
        needs_review = str(item.get("needs_review") or "").strip()
        source_reason = str(item.get("source_reason") or "").strip()
        if grammar_target:
            pieces.append(f"Source grammar target/focus: {grammar_target}")
        if provided_sentence:
            pieces.append(f"Source sentence to preserve as audio sentence: {provided_sentence}")
        if source_rule:
            pieces.append(f"Source rule/note, not audio: {source_rule}")
        if source_type:
            pieces.append(f"Smart import detected source type: {source_type}")
        if strategy:
            pieces.append(f"Smart import card strategy: {strategy}")
        if example_origin:
            pieces.append(f"Smart import example origin: {example_origin}")
        if needs_review:
            pieces.append(f"Smart import needs review: {needs_review}")
        if source_reason:
            pieces.append(f"Smart import reason: {source_reason}")
        return "\n".join(pieces)


    def _quality_expected_input_for_item(self, item: dict[str, object], card: VocabularyCard) -> str:
        """Return the expected lexical item for quality validation.

        In Provided examples mode, the raw Queue row may be
        ``target | sentence``. The quality validator must check only the
        target item, otherwise valid cards get a false HARD warning like
        ``expected 'microorganisms | ...', got 'microorganisms'``.
        """
        mode = str(item.get("resolved_mode") or item.get("batch_mode") or "").strip()
        raw_word = str(item.get("word") or "").strip()
        provided_target = str(item.get("provided_target") or "").strip()
        if provided_target:
            return provided_target
        if mode == "Provided examples":
            parsed_target, _provided_sentence = self._parse_provided_example_item(raw_word)
            if parsed_target:
                item["provided_target"] = parsed_target
                return parsed_target
            return card.word_or_phrase
        return raw_word or card.word_or_phrase

    def _sync_quality_warnings_for_item(self, item: dict[str, object], card: VocabularyCard) -> list[str]:
        """Recompute and store the active quality warnings for a Queue card.

        This is the single source of truth used by preview, Approve warning,
        Add this card, and Add all ready. It also rewrites the stored card
        payload, because old autosaves/provider responses may contain stale
        ``card.quality_warnings`` that would otherwise still render at the top
        of the preview even after current validation disagrees.
        """
        warnings = self._quality_warnings_for_card(
            card,
            expected_input=self._quality_expected_input_for_item(item, card),
            topic_context=str(item.get("topic") or self._current_batch_topic()),
        )
        warnings = list(warnings)
        hard = [warning for warning in warnings if warning.startswith("HARD:")]

        # Keep the card object and its serialized payload in sync with the
        # active warnings so UI rendering cannot display a different warning set
        # than the one used by approval/add logic. Pydantic models are mutable in
        # this project, but the payload update is the important persistent part.
        try:
            card.quality_warnings = warnings
        except Exception:
            pass
        payload = item.get("card")
        if isinstance(payload, dict):
            payload["quality_warnings"] = warnings

        if warnings:
            item["quality_warnings"] = warnings
        else:
            item.pop("quality_warnings", None)
        if not hard and item.get("status") == "blocked_quality_warning":
            item["status"] = "ready"
            stale_error = str(item.get("error") or "")
            if "hard quality warning" in stale_error.casefold() or "input phrase changed" in stale_error.casefold():
                item.pop("error", None)
        if not hard and item.get("quality_override"):
            # An override is not needed anymore if the current validator no longer
            # sees a hard warning. Keep old audit details only in autosave if they
            # already exist, but do not display an active override badge.
            item.pop("quality_override", None)
            item.pop("quality_override_reason", None)
        return warnings

    def _batch_tags_for_item(self, item: dict[str, object] | None = None) -> list[str]:
        """Return topic + card-type tags for one Queue item."""
        tags = self._topic_tags_for_batch_item(item)
        mode = str((item or {}).get("resolved_mode") or (item or {}).get("batch_mode") or "").strip()
        if mode == "Grammar":
            tags.append("card_type::grammar")
        elif mode == "Provided examples":
            tags.append("card_type::provided_example")
        elif mode == "Vocabulary":
            tags.append("card_type::vocabulary")
        return tags

    @staticmethod
    def _looks_like_grammar_item(value: str) -> bool:
        """Conservative heuristic for Mixed Queue mode.

        It detects common grammar/writing structures without pretending to be a
        full classifier. Ambiguous items stay vocabulary to avoid surprising the
        user.
        """
        text = value.strip().casefold()
        if not text:
            return False
        grammar_markers = (
            " + ", "+", "subjuntivo", "indicativo", "infinitivo", "gerundio",
            "condicional", "pretérito", "imperfecto", "ser/estar", "por/para",
            "aunque", "a pesar de", "por mucho que", "de ahí que", "siempre que",
            "en cuanto a", "no solo", "sino también", "cuanto más", "tan pronto como",
            "there is", "there are", "used to", "would rather", "had better",
        )
        return any(marker in text for marker in grammar_markers)

    def _batch_mode_for_item(self, item: dict[str, object] | None = None, word: str = "") -> str:
        """Return the effective Queue mode for an item."""
        selected = str((item or {}).get("batch_mode") or self._batch_mode_var.get() or "Vocabulary").strip()
        if selected not in BATCH_MODES:
            selected = "Vocabulary"
        if selected == "Mixed":
            value = word or str((item or {}).get("word") or "")
            return "Grammar" if self._looks_like_grammar_item(value) else "Vocabulary"
        return selected


    @staticmethod
    def _normalise_anki_value(value: str) -> str:
        """Normalize a value for exact duplicate checks."""
        import html
        plain = re.sub(r"<[^>]+>", "", html.unescape(value or ""))
        return " ".join(plain.split()).casefold()


    @classmethod
    def _batch_duplicate_target_for_item(
        cls,
        item: dict[str, object] | None,
        raw_value: str = "",
        *,
        mode: str = "",
        generated_word: str = "",
    ) -> str:
        """Return the one vocabulary target used for duplicate checks.

        Vocabulary duplicates are defined by the learner's target word/phrase
        versus Anki's ``Word`` field. Source/example sentences must never become
        part of that key. The same target is reused before generation and again
        before the Anki write so a row like ``echo chamber | ...sentence...``
        cannot be reported as new before AI and duplicate only afterwards.

        Sentence-only Provided Examples do not have a reliable lexical target
        before generation, so they intentionally skip the pre-generation lookup
        instead of comparing the whole sentence with Anki's ``Word`` field.
        Grammar uses its own target-first duplicate logic.
        """
        item = item or {}
        effective_mode = str(
            mode
            or item.get("resolved_mode")
            or item.get("batch_mode")
            or "Vocabulary"
        ).strip()
        if effective_mode == "Grammar":
            return ""

        # Imported Vocabulary + source example / Provided Examples rows already
        # carry the lexical target separately. Prefer it over every rendered/raw
        # representation of the row.
        stored_target = str(item.get("provided_target") or item.get("duplicate_target") or "").strip()
        if stored_target:
            return stored_target

        value = str(raw_value or item.get("word") or "").strip()
        if not value:
            return str(generated_word or "").strip()

        # Structured target + sentence rows: only the left side is the vocabulary
        # key. _parse_provided_example_item supports both pipe and TAB input.
        parsed_target, parsed_sentence = cls._parse_provided_example_item(value)
        if parsed_target and parsed_sentence:
            return parsed_target

        # In sentence-only Provided Examples there is no word/phrase to compare
        # before AI has inferred one. Do not compare the sentence to Anki Word.
        if effective_mode == "Provided examples":
            return str(generated_word or "").strip()

        # Plain Vocabulary rows are already the learner's lexical target.
        return value

    @classmethod
    def _batch_duplicate_lookup_candidates(cls, raw_value: str, mode: str = "Vocabulary") -> list[str]:
        """Backward-compatible wrapper returning the single lexical key.

        Duplicate lookup no longer guesses multiple keys from commas/dashes or
        source sentences. Vocabulary compares one target with Anki ``Word``.
        """
        target = cls._batch_duplicate_target_for_item({}, raw_value, mode=mode)
        return [target] if target else []

    def _precheck_one_batch_duplicate(
        self,
        index: int,
        existing_map: dict[str, dict[str, object]] | None = None,
        *,
        reason: str = "before generation",
    ) -> bool:
        """Mark one pending Queue item as duplicate before a provider call.

        Returns True when the item was marked and should not be generated.
        Returns False when no duplicate was found.
        Raises if Anki duplicate data cannot be read.
        """
        item = self._batch_items[index]
        word = str(item.get("word") or "").strip()
        if not word:
            return False
        mode = self._batch_mode_for_item(item, word)
        if mode == "Grammar":
            # v12.4.4 made grammar cards target-first.  When Queue already has a
            # compact grammar target, use it before generation so the same front
            # does not consume another provider call.  Rule-only / sentence-only
            # rows still defer until AI has produced the final concise Target.
            raw_target, _raw_sentence = self._split_batch_grammar_item(word)
            grammar_target = str(item.get("grammar_target") or raw_target).strip()
            reliable_target = bool(
                grammar_target
                and len(grammar_target) <= 120
                and not self._looks_like_complete_sentence(grammar_target)
                and not self._ocr_looks_like_rule_explanation(grammar_target)
            )
            if reliable_target:
                existing_note_id = self._anki_client.find_existing_grammar_note_id(grammar_target)
                item["duplicate_prechecked"] = True
                item["duplicate_precheck_scope"] = "all_decks_grammar_target"
                item["duplicate_lookup_value"] = grammar_target
                item["duplicate_target"] = grammar_target
                if existing_note_id is not None:
                    item["status"] = "duplicate_found"
                    item["duplicate_note_id"] = existing_note_id
                    item["duplicate_model"] = GRAMMAR_MODEL_NAME
                    item["error"] = (
                        f"Skipped {reason}: Grammar target '{grammar_target}' already exists in the Anki collection. "
                        "No AI provider API was used."
                    )
                    return True
                return False
            item["duplicate_prechecked"] = True
            item["duplicate_precheck_scope"] = "grammar_target_unavailable_before_generation"
            item.pop("duplicate_lookup_value", None)
            item.pop("duplicate_target", None)
            return False
        if existing_map is None:
            self._set_selected_deck()
            existing_map = self._anki_client.existing_note_map_broad(include_all_decks=True)
        candidate = self._batch_duplicate_target_for_item(item, word, mode=mode)
        if not candidate:
            # Sentence-only Provided Examples cannot be compared with the Anki
            # Word field before generation because there is no lexical target yet.
            item["duplicate_prechecked"] = True
            item["duplicate_precheck_scope"] = "target_unavailable_before_generation"
            item.pop("duplicate_lookup_value", None)
            item.pop("duplicate_target", None)
            return False

        item["duplicate_target"] = candidate
        existing = existing_map.get(self._normalise_anki_value(candidate))
        if existing:
            model = str(existing.get("model") or "unknown model")
            duplicate_count = int(existing.get("duplicate_count", 1) or 1)
            safe = model == MODEL_NAME and duplicate_count == 1
            item["status"] = "duplicate_found" if safe else "duplicate_uncertain"
            item["duplicate_note_id"] = existing.get("note_id")
            item["duplicate_model"] = model
            item["duplicate_lookup_value"] = candidate
            item["duplicate_prechecked"] = True
            item["duplicate_precheck_scope"] = "all_decks_word_field"
            item["error"] = (
                f"Skipped {reason}: Word '{candidate}' already exists in the Anki collection "
                f"({model}, matches: {duplicate_count}). No AI provider API was used."
            )
            return True
        item["duplicate_prechecked"] = True
        item["duplicate_precheck_scope"] = "all_decks_word_field"
        return False

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

    def _quality_warnings_for_card(
        self,
        card: VocabularyCard,
        *,
        expected_input: str = "",
        topic_context: str = "",
    ) -> list[str]:
        """Return local quality warnings before sending a card to Anki."""
        return validate_vocabulary_card(
            card,
            expected_input=expected_input or card.word_or_phrase,
            expected_target_language=self._language_var.get().strip(),
            expected_explanation_language=self._explanation_language_var.get().strip(),
            topic_context=topic_context,
        )

    def _quality_warnings_for_batch_indexes(self, indexes: list[int]) -> list[str]:
        warnings: list[str] = []
        for index in indexes:
            item = self._batch_items[index]
            card = self._card_from_batch_payload(item.get("card"))
            if card is None:
                continue
            card_warnings = self._sync_quality_warnings_for_item(item, card)
            if card_warnings:
                warnings.append(f"{index + 1}. {card.word_or_phrase}: " + "; ".join(card_warnings[:3]))
        return warnings

    def _block_hard_quality_warnings_for_batch_indexes(self, indexes: list[int]) -> int:
        """Mark ready Queue cards with hard warnings as blocked before Anki writes."""
        blocked = 0
        for index in indexes:
            item = self._batch_items[index]
            card = self._card_from_batch_payload(item.get("card"))
            if card is None:
                continue
            card_warnings = self._sync_quality_warnings_for_item(item, card)
            if item.get("quality_override"):
                continue
            hard = [warning for warning in card_warnings if warning.startswith("HARD:")]
            if not hard:
                continue
            item["status"] = "blocked_quality_warning"
            item["quality_warnings"] = card_warnings
            item["error"] = "Blocked before Anki write because of hard quality warning(s): " + "; ".join(hard[:3])
            blocked += 1
        if blocked:
            self._autosave_batch_session("blocked hard quality warnings")
            self._update_batch_progress()
            self._show_current_batch_item(generate=False)
        return blocked

    def _approve_current_quality_warning(self) -> None:
        """Let the user manually approve a generated card with hard warnings."""
        if not self._batch_items:
            return
        item = self._batch_items[self._batch_index]
        card = self._batch_generated_card or self._card_from_batch_payload(item.get("card"))
        if card is None:
            messagebox.showerror("No generated card", "Generate or select a generated vocabulary card first. Invalid items without a card cannot be approved; regenerate them after editing the input.")
            return

        old_warnings_raw = item.get("quality_warnings")
        old_warnings = old_warnings_raw if isinstance(old_warnings_raw, list) else []
        old_hard = [
            warning for warning in old_warnings
            if isinstance(warning, str) and warning.startswith("HARD:")
        ]
        warnings = self._sync_quality_warnings_for_item(item, card)
        hard = [warning for warning in warnings if warning.startswith("HARD:")]
        if not hard:
            self._batch_generated_card = card
            self._set_batch_preview(self._format_batch_card_preview(item, card))
            self._update_batch_progress()
            if old_hard:
                self._batch_status_var.set(f"Stale quality warning cleared: {card.word_or_phrase}")
                self._status_var.set(self._batch_status_var.get())
                self._autosave_batch_session(f"cleared stale quality warning: {card.word_or_phrase}")
                messagebox.showinfo(
                    "Stale warning cleared",
                    "This card no longer has hard quality warnings after current validation. It is ready now.",
                )
            else:
                messagebox.showinfo("No hard warnings", "This card has no hard quality warnings to approve.")
            return
        ok = messagebox.askyesno(
            "Approve hard warning?",
            "This card has hard quality warning(s). Mark it as ready anyway?\n\n"
            + "\n".join(f"• {warning}" for warning in hard[:5])
            + "\n\nThis approval will be saved in autosave/logs.",
        )
        if not ok:
            return
        item["quality_override"] = True
        item["quality_override_reason"] = "Approved manually by user"
        item["overridden_quality_warnings"] = warnings
        item["quality_warnings"] = warnings
        if item.get("status") in {"blocked_quality_warning", "invalid"}:
            item["status"] = "ready"
        item.pop("error", None)
        self._batch_generated_card = card
        self._set_batch_preview(self._format_batch_card_preview(item, card))
        self._batch_status_var.set(f"Approved hard warning for: {card.word_or_phrase}")
        self._status_var.set(self._batch_status_var.get())
        self._update_batch_progress()
        self._autosave_batch_session(f"approved quality warning: {card.word_or_phrase}")

    def _confirm_quality_warnings(
        self,
        card: VocabularyCard,
        *,
        expected_input: str = "",
        topic_context: str = "",
        batch_item: dict[str, object] | None = None,
    ) -> bool:
        if batch_item is not None:
            warnings = self._sync_quality_warnings_for_item(batch_item, card)
        else:
            warnings = self._quality_warnings_for_card(
                card,
                expected_input=expected_input or card.word_or_phrase,
                topic_context=topic_context,
            )
        if not warnings:
            return True
        hard = [warning for warning in warnings if warning.startswith("HARD:")]
        if hard:
            if batch_item is not None and batch_item.get("quality_override"):
                batch_item["quality_warnings"] = warnings
                batch_item["overridden_quality_warnings"] = batch_item.get("overridden_quality_warnings") or warnings
                return True
            ok = messagebox.askyesno(
                "Hard quality warnings",
                "This card has hard quality warning(s). Add it to Anki anyway?\n\n"
                + "\n".join(f"• {warning}" for warning in hard)
                + "\n\nThis approval will be saved in autosave/logs.",
            )
            if not ok:
                return False
            if batch_item is not None:
                batch_item["quality_override"] = True
                batch_item["quality_override_reason"] = "Approved from Add this card"
                batch_item["overridden_quality_warnings"] = warnings
                batch_item["quality_warnings"] = warnings
                if batch_item.get("status") in {"blocked_quality_warning", "invalid"}:
                    batch_item["status"] = "ready"
                batch_item.pop("error", None)
                self._autosave_batch_session(f"approved hard warning from Add this card: {card.word_or_phrase}")
            return True
        return messagebox.askyesno(
            "Quality warnings",
            "This card has quality warnings. Add it to Anki anyway?\n\n"
            + "\n".join(f"• {warning}" for warning in warnings),
        )

    def _auto_generate_pending_batch_cards(self) -> None:
        """Generate pending Queue cards sequentially without blocking Tk's UI thread."""
        if self._batch_auto_generate_running or self._batch_generation_in_flight:
            self._batch_status_var.set("Auto-generation is already running.")
            return
        if not self._batch_items:
            messagebox.showerror("No list", "Load a vocabulary list first.")
            return

        resume = self._batch_auto_generate_paused
        self._reset_batch_perf()
        precheck_started_at = time.perf_counter()
        # Always precheck remaining pending items before Auto Queue calls a provider.
        # This also covers paused/resumed sessions and old autosaves created before
        # duplicate precheck metadata existed.
        precheck_result = self._mark_pending_duplicates_before_auto_generation()
        self._batch_perf_precheck_s = max(0.0, time.perf_counter() - precheck_started_at)
        LOGGER.info(
            "PERF queue_precheck seconds=%.3f duplicates=%s items=%s",
            self._batch_perf_precheck_s,
            precheck_result,
            len(self._batch_items),
        )
        if precheck_result < 0:
            self._log_batch_perf_summary("precheck_failed")
            self._autosave_batch_session("auto-generation cancelled: duplicate precheck failed")
            return
        if not any(
            str(item.get("status", "pending")) == "pending"
            and not item.get("card")
            and not item.get("grammar_card")
            for item in self._batch_items
        ):
            message = "Auto-generation skipped: all pending items already exist in Anki or are not ready for generation."
            self._batch_status_var.set(message)
            self._status_var.set(message)
            self._autosave_batch_session("auto-generation skipped duplicates")
            self._log_batch_perf_summary("nothing_to_generate")
            return

        provider_name = self._provider_var.get().strip()
        if provider_name not in self._ai_clients:
            messagebox.showerror("AI provider", "Select a configured AI provider before starting Queue generation.")
            return

        # Lock generation settings for this run. The user can navigate the UI while
        # the Queue works, but changing the visible selectors must not silently
        # change provider/language halfway through the same Queue run.
        self._batch_auto_provider_name = provider_name
        self._batch_auto_model_name = self._current_ai_model_name(provider_name)
        self._batch_auto_target_language = self._language_var.get().strip()
        self._batch_auto_explanation_language = self._explanation_language_var.get().strip()
        self._batch_auto_mode = self._batch_mode_var.get().strip() or "Vocabulary"
        self._batch_auto_topic_context = self._batch_topic_var.get().strip()

        self._batch_auto_generate_running = True
        self._batch_auto_generate_paused = False
        self._batch_auto_generate_stop_requested = False
        self._record_activity("Auto-generation resumed" if resume else "Auto-generation started")
        self._autosave_batch_session("before auto-generation resume" if resume else "before auto-generation")
        self._root.after(50, self._auto_generate_next_pending_batch_card)

    def _auto_generate_next_pending_batch_card(self) -> None:
        """Start one background provider call for the next pending Queue item."""
        if self._batch_generation_in_flight:
            return
        if self._batch_auto_generate_stop_requested:
            self._batch_auto_generate_running = False
            self._batch_auto_generate_stop_requested = False
            self._autosave_batch_session("auto-generation stopped")
            if not self._batch_generation_in_flight:
                self._log_batch_perf_summary("stopped")
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
                if not item.get("card") and not item.get("grammar_card"):
                    next_index = index
                    break

        if next_index is None:
            self._batch_auto_generate_running = False
            self._update_batch_progress()
            self._autosave_batch_session("auto-generation finished")
            self._batch_status_var.set("Auto-generation finished. Autosaved.")
            self._status_var.set(self._batch_status_var.get())
            self._record_activity("Auto-generation finished")
            self._log_batch_perf_summary("finished")
            return

        item = self._batch_items[next_index]
        word = str(item.get("word", "")).strip()
        topic_context = str(item.get("topic") or self._batch_auto_topic_context).strip()
        target_language = self._batch_auto_target_language or self._language_var.get().strip()
        explanation_language = (
            self._batch_auto_explanation_language or self._explanation_language_var.get().strip()
        )
        provider_name = self._batch_auto_provider_name or self._provider_var.get().strip()
        model_name = self._batch_auto_model_name or self._current_ai_model_name(provider_name)

        item["word"] = word
        item["topic"] = topic_context
        item["target_language"] = target_language
        item["explanation_language"] = explanation_language
        if not bool(item.get("mode_locked")):
            item["batch_mode"] = self._batch_mode_var.get().strip() or "Vocabulary"
        resolved_mode = self._batch_mode_for_item(item, word)
        item["resolved_mode"] = resolved_mode

        preserve_vocab_source = (
            resolved_mode == "Vocabulary"
            and str(item.get("generation_strategy") or "") == "preserve_source_sentence"
            and bool(str(item.get("source_sentence") or "").strip())
        )
        provided_target = ""
        provided_sentence = ""
        sentence_request_word = word
        grammar_topic_context = ""

        if resolved_mode == "Provided examples" or preserve_vocab_source:
            if preserve_vocab_source:
                provided_target = str(item.get("provided_target") or word).strip()
                provided_sentence = str(item.get("source_sentence") or "").strip()
                sentence_request_word = f"{provided_target} | {provided_sentence}"
            else:
                provided_target, provided_sentence = self._parse_provided_example_item(word)
            if not provided_sentence:
                item["status"] = "invalid"
                item["error"] = "Provided examples mode needs a sentence. Use: target | sentence, or paste a sentence."
                self._batch_status_var.set("Invalid provided example: missing sentence.")
                self._set_batch_status_card("INVALID PROVIDED EXAMPLE", word, "invalid", str(item["error"]))
                self._update_batch_progress()
                self._autosave_batch_session(f"invalid provided example: {word}")
                self._root.after(120, self._auto_generate_next_pending_batch_card)
                return
            item["provided_target"] = provided_target
            item["provided_sentence"] = provided_sentence
        elif resolved_mode == "Grammar":
            grammar_topic_context = self._grammar_topic_context_for_item(item, topic_context)

        client = self._ai_clients[provider_name]
        item_ref = item
        self._batch_processing_index = next_index
        self._batch_generation_in_flight = True
        self._batch_status_var.set(
            f"Generating {resolved_mode.lower()} card {next_index + 1}/{len(self._batch_items)}: {word}..."
        )
        self._status_var.set(self._batch_status_var.get())

        job = {
            "index": next_index,
            "perf_item_started_at": time.perf_counter(),
            "item_ref": item_ref,
            "word": word,
            "resolved_mode": resolved_mode,
            "provider_name": provider_name,
            "model_name": model_name,
            "topic_context": topic_context,
            "target_language": target_language,
            "explanation_language": explanation_language,
            "preserve_vocab_source": preserve_vocab_source,
            "provided_target": provided_target,
            "sentence_request_word": sentence_request_word,
            "grammar_topic_context": grammar_topic_context,
        }

        jobs = [job]
        # Capability must be checked on the real provider, not only on a
        # tracing/decorator wrapper. A wrapper may expose batch methods while its
        # inner client still inherits the base fallback that loops one-by-one.
        capability_client = getattr(client, "_inner", client)
        provider_vocab_batch_method = getattr(
            type(capability_client),
            "generate_cards_batch",
            VocabularyAiClient.generate_cards_batch,
        )
        provider_sentence_batch_method = getattr(
            type(capability_client),
            "generate_sentence_cards_batch",
            VocabularyAiClient.generate_sentence_cards_batch,
        )
        provider_grammar_batch_method = getattr(
            type(capability_client),
            "generate_grammar_cards_batch",
            VocabularyAiClient.generate_grammar_cards_batch,
        )
        provider_supports_vocab_batch = (
            provider_vocab_batch_method is not VocabularyAiClient.generate_cards_batch
        )
        provider_supports_sentence_batch = (
            provider_sentence_batch_method
            is not VocabularyAiClient.generate_sentence_cards_batch
        )
        provider_supports_grammar_batch = (
            provider_grammar_batch_method
            is not VocabularyAiClient.generate_grammar_cards_batch
        )
        LOGGER.info(
            "PERF queue_batch_capability provider=%s runtime=%s inner=%s "
            "vocab=%s sentence=%s grammar=%s",
            provider_name,
            type(client).__name__,
            type(capability_client).__name__,
            provider_supports_vocab_batch,
            provider_supports_sentence_batch,
            provider_supports_grammar_batch,
        )
        if (
            resolved_mode == "Vocabulary"
            and not preserve_vocab_source
            and provider_supports_vocab_batch
        ):
            for candidate_index in range(next_index + 1, len(self._batch_items)):
                if len(jobs) >= QUEUE_AI_BATCH_SIZE:
                    break
                candidate = self._batch_items[candidate_index]
                if (
                    str(candidate.get("status", "pending")) != "pending"
                    or candidate.get("card")
                    or candidate.get("grammar_card")
                ):
                    continue

                candidate_word = str(candidate.get("word", "")).strip()
                candidate_topic = str(
                    candidate.get("topic") or self._batch_auto_topic_context
                ).strip()
                if not bool(candidate.get("mode_locked")):
                    candidate["batch_mode"] = self._batch_auto_mode or "Vocabulary"
                candidate_mode = self._batch_mode_for_item(candidate, candidate_word)
                candidate_preserve = (
                    candidate_mode == "Vocabulary"
                    and str(candidate.get("generation_strategy") or "")
                    == "preserve_source_sentence"
                    and bool(str(candidate.get("source_sentence") or "").strip())
                )
                if (
                    candidate_mode != "Vocabulary"
                    or candidate_preserve
                    or candidate_topic != topic_context
                ):
                    continue

                candidate["word"] = candidate_word
                candidate["topic"] = candidate_topic
                candidate["target_language"] = target_language
                candidate["explanation_language"] = explanation_language
                candidate["resolved_mode"] = "Vocabulary"
                jobs.append(
                    {
                        "index": candidate_index,
                        "perf_item_started_at": time.perf_counter(),
                        "item_ref": candidate,
                        "word": candidate_word,
                        "resolved_mode": "Vocabulary",
                        "provider_name": provider_name,
                        "model_name": model_name,
                        "topic_context": candidate_topic,
                        "target_language": target_language,
                        "explanation_language": explanation_language,
                        "preserve_vocab_source": False,
                        "provided_target": "",
                        "sentence_request_word": candidate_word,
                        "grammar_topic_context": "",
                    }
                )
        elif (
            resolved_mode == "Vocabulary"
            and preserve_vocab_source
            and provider_supports_sentence_batch
        ):
            for candidate_index in range(next_index + 1, len(self._batch_items)):
                if len(jobs) >= QUEUE_AI_BATCH_SIZE:
                    break
                candidate = self._batch_items[candidate_index]
                if (
                    str(candidate.get("status", "pending")) != "pending"
                    or candidate.get("card")
                    or candidate.get("grammar_card")
                ):
                    continue

                candidate_word = str(candidate.get("word", "")).strip()
                candidate_topic = str(
                    candidate.get("topic") or self._batch_auto_topic_context
                ).strip()
                if not bool(candidate.get("mode_locked")):
                    candidate["batch_mode"] = self._batch_auto_mode or "Vocabulary"
                candidate_mode = self._batch_mode_for_item(candidate, candidate_word)
                candidate_source_sentence = str(candidate.get("source_sentence") or "").strip()
                candidate_preserve = (
                    candidate_mode == "Vocabulary"
                    and str(candidate.get("generation_strategy") or "")
                    == "preserve_source_sentence"
                    and bool(candidate_source_sentence)
                )
                if (
                    not candidate_preserve
                    or candidate_topic != topic_context
                ):
                    continue

                candidate_target = str(
                    candidate.get("provided_target") or candidate_word
                ).strip()
                candidate["word"] = candidate_word
                candidate["topic"] = candidate_topic
                candidate["target_language"] = target_language
                candidate["explanation_language"] = explanation_language
                candidate["resolved_mode"] = "Vocabulary"
                candidate["provided_target"] = candidate_target
                candidate["provided_sentence"] = candidate_source_sentence
                jobs.append(
                    {
                        "index": candidate_index,
                        "perf_item_started_at": time.perf_counter(),
                        "item_ref": candidate,
                        "word": candidate_word,
                        "resolved_mode": "Vocabulary",
                        "provider_name": provider_name,
                        "model_name": model_name,
                        "topic_context": candidate_topic,
                        "target_language": target_language,
                        "explanation_language": explanation_language,
                        "preserve_vocab_source": True,
                        "provided_target": candidate_target,
                        "sentence_request_word": f"{candidate_target} | {candidate_source_sentence}",
                        "grammar_topic_context": "",
                    }
                )
        elif resolved_mode == "Grammar" and provider_supports_grammar_batch:
            for candidate_index in range(next_index + 1, len(self._batch_items)):
                if len(jobs) >= QUEUE_AI_BATCH_SIZE:
                    break
                candidate = self._batch_items[candidate_index]
                if (
                    str(candidate.get("status", "pending")) != "pending"
                    or candidate.get("card")
                    or candidate.get("grammar_card")
                ):
                    continue

                candidate_word = str(candidate.get("word", "")).strip()
                if not bool(candidate.get("mode_locked")):
                    candidate["batch_mode"] = self._batch_auto_mode or "Grammar"
                candidate_mode = self._batch_mode_for_item(candidate, candidate_word)
                if candidate_mode != "Grammar":
                    continue

                candidate_topic = str(
                    candidate.get("topic") or self._batch_auto_topic_context
                ).strip()
                candidate_grammar_context = self._grammar_topic_context_for_item(
                    candidate, candidate_topic
                )
                candidate["word"] = candidate_word
                candidate["topic"] = candidate_topic
                candidate["target_language"] = target_language
                candidate["explanation_language"] = explanation_language
                candidate["resolved_mode"] = "Grammar"
                jobs.append(
                    {
                        "index": candidate_index,
                        "perf_item_started_at": time.perf_counter(),
                        "item_ref": candidate,
                        "word": candidate_word,
                        "resolved_mode": "Grammar",
                        "provider_name": provider_name,
                        "model_name": model_name,
                        "topic_context": candidate_topic,
                        "target_language": target_language,
                        "explanation_language": explanation_language,
                        "preserve_vocab_source": False,
                        "provided_target": "",
                        "sentence_request_word": candidate_word,
                        "grammar_topic_context": candidate_grammar_context,
                    }
                )
        elif (
            resolved_mode == "Provided examples"
            and bool(provided_target)
            and bool(provided_sentence)
            and provider_supports_sentence_batch
        ):
            for candidate_index in range(next_index + 1, len(self._batch_items)):
                if len(jobs) >= QUEUE_AI_BATCH_SIZE:
                    break
                candidate = self._batch_items[candidate_index]
                if (
                    str(candidate.get("status", "pending")) != "pending"
                    or candidate.get("card")
                    or candidate.get("grammar_card")
                ):
                    continue

                candidate_word = str(candidate.get("word", "")).strip()
                candidate_topic = str(
                    candidate.get("topic") or self._batch_auto_topic_context
                ).strip()
                if not bool(candidate.get("mode_locked")):
                    candidate["batch_mode"] = self._batch_auto_mode or "Provided examples"
                candidate_mode = self._batch_mode_for_item(candidate, candidate_word)
                candidate_target, candidate_sentence = self._parse_provided_example_item(
                    candidate_word
                )
                if (
                    candidate_mode != "Provided examples"
                    or not candidate_target
                    or not candidate_sentence
                    or candidate_topic != topic_context
                ):
                    continue

                candidate["word"] = candidate_word
                candidate["topic"] = candidate_topic
                candidate["target_language"] = target_language
                candidate["explanation_language"] = explanation_language
                candidate["resolved_mode"] = "Provided examples"
                candidate["provided_target"] = candidate_target
                candidate["provided_sentence"] = candidate_sentence
                jobs.append(
                    {
                        "index": candidate_index,
                        "perf_item_started_at": time.perf_counter(),
                        "item_ref": candidate,
                        "word": candidate_word,
                        "resolved_mode": "Provided examples",
                        "provider_name": provider_name,
                        "model_name": model_name,
                        "topic_context": candidate_topic,
                        "target_language": target_language,
                        "explanation_language": explanation_language,
                        "preserve_vocab_source": False,
                        "provided_target": candidate_target,
                        "sentence_request_word": f"{candidate_target} | {candidate_sentence}",
                        "grammar_topic_context": "",
                    }
                )

        LOGGER.info(
            "PERF queue_batch_plan mode=%s provider=%s jobs=%s indexes=%s "
            "preserve_source=%s",
            resolved_mode,
            provider_name,
            len(jobs),
            [int(batch_job["index"]) for batch_job in jobs],
            preserve_vocab_source,
        )

        if len(jobs) > 1:
            batch_label = {
                "Provided examples": "provided examples",
                "Grammar": "grammar",
            }.get(resolved_mode, "vocabulary")
            self._batch_status_var.set(
                f"Generating {batch_label} batch of {len(jobs)} cards "
                f"starting at {next_index + 1}/{len(self._batch_items)}..."
            )
            self._status_var.set(self._batch_status_var.get())

        def worker() -> None:
            if len(jobs) > 1:
                batch_started_at = time.perf_counter()
                try:
                    if resolved_mode == "Provided examples" or preserve_vocab_source:
                        batch_results = client.generate_sentence_cards_batch(
                            [str(batch_job["sentence_request_word"]) for batch_job in jobs],
                            target_language,
                            explanation_language,
                            topic_context,
                        )
                    elif resolved_mode == "Grammar":
                        batch_results = client.generate_grammar_cards_batch(
                            [str(batch_job["word"]) for batch_job in jobs],
                            target_language,
                            [str(batch_job["grammar_topic_context"]) for batch_job in jobs],
                            explanation_language=explanation_language,
                        )
                    else:
                        batch_results = client.generate_cards_batch(
                            [str(batch_job["word"]) for batch_job in jobs],
                            target_language,
                            explanation_language,
                            topic_context,
                        )
                    if len(batch_results) != len(jobs):
                        raise ValueError(
                            f"Provider returned {len(batch_results)} cards for "
                            f"{len(jobs)} Queue items."
                        )
                    batch_ai_s = max(0.0, time.perf_counter() - batch_started_at)
                    LOGGER.info(
                        "PERF queue_ai_batch mode=%s provider=%s model=%s size=%s seconds=%.3f",
                        resolved_mode,
                        provider_name,
                        model_name,
                        len(jobs),
                        batch_ai_s,
                    )
                    per_item_ai_s = batch_ai_s / len(jobs)
                    batch_size = len(jobs)
                    for position, (batch_job, batch_result) in enumerate(
                        zip(jobs, batch_results),
                        start=1,
                    ):
                        self._batch_worker_results.put(
                            {
                                **batch_job,
                                "result": batch_result,
                                "error": None,
                                "perf_ai_s": per_item_ai_s,
                                "batch_position": position,
                                "batch_size": batch_size,
                            }
                        )
                    return
                except Exception:
                    # A malformed multi-card response must not poison the Queue.
                    # Retry only the first item through the proven single-card
                    # contract; the remaining items stay pending for the next pass.
                    LOGGER.exception(
                        "Queue %s batch failed; falling back to one-card generation: "
                        "start_index=%s size=%s provider=%s",
                        resolved_mode,
                        next_index,
                        len(jobs),
                        provider_name,
                    )

            result: object | None = None
            error: Exception | None = None
            request_started_at = time.perf_counter()
            try:
                if resolved_mode == "Provided examples" or preserve_vocab_source:
                    result = client.generate_sentence_card(
                        sentence_request_word,
                        target_language,
                        explanation_language,
                        topic_context,
                    )
                elif resolved_mode == "Grammar":
                    result = client.generate_grammar_card(
                        word,
                        target_language,
                        grammar_topic_context,
                        explanation_language=explanation_language,
                    )
                else:
                    result = client.generate_card(
                        word,
                        target_language,
                        explanation_language,
                        topic_context,
                    )
            except Exception as exc:
                error = exc
                LOGGER.exception(
                    "Background Queue provider call failed: index=%s word=%s provider=%s",
                    next_index,
                    word,
                    provider_name,
                )
            ai_s = max(0.0, time.perf_counter() - request_started_at)
            self._batch_worker_results.put(
                {
                    **job,
                    "result": result,
                    "error": error,
                    "perf_ai_s": ai_s,
                    "batch_position": 1,
                    "batch_size": 1,
                }
            )

        threading.Thread(
            target=worker,
            name=f"queue-ai-{next_index}",
            daemon=True,
        ).start()
        self._root.after(50, self._poll_background_batch_generation)

    def _poll_background_batch_generation(self) -> None:
        """Poll worker results from Tk's main thread; workers never touch Tk."""
        try:
            payload = self._batch_worker_results.get_nowait()
        except queue.Empty:
            if self._batch_generation_in_flight:
                self._root.after(50, self._poll_background_batch_generation)
            return
        self._finish_background_batch_generation(payload)

    def _finish_background_batch_generation(self, payload: dict[str, object]) -> None:
        """Apply one worker result on Tk's main thread, then continue the Queue."""
        apply_started_at = time.perf_counter()
        batch_position = int(payload.get("batch_position") or 1)
        batch_size = int(payload.get("batch_size") or 1)
        batch_has_more = batch_position < batch_size
        self._batch_generation_in_flight = batch_has_more
        if not batch_has_more:
            self._batch_processing_index = None

        index = int(payload["index"])
        item_ref = payload["item_ref"]
        if index >= len(self._batch_items) or self._batch_items[index] is not item_ref:
            LOGGER.warning("Discarding Queue result because the Queue changed while the request was running.")
            self._record_batch_item_perf(
                payload,
                status="discarded_queue_changed",
                apply_started_at=apply_started_at,
            )
            if batch_has_more:
                self._root.after(0, self._poll_background_batch_generation)
            elif self._batch_auto_generate_running and not self._batch_auto_generate_paused:
                self._root.after(120, self._auto_generate_next_pending_batch_card)
            return

        item = self._batch_items[index]
        word = str(payload["word"])
        resolved_mode = str(payload["resolved_mode"])
        provider_name = str(payload["provider_name"])
        model_name = str(payload["model_name"])
        topic_context = str(payload["topic_context"])
        target_language = str(payload["target_language"])
        explanation_language = str(payload["explanation_language"])
        preserve_vocab_source = bool(payload["preserve_vocab_source"])
        provided_target = str(payload["provided_target"])
        error = payload.get("error")

        if isinstance(error, Exception):
            detail = str(error)
            item["status"] = "error"
            item["error"] = detail
            if self._is_provider_rate_limit_detail(detail):
                item["status"] = "rate_limited"
                self._batch_status_var.set(f"Rate limit while generating: {word}. Session autosaved.")
                self._update_batch_progress()
                self._record_batch_item_perf(
                    payload,
                    status="rate_limited",
                    apply_started_at=apply_started_at,
                )
                self._stop_batch_on_provider_error(word, detail, provider_name, model_name)
                self._log_batch_perf_summary("rate_limited")
                return
            if self._is_fatal_long_generation_detail(detail):
                item["status"] = "provider_failed"
                self._batch_status_var.set(f"Provider stopped while generating: {word}. Session autosaved.")
                self._update_batch_progress()
                self._record_batch_item_perf(
                    payload,
                    status="provider_failed",
                    apply_started_at=apply_started_at,
                )
                self._stop_batch_on_provider_error(word, detail, provider_name, model_name)
                self._log_batch_perf_summary("provider_failed")
                return

            self._batch_status_var.set(f"Generation error: {word}. Raw details saved in logs/autosave.")
            if self._batch_index == index:
                self._batch_generated_card = None
                self._batch_generated_grammar = None
                self._set_batch_status_card(
                    "GENERATION ERROR",
                    word,
                    "error",
                    self._friendly_generation_error_detail(detail, provider_name, model_name),
                )
            self._update_batch_progress()
            self._autosave_batch_session(f"generation error: {word}")
            self._record_batch_item_perf(
                payload,
                status="error",
                apply_started_at=apply_started_at,
            )
            if self._batch_auto_generate_running and not self._batch_auto_generate_paused:
                self._root.after(120, self._auto_generate_next_pending_batch_card)
            return

        result = payload.get("result")
        if resolved_mode == "Grammar":
            grammar_card = result
            if not isinstance(grammar_card, GrammarAnalysis):
                item["status"] = "error"
                item["error"] = "Provider returned an unexpected grammar result."
                self._batch_status_var.set(f"Grammar generation error: {word}. Unexpected provider result.")
                self._autosave_batch_session(f"grammar generation error: {word}")
            else:
                grammar_card, focus_warnings = self._grammar_card_with_source_focus_guard(item, grammar_card)
                if focus_warnings:
                    item["source_focus_warning"] = ", ".join(focus_warnings)
                else:
                    item.pop("source_focus_warning", None)
                item["status"] = "ready"
                item["grammar_card"] = self._grammar_to_batch_payload(grammar_card)
                item.pop("card", None)
                item["provider_name"] = provider_name
                item.pop("error", None)
                if self._batch_index == index:
                    self._batch_generated_card = None
                    self._batch_generated_grammar = grammar_card
                    self._batch_generated_provider_name = provider_name
                    self._set_batch_preview(self._format_batch_grammar_preview(item, grammar_card))
                self._batch_status_var.set(f"Grammar card ready to review: {word}")
                self._autosave_batch_session(f"generated grammar: {word}")
        else:
            card = result
            if not isinstance(card, VocabularyCard):
                item["status"] = "error"
                item["error"] = "Provider returned an unexpected vocabulary result."
                self._batch_status_var.set(f"Generation error: {word}. Unexpected provider result.")
                self._autosave_batch_session(f"generation error: {word}")
            elif not card.is_valid:
                item["status"] = "invalid"
                detail = card.validation_error or "Invalid word or phrase."
                if card.suggested_correction:
                    detail += f" Suggested correction: {card.suggested_correction}"
                item["error"] = detail
                if self._batch_index == index:
                    self._batch_generated_card = None
                    self._set_batch_status_card("VALIDATION ERROR", word, "invalid", detail)
                self._batch_status_var.set(f"Invalid: {word}")
                self._autosave_batch_session(f"invalid item: {word}")
            else:
                expected_input = self._quality_expected_input_for_item(item, card)
                quality_warnings = validate_vocabulary_card(
                    card,
                    expected_input=expected_input,
                    expected_target_language=target_language,
                    expected_explanation_language=explanation_language,
                    topic_context=topic_context,
                )
                card.quality_warnings = list(
                    dict.fromkeys([*card.quality_warnings, *quality_warnings])
                )
                item["status"] = "ready"
                item["card"] = self._card_to_batch_payload(card)
                item.pop("grammar_card", None)
                item["provider_name"] = provider_name
                item.pop("error", None)
                item["topic_status"] = card.topic_fit or (
                    "topic_ok" if topic_context and not quality_warnings else ""
                )
                if quality_warnings:
                    item["quality_warnings"] = quality_warnings
                else:
                    item.pop("quality_warnings", None)

                if self._batch_index == index:
                    self._batch_generated_card = card
                    self._batch_generated_grammar = None
                    self._batch_generated_provider_name = provider_name
                    self._set_batch_preview(self._format_batch_card_preview(item, card))

                if resolved_mode == "Provided examples":
                    self._batch_status_var.set(f"Provided-example card ready to review: {card.word_or_phrase}")
                    autosave_label = "generated provided example"
                elif preserve_vocab_source:
                    item["resolved_mode"] = "Vocabulary"
                    self._batch_status_var.set(
                        f"Vocabulary card ready with preserved source example: {card.word_or_phrase}"
                    )
                    autosave_label = "generated vocabulary with source example"
                elif quality_warnings:
                    self._batch_status_var.set(f"Ready with quality warning(s): {word}")
                    autosave_label = "generated"
                else:
                    self._batch_status_var.set(f"Ready to review: {word}")
                    autosave_label = "generated"
                self._autosave_batch_session(f"{autosave_label}: {card.word_or_phrase}")

        self._status_var.set(self._batch_status_var.get())
        self._update_batch_progress()
        self._record_batch_item_perf(
            payload,
            status=str(item.get("status") or "unknown"),
            apply_started_at=apply_started_at,
        )
        if batch_has_more:
            self._root.after(0, self._poll_background_batch_generation)
        elif self._batch_auto_generate_running and not self._batch_auto_generate_paused:
            self._root.after(120, self._auto_generate_next_pending_batch_card)

    def _pause_batch_process(self) -> None:
        """Pause the currently running Queue operation without clearing results."""
        if self._batch_auto_generate_running:
            self._batch_auto_generate_paused = True
            self._batch_auto_generate_running = False
            self._autosave_batch_session("auto-generation paused")
            self._log_batch_perf_summary("paused")
            message = f"Auto-generation paused. Progress saved: {self._batch_autosave_path}"
        elif self._batch_add_all_running:
            self._batch_add_all_paused = True
            self._batch_add_all_running = False
            self._autosave_batch_session("add all ready paused")
            message = f"Add all ready paused. Progress saved: {self._batch_autosave_path}"
        else:
            message = "No Queue process is currently running."
        self._batch_status_var.set(message)
        self._status_var.set(message)
        self._record_activity(message)

    def _stop_batch_process(self) -> None:
        """Stop the current Queue operation while preserving generated results."""
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
            message = self._format_add_all_summary("Add all ready stopped")
        else:
            message = "No Queue process is currently running."
        self._batch_status_var.set(message)
        self._status_var.set(message)
        self._record_activity(message)

    def _retry_failed_or_rate_limited_batch_cards(self) -> None:
        """Retry failed/rate-limited Queue items with the currently selected provider."""
        if not self._batch_items:
            messagebox.showerror("No list", "Load a vocabulary list first.")
            return

        retryable_statuses = {"error", "add_failed", "rate_limited", "provider_failed"}
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

    def _ask_duplicate_add_strategy(self, summary: str) -> str | None:
        """Ask for an explicit duplicate strategy without ambiguous Yes/No buttons."""
        dialog = tk.Toplevel(self._root)
        dialog.title("Duplicate precheck")
        dialog.geometry("560x330")
        dialog.transient(self._root)
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        result = {"value": None}

        tk.Label(dialog, text="Duplicate check before adding to Anki", font=("Arial", 13, "bold"), anchor="w").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(16, 8)
        )
        text = tk.Text(dialog, height=8, wrap="word")
        text.insert("1.0", summary)
        text.configure(state="disabled")
        text.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 12))

        button_frame = tk.Frame(dialog)
        button_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        button_frame.grid_columnconfigure((0, 1), weight=1)

        def choose(value: str | None) -> None:
            result["value"] = value
            dialog.destroy()

        tk.Button(button_frame, text="Add new only / skip duplicates", command=lambda: choose("add_new_only")).grid(
            row=0, column=0, sticky="ew", padx=(0, 6), pady=4
        )
        tk.Button(button_frame, text="Update safe duplicates", command=lambda: choose("update_duplicates")).grid(
            row=0, column=1, sticky="ew", padx=(6, 0), pady=4
        )
        tk.Button(button_frame, text="Review duplicates first", command=lambda: choose("review_duplicates")).grid(
            row=1, column=0, sticky="ew", padx=(0, 6), pady=4
        )
        tk.Button(button_frame, text="Cancel", command=lambda: choose(None)).grid(
            row=1, column=1, sticky="ew", padx=(6, 0), pady=4
        )
        self._root.wait_window(dialog)
        return result["value"]

    def _duplicate_precheck_summary(
        self,
        indexes: list[int],
        existing_map: dict[str, dict[str, object]],
    ) -> tuple[str, dict[str, int]]:
        """Build duplicate precheck text and counts for ready Queue items."""
        counts = {"new": 0, "safe_duplicates": 0, "uncertain_duplicates": 0}
        examples: list[str] = []
        for index in indexes:
            item = self._batch_items[index]
            card = self._card_from_batch_payload(item.get("card"))
            if card is None:
                continue
            duplicate_target = self._batch_duplicate_target_for_item(
                item,
                str(item.get("word") or ""),
                generated_word=card.word_or_phrase,
            ) or card.word_or_phrase
            item["duplicate_target"] = duplicate_target
            normalized = self._normalise_anki_value(duplicate_target)
            existing = existing_map.get(normalized)
            if existing is None:
                counts["new"] += 1
                continue
            model = str(existing.get("model") or "")
            duplicate_count = int(existing.get("duplicate_count", 1) or 1)
            if model == MODEL_NAME and duplicate_count == 1:
                counts["safe_duplicates"] += 1
                label = "safe update"
            else:
                counts["uncertain_duplicates"] += 1
                label = f"review needed · {model or 'unknown model'}"
            if len(examples) < 12:
                examples.append(f"- {duplicate_target}: duplicate found ({label})")
        summary = (
            "Precheck completed:\n"
            f"{counts['new']} new cards\n"
            f"{counts['safe_duplicates']} safe duplicates in {MODEL_NAME}\n"
            f"{counts['uncertain_duplicates']} uncertain/legacy duplicates\n\n"
            "Choose what to do. Legacy/Basic duplicates are never auto-updated.\n"
        )
        if examples:
            summary += "\nExamples:\n" + "\n".join(examples)
        return summary, counts

    @staticmethod
    def _friendly_anki_error_message(exc: Exception, word: str = "") -> str:
        """Return a user-facing Anki failure reason without raw provider/API noise."""
        raw = str(exc) or exc.__class__.__name__
        lowered = raw.casefold()
        prefix = f"{word}: " if word else ""
        if "duplicate" in lowered:
            return prefix + "Anki reported this as a duplicate. It was not added; review/update the existing note."
        if "model" in lowered and ("not found" in lowered or "unknown" in lowered):
            return prefix + "Anki note type/model problem. Refresh/create the latest Vocabulary Card model and retry."
        if "field" in lowered:
            return prefix + "Anki field mismatch. The target note type probably misses a required field."
        if "connection" in lowered or "refused" in lowered or "8765" in lowered:
            return prefix + "Could not reach AnkiConnect. Open Anki and make sure AnkiConnect is running."
        return prefix + f"Anki update failed: {raw}"

    def _batch_global_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self._batch_items:
            status = str(item.get("status", "pending"))
            counts[status] = counts.get(status, 0) + 1
        return counts

    def _batch_issue_details(self, statuses: set[str], limit: int = 6) -> list[str]:
        details: list[str] = []
        for item in self._batch_items:
            status = str(item.get("status", "pending"))
            if status not in statuses:
                continue
            word = str(item.get("word") or "—")
            reason = str(item.get("error") or item.get("previous_error") or "")
            if not reason and item.get("quality_warnings"):
                warnings = item.get("quality_warnings")
                if isinstance(warnings, list):
                    reason = "; ".join(str(w) for w in warnings[:2])
            details.append(f"{word}: {self._friendly_batch_detail(reason or status, max_chars=160)}")
            if len(details) >= limit:
                break
        return details

    def _format_add_all_summary(self, label: str) -> str:
        step = self._batch_add_all_counts
        counts = self._batch_global_counts()
        total = len(self._batch_items)
        added = counts.get("added", 0) + counts.get("added_to_anki", 0)
        updated = counts.get("updated_in_anki", 0)
        duplicates = (
            counts.get("duplicate", 0)
            + counts.get("duplicate_found", 0)
            + counts.get("duplicate_uncertain", 0)
            + counts.get("duplicate_skipped", 0)
        )
        invalid = counts.get("invalid", 0) + counts.get("blocked_quality_warning", 0)
        failed = counts.get("error", 0) + counts.get("provider_failed", 0) + counts.get("add_failed", 0)
        rate_limited = counts.get("rate_limited", 0)
        remaining = counts.get("pending", 0) + counts.get("ready", 0) + rate_limited
        message = (
            f"{label}. Queue summary: {total} total · {added} added · {updated} updated · "
            f"{duplicates} duplicates skipped/reviewed · {invalid} invalid/blocked · "
            f"{failed} failed · {rate_limited} rate limited · {remaining} remaining. "
            f"Add step: {step['added']} added, {step['updated']} updated, "
            f"{step['duplicates']} duplicates skipped, {step.get('uncertain', 0)} uncertain, {step['failed']} failed."
        )
        failed_details = self._batch_add_all_failed_details or self._batch_issue_details({"error", "provider_failed", "add_failed"})
        invalid_details = self._batch_issue_details({"invalid", "blocked_quality_warning"})
        if failed_details:
            message += " Failed details: " + "; ".join(failed_details[:4])
            if len(failed_details) > 4:
                message += f"; +{len(failed_details) - 4} more"
            message += "."
        if invalid_details:
            message += " Invalid/blocked details: " + "; ".join(invalid_details[:4])
            if len(invalid_details) > 4:
                message += f"; +{len(invalid_details) - 4} more"
            message += "."
        if self._batch_autosave_path:
            message += " Autosaved."
        return self._clean_batch_visible_message(message, max_chars=520)

    def _mark_pending_duplicates_before_auto_generation(self) -> int:
        """Mark pending Queue items that already exist in Anki before any API call.

        Returns:
            Number of duplicate pending items marked. Returns -1 if duplicate
            scan failed, because continuing would waste provider API calls.
        """
        pending_indexes = [
            index
            for index, item in enumerate(self._batch_items)
            if str(item.get("status", "pending")) == "pending"
            and not item.get("card")
            and not item.get("grammar_card")
        ]
        if not pending_indexes:
            return 0
        try:
            self._set_selected_deck()
            existing_map = self._anki_client.existing_note_map_broad(include_all_decks=True)
        except Exception as exc:
            LOGGER.exception("Duplicate precheck before Auto Queue failed")
            message = (
                "Auto Queue cancelled before API calls: duplicate precheck failed. "
                "Open Anki/AnkiConnect or use Generate selected manually. "
                + self._friendly_anki_error_message(exc)
            )
            self._batch_status_var.set(message)
            self._status_var.set(message)
            return -1

        marked = 0
        for index in pending_indexes:
            if self._precheck_one_batch_duplicate(index, existing_map, reason="before generation"):
                marked += 1
        self._autosave_batch_session("auto-generation duplicate precheck")
        self._update_batch_progress()
        self._show_current_batch_item(generate=False)
        if marked:
            message = f"Duplicate precheck before AI: {marked} pending item(s) already exist in the Anki collection and were skipped before provider API calls."
        else:
            message = "Duplicate precheck before AI: no existing cards found. Starting provider generation."
        self._batch_status_var.set(message)
        self._status_var.set(message)
        self._record_activity(message)
        return marked

    def _start_add_all_ready_batch_cards(self) -> None:
        """Start safe step-by-step adding of all ready Queue cards."""
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
            and (
                self._card_from_batch_payload(item.get("card")) is not None
                or self._grammar_from_batch_payload(item.get("grammar_card")) is not None
            )
        ]
        if not indexes:
            self._batch_status_var.set("No ready cards to add.")
            self._status_var.set(self._batch_status_var.get())
            return

        # HARD quality warnings block only the affected cards, not the whole
        # Add all operation. Valid ready cards must still be added.
        blocked = self._block_hard_quality_warnings_for_batch_indexes(indexes)
        if blocked:
            indexes = [
                index for index in indexes
                if str(self._batch_items[index].get("status")) == "ready"
                and (
                    self._card_from_batch_payload(self._batch_items[index].get("card")) is not None
                    or self._grammar_from_batch_payload(self._batch_items[index].get("grammar_card")) is not None
                )
            ]
            message = (
                f"Add all ready: {blocked} card(s) blocked by HARD quality warnings. "
                "Valid ready cards will still be added. Use Go to first blocked to fix blocked cards."
            )
            self._batch_status_var.set(message)
            self._status_var.set(message)
            self._record_activity(message)
            if not indexes:
                messagebox.showwarning(
                    "No valid ready cards",
                    message + "\n\nNo valid ready cards remain to add. Use Go to first blocked, Edit card, or Regenerate.",
                )
                return

        try:
            self._set_selected_deck()
            self._batch_status_var.set("Checking duplicates before adding to Anki...")
            self._status_var.set(self._batch_status_var.get())
            self._root.update_idletasks()
            self._batch_add_all_existing_notes = self._anki_client.existing_note_map_broad(include_all_decks=True)
        except Exception as exc:
            LOGGER.exception("Could not prepare Add all ready")
            messagebox.showerror("Anki error", str(exc))
            return

        precheck_text, precheck_counts = self._duplicate_precheck_summary(indexes, self._batch_add_all_existing_notes)
        if precheck_counts["safe_duplicates"] or precheck_counts["uncertain_duplicates"]:
            strategy = self._ask_duplicate_add_strategy(precheck_text)
            if strategy is None:
                self._batch_status_var.set("Add all ready cancelled before adding anything.")
                self._status_var.set(self._batch_status_var.get())
                return
            if strategy == "review_duplicates":
                for index in indexes:
                    card = self._card_from_batch_payload(self._batch_items[index].get("card"))
                    if card is None:
                        continue
                    existing = self._batch_add_all_existing_notes.get(self._normalise_anki_value(card.word_or_phrase))
                    if existing:
                        model = str(existing.get("model") or "")
                        self._batch_items[index]["status"] = "duplicate_found" if model == MODEL_NAME else "duplicate_uncertain"
                        self._batch_items[index]["error"] = f"Duplicate exists in the Anki collection model: {model or 'unknown model'}. Review before adding."
                self._autosave_batch_session("duplicate review prepared")
                self._update_batch_progress()
                self._show_current_batch_item(generate=False)
                message = "Duplicate review prepared. No cards were added. Check duplicate_found / duplicate_uncertain rows."
                self._batch_status_var.set(message)
                self._status_var.set(message)
                return
        else:
            strategy = "add_new_only"
            self._batch_status_var.set(precheck_text.replace("\n", " · "))

        self._batch_add_all_indexes = indexes
        self._batch_add_all_position = 0
        self._batch_add_all_duplicate_strategy = strategy
        self._batch_add_all_counts = {"added": 0, "updated": 0, "duplicates": 0, "uncertain": 0, "failed": 0}
        self._batch_add_all_failed_details = []
        self._batch_add_all_running = True
        self._batch_add_all_paused = False
        self._batch_add_all_stop_requested = False
        self._autosave_batch_session("before add all ready")
        self._record_activity(f"Add all ready started: {len(indexes)} cards")
        LOGGER.info("Add all ready started: ready=%s", len(indexes))
        self._root.after(50, self._add_next_ready_batch_card)

    def _add_next_ready_batch_card(self) -> None:
        """Add one ready Queue card, then schedule the next one."""
        if self._batch_add_all_stop_requested:
            self._batch_add_all_running = False
            self._batch_add_all_stop_requested = False
            self._autosave_batch_session("add all ready stopped")
            message = self._format_add_all_summary("Add all ready stopped")
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
            self._batch_word_var.set("Queue completed")
            self._autosave_batch_session("add all ready finished")
            message = self._format_add_all_summary("Add all ready finished")
            self._batch_status_var.set(message)
            self._status_var.set(message)
            self._record_activity(message)
            LOGGER.info(message)
            return

        item_index = self._batch_add_all_indexes[self._batch_add_all_position]
        self._batch_add_all_position += 1
        item = self._batch_items[item_index]
        card = self._card_from_batch_payload(item.get("card"))
        grammar_card = self._grammar_from_batch_payload(item.get("grammar_card"))
        total = len(self._batch_add_all_indexes)

        if grammar_card is not None:
            provider_name = str(item.get("provider_name") or self._provider_var.get())
            self._batch_index = item_index
            self._batch_status_var.set(
                f"Adding grammar {self._batch_add_all_position}/{total}: {grammar_card.sentence}"
            )
            self._status_var.set(self._batch_status_var.get())
            self._update_batch_progress()
            self._root.update_idletasks()
            try:
                self._anki_client.add_grammar_card(grammar_card, provider_name, extra_tags=self._batch_tags_for_item(item))
                item["status"] = "added_to_anki"
                item.pop("error", None)
                self._batch_add_all_counts["added"] += 1
            except DuplicateNoteError as exc:
                item["status"] = "duplicate_uncertain"
                item["error"] = str(exc)
                self._batch_add_all_counts["uncertain"] += 1
            except Exception as exc:
                LOGGER.exception("Add all ready failed for grammar %s", grammar_card.sentence)
                friendly_error = self._friendly_anki_error_message(exc, grammar_card.sentence)
                item["status"] = "add_failed"
                item["error"] = friendly_error
                self._batch_add_all_counts["failed"] += 1
                self._batch_add_all_failed_details.append(friendly_error)
                self._batch_status_var.set(friendly_error)
                self._status_var.set(friendly_error)
            self._autosave_batch_session(f"add all grammar {self._batch_add_all_position}/{total}")
            self._root.after(120, self._add_next_ready_batch_card)
            return

        if card is None:
            item["status"] = "error"
            item["error"] = "Stored card payload could not be rebuilt."
            self._batch_add_all_counts["failed"] += 1
            self._autosave_batch_session("add all invalid payload")
            self._root.after(100, self._add_next_ready_batch_card)
            return

        card_warnings = self._quality_warnings_for_card(
            card,
            expected_input=self._quality_expected_input_for_item(item, card),
            topic_context=str(item.get("topic") or ""),
        )
        hard_warnings = [warning for warning in card_warnings if warning.startswith("HARD:")]
        if hard_warnings and not item.get("quality_override"):
            item["status"] = "blocked_quality_warning"
            item["quality_warnings"] = card_warnings
            item["error"] = "Blocked before Anki write because of hard quality warning(s): " + "; ".join(hard_warnings[:3])
            self._batch_add_all_counts["failed"] += 1
            self._batch_add_all_failed_details.append(f"{card.word_or_phrase}: hard quality warning")
            self._autosave_batch_session("add all blocked hard quality warning")
            self._root.after(100, self._add_next_ready_batch_card)
            return
        if hard_warnings and item.get("quality_override"):
            item["quality_warnings"] = card_warnings
            item["overridden_quality_warnings"] = item.get("overridden_quality_warnings") or card_warnings

        provider_name = str(item.get("provider_name") or self._provider_var.get())
        self._batch_index = item_index
        self._batch_status_var.set(
            f"Adding {self._batch_add_all_position}/{total}: {card.word_or_phrase}"
        )
        self._status_var.set(self._batch_status_var.get())
        self._update_batch_progress()
        self._root.update_idletasks()

        try:
            duplicate_target = self._batch_duplicate_target_for_item(
                item,
                str(item.get("word") or ""),
                generated_word=card.word_or_phrase,
            ) or card.word_or_phrase
            item["duplicate_target"] = duplicate_target
            normalized = self._normalise_anki_value(duplicate_target)
            existing_note = self._batch_add_all_existing_notes.get(normalized)
            strategy = self._batch_add_all_duplicate_strategy or "add_new_only"
            if existing_note is not None:
                model = str(existing_note.get("model") or "")
                duplicate_count = int(existing_note.get("duplicate_count", 1) or 1)
                existing_note_id = int(existing_note.get("note_id", 0) or 0)
                if strategy == "update_duplicates" and model == MODEL_NAME and duplicate_count == 1 and existing_note_id > 0:
                    self._anki_client.update_card_by_note_id(
                        existing_note_id, card, provider_name,
                        extra_tags=self._batch_tags_for_item(item),
                    )
                    item["status"] = "updated_in_anki"
                    item.pop("error", None)
                    self._batch_add_all_counts["updated"] += 1
                elif strategy == "update_duplicates":
                    item["status"] = "duplicate_uncertain"
                    item["error"] = f"Duplicate exists in {model or 'unknown model'} and was not auto-updated. Use Fix Cards to review it."
                    self._batch_add_all_counts["uncertain"] += 1
                else:
                    item["status"] = "duplicate_skipped"
                    item["error"] = "Duplicate exists in Anki and was skipped by selected strategy."
                    self._batch_add_all_counts["duplicates"] += 1
            else:
                self._anki_client.add_card_without_duplicate_scan(
                    card, provider_name, extra_tags=self._batch_tags_for_item(item)
                )
                self._batch_add_all_existing_notes[normalized] = {
                    "note_id": -1,
                    "model": MODEL_NAME,
                    "word": card.word_or_phrase,
                    "duplicate_count": 1,
                }
                item["status"] = "added_to_anki"
                item.pop("error", None)
                self._batch_add_all_counts["added"] += 1

        except Exception as exc:
            LOGGER.exception("Add all ready failed for %s", card.word_or_phrase)
            friendly_error = self._friendly_anki_error_message(exc, card.word_or_phrase)
            if "duplicate" in str(exc).casefold():
                item["status"] = "duplicate_uncertain"
                item["error"] = friendly_error
                self._batch_add_all_counts["uncertain"] += 1
            else:
                item["status"] = "add_failed"
                item["error"] = friendly_error
                self._batch_add_all_counts["failed"] += 1
                self._batch_add_all_failed_details.append(friendly_error)
            self._batch_status_var.set(friendly_error)
            self._status_var.set(friendly_error)

        outcome_status = str(item.get("status") or "")
        if outcome_status in {"added_to_anki", "updated_in_anki", "duplicate_skipped", "duplicate_uncertain", "add_failed"}:
            outcome_map = {
                "added_to_anki": "added_to_anki",
                "updated_in_anki": "updated_existing_note",
                "duplicate_skipped": "duplicate_skipped",
                "duplicate_uncertain": "duplicate_uncertain",
                "add_failed": "add_failed",
            }
            self._record_llmops_outcome(
                outcome=outcome_map.get(outcome_status, outcome_status),
                item=card.word_or_phrase,
                card_type="vocabulary",
                source="batch_add_all",
                validation_passed=outcome_status in {"added_to_anki", "updated_in_anki"},
                red_flags_count=len(card_warnings),
                issue_type="anki_export_error" if outcome_status == "add_failed" else "",
                detail=str(item.get("error") or ""),
            )

        self._autosave_batch_session(f"add all {self._batch_add_all_position}/{total}")
        self._root.after(120, self._add_next_ready_batch_card)

    def _save_batch_session(self) -> None:
        if not self._batch_items:
            messagebox.showwarning("No session", "There is no queue session to save.")
            return
        filename = filedialog.asksaveasfilename(
            title="Save queue session",
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
        self._record_activity("Queue session saved")
        self._batch_status_var.set(f"Queue session saved: {filename}")

    def _resume_batch_session(self) -> None:
        filename = filedialog.askopenfilename(
            title="Load queue session file",
            filetypes=[("JSON files", "*.json")],
        )
        if not filename:
            return
        self._load_batch_session_from_path(Path(filename))

    def _latest_batch_autosave_path(self) -> Path | None:
        autosave_dir = Path("batch_autosaves")
        if not autosave_dir.exists():
            return None
        candidates = [
            path for path in autosave_dir.glob("batch_autosave_*.json")
            if path.is_file()
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.stat().st_mtime)

    def _resume_latest_batch_session(self) -> None:
        path = self._latest_batch_autosave_path()
        if path is None:
            messagebox.showinfo("Resume Queue", "No recent Queue autosave was found.")
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("Resume Queue", f"Could not read the latest autosave: {exc}")
            return
        items = list(data.get("items") or [])
        index = int(data.get("index", 0) or 0)
        language = str(data.get("target_language") or "unknown")
        deck = str(data.get("deck") or "unknown")
        autosaved_at = str(data.get("autosaved_at") or datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="minutes"))
        proceed = messagebox.askyesno(
            "Resume latest Queue",
            (
                f"Latest session: {autosaved_at}\n"
                f"Progress: {min(index + 1, len(items)) if items else 0} / {len(items)}\n"
                f"Language: {language}\n"
                f"Deck: {deck}\n\n"
                "Resume this Queue?"
            ),
        )
        if proceed:
            self._load_batch_session_from_path(path)

    def _load_batch_session_from_path(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            session_language = str(data.get("target_language") or "").strip()
            active_language = self._language_var.get().strip()
            if session_language and active_language and session_language != active_language:
                proceed = messagebox.askyesno(
                    "Queue language differs from profile",
                    (
                        f"This Queue was saved for {session_language}, while your active Learning Profile is {active_language}.\n\n"
                        "Existing prepared cards keep their saved data. New generation will use the active profile.\n\n"
                        "Resume anyway?"
                    ),
                )
                if not proceed:
                    self._open_profile_tab()
                    return
            self._batch_items = list(data["items"])
            self._batch_index = int(data.get("index", 0))
            self._batch_autosave_path = path
            if data.get("provider") in self._ai_clients:
                self._provider_var.set(data["provider"])
            self._batch_topic_var.set(data.get("batch_topic", self._batch_topic_var.get()))
            self._batch_mode_var.set(data.get("batch_mode", self._batch_mode_var.get()))
            restored_import_mode = self._queue_mode_from_imported_item_types(self._batch_items)
            if restored_import_mode in BATCH_MODES:
                self._batch_mode_var.set(restored_import_mode)
            self._deck_var.set(data.get("deck", self._deck_var.get()))
        except Exception as exc:
            messagebox.showerror("Resume error", str(exc))
            return
        self._show_current_batch_item(generate=False)
        self._record_activity("Queue session resumed")
        self._batch_status_var.set(f"Queue session resumed: {path.name}")

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

        left = ctk.CTkScrollableFrame(layout, corner_radius=18, width=390)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))
        left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            left,
            text="Fix / Improve existing cards",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            left,
            text="Search, regenerate, edit, tag, or repair audio on existing Anki notes. Use All decks when you do not know where a card lives.",
            wraplength=335,
            justify="left",
            text_color=("gray35", "gray75"),
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        ctk.CTkLabel(left, text="Optional Anki filter").grid(row=2, column=0, sticky="w", padx=18, pady=(4, 4))
        ctk.CTkEntry(
            left,
            textvariable=self._existing_search_var,
            placeholder_text='Examples: tag:needs_fix, is:due, flag:1. Empty = selected deck/all decks.',
        ).grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 8))

        ctk.CTkLabel(left, text="Search scope").grid(row=4, column=0, sticky="w", padx=18, pady=(4, 4))
        ctk.CTkComboBox(
            left,
            variable=self._existing_scope_var,
            values=["Selected deck only", "All decks"],
            state="readonly",
        ).grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 8))

        ctk.CTkLabel(left, text="Tag filter").grid(row=6, column=0, sticky="w", padx=18, pady=(4, 4))
        ctk.CTkEntry(
            left,
            textvariable=self._existing_tag_var,
            placeholder_text='e.g. topic_character or needs_example_fix',
        ).grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 8))

        ctk.CTkLabel(left, text="Flag filter").grid(row=8, column=0, sticky="w", padx=18, pady=(4, 4))
        self._existing_flag_box = ctk.CTkComboBox(
            left,
            variable=self._existing_flag_var,
            values=[
                "No flag filter",
                "Any flag (flagged only)",
                "Red flag (flag:1)",
                "Orange flag (flag:2)",
                "Green flag (flag:3)",
                "Blue flag (flag:4)",
                "No flag (flag:0)",
            ],
            state="readonly",
        )
        self._existing_flag_box.grid(row=9, column=0, sticky="ew", padx=18, pady=(0, 8))

        ctk.CTkCheckBox(left, text="Only leech cards / tag:leech", variable=self._existing_leech_var).grid(
            row=10, column=0, sticky="w", padx=18, pady=(0, 8)
        )

        query_buttons = ctk.CTkFrame(left, fg_color="transparent")
        query_buttons.grid(row=11, column=0, sticky="ew", padx=18, pady=(0, 8))
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

        ctk.CTkLabel(left, text="Words list for finding cards").grid(row=12, column=0, sticky="w", padx=18, pady=(8, 4))
        self._existing_words_text = ctk.CTkTextbox(left, height=105, wrap="word")
        self._existing_words_text.grid(row=13, column=0, sticky="nsew", padx=18, pady=(0, 8))
        ctk.CTkButton(left, text="Find words from list", command=self._find_existing_words_from_list).grid(
            row=14, column=0, sticky="ew", padx=18, pady=(0, 10)
        )

        ctk.CTkLabel(left, text="Topic tag").grid(row=15, column=0, sticky="w", padx=18, pady=(8, 4))
        self._existing_topic_box = ctk.CTkComboBox(left, variable=self._existing_topic_var, values=TOPIC_PRESETS[1:])
        self._existing_topic_box.grid(row=16, column=0, sticky="ew", padx=18, pady=(0, 10))

        tag_buttons = ctk.CTkFrame(left, fg_color="transparent")
        tag_buttons.grid(row=17, column=0, sticky="ew", padx=18, pady=(0, 8))
        tag_buttons.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(tag_buttons, text="Select all", command=lambda: self._set_existing_selection(True)).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(tag_buttons, text="Clear", command=lambda: self._set_existing_selection(False)).grid(
            row=0, column=1, sticky="ew", padx=(5, 0)
        )

        ctk.CTkButton(left, text="Apply topic tag to selected", command=self._apply_topic_to_existing_selected).grid(
            row=18, column=0, sticky="ew", padx=18, pady=(0, 8)
        )
        ctk.CTkButton(left, text="Fix selected card", command=self._fix_selected_existing_card).grid(
            row=19, column=0, sticky="ew", padx=18, pady=(0, 8)
        )
        ctk.CTkButton(left, text="Regenerate selected card", command=self._regenerate_selected_existing_card).grid(
            row=20, column=0, sticky="ew", padx=18, pady=(0, 8)
        )
        ctk.CTkButton(left, text="Fix selected audio", command=self._fix_audio_selected_existing_card).grid(
            row=21, column=0, sticky="ew", padx=18, pady=(0, 18)
        )

        right = ctk.CTkFrame(layout, corner_radius=18)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=2)
        right.grid_rowconfigure(4, weight=1)

        header = ctk.CTkFrame(right, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 8))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Fix cards queue", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, textvariable=self._existing_progress_var).grid(row=0, column=1, sticky="e")

        self._existing_scroll = ctk.CTkScrollableFrame(right, corner_radius=18)
        self._existing_scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
        self._existing_scroll.grid_columnconfigure(0, weight=1)

        action_row = ctk.CTkFrame(right, fg_color="transparent")
        action_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 10))
        action_row.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        ctk.CTkButton(action_row, text="Edit selected card", command=self._fix_selected_existing_card).grid(
            row=0, column=0, sticky="ew", padx=(0, 5)
        )
        ctk.CTkButton(action_row, text="Regenerate", command=self._regenerate_selected_existing_card).grid(
            row=0, column=1, sticky="ew", padx=5
        )
        ctk.CTkButton(action_row, text="Fix audio", command=self._fix_audio_selected_existing_card).grid(
            row=0, column=2, sticky="ew", padx=5
        )
        ctk.CTkButton(action_row, text="Apply topic tag", command=self._apply_topic_to_existing_selected).grid(
            row=0, column=3, sticky="ew", padx=5
        )
        ctk.CTkButton(action_row, text="Select all", command=lambda: self._set_existing_selection(True)).grid(
            row=0, column=4, sticky="ew", padx=5
        )
        ctk.CTkButton(action_row, text="Clear", command=lambda: self._set_existing_selection(False)).grid(
            row=0, column=5, sticky="ew", padx=(5, 0)
        )

        ctk.CTkLabel(right, text="Preview selected card", anchor="w").grid(row=3, column=0, sticky="w", padx=18, pady=(0, 4))
        self._existing_preview = ctk.CTkTextbox(right, wrap="word", height=180, font=ctk.CTkFont(size=14))
        self._existing_preview.grid(row=4, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self._existing_preview.insert(
            "1.0",
            "Load cards. Select exactly one card, then use Edit selected card, Regenerate, or Fix audio. Use Search scope = All decks if you do not know the deck."
        )
        self._existing_preview.configure(state="disabled")

    def _find_existing_cards(self) -> None:
        self._load_existing_cards()

    def _load_flagged_existing_cards(self) -> None:
        if self._existing_flag_var.get() == "No flag filter":
            self._existing_flag_var.set("Any flag (flagged only)")
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
        value = self._existing_flag_var.get().strip()
        if value.startswith("Any flag"):
            # Anki flag:0 means unflagged; its negation means any non-zero flag.
            return "-flag:0"
        if value == "No flag filter":
            return ""
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
            include_all_decks = self._existing_scope_var.get() == "All decks"
            if not include_all_decks:
                self._set_selected_deck()
            query = self._compose_existing_cards_query()
            self._existing_cards = self._anki_client.list_existing_notes(
                search_query=query,
                missing_audio_only=False,
                words=words,
                include_all_decks=include_all_decks,
            )
        except Exception as exc:
            LOGGER.exception("Existing-card search failed")
            messagebox.showerror("Anki error", str(exc))
            return
        scope_label = "all decks" if self._existing_scope_var.get() == "All decks" else "selected deck"
        query_label = self._compose_existing_cards_query() or scope_label
        if words:
            found = {self._normalise_anki_value(str(note.get("word", ""))) for note in self._existing_cards}
            missing = [word for word in words if self._normalise_anki_value(word) not in found]
            for note in self._existing_cards:
                note["action_status"] = "found"
            message = (
                f"Find from word list: {len(self._existing_cards)} found, "
                f"{len(missing)} not found. Filter: {query_label}"
            )
            if missing:
                self._set_existing_preview(
                    "NOT FOUND FROM LIST\n" + "\n".join(f"- {word}" for word in missing[:80])
                )
        else:
            for note in self._existing_cards:
                note.setdefault("action_status", "found")
            message = f"Loaded {len(self._existing_cards)} card(s). Filter: {query_label}"
        self._render_existing_cards(message)

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
            action_status = str(note.get("action_status") or "found")
            label = (
                f"[{action_status}] {note.get('word', '—')} · {note.get('model', 'unknown model')}"
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
            self._set_existing_preview("No matching cards found. Try a broader tag/query or use Speech & Audio for missing-audio search.")

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
            (
                "AUDIO METADATA\n"
                f"Provider: {note.get('audio_provider') or '—'} · "
                f"Model: {note.get('audio_model') or '—'} · "
                f"Voice: {note.get('audio_voice_label') or note.get('audio_voice') or '—'} · "
                f"Generated: {note.get('audio_generated_at') or '—'}"
            ),
            "",
            f"ACTION STATUS\n{note.get('action_status') or 'found'}",
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
            messagebox.showwarning("Missing topic", "Choose or type a topic first.")
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
            note["action_status"] = "topic_tagged"
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
            translation=field("Translation", "TranslationPL", "PL"),
            example=field("Example", "Sentence", "ExampleSentence") or str(note.get("example", "")),
            example_translation=field("ExampleTranslation", "ExamplePL"),
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


    def _fix_audio_selected_existing_card(self) -> None:
        """Open a one-card audio repair dialog for an existing Anki note."""
        selected = self._selected_existing_cards()
        if len(selected) != 1:
            message = f"Fix audio needs exactly one selected card. Selected: {len(selected)}."
            self._existing_progress_var.set(message)
            messagebox.showwarning("Select one card", message)
            return
        if not self._speech_service or not self._tts_provider_var.get():
            messagebox.showerror("Audio provider unavailable", "Configure at least one audio provider first.")
            return
        note = selected[0]
        self._preview_existing_card(self._existing_cards.index(note))
        self._open_existing_audio_repair_dialog(note)

    @staticmethod
    def _sound_tag(media_filename: str) -> str:
        return f"[sound:{media_filename}]"

    @staticmethod
    def _audio_metadata_from_tts_result(
        result: TtsResult,
        source_text: str,
        voice_label: str = "",
    ) -> dict[str, str]:
        """Build hidden Anki fields for TTS provider/model/voice audit metadata."""
        clean_source = " ".join(str(source_text or "").split())
        return {
            "AudioProvider": result.provider_name,
            "AudioModel": result.model,
            "AudioVoice": result.voice,
            "AudioVoiceLabel": voice_label or result.voice,
            "AudioSourceText": clean_source,
            "AudioGeneratedAt": datetime.now().isoformat(timespec="seconds"),
            "AudioCacheKey": result.path.stem,
            "AudioCached": "true" if result.cached else "false",
            "AudioFile": result.path.name,
        }

    @staticmethod
    def _replace_or_append_sound_tag(current_value: str, media_filename: str) -> str:
        """Preserve text and replace old Anki [sound:...] tags with a new one."""
        sound = ModernVocabularyGui._sound_tag(media_filename)
        current = str(current_value or "")
        if re.search(r"\[sound:[^\]]+\]", current, flags=re.IGNORECASE):
            return re.sub(r"\[sound:[^\]]+\]", sound, current, flags=re.IGNORECASE)
        if current.strip():
            return f"{current}<br>{sound}"
        return sound

    def _open_existing_audio_repair_dialog(self, note: dict[str, object]) -> None:
        """Generate and replace audio for exactly one existing Anki note."""
        fields = note.get("fields") if isinstance(note.get("fields"), dict) else {}
        field_names = list(fields.keys())
        if not field_names:
            messagebox.showerror("Unsupported note", "This note has no readable fields.")
            return

        default_source = str(note.get("example_field") or note.get("word_field") or "").strip()
        if not default_source or default_source not in fields:
            for candidate in ("Example", "Sentence", "ExampleSentence", "Back", "Word", "Front", "Phrase", "Term"):
                if candidate in fields and self._plain_text(str(fields.get(candidate, ""))):
                    default_source = candidate
                    break
        default_source = default_source if default_source in fields else field_names[0]

        default_target = str(note.get("audio_field") or "").strip()
        dedicated_audio = default_target in fields and default_target in {"Audio", "WordAudio", "ExampleAudio", "SentenceAudio"}
        if not default_target or default_target not in fields:
            for candidate in ("Audio", "ExampleAudio", "SentenceAudio", "WordAudio"):
                if candidate in fields:
                    default_target = candidate
                    dedicated_audio = True
                    break
        if not default_target or default_target not in fields:
            default_target = "Back" if "Back" in fields else field_names[-1]
            dedicated_audio = False

        dialog = tk.Toplevel(self._root)
        dialog.title(f"Fix audio: {note.get('word', 'selected card')}")
        dialog.geometry("700x460")
        dialog.transient(self._root)
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        dialog.grid_columnconfigure(1, weight=1)
        dialog.grid_rowconfigure(6, weight=1)

        source_var = tk.StringVar(value=default_source)
        target_var = tk.StringVar(value=default_target)
        mode_var = tk.StringVar(
            value=(
                "Replace target field with [sound]"
                if dedicated_audio
                else "Append/replace [sound] in target field"
            )
        )
        status_var = tk.StringVar(value="Choose source/target, generate preview, then replace audio in Anki.")
        generated: dict[str, TtsResult | None] = {"result": None}

        tk.Label(dialog, text="Source text field", anchor="w").grid(row=0, column=0, sticky="w", padx=12, pady=(14, 6))
        tk.OptionMenu(dialog, source_var, *field_names).grid(row=0, column=1, sticky="ew", padx=12, pady=(14, 6))

        tk.Label(dialog, text="Target audio field", anchor="w").grid(row=1, column=0, sticky="w", padx=12, pady=6)
        tk.OptionMenu(dialog, target_var, *field_names).grid(row=1, column=1, sticky="ew", padx=12, pady=6)

        tk.Label(dialog, text="Write mode", anchor="w").grid(row=2, column=0, sticky="w", padx=12, pady=6)
        tk.OptionMenu(
            dialog,
            mode_var,
            "Replace target field with [sound]",
            "Append/replace [sound] in target field",
        ).grid(row=2, column=1, sticky="ew", padx=12, pady=6)

        provider_summary = f"Provider: {self._tts_provider_var.get()} · Model: {self._tts_model_var.get()} · Voice: {self._tts_voice_var.get()}"
        tk.Label(dialog, text=provider_summary, anchor="w", fg="gray").grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 8)
        )

        tk.Label(dialog, text="Source preview", anchor="w").grid(row=4, column=0, sticky="nw", padx=12, pady=6)
        preview = tk.Text(dialog, height=7, wrap="word")
        preview.grid(row=4, column=1, sticky="nsew", padx=12, pady=6)

        def refresh_preview(*_args: object) -> None:
            source_field = source_var.get()
            raw_text = fields.get(source_field, "")
            text = self._plain_text(str(raw_text))
            preview.delete("1.0", "end")
            preview.insert("1.0", text)
            if not text:
                status_var.set(f"Selected source field '{source_field}' is empty.")
            else:
                status_var.set(f"Ready to generate audio from '{source_field}' → '{target_var.get()}'.")

        source_var.trace_add("write", refresh_preview)
        target_var.trace_add("write", refresh_preview)
        mode_var.trace_add("write", refresh_preview)
        refresh_preview()

        tk.Label(dialog, textvariable=status_var, anchor="w", fg="gray").grid(
            row=5, column=0, columnspan=2, sticky="ew", padx=12, pady=(4, 8)
        )

        buttons = tk.Frame(dialog)
        buttons.grid(row=6, column=0, columnspan=2, sticky="ew", padx=12, pady=12)

        def generate_preview() -> None:
            source_text = preview.get("1.0", "end").strip()
            if not source_text:
                messagebox.showwarning("Missing text", "Choose a source field that contains text.")
                return
            provider_name = self._tts_provider_var.get()
            model_name = self._tts_model_var.get()
            if self._piper_voice_missing(provider_name, self._tts_voice_var.get()):
                messagebox.showerror(
                    "Piper voice unavailable",
                    f"No {self._current_tts_default_language()} Piper voice is installed. Add one in Speech & Audio → Voice Library first.",
                )
                return
            voice_value = self._selected_tts_voice()
            try:
                status_var.set("Generating audio preview...")
                dialog.update_idletasks()
                result = self._speech_service.generate(
                    provider_name,
                    source_text,
                    str(note.get("language") or self._language_var.get()),
                    model_name,
                    voice_value,
                )
            except Exception as exc:
                LOGGER.exception("Fix Cards audio preview failed")
                message = self._friendly_tts_error_message(exc)
                status_var.set(message)
                messagebox.showerror("TTS error", message)
                return
            generated["result"] = result
            status_var.set(f"Audio preview ready: {result.path.name}")
            self._record_activity(f"♪ Fix Cards audio preview: {note.get('word', 'selected card')}")
            self._play_audio_in_app(result.path, context="Fix Cards audio preview")

        def play_preview() -> None:
            result = generated.get("result")
            if result is None:
                messagebox.showwarning("No preview", "Generate audio preview first.")
                return
            self._play_audio_in_app(result.path, context="Fix Cards audio preview")

        def replace_audio() -> None:
            result = generated.get("result")
            if result is None:
                messagebox.showwarning("No preview", "Generate audio preview first.")
                return
            target_field = target_var.get().strip()
            if not target_field or target_field not in fields:
                messagebox.showerror("Invalid target", "Choose an existing target field.")
                return
            current_value = str(fields.get(target_field, "") or "")
            has_existing_audio = "[sound:" in current_value.casefold()
            if has_existing_audio:
                if not messagebox.askyesno(
                    "Replace existing audio?",
                    f"Field '{target_field}' already contains audio. Replace the existing [sound:...] tag?",
                ):
                    status_var.set("Audio replace cancelled. Nothing was changed in Anki.")
                    return
            try:
                media_name = self._anki_client.store_media_file(result.path)
                audio_metadata = self._audio_metadata_from_tts_result(
                    result,
                    preview.get("1.0", "end").strip(),
                    self._tts_voice_var.get(),
                )
                if mode_var.get() == "Replace target field with [sound]":
                    updated_value = self._sound_tag(media_name)
                else:
                    updated_value = self._replace_or_append_sound_tag(current_value, media_name)
                backup_path = self._backup_existing_note_update(
                    note,
                    {target_field: updated_value, **audio_metadata},
                    "audio repair",
                )
                if mode_var.get() == "Replace target field with [sound]":
                    self._anki_client.attach_audio_to_note(
                        int(note["note_id"]),
                        media_name,
                        target_field,
                        audio_metadata=audio_metadata,
                    )
                else:
                    self._anki_client.append_audio_to_note(
                        int(note["note_id"]),
                        media_name,
                        target_field,
                        audio_metadata=audio_metadata,
                    )
                self._anki_client.add_tags_to_notes([int(note["note_id"])], "ai_audio_fixed")
            except Exception as exc:
                LOGGER.exception("Could not replace existing-card audio")
                messagebox.showerror("Anki audio update error", str(exc))
                status_var.set("Audio update failed. See logs for details.")
                return
            fields[target_field] = updated_value
            note["fields"] = fields
            note["audio"] = updated_value
            note["audio_field"] = target_field
            note["audio_status"] = "has_audio"
            note["action_status"] = "audio_replaced"
            tags = list(note.get("tags") or [])
            if "ai_audio_fixed" not in tags:
                tags.append("ai_audio_fixed")
            note["tags"] = tags
            self._render_existing_cards(f"Audio replaced for {note.get('word', 'selected card')}. Backup: {backup_path}")
            self._record_activity(f"Replaced audio for existing card: {note.get('word', 'selected card')}")
            dialog.destroy()

        tk.Button(buttons, text="Generate audio preview", command=generate_preview).pack(side="left")
        tk.Button(buttons, text="Play preview", command=play_preview).pack(side="left", padx=(8, 0))
        tk.Button(buttons, text="Replace audio in Anki", command=replace_audio).pack(side="left", padx=(8, 0))
        tk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="left", padx=(8, 0))

    def _fix_selected_existing_card(self) -> None:
        selected = self._selected_existing_cards()
        if len(selected) != 1:
            message = f"Fix Cards needs exactly one selected card. Selected: {len(selected)}."
            self._existing_progress_var.set(message)
            messagebox.showwarning("Select one card", message)
            return
        note = selected[0]
        try:
            card = self._card_from_existing_note(note)
        except Exception as exc:
            self._existing_progress_var.set("Could not parse selected card for editing.")
            messagebox.showerror("Card parse error", str(exc))
            return
        self._preview_existing_card(self._existing_cards.index(note))
        self._existing_progress_var.set(f"Opening editor for: {card.word_or_phrase}")
        self._open_existing_card_editor(note, card)

    def _regenerate_selected_existing_card(self) -> None:
        """Open the existing-card editor and immediately regenerate a preview."""
        selected = self._selected_existing_cards()
        if len(selected) != 1:
            message = f"Regenerate needs exactly one selected card. Selected: {len(selected)}."
            self._existing_progress_var.set(message)
            messagebox.showwarning("Select one card", message)
            return
        note = selected[0]
        try:
            card = self._card_from_existing_note(note)
        except Exception as exc:
            self._existing_progress_var.set("Could not parse selected card for regeneration.")
            messagebox.showerror("Card parse error", str(exc))
            return
        self._preview_existing_card(self._existing_cards.index(note))
        self._existing_progress_var.set(f"Regenerating preview for: {card.word_or_phrase}")
        self._open_existing_card_editor(note, card, auto_regenerate=True)

    def _open_existing_card_editor(self, note: dict[str, object], card: VocabularyCard, auto_regenerate: bool = False) -> None:
        editor = tk.Toplevel(self._root)
        editor.title(f"Fix existing card: {card.word_or_phrase}")
        editor.geometry("760x760")
        editor.transient(self._root)
        editor.lift()
        editor.focus_force()
        editor.grab_set()
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
        row = add_text(row, "Translation / explanation", "translation", card.translation, height=3)
        row = add_text(row, "Example", "example", card.example, height=3)
        row = add_text(row, "Example translation", "example_translation", card.example_translation, height=3)
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
                    "translation": value("translation"),
                    "example": value("example"),
                    "example_translation": value("example_translation"),
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
                "Translation": updated_card.translation,
                "TranslationPL": updated_card.translation,
                "Definition": updated_card.definition,
                "Example": updated_card.example,
                "ExampleTranslation": updated_card.example_translation,
                "ExamplePL": updated_card.example_translation,
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
                    f"Definition: {updated_card.definition}\n\nExample: {updated_card.example}\n{updated_card.example_translation}",
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
            note["action_status"] = "saved_to_anki"
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
                "translation": regenerated.translation,
                "example": regenerated.example,
                "example_translation": regenerated.example_translation,
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
        if auto_regenerate:
            editor.after(150, regenerate_full_preview)

    def _build_speech_tab(self, parent: ctk.CTkFrame) -> None:
        """Build the central TTS/audio backfill workflow."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(5, weight=1)

        controls = ctk.CTkFrame(frame, corner_radius=18)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        controls.grid_columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(controls, text="Anki deck to scan").grid(row=0, column=0, padx=(16, 8), pady=(12, 6), sticky="w")
        self._speech_deck_box = ctk.CTkComboBox(controls, variable=self._speech_deck_var, values=[])
        self._speech_deck_box.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 8), pady=(12, 6))
        ctk.CTkButton(controls, text="Refresh decks", width=110, command=self._load_decks).grid(
            row=0, column=3, sticky="ew", padx=(0, 16), pady=(12, 6)
        )
        ctk.CTkLabel(controls, text="Learning profile").grid(row=0, column=4, padx=(0, 8), pady=(12, 6), sticky="w")
        profile_audio = ctk.CTkFrame(controls, fg_color="transparent")
        profile_audio.grid(row=0, column=5, sticky="ew", padx=(0, 16), pady=(12, 6))
        profile_audio.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(profile_audio, textvariable=self._profile_summary_var, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ctk.CTkButton(profile_audio, text="Edit", width=54, command=self._open_profile_tab).grid(
            row=0, column=1, sticky="e"
        )

        ctk.CTkLabel(controls, text="Audio provider").grid(row=1, column=0, padx=(16, 8), pady=6, sticky="w")
        self._tts_provider_box = ctk.CTkComboBox(
            controls, variable=self._tts_provider_var,
            values=list(self._speech_service.providers) if self._speech_service else [],
            state="readonly", command=lambda _value: self._sync_tts_defaults(),
        )
        self._tts_provider_box.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=6)
        ctk.CTkLabel(controls, text="Model").grid(row=1, column=2, padx=(0, 8), pady=6, sticky="w")
        self._tts_model_box = ctk.CTkComboBox(controls, variable=self._tts_model_var, values=[])
        self._tts_model_box.grid(row=1, column=3, sticky="ew", padx=(0, 16), pady=6)
        ctk.CTkLabel(controls, text="Voice").grid(row=1, column=4, padx=(0, 8), pady=6, sticky="w")
        self._tts_voice_box = ctk.CTkComboBox(controls, variable=self._tts_voice_var, values=[])
        self._tts_voice_box.grid(row=1, column=5, sticky="ew", padx=(0, 16), pady=6)
        ctk.CTkLabel(
            controls,
            text="Audio uses the active Learning Profile language. Choose another language once in Profile, not separately here.",
            text_color=("gray35", "gray75"),
        ).grid(row=2, column=0, columnspan=6, sticky="w", padx=16, pady=(0, 12))

        voice_lab = ctk.CTkFrame(frame, corner_radius=18)
        voice_lab.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        voice_lab.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(voice_lab, text="Voice Lab", font=ctk.CTkFont(size=17, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=(16, 8), pady=(12, 4)
        )
        ctk.CTkLabel(
            voice_lab, text="Test the selected voice here. Playback stays inside the app — no external media player.",
            text_color=("gray35", "gray75"),
        ).grid(row=0, column=1, columnspan=3, sticky="w", padx=(0, 16), pady=(12, 4))
        ctk.CTkLabel(voice_lab, text="Sample text").grid(row=1, column=0, sticky="w", padx=(16, 8), pady=(4, 12))
        ctk.CTkEntry(voice_lab, textvariable=self._speech_preview_text_var, height=36).grid(
            row=1, column=1, sticky="ew", padx=(0, 8), pady=(4, 12)
        )
        ctk.CTkButton(voice_lab, text="Play voice", width=110, command=self._preview_tts_voice_sample).grid(
            row=1, column=2, padx=(0, 8), pady=(4, 12)
        )
        ctk.CTkButton(voice_lab, text="Stop", width=80, command=self._stop_speech_preview).grid(
            row=1, column=3, padx=(0, 8), pady=(4, 12)
        )
        ctk.CTkButton(voice_lab, text="Test provider", width=110, command=self._test_tts_provider).grid(
            row=1, column=4, padx=(0, 8), pady=(4, 12)
        )
        ctk.CTkButton(voice_lab, text="Voice Library", width=120, command=self._open_voice_library).grid(
            row=1, column=5, padx=(0, 16), pady=(4, 12)
        )

        search = ctk.CTkFrame(frame, corner_radius=18)
        search.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        search.grid_columnconfigure((1, 3, 5), weight=1)

        ctk.CTkLabel(search, text="Optional Anki filter").grid(row=0, column=0, padx=(16, 8), pady=(12, 6), sticky="w")
        ctk.CTkEntry(
            search,
            textvariable=self._speech_search_var,
            placeholder_text='Examples: tag:topic_character, note:Basic, is:due. Empty = selected audio deck.',
        ).grid(row=0, column=1, columnspan=5, sticky="ew", padx=(0, 16), pady=(12, 6))

        ctk.CTkLabel(search, text="Source text field").grid(row=1, column=0, padx=(16, 8), pady=6, sticky="w")
        self._speech_source_field_box = ctk.CTkComboBox(
            search,
            variable=self._speech_source_field_var,
            values=[
                "Auto: Example/ContextExample/Back/Word",
                "Example",
                "ContextExample",
                "Sentence",
                "ExampleSentence",
                "Back",
                "Front",
                "Word",
                "Phrase",
                "Term",
            ],
        )
        self._speech_source_field_box.grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=6)

        ctk.CTkLabel(search, text="Target audio field").grid(row=1, column=2, padx=(0, 8), pady=6, sticky="w")
        self._speech_target_field_box = ctk.CTkComboBox(
            search,
            variable=self._speech_target_field_var,
            values=["Audio", "ExampleAudio", "SentenceAudio", "WordAudio", "Back", "Example", "Front"],
        )
        self._speech_target_field_box.grid(row=1, column=3, sticky="ew", padx=(0, 16), pady=6)

        ctk.CTkLabel(search, text="Write mode").grid(row=1, column=4, padx=(0, 8), pady=6, sticky="w")
        self._speech_write_mode_box = ctk.CTkComboBox(
            search,
            variable=self._speech_write_mode_var,
            values=["Use dedicated audio field", "Append [sound] to existing field"],
            state="readonly",
        )
        self._speech_write_mode_box.grid(row=1, column=5, sticky="ew", padx=(0, 16), pady=6)

        ctk.CTkLabel(
            search,
            text="If old cards have no Audio field, choose Append mode and target Back/Example. Generate is enabled only for ready rows.",
            text_color=("gray35", "gray75"),
        ).grid(row=3, column=0, columnspan=6, sticky="w", padx=16, pady=(0, 12))

        actions = ctk.CTkFrame(frame, corner_radius=18)
        actions.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkButton(actions, text="Find missing audio", command=self._load_speech_notes).pack(side="left", padx=16, pady=14)
        ctk.CTkButton(
            actions,
            text="Find missing audio — all decks / current language",
            command=lambda: self._load_speech_notes(include_all_decks=True),
        ).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkButton(actions, text="Select ready", command=self._select_ready_speech_notes).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkButton(actions, text="Deselect all", command=self._deselect_speech_notes).pack(side="left", padx=(0, 8), pady=14)
        ctk.CTkButton(actions, text="Clear results", command=self._clear_speech_results).pack(side="left", padx=(0, 8), pady=14)
        self._generate_audio_button = ctk.CTkButton(actions, text="Generate audio for selected", command=self._generate_audio_for_existing)
        self._generate_audio_button.pack(side="left", padx=(0, 8), pady=14)
        self._pause_audio_button = ctk.CTkButton(actions, text="Pause audio", command=self._pause_existing_audio_batch, state="disabled")
        self._pause_audio_button.pack(side="left", padx=(0, 8), pady=14)
        self._stop_audio_button = ctk.CTkButton(actions, text="Stop audio", command=self._stop_existing_audio_batch, state="disabled")
        self._stop_audio_button.pack(side="left", padx=(0, 8), pady=14)

        status_panel = ctk.CTkFrame(frame, corner_radius=18)
        status_panel.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        status_panel.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(status_panel, text="Audio scan").grid(row=0, column=0, sticky="w", padx=(16, 8), pady=(10, 2))
        ctk.CTkLabel(status_panel, textvariable=self._speech_summary_var, anchor="w").grid(
            row=0, column=1, sticky="ew", padx=(0, 16), pady=(10, 2)
        )
        ctk.CTkLabel(status_panel, text="Audio status").grid(row=1, column=0, sticky="w", padx=(16, 8), pady=(2, 10))
        ctk.CTkLabel(
            status_panel,
            textvariable=self._speech_progress_var,
            anchor="w",
            text_color=("gray25", "gray80"),
        ).grid(row=1, column=1, sticky="ew", padx=(0, 16), pady=(2, 10))

        self._speech_scroll = ctk.CTkScrollableFrame(frame, corner_radius=18)
        self._speech_scroll.grid(row=5, column=0, sticky="nsew")
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

    def _plain_text(self, value: object) -> str:
        """Return a safe plain-text preview from Anki field values.

        Anki fields often contain HTML snippets, line breaks, and [sound:...] tags.
        The Fix Cards and Speech & Audio views use this helper only for preview
        and source-text extraction, so it must be conservative and never raise.
        """
        if value is None:
            return ""
        text = str(value)
        text = re.sub(r"\[sound:[^\]]+\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</\s*(div|p|li|tr|h[1-6])\s*>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text)
        return text.strip()

    def _record_activity(self, text: str) -> None:
        previous = [part.strip() for part in self._activity_var.get().split(" | ") if part.strip()]
        previous.append(text)
        self._activity_var.set(" | ".join(previous[-3:]))

    def _record_llmops_outcome(
        self,
        *,
        outcome: str,
        item: str = "",
        card_type: str = "",
        source: str = "anki_connect",
        validation_passed: bool | None = None,
        red_flags_count: int | None = None,
        issue_type: str = "",
        detail: str = "",
    ) -> None:
        """Record user review / Anki outcome in the local LLMOps log."""
        try:
            get_llmops_tracer().record_outcome(
                outcome=outcome,
                item=item,
                card_type=card_type,
                source=source,
                validation_passed=validation_passed,
                red_flags_count=red_flags_count,
                issue_type=issue_type,
                detail=detail,
            )
            self._refresh_llmops_log()
        except Exception:
            # Observability must never break review/export flows.
            LOGGER.debug("Could not record LLMOps outcome", exc_info=True)

    def _current_ai_client(self) -> VocabularyAiClient:
        if not self._ai_clients:
            raise ValueError("No AI provider is configured. Open Setup and configure Local, Hybrid/BYOK or API/BYOK first.")
        provider_name = self._provider_var.get()
        client = self._ai_clients.get(provider_name)
        if client is None:
            provider_name = next(iter(self._ai_clients))
            self._provider_var.set(provider_name)
            client = self._ai_clients[provider_name]
        return client

    def _current_ai_model_name(self, provider_name: str | None = None, workflow: str = "card") -> str:
        if not self._ai_clients:
            return ""
        client = self._ai_clients.get(provider_name or self._provider_var.get()) or self._current_ai_client()
        resolver = getattr(client, "model_for_workflow", None)
        if callable(resolver):
            try:
                return str(resolver(workflow))
            except Exception:
                pass
        inner = getattr(client, "_inner", None)
        resolver = getattr(inner, "model_for_workflow", None)
        if callable(resolver):
            try:
                return str(resolver(workflow))
            except Exception:
                pass
        return str(getattr(client, "_model", getattr(inner, "_model", "")))

    def _multimodal_model_name(self, provider_name: str) -> str | None:
        """Return the configured vision/multimodal model for Import Material."""
        provider = (provider_name or "").strip().casefold()
        if "openai" in provider:
            return (
                os.getenv("OPENAI_MULTIMODAL_MODEL")
                or os.getenv("OPENAI_IMPORT_MODEL")
                or os.getenv("OPENAI_MODEL")
            )
        if "gemini" in provider or "google" in provider:
            return (
                os.getenv("GEMINI_MULTIMODAL_MODEL")
                or os.getenv("GEMINI_IMPORT_MODEL")
                or os.getenv("GEMINI_MODEL")
            )
        return None

    def _load_decks(self) -> None:
        try:
            decks = self._anki_client.list_decks()
        except Exception as exc:
            self._deck_box.configure(values=[self._anki_client.deck_name])
            speech_deck_box = getattr(self, "_speech_deck_box", None)
            if speech_deck_box is not None:
                speech_deck_box.configure(values=[self._anki_client.deck_name])
            conversation_deck_box = getattr(self, "_conversation_deck_box", None)
            if conversation_deck_box is not None:
                conversation_deck_box.configure(values=[self._anki_client.deck_name])
            if not self._speech_deck_var.get().strip():
                self._speech_deck_var.set(self._anki_client.deck_name)
            if not self._conversation_deck_var.get().strip():
                self._conversation_deck_var.set(self._anki_client.deck_name)
            self._status_var.set("Could not load decks. Open Anki and click Refresh.")
            messagebox.showwarning("Anki connection", str(exc))
            return

        if self._anki_client.deck_name not in decks:
            decks.append(self._anki_client.deck_name)
        deck_values = sorted(decks)
        self._deck_box.configure(values=deck_values)
        speech_deck_box = getattr(self, "_speech_deck_box", None)
        if speech_deck_box is not None:
            speech_deck_box.configure(values=deck_values)
        conversation_deck_box = getattr(self, "_conversation_deck_box", None)
        if conversation_deck_box is not None:
            conversation_deck_box.configure(values=deck_values)
        if not self._deck_var.get().strip():
            self._deck_var.set(self._anki_client.deck_name)
        if not self._speech_deck_var.get().strip():
            self._speech_deck_var.set(self._deck_var.get() or self._anki_client.deck_name)
        if not self._conversation_deck_var.get().strip():
            self._conversation_deck_var.set(self._deck_var.get() or self._anki_client.deck_name)
        self._status_var.set(
            "Decks loaded. Select a target deck for cards, audio, or Conversation."
        )

    def _set_selected_deck(self) -> str:
        deck_name = self._deck_var.get().strip()
        if not deck_name:
            raise ValueError("Select or type an Anki deck name.")
        self._anki_client.set_deck(deck_name)
        return deck_name

    def _set_speech_selected_deck(self) -> str:
        """Select the deck used by Speech & Audio without relying on the hidden top bar."""
        deck_name = self._speech_deck_var.get().strip() or self._deck_var.get().strip()
        if not deck_name:
            raise ValueError("Select or type an Anki deck to scan in Speech & Audio.")
        self._anki_client.set_deck(deck_name)
        return deck_name

    def _current_speech_language(self) -> str:
        """Language fallback for Speech & Audio when a note has no language field."""
        return self._speech_language_var.get().strip() or self._language_var.get().strip()

    def _current_tts_default_language(self) -> str:
        """Choose the language for TTS presets/previews in the active workflow."""
        try:
            if getattr(self, "_tabs", None) is not None and self._tabs.get() == "Speech & Audio":
                return self._current_speech_language()
        except Exception:
            pass
        return self._language_var.get().strip()

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
        """Return a readable pseudo-card preview for single and Queue workflows."""
        synonyms = ", ".join(card.synonyms) if card.synonyms else "—"
        collocations = "\n".join(f"  • {item}" for item in card.collocations) if card.collocations else "—"
        audio_line = str(audio_status or card.audio or "not generated")
        display_warnings = [
            str(item)
            for item in card.quality_warnings
            if "spanish-looking characters detected in polish" not in str(item).casefold()
            and "possible mixed-language text in polish grammar note" not in str(item).casefold()
        ]
        warnings = "\n".join(f"  • {item}" for item in display_warnings) if display_warnings else "—"
        topic = card.topic_fit or "—"
        if card.topic_warning:
            topic += f" · {card.topic_warning}"
        return (
            "╭────────────────────────────────────────╮\n"
            f"  {card.word_or_phrase}\n"
            "╰────────────────────────────────────────╯\n\n"
            f"LANGUAGE / TYPE\n{card.target_language} · {card.part_of_speech or '—'}\n\n"
            f"DEFINITION\n{card.definition or '—'}\n\n"
            f"EXPLANATION LANGUAGE\n{card.explanation_language or '—'}\n\n"
            f"TRANSLATION / EXPLANATION\n{card.translation or '—'}\n\n"
            f"EXAMPLE\n{card.example or '—'}\n{card.example_translation or '—'}\n\n"
            f"SYNONYMS / ALTERNATIVES\n{synonyms}\n\n"
            f"COLLOCATIONS / USAGE\n{collocations}\n\n"
            f"GRAMMAR NOTE\n{card.grammar_note or '—'}\n\n"
            f"TOPIC FIT\n{topic}\n\n"
            f"QUALITY WARNINGS\n{warnings}\n\n"
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
        audio_metadata: dict[str, str] | None = None
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

                audio_metadata = self._audio_metadata_from_tts_result(
                    self._generated_audio,
                    self._generated_card.example,
                    self._tts_voice_var.get(),
                )
                self._generated_card = self._generated_card.model_copy(
                    update={"audio": f"[sound:{media_name}]"}
                )
                LOGGER.info(
                    "Generated card audio field set: word=%s media=%s provider=%s model=%s voice=%s",
                    self._generated_card.word_or_phrase,
                    media_name,
                    audio_metadata.get("AudioProvider") if audio_metadata else "",
                    audio_metadata.get("AudioModel") if audio_metadata else "",
                    audio_metadata.get("AudioVoice") if audio_metadata else "",
                )
            self._anki_client.add_card(self._generated_card, provider_name, audio_metadata=audio_metadata)
        except DuplicateNoteError as exc:
            if not exc.update_safe:
                model = exc.model_name or "another/legacy note type"
                self._status_var.set("Duplicate found; existing card was left unchanged.")
                messagebox.showwarning(
                    "Card already exists",
                    f"A card for '{self._generated_card.word_or_phrase}' already exists "
                    f"somewhere in the Anki collection ({model}).\n\n"
                    "It was not overwritten automatically because the existing note is not "
                    "a single current AI Vocabulary Light Card.",
                )
                return
            replace = messagebox.askyesno(
                "Card already exists",
                f"A card for '{self._generated_card.word_or_phrase}' already exists "
                "in the Anki collection.\n\nReplace it with this reviewed version?",
            )
            if not replace:
                self._status_var.set("Existing card was not changed.")
                return
            try:
                self._anki_client.update_card(self._generated_card, provider_name, audio_metadata=audio_metadata)
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
            self._record_llmops_outcome(
                outcome="updated_existing_note",
                item=self._generated_card.word_or_phrase,
                card_type="vocabulary",
                source="single_flashcard",
                validation_passed=True,
            )
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
            self._record_llmops_outcome(
                outcome="add_failed",
                item=self._generated_card.word_or_phrase if self._generated_card else "",
                card_type="vocabulary",
                source="single_flashcard",
                validation_passed=False,
                issue_type="anki_export_error",
                detail=message,
            )
            messagebox.showerror("Anki error", message)
            return
        self._status_var.set(f"✓ Added to Anki deck {deck}: {self._generated_card.word_or_phrase}")
        self._record_activity(f"✓ {self._generated_card.word_or_phrase} added")
        self._record_llmops_outcome(
            outcome="added_to_anki",
            item=self._generated_card.word_or_phrase,
            card_type="vocabulary",
            source="single_flashcard",
            validation_passed=True,
        )
        self._word_var.set("")
        self._generated_card = None
        self._generated_provider_name = None
        self._generated_audio = None

    def _sync_single_tts_provider(self) -> None:
        """Mirror the Single Flashcard TTS selector into shared TTS defaults."""
        provider_name = self._single_tts_provider_var.get().strip()
        if provider_name == "Off":
            return
        self._tts_provider_var.set(provider_name)
        self._sync_tts_defaults()

    def _sync_speech_preview_text(self) -> None:
        """Update Voice Lab sample when its text is still the previous automatic sample."""
        language = self._current_speech_language()
        new_sample = TTS_SAMPLE_TEXTS.get(language, TTS_SAMPLE_TEXTS["English"])
        current = self._speech_preview_text_var.get().strip()
        if not current or current == self._speech_preview_last_auto_text:
            self._speech_preview_text_var.set(new_sample)
            self._speech_preview_last_auto_text = new_sample

    def _register_runtime_voice(self, provider_name: str, label: str, value: str, language: str = "") -> None:
        """Register a user-discovered voice without hard-coding it into presets."""
        if not provider_name or not label or not value:
            return
        self._runtime_voice_values.setdefault(provider_name, {})[label] = value
        self._runtime_voice_languages.setdefault(provider_name, {})[label] = language or ""

    @staticmethod
    def _voice_language_matches(candidate: str, requested: str) -> bool:
        if not requested or not candidate:
            return True
        c = candidate.strip().casefold().replace("_", "-")
        r = requested.strip().casefold().replace("_", "-")
        if c in {"multilingual", "multi", "auto", "all"}:
            return True
        aliases = {
            "english": "en",
            "spanish": "es",
            "polish": "pl",
            "german": "de",
            "french": "fr",
            "italian": "it",
            "portuguese": "pt",
        }
        r_short = aliases.get(r, r[:2])
        c_short = aliases.get(c, c[:2])
        return c == r or c_short == r_short

    def _voice_options_for_provider(self, provider_name: str, language: str) -> list[str]:
        """Return readable voice labels, including downloaded/runtime voices."""
        if not self._speech_service or provider_name not in self._speech_service.providers:
            return []
        provider = self._speech_service.providers[provider_name]
        labels: list[str] = []

        # Piper voice paths are converted into readable labels from their JSON metadata.
        is_piper = provider_name.casefold().startswith("piper")
        if is_piper:
            for raw_path in provider.voices:
                meta = piper_voice_metadata(raw_path)
                if language and meta.get("language") and not self._voice_language_matches(meta["language"], language):
                    continue
                label = meta.get("label") or Path(raw_path).stem
                self._register_runtime_voice(provider_name, label, str(raw_path), meta.get("language") or meta.get("locale") or "")
                if label not in labels:
                    labels.append(label)

        # Piper is language-specific. Never fall back to a voice from another
        # language just because no matching model is installed.
        if is_piper:
            return labels

        # Built-in cloud presets remain useful fallbacks.
        for label in get_voice_labels(provider_name, language):
            if label not in labels:
                labels.append(label)
        if not labels:
            for label in get_voice_labels(provider_name):
                if label not in labels:
                    labels.append(label)

        # Voices discovered from ElevenLabs My Voices / Voice Library are kept in memory.
        runtime = self._runtime_voice_values.get(provider_name, {})
        languages = self._runtime_voice_languages.get(provider_name, {})
        for label in runtime:
            candidate_language = languages.get(label, "")
            if candidate_language and language and not self._voice_language_matches(candidate_language, language):
                continue
            if label not in labels:
                labels.append(label)

        if not labels:
            labels = list(provider.voices)
        return labels

    def _resolve_runtime_voice(self, provider_name: str, label: str) -> str | None:
        return self._runtime_voice_values.get(provider_name, {}).get(label)

    def _open_voice_library(self) -> None:
        """Open one in-app browser for Piper, OpenAI, Gemini and ElevenLabs voices."""
        if self._voice_library_window is not None and self._voice_library_window.winfo_exists():
            self._voice_library_window.focus()
            return

        window = ctk.CTkToplevel(self._root)
        self._voice_library_window = window
        window.title("Voice Library")
        window.geometry("1040x650")
        window.minsize(900, 560)
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(window, corner_radius=18)
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        header.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(header, text="Voice Library", font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=(16, 10), pady=(14, 4)
        )
        ctk.CTkLabel(
            header,
            text="Browse and preview Piper, OpenAI, Gemini and ElevenLabs voices in one place.",
            text_color=("gray35", "gray75"),
        ).grid(row=0, column=1, columnspan=5, sticky="w", padx=(0, 16), pady=(14, 4))

        sources = ["Piper online catalog", "OpenAI built-in voices", "Gemini built-in voices"]
        settings = get_settings()
        if settings.elevenlabs_api_key:
            sources.extend(["ElevenLabs Voice Library", "ElevenLabs My Voices"])
        source_box = ctk.CTkComboBox(
            header,
            variable=self._voice_library_source_var,
            values=sources,
            state="readonly",
            width=220,
        )
        source_box.grid(row=1, column=0, padx=(16, 8), pady=(6, 14), sticky="w")
        language_values = ["All", *list(TTS_SAMPLE_TEXTS.keys())]
        current_language = self._current_tts_default_language()
        self._voice_library_language_var.set(current_language if current_language in language_values else "All")
        language_box = ctk.CTkComboBox(
            header,
            variable=self._voice_library_language_var,
            values=language_values,
            state="normal",
            width=170,
        )
        language_box.grid(row=1, column=1, padx=(0, 8), pady=(6, 14), sticky="w")
        self._voice_library_language_box = language_box
        self._load_piper_language_choices_async()
        ctk.CTkEntry(
            header,
            textvariable=self._voice_library_search_var,
            placeholder_text="Search name, accent, locale...",
        ).grid(row=1, column=2, sticky="ew", padx=(0, 8), pady=(6, 14))
        ctk.CTkButton(header, text="Search", width=90, command=self._search_voice_library).grid(
            row=1, column=3, padx=(0, 8), pady=(6, 14)
        )
        ctk.CTkButton(header, text="Add local Piper .onnx", width=150, command=self._add_local_piper_voice).grid(
            row=1, column=4, padx=(0, 8), pady=(6, 14)
        )
        ctk.CTkButton(header, text="Open Piper folder", width=130, command=self._open_piper_voice_folder).grid(
            row=1, column=5, padx=(0, 16), pady=(6, 14)
        )

        info = ctk.CTkLabel(
            window,
            text=(
                "Piper uses public provider samples. OpenAI and Gemini previews are generated with your own API key and may incur API usage. "
                "ElevenLabs browsing uses your own API key and its shared Voice Library may require an eligible paid tier."
            ),
            text_color=("gray35", "gray75"),
            anchor="w",
        )
        info.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 8))

        tree_frame = ctk.CTkFrame(window, corner_radius=18)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=14, pady=(0, 8))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        columns = ("name", "language", "accent", "quality", "status")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        self._voice_library_tree = tree
        for col, title, width in (
            ("name", "Voice", 310),
            ("language", "Language / locale", 190),
            ("accent", "Accent / gender", 170),
            ("quality", "Quality", 120),
            ("status", "Status", 110),
        ):
            tree.heading(col, text=title)
            tree.column(col, width=width, minwidth=80, stretch=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        tree.bind("<Double-1>", lambda _event: self._preview_selected_library_voice())

        footer = ctk.CTkFrame(window, corner_radius=18)
        footer.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, textvariable=self._voice_library_status_var, anchor="w").grid(
            row=0, column=0, sticky="ew", padx=16, pady=(12, 4)
        )
        buttons = ctk.CTkFrame(footer, fg_color="transparent")
        buttons.grid(row=1, column=0, sticky="w", padx=16, pady=(4, 12))
        ctk.CTkButton(buttons, text="Preview", command=self._preview_selected_library_voice).pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons, text="Add / download", command=self._add_selected_library_voice).pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons, text="Use selected", command=self._use_selected_library_voice).pack(side="left", padx=(0, 8))
        ctk.CTkButton(buttons, text="Stop preview", command=self._stop_speech_preview).pack(side="left")

        self._voice_library_status_var.set("Choose a source and press Search. Double-click a voice to preview it.")
        self._search_voice_library()

    def _load_piper_language_choices_async(self) -> None:
        """Populate the Voice Library filter with every language in Piper's live catalog."""
        def worker() -> None:
            try:
                languages = fetch_piper_language_names()
            except Exception:
                LOGGER.exception("Could not load Piper language catalog")
                return

            def apply() -> None:
                box = self._voice_library_language_box
                if box is None or not box.winfo_exists():
                    return
                values = ["All", *sorted(set(TTS_SAMPLE_TEXTS) | set(languages), key=str.casefold)]
                box.configure(values=values)

            self._root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _voice_library_selected_item(self) -> VoiceLibraryItem | None:
        tree = self._voice_library_tree
        if tree is None:
            return None
        selected = tree.selection()
        if not selected:
            return None
        return self._voice_library_result_by_iid.get(selected[0])

    def _voice_library_run_async(self, working_text: str, worker, on_success) -> None:
        self._voice_library_status_var.set(working_text)

        def run() -> None:
            try:
                result = worker()
            except Exception as exc:
                LOGGER.exception("Voice Library operation failed")
                detail = str(exc)
                if "403" in detail and "ElevenLabs" in self._voice_library_source_var.get():
                    detail = "ElevenLabs denied Voice Library access (HTTP 403). The Voice Library API may require an eligible paid tier."
                self._root.after(0, lambda detail=detail: self._voice_library_status_var.set(f"Voice Library error: {detail}"))
                return
            self._root.after(0, lambda: on_success(result))

        threading.Thread(target=run, daemon=True).start()

    def _search_voice_library(self) -> None:
        source = self._voice_library_source_var.get().strip()
        query = self._voice_library_search_var.get().strip()
        language = self._voice_library_language_var.get().strip()
        language_name = None if language == "All" else language
        settings = get_settings()

        if source == "Piper online catalog":
            worker = lambda: fetch_piper_catalog(language_name=language_name, query=query)
        elif source == "OpenAI built-in voices":
            worker = lambda: openai_builtin_voice_items(query=query)
        elif source == "Gemini built-in voices":
            worker = lambda: gemini_builtin_voice_items(query=query)
        elif source == "ElevenLabs Voice Library":
            if not settings.elevenlabs_api_key:
                self._voice_library_status_var.set("Add ELEVENLABS_API_KEY in Setup first.")
                return
            worker = lambda: fetch_elevenlabs_shared_voices(
                settings.elevenlabs_api_key or "", language_name=language_name, query=query
            )
        else:
            if not settings.elevenlabs_api_key:
                self._voice_library_status_var.set("Add ELEVENLABS_API_KEY in Setup first.")
                return
            worker = lambda: fetch_elevenlabs_my_voices(settings.elevenlabs_api_key or "", query=query)

        self._voice_library_run_async("Loading voices...", worker, self._populate_voice_library_results)

    def _populate_voice_library_results(self, items: list[VoiceLibraryItem]) -> None:
        tree = self._voice_library_tree
        if tree is None or not tree.winfo_exists():
            return
        for iid in tree.get_children():
            tree.delete(iid)
        self._voice_library_results = list(items)
        self._voice_library_result_by_iid.clear()
        installed_keys = {path.parent.name for path in installed_piper_models()}
        for index, item in enumerate(items):
            status = "available"
            if item.provider == "Piper" and item.key in installed_keys:
                status = "installed"
            elif item.provider == "ElevenLabs mine":
                status = "in account"
            elif item.provider in {"OpenAI TTS", "Gemini TTS"}:
                status = "built-in"
            accent_gender = " · ".join(bit for bit in (item.accent, item.gender) if bit)
            iid = f"voice_{index}"
            tree.insert(
                "",
                "end",
                iid=iid,
                values=(item.name, " · ".join(bit for bit in (item.language, item.locale) if bit), accent_gender, item.quality, status),
            )
            self._voice_library_result_by_iid[iid] = item
        self._voice_library_status_var.set(f"Found {len(items)} voice(s). Select one to preview, add or use.")

    def _preview_selected_library_voice(self) -> None:
        item = self._voice_library_selected_item()
        if item is None:
            self._voice_library_status_var.set("Select a voice first.")
            return
        settings = get_settings()

        preview_text = self._speech_preview_text_var.get().strip() or TTS_SAMPLE_TEXTS.get(
            self._current_tts_default_language(), TTS_SAMPLE_TEXTS["English"]
        )
        preview_language = self._current_tts_default_language()

        def worker() -> Path:
            if item.provider in {"OpenAI TTS", "Gemini TTS"}:
                if not self._speech_service or item.provider not in self._speech_service.providers:
                    key_name = "OPENAI_API_KEY" if item.provider == "OpenAI TTS" else "GEMINI_API_KEY"
                    raise ValueError(f"Add {key_name} in Setup and reload providers to preview this voice.")
                provider = self._speech_service.providers[item.provider]
                result = self._speech_service.generate(
                    item.provider,
                    preview_text,
                    preview_language,
                    provider.default_model,
                    item.voice_id or item.key,
                )
                return result.path

            preview_url = item.preview_url
            if not preview_url and item.voice_id and settings.elevenlabs_api_key:
                preview_url = fetch_elevenlabs_voice_preview(settings.elevenlabs_api_key, item.voice_id)
            suffix = ".mp3"
            preview_dir = Path(settings.audio_cache_dir) / "voice_previews"
            safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", item.key or item.name)
            destination = preview_dir / f"{safe_key}{suffix}"
            if not destination.exists() or destination.stat().st_size == 0:
                download_preview_audio(preview_url, destination)
            return destination

        def success(path: Path) -> None:
            self._voice_library_status_var.set(f"Previewing {item.name} inside the app.")
            self._play_audio_in_app(path, context=f"Voice Library · {item.name}")

        self._voice_library_run_async(f"Loading preview for {item.name}...", worker, success)

    def _add_selected_library_voice(self) -> None:
        item = self._voice_library_selected_item()
        if item is None:
            self._voice_library_status_var.set("Select a voice first.")
            return
        settings = get_settings()

        if item.provider == "Piper":
            def worker() -> Path:
                return download_piper_voice(item)

            def success(path: Path) -> None:
                self._voice_library_status_var.set(f"Installed Piper voice: {item.name}. Reloading audio providers...")
                self._reload_provider_configuration()
                self._select_piper_voice_path(path)
                self._search_voice_library()

            self._voice_library_run_async(f"Downloading {item.name}...", worker, success)
            return

        if item.provider in {"OpenAI TTS", "Gemini TTS"}:
            self._voice_library_status_var.set(f"{item.name} is a built-in cloud voice; nothing needs to be downloaded.")
            self._use_selected_library_voice()
            return

        if item.provider == "ElevenLabs mine":
            self._register_elevenlabs_runtime_voice(item, item.voice_id)
            self._voice_library_status_var.set(f"{item.name} is already in your ElevenLabs account.")
            self._use_selected_library_voice()
            return

        if not settings.elevenlabs_api_key:
            self._voice_library_status_var.set("Add ELEVENLABS_API_KEY in Setup first.")
            return

        def worker() -> str:
            return add_elevenlabs_shared_voice(settings.elevenlabs_api_key or "", item)

        def success(voice_id: str) -> None:
            self._register_elevenlabs_runtime_voice(item, voice_id)
            self._voice_library_status_var.set(f"Added {item.name} to ElevenLabs My Voices and selected it.")
            self._set_elevenlabs_voice_selected(item.name, voice_id, item.language or item.locale)

        self._voice_library_run_async(f"Adding {item.name} to ElevenLabs...", worker, success)

    def _register_elevenlabs_runtime_voice(self, item: VoiceLibraryItem, voice_id: str) -> None:
        label = f"ElevenLabs · {item.name}"
        self._register_runtime_voice("ElevenLabs", label, voice_id, item.language or item.locale)

    def _set_elevenlabs_voice_selected(self, name: str, voice_id: str, language: str = "") -> None:
        label = f"ElevenLabs · {name}"
        self._register_runtime_voice("ElevenLabs", label, voice_id, language)
        save_elevenlabs_registry_voice(label, voice_id, language)
        if self._speech_service and "ElevenLabs" in self._speech_service.providers:
            self._tts_provider_var.set("ElevenLabs")
            self._sync_tts_defaults()
            self._tts_voice_var.set(label)
            self._conversation_tts_provider_var.set("ElevenLabs")
            self._sync_conversation_tts_defaults(preserve_voice=False)
            self._conversation_tts_voice_var.set(label)

    def _use_selected_library_voice(self) -> None:
        item = self._voice_library_selected_item()
        if item is None:
            self._voice_library_status_var.set("Select a voice first.")
            return
        if item.provider == "Piper":
            candidates = [path for path in installed_piper_models() if path.parent.name == item.key or path.stem == Path(item.model_filename).stem]
            if not candidates:
                self._voice_library_status_var.set("Download this Piper voice first, then choose Use selected.")
                return
            self._select_piper_voice_path(candidates[0])
            self._voice_library_status_var.set(f"Selected Piper voice: {item.name}.")
            return
        if item.provider in {"OpenAI TTS", "Gemini TTS"}:
            if not self._speech_service or item.provider not in self._speech_service.providers:
                key_name = "OPENAI_API_KEY" if item.provider == "OpenAI TTS" else "GEMINI_API_KEY"
                self._voice_library_status_var.set(f"Add {key_name} in Setup and reload providers before using this voice.")
                return
            self._register_runtime_voice(item.provider, item.name, item.voice_id or item.key, "Multilingual")
            self._tts_provider_var.set(item.provider)
            self._sync_tts_defaults()
            self._tts_voice_var.set(item.name)
            self._conversation_tts_provider_var.set(item.provider)
            self._sync_conversation_tts_defaults(preserve_voice=False)
            self._conversation_tts_voice_var.set(item.name)
            self._voice_library_status_var.set(f"Selected {item.name} for Voice Lab and Conversation.")
            return

        self._register_elevenlabs_runtime_voice(item, item.voice_id)
        self._set_elevenlabs_voice_selected(item.name, item.voice_id, item.language or item.locale)
        self._voice_library_status_var.set(f"Selected ElevenLabs voice: {item.name}.")

    def _select_piper_voice_path(self, path: Path) -> None:
        if not self._speech_service:
            return
        provider_name = next((name for name in self._speech_service.providers if name.casefold().startswith("piper")), "")
        if not provider_name:
            return
        meta = piper_voice_metadata(path)
        label = meta.get("label") or path.stem
        self._register_runtime_voice(provider_name, label, str(path), meta.get("language") or meta.get("locale") or "")
        self._tts_provider_var.set(provider_name)
        self._sync_tts_defaults()
        self._tts_voice_var.set(label)
        self._tts_model_var.set(str(path))
        self._conversation_tts_provider_var.set(provider_name)
        self._sync_conversation_tts_defaults(preserve_voice=False)
        self._conversation_tts_voice_var.set(label)

    def _add_local_piper_voice(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self._voice_library_window or self._root,
            title="Choose Piper .onnx voice",
            filetypes=[("Piper voice model", "*.onnx"), ("All files", "*.*")],
        )
        if not selected:
            return
        try:
            path = import_piper_voice(Path(selected))
        except Exception as exc:
            messagebox.showerror("Add Piper voice", str(exc), parent=self._voice_library_window or self._root)
            return
        self._voice_library_status_var.set(f"Imported {path.name}. Reloading audio providers...")
        self._reload_provider_configuration()
        self._select_piper_voice_path(path)
        self._search_voice_library()

    def _open_piper_voice_folder(self) -> None:
        folder = piper_voice_directory()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(folder.resolve()))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder.resolve())])
            else:
                subprocess.Popen(["xdg-open", str(folder.resolve())])
        except Exception as exc:
            messagebox.showerror("Open Piper folder", str(exc), parent=self._voice_library_window or self._root)

    def _sync_tts_defaults(self) -> None:
        self._sync_speech_preview_text()
        if not self._speech_service or not self._tts_provider_var.get():
            self._tts_model_var.set("")
            self._tts_voice_var.set("")
            return

        provider_name = self._tts_provider_var.get()
        provider = self._speech_service.providers[provider_name]
        self._tts_model_box.configure(values=provider.models) if hasattr(self, "_tts_model_box") else None

        voice_labels = self._voice_options_for_provider(provider_name, self._current_tts_default_language())

        self._tts_voice_box.configure(values=voice_labels) if hasattr(self, "_tts_voice_box") else None
        self._tts_model_var.set(provider.default_model)

        current_voice = self._tts_voice_var.get().strip()
        if current_voice in voice_labels:
            self._tts_voice_var.set(current_voice)
        elif voice_labels:
            self._tts_voice_var.set(voice_labels[0])
        else:
            self._tts_voice_var.set("")
            if provider_name.casefold().startswith("piper"):
                self._tts_model_var.set("")
                self._speech_progress_var.set(
                    f"No {self._current_tts_default_language()} Piper voice is installed. Open Voice Library to preview and add one."
                )
        if provider_name.casefold().startswith("piper") and self._tts_voice_var.get().strip():
            selected_path = self._resolve_runtime_voice(provider_name, self._tts_voice_var.get().strip())
            if selected_path:
                self._tts_model_var.set(selected_path)
        if provider_name == "ElevenLabs":
            self._speech_progress_var.set(
                "ElevenLabs is optional/premium. Presets are not guaranteed; use Preview voice or switch to OpenAI/Gemini/Piper."
            )

    def _selected_tts_voice(self) -> str:
        """Return the provider-specific voice ID/name selected in the GUI."""
        provider_name = self._tts_provider_var.get()
        selected = self._tts_voice_var.get()
        runtime = self._resolve_runtime_voice(provider_name, selected)
        if runtime:
            return runtime
        runtime = self._resolve_runtime_voice(provider_name, selected)
        if runtime:
            return runtime
        try:
            return get_voice_by_label(provider_name, selected)
        except ValueError:
            return selected

    @staticmethod
    def _piper_voice_missing(provider_name: str, voice_label: str) -> bool:
        return provider_name.casefold().startswith("piper") and not voice_label.strip()

    def _test_tts_provider(self, *, preflight: bool = False) -> bool:
        """Run a tiny shared TTS diagnostic before preview/queue work."""
        if not self._speech_service or not self._tts_provider_var.get():
            message = "Audio provider diagnostics failed: no audio provider is configured."
            self._speech_progress_var.set(message)
            if not preflight:
                messagebox.showerror("Audio provider unavailable", message)
            return False

        provider_name = self._tts_provider_var.get()
        model_name = self._tts_model_var.get()
        voice_label = self._tts_voice_var.get()
        if self._piper_voice_missing(provider_name, voice_label):
            message = (
                f"No {self._current_tts_default_language()} Piper voice is installed. "
                "Open Voice Library and add a matching local voice first."
            )
            self._speech_progress_var.set(message)
            if not preflight:
                messagebox.showerror("Piper voice unavailable", message)
            return False
        voice_value = self._selected_tts_voice()
        self._speech_progress_var.set("Testing audio provider...")
        self._root.update_idletasks()
        diagnostic = self._speech_service.diagnose_provider(
            provider_name,
            self._current_tts_default_language(),
            model_name,
            voice_value,
        )

        message = ("Audio provider diagnostics OK: " if diagnostic.ok else "Audio provider diagnostics failed: ") + diagnostic.to_message()
        if not diagnostic.ok:
            status = self._http_status_label(self._http_status_from_exception(Exception(diagnostic.error_message)))
            friendly = self._friendly_tts_error_message(Exception(diagnostic.error_message))
            if status:
                message += f" · HTTP: {status}"
            if friendly and friendly not in message:
                message += f" · {friendly}"
            if diagnostic.provider_name == "ElevenLabs":
                message += " · Action: check ELEVENLABS_API_KEY, verify the selected voice/model, or switch provider."
            self._speech_progress_var.set(message)
            if not preflight:
                self._record_activity(message)
                messagebox.showerror("Audio provider diagnostics", message)
            return False

        self._speech_progress_var.set(message)
        if not preflight:
            self._record_activity(message)
        return True

    def _generate_single_audio(self) -> None:
        if self._generated_card is None:
            messagebox.showerror("No card", "Generate a vocabulary card first.")
            return
        provider_name = self._single_tts_provider_var.get().strip()
        if provider_name == "Off":
            messagebox.showinfo("Audio disabled", "Select a TTS provider before generating audio.")
            return
        if not self._speech_service or provider_name not in self._speech_service.providers:
            messagebox.showerror("Audio provider unavailable", "Configure at least one audio provider, e.g. Piper Local.")
            return
        self._tts_provider_var.set(provider_name)
        self._sync_tts_defaults()
        if self._piper_voice_missing(provider_name, self._tts_voice_var.get()):
            messagebox.showerror(
                "Piper voice unavailable",
                f"No {self._current_tts_default_language()} Piper voice is installed. Open Speech & Audio → Voice Library and add one first.",
            )
            return
        self._status_var.set(f"Generating example audio with {provider_name}...")
        self._root.update_idletasks()
        try:
            self._generated_audio = self._speech_service.generate(
                provider_name,
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
            friendly = self._friendly_tts_error_message(exc)
            message = f"Audio generation failed: {friendly}"
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
        self._play_audio_in_app(self._generated_audio.path, context="Example audio")

    def _play_audio_in_app(self, path: Path, context: str = "Audio") -> bool:
        """Play preview audio inside the app instead of opening an OS player."""
        try:
            self._speech_preview_player.play(Path(path))
        except Exception as exc:
            LOGGER.exception("In-app audio preview failed: %s", path)
            message = f"{context} could not be played in the app: {exc}"
            self._speech_progress_var.set(message)
            messagebox.showerror("Audio playback", message)
            return False
        self._speech_progress_var.set(f"{context} playing in app: {Path(path).name}")
        return True

    def _stop_speech_preview(self) -> None:
        self._speech_preview_player.stop()
        self._speech_progress_var.set("Voice preview stopped.")

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
            messagebox.showerror("Audio provider unavailable", "Configure at least one audio provider.")
            return

        language = self._current_tts_default_language()
        sample_text = self._speech_preview_text_var.get().strip() or TTS_SAMPLE_TEXTS.get(
            language, TTS_SAMPLE_TEXTS["English"]
        )
        provider_name = self._tts_provider_var.get()
        model_name = self._tts_model_var.get()
        voice_label = self._tts_voice_var.get()
        if self._piper_voice_missing(provider_name, voice_label):
            message = (
                f"No {language} Piper voice is installed. Open Voice Library and add a matching voice first."
            )
            self._speech_progress_var.set(message)
            messagebox.showerror("Piper voice unavailable", message)
            return
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
        self._play_audio_in_app(result.path, context=f"Voice preview · {voice_label}")

    def _set_audio_batch_controls_state(self, running: bool) -> None:
        """Enable Pause/Stop only while a long audio queue is running."""
        for name, state in (
            ("_pause_audio_button", "normal" if running else "disabled"),
            ("_stop_audio_button", "normal" if running else "disabled"),
        ):
            button = getattr(self, name, None)
            if button is not None:
                button.configure(state=state)

    def _speech_source_text_for_note(self, note: dict[str, object]) -> tuple[str, str]:
        """Return source text and source field name for TTS generation.

        Auto mode must not create a hidden mismatch where the learner sees one
        complete grammar sentence on the card but hears a different natural
        context sentence. For grammar notes, if the visible Sentence/Word field
        already looks like a full sentence, that visible sentence wins. Natural
        Context is still preferred when the visible field is only a target,
        connector, phrase, or structure.
        """
        fields = note.get("fields") if isinstance(note.get("fields"), dict) else {}
        selected = self._speech_source_field_var.get().strip()
        if selected and not selected.startswith("Auto"):
            return self._plain_text(str(fields.get(selected, ""))), selected

        model_name = str(note.get("model") or "").casefold()
        is_grammar_note = "grammar" in model_name

        # For grammar cards whose visible front is already a sentence, audio
        # should read that same visible sentence. Otherwise users read one
        # sentence and hear another.
        if is_grammar_note:
            for visible_field in ("Sentence", "Word", "Front"):
                if visible_field in fields:
                    visible_text = self._plain_text(str(fields.get(visible_field, "")))
                    if visible_text and self._looks_like_complete_sentence(visible_text):
                        return visible_text, visible_field

        # For word/phrase/connector cards, Natural Context is usually the best
        # audio source because the visible field may only be the target.
        for field_name in ("ContextExample", "Example", "ExampleSentence", "Sentence", "Back", "Word", "Front", "Phrase", "Term"):
            if field_name in fields:
                value = self._plain_text(str(fields.get(field_name, "")))
                if value:
                    return value, field_name
        return str(note.get("example") or note.get("word") or "").strip(), "auto"

    def _speech_target_field_for_note(self, note: dict[str, object]) -> str:
        """Return the writable field where [sound:...] should be placed."""
        fields = note.get("fields") if isinstance(note.get("fields"), dict) else {}
        target = self._speech_target_field_var.get().strip()
        if self._speech_write_mode_var.get() == "Append [sound] to existing field":
            return target if target in fields else ""
        if target and target in fields:
            return target
        audio_field = str(note.get("audio_field") or "").strip()
        return audio_field if audio_field in fields else ""

    def _field_has_audio(self, note: dict[str, object], field_name: str) -> bool:
        fields = note.get("fields") if isinstance(note.get("fields"), dict) else {}
        return "[sound:" in str(fields.get(field_name, "")).casefold()

    def _speech_note_readiness(self, note: dict[str, object]) -> tuple[bool, str, str, str, str]:
        """Return readiness tuple for UI and queue selection.

        Returns:
            can_generate, status, detail, source_text, target_field
        """
        note_id = int(note["note_id"])
        current_status = self._speech_audio_status_by_note_id.get(
            note_id, str(note.get("audio_status") or "missing_audio")
        )
        if current_status in {"audio_ready", "updated_in_anki", "provider_failed", "audio_error"}:
            return False, current_status, self._speech_audio_error_by_note_id.get(note_id, ""), "", ""
        source_text, source_field = self._speech_source_text_for_note(note)
        target_field = self._speech_target_field_for_note(note)
        write_mode = self._speech_write_mode_var.get()
        if not source_text:
            return False, "needs_source_text", "Choose a source text field that contains text.", "", target_field
        if not target_field:
            if write_mode == "Append [sound] to existing field":
                return False, "needs_append_target_field", "Target field does not exist on this note type.", source_text, ""
            return False, "needs_audio_field", "This note type has no selected Audio/ExampleAudio field.", source_text, ""
        if self._field_has_audio(note, target_field) or str(note.get("audio_status")) == "has_audio":
            return False, "has_audio", f"{target_field} already contains [sound:...].", source_text, target_field
        return True, "ready_for_audio", f"Source: {source_field} → Target: {target_field}", source_text, target_field

    def _deselect_speech_notes(self) -> None:
        """Uncheck visible audio rows without clearing scan results."""
        for var in self._speech_note_vars:
            var.set(False)
        self._speech_progress_var.set("Deselected all audio rows. Scan results kept.")

    def _clear_speech_results(self) -> None:
        """Clear the current audio scan result list."""
        self._speech_notes = []
        self._speech_note_vars = []
        self._speech_audio_status_by_note_id = {}
        self._speech_audio_error_by_note_id = {}
        self._speech_audio_path_by_note_id = {}
        self._speech_scan_loaded = False
        self._speech_summary_var.set("No audio scan loaded yet.")
        self._render_speech_notes("Audio results cleared. Click Find missing audio to scan again.")

    def _select_ready_speech_notes(self) -> None:
        for note, var in zip(self._speech_notes, self._speech_note_vars):
            can_generate, *_ = self._speech_note_readiness(note)
            var.set(can_generate)
        self._render_speech_notes("Selected only cards that are ready for audio generation.")

    def _speech_scan_summary(self, notes: list[dict[str, object]] | None = None) -> str:
        scan_notes = self._speech_notes if notes is None else notes
        counts = {
            "ready_for_audio": 0,
            "has_audio": 0,
            "needs_audio_field": 0,
            "needs_append_target_field": 0,
            "needs_source_text": 0,
            "malformed_audio": 0,
            "audio_error": 0,
            "provider_failed": 0,
        }
        for note in scan_notes:
            can_generate, status, *_ = self._speech_note_readiness(note)
            key = "ready_for_audio" if can_generate else status
            counts[key] = counts.get(key, 0) + 1

        total = len(scan_notes)
        with_audio = counts.get("has_audio", 0)
        missing = max(0, total - with_audio)
        coverage = (100.0 * with_audio / total) if total else 100.0
        blocked_target = counts.get("needs_audio_field", 0) + counts.get("needs_append_target_field", 0)
        return (
            f"Audio coverage: {with_audio}/{total} ({coverage:.1f}%) have audio · "
            f"{missing} need attention: "
            f"{counts.get('ready_for_audio', 0)} ready to generate, "
            f"{blocked_target} need a target audio field, "
            f"{counts.get('needs_source_text', 0)} need source text, "
            f"{counts.get('malformed_audio', 0)} malformed."
        )

    @classmethod
    def _speech_note_language_matches(cls, note_language: object, requested_language: str) -> bool:
        """Match explicit Anki note language to the active learning language.

        Global all-deck scans intentionally exclude notes with no Language value
        so TTS never guesses across mixed-language collections.
        """
        candidate = str(note_language or "").strip()
        requested = str(requested_language or "").strip()
        if not candidate or not requested:
            return False
        return cls._voice_language_matches(candidate, requested)

    def _load_speech_notes(self, include_all_decks: bool = False) -> None:
        """Load missing/malformed audio from one deck or the whole Anki collection."""
        try:
            if not include_all_decks:
                self._set_speech_selected_deck()
            # Make sure grammar note types created by Queue Grammar expose Audio/ExampleAudio
            # before the broad missing-audio scan runs. This is idempotent.
            try:
                self._anki_client.ensure_grammar_model_exists()
            except Exception:
                LOGGER.info("Grammar model audio-field refresh skipped during audio scan", exc_info=True)
            all_notes = self._anki_client.list_existing_notes(
                search_query=self._speech_search_var.get().strip(),
                missing_audio_only=False,
                include_all_decks=include_all_decks,
            )
            requested_language = self._current_speech_language()
            if include_all_decks:
                all_notes = [
                    note
                    for note in all_notes
                    if self._speech_note_language_matches(note.get("language"), requested_language)
                ]
        except Exception as exc:
            LOGGER.exception("Speech/audio missing-audio scan failed")
            messagebox.showerror("Anki error", str(exc))
            return
        self._speech_audio_status_by_note_id = {}
        self._speech_audio_error_by_note_id = {}
        self._speech_audio_path_by_note_id = {}
        for note in all_notes:
            note_id = int(note["note_id"])
            self._speech_audio_status_by_note_id[note_id] = str(note.get("audio_status") or "missing_audio")

        scan_summary = self._speech_scan_summary(all_notes)
        # Keep the work list focused: coverage counts all supported notes, while
        # the rows below show only notes that still need audio-related attention.
        self._speech_notes = []
        for note in all_notes:
            _can_generate, status, *_ = self._speech_note_readiness(note)
            if status != "has_audio":
                self._speech_notes.append(note)

        self._speech_scan_loaded = True
        extra = self._speech_search_var.get().strip()
        scope = (
            f" · scope: all decks · language: {self._current_speech_language()}"
            if include_all_decks
            else f" · deck: {self._speech_deck_var.get().strip()}"
        )
        suffix = f" · filter: {extra}" if extra else ""
        scan_summary = f"{scan_summary}{scope}{suffix}"
        self._speech_summary_var.set(scan_summary)
        self._render_speech_notes(scan_summary)

    def _render_speech_notes(self, progress_message: str | None = None) -> None:
        """Render the current existing-card audio list without reloading from Anki."""
        for widget in self._speech_scroll.winfo_children():
            widget.destroy()
        self._speech_note_vars = []
        if not self._speech_notes:
            empty_text = (
                "✓ All supported cards in this scan have audio."
                if self._speech_scan_loaded
                else "No audio scan results. Click Find missing audio to load cards from the selected deck."
            )
            ctk.CTkLabel(
                self._speech_scroll,
                text=empty_text,
                text_color=("gray35", "gray75"),
            ).grid(row=0, column=0, sticky="w", padx=12, pady=12)
        for index, note in enumerate(self._speech_notes):
            note_id = int(note["note_id"])
            self._speech_audio_status_by_note_id.setdefault(
                note_id, str(note.get("audio_status") or "missing_audio")
            )
            can_generate, status, detail, source_text, target_field = self._speech_note_readiness(note)
            var = ctk.BooleanVar(value=can_generate)
            self._speech_note_vars.append(var)
            word = str(note.get("word") or "—")
            model = str(note.get("model") or "unknown model")
            source_preview = source_text[:90] + ("..." if len(source_text) > 90 else "")
            if status == "ready_for_audio":
                label = f"[ready] {word} · {model} · {detail} — {source_preview}"
            elif status == "needs_audio_field":
                label = f"[needs audio field] {word} · {model} · choose a target Audio field or Append mode"
            elif status == "needs_append_target_field":
                label = f"[target field missing] {word} · {model} · target '{self._speech_target_field_var.get()}' does not exist"
            elif status == "needs_source_text":
                label = f"[needs source text] {word} · {model} · choose Front/Back/Example/Word as source"
            elif status == "has_audio":
                label = f"[has audio] {word} · {model} · {detail}"
            else:
                error = self._speech_audio_error_by_note_id.get(note_id, "")
                label = f"[{status}] {word} · {model} · {error or detail}"
            checkbox = ctk.CTkCheckBox(self._speech_scroll, text=label, variable=var)
            # Keep completed/skipped rows readable on dark theme. Disabled CTk text can
            # become almost invisible, so use explicit disabled contrast.
            try:
                checkbox.configure(
                    text_color_disabled=("gray35", "gray72"),
                    text_color=("gray10", "gray92") if can_generate else ("gray30", "gray75"),
                )
            except Exception:
                pass
            if not can_generate:
                checkbox.configure(state="disabled")
            checkbox.grid(row=index, column=0, sticky="w", padx=12, pady=6)
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
                    "audio_field": note.get("_target_audio_field") or note.get("audio_field", "Audio"),
                    "source_text": note.get("_source_text") or note.get("example", ""),
                    "write_mode": note.get("_write_mode") or self._speech_audio_write_mode,
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
        started_at = time.perf_counter()
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
        finally:
            LOGGER.info(
                "PERF audio_autosave reason=%r seconds=%.3f notes=%s",
                reason,
                max(0.0, time.perf_counter() - started_at),
                len(getattr(self, "_speech_notes", [])),
            )

    def _pause_existing_audio_batch(self) -> None:
        if not self._speech_audio_running:
            self._speech_progress_var.set("No audio queue is currently running.")
            return
        self._speech_audio_pause_requested.set()
        self._autosave_audio_progress("audio paused")
        message = f"Audio paused. Progress saved: {self._speech_audio_autosave_path}"
        self._speech_progress_var.set(message)
        self._record_activity(message)

    def _stop_existing_audio_batch(self) -> None:
        if not self._speech_audio_running:
            self._speech_progress_var.set("No audio queue is currently running.")
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
        selected_raw = [
            note for note, var in zip(self._speech_notes, self._speech_note_vars) if var.get()
        ]
        if not selected_raw:
            messagebox.showwarning("No cards selected", "Select at least one ready card.")
            return
        selected: list[dict[str, object]] = []
        blocked: list[str] = []
        for note in selected_raw:
            can_generate, status, detail, source_text, target_field = self._speech_note_readiness(note)
            if not can_generate:
                blocked.append(f"{note.get('word', '—')}: {status}")
                continue
            prepared = dict(note)
            prepared["_source_text"] = source_text
            prepared["_target_audio_field"] = target_field
            prepared["_write_mode"] = self._speech_write_mode_var.get()
            selected.append(prepared)
        if not selected:
            message = "No selected cards are ready for audio. " + self._speech_scan_summary()
            self._speech_progress_var.set(message)
            messagebox.showwarning("No ready cards", message)
            return
        if blocked:
            self._speech_progress_var.set(
                f"Generating {len(selected)} ready card(s). Skipping {len(blocked)} not-ready selection(s)."
            )
        if not self._speech_service or not self._tts_provider_var.get():
            messagebox.showerror("Audio provider unavailable", "Configure at least one audio provider.")
            return
        provider_name = self._tts_provider_var.get()
        model_name = self._tts_model_var.get()
        voice_label = self._tts_voice_var.get()
        voice_value = self._selected_tts_voice()
        self._speech_audio_write_mode = self._speech_write_mode_var.get()
        if not self._test_tts_provider(preflight=True):
            message = "Audio queue not started because audio provider diagnostics failed. Fix the provider/key/voice or switch provider."
            self._speech_progress_var.set(message)
            self._record_activity(message)
            return
        self._speech_audio_stop_requested.clear()
        self._speech_audio_pause_requested.clear()
        self._speech_audio_running = True
        self._set_audio_batch_controls_state(True)
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
            return "Audio provider 401 Unauthorized. Check the API key or switch provider."
        if status == 402:
            return "Audio provider 402 payment/credits problem. Use a verified voice or switch provider."
        if status == 403:
            return "Audio provider 403 forbidden. The selected voice/model may not be allowed. Switch voice/provider."
        if status == 400:
            return "Audio provider 400 bad request. Check text/model/voice; this item was not retried automatically."
        if status == 404:
            return "Audio provider 404 not found. Check the configured model/voice or switch provider."
        if status == 422:
            return "Audio provider 422 could not process this item. Edit the input or switch provider."
        if status == 429:
            return "Audio provider rate limit. Wait before retrying or switch provider."
        if status is not None and 500 <= status <= 599:
            return "Audio provider server error. Progress was saved; retry later or switch provider."
        detail = str(exc)
        if "Piper executable not found" in detail:
            return "Piper is not configured correctly. Check PIPER_EXE_PATH in .env."
        if "Piper voice model not found" in detail or "Configure at least one Piper voice" in detail:
            return "Piper voice is not configured. Download a voice in Voice Library or configure a PIPER_VOICE_* path in .env."
        if "Piper failed" in detail:
            return "Piper failed to generate audio. Check that piper.exe and the selected .onnx voice work from PowerShell."
        if ModernVocabularyGui._is_timeout_detail(detail):
            return "Audio provider timed out. Progress was saved; retry later or switch provider."
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
        perf_run_started_at = time.perf_counter()
        perf_tts_s = 0.0
        perf_media_s = 0.0
        perf_anki_update_s = 0.0
        perf_items = 0

        def publish_progress(message: str) -> None:
            # Updating progress must stay O(1). Re-rendering the whole Speech &
            # Audio checklist here rebuilt hundreds of CTk widgets after every
            # card and dominated long audio runs.
            self._root.after(0, self._speech_progress_var.set, message)

        stopped = False
        stop_message = ""
        failed_index = None
        stop_status = ""
        pending_writes: list[dict[str, object]] = []

        def apply_success(entry: dict[str, object], media_name: str) -> None:
            nonlocal completed
            note = entry["note"]
            assert isinstance(note, dict)
            note_id = int(entry["note_id"])
            audio_field = str(entry["audio_field"])
            write_mode = str(entry["write_mode"])
            known_fields = entry["known_fields"]
            assert isinstance(known_fields, dict)

            self._speech_audio_status_by_note_id[note_id] = "updated_in_anki"
            fields = known_fields
            if write_mode == "Append [sound] to existing field" and audio_field in fields:
                fields[audio_field] = (
                    f"{fields.get(audio_field, '')}<br>[sound:{media_name}]"
                    if fields.get(audio_field)
                    else f"[sound:{media_name}]"
                )
            elif audio_field in fields:
                fields[audio_field] = f"[sound:{media_name}]"
            note["fields"] = fields
            note["audio_field"] = audio_field
            note["audio_status"] = "has_audio"
            completed += 1

        def flush_pending() -> None:
            nonlocal errors, perf_media_s, perf_anki_update_s
            if not pending_writes:
                return

            batch = list(pending_writes)
            pending_writes.clear()
            anki_started_at = time.perf_counter()
            try:
                media_names = self._anki_client.store_and_attach_audio_batch(
                    [
                        {
                            "path": entry["path"],
                            "note_id": entry["note_id"],
                            "field_name": entry["audio_field"],
                            "audio_metadata": entry["audio_metadata"],
                            "existing_fields": entry["known_fields"],
                            "append": entry["write_mode"] == "Append [sound] to existing field",
                        }
                        for entry in batch
                    ]
                )
                anki_s = max(0.0, time.perf_counter() - anki_started_at)
                perf_anki_update_s += anki_s
                LOGGER.info(
                    "PERF audio_anki_batch size=%s seconds=%.3f mode=multi",
                    len(batch),
                    anki_s,
                )
                for entry, media_name in zip(batch, media_names):
                    apply_success(entry, media_name)
            except Exception:
                # One malformed legacy note must not poison the whole audio run.
                # Fall back only for this batch; normal batches keep the two-call
                # AnkiConnect multi fast path.
                LOGGER.exception(
                    "Audio Anki multi batch failed; falling back to per-note writes: size=%s",
                    len(batch),
                )
                for entry in batch:
                    note_id = int(entry["note_id"])
                    try:
                        media_started_at = time.perf_counter()
                        media_name = self._anki_client.store_media_file(Path(str(entry["path"])))
                        perf_media_s += max(0.0, time.perf_counter() - media_started_at)

                        update_started_at = time.perf_counter()
                        if entry["write_mode"] == "Append [sound] to existing field":
                            self._anki_client.append_audio_to_note(
                                note_id,
                                media_name,
                                str(entry["audio_field"]),
                                audio_metadata=entry["audio_metadata"],
                                existing_fields=entry["known_fields"],
                            )
                        else:
                            self._anki_client.attach_audio_to_note(
                                note_id,
                                media_name,
                                str(entry["audio_field"]),
                                audio_metadata=entry["audio_metadata"],
                                existing_field_names=set(entry["known_fields"]),
                            )
                        perf_anki_update_s += max(0.0, time.perf_counter() - update_started_at)
                        apply_success(entry, media_name)
                    except Exception as exc:
                        errors += 1
                        self._speech_audio_status_by_note_id[note_id] = "audio_error"
                        self._speech_audio_error_by_note_id[note_id] = str(exc)
                        LOGGER.exception(
                            "Audio Anki fallback write failed: note_id=%s",
                            note_id,
                        )

            self._autosave_audio_progress(
                f"audio batch flushed ({len(batch)})",
                provider_name,
                model_name,
                voice_label,
                voice_value,
            )

        try:
            for index, note in enumerate(notes, start=1):
                if self._speech_audio_stop_requested.is_set():
                    flush_pending()
                    stopped = True
                    failed_index = index
                    stop_message = "User stopped audio queue."
                    break

                if self._speech_audio_pause_requested.is_set():
                    flush_pending()
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
                        stop_message = "User stopped audio queue."
                        break
                    time.sleep(0.25)
                if stopped:
                    break

                note_id = int(note["note_id"])
                current_status = self._speech_audio_status_by_note_id.get(note_id, "pending_audio")
                audio_field = str(note.get("_target_audio_field") or note.get("audio_field") or "").strip()
                source_text = str(note.get("_source_text") or note.get("example") or note.get("word") or "").strip()
                write_mode = str(note.get("_write_mode") or "Use dedicated audio field")

                if current_status in {"updated_in_anki", "has_audio"}:
                    skipped_done += 1
                    publish_progress(
                        f"Skipping already generated {index}/{len(notes)} · Updated {completed} · Skipped {skipped_done} · Failed {errors}"
                    )
                    continue
                if not audio_field or not source_text:
                    skipped_done += 1
                    self._speech_audio_status_by_note_id[note_id] = "skipped"
                    self._speech_audio_error_by_note_id[note_id] = (
                        "Missing target audio field." if not audio_field else "Missing source text for TTS."
                    )
                    continue

                self._speech_audio_status_by_note_id[note_id] = "pending_audio"
                item_started_at = time.perf_counter()
                tts_s = 0.0
                cached: bool | None = None
                try:
                    tts_started_at = time.perf_counter()
                    try:
                        result = self._speech_service.generate(
                            provider_name,
                            source_text,
                            str(note.get("language") or self._current_speech_language()),
                            model_name,
                            voice_value,
                        )
                    finally:
                        tts_s = max(0.0, time.perf_counter() - tts_started_at)

                    cached = result.cached
                    self._speech_audio_status_by_note_id[note_id] = "audio_ready"
                    self._speech_audio_path_by_note_id[note_id] = str(result.path)
                    known_fields = note.get("fields") if isinstance(note.get("fields"), dict) else {}
                    pending_writes.append(
                        {
                            "index": index,
                            "note": note,
                            "note_id": note_id,
                            "path": result.path,
                            "audio_field": audio_field,
                            "write_mode": write_mode,
                            "known_fields": known_fields,
                            "audio_metadata": self._audio_metadata_from_tts_result(
                                result,
                                source_text,
                                voice_label,
                            ),
                        }
                    )
                    LOGGER.info(
                        "Existing-card TTS ready: note_id=%s word=%s path=%s cached=%s provider=%s model=%s",
                        note_id,
                        note.get("word"),
                        result.path,
                        result.cached,
                        provider_name,
                        model_name,
                    )
                    if len(pending_writes) >= AUDIO_ANKI_BATCH_SIZE:
                        flush_pending()
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
                        "Existing-card audio generation failed: note_id=%s word=%s fatal=%s error=%s",
                        note_id,
                        note.get("word"),
                        self._is_fatal_tts_error(exc),
                        exc,
                    )
                    if self._is_fatal_tts_error(exc):
                        flush_pending()
                        stopped = True
                        break
                finally:
                    perf_items += 1
                    perf_tts_s += tts_s
                    LOGGER.info(
                        "PERF audio_item index=%s/%s note_id=%s status=%s cached=%s "
                        "tts_s=%.3f total_s=%.3f chars=%s word=%r",
                        index,
                        len(notes),
                        note_id,
                        self._speech_audio_status_by_note_id.get(note_id, "unknown"),
                        cached,
                        tts_s,
                        max(0.0, time.perf_counter() - item_started_at),
                        len(source_text),
                        note.get("word"),
                    )

                publish_progress(
                    f"Generating {index}/{len(notes)} · Updated {completed} · Buffered {len(pending_writes)} · Skipped {skipped_done} · Failed {errors}"
                )

            flush_pending()
            self._autosave_audio_progress(
                "audio queue finished" if not stopped else "audio queue stopped",
                provider_name,
                model_name,
                voice_label,
                voice_value,
            )
            LOGGER.info(
                "PERF audio_summary outcome=%s selected=%s processed=%s updated=%s skipped=%s failed=%s "
                "total_s=%.3f tts_s=%.3f media_s=%.3f anki_update_s=%.3f",
                "stopped" if stopped else "finished",
                len(notes),
                perf_items,
                completed,
                skipped_done,
                errors,
                max(0.0, time.perf_counter() - perf_run_started_at),
                perf_tts_s,
                perf_media_s,
                perf_anki_update_s,
            )

            if stopped:
                if stop_message == "User stopped audio queue.":
                    final_message = (
                        f"Audio stopped by user at item {failed_index}. Progress saved. "
                        f"Summary: {completed} updated, {errors} failed, {skipped_done} skipped."
                    )
                else:
                    final_message = (
                        f"Audio stopped. Provider: {provider_name}. Error: {stop_status or 'provider error'}. "
                        f"Stopped at: {failed_index}/{len(notes)}. Updated: {completed}. Failed: {errors}. "
                        f"Skipped: {skipped_done}. Progress saved. {stop_message}"
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
            self._root.after(0, self._set_audio_batch_controls_state, False)

    def _analyze_grammar_sentence(self) -> None:
        """Generate and preview a target-first grammar analysis from one sentence."""
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
                explanation_language=self._explanation_language_var.get(),
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
        target = (analysis.target or analysis.structure or "Grammar").strip()
        support = (analysis.explanation_language or analysis.target_language).strip()
        validation = "OK"
        if not analysis.target_is_valid or not analysis.example_demonstrates_target:
            validation = analysis.validation_note or "Provider self-check needs review."
        return (
            f"GRAMMAR TARGET\n{target}\n\n"
            f"LANGUAGE\n{analysis.target_language} · explanation: {support}\n\n"
            f"STRUCTURE / PATTERN\n{analysis.structure}\n\n"
            f"MEANING / FUNCTION\n{analysis.meaning}\n\n"
            f"EXAMPLE\n{analysis.sentence}\n\n"
            f"HOW IT WORKS\n- " + "\n- ".join(analysis.breakdown) + "\n\n"
            f"WHEN TO USE IT\n{analysis.usage}\n\n"
            f"CONTRAST\n- " + "\n- ".join(analysis.contrasts) + "\n\n"
            f"COMMON MISTAKES\n- " + "\n- ".join(analysis.common_mistakes) + "\n\n"
            f"AI SELF-CHECK\n{validation}"
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
            grammar_target = (self._generated_grammar.target or self._generated_grammar.structure).strip()
            replace = messagebox.askyesno(
                "Grammar card already exists",
                f"A grammar card for '{grammar_target}' already exists in the Anki collection.\n\n"
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


    def _conversation_ai_client(self) -> VocabularyAiClient:
        """Return the AI client selected for Conversation."""
        provider_name = self._conversation_provider_var.get() or self._provider_var.get()
        try:
            return self._ai_clients[provider_name]
        except KeyError as exc:
            raise ValueError(f"Conversation provider is not configured: {provider_name}") from exc

    def _start_conversation_recording(self) -> None:
        """Start microphone recording for Conversation."""
        self._stop_conversation_audio(silent=True)
        if not self._stt_service:
            messagebox.showerror(
                "Speech input not configured",
                "Speech-to-text is not configured. Choose Local Whisper, Groq Cloud or OpenAI Cloud in Setup.",
            )
            return
        try:
            self._stt_service.start_recording()
        except Exception as exc:
            self._handle_stt_error(exc)
            return
        self._stt_status_var.set("Recording... 00:00")
        self._status_var.set("Recording answer...")
        self._schedule_recording_timer()

    def _schedule_recording_timer(self) -> None:
        """Update the visible recording timer while the microphone is active."""
        if not self._stt_service or not self._stt_service.is_recording:
            self._recording_timer_after_id = None
            return
        seconds = int(self._stt_service.recording_duration_seconds)
        self._stt_status_var.set(f"Recording... {seconds // 60:02d}:{seconds % 60:02d}")
        self._recording_timer_after_id = self._root.after(500, self._schedule_recording_timer)

    def _cancel_recording_timer(self) -> None:
        if self._recording_timer_after_id:
            try:
                self._root.after_cancel(self._recording_timer_after_id)
            except Exception:
                pass
            self._recording_timer_after_id = None

    def _conversation_stt_language_code(self) -> str | None:
        """Return an ISO language code for the selected STT provider."""
        return STT_LANGUAGE_CODES.get(self._conversation_language_var.get().strip())

    def _build_conversation_stt_prompt(self) -> str:
        """Build a short dynamic STT prompt from the active conversation context."""
        language = self._conversation_language_var.get().strip()
        topic = (
            ""
            if self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS
            else self._topic_var.get().strip()
        )
        vocabulary = dedupe_expressions(
            [
                *self._conversation_flashcard_targets[:16],
                *self._conversation_expressions_to_use_next[:6],
            ],
            limit=20,
        )
        recent = self._conversation_history[-4:]
        recent_text = " ".join(message for _speaker, message in recent if message).strip()
        parts = [f"Conversation language: {language}."]
        if topic:
            parts.append(f"Topic: {topic}.")
        if vocabulary:
            parts.append("Expected vocabulary and names: " + ", ".join(vocabulary) + ".")
        if self._conversation_question:
            parts.append(f"Current question: {self._conversation_question}")
        if recent_text:
            parts.append(f"Recent context: {recent_text}")
        prompt = " ".join(parts)
        return prompt[-1200:]

    def _stop_conversation_recording(self) -> None:
        """Stop recording and transcribe the audio in a background thread."""
        if not self._stt_service:
            messagebox.showerror("Speech input not configured", "Choose Local Whisper, Groq Cloud or OpenAI Cloud in Setup.")
            return
        if not self._stt_service.is_recording:
            messagebox.showinfo("Speech input", "No recording is running.")
            return
        self._cancel_recording_timer()
        self._stt_status_var.set("Finishing recording, then transcribing... first run can be slow.")
        self._status_var.set("Finishing recording and transcribing spoken answer...")
        self._root.update_idletasks()

        stt_prompt = self._build_conversation_stt_prompt()
        stt_language = self._conversation_stt_language_code()

        def _worker() -> None:
            try:
                result = self._stt_service.stop_and_transcribe(
                    initial_prompt=stt_prompt,
                    language=stt_language,
                )
            except Exception as exc:
                self._root.after(0, lambda exc=exc: self._handle_stt_error(exc))
                return
            self._root.after(0, lambda: self._insert_stt_transcript(result.text, result.provider, result.model, result.language))

        threading.Thread(target=_worker, daemon=True).start()

    def _handle_stt_error(self, exc: Exception) -> None:
        detail = str(exc) or exc.__class__.__name__
        if "No microphone/input device detected" in detail or "Error querying device -1" in detail:
            message = "No microphone/input device detected. Connect or enable a microphone, then try again."
            self._stt_status_var.set("No microphone detected.")
            self._status_var.set("Speech input unavailable: no microphone detected.")
            messagebox.showerror("No microphone detected", message)
            return
        self._stt_status_var.set("Transcription failed.")
        self._status_var.set("Speech transcription failed.")
        messagebox.showerror("Speech transcription error", detail)

    def _insert_stt_transcript(self, transcript: str, provider: str, model: str, language: str | None) -> None:
        transcript = transcript.strip()
        if not transcript:
            self._stt_status_var.set("No speech detected. Try recording again.")
            self._status_var.set("No speech detected.")
            return
        current = self._message_input.get("1.0", "end").strip()
        if current:
            self._message_input.insert("end", "\n" + transcript)
        else:
            self._message_input.insert("1.0", transcript)
        self._conversation_current_input_from_stt = True
        language_part = f", language: {language}" if language else ""
        audio_hint = " Last recording saved for playback." if self._stt_service and self._stt_service.last_recording_path else ""
        self._stt_status_var.set(
            f"Transcript inserted ({provider} · {model}{language_part}, context-aware). Edit it before sending.{audio_hint}"
        )
        self._status_var.set("Spoken answer transcribed. Play last recording if the transcript looks cut, then review/edit and click Send.")


    def _last_recording_path(self) -> Path | None:
        if not self._stt_service:
            return None
        path = self._stt_service.last_recording_path
        if path and path.exists():
            return path
        return None

    def _play_last_conversation_recording(self) -> None:
        """Play the last recorded WAV inside the app for STT diagnostics."""
        path = self._last_recording_path()
        if not path:
            messagebox.showinfo("No recording", "No saved recording yet. Record and transcribe an answer first.")
            return
        self._play_existing_conversation_audio(path, label="last recording")

    def _open_last_conversation_recording(self) -> None:
        """Open the folder containing the last recorded WAV for diagnostics."""
        path = self._last_recording_path()
        if not path:
            messagebox.showinfo("No recording", "No saved recording yet. Record and transcribe an answer first.")
            return
        folder = path.parent
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(folder)])
        else:
            subprocess.Popen(["xdg-open", str(folder)])
        self._status_var.set(f"Opened last recording location: {path}")

    def _on_conversation_language_changed(self) -> None:
        """Refresh tutor voices when the learner changes the conversation language."""
        self._sync_conversation_tts_defaults(preserve_voice=False)

    def _sync_conversation_tts_defaults(self, *, preserve_voice: bool = True) -> None:
        """Populate conversation-specific provider/model/voice selectors."""
        if not self._speech_service:
            self._conversation_tts_model_var.set("")
            self._conversation_tts_voice_var.set("")
            return

        providers = list(self._speech_service.providers)
        if hasattr(self, "_conversation_tts_provider_box"):
            self._conversation_tts_provider_box.configure(
                values=providers,
                state="readonly" if providers else "disabled",
            )
        provider_name = self._conversation_tts_provider_var.get().strip()
        if provider_name not in self._speech_service.providers:
            provider_name = providers[0] if providers else ""
            self._conversation_tts_provider_var.set(provider_name)
        if not provider_name:
            return

        provider = self._speech_service.providers[provider_name]
        if hasattr(self, "_conversation_tts_model_box"):
            self._conversation_tts_model_box.configure(values=provider.models)
        current_model = self._conversation_tts_model_var.get().strip()
        if current_model not in provider.models:
            self._conversation_tts_model_var.set(provider.default_model)

        language = self._conversation_language_var.get().strip()
        voice_labels = self._voice_options_for_provider(provider_name, language)
        if hasattr(self, "_conversation_tts_voice_box"):
            self._conversation_tts_voice_box.configure(
                values=voice_labels,
                state="readonly" if voice_labels else "disabled",
            )
        current_voice = self._conversation_tts_voice_var.get().strip()
        if not preserve_voice or current_voice not in voice_labels:
            self._conversation_tts_voice_var.set(voice_labels[0] if voice_labels else "")
            if not voice_labels and provider_name.casefold().startswith("piper"):
                self._conversation_tts_model_var.set("")
                self._conversation_audio_status_var.set(
                    f"No {language} Piper voice is installed. Add one in Speech & Audio → Voice Library."
                )
        if provider_name.casefold().startswith("piper") and self._conversation_tts_voice_var.get().strip():
            selected_path = self._resolve_runtime_voice(
                provider_name, self._conversation_tts_voice_var.get().strip()
            )
            if selected_path:
                self._conversation_tts_model_var.set(selected_path)

    def _selected_conversation_tts_voice(self) -> str:
        provider_name = self._conversation_tts_provider_var.get().strip()
        selected = self._conversation_tts_voice_var.get().strip()
        runtime = self._resolve_runtime_voice(provider_name, selected)
        if runtime:
            return runtime
        try:
            return get_voice_by_label(provider_name, selected)
        except ValueError:
            return selected

    def _conversation_audio_configuration(self) -> tuple[str, str, str]:
        if not self._speech_service or not self._conversation_tts_provider_var.get().strip():
            raise ValueError(
                "Configure tutor audio in Conversation or add a TTS provider in Speech & Audio."
            )
        provider_name = self._conversation_tts_provider_var.get().strip()
        try:
            provider = self._speech_service.providers[provider_name]
        except KeyError as exc:
            raise ValueError(f"TTS provider is not configured: {provider_name}") from exc
        if self._piper_voice_missing(provider_name, self._conversation_tts_voice_var.get()):
            raise ValueError(
                f"No {self._conversation_language_var.get().strip()} Piper voice is installed. "
                "Add one in Speech & Audio → Voice Library first."
            )
        model_name = self._conversation_tts_model_var.get().strip() or provider.default_model
        voice_name = self._selected_conversation_tts_voice().strip() or provider.default_voice
        return provider_name, model_name, voice_name

    def _play_existing_conversation_audio(self, path: Path, *, label: str) -> None:
        """Play an already-generated file without opening an external player."""
        self._conversation_audio_request_id += 1
        request_id = self._conversation_audio_request_id
        try:
            self._conversation_audio_player.play(path)
        except Exception as exc:
            LOGGER.exception("Conversation in-app playback failed")
            message = str(exc) or exc.__class__.__name__
            self._conversation_audio_status_var.set("Audio playback failed.")
            self._status_var.set(message)
            messagebox.showerror("Audio playback error", message)
            return
        self._conversation_audio_status_var.set(f"Playing {label}...")
        self._status_var.set(f"Playing {label}: {path.name}")
        threading.Thread(
            target=self._wait_for_conversation_audio,
            args=(request_id, label),
            daemon=True,
        ).start()

    def _wait_for_conversation_audio(self, request_id: int, label: str) -> None:
        try:
            self._conversation_audio_player.wait()
        except Exception:
            LOGGER.exception("Conversation audio wait failed")
            return
        if request_id != self._conversation_audio_request_id:
            return
        self._root.after(
            0,
            lambda: self._conversation_audio_status_var.set(f"Finished {label}."),
        )

    def _request_conversation_audio(self, text: str, *, label: str) -> None:
        """Generate a complete TTS file in the background, then play it in-app."""
        clean_text = " ".join((text or "").split())
        if not clean_text:
            messagebox.showinfo("No text", f"There is no {label} to read yet.")
            return
        try:
            provider_name, model_name, voice_name = self._conversation_audio_configuration()
        except ValueError as exc:
            messagebox.showerror("TTS not configured", str(exc))
            return

        self._conversation_audio_request_id += 1
        request_id = self._conversation_audio_request_id
        self._conversation_audio_player.stop()
        self._conversation_audio_status_var.set(f"Generating {label}...")
        self._status_var.set(f"Generating {label} audio with {provider_name}...")

        def _worker() -> None:
            try:
                assert self._speech_service is not None
                with self._conversation_audio_generation_lock:
                    result = self._speech_service.generate(
                        provider_name,
                        clean_text,
                        self._conversation_language_var.get(),
                        model_name,
                        voice_name,
                    )
                if not result.path.exists() or result.path.stat().st_size <= 0:
                    raise RuntimeError("TTS provider returned an empty audio file.")
            except Exception as exc:
                LOGGER.exception("Conversation TTS failed: label=%s", label)
                self._root.after(
                    0,
                    lambda exc=exc: self._handle_conversation_audio_error(exc, request_id=request_id),
                )
                return
            self._root.after(
                0,
                lambda result=result: self._play_generated_conversation_audio(
                    result.path, request_id=request_id, label=label
                ),
            )

        threading.Thread(target=_worker, daemon=True).start()

    def _handle_conversation_audio_error(self, exc: Exception, *, request_id: int | None = None) -> None:
        if request_id is not None and request_id != self._conversation_audio_request_id:
            return
        message = self._friendly_tts_error_message(exc)
        self._conversation_audio_status_var.set("Audio generation failed.")
        self._status_var.set(message)
        messagebox.showerror("TTS error", message)

    def _play_generated_conversation_audio(
        self,
        path: Path,
        *,
        request_id: int,
        label: str,
    ) -> None:
        if request_id != self._conversation_audio_request_id:
            return
        try:
            self._conversation_audio_player.play(path)
        except Exception as exc:
            self._handle_conversation_audio_error(exc, request_id=request_id)
            return
        self._conversation_audio_status_var.set(f"Playing {label}...")
        self._status_var.set(f"Playing {label} in the app: {path.name}")
        threading.Thread(
            target=self._wait_for_conversation_audio,
            args=(request_id, label),
            daemon=True,
        ).start()

    def _stop_conversation_audio(self, *, silent: bool = False) -> None:
        """Stop current playback and invalidate any older pending auto-read request."""
        self._conversation_audio_request_id += 1
        self._conversation_audio_player.stop()
        self._conversation_audio_status_var.set("Conversation audio: stopped." if not silent else "Conversation audio: ready.")
        if not silent:
            self._status_var.set("Conversation audio stopped.")

    def _read_conversation_tutor_reply_aloud(self) -> None:
        self._request_conversation_audio(
            self._conversation_tutor_reply or "",
            label="tutor reply",
        )

    def _read_conversation_question_aloud(self) -> None:
        self._request_conversation_audio(
            self._conversation_question or "",
            label="question",
        )

    def _schedule_conversation_auto_read(self, *, tutor_reply: str, next_question: str) -> None:
        text = build_auto_read_text(
            tutor_reply=tutor_reply,
            next_question=next_question,
            read_tutor_reply=bool(self._conversation_auto_read_tutor_var.get()),
            read_next_question=bool(self._conversation_auto_read_question_var.get()),
        )
        if not text:
            return
        if tutor_reply.strip() and next_question.strip() and self._conversation_auto_read_tutor_var.get() and self._conversation_auto_read_question_var.get():
            label = "tutor reply + next question"
        elif tutor_reply.strip() and self._conversation_auto_read_tutor_var.get():
            label = "tutor reply"
        else:
            label = "question"
        self._request_conversation_audio(text, label=label)

    def _conversation_rotation_source_key(self) -> str:
        source = self._conversation_flashcard_source_var.get().strip()
        if source == CONVERSATION_FLASHCARD_SOURCE_BATCH:
            return "batch_queue"
        return f"anki:{self._conversation_deck_var.get().strip()}"

    def _commit_pending_conversation_rotation_state(self) -> None:
        pending = getattr(self, "_conversation_pending_rotation_state", None)
        if not pending:
            return
        source_key, state_entry = pending
        self._conversation_rotation_state[source_key] = dict(state_entry)
        try:
            save_rotation_state(self._conversation_rotation_state_path, self._conversation_rotation_state)
        except OSError:
            LOGGER.exception("Could not save Conversation rotation state")
        self._conversation_pending_rotation_state = None

    def _conversation_flashcard_records(
        self,
        limit: int = CONVERSATION_FLASHCARD_LIMIT,
    ) -> tuple[list[str], list[str], int]:
        """Select one flashcard session and retain the full source target set."""
        source = self._conversation_flashcard_source_var.get().strip()
        selection_mode = self._conversation_selection_var.get().strip() or SELECTION_CONTINUE_ROTATION
        safe_limit = max(1, int(limit))

        records: list[tuple[str, object, str]] = []
        seen_targets: set[str] = set()
        due_keys: list[str] = []

        if source == CONVERSATION_FLASHCARD_SOURCE_BATCH:
            all_rows, all_targets, _total = build_flashcard_conversation_material(
                self._batch_items,
                limit=max(1, len(self._batch_items)),
            )
            self._conversation_all_flashcard_targets = list(all_targets)
            for item in self._batch_items:
                rows, targets, _ = build_flashcard_conversation_material([item], limit=1)
                if not rows or not targets:
                    continue
                target = targets[0]
                normalized = normalize_expression(target)
                if not normalized or normalized in seen_targets:
                    continue
                seen_targets.add(normalized)
                records.append((f"target:{normalized}", item, target))
            if selection_mode == SELECTION_ANKI_DUE:
                selection_mode = SELECTION_CONTINUE_ROTATION
                self._conversation_selection_var.set(selection_mode)
        else:
            deck_name = self._conversation_deck_var.get().strip()
            if not deck_name:
                raise ValueError("Select an Anki deck for Conversation.")
            try:
                notes = self._anki_client.list_notes_for_conversation(deck_name)
            except Exception as exc:
                raise ValueError(
                    f"Could not read Anki deck '{deck_name}'. Open Anki, make sure "
                    "AnkiConnect is running, then click Refresh decks."
                ) from exc
            _all_rows, all_targets, _total = build_anki_note_conversation_material(
                notes,
                limit=max(1, len(notes)),
            )
            self._conversation_all_flashcard_targets = list(all_targets)
            for note in notes:
                rows, targets, _ = build_anki_note_conversation_material([note], limit=1)
                if not rows or not targets:
                    continue
                target = targets[0]
                normalized = normalize_expression(target)
                if not normalized or normalized in seen_targets:
                    continue
                seen_targets.add(normalized)
                raw_note_id = note.get("note_id")
                key = f"note:{raw_note_id}" if raw_note_id is not None else f"target:{normalized}"
                records.append((key, note, target))

            if selection_mode == SELECTION_ANKI_DUE:
                try:
                    due_note_ids = self._anki_client.list_due_note_ids_for_conversation(deck_name)
                except Exception as exc:
                    raise ValueError(
                        f"Could not read due cards from Anki deck '{deck_name}'. "
                        "Open Anki and make sure AnkiConnect is running."
                    ) from exc
                due_keys = [f"note:{note_id}" for note_id in due_note_ids]

        total = len(records)
        available_keys = [key for key, _payload, _target in records]
        source_key = self._conversation_rotation_source_key()
        state_entry = self._conversation_rotation_state.get(source_key, {})
        selected_keys, updated_state = select_session_keys(
            available_keys,
            mode=selection_mode,
            limit=safe_limit,
            state_entry=state_entry,
            due_keys=due_keys,
        )
        if not selected_keys:
            if selection_mode == SELECTION_REPEAT_LAST:
                raise ValueError(
                    "There is no previous flashcard session to repeat for this source yet."
                )
            if selection_mode == SELECTION_ANKI_DUE:
                raise ValueError(
                    "No due cards were found in this Anki deck. Choose Continue rotation or Random cards."
                )
            return [], [], total

        selected_set = set(selected_keys)
        ordered_records = [record for record in records if record[0] in selected_set]
        order_index = {key: index for index, key in enumerate(selected_keys)}
        ordered_records.sort(key=lambda record: order_index.get(record[0], 10**9))

        if source == CONVERSATION_FLASHCARD_SOURCE_BATCH:
            selected_payloads = [payload for _key, payload, _target in ordered_records]
            rows, targets, _ = build_flashcard_conversation_material(
                selected_payloads,
                limit=max(1, len(selected_payloads)),
            )
        else:
            selected_payloads = [payload for _key, payload, _target in ordered_records]
            rows, targets, _ = build_anki_note_conversation_material(
                selected_payloads,
                limit=max(1, len(selected_payloads)),
            )

        self._conversation_pending_rotation_state = (source_key, updated_state)
        remaining = len(updated_state.get("remaining", []))
        cycle = int(updated_state.get("cycle", 0) or 0)
        if selection_mode == SELECTION_CONTINUE_ROTATION:
            self._conversation_selection_summary = (
                f"{selection_mode} · cycle {cycle} · {remaining} card(s) left before the next cycle"
            )
        else:
            self._conversation_selection_summary = selection_mode
        return rows, targets, total

    def _refresh_conversation_decks(self) -> None:
        """Reload Anki deck names for the Conversation selector."""
        self._load_decks()
        self._refresh_conversation_flashcard_status()

    def _refresh_conversation_flashcard_status(self) -> None:
        mode = self._conversation_mode_var.get().strip()
        if mode != CONVERSATION_MODE_FLASHCARDS:
            self._conversation_flashcard_status_var.set(
                "Topic mode does not use a flashcard source."
            )
            return

        source = self._conversation_flashcard_source_var.get().strip()
        selection_mode = self._conversation_selection_var.get().strip() or SELECTION_CONTINUE_ROTATION
        if source == CONVERSATION_FLASHCARD_SOURCE_BATCH:
            rows, _targets, total = build_flashcard_conversation_material(
                self._batch_items,
                limit=CONVERSATION_FLASHCARD_LIMIT,
            )
            if total == 0:
                self._conversation_flashcard_status_var.set(
                    "No usable Queue items. Load or create flashcards there first."
                )
            else:
                self._conversation_flashcard_status_var.set(
                    f"{total} usable Queue item(s). Selection: {selection_mode}. "
                    f"Up to {min(CONVERSATION_FLASHCARD_LIMIT, total)} will be used."
                )
            return

        deck_name = self._conversation_deck_var.get().strip()
        if not deck_name:
            self._conversation_flashcard_status_var.set(
                "Select an Anki deck. Open Anki and click Refresh decks if the list is empty."
            )
            return
        if selection_mode == SELECTION_ANKI_DUE:
            detail = "Only cards currently due in Anki will be loaded."
        elif selection_mode == SELECTION_REPEAT_LAST:
            detail = "The previous session for this deck will be loaded again."
        elif selection_mode == SELECTION_RANDOM:
            detail = "A random session will be loaded without consuming rotation progress."
        else:
            detail = "The next not-yet-used cards in the current rotation cycle will be loaded."
        self._conversation_flashcard_status_var.set(
            f"Anki deck: {deck_name}. Selection: {selection_mode}. {detail}"
        )

    def _on_conversation_source_changed(self, selected: str | None = None) -> None:
        """Enable source-specific controls and clear only the active session state."""
        source = (selected or self._conversation_flashcard_source_var.get()).strip()
        uses_anki = source == CONVERSATION_FLASHCARD_SOURCE_ANKI
        deck_state = "readonly" if uses_anki else "disabled"
        button_state = "normal" if uses_anki else "disabled"
        self._conversation_deck_box.configure(state=deck_state)
        self._conversation_refresh_decks_button.configure(state=button_state)
        selection_values = SELECTION_MODES if uses_anki else [
            SELECTION_CONTINUE_ROTATION,
            SELECTION_RANDOM,
            SELECTION_REPEAT_LAST,
        ]
        self._conversation_selection_box.configure(values=selection_values)
        if self._conversation_selection_var.get() not in selection_values:
            self._conversation_selection_var.set(SELECTION_CONTINUE_ROTATION)
        self._conversation_all_flashcard_targets = []
        self._conversation_flashcard_rows = []
        self._conversation_flashcard_targets = []
        self._conversation_practised_targets.clear()
        self._conversation_pending_rotation_state = None
        self._conversation_new_candidate_pool = []
        if hasattr(self, "_conversation_session_text"):
            self._refresh_conversation_session_display()
        if hasattr(self, "_suggestions_frame"):
            self._render_suggestions([])
        self._refresh_conversation_flashcard_status()

    @staticmethod
    def _set_conversation_readonly_text(widget: ctk.CTkTextbox, text: str) -> None:
        """Replace text in one read-only Conversation side-panel box."""
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _toggle_conversation_session_cards(self) -> None:
        self._conversation_session_expanded = not self._conversation_session_expanded
        if self._conversation_session_expanded:
            self._conversation_session_text.grid()
        else:
            self._conversation_session_text.grid_remove()
        self._refresh_conversation_session_display()

    def _refresh_conversation_session_display(self) -> None:
        total = len(self._conversation_flashcard_targets)
        practised = len(self._conversation_practised_targets)
        arrow = "▼" if self._conversation_session_expanded else "▶"
        if total:
            self._conversation_session_title_var.set(
                f"{arrow} Flashcards in this session — {practised}/{total} practised"
            )
            lines = []
            for index, target in enumerate(self._conversation_flashcard_targets, start=1):
                marker = "✓" if normalize_expression(target) in self._conversation_practised_targets else "○"
                lines.append(f"{marker} {index}. {target}")
            self._set_conversation_readonly_text(self._conversation_session_text, "\n".join(lines))
        else:
            self._conversation_session_title_var.set(f"{arrow} Flashcards in this session")
            self._set_conversation_readonly_text(
                self._conversation_session_text,
                "Start a flashcard conversation to load the session targets.",
            )

    def _rebuild_conversation_flashcard_context(self) -> None:
        if not self._conversation_flashcard_rows or not self._conversation_flashcard_targets:
            self._conversation_flashcard_context = ""
            self._refresh_conversation_session_display()
            return
        pairs = list(zip(self._conversation_flashcard_rows, self._conversation_flashcard_targets))
        pairs.sort(
            key=lambda pair: normalize_expression(pair[1]) in self._conversation_practised_targets
        )
        lines: list[str] = []
        for index, (row, target) in enumerate(pairs, start=1):
            used = normalize_expression(target) in self._conversation_practised_targets
            status = "ALREADY USED" if used else "NOT USED YET"
            lines.append(f"{index}. [{status}] {row}")
        self._conversation_flashcard_context = "\n".join(lines)
        self._refresh_conversation_session_display()

    def _mark_conversation_targets_practised(self, text: str) -> None:
        if not text or not self._conversation_flashcard_targets:
            return
        changed = False
        for target in self._conversation_flashcard_targets:
            key = normalize_expression(target)
            if key in self._conversation_practised_targets:
                continue
            if expression_is_grounded_in_exchange(target, text):
                self._conversation_practised_targets.add(key)
                changed = True
        if changed:
            self._rebuild_conversation_flashcard_context()
        else:
            self._refresh_conversation_session_display()

    def _refresh_conversation_suggestion_panel_mode(self) -> None:
        """Show separate semantics for topic suggestions and flashcard practice."""
        flashcard_mode = self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS
        flashcard_widgets = (
            self._conversation_session_toggle_button,
            self._conversation_use_next_label,
            self._conversation_use_next_text,
            self._conversation_candidates_label,
        )
        if flashcard_mode:
            self._conversation_suggestions_title_label.configure(text="Flashcard conversation")
            self._conversation_suggestions_help_label.configure(
                text=(
                    "Practice cues and genuinely new cards stay separate. New candidates accumulate "
                    "during the session; the session-card list is collapsed at the bottom."
                )
            )
            for widget in flashcard_widgets:
                widget.grid()
            self._conversation_clear_candidates_button.grid()
            self._conversation_suggestion_buttons.grid_columnconfigure(2, weight=1)
            if self._conversation_session_expanded:
                self._conversation_session_text.grid()
            else:
                self._conversation_session_text.grid_remove()
        else:
            self._conversation_suggestions_title_label.configure(text="AI suggestions")
            self._conversation_suggestions_help_label.configure(
                text=(
                    "Checkbox → edit/remove → stage here → send to Queue. "
                    "No direct Anki write here."
                )
            )
            for widget in flashcard_widgets:
                widget.grid_remove()
            self._conversation_clear_candidates_button.grid_remove()
            self._conversation_suggestion_buttons.grid_columnconfigure(2, weight=0)
            self._conversation_session_text.grid_remove()

    def _on_conversation_mode_changed(self, selected: str | None = None) -> None:
        """Show only controls that belong to the selected conversation mode."""
        mode = (selected or self._conversation_mode_var.get()).strip()
        flashcard_mode = mode == CONVERSATION_MODE_FLASHCARDS
        self._conversation_start_button.configure(text="Start conversation")

        topic_frame = getattr(self, "_conversation_topic_frame", None)
        flashcard_frame = getattr(self, "_conversation_flashcard_settings_frame", None)

        if flashcard_mode:
            current_topic = self._topic_var.get().strip()
            if current_topic:
                self._conversation_topic_draft = current_topic
            self._topic_var.set("")
            if topic_frame is not None:
                topic_frame.grid_remove()
            if flashcard_frame is not None:
                flashcard_frame.grid()
        else:
            if flashcard_frame is not None:
                flashcard_frame.grid_remove()
            if topic_frame is not None:
                topic_frame.grid()
            if not self._topic_var.get().strip() and self._conversation_topic_draft:
                self._topic_var.set(self._conversation_topic_draft)

        self._conversation_source_box.configure(
            state="readonly" if flashcard_mode else "disabled"
        )
        self._conversation_selection_box.configure(
            state="readonly" if flashcard_mode else "disabled"
        )
        self._conversation_expressions_to_use_next = []
        self._conversation_new_candidate_pool = []
        self._render_suggestions([])
        self._refresh_conversation_suggestion_panel_mode()
        if flashcard_mode:
            self._on_conversation_source_changed()
            self._set_conversation_readonly_text(
                self._conversation_use_next_text,
                "The tutor will place relevant speaking cues here after your answer.",
            )
        else:
            self._conversation_deck_box.configure(state="disabled")
            self._conversation_refresh_decks_button.configure(state="disabled")
            self._conversation_flashcard_context = ""
            self._conversation_flashcard_rows = []
            self._conversation_flashcard_targets = []
            self._conversation_all_flashcard_targets = []
            self._conversation_practised_targets.clear()
            self._conversation_pending_rotation_state = None
            self._refresh_conversation_session_display()
            self._refresh_conversation_flashcard_status()

    def _prepare_conversation_context(self) -> tuple[str, str]:
        """Return (display label, flashcard context) for the selected mode."""
        topic = self._topic_var.get().strip()
        if self._conversation_mode_var.get() != CONVERSATION_MODE_FLASHCARDS:
            if not topic:
                raise ValueError("Enter a conversation topic first.")
            self._conversation_flashcard_context = ""
            self._conversation_flashcard_rows = []
            self._conversation_flashcard_targets = []
            self._conversation_all_flashcard_targets = []
            self._conversation_practised_targets.clear()
            return topic, ""

        rows, targets, total = self._conversation_flashcard_records()
        source = self._conversation_flashcard_source_var.get().strip()
        if not rows:
            if source == CONVERSATION_FLASHCARD_SOURCE_BATCH:
                raise ValueError(
                    "No usable flashcards are loaded in Queue. "
                    "Load a list or create cards there first."
                )
            deck_name = self._conversation_deck_var.get().strip()
            raise ValueError(
                f"No usable flashcards were found in Anki deck '{deck_name}'. "
                "Choose another deck or add supported vocabulary/grammar cards."
            )

        self._conversation_flashcard_rows = list(rows)
        self._conversation_flashcard_targets = list(targets)
        self._conversation_practised_targets.clear()
        self._rebuild_conversation_flashcard_context()
        if source == CONVERSATION_FLASHCARD_SOURCE_BATCH:
            source_label = "Current Queue"
        else:
            source_label = f"Anki deck: {self._conversation_deck_var.get().strip()}"
        return (
            f"{source_label} ({total} usable) · {self._conversation_selection_summary} · flashcard targets only",
            self._conversation_flashcard_context,
        )

    def _start_conversation_topic(self) -> None:
        """Start a topic conversation or one based on a selected flashcard source."""
        if (
            self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS
            and self._conversation_flashcard_source_var.get() == CONVERSATION_FLASHCARD_SOURCE_ANKI
        ):
            deck_name = self._conversation_deck_var.get().strip()
            self._status_var.set(f"Loading flashcards from Anki deck: {deck_name}...")
            self._root.update_idletasks()
        self._conversation_pending_rotation_state = None
        try:
            display_context, flashcard_context = self._prepare_conversation_context()
        except ValueError as exc:
            messagebox.showerror("Conversation", str(exc))
            return

        flashcard_mode = self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS
        topic = "" if flashcard_mode else self._topic_var.get().strip()
        provider_name = self._conversation_provider_var.get()
        self._conversation_history.clear()
        self._conversation_question = None
        self._conversation_tutor_reply = None
        self._stop_conversation_audio(silent=True)
        self._conversation_current_input_from_stt = False
        self._conversation_expressions_to_use_next = []
        self._conversation_new_candidate_pool = []
        self._render_suggestions([])
        self._clear_chat()

        if flashcard_context:
            self._append_chat("MODE", display_context)
            preview = "\n".join(f"• {target}" for target in self._conversation_flashcard_targets[:12])
            if len(self._conversation_flashcard_targets) > 12:
                preview += f"\n• +{len(self._conversation_flashcard_targets) - 12} more"
            self._append_chat("FLASHCARD TARGETS", preview)
            self._refresh_conversation_session_display()
            self._set_conversation_readonly_text(
                self._conversation_use_next_text,
                "Answer naturally first. Relevant speaking cues will appear here after feedback.",
            )
        else:
            self._append_chat("TOPIC", display_context)

        self._status_var.set(f"Starting conversation with {provider_name}...")
        self._root.update_idletasks()

        try:
            start = self._conversation_ai_client().start_conversation(
                topic=topic,
                target_language=self._conversation_language_var.get(),
                flashcard_context=flashcard_context,
            )
        except Exception as exc:
            self._conversation_pending_rotation_state = None
            self._status_var.set("Conversation start failed.")
            messagebox.showerror("Conversation error", str(exc))
            return

        self._commit_pending_conversation_rotation_state()
        self._conversation_question = start.question
        self._conversation_history.append(("ai", start.question))
        self._append_chat("AI TUTOR", start.question)
        if flashcard_context:
            self._mark_conversation_targets_practised(start.question)
            total = len(self._conversation_flashcard_targets)
            practised = len(self._conversation_practised_targets)
            self._status_var.set(
                f"Flashcard conversation started · {practised}/{total} practised. "
                "The tutor will prefer targets not used yet."
            )
        else:
            self._status_var.set("Conversation started. Write your answer and send it.")
        if self._conversation_auto_read_question_var.get():
            self._schedule_conversation_auto_read(tutor_reply="", next_question=start.question)

    def _conversation_feedback_exchange_text(
        self,
        answer: str,
        feedback: ConversationFeedback,
    ) -> str:
        """Return fields that may legitimately ground a new flashcard candidate."""
        parts = [
            answer,
            feedback.feedback,
            feedback.corrected_version,
            feedback.advanced_answer,
            feedback.mini_practice,
            feedback.tutor_reply,
        ]
        for correction in feedback.corrections:
            parts.extend((correction.original, correction.correction, correction.explanation))
        # Deliberately exclude next_question: the model must not seed an unrelated
        # phrase into the next prompt merely to make it look like a valid candidate.
        return "\n".join(part.strip() for part in parts if part and part.strip())

    def _send_conversation_message(self) -> None:
        """Send the learner answer, request feedback, and continue the conversation."""
        if not self._conversation_question:
            messagebox.showerror("No conversation", "Start a conversation first.")
            return

        answer = self._message_input.get("1.0", "end").strip()
        if not answer:
            return

        self._message_input.delete("1.0", "end")
        self._append_chat("YOU", answer)

        provider_name = self._conversation_provider_var.get()
        self._status_var.set(f"Reviewing answer with {provider_name}...")
        self._root.update_idletasks()
        history_for_prompt = self._build_history_text(max_turns=10)
        if self._conversation_current_input_from_stt:
            history_for_prompt = (
                history_for_prompt
                + "\nINPUT SOURCE: The CURRENT learner answer originated from speech-to-text. "
                "Obvious garbled proper names or nonsensical phonetic fragments may be transcription errors."
            ).strip()
        try:
            feedback = self._conversation_ai_client().review_conversation_answer(
                topic=(
                    ""
                    if self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS
                    else self._topic_var.get().strip()
                ),
                question=self._conversation_question,
                answer=answer,
                target_language=self._conversation_language_var.get(),
                improvement_level=self._improvement_level_var.get(),
                feedback_language=self._feedback_language_var.get(),
                flashcard_context=self._conversation_flashcard_context,
                conversation_history=history_for_prompt,
            )
        except Exception as exc:
            self._status_var.set("Conversation reply failed.")
            messagebox.showerror("Conversation error", str(exc))
            return

        self._conversation_current_input_from_stt = False
        flashcard_mode = self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS
        if flashcard_mode:
            # Older/local providers may still fill only suggested_vocabulary. Keep it usable
            # as a speaking-cue fallback, and only let its items become candidates after the
            # same strict deck/staged/grounding filter used for the dedicated new-card field.
            use_next_source = feedback.expressions_to_use_next or feedback.suggested_vocabulary
            use_next = dedupe_expressions(use_next_source, limit=4)
            candidate_source = feedback.new_flashcard_candidates or feedback.suggested_vocabulary
            exchange_text = self._conversation_feedback_exchange_text(answer, feedback)
            new_candidates = filter_new_flashcard_candidates(
                candidate_source,
                existing_expressions=(
                    list(self._conversation_all_flashcard_targets)
                    + list(self._conversation_flashcard_targets)
                ),
                staged_expressions=self._flashcard_queue,
                exchange_text=exchange_text,
                limit=3,
            )
            self._conversation_new_candidate_pool = dedupe_expressions(
                [*self._conversation_new_candidate_pool, *new_candidates],
                limit=30,
            )
            self._conversation_expressions_to_use_next = use_next
            self._set_conversation_readonly_text(
                self._conversation_use_next_text,
                "\n".join(f"• {item}" for item in use_next)
                if use_next
                else "No additional speaking cue is needed for the next answer.",
            )
            self._render_suggestions(self._conversation_new_candidate_pool)
        else:
            topic_suggestions = dedupe_expressions(feedback.suggested_vocabulary, limit=6)
            use_next = []
            new_candidates = topic_suggestions
            self._render_suggestions(topic_suggestions)

        self._conversation_history.append(("user", answer))
        assistant_turn = " ".join(
            part.strip()
            for part in (feedback.tutor_reply, feedback.next_question)
            if part and part.strip()
        )
        if assistant_turn:
            self._conversation_history.append(("ai", assistant_turn))
        self._append_conversation_feedback(
            feedback,
            expressions_to_use_next=use_next,
            new_flashcard_candidates=new_candidates if flashcard_mode else [],
        )
        self._conversation_tutor_reply = feedback.tutor_reply or ""
        self._conversation_question = feedback.next_question

        if flashcard_mode:
            coverage_text = "\n".join(
                part for part in (self._conversation_question or "", answer, assistant_turn) if part
            )
            self._mark_conversation_targets_practised(coverage_text)
            total = len(self._conversation_flashcard_targets)
            practised = len(self._conversation_practised_targets)
            pool_total = len(self._conversation_new_candidate_pool)
            if new_candidates:
                status = (
                    f"Feedback ready · {practised}/{total} practised · "
                    f"{len(new_candidates)} new candidate(s) this turn · {pool_total} accumulated."
                )
            else:
                status = (
                    f"Feedback ready · {practised}/{total} practised · "
                    f"no new candidate this turn · {pool_total} accumulated."
                )
        else:
            status = "Feedback ready. Select expressions or continue the conversation."
        self._status_var.set(status)
        self._schedule_conversation_auto_read(
            tutor_reply=feedback.tutor_reply or "",
            next_question=feedback.next_question or "",
        )

    def _build_history_text(self, max_turns: int = 8) -> str:
        recent = self._conversation_history[-max_turns:]
        return "\n".join(f"{speaker}: {message}" for speaker, message in recent)

    def _append_conversation_feedback(
        self,
        feedback: ConversationFeedback,
        *,
        expressions_to_use_next: list[str] | None = None,
        new_flashcard_candidates: list[str] | None = None,
    ) -> None:
        """Render compact coaching first and keep extended material optional."""
        self._append_chat(
            f"FEEDBACK ({feedback.feedback_language or self._feedback_language_var.get()})",
            feedback.feedback,
        )

        grouped: dict[str, list[str]] = {
            "error": [],
            "improvement": [],
            "possible_transcription": [],
        }
        for correction in feedback.corrections:
            kind = (getattr(correction, "kind", "error") or "error").strip().casefold()
            if kind not in grouped:
                kind = "error"
            original = correction.original.strip() or "original wording"
            fixed = correction.correction.strip() or "corrected wording"
            explanation = correction.explanation.strip()
            if kind == "possible_transcription":
                block = f"🎙 {original}\n   → {fixed}"
            elif kind == "improvement":
                block = f"• {original}\n   → {fixed}"
            else:
                block = f"❌ {original}\n   ✅ {fixed}"
            if explanation:
                block += f"\n   💡 {explanation}"
            grouped[kind].append(block)

        if grouped["error"]:
            self._append_chat("CORRECTIONS", "\n\n".join(grouped["error"]))
        if grouped["improvement"]:
            self._append_chat("MORE NATURAL / ADVANCED", "\n\n".join(grouped["improvement"]))
        if grouped["possible_transcription"]:
            self._append_chat(
                "POSSIBLE TRANSCRIPTION ERROR",
                "\n\n".join(grouped["possible_transcription"]),
            )

        detailed = bool(self._conversation_detailed_feedback_var.get())
        if detailed:
            if feedback.corrected_version:
                self._append_chat("CORRECTED VERSION", feedback.corrected_version)
            if feedback.advanced_answer:
                self._append_chat("STRONGER ANSWER", feedback.advanced_answer)
            if feedback.mini_practice:
                self._append_chat("MINI PRACTICE", feedback.mini_practice)

        flashcard_mode = self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS
        if detailed and flashcard_mode:
            use_next = expressions_to_use_next or []
            candidates = new_flashcard_candidates or []
            if use_next:
                self._append_chat(
                    "EXPRESSIONS TO USE NEXT",
                    "\n".join(f"• {item}" for item in use_next),
                )
            if candidates:
                self._append_chat(
                    "NEW FLASHCARD CANDIDATES",
                    "\n".join(f"• {item}" for item in candidates),
                )
        elif detailed and feedback.suggested_vocabulary:
            self._append_chat(
                "SUGGESTED EXPRESSIONS",
                "\n".join(f"• {item}" for item in feedback.suggested_vocabulary),
            )

        if feedback.tutor_reply:
            self._append_chat("AI TUTOR", feedback.tutor_reply)
            self._append_chat("NEXT QUESTION", feedback.next_question)
        else:
            # Backward-compatible display for older/local providers that do not
            # yet return the dedicated conversational reply field.
            self._append_chat("AI TUTOR", feedback.next_question)

    def _conversation_export_metadata(self) -> dict[str, str]:
        metadata = {
            "Exported": datetime.now().astimezone().isoformat(timespec="seconds"),
            "Language": self._conversation_language_var.get().strip(),
            "Mode": self._conversation_mode_var.get().strip(),
            "Topic": (
                ""
                if self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS
                else self._topic_var.get().strip()
            ),
            "Conversation model": self._conversation_provider_var.get().strip(),
            "Feedback language": self._feedback_language_var.get().strip(),
        }
        if self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS:
            metadata["Flashcard source"] = self._conversation_flashcard_source_var.get().strip()
            if self._conversation_flashcard_source_var.get() == CONVERSATION_FLASHCARD_SOURCE_ANKI:
                metadata["Deck"] = self._conversation_deck_var.get().strip()
            metadata["Card selection"] = self._conversation_selection_var.get().strip()
            metadata["Practised"] = (
                f"{len(self._conversation_practised_targets)}/{len(self._conversation_flashcard_targets)}"
            )
        return metadata

    def _export_conversation(self) -> None:
        """Export the visible Conversation session as Markdown or TXT."""
        if not self._conversation_export_entries:
            messagebox.showinfo("Nothing to export", "Start a conversation before exporting it.")
            return
        export_dir = Path("conversation_exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        default_name = default_conversation_export_name(
            language=self._conversation_language_var.get(),
            topic=self._topic_var.get(),
        )
        selected = filedialog.asksaveasfilename(
            title="Export Conversation",
            initialdir=str(export_dir.resolve()),
            initialfile=default_name,
            defaultextension=".md",
            filetypes=[
                ("Markdown", "*.md"),
                ("Text", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not selected:
            return
        path = Path(selected)
        try:
            write_conversation_export(
                path,
                self._conversation_export_entries,
                metadata=self._conversation_export_metadata(),
                session_flashcards=self._conversation_flashcard_targets,
                new_candidates=self._conversation_new_candidate_pool,
            )
        except Exception as exc:
            LOGGER.exception("Conversation export failed")
            messagebox.showerror("Export failed", str(exc) or exc.__class__.__name__)
            return
        self._status_var.set(f"Conversation exported: {path}")
        messagebox.showinfo("Conversation exported", f"Saved to:\n{path}")

    def _append_chat(self, speaker: str, text: str) -> None:
        clean_speaker = (speaker or "ENTRY").strip()
        clean_text = (text or "").strip()
        if clean_text:
            self._conversation_export_entries.append((clean_speaker, clean_text))
        self._chat_text.configure(state="normal")
        self._chat_text.insert("end", f"\n{speaker}\n{text}\n")
        self._chat_text.see("end")
        self._chat_text.configure(state="disabled")

    def _clear_chat(self) -> None:
        self._conversation_export_entries.clear()
        self._chat_text.configure(state="normal")
        self._chat_text.delete("1.0", "end")
        self._chat_text.configure(state="disabled")

    def _render_suggestions(self, suggestions: list[str]) -> None:
        for widget in self._suggestions_frame.winfo_children():
            widget.destroy()
        self._latest_suggestions = [item.strip() for item in suggestions if item and item.strip()]
        self._suggestion_items = [
            {"expression": expression, "source": "ai suggestion"}
            for expression in self._latest_suggestions
        ]
        self._suggestion_vars = []
        self._suggestion_entry_vars = []
        if not self._suggestion_items:
            flashcard_mode = self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS
            empty_text = (
                "No genuinely new flashcard candidates have been found in this session yet. "
                "Existing deck expressions stay in the practice-cue area instead of being recreated."
                if flashcard_mode
                else "No suggestions yet. AI suggestions will appear here after conversation feedback."
            )
            ctk.CTkLabel(
                self._suggestions_frame,
                text=empty_text,
                text_color=("gray35", "gray75"),
                wraplength=330,
                justify="left",
            ).pack(anchor="w", padx=8, pady=8)
            for name in ("_conversation_stage_selected_button", "_conversation_stage_all_button"):
                button = getattr(self, name, None)
                if button is not None:
                    button.configure(state="disabled")
            clear_button = getattr(self, "_conversation_clear_candidates_button", None)
            if clear_button is not None:
                clear_button.configure(state="disabled")
            return

        for name in ("_conversation_stage_selected_button", "_conversation_stage_all_button"):
            button = getattr(self, name, None)
            if button is not None:
                button.configure(state="normal")
        clear_button = getattr(self, "_conversation_clear_candidates_button", None)
        if clear_button is not None:
            clear_button.configure(state="normal")

        for index, item in enumerate(self._suggestion_items):
            expression_var = ctk.StringVar(value=item.get("expression", ""))
            selected_var = ctk.BooleanVar(value=True)
            self._suggestion_entry_vars.append(expression_var)
            self._suggestion_vars.append(selected_var)

            row = ctk.CTkFrame(self._suggestions_frame, corner_radius=10)
            row.pack(anchor="w", fill="x", padx=6, pady=5)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkCheckBox(row, text="", variable=selected_var, width=22).grid(
                row=0, column=0, sticky="w", padx=(8, 4), pady=8
            )
            ctk.CTkEntry(row, textvariable=expression_var, height=32).grid(
                row=0, column=1, sticky="ew", padx=(0, 6), pady=8
            )
            ctk.CTkButton(
                row,
                text="Remove",
                width=72,
                height=30,
                command=lambda i=index: self._remove_suggestion_draft(i),
            ).grid(row=0, column=2, sticky="e", padx=(0, 8), pady=8)

    def _sync_suggestion_items_from_ui(self) -> None:
        for item, entry_var in zip(self._suggestion_items, self._suggestion_entry_vars):
            item["expression"] = clean_ocr_text(entry_var.get()).replace("\n", " ").strip()
        if self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS:
            self._conversation_new_candidate_pool = dedupe_expressions(
                [item.get("expression", "") for item in self._suggestion_items],
                limit=30,
            )

    def _remove_suggestion_draft(self, index: int) -> None:
        self._sync_suggestion_items_from_ui()
        if index < 0 or index >= len(self._suggestion_items):
            return
        del self._suggestion_items[index]
        current = [item.get("expression", "") for item in self._suggestion_items]
        if self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS:
            self._conversation_new_candidate_pool = dedupe_expressions(current, limit=30)
        self._render_suggestions(current)
        self._status_var.set("Suggestion draft removed.")

    def _clear_conversation_candidates(self) -> None:
        self._conversation_new_candidate_pool = []
        self._render_suggestions([])
        self._status_var.set("Conversation flashcard candidates cleared. Staged items were not changed.")

    def _add_selected_suggestions_to_queue(self) -> None:
        self._sync_suggestion_items_from_ui()
        selected = [
            item.get("expression", "")
            for item, var in zip(self._suggestion_items, self._suggestion_vars)
            if var.get()
        ]
        self._add_phrases_to_queue(selected)
        if self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS and selected:
            selected_keys = {normalize_expression(item) for item in selected}
            self._conversation_new_candidate_pool = [
                item for item in self._conversation_new_candidate_pool
                if normalize_expression(item) not in selected_keys
            ]
            self._render_suggestions(self._conversation_new_candidate_pool)

    def _add_all_suggestions_to_queue(self) -> None:
        self._sync_suggestion_items_from_ui()
        all_items = [item.get("expression", "") for item in self._suggestion_items]
        self._add_phrases_to_queue(all_items)
        if self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS and all_items:
            self._conversation_new_candidate_pool = []
            self._render_suggestions([])

    def _add_custom_phrase_to_queue(self) -> None:
        phrase = self._custom_phrase_var.get().strip()
        if not phrase:
            return
        self._add_phrases_to_queue([phrase])
        self._custom_phrase_var.set("")

    def _add_phrases_to_queue(self, phrases: list[str]) -> None:
        added = 0
        merged = dedupe_expressions([*self._flashcard_queue, *phrases])
        existing_count = len(self._flashcard_queue)
        self._flashcard_queue = merged
        added = max(0, len(self._flashcard_queue) - existing_count)
        if added:
            self._conversation_last_batch_send = []
        self._refresh_queue_text()
        total = len(self._flashcard_queue)
        self._conversation_queue_log_var.set(
            f"Staged {added} new expression(s). Total staged: {total}. Review the list below, then send it to Queue."
        )
        self._status_var.set(f"Staged {added} expression(s) for Queue. Nothing added to Anki yet.")

    def _refresh_queue_text(self) -> None:
        self._queue_text.configure(state="normal")
        self._queue_text.delete("1.0", "end")
        if self._flashcard_queue:
            lines = [
                f"STAGED — NOT SENT YET ({len(self._flashcard_queue)} item(s))",
                "These will go to Queue only after you click Add staged to Queue.",
                "",
            ]
            lines.extend(f"{idx}. {item}" for idx, item in enumerate(self._flashcard_queue, start=1))
            self._queue_text.insert("1.0", "\n".join(lines))
        elif self._conversation_last_batch_send:
            lines = [
                f"LAST SENT TO QUEUE ({len(self._conversation_last_batch_send)} item(s))",
                "Nothing was added directly to Anki. Review/generate/add these in the Queue tab.",
                "",
            ]
            lines.extend(f"{idx}. {item}" for idx, item in enumerate(self._conversation_last_batch_send, start=1))
            self._queue_text.insert("1.0", "\n".join(lines))
        else:
            self._queue_text.insert(
                "1.0",
                "No staged expressions yet. Use Stage selected / Stage all above.\n\n"
                "After staging, this box will show the exact items before they are sent to Queue.",
            )
        self._queue_text.configure(state="disabled")

    def _clear_queue(self) -> None:
        self._flashcard_queue.clear()
        self._conversation_last_batch_send = []
        self._refresh_queue_text()
        self._cleanup_runtime_memory("clear conversation staged queue", aggressive=False)
        self._conversation_queue_log_var.set(
            "Staged expressions cleared. Nothing was added to Anki."
        )
        self._status_var.set("Conversation staged expressions cleared.")

    def _send_conversation_queue_to_batch(self) -> None:
        """Move staged conversation suggestions into the central Queue flow.

        Conversation should not silently generate cards or write to Anki.
        It only prepares vocabulary candidates. The Queue tab remains the
        single visible place where cards are generated, reviewed, duplicate-checked,
        and finally added to the selected Anki deck.
        """
        if not self._flashcard_queue:
            messagebox.showerror("Nothing staged", "Stage at least one expression before sending it to Queue.")
            return

        deck_name = self._deck_var.get().strip() or self._anki_client.deck_name
        conversation_provider = self._conversation_provider_var.get().strip()
        if conversation_provider in self._ai_clients:
            # Make the next Queue generation match the provider used in this
            # conversation, and make that visible in the top bar.
            self._provider_var.set(conversation_provider)
        provider_name = self._provider_var.get().strip()
        target_language = self._conversation_language_var.get().strip() or self._language_var.get().strip()
        if target_language:
            self._language_var.set(target_language)
        explanation_language = self._explanation_language_var.get().strip()
        topic = self._topic_var.get().strip()

        existing = {str(item.get("word", "")).strip().casefold() for item in self._batch_items}
        new_items: list[dict[str, object]] = []
        skipped_duplicates: list[str] = []
        for phrase in self._flashcard_queue:
            cleaned = clean_ocr_text(phrase).replace("\n", " ").strip()
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key in existing:
                skipped_duplicates.append(cleaned)
                continue
            new_items.append(
                {
                    "word": cleaned,
                    "status": "pending",
                    "topic": topic,
                    "batch_mode": "Vocabulary",
                    "target_language": target_language,
                    "explanation_language": explanation_language,
                    "source": "conversation_practice/suggested_expression",
                    "provider_name": provider_name,
                }
            )
            existing.add(key)

        if not new_items:
            self._conversation_queue_log_var.set(
                f"Nothing new sent. {len(skipped_duplicates)} duplicate staged expression(s) were already in Queue."
            )
            messagebox.showinfo("Queue", "All staged expressions are already in Queue.")
            return

        append_mode = bool(self._batch_items)
        self._batch_items.extend(new_items)
        if not append_mode:
            self._batch_index = 0
        else:
            self._batch_index = len(self._batch_items) - len(new_items)
        self._batch_generated_card = None
        self._batch_generated_provider_name = None
        self._batch_generated_grammar = None
        self._batch_mode_var.set("Vocabulary")
        self._batch_topic_var.set(topic)
        self._batch_source_summary_var.set(f"Received {len(new_items)} clean vocabulary item(s) from Conversation.")
        self._update_batch_mode_help()
        self._show_current_batch_item(generate=False)
        self._batch_status_var.set(
            f"Conversation sent {len(new_items)} item(s). Review/generate them here, then add to Anki deck: {deck_name}."
        )
        self._autosave_batch_session("conversation suggestions sent to queue")

        sent_preview = ", ".join(item["word"] for item in new_items[:4])
        if len(new_items) > 4:
            sent_preview += f", +{len(new_items) - 4} more"
        duplicate_note = f" Skipped duplicates: {len(skipped_duplicates)}." if skipped_duplicates else ""
        log_message = (
            f"Sent {len(new_items)} expression(s) to Queue. Nothing added to Anki yet. "
            f"Deck for final Anki add: {deck_name}. Provider: {provider_name}. Items: {sent_preview}.{duplicate_note}"
        )
        self._conversation_queue_log_var.set(log_message)
        self._status_var.set(log_message)
        self._append_chat("QUEUE LOG", log_message)
        self._record_activity(f"Conversation → Queue: {len(new_items)}")
        self._conversation_last_batch_send = [str(item.get("word", "")).strip() for item in new_items if str(item.get("word", "")).strip()]
        if self._conversation_mode_var.get() == CONVERSATION_MODE_FLASHCARDS:
            sent_keys = {normalize_expression(item) for item in self._conversation_last_batch_send}
            self._conversation_new_candidate_pool = [
                item for item in self._conversation_new_candidate_pool
                if normalize_expression(item) not in sent_keys
            ]
            self._render_suggestions(self._conversation_new_candidate_pool)
        self._flashcard_queue.clear()
        self._refresh_queue_text()
        self._cleanup_runtime_memory("clear conversation staged queue", aggressive=False)
        try:
            self._tabs.set("Queue")
        except Exception:
            pass
        messagebox.showinfo(
            "Sent to Queue",
            f"Sent {len(new_items)} expression(s) to Queue.\n\n"
            f"Nothing has been added to Anki yet.\n"
            f"Final Anki deck later: {deck_name}\n"
            f"Card AI provider for generation: {provider_name}\n\n"
            f"Review them in Queue, then generate/add from there.",
        )

    def _reset_conversation(self) -> None:
        self._conversation_history.clear()
        self._conversation_question = None
        self._conversation_tutor_reply = None
        self._stop_conversation_audio(silent=True)
        self._conversation_current_input_from_stt = False
        self._conversation_flashcard_context = ""
        self._conversation_flashcard_rows = []
        self._conversation_flashcard_targets = []
        self._conversation_all_flashcard_targets = []
        self._conversation_practised_targets.clear()
        self._conversation_expressions_to_use_next = []
        self._conversation_new_candidate_pool = []
        self._conversation_pending_rotation_state = None
        self._latest_suggestions = []
        self._conversation_last_batch_send = []
        self._suggestion_items = []
        self._suggestion_vars = []
        self._suggestion_entry_vars = []
        self._clear_chat()
        self._chat_text.configure(state="normal")
        self._chat_text.insert(
            "1.0",
            "Choose a mode. Start with a topic or use flashcards from an Anki deck or Queue.\n",
        )
        self._chat_text.configure(state="disabled")
        self._flashcard_queue.clear()
        self._render_suggestions([])
        self._refresh_queue_text()
        self._refresh_conversation_session_display()
        self._set_conversation_readonly_text(
            self._conversation_use_next_text,
            "The tutor will place relevant speaking cues here after your answer.",
        )
        self._conversation_queue_log_var.set(
            "Conversation reset. Rotation progress was kept; use Repeat last session if you want the same cards again."
        )
        self._refresh_conversation_flashcard_status()
        self._status_var.set("Conversation reset. Flashcard rotation progress kept.")
