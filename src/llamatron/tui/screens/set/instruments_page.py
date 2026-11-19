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

"""The Instruments page: every MIDI device and channel that a track can play through in real time."""

from llamatron.composition.file_format import Section
from llamatron.strings import help as help_text, labels, legends, marks, messages, names
from llamatron.tui import keybindings
from llamatron.tui.drawing import Align
from llamatron.tui.screens.set.instrument_editor import InstrumentEditor
from llamatron.tui.screens.shared.named_list_page import NamedListPage


class InstrumentsPage(NamedListPage):
    """The set's instruments, each with its device, its channel and how many tracks play through it."""

    KEYS = keybindings.InstrumentsPage
    LISTED_SECTION = Section.INSTRUMENTS
    RENAME_PROMPT = messages.MSG_RENAME_INSTRUMENT_PROMPT
    WHAT = legends.MSG_INSTRUMENT_WHAT
    crumbs = (labels.Crumb.INSTRUMENTS,)
    HELP = help_text.HELP_INSTRUMENTS_PAGE
    columns = ((labels.Column.SELECT_INSTRUMENT, None, Align.LEFT), (labels.Column.DEVICE, 36, Align.LEFT), (labels.Column.CHANNEL, 3, Align.RIGHT), (labels.Column.USED, 4, Align.RIGHT))

    def rows(self):
        setlist = self.document().setlist()
        return [
            (name, [name, setlist.get_instrument(name).get_device() or marks.MSG_NO_DEVICE_SHOWN, setlist.get_instrument(name).get_channel(), len(self.uses(name))])
            for name in self.names()
        ]

    def open_item(self):
        self.show_page(InstrumentEditor(holder=self.holder, name=self.current()))

    def add(self):
        """Add an instrument with no device yet, numbered like new tracks and scenes, and open it."""
        name = self.new_name(names.MSG_NEW_INSTRUMENT_WORD)
        self.document().add_instrument(name)
        self.put_cursor_on(name)
        self.show_page(InstrumentEditor(holder=self.holder, name=name))
