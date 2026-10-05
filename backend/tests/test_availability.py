from datetime import UTC, date, datetime, time

import pytest

from app.availability import available_slots


def slots(periods, duration=60, busy=None, now=None, zone="America/Cuiaba", day=date(2026, 10, 5)):
    return available_slots(
        day, zone, periods, duration, busy or [], now or datetime(2026, 1, 1, tzinfo=UTC)
    )


def test_combined_duration_respects_breaks():
    result = slots([(time(9), time(12)), (time(13), time(15))], duration=120)
    assert [s.hour * 60 + s.minute for s, _ in result] == [780, 795, 810, 825, 840, 1020]
    assert all((end - start).total_seconds() == 7200 for start, end in result)


def test_occupancy_allows_exact_boundaries():
    busy = [(datetime(2026, 10, 5, 14, tzinfo=UTC), datetime(2026, 10, 5, 15, tzinfo=UTC))]
    result = slots([(time(9), time(12))], busy=busy)
    assert [start.hour for start, _ in result] == [13, 15]


def test_adjacent_periods_are_continuous_and_results_unique():
    result = slots([(time(9), time(10)), (time(10), time(11))], duration=120)
    assert len(result) == 1
    assert result[0][0].hour == 13


def test_past_and_current_starts_are_removed():
    result = slots([(time(9), time(11))], now=datetime(2026, 10, 5, 13, 30, tzinfo=UTC))
    assert [(s.hour, s.minute) for s, _ in result] == [(13, 45), (14, 0)]


def test_closed_day_and_too_short_window():
    assert slots([]) == []
    assert slots([(time(9), time(10))], duration=61) == []


def test_timezone_changes_utc_time():
    assert slots([(time(9), time(10))], zone="America/Sao_Paulo")[0][0].hour == 12
    assert slots([(time(9), time(10))])[0][0].hour == 13


@pytest.mark.parametrize("day", [date(2026, 3, 8), date(2026, 11, 1)])
def test_dst_transition_window_is_conservatively_unavailable(day):
    assert slots([(time(0), time(4))], zone="America/New_York", day=day) == []
    assert slots([(time(9), time(10))], zone="America/New_York", day=day)


def test_overnight_occupation_blocks_next_morning():
    busy = [(datetime(2026, 10, 4, 23, tzinfo=UTC), datetime(2026, 10, 5, 14, tzinfo=UTC))]
    assert [s.hour for s, _ in slots([(time(9), time(11))], busy=busy)] == [14]
