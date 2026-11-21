# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every kind of generator, by its section and by its kind: what the tracker calls it and the page that edits one, which the Generators page, the chain editor and Arrange's details open."""

from typing import NamedTuple

from llamatron.engine.generators import arp as arp_plugin, articulate as articulate_plugin, auto_ratchet as auto_ratchet_plugin, density as density_plugin, drag as drag_plugin, drift as drift_plugin, euclid as euclid_plugin, follow_chords as follow_chords_plugin, glide as glide_plugin, guitarify as guitarify_plugin, hocket as hocket_plugin, musician as musician_plugin, phrasing as phrasing_plugin, progression as progression_plugin, rush as rush_plugin, shorten as shorten_plugin, strum as strum_plugin, swell as swell_plugin, voice_leading as voice_leading_plugin
from llamatron.engine.generators.arp import strings as arp_strings
from llamatron.engine.generators.auto_ratchet import strings as auto_ratchet_strings
from llamatron.engine.generators.drag import strings as drag_strings
from llamatron.engine.generators.drift import strings as drift_strings
from llamatron.engine.generators.euclid import strings as euclid_strings
from llamatron.engine.generators.follow_chords import strings as follow_chords_strings
from llamatron.engine.generators.glide import strings as glide_strings
from llamatron.engine.generators.guitarify import strings as guitarify_strings
from llamatron.engine.generators.hocket import strings as hocket_strings
from llamatron.engine.generators.musician import strings as musician_strings
from llamatron.engine.generators.phrasing import strings as phrasing_strings
from llamatron.engine.generators.progression import strings as progression_strings
from llamatron.engine.generators.rush import strings as rush_strings
from llamatron.engine.generators.shorten import strings as shorten_strings
from llamatron.engine.generators.strum import strings as strum_strings
from llamatron.engine.generators.voice_leading import strings as voice_leading_strings
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Section, Shape
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
from llamatron.user_strings import labels, messages


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
        GeneratorListing(kind=arp_plugin.NAME, section=arp_plugin.SECTION, label=arp_strings.MSG_LABEL, group=labels.GeneratorGroup.VOICING, EDITOR=ArpEditor),
        GeneratorListing(kind=auto_ratchet_plugin.NAME, section=auto_ratchet_plugin.SECTION, label=auto_ratchet_strings.MSG_LABEL, group=labels.GeneratorGroup.RHYTHM, EDITOR=AutoRatchetEditor),
        GeneratorListing(kind=drift_plugin.NAME, section=drift_plugin.SECTION, label=drift_strings.MSG_LABEL, group=labels.GeneratorGroup.TRANSITIONS, EDITOR=DriftEditor),
        GeneratorListing(kind=progression_plugin.NAME, section=progression_plugin.SECTION, label=progression_strings.MSG_LABEL, group=labels.GeneratorGroup.HARMONY, EDITOR=ProgressionEditor),
        GeneratorListing(kind=voice_leading_plugin.NAME, section=voice_leading_plugin.SECTION, label=voice_leading_strings.MSG_LABEL, group=labels.GeneratorGroup.VOICING, EDITOR=VoiceLeadingEditor),
        GeneratorListing(kind=strum_plugin.NAME, section=strum_plugin.SECTION, label=strum_strings.MSG_LABEL, group=labels.GeneratorGroup.RHYTHM, EDITOR=StrumEditor),
        GeneratorListing(kind=euclid_plugin.NAME, section=euclid_plugin.SECTION, label=euclid_strings.MSG_LABEL, group=labels.GeneratorGroup.RHYTHM, EDITOR=EuclidEditor),
        GeneratorListing(kind=density_plugin.NAME, section=density_plugin.SECTION, label=labels.MSG_SHAPE_NAMES[Shape.DENSITY], group=labels.GeneratorGroup.TRANSITIONS, EDITOR=DensityEditor),
        GeneratorListing(kind=swell_plugin.NAME, section=swell_plugin.SECTION, label=labels.MSG_SHAPE_NAMES[Shape.SWELL], group=labels.GeneratorGroup.TRANSITIONS, EDITOR=SwellEditor),
        GeneratorListing(kind=articulate_plugin.NAME, section=articulate_plugin.SECTION, label=labels.MSG_SHAPE_NAMES[Shape.ARTICULATE], group=labels.GeneratorGroup.TRANSITIONS, EDITOR=ArticulateEditor),
        GeneratorListing(kind=glide_plugin.NAME, section=glide_plugin.SECTION, label=glide_strings.MSG_LABEL, group=labels.GeneratorGroup.ARTICULATION, EDITOR=GlideEditor),
        GeneratorListing(kind=shorten_plugin.NAME, section=shorten_plugin.SECTION, label=shorten_strings.MSG_LABEL, group=labels.GeneratorGroup.ARTICULATION, EDITOR=ShortenEditor),
        GeneratorListing(kind=rush_plugin.NAME, section=rush_plugin.SECTION, label=rush_strings.MSG_LABEL, group=labels.GeneratorGroup.TIMING, EDITOR=RushEditor),
        GeneratorListing(kind=drag_plugin.NAME, section=drag_plugin.SECTION, label=drag_strings.MSG_LABEL, group=labels.GeneratorGroup.TIMING, EDITOR=DragEditor),
        GeneratorListing(kind=hocket_plugin.NAME, section=hocket_plugin.SECTION, label=hocket_strings.MSG_LABEL, group=labels.GeneratorGroup.ARRANGEMENT, EDITOR=HocketEditor),
        GeneratorListing(kind=guitarify_plugin.NAME, section=guitarify_plugin.SECTION, label=guitarify_strings.MSG_LABEL, group=labels.GeneratorGroup.VOICING, EDITOR=GuitarifyEditor),
        GeneratorListing(kind=follow_chords_plugin.NAME, section=follow_chords_plugin.SECTION, label=follow_chords_strings.MSG_LABEL, group=labels.GeneratorGroup.HARMONY, EDITOR=FollowChordsEditor),
        GeneratorListing(kind=phrasing_plugin.NAME, section=phrasing_plugin.SECTION, label=phrasing_strings.MSG_LABEL, group=labels.GeneratorGroup.ARTICULATION, EDITOR=PhrasingEditor),
        GeneratorListing(kind=musician_plugin.NAME, section=musician_plugin.SECTION, label=musician_strings.MSG_LABEL, group=labels.GeneratorGroup.BAND, EDITOR=MusicianEditor),
    ))
}


