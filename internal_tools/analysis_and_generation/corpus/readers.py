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

"""A reader for every source in .corpus/, each yielding the corpus's pieces: up to a limit, taken evenly through the source so a
sample spans it, in the same order every time; a file that can't be read is passed over (the data isn't assumed to be good)."""

import csv
import json
import pathlib
import re
import sqlite3

import numpy
import pretty_midi
from music21 import converter, harmony, key as m21key, meter as m21meter

from corpus.piece import CorpusNote, Piece
from dataset_study import billboard_song, billboard_years, expanded_rules, numeral_root

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent / '.corpus'
KERN = '*.krn'
DEFAULT_LIMIT = 500
SECONDS_IN_A_MINUTE = 60.0
MODE_NAME_LETTERS = 3
SESSION_HEADER = 'X:1\nT:{name}\nM:{meter}\nL:1/8\nK:{key}\n{abc}'
# The Humdrum collections named after their composer, whose pieces are labelled by the composer's period and person: chamber,
# choral and keyboard scores, so that the classical corpus is not all piano.
COMPOSER_COLLECTIONS = ('beethoven-string-quartets', 'beethoven-piano-sonatas', 'bach-chorales', 'bach-art-of-fugue', 'vivaldi-op6')
KERN_COLLECTIONS = ('joplin', 'chopin-mazurkas', 'haydn-piano-sonatas', 'mozart-piano-sonatas') + COMPOSER_COLLECTIONS
# The most pieces read of a collection whose pieces are all of one kind, so that 370 chorales don't stand for the baroque.
SAMPLED = {'bach-chorales': 80}


def spread(items, *, limit):
    """Return up to limit of the items, taken evenly through them."""
    items = list(items)
    if len(items) <= limit:
        return items
    step = len(items) / limit
    return [items[int(place * step)] for place in range(limit)]


def notes_of_score(score):
    """Return a music21 score's notes, each part its own, at their offsets in quarter notes."""
    notes = []
    parts = list(score.parts) or [score]
    for number, part in enumerate(parts):
        for element in part.stripTies().flatten().notes:
            if isinstance(element, harmony.ChordSymbol):
                continue
            for pitch in element.pitches:
                notes.append(CorpusNote(start=float(element.offset), length=float(element.quarterLength), pitch=pitch.midi, part=str(number + 1)))
    return tuple(notes)


def chords_of_score(score):
    """Return a lead sheet's chord symbols as (beat, root's pitch class, quality), in order, passing over a symbol with no notes
    in it, which crowd-made transcriptions sometimes hold."""
    chords = []
    for symbol in score.recurse().getElementsByClass(harmony.ChordSymbol):
        try:
            root = symbol.root()
        except Exception:
            continue
        if root is not None:
            chords.append((float(symbol.offset), root.pitchClass, symbol.chordKind))
    return tuple(chords)


def meter_and_key(score):
    """Return a score's first time signature as text with its beats in a bar, and its first key signature's major tonic."""
    signatures = list(score.recurse().getElementsByClass(m21meter.TimeSignature))
    signature = signatures[0] if signatures else m21meter.TimeSignature()
    keys = list(score.recurse().getElementsByClass(m21key.KeySignature))
    tonic = keys[0].asKey('major').tonic.name if keys else None
    return signature.ratioString, float(signature.barDuration.quarterLength), tonic


def piece_of_score(*, score, source, identity, **known):
    """Return a music21 score as a piece, or None when it can't be read into notes."""
    try:
        return read_piece_of_score(score=score, source=source, identity=identity, **known)
    except Exception:
        return None


def read_piece_of_score(*, score, source, identity, **known):
    meter, beats_per_bar, tonic = meter_and_key(score)
    try:
        score = score.expandRepeats()
    except Exception:
        pass
    return Piece(source=source, identity=identity, meter=meter, beats_per_bar=beats_per_bar, key=tonic, notes=notes_of_score(score), chords=chords_of_score(score), **known)


def read_kern(*, source, limit=DEFAULT_LIMIT):
    """Read a Humdrum collection: the Essen songs, with their region from their folders, or a composer's pieces."""
    folder = ROOT / source
    for path in spread(sorted(folder.rglob(KERN)), limit=limit):
        try:
            score = converter.parse(str(path))
        except Exception:
            continue
        region = '/'.join(path.relative_to(folder).parts[:-1]) or None
        yield piece_of_score(score=score, source=source, identity=str(path.relative_to(folder)), title=path.stem, region=region,
                             creator=None if source == 'essen' else source.split('-')[0])


