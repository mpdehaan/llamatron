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

"""Study the research datasets internal_tools/analysis_and_generation/fetch_corpus.sh fetches into .corpus/ (internal_tools/analysis_and_generation/dataset_study.sh), for
calibrating the genre library where it had only estimates (109 A): the Weimar Jazz Database's transcribed solos, measured by
style and by performer (how dense, how stepwise, how wide, how much space, how loud and varied); the McGill Billboard chord
annotations, measured by decade (which chords, how roots move, how songs are laid out, how often a solo or instrumental comes
and where); de Clercq and Temperley's rock corpus (which chords rock uses); and Google Magenta's Groove MIDI drums, measured by
style and by drummer (swing, ghost notes, density, fills, the spread of velocity). Each beside the library's own values where it
has them. The data isn't assumed to be good: a file that can't be read is passed over and counted. Prints Markdown.

    internal_tools/analysis_and_generation/dataset_study.sh > datasets.md
"""

import csv
import pathlib
import re
import sqlite3
import statistics
import sys
from collections import Counter, defaultdict

import mido


ROOT = pathlib.Path(__file__).resolve().parent.parent.parent / '.corpus'
PITCH_CLASSES = 12
STEP = 2
# A note this many beats or more after the last one ends starts a new phrase where the database marks none.
FEWEST_SOLOS = 6
# The note names a Billboard chord's root is written with.
NOTE_CLASSES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
DEGREE_NAMES = ('I', 'bII', 'II', 'bIII', 'III', 'IV', 'bV', 'V', 'bVI', 'VI', 'bVII', 'VII')
# Each degree's place in the octave by its name in lower case, which a minor chord's numeral is written in.
DEGREE_INDEX = {name.lower(): place for place, name in enumerate(DEGREE_NAMES)}
MINOR_QUALITIES = ('min', 'min7', 'min9', 'min11', 'minmaj7', 'hdim7', 'dim', 'dim7')
SOLO_SECTIONS = ('solo', 'instrumental', 'interlude')
DECADE = 10
# The General MIDI notes Magenta's kit is recorded on, sorted into voices.
KICKS = {35, 36}
SNARES = {37, 38, 40}
HATS = {22, 26, 42, 44, 46}
RIDES = {51, 53, 59}
TOMS = {41, 43, 45, 47, 48, 50, 58}
GHOST_VELOCITY = 40
SIXTEENTH = 0.25
EIGHTH = 0.5
HEADING = '\n## {name}\n'
SUBHEADING = '\n### {name}\n'
ROW = '| {cells} |'
RULE = '| {cells} |'
JOIN = ', '
CELL = ' | '
DASH = '---'
COUNT = '{name} {count}'
NOTHING = '-'
SKIPPED = '- passed over, unreadable: {count}'


def median(values):
    return round(statistics.median(values), 2) if values else NOTHING


def table(*, heading, rows):
    """Return a Markdown table's lines from its heading cells and rows of cells."""
    return [ROW.format(cells=CELL.join(heading)), RULE.format(cells=CELL.join([DASH] * len(heading)))] + [ROW.format(cells=CELL.join(str(cell) for cell in row)) for row in rows]


# The jazz solos.


def solo_measures(*, notes, beats):
    """Return one solo's measures from its notes (onset, pitch, duration, loudness) and its count of beats: notes a beat, the
    share of moves by step, the range between its 5th and 95th percentile pitches, the share of its time in rests, and the spread
    of its loudness."""
    if len(notes) < 2 or beats <= 0:
        return None
    pitches = [pitch for _, pitch, _, _ in notes]
    moves = [abs(later - earlier) for earlier, later in zip(pitches, pitches[1:]) if later != earlier]
    ordered = sorted(pitches)
    low = ordered[int(0.05 * (len(ordered) - 1))]
    high = ordered[int(0.95 * (len(ordered) - 1))]
    span = notes[-1][0] + notes[-1][2] - notes[0][0]
    sounding = sum(min(duration, later[0] - onset) for (onset, _, duration, _), later in zip(notes, notes[1:])) + notes[-1][2]
    loudness = [loud for _, _, _, loud in notes if loud is not None]
    return {'density': len(notes) / beats, 'steps': sum(1 for move in moves if move <= STEP) / len(moves) if moves else 0.0, 'range': high - low,
            'space': max(0.0, 1 - sounding / span) if span > 0 else 0.0, 'dynamics': statistics.pstdev(loudness) if len(loudness) > 1 else 0.0}


