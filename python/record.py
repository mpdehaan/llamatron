#!/usr/bin/env python3
# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Record a video of llamatron playing a set on Arrange, with its sound, for a demo video: sh user_scripts/record.sh SET.

Run from the top folder, in the terminal window the video should show, sized the way the video should look (16 by 9 is
what video sites expect). The recorder works on a Mac alone, with the system's own screencapture, avconvert and
osascript, and writes nothing but the video and a copy of the set it plays, in a temporary folder it removes:

- With --sound daw, the default, the tracks play over MIDI into a DAW: one instrument per MIDI channel used, RECORDER 1,
  RECORDER 2 and so on, on the first MIDI output port whose name holds --use-driver's text (IAC by default), the first
  track on channel 1, the second on 2 and so on, or as --track-assign names them (1,1,2, with - to keep a track's own
  instrument). The DAW plays them and sends its sound to a loopback audio device, BlackHole unless --audio-device names
  another, which the video records.
- With --sound own, or its old name --sound fluidsynth, the set plays on its own instruments, the built-in synths and
  FluidSynth among them, their sound sent to --sound-output, else a Multi-Output Device when the computer has one, so
  that the take is heard as it records, else the recorded device.

The tracker is launched for recording (llamatron --launch-for-recording): the title, Arrange, the song from the top, the
title again. --interactive plays nothing by itself: you start the song from Arrange, perform, and stop to end the take.
A scene whose every clip loops is refused unless the take is interactive, since the song would never end. The video is
output/recordings/<set>.mov, a second take writing over the first, its first and last seconds trimmed so that it opens
on black and ends on the title.
"""

import argparse
import os
import pty
import shutil
import subprocess
import sys
import tempfile
import time

import yaml

LLAMATRON = 'src/target/release/llamatron'
RECORDINGS = 'output/recordings'
VIDEO_SUFFIX = '.mov'
DEFAULT_DRIVER = 'IAC'
DEFAULT_AUDIO_DEVICE = 'BlackHole'
DEFAULT_MAX_SECONDS = 15 * 60
# The recorder's instruments, one per channel, named by the channel as people number it, and the channels MIDI has.
INSTRUMENT_NAME = 'RECORDER {channel}'
LOWEST_CHANNEL = 1
HIGHEST_CHANNEL = 16
CHANNEL_SEPARATOR = ','
KEEP_OWN = '-'
# The tracker's launch: the title it opens and closes on, the lead-in and the lead-out, in seconds, as llamatron's own.
SPLASH_SECONDS = 6.0
LEAD_IN_SECONDS = 1.0
LEAD_OUT_SECONDS = 2.0
HOLD_SECONDS = 0.5
# How much longer the recording runs than the take, and the start and end cut off it, so that the video opens on black and
# ends on the title, never on the shell.
MARGIN_SECONDS = 1.0
SETTLE_SECONDS = 3.0
CUT_FROM_START = 2.0
CUT_FROM_END = 0.5
BLACK_SCREEN = '\x1b[48;2;0;0;0m\x1b[2J\x1b[H'
# The sounds a take can have.
SOUND_DAW = 'daw'
SOUND_OWN = 'own'
SOUND_FLUIDSYNTH = 'fluidsynth'
SOUNDS = (SOUND_DAW, SOUND_OWN, SOUND_FLUIDSYNTH)
# Where llamatron's own sound goes, by the environment variable it reads, and the kind of output that also reaches the
# speakers.
AUDIO_DEVICE_VARIABLE = 'LLAMATRON_AUDIO_DEVICE'
MULTI_OUTPUT = 'Multi-Output'
# The screen recording: screencapture of a window, which stops and writes its file when a character is typed into its
# own terminal and writes nothing when it is signalled.
SCREENCAPTURE = 'screencapture'
CAPTURE_FLAGS = ['-x', '-v']
WINDOW_FLAG = '-l'
SOUND_FLAG = '-G'
STOP_KEY = b'q'
STOP_TIMEOUT_SECONDS = 60
# The Mac's own tool that copies a span of a video.
AVCONVERT = 'avconvert'
TRIM_PRESET = 'PresetHighestQuality'
# How the terminal window is found, by the program that owns it.
TERM_PROGRAM = 'TERM_PROGRAM'
WINDOW_ID_SCRIPTS = {
    'Apple_Terminal': 'tell application "Terminal" to id of front window',
    'iTerm.app': 'tell application "iTerm2" to id of current window',
}
OSASCRIPT = 'osascript'
# Swift, which every Mac with Xcode's command line tools has, lists the audio input devices with the ids screencapture takes,
# and the output devices by name.
SWIFT = 'swift'
INPUTS_SWIFT = '''
import AVFoundation
let session = AVCaptureDevice.DiscoverySession(deviceTypes: [.microphone, .external], mediaType: .audio, position: .unspecified)
for device in session.devices { print(device.uniqueID + "\\t" + device.localizedName) }
'''
FIELD_SEPARATOR = '\t'
LIST_TIMEOUT_SECONDS = 120
ONE_LINE_TIMEOUT_SECONDS = 20
SUCCESS = 0
FAILURE = 1
MEGABYTE = 1024 * 1024

ASK_VIEW = 'What should the take show? Type its number:'
VIEW_LINE = '  {number:2}  {name}'
CLIPS_VIEW = 'the clips on Arrange'
NOT_A_CHOICE = 'that is not one of the numbers'
NOT_BUILT = 'llamatron is not built: run sh build.sh first'
NO_DRIVER = 'no MIDI output port has ({text}) in its name; the ports are: {ports}'
NO_PORTS = '(none)'
NO_AUDIO_DEVICE = ('no audio input device has ({text}) in its name, so there is nothing to record the sound from; the devices are: {devices}. '
                   'Install BlackHole with sh user_scripts/install_blackhole.sh, as docs/RECORDING.md says')
NO_SWIFT = 'the audio devices cannot be listed without the swift command: install Xcode\'s command line tools with xcode-select --install'
NO_WINDOW = 'the terminal window cannot be found: run this from Terminal or iTerm2, or pass --window-id with the window\'s id'
BAD_ASSIGNMENT_COUNT = '--track-assign names {given} channels, and the song has {tracks} tracks: {names}'
BAD_CHANNEL = 'a channel must be an integer from {low} to {high}, or - to keep the track\'s own instrument, got {value}'
NO_TRACK_PLAYS = 'no track has an instrument to play through: pass --track-assign, or record with --sound own'
NOT_BACK_YET = '{option} is not back yet in the Rust program, so the take is recorded without it'
DRIVER_FOUND = 'MIDI goes out of ({port})'
AUDIO_FOUND = 'sound is recorded from ({device})'
OWN_SOUND = 'the set plays on its own instruments, its sound sent to ({output})'
TRACK_LINE = '  track ({track}) plays through ({instrument}) on channel {channel}'
TRACK_KEPT = '  track ({track}) keeps its own instrument ({instrument})'
TRACK_SILENT = '  track ({track}) has no instrument and stays silent'
SETUP_DAW = ('In the DAW, give each of those a MIDI track whose MIDI From is ({port}) on that channel, arm it with Monitor set to In, '
             'and set the audio output device to ({device}), so that the sound comes back into the recording.')
SETUP_GO = 'Ready? Press ENTER to Start - DO NOT MOVE YOUR MOUSE CURSOR'
INTERACTIVE_TAKE = ('An interactive take: after the title, Arrange waits. Press Space on the corner to start the song, perform as you like, '
                    'and stop everything, or leave Arrange, to end the take. It ends by itself after {seconds:.0f} s.')
TAKE = 'recording window {window} for up to {seconds:.0f} s'
WRITTEN = 'wrote {path} ({size:.1f} MB)'
NOT_WRITTEN = 'no video was written: screencapture ended with {code}'
NOT_TRIMMED = 'the video was left as it was, its last seconds showing the terminal: avconvert could not trim it ({reason})'
PLAY_FAILED = 'llamatron could not play the take: {problem}'


def llamatron_lines(*flags):
    """Return what llamatron prints for some listing flags, a line each, such as its MIDI output ports."""
    finished = subprocess.run([LLAMATRON, *flags], capture_output=True, text=True, timeout=ONE_LINE_TIMEOUT_SECONDS, check=False)
    return [line for line in finished.stdout.splitlines() if line.strip()]


def first_matching(*, names, text):
    """Return the first name holding the text, ignoring case, or None."""
    wanted = text.lower()
    return next((name for name in names if wanted in name.lower()), None)


def audio_inputs():
    """Return (id, name) for each audio input device, as screencapture names them, or None when Swift isn't there to ask."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.swift', delete=False) as script:
        script.write(INPUTS_SWIFT)
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


