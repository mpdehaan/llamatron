# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Naming notes struck together as one step's chord, as the Chord rows play it, so that a hand's chords are one track.

The readings are tried in the order a player names a chord, plainest first, so that a chord is never given a wrong name
(the user's order, with the professor's one exception):

1. a chord in root position or an inversion;
2. that with one change: notes doubled an octave away (the Double row), chord tones left out of a four-note chord (the
   Omit row), or one tension added (the Tension row);
3. that with two of those changes, such as D7's 3rd and 7th with its 13th, C F# B, the classic left hand;
4. a slash chord, where the lowest note lies a 5th or more below the rest and the rest are a chord by 1 or 2, the lowest
   note the Bass, and with the octave above it too the Bass Octave; the Realizer plays the bass in the nearest octave below
   the chord, so only a bass there is read so.

Where two readings fit at one rank, a root in the key wins, then the chord of the step before, so that F and B alone are
G7's 3rd and 7th in C rather than C#7's, and a held chord over a moving bass reads as a line, Am, Am/G, Am/F#. A shape is
matched as the Realizer voices it: the chord from its root, its tension added, the omitted tones left out, its lowest notes
lifted for its inversion.
"""

import itertools
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
# The omissions in the order a reading prefers them, their row's own order; with a tension added, those that keep the 3rd
# and 7th first, the guide tones and the rootless voicings a pianist plays a 13th or a 9th with; and the tensions players
# add most first.
OMISSION_RANKS = {omission: rank for rank, omission in enumerate(file_format.OMISSIONS, start=1)}
OMISSION_RANKS_WITH_A_TENSION = {
    omission: rank for rank, omission in enumerate((
        file_format.Omission.NO_ROOT_FIFTH, file_format.Omission.NO_ROOT, file_format.Omission.NO_FIFTH,
        file_format.Omission.NO_THIRD, file_format.Omission.NO_THIRD_FIFTH,
    ), start=1)
}
TENSION_RANKS = {
    tension: rank for rank, tension in enumerate((
        file_format.Tension.THIRTEENTH, file_format.Tension.NINTH, file_format.Tension.FLAT_NINTH, file_format.Tension.SHARP_ELEVENTH,
        file_format.Tension.ELEVENTH, file_format.Tension.SHARP_NINTH, file_format.Tension.FLAT_THIRTEENTH,
    ), start=1)
}
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
    number its degree is written from, its Double and Omit rows' values or None, its Bass as a MIDI number, or None, with
    whether the Bass Octave plays, and its one tension, or None."""

    symbol: object
    inversion: int
    root: int
    doubling: object = None
    omission: object = None
    bass: object = None
    bass_octave: bool = False
    tension: object = None

    def same_chord(self, other):
        """Return whether another reading is the same chord, its symbol on the same note, as a held chord over a moving bass is."""
        return other is not None and self.symbol == other.symbol and self.root % OCTAVE == other.root % OCTAVE

    def with_doubling(self, doubling):
        """Return the reading with notes doubled an octave away."""
        return NamedChord(self.symbol, self.inversion, self.root, doubling, self.omission, self.bass, self.bass_octave, self.tension)

    def over_bass(self, *, bass, bass_octave):
        """Return the reading over a bass, a MIDI number, with the Bass Octave or not."""
        return NamedChord(self.symbol, self.inversion, self.root, self.doubling, self.omission, bass, bass_octave, self.tension)


class Hearing(NamedTuple):
    """What decides between readings of notes struck together that fit equally: the key's notes, as places in the octave, a
    root among them winning, or None where the key isn't known, and the reading of the step before, whose chord wins next."""

    in_key: object = None
    before: object = None

    def ranked(self, readings):
        """Return readings that fit equally in the order this hearing prefers them: a root in the key, then the step before's
        chord, then as given."""
        return sorted(readings, key=lambda named: (not self.has_root_in_key(named), not named.same_chord(self.before)))

    def has_root_in_key(self, named):
        return self.in_key is None or named.root % OCTAVE in self.in_key

    def after(self, named):
        """Return the hearing of the next notes struck together, after these were read as named."""
        return Hearing(self.in_key, named)


