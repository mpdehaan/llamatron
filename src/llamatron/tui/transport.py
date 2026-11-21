# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The transport: the tracker's side of real-time playback, between the pages and the player.

The pages ask it to play the song, a scene or a clip of the current song, or to stop, and ask it
what is playing for their lights. It works out each track's Route from the set's instruments, the
seed of each play and what stops a song from playing, and hands the rest to the player's side
(realtime/playback.py): the set's data, what each score is made from (Wanted), the launches, the
edits made while playing and the ports of the devices those instruments name, where the scores are
built, the Player launches their clips and the Realtime Sender Process sends them. It ticks on a
timer while anything plays, so that the player plans ahead and the page on top redraws its lights,
and it stops the timer when the last clip ends. The emergency stop, Ctrl+T, goes through it too, silencing every channel the instruments
use on every connected device.

What stops anything from playing is answered before anything is rendered: the set's Real Time
switch is off, no track has an instrument, an instrument's device isn't connected, or a track plays
through FluidSynth and FluidSynth isn't installed. A track whose instrument's Device is FluidSynth
gets a channel as the General MIDI export gives one, drums on channel 10 and the rest in turn, and
its instrument's General MIDI sound as a program change at each clip's start; FluidSynth is started
when something first plays through it, and waited for, before the sender opens its port. The tests
give the transport a stepped clock, an engine in place of the process and a FluidSynth that starts
nothing, so that nothing sleeps.
"""

import random
import threading
from typing import NamedTuple

from llamatron.composition import limits
from llamatron.composition.file_format import Section
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters import midi_arrangement
from llamatron.playback.step_order import walk_order
from llamatron.realtime import fluidsynth as fluidsynth_values, playback as playback_values, player as player_values
from llamatron.realtime.engine import MonotonicClock
from llamatron.realtime.fluidsynth import FluidSynth, installed
from llamatron.realtime.outputs import output_port_names
from llamatron.realtime.playback import Launch, LocalPlayback, Wanted
from llamatron.realtime.playback_process import PlaybackProcess
from llamatron.realtime.sender_process import RealtimeMIDISenderProcess, SenderNotStarted
from llamatron.realtime.timeline import Route
from llamatron.tui.uses import loop_error_lines
from llamatron.user_strings import errors, messages
from llamatron.visualizers import heard as heard_values
from llamatron.visualizers.heard import Heard, HeardNote

# How often the player plans ahead and the page redraws while something plays.
TICK_SECONDS = 0.1
# How often the tracker looks, while nothing plays, whether the set has changed and the next play's score should be built ahead.
KEEP_READY_SECONDS = 0.25
# How far ahead of now a launch from silence starts: long enough for its first window of events to reach the Realtime Sender
# Process before they are due, a fraction of a millisecond for a window, so that every track's first note leaves at the same instant.
LAUNCH_LEAD_SECONDS = 0.003
# MIDI channels are sent one less than people number them.
CHANNEL_OFFSET = 1
# How long after the last edit made while playing the edit is heard, so that typed digits, 1 then 12 then 120, are heard as 120 alone.
LIVE_SETTLE_SECONDS = 0.15
# The seeds a play draws its random parts from, for a song with no seed of its own, one seed for the whole play so that an edit re-rolls nothing.
SEED_RANGE = 2 ** 31


def step_sounding(*, elapsed, quarter, step_size, steps, direction):
    """Return the step that sounds a time into a clip's play, by the direction's order, or None for a direction that chooses its steps as it goes."""
    order = walk_order(count=steps, direction=direction)
    if order is None:
        return None
    step_seconds = float(step_size) * player_values.QUARTERS_PER_WHOLE * quarter
    return order[int(elapsed / step_seconds) % len(order)]


def fluidsynth_is_installed():
    """Return whether FluidSynth is installed, as looked for once a run, through a name of this module, so that the tests can answer for a computer that has none."""
    return installed()


def process_sender(ports):
    """Return the Realtime Sender Process for the ports, the sender every real play uses."""
    return RealtimeMIDISenderProcess(ports=ports)


class Problem:
    """Why nothing can play: a dialog's title and its lines."""

    __slots__ = ('title', 'lines')

    def __init__(self, *, title, lines):
        self.title = title
        self.lines = list(lines)


