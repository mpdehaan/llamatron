# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What several kinds of stored object do alike, each said once: running chains, being bypassed by statements, resetting draws, holding a row of cells, holding sections of named things.

Each is a trait, a class with no data of its own that a holder of settings (HoldsSettings) lists
before it, and that reads and stores through get_written() and set_written(). A trait names the
setting it keeps its value under, which every class with the trait writes under the same name.
"""

from llamatron.caching.revised import notes_change
from llamatron.model.file.checks import listed
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects import sections
from llamatron.model.objects.conditions import with_statement
from llamatron.model.objects.llama_data import own_copy
from llamatron.model.objects.named_items import NamedItems
from llamatron.model.schema import file_format
from llamatron.model.schema.setting import Checked
from llamatron.user_strings import errors


class RunsChains:
    """Something whose clips run chains of generators, by name, in order: a clip, its scene and its track."""

    __slots__ = ()

    # The name its class writes the setting under.
    CHAINS_SETTING = None

    def get_chain_names(self):
        """Return the names of the chains it runs, in order; none when it runs none."""
        return list(self.get_written(self.CHAINS_SETTING) or [])

    def set_chain_names(self, *, names, song):
        """Set the chains it runs, by name, in order, or none for an empty list."""
        chains = None
        if names:
            chains = list(names)
        self.set_written(name=self.CHAINS_SETTING, value=chains, song=song)


class BypassedWhen:
    """Something a table of statements about the draws leaves out: while any statement is true as a clip's pattern starts over, it is bypassed for that pass."""

    __slots__ = ()

    # The name its class writes the setting under.
    BYPASS_SETTING = None

    def get_bypass_when(self):
        """Return its statements about the draws, in order; none when it has none."""
        return own_copy(self.get_written(self.BYPASS_SETTING) or [])

    def set_bypass_statement(self, *, place, statement):
        """Write the statement at a place of its table, add one just past the last, or remove one with None."""
        self.set_written(name=self.BYPASS_SETTING, value=with_statement(statements=self.get_written(self.BYPASS_SETTING), place=place, statement=statement))


class ResetsDraws:
    """Something that sends draws back to their first slot, or a serial draw to a new round, as it first starts: a scene, and a
    clip, each on its scene's first play alone."""

    __slots__ = ()

    # The name its class writes the setting under.
    RESET_DRAWS_SETTING = None

    def get_reset_draw_names(self):
        """Return the draws it resets as it first starts, in the order the draws come."""
        reset = self.get_written(self.RESET_DRAWS_SETTING) or []
        return [name for name in file_format.DRAW_NAMES if name in reset]

    def set_reset_draw(self, *, draw, on):
        """Make it reset a draw as it first starts, or stop it, keeping the draws in order."""
        if draw not in file_format.DRAW_NAMES:
            raise InvalidValue(errors.ERR_NO_SUCH_DRAW.format(name=draw, names=listed(file_format.DRAW_NAMES)))
        switched = set(self.get_reset_draw_names())
        if on:
            switched.add(draw)
        else:
            switched.discard(draw)
        in_order = [name for name in file_format.DRAW_NAMES if name in switched]
        self.set_written(name=self.RESET_DRAWS_SETTING, value=in_order or None)


def reset_draws_setting(name):
    """Return the description of the setting a ResetsDraws writes its draws under, by its name."""
    return Checked(name=name, check=_check_reset_draws)


class HasCells:
    """Something that holds a row of cells edited one at a time: a groove's amounts, an arp's offsets, a step row's steps, a Guitarify's bar of strokes.

    Each says what a cell holds and how few and how many it can have; an editor of one row asks all of them the same three things.
    """

    __slots__ = ()

    def set_cell(self, *, step, value):
        """Give the cell at a step a value."""
        raise NotImplementedError

    def insert_cell(self, step):
        """Add a cell before a step, holding what a new cell holds."""
        raise NotImplementedError

    def remove_cell(self, step):
        """Take the cell at a step out."""
        raise NotImplementedError


class HoldsSections:
    """Something that holds sections of named things, in order, and changes every section the same way: the set, and a song for its tracks and registers.

    Its class keeps the sections in `_sections`, one NamedItems a section. A class adds to a
    method here what is its own, such as a rename reaching everything that names the thing.
    """

    __slots__ = ()

    @notes_change
    def _set_section(self, *, section, items):
        """Give a section its items as read from the file, or None for a section the file leaves out."""
        self._sections[section] = NamedItems(label=sections.section_label(section), items=items)

    def _section(self, section):
        return self._sections[section]

    def has_item(self, *, section, name):
        return self._section(section).has(name)

    def get_item(self, *, section, name):
        return self._section(section).get(name)

    def get_item_names(self, section):
        """Return the names in a section, in order."""
        return self._section(section).names()

    def add_item(self, *, section, name, item, after=None):
        """Add a named item to a section, at the end, or right after another item."""
        self._section(section).add(name=name, item=item, after=after)

    def replace_item(self, *, section, name, item):
        """Put a new item under an existing name, keeping its place."""
        self._section(section).replace(name=name, item=item)

    def remove_item(self, *, section, name):
        """Take an item out of a section."""
        self._section(section).remove(name)

    def move_item(self, *, section, place, offset):
        """Move an item up or down its section, and return whether it moved, which it can't past either end."""
        return self._section(section).move(place=place, offset=offset)

    def sort_items(self, section):
        """Put a section's items in alphabetical order, ignoring case."""
        self._section(section).sort()


def _check_reset_draws(value):
    """Refuse anything but a list of some of the draws' names."""
    if not isinstance(value, list) or not set(value) <= set(file_format.DRAW_NAMES):
        raise InvalidValue(errors.ERR_BAD_RESET_DRAWS.format(names=listed(file_format.DRAW_NAMES), value=value))