class Reading(NamedTuple):
    """One way a chord sounds as a shape: its symbol, the chord tones it leaves out, the tension it adds, its inversion, and its
    root's half steps above the lowest note it sounds."""

    symbol: str
    omission: object
    tension: object
    inversion: int
    root: int

    def kind_rank(self):
        """Return how soon a reading's omission and tension are preferred, those players reach for sooner first."""
        ranks = OMISSION_RANKS
        if self.tension is not None:
            ranks = OMISSION_RANKS_WITH_A_TENSION
        return (ranks.get(self.omission, 0), TENSION_RANKS.get(self.tension, 0))

    def rank(self):
        """Return how soon a reading is preferred among those of its kind: its omission and tension; then, a chord with notes
        left out, the symbols in the order players voice them before its inversion, so F B alone is G7's 3rd and 7th rather
        than a diminished seventh's; and any other, root position before any inversion, whatever the symbol."""
        if self.omission is not None:
            return (*self.kind_rank(), OMITTED_SYMBOL_RANKS.get(self.symbol, 0), self.inversion)
        return (*self.kind_rank(), self.inversion, 0)


def voicing_table():
    """Return every shape a step's chord can sound as, by its notes' half steps above its lowest, each with the Readings that
    sound so. Only a chord of four notes, a seventh or a six, is read with notes left out, as a pianist voices it with three
    fingers: a triad less a note is an interval, and a ninth to a thirteenth less notes is read as the slash chord players
    write instead. Intervals take no tension."""
    table = {}
    every_way = itertools.product((None, *file_format.OMISSIONS), (None, *file_format.TENSIONS), file_format.FIXED_CHORDS.items())
    for omission, tension, (symbol, chord_type) in every_way:
        for key, reading in shape_readings(symbol=symbol, shape=chord_type.value, omission=omission, tension=tension):
            table.setdefault(key, []).append(reading)
    return table


def shape_readings(*, symbol, shape, omission, tension):
    """Return the shapes one chord sounds as with an omission and a tension, in root position and each inversion, as (its
    notes' half steps above its lowest, its Reading); none where the chord can't take them."""
    if omission is not None and len(shape) != FOUR_NOTE_SHAPE:
        return []
    if tension is not None and symbol in file_format.INTERVAL_CHORDS:
        return []
    notes = sounding(shape=shape, omission=omission, tension=tension)
    if notes is None:
        return []
    readings = []
    for inversion in (NO_INVERSION, *limits.INVERSIONS):
        voiced = inverted(notes=notes, inversion=inversion)
        if voiced is not None:
            lowest = voiced[0]
            readings.append((tuple(note - lowest for note in voiced), Reading(symbol, omission, tension, inversion, -lowest)))
    return readings


def chord_named(pitches, *, hearing=None):
    """Return how a step plays exactly these MIDI numbers, lowest first, as a NamedChord, or None where no reading does; the
    Hearing decides between readings that fit equally."""
    hearing = hearing or Hearing()
    for reading in (plain_chord, chord_with_one_change, chord_with_two_changes, slash_chord):
        named = reading(pitches=list(pitches), hearing=hearing)
        if named is not None:
            return named
    return None


def plain_chord(*, pitches, hearing):
    """Return the chord, in root position or an inversion, these MIDI numbers are, or None."""
    return voiced_chord(pitches=pitches, hearing=hearing, omitted=False, tensioned=False)


def chord_with_one_change(*, pitches, hearing):
    """Return a chord with one change these MIDI numbers are, notes doubled, chord tones left out or a tension added, or None."""
    named = doubled_chord(pitches=pitches, hearing=hearing, omitted=False, tensioned=False)
    if named is None:
        named = voiced_chord(pitches=pitches, hearing=hearing, omitted=True, tensioned=False)
    if named is None:
        named = voiced_chord(pitches=pitches, hearing=hearing, omitted=False, tensioned=True)
    return named


