from pathlib import Path

from src.core.user_setup import normalize_setup_mode


def test_setup_mode_label_mapping() -> None:
    assert normalize_setup_mode("Fully local") == "local"
    assert normalize_setup_mode("Hybrid / BYOK") == "hybrid"
    assert normalize_setup_mode("API / BYOK") == "api"


def test_setup_tab_is_present_in_modern_gui_source() -> None:
    text = Path("src/ui/modern_gui.py").read_text(encoding="utf-8")
    assert '"Setup"' in text
    assert "Create / update .env" in text
    assert "Import .env" in text
    assert "Reload configuration" in text
    assert "Check Ollama" in text


def test_local_requirements_do_not_pull_cloud_ai_sdks() -> None:
    text = Path("requirements-local.txt").read_text(encoding="utf-8").casefold()
    assert "openai" not in text
    assert "google-genai" not in text
    assert "anthropic" not in text
    assert "mistralai" not in text
    assert "langsmith" not in text


def test_hybrid_requirements_include_local_and_cloud_sdks() -> None:
    text = Path("requirements-hybrid.txt").read_text(encoding="utf-8").casefold()
    assert "-r requirements-local.txt" in text
    assert "openai" in text
    assert "google-genai" in text
    assert "anthropic" in text
