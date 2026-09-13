"""Online/local TTS voice library helpers.

The GUI deliberately keeps these network operations behind explicit user actions.
Piper voices are downloaded from the public rhasspy/piper-voices repository;
ElevenLabs voices are queried through the user's own API key.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
from typing import Any

import requests


PIPER_CATALOG_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json"
PIPER_RESOLVE_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"
ELEVENLABS_API_BASE = "https://api.elevenlabs.io"

LANGUAGE_FAMILY_BY_NAME = {
    "English": "en",
    "Spanish": "es",
    "Polish": "pl",
    "German": "de",
    "French": "fr",
    "Italian": "it",
    "Portuguese": "pt",
}


OPENAI_BUILTIN_VOICES: tuple[str, ...] = (
    "alloy", "ash", "ballad", "coral", "echo", "fable", "nova",
    "onyx", "sage", "shimmer", "verse", "marin", "cedar",
)

GEMINI_BUILTIN_VOICES: tuple[tuple[str, str], ...] = (
    ("Zephyr", "Bright"),
    ("Puck", "Upbeat"),
    ("Charon", "Informative"),
    ("Kore", "Firm"),
    ("Fenrir", "Excitable"),
    ("Leda", "Youthful"),
    ("Orus", "Firm"),
    ("Aoede", "Breezy"),
    ("Callirrhoe", "Easy-going"),
    ("Autonoe", "Bright"),
    ("Enceladus", "Breathy"),
    ("Iapetus", "Clear"),
    ("Umbriel", "Easy-going"),
    ("Algieba", "Smooth"),
    ("Despina", "Smooth"),
    ("Erinome", "Clear"),
    ("Algenib", "Gravelly"),
    ("Rasalgethi", "Informative"),
    ("Laomedeia", "Upbeat"),
    ("Achernar", "Soft"),
    ("Alnilam", "Firm"),
    ("Schedar", "Even"),
    ("Gacrux", "Mature"),
    ("Pulcherrima", "Forward"),
    ("Achird", "Friendly"),
    ("Zubenelgenubi", "Casual"),
    ("Vindemiatrix", "Gentle"),
    ("Sadachbia", "Lively"),
    ("Sadaltager", "Knowledgeable"),
    ("Sulafat", "Warm"),
)


@dataclass(frozen=True)
class VoiceLibraryItem:
    """One browsable voice from Piper or ElevenLabs."""

    provider: str
    key: str
    name: str
    language: str = ""
    locale: str = ""
    accent: str = ""
    gender: str = ""
    quality: str = ""
    description: str = ""
    preview_url: str = ""
    voice_id: str = ""
    public_owner_id: str = ""
    model_url: str = ""
    config_url: str = ""
    model_card_url: str = ""
    model_filename: str = ""
    config_filename: str = ""
    source_label: str = ""

    @property
    def display_name(self) -> str:
        bits = [self.name]
        if self.locale:
            bits.append(self.locale)
        if self.quality:
            bits.append(self.quality)
        return " · ".join(bit for bit in bits if bit)



def openai_builtin_voice_items(query: str = "") -> list[VoiceLibraryItem]:
    """Return OpenAI built-in TTS voices as browsable library items."""
    needle = query.strip().casefold()
    items: list[VoiceLibraryItem] = []
    for voice in OPENAI_BUILTIN_VOICES:
        label = f"OpenAI · {voice.title()}"
        description = "Built-in OpenAI TTS voice."
        quality = "recommended" if voice in {"marin", "cedar"} else "built-in"
        if voice in {"marin", "cedar"}:
            description += " OpenAI recommends Marin and Cedar for best quality."
        haystack = f"{voice} {label} {quality} {description}".casefold()
        if needle and needle not in haystack:
            continue
        items.append(
            VoiceLibraryItem(
                provider="OpenAI TTS",
                key=voice,
                name=label,
                language="Multilingual",
                locale="auto",
                quality=quality,
                description=description,
                voice_id=voice,
                source_label="OpenAI built-in voices",
            )
        )
    return items


def gemini_builtin_voice_items(query: str = "") -> list[VoiceLibraryItem]:
    """Return Gemini TTS voices as browsable library items."""
    needle = query.strip().casefold()
    items: list[VoiceLibraryItem] = []
    for voice, style in GEMINI_BUILTIN_VOICES:
        label = f"Gemini · {voice} — {style}"
        description = f"Gemini TTS built-in voice: {style}."
        haystack = f"{voice} {style} {label} {description}".casefold()
        if needle and needle not in haystack:
            continue
        items.append(
            VoiceLibraryItem(
                provider="Gemini TTS",
                key=voice,
                name=label,
                language="Multilingual",
                locale="auto",
                quality=style,
                description=description,
                voice_id=voice,
                source_label="Gemini built-in voices",
            )
        )
    return items

def piper_voice_directory() -> Path:
    """Return the writable directory used for user-installed Piper voices."""
    return Path(os.getenv("PIPER_VOICE_DIR") or "voices/piper")


def _response_json(response: requests.Response) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Voice provider returned an unexpected response.")
    return payload


def fetch_piper_catalog(
    *,
    language_name: str | None = None,
    query: str = "",
    timeout: float = 30.0,
) -> list[VoiceLibraryItem]:
    """Fetch and filter the public Piper voice catalog."""
    response = requests.get(PIPER_CATALOG_URL, timeout=timeout)
    payload = _response_json(response)
    requested_language = (language_name or "").strip()
    family = LANGUAGE_FAMILY_BY_NAME.get(requested_language, "")
    requested_language_folded = requested_language.casefold()
    needle = query.strip().casefold()
    results: list[VoiceLibraryItem] = []

    for key, raw in payload.items():
        if not isinstance(raw, dict):
            continue
        language = raw.get("language") if isinstance(raw.get("language"), dict) else {}
        language_family = str(language.get("family") or "")
        language_english = str(language.get("name_english") or "")
        if family and language_family != family:
            continue
        if requested_language and not family and language_english.casefold() != requested_language_folded:
            continue

        name = str(raw.get("name") or key)
        locale = str(language.get("code") or "")
        quality = str(raw.get("quality") or "")
        haystack = " ".join((key, name, locale, language_english, quality)).casefold()
        if needle and needle not in haystack:
            continue

        files = raw.get("files") if isinstance(raw.get("files"), dict) else {}
        model_rel = next((str(path) for path in files if str(path).endswith(".onnx")), "")
        config_rel = next((str(path) for path in files if str(path).endswith(".onnx.json")), "")
        card_rel = next((str(path) for path in files if str(path).endswith("MODEL_CARD")), "")
        if not model_rel or not config_rel:
            continue
        folder_rel = model_rel.rsplit("/", 1)[0]
        preview_rel = f"{folder_rel}/samples/speaker_0.mp3"

        results.append(
            VoiceLibraryItem(
                provider="Piper",
                key=str(key),
                name=name,
                language=language_english,
                locale=locale,
                quality=quality,
                description=f"{language_english} · {str(language.get('country_english') or '')}".strip(" ·"),
                preview_url=f"{PIPER_RESOLVE_BASE}/{preview_rel}",
                model_url=f"{PIPER_RESOLVE_BASE}/{model_rel}",
                config_url=f"{PIPER_RESOLVE_BASE}/{config_rel}",
                model_card_url=f"{PIPER_RESOLVE_BASE}/{card_rel}" if card_rel else "",
                model_filename=Path(model_rel).name,
                config_filename=Path(config_rel).name,
                source_label="Piper / rhasspy-piper-voices",
            )
        )

    return sorted(results, key=lambda item: (item.language, item.locale, item.name, item.quality))



def fetch_piper_language_names(timeout: float = 30.0) -> list[str]:
    """Return every language currently exposed by the public Piper catalog."""
    response = requests.get(PIPER_CATALOG_URL, timeout=timeout)
    payload = _response_json(response)
    names: set[str] = set()
    for raw in payload.values():
        if not isinstance(raw, dict):
            continue
        language = raw.get("language") if isinstance(raw.get("language"), dict) else {}
        name = str(language.get("name_english") or "").strip()
        if name:
            names.add(name)
    return sorted(names, key=str.casefold)

def _download_file(url: str, destination: Path, *, timeout: float = 180.0) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".part")
    try:
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with tmp.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        tmp.replace(destination)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return destination


def download_piper_voice(item: VoiceLibraryItem, directory: Path | None = None) -> Path:
    """Download a Piper ONNX model/config pair and return the model path."""
    if item.provider != "Piper" or not item.model_url or not item.config_url:
        raise ValueError("Selected item is not a downloadable Piper voice.")
    root = directory or piper_voice_directory()
    target_dir = root / item.key
    model_path = _download_file(item.model_url, target_dir / item.model_filename)
    try:
        _download_file(item.config_url, target_dir / item.config_filename)
        if item.model_card_url:
            try:
                _download_file(item.model_card_url, target_dir / "MODEL_CARD", timeout=30.0)
            except Exception:
                # Voice stays usable even when the optional model card cannot be fetched.
                pass
    except Exception:
        model_path.unlink(missing_ok=True)
        raise
    return model_path


def import_piper_voice(model_path: Path, directory: Path | None = None) -> Path:
    """Copy an existing Piper .onnx + .onnx.json pair into the app voice library."""
    source = Path(model_path)
    if source.suffix.casefold() != ".onnx" or not source.is_file():
        raise ValueError("Choose a Piper .onnx voice model.")
    config = source.with_name(source.name + ".json")
    if not config.exists():
        raise FileNotFoundError(f"Matching Piper config not found: {config.name}")
    root = directory or piper_voice_directory()
    target_dir = root / "custom" / source.stem
    target_dir.mkdir(parents=True, exist_ok=True)
    target_model = target_dir / source.name
    shutil.copy2(source, target_model)
    shutil.copy2(config, target_dir / config.name)
    model_card = source.parent / "MODEL_CARD"
    if model_card.exists():
        shutil.copy2(model_card, target_dir / "MODEL_CARD")
    return target_model


def installed_piper_models(directory: Path | None = None) -> list[Path]:
    """Return valid installed Piper models with their matching JSON config."""
    root = directory or piper_voice_directory()
    if not root.exists():
        return []
    models: list[Path] = []
    for model in root.rglob("*.onnx"):
        if model.with_name(model.name + ".json").exists():
            models.append(model)
    return sorted(models, key=lambda path: path.name.casefold())


def piper_voice_metadata(model_path: str | Path) -> dict[str, str]:
    """Read safe display metadata from a Piper config file."""
    model = Path(model_path)
    config = model.with_name(model.name + ".json")
    result = {
        "label": model.stem,
        "language": "",
        "language_family": "",
        "locale": "",
        "quality": "",
        "name": model.stem,
    }
    if not config.exists():
        return result
    try:
        payload = json.loads(config.read_text(encoding="utf-8"))
    except Exception:
        return result
    language = payload.get("language") if isinstance(payload.get("language"), dict) else {}
    locale = str(language.get("code") or "")
    language_name = str(language.get("name_english") or "")
    family = str(language.get("family") or "")
    quality = str((payload.get("audio") or {}).get("quality") or "") if isinstance(payload.get("audio"), dict) else ""
    dataset = str(payload.get("dataset") or model.stem)
    bits = [language_name or locale, f"({locale})" if locale else "", dataset, quality]
    label = " ".join(bits[:2]).strip()
    tail = " · ".join(bit for bit in bits[2:] if bit)
    if tail:
        label = f"{label} · {tail}" if label else tail
    return {
        "label": label or model.stem,
        "language": language_name,
        "language_family": family,
        "locale": locale,
        "quality": quality,
        "name": dataset,
    }


def fetch_elevenlabs_shared_voices(
    api_key: str,
    *,
    language_name: str | None = None,
    query: str = "",
    page_size: int = 50,
    timeout: float = 30.0,
) -> list[VoiceLibraryItem]:
    """Search ElevenLabs' shared Voice Library using the user's API key."""
    if not api_key.strip():
        raise ValueError("ELEVENLABS_API_KEY is not configured.")
    params: dict[str, Any] = {
        "page_size": max(1, min(int(page_size), 100)),
        "sort": "trending",
    }
    family = LANGUAGE_FAMILY_BY_NAME.get((language_name or "").strip(), "")
    if family:
        params["language"] = family
    if query.strip():
        params["search"] = query.strip()
    response = requests.get(
        f"{ELEVENLABS_API_BASE}/v1/shared-voices",
        params=params,
        headers={"xi-api-key": api_key},
        timeout=timeout,
    )
    payload = _response_json(response)
    results: list[VoiceLibraryItem] = []
    for raw in payload.get("voices", []):
        if not isinstance(raw, dict):
            continue
        voice_id = str(raw.get("voice_id") or "")
        if not voice_id:
            continue
        results.append(
            VoiceLibraryItem(
                provider="ElevenLabs shared",
                key=voice_id,
                name=str(raw.get("name") or voice_id),
                language=str(raw.get("language") or ""),
                locale=str((raw.get("verified_languages") or [{}])[0].get("locale") or "")
                if isinstance(raw.get("verified_languages"), list) and raw.get("verified_languages")
                else "",
                accent=str(raw.get("accent") or ""),
                gender=str(raw.get("gender") or ""),
                quality=str(raw.get("category") or ""),
                description=str(raw.get("description") or ""),
                preview_url=str(raw.get("preview_url") or ""),
                voice_id=voice_id,
                public_owner_id=str(raw.get("public_owner_id") or ""),
                source_label="ElevenLabs Voice Library",
            )
        )
    return results


def fetch_elevenlabs_my_voices(
    api_key: str,
    *,
    query: str = "",
    page_size: int = 100,
    timeout: float = 30.0,
) -> list[VoiceLibraryItem]:
    """List voices already available in the user's ElevenLabs account/workspace."""
    if not api_key.strip():
        raise ValueError("ELEVENLABS_API_KEY is not configured.")
    params: dict[str, Any] = {"page_size": max(1, min(int(page_size), 100))}
    if query.strip():
        params["search"] = query.strip()
    response = requests.get(
        f"{ELEVENLABS_API_BASE}/v2/voices",
        params=params,
        headers={"xi-api-key": api_key},
        timeout=timeout,
    )
    payload = _response_json(response)
    results: list[VoiceLibraryItem] = []
    for raw in payload.get("voices", []):
        if not isinstance(raw, dict):
            continue
        voice_id = str(raw.get("voice_id") or "")
        if not voice_id:
            continue
        labels = raw.get("labels") if isinstance(raw.get("labels"), dict) else {}
        preview_url = str(raw.get("preview_url") or "")
        verified = raw.get("verified_languages") if isinstance(raw.get("verified_languages"), list) else []
        if not preview_url and verified and isinstance(verified[0], dict):
            preview_url = str(verified[0].get("preview_url") or "")
        results.append(
            VoiceLibraryItem(
                provider="ElevenLabs mine",
                key=voice_id,
                name=str(raw.get("name") or voice_id),
                language=str(labels.get("language") or (verified[0].get("language") if verified and isinstance(verified[0], dict) else "")),
                locale=str(verified[0].get("locale") or "") if verified and isinstance(verified[0], dict) else "",
                accent=str(labels.get("accent") or ""),
                gender=str(labels.get("gender") or ""),
                quality=str(raw.get("category") or ""),
                description=str(raw.get("description") or ""),
                preview_url=preview_url,
                voice_id=voice_id,
                source_label="ElevenLabs My Voices",
            )
        )
    return results


