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

from llamatron.composition.checks import check_keys, number
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.song_file_error import SongFileError
from llamatron.generators.arp import MAX_OCTAVE_RANGE, Arp, ChordOrder, OctaveJump, _check_offsets
from llamatron.generators.auto_ratchet import AutoRatchet

# The kinds of value a generator setting can hold.
WHOLE, LENGTH, WHOLES, OCTAVES, OFFSETS = 'whole number', 'length', 'list of whole numbers', 'octave range', 'offsets'
ORDERS = {member.name.lower(): member for member in ChordOrder}
OCTAVE_JUMPS = {member.name.lower(): member for member in OctaveJump}


class GeneratorSettings(LlamaData):
    """The settings of one named generator, kept as the file writes them until a chain uses them.

    Each subclass says which generator it makes, what settings it allows, what kind of value each
    one is, and which are required.
    """

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
            key: _value(self._settings[key], kind, key, where)
            for key, kind in self.SETTINGS.items() if key in self._settings
        }
        for setting in self.REQUIRED:
            if setting not in values:
                raise SongFileError(f'{where}: needs {setting}')
        return self.GENERATOR(**self._with_default_seed(values, default_seed))

    def _with_default_seed(self, values, default_seed):
        return values


class ArpSettings(GeneratorSettings):
    """An arpeggiator's settings: its step length, order, seed, octave range and jump, and offsets."""

    GENERATOR = Arp
    SETTINGS = {'step': LENGTH, 'order': ORDERS, 'seed': WHOLE, 'octave_range': OCTAVES, 'octave_jump': OCTAVE_JUMPS, 'offsets': OFFSETS}
    REQUIRED = ['step']

    def _with_default_seed(self, values, default_seed):
        if 'seed' not in values:
            values['seed'] = default_seed
        return values


class AutoRatchetSettings(GeneratorSettings):
    """An AutoRatchet's settings: the counts it cycles through."""

    GENERATOR = AutoRatchet
    SETTINGS = {'counts': WHOLES}
    REQUIRED = ['counts']


# Each generator a chain step can name, and the class that holds its settings.
GENERATOR_SETTINGS = {'arp': ArpSettings, 'auto_ratchet': AutoRatchetSettings}


def _value(value, kind, key, where):
    """Return one setting's value as the generator takes it, or raise SongFileError if it's wrong."""
    if isinstance(kind, dict):
        if value not in kind:
            raise SongFileError(f'{where}: {key} must be one of {sorted(kind)}, got {value!r}')
        return kind[value]
    if kind == WHOLE:
        if type(value) is not int:
            raise SongFileError(f'{where}: {key} must be a whole number, got {value!r}')
        return value
    if kind == LENGTH:
        return number(value, where)
    if kind == OCTAVES:
        if type(value) is not int or not 1 <= value <= MAX_OCTAVE_RANGE:
            raise SongFileError(f'{where}: {key} must be a whole number from 1 to {MAX_OCTAVE_RANGE}, got {value!r}')
        return value
    if kind == OFFSETS:
        try:
            _check_offsets(value)
        except ValueError as error:
            raise SongFileError(f'{where}: {error}') from None
        return value
    if not isinstance(value, list):
        raise SongFileError(f'{where}: {key} must be a list, got {value!r}')
    return value
