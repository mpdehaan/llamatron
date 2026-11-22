# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tab of a built-in generator on a clip's or a track's page: the inside of the generator's own page, its view's fields, for the
built-in the clip or the track holds, the page that shows the tab asking for every dialog. ENTER on a part, such as a Chords
generator's progression, opens that part's page on the built-in."""

from llamatron.interface.tracker.screens.shared.view_fields import ViewFields
from llamatron.model.schema import generator_plugins
from llamatron.user_strings import labels


class BuiltInTab(ViewFields):
    """What makes a built-in generator's tab: page is the clip's or the track's page that shows it, and place the BuiltInPlace of
    the generator. SECTION, item and holder are what the fields and the parts' pages ask of a generator's page: the section of the
    generator's kind, what the kind is called, and the page's holder."""

    __slots__ = ('_page', '_place', '_plugin', 'SECTION', 'item', 'holder')

    def __init__(self, *, page, place):
        self._page = page
        self._place = place
        self._plugin = generator_plugins.plugins()[place.kind]
        self.SECTION = self._plugin.section
        self.item = self._plugin.strings.MSG_LABEL
        self.holder = page.holder

    def tab(self):
        """Return the generator's tab: Enabled and its Mode across the top, then its columns, marked on or off."""
        return self.view_tab(label=self._plugin.strings.MSG_TAB_LABEL)

    def view(self):
        return self._plugin.view

    def settings(self):
        """Return the built-in generator's settings, which keep every change in the clip or the track holding them."""
        return self._page.document().built_in(self._place)

    def store(self, *, setting, value):
        """Keep one setting by its file name, checked as reading a file checks it, or None to leave it out of the file."""
        document = self._page.document()
        document.change_set(self.settings().set_setting, name=setting, value=value)

    def open_part(self, page_class, **given):
        """Open the page of a part of the built-in generator, such as its offsets, its crumbs following the clip's or the track's."""
        page = page_class(holder=self.holder, name=self.item, built_in=self._place, **given)
        self._page.show_page(page.opened_from(page=self._page, word=labels.MSG_BUILT_IN_WORD))

    def document(self):
        return self._page.document()

    def heading(self, **given):
        return self._page.heading(**given)

    def ask(self, **given):
        return self._page.ask(**given)

    def ask_number(self, **given):
        return self._page.ask_number(**given)

    def ask_text(self, **given):
        return self._page.ask_text(**given)

    def refuse(self, text):
        return self._page.refuse(text)

    def show_page(self, page):
        return self._page.show_page(page)
