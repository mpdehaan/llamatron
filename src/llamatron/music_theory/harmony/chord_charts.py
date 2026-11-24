# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The chords a chord chart prints for a learner: the chord heard on each beat (heard_chords.py) read as a teacher writes a
song's harmony on the board, at one of three levels.

At Triads and Sevenths, the beats of a span, a bar in 2/4, 3/4 and 6/8 and half a bar in 4/4, are one chord where they share
a root or one beat's notes fit inside the other's chord, so that a stride's bass on one beat and its chord on the next read as
one chord; a new root, or a tritone the beat before lacked, starts a chord anew inside the span, so that a cadence's C/G G7 or
a ii-V in half a bar stays two chords. A bar of only octaves or a root and fifth stays a power chord, unless the melody sounds
its third on a beat, when it truly sounds as that triad. Then each chord is read at its level: Triads keeps triads and
anything smaller, Sevenths the seventh chords too, a 9th, 11th, 13th or added note dropped back to its seventh; a two-note
chord stays itself at every level, since nothing becomes a chord that sounds unlike it. Triads drops every slash; Sevenths
keeps a slash only where the bass holds through the chord and walks by step to the next, or where it is the fifth the next
chord is rooted on, a cadence's C/G before G7. As played prints every beat as heard.
"""

from typing import NamedTuple

from llamatron.model.schema.file_format import ChordSymbol as S
from llamatron.music_theory.fundamentals import intervals
from llamatron.music_theory.harmony.heard_chords import chord_shapes

OCTAVE = intervals.HALF_STEPS_PER_OCTAVE
TRITONE = 6
# How far a bass may walk to the next chord's and still be a step.
LARGEST_STEP = 2
MINOR_THIRD = 3
MAJOR_THIRD = 4
FIFTH = 7


class ChordLevel:
    """How simply a chart prints a song's chords."""

    TRIADS = 'triads'
    SEVENTHS = 'sevenths'
    AS_PLAYED = 'as_played'


CHORD_LEVELS = (ChordLevel.TRIADS, ChordLevel.SEVENTHS, ChordLevel.AS_PLAYED)
DEFAULT_CHORD_LEVEL = ChordLevel.SEVENTHS
# What each chord symbol is printed as at Sevenths: a seventh chord as itself, a sixth or added note dropped to its triad, a
# 9th, 11th or 13th to its seventh. A symbol not listed is printed as itself.
AT_SEVENTHS = {
    S.MAJOR6: S.MAJOR, S.MINOR6: S.MINOR, S.ADD9: S.MAJOR, S.MINOR_ADD9: S.MINOR, S.MINOR_MAJOR7: S.MINOR,
    S.AUGMENTED7: S.DOMINANT7, S.AUGMENTED_MAJOR7: S.MAJOR7,
    S.DOMINANT9: S.DOMINANT7, S.DOMINANT11: S.DOMINANT7, S.DOMINANT13: S.DOMINANT7,
    S.MAJOR9: S.MAJOR7, S.MAJOR11: S.MAJOR7, S.MAJOR13: S.MAJOR7,
    S.MINOR9: S.MINOR7, S.MINOR11: S.MINOR7, S.MINOR13: S.MINOR7,
}
# What each chord symbol is printed as at Triads, from what it is at Sevenths: every seventh chord as its triad.
SEVENTHS_AT_TRIADS = {
    S.DOMINANT7: S.MAJOR, S.MAJOR7: S.MAJOR, S.MINOR7: S.MINOR, S.DIMINISHED7: S.DIMINISHED, S.HALF_DIMINISHED7: S.DIMINISHED,
    S.DOMINANT7_SUS4: S.SUS4,
}


class HeardBeat(NamedTuple):
    """A beat's chord as heard: when the beat starts, its root's pitch class, its symbol, and its bass's pitch class or
    None where the bass is the root."""

    start: object
    root: int
    symbol: str
    bass: object


class Stretch(NamedTuple):
    """A stretch of music a chart reads, such as a scene: how long it lasts, its beat, and the span a chord is heard over,
    each in whole notes."""

    length: object
    beat: object
    span: object


class ChartChord(NamedTuple):
    """A chord as a chart prints it: when it starts and ends, its root's pitch class, its symbol, and its bass's pitch
    class, or None where none is printed."""

    start: object
    end: object
    root: int
    symbol: str
    bass: object


def chord_span(signature):
    """Return the span a chord is heard over at Triads and Sevenths: half a bar of four beats, else a bar."""
    if signature.get_beats() == 4:
        return signature.bar_length() / 2
    return signature.bar_length()