def read_weimar(*, limit=DEFAULT_LIMIT):
    """Read the Weimar Jazz Database's solos, each note's seconds turned into beats by the solo's own beat times."""
    connection = sqlite3.connect('file:{}?mode=ro'.format(ROOT / 'weimar-jazz' / 'wjazzd.db'), uri=True)
    beats = {}
    for melid, onset in connection.execute('select melid, onset from beats order by melid, onset'):
        beats.setdefault(melid, []).append(onset)
    melodies = {}
    for melid, onset, pitch, duration, loudness in connection.execute('select melid, onset, pitch, duration, loud_med from melody order by melid, onset'):
        melodies.setdefault(melid, []).append((onset, pitch, duration, loudness))
    # The year a solo was recorded, not the year its record was released, which for early jazz is a reissue decades later.
    rows = list(connection.execute('select s.melid, s.performer, s.title, s.style, s.avgtempo, s.signature, s.instrument, s.rhythmfeel, t.recordingdate '
                                   'from solo_info s left join track_info t on s.trackid = t.trackid order by s.melid'))
    for melid, performer, title, style, tempo, signature, instrument, feel, released in spread(rows, limit=limit):
        times = beats.get(melid)
        if not times or len(times) < 2 or melid not in melodies:
            continue
        places = numpy.arange(len(times), dtype=float)
        notes = []
        for onset, pitch, duration, loudness in melodies[melid]:
            start = float(numpy.interp(onset, times, places))
            end = float(numpy.interp(onset + duration, times, places))
            velocity = int(max(1, min(127, (loudness or 60) + 40)))
            notes.append(CorpusNote(start=start, length=max(end - start, 0.05), pitch=int(pitch), velocity=velocity))
        found = re.search(r'(1[89]|20)\d\d', released or '')
        year = int(found.group(0)) if found else None
        yield Piece(source='weimar-jazz', identity=str(melid), title=title, creator=performer, year=year, style=style, meter=signature or '4/4',
                    tempo=tempo or 120, notes=tuple(notes), extra={'instrument': instrument, 'feel': feel})


def read_billboard(*, limit=DEFAULT_LIMIT):
    """Read the Billboard songs' chords as degrees of their key and their sections, with their chart years."""
    folder = ROOT / 'billboard'
    years = billboard_years(folder / 'billboard-2.0-index.csv')
    for path in spread(sorted(folder.rglob('salami_chords.txt')), limit=limit):
        try:
            tonic, sections, bars = billboard_song(path)
        except Exception:
            continue
        if not bars:
            continue
        lines = path.read_text(errors='replace').splitlines()
        title = next((line.split(':', 1)[1].strip() for line in lines if line.startswith('# title:')), None)
        artist = next((line.split(':', 1)[1].strip() for line in lines if line.startswith('# artist:')), None)
        yield Piece(source='billboard', identity=path.parent.name, title=title, creator=artist, year=years.get(path.parent.name.zfill(4)),
                    chords=tuple(tuple(bar) for bar in bars), sections=tuple(sections))


def read_rock_corpus(*, limit=DEFAULT_LIMIT):
    """Read the rock corpus's songs as their chord numerals in order, from Trevor de Clercq's analyses."""
    for path in spread(sorted((ROOT / 'rock-corpus').rglob('*_tdc.har')), limit=limit):
        symbols = [numeral_root(symbol) for symbol in expanded_rules(path.read_text(errors='replace'))]
        symbols = tuple((symbol,) for symbol in symbols if symbol)
        if symbols:
            yield Piece(source='rock-corpus', identity=path.stem, title=path.stem.rsplit('_', 1)[0].replace('_', ' '), chords=symbols)


