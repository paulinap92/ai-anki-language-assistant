"""Session selection and persistent rotation helpers for Conversation Practice."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Iterable, MutableMapping, Sequence


SELECTION_CONTINUE_ROTATION = "Continue rotation"
SELECTION_ANKI_DUE = "Anki due cards"
SELECTION_RANDOM = "Random cards"
SELECTION_REPEAT_LAST = "Repeat last session"
SELECTION_MODES = [
    SELECTION_CONTINUE_ROTATION,
    SELECTION_ANKI_DUE,
    SELECTION_RANDOM,
    SELECTION_REPEAT_LAST,
]


def _unique(values: Iterable[object]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = str(value or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def load_rotation_state(path: Path) -> dict[str, dict[str, object]]:
    """Load local per-source rotation state, ignoring malformed runtime data."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, dict[str, object]] = {}
    for source_key, raw_entry in payload.items():
        if isinstance(source_key, str) and isinstance(raw_entry, dict):
            result[source_key] = dict(raw_entry)
    return result


def save_rotation_state(path: Path, state: MutableMapping[str, dict[str, object]]) -> None:
    """Persist local rotation progress without making it part of a release package."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temp_path.replace(path)


def select_session_keys(
    available_keys: Sequence[object],
    *,
    mode: str,
    limit: int,
    state_entry: MutableMapping[str, object] | None = None,
    due_keys: Sequence[object] = (),
    rng: random.Random | None = None,
) -> tuple[list[str], dict[str, object]]:
    """Select one session while keeping strict no-repeat rotation semantics.

    ``Continue rotation`` consumes a shuffled queue and starts a new shuffled
    cycle only after the current cycle is exhausted. ``Random cards`` and
    ``Anki due cards`` do not consume the rotation queue. Every successful mode
    stores ``last_session`` so it can be deliberately repeated later.
    """
    available = _unique(available_keys)
    safe_limit = max(1, int(limit))
    entry = dict(state_entry or {})
    randomizer = rng or random.Random()

    known = _unique(entry.get("known", [])) if isinstance(entry.get("known", []), list) else []
    remaining = (
        _unique(entry.get("remaining", []))
        if isinstance(entry.get("remaining", []), list)
        else []
    )
    last_session = (
        _unique(entry.get("last_session", []))
        if isinstance(entry.get("last_session", []), list)
        else []
    )
    cycle = int(entry.get("cycle", 0) or 0)

    available_set = set(available)
    remaining = [key for key in remaining if key in available_set]
    last_session = [key for key in last_session if key in available_set]

    # New cards join the unfinished cycle instead of waiting for a full reset.
    known_set = set(known)
    new_keys = [key for key in available if key not in known_set]
    if new_keys:
        randomizer.shuffle(new_keys)
        remaining.extend(key for key in new_keys if key not in set(remaining))
    known = list(available)

    selected: list[str]
    if mode == SELECTION_REPEAT_LAST:
        selected = last_session[:safe_limit]
    elif mode == SELECTION_ANKI_DUE:
        due_set = set(_unique(due_keys))
        selected = [key for key in available if key in due_set][:safe_limit]
        if selected:
            last_session = list(selected)
    elif mode == SELECTION_RANDOM:
        if len(available) <= safe_limit:
            selected = list(available)
            randomizer.shuffle(selected)
        else:
            selected = randomizer.sample(available, safe_limit)
        if selected:
            last_session = list(selected)
    else:
        # Continue rotation is the default and the only mode that consumes the queue.
        if not remaining and available:
            remaining = list(available)
            randomizer.shuffle(remaining)
            cycle += 1
        elif cycle <= 0 and available:
            cycle = 1
        selected = remaining[:safe_limit]
        remaining = remaining[len(selected) :]
        if selected:
            last_session = list(selected)

    updated = {
        "known": known,
        "remaining": remaining,
        "last_session": last_session,
        "cycle": cycle,
    }
    return selected, updated
