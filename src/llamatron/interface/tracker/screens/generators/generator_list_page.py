# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Chains list page: the chains a clip, a scene or a track runs, in the order they run, which the page that opened it reads and stores."""

from llamatron.interface.pages.generator_names import generators_to_add, listed_generator
from llamatron.interface.tracker import keybindings, themes
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.drawing import Align
from llamatron.interface.tracker.screens.shared.list_page import ListPage
from llamatron.interface.tracker.screens.shared.shared import list_keys, move_key
from llamatron.user_strings import errors, help as help_text, labels, messages


class GeneratorListPage(ListPage):

    """A list of the generators of one kind, with the keys every list of named things has."""

    THEME = themes.GENERATORS
    """A list of generators by name, a chain among them, in the order they run: A adds one, M moves it, Bksp takes it out of the list.

    It edits whatever list the page that opened it hands over: names() returns the list as it is
    now, and store(names) keeps a new one, so the clip page, the Scene page and the track editor
    share it. A generator may be listed more than once, and then runs more than once.
    """

    KEYS = keybindings.GeneratorListPage
    HELP = help_text.HELP_GENERATOR_LIST_PAGE
    columns = ((labels.Column.SELECT_ANY_GENERATOR, None, Align.LEFT),)

    def __init__(self, *, holder, opener, names, store):
        super().__init__(holder)
        self.opener = opener
        self.names = names
        self.store = store

    def crumb_trail(self):
        return (*self.opener.crumb_trail(), labels.Crumb.GENERATORS)

    def rows(self):
        setlist = self.document().get_setlist()
        return [(place, [listed_generator(setlist=setlist, name=name)]) for place, name in enumerate(self.names())]

    def keys(self):
        return list_keys(page=self, extra=[self.bind(self.KEYS.REMOVE, action=self.remove_chain), move_key(self)])

    def add(self):
        setlist = self.document().get_setlist()
        offered = [name for _, name in generators_to_add(setlist)]
        if not offered:
            self.tell(errors.ERR_NOTHING_TO_ADD_TITLE, errors.ERR_MAKE_A_GENERATOR_FIRST)
            return

        def picked(item):
            self.store([*self.names(), offered[item]])
            self.cursor.set_place(len(self.names()) - 1)
        self.ask(dialog=ChoiceDialog(title=messages.MSG_ADD_GENERATOR_TITLE, options=[listed_generator(setlist=setlist, name=name) for name in offered]), then=picked)

    def remove_chain(self):
        names = self.names()
        names.pop(self.cursor.get_place())
        self.store(names)
        self.clamp()

    def shift(self, offset):
        names = self.names()
        moved = self.cursor.get_place() + offset
        if 0 <= moved < len(names):
            names[self.cursor.get_place()], names[moved] = names[moved], names[self.cursor.get_place()]
            self.store(names)
            self.cursor.set_place(moved)
