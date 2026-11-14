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

"""Record a video of the tracker playing a set on Arrange, with the sound the synths make, for a demo video.

Run from the top folder, in the terminal window the video should show, sized the way the video should look:

    .venv/bin/python internal_tools/record_demo.py examples/arp_demo.yml                 # records that set
    .venv/bin/python internal_tools/record_demo.py my_set.yml --track-assign 1,1,2       # the first two tracks on channel 1, the third on 2
    .venv/bin/python internal_tools/record_demo.py my_set.yml --use-driver "My Synth" --max-seconds 60
    .venv/bin/python internal_tools/record_demo.py my_set.yml --visualizer lava_lamp     # the lava lamp over the clip area instead of the clips
    .venv/bin/python internal_tools/record_demo.py --fluidsynth                          # FluidSynth plays the set's own instruments, with no DAW
    .venv/bin/python internal_tools/record_demo.py --interactive                         # you start the song, perform, and stop it from the corner to end the take
    sh user_scripts/record.sh examples/learning/01_hello_world.yml                                    # the same as the first
    sh user_scripts/record.sh --sound fluidsynth examples/learning/01_hello_world.yml                             # the same as --fluidsynth

With --fluidsynth no MIDI port and no DAW are used: the set keeps its own instruments, and those whose
Device is *FluidSynth, as every example's are, play through FluidSynth, which the tracker starts with
its sound sent (LLAMATRON_FLUIDSYNTH_AUDIO_DEVICE, which only the recorder sets) to a Multi-Output
Device when FluidSynth lists one, which reaches the recorded device and the speakers at once, so the
take is heard as it records, else to the audio device recorded, or to --fluidsynth-output when given.

docs/RECORDING.md says how to set the Mac and the DAW up for it. The recorder works on a Mac alone,
with the system's own screencapture, and touches no file but the video: the set is read, given the
recorder's instruments in memory, and played by the tracker launched for recording (tui/launch.py),
which opens on the splash, plays the song from the top on Arrange with no save mark in its header,
and quits when the song ends. After the set it asks whether the take shows the clips or a
visualizer mode over the clip area, unless --clips or --visualizer says. The instruments are one per MIDI channel used, RECORDER 1, RECORDER 2
and so on, on the first MIDI output port whose name holds the text --use-driver gives, IAC by default,
the Mac's own bus from one program to another; --track-assign-auto, the default, puts the first track
on channel 1, the second on 2 and so on, and --track-assign 1,1,2 names a channel for each track in
the song's order. The DAW listens on those channels and plays the sound, which comes back into the
recording through a loopback audio device, BlackHole unless --audio-device names another, that the
DAW's output is also sent to. Without such a device the recorder stops and records nothing, so that a
silent take is never made by accident. Before the take the recorder says which track plays on which
MIDI channel of the port and what to set up in the DAW, the tracks' MIDI inputs, their Arm buttons
and the audio output device, and waits for Enter after its last line, "Ready? Press Enter to Start - DO
NOT MOVE YOUR MOUSE CURSOR", unless --go says to start at once. A scene whose
every clip loops is refused, since the song would wait there forever, and every take ends at
--max-seconds, fifteen minutes unless told otherwise. The
video is written as recordings/<set>.mov, a second take writing over the first, with the screen's own
recording of the terminal window this is run from, so size the window first: 16 by 9 is what video
sites expect.
"""

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time

from llamatron.composition.instrument import MAX_CHANNEL, MIN_CHANNEL
from llamatron.composition.setlist import file_stem
from llamatron.realtime.fluidsynth import AUDIO_DEVICE_VARIABLE, fluidsynth_path, is_installed, soundfont_path
from llamatron.realtime.outputs import output_port_names
from llamatron.tui.app import LlamatronApp
from llamatron.tui.document import Document
from llamatron.tui.batch_stage import GROW_SECONDS, READY_SECONDS
from llamatron.tui.components.title_card import whole_title_seconds
from llamatron.tui.launch import Launch, LEAD_IN_SECONDS, LEAD_OUT_SECONDS, recording_problem, SPLASH_SECONDS
from llamatron.visualizers.modes import MODES, mode_options

