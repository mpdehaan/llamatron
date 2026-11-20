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

"""A clip slot: what one track plays in one scene, which is a clip in Live.

It's called a clip slot, Live's own word for the place where a track meets a scene, to keep it
apart from the finished Clip that it renders into, and from the cells of a groove and of the
grids the tracker draws. It was once called Cell. People are always
shown the word clip. Its settings are changed through its setters, which check a value the way
reading a file does and raise InvalidValue if it's wrong, with the song passed in wherever a
setting names something the song holds.
"""

from llamatron.composition import corrections, defaults, file_format, limits, sections
from llamatron.composition.chain import check_chain_names
from llamatron.composition.checks import check_name, pass_over_unknown, reading
from llamatron.composition.conditions import register_values_setting, statements_setting, with_statement
from llamatron.composition.file_format import ClipSlotSetting, PatternOrder, Section, strum_setting
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.llama_data import HoldsSettings, own_copy, settings_by_name, written_settings
from llamatron.composition.setting import check_settings, Checked, Choice, described, Flag, WholeNumber
from llamatron.composition.shapes import shape_settings, shape_values
from llamatron.composition.strum import strum_settings, strum_values
from llamatron.composition.traits import RunsChains, SetsRegisters
from llamatron.composition.velocity_ramps import velocity_of, velocity_setting_descriptions
from llamatron.generators.blend import BlendMode
from llamatron.strings import errors, marks
from llamatron.support.revised import notes_change


def morph_style_name(mode):
    """Return a morph style as a file writes it, like 'left' for BlendMode.LEFT."""
    return mode.name.lower()


FIRST_MORPH_STYLE_PLACE = 0
MORPH_STYLES = {morph_style_name(member): member for member in BlendMode}
# The morph style a clip slot gets when one is set without saying which.
FIRST_MORPH_STYLE = list(MORPH_STYLES)[FIRST_MORPH_STYLE_PLACE]
# A morph has to play its first pattern and its target, so it needs at least two repeats.
MIN_MORPH_REPEAT = 2


def _check_pattern_name(*, value, song):
    if not song.has_pattern(value):
        raise InvalidValue(errors.ERR_CLIP_SLOT_NO_SUCH_PATTERN.format(name=value))


def _check_pattern_names(*, value, song):
    """Refuse a clip's patterns unless they are a list of at least one of the set's patterns by name, a pattern allowed more than once, all drum patterns or none."""
    if not isinstance(value, list) or not value or not all(isinstance(name, str) for name in value):
        raise InvalidValue(errors.ERR_NOT_PATTERN_NAMES.format(value=value))
    for name in value:
        _check_pattern_name(value=name, song=song)
    if len({song.get_pattern(name).is_drum() for name in value}) > 1:
        raise InvalidValue(errors.ERR_PATTERNS_DRUMS_AND_NOTES)


def _check_scale_name(*, value, song):
    if not song.has_scale(value):
        raise InvalidValue(errors.ERR_SCENE_NO_SUCH_SCALE.format(scale=value))




def _check_grab_track_name(*, value, song):
    if not song.has_track(value):
        raise InvalidValue(errors.ERR_NO_GRAB_TRACK.format(name=value))


# A clip slot's settings, each described once, in the order they're written to a file.
SETTINGS = described(
    Checked(name=ClipSlotSetting.NAME, check=check_name),
    Checked(name=ClipSlotSetting.PATTERNS, check=_check_pattern_names, needs_song=True),
    Checked(name=ClipSlotSetting.CHAINS, check=check_chain_names, needs_song=True),
    Flag(name=ClipSlotSetting.LOOP, error=errors.ERR_LOOP_NOT_TRUE_OR_FALSE),
    Choice(name=ClipSlotSetting.PATTERN_ORDER, choices=file_format.PATTERN_ORDERS, default=PatternOrder.FORWARD, error=errors.ERR_BAD_PATTERN_ORDER),
    WholeNumber(name=ClipSlotSetting.REPEAT, lowest=limits.MIN_REPEAT, highest=limits.MAX_CLIP_REPEAT, error=errors.ERR_BAD_REPEAT),
    Choice(name=ClipSlotSetting.DIRECTION, choices=file_format.DIRECTIONS, default=corrections.LEFT_OUT, error=errors.ERR_BAD_DIRECTION),
    Checked(name=ClipSlotSetting.MORPH_TO, check=_check_pattern_name, needs_song=True),
    Choice(name=ClipSlotSetting.MORPH_STYLE, choices=sorted(MORPH_STYLES), default=FIRST_MORPH_STYLE, error=errors.ERR_BAD_MORPH_STYLE),
    Checked(name=ClipSlotSetting.GRAB_TRACK, check=_check_grab_track_name, needs_song=True),
    Choice(name=ClipSlotSetting.FOLLOW_ACTION, choices=file_format.FOLLOW_ACTION_CHOICES, default=corrections.LEFT_OUT, error=errors.ERR_BAD_FOLLOW_ACTION),
    Checked(name=ClipSlotSetting.SCALE, check=_check_scale_name, needs_song=True),
    *velocity_setting_descriptions(),
    *shape_settings(),
    *strum_settings(),
    register_values_setting(ClipSlotSetting.SET_REGISTERS),
    register_values_setting(ClipSlotSetting.ADD_REGISTERS),
    statements_setting(ClipSlotSetting.BYPASS_WHEN),
    statements_setting(ClipSlotSetting.SKIP_WHEN),
)


