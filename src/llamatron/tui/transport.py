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

"""The transport: the tracker's side of real-time playback, between the pages and the player.

The pages ask it to play the song, a scene or a clip of the current song, or to stop, and ask it
what is playing for their lights. It renders the song into a Score when something is launched,
again only when the set has changed since, works out each track's Route from the set's instruments,
starts the Realtime Sender Process on the devices those instruments name, and keeps the Player that
launches the score's clips into the process. It ticks on a timer while anything plays, so that the
player plans ahead and the page on top redraws its lights, and it stops the timer when the last
clip ends. The emergency stop, Ctrl+T, goes through it too, silencing every channel the instruments
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

from llamatron.composition.file_format import Section
from llamatron.composition.song_file_error import SongFileError
from llamatron.composition.limits import MIN_GM_SOUND
from llamatron.exporters.midi_arrangement import DRUM_CHANNEL_BYTE, MELODIC_CHANNEL_BYTES
from llamatron.realtime.fluidsynth import FLUIDSYNTH_PORT, FluidSynth, is_installed
from llamatron.visualizers.heard import REFERENCE_SECONDS_PER_BEAT, SILENCE, Heard, HeardNote
from llamatron.realtime.engine import MonotonicClock
from llamatron.realtime.outputs import output_port_names
from llamatron.playback.step_order import walk_order
from llamatron.realtime.player import QUARTERS_PER_WHOLE, Player
from llamatron.realtime.score import Score
from llamatron.realtime.sender_process import RealtimeMIDISenderProcess
from llamatron.realtime.timeline import Route
from llamatron.tui.uses import loop_error_lines
from llamatron.strings.errors import (
    ERR_CANT_PLAY_TITLE, ERR_DEVICE_NOT_CONNECTED, ERR_FLUIDSYNTH_NOT_INSTALLED, ERR_LOOP_SCENES_TITLE, ERR_NO_INSTRUMENTS_TITLE, ERR_ADD_INSTRUMENT_FIRST,
    ERR_NO_TRACK_HAS_A_DEVICE, ERR_NO_TRACK_HAS_AN_INSTRUMENT, ERR_REAL_TIME_OFF,
)
from llamatron.strings.messages import MSG_LIVE_EDIT_NOT_HEARD, MSG_LIVE_EDIT_NEEDS_A_DEVICE, MSG_NOTHING_TO_SILENCE, MSG_SILENCED

# How often the player plans ahead and the page redraws while something plays.
TICK_SECONDS = 0.1
# MIDI channels are sent one less than people number them.
CHANNEL_OFFSET = 1
NO_CHANNELS = 0
# How long after the last edit made while playing the edit is heard, so that typed digits, 1 then 12 then 120, are heard as 120 alone.
LIVE_SETTLE_SECONDS = 0.15
# The seeds a play draws its random parts from, for a song with no seed of its own, one seed for the whole play so that an edit re-rolls nothing.
SEED_RANGE = 2 ** 31


def step_sounding(*, elapsed, quarter, step_size, steps, direction):
    """Return the step that sounds a time into a clip's play, by the direction's order, or None for a direction that chooses its steps as it goes."""
    order = walk_order(count=steps, direction=direction)
    if order is None:
        return None
    step_seconds = float(step_size) * QUARTERS_PER_WHOLE * quarter
    return order[int(elapsed / step_seconds) % len(order)]


def fluidsynth_is_installed():
    """Return whether FluidSynth is installed, asked each time, so that the tests can answer for a computer that has none."""
    return is_installed()


class Problem:
    """Why nothing can play: a dialog's title and its lines."""

    __slots__ = ('title', 'lines')

    def __init__(self, *, title, lines):
        self.title = title
        self.lines = list(lines)


