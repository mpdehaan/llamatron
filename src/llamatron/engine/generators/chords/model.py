# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Chords plugin's model: its Mode, Voicing, Progression or Follow Progression; a progression's chords, each with a sharp or
flat, an inversion, a borrowed scale type, a quality and tensions, and how long each lasts; the track whose chords it follows; and
its Voicing, voice leading on or off, its octaves and whether the root stays in the bass, which every mode has."""

from llamatron.caching.revised import notes_change
from llamatron.engine.generators import settings_base
from llamatron.engine.generators.chords.following import FollowChords
from llamatron.engine.generators.chords.progression import Progression
from llamatron.engine.generators.chords.voicing import VoiceLeading
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.file import corrections
from llamatron.model.file.checks import Bars, is_whole_number_from, listed, time_length
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.llama_data import or_default
from llamatron.model.objects.named_scale import scale_type_names
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Accidental, Section
from llamatron.model.schema.setting import Checked, Choice, described, Flag, Text, WholeNumber
from llamatron.model.values import note
from llamatron.user_strings import errors

# What a Chords generator does to a part's notes before voicing them, as a file names it.
VOICING = 'voicing'
PROGRESSION = 'progression'
FOLLOW_PROGRESSION = 'follow_progression'
MODES = [VOICING, PROGRESSION, FOLLOW_PROGRESSION]
DEFAULT_MODE = VOICING


class ChordsSetting:
    """A Chords generator's own settings, as a file names them, beside its progression's (ProgressionSetting): its Mode, the track
    it follows in Follow Progression, and its Voicing."""

    MODE = 'mode'
    CHORDS_FROM = 'chords_from'
    VOICE_LEADING = 'voice_leading'
    LOWEST_OCTAVE = 'lowest_octave'
    HIGHEST_OCTAVE = 'highest_octave'
    ROOT_IN_BASS = 'root_in_bass'


DEFAULT_VOICING_LOWEST_OCTAVE = 4
DEFAULT_VOICING_HIGHEST_OCTAVE = 6


class ProgressionSetting:
    """A Chords generator's progression, as a file names it: its chords as degrees, a sharp or flat and an inversion for each, and
    how long each chord lasts."""


    EVERY = 'every'
    CHORDS = 'chords'
    ACCIDENTALS = 'accidentals'
    INVERSIONS = 'inversions'
    # The scale type each chord borrows, its named quality, and the tensions on top, each beside the chords.
    SCALES = 'scales'
    QUALITIES = 'qualities'
    TENSIONS = 'tensions'


def _check_progression_chords(chords):
    """Check a progression's chords: a list of 1 to MAX_PROGRESSION_CHORDS degrees."""
    fits = isinstance(chords, list) and limits.MIN_PROGRESSION_CHORDS <= len(chords) <= limits.MAX_PROGRESSION_CHORDS and all(
        is_whole_number_from(value=degree, lowest=limits.MIN_PROGRESSION_DEGREE, highest=limits.MAX_PROGRESSION_DEGREE) for degree in chords)
    if not fits:
        raise InvalidValue(errors.ERR_BAD_PROGRESSION_CHORDS.format(most=limits.MAX_PROGRESSION_CHORDS, lowest=limits.MIN_PROGRESSION_DEGREE, highest=limits.MAX_PROGRESSION_DEGREE, value=chords))


def _row_of(*, name, allowed):
    """Return a check of a list beside the chords, each step one of the allowed values or nothing."""
    def check(values):
        if not isinstance(values, list) or not all(value is None or value in allowed for value in values):
            raise InvalidValue(errors.ERR_BAD_PROGRESSION_ROW.format(name=name, choices=listed(allowed), value=values))
    return check


def _tensions_row(values):
    """Check a progression's tensions: a list beside the chords, each step a list of some of the tensions, each once, or nothing."""
    def is_tensions(value):
        return isinstance(value, (list, tuple)) and len(value) > 0 and len(set(value)) == len(value) and all(tension in file_format.TENSIONS for tension in value)
    if not isinstance(values, list) or not all(value is None or is_tensions(value) for value in values):
        raise InvalidValue(errors.ERR_BAD_PROGRESSION_TENSIONS.format(name=ProgressionSetting.TENSIONS, choices=listed(file_format.TENSIONS), value=values))


# What a progression's sharp-or-flat and inversion rows may hold beside nothing.
PROGRESSION_ACCIDENTALS = [Accidental.SHARP, Accidental.FLAT]


