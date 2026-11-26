# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The recorder's set-up of a take: which channel each track plays on, and the instruments it gives the set's copy."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import record  # noqa: E402

PORT = 'IAC Driver Bus 1'


def two_track_set():
    """A set of one song whose bass plays a FluidSynth instrument and whose lead has none."""
    return {
        'instruments': [{'name': 'bass', 'device': '*FluidSynth', 'gm_sound': 33}],
        'songs': [{'name': 'song', 'tracks': [{'name': 'bass', 'instrument': 'bass'}, {'name': 'lead'}]}],
    }


class TestTakeSetUp(unittest.TestCase):

    def test_tracks_go_on_channels_in_order_unless_assigned(self):
        tracks = ['bass', 'lead']
        self.assertEqual(record.channels_for(assignment=None, tracks=tracks), [1, 2])
        self.assertEqual(record.channels_for(assignment='-,3', tracks=tracks), [None, 3])
        with self.assertRaises(ValueError):
            record.channels_for(assignment='1', tracks=tracks)
        with self.assertRaises(ValueError):
            record.channels_for(assignment='1,17', tracks=tracks)

    def test_a_take_gives_each_channel_a_recorder_instrument_and_keeps_the_rest(self):
        data = record.assigned(data=two_track_set(), channels=[None, 2], port=PORT)
        recorder = record.INSTRUMENT_NAME.format(channel=2)
        self.assertIn({'name': recorder, 'device': PORT, 'channel': 2}, data['instruments'])
        tracks = {track['name']: track.get('instrument') for track in data['songs'][0]['tracks']}
        self.assertEqual(tracks, {'bass': 'bass', 'lead': recorder})
        self.assertTrue(data['real_time'])

    def test_a_take_where_nothing_plays_is_refused(self):
        data = {'songs': [{'name': 'song', 'tracks': [{'name': 'lead'}]}]}
        with self.assertRaises(ValueError):
            record.assigned(data=data, channels=[None], port=PORT)


if __name__ == '__main__':
    unittest.main()
