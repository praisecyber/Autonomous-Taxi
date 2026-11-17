from dataclasses import FrozenInstanceError

import pytest

from taxi.latest_frame import LatestFrameBuffer


def test_fast_producer_keeps_one_latest_immutable_frame_and_no_backlog():
    clock = [10.0]
    buffer = LatestFrameBuffer(clock=lambda: clock[0], max_bytes=8)
    for sequence in range(1000):
        buffer.publish(str(sequence).encode(), source='simulated', sequence=sequence, captured_at=10)
    assert buffer.overwritten == 999
    frame = buffer.latest(consume=True)
    assert frame.sequence == 999 and frame.payload == b'999' and frame.received_at == 10
    assert buffer.latest() is None
    with pytest.raises(FrozenInstanceError):
        frame.payload = b'changed'


@pytest.mark.parametrize('override', [
    {'payload': b''}, {'payload': b'x' * 9}, {'payload': bytearray(b'x')},
    {'source': 'device'}, {'captured_at': 9.49}, {'captured_at': 10.01},
    {'captured_at': float('nan')}, {'captured_at': True},
    {'sequence': 1}, {'sequence': True}, {'sequence': -1},
])
def test_invalid_frame_clears_old_data_instead_of_appearing_healthy(override):
    buffer = LatestFrameBuffer(clock=lambda: 10, max_bytes=8)
    buffer.publish(b'valid', source='recorded', sequence=1, captured_at=10)
    arguments = dict(payload=b'new', source='recorded', sequence=2, captured_at=10)
    arguments.update(override)
    with pytest.raises(ValueError):
        buffer.publish(**arguments)
    assert buffer.latest() is None


def test_sample_age_not_delivery_time_and_explicit_session_reset():
    clock = [10.0]
    buffer = LatestFrameBuffer(clock=lambda: clock[0])
    buffer.publish(b'frame', source='recorded', sequence=10, captured_at=9.6)
    clock[0] = 10.11
    assert buffer.latest() is None
    with pytest.raises(ValueError):
        buffer.publish(b'replay', source='recorded', sequence=9, captured_at=10.11)
    buffer.reset()
    buffer.publish(b'new-session', source='simulated', sequence=0, captured_at=10.11)
    assert buffer.latest().payload == b'new-session'
    clock[0] = 9
    assert buffer.latest() is None
