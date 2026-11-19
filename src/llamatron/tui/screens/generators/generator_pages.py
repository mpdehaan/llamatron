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
from llamatron.strings import labels, messages
from llamatron.tui.dialogs.grouped_choice_dialog import GroupedChoiceDialog
from llamatron.tui.screens.generators.arp_editor import ArpEditor
from llamatron.tui.screens.generators.articulate_editor import ArticulateEditor
from llamatron.tui.screens.generators.auto_ratchet_editor import AutoRatchetEditor
from llamatron.tui.screens.generators.density_editor import DensityEditor
from llamatron.tui.screens.generators.drag_editor import DragEditor
from llamatron.tui.screens.generators.drift_editor import DriftEditor
from llamatron.tui.screens.generators.euclid_editor import EuclidEditor
from llamatron.tui.screens.generators.follow_chords_editor import FollowChordsEditor
from llamatron.tui.screens.generators.glide_editor import GlideEditor
from llamatron.tui.screens.generators.guitarify_editor import GuitarifyEditor
from llamatron.tui.screens.generators.hocket_editor import HocketEditor
from llamatron.tui.screens.generators.musician_editor import MusicianEditor
from llamatron.tui.screens.generators.phrasing_editor import PhrasingEditor
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
        GeneratorListing(kind=GeneratorKind.ARP, section=Section.ARPS, label=labels.MSG_ARP_LABEL, group=labels.GeneratorGroup.VOICING, EDITOR=ArpEditor),
        GeneratorListing(kind=GeneratorKind.AUTO_RATCHET, section=Section.AUTO_RATCHETS, label=labels.MSG_AUTO_RATCHET_LABEL, group=labels.GeneratorGroup.RHYTHM, EDITOR=AutoRatchetEditor),
        GeneratorListing(kind=GeneratorKind.DRIFT, section=Section.DRIFTS, label=labels.MSG_DRIFT_LABEL, group=labels.GeneratorGroup.TRANSITIONS, EDITOR=DriftEditor),
        GeneratorListing(kind=GeneratorKind.PROGRESSION, section=Section.PROGRESSIONS, label=labels.MSG_PROGRESSION_LABEL, group=labels.GeneratorGroup.HARMONY, EDITOR=ProgressionEditor),
        GeneratorListing(kind=GeneratorKind.VOICE_LEADING, section=Section.VOICE_LEADINGS, label=labels.MSG_VOICE_LEADING_LABEL, group=labels.GeneratorGroup.VOICING, EDITOR=VoiceLeadingEditor),
        GeneratorListing(kind=GeneratorKind.STRUM, section=Section.STRUMS, label=labels.MSG_STRUM_LABEL, group=labels.GeneratorGroup.RHYTHM, EDITOR=StrumEditor),
        GeneratorListing(kind=GeneratorKind.EUCLID, section=Section.EUCLIDS, label=labels.MSG_EUCLID_LABEL, group=labels.GeneratorGroup.RHYTHM, EDITOR=EuclidEditor),
        GeneratorListing(kind=GeneratorKind.DENSITY, section=Section.DENSITIES, label=labels.MSG_SHAPE_NAMES[Shape.DENSITY], group=labels.GeneratorGroup.TRANSITIONS, EDITOR=DensityEditor),
        GeneratorListing(kind=GeneratorKind.SWELL, section=Section.SWELLS, label=labels.MSG_SHAPE_NAMES[Shape.SWELL], group=labels.GeneratorGroup.TRANSITIONS, EDITOR=SwellEditor),
        GeneratorListing(kind=GeneratorKind.ARTICULATE, section=Section.ARTICULATES, label=labels.MSG_SHAPE_NAMES[Shape.ARTICULATE], group=labels.GeneratorGroup.TRANSITIONS, EDITOR=ArticulateEditor),
        GeneratorListing(kind=GeneratorKind.GLIDE, section=Section.GLIDES, label=labels.MSG_GLIDE_LABEL, group=labels.GeneratorGroup.ARTICULATION, EDITOR=GlideEditor),
        GeneratorListing(kind=GeneratorKind.SHORTEN, section=Section.SHORTENS, label=labels.MSG_SHORTEN_LABEL_NAME, group=labels.GeneratorGroup.ARTICULATION, EDITOR=ShortenEditor),
        GeneratorListing(kind=GeneratorKind.RUSH, section=Section.RUSHES, label=labels.MSG_RUSH_LABEL, group=labels.GeneratorGroup.TIMING, EDITOR=RushEditor),
        GeneratorListing(kind=GeneratorKind.DRAG, section=Section.DRAGS, label=labels.MSG_DRAG_LABEL, group=labels.GeneratorGroup.TIMING, EDITOR=DragEditor),
        GeneratorListing(kind=GeneratorKind.HOCKET, section=Section.HOCKETS, label=labels.MSG_HOCKET_LABEL, group=labels.GeneratorGroup.ARRANGEMENT, EDITOR=HocketEditor),
        GeneratorListing(kind=GeneratorKind.GUITARIFY, section=Section.GUITARIFIES, label=labels.MSG_GUITARIFY_LABEL, group=labels.GeneratorGroup.VOICING, EDITOR=GuitarifyEditor),
        GeneratorListing(kind=GeneratorKind.FOLLOW_CHORDS, section=Section.FOLLOW_CHORDS, label=labels.MSG_FOLLOW_CHORDS_LABEL, group=labels.GeneratorGroup.HARMONY, EDITOR=FollowChordsEditor),
        GeneratorListing(kind=GeneratorKind.PHRASING, section=Section.PHRASINGS, label=labels.MSG_PHRASING_LABEL, group=labels.GeneratorGroup.ARTICULATION, EDITOR=PhrasingEditor),
        GeneratorListing(kind=GeneratorKind.MUSICIAN, section=Section.MUSICIANS, label=labels.MSG_MUSICIAN_LABEL, group=labels.GeneratorGroup.BAND, EDITOR=MusicianEditor),
    ))
}


def generator_type_dialog(*, opened):
    """Return the dialog that asks which type of generator to make, the types under their headings; it answers a place among GENERATOR_PAGES' listings."""
    groups = {}
    for listing in GENERATOR_PAGES.values():
        groups.setdefault(listing.group, []).append(listing.label)
    return GroupedChoiceDialog(title=messages.MSG_NEW_GENERATOR_KIND_TITLE, groups=list(groups.items()), opened=opened)


def generator_page_of_kind(kind):
    """Return a kind of generator's listing, such as the arpeggiator's for arp: its EDITOR edits one and its label names the kind."""
    return next(listing for listing in GENERATOR_PAGES.values() if listing.kind == kind)
