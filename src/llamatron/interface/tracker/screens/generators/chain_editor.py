# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Chain editor page: a chain's steps, each an arpeggiator or AutoRatchet chosen by name."""

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.drawing import Align
from llamatron.interface.tracker.screens.generators import generator_pages
from llamatron.interface.tracker.screens.generators.chain_statements_page import ChainStatementsPage
from llamatron.interface.tracker.screens.generators.generator_pages import generator_page_of_kind, generator_type_dialog
from llamatron.interface.tracker.screens.shared.list_page import ListPage
from llamatron.interface.tracker.screens.shared.shared import list_keys, move_key
from llamatron.interface.tracker.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.interface.tracker.text import sorted_names
from llamatron.model.objects.naming import suggested_word
from llamatron.model.schema import generator_plugins
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels as labels_text, marks, messages


# The number a generator listed again in one chain is shown with, the second time.
FIRST_REPEAT = 2


def step_shown(*, kind, name, number=None):
    """Return a step as the chain editor shows it: the generator's name, numbered when number is given, then its kind by the name its page gives it."""
    label = generator_page_of_kind(kind).label
    if number is None:
        return marks.MSG_CHAIN_STEP_SHOWN.format(name=name, kind=label)
    return marks.MSG_CHAIN_STEP_AGAIN.format(name=name, number=number, kind=label)


def steps_shown(steps):
    """Return a chain's steps as shown, a generator listed again numbered from 2 on, on screen only, since the file names the same generator each time."""
    seen = {}
    shown = []
    for kind, name in steps:
        seen[(kind, name)] = seen.get((kind, name), 0) + 1
        count = seen[(kind, name)]
        shown.append(step_shown(kind=kind, name=name, number=count if count >= FIRST_REPEAT else None))
    return shown


class ChainEditor(ShowsNamedItem, ListPage):
    """A chain's steps, each an arpeggiator or AutoRatchet chosen by name."""

    KEYS = keybindings.ChainEditor

    HELP = help_text.HELP_CHAIN_EDITOR
    columns = ((labels_text.Column.SELECT_CHAIN_LINKS, None, Align.LEFT),)

    SECTION = Section.CHAINS
    CRUMBS_BEFORE = (labels_text.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_CHAIN_PROMPT

    def steps(self):
        """Return the chain's steps, each (kind of generator, its name)."""
        return self.document().song().get_setlist().get_chain(self.item).get_steps()

    def rows_depend_on(self):
        """Return the chain the rows are of, since one editor's kept rows are another chain's otherwise."""
        return (self.item,)

    def rows(self):
        return [(place, [text]) for place, text in enumerate(steps_shown(self.steps()))]

    def keys(self):
        return list_keys(page=self, extra=[
            self.bind(self.KEYS.CHANGE, action=self.change),
            self.bind(self.KEYS.COPY, action=self.copy),
            self.bind(self.KEYS.REMOVE, action=self.remove_step),
            move_key(self),
        ], always=[self.bind(self.KEYS.RENAME, action=self.rename), self.bind(self.KEYS.WHEN, action=self.open_statements)])

    def open_statements(self):
        """Open the chain's statements about the registers, which say when a pass goes by the whole chain."""
        self.show_page(ChainStatementsPage(holder=self.holder, name=self.item))

    def pick_generator(self, *, title, then):
        """Ask for a generator: a new one first, then every one the set has, each with its kind; then(kind=, name=) takes the one chosen."""
        song = self.document().song()
        options = [(kind, name) for kind in generator_plugins.sections_by_name() for name in sorted_names(song.get_setlist().get_generator_names(kind))]
        labels = [messages.MSG_NEW_GENERATOR_CHOICE, *[step_shown(kind=kind, name=name) for kind, name in options]]

        def picked(place):
            if place == 0:
                self.new_generator(then=then)
                return
            kind, name = options[place - 1]
            then(kind=kind, name=name)
        self.ask(dialog=ChoiceDialog(title=title, options=labels), then=picked)

    def new_generator(self, *, then):
        """Ask which kind of generator to make, make one of it named after its kind, hand it to then(kind=, name=), and open its editor, its crumbs after the chain's."""
        sections = list(generator_pages.GENERATOR_PAGES)
        listings = [generator_pages.GENERATOR_PAGES[section] for section in sections]

        def chosen(place):
            listing = listings[place]
            name = self.document().new_name(section=sections[place], word=suggested_word(listing.label))
            self.document().add_generator(section=sections[place], name=name)
            then(kind=listing.kind, name=name)
            self.open_editor(section=listing.section, name=name, word=listing.label)
        self.ask(dialog=generator_type_dialog(opened=self.holder.open_generator_groups), then=chosen)

    def add(self):
        def chosen(*, kind, name):
            self.document().change_set(self.document().get_setlist().get_chain(self.item).add_step, kind=kind, name=name, setlist=self.document().get_setlist())
            self.cursor.set_place(len(self.steps()) - 1)
        self.pick_generator(title=messages.MSG_ADD_TO_CHAIN_TITLE, then=chosen)

    def change(self):
        place = self.current()
        self.pick_generator(title=messages.MSG_CHANGE_STEP_TITLE, then=lambda kind, name: self.document().change_set(self.document().get_setlist().get_chain(self.item).set_step, place=place, kind=kind, name=name, setlist=self.document().get_setlist()))

    def copy(self):
        self.document().change_set(self.document().get_setlist().get_chain(self.item).copy_step, self.cursor.get_place())
        self.cursor.shift(1)

    def remove_step(self):
        self.document().change_set(self.document().get_setlist().get_chain(self.item).remove_step, self.cursor.get_place())
        self.clamp()

    def shift(self, offset):
        if self.document().move_chain_step(chain=self.item, place=self.cursor.get_place(), offset=offset):
            self.cursor.shift(offset)
