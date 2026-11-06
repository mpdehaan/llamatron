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

"""Writes a song back to the YAML song format, one setting or pattern row per line.

Comments aren't kept, because a song is only data by the time it gets here.
"""

import json
import re

import yaml

from llamatron.composition.file_format import PATTERN_ROWS, PatternSetting, Section, SceneSetting, SongSetting

# Text that can be written without quotes: it starts with a letter, digit or underscore, and
# holds only those, #, ., /, spaces and hyphens.
_PLAIN = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_#./ -]*')
# The song's settings, in the order they're written at the top of a file. The description is
# written as a block after the title and author.
_SETTINGS = [
    SongSetting.TITLE, SongSetting.AUTHOR, SongSetting.TEMPO, SongSetting.SCALE, SongSetting.SEED,
    SongSetting.DEFAULT_LENGTH, SongSetting.GRANULARITY, SongSetting.DEFAULT_OCTAVE, SongSetting.DEFAULT_DRUM_OCTAVE,
]
_BEFORE_DESCRIPTION = (SongSetting.TITLE, SongSetting.AUTHOR)
_GENERATOR_SECTIONS = [Section.ARPS, Section.AUTO_RATCHETS]
_PATTERN_SETTINGS = [PatternSetting.DIRECTION, PatternSetting.ACCUMULATOR_LIMIT]

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
DRUM_LINE = 'drum: true'
# A block of text, like a description: | then lines indented under it. A number after the | says
# how far the text is indented, which YAML needs when its first line starts with a space. Then -
# drops the last line break, nothing keeps one, and + keeps them all.
BLOCK = '{key}: |{indent}{chomp}'
BLOCK_INDENT = '2'
DROP_LAST_BREAK, KEEP_ONE_BREAK, KEEP_EVERY_BREAK = '-', '', '+'
NO_INDENT = ''


def _description(text):
    """Return a description as a YAML block, so that each line of it reads as it was written."""
    key = SongSetting.DESCRIPTION
    if not text.strip():
        return [SETTING.format(key=key, value=_text(text))]
    indent = BLOCK_INDENT if text.lstrip(LINE_BREAK)[:1] == SPACE else NO_INDENT
    if not text.endswith(LINE_BREAK):
        chomp, body = DROP_LAST_BREAK, text
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
    return _PLAIN.fullmatch(text) is not None and yaml.safe_load(LIST.format(items=text)) == [text]


def _first_line(text):
    return text.split(LINE_BREAK)[0]


def _braces(settings):
    if not settings:
        return EMPTY_MAP
    return MAP.format(items=ITEM_SEPARATOR.join(SETTING.format(key=_text(key), value=_text(value)) for key, value in settings.items()))


def _named(section, items):
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
    """Return one scene as a list item: its settings, then its tracks' cells, each on its own line."""
    if not scene:
        return [INDENT + LIST_ITEM + EMPTY_MAP]
    lines = []
    for key, value in scene.items():
        prefix = INDENT + LIST_ITEM if not lines else INDENT * 2
        if key == SceneSetting.TRACKS:
            lines.append(prefix + (HEADING.format(key=key) if value else SETTING.format(key=key, value=EMPTY_MAP)))
            lines += [INDENT * 3 + SETTING.format(key=_text(track), value=_braces(cell)) for track, cell in (value or {}).items()]
        else:
            lines.append(prefix + SETTING.format(key=key, value=_text(value)))
    return lines


def dump_song(song):
    """Return a song's data as the text of a song file."""
    settings = [SETTING.format(key=key, value=_text(song[key])) for key in _SETTINGS if key in song]
    if song.get(SongSetting.DESCRIPTION):
        # The description comes straight after the title and author.
        place = sum(key in song for key in _BEFORE_DESCRIPTION)
        settings[place:place] = _description(song[SongSetting.DESCRIPTION])
    sections = [settings]
    if song.get(Section.SCALES):
        sections.append(_named(Section.SCALES, song[Section.SCALES]))
    if song.get(Section.PATTERNS):
        sections.append(_patterns(song[Section.PATTERNS]))
    tracks = song.get(Section.TRACKS)
    sections.append(_named(Section.TRACKS, tracks) if tracks else [SETTING.format(key=Section.TRACKS, value=EMPTY_MAP)])
    for section in _GENERATOR_SECTIONS:
        if song.get(section):
            sections.append(_named(section, song[section]))
    if song.get(Section.CHAINS):
        sections.append(_chains(song[Section.CHAINS]))
    sections.append(_scenes(song.get(Section.SCENES) or []))
    return BLANK_LINE.join(LINE_BREAK.join(section) for section in sections) + LINE_BREAK
