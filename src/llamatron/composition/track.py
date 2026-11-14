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

"""A track: a column of the song, with settings that apply to every clip on it."""

from llamatron.composition.chain import check_chain_names
from llamatron.composition.strum import strum_settings, strum_values
from llamatron.composition.euclid import euclid_settings, euclid_values
from llamatron.composition.checks import reading, check_keys, is_whole_number_from
from llamatron.composition.defaults import DEFAULT_TRANSPOSE
from llamatron.composition.corrections import LEFT_OUT
from llamatron.composition.file_format import euclid_setting, strum_setting, CC_REGISTER_SETTINGS, CC_ROWS, REGISTER_NAMES, Section, TrackSetting
from llamatron.composition.groove import check_groove_choice
from llamatron.composition.limits import MAX_OCTAVE, MAX_TRANSPOSE, MIN_OCTAVE
from llamatron.music.midi import MAX_CC_NUMBER, MIN_CC_NUMBER
from llamatron.composition.llama_data import LlamaData, or_default, own_copy, written_settings
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.setting import Checked, Choice, Flag, WholeNumber, check_settings, described
from llamatron.strings.errors import (
    ERR_BAD_BOUND_REGISTER, ERR_BAD_CC_NUMBERS, ERR_BAD_TRACK_OCTAVE, ERR_BAD_TRANSPOSE, ERR_NO_SUCH_LANE, ERR_OCTAVE_RANGE_BACKWARDS, ERR_TRACK_EXPECTED_SETTINGS,
    ERR_NO_SUCH_INSTRUMENT, ERR_TRACK_NOT_TRUE_OR_FALSE,
)
from llamatron.support.revised import notes_change

# A track's settings, in the order they're written to a file.


def _no_cc_numbers():
    """Return the CC numbers of a track that sends no CC values: none for every lane."""
    return [None] * len(CC_ROWS)


def _is_cc_number_list(numbers):
    """Return whether numbers has a CC number, or None for a lane that sends nothing, for every CC lane."""
    return isinstance(numbers, list) and len(numbers) == len(CC_ROWS) and all(
        number is None or is_whole_number_from(value=number, lowest=MIN_CC_NUMBER, highest=MAX_CC_NUMBER) for number in numbers
    )


def _check_cc_numbers(numbers):
    if not _is_cc_number_list(numbers):
        raise InvalidValue(ERR_BAD_CC_NUMBERS.format(lanes=len(CC_ROWS), lowest=MIN_CC_NUMBER, highest=MAX_CC_NUMBER, value=numbers))


def _check_instrument_name(*, value, song):
    if not song.has_instrument(value):
        raise InvalidValue(ERR_NO_SUCH_INSTRUMENT.format(name=value))


# A track's settings, each described once, in the order they're written to a file.
SETTINGS = described(
    Flag(name=TrackSetting.DRUM, error=ERR_TRACK_NOT_TRUE_OR_FALSE),
    Flag(name=TrackSetting.MUTE, error=ERR_TRACK_NOT_TRUE_OR_FALSE),
    WholeNumber(name=TrackSetting.TRANSPOSE, lowest=-MAX_TRANSPOSE, highest=MAX_TRANSPOSE, error=ERR_BAD_TRANSPOSE),
    WholeNumber(name=TrackSetting.LOWEST_OCTAVE, lowest=MIN_OCTAVE, highest=MAX_OCTAVE, error=ERR_BAD_TRACK_OCTAVE),
    WholeNumber(name=TrackSetting.HIGHEST_OCTAVE, lowest=MIN_OCTAVE, highest=MAX_OCTAVE, error=ERR_BAD_TRACK_OCTAVE),
    Checked(name=TrackSetting.CC, check=_check_cc_numbers),
    Checked(name=TrackSetting.GROOVE, check=check_groove_choice, needs_song=True),
    Checked(name=TrackSetting.INSTRUMENT, check=_check_instrument_name, needs_song=True),
    *[Choice(name=name, choices=REGISTER_NAMES, default=LEFT_OUT, error=ERR_BAD_BOUND_REGISTER) for name in CC_REGISTER_SETTINGS],
    Choice(name=TrackSetting.VELOCITY_REGISTER, choices=REGISTER_NAMES, default=LEFT_OUT, error=ERR_BAD_BOUND_REGISTER),
    Checked(name=TrackSetting.CHAINS, check=check_chain_names, needs_song=True),
    *strum_settings(),
    *euclid_settings(),
)


