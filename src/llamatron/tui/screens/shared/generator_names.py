# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How a clip's, a scene's and a track's list of generators names each one, and which of the set's generators may be added to it."""

from llamatron.composition.naming import name_order
from llamatron.user_strings import labels


def listed_generator(*, setlist, name):
    """Return a generator of a list as the page shows it, its kind before its name, as Chain: fills."""
    return labels.MSG_LISTED_GENERATOR.format(kind=labels.MSG_GENERATOR_KIND_LABELS[setlist.generator_kind(name)], name=name)


def generators_to_add(setlist):
    """Return every generator of the set, a chain among them, as (kind, name), sorted by what the kind is called and then by name."""
    return sorted(setlist.ordered_generators(), key=lambda pair: (name_order(labels.MSG_GENERATOR_KIND_LABELS[pair[0]]), name_order(pair[1])))
