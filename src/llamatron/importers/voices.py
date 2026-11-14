# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Splitting a MIDI part into voices, each what one track of the song plays: one note or one chord at a time.

A pattern's step holds one note, or one note with a chord symbol, and a step's note lasts until
it ends, so a part that plays several notes at once is split, and nothing is ever cut or left
out:

- Drums are split by sound, a voice for each drum, since a drum pattern's step holds one note.
- A part that plays both hands, notes together on both sides of middle C, is split into its
  treble and its bass.
- Notes that start and end together, at one velocity, in a shape a chord symbol has, like a
  major triad, are one chord, when chords are asked for.
- Whatever still overlaps goes into voices by rank at each moment: the top note first for a
  treble, the bottom note first for a bass, each into the first voice that is free then, so a
  melody keeps to its voice as long as it can.
"""

from collections import Counter
from dataclasses import dataclass, field
from typing import NamedTuple

from llamatron.composition.file_format import CC_ROWS, FIXED_CHORDS
from llamatron.strings.importing import (
    MSG_BASS_PART, MSG_DRUM_NAMES, MSG_TREBLE_PART, MSG_UNNAMED_DRUM, MSG_VOICE_LETTERS, MSG_VOICE_PART,
)

# Middle C, where a part that plays both hands is split. A part plays both hands when enough of its
# notes sound together with a note further away than one hand reaches, a tenth and a little more.
MIDDLE_C = 60
HAND_REACH = 16
HAND_SHARE = 0.1
FIRST_DRUM_NUMBER = 1


def chord_shapes():
    """Return the chord symbols by the half steps of their notes above the lowest, the first symbol for a shape winning."""
    shapes = {}
    for symbol, chord_type in FIXED_CHORDS.items():
        shapes.setdefault(chord_type.value, symbol)
    return shapes


SHAPES = chord_shapes()


# The CC numbers a track's lanes take first, in this order, each only if the part sends it: the mod wheel, volume and
# the sustain pedal, the user's order of 2026-11-10. The lanes left take the part's other CCs, the most sent first.
MOD_WHEEL = 1
VOLUME = 7
SUSTAIN = 64
CC_PRIORITY = (MOD_WHEEL, VOLUME, SUSTAIN)
# The channel mode messages, like all notes off, which share the CC numbers from here up and are never a lane's.
FIRST_CHANNEL_MODE = 120


class Played(NamedTuple):
    """What a voice plays at one time: when it starts and ends, its MIDI numbers from the lowest, its velocity, and its chord symbol if it is a chord."""

    start: object
    end: object
    pitches: tuple
    velocity: int
    chord: object


@dataclass(slots=True, kw_only=True)
class Voice:
    """What one track of the imported song plays: its name, whether it is a drum, what it plays, in time order, nothing overlapping, and the CC numbers its lanes send with the CC messages they come from."""

    name: str
    drum: bool
    played: list
    lanes: list = field(default_factory=list)
    controls: list = field(default_factory=list)


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
            voices += named_voices(name=name, drum=False, lines=lines_of(units=units, from_top=from_top))
    lanes = control_lanes(part) if controls else []
    if lanes:
        voices[0].lanes = lanes
        voices[0].controls = [control for control in part.controls if control.number in lanes]
    return voices


def control_lanes(part):
    """Return the CC numbers a part's track brings in, in the order its lanes take them: those of CC_PRIORITY the part sends, then its others, the most sent first, as many as a track has lanes."""
    sent = Counter(control.number for control in part.controls if control.number < FIRST_CHANNEL_MODE)
    first = [number for number in CC_PRIORITY if number in sent]
    others = sorted((number for number in sent if number not in CC_PRIORITY), key=lambda number: (-sent[number], number))
    return (first + others)[:len(CC_ROWS)]


def single(note):
    """Return one note as what a voice plays."""
    return Played(note.start, note.end, (note.pitch,), note.velocity, None)


def drum_voices(part):
    """Return a voice for each drum sound a part plays, from the lowest note, named after General MIDI's name for it or perc 1 and so on."""
    voices = []
    unnamed = FIRST_DRUM_NUMBER
    for pitch in sorted({note.pitch for note in part.notes}):
        name = MSG_DRUM_NAMES.get(pitch)
        if name is None:
            name = MSG_UNNAMED_DRUM.format(number=unnamed)
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
        return [(MSG_TREBLE_PART.format(track=part.name), above, True), (MSG_BASS_PART.format(track=part.name), below, False)]
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
        symbol = chord_symbol(pitches)
        if symbol is None:
            units += [Played(start, end, (pitch,), velocity, None) for pitch in pitches]
        else:
            units.append(Played(start, end, tuple(pitches), velocity, symbol))
    return sorted(units)


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
    letters = len(MSG_VOICE_LETTERS)
    if place < letters:
        return MSG_VOICE_LETTERS[place]
    return voice_letter(place // letters - 1) + MSG_VOICE_LETTERS[place % letters]


def named_voices(*, name, drum, lines):
    """Return the voices of lines, named after the part alone when there is one and lettered when there are several."""
    if len(lines) == 1:
        return [Voice(name=name, drum=drum, played=lines[0])]
    return [Voice(name=MSG_VOICE_PART.format(part=name, letter=voice_letter(place)), drum=drum, played=line) for place, line in enumerate(lines)]
