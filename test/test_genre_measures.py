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

"""The measure registry: every field a trait compares is one measure, with a unit and a name in plain words; a measure reads
itself from a style and from a song alike; every style's values and a demo's keep to their units' bounds; and one trait is
heard from a performance on its own, the same as with the rest."""

import os
import unittest

from llamatron.composition.setlist import Setlist
from llamatron.genres.hearing.performance import performance_of
from llamatron.genres.hearing.profile import HEARERS, Listening, profile_of_performance
from llamatron.genres.measures.comparing import UNIT_BOUNDS, Unit
from llamatron.genres.measures.registry import MEASURES, MEASURES_BY_NAME, SPACING, NoSuchMeasure, measure
from llamatron.genres.measures.traits import TRAIT_KINDS, TRAITS, Spacing, Trait
from llamatron.strings.genres import MSG_MEASURE_LABELS

DEMO = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'examples', 'by_genre', 'rock', 'green_men.yml')
SEED = 1
SINGABLE = 'vocal.singable'
TEMPO = 'tempo.low'
MUD = 'spacing.mud'
UNKNOWN = 'vocal.loudness'
UNITS = tuple(value for name, value in vars(Unit).items() if not name.startswith('_'))


def demo_performance():
    setlist = Setlist.read_file(DEMO)
    return performance_of(setlist.get_song(setlist.get_song_names()[0]), seed=SEED)


def out_of_bounds(*, subject):
    """Return the names of the measures whose value in a subject lies outside its unit's bounds."""
    found = []
    for each in MEASURES:
        value = each.of(subject)
        bounds = each.bounds()
        if bounds is None or value is None:
            continue
        values = value if isinstance(value, tuple) else (value,)
        if any(not bounds[0] <= one <= bounds[1] for one in values):
            found.append(each.name())
    return found


class TestTheRegistry(unittest.TestCase):

    def test_every_compared_field_of_every_trait_is_one_measure(self):
        declared = [trait + '.' + field for trait in TRAITS for field in TRAIT_KINDS[trait].COMPARED]
        declared += [SPACING + '.' + field for field in Spacing.COMPARED]
        self.assertEqual([each.name() for each in MEASURES], declared)
        self.assertEqual(len(MEASURES_BY_NAME), len(MEASURES))

    def test_every_trait_has_a_class_and_a_hearer(self):
        self.assertEqual(tuple(TRAIT_KINDS), TRAITS)
        self.assertEqual(tuple(HEARERS), TRAITS)

    def test_every_measure_has_a_unit_and_a_label_and_no_label_is_left_over(self):
        for each in MEASURES:
            self.assertIn(each.unit(), UNITS, each.name())
            self.assertTrue(each.label(), each.name())
        self.assertEqual(sorted(MSG_MEASURE_LABELS), sorted(MEASURES_BY_NAME))

    def test_every_bounded_unit_is_a_unit(self):
        for unit in UNIT_BOUNDS:
            self.assertIn(unit, UNITS)

    def test_a_measure_is_found_by_its_name_and_an_unknown_name_is_refused(self):
        self.assertEqual(measure(SINGABLE).holder, Trait.VOCAL)
        self.assertEqual(measure(TEMPO).holder, Trait.TEMPO)
        with self.assertRaises(NoSuchMeasure):
            measure(UNKNOWN)


class TestReadingMeasures(unittest.TestCase):

    def test_a_song_keeps_every_measure_within_its_units_bounds(self):
        profile = profile_of_performance(performance=demo_performance(), name='demo')
        self.assertEqual(out_of_bounds(subject=profile), [])


class TestListening(unittest.TestCase):

    def test_one_trait_heard_alone_is_the_same_as_heard_with_the_rest(self):
        performance = demo_performance()
        profile = profile_of_performance(performance=performance, name='demo')
        for trait in TRAITS:
            self.assertEqual(Listening(performance).trait(trait), profile.trait(trait), trait)

    def test_what_several_traits_are_heard_from_is_worked_out_once(self):
        heard = Listening(demo_performance())
        self.assertIs(heard.roles(), heard.roles())
        self.assertIs(heard.line(), heard.line())


if __name__ == '__main__':
    unittest.main()
