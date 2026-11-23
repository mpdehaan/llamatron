# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Chain editor page: a chain's steps, each a generator chosen by name."""

from llamatron.interface.pages.chain import ChainPresenter
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.generators.chain_statements_page import ChainStatementsPage
from llamatron.interface.tracker.screens.generators.generator_pages import generator_type_dialog
from llamatron.interface.tracker.screens.shared.list_page import ListPage
from llamatron.interface.tracker.screens.shared.shared import list_keys, move_key
from llamatron.interface.tracker.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels as labels_text, messages


# The place of the picker's first choice, a new generator, which the picker opens on.
NEW_GENERATOR_PLACE = 0


class ChainEditor(ShowsNamedItem, ListPage):
    """A chain's steps, each a generator chosen by name, from the chain presenter (interface/pages/chain.py)."""

    KEYS = keybindings.ChainEditor

    HELP = help_text.HELP_CHAIN_EDITOR
    columns = ChainPresenter.COLUMNS

    SECTION = Section.CHAINS
    CRUMBS_BEFORE = (labels_text.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_CHAIN_PROMPT

    def presenter(self):
        return ChainPresenter(document=self.document(), name=self.item)

    def steps(self):
        return self.presenter().steps()

    def rows_depend_on(self):
        """Return the chain the rows are of, since one editor's kept rows are another chain's otherwise."""
        return (self.item,)

    def rows(self):
        return self.presenter().rows()

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
        options, shown = self.presenter().offered()

        def picked(place):
            if place == NEW_GENERATOR_PLACE:
                self.new_generator(then=then)
                return
            kind, name = options[place - 1]
            then(kind=kind, name=name)
        self.ask_choice(title=title, options=shown, current=NEW_GENERATOR_PLACE, then=picked)

    def new_generator(self, *, then):
        """Ask which kind of generator to make, make one of it named after its kind, hand it to then(kind=, name=), and open its editor, its crumbs after the chain's."""
        kinds = ChainPresenter.kinds_to_make()

        def chosen(place):
            listed = kinds[place]
            name = self.presenter().make_generator(listed)
            then(kind=listed.kind, name=name)
            self.open_editor(section=listed.section, name=name, word=listed.label)
        self.ask(dialog=generator_type_dialog(), then=chosen)

    def add(self):
        def chosen(*, kind, name):
            self.cursor.set_place(self.presenter().add_step(kind=kind, name=name))
        self.pick_generator(title=messages.MSG_ADD_TO_CHAIN_TITLE, then=chosen)

    def change(self):
        place = self.current()
        self.pick_generator(title=messages.MSG_CHANGE_STEP_TITLE, then=lambda kind, name: self.presenter().set_step(place=place, kind=kind, name=name))

    def copy(self):
        self.presenter().copy_step(self.cursor.get_place())
        self.cursor.shift(1)

    def remove_step(self):
        self.presenter().remove_step(self.cursor.get_place())
        self.clamp()

    def shift(self, offset):
        if self.presenter().move_step(place=self.cursor.get_place(), offset=offset):
            self.cursor.shift(offset)
