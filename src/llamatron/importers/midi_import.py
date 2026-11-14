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
"""The MIDI import: a MIDI file made into a song of the open set, with the patterns and scales it needs, the user's design of 2026-11-10.

MidiImport reads the file once, says what it holds (found), and makes the song for a set and a
set of choices as often as the choices change (imported), without changing the set, so that the
import dialog can say what an import would make before it is made. add_imported (writing.py)
then adds it. Every note the file plays is played by the song, for as long as the file plays it
(cutting.py), and what had to change, like a note moved to a step, is said in the warnings.
"""

from dataclasses import dataclass, field
from typing import NamedTuple

import mido

from llamatron.importers.cutting import AUTO_STEP_SIZES, Cutter, bar_lines, grid_for, snapped, step_size_for
from llamatron.importers.keys import key_of_notes, key_of_signature
from llamatron.importers.midi_reading import Change, read_midi
from llamatron.importers.voices import voices_of
from llamatron.importers.writing import SongWriter, tempo_of, time_signature_text
from llamatron.strings.errors import ERR_MIDI_NO_NOTES
from llamatron.strings.importing import (
    MSG_WARN_CONTROLS_LEFT_OUT, MSG_WARN_CONTROLS_MOVED, MSG_WARN_CONTROLS_NO_NOTES, MSG_WARN_CONTROLS_OFF, MSG_WARN_LEFT_OUT,
    MSG_WARN_LENGTHS_CHANGED, MSG_WARN_NUMBERS_JOIN, MSG_WARN_SWUNG, MSG_WARN_MOVED, MSG_WARN_TEMPOS_MOVED, MSG_WARN_TOO_LOW, MSG_WARN_UNENDED,
)
from llamatron.support.rational import Rational

# The share of all the notes moved to a step from which the import says they were played to a timing feel, a swing,
# a groove or a live performance, rather than a few strays.
SWING_SHARE = 0.1
# The longest pattern the import may make, in steps, as the import dialog offers it, and the one it starts on.
LONGEST_PATTERN_CHOICES = (8, 16, 32, 64, 128)
DEFAULT_LONGEST_PATTERN = 32


class Found(NamedTuple):
    """What a MIDI file holds, as the import dialog says it: its tracks, its bars, its first time signature and tempo, and its keys in order."""

    tracks: int
    bars: int
    time_signature: object
    tempo: object
    keys: list


class MidiImportProblem(ValueError):
    """A MIDI file that can't be made into a song, like one that plays no notes."""


@dataclass(slots=True, kw_only=True)
class ImportChoices:
    """What the import dialog asks: the song's name, the longest pattern, whether every pattern gets a name of its own, chords as chords, whether CCs come in, and the step size, or None to work it out."""

    song_name: str
    longest_pattern: int = DEFAULT_LONGEST_PATTERN
    unique_names: bool = True
    chords: bool = True
    controls: bool = True
    step_size: object = None


@dataclass(slots=True, kw_only=True)
class Imported:
    """A song made from a MIDI file, ready to add to the set, and what it holds and what changed, for the dialog to say."""

    song: object
    step_size: object
    tracks: int
    patterns: int
    scenes: int
    long_patterns: int
    warnings: list = field(default_factory=list)
    # Each part whose CC messages came in, by its place among the file's parts, with the track that sends them and the CC numbers.
    control_tracks: list = field(default_factory=list)


