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

from llamatron.song_file import PATTERN_ROWS

_PLAIN = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_#./ -]*')
_SETTINGS = ['title', 'author', 'tempo', 'scale', 'seed', 'default_length', 'granularity', 'default_octave', 'default_drum_octave']


def _description(text):
    """Return a description as a YAML block, so that each line of it reads as it was written."""
    # A number says how far the text is indented, which YAML needs when the first line starts
    # with a space. Then |- drops the last line break, | keeps one, and |+ keeps them all.
    if not text.strip():
        return [f'description: {_text(text)}']
    indent = '2' if text.lstrip('\n')[:1] == ' ' else ''
    if not text.endswith('\n'):
        chomp, body = '-', text
    else:
        chomp, body = ('+' if text.endswith('\n\n') else ''), text[:-1]
    return [f'description: |{indent}{chomp}'] + [f'  {line}' if line else '' for line in body.split('\n')]


def _text(value):
    """Return a value as YAML that's safe inside brackets and braces."""
    if value is None:
        return '~'
    if isinstance(value, list):
        return '[' + ', '.join(_text(item) for item in value) + ']'
    if isinstance(value, dict):
        return _braces(value)
    if isinstance(value, str):
        if _PLAIN.fullmatch(value) and yaml.safe_load(f'[{value}]') == [value]:
            return value
        return json.dumps(value)
    return yaml.safe_dump(value).split('\n')[0]


def _braces(settings):
    if not settings:
        return '{}'
    return '{ ' + ', '.join(f'{_text(key)}: {_text(value)}' for key, value in settings.items()) + ' }'


def _named(section, items):
    return [f'{section}:'] + [f'  {_text(name)}: {_braces(item)}' for name, item in items.items()]


def _patterns(patterns):
    lines = ['patterns:']
    for name, pattern in patterns.items():
        lines.append(f'  {_text(name)}:')
        lines.append(f'    steps: {pattern["steps"]}')
        if pattern.get('drum'):
            lines.append('    drum: true')
        for setting in ['direction', 'accumulator_limit']:
            if pattern.get(setting):
                lines.append(f'    {setting}: {_text(pattern[setting])}')
        lines += [f'    {row}: {_text(pattern[row])}' for row in PATTERN_ROWS if pattern.get(row) is not None]
    return lines


def _chains(chains):
    lines = ['chains:']
    for name, steps in chains.items():
        lines.append(f'  {_text(name)}: []' if not steps else f'  {_text(name)}:')
        for step in steps:
            for generator, settings in step.items():
                lines.append(f'    - {_text(generator)}: {_text(settings)}')
    return lines


def _scenes(scenes):
    if not scenes:
        return ['scenes: []']
    lines = ['scenes:']
    for scene in scenes:
        first = True
        for key, value in scene.items():
            prefix = '  - ' if first else '    '
            first = False
            if key == 'tracks':
                lines.append(f'{prefix}tracks:' if value else f'{prefix}tracks: {{}}')
                lines += [f'      {_text(track)}: {_braces(cell)}' for track, cell in (value or {}).items()]
            else:
                lines.append(f'{prefix}{key}: {_text(value)}')
        if first:
            lines.append('  - {}')
    return lines


def dump_song(song):
    """Return a song's data as the text of a song file."""
    settings = [f'{key}: {_text(song[key])}' for key in _SETTINGS if key in song]
    if song.get('description'):
        # The description comes straight after the title and author.
        place = sum(key in song for key in ('title', 'author'))
        settings[place:place] = _description(song['description'])
    sections = [settings]
    if song.get('scales'):
        sections.append(_named('scales', song['scales']))
    if song.get('patterns'):
        sections.append(_patterns(song['patterns']))
    sections.append(_named('tracks', song['tracks']) if song.get('tracks') else ['tracks: {}'])
    for section in ['arps', 'auto_ratchets']:
        if song.get(section):
            sections.append(_named(section, song[section]))
    if song.get('chains'):
        sections.append(_chains(song['chains']))
    sections.append(_scenes(song.get('scenes') or []))
    return '\n\n'.join('\n'.join(section) for section in sections) + '\n'
