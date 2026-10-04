from pathlib import Path

from src.core.user_setup import (
    configured_status,
    create_or_update_starter_env,
    import_env_file,
    normalize_setup_mode,
    read_env_values,
)


def test_normalize_setup_mode_labels() -> None:
    assert normalize_setup_mode("Fully local") == "local"
    assert normalize_setup_mode("Hybrid / BYOK") == "hybrid"
    assert normalize_setup_mode("API / BYOK") == "api"


def test_starter_env_preserves_existing_user_secret(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=keep-me\nOLLAMA_MODEL=my-local-model\n", encoding="utf-8")

    create_or_update_starter_env("Hybrid / BYOK", env_path)
    values = read_env_values(env_path)

    assert values["AI_SETUP_MODE"] == "hybrid"
    assert values["OPENAI_API_KEY"] == "keep-me"
    assert values["OLLAMA_MODEL"] == "my-local-model"
    assert values["STT_PROVIDER"] == "local_whisper"


def test_import_env_only_merges_supported_app_values(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    source.write_text(
        "OPENAI_API_KEY=user-key\nAI_SETUP_MODE=api\nUNRELATED_DATABASE_PASSWORD=do-not-import\n",
        encoding="utf-8",
    )
    destination = tmp_path / ".env"
    destination.write_text("ANKI_DECK_NAME=Existing\n", encoding="utf-8")

    _, backup, count = import_env_file(source, destination)
    values = read_env_values(destination)

    assert count == 2
    assert backup is not None and backup.exists()
    assert values["OPENAI_API_KEY"] == "user-key"
    assert values["AI_SETUP_MODE"] == "api"
    assert values["ANKI_DECK_NAME"] == "Existing"
    assert "UNRELATED_DATABASE_PASSWORD" not in values


def test_configured_status_does_not_expose_secret_values() -> None:
    status = configured_status(
        {
            "OPENAI_API_KEY": "super-secret",
            "OLLAMA_MODEL": "gemma3:4b",
            "STT_PROVIDER": "local_whisper",
        }
    )
    assert status["openai"] is True
    assert status["ollama"] is True
    assert status["whisper"] is True


def test_starter_env_includes_free_cloud_provider_slots(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"

    create_or_update_starter_env("API / BYOK", env_path)
    values = read_env_values(env_path)

    assert values["OPENROUTER_API_KEY"] == ""
    assert values["OPENROUTER_MODEL"] == "openrouter/free"
    assert values["GROQ_API_KEY"] == ""
    assert values["GROQ_MODEL"] == "openai/gpt-oss-20b"
    assert values["GROQ_IMPORT_MODEL"] == "openai/gpt-oss-20b"
    assert values["GROQ_REVIEW_MODEL"] == "openai/gpt-oss-20b"
    assert values["GROQ_STT_MODEL"] == "whisper-large-v3-turbo"


def test_configured_status_recognizes_openrouter_and_groq() -> None:
    status = configured_status(
        {
            "OPENROUTER_API_KEY": "router-secret",
            "GROQ_API_KEY": "groq-secret",
            "STT_PROVIDER": "groq",
        }
    )

    assert status["openrouter"] is True
    assert status["groq"] is True
    assert status["groq_stt"] is True
