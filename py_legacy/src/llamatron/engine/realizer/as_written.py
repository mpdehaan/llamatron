# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A song as its patterns are written, before anything that works after them, which Scene View shows beside the song as played."""

from llamatron.model.objects.setlist import Setlist
from llamatron.model.objects.shapes import shape_settings
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import ClipSlotSetting, Row, SceneSetting, Section, SongSetting, TrackSetting

# The rows of a pattern that change what plays by chance or by a statement.
CHANCE_AND_READING_ROWS = [Row.PROBABILITY, *file_format.STATEMENT_OF_ROW]


def as_written(song):
    """Return a copy of a song, in a copy of its set, with everything that works after the patterns taken out, so that it is
    realized as written: the chains, the grooves, the shapes, the strums and the masks, and the patterns' probability and the steps'
    statements. A feature added that works after the patterns is taken out here too."""
    setlist = song.get_setlist()
    song_name = next(each for each in setlist.get_song_names() if setlist.get_song(each) is song)
    data = setlist.to_data()
    for pattern in data.get(Section.PATTERNS, {}).values():
        for row in CHANCE_AND_READING_ROWS:
            pattern.pop(row, None)
    shaped = [setting.get_name() for setting in shape_settings()]
    for song_data in data[Section.SONGS].values():
        song_data.pop(SongSetting.GROOVE, None)
        for track in (song_data.get(Section.TRACKS) or {}).values():
            for name in [TrackSetting.CHAINS, TrackSetting.GROOVE]:
                track.pop(name, None)
        for scene in song_data.get(Section.SCENES) or []:
            for name in [SceneSetting.CHAINS, SceneSetting.GROOVE, *shaped]:
                scene.pop(name, None)
            for clip in (scene.get(SceneSetting.TRACKS) or {}).values():
                for name in [ClipSlotSetting.CHAINS, *shaped]:
                    clip.pop(name, None)
    return Setlist.from_data(data=data).get_song(song_name)
