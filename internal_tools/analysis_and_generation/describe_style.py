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

"""Print the style of a song as JSON (user_scripts/describe_style.sh): a MIDI file, or a llamatron set and one of its songs
rendered to its real notes. Only what the analyzer measures from the song's notes: no genre, artist or composer is consulted,
and no note of the song is written. The document can be read by a person or a tool, and in time handed to
a generator. Unstable: the fields change as the
analyzer does.

    sh user_scripts/describe_style.sh examples/midi/entertainer.mid
    sh user_scripts/describe_style.sh my_set.yml --song "second song" > style.json
"""

import argparse
import json
import pathlib
import sys

from llamatron.genres.hearing.profile import profile_of_performance
from llamatron.genres.reporting.style_document import style_document

from song_reading import performance_and_name

PATH_HELP = 'the song: a MIDI file, or a llamatron set file'
SONG_HELP = "the song of a set to describe; needed when the set holds more than one"
NO_SUCH_FILE = 'no file at {path}'
JSON_INDENT = 2
SUCCESS = 0


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('path', help=PATH_HELP)
    parser.add_argument('--song', help=SONG_HELP)
    arguments = parser.parse_args(argv)
    path = pathlib.Path(arguments.path)
    if not path.is_file():
        raise SystemExit(NO_SUCH_FILE.format(path=path))
    performance, name, _ = performance_and_name(path=path, song=arguments.song)
    print(json.dumps(style_document(profile_of_performance(performance=performance, name=name)), indent=JSON_INDENT))
    return SUCCESS


if __name__ == '__main__':
    sys.exit(main())