RECORDINGS = 'recordings'
VIDEO_SUFFIX = '.mov'
DEFAULT_DRIVER = 'IAC'
DEFAULT_AUDIO_DEVICE = 'BlackHole'
DEFAULT_MAX_SECONDS = 15 * 60
# The recorder's instruments, one per channel, named by the channel as people number it.
INSTRUMENT_NAME = 'RECORDER {channel}'
CHANNEL_SEPARATOR = ','
KEEP_OWN = '-'
# How much longer the screen recording runs than the song, so that the lead-out and the tracker's quitting are in it.
MARGIN_SECONDS = 1.0
# After the song, the tracker shows the splash again for its usual seconds and then stays on it this
# long, and this much is cut off the end of the video afterwards, so that the video ends on the splash
# and never shows the terminal it quits back to (the user's fix of 2026-11-11).
HOLD_SECONDS = 5.0
TRIMMED_SECONDS = 4.0
# The start of a take, the user's design: once the screen recording has begun, the terminal shows black for
# SETTLE_SECONDS before the tracker starts, so that nothing of the calibration or the shell is in the video, and the
# first CUT_FROM_START seconds are cut, so that the video opens on a moment of black and then the title.
SETTLE_SECONDS = 3.0
CUT_FROM_START = 2.0
BLACK_SCREEN = '\x1b[48;2;0;0;0m\x1b[2J\x1b[H'
START_FLAG = '--start'
# The Mac's own tool that copies a span of a video, which every macOS has in /usr/bin.
AVCONVERT = 'avconvert'
TRIM_PRESET = 'PresetHighestQuality'
SOURCE_FLAG = '--source'
OUTPUT_FLAG = '--output'
PRESET_FLAG = '--preset'
DURATION_FLAG = '--duration'
REPLACE_FLAG = '--replace'
TRIMMING_SUFFIX = '.trimming.mov'
SUCCESS = 0
FAILURE = 1
# The video tutorial's screen recording, which runs with no time limit and stops when a key is typed into its own terminal, for a take whose length nobody knows.
TUTORIAL_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'make_video_tutorial.py')
TUTORIAL_MODULE = 'make_video_tutorial'
REGION_SCRIPT = 'window_region.py'
REGION_MODULE = 'window_region'
# Asking FluidSynth's own shell which audio outputs it can play to: the Options line of its device setting.
FLUIDSYNTH_DEVICE_QUESTION = 'info audio.coreaudio.device\nquit\n'
FLUIDSYNTH_PROBE = ['-a', 'coreaudio', '-g', '0', '-o', 'midi.portname=llamatron probe {pid}']
OPTIONS_LINE = 'Options:'
OPTION_SEPARATOR = ','
# A Multi-Output Device plays to BlackHole and the speakers at once, so that the person recording hears FluidSynth too.
MULTI_OUTPUT = 'Multi-Output'
PROBE_TIMEOUT_SECONDS = 30
# How the terminal window is found, by the program that owns it.
TERM_PROGRAM = 'TERM_PROGRAM'
APPLE_TERMINAL = 'Apple_Terminal'
ITERM = 'iTerm.app'
WINDOW_ID_SCRIPTS = {
    APPLE_TERMINAL: 'tell application "Terminal" to id of front window',
    ITERM: 'tell application "iTerm2" to id of current window',
}
OSASCRIPT = 'osascript'
SWIFT = 'swift'
# Swift, which every Mac with Xcode's command line tools has, lists the audio input devices with the ids screencapture takes.
AUDIO_DEVICES_SWIFT = '''
import AVFoundation
let session = AVCaptureDevice.DiscoverySession(deviceTypes: [.microphone, .external], mediaType: .audio, position: .unspecified)
for device in session.devices { print(device.uniqueID + "\\t" + device.localizedName) }
'''
SWIFT_SUFFIX = '.swift'
FIELD_SEPARATOR = '\t'
LIST_TIMEOUT_SECONDS = 120
ONE_LINE_TIMEOUT_SECONDS = 20

ASK_VIEW = 'What should the take show? Type its number:'
VIEW_LINE = '  {number:2}  {name}'
CLIPS_VIEW = 'the clips on Arrange'
NOT_A_CHOICE = 'that is not one of the numbers'
NO_DRIVER = 'no MIDI output port has ({text}) in its name; the ports are: {ports}'
NO_PORTS = '(none)'
NO_AUDIO_DEVICE = ('no audio input device has ({text}) in its name, so there is nothing to record the sound from; the devices are: {devices}. '
                   'Install BlackHole from https://existential.audio/blackhole/ and send the DAW to it, as docs/RECORDING.md says')
