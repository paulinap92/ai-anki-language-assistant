"""Conversation Practice transcript export helpers."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Mapping


ConversationEntry = tuple[str, str]


def safe_export_stem(value: str, *, fallback: str = "conversation") -> str:
    """Return a short filesystem-safe stem for conversation exports."""
    cleaned = re.sub(r"[^\w\-]+", "_", (value or "").strip(), flags=re.UNICODE)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_.-")
    return (cleaned[:60] or fallback).lower()


def default_conversation_export_name(
    *,
    language: str,
    topic: str,
    now: datetime | None = None,
    extension: str = ".md",
) -> str:
    timestamp = (now or datetime.now()).strftime("%Y-%m-%d_%H%M")
    subject = safe_export_stem(topic or language or "conversation")
    suffix = extension if extension.startswith(".") else f".{extension}"
    return f"conversation_{subject}_{timestamp}{suffix}"


def _metadata_lines(metadata: Mapping[str, str]) -> list[str]:
    return [f"{key}: {value}" for key, value in metadata.items() if str(value).strip()]


def render_conversation_text(
    entries: Iterable[ConversationEntry],
    *,
    metadata: Mapping[str, str],
    session_flashcards: Iterable[str] = (),
    new_candidates: Iterable[str] = (),
) -> str:
    """Render a portable plain-text Conversation Practice transcript."""
    lines = ["AI ANKI LANGUAGE ASSISTANT - CONVERSATION EXPORT", ""]
    lines.extend(_metadata_lines(metadata))
    flashcards = [item.strip() for item in session_flashcards if item and item.strip()]
    candidates = [item.strip() for item in new_candidates if item and item.strip()]
    if flashcards:
        lines.extend(["", f"SESSION FLASHCARDS ({len(flashcards)})", *[f"- {item}" for item in flashcards]])
    if candidates:
        lines.extend(["", f"NEW FLASHCARD CANDIDATES ({len(candidates)})", *[f"- {item}" for item in candidates]])
    lines.extend(["", "TRANSCRIPT", ""])
    for speaker, text in entries:
        clean_text = (text or "").strip()
        if not clean_text:
            continue
        lines.extend([speaker.strip() or "ENTRY", clean_text, ""])
    return "\n".join(lines).rstrip() + "\n"


def render_conversation_markdown(
    entries: Iterable[ConversationEntry],
    *,
    metadata: Mapping[str, str],
    session_flashcards: Iterable[str] = (),
    new_candidates: Iterable[str] = (),
) -> str:
    """Render a readable Markdown Conversation Practice transcript."""
    lines = ["# Conversation Practice export", ""]
    for key, value in metadata.items():
        clean = str(value).strip()
        if clean:
            lines.append(f"- **{key}:** {clean}")
    flashcards = [item.strip() for item in session_flashcards if item and item.strip()]
    candidates = [item.strip() for item in new_candidates if item and item.strip()]
    if flashcards:
        lines.extend(["", f"## Session flashcards ({len(flashcards)})", ""])
        lines.extend(f"- {item}" for item in flashcards)
    if candidates:
        lines.extend(["", f"## New flashcard candidates ({len(candidates)})", ""])
        lines.extend(f"- {item}" for item in candidates)
    lines.extend(["", "## Transcript", ""])
    for speaker, text in entries:
        clean_text = (text or "").strip()
        if not clean_text:
            continue
        lines.extend([f"### {speaker.strip() or 'Entry'}", "", clean_text, ""])
    return "\n".join(lines).rstrip() + "\n"


def write_conversation_export(
    path: Path,
    entries: Iterable[ConversationEntry],
    *,
    metadata: Mapping[str, str],
    session_flashcards: Iterable[str] = (),
    new_candidates: Iterable[str] = (),
) -> Path:
    """Write TXT or Markdown based on the selected filename extension."""
    suffix = path.suffix.casefold()
    if suffix not in {".txt", ".md", ".markdown"}:
        raise ValueError("Conversation export supports .txt, .md or .markdown files.")
    if suffix == ".txt":
        content = render_conversation_text(
            entries,
            metadata=metadata,
            session_flashcards=session_flashcards,
            new_candidates=new_candidates,
        )
    else:
        content = render_conversation_markdown(
            entries,
            metadata=metadata,
            session_flashcards=session_flashcards,
            new_candidates=new_candidates,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
