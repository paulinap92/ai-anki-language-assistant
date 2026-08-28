"""User-facing local / hybrid / BYOK configuration helpers.

The desktop app keeps secrets in a local ``.env`` file. This module never sends
keys anywhere; it only creates, imports, merges and inspects local configuration.
"""

from __future__ import annotations

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib import error, request


SETUP_MODE_LABELS = {
    "local": "Fully local",
    "hybrid": "Hybrid / BYOK",
    "api": "API / BYOK",
}

SUPPORTED_ENV_KEYS = {
    "AI_SETUP_MODE",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_IMPORT_MODEL",
    "GEMINI_MULTIMODAL_MODEL",
    "GEMINI_REVIEW_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_IMPORT_MODEL",
    "OPENAI_MULTIMODAL_MODEL",
    "OPENAI_REVIEW_MODEL",
    "OPENAI_PREMIUM_MODEL",
    "ANTHROPIC_API_KEY",
    "CLAUDE_API_KEY",
    "CLAUDE_MODEL",
    "CLAUDE_IMPORT_MODEL",
    "CLAUDE_REVIEW_MODEL",
    "CLAUDE_PREMIUM_MODEL",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "ANKI_CONNECT_URL",
    "ANKI_DECK_NAME",
    "DEFAULT_TARGET_LANGUAGE",
    "ELEVENLABS_API_KEY",
    "ELEVENLABS_TTS_MODEL",
    "ELEVENLABS_VOICE_ID",
    "OPENAI_TTS_MODEL",
    "OPENAI_TTS_VOICE",
    "GEMINI_TTS_MODEL",
    "GEMINI_TTS_VOICE",
    "PIPER_EXE_PATH",
    "PIPER_VOICE_EN",
    "PIPER_VOICE_ES",
    "PIPER_VOICE_PL",
    "PIPER_MODEL_PATH",
    "PIPER_VOICE_DIR",
    "AUDIO_CACHE_DIR",
    "STT_PROVIDER",
    "WHISPER_MODEL",
    "WHISPER_LANGUAGE",
    "MISTRAL_API_KEY",
    "MISTRAL_OCR_MODEL",
    "LANGSMITH_TRACING",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "LANGSMITH_ENDPOINT",
    "LANGSMITH_REDACT_INPUTS",
}

_ENV_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def normalize_setup_mode(value: str | None) -> str:
    text = (value or "hybrid").strip().casefold()
    aliases = {
        "local": "local",
        "fully local": "local",
        "offline": "local",
        "hybrid": "hybrid",
        "hybrid / byok": "hybrid",
        "byok": "hybrid",
        "local + api": "hybrid",
        "api": "api",
        "api / byok": "api",
        "cloud": "api",
    }
    return aliases.get(text, "hybrid")


def parse_env_text(text: str) -> dict[str, str]:
    """Parse simple KEY=value lines without evaluating shell syntax."""
    values: dict[str, str] = {}
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE_RE.match(raw_line)
        if not match:
            continue
        key, raw_value = match.groups()
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def read_env_values(path: str | Path) -> dict[str, str]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return parse_env_text(file_path.read_text(encoding="utf-8-sig"))


