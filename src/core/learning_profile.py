"""Persistent learner profile used as the single source of language settings.

The profile intentionally contains learning preferences only. Provider/API setup
remains in ``.env`` and the Setup tab so language choices are not duplicated
throughout the application.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


DEFAULT_PROFILE_PATH = Path("user_profile.json")


@dataclass(frozen=True)
class LearningProfile:
    learning_language: str
    level: str
    support_language: str

    @property
    def is_complete(self) -> bool:
        return bool(
            self.learning_language.strip()
            and self.level.strip()
            and self.support_language.strip()
        )

    @property
    def summary(self) -> str:
        return (
            f"{self.learning_language.strip()} · {self.level.strip()} · "
            f"{self.support_language.strip()} support"
        )


def load_learning_profile(path: str | Path = DEFAULT_PROFILE_PATH) -> LearningProfile | None:
    file_path = Path(path)
    if not file_path.exists():
        return None
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    profile = LearningProfile(
        learning_language=str(payload.get("learning_language") or "").strip(),
        level=str(payload.get("level") or "").strip(),
        support_language=str(payload.get("support_language") or "").strip(),
    )
    return profile if profile.is_complete else None


def save_learning_profile(
    profile: LearningProfile,
    path: str | Path = DEFAULT_PROFILE_PATH,
) -> Path:
    if not profile.is_complete:
        raise ValueError("Learning profile is incomplete.")
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(
        json.dumps(asdict(profile), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return file_path
