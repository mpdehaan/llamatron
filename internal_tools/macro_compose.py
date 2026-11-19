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

"""The MacroComposer: a set composed from a song's input, structured data that says what to play (src/llamatron/macro_composer/).

    .venv/bin/python internal_tools/macro_compose.py INPUT --out SET          # compose the input into a set file
    .venv/bin/python internal_tools/macro_compose.py --decompose SET --out INPUT   # write an existing set as an input
    .venv/bin/python internal_tools/macro_compose.py INPUT --same-as SET      # say whether the input composes to the set's music, and fail if not
    .venv/bin/python internal_tools/macro_compose.py --arrange PICKS --out SET     # a whole song from a song's picks and its style's template (--keep-input INPUT)

It reads its input file and nothing else: it fetches nothing and looks nothing up.
"""

import argparse
import sys
from pathlib import Path

import yaml

from llamatron.composition.setlist import Setlist
from llamatron.macro_composer.arranger import STYLE, arranged, style_named
from llamatron.macro_composer.composer import composed
from llamatron.macro_composer.decomposer import decomposed, same_music
from llamatron.support.safe_yaml import load_safely
from llamatron.support import version

FILE_ENCODING = 'utf-8'
WRITE_TEXT = 'w'
LINE_WIDTH = 160
LEGEND = '''# A MacroComposer input: what a song plays, as data. Compose it with internal_tools/macro_compose.sh.
#
# parts     each part by name. A tune has lines, each a list of notes: degree is the note of the scale, steps how long it
#           lasts, rest a silence; octave moves a note up or down octaves, accidental is sharp or flat, and stress says why
#           a note is louder or softer than the part's velocity: pickup (soft, leading into a bar), arrival (the stressed
#           note a line arrives on), peak (a line's highest or most stressed note), ending (a line's last note, eased).
#           A drum has hits, one of loud, soft and none for every step. A part under raw is a pattern as a set writes it.
# shaped    the parts whose velocity the song's feel moves a little by where each note falls in the bar.
# bands     named groups of what tracks play, which a scene of the form takes with "with".
# form      the scenes in order: bars is how long a scene lasts, play is each track's part, by name or as a mapping
#           with its chains; a part loops for the scene unless it says repeat or once.
'''
MSG_ARRANGED = 'arranged {} in the style ({}) into {}'
MSG_COMPOSED = 'composed {} into {}'
MSG_DECOMPOSED = 'wrote {} as the input {}'
MSG_SAME = '{} composes to the music of {}'
ERR_DIFFERENT = '{} does not compose to the music of {}'


def read(path):
    with open(path, encoding=FILE_ENCODING) as file:
        return load_safely(file)


def compose_file(*, source, out):
    Setlist.from_data(data=composed(given=read(source), version=version.VERSION)).write_file(str(out))
    print(MSG_COMPOSED.format(source, out))


def arrange_file(*, source, out, keep_input):
    """A song's picks made into a set through its style's template, the input kept beside it when asked."""
    song = read(source)
    given = arranged(style=style_named(song[STYLE]), song=song)
    if keep_input:
        with open(keep_input, WRITE_TEXT, encoding=FILE_ENCODING) as file:
            file.write(LEGEND + yaml.safe_dump(given, sort_keys=False, width=LINE_WIDTH, default_flow_style=None, allow_unicode=True))
    Setlist.from_data(data=composed(given=given, version=version.VERSION)).write_file(str(out))
    print(MSG_ARRANGED.format(source, song[STYLE], out))


def decompose_file(*, source, out):
    text = yaml.safe_dump(decomposed(read(source)), sort_keys=False, width=LINE_WIDTH, default_flow_style=None, allow_unicode=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, WRITE_TEXT, encoding=FILE_ENCODING) as file:
        file.write(LEGEND + text)
    print(MSG_DECOMPOSED.format(source, out))


def composes_to(*, source, set_file):
    """Whether the input composes to the set file's music, each read back through the program so that both are written the same way."""
    made = Setlist.from_data(data=composed(given=read(source), version=version.VERSION)).to_data()
    kept = Setlist.read_file(str(set_file)).to_data()
    return same_music(one=made, other=kept)


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('input', nargs='?')
    parser.add_argument('--out')
    parser.add_argument('--decompose')
    parser.add_argument('--same-as')
    parser.add_argument('--arrange')
    parser.add_argument('--keep-input')
    arguments = parser.parse_args(argv)
    if arguments.arrange:
        arrange_file(source=arguments.arrange, out=arguments.out, keep_input=arguments.keep_input)
        return 0
    if arguments.decompose:
        decompose_file(source=arguments.decompose, out=arguments.out)
        return 0
    if arguments.same_as:
        same = composes_to(source=arguments.input, set_file=arguments.same_as)
        print((MSG_SAME if same else ERR_DIFFERENT).format(arguments.input, arguments.same_as))
        return 0 if same else 1
    compose_file(source=arguments.input, out=arguments.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
