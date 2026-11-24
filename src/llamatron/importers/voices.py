# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Splitting a MIDI part into voices, each what one track of the song plays: one note or one chord at a time.

A pattern's step holds one note, or one note with a chord symbol, and a step's note lasts until
it ends, so a part that plays several notes at once is split, and nothing is ever cut or left
out:

- Drums are split by sound, a voice for each drum, since a drum pattern's step holds one note.
- A part that plays both hands, notes together on both sides of middle C, is split into its
  treble and its bass.
- Notes that start and end together, at one velocity, in a shape a chord symbol has, like a
  major triad, are one chord, when chords are asked for, in root position or in an inversion,
  which the Inversion row plays exactly as the file does.
- Whatever still overlaps goes into voices by rank at each moment: the top note first for a
  treble, the bottom note first for a bass, each into the first voice that is free then, so a
  melody keeps to its voice as long as it can.
"""

import bisect
from collections import Counter
from dataclasses import dataclass, field
from typing import NamedTuple

from llamatron.math.rational import Rational
from llamatron.model.schema import file_format, limits
from llamatron.music_theory.fundamentals import intervals
from llamatron.user_strings import importing

# Middle C, where a part that plays both hands is split. A part plays both hands when enough of its
# notes sound together with a note further away than one hand reaches, a tenth and a little more.
MIDDLE_C = 60
HAND_REACH = 16
HAND_SHARE = 0.1
FIRST_DRUM_NUMBER = 1
# A note held into the next by less than this share of itself is slurred into it on purpose, a legato line (legato_line).
LEGATO_SHARE = Rational(1, 2)
# The General MIDI sounds, numbered from 1, of instruments that play one note at a time: the basses, the solo brass, the
# reeds, the pipes and the synth leads. The brass section and the synth brass play chords, and are left out.
MONOPHONIC_SOUNDS = (range(33, 41), range(57, 62), range(65, 89))
# The General MIDI sound a part's tracks get where the file sets no program: a piano, which the user can change.
DEFAULT_SOUND = limits.MIN_GM_SOUND
# A chord in root position, which writes no Inversion.
NO_INVERSION = 0


def chord_shapes():
    """Return the chord symbols by the half steps of their notes above the lowest, the first symbol for a shape winning."""
    shapes = {}
    for symbol, chord_type in file_format.FIXED_CHORDS.items():
        shapes.setdefault(chord_type.value, symbol)
    return shapes


SHAPES = chord_shapes()


# The CC numbers a track's lanes take first, in this order, each only if the part sends it: the mod wheel, volume and
# the sustain pedal. The lanes left take the part's other CCs, the most sent first.
MOD_WHEEL = 1
VOLUME = 7
SUSTAIN = 64
CC_PRIORITY = (MOD_WHEEL, VOLUME, SUSTAIN)
# The channel mode messages, like all notes off, which share the CC numbers from here up and are never a lane's.
FIRST_CHANNEL_MODE = 120


class Played(NamedTuple):
    """What a voice plays at one time: when it starts and ends, its MIDI numbers from the lowest, its velocity, its chord symbol
    if it is a chord, the chord's inversion, 0 for root position, and the chord's root, which its step's degree is written from."""

    start: object
    end: object
    pitches: tuple
    velocity: int
    chord: object
    inversion: int = 0
    root: object = None
    # Whether it runs on into the next note with Glide, as a legato line played on purpose does (legato_line).
    glide: bool = False
    # What its Double row plays again an octave away (file_format.DOUBLINGS), or None.
    doubling: object = None

    def written_pitch(self):
        """Return the MIDI number a step's degree is written from: a chord's root, or the note itself."""
        if self.root is None:
            return self.pitches[0]
        return self.root


