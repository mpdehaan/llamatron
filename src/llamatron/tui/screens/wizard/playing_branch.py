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

"""The wizard's Playing branch: how the whole song is played, for now its drum fills."""

from llamatron.macro_composer.wizard_choices import FILLS_TRAITS
from llamatron.strings.labels import MSG_WIZARD_FILLS_LABEL, MSG_WIZARD_PLAYING_BRANCH
from llamatron.tui.screens.wizard.song_ways_branch import SongWaysBranch


class PlayingBranch(SongWaysBranch):
    """The song's Fills; the mood gauges and the modifiers are to come. A feel is not offered: a style's feels are written into
    its drums and differ in nothing else, so the field chose nothing."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_PLAYING_BRANCH

    def traits(self):
        return [(MSG_WIZARD_FILLS_LABEL, FILLS_TRAITS)]
