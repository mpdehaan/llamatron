# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A generator's view's fields made for a page that shows them and asks for every dialog they need: the fields are handed this
as their page, and it passes each question on to the real one."""

from llamatron.interface.pages.view_fields import ViewFields


class PageViewFields(ViewFields):
    """ViewFields on a page: page is the page that shows the fields, which answers what they ask, a dialog, a section's heading,
    a refusal or another page shown."""

    __slots__ = ('_page',)

    def __init__(self, page):
        self._page = page

    def document(self):
        return self._page.document()

    def heading(self, **given):
        return self._page.heading(**given)

    def ask(self, **given):
        return self._page.ask(**given)

    def ask_choice(self, **given):
        return self._page.ask_choice(**given)

    def ask_grouped(self, **given):
        return self._page.ask_grouped(**given)

    def ask_many(self, **given):
        return self._page.ask_many(**given)

    def ask_number(self, **given):
        return self._page.ask_number(**given)

    def ask_text(self, **given):
        return self._page.ask_text(**given)

    def ask_long_name(self, **given):
        return self._page.ask_long_name(**given)

    def pick(self, **given):
        return self._page.pick(**given)

    def refuse(self, text):
        return self._page.refuse(text)

    def show_page(self, page):
        return self._page.show_page(page)
