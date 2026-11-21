# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""One piece of the corpus, whatever its source: what it is (its source, its identity, who made it, when and where, its style,
meter, key and tempo as the source says) and what it holds (notes by part, chords as degrees of the key, sections, and whether
its notes are drums). A piece with notes becomes the analyzer's performance, so every source is measured as the demos are."""

from dataclasses import dataclass, field
from measuring.hearing.performance import Performance, PlayedNote, PlayedTrack

DEFAULT_TEMPO = 100
DEFAULT_VELOCITY = 80


@dataclass(slots=True, kw_only=True, frozen=True)
class CorpusNote:
    """A note: its start and length in beats, its MIDI number, its velocity and the part it belongs to."""

    start: float
    length: float
    pitch: int
    velocity: int = DEFAULT_VELOCITY
    part: str = '1'


@dataclass(slots=True, kw_only=True)
class Piece:
    """A piece of the corpus and what its source tells of it."""

    source: str
    identity: str
    title: str = None
    creator: str = None
    year: int = None
    region: str = None
    style: str = None
    meter: str = '4/4'
    beats_per_bar: float = 4.0
    key: str = None
    tempo: float = DEFAULT_TEMPO
    notes: tuple = ()
    drums: bool = False
    drum_parts: frozenset = frozenset()
    chords: tuple = ()
    sections: tuple = ()
    extra: dict = field(default_factory=dict)

    def performance(self):
        """Return the piece's notes as the analyzer's performance, a track for each part."""
        parts = {}
        for note in self.notes:
            parts.setdefault(note.part, []).append(PlayedNote(start=note.start, end=note.start + max(note.length, 1e-3), pitch=note.pitch, velocity=note.velocity))
        tracks = tuple(PlayedTrack(name=name, drum=self.drums or name in self.drum_parts, sound=None, notes=tuple(sorted(notes, key=lambda note: (note.begins, note.pitch))))
                       for name, notes in parts.items())
        length = max((note.start + note.length for note in self.notes), default=self.beats_per_bar)
        return Performance(tracks=tracks, tempo=round(self.tempo), meter=self.meter, beats_per_bar=self.beats_per_bar, length=max(length, self.beats_per_bar))
