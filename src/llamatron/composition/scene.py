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

"""A scene: a row of the song, launching one clip slot on each track that has one.

Its settings and clip slots are changed through its setters, which check a value the way reading a
file does and raise InvalidValue if it's wrong, with the song passed in wherever a setting names
something the song holds.
"""


from llamatron.support.rational import Rational
from llamatron.composition.clip_slot import ClipSlot
from llamatron.composition.chain import check_chain_names
from llamatron.composition.shapes import shape_settings, shape_values
from llamatron.composition.checks import check_keys, listed, number, reading
from llamatron.composition.defaults import DEFAULT_LAUNCH_TOGETHER, DEFAULT_REPEAT
from llamatron.composition.file_format import REGISTER_NAMES, SceneSetting, Section
from llamatron.composition.groove import check_groove_choice
from llamatron.composition.limits import MAX_SCENE_REPEAT, MIN_REPEAT
from llamatron.composition.llama_data import LlamaData, data_as_kept, data_built_anew, own_copy, written_settings
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.setting import Checked, Flag, WholeNumber, check_settings, described
from llamatron.strings.errors import (
    ERR_BAD_REPEAT, ERR_BAD_RESET, ERR_LAUNCH_TOGETHER_NOT_TRUE_OR_FALSE, ERR_NO_CLIP_SLOT, ERR_NO_SUCH_REGISTER, ERR_NO_SUCH_TRACK, ERR_RAMP_NEEDS_BOTH, ERR_SCENE_EXPECTED_SETTINGS,
    ERR_SCENE_NAME_NOT_TEXT, ERR_SCENE_NO_SUCH_SCALE,
)
from llamatron.support.revised import notes_change

# How far through a tempo ramp a scene that plays only once is: at its start.
NO_RAMP = 0


def _check_scene_name(name):
    if not isinstance(name, str):
        raise InvalidValue(ERR_SCENE_NAME_NOT_TEXT.format(value=name))


def _check_scale_name(*, value, song):
    """Refuse a scale the song doesn't have. None is no scale of the scene's own."""
    if value is not None and not song.has_scale(value):
        raise InvalidValue(ERR_SCENE_NO_SUCH_SCALE.format(scale=value))


def is_register_list(value):
    """Return whether a value is a list of register names, each at most once."""
    return isinstance(value, list) and all(name in REGISTER_NAMES for name in value) and len(set(value)) == len(value)


def _check_reset(value):
    if not is_register_list(value):
        raise InvalidValue(ERR_BAD_RESET.format(names=listed(REGISTER_NAMES), value=value))


# A scene's settings, each described once, in the order they're written to a file, before its tracks.
SETTINGS = described(
    Checked(name=SceneSetting.NAME, check=_check_scene_name),
    WholeNumber(name=SceneSetting.REPEAT, lowest=MIN_REPEAT, highest=MAX_SCENE_REPEAT, error=ERR_BAD_REPEAT),
    Checked(name=SceneSetting.SCALE, check=_check_scale_name, needs_song=True),
    Checked(name=SceneSetting.TEMPO, check=number),
    Checked(name=SceneSetting.TEMPO_START, check=number),
    Checked(name=SceneSetting.TEMPO_END, check=number),
    Checked(name=SceneSetting.RESET, check=_check_reset),
    Checked(name=SceneSetting.GROOVE, check=check_groove_choice, needs_song=True),
    Flag(name=SceneSetting.LAUNCH_TOGETHER, error=ERR_LAUNCH_TOGETHER_NOT_TRUE_OR_FALSE),
    Checked(name=SceneSetting.CHAINS, check=check_chain_names, needs_song=True),
    *shape_settings(),
)
# The settings a file is read without the plain check of: a name is kept as the file writes it, a number too, and
# which of the tempo and its ramp are read depends on which the file gives (_check_tempo).
READ_ANOTHER_WAY = (SceneSetting.NAME, SceneSetting.TEMPO, SceneSetting.TEMPO_START, SceneSetting.TEMPO_END)