def _serialize_env_value(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    if any(ch.isspace() for ch in text) or "#" in text:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text


def merge_env_values(path: str | Path, updates: dict[str, str]) -> Path:
    """Merge values into .env while preserving unrelated lines and comments."""
    file_path = Path(path)
    existing_lines = file_path.read_text(encoding="utf-8-sig").splitlines() if file_path.exists() else []
    pending = dict(updates)
    output: list[str] = []
    for raw_line in existing_lines:
        match = _ENV_LINE_RE.match(raw_line)
        if match and match.group(1) in pending:
            key = match.group(1)
            output.append(f"{key}={_serialize_env_value(pending.pop(key))}")
        else:
            output.append(raw_line)
    if pending:
        if output and output[-1].strip():
            output.append("")
        output.append("# AI Anki user setup")
        for key, value in pending.items():
            output.append(f"{key}={_serialize_env_value(value)}")
    file_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    return file_path


def backup_env(path: str | Path) -> Path | None:
    file_path = Path(path)
    if not file_path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = file_path.with_name(f"{file_path.name}.backup_{stamp}")
    shutil.copy2(file_path, backup)
    return backup


def import_env_file(source: str | Path, destination: str | Path = ".env") -> tuple[Path, Path | None, int]:
    """Import supported app settings from another .env file.

    Existing destination values are backed up first. Unsupported variables from
    the source are ignored so an arbitrary project .env cannot overwrite unrelated
    process configuration.
    """
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError(source_path)
    values = read_env_values(source_path)
    filtered = {key: value for key, value in values.items() if key in SUPPORTED_ENV_KEYS}
    if not filtered:
        raise ValueError("The selected file does not contain supported AI Anki settings.")
    destination_path = Path(destination)
    backup = backup_env(destination_path)
    merge_env_values(destination_path, filtered)
    return destination_path, backup, len(filtered)


def starter_updates(mode: str) -> dict[str, str]:
    normalized = normalize_setup_mode(mode)
    common = {
        "AI_SETUP_MODE": normalized,
        "ANKI_CONNECT_URL": "http://localhost:8765",
        "ANKI_DECK_NAME": "AI Vocabulary",
        "DEFAULT_TARGET_LANGUAGE": "English",
        "AUDIO_CACHE_DIR": ".audio_cache",
        "STT_PROVIDER": "local_whisper",
        "WHISPER_MODEL": "small",
        "WHISPER_LANGUAGE": "",
    }
    if normalized in {"local", "hybrid"}:
        common.update(
            {
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "OLLAMA_MODEL": "gemma3:4b",
                "PIPER_EXE_PATH": "",
                "PIPER_VOICE_EN": "",
                "PIPER_VOICE_ES": "",
                "PIPER_VOICE_PL": "",
                "PIPER_MODEL_PATH": "",
                "PIPER_VOICE_DIR": "voices/piper",
            }
        )
    if normalized in {"api", "hybrid"}:
        common.update(
            {
                "OPENAI_API_KEY": "",
                "GEMINI_API_KEY": "",
                "ANTHROPIC_API_KEY": "",
                "ELEVENLABS_API_KEY": "",
                "MISTRAL_API_KEY": "",
            }
        )
    return common


def create_or_update_starter_env(mode: str, path: str | Path = ".env") -> Path:
    """Create a safe starter .env without overwriting existing non-empty secrets."""
    file_path = Path(path)
    current = read_env_values(file_path)
    updates = starter_updates(mode)
    merged: dict[str, str] = {}
    for key, default_value in updates.items():
        if key == "AI_SETUP_MODE":
            merged[key] = normalize_setup_mode(mode)
        elif key in current and current[key].strip():
            # Keep existing user values/API keys.
            continue
        else:
            merged[key] = default_value
    return merge_env_values(file_path, merged)


def configured_status(values: dict[str, str]) -> dict[str, bool]:
    """Return non-secret configured/missing flags for the setup screen."""
    nonempty = lambda key: bool((values.get(key) or "").strip())
    piper_dir = Path(values.get("PIPER_VOICE_DIR") or "voices/piper")
    has_piper_library = piper_dir.exists() and any(
        model.with_name(model.name + ".json").exists() for model in piper_dir.rglob("*.onnx")
    )
    return {
        "ollama": nonempty("OLLAMA_MODEL"),
        "whisper": (values.get("STT_PROVIDER") or "local_whisper").casefold() in {"local_whisper", "whisper", "faster_whisper"},
        "piper": nonempty("PIPER_MODEL_PATH") or has_piper_library or (nonempty("PIPER_EXE_PATH") and any(nonempty(k) for k in ("PIPER_VOICE_EN", "PIPER_VOICE_ES", "PIPER_VOICE_PL"))),
        "openai": nonempty("OPENAI_API_KEY"),
        "gemini": nonempty("GEMINI_API_KEY") or nonempty("GOOGLE_API_KEY"),
        "claude": nonempty("ANTHROPIC_API_KEY") or nonempty("CLAUDE_API_KEY"),
        "elevenlabs": nonempty("ELEVENLABS_API_KEY"),
        "mistral": nonempty("MISTRAL_API_KEY"),
    }


def check_ollama(base_url: str, model: str | None, timeout: float = 2.5) -> tuple[bool, str]:
    """Check whether Ollama is reachable and whether the configured model exists."""
    url = (base_url or "http://localhost:11434").rstrip("/") + "/api/tags"
    try:
        with request.urlopen(url, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (error.URLError, TimeoutError, OSError) as exc:
        return False, f"Ollama not reachable at {base_url}: {exc}"
    try:
        import json

        payload = json.loads(raw)
        names = [str(item.get("name") or "") for item in payload.get("models", []) if isinstance(item, dict)]
    except Exception:
        names = []
    if not model:
        return True, "Ollama is running; no OLLAMA_MODEL is configured yet."
    if model in names or any(name.split(":", 1)[0] == model.split(":", 1)[0] for name in names):
        return True, f"Ollama is running and {model} is available."
    if names:
        return False, f"Ollama is running, but {model} is not installed. Available: {', '.join(names[:8])}"
    return False, f"Ollama is running, but {model} was not found. Pull the model first."