@dataclass(slots=True, kw_only=True)
class Voice:
    """What one track of the imported song plays: its name, whether it is a drum, what it plays, in time order, nothing overlapping, and the CC numbers its lanes send with the CC messages they come from."""

    name: str
    drum: bool
    played: list
    lanes: list = field(default_factory=list)
    controls: list = field(default_factory=list)
    # The General MIDI sound its track's instrument plays, numbered 1 to 128 as people number them, or None for a drum's.
    sound: object = None

    def carried_into(self, time):
        """Return what the voice plays that starts before a time and is still held at it, or None: a note a pattern of a clip's
        list holds on with a tie from the pattern before."""
        place = bisect.bisect_left(self.played, time, key=start_of)
        if place and self.played[place - 1].end > time:
            return self.played[place - 1]
        return None

    def played_between(self, *, begin, end):
        """Return what the voice plays starting at or after one time and before another, found by halving, since what it plays is
        in time order and a scene by scene import asks this of every scene: going through every note each time grew with the
        square of the song's length."""
        return self.played[bisect.bisect_left(self.played, begin, key=start_of):bisect.bisect_left(self.played, end, key=start_of)]


def start_of(played):
    """When something played starts."""
    return played.start


def voices_of(*, part, chords, controls):
    """Return the voices a part splits into, in the order their tracks go: drums by sound, and otherwise each hand's voices from the outside in.

    With controls, the first voice takes the part's CC messages of the numbers the import brings
    in, since a CC belongs to the whole channel, and sending it from every voice would send it twice.
    """
    if part.is_drums():
        voices = drum_voices(part)
    else:
        voices = []
        for name, notes, from_top in hands(part):
            units = chord_units(notes) if chords else [single(note) for note in notes]
            units = legato_line(units=units, monophonic=plays_one_note_at_a_time(part))
            voices += named_voices(name=name, drum=False, lines=lines_of(units=units, from_top=from_top))
    if not part.is_drums():
        for voice in voices:
            voice.sound = sound_of(part)
    lanes = control_lanes(part) if controls else []
    if lanes:
        voices[0].lanes = lanes
        voices[0].controls = [control for control in part.controls if control.number in lanes]
    return voices


def sound_of(part):
    """Return the General MIDI sound a part's program sets, numbered from 1, or the piano where the file sets none."""
    if part.program is None:
        return DEFAULT_SOUND
    return part.program + limits.MIN_GM_SOUND


def legato_line(*, units, monophonic):
    """Return what a hand plays, as one line with Glide where it is a legato line: single notes one after another, none
    starting together, each next note starting while the last still sounds, as a horn or a voice slurs a phrase on purpose.
    An instrument that plays one note at a time (monophonic) slurs wherever its notes overlap; any other only where every
    overlap is short, under LEGATO_SHARE of the earlier note, and reaches no further than the next note, so that two voices
    of a keyboard's line are never run into one. Each slurred note ends where the next starts, with Glide, which runs it on
    into the next as a monosynth slides; anything else, chords or notes sounding together, is as it was."""
    ordered = sorted(units, key=start_of)
    pairs = list(zip(ordered, ordered[1:]))
    if any(len(unit.pitches) > 1 for unit in ordered) or any(later.start == earlier.start for earlier, later in pairs):
        return units
    if not any(earlier.end > later.start for earlier, later in pairs):
        return units
    if not monophonic and not all(is_short_slur(earlier=earlier, later=later, after=after) for (earlier, later), after in zip(pairs, [*ordered[2:], None])):
        return units
    joined = []
    for earlier, later in zip(ordered, [*ordered[1:], None]):
        if later is not None and earlier.end > later.start:
            earlier = Played(earlier.start, later.start, earlier.pitches, earlier.velocity, earlier.chord, earlier.inversion, earlier.root, True, earlier.doubling)
        joined.append(earlier)
    return joined


def is_short_slur(*, earlier, later, after):
    """Return whether a note, on any instrument, can be slurred into the next: it ends before the next starts, or overlaps it
    by under LEGATO_SHARE of itself and ends before the note after."""
    if earlier.end <= later.start:
        return True
    return is_legato(earlier=earlier, later=later) and (after is None or earlier.end <= after.start)