class Scene(LlamaData):
    """A name, how many times it repeats, an optional scale and tempo, and a clip slot for each track it plays.

    Settings the file leaves out are kept as None, meaning their defaults. Its scale is kept as
    the name of one of the song's scales.
    """

    __slots__ = ('_settings', '_clip_slots')

    # A scene names the scale and the groove it chooses. Its clips name things too, and are its referring parts.
    REFERENCES = {Section.SCALES: (SceneSetting.SCALE,), Section.GROOVES: (SceneSetting.GROOVE,), Section.CHAINS: (SceneSetting.CHAINS,)}

    def __init__(self, *, clip_slots=None, **settings):
        self.note_change()
        # The list of registers to reset is copied, so that the scene shares nothing with the data it was read from.
        self._settings = {name: own_copy(settings.get(name)) for name in SETTINGS}
        self._clip_slots = None if clip_slots is None else dict(clip_slots)

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(ERR_SCENE_EXPECTED_SETTINGS)
            check_keys(data=data, allowed={*SETTINGS, SceneSetting.TRACKS})
            check_settings(settings=SETTINGS, data=data, song=song, leaving_out=READ_ANOTHER_WAY)
            _check_tempo(data)
            clip_slots = {}
            for track, clip_slot in (data.get(SceneSetting.TRACKS) or {}).items():
                if not song.has_track(track):
                    raise InvalidValue(ERR_NO_SUCH_TRACK.format(track=track))
                clip_slots[track] = ClipSlot.from_data(data=clip_slot, where=where, song=song, track=track)
            settings = {name: data[name] for name in SETTINGS if name in data}
            return cls(clip_slots=clip_slots if SceneSetting.TRACKS in data else None, **settings)

    def to_data(self):
        return self._data_from(data_built_anew)

    def kept_data(self):
        """Return the scene's data with each clip's as the clip keeps it, put together each time, since a clip changes without its scene changing."""
        return self._data_from(data_as_kept)

    def _data_from(self, part_data):
        data = written_settings(self._settings)
        if self._clip_slots is not None:
            data[SceneSetting.TRACKS] = {track: part_data(clip_slot) for track, clip_slot in self._clip_slots.items()}
        return data

    def get_name(self):
        """Return its name as the file gives it, or None if it has none."""
        return self._settings[SceneSetting.NAME]

    def get_repeat(self):
        repeat = self._settings[SceneSetting.REPEAT]
        return DEFAULT_REPEAT if repeat is None else repeat

    def launches_together(self):
        """Return whether a start reaching any clip of the scene launches the whole scene in real-time playback, which no export reads (the user's design of 2026-11-09)."""
        launch = self._settings[SceneSetting.LAUNCH_TOGETHER]
        return DEFAULT_LAUNCH_TOGETHER if launch is None else launch

    @notes_change
    def set_launch_together(self, value):
        """Make a start reaching any of its clips launch the whole scene, or each clip wait for its own; the default is left out of the file."""
        SETTINGS[SceneSetting.LAUNCH_TOGETHER].check(value)
        self._settings[SceneSetting.LAUNCH_TOGETHER] = None if value == DEFAULT_LAUNCH_TOGETHER else value

    def get_scale_name(self):
        """Return the name of the scale it sets, or None to use the song's."""
        return self._settings[SceneSetting.SCALE]

    def get_tempo(self, place):
        """Return its tempo on one of its repeats, counted from 0, or None to use the song's.

        A scene with tempo_start and tempo_end ramps evenly between them across its repeats.
        """
        settings = self._settings
        if settings[SceneSetting.TEMPO] is not None:
            return number(settings[SceneSetting.TEMPO])
        if settings[SceneSetting.TEMPO_START] is None:
            return None
        start = number(settings[SceneSetting.TEMPO_START])
        end = number(settings[SceneSetting.TEMPO_END])
        return start + (end - start) * _ramp_fraction(place=place, repeat=self.get_repeat())

    def get_tempo_setting(self):
        """Return the tempo it sets for all its repeats, as written, or None if it has none or ramps."""
        return self._settings[SceneSetting.TEMPO]

    def get_tempo_start(self):
        """Return the tempo its ramp starts from, as written, or None if it doesn't ramp."""
        return self._settings[SceneSetting.TEMPO_START]

    def get_tempo_end(self):
        """Return the tempo its ramp ends at, as written, or None if it doesn't ramp."""
        return self._settings[SceneSetting.TEMPO_END]

    def get_reset_names(self):
        """Return the registers it sets back to their defaults as it starts, in the order the registers come."""
        reset = self._settings[SceneSetting.RESET] or []
        return [name for name in REGISTER_NAMES if name in reset]

    def get_track_names(self):
        """Return the tracks it plays a clip slot on, in the order the file lists them."""
        return list(self._clip_slots or {})

    def get_clip_slot(self, track):
        """Return its clip slot for a track, or None if it plays nothing there."""
        return (self._clip_slots or {}).get(track)

    def has_clip_slot(self, track):
        return track in (self._clip_slots or {})

    def resets(self, register):
        """Return whether it sets a register back to its default as it starts."""
        return register in self.get_reset_names()

    def copy(self):
        """Return a scene just like this one, with clip slots of its own."""
        clip_slots = None if self._clip_slots is None else {track: clip_slot.copy() for track, clip_slot in self._clip_slots.items()}
        return Scene(clip_slots=clip_slots, **self._settings)

    def every_clip_loops(self):
        """Return whether every clip in the scene loops, which would leave the scene with no end."""
        clip_slots = [self.get_clip_slot(track) for track in self.get_track_names()]
        return bool(clip_slots) and all(clip_slot.loops() for clip_slot in clip_slots)

    def clip_slots_naming(self, *, section, name):
        """Return the track of each of its clips that names an item of a section, in order: the clips that play or morph to a pattern, run a chain or grab from a track."""
        return [track for track, clip_slot in (self._clip_slots or {}).items() if clip_slot.names_item(section=section, name=name)]

    def grab_circle(self, *, track, other):
        """Return the tracks a grab from track to other would go round in a circle, like [lead, bass, lead], or None.

        A clip grabbing from other follows other's grab, and so on, within the scene.
        """
        path = [track, other]
        while path[-1] != track:
            clip_slot = self.get_clip_slot(path[-1])
            following = None if clip_slot is None else clip_slot.get_grab_track()
            if following is None or following in path[1:]:
                return None
            path.append(following)
        return path

    # Changing the scene.

    @notes_change
    def set_name(self, name):
        if name is not None:
            SETTINGS[SceneSetting.NAME].check(name)
        self._settings[SceneSetting.NAME] = name

    @notes_change
    def set_repeat(self, repeat):
        """Set how many times it plays, where None or 1 is once."""
        if repeat is not None:
            SETTINGS[SceneSetting.REPEAT].check(repeat)
        self._settings[SceneSetting.REPEAT] = None if repeat == DEFAULT_REPEAT else repeat

    @notes_change
    def set_scale_name(self, *, name, song):
        """Give it one of the song's scales instead of the song's own, or None to use the song's."""
        SETTINGS[SceneSetting.SCALE].check(name, song=song)
        self._settings[SceneSetting.SCALE] = name

    @notes_change
    def set_tempo(self, tempo):
        """Set its tempo, which is where its ramp starts if it has one."""
        SETTINGS[SceneSetting.TEMPO].check(tempo)
        if self._settings[SceneSetting.TEMPO_END] is not None:
            self._settings[SceneSetting.TEMPO_START] = tempo
        else:
            self._settings[SceneSetting.TEMPO] = tempo

    @notes_change
    def clear_tempo(self):
        """Make it play at the song's tempo, dropping any ramp."""
        for setting in (SceneSetting.TEMPO, SceneSetting.TEMPO_START, SceneSetting.TEMPO_END):
            self._settings[setting] = None

    @notes_change
    def set_tempo_ramp(self, *, start, end):
        """Make its tempo ramp from one value to another across its repeats."""
        SETTINGS[SceneSetting.TEMPO_START].check(start)
        SETTINGS[SceneSetting.TEMPO_END].check(end)
        self._settings[SceneSetting.TEMPO] = None
        self._settings[SceneSetting.TEMPO_START] = start
        self._settings[SceneSetting.TEMPO_END] = end

    @notes_change
    def clear_tempo_ramp(self):
        """Stop its tempo ramping, keeping where the ramp started as its tempo."""
        start = self._settings[SceneSetting.TEMPO_START]
        self._settings[SceneSetting.TEMPO_START] = None
        self._settings[SceneSetting.TEMPO_END] = None
        if start is not None:
            self._settings[SceneSetting.TEMPO] = start

    @notes_change
    def set_reset(self, *, register, on):
        """Make it set a register back to its default as it starts, or stop it, keeping the registers in order."""
        if register not in REGISTER_NAMES:
            raise InvalidValue(ERR_NO_SUCH_REGISTER.format(name=register, names=listed(REGISTER_NAMES)))
        chosen = set(self.get_reset_names())
        chosen = chosen | {register} if on else chosen - {register}
        reset = [name for name in REGISTER_NAMES if name in chosen]
        self._settings[SceneSetting.RESET] = reset or None

    @notes_change
    def set_clip_slot(self, *, track, clip_slot, song):
        """Give a track a clip slot, replacing any it had."""
        if not song.has_track(track):
            raise InvalidValue(ERR_NO_SUCH_TRACK.format(track=track))
        if self._clip_slots is None:
            self._clip_slots = {}
        self._clip_slots[track] = clip_slot

    @notes_change
    def remove_clip_slot(self, track):
        if not self.has_clip_slot(track):
            raise InvalidValue(ERR_NO_CLIP_SLOT.format(track=track))
        del self._clip_slots[track]

    # Keeping its names right when the song renames or removes something.

    def referring_parts(self):
        """Return its clips, which name patterns, chains and tracks."""
        return list((self._clip_slots or {}).values())

    def rename_references(self, *, section, old, new):
        """Follow a rename as every stored object does, and move a renamed track's clip to the track's new name first."""
        if section == Section.TRACKS and self.has_clip_slot(old):
            self._move_clip_slot(old=old, new=new)
        super().rename_references(section=section, old=old, new=new)

    @notes_change
    def _move_clip_slot(self, *, old, new):
        """Keep a track's clip under the track's new name, in its place."""
        self._clip_slots = {(new if track == old else track): clip_slot for track, clip_slot in self._clip_slots.items()}

    @notes_change
    def remove_track(self, track):
        """Drop the track's clip slot, and stop any clip slot grabbing from it."""
        if self._clip_slots is not None:
            self._clip_slots.pop(track, None)
            for clip_slot in self._clip_slots.values():
                if clip_slot.names_item(section=Section.TRACKS, name=track):
                    clip_slot.clear_grab()

    def get_setting(self, name):
        """Return one of its shape settings as the file writes it, like density_start, or None when it's left blank."""
        return self._settings[name]

    def get_shape(self, shape):
        """Return how a shape, Density, Swell or Articulate, runs over the scene, or None when the scene sets neither its start nor its end."""
        return shape_values(settings=self._settings, shape=shape)

    @notes_change
    def set_shape_setting(self, *, name, value):
        """Set one part of a shape by its file name, like density_start, or None to leave it out."""
        if value is not None:
            SETTINGS[name].check(value)
        self._settings[name] = value

    def get_chain_names(self):
        """Return the names of the chains every clip of the scene runs, after the clip's own, in order."""
        return list(self._settings[SceneSetting.CHAINS] or [])

    @notes_change
    def set_chain_names(self, *, names, song):
        """Set the chains every clip of the scene runs, by name, in order, or none for an empty list."""
        if names:
            SETTINGS[SceneSetting.CHAINS].check(list(names), song=song)
        self._settings[SceneSetting.CHAINS] = list(names) if names else None

    def get_groove_choice(self):
        """Return the groove it chooses by name, False for no groove in this scene whatever the song chooses, or None to take the song's."""
        return self._settings[SceneSetting.GROOVE]

    @notes_change
    def set_groove_choice(self, *, choice, song):
        """Choose a groove by name, False for none in this scene, or None to take the song's."""
        SETTINGS[SceneSetting.GROOVE].check(choice, song=song)
        self._settings[SceneSetting.GROOVE] = choice


def _check_tempo(data):
    """Refuse a tempo that isn't a number, or a ramp that doesn't give both its start and end."""
    if SceneSetting.TEMPO in data:
        SETTINGS[SceneSetting.TEMPO].check_held(data)
    elif SceneSetting.TEMPO_START in data or SceneSetting.TEMPO_END in data:
        if SceneSetting.TEMPO_START not in data or SceneSetting.TEMPO_END not in data:
            raise InvalidValue(ERR_RAMP_NEEDS_BOTH)
        SETTINGS[SceneSetting.TEMPO_START].check_held(data)
        SETTINGS[SceneSetting.TEMPO_END].check_held(data)


def _ramp_fraction(*, place, repeat):
    """Return how far through a tempo ramp a repeat is, from 0 on the first to 1 on the last."""
    last_place = repeat - 1
    return Rational(place, last_place) if last_place > 0 else NO_RAMP