def ask_for_view():
    """Print what a take can show, the clips or each visualizer mode, numbered, and return the mode's name, or None for the
    clips, or False for an answer that is none of them."""
    modes = [line.split(FIELD_SEPARATOR, 1) for line in llamatron_lines('--list-visualizers')]
    names = [CLIPS_VIEW, *[shown for _, shown in modes]]
    for number, name in enumerate(names, start=1):
        print(VIEW_LINE.format(number=number, name=name))
    print(ASK_VIEW)
    typed = input().strip()
    if not typed.isdigit() or not 1 <= int(typed) <= len(names):
        print(NOT_A_CHOICE, file=sys.stderr)
        return False
    return None if int(typed) == 1 else modes[int(typed) - 2][0]


def channels_for(*, assignment, tracks):
    """Return a channel, or None to keep the track's own instrument, for each track: as a list like 1,1,2 or 1,-,3 names
    them, or the first track on channel 1, the second on 2 and so on, going round after 16."""
    if assignment is None:
        count = HIGHEST_CHANNEL - LOWEST_CHANNEL + 1
        return [LOWEST_CHANNEL + place % count for place in range(len(tracks))]
    parts = [part.strip() for part in assignment.split(CHANNEL_SEPARATOR)]
    if len(parts) != len(tracks):
        raise ValueError(BAD_ASSIGNMENT_COUNT.format(given=len(parts), tracks=len(tracks), names=CHANNEL_SEPARATOR.join(tracks)))
    channels = []
    for part in parts:
        if part == KEEP_OWN:
            channels.append(None)
        elif part.isdigit() and LOWEST_CHANNEL <= int(part) <= HIGHEST_CHANNEL:
            channels.append(int(part))
        else:
            raise ValueError(BAD_CHANNEL.format(low=LOWEST_CHANNEL, high=HIGHEST_CHANNEL, value=part))
    return channels


