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


from types import MethodType

from llamatron.composition import clip_slot as clip_slot_values, limits
from llamatron.composition.clip_slot import ClipSlot
from llamatron.composition.file_format import ClipSlotSetting, RegisterSetting, Section
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.naming import copy_name
from llamatron.composition.scene import Scene
from llamatron.composition.track import Track
from llamatron.strings import names as names_text


# What a setter that takes a name of the song, or several, calls what it is given.
ONE_NAME = 'name'
MANY_NAMES = 'names'
# The clip slot settings that are set by handing the setter the value alone.
CLIP_SLOT_SETTERS = {
    ClipSlotSetting.NAME: ClipSlot.set_name,
    ClipSlotSetting.PATTERN_ORDER: ClipSlot.set_pattern_order,
    ClipSlotSetting.REPEAT: ClipSlot.set_repeat,
    ClipSlotSetting.DIRECTION: ClipSlot.set_direction,
    ClipSlotSetting.MORPH_STYLE: ClipSlot.set_morph_style,
    ClipSlotSetting.FOLLOW_ACTION: ClipSlot.set_follow_action,
}
# The clip slot settings that name things of the song: each setter, and what it calls the value, checked against the song.
CLIP_SLOT_NAME_SETTERS = {
    ClipSlotSetting.PATTERN: (ClipSlot.set_pattern_name, ONE_NAME),
    ClipSlotSetting.PATTERNS: (ClipSlot.set_pattern_names, MANY_NAMES),
    ClipSlotSetting.CHAINS: (ClipSlot.set_chain_names, MANY_NAMES),
    ClipSlotSetting.SCALE: (ClipSlot.set_scale_name, ONE_NAME),
}