def fetch_elevenlabs_voice_preview(api_key: str, voice_id: str, timeout: float = 30.0) -> str:
    """Resolve a preview URL for an ElevenLabs voice."""
    response = requests.get(
        f"{ELEVENLABS_API_BASE}/v1/voices/{voice_id}",
        headers={"xi-api-key": api_key},
        timeout=timeout,
    )
    payload = _response_json(response)
    preview = str(payload.get("preview_url") or "")
    if preview:
        return preview
    verified = payload.get("verified_languages") if isinstance(payload.get("verified_languages"), list) else []
    for item in verified:
        if isinstance(item, dict) and item.get("preview_url"):
            return str(item["preview_url"])
    raise ValueError("This ElevenLabs voice does not expose a preview sample.")


def add_elevenlabs_shared_voice(
    api_key: str,
    item: VoiceLibraryItem,
    *,
    new_name: str | None = None,
    timeout: float = 30.0,
) -> str:
    """Add a shared ElevenLabs voice to the user's own voice collection."""
    if not api_key.strip():
        raise ValueError("ELEVENLABS_API_KEY is not configured.")
    if not item.public_owner_id or not item.voice_id:
        raise ValueError("Selected shared voice is missing its owner/voice identifier.")
    response = requests.post(
        f"{ELEVENLABS_API_BASE}/v1/voices/add/{item.public_owner_id}/{item.voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={"new_name": (new_name or item.name).strip() or item.name, "bookmarked": True},
        timeout=timeout,
    )
    payload = _response_json(response)
    voice_id = str(payload.get("voice_id") or item.voice_id)
    return voice_id


