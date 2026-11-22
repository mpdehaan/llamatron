# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A track: a column of the song, with settings that apply to every clip on it."""

from llamatron.caching.revised import notes_change
from llamatron.model.file import corrections
from llamatron.model.file.checks import is_whole_number_from, pass_over_unknown, reading
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.chain import check_chain_names
from llamatron.model.objects.conditions import statements_setting, with_statement
from llamatron.model.objects.groove import check_groove_choice
from llamatron.model.objects.llama_data import HoldsSettings, left_out_if_default, or_default, own_copy
from llamatron.model.objects.strum import strum_settings, strum_values
from llamatron.model.objects.traits import RunsChains
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import Section, strum_setting, TrackSetting
from llamatron.model.schema.setting import check_settings, Checked, Choice, described, Flag, WholeNumber
from llamatron.model.values import midi
from llamatron.user_strings import errors

# A track's settings, in the order they're written to a file.


def _no_cc_numbers():
    """Return the CC numbers of a track that sends no CC values: none for every lane."""
    return [None] * len(file_format.CC_ROWS)


def _is_cc_number_list(numbers):
    """Return whether numbers has a CC number, or None for a lane that sends nothing, for every CC lane."""
    if not isinstance(numbers, list) or len(numbers) != len(file_format.CC_ROWS):
        return False
    for number in numbers:
        if number is not None and not is_whole_number_from(value=number, lowest=midi.MIN_CC_NUMBER, highest=midi.MAX_CC_NUMBER):
            return False
    return True


def _check_cc_numbers(numbers):
    if not _is_cc_number_list(numbers):
        raise InvalidValue(errors.ERR_BAD_CC_NUMBERS.format(lanes=len(file_format.CC_ROWS), lowest=midi.MIN_CC_NUMBER, highest=midi.MAX_CC_NUMBER, value=numbers))


def _check_instrument_name(*, value, song):
    if not song.get_setlist().has_instrument(value):
        raise InvalidValue(errors.ERR_NO_SUCH_INSTRUMENT.format(name=value))


# A track's settings, each described once, in the order they're written to a file.
SETTINGS = described(
    Flag(name=TrackSetting.DRUM, error=errors.ERR_TRACK_NOT_TRUE_OR_FALSE),
    Flag(name=TrackSetting.MUTE, error=errors.ERR_TRACK_NOT_TRUE_OR_FALSE),
    WholeNumber(name=TrackSetting.TRANSPOSE, lowest=-limits.MAX_TRANSPOSE, highest=limits.MAX_TRANSPOSE, error=errors.ERR_BAD_TRANSPOSE),
    WholeNumber(name=TrackSetting.LOWEST_OCTAVE, lowest=limits.MIN_OCTAVE, highest=limits.MAX_OCTAVE, error=errors.ERR_BAD_TRACK_OCTAVE),
    WholeNumber(name=TrackSetting.HIGHEST_OCTAVE, lowest=limits.MIN_OCTAVE, highest=limits.MAX_OCTAVE, error=errors.ERR_BAD_TRACK_OCTAVE),
    Checked(name=TrackSetting.CC, check=_check_cc_numbers),
    Checked(name=TrackSetting.GROOVE, check=check_groove_choice, needs_song=True),
    Checked(name=TrackSetting.INSTRUMENT, check=_check_instrument_name, needs_song=True),
    *[Choice(name=name, choices=file_format.REGISTER_NAMES, default=corrections.LEFT_OUT, error=errors.ERR_BAD_BOUND_REGISTER) for name in file_format.CC_REGISTER_SETTINGS],
    Choice(name=TrackSetting.VELOCITY_REGISTER, choices=file_format.REGISTER_NAMES, default=corrections.LEFT_OUT, error=errors.ERR_BAD_BOUND_REGISTER),
    WholeNumber(name=TrackSetting.DEFAULT_VELOCITY, lowest=midi.MIN_VELOCITY, highest=midi.MAX_VELOCITY, error=errors.ERR_BAD_DEFAULT_VELOCITY),
    WholeNumber(name=TrackSetting.ACCENT, lowest=limits.MIN_STEP_ACCENT, highest=limits.MAX_STEP_ACCENT, error=errors.ERR_BAD_ACCENT),
    Checked(name=TrackSetting.CHAINS, check=check_chain_names, needs_song=True),
    *strum_settings(),
    statements_setting(TrackSetting.BYPASS_WHEN),
    statements_setting(TrackSetting.SKIP_WHEN),
)


