# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every kind of generator, by its section and by its kind: what the tracker calls it and the page that edits one, which the Generators page, the chain editor and Arrange's details open."""

from typing import NamedTuple

from llamatron.interface.pages import generator_kinds
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.screens.shared.plugin_editor import plugin_editor_of
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import messages


class GeneratorListing(NamedTuple):
    """One kind of generator: its kind as a chain names it, the set's section that holds it, what the tracker calls it, the heading it is offered under, and the page that edits one."""

    kind: str
    section: str
    label: str
    EDITOR: type


def _listing_of(listed):
    """Return how the tracker lists a kind of generator: its kind, its section and its label, and its editor, a plugin's page
    drawn from its view, or none for a chain, whose editor is the chain editor (interface/tracker/screens/editors.py)."""
    editor = None
    if listed.section != Section.CHAINS:
        editor = plugin_editor_of(listed.section)
    return GeneratorListing(kind=listed.kind, section=listed.section, label=listed.label, EDITOR=editor)


# Every kind of generator, in the order the Generators page offers them when adding one, from the plugins found.
GENERATOR_PAGES = {section: _listing_of(listed) for section, listed in generator_kinds.GENERATOR_KINDS.items()}
# Every kind the Generators page lists and offers to make, the chain among them, in the order it offers them.
LISTED_PAGES = {section: _listing_of(listed) for section, listed in generator_kinds.LISTED_KINDS.items()}


def generator_type_dialog(*, listings=GENERATOR_PAGES):
    """Return the dialog that asks which type of generator to make, the types sorted by name, searched by typing; it answers a
    place among the listings, a chain's steps offering the generators and the Generators page every kind, the chain among them
    (LISTED_PAGES)."""
    names = [listing.label for listing in listings.values()]
    return ChoiceDialog(title=messages.MSG_NEW_GENERATOR_KIND_TITLE, options=names)


def generator_page_of_kind(kind):
    """Return a kind of generator's listing, such as the arpeggiator's for arp: its EDITOR edits one and its label names the kind."""
    return next(listing for listing in LISTED_PAGES.values() if listing.kind == kind)
