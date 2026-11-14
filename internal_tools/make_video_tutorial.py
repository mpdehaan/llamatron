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

"""Run a video tutorial: the tracker builds a demo set from a new set, key by key, as a person would, and plays it at the end.

Run from the top folder, in the terminal window the video should show:

    .venv/bin/python internal_tools/make_video_tutorial.py examples/learning/01_hello_world.yml     # builds that set
    .venv/bin/python internal_tools/make_video_tutorial.py my_set.yml --pace 0.2             # faster keys
    .venv/bin/python internal_tools/make_video_tutorial.py my_set.yml --no-play              # builds and quits without instruments
    .venv/bin/python internal_tools/make_video_tutorial.py my_set.yml --save-set-yaml built.yml   # keeps what was built, for debugging
    .venv/bin/python internal_tools/make_video_tutorial.py my_set.yml --no-video             # runs in the terminal without recording
    internal_tools/tutorial.sh examples/learning/01_hello_world.yml                                # the same as the second

The tutorial is the user's design of 2026-11-10 (dev_notes/IDEAS.md, "A story demo"): nothing is scripted by
hand. The set named is read, and the plan (tutorial/plan.py) works out the keys that build it in the
tracker from the state of the screen as it goes, so that any demo becomes a tutorial. The tracker is
launched with the tutorial (tui/launch.py) on a new set, presses one key every --pace seconds, says a
sentence at each part worth one in the caption strip at the foot of the screen, printed again after the tracker
quits, and at the end adds an instrument per track on the MIDI port --use-driver names (IAC by
default, the Mac's bus from one program to another), one channel each, turns Real Time on and plays
the song on Arrange, and once the song has ended quits the tracker through its Quit cell without
saving. Before the build it says which track
will play on which channel and what to set up in the DAW, and then, with or without --no-play,
waits for Enter after its last line, "Ready? Press Enter to Start - DO NOT MOVE YOUR MOUSE
CURSOR", unless --go. Keep
your hands off the keyboard while it runs: a key of yours would land in the tracker among the plan's.
Nothing is saved: the set built is thrown away with the tracker, unless --save-set-yaml names a file
to write it to for debugging.

The tutorial is recorded as a video, recordings/<set>_tutorial.mov, a second take writing over the
first, unless --no-video: the screen's own recording of the terminal window this is run from, so
size the window first (16 by 9 is what video sites expect), with the sound from the loopback audio
device --audio-device names (BlackHole by default) when it plays, as internal_tools/record_demo.py records,
and with no sound under --no-play. The tracker opens on the splash, as it does for the recorder.
The recording is started under a pseudo-terminal of its own, where screencapture stops and writes
its file when a character is typed, which a signal would leave unwritten, so the video ends the
moment the tracker quits. screencapture is given no time limit, since with one it ignores the
character; --max-seconds, an hour unless told otherwise, quits the tracker instead, which ends the
recording. A
song with a scene whose every clip loops is refused, since the tutorial waits for the song to end.
"""

import argparse
import importlib.util
import os
import pty
import subprocess
import sys

from llamatron.composition.setlist import file_stem, Setlist
from llamatron.realtime.outputs import output_port_names
from llamatron.tui.app import LlamatronApp
from llamatron.tui.document import Document
from llamatron.tui.launch import Launch, recording_problem
from llamatron.tutorial.subtitles import subtitles
from llamatron.tutorial.runner import HUMAN_PACE, tutorial

RECORDER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'record_demo.py')
RECORDER_MODULE = 'record_demo'
DEFAULT_DRIVER = 'IAC'
DEFAULT_AUDIO_DEVICE = 'BlackHole'
RECORDINGS = 'recordings'
VIDEO_NAME = '{stem}_tutorial.mov'
# The captions as a SubRip file beside the video, for YouTube, the user's design.
SUBTITLES_NAME = '{stem}_tutorial.srt'
FILE_ENCODING = 'utf-8'
DEFAULT_MAX_SECONDS = 60 * 60
WINDOW_FLAG = '-l'
REGION_FLAG = '-R'
SCREENCAPTURE = 'screencapture'
CAPTURE_FLAGS = ['-x', '-v']
# What stops a recording when typed into its terminal, and how long it may take to write the file after.
STOP_KEY = b'q'
STOP_TIMEOUT_SECONDS = 60
SUCCESS = 0
FAILURE = 1

