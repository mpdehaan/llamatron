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

"""The Chain editor page: a chain's steps, each an arpeggiator or AutoRatchet chosen by name."""

from llamatron.composition.file_format import NAMED_GENERATORS, Section
from llamatron.tui.text import sorted_names
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.drawing import Align
from llamatron.strings.help import HELP_CHAIN_EDITOR
from llamatron.tui.screens.list_page import ListPage
from llamatron.tui.screens.generator_pages import GENERATOR_PAGES, generator_page_of_kind
from llamatron.composition.naming import unique_name
from llamatron.tui.screens.shared import list_keys, move_key
from llamatron.strings.labels import Column, Crumb
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.strings.marks import MSG_CHAIN_STEP_AGAIN, MSG_CHAIN_STEP_SHOWN
from llamatron.strings.messages import MSG_NEW_GENERATOR_CHOICE, MSG_NEW_GENERATOR_KIND_TITLE, MSG_NEW_GENERATOR_NAMED, MSG_ADD_TO_CHAIN_TITLE, MSG_CHANGE_STEP_TITLE, MSG_RENAME_CHAIN_PROMPT
from llamatron.tui import keybindings


# The number a generator listed again in one chain is shown with, the second time.
FIRST_REPEAT = 2


def step_shown(*, kind, name, number=None):
    """Return a step as the chain editor shows it: the generator's name, numbered when number is given, then its kind by the name its page gives it."""
    label = generator_page_of_kind(kind).label
    if number is None:
        return MSG_CHAIN_STEP_SHOWN.format(name=name, kind=label)
    return MSG_CHAIN_STEP_AGAIN.format(name=name, number=number, kind=label)


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

    HELP = HELP_CHAIN_EDITOR
    columns = ((Column.SELECT_CHAIN_LINKS, None, Align.LEFT),)

    SECTION = Section.CHAINS
    CRUMBS_BEFORE = (Crumb.CHAINS,)
    RENAME_PROMPT = MSG_RENAME_CHAIN_PROMPT

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def steps(self):
        """Return the chain's steps, each (kind of generator, its name)."""
        return self.document().song().get_chain(self.item).get_steps()

    def rows(self):
        return [(place, [text]) for place, text in enumerate(steps_shown(self.steps()))]

    def keys(self):
        return list_keys(page=self, extra=[
            self.bind(self.KEYS.CHANGE, action=self.change),
            self.bind(self.KEYS.COPY, action=self.copy),
            self.bind(self.KEYS.REMOVE, action=self.remove_step),
            move_key(self),
        ], always=[self.bind(self.KEYS.RENAME, action=self.rename)])

    def pick_generator(self, *, title, then):
        """Ask for a generator: a new one first, the user's ask, then every one the set has, each with its kind; then(kind=, name=) takes the one chosen."""
        song = self.document().song()
        options = [(kind, name) for kind in NAMED_GENERATORS for name in sorted_names(song.get_generator_names(kind))]
        labels = [MSG_NEW_GENERATOR_CHOICE, *[step_shown(kind=kind, name=name) for kind, name in options]]

        def picked(place):
            if place == 0:
                self.new_generator(then=then)
                return
            kind, name = options[place - 1]
            then(kind=kind, name=name)
        self.ask(dialog=ChoiceDialog(title=title, options=labels), then=picked)

    def new_generator(self, *, then):
        """Ask which kind of generator to make, make one of it named after its kind, hand it to then(kind=, name=), and open its editor, its crumbs after the chain's."""
        sections = list(GENERATOR_PAGES)
        listings = [GENERATOR_PAGES[section] for section in sections]

        def chosen(place):
            listing = listings[place]
            name = unique_name(base=MSG_NEW_GENERATOR_NAMED.format(kind=listing.label), taken=self.document().names_of(sections[place]))
            self.document().add_generator(section=sections[place], name=name)
            then(kind=listing.kind, name=name)
            self.show_page(listing.EDITOR(holder=self.holder, name=name).opened_from(page=self, word=listing.label))
        self.ask(dialog=ChoiceDialog(title=MSG_NEW_GENERATOR_KIND_TITLE, options=[listing.label for listing in listings]), then=chosen)

    def add(self):
        def chosen(*, kind, name):
            self.document().add_chain_step(chain=self.item, kind=kind, name=name)
            self.place = len(self.steps()) - 1
        self.pick_generator(title=MSG_ADD_TO_CHAIN_TITLE, then=chosen)

    def change(self):
        place = self.current()
        self.pick_generator(title=MSG_CHANGE_STEP_TITLE, then=lambda kind, name: self.document().set_chain_step(chain=self.item, place=place, kind=kind, name=name))

    def copy(self):
        self.document().copy_chain_step(chain=self.item, place=self.place)
        self.place += 1

    def remove_step(self):
        self.document().remove_chain_step(chain=self.item, place=self.place)
        self.clamp()

    def shift(self, offset):
        if self.document().move_chain_step(chain=self.item, place=self.place, offset=offset):
            self.place += offset
