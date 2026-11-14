#!/usr/bin/env python3
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
"""Print which features each example set uses, to see what the demos underuse.

    .venv/bin/python internal_tools/demo_features.py                        # every set in examples/
    .venv/bin/python internal_tools/demo_features.py examples/learning/19_hocket_shanty.yml  # only the sets named
    .venv/bin/python internal_tools/demo_features.py --csv                  # comma-separated values (sh user_scripts/demo_report.sh --features)

The table has a row for each feature a set file can use, a pattern row, a setting or a section,
and a column for each set, marked where the set uses it. After the table come the features no set
uses and the features only one set uses, which are the candidates for a new demo or a new scene
in an existing one.
"""

import argparse
import csv
import io
import os
import sys

from llamatron.composition.defaults import DEFAULT_TIME_SIGNATURE
from llamatron.composition.file_format import (
    SHAPES, SHAPE_PARTS, shape_setting,
    CC_REGISTER_SETTINGS,
    CC_ROWS,
    CONDITION_ROWS,
    REGISTER_ADD_ROWS,
    REGISTER_NOTE_ROWS,
    REGISTER_SET_ROWS,
    REGISTER_VELOCITY_ROWS,
    ClipSlotSetting,
    PatternSetting,
    Row,
    SceneSetting,
    Section,
    SetlistSetting,
    SongSetting,
    TrackSetting,
)
from llamatron.composition.limits import MIN_REPEAT
from llamatron.composition.setlist import Setlist
from llamatron.support.example_sets import example_sets

SET_SUFFIX = '.yml'
USED = '●'
UNUSED = '·'
# How the table is laid out: the feature column's width, and each set's column's width.
FEATURE_WIDTH = 28
COLUMN_WIDTH = 7
HEADING_ROWS = 'Set file: '
MSG_UNUSED_BY_ALL = '\nUsed by no set: {features}'
MSG_UNUSED_BY_ALL_NONE = '\nEvery feature is used by at least one set.'
MSG_USED_BY_ONE = 'Used by one set only: {features}'
MSG_FEATURE_IN_SET = '{feature} ({name})'
LISTED = ', '.join
CSV_FEATURE = 'feature'
CSV_USED = 'yes'
CSV_UNUSED = ''
CSV_LINE_END = '\n'


def patterns(data):
    return data.get(Section.PATTERNS, {}).values()


def songs(data):
    return data.get(Section.SONGS, {}).values()


def scenes(data):
    return [scene for song in songs(data) for scene in song.get(Section.SCENES, [])]


def clip_slots(data):
    return [clip_slot for scene in scenes(data) for clip_slot in scene.get(SceneSetting.TRACKS, {}).values()]


def tracks(data):
    return [track for song in songs(data) for track in song.get(Section.TRACKS, {}).values()]


def row_is_used(*, pattern, row):
    """Return whether any step of a pattern's row holds a value, since blank rows are left out and toggles are false."""
    return any(value not in (None, False) for value in pattern.get(row, []))


def any_pattern_row(row):
    return lambda data: any(row_is_used(pattern=pattern, row=row) for pattern in patterns(data))


def any_pattern_rows(rows):
    return lambda data: any(any_pattern_row(row)(data) for row in rows)


def any_pattern_setting(setting):
    return lambda data: any(setting in pattern for pattern in patterns(data))


def any_clip_slot_setting(setting):
    return lambda data: any(setting in clip_slot for clip_slot in clip_slots(data))


def any_scene_setting(setting):
    return lambda data: any(setting in scene for scene in scenes(data))


def any_track_setting(setting):
    return lambda data: any(setting in track for track in tracks(data))


def any_song_setting(setting):
    return lambda data: any(setting in song for song in songs(data))


def has_section(section):
    return lambda data: bool(data.get(section))


def any_song_section(section):
    return lambda data: any(song.get(section) for song in songs(data))


def repeats(*, items, setting):
    return any(item.get(setting, MIN_REPEAT) > MIN_REPEAT for item in items)


def binds_registers(data):
    """Return whether any track binds a CC lane or its velocity to a register."""
    return any(any_track_setting(setting)(data) for setting in (*CC_REGISTER_SETTINGS, TrackSetting.VELOCITY_REGISTER))


def uses_another_time_signature(data):
    return any(song.get(SongSetting.TIME_SIGNATURE, DEFAULT_TIME_SIGNATURE) != DEFAULT_TIME_SIGNATURE for song in songs(data))


