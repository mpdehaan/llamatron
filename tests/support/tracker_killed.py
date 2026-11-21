# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""Stand in for a tracker that is killed outright while it plays: start a render process with a recording Realtime Sender Process,
launch a song that plays for a while, print the render process's id, and wait to be killed.

tests/realtime/test_playback_process.py runs this in an interpreter of its own and kills it with SIGKILL, which runs nothing of
the tracker's closing, and then checks that the render process and its sender are gone (render_process.watch_lifeline).
"""

import sys
import threading

from llamatron.model.schema.file_format import ClipSlotSetting, Section
from llamatron.realtime import playback as playback_values
from llamatron.realtime.playback import PlayRequest, Wanted
from llamatron.realtime.playback_process import PlaybackProcess
from llamatron.realtime.timeline import Route
from tests.support import song_testing
from tests.support.rendering import setlist_from_data

PORT = 'test port'
TUNE = 'tune'
NOTES = 4
SIXTEENTH = '1/16'
# Enough passes of the tune to play on long after the test kills this interpreter.
PASSES = 400
SEED = 1
FIRST_REVISION = 1
NO_LEAD = 0.0
# How long this waits to be killed before it gives up.
WAIT_SECONDS = 60


def main():
    tune = song_testing.pat(*[[1, SIXTEENTH]] * NOTES)
    setlist = setlist_from_data(song_testing.with_parts(patterns={TUNE: tune}, scenes=[{Section.TRACKS: {
        song_testing.LEAD: {ClipSlotSetting.PATTERN: TUNE, ClipSlotSetting.REPEAT: PASSES},
    }}]))
    playback = PlaybackProcess(lead=NO_LEAD, recording=True)
    playback.take_set(setlist.kept_data())
    wanted = Wanted(FIRST_REVISION, setlist.first_song_name(), ((song_testing.LEAD, Route(PORT, 0)),), SEED)
    playback.launch(wanted=wanted, launch=PlayRequest(playback_values.LAUNCH_SCENE, 0), ports=[PORT])
    print(playback.get_process_id(), flush=True)
    threading.Event().wait(WAIT_SECONDS)
    sys.exit(1)


if __name__ == '__main__':
    main()