class Tried(NamedTuple):
    """What came of trying to play: what the playing answered, or the refusal to show, one of them None."""

    answer: object
    refusal: str

class Transport:
    """Plays the current song through the Realtime Sender Process, and answers what is playing."""

    __slots__ = ('_playback', '_lead', '_next_seed', '_pending', '_requested', '_closing', '_document_holder', '_clock', '_make_sender', '_set_timer', '_wanted', '_ports', '_timer',
                 '_fluidsynth', '_fluidsynth_installed', '_song', '_song_name', '_instead', '_seed', '_seen_revision', '_changed_at',
                 '_scenes', '_tracks', '_previewing', '_live_message')

    def __init__(self, *, document_holder, clock=None, make_sender=None, set_timer=None, fluidsynth=None, fluidsynth_installed=None, lead=LAUNCH_LEAD_SECONDS, playback=None):
        """document_holder answers get_document(). clock and make_sender(ports) are for the tests, which give a stepped clock and an engine; set_timer(seconds, callback) starts a repeating timer and returns something with stop(). fluidsynth and fluidsynth_installed() are for the tests too, which start no real FluidSynth, and playback is a player's side a test gives, a render process with a recording sender."""
        self._document_holder = document_holder
        # Whether the tracker is quitting, so that a sender started under the start screen meanwhile is closed rather than left behind.
        self._closing = False
        self._fluidsynth = FluidSynth() if fluidsynth is None else fluidsynth
        self._fluidsynth_installed = fluidsynth_is_installed if fluidsynth_installed is None else fluidsynth_installed
        self._clock = MonotonicClock() if clock is None else clock
        self._make_sender = process_sender if make_sender is None else make_sender
        # The scores, the player and the sender: in the render process, or, for a transport given its own sender, a test's or a
        # preview's, in this process, building every score in its request. lead is how far ahead of now a launch from silence
        # starts, and a test on a clock that never moves asks for none.
        self._lead = lead
        if playback is not None:
            self._playback = playback
        elif make_sender is None:
            self._playback = PlaybackProcess(lead=lead)
        else:
            self._playback = LocalPlayback(make_sender=self._make_sender, clock=self._clock, lead=lead, at_once=True)
        self._build_ahead()
        self._set_timer = set_timer
        # What the player's score was made from (Wanted), and the ports the sender was last asked to open.
        self._wanted = None
        self._ports = []
        self._timer = None
        self._know_nothing_plays()
        # Whether what plays is a listening page's preview, which stops when its page is left, where a song played from Arrange plays on.
        self._previewing = False
        self._live_message = None

    def _know_nothing_plays(self):
        """Start with nothing known of what plays, which following edits made while it plays needs: the song rendered, its name,
        whether it's a copy a listening page made, the instruments chosen in place of the tracks', the seed of this play, and the
        song's scenes and tracks as they were, to find them again after an edit."""
        self._song = None
        self._song_name = None
        self._instead = None
        self._seed = None
        self._seen_revision = None
        self._changed_at = None
        self._scenes = []
        self._tracks = {}

    def _build_ahead(self):
        """Make ready to build scores ahead (realtime/score_builder.py)."""
        # The seed the next play from silence draws its random parts from, chosen ahead so that its score can be built ahead.
        self._next_seed = random.randrange(SEED_RANGE)
        # The key of the score last asked for ahead of a play, and of the score an edit made while playing waits for, if any.
        self._requested = None
        self._pending = None

    def document(self):
        return self._document_holder.get_document()

    def shared(self):
        """Return what a second transport beside this one is made with, the pattern preview's: the same document, clock, timer, FluidSynth and way of making a sender."""
        return dict(
            document_holder=self._document_holder, clock=self._clock, make_sender=self._make_sender, set_timer=self._set_timer,
            fluidsynth=self._fluidsynth, fluidsynth_installed=self._fluidsynth_installed,
        )

    def is_connected(self, device):
        """Return whether this computer lists a MIDI port now."""
        return device in set(output_port_names())

    def output_port_names(self):
        """Return the names of the MIDI ports this computer lists now, FluidSynth's own among them."""
        return output_port_names()

    def device_port_names(self):
        """Return the names of the MIDI ports an instrument can be sent to: every port this computer lists now but FluidSynth's own, which an instrument reaches by choosing FluidSynth."""
        return [name for name in output_port_names() if not name.startswith(fluidsynth_values.FLUIDSYNTH_PORT_PREFIX)]

    def fluidsynth_installed(self):
        """Return whether FluidSynth is installed on this computer."""
        return self._fluidsynth_installed()

    def try_play(self, play):
        """Run something that plays, and return a Tried: what it answered, or why it could not play, in words to show.

        A set that cannot be played as written and a Realtime Sender Process that did not start are the two refusals
        of playing, which every page that plays tells the same way.
        """
        try:
            return Tried(answer=play(), refusal=None)
        except (SongFileError, SenderNotStarted) as problem:
            return Tried(answer=None, refusal=str(problem))

    # What stops anything from playing.

    def problem(self, *, track=None):
        """Return why nothing can play, or None when it can: the switch, the instruments, their devices, and the scenes that never end. With a track, which a listening page picks an instrument for, no track needs one yet."""
        setlist = self.document().get_setlist()
        song = self.document().song()
        if not setlist.is_real_time():
            return Problem(title=errors.ERR_CANT_PLAY_TITLE, lines=[errors.ERR_REAL_TIME_OFF])
        if not setlist.get_instrument_names():
            return Problem(title=errors.ERR_NO_INSTRUMENTS_TITLE, lines=[errors.ERR_ADD_INSTRUMENT_FIRST])
        if track is None and not any(song.get_track(name).get_instrument_name() for name in song.get_track_names()):
            return Problem(title=errors.ERR_CANT_PLAY_TITLE, lines=[errors.ERR_NO_TRACK_HAS_AN_INSTRUMENT])
        # An instrument with no device, which may be there only for its General MIDI sound, leaves its tracks silent, so a song where every track is silent can't play.
        if track is None and not any(self.has_a_device(name) for name in song.get_track_names()):
            return Problem(title=errors.ERR_CANT_PLAY_TITLE, lines=[errors.ERR_NO_TRACK_HAS_A_DEVICE])
        missing = self.missing_devices()
        if missing:
            return Problem(title=errors.ERR_CANT_PLAY_TITLE, lines=[errors.ERR_DEVICE_NOT_CONNECTED.format(instrument=name, device=device) for name, device in missing])
        if self.uses_fluidsynth() and not self._fluidsynth_installed():
            return Problem(title=errors.ERR_CANT_PLAY_TITLE, lines=[errors.ERR_FLUIDSYNTH_NOT_INSTALLED])
        lines = loop_error_lines(song)
        if lines:
            return Problem(title=errors.ERR_LOOP_SCENES_TITLE, lines=lines)
        return None

    def has_a_device(self, track):
        """Return whether a track of the current song plays through an instrument that has a device."""
        name = self.document().song().get_track(track).get_instrument_name()
        setlist = self.document().get_setlist()
        return name is not None and setlist.has_item(section=Section.INSTRUMENTS, name=name) and setlist.get_instrument(name).has_device()

    def missing_devices(self):
        """Return (instrument, device) for each instrument whose MIDI port this computer doesn't list now. FluidSynth is no port, and the tracker starts it."""
        connected = set(output_port_names())
        setlist = self.document().get_setlist()
        return [(name, setlist.get_instrument(name).get_device()) for name in setlist.get_instrument_names()
                if setlist.get_instrument(name).has_device() and not setlist.get_instrument(name).uses_fluidsynth()
                and setlist.get_instrument(name).get_device() not in connected]

    def uses_fluidsynth(self, *, instead=None):
        """Return whether some track of the current song plays through FluidSynth."""
        return any(route.port == fluidsynth_values.FLUIDSYNTH_PORT for route in self.routes(instead=instead).values())

    def routes(self, *, instead=None):
        """Return each track's Route, by the track's name, for the tracks whose instrument has a device. instead maps a track to an instrument to play through for one preview.

        A track through FluidSynth gets the channel the General MIDI export gives it, 10 for a drum track and the
        others in turn among the unmuted tracks through FluidSynth, and its instrument's sound as the program,
        none for a drum track or an instrument with no sound, as that export does.
        """
        setlist = self.document().get_setlist()
        song = self.document().song()
        routes = {}
        melodic = 0
        for track in song.get_track_names():
            name = (instead or {}).get(track) or song.get_track(track).get_instrument_name()
            if not (name and setlist.has_instrument(name) and setlist.get_instrument(name).has_device()):
                continue
            instrument = setlist.get_instrument(name)
            if not instrument.uses_fluidsynth():
                routes[track] = Route(instrument.get_device(), instrument.get_channel() - CHANNEL_OFFSET)
            elif song.get_track(track).is_drum():
                routes[track] = Route(fluidsynth_values.FLUIDSYNTH_PORT, midi_arrangement.DRUM_CHANNEL_BYTE, None, keyswitches=False)
            elif not song.get_track(track).is_muted():
                sound = instrument.get_gm_sound()
                routes[track] = Route(fluidsynth_values.FLUIDSYNTH_PORT, midi_arrangement.MELODIC_CHANNEL_BYTES[melodic % len(midi_arrangement.MELODIC_CHANNEL_BYTES)], None if sound is None else sound - limits.MIN_GM_SOUND, keyswitches=False)
                melodic += 1
        return routes

    def channels_in_use(self):
        """Return the (device, channel) pairs the set's instruments use, on the devices connected now, each once, and FluidSynth's channels while it runs."""
        connected = set(output_port_names())
        setlist = self.document().get_setlist()
        pairs = set()
        for name in setlist.get_instrument_names():
            instrument = setlist.get_instrument(name)
            if instrument.has_device() and not instrument.uses_fluidsynth() and instrument.get_device() in connected:
                pairs.add((instrument.get_device(), instrument.get_channel() - CHANNEL_OFFSET))
        if self._fluidsynth.is_running():
            pairs |= {(route.port, route.channel) for route in self.routes().values() if route.port == fluidsynth_values.FLUIDSYNTH_PORT}
        return sorted(pairs)

    # Playing.

    def play_song(self):
        return self.play_scene(index=0)

    def play_scene(self, *, index):
        """Play the current song from a scene, every clip of it, the follow actions taking it on. Return whether it waits for the next bar of what plays."""
        self._previewing = False
        return self._launch(launch=Launch(playback_values.LAUNCH_SCENE, index), instead=None)

    def play_clip(self, *, index, track, instead=None, forever=False):
        """Play one clip on its own, through its track's instrument or the one instead names, once as its scene would or again and again. Return whether it waits for the next bar.

        Played again and again (forever), it is a listening page's preview, which stops when its page is left; a preview while a song plays from Arrange stops the song first.
        """
        if forever and self.is_playing() and not self._previewing:
            self.stop_all()
        self._previewing = forever
        return self._launch(launch=Launch(playback_values.LAUNCH_CLIP, index, (track,), forever), instead=instead)

    def play_clips(self, *, index, tracks):
        """Play several clips of one scene together, again and again, as a preview of a few players, which stops when its page is left."""
        if self.is_playing() and not self._previewing:
            self.stop_all()
        self._previewing = True
        self._launch(launch=Launch(playback_values.LAUNCH_CLIPS, index, tuple(tracks), True), instead=None)

    def stop_clip(self, track):
        self._playback.stop_clip(track)

    def stop_all(self):
        """Stop everything playing, silencing what sounded, which a page does as it closes."""
        self._playback.stop_all()
        self._stop_timer()

    def silence_everything(self):
        """The emergency stop: note offs, all notes off and all sound off on every channel the instruments use, and return what the status line says."""
        channels = self.channels_in_use()
        if not channels:
            return messages.MSG_NOTHING_TO_SILENCE
        self.stop_all()
        self._playback.silence(ports=self._ports_ready(sorted({port for port, _ in channels})), channels=channels)
        return messages.MSG_SILENCED.format(channels=len(channels), devices=len({port for port, _ in channels}))

    def prepare(self):
        """Get real time ready in the background while the start screen shows, as a game loads behind its title: the MIDI ports
        listed, FluidSynth started where it is installed, whether or not the set uses it, and the Realtime Sender Process opened on
        every port, so that no play waits for them and no song's port makes the process start again. Return a function answering
        whether it is done. What fails here is tried again by the first play, as without the start screen."""
        done = threading.Event()

        def get_ready():
            try:
                self._playback.start()
                if self._fluidsynth_installed():
                    self._fluidsynth.ensure_running()
                ports = output_port_names()
                if ports:
                    self._playback.use_ports(self._ports_ready(sorted(set(ports))))
            except SenderNotStarted:
                pass
            finally:
                if self._closing:
                    self.close()
                done.set()
        threading.Thread(target=get_ready, daemon=True).start()
        if self._set_timer is not None:
            self._set_timer(seconds=KEEP_READY_SECONDS, tick=self.keep_ready)
        return done.is_set

    def close(self):
        """Stop everything and end the process and FluidSynth, as the tracker quits."""
        self._closing = True
        self._end_playback()
        self._fluidsynth.stop()

    def forget(self):
        """Stop everything and forget the song, as another set is opened; the process stays for the next play."""
        self._drop_score()

    def _drop_score(self):
        """Stop everything and forget the score, keeping the sender for the next play."""
        self._stop_timer()
        self._playback.forget()
        self._wanted = None

    def _end_playback(self):
        """Stop everything and end the sender, leaving FluidSynth, which a preview's transport shares with the song's."""
        self._stop_timer()
        self._playback.close()
        self._wanted = None

    def may_play(self):
        """Return whether anything may go on playing: the set's Real Time switch is on."""
        return self.document().get_setlist().is_real_time()

    def is_previewing(self):
        """Return whether what plays is a listening page's preview, which stops when its page is left."""
        return self._previewing and self.is_playing()

    def take_problem(self):
        """Return the dialog to show when the render process ended without being closed, once, and start afresh, or None."""
        if not self._playback.has_ended():
            return None
        self._stop_timer()
        self._playback = PlaybackProcess(lead=self._lead)
        self._wanted = None
        self._requested = None
        self._pending = None
        return Problem(title=errors.ERR_PLAYBACK_ENDED_TITLE, lines=[errors.ERR_PLAYBACK_ENDED])

    def take_live_message(self):
        """Return what the status line should say about the last edit made while playing, once, or None."""
        message = self._live_message
        self._live_message = None
        return message

    def tick(self):
        """Plan ahead, follow any edit made while playing, and stop the timer once the last clip has ended."""
        if self._wanted is None:
            return
        # Real Time turned off while something plays, on the main screen or by deleting the last instrument, stops it, since the
        # pages then show no stop for it, which was once a bug.
        if not self.may_play():
            self.stop_all()
            return
        self._follow_edits()
        if self._wanted is None:
            return
        self._playback.tick()
        if not self._playback.is_playing():
            self._stop_timer()

    # What is playing, for the lights.

    def is_playing(self):
        return self._playback.is_playing()

    def playing_scenes(self):
        return self._playback.playing_scenes()

    def is_clip_playing(self, *, index, track):
        return self._playback.is_clip_playing(index=index, track=track)

    def is_track_sounding(self, track):
        return self._playback.is_track_sounding(track)

    def scene_elapsed(self, index):
        return self._playback.scene_elapsed(index)

    def clip_elapsed(self, *, index, track):
        return self._playback.clip_elapsed(index=index, track=track)

    def repeats_left(self, *, index, track):
        return self._playback.repeats_left(index=index, track=track)

    def song_position(self):
        return self._playback.song_position()

    def song_seconds(self):
        return self._playback.song_seconds()

    def heard(self, *, since):
        """Return the clock's time now and what the visualizer hears since an earlier time, or None for now alone (visualizers/heard.py): each note that started since then or still sounds, by its track's place in the song, and the beat. Nothing plays, and it is silence at no time."""
        if not self._playback.is_playing():
            return None, heard_values.SILENCE
        now, heard = self._playback.heard(since=since)
        song = self.document().song()
        places = {name: place for place, name in enumerate(song.get_track_names())}
        notes = []
        for track, started, held in heard:
            if track not in places:
                continue
            drum = song.get_track(track).is_drum()
            notes += [HeardNote(places[track], note.number, note.velocity, True, drum) for note in started]
            notes += [HeardNote(places[track], note.number, note.velocity, False, drum) for note in held]
        seconds_per_beat = self._playback.seconds_per_quarter() or heard_values.REFERENCE_SECONDS_PER_BEAT
        position = self._playback.song_position() or 0.0
        return now, Heard(notes=tuple(notes), seconds_per_beat=seconds_per_beat, beats=position / seconds_per_beat, names=tuple(song.get_track_names()))

    def playing_step(self, pattern):
        """Return the step of a pattern that sounds now, for the piano roll's read head: the step of the first playing clip that plays the pattern, in the clip's
        direction, or None when no playing clip plays the pattern or the direction chooses its steps as it goes. What a generator or a morph does to the clip is not followed."""
        if not self.is_playing() or self._song is None or not self._song.has_pattern(pattern):
            return None
        song = self._song
        played = song.get_pattern(pattern)
        quarter = self._playback.seconds_per_quarter()
        scenes = song.get_scenes()
        for index in self.playing_scenes():
            if not quarter or index >= len(scenes):
                continue
            for track in song.get_track_names():
                clip_slot = scenes[index].get_clip_slot(track)
                if clip_slot is None or clip_slot.get_pattern_name() != pattern or not self.is_clip_playing(index=index, track=track):
                    continue
                elapsed = self.clip_elapsed(index=index, track=track)
                if elapsed is None:
                    continue
                return step_sounding(
                    elapsed=elapsed, quarter=quarter, step_size=song.get_pattern_step_size(played), steps=played.get_steps(),
                    direction=clip_slot.get_direction() or played.get_direction(),
                )
        return None

    def draw_places(self):
        """Return where every draw stands in what plays now, by name, the place of the slot each last took its value from, for the
        Draws page's lights: in the first scene that plays, and none while nothing plays."""
        scenes = self.playing_scenes()
        if not scenes:
            return {}
        elapsed = self.scene_elapsed(scenes[0])
        return {} if elapsed is None else self._playback.draw_places(scene=scenes[0], seconds=elapsed)

    def get_player(self):
        """Return the player, for the tests."""
        return self._playback.get_player()

    # Underneath.

    def _launch(self, *, launch, instead):
        """Play what a launch names on a score of the current song as it is now, through the sender for the routes' ports, and run
        the timer. A play started from silence draws a seed of its own for the song's random parts, which it keeps while it plays.
        Return whether it waits for the next bar of what plays."""
        song = self.document().song()
        if not self.is_playing() or self._seed is None:
            self._seed = self._next_seed
            self._next_seed = random.randrange(SEED_RANGE)
        routes = self.routes(instead=instead)
        self._remember_song(song=song, instead=instead)
        wanted = self._wanted_now(routes=routes, seed=self._seed)
        if not self._playback.has_score(wanted):
            self._playback.take_set(self.document().get_setlist().kept_data())
        waits = self._playback.launch(wanted=wanted, launch=launch, ports=self._ports_ready(sorted({route.port for route in routes.values()})))
        self._wanted = wanted
        self._run()
        return waits

    def _remember_song(self, *, song, instead):
        """Remember what plays, and its scenes and tracks as they are, to find them again after an edit."""
        self._song = song
        self._song_name = self.document().get_current_song_name()
        self._instead = instead
        self._scenes = list(song.get_scenes())
        self._tracks = {name: song.get_track(name) for name in song.get_track_names()}
        self._seen_revision = self.document().get_revision()
        self._changed_at = None

    def _playing_song(self):
        """Return the song that plays, after an edit: the current song while it is the one launched, or None when another song was made current."""
        if self.document().get_current_song_name() != self._song_name:
            return None
        return self.document().song()

    def _follow_edits(self):
        """Hear an edit made while playing, once the edits have settled for LIVE_SETTLE_SECONDS: render the song again with this play's seed and hand the score to the player, which takes it from the moment the song's Live response says."""
        if not self._playback.is_playing():
            return
        if self._playing_song() is None:
            # Another song was made current, so what plays stops at once, since nothing on screen could show or stop it any more.
            self.stop_all()
            return
        revision = self.document().get_revision()
        if revision == self._wanted.revision:
            return
        now = self._clock.now()
        if revision != self._seen_revision:
            self._seen_revision = revision
            self._changed_at = now
            return
        if self._changed_at is not None and now - self._changed_at < LIVE_SETTLE_SECONDS:
            return
        song = self._playing_song()
        routes = self.routes(instead=self._instead)
        if set(route.port for route in routes.values()) - set(self._ports):
            self._wanted = self._wanted._replace(revision=revision)
            self._live_message = messages.MSG_LIVE_EDIT_NEEDS_A_DEVICE
            return
        # The edit is rendered off the screen's thread, from the set's data as kept; a later tick hands the score over once it is made.
        wanted = self._wanted_now(routes=routes, seed=self._seed)
        if self._pending != wanted:
            self._pending = wanted
            self._request(wanted)
        built = self._playback.built(wanted)
        if built is None:
            return
        self._pending = None
        if built.problem is not None:
            self._wanted = self._wanted._replace(revision=revision)
            self._live_message = messages.MSG_LIVE_EDIT_NOT_HEARD.format(problem=built.problem)
            return
        scene_map, track_map = self._places_after_the_edit(song)
        self._playback.apply(wanted=wanted, responsiveness=song.get_live_responsiveness(), scene_map=scene_map, track_map=track_map)
        self._wanted = wanted
        self._remember_song(song=song, instead=self._instead)

    def keep_ready(self):
        """Ask for the current song's score to be built ahead, off the screen's thread, whenever the set has changed since the last
        one asked for and nothing plays, so that the next play from silence starts with no render. Called on a light timer while
        the tracker runs (prepare)."""
        if not self._playback.is_ready() or self.is_playing() or not self.may_play():
            return
        wanted = self._wanted_now(routes=self.routes(instead=None), seed=self._next_seed)
        if wanted != self._requested:
            self._requested = wanted
            self._request(wanted)

    def _wanted_now(self, *, routes, seed):
        """Return what a score of the current song as it is now is made from: the set's revision, the song, the routes and the seed."""
        document = self.document()
        return Wanted(document.get_revision(), document.get_current_song_name(), tuple(sorted(routes.items())), seed)

    def _request(self, wanted):
        """Ask for a score of the current song to be built off the screen's thread, from the set's data as its objects keep it now,
        whose parts never change, so that nothing the render reads changes while it renders."""
        self._playback.take_set(self.document().get_setlist().kept_data())
        self._playback.build(wanted)

    def _places_after_the_edit(self, song):
        """Return each scene's new place by its old one and each track's new name by its old one, found by the objects themselves, else by place or name when an undo read the song again, None for one that has gone."""
        scenes = list(song.get_scenes())
        places = {id(scene): place for place, scene in enumerate(scenes)}
        scene_map = {}
        for place, scene in enumerate(self._scenes):
            if id(scene) in places:
                scene_map[place] = places[id(scene)]
            else:
                scene_map[place] = place if len(scenes) == len(self._scenes) else None
        names = {id(song.get_track(name)): name for name in song.get_track_names()}
        track_map = {}
        for name, track in self._tracks.items():
            track_map[name] = names.get(id(track), name if song.has_item(section=Section.TRACKS, name=name) else None)
        return scene_map, track_map

    def _ports_ready(self, ports):
        """Return the ports, FluidSynth started first where it is one of them, and tell the player's side when FluidSynth started
        again, since its port is then new though named the same."""
        if fluidsynth_values.FLUIDSYNTH_PORT in ports and self._fluidsynth.ensure_running():
            self._playback.use_ports(ports, renewed=[fluidsynth_values.FLUIDSYNTH_PORT])
        self._ports = list(ports)
        return ports

    def _run(self):
        if self._timer is None and self._set_timer is not None:
            self._timer = self._set_timer(seconds=TICK_SECONDS, tick=self.tick)

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

