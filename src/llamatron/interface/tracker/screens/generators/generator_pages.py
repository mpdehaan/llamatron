# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every kind of generator, by its section and by its kind: what the tracker calls it and the page that edits one, which the Generators page, the chain editor and Arrange's details open."""

from typing import NamedTuple

from llamatron.interface.tracker.dialogs.grouped_choice_dialog import GroupedChoiceDialog
from llamatron.interface.tracker.screens.generators.arp_editor import ArpEditor
from llamatron.interface.tracker.screens.generators.drift_editor import DriftEditor
from llamatron.interface.tracker.screens.generators.hocket_editor import HocketEditor
from llamatron.interface.tracker.screens.generators.musician_editor import MusicianEditor
from llamatron.interface.tracker.screens.shared.plugin_editor import has_view, plugin_editor_of
from llamatron.model.schema import file_format, generator_plugins
from llamatron.model.schema.file_format import Section
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


# The page that edits a generator of each kind, by the section of the set that holds them, which each editor names.
EDITORS = {editor.SECTION: editor for editor in (
    ArpEditor, DriftEditor, HocketEditor, MusicianEditor,
)}


def _listing_of(plugin):
    """Return how the tracker lists a generator plugin: its name, its section, its own label and heading, and its editor, the
    page drawn from its view where it describes one."""
    if has_view(plugin.section):
        editor = plugin_editor_of(plugin.section)
    else:
        editor = EDITORS[plugin.section]
    return GeneratorListing(kind=plugin.name, section=plugin.section, label=plugin.strings.MSG_LABEL, group=plugin.strings.MSG_GROUP, EDITOR=editor)


def _plugin_listings():
    """Return how the tracker lists every generator plugin found."""
    return [_listing_of(plugin) for plugin in generator_plugins.plugins().values()]


# Every kind of generator, in the order the Generators page offers them when adding one, from the plugins found.
GENERATOR_PAGES = {listing.section: listing for listing in _in_shown_order(_plugin_listings())}


# A chain, which a clip, a scene and a track list beside the generators and the Generators page lists as one more kind; its
# editor is the chain editor (interface/tracker/screens/editors.py), and a chain's own steps are never chains.
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
