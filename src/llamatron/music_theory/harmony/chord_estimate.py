# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The chords a lead sheet prints under a tune, estimated from all the notes of a song merged into one, a bar at a time, as a
musician sketching a song's harmony would.

Each bar's chord is the one whose notes cover the most of the bar's sounding time, less what sounds outside it, with a
preference for the chords of the key, the home chord most and then IV and V, and for a chord rooted on the bar's lowest note
at its start. A bar of four beats or more is split into halves where the halves clearly differ. At Triads the chords are the
major, minor and diminished triads; at Sevenths the seventh chords are tried too, a seventh winning only where its fourth
note sounds through a real share of the span in the accompaniment, the tune aside, so that a passing note or the tune's
own note never makes C into C7. A span whose notes hold a root
and its fifth and no third is a power chord, since nothing should be named as a chord that sounds unlike it.
"""

from typing import NamedTuple

from llamatron.model.schema.file_format import ChordSymbol
from llamatron.model.values import note as note_values
from llamatron.music_theory.fundamentals import intervals
from llamatron.music_theory.harmony.heard_chords import chord_shapes

OCTAVE = intervals.HALF_STEPS_PER_OCTAVE


class ChordLevel:
    """How simply a lead sheet prints a song's chords."""

    TRIADS = 'triads'
    SEVENTHS = 'sevenths'
    AS_PLAYED = 'as_played'


CHORD_LEVELS = (ChordLevel.TRIADS, ChordLevel.SEVENTHS, ChordLevel.AS_PLAYED)
DEFAULT_CHORD_LEVEL = ChordLevel.SEVENTHS
TRIADS = (ChordSymbol.MAJOR, ChordSymbol.MINOR, ChordSymbol.DIMINISHED)
SEVENTHS = (ChordSymbol.DOMINANT7, ChordSymbol.MAJOR7, ChordSymbol.MINOR7, ChordSymbol.DIMINISHED7, ChordSymbol.HALF_DIMINISHED7)
# How much what sounds outside a chord counts against it, against what sounds inside it.
OUTSIDE_WEIGHT = 0.6
# The preferences, each a share of the span's whole sounding time: a chord of the key, the home chord, IV or V major, and a
# root in the bass; and what a diminished chord loses, being the least likely guess.
IN_KEY = 0.15
HOME_CHORD = 0.12
FOURTH_OR_FIFTH = 0.05
ROOT_IN_BASS = 0.1
DIMINISHED_DOUBT = 0.1
# A seventh is tried only where its seventh sounds through this share of the span's sounding time.
SEVENTH_SHARE = 0.15
# A bar this many whole notes long or more may change chord halfway, where the halves together score this much more.
SPLIT_BAR = 1
SPLIT_GAIN = 1.25
FOURTH = 5
FIFTH = 7
MINOR_THIRD = 3
MAJOR_THIRD = 4


class EstimatedChord(NamedTuple):
    """A chord estimated for a span: when it starts and ends, its root's pitch class and its symbol."""

    start: object
    end: object
    root: int
    symbol: str


class SpanSound(NamedTuple):
    """What sounds in a span: how long each pitch class sounds through it, by pitch class, the whole of that, and the pitch
    class of the lowest note struck first in it, or None."""

    weights: dict
    total: float
    bass: object


class Music(NamedTuple):
    """The notes chords are estimated from, each with a start, an end and a pitch in whole notes, and those of them that
    are the tune, which may supply a chord's third but never its seventh."""

    notes: tuple
    tune: frozenset


def estimated_chords(*, music, bars, scale_at, level):
    """Return the chords of some Music, a bar or half bar each, its bars as (start, end), scale_at giving the scale in force
    at a time or None, at a level (ChordLevel), Triads or Sevenths; a chord carrying on into the next span in the same key
    joined with it."""
    chords = []
    for start, end in bars:
        for chord in bar_chords(music=music, span=(start, end), scale=scale_at(start), level=level):
            if chords and chords[-1].end == chord.start and (chords[-1].root, chords[-1].symbol) == (chord.root, chord.symbol) and scale_at(chords[-1].start) == scale_at(start):
                chords[-1] = chords[-1]._replace(end=chord.end)
            else:
                chords.append(chord)
    return chords


