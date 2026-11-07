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

"""llamatron's version, which the title shows and every saved song file records.

The version is a string of three whole numbers separated by dots, like 1.0.2. The last number
goes up with every commit that changes the program's Python code, and the user changes the
first two when they choose. Versions are compared number by number, never as decimals, so
1.0.10 comes after 1.0.9.
"""

VERSION = '1.0.10'

VERSION_SEPARATOR = '.'
VERSION_PARTS = 3
MSG_BAD_VERSION = 'a version must be three whole numbers separated by dots, like 1.0.2, got {value!r}'


def is_version(text):
    """Return whether text is a version: three whole numbers separated by dots, like 1.0.2."""
    if not isinstance(text, str):
        return False
    parts = text.split(VERSION_SEPARATOR)
    return len(parts) == VERSION_PARTS and all(part.isdigit() and part.isascii() for part in parts)


def version_numbers(text):
    """Return a version's three numbers, so versions compare number by number, like (1, 0, 2)."""
    if not is_version(text):
        raise ValueError(MSG_BAD_VERSION.format(value=text))
    return tuple(int(part) for part in text.split(VERSION_SEPARATOR))
