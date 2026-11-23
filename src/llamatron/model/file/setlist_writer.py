# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Writes a set back to the YAML set format, one setting or pattern row per line.

The set's settings come first, then what every song shares (scales, patterns, generators, grooves and
instruments), each a list whose items begin with their names, then the songs, each an item with its
settings, registers, tracks and scenes indented under its name. The data written is laid out as the file is
(model/file/file_layout.py). Comments aren't kept, because a set is only data by the time it gets here.
"""

import functools
import json
import re
import yaml

from llamatron.model.file.file_layout import as_file_layout
from llamatron.model.file.safe_yaml import load_safely
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import FileLayout, PatternSetting, Section, SetlistSetting, SongSetting

# Text that can be written without quotes: it starts with a letter, digit or underscore, and
# holds only those, #, ., /, spaces and hyphens.
_PLAIN = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_#./ -]*')
# The set's settings, in the order they're written at the top of a file. The notes are
# written as a block after the title, author and description.
_SETTINGS = [
    SetlistSetting.VERSION, SetlistSetting.TITLE, SetlistSetting.AUTHOR, SetlistSetting.DESCRIPTION, SetlistSetting.STEP_SIZE, SetlistSetting.DEFAULT_OCTAVE,
    SetlistSetting.DEFAULT_DRUM_OCTAVE, SetlistSetting.OCTAVE_LABELS, SetlistSetting.DEFAULT_FOLLOW_ACTION, SetlistSetting.REAL_TIME,
    SetlistSetting.VISUALIZER, SetlistSetting.HIDDEN_VISUALIZERS, SetlistSetting.GENERATOR_ORDER, SetlistSetting.PROTECTED, file_format.OPEN_GENERATOR_TYPES,
]
_BEFORE_NOTES = (SetlistSetting.VERSION, SetlistSetting.TITLE, SetlistSetting.AUTHOR, SetlistSetting.DESCRIPTION)
# A song's settings, in the order they're written at the top of its entry.
_SONG_SETTINGS = [SongSetting.TEMPO, SongSetting.TIME_SIGNATURE, SongSetting.ENTRY_SIZE, SongSetting.SCALE, SongSetting.GROOVE, SongSetting.GENRE, SongSetting.SUBGENRE, SongSetting.VARIANT, SongSetting.LIVE_RESPONSIVENESS, SongSetting.VISUALIZER, SongSetting.PREVIEW_INSTRUMENT, SongSetting.WIZARD]
_PATTERN_SETTINGS = [PatternSetting.GROUP, PatternSetting.STEP_SIZE, PatternSetting.TIME_SIGNATURE, PatternSetting.ENTRY_SIZE, PatternSetting.DIRECTION]

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
    # A block whose first line starts with a space says how far it is indented, which YAML can't work out from that line.
    indent = NO_INDENT
    if text.lstrip(LINE_BREAK)[:1] == SPACE:
        indent = BLOCK_INDENT
    chomp = DROP_LAST_BREAK
    body = text
    if text.endswith(LINE_BREAK):
        chomp = KEEP_ONE_BREAK
        if text.endswith(BLANK_LINE):
            chomp = KEEP_EVERY_BREAK
        body = text[:-len(LINE_BREAK)]
    return [BLOCK.format(key=key, indent=indent, chomp=chomp), *_indented_lines(body)]


def _indented_lines(body):
    """Return a block's lines, each indented under its key, with blank lines left blank."""
    lines = []
    for line in body.split(LINE_BREAK):
        if line:
            line = INDENT + line
        lines.append(line)
    return lines


def _text(value):
    """Return a value as YAML that's safe inside brackets and braces."""
    if value is None:
        return NULL
    if isinstance(value, list):
        items = [_text(item) for item in value]
        return LIST.format(items=ITEM_SEPARATOR.join(items))
    if isinstance(value, dict):
        return _braces(value)
    return _scalar_text(kind=type(value), value=value)


@functools.cache
def _scalar_text(*, kind, value):
    """Return one text, number or true or false as YAML, worked out once for each: a set repeats a few hundred values many
    thousands of times, and asking YAML about each was most of the time a save took. The kind is part of what is remembered,
    since 1, 1.0 and true are equal to Python and are written differently."""
    if kind is str:
        if _reads_back_as_itself(value):
            return value
        return json.dumps(value)
    return _first_line(yaml.safe_dump(value))


def _reads_back_as_itself(text):
    """Return whether text can be written without quotes and still read back as the same text."""
    return _PLAIN.fullmatch(text) is not None and load_safely(LIST.format(items=text)) == [text]


def _first_line(text):
    return text.split(LINE_BREAK)[0]


def _braces(settings):
    if not settings:
        return EMPTY_MAP
    items = []
    for key, value in settings.items():
        items.append(SETTING.format(key=_text(key), value=_text(value)))
    return MAP.format(items=ITEM_SEPARATOR.join(items))


def _keyed(*, section, items):
    """Return a section of settings kept by fixed names, as a song's registers are, each on one line with its settings in braces."""
    lines = [HEADING.format(key=section)]
    for name, item in items.items():
        lines.append(INDENT + SETTING.format(key=_text(name), value=_braces(item)))
    return lines


def _items(*, section, items):
    """Return a list of named things, each item on one line with its settings, its name first, in braces."""
    if not items:
        return [SETTING.format(key=section, value=EMPTY_LIST)]
    lines = [HEADING.format(key=section)]
    for item in items:
        lines.append(INDENT + LIST_ITEM + _braces(item))
    return lines