class Transport:
    """Plays the current song through the Realtime Sender Process, and answers what is playing."""

    __slots__ = ('_document_holder', '_clock', '_make_sender', '_set_timer', '_sender', '_ports', '_zero', '_player', '_score_revision', '_score_key', '_timer',
                 '_fluidsynth', '_fluidsynth_installed', '_song', '_song_name', '_song_is_copy', '_instead', '_seed', '_seen_revision', '_changed_at',
                 '_scenes', '_tracks', '_previewing', '_live_message')

    def __init__(self, *, document_holder, clock=None, make_sender=None, set_timer=None, fluidsynth=None, fluidsynth_installed=None):
        """document_holder answers get_document(). clock and make_sender(ports) are for the tests, which give a stepped clock and an engine; set_timer(seconds, callback) starts a repeating timer and returns something with stop(). fluidsynth and fluidsynth_installed() are for the tests too, which start no real FluidSynth."""
        self._document_holder = document_holder
        self._fluidsynth = FluidSynth() if fluidsynth is None else fluidsynth
        self._fluidsynth_installed = fluidsynth_is_installed if fluidsynth_installed is None else fluidsynth_installed
        self._clock = MonotonicClock() if clock is None else clock
        self._make_sender = self._process_sender if make_sender is None else make_sender
        self._set_timer = set_timer
        self._sender = None
        self._ports = None
        self._zero = None
        self._player = None
        self._score_revision = None
        self._score_key = None
        self._timer = None
        # What plays, for following edits made while it plays: the song rendered, its name, whether it's a copy a listening page made, the instruments
        # chosen in place of the tracks', the seed of this play, and the song's scenes and tracks as they were, to find them again after an edit.
        self._song = None
        self._song_name = None
        self._song_is_copy = False
        self._instead = None
        self._seed = None
        self._seen_revision = None
        self._changed_at = None
        self._scenes = []
        self._tracks = {}
        # Whether what plays is a listening page's preview, which stops when its page is left, where a song played from Arrange plays on.
        self._previewing = False
        self._live_message = None

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

    # What stops anything from playing.

    def problem(self, *, track=None):
        """Return why nothing can play, or None when it can: the switch, the instruments, their devices, and the scenes that never end. With a track, which a listening page picks an instrument for, no track needs one yet."""
        setlist = self.document().setlist()
        song = self.document().song()
        if not setlist.is_real_time():
            return Problem(title=ERR_CANT_PLAY_TITLE, lines=[ERR_REAL_TIME_OFF])
        if not setlist.get_instrument_names():
            return Problem(title=ERR_NO_INSTRUMENTS_TITLE, lines=[ERR_ADD_INSTRUMENT_FIRST])
        if track is None and not any(song.get_track(name).get_instrument_name() for name in song.get_track_names()):
            return Problem(title=ERR_CANT_PLAY_TITLE, lines=[ERR_NO_TRACK_HAS_AN_INSTRUMENT])
        # An instrument with no device, which may be there only for its General MIDI sound, leaves its tracks silent, so a song where every track is silent can't play.
        if track is None and not any(self.has_a_device(name) for name in song.get_track_names()):
            return Problem(title=ERR_CANT_PLAY_TITLE, lines=[ERR_NO_TRACK_HAS_A_DEVICE])
        missing = self.missing_devices()
        if missing:
            return Problem(title=ERR_CANT_PLAY_TITLE, lines=[ERR_DEVICE_NOT_CONNECTED.format(instrument=name, device=device) for name, device in missing])
        if self.uses_fluidsynth() and not self._fluidsynth_installed():
            return Problem(title=ERR_CANT_PLAY_TITLE, lines=[ERR_FLUIDSYNTH_NOT_INSTALLED])
        lines = loop_error_lines(song)
        if lines:
            return Problem(title=ERR_LOOP_SCENES_TITLE, lines=lines)
        return None

    def has_a_device(self, track):
        """Return whether a track of the current song plays through an instrument that has a device."""
        name = self.document().song().get_track(track).get_instrument_name()
        setlist = self.document().setlist()
        return name is not None and setlist.has_item(section=Section.INSTRUMENTS, name=name) and setlist.get_instrument(name).has_device()

    def missing_devices(self):
        """Return (instrument, device) for each instrument whose MIDI port this computer doesn't list now. FluidSynth is no port, and the tracker starts it."""
        connected = set(output_port_names())
        setlist = self.document().setlist()
        return [(name, setlist.get_instrument(name).get_device()) for name in setlist.get_instrument_names()
                if setlist.get_instrument(name).has_device() and not setlist.get_instrument(name).uses_fluidsynth()
                and setlist.get_instrument(name).get_device() not in connected]

    def uses_fluidsynth(self, *, instead=None):
        """Return whether some track of the current song plays through FluidSynth."""
        return any(route.port == FLUIDSYNTH_PORT for route in self.routes(instead=instead).values())

    def routes(self, *, instead=None):
        """Return each track's Route, by the track's name, for the tracks whose instrument has a device. instead maps a track to an instrument to play through for one preview.

        A track through FluidSynth gets the channel the General MIDI export gives it, 10 for a drum track and the
        others in turn among the unmuted tracks through FluidSynth, and its instrument's sound as the program,
        none for a drum track or an instrument with no sound, as that export does.
        """
        setlist = self.document().setlist()
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
                routes[track] = Route(FLUIDSYNTH_PORT, DRUM_CHANNEL_BYTE)
            elif not song.get_track(track).is_muted():
                sound = instrument.get_gm_sound()
                routes[track] = Route(FLUIDSYNTH_PORT, MELODIC_CHANNEL_BYTES[melodic % len(MELODIC_CHANNEL_BYTES)], None if sound is None else sound - MIN_GM_SOUND)
                melodic += 1
        return routes

    def channels_in_use(self):
        """Return the (device, channel) pairs the set's instruments use, on the devices connected now, each once, and FluidSynth's channels while it runs."""
        connected = set(output_port_names())
        setlist = self.document().setlist()
        pairs = set()
        for name in setlist.get_instrument_names():
            instrument = setlist.get_instrument(name)
            if instrument.has_device() and not instrument.uses_fluidsynth() and instrument.get_device() in connected:
                pairs.add((instrument.get_device(), instrument.get_channel() - CHANNEL_OFFSET))
        if self._fluidsynth.is_running():
            pairs |= {(route.port, route.channel) for route in self.routes().values() if route.port == FLUIDSYNTH_PORT}
        return sorted(pairs)

    # Playing.

    def play_song(self, *, song=None):
        return self.play_scene(index=0, song=song)

    def play_scene(self, *, index, song=None):
        """Play the current song, or the one given, from a scene, every clip of it, the follow actions taking it on. Return whether it waits for the next bar of what plays."""
        self._previewing = False
        at = self._ready(song=song, instead=None).play_scene(index)
        self._run()
        return at > self._now()

    def play_clip(self, *, index, track, song=None, instead=None, forever=False):
        """Play one clip on its own, through its track's instrument or the one instead names, once as its scene would or again and again. Return whether it waits for the next bar.

        Played again and again (forever), it is a listening page's preview, which stops when its page is left; a preview while a song plays from Arrange stops the song first.
        """
        if forever and self.is_playing() and not self._previewing:
            self.stop_all()
        self._previewing = forever
        at = self._ready(song=song, instead=instead).play_clip(scene=index, track=track, forever=forever)
        self._run()
        return at > self._now()

    def stop_clip(self, track):
        if self._player is not None:
            self._player.stop_clip(track)

    def stop_all(self):
        """Stop everything playing, silencing what sounded, which a page does as it closes."""
        if self._player is not None:
            self._player.stop_all()
        self._stop_timer()

    def silence_everything(self):
        """The emergency stop: note offs, all notes off and all sound off on every channel the instruments use, and return what the status line says."""
        channels = self.channels_in_use()
        if not channels:
            return MSG_NOTHING_TO_SILENCE
        self.stop_all()
        self._sender_for(sorted({port for port, _ in channels})).silence(channels=channels)
        return MSG_SILENCED.format(channels=len(channels), devices=len({port for port, _ in channels}))

    def close(self):
        """Stop everything and end the process and FluidSynth, as the tracker quits."""
        self.stop_all()
        if self._sender is not None:
            self._sender.close()
            self._sender = None
        self._player = None
        self._fluidsynth.stop()

    def forget(self):
        """Stop everything and forget the song, as another set is opened; the process stays for the next play."""
        self.stop_all()
        self._player = None

    def may_play(self):
        """Return whether anything may go on playing: the set's Real Time switch is on."""
        return self.document().setlist().is_real_time()

    def is_previewing(self):
        """Return whether what plays is a listening page's preview, which stops when its page is left."""
        return self._previewing and self.is_playing()

    def take_live_message(self):
        """Return what the status line should say about the last edit made while playing, once, or None."""
        message = self._live_message
        self._live_message = None
        return message

    def tick(self):
        """Plan ahead, follow any edit made while playing, and stop the timer once the last clip has ended."""
        if self._player is None:
            return
        # Real Time turned off while something plays, on the main screen or by deleting the last instrument, stops it, since the
        # pages then show no stop for it (a bug the user found).
        if not self.may_play():
            self.stop_all()
            return
        self._follow_edits()
        if self._player is None:
            return
        self._player.tick()
        if not self._player.is_playing():
            self._stop_timer()

    # What is playing, for the lights.

    def is_playing(self):
        return self._player is not None and self._player.is_playing()

    def playing_scenes(self):
        return [] if self._player is None else self._player.playing_scenes()

    def is_clip_playing(self, *, index, track):
        return self._player is not None and self._player.is_clip_playing(scene=index, track=track)

    def is_track_sounding(self, track):
        return self._player is not None and self._player.is_track_sounding(track)

    def scene_elapsed(self, index):
        return None if self._player is None else self._player.scene_elapsed(index)

    def clip_elapsed(self, *, index, track):
        return None if self._player is None else self._player.clip_elapsed(scene=index, track=track)

    def repeats_left(self, *, index, track):
        return None if self._player is None else self._player.repeats_left(scene=index, track=track)

    def song_position(self):
        return None if self._player is None else self._player.song_position()

    def song_seconds(self):
        return None if self._player is None else self._player.score().song_seconds()

    def heard(self, *, since):
        """Return the clock's time now and what the visualizer hears since an earlier time, or None for now alone (visualizers/heard.py): each note that started since then or still sounds, by its track's place in the song, and the beat. Nothing plays, and it is silence at no time."""
        if self._player is None or not self._player.is_playing():
            return None, SILENCE
        now, heard = self._player.heard(since=since)
        song = self.document().song()
        places = {name: place for place, name in enumerate(song.get_track_names())}
        notes = []
        for track, started, held in heard:
            if track not in places:
                continue
            drum = song.get_track(track).is_drum()
            notes += [HeardNote(places[track], note.number, note.velocity, True, drum) for note in started]
            notes += [HeardNote(places[track], note.number, note.velocity, False, drum) for note in held]
        seconds_per_beat = self._player.seconds_per_quarter() or REFERENCE_SECONDS_PER_BEAT
        position = self._player.song_position() or 0.0
        return now, Heard(notes=tuple(notes), seconds_per_beat=seconds_per_beat, beats=position / seconds_per_beat, names=tuple(song.get_track_names()))

    def playing_step(self, pattern):
        """Return the step of a pattern that sounds now, for the piano roll's read head: the step of the first playing clip that plays the pattern, in the clip's
        direction, or None when no playing clip plays the pattern or the direction chooses its steps as it goes. What a generator or a morph does to the clip is not followed."""
        if not self.is_playing() or self._song is None or not self._song.has_pattern(pattern):
            return None
        song = self._song
        played = song.get_pattern(pattern)
        quarter = self._player.seconds_per_quarter()
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

    def player(self):
        """Return the player, for the tests."""
        return self._player

    # Underneath.

    def _ready(self, *, song, instead):
        """Return the player, on a score of the song as it is now, through the sender for the routes' ports. A play started from silence draws a seed of its own for the song's random parts, which it keeps while it plays."""
        document = self.document()
        self._song_is_copy = song is not None and song is not document.song()
        song = document.song() if song is None else song
        if not self.is_playing() or self._seed is None:
            self._seed = random.randrange(SEED_RANGE) if song.get_seed() is None else None
        routes = self.routes(instead=instead)
        key = (id(song), tuple(sorted(routes.items())))
        self._remember_song(song=song, instead=instead)
        if self._player is None or self._score_revision != document.revision() or self._score_key != key:
            score = Score(song=song, routes=routes, seed=self._seed)
            sender = self._sender_for(sorted({route.port for route in routes.values()}))
            if self._player is None or self._player.sender() is not sender:
                self._player = Player(score=score, sender=sender, now=self._now)
            else:
                self._player.set_score(score)
            self._score_revision = document.revision()
            self._score_key = key
        return self._player

    def _remember_song(self, *, song, instead):
        """Remember what plays, and its scenes and tracks as they are, to find them again after an edit."""
        self._song = song
        self._song_name = None if self._song_is_copy else self.document().current_song_name()
        self._instead = instead
        self._scenes = list(song.get_scenes())
        self._tracks = {name: song.get_track(name) for name in song.get_track_names()}
        self._seen_revision = self.document().revision()
        self._changed_at = None

    def _playing_song(self):
        """Return the song that plays, after an edit: the copy a listening page made, or the current song while it is the one launched, or None when another song was made current."""
        if self._song_is_copy:
            return self._song
        if self.document().current_song_name() != self._song_name:
            return None
        return self.document().song()

    def _follow_edits(self):
        """Hear an edit made while playing, once the edits have settled for LIVE_SETTLE_SECONDS: render the song again with this play's seed and hand the score to the player, which takes it from the moment the song's Live response says."""
        if not self._player.is_playing():
            return
        if self._playing_song() is None:
            # Another song was made current, so what plays stops at once, since nothing on screen could show or stop it any more.
            self.stop_all()
            return
        revision = self.document().revision()
        if revision == self._score_revision:
            return
        now = self._clock.now()
        if revision != self._seen_revision:
            self._seen_revision = revision
            self._changed_at = now
            return
        if self._changed_at is not None and now - self._changed_at < LIVE_SETTLE_SECONDS:
            return
        self._score_revision = revision
        song = self._playing_song()
        routes = self.routes(instead=self._instead)
        if set(route.port for route in routes.values()) - set(self._ports):
            self._live_message = MSG_LIVE_EDIT_NEEDS_A_DEVICE
            return
        try:
            score = Score(song=song, routes=routes, seed=self._seed)
        except (SongFileError, ValueError) as error:
            self._live_message = MSG_LIVE_EDIT_NOT_HEARD.format(problem=error)
            return
        scene_map, track_map = self._places_after_the_edit(song)
        self._player.update_score(score=score, responsiveness=song.get_live_responsiveness(), scene_map=scene_map, track_map=track_map)
        self._score_key = (id(song), tuple(sorted(routes.items())))
        self._remember_song(song=song, instead=self._instead)

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

    def _sender_for(self, ports):
        """Return the sender, started on the ports, starting another when the ports it opened aren't these, or when FluidSynth was started again and its port is new."""
        if FLUIDSYNTH_PORT in ports and self._fluidsynth.ensure_running() and self._sender is not None and FLUIDSYNTH_PORT in self._ports:
            self._ports = [port for port in self._ports if port != FLUIDSYNTH_PORT]
        if self._sender is not None and set(ports) - set(self._ports):
            self.stop_all()
            self._sender.close()
            self._sender = None
            self._player = None
        if self._sender is None:
            self._ports = list(ports)
            self._zero = self._clock.now()
            self._sender = self._make_sender(self._ports)
            self._sender.start(at=self._zero)
        return self._sender

    def _process_sender(self, ports):
        return RealtimeMIDISenderProcess(ports=ports)

    def _now(self):
        return self._clock.now() - self._zero

    def _run(self):
        if self._timer is None and self._set_timer is not None:
            self._timer = self._set_timer(seconds=TICK_SECONDS, tick=self.tick)

    def _stop_timer(self):
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

