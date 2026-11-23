# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Scales page: the set's named scales, each opened on its own page."""

from llamatron.interface.pages.scale_list import ScaleListPresenter
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.shared.named_list_page import NamedListPage
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels, legends, messages


class ScalesPage(NamedListPage):
    """The Scales page: the set's scales, listed by name, from the Scale list presenter (interface/pages/scale_list.py)."""

    KEYS = keybindings.ScalesPage
    LISTED_SECTION = Section.SCALES
    RENAME_PROMPT = messages.MSG_RENAME_SCALE_PROMPT
    WHAT = legends.MSG_SCALE_WHAT
    crumbs = (labels.Crumb.SCALES,)
    HELP = help_text.HELP_SCALES_PAGE
    columns = ScaleListPresenter.COLUMNS

    def presenter(self):
        return ScaleListPresenter(page=self, document=self.document())

    def rows(self):
        return self.presenter().rows()

    def open_item(self):
        self.open_place(ScaleListPresenter.place_of(self.current()))

    def add(self):
        self.presenter().add()