class SongEdits:
    """The changes the Song, Arrange, Scene, Clip, Track and Registers pages make to the current song, each through the song's own setters.

    It holds no data of its own: it works on what Document keeps, through `self._setlist`,
    `self.song()` and `self.change(method, ...)`, which makes one change through an object's own
    method and notes it.
    """

    __slots__ = ()

    # The current song's own settings, from the Song page.

    # Tracks, of the current song.

    def _track(self, name):
        return self.song().get_track(name)

    def add_track(self, name):
        self.change(self.song().add_item, section=Section.TRACKS, name=name, item=Track())

    def insert_track(self, *, name, place):
        """Add a new track with no clips before the track at a place, which the Arrange page's I does."""
        self.change(self.song().insert_item, section=Section.TRACKS, name=name, item=Track(), place=place)

    def track_names(self):
        return self.song().get_track_names()

    def grab_circle(self, *, index, track, other):
        """Return the tracks a grab would go round in a circle, like [lead, bass, lead], or None."""
        return self.song().get_scene(index).grab_circle(track=track, other=other)

    # Which groove the song, a scene or a track chooses.

    def set_track_instrument(self, *, name, instrument):
        """Send a track to an instrument of the set in real-time playback, or None for none."""
        song = self.song()
        self.change(song.get_track(name).set_instrument_name, name=instrument, song=song)

    # Scenes, of the current song.

    def _scene(self, index):
        return self.song().get_scene(index)

    def add_scene(self, *, index, name):
        self.change(self.song().add_scene, index=index, scene=Scene(clip_slots={}, name=name))

    def copy_scene(self, index):
        """Put a copy of a scene right after it, named after it."""
        taken = {scene.get_name() for scene in self.song().get_scenes()}
        name = self._scene(index).get_name()
        new = copy_name(name=names_text.MSG_SCENE_WITHOUT_A_NAME if name is None else name, taken=taken)
        self.change(self.song().copy_scene, index=index, name=new)

    def move_scene(self, *, index, offset):
        if not self.song().move_scene(index=index, offset=offset):
            return False
        self.changed()
        return True

    # Registers, of the current song. There are always four, and the file only holds the settings that differ from the defaults.

    def register(self, name):
        """Return a register, AX to DX, as a Register, with its defaults for anything not set."""
        return self.song().get_register(name)

    def modulator_range(self):
        """Return the lowest and highest values a modulator's minimum, start and maximum may take."""
        return limits.MIN_REGISTER_VALUE, limits.MAX_REGISTER_VALUE

    def hertz_range(self):
        """Return the slowest and fastest rate in hertz a modulator may have, and how many steps a hertz is set in."""
        return limits.MIN_HERTZ, limits.MAX_HERTZ, limits.HERTZ_STEPS

    def modulator(self, name):
        """Return a modulator, XMod to ZMod, as a Modulator, with its defaults for anything not set."""
        return self.song().get_modulator(name)

    def set_modulator_setting(self, *, name, setting, value):
        """Change one setting of a modulator, or return why it can't change, like a start above the maximum. None goes back to the default."""
        try:
            self.change(self.song().set_modulator_setting, name=name, setting=setting, value=value)
        except InvalidValue as problem:
            return str(problem)
        return None

    def set_register_setting(self, *, name, setting, value):
        """Change one setting of a register, or return why it can't change, like a default above the maximum.

        A value of None goes back to the setting's default. A lower Allowed Inc Max brings every add
        to that register within it, in every pattern the song plays, as one change.
        """
        try:
            self.change(self.song().set_register_setting, name=name, setting=setting, value=value)
        except InvalidValue as problem:
            return str(problem)
        if setting == RegisterSetting.ALLOWED_INC_MAX:
            self.change(self._setlist.hold_adds_within_limits)
        return None

    def resets(self, *, index, register):
        """Return whether a scene sets a register back to its default as it starts."""
        return self._scene(index).resets(register)

    # Clips, of the current song.

    def clip_slot(self, *, index, track):
        """Return the ClipSlot a track plays in a scene, or None if it plays nothing there."""
        return self._scene(index).get_clip_slot(track)

    def add_clip_slot(self, *, index, track, pattern):
        """Give a track a clip in a scene, playing a pattern once."""
        clip_slot = ClipSlot()
        clip_slot.set_pattern_name(name=pattern, song=self.song())
        self.change(self._scene(index).set_clip_slot, track=track, clip_slot=clip_slot, song=self.song())

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
        self.change(self._scene(index).set_clip_slot, track=track, clip_slot=clip_slot, song=self.song())
        return dropped

    def set_clip_slot_setting(self, *, index, track, setting, value):
        """Set one setting of a clip slot by its file name, or None to leave it out and use its default."""
        clip_slot = self.clip_slot(index=index, track=track)
        song = self.song()
        if setting in CLIP_SLOT_SETTERS:
            self.change(MethodType(CLIP_SLOT_SETTERS[setting], clip_slot), value)
        elif setting in CLIP_SLOT_NAME_SETTERS:
            setter, named = CLIP_SLOT_NAME_SETTERS[setting]
            self.change(MethodType(setter, clip_slot), song=song, **{named: value})
        elif setting == ClipSlotSetting.LOOP:
            self.change(clip_slot.set_loop, bool(value))
        elif setting == ClipSlotSetting.MORPH_TO:
            self.set_clip_slot_morph_target(index=index, track=track, pattern=value)
        elif setting == ClipSlotSetting.GRAB_TRACK:
            self.change(clip_slot.set_grab_track, name=value, song=song, own_track=track)

    def set_clip_slot_repeat(self, *, index, track, repeat):
        """Set how many times a clip plays. Going back to once drops its morph, which runs across repeats."""
        self.change(self.clip_slot(index=index, track=track).set_repeat, max(repeat, limits.MIN_REPEAT))

    def set_clip_slot_morph_target(self, *, index, track, pattern):
        """Make a clip morph to a pattern across its repeats, in the first style unless it has one."""
        clip_slot = self.clip_slot(index=index, track=track)
        style = clip_slot.get_morph_style_name() or clip_slot_values.FIRST_MORPH_STYLE
        self.change(clip_slot.set_morph, target=pattern, style=style, song=self.song())

    def move_clip_slot(self, *, index, track, to_index, to_track):
        """Move a clip slot to an empty cell, and return the track a grab was dropped from, as a paste would, or None."""
        clip_slot = self.clip_slot(index=index, track=track)
        self.change(self.song().get_scene(index).remove_clip_slot, track)
        return self.paste_clip_slot(index=to_index, track=to_track, copied=clip_slot)
