# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The video tutorial's captions as a SubRip (.srt) file, so that YouTube has them for search and
translation as well as in the picture: each sentence and key called out, from the second it was said until the next."""

from llamatron.strings import narration

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
    return narration.MSG_SUBTITLE_TIME.format(hours=hours, minutes=minutes, seconds=whole, milliseconds=milliseconds)


def subtitles(*, said, ended, offset):
    """Return the text of a SubRip file from what was said, each (seconds, text) with the seconds counted from the tutorial's start,
    until ended, every moment moved later by offset, the seconds of the video before the tutorial starts."""
    cues = []
    for number, (start, text) in enumerate(said, start=FIRST_CUE):
        end = said[number][0] if number < len(said) else ended
        cues.append(narration.MSG_SUBTITLE_CUE.format(number=number, start=subtitle_time(start + offset), end=subtitle_time(end + offset), text=text))
    return ''.join(cues)
