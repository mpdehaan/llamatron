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

"""The video tutorial's captions as a SubRip (.srt) file, the user's design, so that YouTube has them for search and
translation as well as in the picture: each sentence and key called out, from the second it was said until the next."""

from llamatron.strings.narration import MSG_SUBTITLE_CUE, MSG_SUBTITLE_TIME

MILLISECONDS_IN_A_SECOND = 1000
SECONDS_IN_A_MINUTE = 60
MINUTES_IN_AN_HOUR = 60
FIRST_CUE = 1


def subtitle_time(seconds):
    """Return a moment as SubRip writes it, hours, minutes, seconds and milliseconds, such as 00:01:02,500."""
    milliseconds = int(round(seconds * MILLISECONDS_IN_A_SECOND))
    whole, milliseconds = divmod(milliseconds, MILLISECONDS_IN_A_SECOND)
    minutes, whole = divmod(whole, SECONDS_IN_A_MINUTE)
    hours, minutes = divmod(minutes, MINUTES_IN_AN_HOUR)
    return MSG_SUBTITLE_TIME.format(hours=hours, minutes=minutes, seconds=whole, milliseconds=milliseconds)


def subtitles(*, said, ended, offset):
    """Return the text of a SubRip file from what was said, each (seconds, text) with the seconds counted from the tutorial's start,
    until ended, every moment moved later by offset, the seconds of the video before the tutorial starts."""
    cues = []
    for number, (start, text) in enumerate(said, start=FIRST_CUE):
        end = said[number][0] if number < len(said) else ended
        cues.append(MSG_SUBTITLE_CUE.format(number=number, start=subtitle_time(start + offset), end=subtitle_time(end + offset), text=text))
    return ''.join(cues)