# Each feature a set can use, in the order the table lists them, with how to tell from a set's data.
# Every setting of a shape a scene or a clip can hold, like density_start.
SHAPE_SETTINGS = [shape_setting(shape=shape, part=part) for shape in SHAPES for part in SHAPE_PARTS]

FEATURES = [
    ('gates', any_pattern_row(Row.GATE)),
    ('dotted or triplet gates', any_pattern_row(Row.DOT)),
    ('accidentals', any_pattern_row(Row.ACCIDENTAL)),
    ('octaves', any_pattern_row(Row.OCTAVE)),
    ('chords', any_pattern_row(Row.CHORD)),
    ('velocity', any_pattern_row(Row.VELOCITY)),
    ('probability', any_pattern_row(Row.PROBABILITY)),
    ('glide', any_pattern_row(Row.GLIDE)),
    ('ties', any_pattern_row(Row.TIE)),
    ('ratchets', any_pattern_row(Row.RATCHET)),
    ('ratchet offsets', any_pattern_row(Row.RATCHET_OFFSET)),
    ('grab steps', any_pattern_row(Row.GRAB)),
    ('CC rows', any_pattern_rows(CC_ROWS)),
    ('slides', any_pattern_row(Row.SLIDE)),
    ('register note rows', any_pattern_rows(REGISTER_NOTE_ROWS.values())),
    ('register velocity rows', any_pattern_rows(REGISTER_VELOCITY_ROWS.values())),
    ('register adds', any_pattern_rows(REGISTER_ADD_ROWS.values())),
    ('register sets', any_pattern_rows(REGISTER_SET_ROWS.values())),
    ('conditions', any_pattern_rows(CONDITION_ROWS.values())),
    ('register binding', binds_registers),
    ('drum patterns', any_pattern_setting(PatternSetting.DRUM)),
    ('pattern step size', any_pattern_setting(PatternSetting.STEP_SIZE)),
    ('pattern time signature', any_pattern_setting(PatternSetting.TIME_SIGNATURE)),
    ('pattern direction', any_pattern_setting(PatternSetting.DIRECTION)),
    ('clip direction', any_clip_slot_setting(ClipSlotSetting.DIRECTION)),
    ('clip repeat', lambda data: repeats(items=clip_slots(data), setting=ClipSlotSetting.REPEAT)),
    ('clip loop', any_clip_slot_setting(ClipSlotSetting.LOOP)),
    ('clip chain', any_clip_slot_setting(ClipSlotSetting.CHAINS)),
    ('scene chains', any_scene_setting(SceneSetting.CHAINS)),
    ('track chains', any_track_setting(TrackSetting.CHAINS)),
    ('clip shapes', lambda data: any(any_clip_slot_setting(setting)(data) for setting in SHAPE_SETTINGS)),
    ('scene shapes', lambda data: any(any_scene_setting(setting)(data) for setting in SHAPE_SETTINGS)),
    ('morphs', any_clip_slot_setting(ClipSlotSetting.MORPH_TO)),
    ('grab track', any_clip_slot_setting(ClipSlotSetting.GRAB_TRACK)),
    ('clip names', any_clip_slot_setting(ClipSlotSetting.NAME)),
    ('clip scale', any_clip_slot_setting(ClipSlotSetting.SCALE)),
    ('scene repeat', lambda data: repeats(items=scenes(data), setting=SceneSetting.REPEAT)),
    ('scene scale', any_scene_setting(SceneSetting.SCALE)),
    ('scene tempo', any_scene_setting(SceneSetting.TEMPO)),
    ('tempo ramps', any_scene_setting(SceneSetting.TEMPO_START)),
    ('register resets', any_scene_setting(SceneSetting.RESET)),
    ('scene groove', any_scene_setting(SceneSetting.GROOVE)),
    ('drum tracks', any_track_setting(TrackSetting.DRUM)),
    ('muted tracks', any_track_setting(TrackSetting.MUTE)),
    ('transpose', any_track_setting(TrackSetting.TRANSPOSE)),
    ('track CC numbers', any_track_setting(TrackSetting.CC)),
    ('track groove', any_track_setting(TrackSetting.GROOVE)),
    ('song groove', any_song_setting(SongSetting.GROOVE)),
    ('song seed', any_song_setting(SongSetting.SEED)),
    ('time signature not 4/4', uses_another_time_signature),
    ('registers section', any_song_section(Section.REGISTERS)),
    ('several songs', lambda data: len(songs(data)) > 1),
    ('several scales', lambda data: len(data.get(Section.SCALES, {})) > 1),
    ('arps', has_section(Section.ARPS)),
    ('AutoRatchets', has_section(Section.AUTO_RATCHETS)),
    ('drifts', has_section(Section.DRIFTS)),
    ('progressions', has_section(Section.PROGRESSIONS)),
    ('voice leadings', has_section(Section.VOICE_LEADINGS)),
    ('inversions', any_pattern_row(Row.INVERSION)),
    ('euclids', lambda data: has_section(Section.EUCLIDS)(data) or any_track_setting(TrackSetting.EUCLID_HITS)(data)),
    ('glides', has_section(Section.GLIDES)),
    ('shortens', has_section(Section.SHORTENS)),
    ('rushes', has_section(Section.RUSHES)),
    ('drags', has_section(Section.DRAGS)),
    ('hockets', has_section(Section.HOCKETS)),
    ('strums', lambda data: has_section(Section.STRUMS)(data) or any_track_setting(TrackSetting.STRUM_DIRECTION)(data) or any_clip_slot_setting(ClipSlotSetting.STRUM_DIRECTION)(data)),
    ('Densities', has_section(Section.DENSITIES)),
    ('Swells', has_section(Section.SWELLS)),
    ('Articulates', has_section(Section.ARTICULATES)),
    ('chains', has_section(Section.CHAINS)),
    ('own grooves', has_section(Section.GROOVES)),
    ('description', lambda data: SetlistSetting.DESCRIPTION in data),
    ('notes', lambda data: SetlistSetting.NOTES in data),
]


