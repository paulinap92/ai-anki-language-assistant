from pathlib import Path


def test_first_profile_startup_does_not_use_nested_wait_loop() -> None:
    source = Path("src/ui/modern_gui.py").read_text(encoding="utf-8")
    start = source.index("def _show_first_learning_profile_setup")
    end = source.index("def _apply_learning_profile", start)
    block = source[start:end]
    assert "self._root.wait_variable(" not in block
    assert "self._root.wait_window(" not in block
    assert "after_idle(reveal)" in block


def test_constructor_returns_to_mainloop_when_profile_is_missing() -> None:
    source = Path("src/ui/modern_gui.py").read_text(encoding="utf-8")
    assert "self._show_first_learning_profile_setup(profile_seed)\n            return" in source
    assert 'STARTUP PROFILE REQUIRED: showing non-blocking onboarding' in source
    assert 'STARTUP MAIN UI BUILT AFTER PROFILE' in source
