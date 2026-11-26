# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Measure the corpus into its tables (internal_tools/analysis_and_generation/corpus_tables.sh): every source's pieces, or the
named sources, profiled in every numeric field the library compares and cached in output/library/tables/, rebuilt when llamatron's
version has changed since a table was measured, or always with --rebuild (114 C: re-analysed as the analyzers improve).

    internal_tools/analysis_and_generation/corpus_tables.sh                 every source, the stale ones measured
    internal_tools/analysis_and_generation/corpus_tables.sh joplin --rebuild one source, measured afresh
"""

import argparse
from corpus.readers import COMPOSER_COLLECTIONS, is_fetched, READERS
from corpus.tables import table_of
import sys
import time

REBUILD = '--rebuild'
NAMES_HELP = 'the sources to measure; every one when none is named'
REBUILD_HELP = 'measure afresh even when a table is current'
MEASURED = '{source}: {rows} pieces measured ({seconds}s)'
NOT_FETCHED = '{source}: not fetched, passed over (fetch_corpus.sh fetches it)'
# The sources whose pieces are notes to measure; the chord annotations and drums have studies of their own.
MEASURED_SOURCES = ('joplin', 'chopin-mazurkas', 'haydn-piano-sonatas', 'mozart-piano-sonatas', 'essen', 'thesession', 'nottingham',
                    'mutopia', 'maestro', 'openewld', 'song-anthology') + COMPOSER_COLLECTIONS


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
