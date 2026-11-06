# llamatron: a Python language and framework for producing MIDI clips.
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

import glob
import os
import tempfile
import unittest
from fractions import Fraction

import yaml

from llamatron.song_file import SongBuilder, SongFileError
from llamatron.tui.document import DEFAULT_SCALE, Document, clock, new_song, unique_name


def song_with_things():
    """Return a document with a little of everything."""
    data = new_song()
    data['patterns'] = {
        'a': {'steps': 2, 'degree': [1, 3], 'duration': ['1/4', '1/4']},
        'b': {'steps': 1, 'degree': [5], 'duration': ['1/2']},
        'unused': {'steps': 1, 'duration': ['1/4']},
    }
    data['tracks'] = {'lead': {}, 'bass': {}}
    data['arps'] = {'up': {'step': '1/8', 'order': 'up'}}
    data['auto_ratchets'] = {'rolls': {'counts': [2]}}
    data['chains'] = {
        'named': [{'arp': 'up'}, {'auto_ratchet': 'rolls'}],
    }
    data['scenes'] = [
        {'name': 'one', 'repeat': 2, 'tracks': {'lead': {'pattern': 'a', 'chain': 'named'}}},
        {'name': 'two', 'tracks': {'lead': {'pattern': 'a', 'repeat': 2, 'morph_to': 'b', 'morph_style': 'left'}, 'bass': {'pattern': 'b'}}},
        {'name': 'three', 'scale': DEFAULT_SCALE, 'tracks': {'bass': {'pattern': 'b'}}},
    ]
    return Document(data)


class TestNewSong(unittest.TestCase):

    def test_has_a_c_major_scale_that_can_be_deleted(self):
        document = Document()
        self.assertEqual(document.data['scale'], 'C Major')
        self.assertEqual(document.data['scales'], {'C Major': {'root': 'C', 'type': 'major'}})
        self.assertEqual(document.scale_uses('C Major'), ['the song'])
        document.data['scale'] = None
        document.changed()
        self.assertEqual(document.scale_uses('C Major'), [])
        document.delete_scale('C Major')
        self.assertEqual(document.data['scales'], {})

    def test_has_the_song_defaults(self):
        data = Document().data
        self.assertEqual(data['default_length'], '1/16')
        self.assertEqual(data['granularity'], '1/16')
        self.assertEqual(data['default_octave'], 3)
        self.assertEqual(data['default_drum_octave'], 1)

    def test_starts_with_nothing_unsaved(self):
        self.assertFalse(Document().dirty)


