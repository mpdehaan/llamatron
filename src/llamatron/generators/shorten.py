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
"""The Shorten generator: a row of on-or-off steps that makes the notes starting on the steps that are on play short, a share of their length with a rest after, the user's design of 2026-11-11."""

from llamatron.generators.glide import StepRow
from llamatron.music.sound import LENGTH, Sound
from llamatron.support.length import Length
from llamatron.support.rational import Rational

PERCENT = 100


class Shorten(StepRow):
    """Plays a single note starting on a step that's on for its shorten amount of its length, the rest of its place a rest."""

    __slots__ = ('_shorten',)

    def __init__(self, *, steps, step, shorten, continuation=None):
        super().__init__(steps=steps, step=step, continuation=continuation)
        self._shorten = shorten

    def _changed(self, *, note, following):
        short = Length.multiplied(note[LENGTH], Length.of(Rational(self._shorten, PERCENT)))
        return [Sound.with_length(note, short), Sound.rest(Length.subtract(note[LENGTH], short))]
