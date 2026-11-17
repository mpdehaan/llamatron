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
    GeneratorGroup, MSG_ARP_LABEL, MSG_AUTO_RATCHET_LABEL, MSG_DRAG_LABEL, MSG_DRIFT_LABEL, MSG_EUCLID_LABEL, MSG_FOLLOW_CHORDS_LABEL, MSG_GLIDE_LABEL, MSG_GUITARIFY_LABEL, MSG_HOCKET_LABEL,
    MSG_PROGRESSION_LABEL, MSG_RUSH_LABEL, MSG_SHAPE_NAMES, MSG_SHORTEN_LABEL_NAME, MSG_STRUM_LABEL, MSG_VOICE_LEADING_LABEL,
)
from llamatron.strings.messages import MSG_NEW_GENERATOR_KIND_TITLE
from llamatron.tui.dialogs.grouped_choice_dialog import GroupedChoiceDialog
from llamatron.tui.screens.generators.arp_editor import ArpEditor
from llamatron.tui.screens.generators.articulate_editor import ArticulateEditor
from llamatron.tui.screens.generators.auto_ratchet_editor import AutoRatchetEditor
from llamatron.tui.screens.generators.density_editor import DensityEditor
from llamatron.tui.screens.generators.drag_editor import DragEditor
from llamatron.tui.screens.generators.drift_editor import DriftEditor
from llamatron.tui.screens.generators.euclid_editor import EuclidEditor
from llamatron.tui.screens.generators.glide_editor import GlideEditor
from llamatron.tui.screens.generators.guitarify_editor import GuitarifyEditor
from llamatron.tui.screens.generators.follow_chords_editor import FollowChordsEditor
from llamatron.tui.screens.generators.hocket_editor import HocketEditor
from llamatron.tui.screens.generators.progression_editor import ProgressionEditor
from llamatron.tui.screens.generators.rush_editor import RushEditor
from llamatron.tui.screens.generators.shorten_editor import ShortenEditor
from llamatron.tui.screens.generators.strum_editor import StrumEditor
from llamatron.tui.screens.generators.swell_editor import SwellEditor
from llamatron.tui.screens.generators.voice_leading_editor import VoiceLeadingEditor


class GeneratorListing(NamedTuple):
    """One kind of generator: its kind as a chain names it, the set's section that holds it, what the tracker calls it, the heading it is offered under, and the page that edits one."""

    kind: str
    section: str
    label: str
    group: str
    EDITOR: type


def _in_shown_order(listings):
    """Return the kinds of generator as they are offered: by heading, and by name under a heading, capitals ignored."""
    return sorted(listings, key=lambda listing: (listing.group.casefold(), listing.label.casefold()))


# Every kind of generator, in the order the Generators page offers them when adding one.
GENERATOR_PAGES = {
    listing.section: listing for listing in _in_shown_order((
        GeneratorListing(kind=GeneratorKind.ARP, section=Section.ARPS, label=MSG_ARP_LABEL, group=GeneratorGroup.VOICING, EDITOR=ArpEditor),
        GeneratorListing(kind=GeneratorKind.AUTO_RATCHET, section=Section.AUTO_RATCHETS, label=MSG_AUTO_RATCHET_LABEL, group=GeneratorGroup.RHYTHM, EDITOR=AutoRatchetEditor),
        GeneratorListing(kind=GeneratorKind.DRIFT, section=Section.DRIFTS, label=MSG_DRIFT_LABEL, group=GeneratorGroup.TRANSITIONS, EDITOR=DriftEditor),
        GeneratorListing(kind=GeneratorKind.PROGRESSION, section=Section.PROGRESSIONS, label=MSG_PROGRESSION_LABEL, group=GeneratorGroup.HARMONY, EDITOR=ProgressionEditor),
        GeneratorListing(kind=GeneratorKind.VOICE_LEADING, section=Section.VOICE_LEADINGS, label=MSG_VOICE_LEADING_LABEL, group=GeneratorGroup.VOICING, EDITOR=VoiceLeadingEditor),
        GeneratorListing(kind=GeneratorKind.STRUM, section=Section.STRUMS, label=MSG_STRUM_LABEL, group=GeneratorGroup.RHYTHM, EDITOR=StrumEditor),
        GeneratorListing(kind=GeneratorKind.EUCLID, section=Section.EUCLIDS, label=MSG_EUCLID_LABEL, group=GeneratorGroup.RHYTHM, EDITOR=EuclidEditor),
        GeneratorListing(kind=GeneratorKind.DENSITY, section=Section.DENSITIES, label=MSG_SHAPE_NAMES[Shape.DENSITY], group=GeneratorGroup.TRANSITIONS, EDITOR=DensityEditor),
        GeneratorListing(kind=GeneratorKind.SWELL, section=Section.SWELLS, label=MSG_SHAPE_NAMES[Shape.SWELL], group=GeneratorGroup.TRANSITIONS, EDITOR=SwellEditor),
        GeneratorListing(kind=GeneratorKind.ARTICULATE, section=Section.ARTICULATES, label=MSG_SHAPE_NAMES[Shape.ARTICULATE], group=GeneratorGroup.TRANSITIONS, EDITOR=ArticulateEditor),
        GeneratorListing(kind=GeneratorKind.GLIDE, section=Section.GLIDES, label=MSG_GLIDE_LABEL, group=GeneratorGroup.ARTICULATION, EDITOR=GlideEditor),
        GeneratorListing(kind=GeneratorKind.SHORTEN, section=Section.SHORTENS, label=MSG_SHORTEN_LABEL_NAME, group=GeneratorGroup.ARTICULATION, EDITOR=ShortenEditor),
        GeneratorListing(kind=GeneratorKind.RUSH, section=Section.RUSHES, label=MSG_RUSH_LABEL, group=GeneratorGroup.TIMING, EDITOR=RushEditor),
        GeneratorListing(kind=GeneratorKind.DRAG, section=Section.DRAGS, label=MSG_DRAG_LABEL, group=GeneratorGroup.TIMING, EDITOR=DragEditor),
        GeneratorListing(kind=GeneratorKind.HOCKET, section=Section.HOCKETS, label=MSG_HOCKET_LABEL, group=GeneratorGroup.ARRANGEMENT, EDITOR=HocketEditor),
        GeneratorListing(kind=GeneratorKind.GUITARIFY, section=Section.GUITARIFIES, label=MSG_GUITARIFY_LABEL, group=GeneratorGroup.VOICING, EDITOR=GuitarifyEditor),
        GeneratorListing(kind=GeneratorKind.FOLLOW_CHORDS, section=Section.FOLLOW_CHORDS, label=MSG_FOLLOW_CHORDS_LABEL, group=GeneratorGroup.HARMONY, EDITOR=FollowChordsEditor),
    ))
}


def generator_type_dialog(*, opened):
    """Return the dialog that asks which type of generator to make, the types under their headings; it answers a place among GENERATOR_PAGES' listings."""
    groups = {}
    for listing in GENERATOR_PAGES.values():
        groups.setdefault(listing.group, []).append(listing.label)
    return GroupedChoiceDialog(title=MSG_NEW_GENERATOR_KIND_TITLE, groups=list(groups.items()), opened=opened)


def generator_page_of_kind(kind):
    """Return a kind of generator's listing, such as the arpeggiator's for arp: its EDITOR edits one and its label names the kind."""
    return next(listing for listing in GENERATOR_PAGES.values() if listing.kind == kind)