def download_preview_audio(url: str, destination: Path, timeout: float = 60.0) -> Path:
    """Download a provider's public voice preview for in-app playback."""
    if not url.strip():
        raise ValueError("This voice has no preview sample.")
    return _download_file(url, destination, timeout=timeout)


def elevenlabs_registry_path() -> Path:
    """Return the local non-secret registry of user-selected ElevenLabs voices."""
    return Path(os.getenv("ELEVENLABS_VOICE_REGISTRY") or "voices/elevenlabs.json")


def load_elevenlabs_registry(path: Path | None = None) -> list[dict[str, str]]:
    registry = path or elevenlabs_registry_path()
    if not registry.exists():
        return []
    try:
        payload = json.loads(registry.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    rows: list[dict[str, str]] = []
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        label = str(raw.get("label") or "").strip()
        voice_id = str(raw.get("voice_id") or "").strip()
        if not label or not voice_id:
            continue
        rows.append({"label": label, "voice_id": voice_id, "language": str(raw.get("language") or "")})
    return rows


def save_elevenlabs_registry_voice(
    label: str,
    voice_id: str,
    language: str = "",
    path: Path | None = None,
) -> Path:
    """Remember a selected ElevenLabs voice ID locally without storing the API key."""
    registry = path or elevenlabs_registry_path()
    rows = load_elevenlabs_registry(registry)
    normalized = label.strip()
    rows = [row for row in rows if row["label"] != normalized and row["voice_id"] != voice_id]
    rows.append({"label": normalized, "voice_id": voice_id.strip(), "language": language.strip()})
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return registry
