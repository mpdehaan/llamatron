# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Instruments page as a presenter: every instrument a track can play through in real time, its MIDI device and channel,
its built-in engine, or that it is off, each with how many tracks play through it."""

from llamatron.interface.forms.table import Align, ListColumn
from llamatron.interface.pages.places import ItemPlace
from llamatron.model.schema.file_format import InstrumentKind, Section, SoundSetting
from llamatron.user_strings import labels, marks, names


class InstrumentListPresenter:
    """What the Instruments page lists and does. Its page does what only the tracker can: put_cursor_on(name) and open_place(place)."""

    COLUMNS = (
        ListColumn(heading=labels.Column.SELECT_INSTRUMENT, width=None, align=Align.LEFT), ListColumn(heading=labels.Column.DEVICE, width=36, align=Align.LEFT),
        ListColumn(heading=labels.Column.CHANNEL, width=3, align=Align.RIGHT), ListColumn(heading=labels.Column.USED, width=4, align=Align.RIGHT),
    )

    __slots__ = ('_page', '_document')

    def __init__(self, *, page, document):
        self._page = page
        self._document = document

    def rows(self):
        """Return each instrument's name and its row: its name, its device, its channel and how many tracks play through it."""
        setlist = self._document.get_setlist()
        rows = []
        for name in self._document.names_of(Section.INSTRUMENTS):
            instrument = setlist.get_instrument(name)
            uses = self._document.uses(section=Section.INSTRUMENTS, name=name)
            rows.append((name, [name, plays_through(instrument), channel_shown(instrument), len(uses)]))
        return rows

    @staticmethod
    def place_of(name):
        """Return the place of an instrument's own page."""
        return ItemPlace(section=Section.INSTRUMENTS, name=name)

    def add(self):
        """Add an instrument with no device yet, numbered like new tracks and scenes, and open it."""
        name = self._document.new_name(section=Section.INSTRUMENTS, word=names.MSG_NEW_INSTRUMENT_WORD)
        self._document.add_instrument(name)
        self._page.put_cursor_on(name)
        self._page.open_place(self.place_of(name))


def plays_through(instrument):
    """Return what an instrument plays through as its row shows it: its built-in engine, its device, or that it is off."""
    kind = instrument.get_kind()
    if kind == InstrumentKind.BUILT_IN:
        return labels.MSG_BUILT_IN_SHOWN.format(engine=labels.MSG_ENGINE_NAMES[instrument.get_sound(SoundSetting.ENGINE)])
    if kind == InstrumentKind.OFF:
        return marks.MSG_INSTRUMENT_OFF_SHOWN
    return instrument.get_device() or marks.MSG_NO_DEVICE_SHOWN


def channel_shown(instrument):
    """Return an instrument's channel as its row shows it: none for one that isn't MIDI."""
    if instrument.get_kind() != InstrumentKind.MIDI:
        return marks.MSG_NO_CHANNEL_SHOWN
    return instrument.get_channel()
