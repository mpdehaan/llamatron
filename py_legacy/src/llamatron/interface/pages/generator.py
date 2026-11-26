# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The page of one of the set's generators, of any plugin that describes its view (model/schema/generator_views.py), as a
presenter: its Name, then each of the view's settings, made from the description alone, so that the plugin's page needs no code
outside its folder."""

from llamatron.interface.forms.nodes import NameField
from llamatron.interface.pages.page_view_fields import PageViewFields
from llamatron.model.schema import generator_plugins


class GeneratorPresenter(PageViewFields):
    """What a generator's page shows and does, for a generator of a section by name. Its page does what only the tracker can:
    rename(), open_part(part, **given) on a part of the generator, and every dialog. SECTION is the generator's section, which
    the view's fields ask for."""

    __slots__ = ('SECTION', '_name', '_view')

    def __init__(self, *, page, section, name):
        super().__init__(page)
        self.SECTION = section
        self._name = name
        self._view = generator_plugins.plugins_by_section()[section].view

    def form(self):
        """Return the page's form: the generator's name, then the view's settings, column by column."""
        return [NameField(value=self._shown_name, rename=self._page.rename), *self.view_fields()]

    def view(self):
        return self._view

    def settings(self):
        """Return the generator's settings."""
        document = self._page.document()
        return document.generator(section=self.SECTION, name=self._name)

    def store(self, *, setting, value):
        """Keep one setting by its file name, checked as reading a file checks it, or None to leave it out of the file."""
        document = self._page.document()
        document.change_set(self.settings().set_setting, name=setting, value=value)

    def open_part(self, part, **given):
        """Open the page of a part of the generator, such as its offsets, on the same generator."""
        self._page.open_part(part, **given)

    def _shown_name(self):
        return self._name
