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

"""A chain: a list of named generators that a clip's notes go through, in order."""

from llamatron.composition.generator_settings import GENERATOR_SETTINGS
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.song_file_error import SongFileError


class Chain(LlamaData):
    """Steps like arp: bells or auto_ratchet: rolls, each naming a generator the song defines.

    A step only names its generator. The generator's settings are kept with the song, under its
    name, so that several chains can share one.
    """

    def __init__(self, steps):
        self._steps = [(kind, name) for kind, name in steps]

    @classmethod
    def from_data(cls, data, where, song=None):
        if not isinstance(data, list):
            raise SongFileError(f'{where}: expected a list of generators')
        steps = []
        for step in data:
            if not isinstance(step, dict) or len(step) != 1:
                raise SongFileError(f'{where}: each step must be one generator, got {step!r}')
            kind, name = next(iter(step.items()))
            if kind not in GENERATOR_SETTINGS:
                raise SongFileError(f'{where}: unknown generator {kind!r}, expected one of {sorted(GENERATOR_SETTINGS)}')
            if not isinstance(name, str) or not song.has_generator(kind, name):
                raise SongFileError(f'{where}: no {kind} called {name!r}')
            steps.append((kind, name))
        return cls(steps)

    def to_data(self):
        return [{kind: name} for kind, name in self._steps]

    def get_steps(self):
        """Return each step as (kind of generator, its name), in the order they run."""
        return list(self._steps)
