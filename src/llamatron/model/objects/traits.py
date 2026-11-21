# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What several kinds of stored object do alike, each said once: running chains, being bypassed by statements, setting registers, holding a row of cells, holding sections of named things.

Each is a trait, a class with no data of its own that a holder of settings (HoldsSettings) lists
before it, and that reads and stores through get_written() and set_written(). A trait names the
setting it keeps its value under, which every class with the trait writes under the same name.
"""

from llamatron.caching.revised import notes_change
from llamatron.model.objects import sections
from llamatron.model.objects.conditions import with_register_value, with_statement
from llamatron.model.objects.llama_data import own_copy
from llamatron.model.objects.named_items import NamedItems


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
        self.set_written(name=self.CHAINS_SETTING, value=list(names) if names else None, song=song)


class BypassedWhen:
    """Something a table of statements about the registers leaves out: while any statement is true as a clip's pattern starts over, it is bypassed for that pass."""

    __slots__ = ()

    # The name its class writes the setting under.
    BYPASS_SETTING = None

    def get_bypass_when(self):
        """Return its statements about the registers, in order; none when it has none."""
        return own_copy(self.get_written(self.BYPASS_SETTING) or [])

    def set_bypass_statement(self, *, place, statement):
        """Write the statement at a place of its table, add one just past the last, or remove one with None."""
        self.set_written(name=self.BYPASS_SETTING, value=with_statement(statements=self.get_written(self.BYPASS_SETTING), place=place, statement=statement))


class SetsRegisters:
    """Something that sets registers to values as it starts and adds amounts to registers each time it plays: a scene and a clip."""

    __slots__ = ()

    # The name its class writes the setting under.
    SET_REGISTERS_SETTING = None
    # The name its class writes the setting under.
    ADD_REGISTERS_SETTING = None

    def get_register_sets(self):
        """Return what it sets registers to as it starts, a value for each register it sets."""
        return dict(self.get_written(self.SET_REGISTERS_SETTING) or {})

    def get_register_adds(self):
        """Return what it adds to registers every time it plays, an amount for each register it adds to."""
        return dict(self.get_written(self.ADD_REGISTERS_SETTING) or {})

    def set_register_set(self, *, register, value):
        """Make it set a register to a value as it starts, or None to leave the register alone."""
        self.set_written(name=self.SET_REGISTERS_SETTING, value=with_register_value(values=self.get_written(self.SET_REGISTERS_SETTING), register=register, value=value))

    def set_register_add(self, *, register, value):
        """Make it add an amount to a register every time it plays, or None or 0 to add nothing."""
        self.set_written(name=self.ADD_REGISTERS_SETTING, value=with_register_value(values=self.get_written(self.ADD_REGISTERS_SETTING), register=register, value=value or None))


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
        self._sections[section] = NamedItems(label=sections.SECTION_LABELS[section], items=items)

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
