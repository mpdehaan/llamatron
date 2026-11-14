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

"""Take the cells of every song of Lakh's clean subset (internal_tools/analysis_and_generation/extract_cells.sh): the kit's, the
bass's and the chord part's commonest bars and the lead's rhythm, one line of JSON a song in .corpus/tables/lakh-cells.jsonl,
with its artist and title from its folder and file. One version of each song is read, a file refused is counted with why, and
no lead's pitch is read (corpus/cells.py). The training the generator's tables are made from; development only.

    internal_tools/analysis_and_generation/extract_cells.sh            # every artist
    internal_tools/analysis_and_generation/extract_cells.sh --limit 200
"""

import argparse
import collections
import json
import multiprocessing
import pathlib
import re
import sys

from corpus.cells import NotRead, cells_of

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent / '.corpus'
SONGS = ROOT / 'lakh-clean'
WRITTEN = ROOT / 'tables' / 'lakh-cells.jsonl'
MIDI_FILES = '*.mid'
# A second transcription of a song is named with a number after a dot, and is passed over.
VERSION = re.compile(r'\.\d+$')
LIMIT_HELP = 'read this many songs only, spread through the artists'
NOT_FETCHED = 'Lakh is not in .corpus/ (fetch_corpus.sh fetches it)'
DONE = '{read} songs read into {path}'
REFUSED = '  {count} {reason}'
ARTIST = 'artist'
TITLE = 'title'
REASON = 'reason'
SUCCESS = 0


def one_song(path):
    """Return a song's line: its artist, its title and its cells, or why it was not read."""
    found = {ARTIST: path.parent.name, TITLE: path.stem}
    try:
        found.update(cells_of(path))
    except NotRead as error:
        found[REASON] = str(error)
    except Exception as error:
        found[REASON] = type(error).__name__
    return found


def first_versions(paths):
    return [path for path in paths if not VERSION.search(path.stem)]


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--limit', type=int, help=LIMIT_HELP)
    arguments = parser.parse_args(argv)
    paths = first_versions(sorted(SONGS.rglob(MIDI_FILES)))
    if not paths:
        raise SystemExit(NOT_FETCHED)
    if arguments.limit:
        paths = paths[::max(len(paths) // arguments.limit, 1)]
    refused = collections.Counter()
    read = 0
    with multiprocessing.Pool() as pool, WRITTEN.open('w') as handle:
        for found in pool.imap(one_song, paths, chunksize=16):
            if REASON in found:
                refused[found[REASON]] += 1
                continue
            handle.write(json.dumps(found) + '\n')
            read += 1
    print(DONE.format(read=read, path=WRITTEN))
    for reason, count in refused.most_common():
        print(REFUSED.format(count=count, reason=reason))
    return SUCCESS


if __name__ == '__main__':
    sys.exit(main())
