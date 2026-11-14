#!/usr/bin/env python3
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

"""Report how tightly real-time playback keeps time, and how long the stage before it takes, against a song's export.

Run from the top folder:

    .venv/bin/python internal_tools/realtime_report.py                                  # the Entertainer, whole, through the Realtime Sender Process
    .venv/bin/python internal_tools/realtime_report.py examples/by_genre/electronic/minimal_techno.yml --seconds 30
    internal_tools/realtime_report.sh                                                       # the same as the first

The report has two parts. The first plays the song's timeline through the real Realtime Sender Process into
recording outputs, which write down the clock as each message is handed over, and compares each event's scheduled
second with the second it went out: the mean, the 99th percentile and the worst, and how many events were more than
half a millisecond, one and five off. test/test_realtime.py proves the timeline holds the MIDI export's events tick
for tick, so this is the skew between real time and the export. It takes as long as the song, so it is not part of
the suite. The second part times the stage before the process on test/sample_sets/heavy_chain.yml, a chain of twenty
generators with grabs and chords: how long rendering and building the timeline take against the length of one pass,
since an edit while playing has to be rendered before the passes already queued run out.
"""

import argparse
import statistics
import sys
import time

from llamatron.composition.setlist import Setlist
from llamatron.playback.song_renderer import SongRenderer
from llamatron.realtime.sender_process import RealtimeMIDISenderProcess
from llamatron.realtime.timeline import Route, seconds_per_whole, song_timeline

DEFAULT_SONG = 'examples/by_genre/ragtime/entertainer.yml'
HEAVY_SET = 'test/sample_sets/heavy_chain.yml'
PORT = 'report'
SEED = 1
SETTLE_SECONDS = 0.5
MILLISECONDS = 1000
THRESHOLDS_MS = (0.5, 1, 5)
PERCENTILE = 99
PERCENTILES = 100
TIGHT_MS = 0.5

HEADING = 'played {count} events of {path} over {seconds:.1f} s through the Realtime Sender Process'
SKEW = '  skew from the export: mean {mean:.3f} ms, {percentile}th percentile {high:.3f} ms, worst {worst:.3f} ms'
OVER = '  events more than {threshold} ms off: {count} ({share:.1f}%)'
VERDICT_TIGHT = '  verdict: tight, nothing over {threshold} ms'
VERDICT_LOOSE = '  verdict: {count} events over {threshold} ms, the worst {worst:.3f} ms'
MISSING = '  only {received} of {count} events were sent'
HEAVY_HEADING = 'the stage before the process, on {path}:'
HEAVY_LINE = '  render {render:.0f} ms, timeline {timeline:.0f} ms, {events} events; a pass lasts {pass_seconds:.2f} s, so the stage takes {share:.0f}% of a pass'


def first_song_grid(path):
    setlist = Setlist.read_file(path)
    song = setlist.get_song(setlist.first_song_name())
    return song, SongRenderer(song, seed=SEED).render()


def routes_for(grid):
    """Return a route for every track, each on its own channel of the report's one port."""
    return {track.get_name(): Route(PORT, place % 16) for place, track in enumerate(grid.get_columns())}


def play_report(*, path, seconds):
    song, grid = first_song_grid(path)
    events = song_timeline(grid=grid, routes=routes_for(grid))
    if seconds is not None:
        events = [event for event in events if event.seconds < seconds]
    length = events[-1].seconds if events else 0.0
    sender = RealtimeMIDISenderProcess(ports=[PORT], recording=True)
    sender.start()
    sender.add(events)
    time.sleep(length + SETTLE_SECONDS)
    started, sent = sender.close()
    arrived = sent[PORT][:len(events)]
    print(HEADING.format(count=len(events), path=path, seconds=length))
    if len(arrived) < len(events):
        print(MISSING.format(received=len(arrived), count=len(events)))
    offsets = [abs((at - started) - event.seconds) * MILLISECONDS for event, (at, _) in zip(events, arrived)]
    if len(offsets) < 2:
        return
    high = statistics.quantiles(offsets, n=PERCENTILES)[PERCENTILE - 1]
    print(SKEW.format(mean=statistics.fmean(offsets), percentile=PERCENTILE, high=high, worst=max(offsets)))
    for threshold in THRESHOLDS_MS:
        over = sum(1 for value in offsets if value > threshold)
        print(OVER.format(threshold=threshold, count=over, share=over * 100 / len(offsets)))
    over_tight = [value for value in offsets if value > TIGHT_MS]
    if over_tight:
        print(VERDICT_LOOSE.format(count=len(over_tight), threshold=TIGHT_MS, worst=max(over_tight)))
    else:
        print(VERDICT_TIGHT.format(threshold=TIGHT_MS))


def heavy_report(path):
    setlist = Setlist.read_file(path)
    song = setlist.get_song(setlist.first_song_name())
    before = time.perf_counter()
    grid = SongRenderer(song, seed=SEED).render()
    rendered = time.perf_counter()
    events = song_timeline(grid=grid, routes=routes_for(grid))
    built = time.perf_counter()
    # A pass is the first pattern's length at the song's tempo, which is what an edit has to be rendered within.
    pattern = song.get_pattern(song.get_pattern_names()[0])
    pass_seconds = float(pattern.get_steps() * song.get_pattern_step_size(pattern)) * seconds_per_whole(song.get_tempo())
    stage = built - before
    print(HEAVY_HEADING.format(path=path))
    print(HEAVY_LINE.format(render=(rendered - before) * MILLISECONDS, timeline=(built - rendered) * MILLISECONDS, events=len(events),
                            pass_seconds=pass_seconds, share=stage * 100 / pass_seconds))


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('path', nargs='?', default=DEFAULT_SONG)
    parser.add_argument('--seconds', type=float, default=None, help='play only the first seconds of the song')
    arguments = parser.parse_args(argv)
    play_report(path=arguments.path, seconds=arguments.seconds)
    heavy_report(HEAVY_SET)
    return 0


if __name__ == '__main__':
    sys.exit(main())
