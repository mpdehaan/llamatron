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
"""internal_tools/preview_midi.py writes a MIDI file of each example for a plain MIDI player: drum tracks on channel 10, every other track on a channel of its own."""

import contextlib
import importlib.util
import io
import os
import pathlib
import tempfile
import unittest

import mido

from llamatron.composition.setlist import Setlist

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / 'internal_tools' / 'preview_midi.py'
MODULE_NAME = 'preview_midi'
# A demo with drum tracks and others, and General MIDI's drum channel counted from 0.
WITH_DRUMS = 'examples/by_genre/pop/rick_rolling.yml'
DRUM_CHANNEL = 9
# Another name for the set that WITH_DRUMS holds, so that its song's name differs from the set's.
RENAMED_SET = 'another_name.yml'
# A piece whose one song's name has a space where the set's file name has an underscore.
SONG_WITH_A_SPACE = 'examples/by_genre/electronic/minimal_techno.yml'
SPACE = ' '
UNDERSCORE = '_'
PROGRAM_CHANGE = 'program_change'


def load_script():
    """Load the tool as a module, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPreviewMidi(unittest.TestCase):

    def test_drum_tracks_play_on_channel_10_and_every_other_track_on_a_channel_of_its_own(self):
        tool = load_script()
        song = Setlist.read_file(WITH_DRUMS).get_songs()[0]
        drums = {name for name in song.get_track_names() if song.get_track(name).is_drum()}
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(tool.main(argv=[WITH_DRUMS, '--out', folder]), 0)
            review = pathlib.Path(folder, tool.REVIEW_FILE).read_text()
            written = [os.path.join(folder, name) for name in os.listdir(folder) if name != tool.REVIEW_FILE]
            self.assertEqual(len(written), 1)
            channels = {track.name: {message.channel for message in track if hasattr(message, 'channel')} for track in mido.MidiFile(written[0]).tracks}
            programs = {track.name: [message.program for message in track if message.type == PROGRAM_CHANGE] for track in mido.MidiFile(written[0]).tracks}
        # The review table names the set with what it plays.
        self.assertIn(Setlist.read_file(WITH_DRUMS).get_description(), review)
        melodic = []
        for name in song.get_track_names():
            if name in drums:
                self.assertEqual(channels[name], {DRUM_CHANNEL})
            elif channels.get(name):
                melodic += list(channels[name])
        self.assertNotIn(DRUM_CHANNEL, melodic)
        self.assertEqual(len(melodic), len(set(melodic)))
        # Each melodic track starts with its instrument's General MIDI sound.
        self.assertTrue(all(programs[name] for name in song.get_track_names() if name not in drums and channels.get(name)))

    def test_a_preview_is_named_after_the_set_alone_when_the_song_has_the_set_name(self):
        tool = load_script()
        stem = pathlib.Path(WITH_DRUMS).stem
        self.assertEqual(Setlist.read_file(WITH_DRUMS).get_song_names(), [stem])
        with tempfile.TemporaryDirectory() as folder:
            written = tool.preview(path=WITH_DRUMS, folder=folder)
            self.assertEqual(written, [os.path.join(folder, tool.PREVIEW_FILE.format(name=stem))])

    def test_a_space_in_the_song_name_counts_as_the_underscore_in_the_set_name(self):
        tool = load_script()
        stem = pathlib.Path(SONG_WITH_A_SPACE).stem
        song = Setlist.read_file(SONG_WITH_A_SPACE).get_song_names()[0]
        self.assertIn(SPACE, song)
        self.assertEqual(song.replace(SPACE, UNDERSCORE), stem)
        self.assertEqual(tool.preview_name(stem=stem, song=song), stem)

    def test_a_song_name_that_differs_from_the_set_name_has_no_spaces_in_the_file_name(self):
        tool = load_script()
        song = Setlist.read_file(SONG_WITH_A_SPACE).get_song_names()[0]
        named = tool.preview_name(stem=pathlib.Path(RENAMED_SET).stem, song=song)
        self.assertEqual(named, tool.NAME_JOIN.format(set=pathlib.Path(RENAMED_SET).stem, song=song.replace(SPACE, UNDERSCORE)))
        self.assertNotIn(SPACE, named)

    def test_a_preview_is_named_after_the_set_and_the_song_when_their_names_differ(self):
        tool = load_script()
        song = Setlist.read_file(WITH_DRUMS).get_song_names()[0]
        with tempfile.TemporaryDirectory() as folder:
            renamed = os.path.join(folder, RENAMED_SET)
            pathlib.Path(renamed).write_text(pathlib.Path(WITH_DRUMS).read_text())
            written = tool.preview(path=renamed, folder=folder)
            named = tool.NAME_JOIN.format(set=pathlib.Path(RENAMED_SET).stem, song=song)
            self.assertEqual(written, [os.path.join(folder, tool.PREVIEW_FILE.format(name=named))])


if __name__ == '__main__':
    unittest.main()