class ClipSlot(RunsChains, SetsRegisters, HoldsSettings):
    """A pattern to play, and how: its chain, repeats or loop, direction, morph and grab, and its own name if it has one.

    Settings the file leaves out are kept as None, meaning their defaults. A clip with no name of
    its own goes by its pattern's, on the grid and in everything exported. The pattern, chain and
    other patterns and tracks are kept as names, and looked up when the song renders.
    """

    __slots__ = ()

    SETTINGS = SETTINGS
    CHAINS_SETTING = ClipSlotSetting.CHAINS
    SET_REGISTERS_SETTING = ClipSlotSetting.SET_REGISTERS
    ADD_REGISTERS_SETTING = ClipSlotSetting.ADD_REGISTERS

    # A clip names the pattern it plays and the one it morphs to, the chain it runs and the track it grabs from.
    REFERENCES = {
        Section.PATTERNS: (ClipSlotSetting.PATTERNS, ClipSlotSetting.MORPH_TO),
        **{section: (ClipSlotSetting.CHAINS,) for section in sections.GENERATOR_SECTIONS},
        Section.TRACKS: (ClipSlotSetting.GRAB_TRACK,),
        Section.SCALES: (ClipSlotSetting.SCALE,),
    }

    def __init__(self, **settings):
        self.note_change()
        # A list of chains is copied, so that the clip shares nothing with the data it was read from.
        self._settings = {name: own_copy(value) for name, value in settings_by_name(names=SETTINGS, given=settings).items()}

    @classmethod
    def from_data(cls, *, data, where, song=None, track=None):
        """Read the clip slot for a track in a scene. where names the scene, and song knows the names."""
        where = errors.ERR_CLIP_SLOT_WHERE.format(where=where, track=track)
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(errors.ERR_CLIP_SLOT_EXPECTED_SETTINGS.format(data=data))
            pass_over_unknown(data=data, allowed={*SETTINGS, ClipSlotSetting.PATTERN})
            # One pattern, as a file names it, is read as a list of one in the file's own data, where a correction is made, and
            # the data is then put back as the file had it, in the file's order, since it may be data the undo history keeps.
            keys = list(data)
            _read_pattern(data)
            try:
                check_settings(settings=SETTINGS, data=data, song=song)
                # What one setting may hold given another: a clip can't grab from its own track, a morph needs its target, its style and two repeats, and every clip plays a pattern.
                if ClipSlotSetting.GRAB_TRACK in data and data[ClipSlotSetting.GRAB_TRACK] == track:
                    raise InvalidValue(errors.ERR_GRABS_ITSELF)
                _check_morph(data=data, repeat=data.get(ClipSlotSetting.REPEAT, defaults.DEFAULT_REPEAT))
                if ClipSlotSetting.PATTERNS not in data:
                    raise InvalidValue(errors.ERR_NEEDS_PATTERN)
                return cls(**data)
            finally:
                if ClipSlotSetting.PATTERN in keys:
                    _unread_pattern(data=data, keys=keys)

    def to_data(self):
        """Return the clip as a file holds it: a clip of one pattern names it as pattern, as files always have, and a clip of several lists them as patterns."""
        return {(ClipSlotSetting.PATTERN if is_one_pattern(name=name, value=value) else name): (value[0] if is_one_pattern(name=name, value=value) else value) for name, value in written_settings(self._settings).items()}

    def get_name(self):
        """Return the clip's own name, or None if it goes by its pattern's."""
        return self._settings[ClipSlotSetting.NAME]

    def get_display_name(self):
        """Return the name the clip shows and exports as: its own, or its pattern's, with a count of the patterns after the first when it plays several."""
        if self.get_name():
            return self.get_name()
        names = self.get_pattern_names()
        if len(names) == 1:
            return names[0]
        return marks.MSG_CLIP_PATTERNS_COUNTED.format(name=names[0], more=len(names) - 1)

    def get_pattern_names(self):
        """Return the patterns it plays, in order, laid end to end as one long pattern."""
        return list(self._settings[ClipSlotSetting.PATTERNS])

    def get_pattern_name(self):
        """Return the first pattern it plays, which is the only one of a clip with one pattern, and what such a clip goes by."""
        return self._settings[ClipSlotSetting.PATTERNS][0]

    def get_strum(self):
        """Return how the clip strums its chords, or None when its Direction is blank and it takes its track's."""
        return strum_values(lambda part: self._settings[strum_setting(part)])

    def set_strum_setting(self, *, part, value):
        """Set one part of the clip's strum, or None to leave it blank."""
        name = strum_setting(part)
        self.set_written(name=name, value=value)

    def get_velocity_settings(self):
        """Return its velocity settings as written, each by its file name: the level that holds and the parts of its two ramps, None where one is blank."""
        return {name: self._settings[name] for name in file_format.VELOCITY_SETTINGS}

    def get_velocity(self, scene):
        """Return how loud the clip plays in its scene, as a Velocity: its own settings over the scene's, field by field."""
        return velocity_of(scene_settings=scene.get_velocity_settings(), clip_settings=self.get_velocity_settings())

    def get_shape(self, shape):
        """Return how a shape, Density or Articulate, runs over the clip, or None when the clip sets neither its start nor its end and takes its scene's."""
        return shape_values(settings=self._settings, shape=shape)

    def loops(self):
        return bool(self._settings[ClipSlotSetting.LOOP])

    def get_repeat(self):
        repeat = self._settings[ClipSlotSetting.REPEAT]
        return defaults.DEFAULT_REPEAT if repeat is None else repeat

    def get_direction(self):
        """Return the direction it overrides its patterns with, or None to use theirs."""
        return self._settings[ClipSlotSetting.DIRECTION]

    def get_morph_target(self):
        """Return the pattern it morphs to across its repeats, or None if it doesn't morph."""
        return self._settings[ClipSlotSetting.MORPH_TO]

    def get_morph_style(self):
        """Return how it morphs, as a BlendMode, or None if it doesn't morph."""
        style = self.get_morph_style_name()
        return None if style is None else MORPH_STYLES[style]

    def get_morph_style_name(self):
        """Return how it morphs as the file writes it, like 'left', or None if it doesn't morph."""
        return self._settings[ClipSlotSetting.MORPH_STYLE]

    def get_written_follow_action(self):
        """Return what it sends down in real-time playback when its scene is done, one of FOLLOW_ACTION_CHOICES, or None when the set's default applies. No export reads it."""
        return self._settings[ClipSlotSetting.FOLLOW_ACTION]

    def get_scale_name(self):
        """Return the name of its own scale, which wins over its scene's and its song's, or None to take theirs."""
        return self._settings[ClipSlotSetting.SCALE]

    def get_grab_track(self):
        """Return the track its grab steps take notes from, or None if it doesn't grab."""
        return self._settings[ClipSlotSetting.GRAB_TRACK]

    def copy(self):
        return ClipSlot(**self._settings)


    # Changing the clip slot.

    @notes_change
    def set_name(self, name):
        """Give the clip a name of its own, or None (or nothing) to go by its pattern's."""
        SETTINGS[ClipSlotSetting.NAME].check(name)
        self._settings[ClipSlotSetting.NAME] = name or None

    def set_pattern_name(self, *, name, song):
        """Make it play one pattern alone."""
        self.set_pattern_names(names=[name], song=song)

    @notes_change
    def set_pattern_names(self, *, names, song):
        """Make it play a list of patterns, one after another."""
        SETTINGS[ClipSlotSetting.PATTERNS].check(names, song=song)
        self._settings[ClipSlotSetting.PATTERNS] = list(names)

    @notes_change
    def set_loop(self, loop):
        """Make it loop until its scene ends, or not, which is left out of the file."""
        SETTINGS[ClipSlotSetting.LOOP].check(loop)
        self._settings[ClipSlotSetting.LOOP] = True if loop else None

    @notes_change
    def set_repeat(self, repeat):
        """Set how many times it plays its pattern, where None or 1 is once. Going back to once drops its morph, which runs across repeats."""
        if repeat is not None:
            SETTINGS[ClipSlotSetting.REPEAT].check(repeat)
        self._settings[ClipSlotSetting.REPEAT] = None if repeat == defaults.DEFAULT_REPEAT else repeat
        if self.get_repeat() < MIN_MORPH_REPEAT:
            self.clear_morph()

    def get_pattern_order(self):
        """Return the order it plays its patterns in on each pass through them, forward unless it says otherwise."""
        return self._settings[ClipSlotSetting.PATTERN_ORDER] or PatternOrder.FORWARD

    def set_pattern_order(self, order):
        """Set the order it plays its patterns in, or None for forward."""
        self.set_written_unless_default(name=ClipSlotSetting.PATTERN_ORDER, value=order, default=PatternOrder.FORWARD)

    def set_direction(self, direction):
        """Override its pattern's play direction, or None to use the pattern's."""
        self.set_written(name=ClipSlotSetting.DIRECTION, value=direction)

    @notes_change
    def set_morph(self, *, target, style, song):
        """Make it morph to a pattern across its repeats, in a style like 'left'."""
        if self.get_repeat() < MIN_MORPH_REPEAT:
            raise InvalidValue(errors.ERR_MORPH_TOO_FEW_REPEATS.format(lowest=MIN_MORPH_REPEAT))
        SETTINGS[ClipSlotSetting.MORPH_TO].check(target, song=song)
        SETTINGS[ClipSlotSetting.MORPH_STYLE].check(style)
        self._settings[ClipSlotSetting.MORPH_TO] = target
        self._settings[ClipSlotSetting.MORPH_STYLE] = style

    @notes_change
    def set_morph_style(self, style):
        """Change how it morphs, which it has to be doing already."""
        if self.get_morph_target() is None:
            raise InvalidValue(errors.ERR_MORPH_STYLE_WITHOUT_MORPH)
        SETTINGS[ClipSlotSetting.MORPH_STYLE].check(style)
        self._settings[ClipSlotSetting.MORPH_STYLE] = style

    @notes_change
    def clear_morph(self):
        self._settings[ClipSlotSetting.MORPH_TO] = None
        self._settings[ClipSlotSetting.MORPH_STYLE] = None

    def set_scale_name(self, *, name, song):
        """Give it one of the song's scales of its own, which wins over its scene's and its song's, or None to take theirs."""
        self.set_written(name=ClipSlotSetting.SCALE, value=name, song=song)

    def get_statements(self, name):
        """Return one of its tables of statements about the registers, by the setting's name: the one that bypasses its generators or the one that makes it sit out."""
        return own_copy(self._settings[name] or [])

    @notes_change
    def set_statement(self, *, name, place, statement):
        """Write the statement at a place of one of its tables, add one just past the last, or remove one with None."""
        self.set_written(name=name, value=with_statement(statements=self._settings[name], place=place, statement=statement))

    def set_follow_action(self, advance):
        """Set what it sends down in real-time playback when its scene is done, or None to take the set's default."""
        self.set_written(name=ClipSlotSetting.FOLLOW_ACTION, value=advance)

    @notes_change
    def set_grab_track(self, *, name, song, own_track):
        """Make its grab steps take notes from a track, which can't be its own, or None to stop grabbing."""
        if name is not None:
            SETTINGS[ClipSlotSetting.GRAB_TRACK].check(name, song=song)
            if name == own_track:
                raise InvalidValue(errors.ERR_GRABS_ITSELF)
        self._settings[ClipSlotSetting.GRAB_TRACK] = name

    @notes_change
    def clear_grab(self):
        self._settings[ClipSlotSetting.GRAB_TRACK] = None


