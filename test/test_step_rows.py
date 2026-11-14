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
"""Glide, Shorten, Rush and Drag, the user's design of 2026-11-11: rows of on-or-off steps running from each clip's start, gliding or shortening the notes starting on the steps that are on, or moving them early or late."""

import unittest

from llamatron.composition.file_format import ClipSlotSetting, GeneratorKind, PatternSetting, Row, SceneSetting, Section
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.timing import GLIDE_OVERLAP
from llamatron.support.rational import Rational
from rendering import setlist_from_data
from test_registers import LEAD, X, pattern, song
from test_shapes import notes

STEPS = 4
QUARTER = Rational(1, 4)
SIXTEENTH = Rational(1, 16)
ON = True
OFF = False


def through(*rows):
    """Return a song whose lead plays four quarter notes climbing C, E, G, A through generators, each (section, kind, settings), in one chain."""
    figure = dict(pattern(STEPS, **{Row.DEGREE: [1, 3, 5, 6]}), **{PatternSetting.STEP_SIZE: '1/4'})
    chain = 'chain'
    data = song(patterns={X: figure}, scenes=[{SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: X, ClipSlotSetting.CHAINS: [chain]}}}])
    data[Section.CHAINS] = {chain: []}
    for place, (section, kind, settings) in enumerate(rows):
        name = '{kind} {place}'.format(kind=kind, place=place)
        data.setdefault(section, {})[name] = settings
        data[Section.CHAINS][chain].append({kind: name})
    return data


def glide(steps, **settings):
    return (Section.GLIDES, GeneratorKind.GLIDE, {'steps': steps, **settings})


def shorten(steps, **settings):
    return (Section.SHORTENS, GeneratorKind.SHORTEN, {'steps': steps, **settings})


def rush(steps, **settings):
    return (Section.RUSHES, GeneratorKind.RUSH, {'steps': steps, **settings})


def drag(steps, **settings):
    return (Section.DRAGS, GeneratorKind.DRAG, {'steps': steps, **settings})


def lengths(*rows):
    return [length for _, length, _, _ in notes(through(*rows))]


def starts(*rows):
    return [start for start, _, _, _ in notes(through(*rows))]


class TestGlide(unittest.TestCase):

    def test_a_step_that_is_on_runs_its_note_into_the_next(self):
        self.assertEqual(lengths(glide([ON, OFF]))[:2], [QUARTER + GLIDE_OVERLAP, QUARTER])

    def test_the_glide_amount_sets_how_far(self):
        self.assertEqual(lengths(glide([ON], glide_amount='1/16'))[0], QUARTER + SIXTEENTH)

    def test_the_last_note_has_nothing_to_glide_into(self):
        self.assertEqual(lengths(glide([ON]))[-1], QUARTER)


class TestShorten(unittest.TestCase):

    def test_a_step_that_is_on_plays_its_share(self):
        self.assertEqual(set(lengths(shorten([ON], shorten=50))), {Rational(1, 8)})

    def test_the_row_runs_at_its_own_step(self):
        self.assertEqual(lengths(shorten([ON, OFF], step='1/2', shorten=50)), [Rational(1, 8), Rational(1, 8), QUARTER, QUARTER])


class TestRushAndDrag(unittest.TestCase):

    def test_a_drag_moves_a_note_late_and_a_rush_early(self):
        self.assertEqual(starts(drag([OFF, ON, OFF, OFF])), [0, QUARTER + QUARTER / 5, 2 * QUARTER, 3 * QUARTER])
        self.assertEqual(starts(rush([OFF, OFF, OFF, ON])), [0, QUARTER, 2 * QUARTER, 3 * QUARTER - QUARTER * Rational(15, 100)])

    def test_a_step_on_in_both_moves_by_the_difference(self):
        self.assertEqual(starts(rush([OFF, ON], amount=10), drag([OFF, ON], amount=30))[1], QUARTER + QUARTER / 5)

    def test_the_first_note_cannot_move_before_the_clip(self):
        self.assertEqual(starts(rush([ON]))[0], 0)


class TestWhatAFileHolds(unittest.TestCase):

    def test_more_than_half_a_step_is_refused(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(through(drag([ON], amount=51)))

    def test_a_step_that_is_not_on_or_off_is_refused(self):
        with self.assertRaises(SongFileError):
            setlist_from_data(through(glide(['wobble'])))
