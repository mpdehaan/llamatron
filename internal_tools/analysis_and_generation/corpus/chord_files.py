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


"""Reading the chord files of the research datasets: a song of the chart chord annotations as its key, its chords by degree and
its sections, the index of its years, and a rock corpus file's rules written out as numerals. The corpus readers use these;
the study that printed tables of them is gone."""

import csv
import re

PITCH_CLASSES = 12
NOTE_CLASSES = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
DEGREE_NAMES = ('I', 'bII', 'II', 'bIII', 'III', 'IV', 'bV', 'V', 'bVI', 'VI', 'bVII', 'VII')
DEGREE_INDEX = {name.lower(): place for place, name in enumerate(DEGREE_NAMES)}
MINOR_QUALITIES = ('min', 'min7', 'min9', 'min11', 'minmaj7', 'hdim7', 'dim', 'dim7')
SOLO_SECTIONS = ('solo', 'instrumental', 'interlude')
DECADE = 10


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
