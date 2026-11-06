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

from llamatron.composition.checks import check_keys
from llamatron.composition.file_format import CC_ROWS, MAX_TRANSPOSE
from llamatron.composition.llama_data import LlamaData
from llamatron.composition.song_file_error import SongFileError


class Track(LlamaData):
    """A track's settings: whether it's a drum track, whether it's muted, its transpose and CC numbers.

    A setting the file leaves out is kept as None and means its default, so that saving writes
    back only what was set.
    """

    def __init__(self, drum=None, mute=None, transpose=None, cc=None):
        self._drum = drum
        self._mute = mute
        self._transpose = transpose
        self._cc = cc

    @classmethod
    def from_data(cls, data, where, song=None):
        data = {} if data is None else data
        if not isinstance(data, dict):
            raise SongFileError(f'{where}: expected settings like {{ drum: true }}, got {data!r}')
        check_keys(data, where, {'drum', 'mute', 'transpose', 'cc'})
        for flag in ('drum', 'mute'):
            if type(data.get(flag, False)) is not bool:
                raise SongFileError(f'{where}: {flag} must be true or false, got {data[flag]!r}')
        transpose = data.get('transpose', 0)
        if type(transpose) is not int or not -MAX_TRANSPOSE <= transpose <= MAX_TRANSPOSE:
            raise SongFileError(f'{where}: transpose must be a whole number from -{MAX_TRANSPOSE} to {MAX_TRANSPOSE}, got {transpose!r}')
        numbers = data.get('cc', [None] * len(CC_ROWS))
        if not isinstance(numbers, list) or len(numbers) != len(CC_ROWS) or not all(
            number is None or (type(number) is int and 0 <= number <= 127) for number in numbers
        ):
            raise SongFileError(f'{where}: cc must be a list of {len(CC_ROWS)} CC numbers from 0 to 127, or ~ for a lane it doesn\'t use, got {numbers!r}')
        return cls(data.get('drum'), data.get('mute'), data.get('transpose'), data.get('cc'))

    def to_data(self):
        settings = {'drum': self._drum, 'mute': self._mute, 'transpose': self._transpose, 'cc': self._cc}
        return {name: value for name, value in settings.items() if value is not None}

    def is_drum(self):
        return bool(self._drum)

    def is_muted(self):
        return bool(self._mute)

    def get_transpose(self):
        """Return how many scale notes the track moves its notes, which is always 0 on a drum track."""
        return 0 if self.is_drum() else (self._transpose or 0)

    def get_cc_numbers(self):
        """Return the CC number each of a pattern's CC lanes sends on this track, or None for a lane it doesn't use."""
        return list(self._cc) if self._cc is not None else [None] * len(CC_ROWS)
