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
grids the tracker draws. It was called Cell until the user chose this name. People are always
shown the word clip. Its settings are changed through its setters, which check a value the way
reading a file does and raise InvalidValue if it's wrong, with the song passed in wherever a
setting names something the song holds.
"""

from llamatron.composition.checks import check_keys, check_name, reading
from llamatron.composition.defaults import DEFAULT_REPEAT
from llamatron.composition.file_format import strum_setting, FOLLOW_ACTION_CHOICES, DIRECTIONS, ClipSlotSetting, Section
from llamatron.composition.limits import MAX_CLIP_REPEAT, MIN_REPEAT
from llamatron.composition.llama_data import own_copy, LlamaData, settings_by_name, written_settings
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.chain import check_chain_names
from llamatron.composition.shapes import shape_settings, shape_values
from llamatron.composition.strum import strum_settings, strum_values
from llamatron.composition.corrections import LEFT_OUT
from llamatron.composition.setting import Checked, Choice, Flag, WholeNumber, check_settings, described
from llamatron.generators.blend import BlendMode
from llamatron.strings.errors import (
    ERR_CHAIN_AND_CHAINS,
    ERR_SCENE_NO_SUCH_SCALE,
    ERR_BAD_FOLLOW_ACTION, ERR_BAD_DIRECTION, ERR_BAD_MORPH_STYLE, ERR_BAD_REPEAT, ERR_CLIP_SLOT_EXPECTED_SETTINGS, ERR_CLIP_SLOT_NO_SUCH_PATTERN, ERR_CLIP_SLOT_WHERE, ERR_GRABS_ITSELF,
    ERR_LOOP_NOT_TRUE_OR_FALSE, ERR_MORPH_NEEDS_BOTH, ERR_MORPH_STYLE_WITHOUT_MORPH, ERR_MORPH_TOO_FEW_REPEATS, ERR_NEEDS_PATTERN,
    ERR_NO_GRAB_TRACK,
)
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
        raise InvalidValue(ERR_CLIP_SLOT_NO_SUCH_PATTERN.format(name=value))


def _check_scale_name(*, value, song):
    if not song.has_scale(value):
        raise InvalidValue(ERR_SCENE_NO_SUCH_SCALE.format(scale=value))




def _check_grab_track_name(*, value, song):
    if not song.has_track(value):
        raise InvalidValue(ERR_NO_GRAB_TRACK.format(name=value))


# A clip slot's settings, each described once, in the order they're written to a file.
SETTINGS = described(
    Checked(name=ClipSlotSetting.NAME, check=check_name),
    Checked(name=ClipSlotSetting.PATTERN, check=_check_pattern_name, needs_song=True),
    Checked(name=ClipSlotSetting.CHAINS, check=check_chain_names, needs_song=True),
    Flag(name=ClipSlotSetting.LOOP, error=ERR_LOOP_NOT_TRUE_OR_FALSE),
    WholeNumber(name=ClipSlotSetting.REPEAT, lowest=MIN_REPEAT, highest=MAX_CLIP_REPEAT, error=ERR_BAD_REPEAT),
    Choice(name=ClipSlotSetting.DIRECTION, choices=DIRECTIONS, default=LEFT_OUT, error=ERR_BAD_DIRECTION),
    Checked(name=ClipSlotSetting.MORPH_TO, check=_check_pattern_name, needs_song=True),
    Choice(name=ClipSlotSetting.MORPH_STYLE, choices=sorted(MORPH_STYLES), default=FIRST_MORPH_STYLE, error=ERR_BAD_MORPH_STYLE),
    Checked(name=ClipSlotSetting.GRAB_TRACK, check=_check_grab_track_name, needs_song=True),
    Choice(name=ClipSlotSetting.FOLLOW_ACTION, choices=FOLLOW_ACTION_CHOICES, default=LEFT_OUT, error=ERR_BAD_FOLLOW_ACTION),
    Checked(name=ClipSlotSetting.SCALE, check=_check_scale_name, needs_song=True),
    *shape_settings(),
    *strum_settings(),
)


class ClipSlot(LlamaData):
    """A pattern to play, and how: its chain, repeats or loop, direction, morph and grab, and its own name if it has one.

    Settings the file leaves out are kept as None, meaning their defaults. A clip with no name of
    its own goes by its pattern's, on the grid and in everything exported, as the user asked on 2026-11-07. The pattern, chain and
    other patterns and tracks are kept as names, and looked up when the song renders.
    """

    __slots__ = ('_settings',)

    # A clip names the pattern it plays and the one it morphs to, the chain it runs and the track it grabs from.
    REFERENCES = {
        Section.PATTERNS: (ClipSlotSetting.PATTERN, ClipSlotSetting.MORPH_TO),
        Section.CHAINS: (ClipSlotSetting.CHAINS,),
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
        where = ERR_CLIP_SLOT_WHERE.format(where=where, track=track)
        with reading(where):
            if not isinstance(data, dict):
                raise InvalidValue(ERR_CLIP_SLOT_EXPECTED_SETTINGS.format(data=data))
            check_keys(data=data, allowed={*SETTINGS, ClipSlotSetting.CHAIN})
            _read_chain(data)
            check_settings(settings=SETTINGS, data=data, song=song)
            # What one setting may hold given another: a clip can't grab from its own track, a morph needs its target, its style and two repeats, and every clip plays a pattern.
            if ClipSlotSetting.GRAB_TRACK in data and data[ClipSlotSetting.GRAB_TRACK] == track:
                raise InvalidValue(ERR_GRABS_ITSELF)
            _check_morph(data=data, repeat=data.get(ClipSlotSetting.REPEAT, DEFAULT_REPEAT))
            if ClipSlotSetting.PATTERN not in data:
                raise InvalidValue(ERR_NEEDS_PATTERN)
            return cls(**data)

    def to_data(self):
        return written_settings(self._settings)

    def get_name(self):
        """Return the clip's own name, or None if it goes by its pattern's."""
        return self._settings[ClipSlotSetting.NAME]

    def get_display_name(self):
        """Return the name the clip shows and exports as: its own, or its pattern's."""
        return self.get_name() or self.get_pattern_name()

    def get_pattern_name(self):
        return self._settings[ClipSlotSetting.PATTERN]

    def get_setting(self, name):
        """Return one of its shape settings as the file writes it, like density_start, or None when it's left blank."""
        return self._settings[name]

    def get_strum(self):
        """Return how the clip strums its chords, or None when its Direction is blank and it takes its track's."""
        return strum_values(lambda part: self._settings[strum_setting(part)])

    @notes_change
    def set_strum_setting(self, *, part, value):
        """Set one part of the clip's strum, or None to leave it blank."""
        name = strum_setting(part)
        if value is not None:
            SETTINGS[name].check(value)
        self._settings[name] = value

    def get_shape(self, shape):
        """Return how a shape, Density, Swell or Articulate, runs over the clip, or None when the clip sets neither its start nor its end and takes its scene's."""
        return shape_values(settings=self._settings, shape=shape)

    @notes_change
    def set_shape_setting(self, *, name, value):
        """Set one part of a shape by its file name, like density_start, or None to leave it out."""
        if value is not None:
            SETTINGS[name].check(value)
        self._settings[name] = value

    def get_chain_names(self):
        """Return the names of the chains it runs, in order, before its scene's and its track's; none when it runs none."""
        return list(self._settings[ClipSlotSetting.CHAINS] or [])

    def loops(self):
        return bool(self._settings[ClipSlotSetting.LOOP])

    def get_repeat(self):
        repeat = self._settings[ClipSlotSetting.REPEAT]
        return DEFAULT_REPEAT if repeat is None else repeat

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
        """Return the name of its own scale, which wins over its scene's and its song's, or None to take theirs (the user's design of 2026-11-11)."""
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

    @notes_change
    def set_pattern_name(self, *, name, song):
        SETTINGS[ClipSlotSetting.PATTERN].check(name, song=song)
        self._settings[ClipSlotSetting.PATTERN] = name

    @notes_change
    def set_chain_names(self, *, names, song):
        """Send its notes through chains, by name, in order, or none for an empty list."""
        if names:
            SETTINGS[ClipSlotSetting.CHAINS].check(list(names), song=song)
        self._settings[ClipSlotSetting.CHAINS] = list(names) if names else None

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
        self._settings[ClipSlotSetting.REPEAT] = None if repeat == DEFAULT_REPEAT else repeat
        if self.get_repeat() < MIN_MORPH_REPEAT:
            self.clear_morph()

    @notes_change
    def set_direction(self, direction):
        """Override its pattern's play direction, or None to use the pattern's."""
        if direction is not None:
            SETTINGS[ClipSlotSetting.DIRECTION].check(direction)
        self._settings[ClipSlotSetting.DIRECTION] = direction

    @notes_change
    def set_morph(self, *, target, style, song):
        """Make it morph to a pattern across its repeats, in a style like 'left'."""
        if self.get_repeat() < MIN_MORPH_REPEAT:
            raise InvalidValue(ERR_MORPH_TOO_FEW_REPEATS.format(lowest=MIN_MORPH_REPEAT))
        SETTINGS[ClipSlotSetting.MORPH_TO].check(target, song=song)
        SETTINGS[ClipSlotSetting.MORPH_STYLE].check(style)
        self._settings[ClipSlotSetting.MORPH_TO] = target
        self._settings[ClipSlotSetting.MORPH_STYLE] = style

    @notes_change
    def set_morph_style(self, style):
        """Change how it morphs, which it has to be doing already."""
        if self.get_morph_target() is None:
            raise InvalidValue(ERR_MORPH_STYLE_WITHOUT_MORPH)
        SETTINGS[ClipSlotSetting.MORPH_STYLE].check(style)
        self._settings[ClipSlotSetting.MORPH_STYLE] = style

    @notes_change
    def clear_morph(self):
        self._settings[ClipSlotSetting.MORPH_TO] = None
        self._settings[ClipSlotSetting.MORPH_STYLE] = None

    @notes_change
    def set_scale_name(self, *, name, song):
        """Give it one of the song's scales of its own, which wins over its scene's and its song's, or None to take theirs."""
        if name is not None:
            SETTINGS[ClipSlotSetting.SCALE].check(name, song=song)
        self._settings[ClipSlotSetting.SCALE] = name

    @notes_change
    def set_follow_action(self, advance):
        """Set what it sends down in real-time playback when its scene is done, or None to take the set's default."""
        if advance is not None:
            SETTINGS[ClipSlotSetting.FOLLOW_ACTION].check(advance)
        self._settings[ClipSlotSetting.FOLLOW_ACTION] = advance

    @notes_change
    def set_grab_track(self, *, name, song, own_track):
        """Make its grab steps take notes from a track, which can't be its own, or None to stop grabbing."""
        if name is not None:
            SETTINGS[ClipSlotSetting.GRAB_TRACK].check(name, song=song)
            if name == own_track:
                raise InvalidValue(ERR_GRABS_ITSELF)
        self._settings[ClipSlotSetting.GRAB_TRACK] = name

    @notes_change
    def clear_grab(self):
        self._settings[ClipSlotSetting.GRAB_TRACK] = None


def _check_morph(*, data, repeat):
    """Refuse a morph without both its settings or without enough repeats, once each setting has been checked on its own."""
    if (ClipSlotSetting.MORPH_TO in data) != (ClipSlotSetting.MORPH_STYLE in data):
        raise InvalidValue(ERR_MORPH_NEEDS_BOTH)
    if ClipSlotSetting.MORPH_TO in data and repeat < MIN_MORPH_REPEAT:
        raise InvalidValue(ERR_MORPH_TOO_FEW_REPEATS.format(lowest=MIN_MORPH_REPEAT))


def _read_chain(data):
    """Read chain, from a file saved before a clip held a list of chains, as a list of one, in the file's own data, so that a correction made after finds what it reads."""
    if ClipSlotSetting.CHAIN not in data:
        return
    if ClipSlotSetting.CHAINS in data:
        raise InvalidValue(ERR_CHAIN_AND_CHAINS)
    data[ClipSlotSetting.CHAINS] = [data.pop(ClipSlotSetting.CHAIN)]