NO_SWIFT = 'the audio devices cannot be listed without the swift command: install Xcode\'s command line tools with xcode-select --install'
NO_WINDOW = 'the terminal window cannot be found: run this from Terminal or iTerm2, or pass --window-id with the window\'s id'
BAD_ASSIGNMENT_COUNT = '--track-assign names {given} channels, and the song has {tracks} tracks: {names}'
BAD_CHANNEL = 'a channel must be an integer from {low} to {high}, or - to keep the track\'s own instrument, got {value}'
NO_TRACK_PLAYS = 'no track has an instrument to play through: pass --track-assign-auto or --track-assign'
NO_FLUIDSYNTH = 'FluidSynth is not installed: run sh user_scripts/install_fluidsynth.sh first'
NO_FLUIDSYNTH_TRACK = 'no track plays through an instrument whose Device is *FluidSynth: choose it on the Instruments page, as every example does'
TRACK_FLUIDSYNTH = '  track ({track}) plays through FluidSynth, with its instrument ({instrument})'
SETUP_FLUIDSYNTH_HEARD = ('FluidSynth plays to ({output}), which the recording hears through ({device}) as long as that Multi-Output Device includes it, '
                          'and your speakers too, so you hear the take as it records. Pass --fluidsynth-output to choose another output.')
SETUP_FLUIDSYNTH = ('FluidSynth plays the set\'s own instruments to ({output}), and the recording hears ({device}), but your speakers don\'t. To hear the take as it records, '
                    'make a Multi-Output Device of ({device}) and your speakers in Audio MIDI Setup, which the recorder then plays to by itself, as docs/RECORDING.md says.')
SONG_LENGTH_UNKNOWN = 'the song\'s length cannot be worked out, so the recording cannot be timed'
DRIVER_FOUND = 'MIDI goes out of ({port})'
SETUP_INTRO = 'Before the take, set the DAW up for what the tracker will play:'
SETUP_TRACK = '  the track ({track}) on MIDI channel {channel} of ({port})'
SETUP_DAW = ('In Live, give each of those a MIDI track whose MIDI From is ({port}) on that channel, arm it (the Arm button, so that it plays '
             'what the tracker sends) with Monitor set to In, and set the audio output device to ({device}), so that the sound comes back into the recording.')
# The last line before a take, which nothing follows until Enter: a mouse moved during the take moves on the video.
SETUP_GO = 'Ready? Press Enter to Start - DO NOT MOVE YOUR MOUSE CURSOR'
INTERACTIVE_TAKE = ('An interactive take: after the splash, Arrange waits with the cursor on the corner at the top left. Press Space there to start the song, '
                    'perform as you like, and press Space on the corner again to stop and end the take, or Esc; the splash then shows again and the tracker quits. '
                    'The take ends by itself after {seconds:.0f} s.')
AUDIO_FOUND = 'sound is recorded from ({device})'
TRACK_LINE = '  track ({track}) plays through ({instrument}) on channel {channel}'
TRACK_KEPT = '  track ({track}) keeps its own instrument ({instrument})'
TRACK_SILENT = '  track ({track}) has no instrument and stays silent'
BATCH_TAKE = 'recording {region} for up to {seconds:.0f} s: the title, READY, the song ({song:.0f} s) with {mode} in the frame, and black'
NO_REGION = 'the terminal window\'s cells cannot be found on the screen: give the recorder Screen Recording permission, keep the window in front and unhidden, and try again'
BATCH_VIDEO = '{stem}_{mode}'
BATCH_NEEDS_MODE = 'a batch video shows a visualizer mode, not the clips: choose a mode or name one with --visualizer'
CALIBRATION_SECONDS = 0.5
TAKE = 'recording window {window} for up to {seconds:.0f} s: {splash:.0f} s of splash, {lead_in:.0f} s on Arrange, the song ({song:.0f} s), {lead_out:.0f} s to ring out'
WRITTEN = 'wrote {path} ({size:.1f} MB)'
NOT_WRITTEN = 'no video was written: screencapture ended with {code}'
NOT_TRIMMED = 'the video was left as it was, its last seconds showing the terminal: avconvert could not trim it ({reason})'
MEGABYTE = 1024 * 1024


