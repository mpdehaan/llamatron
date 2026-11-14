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

"""A style as a document, and the tool that prints a song's: every trait a subject sets as plain data that JSON can hold,
nothing of a song's notes, and the script on the Entertainer."""

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path

from llamatron.genres.hearing.midi_file import performance_of_midi
from llamatron.genres.hearing.profile import profile_of_performance
from llamatron.genres.measures.traits import TRAITS, Bass, BassMotion, Trait
from llamatron.genres.reporting.style_document import plain, style_document

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'internal_tools' / 'analysis_and_generation'))

import describe_style  # noqa: E402

ENTERTAINER = ROOT / 'examples' / 'midi' / 'entertainer.mid'
SONG = 'song'
MISSING = 'no_such_file.mid'
NOTES_PER_BAR = 4
# Words a style document must never hold: it says what kind of music, not which notes.
NOTE_WORDS = ('notes', 'pitch', 'pattern', 'begins')
NOTES_PER_BAR_FIELD = 'notes_per_bar'
MOTION_FIELD = 'motion'
REACH_FIELD = 'reach'


class TestStyleDocument(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.profile = profile_of_performance(performance=performance_of_midi(ENTERTAINER), name=SONG)
        cls.document = style_document(cls.profile)

    def test_a_trait_becomes_its_fields_with_the_unset_ones_left_out(self):
        fields = plain(Bass(motion=BassMotion.WALKING, notes_per_bar=NOTES_PER_BAR))
        self.assertEqual(fields[MOTION_FIELD], BassMotion.WALKING)
        self.assertEqual(fields[NOTES_PER_BAR_FIELD], NOTES_PER_BAR)
        self.assertNotIn(REACH_FIELD, fields)

    def test_a_songs_document_holds_the_traits_it_sets_in_the_traits_order_and_none_it_does_not(self):
        self.assertEqual(list(self.document), [trait for trait in TRAITS if trait in self.document])
        for trait in TRAITS:
            self.assertEqual(trait in self.document, self.profile.trait(trait) is not None and bool(plain(self.profile.trait(trait))), trait)
        self.assertIn(Trait.TEMPO, self.document)
        self.assertIn(Trait.HARMONY, self.document)

    def test_the_document_is_json_and_reads_back_the_same(self):
        self.assertEqual(json.loads(json.dumps(self.document)), self.document)

    def test_the_document_holds_nothing_of_the_songs_notes(self):
        for trait, fields in self.document.items():
            for name in fields:
                self.assertFalse(any(name == word for word in NOTE_WORDS), (trait, name))

class TestDescribeStyle(unittest.TestCase):

    def printed(self, *arguments):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            describe_style.main(argv=list(arguments))
        return out.getvalue()

    def test_the_script_prints_the_songs_document_as_json(self):
        document = json.loads(self.printed(str(ENTERTAINER)))
        self.assertEqual(document, style_document(profile_of_performance(performance=performance_of_midi(ENTERTAINER), name=SONG)))

    def test_a_file_that_is_not_there_is_refused(self):
        with self.assertRaises(SystemExit) as refused:
            describe_style.main(argv=[MISSING])
        self.assertEqual(str(refused.exception), describe_style.NO_SUCH_FILE.format(path=MISSING))


if __name__ == '__main__':
    unittest.main()
