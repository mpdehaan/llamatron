# llamatron: a Python language and framework for producing MIDI clips.
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

"""The settings of a named arp or AutoRatchet, which chains use by name.

A generator's settings are checked when a chain uses it, rather than when the file is read, so
that a problem is reported with the name of the chain that uses it, as it always has been.
"""

from llamatron.composition.checks import check_keys, is_whole_number, is_whole_number_from, number
from llamatron.composition.file_format import GeneratorKind
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.arp import MAX_OCTAVE_RANGE, Arp, ChordOrder, OctaveJump, _check_offsets
from llamatron.generators.auto_ratchet import AutoRatchet

MSG_NEEDS_SETTING = '{where}: needs {name}'
MSG_NOT_A_CHOICE = '{where}: {name} must be one of {choices}, got {value!r}'
MSG_NOT_WHOLE_NUMBER = '{where}: {name} must be a whole number, got {value!r}'
MSG_BAD_OCTAVE_RANGE = '{where}: {name} must be a whole number from {lowest} to {highest}, got {value!r}'
MSG_BAD_OFFSETS = '{where}: {problem}'
MSG_NOT_A_LIST = '{where}: {name} must be a list, got {value!r}'
MIN_OCTAVE_RANGE = 1


class ArpSetting:
    """An arpeggiator's settings, as a file names them."""

    STEP = 'step'
    ORDER = 'order'
    SEED = 'seed'
    OCTAVE_RANGE = 'octave_range'
    OCTAVE_JUMP = 'octave_jump'
    OFFSETS = 'offsets'


class AutoRatchetSetting:
    """An AutoRatchet's settings, as a file names them."""

    COUNTS = 'counts'


class ValueKind:
    """The kinds of value a generator setting can hold, besides a choice from a list of names."""

    WHOLE = 'whole number'
    LENGTH = 'length'
    WHOLES = 'list of whole numbers'
    OCTAVES = 'octave range'
    OFFSETS = 'offsets'


# The choices for settings that pick one of several names, by the name a file uses.
ORDERS = {member.name.lower(): member for member in ChordOrder}
OCTAVE_JUMPS = {member.name.lower(): member for member in OctaveJump}


class GeneratorSettings(LlamaData):
    """The settings of one named generator, kept as the file writes them until a chain uses them.

    Each subclass says which generator it makes, what settings it allows, what kind of value each
    one is, and which are required.
    """

    __slots__ = ('_settings',)

    GENERATOR = None
    SETTINGS = {}
    REQUIRED = []

    def __init__(self, settings):
        # Kept exactly as given, even if it's wrong, since it's only checked when a chain uses it.
        self._settings = settings or {}

    @classmethod
    def from_data(cls, data, where, song=None):
        return cls(data)

    def to_data(self):
        return dict(self._settings) if isinstance(self._settings, dict) else self._settings

    def make_generator(self, where, default_seed):
        """Return the generator these settings describe, or raise SongFileError if they're wrong.

        where names the chain using it. default_seed is used by a generator that chooses at
        random, when its settings don't give a seed.
        """
        check_keys(self._settings, where, set(self.SETTINGS))
        values = {
            name: _value(self._settings[name], kind, name, where)
            for name, kind in self.SETTINGS.items() if name in self._settings
        }
        for name in self.REQUIRED:
            if name not in values:
                raise SongFileError(MSG_NEEDS_SETTING.format(where=where, name=name))
        return self.GENERATOR(**self._with_default_seed(values, default_seed))

    def _with_default_seed(self, values, default_seed):
        """Return the generator's values, with a seed added if it needs one. Most don't."""
        return values


class ArpSettings(GeneratorSettings):
    """An arpeggiator's settings: its step length, order, seed, octave range and jump, and offsets."""

    __slots__ = ()

    GENERATOR = Arp
    SETTINGS = {
        ArpSetting.STEP: ValueKind.LENGTH, ArpSetting.ORDER: ORDERS, ArpSetting.SEED: ValueKind.WHOLE,
        ArpSetting.OCTAVE_RANGE: ValueKind.OCTAVES, ArpSetting.OCTAVE_JUMP: OCTAVE_JUMPS, ArpSetting.OFFSETS: ValueKind.OFFSETS,
    }
    REQUIRED = [ArpSetting.STEP]

    def _with_default_seed(self, values, default_seed):
        if ArpSetting.SEED not in values:
            values[ArpSetting.SEED] = default_seed
        return values


class AutoRatchetSettings(GeneratorSettings):
    """An AutoRatchet's settings: the counts it cycles through."""

    __slots__ = ()

    GENERATOR = AutoRatchet
    SETTINGS = {AutoRatchetSetting.COUNTS: ValueKind.WHOLES}
    REQUIRED = [AutoRatchetSetting.COUNTS]


# Each generator a chain step can name, and the class that holds its settings.
GENERATOR_SETTINGS = {GeneratorKind.ARP: ArpSettings, GeneratorKind.AUTO_RATCHET: AutoRatchetSettings}


def _value(value, kind, name, where):
    """Return one setting's value as the generator takes it, or raise SongFileError if it's wrong."""
    if isinstance(kind, dict):
        if value not in kind:
            raise SongFileError(MSG_NOT_A_CHOICE.format(where=where, name=name, choices=sorted(kind), value=value))
        return kind[value]
    if kind == ValueKind.WHOLE:
        if not is_whole_number(value):
            raise SongFileError(MSG_NOT_WHOLE_NUMBER.format(where=where, name=name, value=value))
        return value
    if kind == ValueKind.LENGTH:
        return number(value, where)
    if kind == ValueKind.OCTAVES:
        if not is_whole_number_from(value, MIN_OCTAVE_RANGE, MAX_OCTAVE_RANGE):
            raise SongFileError(MSG_BAD_OCTAVE_RANGE.format(where=where, name=name, lowest=MIN_OCTAVE_RANGE, highest=MAX_OCTAVE_RANGE, value=value))
        return value
    if kind == ValueKind.OFFSETS:
        try:
            _check_offsets(value)
        except ValueError as error:
            raise SongFileError(MSG_BAD_OFFSETS.format(where=where, problem=error)) from None
        return value
    if not isinstance(value, list):
        raise SongFileError(MSG_NOT_A_LIST.format(where=where, name=name, value=value))
    return value