def ask_for_view():
    """Print what a take can show, the clips or each visualizer mode, numbered, and return the mode's name on the command line, or None for the clips, or False for an answer that is none of them."""
    names = [CLIPS_VIEW, *[mode.NAME for mode in MODES]]
    for number, name in enumerate(names, start=1):
        print(VIEW_LINE.format(number=number, name=name))
    print(ASK_VIEW)
    typed = input().strip()
    if not typed.isdigit() or not 1 <= int(typed) <= len(names):
        print(NOT_A_CHOICE, file=sys.stderr)
        return False
    return None if int(typed) == 1 else MODES[int(typed) - 2].OPTION


def first_matching(*, names, text):
    """Return the first name holding the text, ignoring case, or None."""
    wanted = text.lower()
    return next((name for name in names if wanted in name.lower()), None)


def audio_devices():
    """Return (id, name) for each audio input device, as screencapture names them, or None when Swift isn't there to ask."""
    with tempfile.NamedTemporaryFile(mode='w', suffix=SWIFT_SUFFIX, delete=False) as script:
        script.write(AUDIO_DEVICES_SWIFT)
    try:
        result = subprocess.run([SWIFT, script.name], capture_output=True, text=True, timeout=LIST_TIMEOUT_SECONDS, check=False)
    except FileNotFoundError:
        return None
    finally:
        os.unlink(script.name)
    devices = []
    for line in result.stdout.splitlines():
        if FIELD_SEPARATOR in line:
            device_id, name = line.split(FIELD_SEPARATOR, 1)
            devices.append((device_id, name))
    return devices


def terminal_window_id():
    """Return the id of the terminal window this runs in, asking the terminal program, or None."""
    script = WINDOW_ID_SCRIPTS.get(os.environ.get(TERM_PROGRAM))
    if script is None:
        return None
    try:
        result = subprocess.run([OSASCRIPT, '-e', script], capture_output=True, text=True, timeout=ONE_LINE_TIMEOUT_SECONDS, check=False)
    except FileNotFoundError:
        return None
    answer = result.stdout.strip()
    return int(answer) if answer.isdigit() else None


def parse_assignment(*, text, tracks):
    """Return a channel, or None to keep the track's own instrument, for each track, from a list like 1,1,2 or 1,-,3."""
    parts = text.split(CHANNEL_SEPARATOR)
    if len(parts) != len(tracks):
        raise ValueError(BAD_ASSIGNMENT_COUNT.format(given=len(parts), tracks=len(tracks), names=CHANNEL_SEPARATOR.join(tracks)))
    channels = []
    for part in parts:
        part = part.strip()
        if part == KEEP_OWN:
            channels.append(None)
        elif part.isdigit() and MIN_CHANNEL <= int(part) <= MAX_CHANNEL:
            channels.append(int(part))
        else:
            raise ValueError(BAD_CHANNEL.format(low=MIN_CHANNEL, high=MAX_CHANNEL, value=part))
    return channels


def auto_assignment(tracks):
    """Return channel 1 for the first track, 2 for the second and so on, going round after 16."""
    count = MAX_CHANNEL - MIN_CHANNEL + 1
    return [MIN_CHANNEL + place % count for place in range(len(tracks))]


def has_a_device(*, document, track):
    """Return whether a track plays through an instrument with a device, since an example's instruments may carry only a General MIDI sound and stay silent in real time."""
    name = document.song().get_track(track).get_instrument_name()
    return name is not None and document.setlist().get_instrument(name).has_device()


def assign_tracks(*, document, channels, port):
    """Give the set one RECORDER instrument per channel used, on the port, and each track the instrument of its channel; print what each track plays through."""
    song = document.song()
    tracks = song.get_track_names()
    for channel in sorted({channel for channel in channels if channel is not None}):
        name = INSTRUMENT_NAME.format(channel=channel)
        document.add_instrument(name)
        document.set_instrument_device(name=name, device=port)
        document.set_instrument_channel(name=name, channel=channel)
    plays = 0
    for track, channel in zip(tracks, channels):
        if channel is not None:
            name = INSTRUMENT_NAME.format(channel=channel)
            document.set_track_instrument(name=track, instrument=name)
            print(TRACK_LINE.format(track=track, instrument=name, channel=channel))
            plays += 1
        elif has_a_device(document=document, track=track):
            print(TRACK_KEPT.format(track=track, instrument=song.get_track(track).get_instrument_name()))
            plays += 1
        else:
            print(TRACK_SILENT.format(track=track))
    document.set_real_time(True)
    if not plays:
        raise ValueError(NO_TRACK_PLAYS)