def bar_chords(*, music, span, scale, level):
    """Return a bar's chord, or its two halves' where the bar is long enough and they clearly differ, or nothing for a bar
    where nothing sounds."""
    start, end = span
    whole = best_chord(sound=heard_in(music=music, start=start, end=end), scale=scale, level=level)
    if whole is None:
        return []
    if end - start >= SPLIT_BAR:
        middle = start + (end - start) / 2
        first = best_chord(sound=heard_in(music=music, start=start, end=middle), scale=scale, level=level)
        second = best_chord(sound=heard_in(music=music, start=middle, end=end), scale=scale, level=level)
        if first and second and first[1:] != second[1:] and first[0] + second[0] > whole[0] * SPLIT_GAIN:
            return [EstimatedChord(start, middle, *first[1:]), EstimatedChord(middle, end, *second[1:])]
    return [EstimatedChord(start, end, *whole[1:])]


def heard_in(*, music, start, end):
    """Return what sounds in a span, and what the accompaniment alone sounds there, as a pair of SpanSound."""
    accompaniment = [note for note in music.notes if note not in music.tune]
    return (span_sound(notes=music.notes, start=start, end=end), span_sound(notes=accompaniment, start=start, end=end))


def span_sound(*, notes, start, end):
    """Return what sounds in a span (SpanSound)."""
    weights = {}
    lowest = None
    for note in notes:
        overlap = min(note.end, end) - max(note.start, start)
        if overlap <= 0:
            continue
        weights[note.pitch % OCTAVE] = weights.get(note.pitch % OCTAVE, 0) + float(overlap)
        if note.start >= start and (lowest is None or (note.start, note.pitch) < lowest):
            lowest = (note.start, note.pitch)
    bass = None
    if lowest is not None:
        bass = lowest[1] % OCTAVE
    return SpanSound(weights=weights, total=sum(weights.values()), bass=bass)


def best_chord(*, sound, scale, level):
    """Return the chord that best fits what sounds in a span, a pair of SpanSound, everything and the accompaniment alone,
    as (score, root, symbol), a power chord where only a root and its fifth sound, or None where nothing sounds."""
    sound, accompaniment = sound
    if sound.total <= 0:
        return None
    best = None
    for root in range(OCTAVE):
        for symbol in candidates(sound=accompaniment, root=root, level=level):
            score = chord_score(sound=sound, root=root, symbol=symbol, scale=scale)
            if best is None or score > best[0]:
                best = (score, root, symbol)
    return as_power_chord(chord=best, sound=sound)


def candidates(*, sound, root, level):
    """Return the chord symbols tried on a root: the triads, and at Sevenths each seventh chord whose seventh the
    accompaniment sounds enough, the tune's notes never making a seventh."""
    symbols = list(TRIADS)
    if level == ChordLevel.SEVENTHS:
        for symbol in SEVENTHS:
            seventh = (root + max(chord_shapes()[symbol])) % OCTAVE
            if sound.weights.get(seventh, 0) >= SEVENTH_SHARE * sound.total:
                symbols.append(symbol)
    return symbols


def chord_score(*, sound, root, symbol, scale):
    """Return how well a chord fits what sounds: the time its notes sound, less what sounds outside it, with the preferences
    for the chords of the key, the home chord, IV and V and a root in the bass."""
    members = {(root + step) % OCTAVE for step in chord_shapes()[symbol]}
    inside = sum(weight for pitch_class, weight in sound.weights.items() if pitch_class in members)
    score = inside - OUTSIDE_WEIGHT * (sound.total - inside)
    score += preference(root=root, symbol=symbol, members=members, scale=scale) * sound.total
    if sound.bass == root:
        score += ROOT_IN_BASS * sound.total
    return score


def preference(*, root, symbol, members, scale):
    """Return how much more likely a chord is in a key, as a share of the span's sounding time."""
    favoured = 0
    if symbol in (ChordSymbol.DIMINISHED, ChordSymbol.DIMINISHED7):
        favoured -= DIMINISHED_DOUBT
    if scale is None:
        return favoured
    tonic = note_values.SEMITONES_ABOVE_C[scale.get_root()] % OCTAVE
    in_key = {(tonic + step) % OCTAVE for step in scale.get_half_steps()}
    if members <= in_key:
        favoured += IN_KEY
        above = (root - tonic) % OCTAVE
        if above == 0:
            favoured += HOME_CHORD
        elif above in (FOURTH, FIFTH) and symbol in (ChordSymbol.MAJOR, ChordSymbol.DOMINANT7):
            favoured += FOURTH_OR_FIFTH
    return favoured


def as_power_chord(*, chord, sound):
    """Return a chord as a power chord where its root and fifth sound and neither third does, else as it is."""
    score, root, symbol = chord
    thirds = (sound.weights.get((root + MINOR_THIRD) % OCTAVE, 0), sound.weights.get((root + MAJOR_THIRD) % OCTAVE, 0))
    if not any(thirds) and sound.weights.get((root + FIFTH) % OCTAVE, 0) > 0:
        return (score, root, ChordSymbol.POWER)
    return chord
