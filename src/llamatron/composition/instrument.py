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

"""An instrument: a MIDI device and channel that real-time playback sends a track to.

Instruments are a named section of the set, like patterns, and each track chooses one or none,
the user's design of 2026-11-09 (dev_notes/IDEAS.md, "Previewing with real-time MIDI"). A track with no
instrument is left out of real-time playback and gets no play keys. The device is the name of a
MIDI output port of the computer, as the port lists itself, or blank until one is chosen, and the
channel is numbered 1 to 16 as people and devices number them, so the byte sent is one less. Two
instruments may share a device and a channel. Its General MIDI sound, if it has one, is what the
General MIDI export gives its tracks; no other export reads an instrument. A device of
FLUIDSYNTH_DEVICE plays through FluidSynth, which the tracker starts (realtime/fluidsynth.py): the
channel is then ignored, each track getting one as the General MIDI export gives them, and the
sound is sent as a program change, which no MIDI port's instrument is sent.
"""

from llamatron.composition.checks import check_keys, reading
from llamatron.composition.defaults import DEFAULT_CHANNEL
from llamatron.composition.file_format import FLUIDSYNTH_DEVICE, InstrumentSetting
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.llama_data import LlamaData, or_default, settings_by_name, written_settings
from llamatron.composition.setting import Text, WholeNumber, check_settings, described
from llamatron.music.midi import MAX_CHANNEL, MIN_CHANNEL
from llamatron.strings.errors import ERR_BAD_CHANNEL, ERR_BAD_GM_SOUND, ERR_DEVICE_NOT_TEXT, ERR_INSTRUMENT_EXPECTED_SETTINGS
from llamatron.composition.limits import MAX_GM_SOUND, MIN_GM_SOUND
from llamatron.support.revised import notes_change

# An instrument's settings, each described once, in the order they're written to a file.
SETTINGS = described(
    Text(name=InstrumentSetting.DEVICE, error=ERR_DEVICE_NOT_TEXT),
    WholeNumber(name=InstrumentSetting.CHANNEL, lowest=MIN_CHANNEL, highest=MAX_CHANNEL, error=ERR_BAD_CHANNEL),
    WholeNumber(name=InstrumentSetting.GM_SOUND, lowest=MIN_GM_SOUND, highest=MAX_GM_SOUND, error=ERR_BAD_GM_SOUND),
)


class Instrument(LlamaData):
    """A MIDI device, by its port's name, and a channel from 1 to 16."""

    __slots__ = ('_settings',)

    def __init__(self, *, device=None, channel=None, gm_sound=None):
        self.note_change()
        self._settings = settings_by_name(names=SETTINGS, given={InstrumentSetting.DEVICE: device, InstrumentSetting.CHANNEL: channel, InstrumentSetting.GM_SOUND: gm_sound})
        check_settings(settings=SETTINGS, data=written_settings(self._settings))

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(ERR_INSTRUMENT_EXPECTED_SETTINGS.format(data=data))
            check_keys(data=data, allowed=set(SETTINGS))
            return cls(device=data.get(InstrumentSetting.DEVICE), channel=data.get(InstrumentSetting.CHANNEL), gm_sound=data.get(InstrumentSetting.GM_SOUND))

    def to_data(self):
        return written_settings(self._settings)

    def copy(self):
        return Instrument(device=self.get_device(), channel=self.get_written_channel(), gm_sound=self.get_gm_sound())

    def get_device(self):
        """Return the name of its MIDI output port, or None until one is chosen."""
        return self._settings[InstrumentSetting.DEVICE]

    def get_channel(self):
        """Return its channel as people number them, 1 to 16."""
        return or_default(value=self._settings[InstrumentSetting.CHANNEL], default=DEFAULT_CHANNEL)

    def get_written_channel(self):
        """Return its channel as the file holds it, or None for the default."""
        return self._settings[InstrumentSetting.CHANNEL]

    def has_device(self):
        return self.get_device() is not None

    def uses_fluidsynth(self):
        """Return whether it plays through FluidSynth, which the tracker starts, rather than through a MIDI port: its channel is then chosen for each track and its General MIDI sound sent."""
        return self.get_device() == FLUIDSYNTH_DEVICE

    @notes_change
    def set_device(self, device):
        """Name its MIDI output port, or None to choose none."""
        if device is not None:
            SETTINGS[InstrumentSetting.DEVICE].check(device)
        self._settings[InstrumentSetting.DEVICE] = device

    def get_gm_sound(self):
        """Return the General MIDI sound a General MIDI export gives its tracks, 1 to 128, or None for none."""
        return self._settings[InstrumentSetting.GM_SOUND]

    @notes_change
    def set_gm_sound(self, sound):
        """Choose its General MIDI sound, 1 to 128, or None for none."""
        if sound is not None:
            SETTINGS[InstrumentSetting.GM_SOUND].check(sound)
        self._settings[InstrumentSetting.GM_SOUND] = sound

    @notes_change
    def set_channel(self, channel):
        SETTINGS[InstrumentSetting.CHANNEL].check(channel)
        self._settings[InstrumentSetting.CHANNEL] = channel