class Track(RunsChains, HoldsSettings):
    """A track's settings: whether it's a drum track, whether it's muted, its transpose, octave range, CC numbers, groove and instrument, and the registers bound to its CC lanes and its velocity.

    A setting the file leaves out is kept as None and means its default, so that saving writes
    back only what was set.
    """

    __slots__ = ()

    SETTINGS = SETTINGS
    CHAINS_SETTING = TrackSetting.CHAINS

    # A track names the groove it chooses.
    REFERENCES = {Section.GROOVES: (TrackSetting.GROOVE,), Section.INSTRUMENTS: (TrackSetting.INSTRUMENT,)}
    CHAINS_NAMED_BY = (TrackSetting.CHAINS,)

    def __init__(
        self, *, drum=None, mute=None, transpose=None, lowest_octave=None, highest_octave=None, cc=None, groove=None, instrument=None,
        cc1_register=None, cc2_register=None, cc3_register=None, cc4_register=None, velocity_register=None, default_velocity=None, accent=None, chains=None,
        strum_direction=None, strum_spread=None, strum_fade=None, strum_loose_timing=None, strum_upstroke_strings=None,
        bypass_when=None, skip_when=None,
    ):
        self.note_change()
        self._settings = {
            TrackSetting.DRUM: drum, TrackSetting.MUTE: mute, TrackSetting.TRANSPOSE: transpose,
            TrackSetting.LOWEST_OCTAVE: lowest_octave, TrackSetting.HIGHEST_OCTAVE: highest_octave, TrackSetting.CC: own_copy(cc), TrackSetting.GROOVE: groove,
            TrackSetting.INSTRUMENT: instrument, TrackSetting.CC1_REGISTER: cc1_register, TrackSetting.CC2_REGISTER: cc2_register,
            TrackSetting.CC3_REGISTER: cc3_register, TrackSetting.CC4_REGISTER: cc4_register, TrackSetting.VELOCITY_REGISTER: velocity_register, TrackSetting.DEFAULT_VELOCITY: default_velocity, TrackSetting.ACCENT: accent,
            TrackSetting.CHAINS: own_copy(chains), TrackSetting.STRUM_DIRECTION: strum_direction, TrackSetting.STRUM_SPREAD: strum_spread,
            TrackSetting.STRUM_FADE: strum_fade, TrackSetting.STRUM_LOOSE_TIMING: strum_loose_timing, TrackSetting.STRUM_UPSTROKE_STRINGS: strum_upstroke_strings,
            TrackSetting.BYPASS_WHEN: own_copy(bypass_when), TrackSetting.SKIP_WHEN: own_copy(skip_when),
        }

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            if data is None:
                data = {}
            if not isinstance(data, dict):
                raise InvalidValue(errors.ERR_TRACK_EXPECTED_SETTINGS.format(data=data))
            pass_over_unknown(data=data, allowed=SETTINGS)
            check_settings(settings=SETTINGS, data=data, song=song)
            _check_octave_order(lowest=data.get(TrackSetting.LOWEST_OCTAVE, limits.MIN_OCTAVE), highest=data.get(TrackSetting.HIGHEST_OCTAVE, limits.MAX_OCTAVE))
            settings = {name: data.get(name) for name in SETTINGS}
            return cls(**settings)

    def is_drum(self):
        return bool(self._settings[TrackSetting.DRUM])

    def is_muted(self):
        return bool(self._settings[TrackSetting.MUTE])

    def get_transpose(self):
        """Return how many scale notes the track moves its notes, which is always 0 on a drum track."""
        if self.is_drum():
            return defaults.DEFAULT_TRANSPOSE
        transpose = self._settings[TrackSetting.TRANSPOSE]
        if transpose is None:
            return defaults.DEFAULT_TRANSPOSE
        return transpose

    def get_default_velocity(self):
        """Return the velocity a step with none typed plays at on the track, or None where the track leaves that to its instrument."""
        return self._settings[TrackSetting.DEFAULT_VELOCITY]

    def get_accent(self):
        """Return what an accented step adds to its velocity on the track, on top of its instrument's accent."""
        return or_default(value=self._settings[TrackSetting.ACCENT], default=defaults.DEFAULT_TRACK_ACCENT)

    def get_written_accent(self):
        """Return its accent as the file holds it, or None for the default."""
        return self._settings[TrackSetting.ACCENT]

    def set_default_velocity(self, velocity):
        """Set the velocity a step with none typed plays at, or None to take the instrument's."""
        self.set_written(name=TrackSetting.DEFAULT_VELOCITY, value=velocity)

    def set_accent(self, accent):
        """Set what an accented step adds to its velocity, or None for the default."""
        self.set_written(name=TrackSetting.ACCENT, value=accent)

    def get_lowest_octave(self):
        """Return the lowest octave the track's instrument plays, the bottom of the MIDI range unless set."""
        return or_default(value=self._settings[TrackSetting.LOWEST_OCTAVE], default=limits.MIN_OCTAVE)

    def get_highest_octave(self):
        """Return the highest octave the track's instrument plays, the top of the MIDI range unless set."""
        return or_default(value=self._settings[TrackSetting.HIGHEST_OCTAVE], default=limits.MAX_OCTAVE)

    @notes_change
    def set_lowest_octave(self, octave):
        """Set the lowest octave it plays, which can't be above the highest; the bottom of the MIDI range is left out of the file."""
        SETTINGS[TrackSetting.LOWEST_OCTAVE].check(octave)
        _check_octave_order(lowest=octave, highest=self.get_highest_octave())
        self._settings[TrackSetting.LOWEST_OCTAVE] = left_out_if_default(value=octave, default=limits.MIN_OCTAVE)

    @notes_change
    def set_highest_octave(self, octave):
        """Set the highest octave it plays, which can't be below the lowest; the top of the MIDI range is left out of the file."""
        SETTINGS[TrackSetting.HIGHEST_OCTAVE].check(octave)
        _check_octave_order(lowest=self.get_lowest_octave(), highest=octave)
        self._settings[TrackSetting.HIGHEST_OCTAVE] = left_out_if_default(value=octave, default=limits.MAX_OCTAVE)

    def get_groove_choice(self):
        """Return the groove it chooses by name, False for no groove on this track whatever the scene and song choose, or None to take theirs."""
        return self._settings[TrackSetting.GROOVE]

    def get_instrument_name(self):
        """Return the name of the instrument real-time playback sends it to, or None for none, which leaves the track out."""
        return self._settings[TrackSetting.INSTRUMENT]

    def set_instrument_name(self, *, name, song):
        """Send it to an instrument of the set by name in real-time playback, or None for none."""
        self.set_written(name=TrackSetting.INSTRUMENT, value=name, song=song)

    @notes_change
    def set_groove_choice(self, *, choice, song):
        """Choose a groove by name, False for none on this track, or None to take the scene's or the song's."""
        SETTINGS[TrackSetting.GROOVE].check(choice, song=song)
        self._settings[TrackSetting.GROOVE] = choice

    def get_cc_numbers(self):
        """Return the CC number each of a pattern's CC lanes sends on this track, or None for a lane it doesn't use."""
        numbers = self._settings[TrackSetting.CC]
        if numbers is None:
            return _no_cc_numbers()
        return list(numbers)

    def get_cc_registers(self):
        """Return the register each CC lane is bound to, in lane order, or None for a lane that isn't bound."""
        return [self._settings[name] for name in file_format.CC_REGISTER_SETTINGS]

    def binds_registers(self):
        """Return whether any CC lane or the velocity is bound to a register."""
        return any(self.get_cc_registers()) or self.get_velocity_register() is not None

    @notes_change
    def set_cc_register(self, *, lane, register):
        """Bind one of the four CC lanes to a register by name, or None to bind it to nothing."""
        if not is_whole_number_from(value=lane, lowest=0, highest=len(file_format.CC_ROWS) - 1):
            raise InvalidValue(errors.ERR_NO_SUCH_LANE.format(lane=lane, last=len(file_format.CC_ROWS) - 1))
        name = file_format.CC_REGISTER_SETTINGS[lane]
        if register is not None:
            SETTINGS[name].check(register)
        self._settings[name] = register

    def get_velocity_register(self):
        """Return the register a note with no velocity of its own plays at, or None for none."""
        return self._settings[TrackSetting.VELOCITY_REGISTER]

    def set_velocity_register(self, register):
        """Bind the velocity to a register by name, or None to bind it to nothing."""
        self.set_written(name=TrackSetting.VELOCITY_REGISTER, value=register)

    def get_strum_setting(self, part):
        """Return one part of the track's strum as the file writes it, like its spread, or None when it's blank."""
        return self._settings[strum_setting(part)]

    def get_strum(self):
        """Return how the track strums its chords, or None when its Direction is blank."""
        return strum_values(self.get_strum_setting)

    def set_strum_setting(self, *, part, value):
        """Set one part of the track's strum, or None to leave it blank."""
        name = strum_setting(part)
        self.set_written(name=name, value=value)

    def get_statements(self, name):
        """Return one of its tables of statements about the registers, by the setting's name: the one that bypasses its clips' generators or the one that makes its clips sit out."""
        return own_copy(self._settings[name] or [])

    @notes_change
    def set_statement(self, *, name, place, statement):
        """Write the statement at a place of one of its tables, add one just past the last, or remove one with None."""
        table = with_statement(statements=self._settings[name], place=place, statement=statement)
        if table is not None:
            SETTINGS[name].check(table)
        self._settings[name] = table

    def copy(self):
        settings = dict(self._settings)
        if settings[TrackSetting.CC]:
            settings[TrackSetting.CC] = self.get_cc_numbers()
        else:
            settings[TrackSetting.CC] = None
        settings[TrackSetting.CHAINS] = own_copy(settings[TrackSetting.CHAINS])
        return Track(**settings)

    # Changing the track. A setting at its default is left out of the file.

    def set_drum(self, drum):
        self._set_flag(flag=TrackSetting.DRUM, on=drum)

    def set_mute(self, mute):
        self._set_flag(flag=TrackSetting.MUTE, on=mute)

    @notes_change
    def set_transpose(self, transpose):
        """Set how far it moves its notes along the scale, which can be negative."""
        SETTINGS[TrackSetting.TRANSPOSE].check(transpose)
        self._settings[TrackSetting.TRANSPOSE] = left_out_if_default(value=transpose, default=defaults.DEFAULT_TRANSPOSE)

    @notes_change
    def set_cc_number(self, *, lane, number):
        """Set the CC number one of the four lanes sends, or None for a lane that sends nothing."""
        if not is_whole_number_from(value=lane, lowest=0, highest=len(file_format.CC_ROWS) - 1):
            raise InvalidValue(errors.ERR_NO_SUCH_LANE.format(lane=lane, last=len(file_format.CC_ROWS) - 1))
        numbers = self.get_cc_numbers()
        numbers[lane] = number
        SETTINGS[TrackSetting.CC].check(numbers)
        self._settings[TrackSetting.CC] = left_out_if_default(value=numbers, default=_no_cc_numbers())

    @notes_change
    def _set_flag(self, *, flag, on):
        """Turn a flag on, or off, which the file leaves out."""
        SETTINGS[flag].check(on)
        self._settings[flag] = None
        if on:
            self._settings[flag] = True


def _check_octave_order(*, lowest, highest):
    """Check that a track's lowest octave isn't above its highest, once each has been checked on its own."""
    if lowest > highest:
        raise InvalidValue(errors.ERR_OCTAVE_RANGE_BACKWARDS.format(lowest=lowest, highest=highest))
