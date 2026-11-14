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

"""The Document's edits to the current song: its settings, tracks, scenes, registers and clips, and which groove each chooses."""


from llamatron.composition.clip_slot import ClipSlot, FIRST_MORPH_STYLE
from llamatron.composition.file_format import ClipSlotSetting, RegisterSetting, Section
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.limits import MIN_REPEAT
from llamatron.composition.scene import Scene
from llamatron.composition.track import Track
from llamatron.composition.naming import copy_name
from llamatron.strings.names import MSG_SCENE_WITHOUT_A_NAME



class SongEdits:
    """The changes the Song, Arrange, Scene, Clip, Track and Registers pages make to the current song, each through the song's own setters.

    It holds no data of its own: it works on what Document keeps, through `self._setlist`,
    `self.song()` and `self._change(method, ...)`, which makes one change through an object's own
    method and notes it.
    """

    __slots__ = ()

    # The current song's own settings, from the Song page.

    def set_tempo(self, tempo):
        self._change(self.song().set_tempo, tempo)

    def set_time_signature(self, text):
        """Set the song's time signature, written like 6/8."""
        self._change(self.song().set_time_signature, text)

    def set_entry_size(self, entry_size):
        """Set how long a note placed on a piano roll lasts unless the pattern says otherwise, written like 1/8, or None for one step."""
        self._change(self.song().set_entry_size, entry_size)

    def set_scale_name(self, name):
        """Give the song a scale by name, or None for no scale."""
        self._change(self.song().set_scale_name, name)

    def set_seed(self, seed):
        self._change(self.song().set_seed, seed)

    def set_genre(self, text):
        self._change(self.song().set_genre, text)

    def set_live_responsiveness(self, value):
        self._change(self.song().set_live_responsiveness, value)

    def set_preview_instrument_name(self, name):
        """Choose the instrument Listen plays a pattern through in the current song, or None for the pattern's own track."""
        self._change(self.song().set_preview_instrument_name, name)

    def set_song_visualizer(self, name):
        """Name the visualizer mode Arrange shows first for the current song, or None to take the set's."""
        self._change(self.song().set_visualizer, name)

    # Tracks, of the current song.

    def _track(self, name):
        return self.song().get_track(name)

    def add_track(self, name):
        self._change(self.song().add_item, section=Section.TRACKS, name=name, item=Track())

    def insert_track(self, *, name, place):
        """Add a new track with no clips before the track at a place, which the Arrange page's I does."""
        self._change(self.song().insert_item, section=Section.TRACKS, name=name, item=Track(), place=place)

    def track_names(self):
        return self.song().get_track_names()

    def set_track_drum(self, *, name, drum):
        self._change(self._track(name).set_drum, drum)

    def set_track_mute(self, *, name, muted):
        self._change(self._track(name).set_mute, muted)

    def set_track_transpose(self, *, name, transpose):
        """Set how far a track moves its notes along the scale, left out of the file when it's 0."""
        self._change(self._track(name).set_transpose, transpose)

    def set_track_lowest_octave(self, *, name, octave):
        """Set the lowest octave a track's instrument plays, left out of the file at the bottom of the MIDI range."""
        self._change(self._track(name).set_lowest_octave, octave)

    def set_track_highest_octave(self, *, name, octave):
        """Set the highest octave a track's instrument plays, left out of the file at the top of the MIDI range."""
        self._change(self._track(name).set_highest_octave, octave)

    def set_track_cc_number(self, *, name, lane, number):
        """Set the CC number one of a track's four lanes sends, or None for a lane that sends nothing."""
        self._change(self._track(name).set_cc_number, lane=lane, number=number)

    def set_track_cc_register(self, *, name, lane, register):
        """Bind one of a track's four CC lanes to a register by name, or None to unbind it."""
        self._change(self._track(name).set_cc_register, lane=lane, register=register)

    def set_track_velocity_register(self, *, name, register):
        """Bind a track's velocity to a register by name, or None to unbind it."""
        self._change(self._track(name).set_velocity_register, register)

    def set_track_strum_setting(self, *, name, part, value):
        """Set one part of a track's strum, or None to leave it blank."""
        self._change(self._track(name).set_strum_setting, part=part, value=value)

    def set_track_euclid_setting(self, *, name, part, value):
        """Set one part of a track's Euclidean mask, or None to leave it blank."""
        self._change(self._track(name).set_euclid_setting, part=part, value=value)

    def set_clip_strum_setting(self, *, index, track, part, value):
        """Set one part of a clip's strum, or None to leave it blank and take its track's."""
        self._change(self.clip_slot(index=index, track=track).set_strum_setting, part=part, value=value)

    def set_scene_shape_setting(self, *, index, name, value):
        """Set one part of a scene's Density, Swell or Articulate, by its file name like density_start, or None to leave it blank."""
        self._change(self._scene(index).set_shape_setting, name=name, value=value)

    def set_clip_shape_setting(self, *, index, track, name, value):
        """Set one part of a clip's Density, Swell or Articulate, by its file name, or None to leave it blank and take the scene's."""
        self._change(self.clip_slot(index=index, track=track).set_shape_setting, name=name, value=value)

    def set_scene_chains(self, *, index, names):
        """Set the chains every clip of a scene runs, by name, in order."""
        self._change(self._scene(index).set_chain_names, names=names, song=self.song())

    def set_track_chains(self, *, name, names):
        """Set the chains every clip on a track runs, by name, in order."""
        self._change(self._track(name).set_chain_names, names=names, song=self.song())

    def grab_circle(self, *, index, track, other):
        """Return the tracks a grab would go round in a circle, like [lead, bass, lead], or None."""
        return self.song().get_scene(index).grab_circle(track=track, other=other)

    # Which groove the song, a scene or a track chooses.

    def set_groove_name(self, name):
        """Choose the current song's groove by name."""
        self._change(self.song().set_groove_name, name)

    def set_scene_groove(self, *, index, choice):
        """Choose a scene's groove by name, False for none there, or None to take the song's."""
        self._change(self._scene(index).set_groove_choice, choice=choice, song=self.song())

    def set_track_instrument(self, *, name, instrument):
        """Send a track to an instrument of the set in real-time playback, or None for none."""
        song = self.song()
        self._change(song.get_track(name).set_instrument_name, name=instrument, song=song)

    def set_track_groove(self, *, name, choice):
        """Choose a track's groove by name, False for none there, or None to take the scene's or the song's."""
        self._change(self._track(name).set_groove_choice, choice=choice, song=self.song())

    # Scenes, of the current song.

    def _scene(self, index):
        return self.song().get_scene(index)

    def add_scene(self, *, index, name):
        self._change(self.song().add_scene, index=index, scene=Scene(clip_slots={}, name=name))

    def copy_scene(self, index):
        """Put a copy of a scene right after it, named after it."""
        taken = {scene.get_name() for scene in self.song().get_scenes()}
        name = self._scene(index).get_name()
        new = copy_name(name=MSG_SCENE_WITHOUT_A_NAME if name is None else name, taken=taken)
        self._change(self.song().copy_scene, index=index, name=new)

    def delete_scene(self, index):
        self._change(self.song().remove_scene, index)

    def move_scene(self, *, index, offset):
        if not self.song().move_scene(index=index, offset=offset):
            return False
        self.changed()
        return True

    # Registers, of the current song. There are always four, and the file only holds the settings that differ from the defaults.

    def register(self, name):
        """Return a register, AX to DX, as a Register, with its defaults for anything not set."""
        return self.song().get_register(name)

    def set_register_setting(self, *, name, setting, value):
        """Change one setting of a register, or return why it can't change, like a default above the maximum.

        A value of None goes back to the setting's default. A lower Allowed Inc Max brings every add
        to that register within it, in every pattern the song plays, as one change.
        """
        try:
            self._change(self.song().set_register_setting, name=name, setting=setting, value=value)
        except InvalidValue as problem:
            return str(problem)
        if setting == RegisterSetting.ALLOWED_INC_MAX:
            self._change(self._setlist.hold_adds_within_limits)
        return None

    def resets(self, *, index, register):
        """Return whether a scene sets a register back to its default as it starts."""
        return self._scene(index).resets(register)

    def set_reset(self, *, index, register, on):
        """Make a scene set a register back to its default as it starts, or stop it."""
        self._change(self._scene(index).set_reset, register=register, on=on)

    def set_scene_launch_together(self, *, index, value):
        """Make a start reaching any clip of a scene launch the whole scene in real-time playback, or not."""
        self._change(self._scene(index).set_launch_together, value)

    def set_scene_repeat(self, *, index, repeat):
        self._change(self._scene(index).set_repeat, repeat)

    def set_scene_name(self, *, index, name):
        self._change(self._scene(index).set_name, name)

    def set_scene_scale(self, *, index, name):
        """Set the scale a scene uses instead of the song's, or None to use the song's."""
        self._change(self._scene(index).set_scale_name, name=name, song=self.song())

    def set_scene_tempo(self, *, index, tempo):
        """Set a scene's tempo, which is where its ramp starts if it has one."""
        self._change(self._scene(index).set_tempo, tempo)

    def clear_scene_tempo(self, index):
        """Make a scene use the song's tempo, dropping any ramp."""
        self._change(self._scene(index).clear_tempo)

    def set_scene_tempo_ramp(self, *, index, end):
        """Make a scene's tempo ramp to a value across its repeats, from its tempo or the song's."""
        scene = self._scene(index)
        start = scene.get_tempo_setting()
        if start is None:
            start = scene.get_tempo_start()
        if start is None:
            start = self.song().get_tempo()
        self._change(scene.set_tempo_ramp, start=start, end=end)

    def clear_scene_tempo_ramp(self, index):
        """Stop a scene's tempo ramping, keeping where it started as its tempo."""
        self._change(self._scene(index).clear_tempo_ramp)

    # Clips, of the current song.

    def clip_slot(self, *, index, track):
        """Return the ClipSlot a track plays in a scene, or None if it plays nothing there."""
        return self._scene(index).get_clip_slot(track)

    def add_clip_slot(self, *, index, track, pattern):
        """Give a track a clip in a scene, playing a pattern once."""
        clip_slot = ClipSlot()
        clip_slot.set_pattern_name(name=pattern, song=self.song())
        self._change(self._scene(index).set_clip_slot, track=track, clip_slot=clip_slot, song=self.song())

    def paste_clip_slot(self, *, index, track, copied):
        """Put a copy of a clip slot on a track in a scene, and return the track a grab was dropped from, or None.

        A pasted clip can't grab from its own track or in a circle, so then it keeps its own notes.
        """
        clip_slot = copied.copy()
        other = clip_slot.get_grab_track()
        dropped = None
        if other is not None and (other == track or self.grab_circle(index=index, track=track, other=other)):
            clip_slot.clear_grab()
            dropped = other
        self._change(self._scene(index).set_clip_slot, track=track, clip_slot=clip_slot, song=self.song())
        return dropped

    def set_clip_slot_setting(self, *, index, track, setting, value):
        """Set one setting of a clip slot by its file name, or None to leave it out and use its default."""
        clip_slot = self.clip_slot(index=index, track=track)
        song = self.song()
        if setting == ClipSlotSetting.NAME:
            self._change(clip_slot.set_name, value)
        elif setting == ClipSlotSetting.PATTERN:
            self._change(clip_slot.set_pattern_name, name=value, song=song)
        elif setting == ClipSlotSetting.CHAINS:
            self._change(clip_slot.set_chain_names, names=value, song=song)
        elif setting == ClipSlotSetting.CHAIN:
            # One chain by name, as a file from before lists of chains held it.
            self._change(clip_slot.set_chain_names, names=None if value is None else [value], song=song)
        elif setting == ClipSlotSetting.LOOP:
            self._change(clip_slot.set_loop, bool(value))
        elif setting == ClipSlotSetting.REPEAT:
            self._change(clip_slot.set_repeat, value)
        elif setting == ClipSlotSetting.DIRECTION:
            self._change(clip_slot.set_direction, value)
        elif setting == ClipSlotSetting.MORPH_TO:
            self.set_clip_slot_morph_target(index=index, track=track, pattern=value)
        elif setting == ClipSlotSetting.MORPH_STYLE:
            self._change(clip_slot.set_morph_style, value)
        elif setting == ClipSlotSetting.GRAB_TRACK:
            self._change(clip_slot.set_grab_track, name=value, song=song, own_track=track)
        elif setting == ClipSlotSetting.FOLLOW_ACTION:
            self._change(clip_slot.set_follow_action, value)
        elif setting == ClipSlotSetting.SCALE:
            self._change(clip_slot.set_scale_name, name=value, song=song)

    def set_clip_slot_repeat(self, *, index, track, repeat):
        """Set how many times a clip plays. Going back to once drops its morph, which runs across repeats."""
        self._change(self.clip_slot(index=index, track=track).set_repeat, max(repeat, MIN_REPEAT))

    def set_clip_slot_morph_target(self, *, index, track, pattern):
        """Make a clip morph to a pattern across its repeats, in the first style unless it has one."""
        clip_slot = self.clip_slot(index=index, track=track)
        style = clip_slot.get_morph_style_name() or FIRST_MORPH_STYLE
        self._change(clip_slot.set_morph, target=pattern, style=style, song=self.song())

    def clear_clip_slot_morph(self, *, index, track):
        self._change(self.clip_slot(index=index, track=track).clear_morph)

    def move_clip_slot(self, *, index, track, to_index, to_track):
        """Move a clip slot to an empty cell, and return the track a grab was dropped from, as a paste would, or None."""
        clip_slot = self.clip_slot(index=index, track=track)
        self.delete_clip_slot(index=index, track=track)
        return self.paste_clip_slot(index=to_index, track=to_track, copied=clip_slot)

    def delete_clip_slot(self, *, index, track):
        self._change(self._scene(index).remove_clip_slot, track)
