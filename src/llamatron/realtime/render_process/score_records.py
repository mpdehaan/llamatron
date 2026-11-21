# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""What a score read from its render, which a score after an edit takes scene by scene from the score before it; and such a
score held to a whole render of the same song while the tests check every remembered answer, as a memory holds a kept answer to
the same answer worked out again (caching/memory.py)."""

from typing import NamedTuple

from llamatron.caching import memory

# What a score is held to, as a difference names it.
CHECKED_EVENTS = 'events'
CHECKED_SCENE_SECONDS = 'scene seconds'
CHECKED_CLIP_SECONDS = 'clip seconds'
CHECKED_DRAW_LIGHTS = 'draw lights'
CHECKED_ROWS = 'rows'


class Records(NamedTuple):
    """What a score read from its render: each clip's events, each scene's seconds and rows, each clip's seconds and each scene's draw moments."""

    events: dict
    scene_seconds: list
    clip_seconds: dict
    draw_lights: list
    rows: list


def take_scene(*, into, earlier, index, tracks):
    """Take a scene's rows, events, clip seconds and draw moments from an earlier score's records into a score's, and return how
    long the scene lasts in seconds."""
    into.rows[index] = earlier.rows[index]
    into.draw_lights[index] = earlier.draw_lights[index]
    for track in tracks:
        into.events[(index, track)] = earlier.events[(index, track)]
    for key, seconds in earlier.clip_seconds.items():
        if key[0] == index:
            into.clip_seconds[key] = seconds
    return earlier.scene_seconds[index]


def check(*, kept, again):
    """Raise StaleAnswer where the records of a score that took scenes differ from a whole render's, naming the first difference."""
    pairs = ((CHECKED_EVENTS, kept.events, again.events), (CHECKED_SCENE_SECONDS, kept.scene_seconds, again.scene_seconds),
             (CHECKED_CLIP_SECONDS, kept.clip_seconds, again.clip_seconds), (CHECKED_DRAW_LIGHTS, kept.draw_lights, again.draw_lights),
             (CHECKED_ROWS, _row_times(kept.rows), _row_times(again.rows)))
    for name, ours, theirs in pairs:
        if ours != theirs:
            place = _first_difference(cached=ours, again=theirs)
            ours = _entry(record=ours, place=place)
            theirs = _entry(record=theirs, place=place)
            if isinstance(ours, list) and isinstance(theirs, list):
                # Of a clip's events, only the first that differs, which says enough to find what went wrong.
                event = _first_difference(cached=ours, again=theirs)
                place = (place, event)
                ours = _entry(record=ours, place=event)
                theirs = _entry(record=theirs, place=event)
            raise memory.stale_answer(key=(name, place), cached=ours, again=theirs)


def _row_times(rows):
    """Return where each scene's rows start and how long each lasts, in seconds, leaving out their clocks, which compare by identity."""
    return [_scene_row_times(scene) for scene in rows]


def _scene_row_times(scene):
    return [(row.start, row.seconds) for row in scene]


def _first_difference(*, kept, again):
    """Return the first key or place at which two records differ."""
    places = sorted(kept.keys() | again.keys(), key=str) if isinstance(kept, dict) else range(max(len(kept), len(again)))
    return next((place for place in places if _entry(record=kept, place=place) != _entry(record=again, place=place)), None)


def _entry(*, record, place):
    """Return what a record holds at a key or a place, or None where it holds nothing."""
    if isinstance(record, dict):
        return record.get(place)
    return record[place] if place < len(record) else None
