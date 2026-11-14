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

"""Writes a set back to the YAML set format, one setting or pattern row per line.

The set's settings come first, then what every song shares (scales, patterns, generators,
chains and grooves), then the songs, each with its settings, registers, tracks and scenes indented under its
name. Comments aren't kept, because a set is only data by the time it gets here.
"""

import json
import re

import yaml

from llamatron.support.safe_yaml import load_safely
from llamatron.composition.file_format import PATTERN_ROWS, PatternSetting, Section, SceneSetting, SetlistSetting, SongSetting

# Text that can be written without quotes: it starts with a letter, digit or underscore, and
# holds only those, #, ., /, spaces and hyphens.
_PLAIN = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_#./ -]*')
# The set's settings, in the order they're written at the top of a file. The notes are
# written as a block after the title, author and description.
_SETTINGS = [
    SetlistSetting.VERSION, SetlistSetting.TITLE, SetlistSetting.AUTHOR, SetlistSetting.DESCRIPTION, SetlistSetting.STEP_SIZE, SetlistSetting.DEFAULT_OCTAVE,
    SetlistSetting.DEFAULT_DRUM_OCTAVE, SetlistSetting.OCTAVE_LABELS, SetlistSetting.DEFAULT_FOLLOW_ACTION, SetlistSetting.REAL_TIME,
    SetlistSetting.VISUALIZER, SetlistSetting.HIDDEN_VISUALIZERS, SetlistSetting.GENERATOR_ORDER, SetlistSetting.PROTECTED,
]
_BEFORE_NOTES = (SetlistSetting.VERSION, SetlistSetting.TITLE, SetlistSetting.AUTHOR, SetlistSetting.DESCRIPTION)
# A song's settings, in the order they're written at the top of its entry.
_SONG_SETTINGS = [SongSetting.TEMPO, SongSetting.TIME_SIGNATURE, SongSetting.ENTRY_SIZE, SongSetting.SCALE, SongSetting.SEED, SongSetting.GROOVE, SongSetting.GENRE, SongSetting.LIVE_RESPONSIVENESS, SongSetting.VISUALIZER]
_GENERATOR_SECTIONS = [Section.ARPS, Section.AUTO_RATCHETS, Section.DRIFTS, Section.PROGRESSIONS, Section.VOICE_LEADINGS, Section.STRUMS, Section.EUCLIDS, Section.DENSITIES, Section.SWELLS, Section.ARTICULATES, Section.GLIDES, Section.SHORTENS, Section.RUSHES, Section.DRAGS, Section.HOCKETS]
_PATTERN_SETTINGS = [PatternSetting.STEP_SIZE, PatternSetting.TIME_SIGNATURE, PatternSetting.ENTRY_SIZE, PatternSetting.DIRECTION]

# The pieces of YAML this writes.
NULL = '~'
LIST = '[{items}]'
EMPTY_LIST = '[]'
MAP = '{{ {items} }}'
EMPTY_MAP = '{}'
ITEM_SEPARATOR = ', '
SETTING = '{key}: {value}'
HEADING = '{key}:'
INDENT = '  '
LIST_ITEM = '- '
LINE_BREAK = '\n'
BLANK_LINE = '\n\n'
SPACE = ' '
NOTHING = ''
DRUM_LINE = 'drum: true'
# A block of text, like notes: | then lines indented under it. A number after the | says
# how far the text is indented, which YAML needs when its first line starts with a space. Then -
# drops the last line break, nothing keeps one, and + keeps them all.
BLOCK = '{key}: |{indent}{chomp}'
BLOCK_INDENT = '2'
DROP_LAST_BREAK = '-'
KEEP_ONE_BREAK = ''
KEEP_EVERY_BREAK = '+'
NO_INDENT = ''


def _notes(text):
    """Return the notes as a YAML block, so that each line of them reads as it was written."""
    key = SetlistSetting.NOTES
    if not text.strip():
        return [SETTING.format(key=key, value=_text(text))]
    indent = BLOCK_INDENT if text.lstrip(LINE_BREAK)[:1] == SPACE else NO_INDENT
    if not text.endswith(LINE_BREAK):
        chomp = DROP_LAST_BREAK
        body = text
    else:
        chomp = KEEP_EVERY_BREAK if text.endswith(BLANK_LINE) else KEEP_ONE_BREAK
        body = text[:-len(LINE_BREAK)]
    return [BLOCK.format(key=key, indent=indent, chomp=chomp)] + _indented_lines(body)


def _indented_lines(body):
    """Return a block's lines, each indented under its key, with blank lines left blank."""
    return [INDENT + line if line else line for line in body.split(LINE_BREAK)]


def _text(value):
    """Return a value as YAML that's safe inside brackets and braces."""
    if value is None:
        return NULL
    if isinstance(value, list):
        return LIST.format(items=ITEM_SEPARATOR.join(_text(item) for item in value))
    if isinstance(value, dict):
        return _braces(value)
    if isinstance(value, str):
        return value if _reads_back_as_itself(value) else json.dumps(value)
    return _first_line(yaml.safe_dump(value))


def _reads_back_as_itself(text):
    """Return whether text can be written without quotes and still read back as the same text."""
    return _PLAIN.fullmatch(text) is not None and load_safely(LIST.format(items=text)) == [text]


def _first_line(text):
    return text.split(LINE_BREAK)[0]


def _braces(settings):
    if not settings:
        return EMPTY_MAP
    return MAP.format(items=ITEM_SEPARATOR.join(SETTING.format(key=_text(key), value=_text(value)) for key, value in settings.items()))


def _named(*, section, items):
    """Return a section of named objects, each on one line with its settings in braces."""
    return [HEADING.format(key=section)] + [INDENT + SETTING.format(key=_text(name), value=_braces(item)) for name, item in items.items()]