PROGRESSION_INVERSIONS = list(range(1, limits.MAX_PROGRESSION_INVERSION + 1))


# A new progression's one chord, I, which moves nothing until it's edited.
NEW_PROGRESSION_CHORDS = [1]


# The rows beside a progression's chords, each as long as the chords.
PROGRESSION_ROWS = (
    ProgressionSetting.ACCIDENTALS, ProgressionSetting.INVERSIONS, ProgressionSetting.SCALES, ProgressionSetting.QUALITIES, ProgressionSetting.TENSIONS,
)


class ChordsSettings(GeneratorSettings):
    """A Chords generator's settings: its Mode, its progression or the track it follows, and its Voicing, voice leading on in
    Voicing mode and off in the others unless set."""

    __slots__ = ()

    SETTINGS = described(
        Choice(name=ChordsSetting.MODE, choices=MODES, default=corrections.LEFT_OUT, error=errors.ERR_BAD_CHORDS_MODE),
        Checked(name=ProgressionSetting.EVERY, check=time_length),
        Checked(name=ProgressionSetting.CHORDS, check=_check_progression_chords),
        Checked(name=ProgressionSetting.ACCIDENTALS, check=_row_of(name=ProgressionSetting.ACCIDENTALS, allowed=PROGRESSION_ACCIDENTALS)),
        Checked(name=ProgressionSetting.INVERSIONS, check=_row_of(name=ProgressionSetting.INVERSIONS, allowed=PROGRESSION_INVERSIONS)),
        Checked(name=ProgressionSetting.SCALES, check=_row_of(name=ProgressionSetting.SCALES, allowed=scale_type_names())),
        Checked(name=ProgressionSetting.QUALITIES, check=_row_of(name=ProgressionSetting.QUALITIES, allowed=list(file_format.FIXED_CHORDS))),
        Checked(name=ProgressionSetting.TENSIONS, check=_tensions_row),
        Text(name=ChordsSetting.CHORDS_FROM, error=errors.ERR_NOT_TEXT),
        Flag(name=ChordsSetting.VOICE_LEADING, error=errors.ERR_VOICE_LEADING_NOT_TRUE_OR_FALSE),
        WholeNumber(name=ChordsSetting.LOWEST_OCTAVE, lowest=note.MIN_OCTAVE, highest=note.MAX_OCTAVE, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=ChordsSetting.HIGHEST_OCTAVE, lowest=note.MIN_OCTAVE, highest=note.MAX_OCTAVE, error=errors.ERR_BAD_SHAPE_PERCENT),
        Flag(name=ChordsSetting.ROOT_IN_BASS, error=errors.ERR_ROOT_IN_BASS_NOT_TRUE_OR_FALSE),
        settings_base.RESTART_SETTING,
    )
    TAKEN_AS = {ProgressionSetting.EVERY: time_length}
    REFERENCES = {Section.TRACKS: (ChordsSetting.CHORDS_FROM,)}

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: Voicing mode, voicing a part's chords nearest the one before."""
        return cls({})

    @classmethod
    def check_data(cls, data):
        super().check_data(data)
        lowest = data.get(ChordsSetting.LOWEST_OCTAVE, DEFAULT_VOICING_LOWEST_OCTAVE)
        highest = data.get(ChordsSetting.HIGHEST_OCTAVE, DEFAULT_VOICING_HIGHEST_OCTAVE)
        if lowest > highest:
            raise InvalidValue(errors.ERR_VOICE_LEADING_RANGE.format(lowest=lowest, highest=highest))

    def get_mode(self):
        return or_default(value=self.get_written(ChordsSetting.MODE), default=DEFAULT_MODE)

    def voices(self):
        """Return whether it voices each chord nearest the one before: as set, else in Voicing mode alone."""
        written = self.get_written(ChordsSetting.VOICE_LEADING)
        if written is None:
            return self.get_mode() == VOICING
        return written

    def limits_of(self, name):
        """Return the lowest and highest a number may be: an end of the octaves never past the other end."""
        lowest, highest = super().limits_of(name)
        if name == ChordsSetting.LOWEST_OCTAVE:
            return lowest, self.get_highest_octave()
        if name == ChordsSetting.HIGHEST_OCTAVE:
            return self.get_lowest_octave(), highest
        return lowest, highest

    def progression(self, *, bar, continuation):
        """Return the generator that moves a part through its progression, its chords lasting a bar each unless set."""
        every = time_length(self.get_written(ProgressionSetting.EVERY) or file_format.ONE_BAR_WRITTEN)
        if isinstance(every, Bars):
            every = bar * every.count
        return Progression(
            chords=self.get_chords(), every=every, accidentals=self.get_accidentals(), inversions=self.get_inversions(),
            scales=self.get_scales(), qualities=self.get_qualities(), tensions=self.get_tensions(), continuation=continuation,
        )

    def following(self, chords):
        """Return the generator that moves a part along the chords another track plays, given them."""
        return FollowChords(chords=chords)

    def voicing(self, continuation):
        """Return the generator that voices each chord nearest the one before, within its octaves."""
        return VoiceLeading(
            lowest_octave=self.get_lowest_octave(), highest_octave=self.get_highest_octave(), root_in_bass=self.keeps_root_in_bass(),
            continuation=continuation,
        )

    # The progression.

    def get_every(self):
        return self.get_written(ProgressionSetting.EVERY)

    def get_chords(self):
        return list(self.get_written(ProgressionSetting.CHORDS) or NEW_PROGRESSION_CHORDS)

    def get_accidentals(self):
        return _lined_up(values=self.get_written(ProgressionSetting.ACCIDENTALS), count=len(self.get_chords()))

    def get_inversions(self):
        return _lined_up(values=self.get_written(ProgressionSetting.INVERSIONS), count=len(self.get_chords()))

    def get_scales(self):
        """Return the scale type each chord borrows, or None for the clip's own."""
        return _lined_up(values=self.get_written(ProgressionSetting.SCALES), count=len(self.get_chords()))

    def get_qualities(self):
        """Return each chord's named quality, a chord symbol, or None for the chord its scale builds."""
        return _lined_up(values=self.get_written(ProgressionSetting.QUALITIES), count=len(self.get_chords()))

    def get_tensions(self):
        """Return each chord's tensions as a tuple, lowest first, or None for none."""
        return [_tensions_in_order(value) for value in _lined_up(values=self.get_written(ProgressionSetting.TENSIONS), count=len(self.get_chords()))]

    def set_progression(self, rows):
        """Set the progression's chords and the rows beside them, given as ProgressionRows, a row of nothing left out."""
        written = {
            ProgressionSetting.CHORDS: rows.chords, ProgressionSetting.ACCIDENTALS: rows.accidentals, ProgressionSetting.INVERSIONS: rows.inversions,
            ProgressionSetting.SCALES: rows.scales, ProgressionSetting.QUALITIES: rows.qualities, ProgressionSetting.TENSIONS: _tensions_written(rows.tensions),
        }
        for setting, values in written.items():
            self.set_setting(name=setting, value=_row_written(values))

    # Following another track.

    def get_chords_from(self):
        """Return the name of the track whose chords it follows, or None for none."""
        return self.get_written(ChordsSetting.CHORDS_FROM)

    def names_item(self, *, section, name):
        return section == Section.TRACKS and self.get_chords_from() == name

    # The voicing.

    def get_lowest_octave(self):
        return or_default(value=self.get_written(ChordsSetting.LOWEST_OCTAVE), default=DEFAULT_VOICING_LOWEST_OCTAVE)

    def get_highest_octave(self):
        return or_default(value=self.get_written(ChordsSetting.HIGHEST_OCTAVE), default=DEFAULT_VOICING_HIGHEST_OCTAVE)

    def keeps_root_in_bass(self):
        return bool(self.get_written(ChordsSetting.ROOT_IN_BASS))

    @notes_change
    def _rename_own_references(self, *, section, old, new):
        self._settings[ChordsSetting.CHORDS_FROM] = new


def _lined_up(*, values, count):
    """Return a row beside the chords as long as the chords, a missing step being nothing."""
    values = list(values or [])
    return (values + [None] * count)[:count]


def _tensions_in_order(value):
    """Return the tensions a chord's value holds, in the order the tensions come, as a tuple, or None for none."""
    if value is None:
        return None
    tensions = [tension for tension in file_format.TENSIONS if tension in value]
    return tuple(tensions)


def _tensions_written(tensions):
    """Return each chord's tensions as a file writes them, a list, or None for none."""
    written = []
    for value in tensions:
        if value is None:
            written.append(None)
        else:
            written.append(list(value))
    return written


def _row_written(values):
    """Return a row beside the chords as a file writes it, or None where every step is nothing."""
    if any(value is not None for value in values):
        return list(values)
    return None
