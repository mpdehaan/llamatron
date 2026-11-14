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
"""What a visualizer hears each frame: the notes that just started and those still held, on which track, and the beat, the one input every mode reads.

It is honest: only notes that have started are in it, so a mode never knows what is coming, and
it comes from the score the player plays from, so no MIDI is read back.
"""

from typing import NamedTuple

# A song plays at 120 quarter notes a minute when nothing says otherwise, which is what motion is scaled against.
REFERENCE_SECONDS_PER_BEAT = 0.5


class HeardNote(NamedTuple):
    """A note heard this frame: its track's place in the song's order, its MIDI number, its velocity, whether it started this frame, and whether its track is a drum's."""

    track: int
    pitch: int
    velocity: int
    started: bool
    drum: bool


class Heard(NamedTuple):
    """What a frame hears: its notes, the seconds a beat lasts now, how many beats the song has played, for the motion that follows the beat, and the song's track names, by the places the notes give, for a mode that names the tracks."""

    notes: tuple
    seconds_per_beat: float
    beats: float
    names: tuple = ()

    def tempo_factor(self):
        """Return how much faster than 120 quarter notes a minute the song goes, which scales a mode's motion."""
        return REFERENCE_SECONDS_PER_BEAT / self.seconds_per_beat


# What a frame hears when nothing plays: no notes, at the reference tempo, on no beat.
SILENCE = Heard(notes=(), seconds_per_beat=REFERENCE_SECONDS_PER_BEAT, beats=0.0)
