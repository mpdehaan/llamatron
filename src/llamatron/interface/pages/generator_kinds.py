# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every kind of generator, by its section and by its kind: its kind as a chain names it, the set's section that holds it and
what the tracker calls it, in the order the kinds are offered; the tracker adds the page that edits one
(interface/tracker/screens/generators/generator_pages.py)."""

from typing import NamedTuple

from llamatron.model.schema import file_format, generator_plugins
from llamatron.model.schema.file_format import Section
from llamatron.user_strings import labels


class GeneratorKind(NamedTuple):
    """One kind of generator: its kind as a chain names it, the set's section that holds it, and what the tracker calls it."""

    kind: str
    section: str
    label: str


def in_shown_order(kinds):
    """Return kinds of generator as they are offered: by what the tracker calls each, capitals ignored."""
    return sorted(kinds, key=lambda listed: listed.label.casefold())


def _plugin_kinds():
    """Return every generator plugin found as a kind of generator."""
    return [GeneratorKind(kind=plugin.name, section=plugin.section, label=plugin.strings.MSG_LABEL) for plugin in generator_plugins.plugins().values()]


# Every kind of generator, by its section, in the order they are offered when adding one, from the plugins found.
GENERATOR_KINDS = {listed.section: listed for listed in in_shown_order(_plugin_kinds())}
# A chain, which a clip, a scene and a track list beside the generators and the Generators page lists as one more kind; a
# chain's own steps are never chains.
CHAIN = GeneratorKind(kind=file_format.CHAIN_KIND, section=Section.CHAINS, label=labels.MSG_CHAIN_LABEL)
# Every kind the Generators page lists and offers to make, the chain among them, in the order it offers them.
LISTED_KINDS = {listed.section: listed for listed in in_shown_order((CHAIN, *GENERATOR_KINDS.values()))}


def kind_listed(kind):
    """Return a kind of generator as it is listed, such as the arpeggiator's for arp, its label naming the kind."""
    return next(listed for listed in LISTED_KINDS.values() if listed.kind == kind)