def chord_with_two_changes(*, pitches, hearing):
    """Return a chord with two of the changes these MIDI numbers are, or None."""
    named = doubled_chord(pitches=pitches, hearing=hearing, omitted=True, tensioned=False)
    if named is None:
        named = doubled_chord(pitches=pitches, hearing=hearing, omitted=False, tensioned=True)
    if named is None:
        named = voiced_chord(pitches=pitches, hearing=hearing, omitted=True, tensioned=True)
    return named


def slash_chord(*, pitches, hearing):
    """Return a chord over a bass these MIDI numbers are, or None: the lowest note, or the lowest two an octave apart, a 5th or
    more under the rest, within the octave below the rest's lowest note, where the Realizer plays a Bass, and the rest a
    chord read plainly or with one change."""
    bass_octave = len(pitches) > 3 and pitches[1] - pitches[0] == OCTAVE
    under = 2 if bass_octave else 1
    bass, rest = pitches[under - 1], pitches[under:]
    if len(rest) < 2 or rest[0] - bass < SLASH_GAP or rest[0] - bass >= OCTAVE:
        return None
    for reading in (plain_chord, chord_with_one_change):
        named = reading(pitches=rest, hearing=hearing)
        if named is not None and named.root % OCTAVE != bass % OCTAVE:
            return named.over_bass(bass=bass, bass_octave=bass_octave)
    return None


def doubled_chord(*, pitches, hearing, omitted, tensioned):
    """Return a chord or one note with notes doubled an octave away these MIDI numbers are, read with or without chord tones
    left out and a tension, or None."""
    for doubling in file_format.DOUBLINGS:
        undoubled = undoubled_pitches(pitches=pitches, doubling=doubling)
        if undoubled is None or doubled_pitches(pitches=undoubled, doubling=doubling) != pitches:
            continue
        if len(undoubled) == 1 and not omitted and not tensioned:
            return NamedChord(None, NO_INVERSION, undoubled[0], doubling)
        named = voiced_chord(pitches=undoubled, hearing=hearing, omitted=omitted, tensioned=tensioned)
        if named is not None:
            return named.with_doubling(doubling)
    return None


def voiced_chord(*, pitches, hearing, omitted, tensioned):
    """Return the chord these MIDI numbers sound as, with chord tones left out or not and a tension or not: among the readings
    whose omission and tension players reach for soonest, the one the hearing prefers, then by rank; or None."""
    if len(pitches) < 2 or len(set(pitches)) != len(pitches):
        return None
    lowest = pitches[0]
    readings = []
    for reading in VOICINGS.get(tuple(pitch - lowest for pitch in pitches), []):
        if (reading.omission is not None) == omitted and (reading.tension is not None) == tensioned:
            readings.append(reading)
    if not readings:
        return None
    soonest = min(reading.kind_rank() for reading in readings)
    named = []
    for reading in sorted(readings, key=Reading.rank):
        if reading.kind_rank() == soonest:
            named.append(NamedChord(reading.symbol, reading.inversion, lowest + reading.root, omission=reading.omission, tension=reading.tension))
    return hearing.ranked(named)[0]


def sounding(*, shape, omission, tension):
    """Return a chord's notes as half steps from its root, lowest first, with its tension added and the chord tones an omission
    leaves out gone, as the Realizer voices it, or None where it would leave fewer than two or the tension is a chord tone."""
    notes = [0, *shape]
    if tension is not None and file_format.TENSIONS[tension] in notes:
        return None
    if omission is not None:
        roles = file_format.OMITTED_ROLES[omission]
        notes = [note for note in notes if chord_shapes.role_of(note) not in roles]
    if tension is not None:
        notes.append(file_format.TENSIONS[tension])
    if len(notes) < 2:
        return None
    return sorted(notes)


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
