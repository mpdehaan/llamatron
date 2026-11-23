# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The chain editor as a presenter: a chain's steps, each a generator chosen by name and shown with its kind, a generator listed
again in the chain numbered from 2 on, on screen only, since the file names the same generator each time."""

from llamatron.interface.forms.table import Align, ListColumn
from llamatron.interface.forms.text import sorted_names
from llamatron.interface.pages import generator_kinds
from llamatron.model.objects.naming import suggested_word
from llamatron.model.schema import generator_plugins
from llamatron.user_strings import labels, marks, messages

# The number a generator listed again in one chain is shown with, the second time.
FIRST_REPEAT = 2


def step_shown(*, kind, name, number=None):
    """Return a step as the chain editor shows it: the generator's kind by the name its page gives it, then its name in parentheses, numbered when number is given."""
    label = generator_kinds.kind_listed(kind).label
    if number is None:
        return marks.MSG_CHAIN_STEP_SHOWN.format(name=name, kind=label)
    return marks.MSG_CHAIN_STEP_AGAIN.format(name=name, number=number, kind=label)


def steps_shown(steps):
    """Return a chain's steps as shown, a generator listed again numbered from 2 on."""
    seen = {}
    shown = []
    for kind, name in steps:
        seen[(kind, name)] = seen.get((kind, name), 0) + 1
        count = seen[(kind, name)]
        shown.append(step_shown(kind=kind, name=name, number=count if count >= FIRST_REPEAT else None))
    return shown


class ChainPresenter:
    """What the chain editor shows and does, for one of the set's chains by name."""

    COLUMNS = (ListColumn(heading=labels.Column.SELECT_ANY_GENERATOR, width=None, align=Align.LEFT),)

    __slots__ = ('_document', '_name')

    def __init__(self, *, document, name):
        self._document = document
        self._name = name

    def chain(self):
        setlist = self._document.get_setlist()
        return setlist.get_chain(self._name)

    def steps(self):
        """Return the chain's steps, each (kind of generator, its name)."""
        return self.chain().get_steps()

    def rows(self):
        return [(place, [text]) for place, text in enumerate(steps_shown(self.steps()))]

    def offered(self):
        """Return every generator the set has, each (kind, name), and the picker's lines: a new one first, then each with its kind."""
        setlist = self._document.get_setlist()
        options = [(kind, name) for kind in generator_plugins.sections_by_name() for name in sorted_names(setlist.get_generator_names(kind))]
        return options, [messages.MSG_NEW_GENERATOR_CHOICE, *[step_shown(kind=kind, name=name) for kind, name in options]]

    @staticmethod
    def kinds_to_make():
        """Return the kinds of generator a step can be made as, in the order they are offered."""
        return list(generator_kinds.GENERATOR_KINDS.values())

    def make_generator(self, listed):
        """Make a generator of a kind, named after the kind and numbered, and return its name."""
        name = self._document.new_name(section=listed.section, word=suggested_word(listed.label))
        self._document.add_generator(section=listed.section, name=name)
        return name

    def add_step(self, *, kind, name):
        """Add a step at the end of the chain, and return its place."""
        setlist = self._document.get_setlist()
        self._document.change_set(self.chain().add_step, kind=kind, name=name, setlist=setlist)
        return len(self.steps()) - 1

    def set_step(self, *, place, kind, name):
        setlist = self._document.get_setlist()
        self._document.change_set(self.chain().set_step, place=place, kind=kind, name=name, setlist=setlist)

    def copy_step(self, place):
        self._document.change_set(self.chain().copy_step, place)

    def remove_step(self, place):
        self._document.change_set(self.chain().remove_step, place)

    def move_step(self, *, place, offset):
        """Move a step up or down the chain, and return whether it moved."""
        return self._document.move_chain_step(chain=self._name, place=place, offset=offset)
