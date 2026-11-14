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

"""Play a set on Arrange with a visualizer mode over the clip area, as the demo recorder would record it, but with no video, to see and tune the visualizer.

    .venv/bin/python internal_tools/preview_visualizer.py examples/by_genre/electronic/minimal_techno.yml
    .venv/bin/python internal_tools/preview_visualizer.py my_set.yml --track-assign 1,1,2 --use-driver "My Synth"
    internal_tools/preview_visualizer.sh examples/by_genre/electronic/minimal_techno.yml

It sets the song up as internal_tools/record_demo.py does, which it borrows from: one instrument per MIDI
channel in memory on the first output port whose name holds --use-driver's text (IAC by default),
the tracks on channels by --track-assign-auto or --track-assign, and nothing written. Then it
opens the tracker straight on Arrange, with no splash, the visualizer mode showing (the first, or
the one --visualizer names, and it asks which once there are several), plays the song from the
top and quits two seconds after it ends. The DAW plays what arrives on those channels through the
speakers as ever: no audio device is needed, since nothing is recorded. The user's design of
2026-11-10 (dev_notes/IDEAS.md, "The visualizer").
"""

import argparse
import importlib.util
import os
import sys

from llamatron.realtime.outputs import output_port_names
from llamatron.tui.app import LlamatronApp
from llamatron.tui.document import Document
from llamatron.tui.launch import Launch
from llamatron.visualizers.modes import MODES, mode_options

RECORDER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'record_demo.py')
RECORDER_MODULE = 'record_demo'
SUCCESS = 0
FAILURE = 1
ASK_MODE = 'Which visualizer? Type its number:'
SETUP_SOUND = 'In the DAW, give each of those a MIDI track listening on that channel, armed with Monitor set to In, and listen as ever.'


def recorder():
    """Load internal_tools/record_demo.py as a module, for what the two tools share: asking which set, finding the port and giving the tracks their channels. internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(RECORDER_MODULE, RECORDER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ask_for_mode(*, shared):
    """Return the visualizer mode to show: the only one, or the one typed from the numbered list, or None for an answer that is none of them."""
    if len(MODES) == 1:
        return MODES[0].OPTION
    for number, mode in enumerate(MODES, start=1):
        print(shared.VIEW_LINE.format(number=number, name=mode.NAME))
    print(ASK_MODE)
    typed = input().strip()
    if not typed.isdigit() or not 1 <= int(typed) <= len(MODES):
        print(shared.NOT_A_CHOICE, file=sys.stderr)
        return None
    return MODES[int(typed) - 1].OPTION


def preview(*, path, driver, assignment, visualizer, shared):
    """Set the song up on the port, and play it on Arrange with the visualizer showing. Return the exit code."""
    port = shared.first_matching(names=output_port_names(), text=driver)
    if port is None:
        print(shared.NO_DRIVER.format(text=driver, ports=shared.CHANNEL_SEPARATOR.join(output_port_names()) or shared.NO_PORTS), file=sys.stderr)
        return FAILURE
    document = Document.load(path)
    tracks = document.song().get_track_names()
    channels = shared.auto_assignment(tracks) if assignment is None else shared.parse_assignment(text=assignment, tracks=tracks)
    print(shared.DRIVER_FOUND.format(port=port))
    shared.assign_tracks(document=document, channels=channels, port=port)
    print(SETUP_SOUND)
    LlamatronApp(document=document, launch=Launch(quit_when_finished=True, visualizer=visualizer)).run()
    return SUCCESS


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('path', help='the set to play, such as examples/learning/01_hello_world.yml')
    parser.add_argument('--use-driver', default=None, help='the MIDI output port to play through: the first whose name holds this text (IAC by default)')
    parser.add_argument('--track-assign', default=None, help='a channel for each track in the song\'s order, like 1,1,2, with - to keep a track\'s own instrument')
    parser.add_argument('--visualizer', choices=mode_options(), default=None, help='the visualizer mode to show; with none, it asks once there are several')
    arguments = parser.parse_args(argv)
    shared = recorder()
    path = arguments.path
    visualizer = arguments.visualizer or ask_for_mode(shared=shared)
    if visualizer is None:
        return FAILURE
    try:
        return preview(path=path, driver=arguments.use_driver or shared.DEFAULT_DRIVER, assignment=arguments.track_assign, visualizer=visualizer, shared=shared)
    except ValueError as error:
        print(error, file=sys.stderr)
        return FAILURE


if __name__ == '__main__':
    sys.exit(main())
