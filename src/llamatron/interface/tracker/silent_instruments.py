# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The warning when a set opens whose tracks play through instruments that cannot sound on this computer.

An instrument whose Device is FluidSynth, when FluidSynth isn't installed,
and an instrument whose MIDI port this computer doesn't list, like a set saved on another computer with
"IAC Driver Bus 1", are each told once, in one dialog, as the set opens. Only instruments some track of
some song plays through count, and nothing about the set changes: the set keeps every device, so that it
plays again where the device is, and the Instruments page can choose another.
"""

from llamatron.user_strings import errors


def instruments_played(setlist):
    """Return the names of the instruments some track of some song of the set plays through, in the set's order."""
    played = {setlist.get_song(song).get_track(track).get_instrument_name()
              for song in setlist.get_song_names() for track in setlist.get_song(song).get_track_names()}
    return [name for name in setlist.get_instrument_names() if name in played]


def silent_instrument_lines(*, setlist, installed, connected):
    """Return the dialog's lines: FluidSynth's once when an instrument played through uses it and it isn't installed, then each instrument played through whose port isn't connected."""
    lines = []
    instruments = [setlist.get_instrument(name) for name in instruments_played(setlist)]
    if not installed and any(instrument.uses_fluidsynth() for instrument in instruments):
        lines.append(errors.ERR_FLUIDSYNTH_WILL_NOT_SOUND)
    for name in instruments_played(setlist):
        instrument = setlist.get_instrument(name)
        if instrument.has_device() and not instrument.uses_fluidsynth() and instrument.get_device() not in connected:
            lines.append(errors.ERR_DEVICE_WILL_NOT_SOUND.format(instrument=name, device=instrument.get_device()))
    return lines


def warn_of_silent_instruments(*, page, document):
    """Tell in a dialog over the page which of the set's instruments will not sound here, if any."""
    lines = silent_instrument_lines(setlist=document.get_setlist(), installed=page.app.transport.fluidsynth_installed(), connected=set(page.app.transport.output_port_names()))
    if lines:
        page.tell(errors.ERR_SILENT_INSTRUMENTS_TITLE, *lines)