def short_name(path):
    """Return a set's column heading: its file name without the folder or the suffix."""
    return os.path.basename(path).removesuffix(SET_SUFFIX)


def features_used(path):
    """Return the set of feature names a set file uses."""
    data = Setlist.read_file(path).to_data()
    return {name for name, check in FEATURES if check(data)}


def table(*, paths, used):
    """Return the table's lines: a heading of set names, then a row per feature."""
    names = [short_name(path) for path in paths]
    heading = HEADING_ROWS.ljust(FEATURE_WIDTH) + ''.join(name[:COLUMN_WIDTH - 1].ljust(COLUMN_WIDTH) for name in names)
    lines = [heading]
    for feature, _ in FEATURES:
        marks = ''.join((USED if feature in used[path] else UNUSED).ljust(COLUMN_WIDTH) for path in paths)
        lines.append(feature.ljust(FEATURE_WIDTH) + marks)
    return lines


def summary(*, paths, used):
    """Return the lines naming the features no set uses and the features only one set uses."""
    counts = {feature: [path for path in paths if feature in used[path]] for feature, _ in FEATURES}
    unused = [feature for feature, users in counts.items() if not users]
    once = [MSG_FEATURE_IN_SET.format(feature=feature, name=short_name(users[0])) for feature, users in counts.items() if len(users) == 1]
    lines = [MSG_UNUSED_BY_ALL.format(features=LISTED(unused)) if unused else MSG_UNUSED_BY_ALL_NONE]
    if once:
        lines.append(MSG_USED_BY_ONE.format(features=LISTED(once)))
    return lines


def csv_lines(*, paths, used):
    """Return the table as lines of comma-separated values: a row per feature, a column per set, yes where the set uses it."""
    held = io.StringIO()
    writer = csv.writer(held, lineterminator=CSV_LINE_END)
    writer.writerow([CSV_FEATURE] + [short_name(path) for path in paths])
    for feature, _ in FEATURES:
        writer.writerow([feature] + [CSV_USED if feature in used[path] else CSV_UNUSED for path in paths])
    return held.getvalue().splitlines()


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('paths', nargs='*', help='the sets to look at; with none, every set in examples/')
    parser.add_argument('--csv', action='store_true', help='print comma-separated values, for a spreadsheet or another program')
    arguments = parser.parse_args(argv)
    paths = arguments.paths or example_sets()
    used = {path: features_used(path) for path in paths}
    lines = csv_lines(paths=paths, used=used) if arguments.csv else table(paths=paths, used=used) + summary(paths=paths, used=used)
    for line in lines:
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main(argv=sys.argv[1:]))
