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
    """Makes the page that shows a place."""

    __slots__ = ()

    def page_at(self, *, place, holder):
        """Return the page that shows a place, on the set a holder holds."""
        named = {'holder': holder, 'name': place.name, 'built_in': place.built_in}
        if place.section is not None:
            named['section'] = place.section
        if place.steps is not None:
            named['steps'] = place.steps
        return PART_PAGES[place.part](**named)
