#!/usr/bin/env python3
# llamatron: a Python language and framework for producing MIDI clips.
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

"""Print the notes in MIDI files as note names and lengths, to read a render or a source file by eye.

For each track it prints a line of notes in the order they start, like

    track 1  C3:1/4 r1/8 E3:1/8 G3:1/2

where C3:1/4 is the note C3, as Live numbers octaves, held for a quarter note, and r1/8 is an
eighth note of silence before the next note starts. Lengths are in whole notes, as in song
files. Notes that sound together are printed one after another, each with its own length. It
also prints the file's tempo, time signature and key when it has them.

Run it from the top folder of the project, on one or more files:

    .venv/bin/python tools/show_midi.py output/my_song/clips/001-001-lead.mid
"""

import sys
from fractions import Fraction

import mido

from llamatron.composition.file_format import LIVE_OCTAVE_OFFSET
from llamatron.note import SHARP_NAMES

HALF_STEPS_PER_OCTAVE = 12
QUARTER_NOTES_PER_WHOLE_NOTE = 4
# Lengths are shown as fractions no finer than this, so rounding in the file doesn't show.
FINEST_LENGTH = 64
NO_VELOCITY = 0
NOTE_ON = 'note_on'
NOTE_OFF = 'note_off'
SET_TEMPO = 'set_tempo'
TIME_SIGNATURE = 'time_signature'
KEY_SIGNATURE = 'key_signature'
FILE_LINE = '{path}  ({ticks} ticks per quarter note)'
TEMPO_LINE = '  tempo {bpm} BPM'
TIME_SIGNATURE_LINE = '  time signature {top}/{bottom}'
KEY_LINE = '  key {key}'
TRACK_LINE = '  track {number}  {notes}'
NOTE_TEXT = '{name}{octave}:{length}'
REST_TEXT = 'r{length}'
NOTE_SEPARATOR = ' '
# How many decimal places a tempo is shown with.
TEMPO_PLACES = 1


def note_name(number):
    """Return a MIDI note number as a name with its octave as Live numbers them, like C3 for 60."""
    octave, place = divmod(number, HALF_STEPS_PER_OCTAVE)
    return SHARP_NAMES[place], octave - LIVE_OCTAVE_OFFSET


def whole_notes(ticks, ticks_per_quarter):
    """Return a time in ticks as a fraction of a whole note."""
    return Fraction(ticks, ticks_per_quarter * QUARTER_NOTES_PER_WHOLE_NOTE).limit_denominator(FINEST_LENGTH)


def is_note_start(message):
    return message.type == NOTE_ON and message.velocity > NO_VELOCITY


def is_note_end(message):
    """Return whether a message ends a note: a note off, or a note on with no velocity, which means the same."""
    return message.type == NOTE_OFF or (message.type == NOTE_ON and message.velocity == NO_VELOCITY)


def track_notes(track):
    """Return (start, MIDI number, length) in ticks for each note in a track, in the order they start."""
    now, sounding, notes = 0, {}, []
    for message in track:
        now += message.time
        if is_note_start(message):
            sounding[message.note] = now
        elif is_note_end(message) and message.note in sounding:
            start = sounding.pop(message.note)
            notes.append((start, message.note, now - start))
    return sorted(notes)


def notes_text(notes, ticks_per_quarter):
    """Return a track's notes as text, with a rest wherever nothing sounds before the next note starts."""
    pieces, end = [], 0
    for start, number, length in notes:
        if start > end:
            pieces.append(REST_TEXT.format(length=whole_notes(start - end, ticks_per_quarter)))
        name, octave = note_name(number)
        pieces.append(NOTE_TEXT.format(name=name, octave=octave, length=whole_notes(length, ticks_per_quarter)))
        end = max(end, start + length)
    return NOTE_SEPARATOR.join(pieces)


def settings_lines(track):
    """Return a line for each tempo, time signature and key in a track."""
    lines = []
    for message in track:
        if message.type == SET_TEMPO:
            lines.append(TEMPO_LINE.format(bpm=round(mido.tempo2bpm(message.tempo), TEMPO_PLACES)))
        elif message.type == TIME_SIGNATURE:
            lines.append(TIME_SIGNATURE_LINE.format(top=message.numerator, bottom=message.denominator))
        elif message.type == KEY_SIGNATURE:
            lines.append(KEY_LINE.format(key=message.key))
    return lines


def show(path):
    midi = mido.MidiFile(path)
    print(FILE_LINE.format(path=path, ticks=midi.ticks_per_beat))
    for number, track in enumerate(midi.tracks, start=1):
        for line in settings_lines(track):
            print(line)
        notes = track_notes(track)
        if notes:
            print(TRACK_LINE.format(number=number, notes=notes_text(notes, midi.ticks_per_beat)))


def main():
    for path in sys.argv[1:]:
        show(path)


if __name__ == '__main__':
    main()