def first_song(data):
    """Return the set's first song, which a take plays."""
    return (data.get('songs') or [{}])[0]


def track_names(song):
    return [track.get('name', '') for track in song.get('tracks') or []]


def assigned(*, data, channels, port):
    """Give the set one RECORDER instrument per channel used, on the port, and each track the instrument of its channel;
    print what each track plays through, and refuse a song where nothing plays."""
    song = first_song(data)
    instruments = data.setdefault('instruments', [])
    own = {instrument.get('name') for instrument in instruments if instrument.get('device')}
    for channel in sorted({channel for channel in channels if channel is not None}):
        instruments.append({'name': INSTRUMENT_NAME.format(channel=channel), 'device': port, 'channel': channel})
    plays = 0
    for track, channel in zip(song.get('tracks') or [], channels):
        if channel is not None:
            track['instrument'] = INSTRUMENT_NAME.format(channel=channel)
            print(TRACK_LINE.format(track=track.get('name'), instrument=track['instrument'], channel=channel))
            plays += 1
        elif track.get('instrument') in own:
            print(TRACK_KEPT.format(track=track.get('name'), instrument=track.get('instrument')))
            plays += 1
        else:
            print(TRACK_SILENT.format(track=track.get('name')))
    if not plays:
        raise ValueError(NO_TRACK_PLAYS)
    data['real_time'] = True
    return data


class ScreenRecording:
    """screencapture recording a window into a file, started under a pseudo-terminal of its own."""

    def __init__(self, *, path, window, audio_device):
        self.terminal, own_end = pty.openpty()
        command = [SCREENCAPTURE, *CAPTURE_FLAGS, WINDOW_FLAG, str(window), SOUND_FLAG, audio_device, path]
        self.process = subprocess.Popen(command, stdin=own_end, stdout=own_end, stderr=own_end, close_fds=True)
        os.close(own_end)

    def stop(self):
        """Type the character that ends the recording, wait for the file to be written, and return screencapture's exit code,
        or None when it didn't stop and had to be ended, which leaves no file."""
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


