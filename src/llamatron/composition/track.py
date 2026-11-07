# llamatron: a Python language and framework for producing MIDI clips.
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

from llamatron.composition.checks import reading, check_keys, is_true_or_false, is_whole_number_from
from llamatron.composition.defaults import DEFAULT_TRANSPOSE
from llamatron.composition.file_format import CC_ROWS, TrackSetting
from llamatron.composition.limits import MAX_CC_NUMBER, MAX_TRANSPOSE, MIN_CC_NUMBER
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.invalid_value import InvalidValue

MSG_EXPECTED_SETTINGS = 'expected settings like {{ drum: true }}, got {data!r}'
MSG_NOT_TRUE_OR_FALSE = '{name} must be true or false, got {value!r}'
MSG_BAD_TRANSPOSE = 'transpose must be a whole number from -{most} to {most}, got {value!r}'
MSG_BAD_CC_NUMBERS = "cc must be a list of {lanes} CC numbers from {lowest} to {highest}, or ~ for a lane it doesn't use, got {value!r}"
# A track's settings, in the order they're written to a file.
SETTINGS = [TrackSetting.DRUM, TrackSetting.MUTE, TrackSetting.TRANSPOSE, TrackSetting.CC]


class Track(LlamaData):
    """A track's settings: whether it's a drum track, whether it's muted, its transpose and CC numbers.

    A setting the file leaves out is kept as None and means its default, so that saving writes
    back only what was set.
    """

    __slots__ = ('_settings',)

    def __init__(self, drum=None, mute=None, transpose=None, cc=None):
        self._settings = {TrackSetting.DRUM: drum, TrackSetting.MUTE: mute, TrackSetting.TRANSPOSE: transpose, TrackSetting.CC: cc}

    @classmethod
    def from_data(cls, data, where, song=None):
        with reading(where):
            data = {} if data is None else data
            if not isinstance(data, dict):
                raise InvalidValue(MSG_EXPECTED_SETTINGS.format(data=data))
            check_keys(data, set(SETTINGS))
            for flag in (TrackSetting.DRUM, TrackSetting.MUTE):
                if not is_true_or_false(data.get(flag, False)):
                    raise InvalidValue(MSG_NOT_TRUE_OR_FALSE.format(name=flag, value=data[flag]))
            if not is_whole_number_from(data.get(TrackSetting.TRANSPOSE, DEFAULT_TRANSPOSE), -MAX_TRANSPOSE, MAX_TRANSPOSE):
                raise InvalidValue(MSG_BAD_TRANSPOSE.format(most=MAX_TRANSPOSE, value=data[TrackSetting.TRANSPOSE]))
            numbers = data.get(TrackSetting.CC, _no_cc_numbers())
            if not _is_cc_number_list(numbers):
                raise InvalidValue(MSG_BAD_CC_NUMBERS.format(lanes=len(CC_ROWS), lowest=MIN_CC_NUMBER, highest=MAX_CC_NUMBER, value=numbers))
            return cls(**{name: data.get(name) for name in SETTINGS})

    def to_data(self):
        return {name: value for name, value in self._settings.items() if value is not None}

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

    def get_cc_numbers(self):
        """Return the CC number each of a pattern's CC lanes sends on this track, or None for a lane it doesn't use."""
        numbers = self._settings[TrackSetting.CC]
        return _no_cc_numbers() if numbers is None else list(numbers)


def _no_cc_numbers():
    """Return the CC numbers of a track that sends no CC values: none for every lane."""
    return [None] * len(CC_ROWS)


def _is_cc_number_list(numbers):
    """Return whether numbers has a CC number, or None for a lane that sends nothing, for every CC lane."""
    return isinstance(numbers, list) and len(numbers) == len(CC_ROWS) and all(
        number is None or is_whole_number_from(number, MIN_CC_NUMBER, MAX_CC_NUMBER) for number in numbers
    )
