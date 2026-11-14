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

"""Each piece's measures as a table row, cached per source in .corpus/tables/, for meta-analysis and calibration: every numeric
field the library compares, under its trait's name and field's name joined by a dot, with the piece's source, identity, creator,
year and the library style it is labelled as, where its source says (a rag is ragtime, a reel is Celtic, a bebop solo is
bebop). A table records a fingerprint of the analyzer that measured it (the source of genres/hearing/ and the traits), so that a table
measured by an older analyzer is rebuilt rather than trusted (114 C: everything is re-analysed as the analyzers improve), while a
change elsewhere in llamatron leaves it alone."""

import hashlib
import json
import multiprocessing
import pathlib
import zlib

import pandas

from llamatron.genres.hearing.midi_file import performance_of_midi
from llamatron.genres.hearing.profile import profile_of_performance
from llamatron.genres.measures.registry import MEASURES
from llamatron.strings.genres import StyleName
import llamatron.genres.hearing
import llamatron.genres.measures.traits

from corpus.composers import period_of
from corpus.readers import COMPOSER_COLLECTIONS, READERS, ROOT

N = StyleName
TABLES = ROOT / 'tables'
TABLE = '{source}.parquet'
STAMP = '{source}.json'
# The columns every row has besides its measures.
SOURCE = 'source'
IDENTITY = 'identity'
CREATOR = 'creator'
YEAR = 'year'
LABEL = 'label'
HALF = 'half'
VERSION_KEY = 'analyzer'
PYTHON_FILES = '*.py'
LIMIT_KEY = 'limit'
CALIBRATE = 'calibrate'
# The measures that are not numbers and are kept all the same, as JSON text: how the bass moves, the sounds of each role, the
# moves between keys and the energy's shape, from which a style's sets of possibilities are found.
BASS_MOTION = 'bass.motion'
SOUND_ROLES = 'sounds.roles'
KEY_MOVES = 'modulation.moves'
ENERGY_ARC = 'energy.arc'
WRITTEN_AS_TEXT = (BASS_MOTION, SOUND_ROLES, KEY_MOVES, ENERGY_ARC)
# Where the files of each source that is MIDI are, by the source, a piece's identity being its path from there.
FILE_ROOTS = {'mutopia': ROOT / 'mutopia', 'maestro': ROOT / 'maestro' / 'maestro-v3.0.0'}
TEST = 'test'
# How many pieces of each source to measure by default.
LIMITS = {'essen': 1200, 'weimar-jazz': 456, 'joplin': 47, 'chopin-mazurkas': 52, 'haydn-piano-sonatas': 25, 'mozart-piano-sonatas': 69,
          'thesession': 1200, 'nottingham': 500, 'openewld': 502, 'song-anthology': 348, 'lakh-clean': 600, 'mutopia': 133, 'maestro': 400}
# The library styles the Weimar Jazz Database's styles are labelled as.
JAZZ_LABELS = {'TRADITIONAL': N.NEW_ORLEANS, 'SWING': N.SWING, 'BEBOP': N.BEBOP, 'COOL': N.COOL_JAZZ, 'HARDBOP': N.HARD_BOP, 'POSTBOP': N.MODAL_JAZZ,
               'FUSION': N.JAZZ_FUSION}
# The dance types of the Session and Nottingham that the library's Celtic style holds.
CELTIC_TYPES = ('reel', 'jig', 'hornpipe', 'slip jig', 'strathspey', 'polka', 'slide', 'barndance', 'jigs', 'reelsa-c', 'reelsd-g', 'reelsh-l',
                'reelsm-q', 'reelsr-t', 'reelsu-z', 'hpps', 'slip')
# The genre each composer's collection is labelled as; the composer's own style is judged among the people.
FIXED_LABELS = {'joplin': N.RAGTIME, 'chopin-mazurkas': N.ROMANTIC, 'haydn-piano-sonatas': N.CLASSICAL_ERA, 'mozart-piano-sonatas': N.CLASSICAL_ERA}
CHINA = 'asia/china'
EUROPE = 'europa'