# A chain, which a clip, a scene and a track list beside the generators and the Generators page lists as one more kind; its
# editor is the chain editor (tui/screens/editors.py), and a chain's own steps are never chains.
CHAIN_LISTING = GeneratorListing(kind=file_format.CHAIN_KIND, section=Section.CHAINS, label=labels.MSG_CHAIN_LABEL, group=labels.GeneratorGroup.CHAINS, EDITOR=None)
# Every kind the Generators page lists and offers to make, the chain among them, in the order it offers them.
LISTED_PAGES = {listing.section: listing for listing in _in_shown_order((CHAIN_LISTING, *GENERATOR_PAGES.values()))}


def generator_type_dialog(*, opened, listings=GENERATOR_PAGES):
    """Return the dialog that asks which type of generator to make, the types under their headings; it answers a place among the
    listings, a chain's steps offering the generators and the Generators page every kind, the chain among them (LISTED_PAGES)."""
    groups = {}
    for listing in listings.values():
        groups.setdefault(listing.group, []).append(listing.label)
    return GroupedChoiceDialog(title=messages.MSG_NEW_GENERATOR_KIND_TITLE, groups=list(groups.items()), opened=opened)


def generator_page_of_kind(kind):
    """Return a kind of generator's listing, such as the arpeggiator's for arp: its EDITOR edits one and its label names the kind."""
    return next(listing for listing in LISTED_PAGES.values() if listing.kind == kind)
