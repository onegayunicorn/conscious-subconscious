"""Hardware adapters.

The BLE and serial parsers get the most attention here because that is where the
bugs are: a flags byte, two widths for the same field, optional trailing
sections and a 1/1024-second unit. Getting any of that wrong produces
plausible-looking numbers, which is the worst possible failure mode.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conscious_subconscious.core.errors import DeviceError, DeviceUnavailable
from conscious_subconscious.devices import (
    BleHeartRateDevice,
    ReplayDevice,
    Sample,
    SampleQuality,
    SimulatedCardioDevice,
    available,
    build,
    build_reported,
    get,
    hrv_index_from_rmssd,
    parse_heart_rate_measurement,
    parse_line,
    rmssd_ms,
    write_recording,
)
from conscious_subconscious.devices.base import ChannelSpec, DeviceCapabilities


class TestBleParser:
    def test_eight_bit_rate(self) -> None:
        parsed = parse_heart_rate_measurement(bytes([0x00, 72]))
        assert parsed["heart_rate"] == 72.0
        assert parsed["contact_supported"] is False

    def test_sixteen_bit_rate_is_little_endian(self) -> None:
        # 0x0130 = 304 little-endian => 0x30, 0x01
        parsed = parse_heart_rate_measurement(bytes([0x01, 0x30, 0x01]))
        assert parsed["heart_rate"] == 304.0

    def test_contact_flags(self) -> None:
        parsed = parse_heart_rate_measurement(bytes([0x06, 70]))
        assert parsed["contact_supported"] is True
        assert parsed["contact_detected"] is True
        assert parsed["quality"] is SampleQuality.OK

    def test_contact_supported_but_not_detected_is_suspect(self) -> None:
        parsed = parse_heart_rate_measurement(bytes([0x02, 70]))
        assert parsed["quality"] is SampleQuality.SUSPECT

    def test_energy_expended_is_parsed_when_present(self) -> None:
        parsed = parse_heart_rate_measurement(bytes([0x08, 70, 0x10, 0x27]))
        assert parsed["energy_expended_kj"] == 10_000.0

    def test_rr_intervals_use_one_over_1024_seconds(self) -> None:
        # One interval of 1024 raw units == exactly 1.0 s
        parsed = parse_heart_rate_measurement(bytes([0x10, 60, 0x00, 0x04]))
        assert parsed["rr_intervals_s"] == [1.0]

    def test_combined_flags(self) -> None:
        data = bytes([0x01 | 0x04 | 0x08 | 0x10, 0x30, 0x01, 0x0A, 0x00, 0x00, 0x02])
        parsed = parse_heart_rate_measurement(data)
        assert parsed["heart_rate"] == 304.0
        assert parsed["contact_detected"] is True
        assert parsed["energy_expended_kj"] == 10.0
        assert parsed["rr_intervals_s"] == [0.5]

    def test_zero_rate_means_no_measurement(self) -> None:
        """Zero is the standard "no reading" signal, not a stopped heart."""
        with pytest.raises(DeviceError, match="no measurement"):
            parse_heart_rate_measurement(bytes([0x00, 0]))

    def test_truncated_sixteen_bit_frame_is_rejected(self) -> None:
        with pytest.raises(DeviceError):
            parse_heart_rate_measurement(bytes([0x01, 0x30]))

    def test_truncated_eight_bit_frame_is_rejected(self) -> None:
        with pytest.raises(DeviceError):
            parse_heart_rate_measurement(bytes([0x00]))

    def test_odd_rr_section_is_rejected(self) -> None:
        with pytest.raises(DeviceError, match="16-bit intervals"):
            parse_heart_rate_measurement(bytes([0x10, 60, 0x00]))

    def test_empty_frame_is_rejected(self) -> None:
        with pytest.raises(DeviceError):
            parse_heart_rate_measurement(b"")

    def test_non_bytes_is_rejected(self) -> None:
        with pytest.raises(DeviceError):
            parse_heart_rate_measurement("70")  # type: ignore[arg-type]


class TestHrvMaths:
    def test_rmssd_of_a_known_series(self) -> None:
        # Differences: 10 ms, -10 ms => RMS = 10 ms
        assert rmssd_ms([1.0, 1.01, 1.0]) == pytest.approx(10.0)

    def test_rmssd_needs_two_intervals(self) -> None:
        """One interval has no successive difference; 0.0 would look like data."""
        assert rmssd_ms([1.0]) is None
        assert rmssd_ms([]) is None

    def test_hrv_index_clamps_to_the_unit_interval(self) -> None:
        assert hrv_index_from_rmssd(5.0) == 0.0
        assert hrv_index_from_rmssd(200.0) == 1.0

    def test_hrv_index_passes_none_through(self) -> None:
        assert hrv_index_from_rmssd(None) is None

    def test_hrv_index_rejects_nan(self) -> None:
        assert hrv_index_from_rmssd(float("nan")) is None


class TestSerialParser:
    def test_valid_line(self) -> None:
        sample = parse_line("CS,heart_rate,64.2", device="bridge", t_seconds=1.0)
        assert sample is not None
        assert sample.channel == "heart_rate"
        assert sample.value == 64.2
        assert sample.quality is SampleQuality.OK

    def test_valid_line_with_quality(self) -> None:
        sample = parse_line("CS,eda,3.5,suspect", device="bridge", t_seconds=1.0)
        assert sample is not None
        assert sample.quality is SampleQuality.SUSPECT

    def test_non_protocol_lines_are_ignored(self) -> None:
        """Firmware that prints a boot banner must not crash the host."""
        assert parse_line("booting...", device="b", t_seconds=0.0) is None
        assert parse_line("", device="b", t_seconds=0.0) is None

    def test_malformed_protocol_line_is_an_error(self) -> None:
        with pytest.raises(DeviceError):
            parse_line("CS,heart_rate", device="b", t_seconds=0.0)

    def test_non_numeric_value_is_an_error(self) -> None:
        with pytest.raises(DeviceError):
            parse_line("CS,heart_rate,fast", device="b", t_seconds=0.0)

    def test_nan_is_an_error(self) -> None:
        with pytest.raises(DeviceError):
            parse_line("CS,heart_rate,nan", device="b", t_seconds=0.0)

    def test_unknown_quality_is_an_error(self) -> None:
        with pytest.raises(DeviceError):
            parse_line("CS,heart_rate,60,maybe", device="b", t_seconds=0.0)

    def test_unknown_channel_is_marked_invalid_not_dropped(self) -> None:
        """Newer firmware must not be able to feed a channel nobody understands."""
        sample = parse_line("CS,brainwave,42", device="b", t_seconds=0.0)
        assert sample is not None
        assert sample.quality is SampleQuality.INVALID
        assert not sample.usable

    def test_empty_channel_is_an_error(self) -> None:
        with pytest.raises(DeviceError):
            parse_line("CS,,60", device="b", t_seconds=0.0)


class TestSimulatedDevice:
    def test_capabilities_declare_channels(self) -> None:
        device = SimulatedCardioDevice()
        assert {c.name for c in device.capabilities.channels} == {"heart_rate", "hrv_index"}
        assert device.capabilities.bidirectional is False

    def test_read_requires_open(self) -> None:
        with pytest.raises(DeviceError, match="not open"):
            SimulatedCardioDevice().read()

    def test_read_is_deterministic_for_a_seed(self) -> None:
        first = SimulatedCardioDevice(config={"seed": 5, "sample_rate_hz": 2.0})
        second = SimulatedCardioDevice(config={"seed": 5, "sample_rate_hz": 2.0})
        first.open()
        second.open()
        for _ in range(10):
            assert first.read() == second.read()

    def test_different_seeds_produce_different_series(self) -> None:
        """Not a guarantee per sample, but a different seed must diverge overall."""

        def series(seed: int) -> list[float]:
            device = SimulatedCardioDevice(config={"seed": seed})
            device.open()
            values: list[float] = []
            for _ in range(50):
                values.extend(s.value for s in device.read() if s.channel == "heart_rate")
            return values

        assert series(1) != series(2)

    def test_noise_is_bounded(self) -> None:
        device = SimulatedCardioDevice(config={"seed": 3, "noise_bpm": 1.0})
        device.open()
        values = []
        for _ in range(200):
            values.extend(s.value for s in device.read() if s.channel == "heart_rate")
        assert all(25.0 <= value <= 220.0 for value in values)

    def test_read_is_bounded_per_call(self) -> None:
        device = SimulatedCardioDevice(config={"sample_rate_hz": 100.0})
        device.open()
        assert len(device.read()) <= 128

    def test_rejects_non_positive_sample_rate(self) -> None:
        with pytest.raises(ValueError):
            SimulatedCardioDevice(config={"sample_rate_hz": 0.0})

    def test_hello_payload_matches_the_schema_enum(self) -> None:
        payload = SimulatedCardioDevice().hello_payload()
        assert payload["kind"] == "simulated"
        assert payload["device"]

    def test_close_is_idempotent(self) -> None:
        device = SimulatedCardioDevice()
        device.open()
        device.close()
        device.close()
        assert device.is_open is False


class TestReplayDevice:
    def _write(self, path: Path) -> None:
        rows = [
            Sample(device="d", channel="heart_rate", value=60.0, t_seconds=0.0),
            Sample(device="d", channel="heart_rate", value=61.0, t_seconds=1.0),
            Sample(device="d", channel="hrv_index", value=0.5, t_seconds=1.0),
        ]
        write_recording(path, rows)

    def test_round_trip(self, tmp_path: Path) -> None:
        path = tmp_path / "rec.csv"
        self._write(path)
        device = ReplayDevice(config={"path": str(path)})
        device.open()
        first = device.read()
        assert first[0].value == 60.0
        assert device.remaining == 2

    def test_exhausts_and_stops(self, tmp_path: Path) -> None:
        path = tmp_path / "rec.csv"
        self._write(path)
        device = ReplayDevice(config={"path": str(path)})
        device.open()
        for _ in range(3):
            device.read()
        assert device.exhausted
        assert device.read() == ()

    def test_loops_when_configured(self, tmp_path: Path) -> None:
        path = tmp_path / "rec.csv"
        self._write(path)
        device = ReplayDevice(config={"path": str(path), "loop": True})
        device.open()
        for _ in range(5):
            assert device.read() != ()

    def test_replay_is_deterministic(self, tmp_path: Path) -> None:
        path = tmp_path / "rec.csv"
        self._write(path)
        first = ReplayDevice(config={"path": str(path)})
        second = ReplayDevice(config={"path": str(path)})
        first.open()
        second.open()
        for _ in range(3):
            assert first.read() == second.read()

    def test_missing_path_is_rejected_at_construction(self) -> None:
        with pytest.raises(DeviceError):
            ReplayDevice(config={})

    def test_missing_file_is_an_error_on_open(self, tmp_path: Path) -> None:
        device = ReplayDevice(config={"path": str(tmp_path / "nope.csv")})
        with pytest.raises(DeviceError, match="not found"):
            device.open()

    def test_bad_columns_are_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.csv"
        path.write_text("a,b\n1,2\n", encoding="utf-8")
        with pytest.raises(DeviceError, match="columns"):
            ReplayDevice(config={"path": str(path)}).open()

    def test_empty_recording_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.csv"
        path.write_text("t_seconds,channel,value\n", encoding="utf-8")
        with pytest.raises(DeviceError, match="no samples"):
            ReplayDevice(config={"path": str(path)}).open()

    def test_non_numeric_row_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.csv"
        path.write_text("t_seconds,channel,value\nx,heart_rate,60\n", encoding="utf-8")
        with pytest.raises(DeviceError):
            ReplayDevice(config={"path": str(path)}).open()


class TestBleDevice:
    def test_open_reports_unavailable_without_bleak(self) -> None:
        device = BleHeartRateDevice()
        try:
            import bleak  # noqa: F401
        except ImportError:
            with pytest.raises(DeviceUnavailable):
                device.open()

    def test_ingest_buffers_samples_until_read(self) -> None:
        device = BleHeartRateDevice()
        device.open = lambda: setattr(device, "_open", True)  # type: ignore[method-assign]
        device._open = True  # noqa: SLF001
        produced = device.ingest(bytes([0x00, 70]), t_seconds=1.0)
        assert produced[0].channel == "heart_rate"
        assert len(device.read()) == 1
        assert device.read() == ()

    def test_ingest_emits_an_hrv_index_periodically(self) -> None:
        device = BleHeartRateDevice(config={"hrv_sample_every_n_beats": 2})
        device._open = True  # noqa: SLF001
        # Frame with one RR interval of 1024 raw units == 1.0 s
        frame = bytes([0x10, 60, 0x00, 0x04])
        device.ingest(frame, t_seconds=1.0)
        second = device.ingest(frame, t_seconds=2.0)
        assert any(sample.channel == "hrv_index" for sample in second)

    def test_capabilities_are_read_only(self) -> None:
        assert BleHeartRateDevice().capabilities.bidirectional is False


class TestRegistry:
    def test_all_expected_kinds_are_registered(self) -> None:
        assert set(available()) == {"simulated", "serial", "lsl", "ble-heart-rate", "replay"}

    def test_unknown_kind_is_rejected(self) -> None:
        with pytest.raises(DeviceError):
            get("telepathy")

    def test_build_from_a_spec(self) -> None:
        device = build({"kind": "simulated", "name": "hr-01", "seed": 1})
        assert device.name == "hr-01"

    def test_build_requires_a_kind(self) -> None:
        with pytest.raises(DeviceError):
            build({"name": "hr-01"})

    def test_build_reported_surfaces_problems_instead_of_hiding_them(self) -> None:
        """A spec that cannot even be constructed must be reported, not dropped."""
        drivers, problems = build_reported(
            [{"kind": "simulated"}, {"kind": "replay"}]  # replay without a path
        )
        assert len(drivers) == 1
        assert problems and problems[0]["kind"] == "replay"

    def test_build_reported_reports_nothing_for_good_specs(self) -> None:
        drivers, problems = build_reported([{"kind": "simulated"}])
        assert len(drivers) == 1
        assert problems == []


class TestCapabilities:
    def test_channel_spec_omits_empty_optionals(self) -> None:
        payload = ChannelSpec(name="heart_rate").as_dict()
        assert payload == {"name": "heart_rate"}

    def test_capabilities_dict_shape(self) -> None:
        payload = DeviceCapabilities(
            channels=(ChannelSpec(name="x"),), sample_rate_hz=1.0
        ).as_dict()
        assert payload["channels"] == [{"name": "x"}]
        assert payload["bidirectional"] is False


def test_every_driver_declares_a_kind() -> None:
    for kind in available():
        assert get(kind).kind == kind
