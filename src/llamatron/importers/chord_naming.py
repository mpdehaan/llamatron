# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Naming notes struck together as one step's chord, as the Chord rows play it, so that a hand's chords are one track.

The readings are tried in the order a player names a chord, plainest first, so that a chord is never given a wrong name
(the user's order, with the professor's one exception):

1. a chord in root position or an inversion;
2. that with notes doubled an octave away (the Double row), or with chord tones left out (the Omit row), and then both;
3. a slash chord, where the lowest note lies a 5th or more below the rest and the rest are a chord by 1 or 2, the lowest
   note the Bass, and with the octave above it too the Bass Octave; the Realizer plays the bass in the nearest octave below
   the chord, so only a bass there is read so.

Where two readings fit at the same rank, the one with the chord of the step before wins, so a held chord over a moving
bass reads as a line, Am, Am/G, Am/F#. A shape is matched as the Realizer voices it: the chord from its root, the
omitted tones left out, its lowest notes lifted for its inversion.
"""

from typing import NamedTuple

from llamatron.model.schema import file_format, limits
from llamatron.music_theory.fundamentals import chord_shapes, intervals

NO_INVERSION = 0
# How far a slash chord's bass lies under the chord at least, a 5th, so that a chord with its root a little below the rest is
# read as the chord it is, and how far at most, within the octave the Realizer plays it in.
SLASH_GAP = 7
OCTAVE = intervals.HALF_STEPS_PER_OCTAVE
# A chord of four notes, its shape three notes above the root, the only kind read with notes left out.
FOUR_NOTE_SHAPE = 3
# The omissions in the order a reading prefers them, the Omit row's own order.
OMISSION_RANKS = {omission: rank for rank, omission in enumerate(file_format.OMISSIONS, start=1)}
# The four-note chords a reading with notes left out prefers, as players voice them: the sevenths, the dominant first, and
# the sixes last, so that F# C alone is D7's 3rd and 7th rather than a minor six's.
OMITTED_SYMBOLS = (
    file_format.ChordSymbol.DOMINANT7, file_format.ChordSymbol.MINOR7, file_format.ChordSymbol.MAJOR7, file_format.ChordSymbol.HALF_DIMINISHED7,
    file_format.ChordSymbol.DIMINISHED7, file_format.ChordSymbol.DOMINANT7_SUS4, file_format.ChordSymbol.MINOR_MAJOR7,
    file_format.ChordSymbol.AUGMENTED7, file_format.ChordSymbol.AUGMENTED_MAJOR7, file_format.ChordSymbol.ADD9,
    file_format.ChordSymbol.MINOR_ADD9, file_format.ChordSymbol.MAJOR6, file_format.ChordSymbol.MINOR6,
)
OMITTED_SYMBOL_RANKS = {symbol: rank for rank, symbol in enumerate(OMITTED_SYMBOLS, start=1)}


class NamedChord(NamedTuple):
    """How a step plays notes struck together: its chord symbol, or None for one note, its inversion, its root, the MIDI
    number its degree is written from, its Double and Omit rows' values or None, and its Bass as a MIDI number, or None,
    with whether the Bass Octave plays."""

    symbol: object
    inversion: int
    root: int
    doubling: object = None
    omission: object = None
    bass: object = None
    bass_octave: bool = False

    def same_chord(self, other):
        """Return whether another reading is the same chord, its symbol on the same note, as a held chord over a moving bass is."""
        return other is not None and self.symbol == other.symbol and self.root % OCTAVE == other.root % OCTAVE


def voicing_table():
    """Return every shape a step's chord can sound as, by its notes' half steps above its lowest, each with the readings that
    sound so, plainest first: (symbol, omission, inversion, the root's half steps above the lowest note). Only a chord of four
    notes, a seventh or a six, is read with notes left out, as a pianist voices it with three fingers: a triad less a note is
    an interval, and a ninth to a thirteenth less notes is read as the slash chord players write instead."""
    table = {}
    for omission in (None, *file_format.OMISSIONS):
        for symbol, chord_type in file_format.FIXED_CHORDS.items():
            for key, reading in shape_readings(symbol=symbol, shape=chord_type.value, omission=omission):
                table.setdefault(key, []).append(reading)
    return table


def shape_readings(*, symbol, shape, omission):
    """Return the shapes one chord sounds as with an omission, in root position and each inversion, as (its notes' half steps
    above its lowest, (symbol, omission, inversion, the root's half steps above the lowest)); none for an omission of a chord
    that isn't four notes."""
    if omission is not None and len(shape) != FOUR_NOTE_SHAPE:
        return []
    notes = sounding(shape=shape, omission=omission)
    if notes is None:
        return []
    readings = []
    for inversion in (NO_INVERSION, *limits.INVERSIONS):
        voiced = inverted(notes=notes, inversion=inversion)
        if voiced is not None:
            lowest = voiced[0]
            readings.append((tuple(note - lowest for note in voiced), (symbol, omission, inversion, -lowest)))
    return readings


def chord_named(pitches, *, before=None):
    """Return how a step plays exactly these MIDI numbers, lowest first, as a NamedChord, or None where no reading does; before
    is the reading of the step before, whose chord wins a tie."""
    for reading in (plain_chord, chord_with_one_change, chord_with_both_changes, slash_chord):
        named = reading(pitches=list(pitches), before=before)
        if named is not None:
            return named
    return None


def plain_chord(*, pitches, before):
    """Return the chord, in root position or an inversion, these MIDI numbers are, or None."""
    return voiced_chord(pitches=pitches, before=before, omitting=False)


def chord_with_one_change(*, pitches, before):
    """Return a chord with notes doubled an octave away, or with chord tones left out, these MIDI numbers are, or None."""
    doubled = doubled_chord(pitches=pitches, before=before, omitting=False)
    if doubled is not None:
        return doubled
    return voiced_chord(pitches=pitches, before=before, omitting=True)


def chord_with_both_changes(*, pitches, before):
    """Return a chord with chord tones left out and notes doubled an octave away these MIDI numbers are, or None."""
    return doubled_chord(pitches=pitches, before=before, omitting=True)


def slash_chord(*, pitches, before):
    """Return a chord over a bass these MIDI numbers are, or None: the lowest note, or the lowest two an octave apart, a 5th or
    more under the rest, within the octave below the rest's lowest note, where the Realizer plays a Bass, and the rest a
    chord read plainly or with one change."""
    bass_octave = len(pitches) > 3 and pitches[1] - pitches[0] == OCTAVE
    under = 2 if bass_octave else 1
    bass, rest = pitches[under - 1], pitches[under:]
    if len(rest) < 2 or rest[0] - bass < SLASH_GAP or rest[0] - bass >= OCTAVE:
        return None
    for reading in (plain_chord, chord_with_one_change):
        named = reading(pitches=rest, before=before)
        if named is not None and named.root % OCTAVE != bass % OCTAVE:
            return NamedChord(named.symbol, named.inversion, named.root, named.doubling, named.omission, bass, bass_octave)
    return None


def doubled_chord(*, pitches, before, omitting):
    """Return a chord or one note with notes doubled an octave away these MIDI numbers are, read with or without chord tones
    left out, or None."""
    for doubling in file_format.DOUBLINGS:
        undoubled = undoubled_pitches(pitches=pitches, doubling=doubling)
        if undoubled is None or doubled_pitches(pitches=undoubled, doubling=doubling) != pitches:
            continue
        if len(undoubled) == 1 and not omitting:
            return NamedChord(None, NO_INVERSION, undoubled[0], doubling)
        named = voiced_chord(pitches=undoubled, before=before, omitting=omitting)
        if named is not None:
            return NamedChord(named.symbol, named.inversion, named.root, doubling, named.omission)
    return None


def voiced_chord(*, pitches, before, omitting):
    """Return the chord, its inversion and its root these MIDI numbers sound as, read with no chord tone left out or, when
    omitting, with some, the chord of the step before winning a tie, or None."""
    if len(pitches) < 2 or len(set(pitches)) != len(pitches):
        return None
    lowest = pitches[0]
    readings = []
    for symbol, omission, inversion, root in VOICINGS.get(tuple(pitch - lowest for pitch in pitches), []):
        if (omission is not None) == omitting:
            readings.append(NamedChord(symbol, inversion, lowest + root, omission=omission))
    if not readings:
        return None
    # An omission players reach for sooner first, then root position before any inversion, whatever the symbol, the symbols
    # in their order.
    readings.sort(key=lambda named: (OMISSION_RANKS.get(named.omission, 0), named.inversion, OMITTED_SYMBOL_RANKS.get(named.symbol, 0)))
    for named in readings:
        if named.same_chord(before):
            return named
    return readings[0]


def sounding(*, shape, omission):
    """Return a chord's notes as half steps from its root, from the root up, with those an omission leaves out gone, or None
    where it would leave fewer than two."""
    notes = [0, *shape]
    if omission is not None:
        roles = file_format.OMITTED_ROLES[omission]
        notes = [note for note in notes if chord_shapes.role_of(note) not in roles]
    if len(notes) < 2:
        return None
    return notes


def inverted(*, notes, inversion):
    """Return a chord's notes, lowest first, with its lowest notes moved up an octave for its inversion, as the Realizer moves
    them, or None for an inversion past the chord's last, which plays as the one before it."""
    if inversion > len(notes) - 1:
        return None
    lifted = [note + OCTAVE for note in notes[:inversion]]
    return sorted([*notes[inversion:], *lifted])


def undoubled_pitches(*, pitches, doubling):
    """Return the MIDI numbers, lowest first, that a doubling would make these from, or None where it couldn't: the lowest
    note's or the top note's octave taken away, or, for every note doubled, the notes no octave of a note kept covers."""
    first, last, octaves = file_format.DOUBLED_NOTES[doubling]
    half_steps = octaves * OCTAVE
    if last is not None or first:
        copied = pitches[first:last][0] + half_steps
        if copied not in pitches:
            return None
        return [pitch for pitch in pitches if pitch != copied]
    kept = []
    covered = set()
    for pitch in sorted(pitches, reverse=half_steps < 0):
        if pitch not in covered:
            kept.append(pitch)
            covered.add(pitch + half_steps)
    return sorted(kept)


def doubled_pitches(*, pitches, doubling):
    """Return MIDI numbers, lowest first, with those a doubling plays again an octave away added, each once, as the Realizer
    plays a step's Double row."""
    first, last, octaves = file_format.DOUBLED_NOTES[doubling]
    half_steps = octaves * OCTAVE
    return sorted({*pitches, *[pitch + half_steps for pitch in pitches[first:last]]})


VOICINGS = voicing_table()
