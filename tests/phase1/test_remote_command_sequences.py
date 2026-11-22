"""Remote command sequence tests without sending commands to hardware."""

import asyncio

from ucapi import StatusCodes

from intg_monoprice_htp1.remote import HTP1Remote


def make_remote():
    # These tests exercise the command-sequencing methods only; no framework
    # entity registration or physical Remote is required.
    remote = object.__new__(HTP1Remote)
    remote._device = object()
    return remote


def test_command_sequence_repeats_in_order_and_delays_between_sends(monkeypatch):
    async def exercise():
        remote = make_remote()
        sent = []
        delays = []

        async def send_single(command):
            sent.append(command)
            return StatusCodes.OK

        async def fake_sleep(delay):
            delays.append(delay)

        remote._send_single = send_single
        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        result = await remote._send_commands(["A", "B"], repeat=2, delay=0.025)

        assert result == StatusCodes.OK
        assert sent == ["A", "A", "B", "B"]
        assert delays == [0.025, 0.025, 0.025]

    asyncio.run(exercise())


def test_command_sequence_stops_on_first_failed_command(monkeypatch):
    async def exercise():
        remote = make_remote()
        sent = []
        delays = []

        async def send_single(command):
            sent.append(command)
            return StatusCodes.SERVER_ERROR if command == "B" else StatusCodes.OK

        async def fake_sleep(delay):
            delays.append(delay)

        remote._send_single = send_single
        monkeypatch.setattr(asyncio, "sleep", fake_sleep)

        result = await remote._send_commands(["A", "B", "C"], repeat=2, delay=0.01)

        assert result == StatusCodes.SERVER_ERROR
        assert sent == ["A", "A", "B"]
        assert len(delays) == 2

    asyncio.run(exercise())


def test_repeat_and_delay_validation_rejects_out_of_range_and_boolean_values():
    valid = {"repeat": 2, "delay": 250}
    assert HTP1Remote._repeat_delay(valid) == (2, 0.25)
    assert HTP1Remote._repeat_delay(None) == (1, 0.0)

    for params in (
        {"repeat": True},
        {"repeat": 0},
        {"repeat": 21},
        {"repeat": 1.5},
        {"delay": True},
        {"delay": -1},
        {"delay": 5001},
        {"delay": 2.5},
    ):
        assert HTP1Remote._repeat_delay(params) is None
