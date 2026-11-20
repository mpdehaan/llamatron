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

"""How a clip's, a scene's and a track's list of generators names each one, and which of the set's generators may be added to it."""

from llamatron.composition.naming import name_order
from llamatron.strings import labels


def listed_generator(*, setlist, name):
    """Return a generator of a list as the page shows it, its kind before its name, as Chain: fills."""
    return labels.MSG_LISTED_GENERATOR.format(kind=labels.MSG_GENERATOR_KIND_LABELS[setlist.generator_kind(name)], name=name)


def generators_to_add(setlist):
    """Return every generator of the set, a chain among them, as (kind, name), sorted by what the kind is called and then by name."""
    return sorted(setlist.ordered_generators(), key=lambda pair: (name_order(labels.MSG_GENERATOR_KIND_LABELS[pair[0]]), name_order(pair[1])))
