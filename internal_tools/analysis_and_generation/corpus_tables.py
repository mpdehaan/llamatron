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

"""Measure the corpus into its tables (internal_tools/analysis_and_generation/corpus_tables.sh): every source's pieces, or the
named sources, profiled in every numeric field the library compares and cached in .corpus/tables/, rebuilt when llamatron's
version has changed since a table was measured, or always with --rebuild (114 C: re-analysed as the analyzers improve).

    internal_tools/analysis_and_generation/corpus_tables.sh                 every source, the stale ones measured
    internal_tools/analysis_and_generation/corpus_tables.sh joplin --rebuild one source, measured afresh
"""

import argparse
import sys
import time

from corpus.readers import COMPOSER_COLLECTIONS, READERS, is_fetched
from corpus.tables import table_of

REBUILD = '--rebuild'
NAMES_HELP = 'the sources to measure; every one when none is named'
REBUILD_HELP = 'measure afresh even when a table is current'
MEASURED = '{source}: {rows} pieces measured ({seconds}s)'
NOT_FETCHED = '{source}: not fetched, passed over (fetch_corpus.sh fetches it)'
# The sources whose pieces are notes to measure; the chord annotations and drums have studies of their own.
MEASURED_SOURCES = ('joplin', 'chopin-mazurkas', 'haydn-piano-sonatas', 'mozart-piano-sonatas', 'weimar-jazz', 'essen', 'thesession', 'nottingham',
                    'mutopia', 'maestro', 'openewld', 'song-anthology', 'lakh-clean') + COMPOSER_COLLECTIONS


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('names', nargs='*', help=NAMES_HELP)
    parser.add_argument(REBUILD, action='store_true', help=REBUILD_HELP)
    arguments = parser.parse_args(argv)
    for source in arguments.names or MEASURED_SOURCES:
        if source not in READERS:
            continue
        if not is_fetched(source):
            print(NOT_FETCHED.format(source=source), flush=True)
            continue
        started = time.time()
        table = table_of(source=source, rebuild=arguments.rebuild)
        print(MEASURED.format(source=source, rows=len(table), seconds=round(time.time() - started)), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