class TestSaving(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = temporary.name

    def test_every_example_saves_and_loads_the_same(self):
        for path in glob.glob('examples/*.yml'):
            document = Document.load(path)
            target = os.path.join(self.folder, os.path.basename(path))
            document.save(target)
            with open(path) as first, open(target) as second:
                original, saved = yaml.safe_load(first), yaml.safe_load(second)
            # Saving writes out the song settings that a file left to their defaults.
            with self.subTest(path=path):
                self.assertEqual({key: saved[key] for key in original}, original)

    def test_only_writes_when_asked(self):
        path = os.path.join(self.folder, 'x.yml')
        document = Document(path=path)
        document.add_track('lead')
        self.assertFalse(os.path.exists(path))
        self.assertTrue(document.dirty)
        document.save()
        self.assertTrue(os.path.exists(path))
        self.assertFalse(document.dirty)

    def test_rows_with_nothing_in_them_are_not_written(self):
        document = song_with_things()
        document.set_step_value('a', 'velocity', 0, 90)
        document.set_step_value('a', 'velocity', 0, None)
        path = os.path.join(self.folder, 'x.yml')
        document.save(path)
        with open(path) as file:
            self.assertNotIn('velocity', yaml.safe_load(file)['patterns']['a'])
        self.assertIn('velocity', document.data['patterns']['a'])

    def test_makes_folders(self):
        path = os.path.join(self.folder, 'new', 'x.yml')
        Document().save(path)
        self.assertTrue(os.path.exists(path))

    def test_a_bad_file_raises(self):
        path = os.path.join(self.folder, 'bad.yml')
        with open(path, 'w') as file:
            file.write('tempo: 120\n')
        with self.assertRaises(SongFileError):
            Document.load(path)

    def test_the_name_comes_from_the_file(self):
        self.assertEqual(Document().name, 'untitled')
        self.assertEqual(Document(path='a/b/tune.yml').name, 'tune')


class TestRendering(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        previous = os.getcwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(temporary.name)

    def document(self):
        return song_with_things()

    def test_nothing_is_written_until_asked(self):
        document = self.document()
        document.add_track('another')
        self.assertFalse(os.path.exists('output'))

    def test_ableton_and_clip_tree(self):
        document = self.document()
        self.assertFalse(document.render_exists('ableton'))
        document.render('ableton')
        self.assertTrue(os.path.exists('output/untitled/untitled.als'))
        self.assertTrue(document.render_exists('ableton'))
        self.assertFalse(document.render_exists('cliptree'))
        document.render('cliptree')
        self.assertTrue(document.render_exists('cliptree'))

    def test_replaces_its_own_output_and_keeps_everything_else(self):
        document = self.document()
        document.render('cliptree')
        with open('output/untitled/notes.txt', 'w') as file:
            file.write('keep me')
        document.render('cliptree')
        self.assertTrue(os.path.exists('output/untitled/notes.txt'))

    def test_every_clip_looping_is_an_error(self):
        document = Document()
        document.add_pattern('p', 1)
        document.add_track('t')
        document.add_scene(0, 's')
        document.set_cell(0, 't', {'pattern': 'p', 'loop': True})
        with self.assertRaises(SongFileError) as caught:
            document.render('ableton')
        self.assertIn('every clip is set to loop', str(caught.exception))

    def test_nothing_to_render(self):
        with self.assertRaises(SongFileError):
            Document().render('ableton')


class TestDurations(unittest.TestCase):

    def test_clock(self):
        self.assertEqual(clock(0), '0:00')
        self.assertEqual(clock(65), '1:05')
        self.assertEqual(clock(Fraction(599, 2)), '5:00')
        self.assertEqual(clock(None), '--:--')

    def test_pattern(self):
        self.assertEqual(song_with_things().pattern_seconds('a'), 1)

    def test_a_note_without_a_duration_uses_the_default(self):
        document = song_with_things()
        document.add_pattern('c', 1)
        document.set_step_value('c', 'degree', 0, 1)
        self.assertEqual(document.pattern_length('c'), Fraction(1, 16))

    def test_clip_scene_and_song(self):
        document = song_with_things()
        self.assertEqual(document.clip_seconds(1, 'lead'), 2)
        self.assertEqual(document.scene_seconds(0), 2)
        self.assertEqual(document.scene_seconds(1), 2)
        self.assertEqual(document.song_seconds(), 2 + 2 + 1)

    def test_a_change_updates_the_times(self):
        document = song_with_things()
        document.set_step_value('b', 'duration', 0, 1)
        self.assertEqual(document.scene_seconds(2), 2)

    def test_a_scene_that_cannot_work_is_unknown_without_affecting_others(self):
        document = song_with_things()
        document.data['scenes'][2]['tracks']['bass']['loop'] = True
        document.changed()
        self.assertIsNone(document.scene_seconds(2))
        self.assertIn('every clip', document.scene_problem(2))
        self.assertEqual(document.scene_seconds(1), 2)
        self.assertIsNone(document.song_seconds())


class TestUses(unittest.TestCase):

    def test_pattern(self):
        uses = song_with_things().pattern_uses('b')
        self.assertIn('scene 2 (two), track lead', uses)
        self.assertIn('scene 3 (three), track bass', uses)
        self.assertEqual(song_with_things().pattern_uses('unused'), [])

    def test_rhythm_and_notes_from_count_as_uses(self):
        document = song_with_things()
        document.set_cell(0, 'bass', {'pattern': 'a', 'rhythm_from': 'unused'})
        self.assertEqual(document.pattern_uses('unused'), ['scene 1 (one), track bass'])

    def test_track_clips_are_counted_separately(self):
        self.assertEqual(song_with_things().track_clips('bass'), 2)

    def test_chain(self):
        document = song_with_things()
        self.assertEqual(document.chain_uses('named'), ['scene 1 (one), track lead'])

    def test_arp(self):
        self.assertEqual(song_with_things().generator_uses('arps', 'up'), ['chain named'])

    def test_auto_ratchet(self):
        self.assertEqual(song_with_things().generator_uses('auto_ratchets', 'rolls'), ['chain named'])

    def test_scale(self):
        self.assertEqual(song_with_things().scale_uses(DEFAULT_SCALE), ['the song', 'scene 3 (three)'])


class TestEveryStepTakesTime(unittest.TestCase):

    def test_a_new_pattern_is_rests_of_the_default_length(self):
        document = Document()
        document.data['default_length'] = '1/8'
        document.add_pattern('p', 4)
        self.assertEqual(document.pattern_length('p'), Fraction(1, 2))

    def test_added_and_inserted_steps_are_rests_of_the_default_length(self):
        document = Document()
        document.add_pattern('p', 1)
        document.set_steps('p', 3)
        document.insert_step('p', 0)
        self.assertEqual(document.data['patterns']['p']['duration'], ['1/16'] * 4)

    def test_a_pattern_with_no_duration_row_counts_the_default(self):
        document = song_with_things()
        document.data['patterns']['x'] = {'steps': 2}
        self.assertEqual(document.pattern_length('x'), Fraction(1, 8))
        document.set_steps('x', 3)
        self.assertEqual(document.pattern_length('x'), Fraction(3, 16))


class TestRenaming(unittest.TestCase):

    def test_pattern_updates_everything(self):
        document = song_with_things()
        document.rename_pattern('b', 'new')
        self.assertEqual(list(document.data['patterns']), ['a', 'new', 'unused'])
        self.assertEqual(document.cell(1, 'lead')['morph_to'], 'new')
        self.assertEqual(document.cell(2, 'bass')['pattern'], 'new')
        SongBuilder(document.data).build()

    def test_pattern_updates_rhythm_from(self):
        document = song_with_things()
        document.set_cell(0, 'bass', {'pattern': 'a', 'rhythm_from': 'unused'})
        document.rename_pattern('unused', 'new')
        self.assertEqual(document.cell(0, 'bass'), {'pattern': 'a', 'rhythm_from': 'new'})

    def test_renaming_or_deleting_a_track_updates_grabs_from_it(self):
        document = song_with_things()
        document.set_cell(0, 'bass', {'pattern': 'a', 'grab_track': 'lead'})
        document.rename_track('lead', 'top')
        self.assertEqual(document.cell(0, 'bass')['grab_track'], 'top')
        self.assertEqual(document.grabbers('top'), ['scene 1 (one), track bass'])
        document.delete_track('top')
        self.assertEqual(document.cell(0, 'bass'), {'pattern': 'a'})

    def test_finding_a_grab_circle(self):
        document = song_with_things()
        document.set_cell(0, 'bass', {'pattern': 'a', 'grab_track': 'lead'})
        self.assertEqual(document.grab_circle(0, 'lead', 'bass'), ['lead', 'bass', 'lead'])
        self.assertIsNone(document.grab_circle(0, 'bass', 'lead'))

    def test_track_updates_everything(self):
        document = song_with_things()
        document.rename_track('lead', 'new')
        self.assertEqual(list(document.data['tracks']), ['new', 'bass'])
        SongBuilder(document.data).build()

    def test_chain_updates_everything(self):
        document = song_with_things()
        document.rename_chain('named', 'other')
        self.assertEqual(document.cell(0, 'lead')['chain'], 'other')

    def test_arp_updates_chains(self):
        document = song_with_things()
        document.rename_generator('arps', 'up', 'new')
        self.assertEqual(document.data['chains']['named'], [{'arp': 'new'}, {'auto_ratchet': 'rolls'}])

    def test_auto_ratchet_updates_chains(self):
        document = song_with_things()
        document.rename_generator('auto_ratchets', 'rolls', 'new')
        self.assertEqual(document.data['chains']['named'], [{'arp': 'up'}, {'auto_ratchet': 'new'}])

    def test_changing_a_scale_keeps_its_name(self):
        document = song_with_things()
        document.change_scale(DEFAULT_SCALE, 'D', 'minor')
        self.assertEqual(document.data['scale'], DEFAULT_SCALE)
        self.assertEqual(document.scale_notes_text(DEFAULT_SCALE), 'D minor')
        SongBuilder(document.data).build()

    def test_renaming_a_scale_updates_everything(self):
        document = song_with_things()
        document.rename_scale(DEFAULT_SCALE, 'main')
        self.assertEqual(document.data['scale'], 'main')
        self.assertEqual(document.data['scenes'][2]['scale'], 'main')
        self.assertEqual(list(document.data['scales']), ['main'])
        SongBuilder(document.data).build()

    def test_a_scale_can_be_copied_with_the_same_notes(self):
        document = song_with_things()
        self.assertEqual(document.copy_scale(DEFAULT_SCALE), 'C Major copy')
        self.assertEqual(document.scale_notes_text('C Major copy'), 'C major')


class TestLists(unittest.TestCase):

    def test_moving_and_sorting(self):
        document = song_with_things()
        self.assertTrue(document.move_named('patterns', 0, 1))
        self.assertEqual(list(document.data['patterns']), ['b', 'a', 'unused'])
        self.assertFalse(document.move_named('patterns', 0, -1))
        document.sort_named('patterns')
        self.assertEqual(list(document.data['patterns']), ['a', 'b', 'unused'])

    def test_copying_makes_separate_data(self):
        document = song_with_things()
        new = document.copy_pattern('a')
        self.assertEqual(new, 'a copy')
        document.set_step_value(new, 'degree', 0, 7)
        self.assertEqual(document.step_value('a', 'degree', 0), 1)
        self.assertEqual(document.copy_pattern('a'), 'a copy 2')

    def test_copying_a_track_copies_its_clips(self):
        document = song_with_things()
        document.copy_track('bass')
        self.assertEqual(list(document.data['tracks']), ['lead', 'bass', 'bass copy'])
        self.assertEqual(document.cell(2, 'bass copy'), {'pattern': 'b'})

    def test_unique_name(self):
        self.assertEqual(unique_name('a', ['b']), 'a')
        self.assertEqual(unique_name('a', ['a', 'a 2']), 'a 3')


class TestScenes(unittest.TestCase):

    def setUp(self):
        self.document = song_with_things()

    def names(self):
        return [scene['name'] for scene in self.document.data['scenes']]

    def test_moving_a_scene(self):
        self.document.move_scene(0, 1)
        self.assertEqual(self.names(), ['two', 'one', 'three'])

    def test_deleting_a_scene(self):
        self.document.delete_scene(1)
        self.assertEqual(self.names(), ['one', 'three'])

    def test_adding_a_scene(self):
        self.document.add_scene(0, 'new')
        self.assertEqual(self.names(), ['new', 'one', 'two', 'three'])

    def test_copying_a_scene(self):
        self.document.copy_scene(1)
        self.assertEqual(self.names(), ['one', 'two', 'two copy', 'three'])

    def test_repeats(self):
        self.document.set_scene_repeat(1, 3)
        self.assertEqual(self.document.data['scenes'][1]['repeat'], 3)
        self.document.set_scene_repeat(0, 1)
        self.assertNotIn('repeat', self.document.data['scenes'][0])

    def test_the_result_still_builds(self):
        self.document.move_scene(0, 1)
        self.document.copy_scene(0)
        self.document.delete_scene(1)
        self.document.set_scene_repeat(0, 4)
        SongBuilder(self.document.data).build()


class TestPatternSteps(unittest.TestCase):

    def test_shortening_counts_what_would_be_lost(self):
        document = song_with_things()
        self.assertEqual(document.steps_with_anything_past('a', 1), 1)
        self.assertEqual(document.steps_with_anything_past('a', 2), 0)

    def test_a_rest_of_the_default_length_is_not_something_to_lose(self):
        document = song_with_things()
        document.set_steps('a', 4)
        self.assertEqual(document.steps_with_anything_past('a', 2), 0)
        document.set_step_value('a', 'duration', 3, '1/2')
        self.assertEqual(document.steps_with_anything_past('a', 2), 1)

    def test_setting_steps_keeps_rows_the_right_length(self):
        document = song_with_things()
        document.set_steps('a', 4)
        self.assertEqual(document.data['patterns']['a']['degree'], [1, 3, None, None])
        self.assertEqual(document.data['patterns']['a']['duration'], ['1/4', '1/4', '1/16', '1/16'])
        document.set_steps('a', 1)
        self.assertEqual(document.data['patterns']['a']['duration'], ['1/4'])

    def test_insert_and_remove(self):
        document = song_with_things()
        document.insert_step('a', 1)
        self.assertEqual(document.data['patterns']['a']['degree'], [1, None, 3])
        self.assertEqual(document.data['patterns']['a']['steps'], 3)
        document.remove_step('a', 0)
        self.assertEqual(document.data['patterns']['a']['degree'], [None, 3])

    def test_changing_type_clears_notes_and_keeps_timing(self):
        document = song_with_things()
        document.set_step_value('a', 'chord', 0, 'M')
        document.set_drum('a', True)
        pattern = document.data['patterns']['a']
        self.assertTrue(pattern['drum'])
        self.assertNotIn('degree', pattern)
        self.assertNotIn('chord', pattern)
        self.assertEqual(pattern['duration'], ['1/4', '1/4'])
        SongBuilder(document.data)

    def test_forward_is_not_written(self):
        document = song_with_things()
        document.set_direction('a', 'pendulum')
        self.assertEqual(document.data['patterns']['a']['direction'], 'pendulum')
        document.set_direction('a', 'forward')
        self.assertNotIn('direction', document.data['patterns']['a'])

    def test_flip_and_swap_move_every_row(self):
        document = song_with_things()
        document.data['patterns']['x'] = {'steps': 4, 'degree': [1, 2, 3, 4], 'velocity': [10, None, 30, 40]}
        document.flip_after('x', 0)
        self.assertEqual(document.data['patterns']['x']['degree'], [1, 4, 3, 2])
        self.assertEqual(document.data['patterns']['x']['velocity'], [10, 40, 30, None])
        self.assertEqual(document.swap_around('x', 1), 2)
        self.assertEqual(document.data['patterns']['x']['degree'], [3, 2, 4, 1])
        self.assertTrue(document.dirty)

    def test_load_over_copies_everything_and_stays_separate(self):
        document = song_with_things()
        document.load_over('unused', 'a')
        self.assertEqual(document.data['patterns']['unused'], document.data['patterns']['a'])
        document.set_step_value('unused', 'degree', 0, 7)
        self.assertEqual(document.step_value('a', 'degree', 0), 1)

    def test_degree_limit_uses_the_biggest_scale_this_pattern_can_play_in(self):
        document = song_with_things()
        self.assertEqual(document.degree_limit('unused'), 7)
        document.data['scale'] = None
        self.assertEqual(document.degree_limit('unused'), 7)
        document.data['scales']['all'] = {'root': 'C', 'type': 'chromatic'}
        document.data['scenes'][0]['scale'] = 'all'
        self.assertEqual(document.degree_limit('a'), 12)
        self.assertEqual(document.degree_limit('unused'), 7)

    def test_note_names(self):
        document = song_with_things()
        document.data['scale'] = 'main'
        document.data['scales']['main'] = {'root': 'F', 'type': 'major'}
        document.set_step_value('a', 'octave', 0, 2)
        self.assertEqual(document.note_name('a', 0), 'F2')
        self.assertEqual(document.note_name('a', 1), 'A3')
        document.set_step_value('a', 'accidental', 1, 'b')
        self.assertEqual(document.note_name('a', 1), 'G#3')

    def test_note_name_past_the_top_of_the_scale_wraps_up(self):
        document = song_with_things()
        document.set_step_value('a', 'degree', 0, 8)
        self.assertEqual(document.note_name('a', 0), 'C4')

    def test_note_name_for_a_drum(self):
        document = song_with_things()
        document.add_pattern('d', 1)
        document.set_drum('d', True)
        document.set_step_value('d', 'degree', 0, 'F')
        document.set_step_value('d', 'accidental', 0, '#')
        self.assertEqual(document.note_name('d', 0), 'F#1')

    def test_note_name_without_a_scale(self):
        document = song_with_things()
        document.data['scale'] = None
        self.assertIsNone(document.note_name('a', 0))



class TestPickerLayouts(unittest.TestCase):
    """Every chord, scale and root has exactly one place in its picker."""

    def test_chord_groups_hold_every_chord_in_order(self):
        from llamatron.song_file import CHORD_SYMBOLS
        from llamatron.tui.pattern_editor import CHORD_GROUPS, CHORD_NAMES
        flat = [symbol for _, symbols in CHORD_GROUPS for symbol in symbols]
        self.assertEqual(flat, CHORD_SYMBOLS)
        self.assertEqual(set(CHORD_NAMES), set(CHORD_SYMBOLS))

    def test_scale_pages_hold_every_kind_once_except_melodic_minor(self):
        from llamatron.tui.document import SCALE_KINDS
        from llamatron.tui.pages import SCALE_PAGES
        flat = [kind for _, columns in SCALE_PAGES for groups in columns for _, kinds in groups for kind in kinds]
        flat.remove('melodic_minor')
        self.assertEqual(sorted(flat), sorted(SCALE_KINDS))

    def test_a_paged_grid_opens_on_the_page_of_the_current_option(self):
        from llamatron.tui.base import GridChoiceDialog
        dialog = GridChoiceDialog('Pick', ['a', 'b', 'c'], None, 2, pages=[('ONE', [[0, 1]]), ('TWO', [[1, 2]])])
        self.assertEqual(dialog.page, 1)
        self.assertEqual(dialog.where(), (0, 1))
        self.assertEqual(GridChoiceDialog('Pick', ['a', 'b', 'c'], None, 1, pages=[('ONE', [[0, 1]]), ('TWO', [[1, 2]])]).page, 0)

    def test_the_keyboard_holds_every_root_once(self):
        from llamatron.tui.document import ROOTS
        from llamatron.tui.pages import ROOT_KEYBOARD
        flat = [name for row in ROOT_KEYBOARD for name in row if name]
        self.assertEqual(sorted(flat), sorted(ROOTS))

    def test_scale_notes(self):
        from llamatron.tui.pages import scale_label, scale_notes
        self.assertEqual(scale_notes('D', 'dorian'), 'D E F G A B C')
        self.assertEqual(scale_notes('A', 'minor_pentatonic'), 'A C D E G')
        self.assertEqual(scale_label('whole_half_diminished'), 'whole half dim')
        self.assertEqual(scale_label('bebop_dominant'), 'bebop dom')
        self.assertEqual(scale_label('natural_minor'), 'natural minor')

if __name__ == '__main__':
    unittest.main()
