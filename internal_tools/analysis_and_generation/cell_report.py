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

"""Report what the cells taken from Lakh's clean subset teach (internal_tools/analysis_and_generation/cell_report.sh), as
Markdown: how few bars of the kick, the snare, the timekeeper, the bass and the chord part cover most songs, what the bass plays
of its chord by its place in the bar, how much of the difference between songs the artist explains beside what shuffled artists
would, and, with --melody, how often a melody's notes are chord tones and how it moves in the public-domain lead sheets, which
may be read whole. Run extract_cells.sh first. Development only.

    internal_tools/analysis_and_generation/cell_report.sh > cells.md
    internal_tools/analysis_and_generation/cell_report.sh --melody 150
"""

import argparse
import bisect
import collections
import json
import pathlib
import random
import statistics
import sys

from corpus.cells import FIFTH, OTHER, ROOT, SEVENTH, STRAIGHT, THIRD, TRIPLET, UNKNOWN

WRITTEN = pathlib.Path(__file__).resolve().parent.parent.parent / '.corpus' / 'tables' / 'lakh-cells.jsonl'
NOT_EXTRACTED = 'no cells at {path}: run extract_cells.sh first'
MELODY_HELP = 'also measure this many lead sheets of each public-domain source (slow: each is parsed)'
PARTS = ('kick', 'snare', 'time', 'kit', 'bass_rhythm', 'bass', 'chords')
SHOWN = 6
HALF = 0.5
MOST = 0.8
FEWEST_SONGS = 8
FEWEST_VALUES = 5
SHUFFLES = 20
SEED = 5
PLACES = ('beat 1', 'beat 3', 'beats 2 and 4', 'eighths between', 'sixteenths between')
BASS_TONES = (ROOT, THIRD, FIFTH, SEVENTH, OTHER)
# How a bar is drawn in the report, a step a character, a space between beats: a hit, a rest, or a bass tone's first letter.
DRAWN_HIT = 'x'
DRAWN_REST = '.'
BEAT_GAP = ' '
VOICE_GAP = ' | '
MELODY_PLACES = ('beat 1', 'other beats', 'off the beat')
MELODY_TONES = ('root', 'third', 'fifth', 'seventh', 'other')
MOTIONS = ('same', 'step', 'third', 'leap')
MINOR_KINDS = ('minor', 'diminished', 'half')
HEADING = '\n## {name}\n'
COVERAGE = '- {part}, {grid}: {songs} songs, {distinct} different bars; {half} cover half the songs, {most} cover 80%'
CELL = '  - {share:.1f}%  `{cell}`'
TONE_ROW = '- {place}: {tones}; {notes} notes, {unclear:.0f}% under no clear chord and left out'
SHARE = '{name} {share:.0f}%'
ARTIST_ROW = '- {name}: the artist explains {real:.0f}% (shuffled artists {fake:.0f}%)'
JOIN = ', '
SUCCESS = 0


def as_tuples(value):
    """Return what JSON read as lists as tuples, all the way down, so that a bar can be counted."""
    return tuple(as_tuples(each) for each in value) if isinstance(value, list) else value


def rows_read():
    """Return every song's cells, each bar a tuple as it was written."""
    if not WRITTEN.exists():
        raise SystemExit(NOT_EXTRACTED.format(path=WRITTEN))
    with WRITTEN.open() as handle:
        rows = [json.loads(line) for line in handle]
    return [{key: as_tuples(value) if key in PARTS else value for key, value in row.items()} for row in rows]


def drawn_step(step):
    if step is None or step is False:
        return DRAWN_REST
    return DRAWN_HIT if step is True else step[0]


def drawn(cell):
    """Return a bar drawn for reading, four steps or three to a beat; a kit's three voices side by side."""
    if cell and isinstance(cell[0], tuple):
        return VOICE_GAP.join(drawn(voice) for voice in cell)
    beat = len(cell) // 4
    return BEAT_GAP.join(''.join(drawn_step(step) for step in cell[start:start + beat]) for start in range(0, len(cell), beat))


def covering(*, counts, share):
    """Return how many of the commonest values it takes to hold a share of them all."""
    total = sum(counts.values())
    held = 0
    for number, (_, count) in enumerate(counts.most_common(), 1):
        held += count
        if held >= share * total:
            return number
    return len(counts)


def coverage_lines(*, rows, part, grid):
    counts = collections.Counter(row[part] for row in rows if row['grid'] == grid and row.get(part))
    total = sum(counts.values())
    lines = [COVERAGE.format(part=part, grid=grid, songs=total, distinct=len(counts), half=covering(counts=counts, share=HALF), most=covering(counts=counts, share=MOST))]
    return lines + [CELL.format(share=100 * count / total, cell=drawn(cell)) for cell, count in counts.most_common(SHOWN)]


