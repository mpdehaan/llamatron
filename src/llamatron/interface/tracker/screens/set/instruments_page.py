# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Instruments page: every MIDI device and channel that a track can play through in real time."""

from llamatron.interface.pages.instrument_list import InstrumentListPresenter
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.shared.named_list_page import NamedListPage
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels, legends, messages


class InstrumentsPage(NamedListPage):
    """The set's instruments, each with its device, its channel and how many tracks play through it, from the Instrument list
    presenter (interface/pages/instrument_list.py)."""

    KEYS = keybindings.InstrumentsPage
    LISTED_SECTION = Section.INSTRUMENTS
    RENAME_PROMPT = messages.MSG_RENAME_INSTRUMENT_PROMPT
    WHAT = legends.MSG_INSTRUMENT_WHAT
    crumbs = (labels.Crumb.INSTRUMENTS,)
    HELP = help_text.HELP_INSTRUMENTS_PAGE
    columns = InstrumentListPresenter.COLUMNS

    def presenter(self):
        return InstrumentListPresenter(page=self, document=self.document())

    def rows(self):
        return self.presenter().rows()

    def open_item(self):
        self.open_place(InstrumentListPresenter.place_of(self.current()))

    def add(self):
        self.presenter().add()