def midi_notes(path):
    """Return a MIDI file's notes in beats, its drum parts, its first tempo and its meter, read with pretty_midi."""
    song = pretty_midi.PrettyMIDI(str(path))
    resolution = float(song.resolution)
    notes = []
    drum_parts = set()
    for number, instrument in enumerate(song.instruments):
        part = '{}:{}'.format(number, instrument.name or instrument.program)
        if instrument.is_drum:
            drum_parts.add(part)
        for note in instrument.notes:
            start = song.time_to_tick(note.start) / resolution
            end = song.time_to_tick(note.end) / resolution
            notes.append(CorpusNote(start=start, length=max(end - start, 0.05), pitch=note.pitch, velocity=note.velocity, part=part))
    _, tempos = song.get_tempo_changes()
    signatures = song.time_signature_changes
    meter = '{}/{}'.format(signatures[0].numerator, signatures[0].denominator) if signatures else '4/4'
    beats_per_bar = signatures[0].numerator * 4.0 / signatures[0].denominator if signatures else 4.0
    return tuple(notes), frozenset(drum_parts), float(tempos[0]) if len(tempos) else 120.0, meter, beats_per_bar


def read_midi_folder(*, source, limit=DEFAULT_LIMIT, metadata=None):
    """Read a folder of MIDI files: Lakh's clean subset, its artist and title from its folders."""
    folder = ROOT / source
    for path in spread(sorted(folder.rglob('*.mid')), limit=limit):
        try:
            notes, drum_parts, tempo, meter, beats_per_bar = midi_notes(path)
        except Exception:
            continue
        if not notes:
            continue
        known = (metadata or {}).get(path, {})
        yield Piece(source=source, identity=str(path.relative_to(folder)), title=known.get('title', path.stem), creator=known.get('creator', path.parent.name),
                    style=known.get('style'), tempo=tempo, meter=meter, beats_per_bar=beats_per_bar, notes=notes, drum_parts=drum_parts,
                    drums=known.get('drums', False), extra=known.get('extra', {}))


def read_lakh(*, limit=DEFAULT_LIMIT):
    return read_midi_folder(source='lakh-clean', limit=limit)


def read_groove(*, limit=DEFAULT_LIMIT):
    """Read Groove MIDI's drum performances, beats rather than fills, with their drummer, style and tempo."""
    folder = ROOT / 'groove-midi' / 'groove'
    with (folder / 'info.csv').open(newline='') as handle:
        rows = [row for row in csv.DictReader(handle) if row['beat_type'] == 'beat']
    for row in spread(rows, limit=limit):
        try:
            notes, _, _, meter, beats_per_bar = midi_notes(folder / row['midi_filename'])
        except Exception:
            continue
        yield Piece(source='groove-midi', identity=row['id'], creator=row['drummer'], style=row['style'].split('/')[0], tempo=float(row['bpm']),
                    meter=meter, beats_per_bar=beats_per_bar, notes=notes, drums=True)


def read_lead_sheets(*, source, pattern, limit=DEFAULT_LIMIT, metadata=None):
    """Read a folder of MusicXML lead sheets, melody and chord symbols."""
    folder = ROOT / source
    for path in spread(sorted(folder.rglob(pattern)), limit=limit):
        try:
            score = converter.parse(str(path))
        except Exception:
            continue
        known = (metadata or {}).get(path.name, {})
        yield piece_of_score(score=score, source=source, identity=path.name, title=known.get('title', path.stem.title()), creator=known.get('creator'),
                             year=known.get('year'), style=known.get('style'))


def openewld_metadata():
    """Return OpenEWLD's database facts by each lead sheet's file name: its title, author, year and most common style."""
    path = next((ROOT / 'openewld').rglob('OpenEWLD.db'), None)
    if path is None:
        return {}
    connection = sqlite3.connect('file:{}?mode=ro'.format(path), uri=True)
    authors = dict(connection.execute('select id, author from work_author'))
    styles = {}
    for identity, style, occurrences in connection.execute('select id, style, occurrences from work_style order by occurrences desc'):
        styles.setdefault(identity, style)
    result = {}
    for identity, title, performed, sheet in connection.execute('select id, title, first_performance_date, path_leadsheet from works'):
        year = int(performed[:4]) if performed and performed[:4].isdigit() else None
        result[pathlib.PurePosixPath(sheet or '').name] = {'title': title, 'creator': authors.get(identity), 'year': year, 'style': styles.get(identity)}
    return result


def read_openewld(*, limit=DEFAULT_LIMIT):
    return read_lead_sheets(source='openewld', pattern='*.mxl', limit=limit, metadata=openewld_metadata())


def read_anthology(*, limit=DEFAULT_LIMIT):
    return read_lead_sheets(source='song-anthology', pattern='*.xml', limit=limit)


