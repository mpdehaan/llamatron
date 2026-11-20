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

"""The page that edits one named thing of each section, and the page that shows the whole of a section with no named things, so
that a page opens another by the section and never imports it.

The program holds this registry and answers a page that asks (LlamatronApp.editor_of), and a
page opens one with Page.open_editor(section=, name=).
"""

from llamatron.composition.file_format import Section
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