def study_jazz():
    path = ROOT / 'weimar-jazz' / 'wjazzd.db'
    if not path.exists():
        return []
    connection = sqlite3.connect('file:{}?mode=ro'.format(path), uri=True)
    beats = dict(connection.execute('select melid, count(*) from beats group by melid'))
    notes = defaultdict(list)
    for melid, onset, pitch, duration, loudness in connection.execute('select melid, onset, pitch, duration, loud_med from melody order by melid, onset'):
        notes[melid].append((onset, pitch, duration, loudness))
    by_style = defaultdict(list)
    by_person = defaultdict(list)
    tempos = defaultdict(list)
    feels = defaultdict(Counter)
    for melid, performer, style, tempo, feel, instrument in connection.execute('select melid, performer, style, avgtempo, rhythmfeel, instrument from solo_info'):
        measured = solo_measures(notes=notes[melid], beats=beats.get(melid, 0))
        if measured is None:
            continue
        by_style[style].append(measured)
        by_person[performer].append(measured)
        if tempo:
            tempos[style].append(tempo)
        feels[style][feel] += 1
    lines = [HEADING.format(name='Weimar Jazz Database: solos by style')]
    heading = ('style', 'solos', 'tempo', 'notes a beat', 'steps', 'range', 'space', 'loudness spread', 'feels')
    rows = []
    for style, measured in sorted(by_style.items(), key=lambda item: -len(item[1])):
        rows.append((style, len(measured), median(tempos[style]),
                     median([each['density'] for each in measured]),
                     median([each['steps'] for each in measured]),
                     median([each['range'] for each in measured]),
                     median([each['space'] for each in measured]),
                     median([each['dynamics'] for each in measured]), JOIN.join(COUNT.format(name=name, count=count) for name, count in feels[style].most_common(3))))
    lines += table(heading=heading, rows=rows)
    lines.append(SUBHEADING.format(name='Performers with {} solos or more'.format(FEWEST_SOLOS)))
    rows = []
    for person, measured in sorted(by_person.items(), key=lambda item: -len(item[1])):
        if len(measured) < FEWEST_SOLOS:
            continue
        rows.append((person, len(measured),
                     median([each['density'] for each in measured]),
                     median([each['steps'] for each in measured]),
                     median([each['range'] for each in measured]),
                     median([each['space'] for each in measured]),
                     median([each['dynamics'] for each in measured])))
    lines += table(heading=('performer', 'solos', 'notes a beat', 'steps', 'range', 'space', 'loudness spread'), rows=rows)
    return lines


# The Billboard chord annotations.


def chord_degree(*, chord, tonic):
    """Return a Billboard chord as its degree in the key (a Roman numeral, lower case when minor), or None for no chord."""
    match = re.match(r'([A-G])([b#]*):([^/ ]*)', chord)
    if match is None:
        return None
    root = (NOTE_CLASSES[match.group(1)] + match.group(2).count('#') - match.group(2).count('b')) % PITCH_CLASSES
    name = DEGREE_NAMES[(root - tonic) % PITCH_CLASSES]
    quality = match.group(3)
    return name.lower() if quality.startswith(MINOR_QUALITIES) else name


def tonic_of(text):
    match = re.match(r'([A-G])([b#]*)', text.strip())
    return (NOTE_CLASSES[match.group(1)] + match.group(2).count('#') - match.group(2).count('b')) % PITCH_CLASSES if match else None


def is_section_label(part):
    """Return whether a part of a Billboard line names a section, a lower-case word such as verse or pre-chorus, rather than a
    letter, the bars, or an instrument in brackets."""
    return re.fullmatch(r'[a-z][a-z-]*', part) is not None and part != 'silence'


def billboard_song(path):
    """Return a Billboard song as its tonic, its sections in order (their labels) and its chords bar by bar as degrees, read
    from its annotation file."""
    tonic = None
    sections = []
    bars = []
    for line in path.read_text(errors='replace').splitlines():
        if line.startswith('# tonic:'):
            tonic = tonic_of(line.split(':', 1)[1])
            continue
        if line.startswith('#') or '\t' not in line or tonic is None:
            continue
        _, content = line.split('\t', 1)
        sections += [part.strip() for part in content.split(',') if is_section_label(part.strip())]
        for bar in re.findall(r'\|([^|]*)', content):
            chords = [chord_degree(chord=chord, tonic=tonic) for chord in bar.split()]
            chords = [chord for chord in chords if chord]
            if chords:
                bars.append(chords)
    return tonic, sections, bars