def read_nottingham(*, limit=DEFAULT_LIMIT):
    """Read the Nottingham tunes, each ABC file a collection of them, their type from the file's name."""
    tunes = []
    for path in sorted((ROOT / 'nottingham').rglob('*.abc')):
        if 'cleaned' not in str(path).lower():
            continue
        try:
            opus = converter.parse(str(path))
        except Exception:
            continue
        tunes += [(path.stem, score) for score in (opus.scores if hasattr(opus, 'scores') else [opus])]
    for number, (kind, score) in enumerate(spread(tunes, limit=limit)):
        yield piece_of_score(score=score, source='nottingham', identity='{}-{}'.format(kind, number), title=score.metadata.title if score.metadata else None, style=kind)


def session_key(mode):
    """Return the Session's mode, such as Edorian, as an ABC key, such as Edor."""
    match = re.match(r'([A-G][b#]?)([a-z]+)', mode or '')
    return match.group(1) + match.group(2)[:MODE_NAME_LETTERS] if match else 'C'


def read_session(*, limit=DEFAULT_LIMIT):
    """Read the Session's tunes, each setting's ABC given a header from its meter and mode, with its dance type."""
    tunes = json.loads((ROOT / 'thesession' / 'tunes.json').read_text())
    for tune in spread(tunes, limit=limit):
        text = SESSION_HEADER.format(name=tune['name'], meter=tune['meter'], key=session_key(tune['mode']), abc=tune['abc'].replace('\r', ''))
        try:
            score = converter.parse(text, format='abc')
        except Exception:
            continue
        yield piece_of_score(score=score, source='thesession', identity=tune['setting_id'], title=tune['name'], style=tune['type'],
                             extra={'mode': tune['mode']})


def read_mutopia(*, limit=DEFAULT_LIMIT):
    """Read the Mutopia Project's MIDI files, made from engraved scores, each composer's code its folder."""
    return read_midi_folder(source='mutopia', limit=limit)


def read_maestro(*, limit=DEFAULT_LIMIT):
    """Read MAESTRO's piano performances with their composers, titles and years from the dataset's own list."""
    folder = ROOT / 'maestro'
    listing = next(folder.rglob('*.csv'), None)
    if listing is None:
        return
    with listing.open(newline='') as handle:
        rows = list(csv.DictReader(handle))
    for row in spread(rows, limit=limit):
        path = listing.parent / row['midi_filename']
        try:
            notes, drum_parts, tempo, meter, beats_per_bar = midi_notes(path)
        except Exception:
            continue
        yield Piece(source='maestro', identity=row['midi_filename'], title=row['canonical_title'], creator=row['canonical_composer'], year=int(row['year']),
                    tempo=tempo, meter=meter, beats_per_bar=beats_per_bar, notes=notes, drum_parts=drum_parts)


READERS = {
    'essen': lambda limit: read_kern(source='essen', limit=limit),
    'weimar-jazz': lambda limit: read_weimar(limit=limit),
    'billboard': lambda limit: read_billboard(limit=limit),
    'rock-corpus': lambda limit: read_rock_corpus(limit=limit),
    'groove-midi': lambda limit: read_groove(limit=limit),
    'lakh-clean': lambda limit: read_lakh(limit=limit),
    'openewld': lambda limit: read_openewld(limit=limit),
    'song-anthology': lambda limit: read_anthology(limit=limit),
    'nottingham': lambda limit: read_nottingham(limit=limit),
    'thesession': lambda limit: read_session(limit=limit),
    'mutopia': lambda limit: read_mutopia(limit=limit),
    'maestro': lambda limit: read_maestro(limit=limit),
}
READERS.update({name: (lambda name: lambda limit: read_kern(source=name, limit=min(limit, SAMPLED.get(name, limit))))(name) for name in KERN_COLLECTIONS})


def readable(pieces):
    """Return only the pieces a reader could make, passing over the ones it couldn't."""
    return (piece for piece in pieces if piece is not None)


READERS = {name: (lambda reader: lambda limit: readable(reader(limit)))(reader) for name, reader in READERS.items()}


def is_fetched(source):
    """Return whether a source's files are at hand in .corpus/, fetched by fetch_corpus.sh."""
    folder = ROOT / source
    return folder.is_dir() and any(folder.iterdir())


