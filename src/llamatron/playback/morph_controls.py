# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The CC values of a clip that morphs into another pattern."""



def morph_controls(*, source, target, start, end):
    """Return the CC values of a morph: the target's from start to end, and the source's elsewhere.

    Each side's values carry across the edges, so a lane holds what it would hold there.
    """
    if end <= start:
        return list(source.get_controls())
    result = _sent_before(clip=source, time=start)
    result += _carried_to(clip=target, time=start)
    result += _sent_between(clip=target, start=start, end=end)
    if end < source.total_length():
        result += _carried_to(clip=source, time=end)
        result += _sent_from(clip=source, time=end)
    return result


def _sent_before(*, clip, time):
    """Return the CC values a clip sends before a time."""
    return [item for item in clip.get_controls() if item.get_time() < time]


def _sent_between(*, clip, start, end):
    """Return the CC values a clip sends from a start time until an end time."""
    return [item for item in clip.get_controls() if start <= item.get_time() < end]


def _sent_from(*, clip, time):
    """Return the CC values a clip sends from a time on."""
    return [item for item in clip.get_controls() if item.get_time() >= time]


def _carried_to(*, clip, time):
    """Return the values a clip's lanes were holding just before a time, sent again at that time.

    A lane only holds a value if the clip sent one earlier, so lanes it hasn't used yet send nothing.
    """
    return [item.at_time(time) for item in _values_in_effect(clip=clip, time=time).values() if item.get_time() < time]


def _values_in_effect(*, clip, time):
    """Return, for each CC lane, the last value a clip sent at or before a time."""
    latest = {}
    for item in clip.get_controls():
        if item.get_time() <= time:
            latest[item.get_number()] = item
    return latest
