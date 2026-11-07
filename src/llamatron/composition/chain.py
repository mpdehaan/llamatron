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

from typing import NamedTuple

from llamatron.composition.generator_settings import GENERATOR_SETTINGS
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.checks import reading
from llamatron.composition.invalid_value import InvalidValue

MSG_EXPECTED_LIST = 'expected a list of generators'
MSG_ONE_GENERATOR_PER_STEP = 'each step must be one generator, got {step!r}'
MSG_UNKNOWN_GENERATOR = 'unknown generator {kind!r}, expected one of {kinds}'
MSG_NO_SUCH_GENERATOR = 'no {kind} called {name!r}'
# Each step of a chain names exactly one generator.
GENERATORS_PER_STEP = 1


class ChainStep(NamedTuple):
    """One step of a chain: the kind of generator, like arp, and the name of the one to use."""

    kind: str
    name: str


class Chain(LlamaData):
    """Steps like arp: bells or auto_ratchet: rolls, each naming a generator the song defines.

    A step only names its generator. The generator's settings are kept with the song, under its
    name, so that several chains can share one.
    """

    __slots__ = ('_steps',)

    def __init__(self, steps):
        self._steps = [ChainStep(kind, name) for kind, name in steps]

    @classmethod
    def from_data(cls, data, where, song=None):
        with reading(where):
            if not isinstance(data, list):
                raise InvalidValue(MSG_EXPECTED_LIST)
            steps = []
            for step in data:
                if not _names_one_generator(step):
                    raise InvalidValue(MSG_ONE_GENERATOR_PER_STEP.format(step=step))
                kind, name = next(iter(step.items()))
                if kind not in GENERATOR_SETTINGS:
                    raise InvalidValue(MSG_UNKNOWN_GENERATOR.format(kind=kind, kinds=sorted(GENERATOR_SETTINGS)))
                if not isinstance(name, str) or not song.has_generator(kind, name):
                    raise InvalidValue(MSG_NO_SUCH_GENERATOR.format(kind=kind, name=name))
                steps.append(ChainStep(kind, name))
            return cls(steps)

    def to_data(self):
        return [{step.kind: step.name} for step in self._steps]

    def get_steps(self):
        """Return each step as a ChainStep, in the order they run."""
        return list(self._steps)


def _names_one_generator(step):
    """Return whether a chain step is written like arp: bells, naming one generator by its kind."""
    return isinstance(step, dict) and len(step) == GENERATORS_PER_STEP
