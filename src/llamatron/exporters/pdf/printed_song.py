# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A song as the PDF export prints it: one melody line and the chords under it, with its keys and sections, every time exact
in whole notes from the song's start.

Every page of a PDF is drawn from this, never from the set, so that the pages agree on what the song is: the tracks chosen as
the melody merged into one line, the tracks chosen as the chords heard as one chord at a time, each key where a run of scenes
in it begins, and each section where a scene's Section setting changes or, in a song that sets none, at every scene, a
scene played again in a row counted rather than printed again.
"""

from dataclasses import dataclass
from typing import NamedTuple

from llamatron.math.rational import Rational

NO_TIME = Rational(0)


class PrintedNote(NamedTuple):
    """A note of the melody: when it starts and ends, in whole notes from the song's start, and its MIDI number."""

    start: Rational
    end: Rational
    pitch: int


class PrintedChord(NamedTuple):
    """A chord as printed: when it starts and ends, its name and Roman numeral in its key, its root's pitch class, its
    symbol, and its bass's pitch class or None where the bass is its root."""

    start: Rational
    end: Rational
    name: str
    numeral: str
    root: int
    symbol: str
    bass: object


class KeyStart(NamedTuple):
    """Where a key begins, and its Scale."""

    start: Rational
    scale: object


class SectionStart(NamedTuple):
    """Where a section begins, its name, its Section setting or its scene's name, and how many times in a row it plays."""

    start: Rational
    name: str
    times: int = 1


@dataclass(slots=True, kw_only=True, frozen=True)
class PrintedSong:
    """A song as the PDF export prints it: its title, its melody (PrintedNote), its chords (PrintedChord), its keys
    (KeyStart) and sections (SectionStart) in order, each a tuple, its time signature, its tempo and its length in whole
    notes."""

    title: str
    melody: tuple
    chords: tuple
    keys: tuple
    sections: tuple
    signature: object
    tempo: object
    length: object

    def bar_length(self):
        """Return how long a bar lasts, in whole notes."""
        return self.signature.bar_length()

    def bar_starts(self):
        """Return when each bar starts, in whole notes, from the first to the last that anything plays in."""
        starts = []
        start = NO_TIME
        while start < self.length:
            starts.append(start)
            start += self.bar_length()
        return starts

    def key_at(self, time):
        """Return the Scale of the key in force at a time, or None for a song with no key."""
        found = None
        for key in self.keys:
            if key.start <= time:
                found = key.scale
        return found

    def main_key(self):
        """Return the Scale the song spends longest in, the first of those that tie, or None for a song with no key."""
        totals = {}
        ends = [key.start for key in self.keys[1:]] + [self.length]
        for key, end in zip(self.keys, ends):
            totals[key.scale] = totals.get(key.scale, NO_TIME) + end - key.start
        if not totals:
            return None
        return max(totals, key=totals.get)
