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

from llamatron.composition.defaults import FIRST_NUMBER
from llamatron.composition.file_format import Section
from llamatron.tui.drawing import Align
from llamatron.strings.help import HELP_INSTRUMENTS_PAGE
from llamatron.tui.screens.instrument_editor import InstrumentEditor
from llamatron.tui.screens.named_list_page import NamedListPage
from llamatron.strings.labels import Column, Crumb
from llamatron.strings.legends import MSG_INSTRUMENT_WHAT
from llamatron.strings.marks import MSG_NO_DEVICE_SHOWN
from llamatron.strings.messages import MSG_RENAME_INSTRUMENT_PROMPT
from llamatron.strings.names import MSG_NEW_INSTRUMENT_NAME
from llamatron.tui import keybindings


class InstrumentsPage(NamedListPage):
    """The set's instruments, each with its device, its channel and how many tracks play through it."""

    KEYS = keybindings.InstrumentsPage
    LISTED_SECTION = Section.INSTRUMENTS
    RENAME_PROMPT = MSG_RENAME_INSTRUMENT_PROMPT
    WHAT = MSG_INSTRUMENT_WHAT
    crumbs = (Crumb.INSTRUMENTS,)
    HELP = HELP_INSTRUMENTS_PAGE
    columns = ((Column.SELECT_INSTRUMENT, None, Align.LEFT), (Column.DEVICE, 36, Align.LEFT), (Column.CHANNEL, 3, Align.RIGHT), (Column.USED, 4, Align.RIGHT))

    def rows(self):
        setlist = self.document().setlist()
        return [
            (name, [name, setlist.get_instrument(name).get_device() or MSG_NO_DEVICE_SHOWN, setlist.get_instrument(name).get_channel(), len(self.uses(name))])
            for name in self.names()
        ]

    def open_item(self):
        self.show_page(InstrumentEditor(holder=self.holder, name=self.current()))

    def add(self):
        """Add an instrument with no device yet, numbered like new tracks and scenes, and open it."""
        taken = self.names()
        number = FIRST_NUMBER
        while MSG_NEW_INSTRUMENT_NAME.format(number=number) in taken:
            number += 1
        name = MSG_NEW_INSTRUMENT_NAME.format(number=number)
        self.document().add_instrument(name)
        self.put_cursor_on(name)
        self.show_page(InstrumentEditor(holder=self.holder, name=name))
