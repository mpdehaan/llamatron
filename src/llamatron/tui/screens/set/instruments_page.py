# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Instruments page: every MIDI device and channel that a track can play through in real time."""

from llamatron.model.vocabulary.file_format import Section
from llamatron.tui import keybindings
from llamatron.tui.drawing import Align
from llamatron.tui.screens.shared.named_list_page import NamedListPage
from llamatron.user_strings import help as help_text, labels, legends, marks, messages, names


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
        setlist = self.document().get_setlist()
        return [
            (name, [name, setlist.get_instrument(name).get_device() or marks.MSG_NO_DEVICE_SHOWN, setlist.get_instrument(name).get_channel(), len(self.uses(name))])
            for name in self.names()
        ]

    def open_item(self):
        self.open_editor(section=Section.INSTRUMENTS, name=self.current())

    def add(self):
        """Add an instrument with no device yet, numbered like new tracks and scenes, and open it."""
        name = self.new_name(names.MSG_NEW_INSTRUMENT_WORD)
        self.document().add_instrument(name)
        self.put_cursor_on(name)
        self.open_editor(section=Section.INSTRUMENTS, name=name)