def billboard_years(index):
    """Return each Billboard song's chart year by its folder's number, from the dataset's index."""
    years = {}
    with index.open(newline='') as handle:
        for row in csv.DictReader(handle):
            if row.get('title') and row.get('chart_date'):
                years[row['id'].zfill(4)] = int(row['chart_date'][:4])
    return years


def study_billboard():
    folder = ROOT / 'billboard'
    index = folder / 'billboard-2.0-index.csv'
    if not index.exists():
        return []
    years = billboard_years(index)
    by_decade = defaultdict(lambda: {'songs': 0, 'chords': Counter(), 'motions': Counter(), 'solo': 0, 'bridge': 0, 'prechorus': 0, 'minor': 0, 'changes': [],
                                     'solo_place': []})
    skipped = 0
    for path in sorted(folder.rglob('salami_chords.txt')):
        year = years.get(path.parent.name.zfill(4))
        try:
            tonic, sections, bars = billboard_song(path)
        except Exception:
            skipped += 1
            continue
        if year is None or not bars:
            continue
        decade = by_decade[year // DECADE * DECADE]
        decade['songs'] += 1
        flat = [chord for bar in bars for chord in bar]
        decade['chords'].update(set(flat))
        roots = [DEGREE_INDEX[chord.lower()] for chord in flat]
        decade['motions'].update(DEGREE_NAMES[(later - earlier) % PITCH_CLASSES] for earlier, later in zip(roots, roots[1:]) if later != earlier)
        decade['changes'].append(len(flat) / len(bars))
        decade['minor'] += flat.count('i') > flat.count('I')
        decade['bridge'] += 'bridge' in sections
        decade['prechorus'] += 'pre-chorus' in sections
        soloed = [index for index, section in enumerate(sections) if section in SOLO_SECTIONS]
        if soloed:
            decade['solo'] += 1
            decade['solo_place'].append(soloed[0] / max(1, len(sections) - 1))
    lines = [HEADING.format(name='McGill Billboard: chart songs by decade'), SKIPPED.format(count=skipped)]
    rows = []
    for decade, found in sorted(by_decade.items()):
        songs = found['songs']
        share = lambda count: round(count / songs, 2)
        rows.append(('{}s'.format(decade), songs, share(found['solo']), median(found['solo_place']), share(found['bridge']), share(found['prechorus']), share(found['minor']),
                     median(found['changes']), JOIN.join('{} {}'.format(name, share(count)) for name, count in found['chords'].most_common(7)),
                     JOIN.join('up {} {}'.format(name, count) for name, count in found['motions'].most_common(4))))
    lines += table(heading=('decade', 'songs', 'with a solo or instrumental', 'where the first comes', 'with a bridge', 'with a pre-chorus', 'mostly minor',
                            'chords a bar', 'songs using each chord', 'root moves'), rows=rows)
    return lines


# The rock corpus.


def expanded_rules(text):
    """Return a rock corpus harmony file's song as its chord symbols in order: its rules expanded from the line that starts S:,
    each $Name replaced by its rule and *n repeating what comes before it."""
    rules = {}
    for line in text.splitlines():
        line = line.split('%', 1)[0].strip()
        match = re.match(r'(\w+):\s*(.*)', line)
        if match:
            rules[match.group(1)] = match.group(2)

    def expand(body, depth=0):
        if depth > 20:
            return []
        tokens = []
        for token in body.replace('|', ' ').split():
            count = 1
            if '*' in token:
                token, _, times = token.partition('*')
                count = int(times) if times.isdigit() else 1
            if token.startswith('$'):
                tokens += expand(rules.get(token[1:], ''), depth + 1) * count
            elif token.startswith('[') or token in ('R', '.', '..'):
                continue
            else:
                tokens += [token] * count
        return tokens
    return expand(rules.get('S', ''))


def numeral_root(symbol):
    match = re.match(r'(b|#)?(VII|VI|V|IV|III|II|I|vii|vi|v|iv|iii|ii|i)', symbol)
    return (match.group(1) or '') + match.group(2) if match else None


def study_rock_corpus():
    folder = ROOT / 'rock-corpus'
    files = sorted(folder.rglob('*_tdc.har'))
    if not files:
        return []
    chords = Counter()
    songs = 0
    before_tonic = Counter()
    for path in files:
        symbols = [numeral_root(symbol) for symbol in expanded_rules(path.read_text(errors='replace'))]
        symbols = [symbol for symbol in symbols if symbol]
        if not symbols:
            continue
        songs += 1
        chords.update(set(symbols))
        before_tonic.update(earlier for earlier, later in zip(symbols, symbols[1:]) if later in ('I', 'i') and earlier not in ('I', 'i'))
    lines = [HEADING.format(name="de Clercq and Temperley's rock corpus: {} songs (Trevor de Clercq's analyses)".format(songs))]
    lines.append('- songs using each chord: ' + JOIN.join('{} {}'.format(name, round(count / songs, 2)) for name, count in chords.most_common(12)))
    lines.append('- the chord before the tonic: ' + JOIN.join(COUNT.format(name=name, count=count) for name, count in before_tonic.most_common(8)))
    return lines


# The Groove MIDI drums.


def drum_measures(path):
    """Return one drum performance's measures: notes a beat, the share of snare hits that are ghosts, the swing of its eighths
    (the offbeat eighth's place within the beat, 0.5 straight and 0.67 a full triplet swing), the spread of its velocities and
    the share of hits on the ride rather than the hats."""
    song = mido.MidiFile(str(path))
    ticks = song.ticks_per_beat
    time = 0
    hits = []
    for message in mido.merge_tracks(song.tracks):
        time += message.time
        if message.type == 'note_on' and message.velocity > 0:
            hits.append((time / ticks, message.note, message.velocity))
    if len(hits) < 8:
        return None
    length = max(hit[0] for hit in hits) or 1
    snares = [velocity for _, note, velocity in hits if note in SNARES]
    offbeats = [beat % 1 for beat, note, _ in hits if note in HATS | RIDES and 0.35 < beat % 1 < 0.8]
    timekeeping = [note for _, note, _ in hits if note in HATS | RIDES]
    velocities = [velocity for _, _, velocity in hits]
    return {'density': len(hits) / length, 'ghosts': sum(1 for velocity in snares if velocity < GHOST_VELOCITY) / len(snares) if snares else 0.0,
            'swing': statistics.median(offbeats) if offbeats else None, 'velocity': statistics.pstdev(velocities),
            'ride': sum(1 for note in timekeeping if note in RIDES) / len(timekeeping) if timekeeping else 0.0}


def study_drums():
    folder = ROOT / 'groove-midi' / 'groove'
    info = folder / 'info.csv'
    if not info.exists():
        return []
    by_style = defaultdict(list)
    by_drummer = defaultdict(list)
    fills = Counter()
    tempos = defaultdict(list)
    skipped = 0
    with info.open(newline='') as handle:
        for row in csv.DictReader(handle):
            style = row['style'].split('/')[0]
            if row['beat_type'] == 'fill':
                fills[style] += 1
                continue
            try:
                measured = drum_measures(folder / row['midi_filename'])
            except Exception:
                skipped += 1
                continue
            if measured is None:
                continue
            by_style[style].append(measured)
            by_drummer[row['drummer']].append(measured)
            tempos[style].append(float(row['bpm']))
    lines = [HEADING.format(name='Groove MIDI: drums played by people, by style'), SKIPPED.format(count=skipped)]
    rows = []
    for style, measured in sorted(by_style.items(), key=lambda item: -len(item[1])):
        swings = [each['swing'] for each in measured if each['swing'] is not None]
        rows.append((style, len(measured), fills[style], median(tempos[style]), median([each['density'] for each in measured]),
                     median([each['ghosts'] for each in measured]),
                     median(swings),
                     median([each['velocity'] for each in measured]), median([each['ride'] for each in measured])))
    lines += table(heading=('style', 'beats', 'fills', 'tempo', 'hits a beat', 'snare ghosts', 'offbeat place', 'velocity spread', 'ride share'), rows=rows)
    lines.append(SUBHEADING.format(name='By drummer'))
    rows = []
    for drummer, measured in sorted(by_drummer.items()):
        swings = [each['swing'] for each in measured if each['swing'] is not None]
        rows.append((drummer, len(measured), median([each['density'] for each in measured]), median([each['ghosts'] for each in measured]), median(swings),
                     median([each['velocity'] for each in measured]), median([each['ride'] for each in measured])))
    lines += table(heading=('drummer', 'beats', 'hits a beat', 'snare ghosts', 'offbeat place', 'velocity spread', 'ride share'), rows=rows)
    return lines


def main():
    for study in (study_jazz, study_billboard, study_rock_corpus, study_drums):
        for line in study():
            print(line)
        sys.stdout.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())
