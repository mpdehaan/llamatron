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

"""The Scales page: the set's named scales, each opened on its own page since 2026-11-07."""

from llamatron.composition.file_format import Section
from llamatron.composition.named_scale import scale_type_name
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.composition.naming import default_scale_name, unique_name
from llamatron.tui.drawing import Align, NOTHING
from llamatron.strings.help import HELP_SCALES_PAGE
from llamatron.tui.screens.named_list_page import NamedListPage
from llamatron.tui.screens.scale_page import ScalePage
from llamatron.strings.labels import Column, Crumb
from llamatron.strings.legends import MSG_SCALE_WHAT
from llamatron.strings.marks import MSG_SONG_SCALE_MARK
from llamatron.strings.messages import MSG_RENAME_SCALE_PROMPT
from llamatron.tui import keybindings


NEW_SCALE_ROOT = NoteName.C
NEW_SCALE_KIND = scale_type_name(ScaleType.MAJOR)


class ScalesPage(NamedListPage):

    KEYS = keybindings.ScalesPage
    LISTED_SECTION = Section.SCALES
    RENAME_PROMPT = MSG_RENAME_SCALE_PROMPT
    WHAT = MSG_SCALE_WHAT
    crumbs = (Crumb.SCALES,)
    HELP = HELP_SCALES_PAGE
    columns = ((Column.SELECT_SCALE, None, Align.LEFT), (Column.SCALE, 24, Align.LEFT), (Column.NOTES, 5, Align.RIGHT), (Column.USED, 4, Align.RIGHT))

    def rows(self):
        document = self.document()
        song = self.document().song()
        return [
            (name, [
                name + (MSG_SONG_SCALE_MARK if song.get_scale_name() == name else NOTHING),
                document.scale_notes_text(name), document.scale_size(name), len(self.uses(name)),
            ])
            for name in self.names()
        ]

    def open_item(self):
        self.show_page(ScalePage(holder=self.holder, name=self.current()))

    def add(self):
        """Add a C major scale, named after what it is, and open its page to change it."""
        name = unique_name(base=default_scale_name(root=NEW_SCALE_ROOT, kind=NEW_SCALE_KIND), taken=self.names())
        self.document().add_scale(name=name, root=NEW_SCALE_ROOT, kind=NEW_SCALE_KIND)
        self.put_cursor_on(name)
        self.show_page(ScalePage(holder=self.holder, name=name))
