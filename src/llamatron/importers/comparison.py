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
"""Whether two MIDI files play the same music: the same notes at the same times, as long, as loud, at the same tempos.

This is how an import is proved: a MIDI file, imported, played and exported again, plays the
same notes as the file, the user's rule of 2026-11-10. Times are compared to the tick of
llamatron's own MIDI files, since two files can count ticks differently, and which track or
channel a note is on, the order of messages and the names in a file don't matter to how it
sounds, so they aren't compared.

The CC values a round trip brought in are compared as what a listener hears: for each part and
CC number, the value in force at every moment in the file against the value in force in the
export, giving the largest difference and the longest time the two disagree, so that exact means
the same value at every moment, and a sweep can be within a little of the file. The CC messages
the import leaves out, and says so, aren't compared.
"""

import os
from collections import Counter
from dataclasses import dataclass, field
from typing import NamedTuple

from llamatron.composition.setlist import Setlist
from llamatron.exporters.midi_arrangement import MidiSong
from llamatron.exporters.midi_messages import ticks
from llamatron.importers.midi_import import MidiImport
from llamatron.importers.midi_reading import read_midi
from llamatron.importers.writing import add_imported
from llamatron.playback.song_renderer import SongRenderer
from llamatron.support.rational import Rational

class ComparedNote(NamedTuple):
    """A note as compared: its start and end in llamatron's ticks, its MIDI number and its velocity."""

    start: int
    end: int
    pitch: int
    velocity: int


class ControlDifference(NamedTuple):
    """How far one track's CC number strays from the file: the largest difference in value, and the longest time in whole notes the two disagree."""

    track: str
    number: int
    largest: int
    longest: object


@dataclass(slots=True, kw_only=True)
class Comparison:
    """What differs between two MIDI files: the notes only the first plays, the notes only the second plays, the tempo changes that differ, each as (tick, tempo), and how each CC compared."""

    missing: list
    extra: list
    tempos_missing: list
    tempos_extra: list
    notes: int
    controls: list = field(default_factory=list)

    def is_same(self):
        return not (self.missing or self.extra or self.tempos_missing or self.tempos_extra) and self.controls_are_same()

    def controls_are_same(self):
        return all(difference.largest == 0 for difference in self.controls)

    def largest_control_difference(self):
        """Return the largest difference in any CC's value, and the longest time any disagrees, or None when no CC was compared."""
        if not self.controls:
            return None
        return max(difference.largest for difference in self.controls), max(difference.longest for difference in self.controls)


def values_over_time(*, controls, number):
    """Return a CC number's changes, as (time, value) in time order, a later value at one time replacing an earlier one."""
    changes = {}
    for control in controls:
        if control.number == number:
            changes[control.time] = control.value
    return sorted(changes.items())


def control_difference(*, first, second):
    """Return the largest difference between two CC curves, each (time, value) changes, and the longest time they disagree, in whole notes.

    Only the moments the first has a value are compared, since before its first message there is
    nothing to hear. After the last change of either, the last values are compared once.
    """
    times = sorted({time for time, _ in first} | {time for time, _ in second})
    largest = 0
    longest = Rational(0)
    disagreeing_since = None
    first_value = second_value = None
    first_place = second_place = 0
    for place, time in enumerate(times):
        while first_place < len(first) and first[first_place][0] <= time:
            first_value = first[first_place][1]
            first_place += 1
        while second_place < len(second) and second[second_place][0] <= time:
            second_value = second[second_place][1]
            second_place += 1
        differs = first_value is not None and first_value != second_value
        if differs:
            largest = max(largest, abs(first_value - (second_value if second_value is not None else 0)))
            if disagreeing_since is None:
                disagreeing_since = time
        elif disagreeing_since is not None:
            longest = max(longest, time - disagreeing_since)
            disagreeing_since = None
    return largest, longest


def heard_notes(midi_file):
    """Return every note a mido file plays, as ComparedNotes, whatever track or channel it is on."""
    contents = read_midi(midi_file)
    return Counter(ComparedNote(ticks(note.start), ticks(note.end), note.pitch, note.velocity) for part in contents.parts for note in part.notes)


def tempo_changes(midi_file):
    """Return a mido file's tempo changes as (tick, microseconds a quarter note), each differing from the one before."""
    return Counter((ticks(change.time), change.value) for change in read_midi(midi_file).tempos)


def compared(*, first, second):
    """Return what differs between two mido files' notes and tempos."""
    first_notes = heard_notes(first)
    second_notes = heard_notes(second)
    first_tempos = tempo_changes(first)
    second_tempos = tempo_changes(second)
    return Comparison(
        missing=sorted((first_notes - second_notes).elements()), extra=sorted((second_notes - first_notes).elements()),
        tempos_missing=sorted((first_tempos - second_tempos).elements()), tempos_extra=sorted((second_tempos - first_tempos).elements()),
        notes=sum(first_notes.values()),
    )


@dataclass(slots=True, kw_only=True)
class RoundTrip:
    """A MIDI file imported into a new set, played and exported again: what the import made and said, and how the export compares with the file."""

    imported: object
    comparison: Comparison


def round_trip(*, midi_file, choices):
    """Import a mido file into a new set with the choices given, export the song it makes as one MIDI file in memory, and compare the two, writing no file."""
    setlist = Setlist.new()
    imported = MidiImport(midi_file=midi_file).imported(setlist=setlist, choices=choices)
    song = add_imported(setlist=setlist, imported=imported.song)
    again = MidiSong(directory=os.curdir, grid=SongRenderer(song).render(), name=imported.song.name).midi_file()
    comparison = compared(first=midi_file, second=again)
    comparison.controls = controls_compared(first=midi_file, second=again, control_tracks=imported.control_tracks)
    return RoundTrip(imported=imported, comparison=comparison)


def controls_compared(*, first, second, control_tracks):
    """Return how each CC the import brought in compares: each part's CC numbers in the file against those of the track that sends them in the export."""
    first_parts = read_midi(first).parts
    second_parts = {part.name: part for part in read_midi(second).parts}
    differences = []
    for place, track, numbers in control_tracks:
        exported = second_parts[track].controls if track in second_parts else []
        for number in numbers:
            largest, longest = control_difference(first=values_over_time(controls=first_parts[place].controls, number=number), second=values_over_time(controls=exported, number=number))
            differences.append(ControlDifference(track, number, largest, longest))
    return differences
