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

"""Trying a sound: what a picker of sounds plays when asked to let a sound be heard.

A sound is tried through the pattern preview (tui/pattern_preview.py), once, through General MIDI
in FluidSynth, or on the song's Preview instrument where FluidSynth is not installed, beside
whatever the song plays: a run of notes for a sound that plays notes, and
four quarter notes for a drum of the kit or for a sound that stands in for one.
"""


# A run is played in eighth notes, and a drum's four hits in quarters.
RUN_STEP = '1/8'
HITS_STEP = '1/4'
HITS = 4
NOTES_IN_OCTAVE = 12
# A run where no song gives a scale: the major scale from the C of the fourth octave.
MAJOR_STEPS = (0, 2, 4, 5, 7, 9, 11)
USUAL_OCTAVE = 4
C = 0


def run_of(*, root=C, steps=MAJOR_STEPS, octave=USUAL_OCTAVE):
    """Return the MIDI notes of a scale played up an octave and back down, from a root, as half steps above C, in an octave."""
    low = octave * NOTES_IN_OCTAVE + root
    up = [low + step for step in steps] + [low + NOTES_IN_OCTAVE]
    return up + up[-2::-1]


def hits_of(number):
    """Return the MIDI notes of one note or drum hit four times."""
    return [number] * HITS


class SoundTrial:
    """Tries sounds for a picker. A subclass, or the asker, says what each value of the picker plays."""

    __slots__ = ('_page', '_played')

    def __init__(self, *, page, played):
        """played answers, for a value of the picker, (notes, step size, General MIDI sound or None for the drum kit), or None for a value that plays nothing."""
        self._page = page
        self._played = played

    def preview(self):
        return self._page.app.pattern_preview()

    def can_try(self, value):
        """Return whether a value is something to hear, which the Listen key is shown for whether or not anything can sound."""
        return self._played(value) is not None

    def start(self, value):
        """Play a value, and return None, or why nothing plays, for the picker to say."""
        refusal = self.preview().sound_refusal()
        if refusal is not None:
            return refusal
        numbers, step_size, sound = self._played(value)
        return self._page.app.transport.try_play(lambda: self.preview().play_sound(numbers=numbers, step_size=step_size, sound=sound, key=value)).refusal

    def playing(self):
        return self.preview().playing_sound()

    def stop(self):
        self.preview().stop()


def run_in_sound(sound):
    """What a General MIDI sound plays when tried where no song gives a scale: the usual run."""
    return None if sound is None else (run_of(), RUN_STEP, sound)
