from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def unique_local(naive: datetime, zone: ZoneInfo) -> datetime | None:
    """Reject nonexistent or ambiguous wall times rather than guessing a fold."""
    first, second = naive.replace(tzinfo=zone, fold=0), naive.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset():
        return None
    utc = first.astimezone(UTC)
    return utc if utc.astimezone(zone).replace(tzinfo=None) == naive else None


def available_slots(
    day: date,
    timezone: str,
    periods: list[tuple[time, time]],
    duration: int,
    busy: list[tuple[datetime, datetime]],
    now: datetime,
) -> list[tuple[datetime, datetime]]:
    if duration <= 0 or now.tzinfo is None:
        raise ValueError("Positive duration and aware clock required")
    zone = ZoneInfo(timezone)
    now = now.astimezone(UTC)
    occupied = [(start.astimezone(UTC), end.astimezone(UTC)) for start, end in busy]
    slots = set()
    # Merge adjacent periods so a continuous work window has no artificial gap.
    merged: list[tuple[time, time]] = []
    for start, end in sorted(periods):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    for starts, ends in merged:
        wall_start, wall_end = datetime.combine(day, starts), datetime.combine(day, ends)
        opening, closing = unique_local(wall_start, zone), unique_local(wall_end, zone)
        if opening is None or closing is None:
            continue
        # Conservative policy for work windows crossing a timezone transition.
        if opening.astimezone(zone).utcoffset() != closing.astimezone(zone).utcoffset():
            continue
        candidate = wall_start
        while candidate < wall_end:
            start = unique_local(candidate, zone)
            if start is not None:
                end = start + timedelta(minutes=duration)
                if (
                    start > now
                    and end <= closing
                    and not any(start < b and end > a for a, b in occupied)
                ):
                    slots.add((start, end))
            candidate += timedelta(minutes=15)
    return sorted(slots)