def _patterns(patterns):
    lines = [HEADING.format(key=Section.PATTERNS)]
    for pattern in patterns:
        lines.append(INDENT + LIST_ITEM + SETTING.format(key=FileLayout.NAME, value=_text(pattern[FileLayout.NAME])))
        lines += _indented(lines=_pattern_lines(pattern), depth=2)
    return lines


def _pattern_lines(pattern):
    """Return a pattern's settings and then its rows, one to a line, leaving out rows it doesn't have."""
    lines = [SETTING.format(key=PatternSetting.STEPS, value=pattern[PatternSetting.STEPS])]
    if pattern.get(PatternSetting.DRUM):
        lines.append(DRUM_LINE)
    for setting in _PATTERN_SETTINGS:
        if pattern.get(setting):
            lines.append(SETTING.format(key=setting, value=_text(pattern[setting])))
    for row in file_format.PATTERN_ROWS:
        if pattern.get(row) is not None:
            lines.append(SETTING.format(key=row, value=_text(pattern[row])))
    return lines


def _scenes(scenes):
    if not scenes:
        return [SETTING.format(key=Section.SCENES, value=EMPTY_LIST)]
    lines = [HEADING.format(key=Section.SCENES)]
    for scene in scenes:
        lines += _scene_lines(scene)
    return lines


def _scene_lines(scene):
    """Return one scene as a list item: its settings, then its clips, each on its own line."""
    if not scene:
        return [INDENT + LIST_ITEM + EMPTY_MAP]
    lines = []
    for key, value in scene.items():
        # The first setting starts the list item, and the rest line up under it.
        prefix = INDENT * 2
        if not lines:
            prefix = INDENT + LIST_ITEM
        if key != FileLayout.CLIPS:
            lines.append(prefix + SETTING.format(key=key, value=_text(value)))
        elif not value:
            lines.append(prefix + SETTING.format(key=key, value=EMPTY_LIST))
        else:
            lines.append(prefix + HEADING.format(key=key))
            for clip in value:
                lines.append(INDENT * 3 + LIST_ITEM + _braces(clip))
    return lines


def _settings_lines(setlist):
    """Return the set's settings, with the notes as a block straight after the title, author and description."""
    settings = _setting_lines(data=setlist, keys=_SETTINGS)
    if setlist.get(SetlistSetting.NOTES):
        place = len(_setting_lines(data=setlist, keys=_BEFORE_NOTES))
        settings[place:place] = _notes(setlist[SetlistSetting.NOTES])
    return settings


def _song_groups(song):
    """Return one song's lines in groups: its settings, registers, tracks and scenes, leaving out what it doesn't have."""
    groups = []
    settings = _setting_lines(data=song, keys=_SONG_SETTINGS)
    if settings:
        groups.append(settings)
    if song.get(Section.DRAWS):
        groups.append(_keyed(section=Section.DRAWS, items=song[Section.DRAWS]))
    groups.append(_items(section=Section.TRACKS, items=song.get(Section.TRACKS)))
    groups.append(_scenes(song.get(Section.SCENES) or []))
    return groups


def _songs(songs):
    """Return the list of songs: each song's name as an item, with its groups of lines indented under it and a blank line between."""
    if not songs:
        return [SETTING.format(key=Section.SONGS, value=EMPTY_LIST)]
    lines = [HEADING.format(key=Section.SONGS)]
    for number, song in enumerate(songs):
        if number:
            lines.append(NOTHING)
        lines.append(INDENT + LIST_ITEM + SETTING.format(key=FileLayout.NAME, value=_text(song[FileLayout.NAME])))
        for place, group in enumerate(_song_groups(song)):
            if place:
                lines.append(NOTHING)
            lines += _indented(lines=group, depth=2)
    return lines


def dump_setlist(setlist):
    """Return a set's data, as the objects write it, as the text of a set file, laid out as the file is (model/file/file_layout.py)."""
    return dump_file_layout(as_file_layout(setlist))


def dump_file_layout(setlist):
    """Return a set's data, already laid out as the file is, as the text of a set file."""
    sections = [_settings_lines(setlist)]
    if setlist.get(Section.SCALES):
        sections.append(_items(section=Section.SCALES, items=setlist[Section.SCALES]))
    if setlist.get(Section.PATTERNS):
        sections.append(_patterns(setlist[Section.PATTERNS]))
    for section in (FileLayout.GENERATORS, Section.GROOVES, Section.INSTRUMENTS):
        if setlist.get(section):
            sections.append(_items(section=section, items=setlist[section]))
    sections.append(_songs(setlist.get(Section.SONGS) or []))
    written = [section for section in sections if section]
    return _joined(written) + LINE_BREAK


def _joined(sections):
    """Join sections with a blank line between, except after one ending in a blank line, which kept notes' block would absorb."""
    text = LINE_BREAK.join(sections[0])
    for section in sections[1:]:
        if text.endswith(LINE_BREAK):
            text += LINE_BREAK
        else:
            text += BLANK_LINE
        text += LINE_BREAK.join(section)
    return text


def _setting_lines(*, data, keys):
    """Return a line for each of some keys the data holds, in the keys' order."""
    lines = []
    for key in keys:
        if key in data:
            lines.append(SETTING.format(key=key, value=_text(data[key])))
    return lines


def _indented(*, lines, depth):
    """Return lines each indented so many levels."""
    indent = INDENT * depth
    indented = []
    for line in lines:
        indented.append(indent + line)
    return indented