def label_of(piece):
    """Return the library style a piece is labelled as by what its source says, or None when its source says nothing the
    library has a style for."""
    if piece.source in FIXED_LABELS:
        return FIXED_LABELS[piece.source]
    if piece.source == 'weimar-jazz':
        return JAZZ_LABELS.get(piece.style)
    if piece.source == 'essen':
        if (piece.region or '').startswith(CHINA):
            return N.CHINESE_FOLK
        return N.FOLK if (piece.region or '').startswith(EUROPE) else None
    if piece.source in ('mutopia', 'maestro') + COMPOSER_COLLECTIONS:
        return period_of(piece.creator)
    if piece.source in ('thesession', 'nottingham'):
        kind = (piece.style or '').lower()
        return N.CELTIC if any(kind.startswith(celtic) for celtic in CELTIC_TYPES) else None
    return None


def half_of(identity):
    """Return which half a piece falls in, calibrating or testing, by a stable hash of its identity, so that a style is never
    tested on the pieces it was calibrated from."""
    return CALIBRATE if zlib.crc32(identity.encode()) % 2 == 0 else TEST


def performance_heard(piece):
    """Return a piece as the analyzer hears it: from its own MIDI file where its source is MIDI, exactly as the explain tool
    reads a file, its instruments with it, so that what is measured into a table is what a person running the tool gets; and
    from the reader's notes otherwise."""
    root = FILE_ROOTS.get(piece.source)
    path = root / piece.identity if root is not None else None
    if path is not None and path.is_file():
        return performance_of_midi(str(path))
    return piece.performance()


def row_of(piece):
    """Return a piece's row: who and what it is, then every numeric measure, and the few measures that are names, lists or
    tables, written as text; or None for a piece with no notes to measure."""
    if not piece.notes or piece.drums:
        return None
    try:
        profile = profile_of_performance(performance=performance_heard(piece), name=piece.identity)
    except Exception:
        return None
    row = {SOURCE: piece.source, IDENTITY: piece.identity, CREATOR: piece.creator, YEAR: piece.year, LABEL: label_of(piece),
           HALF: half_of(piece.source + piece.identity)}
    for each in MEASURES:
        measured = each.of(profile)
        if each.is_number() and isinstance(measured, (int, float)) and not isinstance(measured, bool):
            row[each.name()] = float(measured)
        elif each.name() in WRITTEN_AS_TEXT and measured:
            row[each.name()] = json.dumps(measured)
    return row


def build_table(*, source, limit=None, processes=None):
    """Measure a source's pieces into its table and cache it, with the version it was measured by."""
    TABLES.mkdir(parents=True, exist_ok=True)
    limit = limit or LIMITS.get(source, 500)
    pieces = list(READERS[source](limit))
    with multiprocessing.Pool(processes=processes) as pool:
        rows = [row for row in pool.map(row_of, pieces, chunksize=4) if row is not None]
    table = pandas.DataFrame(rows)
    table.to_parquet(TABLES / TABLE.format(source=source))
    (TABLES / STAMP.format(source=source)).write_text(json.dumps({VERSION_KEY: FINGERPRINT, LIMIT_KEY: limit}))
    return table


def analyzer_fingerprint():
    """Return a fingerprint of the analyzer's source: every module of genres/hearing/ and the traits it measures into."""
    digest = hashlib.sha256()
    folder = pathlib.Path(llamatron.genres.hearing.__file__).parent
    for path in sorted(folder.glob(PYTHON_FILES)) + [pathlib.Path(llamatron.genres.measures.traits.__file__)]:
        digest.update(path.read_bytes())
    return digest.hexdigest()


# The analyzer's fingerprint when this process started, so that a table is stamped with the analyzer that actually measured it
# even if the analyzer's files change while a long build runs.
FINGERPRINT = analyzer_fingerprint()


def is_current(source):
    """Return whether a source's cached table was measured by the analyzer as it is now."""
    stamp = TABLES / STAMP.format(source=source)
    return stamp.exists() and json.loads(stamp.read_text()).get(VERSION_KEY) == FINGERPRINT and (TABLES / TABLE.format(source=source)).exists()


def table_of(*, source, rebuild=False):
    """Return a source's table, measuring it afresh when it is missing, stale or asked for."""
    if rebuild or not is_current(source):
        return build_table(source=source)
    return pandas.read_parquet(TABLES / TABLE.format(source=source))


def tables(*, sources, rebuild=False):
    return pandas.concat([table_of(source=source, rebuild=rebuild) for source in sources], ignore_index=True)


