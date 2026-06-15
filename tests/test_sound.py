"""音效波形合成的回归测试（纯函数，无需音频设备）。"""

import numpy as np

from core.sound import EVENT_NOTES, SAMPLE_RATE, render_event_samples


def test_render_shape_and_dtype():
    out = render_event_samples([(440, 0.05)], sample_rate=SAMPLE_RATE)
    assert out.dtype == np.int16
    assert out.ndim == 2 and out.shape[1] == 2  # 立体声
    assert out.shape[0] == int(SAMPLE_RATE * 0.05)
    assert np.abs(out).max() > 0  # 非静音


def test_render_concatenates_notes():
    notes = [(440, 0.05), (660, 0.05), (880, 0.05)]
    out = render_event_samples(notes, sample_rate=SAMPLE_RATE)
    assert out.shape[0] == sum(int(SAMPLE_RATE * d) for _, d in notes)
    # 左右声道一致（单声道复制为立体声）
    assert np.array_equal(out[:, 0], out[:, 1])


def test_render_empty_is_safe():
    out = render_event_samples([])
    assert out.shape[0] >= 1 and out.shape[1] == 2


def test_all_event_notes_render():
    for name, notes in EVENT_NOTES.items():
        out = render_event_samples(notes)
        assert out.shape[0] > 0, name
        assert np.abs(out).max() > 0, name