def trimmed(*, video, recorded_seconds):
    """Cut the start and the end off a video, in place, so that it opens on black and ends on the title. Return None, or why
    it couldn't."""
    folder = tempfile.mkdtemp()
    trimming = os.path.join(folder, os.path.basename(video))
    kept = recorded_seconds - CUT_FROM_START - CUT_FROM_END
    try:
        subprocess.run([AVCONVERT, '--source', video, '--output', trimming, '--preset', TRIM_PRESET, '--start', str(CUT_FROM_START),
                        '--duration', str(kept), '--replace'], check=True, capture_output=True)
        shutil.move(trimming, video)
    except (OSError, subprocess.CalledProcessError) as error:
        return str(error)
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return None


def launch_flags(*, arguments, visualizer):
    """Return the flags llamatron is launched with for the take."""
    flags = ['--launch-for-recording', '--max-seconds', str(arguments.max_seconds)]
    if arguments.interactive:
        flags.append('--interactive')
    if visualizer is not None:
        flags += ['--visualizer', visualizer]
    if arguments.detail:
        flags.append('--details')
    return flags


def record(arguments):
    """Set the take up, record the screen while llamatron plays it, and trim and report the video. Return the exit code."""
    if not os.path.exists(LLAMATRON):
        print(NOT_BUILT, file=sys.stderr)
        return FAILURE
    for option, given in (('--announce', arguments.announce), ('--batch', arguments.batch), ('--scroll-text', arguments.scroll_text)):
        if given:
            print(NOT_BACK_YET.format(option=option), file=sys.stderr)
    own_sound = arguments.sound in (SOUND_OWN, SOUND_FLUIDSYNTH)
    port = None
    if not own_sound:
        ports = llamatron_lines('--list-midi-ports')
        port = first_matching(names=ports, text=arguments.use_driver)
        if port is None:
            print(NO_DRIVER.format(text=arguments.use_driver, ports=CHANNEL_SEPARATOR.join(ports) or NO_PORTS), file=sys.stderr)
            return FAILURE
    inputs = audio_inputs()
    if inputs is None:
        print(NO_SWIFT, file=sys.stderr)
        return FAILURE
    device = next(((device_id, name) for device_id, name in inputs if arguments.audio_device.lower() in name.lower()), None)
    if device is None:
        print(NO_AUDIO_DEVICE.format(text=arguments.audio_device, devices=CHANNEL_SEPARATOR.join(name for _, name in inputs) or NO_PORTS), file=sys.stderr)
        return FAILURE
    window = arguments.window_id if arguments.window_id is not None else terminal_window_id()
    if window is None:
        print(NO_WINDOW, file=sys.stderr)
        return FAILURE
    visualizer = arguments.visualizer
    if visualizer is None and not arguments.clips and not arguments.detail:
        visualizer = ask_for_view()
        if visualizer is False:
            return FAILURE
    with open(arguments.path, encoding='utf-8') as source:
        data = yaml.safe_load(source)
    environment = dict(os.environ)
    print(AUDIO_FOUND.format(device=device[1]))
    if own_sound:
        output = arguments.sound_output or device[1]
        environment[AUDIO_DEVICE_VARIABLE] = output
        data['real_time'] = True
        print(OWN_SOUND.format(output=output))
    else:
        print(DRIVER_FOUND.format(port=port))
        channels = channels_for(assignment=arguments.track_assign, tracks=track_names(first_song(data)))
        data = assigned(data=data, channels=channels, port=port)
        print(SETUP_DAW.format(port=port, device=device[1]))
    if arguments.interactive:
        print(INTERACTIVE_TAKE.format(seconds=arguments.max_seconds))
    print(TAKE.format(window=window, seconds=arguments.max_seconds))
    if not arguments.go:
        print(SETUP_GO)
        input()
    os.makedirs(RECORDINGS, exist_ok=True)
    stem = os.path.splitext(os.path.basename(arguments.path))[0]
    video = os.path.join(RECORDINGS, stem + VIDEO_SUFFIX)
    if os.path.exists(video):
        os.unlink(video)
    folder = tempfile.mkdtemp()
    copy = os.path.join(folder, os.path.basename(arguments.path))
    with open(copy, 'w', encoding='utf-8') as written:
        yaml.safe_dump(data, written, sort_keys=False, allow_unicode=True)
    capture = ScreenRecording(path=video, window=window, audio_device=device[0])
    started = time.monotonic()
    try:
        sys.stdout.write(BLACK_SCREEN)
        sys.stdout.flush()
        time.sleep(SETTLE_SECONDS)
        played = subprocess.run([LLAMATRON, copy, *launch_flags(arguments=arguments, visualizer=visualizer)], env=environment, check=False,
                                stderr=subprocess.PIPE, text=True)
    finally:
        code = capture.stop()
        shutil.rmtree(folder, ignore_errors=True)
    if played.returncode != SUCCESS:
        print(PLAY_FAILED.format(problem=played.stderr.strip()), file=sys.stderr)
    if code != SUCCESS or not os.path.exists(video):
        print(NOT_WRITTEN.format(code=code), file=sys.stderr)
        return FAILURE
    problem = trimmed(video=video, recorded_seconds=time.monotonic() - started)
    if problem is not None:
        print(NOT_TRIMMED.format(reason=problem), file=sys.stderr)
    print(WRITTEN.format(path=video, size=os.path.getsize(video) / MEGABYTE))
    return SUCCESS


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('path', help='the set to record, such as examples/learning/01_hello_world.yml')
    parser.add_argument('--sound', choices=SOUNDS, default=SOUND_DAW, help='where the sound comes from: a DAW over MIDI (daw, the default), or the set\'s own instruments (own; fluidsynth is its old name)')
    parser.add_argument('--use-driver', default=DEFAULT_DRIVER, help='the MIDI output port to play through: the first whose name holds this text')
    parser.add_argument('--audio-device', default=DEFAULT_AUDIO_DEVICE, help='the audio input device to record the sound from: the first whose name holds this text')
    parser.add_argument('--sound-output', '--fluidsynth-output', default=None, help='with --sound own, the audio output llamatron plays to, such as a Multi-Output Device that reaches the recorded one too')
    assignment = parser.add_mutually_exclusive_group()
    assignment.add_argument('--track-assign-auto', action='store_true', help='the first track on channel 1, the second on 2 and so on (the default)')
    assignment.add_argument('--track-assign', default=None, help='a channel for each track in the song\'s order, like 1,1,2, with - to keep a track\'s own instrument')
    parser.add_argument('--max-seconds', type=float, default=DEFAULT_MAX_SECONDS, help='the longest a take may run')
    parser.add_argument('--window-id', type=int, default=None, help='the id of the window to record, when the terminal program cannot be asked')
    parser.add_argument('--go', action='store_true', help='start the take at once, without waiting for ENTER')
    parser.add_argument('--interactive', action='store_true', help='perform the take: nothing plays until you start the song, and stopping ends it')
    parser.add_argument('--announce', action='store_true', help='show each scene\'s name as it starts (not back yet)')
    parser.add_argument('--batch', action='store_true', help='record a batch video (not back yet)')
    parser.add_argument('--scroll-text', default=None, help='the words that cross the screen after the opening title (not back yet)')
    parser.add_argument('--no-scroll', action='store_true', help='show no words crossing the screen after the opening title')
    view = parser.add_mutually_exclusive_group()
    view.add_argument('--visualizer', default=None, help='record this visualizer mode over the clip area instead of the clips')
    view.add_argument('--clips', action='store_true', help='record the clips on Arrange, without asking')
    view.add_argument('--detail', action='store_true', help='record the clips on Arrange with the details view open, without asking')
    arguments = parser.parse_args(argv)
    try:
        return record(arguments)
    except ValueError as error:
        print(error, file=sys.stderr)
        return FAILURE


if __name__ == '__main__':
    sys.exit(main())