class MidiImport:
    """One MIDI file read for importing."""

    __slots__ = ('_contents',)

    def __init__(self, *, midi_file):
        self._contents = read_midi(midi_file)
        if not self._contents.note_count():
            raise MidiImportProblem(ERR_MIDI_NO_NOTES)

    @classmethod
    def from_path(cls, path):
        # A file written carelessly may hold a data byte past 127, which mido refuses unless told to clip it; such files
        # play everywhere, so they are read, the byte held to 127.
        return cls(midi_file=mido.MidiFile(path, clip=True))

    def contents(self):
        return self._contents

    def keys(self):
        """Return the song's keys in time order, each a Change to a Key: the file's key signatures, or the key its notes are in when it has none."""
        keys = []
        for change in self._contents.keys:
            key = key_of_signature(change.value)
            if keys and keys[-1].time == change.time:
                keys[-1] = Change(change.time, key)
            elif not keys or keys[-1].value != key:
                keys.append(Change(change.time, key))
        if not keys or keys[0].time != 0:
            first = keys[0].value if keys else key_of_notes([note for part in self._contents.parts for note in part.notes])
            keys.insert(0, Change(Rational(0), first))
        return keys

    def found(self):
        """Return what the file holds: its MIDI tracks that play notes, its bars, its first time signature and tempo, and its keys."""
        contents = self._contents
        bars = bar_lines(time_signatures=contents.time_signatures, end=contents.end())
        return Found(
            tracks=len({part.name for part in contents.parts}), bars=len(bars) - 1,
            time_signature=time_signature_text(contents.time_signatures[0].value), tempo=tempo_of(contents.tempos[0].value),
            keys=[change.value for change in self.keys()],
        )

    def imported(self, *, setlist, choices):
        """Return the song this file makes for a set, with the choices given, leaving the set as it is."""
        contents = self._contents
        warnings = []
        found_size, fits = step_size_for(contents.parts)
        step_size = choices.step_size or found_size
        clip_step_sizes = [step_size] if choices.step_size else AUTO_STEP_SIZES
        parts, moved = snapped(parts=contents.parts, step_size=step_size)
        voices = []
        firsts = []
        for part in parts:
            firsts.append(len(voices))
            voices += voices_of(part=part, chords=choices.chords, controls=choices.controls)
        bars = bar_lines(
            time_signatures=contents.time_signatures, end=max(note.end for part in parts for note in part.notes),
            holding=max((control.time for voice in voices for control in voice.controls), default=None),
        )
        grid = step_size if choices.step_size else grid_for(voices=voices, step_size=step_size)
        cutter = Cutter(voices=voices, step_size=grid, clip_step_sizes=clip_step_sizes, bars=bars, keys=self.keys(), tempos=contents.tempos, longest=choices.longest_pattern)
        cut = cutter.best_cut()
        writer = SongWriter(setlist=setlist, voices=voices, cut=cut, bars=bars, step_size=step_size, share=not choices.unique_names)
        song = writer.written(name=choices.song_name, time_signature=time_signature_text(contents.time_signatures[0].value))
        track_names = writer.track_names()
        control_tracks = [(place, track_names[first], voices[first].lanes) for place, first in enumerate(firsts) if voices[first].lanes]
        left_out = [control for part, first in zip(parts, firsts) for control in part.controls if control.number not in voices[first].lanes]
        numbers = MSG_WARN_NUMBERS_JOIN.join(str(number) for number in sorted({control.number for control in left_out}))
        tempos_moved = sum(1 for change in contents.tempos if scene_tempo_at(cut=cut, time=change.time, step_size=grid) != change.value)
        swung = moved >= SWING_SHARE * contents.note_count()
        for count, message in (
            (moved, MSG_WARN_SWUNG if swung else MSG_WARN_MOVED), (cut.lengths_changed, MSG_WARN_LENGTHS_CHANGED), (cut.too_low, MSG_WARN_TOO_LOW),
            (cut.controls_moved, MSG_WARN_CONTROLS_MOVED), (tempos_moved, MSG_WARN_TEMPOS_MOVED), (contents.unended, MSG_WARN_UNENDED),
            (len(left_out), MSG_WARN_CONTROLS_LEFT_OUT if choices.controls else MSG_WARN_CONTROLS_OFF),
            (contents.controls_without_notes, MSG_WARN_CONTROLS_NO_NOTES), (contents.left_out, MSG_WARN_LEFT_OUT),
        ):
            if count:
                warnings.append(message.format(count=count, numbers=numbers))
        return Imported(
            song=song, step_size=step_size, tracks=len(voices), patterns=len(song.patterns), scenes=len(cut.scenes),
            long_patterns=cut.long_patterns, warnings=warnings, control_tracks=control_tracks,
        )


def scene_tempo_at(*, cut, time, step_size):
    """Return the tempo of the scene that plays at a time, in microseconds a quarter note, which differs from a tempo change at that time when the change couldn't start a scene."""
    tempo = cut.scenes[0].tempo
    for scene in cut.scenes:
        if scene.start * step_size > time:
            break
        tempo = scene.tempo
    return tempo