def _check_morph(*, data, repeat):
    """Refuse a morph without both its settings or without enough repeats, once each setting has been checked on its own."""
    if (ClipSlotSetting.MORPH_TO in data) != (ClipSlotSetting.MORPH_STYLE in data):
        raise InvalidValue(errors.ERR_MORPH_NEEDS_BOTH)
    if ClipSlotSetting.MORPH_TO in data and repeat < MIN_MORPH_REPEAT:
        raise InvalidValue(errors.ERR_MORPH_TOO_FEW_REPEATS.format(lowest=MIN_MORPH_REPEAT))


def is_one_pattern(*, name, value):
    """Return whether a setting is a clip's patterns and holds one pattern alone."""
    return name == ClipSlotSetting.PATTERNS and len(value) == 1


def _read_pattern(data):
    """Read pattern, one pattern's name, as a list of one."""
    if ClipSlotSetting.PATTERN not in data:
        return
    if ClipSlotSetting.PATTERNS in data:
        raise InvalidValue(errors.ERR_PATTERN_AND_PATTERNS)
    data[ClipSlotSetting.PATTERNS] = [data.pop(ClipSlotSetting.PATTERN)]


def _unread_pattern(*, data, keys):
    """Put a clip's data back to naming its one pattern as pattern, at the place the file had it, keeping whatever else the data now holds."""
    now = dict(data)
    now[ClipSlotSetting.PATTERN] = now.pop(ClipSlotSetting.PATTERNS)[0]
    data.clear()
    data.update({key: now[key] for key in [*keys, *now] if key in now})