def _patterns(patterns):
    lines = [HEADING.format(key=Section.PATTERNS)]
    for name, pattern in patterns.items():
        lines.append(INDENT + HEADING.format(key=_text(name)))
        lines += [INDENT * 2 + line for line in _pattern_lines(pattern)]
    return lines


def _pattern_lines(pattern):
    """Return a pattern's settings and then its rows, one to a line, leaving out rows it doesn't have."""
    lines = [SETTING.format(key=PatternSetting.STEPS, value=pattern[PatternSetting.STEPS])]
    if pattern.get(PatternSetting.DRUM):
        lines.append(DRUM_LINE)
    for setting in _PATTERN_SETTINGS:
        if pattern.get(setting):
            lines.append(SETTING.format(key=setting, value=_text(pattern[setting])))
    lines += [SETTING.format(key=row, value=_text(pattern[row])) for row in PATTERN_ROWS if pattern.get(row) is not None]
    return lines


def _chains(chains):
    lines = [HEADING.format(key=Section.CHAINS)]
    for name, steps in chains.items():
        heading = SETTING.format(key=_text(name), value=EMPTY_LIST) if not steps else HEADING.format(key=_text(name))
        lines.append(INDENT + heading)
        for step in steps:
            for generator, settings in step.items():
                lines.append(INDENT * 2 + LIST_ITEM + SETTING.format(key=_text(generator), value=_text(settings)))
    return lines


def _scenes(scenes):
    if not scenes:
        return [SETTING.format(key=Section.SCENES, value=EMPTY_LIST)]
    lines = [HEADING.format(key=Section.SCENES)]
    for scene in scenes:
        lines += _scene_lines(scene)
    return lines


def _scene_lines(scene):
    """Return one scene as a list item: its settings, then its tracks' clip slots, each on its own line."""
    if not scene:
        return [INDENT + LIST_ITEM + EMPTY_MAP]
    lines = []
    for key, value in scene.items():
        prefix = INDENT + LIST_ITEM if not lines else INDENT * 2
        if key == SceneSetting.TRACKS:
            lines.append(prefix + (HEADING.format(key=key) if value else SETTING.format(key=key, value=EMPTY_MAP)))
            lines += [INDENT * 3 + SETTING.format(key=_text(track), value=_braces(clip_slot)) for track, clip_slot in (value or {}).items()]
        else:
            lines.append(prefix + SETTING.format(key=key, value=_text(value)))
    return lines


def _settings_lines(setlist):
    """Return the set's settings, with the notes as a block straight after the title, author and description."""
    settings = [SETTING.format(key=key, value=_text(setlist[key])) for key in _SETTINGS if key in setlist]
    if setlist.get(SetlistSetting.NOTES):
        place = sum(key in setlist for key in _BEFORE_NOTES)
        settings[place:place] = _notes(setlist[SetlistSetting.NOTES])
    return settings


def _song_groups(song):
    """Return one song's lines in groups: its settings, registers, tracks and scenes, leaving out what it doesn't have."""
    groups = []
    settings = [SETTING.format(key=key, value=_text(song[key])) for key in _SONG_SETTINGS if key in song]
    if settings:
        groups.append(settings)
    if song.get(Section.REGISTERS):
        groups.append(_named(section=Section.REGISTERS, items=song[Section.REGISTERS]))
    tracks = song.get(Section.TRACKS)
    groups.append(_named(section=Section.TRACKS, items=tracks) if tracks else [SETTING.format(key=Section.TRACKS, value=EMPTY_MAP)])
    groups.append(_scenes(song.get(Section.SCENES) or []))
    return groups


def _songs(songs):
    """Return the songs section: each song's name, with its groups of lines indented under it and a blank line between."""
    if not songs:
        return [SETTING.format(key=Section.SONGS, value=EMPTY_MAP)]
    lines = [HEADING.format(key=Section.SONGS)]
    for number, (name, song) in enumerate(songs.items()):
        if number:
            lines.append(NOTHING)
        lines.append(INDENT + HEADING.format(key=_text(name)))
        for place, group in enumerate(_song_groups(song)):
            if place:
                lines.append(NOTHING)
            lines += [INDENT * 2 + line for line in group]
    return lines


def dump_setlist(setlist):
    """Return a set's data as the text of a set file."""
    sections = [_settings_lines(setlist)]
    if setlist.get(Section.SCALES):
        sections.append(_named(section=Section.SCALES, items=setlist[Section.SCALES]))
    if setlist.get(Section.PATTERNS):
        sections.append(_patterns(setlist[Section.PATTERNS]))
    for section in _GENERATOR_SECTIONS:
        if setlist.get(section):
            sections.append(_named(section=section, items=setlist[section]))
    if setlist.get(Section.CHAINS):
        sections.append(_chains(setlist[Section.CHAINS]))
    if setlist.get(Section.GROOVES):
        sections.append(_named(section=Section.GROOVES, items=setlist[Section.GROOVES]))
    if setlist.get(Section.INSTRUMENTS):
        sections.append(_named(section=Section.INSTRUMENTS, items=setlist[Section.INSTRUMENTS]))
    sections.append(_songs(setlist.get(Section.SONGS) or {}))
    written = [section for section in sections if section]
    return _joined(written) + LINE_BREAK


def _joined(sections):
    """Join sections with a blank line between, except after one ending in a blank line, which kept notes' block would absorb."""
    text = LINE_BREAK.join(sections[0])
    for section in sections[1:]:
        text += (LINE_BREAK if text.endswith(LINE_BREAK) else BLANK_LINE) + LINE_BREAK.join(section)
    return text
