from types import SimpleNamespace
import sys

import numpy as np
import pytest

from src.speech import playback
from src.speech.playback import AudioPlaybackError, InternalAudioPlayer, list_output_devices


class PortAudioError(Exception):
    pass


@pytest.fixture
def audio_backend(monkeypatch, tmp_path):
    devices = [
        dict(name="Microphone", hostapi=0, max_output_channels=0),
        dict(name="Speakers", hostapi=0, max_output_channels=2),
        dict(name="Speakers", hostapi=1, max_output_channels=2),
        dict(name="Headphones", hostapi=1, max_output_channels=2),
    ]
    calls, checked = [], []
    failing, unsupported = set(), set()

    def play(data, rate, **kwargs):
        calls.append((rate, kwargs))
        if kwargs["device"] in failing:
            raise PortAudioError("Unanticipated host error -9999 MME error 1")

    def check(**kwargs):
        checked.append(kwargs)
        if kwargs["device"] in unsupported:
            raise PortAudioError("Unsupported sample rate")

    sd = SimpleNamespace(
        PortAudioError=PortAudioError,
        default=SimpleNamespace(device=(-1, 1)),
        query_devices=lambda: devices,
        query_hostapis=lambda: [
            dict(name="MME", default_output_device=1),
            dict(name="Windows WASAPI", default_output_device=2),
        ],
        WasapiSettings=lambda **kwargs: kwargs,
        check_output_settings=check, play=play, stop=lambda: None,
        wait=lambda: None,
    )
    monkeypatch.setitem(sys.modules, "sounddevice", sd)
    monkeypatch.setitem(sys.modules, "soundfile", SimpleNamespace(
        read=lambda *args, **kwargs: (np.zeros((16, 1), dtype="float32"), 24000),
    ))
    monkeypatch.setattr(playback.sys, "platform", "win32")
    path = tmp_path / "preview.wav"
    path.write_bytes(b"audio")
    return SimpleNamespace(sd=sd, devices=devices, calls=calls, checked=checked,
                           failing=failing, unsupported=unsupported, path=path)


def test_only_output_devices_are_listed(audio_backend):
    devices = list_output_devices()
    assert [d.index for d in devices] == [1, 2, 3]
    assert devices[1].host_api == "Windows WASAPI"


def test_windows_automatic_uses_shared_wasapi_and_file_format(audio_backend):
    player = InternalAudioPlayer()
    result = player.play(audio_backend.path)
    assert result.device.index == 2
    assert not result.used_fallback
    rate, kwargs = audio_backend.calls[0]
    assert rate == 24000
    assert kwargs["blocking"] is False
    assert kwargs["extra_settings"] == dict(exclusive=False, auto_convert=True)
    assert audio_backend.checked[0]["channels"] == 1
    assert audio_backend.checked[0]["dtype"] == "float32"
    assert player.current_path == audio_backend.path


def test_saved_device_is_resolved_by_name_after_indices_change(audio_backend):
    player = InternalAudioPlayer()
    player.set_output_device("Headphones", "Windows WASAPI")
    audio_backend.devices.insert(1, dict(name="New output", hostapi=0, max_output_channels=2))
    result = player.play(audio_backend.path)
    assert result.device.index == 4
    assert not result.used_fallback


def test_explicit_mme_is_respected(audio_backend):
    player = InternalAudioPlayer()
    player.set_output_device("Speakers", "MME")
    result = player.play(audio_backend.path)
    assert result.device.index == 1
    assert audio_backend.calls[0][1]["extra_settings"] is None


def test_missing_selected_device_falls_back_without_losing_preference(audio_backend):
    player = InternalAudioPlayer()
    player.set_output_device("Unplugged USB", "Windows WASAPI")
    result = player.play(audio_backend.path)
    assert result.used_fallback
    assert result.device.index == 2
    assert player._device_name == "Unplugged USB"


def test_runtime_open_failure_falls_back_after_successful_preflight(audio_backend):
    audio_backend.failing.add(2)
    player = InternalAudioPlayer()
    result = player.play(audio_backend.path)
    assert [c[1]["device"] for c in audio_backend.calls] == [2, 1]
    assert result.used_fallback
    assert result.device.index == 1


def test_unsupported_format_skips_device(audio_backend):
    audio_backend.unsupported.add(2)
    result = InternalAudioPlayer().play(audio_backend.path)
    assert result.device.index == 1
    assert [c[1]["device"] for c in audio_backend.calls] == [1]


def test_all_outputs_fail_with_friendly_error_and_clean_state(audio_backend):
    audio_backend.failing.update({1, 2, 3})
    player = InternalAudioPlayer()
    player.set_output_device("Headphones", "Windows WASAPI")
    with pytest.raises(AudioPlaybackError) as caught:
        player.play(audio_backend.path)
    assert [c[1]["device"] for c in audio_backend.calls] == [3, 2, 1]
    assert "Output device" in str(caught.value)
    assert "-9999" not in str(caught.value)
    assert isinstance(caught.value.__cause__, PortAudioError)
    assert player.current_path is None
    assert player._data is None


def test_no_outputs_does_not_try_a_random_device(audio_backend):
    audio_backend.devices.clear()
    with pytest.raises(AudioPlaybackError):
        InternalAudioPlayer().play(audio_backend.path)
    assert not audio_backend.calls


def test_non_windows_keeps_system_default(audio_backend, monkeypatch):
    monkeypatch.setattr(playback.sys, "platform", "linux")
    result = InternalAudioPlayer().play(audio_backend.path)
    assert result.device.index == 1


def test_stop_cancels_pending_decode_and_old_stop_cannot_cancel_new_play(audio_backend):
    player = InternalAudioPlayer()
    old = player.reserve_request()
    stop = player.reserve_request()
    player.stop(request_id=stop)
    assert player.play(audio_backend.path, request_id=old) is None
    new = player.reserve_request()
    player.stop(request_id=stop)
    assert player.play(audio_backend.path, request_id=new) is not None
    assert len(audio_backend.calls) == 1