def plays_one_note_at_a_time(part):
    """Return whether a part's General MIDI sound is an instrument that plays one note at a time, a bass, a solo brass
    instrument, a reed, a pipe or a synth lead, so that its overlapping notes are slurs (MONOPHONIC_SOUNDS)."""
    return part.program is not None and any(part.program + limits.MIN_GM_SOUND in sounds for sounds in MONOPHONIC_SOUNDS)


def is_legato(*, earlier, later):
    """Return whether a note runs on into the next as a legato line does: the next starts after it and while it sounds, by
    less than LEGATO_SHARE of it."""
    return earlier.start < later.start < earlier.end and earlier.end - later.start < LEGATO_SHARE * (earlier.end - earlier.start)


def control_lanes(part):
    """Return the CC numbers a part's track brings in, in the order its lanes take them: those of CC_PRIORITY the part sends, then its others, the most sent first, as many as a track has lanes."""
    sent = Counter(control.number for control in part.controls if control.number < FIRST_CHANNEL_MODE)
    first = [number for number in CC_PRIORITY if number in sent]
    others = sorted((number for number in sent if number not in CC_PRIORITY), key=lambda number: (-sent[number], number))
    return (first + others)[:len(file_format.CC_ROWS)]


def single(note):
    """Return one note as what a voice plays."""
    return Played(note.start, note.end, (note.pitch,), note.velocity, None)


def drum_voices(part):
    """Return a voice for each drum sound a part plays, from the lowest note, named after General MIDI's name for it or perc 1 and so on."""
    voices = []
    unnamed = FIRST_DRUM_NUMBER
    for pitch in sorted({note.pitch for note in part.notes}):
        name = importing.MSG_DRUM_NAMES.get(pitch)
        if name is None:
            name = importing.MSG_UNNAMED_DRUM.format(number=unnamed)
            unnamed += 1
        units = [single(note) for note in part.notes if note.pitch == pitch]
        voices += named_voices(name=name, drum=True, lines=lines_of(units=units, from_top=True))
    return voices


def hands(part):
    """Return a part as the hands it plays, each a name, its notes and whether its voices rank from the top: the treble and the bass for a part that plays both, and otherwise the part whole."""
    notes = part.notes
    below = [note for note in notes if note.pitch < MIDDLE_C]
    above = [note for note in notes if note.pitch >= MIDDLE_C]
    if below and above and beyond_one_hand(notes) >= HAND_SHARE * len(notes):
        return [(importing.MSG_TREBLE_PART.format(track=part.name), above, True), (importing.MSG_BASS_PART.format(track=part.name), below, False)]
    return [(part.name, notes, True)]


def beyond_one_hand(notes):
    """Return how many of the notes, in the order they start, sound together with a note further from them than one hand reaches."""
    far = set()
    sounding = []
    for place, note in enumerate(notes):
        sounding = [(other, before) for other, before in sounding if before.end > note.start]
        for other, before in sounding:
            if abs(before.pitch - note.pitch) > HAND_REACH:
                far.update((other, place))
        sounding.append((place, note))
    return len(far)


def chord_units(notes):
    """Return the notes as what voices play, where notes that start and end together at one velocity in a chord symbol's shape are one chord."""
    together = {}
    for note in notes:
        together.setdefault((note.start, note.end, note.velocity), []).append(note.pitch)
    units = []
    for (start, end, velocity), pitches in together.items():
        pitches = sorted(pitches)
        named = chord_named(pitches)
        if named is None:
            units += [Played(start, end, (pitch,), velocity, None) for pitch in pitches]
        else:
            units.append(Played(start, end, tuple(pitches), velocity, named.symbol, named.inversion, named.root, doubling=named.doubling))
    return sorted(units)


class NamedChord(NamedTuple):
    """How a step plays notes struck together: its chord symbol, or None for one note doubled, its inversion, its root, the
    MIDI number its degree is written from, and what its Double row plays again an octave away, or None."""

    symbol: object
    inversion: int
    root: int
    doubling: object = None


