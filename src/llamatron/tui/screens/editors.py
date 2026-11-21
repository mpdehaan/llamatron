# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The page that edits one named thing of each section, and the page that shows the whole of a section with no named things, so
that a page opens another by the section and never imports it.

The program holds this registry and answers a page that asks (LlamatronApp.editor_of), and a
page opens one with Page.open_editor(section=, name=).
"""

from llamatron.model.schema.file_format import Section
from llamatron.tui.screens.arrange.track_editor import TrackEditor
from llamatron.tui.screens.generators import generator_pages
from llamatron.tui.screens.generators.chain_editor import ChainEditor
from llamatron.tui.screens.pattern.pattern_editor import PatternEditor
from llamatron.tui.screens.set.draws_page import DrawsPage
from llamatron.tui.screens.set.groove_editor import GrooveEditor
from llamatron.tui.screens.set.instrument_editor import InstrumentEditor
from llamatron.tui.screens.set.scale_page import ScalePage

# The editor of each section's things: a generator's by the section of its kind.
EDITORS = {
    Section.PATTERNS: PatternEditor,
    Section.CHAINS: ChainEditor,
    Section.SCALES: ScalePage,
    Section.INSTRUMENTS: InstrumentEditor,
    Section.GROOVES: GrooveEditor,
    Section.TRACKS: TrackEditor,
    **{section: listing.EDITOR for section, listing in generator_pages.GENERATOR_PAGES.items()},
}


# The page that shows the whole of a section of the song, for a section with no named things to list.
SECTION_PAGES = {
    Section.DRAWS: DrawsPage,
}


def section_page_of(section):
    """Return the class of the page that shows the whole of a section of the song."""
    return SECTION_PAGES[section]


def editor_of(section):
    """Return the class of the page that edits one named thing of a section."""
    return EDITORS[section]