def place_of_step(step):
    if step == 0:
        return PLACES[0]
    if step == STRAIGHT // 2:
        return PLACES[1]
    if step % (STRAIGHT // 4) == 0:
        return PLACES[2]
    return PLACES[3] if step % 2 == 0 else PLACES[4]


def bass_tone_lines(rows):
    """Return what the bass plays of its chord by its place in the bar, over the songs on a grid of sixteenths."""
    tally = collections.Counter()
    for row in rows:
        if row['grid'] != STRAIGHT:
            continue
        for tone, counts in row.get('bass_tones', {}).items():
            for step, count in enumerate(counts):
                tally[(place_of_step(step), tone)] += count
    lines = []
    for place in PLACES:
        notes = sum(count for (where, _), count in tally.items() if where == place)
        clear = notes - tally[(place, UNKNOWN)]
        tones = JOIN.join(SHARE.format(name=tone, share=100 * tally[(place, tone)] / clear) for tone in BASS_TONES)
        lines.append(TONE_ROW.format(place=place, tones=tones, notes=notes, unclear=100 * tally[(place, UNKNOWN)] / notes))
    return lines


def hits_a_bar(*, row, part):
    cell = row.get(part)
    return None if not cell else sum(step is not None and step is not False for step in cell) * STRAIGHT / row['grid']


FEATURES = {
    'tempo': lambda row: row['tempo'],
    'triplet feel': lambda row: float(row['grid'] == TRIPLET),
    'kick hits a bar': lambda row: hits_a_bar(row=row, part='kick'),
    'timekeeper hits a bar': lambda row: hits_a_bar(row=row, part='time'),
    'bass notes a bar': lambda row: hits_a_bar(row=row, part='bass_rhythm'),
    'chord hits a bar': lambda row: hits_a_bar(row=row, part='chords'),
    'share of minor chords': lambda row: row.get('minor'),
    'share of chords with no third': lambda row: row.get('open'),
    'lead notes a bar': lambda row: row.get('lead_starts'),
    'how often the kit repeats its bar': lambda row: row.get('kit_share'),
}


def explained(groups):
    """Return the share of the values' spread that lies between the groups, not inside them."""
    values = [value for group in groups for value in group]
    mean = statistics.fmean(values)
    total = sum((value - mean) ** 2 for value in values)
    return sum(len(group) * (statistics.fmean(group) - mean) ** 2 for group in groups) / total if total else 0.0


def shuffled(*, groups, chooser):
    values = [value for group in groups for value in group]
    chooser.shuffle(values)
    sizes = iter(values)
    return [[next(sizes) for _ in group] for group in groups]


def artist_lines(rows):
    """Return how much of each feature's spread the artist explains, beside what the same songs under shuffled artists give."""
    by_artist = collections.defaultdict(list)
    for row in rows:
        by_artist[row['artist']].append(row)
    artists = [found for found in by_artist.values() if len(found) >= FEWEST_SONGS]
    chooser = random.Random(SEED)
    lines = []
    for name, feature in FEATURES.items():
        groups = [[feature(row) for row in found if feature(row) is not None] for found in artists]
        groups = [group for group in groups if len(group) >= FEWEST_VALUES]
        fake = statistics.fmean(explained(shuffled(groups=groups, chooser=chooser)) for _ in range(SHUFFLES))
        lines.append(ARTIST_ROW.format(name=name, real=100 * explained(groups), fake=100 * fake))
    return lines


def melody_tone(*, pitch, chord):
    _, root, kind = chord
    interval = (pitch - root) % 12
    third = 3 if kind.startswith(MINOR_KINDS) else 4
    return {0: 'root', third: 'third', 7: 'fifth', 10: 'seventh', 11: 'seventh'}.get(interval, 'other')


def melody_lines(*, pieces):
    """Return, for lead sheets read whole, what a melody's notes are of their chords by place in the bar, and how it moves."""
    tones = collections.Counter()
    motions = collections.Counter()
    for piece in pieces:
        if not piece.chords or not piece.notes:
            continue
        starts = [chord[0] for chord in piece.chords]
        notes = sorted(piece.notes, key=lambda note: note.start)
        for before, note in zip([None] + notes, notes):
            chord = bisect.bisect_right(starts, note.start) - 1
            if chord >= 0:
                where = note.start % piece.beats_per_bar
                place = MELODY_PLACES[0] if where == 0 else MELODY_PLACES[1] if where % 1 == 0 else MELODY_PLACES[2]
                tones[(place, melody_tone(pitch=note.pitch, chord=piece.chords[chord]))] += 1
            if before is not None:
                gap = abs(note.pitch - before.pitch)
                motions[MOTIONS[0] if gap == 0 else MOTIONS[1] if gap <= 2 else MOTIONS[2] if gap <= 4 else MOTIONS[3]] += 1
    lines = []
    for place in MELODY_PLACES:
        total = sum(count for (where, _), count in tones.items() if where == place)
        lines.append('- {}: {}; {} notes'.format(place, JOIN.join(SHARE.format(name=tone, share=100 * tones[(place, tone)] / total) for tone in MELODY_TONES), total))
    total = sum(motions.values())
    return lines + ['- from one note to the next: ' + JOIN.join(SHARE.format(name=motion, share=100 * motions[motion] / total) for motion in MOTIONS)]


def main(*, argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--melody', type=int, help=MELODY_HELP)
    arguments = parser.parse_args(argv)
    rows = rows_read()
    print(HEADING.format(name='How few bars cover most songs ({} songs, {} artists)'.format(len(rows), len({row['artist'] for row in rows}))))
    for grid in (STRAIGHT, TRIPLET):
        for part in PARTS:
            print('\n'.join(coverage_lines(rows=rows, part=part, grid=grid)))
    print(HEADING.format(name='What the bass plays of its chord, by its place in the bar'))
    print('\n'.join(bass_tone_lines(rows)))
    print(HEADING.format(name='How much the artist explains (artists with {} songs or more)'.format(FEWEST_SONGS)))
    print('\n'.join(artist_lines(rows)))
    if arguments.melody:
        from corpus.readers import read_anthology, read_openewld
        for name, reader in (('OpenEWLD', read_openewld), ('the Public Domain Song Anthology', read_anthology)):
            print(HEADING.format(name='A melody against its chords: ' + name))
            print('\n'.join(melody_lines(pieces=reader(limit=arguments.melody))))
    return SUCCESS


if __name__ == '__main__':
    sys.exit(main())