def chord_named(pitches):
    """Return how a step plays exactly these MIDI numbers, lowest first (NamedChord), or None: a chord in root position or
    an inversion, and failing that a chord or one note with notes doubled an octave away, as the Double row plays them."""
    named = voiced_chord(pitches)
    if named is not None:
        return named
    for doubling in file_format.DOUBLINGS:
        undoubled = undoubled_pitches(pitches=pitches, doubling=doubling)
        if undoubled is None or doubled_pitches(pitches=undoubled, doubling=doubling) != list(pitches):
            continue
        if len(undoubled) == 1:
            return NamedChord(None, NO_INVERSION, undoubled[0], doubling)
        named = voiced_chord(undoubled)
        if named is not None:
            return NamedChord(named.symbol, named.inversion, named.root, doubling)
    return None


def undoubled_pitches(*, pitches, doubling):
    """Return the MIDI numbers, lowest first, that a doubling would make these from, or None where it couldn't: the lowest
    note's or the top note's octave taken away, or, for every note doubled, the notes no octave of a note kept covers."""
    first, last, octaves = file_format.DOUBLED_NOTES[doubling]
    half_steps = octaves * intervals.HALF_STEPS_PER_OCTAVE
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
    """Return MIDI numbers, lowest first, with those a doubling plays again an octave away added, each once, as the
    Realizer plays a step's Double row."""
    first, last, octaves = file_format.DOUBLED_NOTES[doubling]
    half_steps = octaves * intervals.HALF_STEPS_PER_OCTAVE
    return sorted({*pitches, *[pitch + half_steps for pitch in pitches[first:last]]})


def voiced_chord(pitches):
    """Return the chord symbol, inversion and root whose chord plays exactly these MIDI numbers, lowest first, or None: root
    position first, then each inversion the Inversion row has, which moves so many of a chord's lowest notes up an octave."""
    symbol = chord_symbol(pitches)
    if symbol is not None:
        return NamedChord(symbol, NO_INVERSION, pitches[0])
    for inversion in limits.INVERSIONS:
        if inversion >= len(pitches):
            break
        # The chord in root position: the notes moved up, brought back down under the others.
        rooted = [pitch - intervals.HALF_STEPS_PER_OCTAVE for pitch in pitches[-inversion:]] + list(pitches[:-inversion])
        if rooted != sorted(rooted):
            continue
        symbol = chord_symbol(rooted)
        if symbol is not None:
            return NamedChord(symbol, inversion, rooted[0])
    return None


def chord_symbol(pitches):
    """Return the chord symbol whose notes are these MIDI numbers above the lowest, or None for one note or a shape no symbol has."""
    if len(pitches) < 2 or len(set(pitches)) != len(pitches):
        return None
    return SHAPES.get(tuple(pitch - pitches[0] for pitch in pitches[1:]))


def lines_of(*, units, from_top):
    """Return what each voice plays, the units shared out by rank at each moment into the first voices free then, new voices made as more are needed."""
    lines = []
    ends = []
    by_start = {}
    for unit in units:
        by_start.setdefault(unit.start, []).append(unit)
    for start in sorted(by_start):
        ranked = sorted(by_start[start], key=lambda unit: unit.pitches[-1] if from_top else unit.pitches[0], reverse=from_top)
        free = [place for place, end in enumerate(ends) if end <= start]
        for unit in ranked:
            if free:
                place = free.pop(0)
            else:
                lines.append([])
                ends.append(start)
                place = len(lines) - 1
            lines[place].append(unit)
            ends[place] = unit.end
    return lines


def voice_letter(place):
    """Return the letter of a voice counted from 0, like a, carrying on as aa, ab after z."""
    letters = len(importing.MSG_VOICE_LETTERS)
    if place < letters:
        return importing.MSG_VOICE_LETTERS[place]
    return voice_letter(place // letters - 1) + importing.MSG_VOICE_LETTERS[place % letters]


def named_voices(*, name, drum, lines):
    """Return the voices of lines, named after the part alone when there is one and lettered when there are several."""
    if len(lines) == 1:
        return [Voice(name=name, drum=drum, played=lines[0])]
    return [Voice(name=importing.MSG_VOICE_PART.format(part=name, letter=voice_letter(place)), drum=drum, played=line) for place, line in enumerate(lines)]
