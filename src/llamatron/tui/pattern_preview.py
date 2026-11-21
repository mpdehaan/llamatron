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

"""The pattern preview: Listen on the Patterns page and in the pattern editor.

One key plays a pattern at once, again and again, and the same key stops it, whether the set's
Real Time switch is on or off. The preview has a
player and a Realtime Sender Process of its own beside the song's, so that it never stops or
restarts a song played from Arrange and is heard over it, starting at once on a clock of its own.

What it plays is a copy of the set whose current song holds one scene: the pattern's clip, on a
track made for it. The clip plays in the pattern's own direction, for as many passes as the
direction takes to come round, in the scale of the first clip that uses the pattern, or the song's.
It sounds through the song's Preview instrument, or General MIDI's piano through FluidSynth when
the song names none, and a drum pattern through General MIDI's drum kit. An edit made while it
plays is heard at the pattern's next pass, since the copy is made again when the set changes.

A sound is tried the same way (play_sound): some notes written for the trial, played once through
General MIDI in FluidSynth, in a sound chosen or on the drum kit, which a picker of sounds does.
"""

from math import lcm

from llamatron.composition import limits
from llamatron.composition.clip_slot import ClipSlot
from llamatron.composition.file_format import LiveResponsiveness, PatternSetting, Row, Section, SongSetting
from llamatron.composition.naming import unique_name
from llamatron.composition.pattern import Pattern
from llamatron.composition.scene import Scene
from llamatron.composition.setlist import Setlist
from llamatron.composition.track import Track
from llamatron.exporters import midi_arrangement
from llamatron.music import note
from llamatron.playback.step_order import walk_order
from llamatron.realtime import fluidsynth
from llamatron.realtime.timeline import Route
from llamatron.strings import errors, names as names_text
from llamatron.tui import transport
from llamatron.tui.transport import Transport

# The one scene of the copy the preview plays.
PREVIEW_SCENE = 0
# The FluidSynth channel a preview's notes go to: the last of the melodic channels, which a song takes only with fifteen tracks through FluidSynth, so
# that the preview's program change never changes the sound of a track of the song.
PREVIEW_CHANNEL_BYTE = midi_arrangement.MELODIC_CHANNEL_BYTES[-1]
# General MIDI's first sound, the piano, as the program byte sent.
PIANO_PROGRAM = 0
# How many passes a preview plays of a direction that chooses its steps as it goes: one, as many choices as the pattern has steps.
CHOSEN_PASSES = 1
# A sound is tried once through.
TRIAL_PASSES = 1
NOTES_IN_OCTAVE = 12
# How loud the notes of a sound's trial are.
TRIAL_VELOCITY = 100