NO_DRIVER = 'no MIDI output port has ({text}) in its name; the ports are: {ports}'
NO_PORTS = '(none)'
PORT_SEPARATOR = ', '
DRIVER_FOUND = 'MIDI goes out of ({port})'
BUILDING = 'building {path} from a new set, one key every {pace} s'
REPORT_HEADING = 'what the tutorial said and did:'
STOPPED = 'the tutorial stopped: {problem}'
SAVED = 'saved what was built to {path}'
SUBTITLES_WRITTEN = 'wrote the captions for YouTube to {path}'
LINE = '  {text}'
RECORDING_TO = 'recording window {window} into {path}'
NOT_WRITTEN = 'no video was written: screencapture ended with {code}, or did not stop when told to and was ended'
SILENT_VIDEO = 'the video has no sound, since nothing plays with --no-play'


class ScreenRecording:
    """screencapture recording a window into a file, started under a pseudo-terminal of its own, since screencapture stops and writes its file when a character is typed there and writes nothing when it is signalled."""

    __slots__ = ('process', 'terminal')

    def __init__(self, *, path, window, audio_device, region=None):
        """audio_device is the id of the audio input device to record the sound from, or None for a silent video; region is a rectangle of the screen, as screencapture -R takes it, to record in place of the window."""
        self.terminal, own_end = pty.openpty()
        sound = [] if audio_device is None else ['-G', audio_device]
        # No -V: with a time limit screencapture neither prompts nor stops for a character (found on 2026-11-10, when a take hung), so --max-seconds quits the tracker instead.
        where = [REGION_FLAG, region] if region is not None else [WINDOW_FLAG, str(window)]
        command = [SCREENCAPTURE, *CAPTURE_FLAGS, *where, *sound, path]
        self.process = subprocess.Popen(command, stdin=own_end, stdout=own_end, stderr=own_end, close_fds=True)
        os.close(own_end)

    def stop(self):
        """Type the character that ends the recording, wait for the file to be written, and return screencapture's exit code, or None when it didn't stop and had to be ended, which leaves no file."""
        if self.process.poll() is None:
            os.write(self.terminal, STOP_KEY)
        try:
            code = self.process.wait(timeout=STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
            code = None
        os.close(self.terminal)
        return code


def subtitles_path(path):
    """Return where the captions of the tutorial of the set at path are written, as a SubRip file beside the video."""
    return os.path.join(RECORDINGS, SUBTITLES_NAME.format(stem=file_stem(path)))


def video_path(path):
    """Return where the video of the tutorial of the set at path is written."""
    return os.path.join(RECORDINGS, VIDEO_NAME.format(stem=file_stem(path)))


def sound_device(*, tools, text):
    """Return the id of the first audio input device whose name holds the text, or print why there is none and return None."""
    devices = tools.audio_devices()
    if devices is None:
        print(tools.NO_SWIFT, file=sys.stderr)
        return None
    for device_id, name in devices:
        if text.lower() in name.lower():
            return device_id
    print(tools.NO_AUDIO_DEVICE.format(text=text, devices=PORT_SEPARATOR.join(name for _, name in devices) or NO_PORTS), file=sys.stderr)
    return None


def recorder():
    """Load internal_tools/record_demo.py as a module, for what the two tools share: asking which set, and explaining the setup before a take. internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(RECORDER_MODULE, RECORDER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def channel_plays(target):
    """Return each track of the target's first song with the channel the tutorial gives it, counted from 1 in track order, as the plan does."""
    song = target.get_song(target.get_song_names()[0])
    return [(track, number + 1) for number, track in enumerate(song.get_track_names())]


def run(*, path, driver, audio_device, pace, play, save_to, go, video=True, window_id=None, max_seconds=DEFAULT_MAX_SECONDS, recording=ScreenRecording):
    """Run the tutorial on the set at path, recording it unless video is False, and print its report. Return the exit code. recording starts a screen recording, which the tests replace."""
    tools = recorder()
    target = Setlist.read_file(path)
    port = None
    if play:
        problem = recording_problem(target.get_song(target.get_song_names()[0]))
        if problem is not None:
            print(problem, file=sys.stderr)
            return FAILURE
        port = tools.first_matching(names=output_port_names(), text=driver)
        if port is None:
            print(NO_DRIVER.format(text=driver, ports=PORT_SEPARATOR.join(output_port_names()) or NO_PORTS), file=sys.stderr)
            return FAILURE
        print(DRIVER_FOUND.format(port=port))
    if video:
        window = window_id if window_id is not None else tools.terminal_window_id()
        if window is None:
            print(tools.NO_WINDOW, file=sys.stderr)
            return FAILURE
        device = None
        if play:
            device = sound_device(tools=tools, text=audio_device)
            if device is None:
                return FAILURE
        else:
            print(SILENT_VIDEO)
    if play:
        tools.explain_setup(plays=channel_plays(target), port=port, device=audio_device)
    print(BUILDING.format(path=path, pace=pace))
    if video:
        print(RECORDING_TO.format(window=window, path=video_path(path)))
    tools.wait_for_go(go=go)
    launch = Launch(driven_by=tutorial(target=target, port=port, pace=pace), quit_when_finished=True, for_recording=video, max_seconds=max_seconds if video else None)
    app = LlamatronApp(document=Document(setlist=Setlist.new(), path=None), launch=launch)
    capture = None
    if video:
        os.makedirs(RECORDINGS, exist_ok=True)
        if os.path.exists(video_path(path)):
            os.unlink(video_path(path))
        capture = recording(path=video_path(path), window=window, audio_device=device)
    try:
        app.run()
    finally:
        code = None if capture is None else capture.stop()
    print(REPORT_HEADING)
    for line in app.driven.report():
        print(LINE.format(text=line))
    if save_to is not None:
        app.get_document().setlist().write_file(save_to)
        print(SAVED.format(path=save_to))
    if capture is not None:
        if code != SUCCESS or not os.path.exists(video_path(path)):
            print(NOT_WRITTEN.format(code=code), file=sys.stderr)
            return FAILURE
        print(tools.WRITTEN.format(path=video_path(path), size=os.path.getsize(video_path(path)) / tools.MEGABYTE))
        driven = app.driven
        with open(subtitles_path(path), 'w', encoding=FILE_ENCODING) as handle:
            handle.write(subtitles(said=driven.narrator.said, ended=driven.ended_at - driven.started_at, offset=launch.splash_seconds))
        print(SUBTITLES_WRITTEN.format(path=subtitles_path(path)))
    if app.driven.problem is not None:
        print(STOPPED.format(problem=app.driven.problem), file=sys.stderr)
        return FAILURE
    return SUCCESS


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('path', help='the set to build, such as examples/learning/01_hello_world.yml')
    parser.add_argument('--use-driver', default=DEFAULT_DRIVER, help='text in the name of the MIDI output port to play through at the end (default IAC)')
    parser.add_argument('--audio-device', default=DEFAULT_AUDIO_DEVICE, help='the loopback audio device to name in the setup instructions (default BlackHole)')
    parser.add_argument('--pace', type=float, default=HUMAN_PACE, help='seconds between two keys (default %(default)s)')
    parser.add_argument('--no-play', dest='play', action='store_false', help='build the set and quit, with no instruments and no MIDI port needed')
    parser.add_argument('--save-set-yaml', default=None, metavar='FILE', help='write the set the tutorial built to this file, for debugging')
    parser.add_argument('--go', action='store_true', help='start at once, without waiting for Enter after the setup is explained')
    parser.add_argument('--no-video', dest='video', action='store_false', help='run in the terminal without recording a video')
    parser.add_argument('--window-id', type=int, default=None, help='the id of the window to record, when the terminal program cannot be asked')
    parser.add_argument('--max-seconds', type=float, default=DEFAULT_MAX_SECONDS, help='the longest the tracker runs while recording, which ends the recording (default an hour)')
    arguments = parser.parse_args(argv)
    path = arguments.path
    return run(path=path, driver=arguments.use_driver, audio_device=arguments.audio_device, pace=arguments.pace, play=arguments.play,
               save_to=arguments.save_set_yaml, go=arguments.go, video=arguments.video, window_id=arguments.window_id, max_seconds=arguments.max_seconds)


if __name__ == '__main__':
    sys.exit(main())
