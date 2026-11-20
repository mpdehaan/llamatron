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

"""A chain: a list of named generators that a clip's notes go through, in order."""

from typing import NamedTuple

from llamatron.composition import file_format, generator_settings, sections
from llamatron.composition.checks import listed, reading
from llamatron.composition.conditions import statements_setting
from llamatron.composition.file_format import ChainSetting
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.llama_data import HoldsSettings, own_copy
from llamatron.composition.traits import BypassedWhen
from llamatron.strings import errors
from llamatron.support.revised import notes_change

# Each step of a chain names exactly one generator.
GENERATORS_PER_STEP = 1
# The check of a chain's table of statements about the registers.
BYPASS_WHEN = statements_setting(ChainSetting.BYPASS_WHEN)


class ChainStep(NamedTuple):
    """One step of a chain: the kind of generator, like arp, and the name of the one to use."""

    kind: str
    name: str


class Chain(BypassedWhen, HoldsSettings):
    """Steps like arp: bells or auto_ratchet: rolls, each naming a generator the song defines.

    A step only names its generator. The generator's settings are kept with the song, under its
    name, so that several chains can share one.
    """

    __slots__ = ('_steps',)

    SETTINGS = {ChainSetting.BYPASS_WHEN: BYPASS_WHEN}
    BYPASS_SETTING = ChainSetting.BYPASS_WHEN

    def __init__(self, steps, *, bypass_when=None):
        self.note_change()
        self._steps = [ChainStep(kind, name) for kind, name in steps]
        self._settings = {ChainSetting.BYPASS_WHEN: own_copy(bypass_when) or None}

    @classmethod
    def from_data(cls, *, data, where, setlist=None):
        """Read a chain: its list of steps, or, for a chain with statements, its steps and its statements under their names."""
        with reading(where):
            bypass_when = None
            if isinstance(data, dict) and ChainSetting.STEPS in data and set(data) <= {ChainSetting.STEPS, ChainSetting.BYPASS_WHEN}:
                bypass_when = data.get(ChainSetting.BYPASS_WHEN)
                if bypass_when is not None:
                    BYPASS_WHEN.check(bypass_when)
                data = data[ChainSetting.STEPS]
            if not isinstance(data, list):
                raise InvalidValue(errors.ERR_EXPECTED_LIST)
            steps = []
            for step in data:
                if not _names_one_generator(step):
                    raise InvalidValue(errors.ERR_ONE_GENERATOR_PER_STEP.format(step=step))
                kind, name = next(iter(step.items()))
                steps.append(_checked_step(kind=kind, name=name, setlist=setlist))
            return cls(steps, bypass_when=bypass_when)

    def to_data(self):
        steps = [{step.kind: step.name} for step in self._steps]
        if self._settings[ChainSetting.BYPASS_WHEN] is None:
            return steps
        return {ChainSetting.STEPS: steps, ChainSetting.BYPASS_WHEN: own_copy(self._settings[ChainSetting.BYPASS_WHEN])}

    def get_steps(self):
        """Return each step as a ChainStep, in the order they run."""
        return list(self._steps)

    def names_item(self, *, section, name):
        """Return whether one of its steps runs a generator of a section, like an arp of the arps. A chain names nothing else."""
        return section in sections.GENERATOR_KINDS and ChainStep(sections.GENERATOR_KINDS[section], name) in self._steps

    def named_items(self):
        """Return the generators its steps run, as a set of (section, name)."""
        return {(file_format.NAMED_GENERATORS[step.kind], step.name) for step in self._steps}

    def copy(self):
        return Chain(self._steps, bypass_when=self._settings[ChainSetting.BYPASS_WHEN])

    # Changing the chain. Each step is checked against the set's generators, as reading a file does.

    @notes_change
    def add_step(self, *, kind, name, setlist):
        """Add a generator, by kind and name, to the end."""
        self._steps.append(_checked_step(kind=kind, name=name, setlist=setlist))

    @notes_change
    def set_step(self, *, place, kind, name, setlist):
        self._check_place(place)
        self._steps[place] = _checked_step(kind=kind, name=name, setlist=setlist)

    @notes_change
    def copy_step(self, place):
        """Put a copy of a step right after it. A step only names a generator, so copying it is enough."""
        self._check_place(place)
        self._steps.insert(place + 1, self._steps[place])

    @notes_change
    def remove_step(self, place):
        self._check_place(place)
        self._steps.pop(place)

    @notes_change
    def move_step(self, *, place, offset):
        """Move a step up or down, and return whether it moved, which it can't past either end."""
        self._check_place(place)
        target = place + offset
        if not 0 <= target < len(self._steps):
            return False
        self._steps.insert(target, self._steps.pop(place))
        return True

    @notes_change
    def _rename_own_references(self, *, section, old, new):
        """Make every step that ran the renamed generator run it under its new name."""
        kind = sections.GENERATOR_KINDS[section]
        self._steps = [ChainStep(kind, new) if step == (kind, old) else step for step in self._steps]

    def _check_place(self, place):
        if not 0 <= place < len(self._steps):
            raise InvalidValue(errors.ERR_CHAIN_NO_SUCH_STEP.format(place=place, steps=len(self._steps)))


def _checked_step(*, kind, name, setlist):
    """Return a step naming a generator the set has, or raise InvalidValue."""
    if kind not in generator_settings.GENERATOR_SETTINGS:
        raise InvalidValue(errors.ERR_UNKNOWN_GENERATOR.format(kind=kind, kinds=listed(sorted(generator_settings.GENERATOR_SETTINGS))))
    if not isinstance(name, str) or not setlist.has_generator(kind=kind, name=name):
        raise InvalidValue(errors.ERR_NO_SUCH_GENERATOR.format(kind=kind, name=name))
    return ChainStep(kind, name)


def _names_one_generator(step):
    """Return whether a chain step is written like arp: bells, naming one generator by its kind."""
    return isinstance(step, dict) and len(step) == GENERATORS_PER_STEP


def check_chain_names(*, value, song):
    """Refuse a list of chains unless it is a list of the set's chains by name, a chain allowed more than once, since it then runs more than once."""
    if not isinstance(value, list) or not all(isinstance(name, str) for name in value):
        raise InvalidValue(errors.ERR_NOT_CHAIN_NAMES.format(value=value))
    for name in value:
        if not song.has_generator_named(name):
            raise InvalidValue(errors.ERR_NO_GENERATOR_CALLED.format(name=name))