def trial_pattern(*, numbers, step_size):
    """Return the data of a pattern that plays some MIDI notes one after another, a step each, written as a drum pattern's
    notes are, by name and octave, so that no scale moves them."""
    names = [note.SHARP_NAMES[number % NOTES_IN_OCTAVE] for number in numbers]
    return {PatternSetting.STEPS: len(numbers), PatternSetting.STEP_SIZE: step_size, PatternSetting.DRUM: True,
            Row.DEGREE: [name[0] for name in names], Row.ACCIDENTAL: [name[1:] or None for name in names],
            Row.OCTAVE: [number // NOTES_IN_OCTAVE for number in numbers], Row.VELOCITY: [TRIAL_VELOCITY] * len(numbers)}


def passes_to_come_round(*, steps, direction):
    """Return how many passes of a pattern a direction takes to come back to where it started, so that a loop of them plays the direction whole."""
    order = walk_order(count=steps, direction=direction)
    if order is None:
        return CHOSEN_PASSES
    return lcm(len(order), steps) // steps


class PreviewSet:
    """What the preview's transport reads as its document: a copy of the set, made again when the set changes, whose current song holds only the pattern's clip."""

    __slots__ = ('_holder', '_pattern', '_clip', '_trial', '_revision', '_setlist', '_track', '_scale')

    def __init__(self, *, holder, pattern=None, clip=None, trial=None):
        """pattern names a pattern to play on a track made for it; clip is (scene, track) for a clip of the song played as it is, with the whole song kept, since the clip may grab from another track."""
        self._holder = holder
        # The data of a pattern written to try a sound with, played once on a track made for it, or None.
        self._trial = trial
        self._pattern = pattern
        self._clip = clip
        self._revision = None
        self._setlist = None
        self._track = None
        self._scale = None

    def real(self):
        return self._holder.get_document()

    def get_revision(self):
        return self.real().get_revision()

    def get_current_song_name(self):
        return self.real().get_current_song_name()

    def get_setlist(self):
        if self._revision != self.get_revision():
            self._copy()
        return self._setlist

    def song(self):
        return self.get_setlist().get_song(self.get_current_song_name())

    def track(self):
        """Return the name of the track that plays: the one made for the pattern, or the clip's own."""
        self.get_setlist()
        return self._track

    def scene(self):
        """Return the place of the scene that plays: the one made for the pattern, or the clip's own."""
        return PREVIEW_SCENE if self._clip is None else self._clip[0]

    def scale(self):
        """Return the name of the scale the pattern plays in, or None for none, as a drum pattern has."""
        self.get_setlist()
        return self._scale

    def _copy(self):
        real = self.real()
        if self._clip is not None:
            self._setlist = Setlist.from_data(data=real.get_setlist().to_data())
            self._track = self._clip[1]
            self._revision = real.get_revision()
            return
        name = real.get_current_song_name()
        data = real.get_setlist().to_data()
        song_data = data[Section.SONGS][name]
        song_data[Section.SCENES] = []
        # An edit is heard at the pattern's next pass, whatever the song's own Live response.
        song_data[SongSetting.LIVE_RESPONSIVENESS] = LiveResponsiveness.CLIP_RESTART
        setlist = Setlist.from_data(data=data)
        song = setlist.get_song(name)
        if self._trial is not None:
            self._copy_trial(setlist=setlist, song=song)
            return
        pattern = song.get_pattern(self._pattern)
        track = unique_name(base=names_text.MSG_PREVIEW_TRACK_NAME, taken=song.get_track_names())
        song.add_item(section=Section.TRACKS, name=track, item=Track(drum=True) if pattern.is_drum() else Track())
        scales = [] if pattern.is_drum() else real.scales_of_pattern(self._pattern)
        clip_slot = ClipSlot()
        clip_slot.set_pattern_name(name=self._pattern, song=song)
        clip_slot.set_repeat(passes_to_come_round(steps=pattern.get_steps(), direction=pattern.get_direction()))
        if scales:
            clip_slot.set_scale_name(name=scales[0], song=song)
        scene = Scene(clip_slots={})
        song.add_scene(index=PREVIEW_SCENE, scene=scene)
        scene.set_clip_slot(track=track, clip_slot=clip_slot, song=song)
        self._setlist = setlist
        self._track = track
        self._scale = scales[0] if scales else None
        self._revision = real.get_revision()


    def _copy_trial(self, *, setlist, song):
        """Finish a copy that plays the pattern written to try a sound with, once, on a drum track made for it, under no scale."""
        name = unique_name(base=names_text.MSG_PREVIEW_PATTERN_NAME, taken=song.get_pattern_names())
        setlist.add_item(section=Section.PATTERNS, name=name, item=Pattern.from_data(data=self._trial, where=name, song=song))
        track = unique_name(base=names_text.MSG_PREVIEW_TRACK_NAME, taken=song.get_track_names())
        song.add_item(section=Section.TRACKS, name=track, item=Track(drum=True))
        clip_slot = ClipSlot()
        clip_slot.set_pattern_name(name=name, song=song)
        clip_slot.set_repeat(TRIAL_PASSES)
        scene = Scene(clip_slots={})
        song.add_scene(index=PREVIEW_SCENE, scene=scene)
        scene.set_clip_slot(track=track, clip_slot=clip_slot, song=song)
        self._setlist = setlist
        self._track = track
        self._scale = None
        self._revision = self.real().get_revision()


class PatternPreview(Transport):
    """Plays one pattern again and again beside whatever the song's transport plays, and answers which step sounds."""

    __slots__ = ('_set', '_pattern', '_clip', '_trial')

    def __init__(self, *, beside):
        """beside is the song's transport, whose clock, FluidSynth and way of making a sender the preview shares."""
        super().__init__(**beside.shared())
        self._set = None
        self._pattern = None
        # The clip of the song, as (scene, track), that plays through General MIDI while the set's Real Time switch is off, when no pattern does.
        self._clip = None
        # The sound being tried, as (the program byte, or None for the drum kit; what the asker tells the trial by), while one is.
        self._trial = None

    def real(self):
        """Return the document the tracker edits, where document() is the copy the preview plays."""
        return self._document_holder.get_document()

    def document(self):
        return self._set

    # Whether a pattern can be heard.

    def instrument_of(self, pattern):
        """Return the name of the instrument a pattern previews through, or None for General MIDI through FluidSynth: the song's Preview instrument, but for a drum pattern, which always plays General MIDI's drum kit."""
        real = self.real()
        if real.song().get_pattern(pattern).is_drum():
            return None
        return real.song().get_preview_instrument_name()

    def can_sound(self, pattern):
        """Return whether Listen is offered for a pattern: the song names a Preview instrument for it, or FluidSynth is installed to play General MIDI."""
        return self.instrument_of(pattern) is not None or self._fluidsynth_installed()

    def refusal(self, pattern):
        """Return why a pattern's Preview instrument cannot sound, for the status line, or None when it can."""
        name = self.instrument_of(pattern)
        if name is None:
            return None
        instrument = self.real().get_setlist().get_instrument(name)
        if not instrument.has_device():
            return errors.ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE.format(name=name)
        if instrument.uses_fluidsynth():
            return None if self._fluidsynth_installed() else errors.ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED.format(name=name)
        if not self.is_connected(instrument.get_device()):
            return errors.ERR_PREVIEW_DEVICE_NOT_CONNECTED.format(name=name, device=instrument.get_device())
        return None

    def shares_a_channel_with(self, *, pattern, routes):
        """Return whether a pattern's preview would choose its sound on a port and channel that one of a song's routes uses, which only a song with
        fifteen tracks through FluidSynth comes to. A drum pattern chooses no sound, so it shares the drum channel freely."""
        if self.real().song().get_pattern(pattern).is_drum():
            return False
        name = self.instrument_of(pattern)
        if name is not None and not self.real().get_setlist().get_instrument(name).uses_fluidsynth():
            return False
        return any((route.port, route.channel) == (fluidsynth.FLUIDSYNTH_PORT, PREVIEW_CHANNEL_BYTE) for route in routes.values())

    def routes(self, *, instead=None):
        """Return the one route of the track made for the pattern."""
        if self._set is None:
            return {}
        return {self._set.track(): self._route()}

    def general_midi_is_installed(self):
        """Return whether FluidSynth is installed, to play General MIDI."""
        return self._fluidsynth_installed()

    def _clip_is_drums(self):
        """Return whether the clip that plays is drums: its track is a drum track, or its pattern a drum pattern."""
        song = self.real().song()
        index, track = self._clip
        clip_slot = song.get_scenes()[index].get_clip_slot(track)
        return song.get_track(track).is_drum() or song.get_pattern(clip_slot.get_pattern_name()).is_drum()

    def _route(self):
        real = self.real()
        if self._trial is not None:
            program, _ = self._trial
            if not self._fluidsynth_installed():
                # Without FluidSynth a sound is tried on the song's Preview instrument, which plays the notes in whatever sound the device has.
                instrument = real.get_setlist().get_instrument(real.song().get_preview_instrument_name())
                return Route(instrument.get_device(), instrument.get_channel() - transport.CHANNEL_OFFSET)
            return Route(fluidsynth.FLUIDSYNTH_PORT, midi_arrangement.DRUM_CHANNEL_BYTE, None, keyswitches=False) if program is None else Route(fluidsynth.FLUIDSYNTH_PORT, PREVIEW_CHANNEL_BYTE, program, keyswitches=False)
        if self._clip is not None:
            return Route(fluidsynth.FLUIDSYNTH_PORT, midi_arrangement.DRUM_CHANNEL_BYTE, None, keyswitches=False) if self._clip_is_drums() else Route(fluidsynth.FLUIDSYNTH_PORT, PREVIEW_CHANNEL_BYTE, PIANO_PROGRAM, keyswitches=False)
        if real.song().get_pattern(self._pattern).is_drum():
            return Route(fluidsynth.FLUIDSYNTH_PORT, midi_arrangement.DRUM_CHANNEL_BYTE, None, keyswitches=False)
        name = self.instrument_of(self._pattern)
        if name is None:
            return Route(fluidsynth.FLUIDSYNTH_PORT, PREVIEW_CHANNEL_BYTE, PIANO_PROGRAM, keyswitches=False)
        instrument = real.get_setlist().get_instrument(name)
        if instrument.uses_fluidsynth():
            sound = instrument.get_gm_sound()
            return Route(fluidsynth.FLUIDSYNTH_PORT, PREVIEW_CHANNEL_BYTE, None if sound is None else sound - limits.MIN_GM_SOUND, keyswitches=False)
        return Route(instrument.get_device(), instrument.get_channel() - transport.CHANNEL_OFFSET)

    # Playing.

    def may_play(self):
        """Return that a preview plays whatever the set's Real Time switch says, since it needs none of the tracks' instruments."""
        return True

    def play(self, pattern):
        """Play a pattern at once, again and again, in place of any pattern the preview played."""
        self.stop()
        self._pattern = pattern
        self._set = PreviewSet(holder=self._document_holder, pattern=pattern)
        try:
            self.play_clip(index=self._set.scene(), track=self._set.track(), forever=True)
        except Exception:
            self.stop()
            raise

    def play_clip_of_song(self, *, index, track):
        """Play a clip of the song as its scene would, again and again, through General MIDI in FluidSynth: the piano, or the drum kit for drums. The clip page listens this way while the set's Real Time switch is off."""
        self.stop()
        self._clip = (index, track)
        self._set = PreviewSet(holder=self._document_holder, clip=self._clip)
        try:
            self.play_clip(index=index, track=track, forever=True)
        except Exception:
            self.stop()
            raise

    def sound_refusal(self):
        """Return why a sound cannot be tried, for a picker to say, or None when it can: FluidSynth plays it, or else the song's Preview instrument
        does, where it is an instrument on a device of its own that is connected."""
        if self._fluidsynth_installed():
            return None
        real = self.real()
        name = real.song().get_preview_instrument_name()
        if name is None:
            return errors.ERR_NOTHING_TO_TRY_A_SOUND_WITH
        instrument = real.get_setlist().get_instrument(name)
        if not instrument.has_device():
            return errors.ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE.format(name=name)
        if instrument.uses_fluidsynth():
            return errors.ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED.format(name=name)
        if not self.is_connected(instrument.get_device()):
            return errors.ERR_PREVIEW_DEVICE_NOT_CONNECTED.format(name=name, device=instrument.get_device())
        return None

    def play_sound(self, *, numbers, step_size, sound, key):
        """Try a sound: play some MIDI notes once, a step each, through General MIDI in FluidSynth, in a General MIDI sound, or on
        the drum kit where sound is None; without FluidSynth, on the song's Preview instrument, in the device's own sound. key is
        whatever the asker tells one trial from another by, answered by playing_sound()."""
        self.stop()
        self._trial = (None if sound is None else sound - limits.MIN_GM_SOUND, key)
        self._set = PreviewSet(holder=self._document_holder, trial=trial_pattern(numbers=numbers, step_size=step_size))
        try:
            self.play_clip(index=self._set.scene(), track=self._set.track())
        except Exception:
            self.stop()
            raise

    def playing_sound(self):
        """Return the key of the sound being tried while its notes play, or None."""
        return self._trial[1] if self._trial is not None and self.is_playing() else None

    def playing_clip(self):
        """Return the clip of the song that plays through General MIDI, as (scene, track), or None."""
        return self._clip if self.is_playing() else None

    def stop(self):
        """Stop the pattern, leaving whatever the song's transport plays."""
        self.stop_all()
        self._pattern = None
        self._clip = None
        self._trial = None
        self._set = None
        self._drop_score()

    def forget(self):
        self.stop()

    def close(self):
        """Stop the pattern and end the preview's process, as the tracker quits; FluidSynth is the song's transport's to end."""
        self.stop()
        self._end_playback()

    def tick(self):
        """Stop when the pattern has gone, by a rename or a delete, or its Preview instrument has, and otherwise tick as the song's transport does."""
        if self._set is None:
            self._stop_timer()
            return
        if self._has_gone():
            self.stop()
            return
        super().tick()
        if not self.is_playing():
            self.stop()

    def _has_gone(self):
        """Return whether what plays is no longer in the set: the pattern, the song's Preview instrument, or the clip."""
        real = self.real()
        song = real.song()
        if self._trial is not None:
            return False
        if self._clip is not None:
            index, track = self._clip
            return index >= len(song.get_scenes()) or not song.has_item(section=Section.TRACKS, name=track) or song.get_scenes()[index].get_clip_slot(track) is None
        name = song.get_preview_instrument_name()
        return not song.has_pattern(self._pattern) or (name is not None and not real.get_setlist().has_instrument(name))

    # What is playing.

    def playing_pattern(self):
        """Return the name of the pattern that plays, or None."""
        return self._pattern if self.is_playing() else None

    def scale(self):
        """Return the name of the scale the pattern plays in, or None."""
        return None if self._set is None else self._set.scale()
