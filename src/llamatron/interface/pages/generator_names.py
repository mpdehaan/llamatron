# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How a clip's, a scene's and a track's list of generators names each one, and which of the set's generators may be added to it."""

from llamatron.model.objects.naming import name_order
from llamatron.model.schema import file_format, generator_plugins
from llamatron.user_strings import labels


def kind_label(kind):
    """Return what a kind of generator is called beside a generator's name: a plugin's own label, or the word for a chain."""
    return labels.MSG_CHAIN_LABEL if kind == file_format.CHAIN_KIND else generator_plugins.plugins()[kind].strings.MSG_LABEL


def listed_generator(*, setlist, name):
    """Return a generator of a list as the page shows it, its kind before its name, as Chain: fills."""
    return labels.MSG_LISTED_GENERATOR.format(kind=kind_label(setlist.generator_kind(name)), name=name)


def generators_to_add(setlist):
    """Return every generator of the set, a chain among them, as (kind, name), sorted by what the kind is called and then by name."""
    return sorted(setlist.ordered_generators(), key=lambda pair: (name_order(kind_label(pair[0])), name_order(pair[1])))
