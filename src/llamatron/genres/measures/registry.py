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

"""Every measure the genre library has, each declared once: a measure is one field of a trait (or of a song's spacing), named
by the two joined with a dot, as vocal.singable is, with how it compares and what it counts (its Field, written beside the
field in measures/traits.py), its name in plain words (strings/genres.py) and the way to read it from anything that holds
traits: a song's profile, a style, a stretch of a song. A new thing the library can hear is a field with its Field, a label and
the hearing of it; everything that lists, compares, calibrates or reports measures finds it here."""

from dataclasses import dataclass

from llamatron.genres.measures.comparing import UNIT_BOUNDS, Compare
from llamatron.genres.measures.traits import TRAIT_KINDS, TRAITS, Spacing
from llamatron.strings.errors import ERR_NO_SUCH_MEASURE
from llamatron.strings.genres import MSG_MEASURE_LABELS

# What a measure's name joins its holder and field with.
SEPARATOR = '.'
# The holder of the measures no style sets, which a song's profile keeps beside its traits.
SPACING = 'spacing'


class NoSuchMeasure(KeyError):
    """A measure asked for by a name the library doesn't have."""


@dataclass(slots=True, kw_only=True, frozen=True)
class Measure:
    """One thing the library measures: the trait (or spacing) that holds it, its field there, and how it compares."""

    holder: str
    field: str
    how: object

    def name(self):
        return self.holder + SEPARATOR + self.field

    def label(self):
        """Return the measure's name in plain words."""
        return MSG_MEASURE_LABELS[self.name()]

    def unit(self):
        return self.how.unit

    def bounds(self):
        """Return the lowest and highest value the measure can take, or None where its unit sets none."""
        return UNIT_BOUNDS.get(self.how.unit)

    def is_number(self):
        return self.how.way == Compare.NUMBER

    def held_by(self, subject):
        """Return what holds the measure in a subject, its trait or its spacing, or None where the subject has none."""
        if self.holder == SPACING:
            return getattr(subject, SPACING, None)
        return subject.trait(self.holder)

    def of(self, subject):
        """Return the measure's value in a subject, anything that holds traits, or None where the subject leaves it unknown."""
        held = self.held_by(subject)
        return getattr(held, self.field, None) if held is not None else None


def measures_held(*, holder, kind):
    """Return the measures one class of fields declares."""
    return [Measure(holder=holder, field=field, how=how) for field, how in kind.COMPARED.items()]


def every_measure():
    """Return every measure, the traits' in the order the traits are compared, then spacing's."""
    found = []
    for trait in TRAITS:
        found += measures_held(holder=trait, kind=TRAIT_KINDS[trait])
    return tuple(found + measures_held(holder=SPACING, kind=Spacing))


MEASURES = every_measure()
MEASURES_BY_NAME = {each.name(): each for each in MEASURES}


def measure(name):
    """Return the measure of a name, such as vocal.singable."""
    if name not in MEASURES_BY_NAME:
        raise NoSuchMeasure(ERR_NO_SUCH_MEASURE.format(name=name))
    return MEASURES_BY_NAME[name]


