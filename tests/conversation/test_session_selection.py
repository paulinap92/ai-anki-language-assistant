import random

from src.conversation import (
    SELECTION_ANKI_DUE,
    SELECTION_CONTINUE_ROTATION,
    SELECTION_RANDOM,
    SELECTION_REPEAT_LAST,
    select_session_keys,
)


def test_continue_rotation_does_not_repeat_before_cycle_is_exhausted():
    keys = [f"note:{idx}" for idx in range(1, 8)]
    state = {}

    first, state = select_session_keys(
        keys,
        mode=SELECTION_CONTINUE_ROTATION,
        limit=3,
        state_entry=state,
        rng=random.Random(7),
    )
    second, state = select_session_keys(
        keys,
        mode=SELECTION_CONTINUE_ROTATION,
        limit=3,
        state_entry=state,
        rng=random.Random(8),
    )
    third, state = select_session_keys(
        keys,
        mode=SELECTION_CONTINUE_ROTATION,
        limit=3,
        state_entry=state,
        rng=random.Random(9),
    )

    assert len(first) == 3
    assert len(second) == 3
    assert len(third) == 1
    assert set(first).isdisjoint(second)
    assert set(first).isdisjoint(third)
    assert set(second).isdisjoint(third)
    assert set(first + second + third) == set(keys)


def test_continue_rotation_starts_a_new_cycle_only_after_exhaustion():
    keys = ["a", "b", "c"]
    first, state = select_session_keys(
        keys,
        mode=SELECTION_CONTINUE_ROTATION,
        limit=10,
        state_entry={},
        rng=random.Random(1),
    )
    second, state = select_session_keys(
        keys,
        mode=SELECTION_CONTINUE_ROTATION,
        limit=10,
        state_entry=state,
        rng=random.Random(2),
    )

    assert set(first) == set(keys)
    assert set(second) == set(keys)
    assert state["cycle"] == 2


def test_random_selection_does_not_consume_rotation_queue():
    keys = ["a", "b", "c", "d"]
    rotated, state = select_session_keys(
        keys,
        mode=SELECTION_CONTINUE_ROTATION,
        limit=2,
        state_entry={},
        rng=random.Random(3),
    )
    remaining_before = list(state["remaining"])

    random_pick, state = select_session_keys(
        keys,
        mode=SELECTION_RANDOM,
        limit=2,
        state_entry=state,
        rng=random.Random(4),
    )

    assert rotated
    assert random_pick
    assert state["remaining"] == remaining_before


def test_repeat_last_session_reuses_the_last_selected_keys():
    keys = ["a", "b", "c", "d"]
    selected, state = select_session_keys(
        keys,
        mode=SELECTION_RANDOM,
        limit=3,
        state_entry={},
        rng=random.Random(5),
    )
    repeated, _state = select_session_keys(
        keys,
        mode=SELECTION_REPEAT_LAST,
        limit=3,
        state_entry=state,
    )

    assert repeated == selected


def test_due_selection_uses_only_available_due_keys_and_keeps_order():
    keys = ["note:1", "note:2", "note:3", "note:4"]
    selected, _state = select_session_keys(
        keys,
        mode=SELECTION_ANKI_DUE,
        limit=2,
        state_entry={},
        due_keys=["note:4", "note:2", "missing"],
    )

    # Session order remains the stable deck/material order.
    assert selected == ["note:2", "note:4"]
