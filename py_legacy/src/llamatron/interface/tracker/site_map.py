# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The site map: which of the tracker's pages shows each place (interface/pages/places.py), so that a presenter or a field opens a
page by saying where it goes."""

from llamatron.interface.pages import places
from llamatron.interface.tracker.screens.shared.chords_editor import ChordsEditor
from llamatron.interface.tracker.screens.shared.generator_statements_page import GeneratorStatementsPage
from llamatron.interface.tracker.screens.shared.guitar_bar_editor import GuitarBarEditor
from llamatron.interface.tracker.screens.shared.offsets_editor import OffsetsEditor
from llamatron.interface.tracker.screens.shared.step_row_editor import StepRowEditor

# The page that edits each part of a generator.
PART_PAGES = {
    places.OFFSETS: OffsetsEditor, places.STEP_ROW: StepRowEditor, places.CHORDS: ChordsEditor, places.GUITAR_BAR: GuitarBarEditor,
    places.BYPASS_WHEN: GeneratorStatementsPage,
}


class SiteMap:
    """Makes the page that shows a place: editor_of(section) gives the class of the page that edits a named thing of a section."""

    __slots__ = ('_editor_of',)

    def __init__(self, *, editor_of):
        self._editor_of = editor_of

    def page_at(self, *, place, holder):
        """Return the page that shows a place, on the set a holder holds, made by the place's kind."""
        if place.KIND == places.ITEM:
            return self._item_page(place=place, holder=holder)
        return self._part_page(place=place, holder=holder)

    def _item_page(self, *, place, holder):
        """Return the page of a named thing of the set."""
        return self._editor_of(place.section)(holder=holder, name=place.name)

    def _part_page(self, *, place, holder):
        """Return the page of a part of a generator."""
        named = {'holder': holder, 'name': place.name, 'built_in': place.built_in}
        if place.section is not None:
            named['section'] = place.section
        if place.steps is not None:
            named['steps'] = place.steps
        return PART_PAGES[place.part](**named)
