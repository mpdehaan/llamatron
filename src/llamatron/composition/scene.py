# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A scene: a row of the song, launching one clip slot on each track that has one.

Its settings and clip slots are changed through its setters, which check a value the way reading a
file does and raise InvalidValue if it's wrong, with the song passed in wherever a setting names
something the song holds.
"""


from typing import NamedTuple

from llamatron.caching.revised import notes_change
from llamatron.composition import corrections, defaults, file_format, limits, sections
from llamatron.composition.chain import check_chain_names
from llamatron.composition.checks import listed, number, pass_over_unknown, reading
from llamatron.composition.clip_slot import ClipSlot
from llamatron.composition.conditions import register_values_setting, statements_setting
from llamatron.composition.file_format import RampPart, SceneSetting, Section
from llamatron.composition.groove import check_groove_choice
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.llama_data import data_as_kept, data_built_anew, HoldsSettings, own_copy, written_settings
from llamatron.composition.setting import check_settings, Checked, Choice, described, Flag, WholeNumber
from llamatron.composition.shapes import shape_settings, shape_values
from llamatron.composition.traits import BypassedWhen, RunsChains, SetsRegisters
from llamatron.composition.velocity_ramps import velocity_of, velocity_setting_descriptions
from llamatron.user_strings import errors

# The settings of a scene's tempo ramps that are tempos, which a file writes as it writes a scene's tempo.
RAMP_TEMPOS = tuple(file_format.TEMPO_RAMP_SETTINGS[(way, part)] for way in file_format.RAMP_WAYS for part in (RampPart.START, RampPart.END))
RAMP_SETTINGS = tuple(file_format.TEMPO_RAMP_SETTINGS[(way, part)] for way in file_format.RAMP_WAYS for part in file_format.RAMP_PARTS)


class TempoRamp(NamedTuple):
    """One tempo ramp of a scene as written: the tempo it starts from and the tempo it reaches, either None for the tempo there would have been, and the bars it takes."""

    start: object
    end: object
    over: object


def _check_scene_name(name):
    if not isinstance(name, str):
        raise InvalidValue(errors.ERR_SCENE_NAME_NOT_TEXT.format(value=name))


def _check_scale_name(*, value, song):
    """Refuse a scale the song doesn't have. None is no scale of the scene's own."""
    if value is not None and not song.has_scale(value):
        raise InvalidValue(errors.ERR_SCENE_NO_SUCH_SCALE.format(scale=value))


def is_register_list(value):
    """Return whether a value is a list of register names, each at most once."""
    return isinstance(value, list) and all(name in file_format.REGISTER_NAMES for name in value) and len(set(value)) == len(value)


def _check_reset(value):
    if not is_register_list(value):
        raise InvalidValue(errors.ERR_BAD_RESET.format(names=listed(file_format.REGISTER_NAMES), value=value))


def is_draw_list(value):
    """Return whether a value is a list of the song's draws' names."""
    return isinstance(value, list) and all(name in file_format.DRAW_NAMES for name in value)


def _check_reset_draws(value):
    if not is_draw_list(value):
        raise InvalidValue(errors.ERR_BAD_RESET_DRAWS.format(names=listed(file_format.DRAW_NAMES), value=value))


# A scene's settings, each described once, in the order they're written to a file, before its tracks.
SETTINGS = described(
    Checked(name=SceneSetting.NAME, check=_check_scene_name),
    Choice(name=SceneSetting.SECTION, choices=file_format.SECTION_KINDS, default=corrections.LEFT_OUT, error=errors.ERR_BAD_SECTION),
    WholeNumber(name=SceneSetting.REPEAT, lowest=limits.MIN_REPEAT, highest=limits.MAX_SCENE_REPEAT, error=errors.ERR_BAD_REPEAT),
    Checked(name=SceneSetting.SCALE, check=_check_scale_name, needs_song=True),
    Checked(name=SceneSetting.TEMPO, check=number),
    Checked(name=SceneSetting.TEMPO_IN_START, check=number),
    Checked(name=SceneSetting.TEMPO_IN_END, check=number),
    WholeNumber(name=SceneSetting.TEMPO_IN_OVER, lowest=limits.MIN_RAMP_BARS, highest=limits.MAX_RAMP_BARS, error=errors.ERR_BAD_RAMP_BARS),
    Checked(name=SceneSetting.TEMPO_OUT_START, check=number),
    Checked(name=SceneSetting.TEMPO_OUT_END, check=number),
    WholeNumber(name=SceneSetting.TEMPO_OUT_OVER, lowest=limits.MIN_RAMP_BARS, highest=limits.MAX_RAMP_BARS, error=errors.ERR_BAD_RAMP_BARS),
    Checked(name=SceneSetting.RESET, check=_check_reset),
    Checked(name=SceneSetting.RESET_DRAWS, check=_check_reset_draws),
    Checked(name=SceneSetting.GROOVE, check=check_groove_choice, needs_song=True),
    Flag(name=SceneSetting.LAUNCH_TOGETHER, error=errors.ERR_LAUNCH_TOGETHER_NOT_TRUE_OR_FALSE),
    Checked(name=SceneSetting.CHAINS, check=check_chain_names, needs_song=True),
    *velocity_setting_descriptions(),
    *shape_settings(),
    register_values_setting(SceneSetting.SET_REGISTERS),
    register_values_setting(SceneSetting.ADD_REGISTERS),
    statements_setting(SceneSetting.BYPASS_WHEN),
)
# The settings a file is read without the plain check of: a name is kept as the file writes it, a number too, and
# so are the tempos of its ramps (_check_tempo).
READ_ANOTHER_WAY = (SceneSetting.NAME, SceneSetting.TEMPO, *RAMP_TEMPOS)


class Scene(RunsChains, BypassedWhen, SetsRegisters, HoldsSettings):
    """A name, how many times it repeats, an optional scale and tempo, and a clip slot for each track it plays.

    Settings the file leaves out are kept as None, meaning their defaults. Its scale is kept as
    the name of one of the song's scales.
    """

    __slots__ = ('_clip_slots')

    SETTINGS = SETTINGS
    CHAINS_SETTING = SceneSetting.CHAINS
    BYPASS_SETTING = SceneSetting.BYPASS_WHEN
    SET_REGISTERS_SETTING = SceneSetting.SET_REGISTERS
    ADD_REGISTERS_SETTING = SceneSetting.ADD_REGISTERS

    # A scene names the scale and the groove it chooses. Its clips name things too, and are its referring parts.
    REFERENCES = {Section.SCALES: (SceneSetting.SCALE,), Section.GROOVES: (SceneSetting.GROOVE,), **{section: (SceneSetting.CHAINS,) for section in sections.GENERATOR_SECTIONS}}

    def __init__(self, *, clip_slots=None, **settings):
        self.note_change()
        # The list of registers to reset is copied, so that the scene shares nothing with the data it was read from.
        self._settings = {name: own_copy(settings.get(name)) for name in SETTINGS}
        self._clip_slots = None if clip_slots is None else dict(clip_slots)

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(errors.ERR_SCENE_EXPECTED_SETTINGS)
            pass_over_unknown(data=data, allowed={*SETTINGS, SceneSetting.TRACKS})
            check_settings(settings=SETTINGS, data=data, song=song, leaving_out=READ_ANOTHER_WAY)
            _check_tempo(data)
            clip_slots = {}
            for track, clip_slot in (data.get(SceneSetting.TRACKS) or {}).items():
                if not song.has_track(track):
                    raise InvalidValue(errors.ERR_NO_SUCH_TRACK.format(track=track))
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
        return defaults.DEFAULT_REPEAT if repeat is None else repeat

    def get_section(self):
        """Return the kind of section the scene says it is, or None for a scene that says none."""
        return self._settings[SceneSetting.SECTION]

    def set_section(self, section):
        """Say what kind of section the scene is, or None for no kind."""
        self.set_written(name=SceneSetting.SECTION, value=section)

    def launches_together(self):
        """Return whether a start reaching any clip of the scene launches the whole scene in real-time playback, which no export reads."""
        launch = self._settings[SceneSetting.LAUNCH_TOGETHER]
        return defaults.DEFAULT_LAUNCH_TOGETHER if launch is None else launch

    @notes_change
    def set_launch_together(self, value):
        """Make a start reaching any of its clips launch the whole scene, or each clip wait for its own; the default is left out of the file."""
        SETTINGS[SceneSetting.LAUNCH_TOGETHER].check(value)
        self._settings[SceneSetting.LAUNCH_TOGETHER] = None if value == defaults.DEFAULT_LAUNCH_TOGETHER else value

    def get_scale_name(self):
        """Return the name of the scale it sets, or None to use the song's."""
        return self._settings[SceneSetting.SCALE]

    def get_tempo(self):
        """Return the tempo it sets, or None to use the song's. Its ramps move away from this tempo and back to it."""
        tempo = self._settings[SceneSetting.TEMPO]
        return None if tempo is None else number(tempo)

    def get_tempo_setting(self):
        """Return the tempo it sets, as written, or None if it has none."""
        return self._settings[SceneSetting.TEMPO]

    def get_tempo_ramp(self, way):
        """Return its tempo ramp in or out as a TempoRamp, or None when the ramp changes nothing: it gives no bars, or neither a start nor an end."""
        start, end, over = (self._settings[file_format.TEMPO_RAMP_SETTINGS[(way, part)]] for part in file_format.RAMP_PARTS)
        if over is None or (start is None and end is None):
            return None
        return TempoRamp(None if start is None else number(start), None if end is None else number(end), over)

    def has_tempo_ramp(self):
        """Return whether either of its tempo ramps changes its tempo."""
        return any(self.get_tempo_ramp(way) is not None for way in file_format.RAMP_WAYS)

    def get_tempo_ramp_setting(self, *, way, part):
        """Return one part of one of its tempo ramps as written, or None where it is blank."""
        return self._settings[file_format.TEMPO_RAMP_SETTINGS[(way, part)]]

    def get_reset_names(self):
        """Return the registers it sets back to their defaults as it starts, in the order the registers come."""
        reset = self._settings[SceneSetting.RESET] or []
        return [name for name in file_format.REGISTER_NAMES if name in reset]

    def get_reset_draw_names(self):
        """Return the draws it sends back to their start, or a serial draw to a new round, as it first starts, in the order the draws come."""
        reset = self._settings[SceneSetting.RESET_DRAWS] or []
        return [name for name in file_format.DRAW_NAMES if name in reset]

    def changes_registers(self):
        """Return whether it, or any of its clips, sets a register or adds to one."""
        own = self._settings[SceneSetting.SET_REGISTERS] or self._settings[SceneSetting.ADD_REGISTERS]
        return bool(own) or any(clip_slot.get_register_sets() or clip_slot.get_register_adds() for clip_slot in (self._clip_slots or {}).values())

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
        """Return whether every clip in the scene loops, which would leave the scene with no end, unless a step of a looping clip's pattern can stop the clip, which only the song knows (Song.scene_never_ends)."""
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

    def set_repeat(self, repeat):
        """Set how many times it plays, where None or 1 is once."""
        self.set_written_unless_default(name=SceneSetting.REPEAT, value=repeat, default=defaults.DEFAULT_REPEAT)

    @notes_change
    def set_scale_name(self, *, name, song):
        """Give it one of the song's scales instead of the song's own, or None to use the song's."""
        SETTINGS[SceneSetting.SCALE].check(name, song=song)
        self._settings[SceneSetting.SCALE] = name

    @notes_change
    def set_tempo(self, tempo):
        """Set its tempo."""
        SETTINGS[SceneSetting.TEMPO].check(tempo)
        self._settings[SceneSetting.TEMPO] = tempo

    @notes_change
    def clear_tempo(self):
        """Make it play at the song's tempo. Its ramps stay."""
        self._settings[SceneSetting.TEMPO] = None

    def set_tempo_ramp_setting(self, *, way, part, value):
        """Set one part of one of its tempo ramps, or None to leave it blank."""
        name = file_format.TEMPO_RAMP_SETTINGS[(way, part)]
        self.set_written(name=name, value=value)

    @notes_change
    def set_reset(self, *, register, on):
        """Make it set a register back to its default as it starts, or stop it, keeping the registers in order."""
        if register not in file_format.REGISTER_NAMES:
            raise InvalidValue(errors.ERR_NO_SUCH_REGISTER.format(name=register, names=listed(file_format.REGISTER_NAMES)))
        chosen = set(self.get_reset_names())
        chosen = chosen | {register} if on else chosen - {register}
        reset = [name for name in file_format.REGISTER_NAMES if name in chosen]
        self._settings[SceneSetting.RESET] = reset or None

    @notes_change
    def set_reset_draw(self, *, draw, on):
        """Make it reset a draw as it first starts, or stop it, keeping the draws in order."""
        if draw not in file_format.DRAW_NAMES:
            raise InvalidValue(errors.ERR_NO_SUCH_DRAW.format(name=draw, names=listed(file_format.DRAW_NAMES)))
        chosen = set(self.get_reset_draw_names())
        chosen = chosen | {draw} if on else chosen - {draw}
        reset = [name for name in file_format.DRAW_NAMES if name in chosen]
        self._settings[SceneSetting.RESET_DRAWS] = reset or None

    @notes_change
    def set_clip_slot(self, *, track, clip_slot, song):
        """Give a track a clip slot, replacing any it had."""
        if not song.has_track(track):
            raise InvalidValue(errors.ERR_NO_SUCH_TRACK.format(track=track))
        if self._clip_slots is None:
            self._clip_slots = {}
        self._clip_slots[track] = clip_slot

    @notes_change
    def remove_clip_slot(self, track):
        if not self.has_clip_slot(track):
            raise InvalidValue(errors.ERR_NO_CLIP_SLOT.format(track=track))
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

    def get_velocity_settings(self):
        """Return its velocity settings as written, each by its file name: the level that holds and the parts of its two ramps, None where one is blank."""
        return {name: self._settings[name] for name in file_format.VELOCITY_SETTINGS}

    def get_velocity(self):
        """Return how loud the scene plays its clips, as a Velocity, before any clip's own."""
        return velocity_of(scene_settings=self.get_velocity_settings())

    def get_shape(self, shape):
        """Return how a shape, Density or Articulate, runs over the scene, or None when the scene sets neither its start nor its end."""
        return shape_values(settings=self._settings, shape=shape)

    def get_groove_choice(self):
        """Return the groove it chooses by name, False for no groove in this scene whatever the song chooses, or None to take the song's."""
        return self._settings[SceneSetting.GROOVE]

    @notes_change
    def set_groove_choice(self, *, choice, song):
        """Choose a groove by name, False for none in this scene, or None to take the song's."""
        SETTINGS[SceneSetting.GROOVE].check(choice, song=song)
        self._settings[SceneSetting.GROOVE] = choice


def _check_tempo(data):
    """Refuse a tempo that isn't a number, the scene's own or one of its ramps'."""
    for name in (SceneSetting.TEMPO, *RAMP_TEMPOS):
        if name in data:
            SETTINGS[name].check_held(data)
