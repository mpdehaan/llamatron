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

"""The warning when a set opens whose tracks play through instruments that cannot sound on this computer.

The user's design of 2026-11-11: an instrument whose Device is FluidSynth, when FluidSynth isn't installed,
and an instrument whose MIDI port this computer doesn't list, like a set saved on another computer with
"IAC Driver Bus 1", are each told once, in one dialog, as the set opens. Only instruments some track of
some song plays through count, and nothing about the set changes: the set keeps every device, so that it
plays again where the device is, and the Instruments page can choose another.
"""

from llamatron.realtime.fluidsynth import is_installed
from llamatron.realtime.outputs import output_port_names
from llamatron.strings.errors import ERR_DEVICE_WILL_NOT_SOUND, ERR_FLUIDSYNTH_WILL_NOT_SOUND, ERR_SILENT_INSTRUMENTS_TITLE


def fluidsynth_installed():
    """Return whether FluidSynth is installed, which the tests answer for themselves."""
    return is_installed()


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
        lines.append(ERR_FLUIDSYNTH_WILL_NOT_SOUND)
    for name in instruments_played(setlist):
        instrument = setlist.get_instrument(name)
        if instrument.has_device() and not instrument.uses_fluidsynth() and instrument.get_device() not in connected:
            lines.append(ERR_DEVICE_WILL_NOT_SOUND.format(instrument=name, device=instrument.get_device()))
    return lines


def warn_of_silent_instruments(*, page, document):
    """Tell in a dialog over the page which of the set's instruments will not sound here, if any."""
    lines = silent_instrument_lines(setlist=document.setlist(), installed=fluidsynth_installed(), connected=set(output_port_names()))
    if lines:
        page.tell(ERR_SILENT_INSTRUMENTS_TITLE, *lines)