def fluidsynth_outputs():
    """Return the audio outputs FluidSynth can play to, by the names it takes, asked of its own shell, or nothing when it can't be asked."""
    try:
        finished = subprocess.run([fluidsynth_path(), *[word.format(pid=os.getpid()) for word in FLUIDSYNTH_PROBE], soundfont_path()],
                                  input=FLUIDSYNTH_DEVICE_QUESTION, capture_output=True, text=True, timeout=PROBE_TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    for line in finished.stdout.splitlines():
        if line.strip().startswith(OPTIONS_LINE):
            return [name.strip() for name in line.split(OPTIONS_LINE, 1)[1].split(OPTION_SEPARATOR) if name.strip()]
    return []


def output_for_fluidsynth(*, given, recorded, outputs):
    """Return the output FluidSynth plays to in a take: the one given, else a Multi-Output Device FluidSynth lists, which reaches the recording and the speakers, else the device recorded."""
    if given:
        return given
    return next((name for name in outputs if MULTI_OUTPUT.lower() in name.lower()), recorded)


def through_fluidsynth(*, document):
    """Print what each track plays through when FluidSynth plays the set's own instruments, and refuse a song where no track plays through FluidSynth."""
    song = document.song()
    setlist = document.setlist()
    through = 0
    for track in song.get_track_names():
        name = song.get_track(track).get_instrument_name()
        if name is not None and setlist.get_instrument(name).uses_fluidsynth():
            print(TRACK_FLUIDSYNTH.format(track=track, instrument=name))
            through += 1
        elif has_a_device(document=document, track=track):
            print(TRACK_KEPT.format(track=track, instrument=name))
        else:
            print(TRACK_SILENT.format(track=track))
    if not through:
        raise ValueError(NO_FLUIDSYNTH_TRACK)
    document.set_real_time(True)


def explain_setup(*, plays, port, device):
    """Print which track plays on which channel of the port, and what to set up in the DAW before the take: its MIDI inputs, the Arm buttons and the output device."""
    print(SETUP_INTRO)
    for track, channel in plays:
        print(SETUP_TRACK.format(track=track, channel=channel, port=port))
    print(SETUP_DAW.format(port=port, device=device))


def wait_for_go(*, go):
    """Wait for Enter before the take, unless --go said to start at once. The prompt is the last thing printed before the take, by the user's wish, so whoever runs it reads it."""
    if not go:
        print(SETUP_GO)
        input()


def batch_take_seconds(*, song_seconds, max_seconds):
    """Return how long a batch video's screen is recorded: the title, READY, the box growing, the song, the lead-out, the hold on black and a margin, or the limit if that is less."""
    return min(whole_title_seconds() + READY_SECONDS + GROW_SECONDS + song_seconds + LEAD_OUT_SECONDS + HOLD_SECONDS + MARGIN_SECONDS, max_seconds)


def cells_region(*, window, size=None, region=None):
    """Return the rectangle of the screen the terminal window's cells cover, found as internal_tools/window_region.py says, or None: the cells are filled with the calibration colour for a moment, a still taken, and the screen put back."""
    found = region_tools() if region is None else region
    columns, rows = shutil.get_terminal_size() if size is None else size
    bounds = found.window_bounds(window)
    if bounds is None:
        return None
    sys.stdout.write(found.calibration_text(columns=columns, rows=rows))
    sys.stdout.flush()
    time.sleep(CALIBRATION_SECONDS)
    try:
        pixels = found.window_still(window)
    finally:
        sys.stdout.write(found.restoring_text())
        sys.stdout.flush()
    if pixels is None:
        return None
    area = found.cell_area(pixels)
    if area is None:
        return None
    return found.screen_region(area=area, still_width=pixels.shape[1], bounds=bounds)


def region_tools():
    """Return internal_tools/window_region.py, which lies beside this tool, loaded as a module."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), REGION_SCRIPT)
    specification = importlib.util.spec_from_file_location(REGION_MODULE, path)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def batch_video_path(*, path, mode):
    """Return where a set's batch video of a mode is written: recordings/<set>_<mode>.mov."""
    return os.path.join(RECORDINGS, BATCH_VIDEO.format(stem=file_stem(path), mode=mode) + VIDEO_SUFFIX)


def take_seconds(*, song_seconds, max_seconds):
    """Return how long the screen is recorded: the splash, the lead-in, the song, the lead-out, the splash again, the hold and a margin, or the limit if that is less."""
    return min(SPLASH_SECONDS + LEAD_IN_SECONDS + song_seconds + LEAD_OUT_SECONDS + SPLASH_SECONDS + HOLD_SECONDS + MARGIN_SECONDS, max_seconds)


def trim_end(*, video, recorded_seconds):
    """Cut CUT_FROM_START seconds off the start of a video recorded for recorded_seconds and TRIMMED_SECONDS off its end, in place, so that it opens on black and ends while the tracker still shows. Return None, or why it couldn't, leaving the video as it was."""
    trimming = video + TRIMMING_SUFFIX
    kept = recorded_seconds - CUT_FROM_START - TRIMMED_SECONDS
    try:
        subprocess.run([AVCONVERT, SOURCE_FLAG, video, OUTPUT_FLAG, trimming, PRESET_FLAG, TRIM_PRESET, START_FLAG, str(CUT_FROM_START),
                        DURATION_FLAG, str(kept), REPLACE_FLAG],
                       check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as error:
        if os.path.exists(trimming):
            os.unlink(trimming)
        return str(error)
    os.replace(trimming, video)
    return None


def screen_recording():
    """Return the video tutorial's ScreenRecording, which records until it is stopped, loaded from internal_tools/make_video_tutorial.py, since internal_tools/ is not a package."""
    spec = importlib.util.spec_from_file_location(TUTORIAL_MODULE, TUTORIAL_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.ScreenRecording


def record_performance(*, document, video, window, device, max_seconds, visualizer, recording=None):
    """Record an interactive take: the screen until the tracker quits, which the person recording decides, then the video's end trimmed as a take's is. Return the exit code."""
    launch = Launch(for_recording=True, interactive=True, max_seconds=max_seconds, visualizer=visualizer, hold_seconds=HOLD_SECONDS)
    return recorded_until_quit(document=document, video=video, window=window, device=device, launch=launch, region=None, recording=recording)


def record(*, path, driver, audio_device, assignment, max_seconds, window_id, go=False, visualizer=None, ask_view=False, fluidsynth=False, fluidsynth_output=None,
           interactive=False, recording=None, batch=False, region=None, staged=True, alternate=True):
    """Set the take up, start the screen recording, run the tracker launched for recording, and report the video. Return the exit code.

    With ask_view, it asks whether the take shows the clips or a visualizer mode, once the port,
    the audio device and the window are found, so that a missing one stops it before any question.
    With fluidsynth, no MIDI port is used: FluidSynth plays the set's own instruments, to the audio
    device recorded, or to fluidsynth_output, an output device that also reaches it. With interactive,
    nothing plays until the person recording starts it, and the take ends when they stop it from
    Arrange's corner, so a song whose every clip loops is welcome; recording is the screen recording
    the tests give in place of the tutorial's. With batch, the take is a batch video (tui/batch_stage.py)
    of the visualizer mode given, recorded from the rectangle the window's cells cover alone, so that
    no title bar or margin is in it, and named after the set and the mode; region is what finds that
    rectangle, which the tests give. A take that isn't interactive and shows a visualizer mode is a batch video
    unless staged is false, the user's choice: the title, Arrange with READY, then the visualizer filling its frame.
    """
    if fluidsynth:
        port = None
        if not is_installed():
            print(NO_FLUIDSYNTH, file=sys.stderr)
            return FAILURE
    else:
        port = first_matching(names=output_port_names(), text=driver)
        if port is None:
            print(NO_DRIVER.format(text=driver, ports=CHANNEL_SEPARATOR.join(output_port_names()) or NO_PORTS), file=sys.stderr)
            return FAILURE
    devices = audio_devices()
    if devices is None:
        print(NO_SWIFT, file=sys.stderr)
        return FAILURE
    device = next(((device_id, name) for device_id, name in devices if audio_device.lower() in name.lower()), None)
    if device is None:
        print(NO_AUDIO_DEVICE.format(text=audio_device, devices=CHANNEL_SEPARATOR.join(name for _, name in devices) or NO_PORTS), file=sys.stderr)
        return FAILURE
    window = window_id if window_id is not None else terminal_window_id()
    if window is None:
        print(NO_WINDOW, file=sys.stderr)
        return FAILURE
    if ask_view:
        visualizer = ask_for_view()
        if visualizer is False:
            return FAILURE
    if batch and visualizer is None:
        print(BATCH_NEEDS_MODE, file=sys.stderr)
        return FAILURE
    batch = batch or (staged and not interactive and visualizer is not None)
    document = Document.load(path)
    song = document.song()
    problem = None if interactive else recording_problem(song)
    if problem is not None:
        print(problem, file=sys.stderr)
        return FAILURE
    if port is not None:
        print(DRIVER_FOUND.format(port=port))
    print(AUDIO_FOUND.format(device=device[1]))
    tracks = song.get_track_names()
    if fluidsynth:
        through_fluidsynth(document=document)
        # The tracker starts FluidSynth in this process, and it plays to the device the environment names.
        output = output_for_fluidsynth(given=fluidsynth_output, recorded=device[1], outputs=[] if fluidsynth_output else fluidsynth_outputs())
        os.environ[AUDIO_DEVICE_VARIABLE] = output
    else:
        channels = auto_assignment(tracks) if assignment is None else parse_assignment(text=assignment, tracks=tracks)
        assign_tracks(document=document, channels=channels, port=port)
    song_seconds = document.lengths().song_seconds()
    if song_seconds is None and not interactive:
        print(SONG_LENGTH_UNKNOWN, file=sys.stderr)
        return FAILURE
    if fluidsynth:
        heard = output != device[1] and MULTI_OUTPUT.lower() in output.lower()
        print((SETUP_FLUIDSYNTH_HEARD if heard else SETUP_FLUIDSYNTH).format(output=output, device=device[1]))
    else:
        explain_setup(plays=[(track, channel) for track, channel in zip(tracks, channels) if channel is not None], port=port, device=device[1])
    if interactive:
        print(INTERACTIVE_TAKE.format(seconds=max_seconds))
    elif batch:
        seconds = batch_take_seconds(song_seconds=float(song_seconds), max_seconds=max_seconds)
    else:
        seconds = take_seconds(song_seconds=float(song_seconds), max_seconds=max_seconds)
        print(TAKE.format(window=window, seconds=seconds, splash=SPLASH_SECONDS, lead_in=LEAD_IN_SECONDS, song=float(song_seconds), lead_out=LEAD_OUT_SECONDS))
    wait_for_go(go=go)
    region_argument = None
    if batch:
        found = cells_region(window=window, region=region)
        if found is None:
            print(NO_REGION, file=sys.stderr)
            return FAILURE
        region_argument = found.argument()
        print(BATCH_TAKE.format(region=region_argument, seconds=seconds, song=float(song_seconds), mode=visualizer))
    os.makedirs(RECORDINGS, exist_ok=True)
    video = batch_video_path(path=path, mode=visualizer) if batch else os.path.join(RECORDINGS, file_stem(path) + VIDEO_SUFFIX)
    if os.path.exists(video):
        os.unlink(video)
    if interactive:
        return record_performance(document=document, video=video, window=window, device=device, max_seconds=max_seconds, visualizer=visualizer, recording=recording)
    if batch:
        launch = Launch(batch_video=True, max_seconds=max_seconds, visualizer=visualizer, hold_seconds=HOLD_SECONDS, alternate=alternate)
    else:
        launch = Launch(quit_when_finished=True, for_recording=True, max_seconds=max_seconds, visualizer=visualizer, hold_seconds=HOLD_SECONDS)
    return recorded_until_quit(document=document, video=video, window=window, device=device, launch=launch, region=region_argument, recording=recording)


def recorded_until_quit(*, document, video, window, device, launch, region, recording=None):
    """Record the screen while the tracker runs the launch, stopping when the tracker quits, however it quits, then trim the video's end as a take's. Return the exit code.

    The recording stops when the tracker does, so quitting early, through the main screen's Quit, ends
    the video there rather than leaving the screen recorded until a time limit, the user's ask.
    """
    recording_class = screen_recording() if recording is None else recording
    capture = recording_class(path=video, window=window, audio_device=device[0], region=region)
    started = time.monotonic()
    try:
        sys.stdout.write(BLACK_SCREEN)
        sys.stdout.flush()
        time.sleep(SETTLE_SECONDS)
        LlamatronApp(document=document, launch=launch).run()
    finally:
        code = capture.stop()
    recorded = time.monotonic() - started
    if code != SUCCESS or not os.path.exists(video):
        print(NOT_WRITTEN.format(code=code), file=sys.stderr)
        return FAILURE
    problem = trim_end(video=video, recorded_seconds=recorded)
    if problem is not None:
        print(NOT_TRIMMED.format(reason=problem), file=sys.stderr)
    print(WRITTEN.format(path=video, size=os.path.getsize(video) / MEGABYTE))
    return SUCCESS


SOUND_DAW = 'daw'
SOUND_FLUIDSYNTH = 'fluidsynth'
SOUNDS = (SOUND_DAW, SOUND_FLUIDSYNTH)


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('path', help='the set to record, such as examples/learning/01_hello_world.yml')
    parser.add_argument('--use-driver', default=DEFAULT_DRIVER, help='the MIDI output port to play through: the first whose name holds this text')
    parser.add_argument('--audio-device', default=DEFAULT_AUDIO_DEVICE, help='the audio input device to record the sound from: the first whose name holds this text')
    assignment = parser.add_mutually_exclusive_group()
    assignment.add_argument('--track-assign-auto', action='store_true', help='the first track on channel 1, the second on 2 and so on (the default)')
    assignment.add_argument('--track-assign', default=None, help='a channel for each track in the song\'s order, like 1,1,2, with - to keep a track\'s own instrument')
    parser.add_argument('--max-seconds', type=float, default=DEFAULT_MAX_SECONDS, help='the longest a take may run')
    parser.add_argument('--window-id', type=int, default=None, help='the id of the window to record, when the terminal program cannot be asked')
    parser.add_argument('--go', action='store_true', help='start the take at once, without waiting for Enter after the setup is explained')
    parser.add_argument('--sound', choices=SOUNDS, default=None, help='where the sound comes from: the DAW through a MIDI port (the default), or the set\'s own FluidSynth instruments, the same as --fluidsynth (sh user_scripts/record.sh)')
    parser.add_argument('--fluidsynth', action='store_true', help='play the set\'s own FluidSynth instruments into the recording, with no MIDI port and no DAW (sh user_scripts/record.sh --sound fluidsynth)')
    parser.add_argument('--fluidsynth-output', default=None, help='with --fluidsynth, the audio output FluidSynth plays to, such as a Multi-Output Device that reaches the recorded one too; the recorded device unless given')
    parser.add_argument('--no-alternate', action='store_true', help='in a staged take, show the visualizer alone in the frame, rather than the clips and the visualizer by turns every ten seconds')
    parser.add_argument('--plain', action='store_true', help='record a visualizer take in the older style, the visualizer over the clip area of Arrange, rather than the title, READY and the framed visualizer every take of a visualizer has by default')
    parser.add_argument('--batch', action='store_true', help='record a batch video: the title, READY, then the visualizer mode filling a frame, from the window\'s cells alone (sh user_scripts/record_all.sh records every example)')
    parser.add_argument('--interactive', action='store_true', help='perform the take: nothing plays until you press Space on Arrange\'s corner, and stopping there, or Esc, ends it')
    view = parser.add_mutually_exclusive_group()
    view.add_argument('--visualizer', choices=mode_options(), default=None, help='record this visualizer mode over the clip area instead of the clips')
    view.add_argument('--clips', action='store_true', help='record the clips on Arrange, without asking')
    arguments = parser.parse_args(argv)
    path = arguments.path
    try:
        return record(path=path, driver=arguments.use_driver, audio_device=arguments.audio_device, assignment=arguments.track_assign,
                      max_seconds=arguments.max_seconds, window_id=arguments.window_id, go=arguments.go, visualizer=arguments.visualizer,
                      ask_view=arguments.visualizer is None and not arguments.clips, fluidsynth=arguments.fluidsynth or arguments.sound == SOUND_FLUIDSYNTH, fluidsynth_output=arguments.fluidsynth_output, interactive=arguments.interactive,
                      batch=arguments.batch, staged=not arguments.plain, alternate=not arguments.no_alternate)
    except ValueError as error:
        print(error, file=sys.stderr)
        return FAILURE


if __name__ == '__main__':
    sys.exit(main())
