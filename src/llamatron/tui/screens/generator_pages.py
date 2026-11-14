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
"""Every kind of generator, by its section and by its kind: what the tracker calls it and the page that edits one, which the Generators page, the chain editor and Arrange's details open."""

from typing import NamedTuple

from llamatron.composition.file_format import GeneratorKind, Section, Shape
from llamatron.strings.labels import (
    MSG_ARP_LABEL, MSG_AUTO_RATCHET_LABEL, MSG_DRAG_LABEL, MSG_DRIFT_LABEL, MSG_EUCLID_LABEL, MSG_GLIDE_LABEL, MSG_HOCKET_LABEL,
    MSG_PROGRESSION_LABEL, MSG_RUSH_LABEL, MSG_SHAPE_NAMES, MSG_SHORTEN_LABEL_NAME, MSG_STRUM_LABEL, MSG_VOICE_LEADING_LABEL,
)
from llamatron.tui.screens.arp_editor import ArpEditor
from llamatron.tui.screens.articulate_editor import ArticulateEditor
from llamatron.tui.screens.auto_ratchet_editor import AutoRatchetEditor
from llamatron.tui.screens.density_editor import DensityEditor
from llamatron.tui.screens.drag_editor import DragEditor
from llamatron.tui.screens.drift_editor import DriftEditor
from llamatron.tui.screens.euclid_editor import EuclidEditor
from llamatron.tui.screens.glide_editor import GlideEditor
from llamatron.tui.screens.hocket_editor import HocketEditor
from llamatron.tui.screens.progression_editor import ProgressionEditor
from llamatron.tui.screens.rush_editor import RushEditor
from llamatron.tui.screens.shorten_editor import ShortenEditor
from llamatron.tui.screens.strum_editor import StrumEditor
from llamatron.tui.screens.swell_editor import SwellEditor
from llamatron.tui.screens.voice_leading_editor import VoiceLeadingEditor


class GeneratorListing(NamedTuple):
    """One kind of generator: its kind as a chain names it, the set's section that holds it, what the tracker calls it, and the page that edits one."""

    kind: str
    section: str
    label: str
    EDITOR: type


# Every kind of generator, in the order the Generators page offers them when adding one.
GENERATOR_PAGES = {
    listing.section: listing for listing in (
        GeneratorListing(kind=GeneratorKind.ARP, section=Section.ARPS, label=MSG_ARP_LABEL, EDITOR=ArpEditor),
        GeneratorListing(kind=GeneratorKind.AUTO_RATCHET, section=Section.AUTO_RATCHETS, label=MSG_AUTO_RATCHET_LABEL, EDITOR=AutoRatchetEditor),
        GeneratorListing(kind=GeneratorKind.DRIFT, section=Section.DRIFTS, label=MSG_DRIFT_LABEL, EDITOR=DriftEditor),
        GeneratorListing(kind=GeneratorKind.PROGRESSION, section=Section.PROGRESSIONS, label=MSG_PROGRESSION_LABEL, EDITOR=ProgressionEditor),
        GeneratorListing(kind=GeneratorKind.VOICE_LEADING, section=Section.VOICE_LEADINGS, label=MSG_VOICE_LEADING_LABEL, EDITOR=VoiceLeadingEditor),
        GeneratorListing(kind=GeneratorKind.STRUM, section=Section.STRUMS, label=MSG_STRUM_LABEL, EDITOR=StrumEditor),
        GeneratorListing(kind=GeneratorKind.EUCLID, section=Section.EUCLIDS, label=MSG_EUCLID_LABEL, EDITOR=EuclidEditor),
        GeneratorListing(kind=GeneratorKind.DENSITY, section=Section.DENSITIES, label=MSG_SHAPE_NAMES[Shape.DENSITY], EDITOR=DensityEditor),
        GeneratorListing(kind=GeneratorKind.SWELL, section=Section.SWELLS, label=MSG_SHAPE_NAMES[Shape.SWELL], EDITOR=SwellEditor),
        GeneratorListing(kind=GeneratorKind.ARTICULATE, section=Section.ARTICULATES, label=MSG_SHAPE_NAMES[Shape.ARTICULATE], EDITOR=ArticulateEditor),
        GeneratorListing(kind=GeneratorKind.GLIDE, section=Section.GLIDES, label=MSG_GLIDE_LABEL, EDITOR=GlideEditor),
        GeneratorListing(kind=GeneratorKind.SHORTEN, section=Section.SHORTENS, label=MSG_SHORTEN_LABEL_NAME, EDITOR=ShortenEditor),
        GeneratorListing(kind=GeneratorKind.RUSH, section=Section.RUSHES, label=MSG_RUSH_LABEL, EDITOR=RushEditor),
        GeneratorListing(kind=GeneratorKind.DRAG, section=Section.DRAGS, label=MSG_DRAG_LABEL, EDITOR=DragEditor),
        GeneratorListing(kind=GeneratorKind.HOCKET, section=Section.HOCKETS, label=MSG_HOCKET_LABEL, EDITOR=HocketEditor),
    )
}


def generator_page_of_kind(kind):
    """Return a kind of generator's listing, such as the arpeggiator's for arp: its EDITOR edits one and its label names the kind."""
    return next(listing for listing in GENERATOR_PAGES.values() if listing.kind == kind)
