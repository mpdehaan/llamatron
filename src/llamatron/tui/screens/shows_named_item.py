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
"""What a page that shows one named thing of the set shares: which thing it shows, whether the thing is still there, and renaming it.

The pattern, chain and groove editors, the arpeggiator and AutoRatchet editors, the offsets
editor, the Scale page and the track editor each show one item of a section by its name. Each
kept the name and its crumbs, asked whether an undo had taken the item away, and renamed it, in
its own words. They descend from three different pages (Page, ListPage and FieldPage), so what
they share is a mixin beside whichever of those a page is.
"""

from llamatron.strings.labels import MSG_CAPTION_WORDS, MSG_EDITING_CAPTION, MSG_ITEM_CRUMB, MSG_OPENED_ITEM_CRUMB

NOTHING = ''
from llamatron.tui.themes import theme_of


class ShowsNamedItem:
    """A page of one named thing: `self.item` is its name, and `SECTION` the section it is in.

    A page says where it is in the crumbs with CRUMBS_BEFORE and CRUMBS_AFTER, how its thing's
    name reads there with ITEM_CRUMB, and what its rename prompt is called with RENAME_PROMPT.
    """

    __slots__ = ()

    # The section of the set the page's thing is in.
    SECTION = None
    # The crumbs before and after the thing's name, and how the name reads among them, a template that takes the name.
    CRUMBS_BEFORE = ()
    CRUMBS_AFTER = ()
    ITEM_CRUMB = MSG_ITEM_CRUMB
    # The title of the prompt that renames the thing, on a page that renames one.
    RENAME_PROMPT = None
    # The page that opened this one when it isn't the thing's own list, such as Arrange's details view, whose crumbs come first, so that
    # the crumbs say where Esc goes back to, and the word for the thing among them, like chain. None when the thing's list opened it.
    opener = None
    opener_word = None

    def caption(self):
        """Return what the theme's stripe says: what kind of thing the page edits, and its name."""
        return MSG_EDITING_CAPTION.format(what=MSG_CAPTION_WORDS.get(self.SECTION, NOTHING).upper(), name=self.item)

    def theme(self):
        """Return the theme colour of the section the page's thing is in, as its list's."""
        return theme_of(self.SECTION)

    def opened_from(self, *, page, word):
        """Say that another page opened this one, whose crumbs come first in this one's, the thing named after word, and return this page."""
        self.opener = page
        self.opener_word = word
        return self

    def crumb_trail(self):
        """Return the crumbs: the opener's and then the thing's word and name, when another page opened this one, and the page's own otherwise."""
        if self.opener is None:
            return self.crumbs
        return (*self.opener.crumb_trail(), MSG_OPENED_ITEM_CRUMB.format(word=self.opener_word, name=self.item))

    def show_item(self, name):
        """Show the thing under a name. This is the one place that sets the name and the crumbs that carry it."""
        self.item = name
        self.crumbs = (*self.CRUMBS_BEFORE, self.ITEM_CRUMB.format(name=name), *self.CRUMBS_AFTER)

    def still_exists(self):
        """Return whether the thing is still in the set, which an undo or redo can take away."""
        return self.document().has_named(section=self.SECTION, name=self.item)

    def follow_renames(self, renames):
        """Keep showing the same thing after an undo or redo renamed it.

        renames is what the step renamed, by section, as old name to new name.
        """
        new = renames.get(self.SECTION, {}).get(self.item)
        if new is not None:
            self.show_item(new)

    def rename(self):
        """Rename the thing, which changes every reference to it by name, and show it under the new name."""
        name = self.item

        def renamed(new):
            self.document().rename_named(section=self.SECTION, old=name, new=new)
            self.show_item(new)
        self.ask_name(title=self.RENAME_PROMPT, value=name, taken=self.document().names_of(self.SECTION), then=renamed)
