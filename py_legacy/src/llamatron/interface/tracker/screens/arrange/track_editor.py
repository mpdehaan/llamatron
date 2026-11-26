# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Track editor page: one track's settings, which apply to every clip on it."""

from rich.text import Text

from llamatron.interface.pages.track import TrackPresenter
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import help as help_text, labels, messages


class TrackEditor(ShowsNamedItem, FieldPage):
    """One track's settings, which apply to every clip on it: the Track presenter's form (interface/pages/track.py), with the
    note under the settings drawn in the tracker's dim."""

    KEYS = keybindings.TrackEditor

    HELP = help_text.HELP_TRACK_EDITOR
    SECTION = Section.TRACKS
    CRUMBS_BEFORE = (labels.Crumb.ARRANGE,)
    ITEM_CRUMB = labels.MSG_TRACK_CRUMB
    RENAME_PROMPT = messages.MSG_RENAME_TRACK_PROMPT

    def presenter(self):
        """Return what the page shows and does, for its track as it is now."""
        return TrackPresenter(page=self, document=self.document(), name=self.item)

    def track(self):
        return self.presenter().track()

    def fields(self):
        return self.presenter().form()

    def remarks(self, width):
        return [Text(messages.MSG_TRANSPOSE_NOTE, style=Style.DIM)]
