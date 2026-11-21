# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""internal_tools/preview_midi.py, one quick check of its main path: drum tracks play on channel 10 and every other track on a channel of its own. A tool fails loudly when it is run, so one check is enough (.claude/TESTING.md)."""

import contextlib
import importlib.util
import io
import mido
import os
import pathlib
import tempfile
import unittest

from llamatron.model.objects.setlist import Setlist

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'preview_midi.py'
MODULE_NAME = 'preview_midi'
# A demo with drum tracks and others, and General MIDI's drum channel counted from 0.
WITH_DRUMS = 'examples/by_genre/pop/rick_rolling.yml'
DRUM_CHANNEL = 9
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

if __name__ == '__main__':
    unittest.main()
