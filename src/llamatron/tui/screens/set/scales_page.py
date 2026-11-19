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

"""The Scales page: the set's named scales, each opened on its own page."""

from llamatron.composition.file_format import Section
from llamatron.composition.named_scale import scale_type_name
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.strings import help as help_text, labels, legends, marks, messages, names
from llamatron.tui import drawing, keybindings
from llamatron.tui.drawing import Align
from llamatron.tui.screens.shared.named_list_page import NamedListPage


NEW_SCALE_ROOT = NoteName.C
NEW_SCALE_KIND = scale_type_name(ScaleType.MAJOR)


class ScalesPage(NamedListPage):

    KEYS = keybindings.ScalesPage
    LISTED_SECTION = Section.SCALES
    RENAME_PROMPT = messages.MSG_RENAME_SCALE_PROMPT
    WHAT = legends.MSG_SCALE_WHAT
    crumbs = (labels.Crumb.SCALES,)
    HELP = help_text.HELP_SCALES_PAGE
    columns = ((labels.Column.SELECT_SCALE, None, Align.LEFT), (labels.Column.SCALE, 24, Align.LEFT), (labels.Column.NOTES, 5, Align.RIGHT), (labels.Column.USED, 4, Align.RIGHT))

    def rows(self):
        document = self.document()
        song = self.document().song()
        return [
            (name, [
                name + (marks.MSG_SONG_SCALE_MARK if song.get_scale_name() == name else drawing.NOTHING),
                document.scale_notes_text(name), document.scale_size(name), len(self.uses(name)),
            ])
            for name in self.names()
        ]

    def open_item(self):
        self.open_editor(section=Section.SCALES, name=self.current())

    def add(self):
        """Add a C major scale, named by its number as every new thing is (since a name after its notes was
        wrong once the notes changed), and open its page to change it."""
        name = self.new_name(names.MSG_NEW_SCALE_WORD)
        self.document().add_scale(name=name, root=NEW_SCALE_ROOT, kind=NEW_SCALE_KIND)
        self.put_cursor_on(name)
        self.open_editor(section=Section.SCALES, name=name)