def charted_chords(*, beats, stretch, level, melody):
    """Return a Stretch of music's chords as a chart prints them at a level, from its beats' chords as heard (HeardBeat),
    melody the pitch classes the melody sounds at each beat's start, by the beat's start."""
    if level == ChordLevel.AS_PLAYED:
        return joined([ChartChord(start=heard.start, end=heard.start + stretch.beat, root=heard.root, symbol=heard.symbol, bass=heard.bass) for heard in beats])
    chords = []
    start = 0 * stretch.beat
    while start < stretch.length:
        end = min(start + stretch.span, stretch.length)
        inside = [heard for heard in beats if start <= heard.start < end]
        chords += span_chords(beats=inside, start=start, end=end, melody=melody)
        start = end
    chords = [at_level(chord=chord, level=level) for chord in chords]
    return joined(printed_basses(chords=chords, level=level))


def span_chords(*, beats, start, end, melody):
    """Return a span's chords: its beats joined where they share a root or one fits inside the other's chord, unless the
    later brings a tritone the earlier lacks; the first chord taking the span's start, each lasting to the next."""
    pieces = []
    for heard in beats:
        if pieces and belongs_with(earlier=pieces[-1], later=heard):
            pieces[-1] = richer(earlier=pieces[-1], later=heard)
        else:
            pieces.append(ChartChord(start=heard.start, end=end, root=heard.root, symbol=heard.symbol, bass=heard.bass))
    if pieces:
        pieces[0] = pieces[0]._replace(start=start)
    ends = [piece.start for piece in pieces[1:]] + [end]
    return [thirded(chord=piece._replace(end=finish), melody=melody) for piece, finish in zip(pieces, ends)]


def belongs_with(*, earlier, later):
    """Return whether a beat's chord is part of the chord before it: the same root, or one's notes inside the other's, with
    no tritone the earlier lacks."""
    first = members(root=earlier.root, symbol=earlier.symbol)
    second = members(root=later.root, symbol=later.symbol)
    if has_tritone(second) and not has_tritone(first):
        return False
    return earlier.root == later.root or first <= second or second <= first


def richer(*, earlier, later):
    """Return the chord a beat joins, taking the beat's reading where it holds more notes, and its bass only while both agree."""
    bass = earlier.bass if earlier.bass == later.bass else None
    if len(members(root=later.root, symbol=later.symbol)) > len(members(root=earlier.root, symbol=earlier.symbol)):
        return earlier._replace(root=later.root, symbol=later.symbol, bass=bass)
    return earlier._replace(bass=bass)


def thirded(*, chord, melody):
    """Return a power chord as the triad whose third the melody sounds on one of its beats, else as it is."""
    if chord.symbol != S.POWER:
        return chord
    for start, classes in melody.items():
        if chord.start <= start < chord.end:
            if (chord.root + MAJOR_THIRD) % OCTAVE in classes:
                return chord._replace(symbol=S.MAJOR)
            if (chord.root + MINOR_THIRD) % OCTAVE in classes:
                return chord._replace(symbol=S.MINOR)
    return chord


def at_level(*, chord, level):
    """Return a chord with its symbol as its level prints it."""
    symbol = AT_SEVENTHS.get(chord.symbol, chord.symbol)
    if level == ChordLevel.TRIADS:
        symbol = SEVENTHS_AT_TRIADS.get(symbol, symbol)
    return chord._replace(symbol=symbol)


def printed_basses(*, chords, level):
    """Return chords with the basses their level prints: none at Triads; at Sevenths only a bass that walks by step to the
    next chord's, or the fifth the next chord is rooted on."""
    printed = []
    for chord, following in zip(chords, chords[1:] + [None]):
        if chord.bass is not None and (level == ChordLevel.TRIADS or not keeps_its_bass(chord=chord, following=following)):
            chord = chord._replace(bass=None)
        printed.append(chord)
    return printed


def keeps_its_bass(*, chord, following):
    """Return whether a chord's bass is worth printing: it walks by step to the next chord's bass, or it is the fifth the
    next chord is rooted on."""
    if following is None:
        return False
    if chord.bass == (chord.root + FIFTH) % OCTAVE and following.root == chord.bass:
        return True
    next_bass = following.root if following.bass is None else following.bass
    gap = (next_bass - chord.bass) % OCTAVE
    return 0 < min(gap, OCTAVE - gap) <= LARGEST_STEP


def joined(chords):
    """Return chords with each run of one chord, end to end, as one."""
    runs = []
    for chord in chords:
        if runs and runs[-1].end == chord.start and runs[-1][2:] == chord[2:]:
            chord = runs.pop()._replace(end=chord.end)
        runs.append(chord)
    return runs


def members(*, root, symbol):
    """Return a chord's notes as pitch classes."""
    return frozenset((root + step) % OCTAVE for step in chord_shapes()[symbol])


def has_tritone(classes):
    """Return whether notes hold a tritone, the sign of a dominant or diminished chord."""
    return any((pitch_class + TRITONE) % OCTAVE in classes for pitch_class in classes)