class Track(LlamaData):
    """A track's settings: whether it's a drum track, whether it's muted, its transpose, octave range, CC numbers, groove and instrument, and the registers bound to its CC lanes and its velocity.

    A setting the file leaves out is kept as None and means its default, so that saving writes
    back only what was set.
    """

    __slots__ = ('_settings',)

    # A track names the groove it chooses.
    REFERENCES = {Section.GROOVES: (TrackSetting.GROOVE,), Section.INSTRUMENTS: (TrackSetting.INSTRUMENT,), Section.CHAINS: (TrackSetting.CHAINS,)}

    def __init__(
        self, *, drum=None, mute=None, transpose=None, lowest_octave=None, highest_octave=None, cc=None, groove=None, instrument=None,
        cc1_register=None, cc2_register=None, cc3_register=None, cc4_register=None, velocity_register=None, chains=None,
        strum_direction=None, strum_spread=None, strum_fade=None, strum_loose_timing=None, strum_upstroke_strings=None,
        euclid_hits=None, euclid_steps=None, euclid_rotate=None, euclid_step=None,
    ):
        self.note_change()
        self._settings = {
            TrackSetting.DRUM: drum, TrackSetting.MUTE: mute, TrackSetting.TRANSPOSE: transpose,
            TrackSetting.LOWEST_OCTAVE: lowest_octave, TrackSetting.HIGHEST_OCTAVE: highest_octave, TrackSetting.CC: own_copy(cc), TrackSetting.GROOVE: groove,
            TrackSetting.INSTRUMENT: instrument, TrackSetting.CC1_REGISTER: cc1_register, TrackSetting.CC2_REGISTER: cc2_register,
            TrackSetting.CC3_REGISTER: cc3_register, TrackSetting.CC4_REGISTER: cc4_register, TrackSetting.VELOCITY_REGISTER: velocity_register,
            TrackSetting.CHAINS: own_copy(chains), TrackSetting.STRUM_DIRECTION: strum_direction, TrackSetting.STRUM_SPREAD: strum_spread,
            TrackSetting.STRUM_FADE: strum_fade, TrackSetting.STRUM_LOOSE_TIMING: strum_loose_timing, TrackSetting.STRUM_UPSTROKE_STRINGS: strum_upstroke_strings,
            TrackSetting.EUCLID_HITS: euclid_hits, TrackSetting.EUCLID_STEPS: euclid_steps, TrackSetting.EUCLID_ROTATE: euclid_rotate, TrackSetting.EUCLID_STEP: euclid_step,
        }

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            data = {} if data is None else data
            if not isinstance(data, dict):
                raise InvalidValue(ERR_TRACK_EXPECTED_SETTINGS.format(data=data))
            check_keys(data=data, allowed=set(SETTINGS))
            check_settings(settings=SETTINGS, data=data, song=song)
            _check_octave_order(lowest=data.get(TrackSetting.LOWEST_OCTAVE, MIN_OCTAVE), highest=data.get(TrackSetting.HIGHEST_OCTAVE, MAX_OCTAVE))
            return cls(**{name: data.get(name) for name in SETTINGS})

    def to_data(self):
        return written_settings(self._settings)

    def is_drum(self):
        return bool(self._settings[TrackSetting.DRUM])

    def is_muted(self):
        return bool(self._settings[TrackSetting.MUTE])

    def get_transpose(self):
        """Return how many scale notes the track moves its notes, which is always 0 on a drum track."""
        if self.is_drum():
            return DEFAULT_TRANSPOSE
        transpose = self._settings[TrackSetting.TRANSPOSE]
        return DEFAULT_TRANSPOSE if transpose is None else transpose

    def get_lowest_octave(self):
        """Return the lowest octave the track's instrument plays, the bottom of the MIDI range unless set."""
        return or_default(value=self._settings[TrackSetting.LOWEST_OCTAVE], default=MIN_OCTAVE)

    def get_highest_octave(self):
        """Return the highest octave the track's instrument plays, the top of the MIDI range unless set."""
        return or_default(value=self._settings[TrackSetting.HIGHEST_OCTAVE], default=MAX_OCTAVE)

    @notes_change
    def set_lowest_octave(self, octave):
        """Set the lowest octave it plays, which can't be above the highest; the bottom of the MIDI range is left out of the file."""
        SETTINGS[TrackSetting.LOWEST_OCTAVE].check(octave)
        _check_octave_order(lowest=octave, highest=self.get_highest_octave())
        self._settings[TrackSetting.LOWEST_OCTAVE] = None if octave == MIN_OCTAVE else octave

    @notes_change
    def set_highest_octave(self, octave):
        """Set the highest octave it plays, which can't be below the lowest; the top of the MIDI range is left out of the file."""
        SETTINGS[TrackSetting.HIGHEST_OCTAVE].check(octave)
        _check_octave_order(lowest=self.get_lowest_octave(), highest=octave)
        self._settings[TrackSetting.HIGHEST_OCTAVE] = None if octave == MAX_OCTAVE else octave

    def get_groove_choice(self):
        """Return the groove it chooses by name, False for no groove on this track whatever the scene and song choose, or None to take theirs."""
        return self._settings[TrackSetting.GROOVE]

    def get_instrument_name(self):
        """Return the name of the instrument real-time playback sends it to, or None for none, which leaves the track out."""
        return self._settings[TrackSetting.INSTRUMENT]

    @notes_change
    def set_instrument_name(self, *, name, song):
        """Send it to an instrument of the set by name in real-time playback, or None for none."""
        if name is not None:
            SETTINGS[TrackSetting.INSTRUMENT].check(name, song=song)
        self._settings[TrackSetting.INSTRUMENT] = name

    @notes_change
    def set_groove_choice(self, *, choice, song):
        """Choose a groove by name, False for none on this track, or None to take the scene's or the song's."""
        SETTINGS[TrackSetting.GROOVE].check(choice, song=song)
        self._settings[TrackSetting.GROOVE] = choice

    def get_cc_numbers(self):
        """Return the CC number each of a pattern's CC lanes sends on this track, or None for a lane it doesn't use."""
        numbers = self._settings[TrackSetting.CC]
        return _no_cc_numbers() if numbers is None else list(numbers)

    def get_cc_registers(self):
        """Return the register each CC lane is bound to, in lane order, or None for a lane that isn't bound."""
        return [self._settings[name] for name in CC_REGISTER_SETTINGS]

    def binds_registers(self):
        """Return whether any CC lane or the velocity is bound to a register."""
        return any(self.get_cc_registers()) or self.get_velocity_register() is not None

    @notes_change
    def set_cc_register(self, *, lane, register):
        """Bind one of the four CC lanes to a register by name, or None to bind it to nothing."""
        if not is_whole_number_from(value=lane, lowest=0, highest=len(CC_ROWS) - 1):
            raise InvalidValue(ERR_NO_SUCH_LANE.format(lane=lane, last=len(CC_ROWS) - 1))
        name = CC_REGISTER_SETTINGS[lane]
        if register is not None:
            SETTINGS[name].check(register)
        self._settings[name] = register

    def get_velocity_register(self):
        """Return the register a note with no velocity of its own plays at, or None for none."""
        return self._settings[TrackSetting.VELOCITY_REGISTER]

    @notes_change
    def set_velocity_register(self, register):
        """Bind the velocity to a register by name, or None to bind it to nothing."""
        if register is not None:
            SETTINGS[TrackSetting.VELOCITY_REGISTER].check(register)
        self._settings[TrackSetting.VELOCITY_REGISTER] = register

    def get_strum_setting(self, part):
        """Return one part of the track's strum as the file writes it, like its spread, or None when it's blank."""
        return self._settings[strum_setting(part)]

    def get_strum(self):
        """Return how the track strums its chords, or None when its Direction is blank."""
        return strum_values(self.get_strum_setting)

    @notes_change
    def set_strum_setting(self, *, part, value):
        """Set one part of the track's strum, or None to leave it blank."""
        name = strum_setting(part)
        if value is not None:
            SETTINGS[name].check(value)
        self._settings[name] = value

    def get_euclid_setting(self, part):
        """Return one part of the track's Euclidean mask as the file writes it, or None when it's blank."""
        return self._settings[euclid_setting(part)]

    def get_euclid(self):
        """Return the track's Euclidean mask, or None when its hits are blank."""
        return euclid_values(self.get_euclid_setting)

    @notes_change
    def set_euclid_setting(self, *, part, value):
        """Set one part of the track's Euclidean mask, or None to leave it blank."""
        name = euclid_setting(part)
        if value is not None:
            SETTINGS[name].check(value)
        self._settings[name] = value

    def get_chain_names(self):
        """Return the names of the chains every clip on the track runs, after the clip's and the scene's, in order."""
        return list(self._settings[TrackSetting.CHAINS] or [])

    @notes_change
    def set_chain_names(self, *, names, song):
        """Set the chains every clip on the track runs, by name, in order, or none for an empty list."""
        if names:
            SETTINGS[TrackSetting.CHAINS].check(list(names), song=song)
        self._settings[TrackSetting.CHAINS] = list(names) if names else None

    def copy(self):
        return Track(**{**self._settings, TrackSetting.CC: self.get_cc_numbers() if self._settings[TrackSetting.CC] else None, TrackSetting.CHAINS: own_copy(self._settings[TrackSetting.CHAINS])})

    # Changing the track. A setting at its default is left out of the file.

    def set_drum(self, drum):
        self._set_flag(flag=TrackSetting.DRUM, on=drum)

    def set_mute(self, mute):
        self._set_flag(flag=TrackSetting.MUTE, on=mute)

    @notes_change
    def _set_flag(self, *, flag, on):
        SETTINGS[flag].check(on)
        self._settings[flag] = True if on else None

    @notes_change
    def set_transpose(self, transpose):
        """Set how far it moves its notes along the scale, which can be negative."""
        SETTINGS[TrackSetting.TRANSPOSE].check(transpose)
        self._settings[TrackSetting.TRANSPOSE] = None if transpose == DEFAULT_TRANSPOSE else transpose

    @notes_change
    def set_cc_number(self, *, lane, number):
        """Set the CC number one of the four lanes sends, or None for a lane that sends nothing."""
        if not is_whole_number_from(value=lane, lowest=0, highest=len(CC_ROWS) - 1):
            raise InvalidValue(ERR_NO_SUCH_LANE.format(lane=lane, last=len(CC_ROWS) - 1))
        numbers = self.get_cc_numbers()
        numbers[lane] = number
        SETTINGS[TrackSetting.CC].check(numbers)
        self._settings[TrackSetting.CC] = None if numbers == _no_cc_numbers() else numbers


def _check_octave_order(*, lowest, highest):
    """Check that a track's lowest octave isn't above its highest, once each has been checked on its own."""
    if lowest > highest:
        raise InvalidValue(ERR_OCTAVE_RANGE_BACKWARDS.format(lowest=lowest, highest=highest))
