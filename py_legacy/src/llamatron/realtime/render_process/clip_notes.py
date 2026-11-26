# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""A clip's notes as they sound, read from its events: what the green light after a track's name asks, what the visualizer
hears, and what sounds at a moment where a clip is cut. Each answer is worked out from the events the first time it is asked."""

import bisect
from typing import NamedTuple

from llamatron.realtime.render_process import timeline

# How long the longest note of a clip with none lasts.
NO_NOTE = 0.0


class Sounding(NamedTuple):
    """When one note of a clip starts and ends, in seconds from the scene's start, for the lights."""

    on: float
    off: float


class HeardClipNote(NamedTuple):
    """One note of a clip as the visualizer hears it: when it starts and ends, in seconds from the scene's start, its MIDI number and its velocity."""

    on: float
    off: float
    number: int
    velocity: int


class ClipNotes:
    """One clip's notes as they sound, from its events counted from its scene's start."""

    __slots__ = ('_events', '_spans', '_heard')

    def __init__(self, events):
        self._events = events
        # Each note's span, and the notes as heard with their starts and the longest of them, worked out when first asked.
        self._spans = None
        self._heard = None

    def is_sounding(self, elapsed):
        """Return whether a note of the clip sounds at a moment counted from the scene's start."""
        if self._spans is None:
            self._spans = _note_spans(self._events)
        for span in self._spans:
            if span.on > elapsed:
                return False
            if span.off > elapsed:
                return True
        return False

    def heard(self, *, since, until):
        """Return the notes the visualizer hears between two moments counted from the scene's start: those that started after since and by until, and those still sounding at until, each a HeardClipNote.

        Only notes that have started are heard, so the visualizer never knows what is coming.
        """
        if self._heard is None:
            notes = _heard_notes(self._events)
            self._heard = (notes, [note.on for note in notes], max((note.off - note.on for note in notes), default=NO_NOTE))
        notes, starts, longest = self._heard
        last = bisect.bisect_right(starts, until)
        first_started = bisect.bisect_right(starts, since)
        earliest_held = bisect.bisect_left(starts, until - longest)
        started = notes[first_started:last]
        held = [note for note in notes[min(earliest_held, first_started):first_started] if note.off > until]
        return started, held

    def sounding_across(self, elapsed):
        """Return the (port, channel, number) of every note that has started and not ended at a moment, for cutting the clip there."""
        notes = set()
        for event in self._events:
            if event.seconds >= elapsed:
                break
            key = (event.port, event.channel, event.number)
            if event.kind == timeline.NOTE_ON:
                notes.add(key)
            elif event.kind == timeline.NOTE_OFF:
                notes.discard(key)
        return sorted(notes)


def _heard_notes(events):
    """Return each note on with its note off, number and velocity, in the order the notes start."""
    notes = []
    open_notes = {}
    for event in events:
        if event.switch:
            continue
        key = (event.port, event.channel, event.number)
        if event.kind == timeline.NOTE_ON:
            open_notes[key] = (event.seconds, event.value)
        elif event.kind == timeline.NOTE_OFF and key in open_notes:
            on, velocity = open_notes.pop(key)
            notes.append(HeardClipNote(on, event.seconds, event.number, velocity))
    notes.sort()
    return notes


def _note_spans(events):
    """Return when each note on's note sounds until its note off, in the order the notes start."""
    spans = []
    open_notes = {}
    for event in events:
        if event.switch:
            continue
        key = (event.port, event.channel, event.number)
        if event.kind == timeline.NOTE_ON:
            open_notes[key] = event.seconds
        elif event.kind == timeline.NOTE_OFF and key in open_notes:
            spans.append(Sounding(open_notes.pop(key), event.seconds))
    spans.sort()
    return spans
