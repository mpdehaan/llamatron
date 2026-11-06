# llamatron: a Python language and framework for producing MIDI clips.
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

"""Write the first versions of the demo songs in examples/, from the tune data below.

Run it from the repository root with: .venv/bin/python test/demo_sources/make_demos.py

It overwrites every demo, including any changes made to them by hand since, so it's only for
starting again. test/test_demos.py also runs it into a temporary folder, to check the tune data
against its sources. The tunes are written here as notes, taken from the transcriptions named in each
demo, except for The Entertainer, which is read from entertainer.mid next to this file: the
Mutopia Project's public domain typesetting, kept here with its LilyPond source so that nothing
has to be downloaded again. Nothing here uses the network.
"""
import collections
import os
import re
import sys
from fractions import Fraction as F
from pathlib import Path

import mido

from llamatron.scale import ScaleType

# The demos are written with durations, as they were first written, and gate_conversion, in the
# test folder above this one, turns them into gates.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from gate_conversion import song_to_gates  # noqa: E402
from llamatron.note import SEMITONES_ABOVE_C
from llamatron.composition.file_format import PATTERN_ROWS, TOGGLE_ROWS
from llamatron.song_writer import dump_song
from llamatron.tui.pages import SCALE_PAGES

SOURCES = os.path.dirname(os.path.abspath(__file__))
# Half steps above C for each note name, from the note names llamatron defines.
PCS = SEMITONES_ABOVE_C


def midi(name):
    """MIDI number of a note named as Live shows it, so C3 is 60."""
    match = re.fullmatch(r'([A-G][#b]?)(-?\d+)', name)
    return 12 * (int(match[2]) + 2) + PCS[match[1]]


def place(number, root, kind, prefer='#'):
    """Return (degree, accidental, octave) that plays a MIDI number in a scale."""
    steps = ScaleType[kind.upper()].value
    r = PCS[root]
    octave, rel = divmod(number - r, 12)
    octave -= 2
    if rel in steps:
        return steps.index(rel) + 1, None, octave
    if prefer == 'b' and (rel + 1) % 12 in steps:
        if rel + 1 == 12:
            return 1, 'b', octave + 1
        return steps.index(rel + 1) + 1, 'b', octave
    return steps.index(rel - 1) + 1, '#', octave


def text_length(value):
    value = F(value)
    return value.numerator if value.denominator == 1 else f'{value.numerator}/{value.denominator}'


def pattern(steps, root=None, kind=None, drum=False, prefer='#', **settings):
    """Build a pattern from steps of (note, duration) or (note, duration, {row: value}).

    A note is a name like 'A3', a MIDI number, or None for a rest. The pattern is written with
    durations, as the demos were first written, and song_to_gates turns it into gates.
    """
    written_rows = ['duration', *PATTERN_ROWS]
    rows = {row: [] for row in written_rows}
    for step in steps:
        note, duration = step[0], step[1]
        extra = step[2] if len(step) > 2 else {}
        degree = accidental = octave = None
        if note is not None:
            number = midi(note) if isinstance(note, str) else note
            if drum:
                letter = note[0]
                accidental = '#' if note[1] == '#' else None
                degree, octave = letter, number // 12 - 2
            else:
                degree, accidental, octave = place(number, root, kind, prefer)
        values = {'degree': degree, 'duration': text_length(duration), 'accidental': accidental, 'octave': octave, **extra}
        for row in written_rows:
            rows[row].append(values.get(row))
    result = {'steps': len(steps)}
    if drum:
        result['drum'] = True
    result.update(settings)
    for row, values in rows.items():
        if row in TOGGLE_ROWS:
            if any(values):
                result[row] = [bool(value) for value in values]
        elif any(value is not None for value in values):
            result[row] = values
    return result


def with_rows(steps, **rows):
    """Add a row's value to every step, from a list or one value for all."""
    result = []
    for index, step in enumerate(steps):
        extra = dict(step[2]) if len(step) > 2 else {}
        for row, value in rows.items():
            extra[row] = value[index % len(value)] if isinstance(value, list) else value
        result.append((step[0], step[1], extra))
    return result


# What to keep in mind when changing each demo, which goes at the end of its description.
EDITING = {
    'scale_demo': [
        'Keep it to scale runs only, one scene per distinct scale, in the order of the scale',
        'picker (SCALE_PAGES in src/llamatron/tui/pages.py). A scale added to llamatron needs a',
        'scene here, and a new size of scale needs its own run pattern.',
    ],
    'arpeggiator_demo': [
        'Keep one arpeggiator per chain, with the chain named after it, and scene names that say',
        'what changed. Up to about 30 scenes is fine. The single D at the end of the chords is',
        'there on purpose, to show what offsets and octave ranges do to a single note.',
    ],
    'ratchet_demo': [
        'Scenes that use the pattern rows start with "Ratchet", and scenes that use a chain start',
        'with "AutoRatchet". "AutoRatchet 2, same as Ratchet 2" sounds the same as "Ratchet 2" on',
        'purpose. Avoid religious tunes here, which is why it uses Ode to Joy.',
    ],
    'chain_demo': [
        'Keep it to one track, with chains doing the work. It should stay musical, moving from a',
        'plain tune to something like happy metal or synthwave by the end. Morphing and',
        'directions have their own demos, so they don\'t belong here.',
    ],
    'grab_demo': [
        'The voices take turns, round robin, as someone would program them by hand. The muted',
        'track has SILENT in its name, which a test checks. A voice\'s notes match the melody\'s, so',
        'it still plays the tune without its grab.',
    ],
    'arrangement_demo': [
        'The point is how few patterns it needs, so add parts by reusing the four note patterns',
        'with a track setting, a chain or a grab, rather than with new note patterns.',
    ],
    'morph_demo': [
        'Every pattern is 16 sixteenth notes, so that any two can morph. It should sound like',
        'slowly evolving minimal techno.',
    ],
    'direction_demo': [
        'Two pairs of scenes sound alike on purpose: a direction set on the pattern and the same',
        'one on the clip, and a clip\'s forward overriding a pendulum pattern.',
    ],
    'basic_classical_demo': [
        'Keep it to patterns, tracks and scenes, with no chains, grabs or ratchets. Pattern names',
        'say what each part does. It was meant to be Ravel\'s Bolero, but no transcription of its',
        'melody could be checked, so it\'s the Canon instead until one can.',
    ],
    'entertainer_demo': [
        'This is the long piece, for getting a feel of a full composition, so keep every bar and',
        'the four-bar phrases that line up with the sheet music. The patterns were cut from',
        'test/demo_sources/entertainer.mid by test/demo_sources/make_demos.py, which overwrites',
        'changes made by hand.',
    ],
}


# Where write() puts the demos. main() sets it, so that a test can write them somewhere else.
OUTPUT = 'examples'


def write(file_name, header, song):
    """Write a demo, with its header as the description, followed by what to keep in mind."""
    name = os.path.splitext(file_name)[0]
    path = os.path.join(OUTPUT, file_name)
    lines = [*header, '', 'When changing this demo:', *EDITING[name]]
    description = '\n'.join(lines) + '\n'
    song = {'title': song.pop('title'), **({'author': song.pop('author')} if 'author' in song else {}),
            'description': description, **song}
    with open(path, 'w') as file:
        file.write(dump_song(song_to_gates(song)))


def song(title, tempo, scale, scales, patterns, tracks, scenes, **sections):
    data = {'title': title, 'tempo': tempo, 'scale': scale, 'scales': scales, 'patterns': patterns, 'tracks': tracks}
    data.update(sections)
    data['scenes'] = scenes
    return data


def title_case(kind):
    return ' '.join(word.capitalize() for word in kind.split('_'))


# ---------------------------------------------------------------------------------------------
# Scales: every distinct scale in the picker's order, run up and down an octave from D.

def scale_demo():
    order = [kind for _, columns in SCALE_PAGES for column in columns for _, kinds in column for kind in kinds]
    distinct = []
    for kind in order:
        if all(ScaleType[kind.upper()].value != ScaleType[other.upper()].value for other in distinct):
            distinct.append(kind)
    scales, scenes, patterns = {}, [], {}
    for kind in distinct:
        value = ScaleType[kind.upper()].value
        aliases = [name.lower() for name, member in ScaleType.__members__.items()
                   if member.value == value and name.lower() != kind]
        name = 'D ' + ' / '.join(title_case(each) for each in [kind, *aliases])
        scales[name] = {'root': 'D', 'type': kind}
        size = len(value)
        run = f'run_{size}_notes'
        if run not in patterns:
            degrees = list(range(1, size + 2)) + list(range(size, 0, -1))
            patterns[run] = {
                'steps': len(degrees), 'degree': degrees,
                'duration': ['1/8'] * (len(degrees) - 1) + ['1/4'], 'octave': [3] * len(degrees),
            }
        scenes.append({'name': name, 'scale': name, 'tracks': {'scale': {'pattern': run}}})
    patterns = dict(sorted(patterns.items(), key=lambda item: item[1]['steps']))
    first = next(iter(scales))
    write('scale_demo.yml', [
        'Scale demo: every scale llamatron knows, run up an octave and back down from D.',
        'Run it with: llamatron examples/scale_demo.yml --to ableton --replace',
        '',
        'Each scene sets its own scale and is named after it, so Live\'s scene names say which scale',
        'each one plays, and each clip is named after the run it plays. Launch them one at a time to compare.',
        'The scales come in the order the scale picker shows them. Names that are the same scale',
        '(Major and Ionian, Minor, Aeolian and Natural Minor) share one scene.',
        '',
        'There\'s one pattern for each size of scale, because a run of 1 to 8 only covers an octave',
        'in a seven-note scale. A degree past the top of the scale wraps up an octave, so each run',
        'goes from degree 1 up to the next octave\'s 1 and back. All of it is one track.',
    ], song('Scale demo', 120, first, scales, patterns, {'scale': {}}, scenes))


# ---------------------------------------------------------------------------------------------
# Drunken Sailor, for the arpeggiator. From the flutetunes.com transcription, D Dorian, 112 BPM,
# an octave lower than written for flute.

SAILOR = [
    ('A3', '1/8'), ('A3', '1/16'), ('A3', '1/16'), ('A3', '1/8'), ('A3', '1/16'), ('A3', '1/16'),
    ('A3', '1/8'), ('D3', '1/8'), ('F3', '1/8'), ('A3', '1/8'),
    ('G3', '1/8'), ('G3', '1/16'), ('G3', '1/16'), ('G3', '1/8'), ('G3', '1/16'), ('G3', '1/16'),
    ('G3', '1/8'), ('C3', '1/8'), ('E3', '1/8'), ('G3', '1/8'),
    ('A3', '1/8'), ('A3', '1/16'), ('A3', '1/16'), ('A3', '1/8'), ('A3', '1/16'), ('A3', '1/16'),
    ('A3', '1/8'), ('B3', '1/8'), ('C4', '1/8'), ('D4', '1/8'),
    ('C4', '1/8'), ('A3', '1/8'), ('G3', '1/8'), ('E3', '1/8'), ('D3', '1/4'), ('D3', '1/4'),
]
SAILOR_CHORDS = [
    ('D2', 1, {'chord': 3}), ('C2', 1, {'chord': 3}), ('D2', 1, {'chord': 3}),
    ('C2', '1/2', {'chord': 3}), ('D2', '1/2'),
]


def arpeggiator_demo():
    root, kind = 'D', 'dorian'
    patterns = {
        'chords': pattern(SAILOR_CHORDS, root, kind),
        'tune': pattern(with_rows(SAILOR, velocity=90), root, kind),
    }
    arps = {
        'up_eighths': {'step': '1/8', 'order': 'up'},
        'up_sixteenths': {'step': '1/16', 'order': 'up'},
        'up_triplets': {'step': '1/12', 'order': 'up'},
        'up_thirty_seconds': {'step': '1/32', 'order': 'up'},
        'down': {'step': '1/16', 'order': 'down'},
        'up_down': {'step': '1/16', 'order': 'up_down'},
        'down_up': {'step': '1/16', 'order': 'down_up'},
        'random_seed_1': {'step': '1/16', 'order': 'random', 'seed': 1},
        'random_seed_2': {'step': '1/16', 'order': 'random', 'seed': 2},
        'two_octaves_after_chord': {'step': '1/16', 'order': 'up', 'octave_range': 2, 'octave_jump': 'after_chord'},
        'two_octaves_after_each_note': {'step': '1/16', 'order': 'up', 'octave_range': 2, 'octave_jump': 'after_each_note'},
        'three_octaves_up_down': {'step': '1/16', 'order': 'up_down', 'octave_range': 3},
        'four_octaves_fast': {'step': '1/32', 'order': 'up', 'octave_range': 4},
        'offsets_octave_bounce': {'step': '1/16', 'order': 'up', 'offsets': [0, 7]},
        'offsets_neighbors': {'step': '1/16', 'order': 'up', 'offsets': [0, 1, 0, -1]},
        'offsets_silent_steps': {'step': '1/16', 'order': 'up', 'offsets': [0, None, 0, 0, None, 0, None, 0]},
        'offsets_climb': {'step': '1/16', 'order': 'up', 'offsets': [0, 1, 2, 3, 4, 5, 6, 7, 7, 6, 5, 4, 3, 2, 1, 0]},
        'offsets_drop': {'step': '1/16', 'order': 'down', 'offsets': [0, -7]},
        'up_down_two_octaves_thirds': {'step': '1/16', 'order': 'up_down', 'octave_range': 2, 'offsets': [0, 0, 2]},
        'random_three_octaves_each_note': {'step': '1/16', 'order': 'random', 'seed': 3, 'octave_range': 3, 'octave_jump': 'after_each_note'},
        'down_eighths_gaps': {'step': '1/8', 'order': 'down', 'offsets': [0, None, 7, None]},
        'triplets_up_down_two_octaves': {'step': '1/12', 'order': 'up_down', 'octave_range': 2},
        'sparkle': {'step': '1/32', 'order': 'up_down', 'octave_range': 4, 'offsets': [0, 7, None, 2]},
    }
    names = {
        'up_eighths': 'Arp up, 1/8 steps', 'up_sixteenths': 'Arp up, 1/16 steps', 'up_triplets': 'Arp up, 1/12 steps (triplets)',
        'up_thirty_seconds': 'Arp up, 1/32 steps', 'down': 'Order: down', 'up_down': 'Order: up_down', 'down_up': 'Order: down_up',
        'random_seed_1': 'Order: random, seed 1', 'random_seed_2': 'Order: random, seed 2',
        'two_octaves_after_chord': 'Octave range 2, jump after_chord', 'two_octaves_after_each_note': 'Octave range 2, jump after_each_note',
        'three_octaves_up_down': 'Octave range 3, up_down', 'four_octaves_fast': 'Octave range 4, 1/32 steps',
        'offsets_octave_bounce': 'Offsets 0 7 (octave bounce)', 'offsets_neighbors': 'Offsets 0 1 0 -1 (neighbors)',
        'offsets_silent_steps': 'Offsets with silent steps', 'offsets_climb': 'Offsets climbing 0 to 7 and back',
        'offsets_drop': 'Offsets 0 -7, order down', 'up_down_two_octaves_thirds': 'Combined: up_down, 2 octaves, thirds',
        'random_three_octaves_each_note': 'Combined: random, 3 octaves, each note',
        'down_eighths_gaps': 'Combined: down, 1/8, octave gaps', 'triplets_up_down_two_octaves': 'Combined: triplets up_down 2 octaves',
        'sparkle': 'Combined: 1/32 up_down 4 octaves offsets',
    }
    chains = {name: [{'arp': name}] for name in arps}
    scenes = [{'name': 'Chords, no arp', 'tracks': {'chords': {'pattern': 'chords'}, 'tune': {'pattern': 'tune'}}}]
    for name in arps:
        scenes.append({'name': names[name], 'tracks': {
            'chords': {'pattern': 'chords', 'chain': name}, 'tune': {'pattern': 'tune'},
        }})
    write('arpeggiator_demo.yml', [
        'Arpeggiator demo: one chord pattern played through a different arpeggiator in each scene.',
        'Run it with: llamatron examples/arpeggiator_demo.yml --to ableton --replace',
        '',
        'The tune is the verse of What Shall We Do With the Drunken Sailor, a traditional sea shanty,',
        'in D Dorian at 112 BPM as the flutetunes.com transcription has it. The tune track plays it',
        'plainly in every scene for reference, so mute it in Live to hear only the arpeggio.',
        '',
        'The chords pattern is Dm, C, Dm for a whole note each, then C for a half note and a single D.',
        'An arpeggiator plays each chord for the chord\'s full length, so the shorter C gets fewer',
        'notes. A plain arpeggiator leaves the single D alone, but one with offsets or an octave',
        'range arpeggiates it as a chord of one note, which the last half note of each scene shows.',
        '',
        'Each chain holds exactly one arpeggiator with the same name, so a scene\'s chain says what',
        'it demonstrates. The first scenes change one setting at a time, from the step length and',
        'the order to the octave range, the octave jump and the offsets. The last ones combine them.',
    ], song('Arpeggiator demo', 112, 'D Dorian', {'D Dorian': {'root': 'D', 'type': 'dorian'}}, patterns,
            {'chords': {}, 'tune': {}}, scenes, arps=arps, chains=chains))


# ---------------------------------------------------------------------------------------------
# Ode to Joy, for ratchets. From the flutetunes.com transcription, D major at 144 BPM, with every
# note twice as long so that the ratchets have room.

ODE = [('F#3', '1/2')] * 2 + [('G3', '1/2'), ('A3', '1/2'), ('A3', '1/2'), ('G3', '1/2'), ('F#3', '1/2'), ('E3', '1/2'),
                              ('D3', '1/2'), ('D3', '1/2'), ('E3', '1/2'), ('F#3', '1/2'), ('F#3', '3/4'), ('E3', '1/4'), ('E3', 1)]


def ratchet_demo():
    root, kind = 'D', 'major'

    def ode(**rows):
        return pattern(with_rows(ODE, **rows) if rows else ODE, root, kind)

    rested = []
    for note, duration in ODE:
        rested += [(note, F(duration) / 2), (None, F(duration) / 2)]
    patterns = {
        'long_notes': ode(),
        'ratchet_2': ode(ratchet=2),
        'ratchet_3': ode(ratchet=3),
        'ratchet_4': ode(ratchet=4),
        'ratchet_mixed': ode(ratchet=[1, 2, 3, 4]),
        'ratchet_building': ode(ratchet=[1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 4, 4, 6, 8, 16]),
        'ratchet_chords': ode(ratchet=2, chord=3),
        'ratchet_offset_up': ode(ratchet=4, ratchet_offset=1),
        'ratchet_offset_down': ode(ratchet=4, ratchet_offset=-1),
        'ratchet_offset_thirds': ode(ratchet=3, ratchet_offset=2),
        'ratchet_probability': ode(ratchet=4, probability=60),
        'long_notes_with_rests': pattern(rested, root, kind),
        'long_chords': ode(chord=3),
    }
    auto_ratchets = {
        'two': {'counts': [2]},
        'four_three_two_one': {'counts': [4, 3, 2, 1]},
        'every_fourth_note_rolls': {'counts': [1, 1, 1, 4]},
        'one_then_four': {'counts': [1, 4]},
        'three': {'counts': [3]},
        'one_then_three': {'counts': [1, 3]},
    }
    chains = {name: [{'auto_ratchet': name}] for name in auto_ratchets}

    def scene(name, pattern_name, chain=None):
        cell = {'pattern': pattern_name}
        if chain:
            cell['chain'] = chain
        return {'name': name, 'tracks': {'tune': cell}}

    scenes = [
        scene('Long notes', 'long_notes'),
        scene('Ratchet 2', 'ratchet_2'),
        scene('Ratchet 3', 'ratchet_3'),
        scene('Ratchet 4', 'ratchet_4'),
        scene('Ratchet 1 2 3 4, step by step', 'ratchet_mixed'),
        scene('Ratchet building up to 16', 'ratchet_building'),
        scene('Ratchet 2 on chords', 'ratchet_chords'),
        scene('Ratchet offset +1 (climbing)', 'ratchet_offset_up'),
        scene('Ratchet offset -1 (falling)', 'ratchet_offset_down'),
        scene('Ratchet offset +2 (thirds)', 'ratchet_offset_thirds'),
        scene('Ratchet 4 at 60% probability', 'ratchet_probability'),
        scene('AutoRatchet 2, same as Ratchet 2', 'long_notes', 'two'),
        scene('AutoRatchet 4 3 2 1', 'long_notes', 'four_three_two_one'),
        scene('AutoRatchet 1 1 1 4', 'long_notes', 'every_fourth_note_rolls'),
        scene('AutoRatchet 1 4, rests skipped', 'long_notes_with_rests', 'one_then_four'),
        scene('AutoRatchet 3 on chords', 'long_chords', 'three'),
        scene('AutoRatchet 1 3 over Ratchet 2', 'ratchet_2', 'one_then_three'),
        scene('AutoRatchet 2 over Ratchet offset', 'ratchet_offset_up', 'two'),
    ]
    write('ratchet_demo.yml', [
        'Ratchet demo: long notes, and what ratcheting does to them.',
        'Run it with: llamatron examples/ratchet_demo.yml --to ableton --replace',
        '',
        'The tune is the first line of Beethoven\'s Ode to Joy, in D major at 144 BPM as the',
        'flutetunes.com transcription has it, with every note twice as long so it starts slow.',
        '',
        'Scenes named Ratchet use the pattern\'s own Ratchet rows, so each one has its own pattern:',
        'ratchet splits a step into equal notes in the same time, ratchet_offset moves each slice',
        'along the scale, and probability is rolled for each slice. Scenes named AutoRatchet all',
        'use the plain long_notes pattern (or one close to it) and do the chopping in a chain, so',
        'the pattern stays the same and only the chain changes. AutoRatchet cycles through its',
        'counts one note or chord at a time, and rests never use one up. The last two scenes run an',
        'AutoRatchet over a pattern that already ratchets, so it chops the slices again.',
        '',
        'The first AutoRatchet scene sounds the same as Ratchet 2 on purpose: the chain does to the',
        'plain pattern what the Ratchet row does in the pattern itself.',
    ], song('Ratchet demo', 144, 'D Major', {'D Major': {'root': 'D', 'type': 'major'}}, patterns,
            {'tune': {}}, scenes, auto_ratchets=auto_ratchets, chains=chains))


# ---------------------------------------------------------------------------------------------
# Simple Gifts, for chains. From the flutetunes.com transcription, A major at 120 BPM: the first
# strain, with the two-note pickup moved to the front so the pattern loops cleanly.

GIFTS = [
    ('E3', '1/8'), ('E3', '1/8'),
    ('A3', '1/4'), ('A3', '1/8'), ('B3', '1/8'), ('C#4', '1/8'), ('A3', '1/8'), ('C#4', '1/8'), ('D4', '1/8'),
    ('E4', '1/4'), ('E4', '1/8'), ('D4', '1/8'), ('C#4', '1/4'), ('B3', '1/8'), ('A3', '1/8'),
    ('B3', '1/4'), ('B3', '1/4'), ('B3', '1/4'), ('A3', '1/4'),
    ('B3', '1/8'), ('C#4', '1/8'), ('B3', '1/8'), ('G#3', '1/8'), ('E3', '1/4'), ('E3', '1/4'),
    ('A3', '1/4'), ('A3', '1/8'), ('B3', '1/8'), ('C#4', '1/8'), ('A3', '1/8'), ('C#4', '1/8'), ('D4', '1/8'),
    ('E4', '1/4'), ('E4', '1/8'), ('D4', '1/8'), ('C#4', '1/4'), ('B3', '1/8'), ('A3', '1/8'),
    ('B3', '1/4'), ('B3', '1/4'), ('C#4', '1/4'), ('C#4', '1/8'), ('B3', '1/8'),
    ('A3', '1/4'), ('A3', '1/8'), ('B3', '1/8'), ('A3', '1/4'),
]
# One chord a bar: A A E E A A E A, with the pickup on A. Each is in half notes, so that an
# AutoRatchet chops every one into the same note length.
GIFTS_CHANGES = [('A2', '1/4')] + [(root, '1/2') for root in ['A2'] * 4 + ['E2'] * 4 + ['A2'] * 4 + ['E2'] * 2] + [('A2', '1/2'), ('A2', '1/4')]


def chain_demo():
    root, kind = 'A', 'major'
    power = [(note, length, {'chord': 5}) for note, length in GIFTS_CHANGES]
    patterns = {
        'tune': pattern(GIFTS, root, kind),
        'tune_in_triads': pattern(with_rows(GIFTS, chord=3), root, kind),
        'tune_in_power_chords': pattern([(midi(note) - 12, length, {'chord': 5}) for note, length in GIFTS], root, kind),
        'changes_sevenths': pattern([(note, length, {'chord': 7}) for note, length in GIFTS_CHANGES], root, kind),
        'changes_power_chords': pattern([(midi(note) - 12, length, extra) for note, length, extra in power], root, kind),
    }
    arps = {
        'octave_sparkle': {'step': '1/16', 'order': 'up', 'octave_range': 2},
        'trill_in_thirds': {'step': '1/16', 'order': 'up', 'offsets': [0, 2]},
        'triad_up': {'step': '1/16', 'order': 'up'},
        'triad_wide': {'step': '1/16', 'order': 'up_down', 'octave_range': 2},
        'synth_arp': {'step': '1/16', 'order': 'up', 'octave_range': 2, 'octave_jump': 'after_chord'},
        'synth_arp_wide': {'step': '1/16', 'order': 'down_up', 'octave_range': 3},
        'shred_up': {'step': '1/32', 'order': 'up', 'offsets': [0, 2, 4, 7]},
        'shred_down': {'step': '1/32', 'order': 'up', 'offsets': [7, 4, 2, 0]},
        'octave_pedal': {'step': '1/16', 'order': 'up', 'offsets': [0, 0, 7, 0]},
        'answer_a_fifth_up': {'step': '1/32', 'order': 'up', 'offsets': [0, 4]},
    }
    auto_ratchets = {
        'double': {'counts': [2]},
        'chug': {'counts': [4]},
        'chug_with_fills': {'counts': [4, 4, 4, 8]},
        'stutter': {'counts': [1, 1, 1, 1, 1, 1, 1, 3]},
    }
    chains = {
        'octave_sparkle': [{'arp': 'octave_sparkle'}],
        'trill_in_thirds': [{'arp': 'trill_in_thirds'}],
        'double': [{'auto_ratchet': 'double'}],
        'shred': [{'arp': 'shred_up'}],
        'triad_up': [{'arp': 'triad_up'}],
        'triad_wide': [{'arp': 'triad_wide'}],
        'triad_up_then_stutter': [{'arp': 'triad_up'}, {'auto_ratchet': 'stutter'}],
        'synth_arp': [{'arp': 'synth_arp'}],
        'synth_arp_then_stutter': [{'arp': 'synth_arp'}, {'auto_ratchet': 'stutter'}],
        'stutter_then_synth_arp': [{'auto_ratchet': 'stutter'}, {'arp': 'synth_arp'}],
        'synth_arp_then_answer': [{'arp': 'synth_arp'}, {'arp': 'answer_a_fifth_up'}],
        'synth_arp_wide': [{'arp': 'synth_arp_wide'}],
        'chug': [{'auto_ratchet': 'chug'}],
        'chug_with_fills': [{'auto_ratchet': 'chug_with_fills'}],
        'double_then_shred_down': [{'auto_ratchet': 'double'}, {'arp': 'shred_down'}],
        'finale': [{'arp': 'octave_pedal'}, {'auto_ratchet': 'stutter'}],
    }
    plan = [
        ('Tune', 'tune', None),
        ('Tune: octave sparkle', 'tune', 'octave_sparkle'),
        ('Tune: trill in thirds', 'tune', 'trill_in_thirds'),
        ('Tune: doubled', 'tune', 'double'),
        ('Tune: shred up', 'tune', 'shred'),
        ('Hymn: tune in triads', 'tune_in_triads', None),
        ('Hymn: triads arpeggiated', 'tune_in_triads', 'triad_up'),
        ('Hymn: triads two octaves', 'tune_in_triads', 'triad_wide'),
        ('Hymn: arp then stutter', 'tune_in_triads', 'triad_up_then_stutter'),
        ('Synthwave: seventh chords', 'changes_sevenths', None),
        ('Synthwave: arp', 'changes_sevenths', 'synth_arp'),
        ('Synthwave: arp then stutter', 'changes_sevenths', 'synth_arp_then_stutter'),
        ('Synthwave: stutter then arp', 'changes_sevenths', 'stutter_then_synth_arp'),
        ('Synthwave: arp of an arp', 'changes_sevenths', 'synth_arp_then_answer'),
        ('Synthwave: three octaves', 'changes_sevenths', 'synth_arp_wide'),
        ('Metal: power chords', 'changes_power_chords', None),
        ('Metal: chug', 'changes_power_chords', 'chug'),
        ('Metal: chug with fills', 'changes_power_chords', 'chug_with_fills'),
        ('Metal: tune in power chords', 'tune_in_power_chords', None),
        ('Metal: power tune doubled', 'tune_in_power_chords', 'double'),
        ('Metal: double then shred down', 'tune', 'double_then_shred_down'),
        ('Finale: octave pedal, stutter', 'tune_in_power_chords', 'finale'),
    ]
    scenes = []
    for name, pattern_name, chain in plan:
        cell = {'pattern': pattern_name}
        if chain:
            cell['chain'] = chain
        scenes.append({'name': name, 'tracks': {'gifts': cell}})
    write('chain_demo.yml', [
        'Chain demo: one tune on one track, turned from a hymn into synthwave and happy metal by chains.',
        'Run it with: llamatron examples/chain_demo.yml --to ableton --replace',
        '',
        'The tune is the first strain of Simple Gifts, the Shaker song by Joseph Brackett from 1848,',
        'in A major at 120 BPM as the flutetunes.com transcription has it, with its two-note pickup',
        'moved to the front so that the pattern loops. Everything plays on a single track, so a',
        'scene changes only the pattern and the chain. Try a bright synth for the synthwave scenes',
        'and a distorted guitar or saw lead for the metal ones.',
        '',
        'There are only five patterns: the tune, the tune in triads, the tune in power chords, and',
        'the chord changes as seventh chords and as power chords. The changes are written in half',
        'notes, so that an AutoRatchet chops every chord into the same length (4 makes eighths).',
        '',
        'A chain runs its steps in order, and each step works on what the one before made. So',
        '"arp then stutter" ratchets the arpeggio\'s notes, while "stutter then arp" arpeggiates each',
        'ratcheted chord from the start, which sounds different. "Arp of an arp" puts a second',
        'arpeggiator after the first: its offsets turn each single note into a note and a fifth.',
    ], song('Chain demo', 120, 'A Major', {'A Major': {'root': 'A', 'type': 'major'}}, patterns,
            {'gifts': {}}, scenes, arps=arps, auto_ratchets=auto_ratchets, chains=chains))


# ---------------------------------------------------------------------------------------------
# The Wellerman, for grabs and the arrangement demo. From the sung setting with lyrics and chords
# on thesession.org (tune 20383, setting 8), in A minor, raised an octave. The pickup "There" is
# the last note, so the tune loops.

def abc_wellerman():
    """Return the verse and chorus as (MIDI number or None, length) steps."""
    verse = 'A,2 A, A, A,2 C2 E2 E2 E2 E2 F2 D D D2 F F A A E2 E2 E2 A,2 A,2 A,2 C2 E2 E2 E2 E2 E2 D2 C C B,2 A,8'
    chorus = 'A4 A3 F G G E2 E3 E F2 D2 D D F2 A2 E2 E4 A4 A2 G F G E E2 E2 E2 F2 D2 C2 B,2 A,4 z2 E2'

    def read(text):
        steps = []
        for token in text.split():
            match = re.fullmatch(r'([A-Gz])(,?)(\d?)', token)
            length = F(int(match[3] or 1), 8)
            if match[1] == 'z':
                steps.append((None, length))
            else:
                # In ABC, C is middle C, MIDI 60, and a comma moves an octave down.
                number = 60 + PCS[match[1]] - (12 if match[2] else 0)
                steps.append((number + 12, length))
        return steps
    return read(verse), read(chorus)


WELLERMAN_TEMPO = 100
# The chords, one per bar of the transcription, as (root, chord symbol, wholes).
WELLERMAN_VERSE_CHORDS = [('A2', 3, 2), ('D3', 3, 1), ('A2', 3, 1), ('A2', 3, 2), ('E2', 'dom7', 1), ('A2', 3, 1)]
WELLERMAN_CHORUS_CHORDS = [('F2', 3, 1), ('C3', 3, 1), ('D3', 3, 1), ('A2', 3, 1), ('F2', 3, 1), ('C3', 3, 1), ('E2', 'dom7', 1), ('A2', 3, 1)]


def grab_demo():
    root, kind = 'A', 'minor'
    verse, chorus = abc_wellerman()
    voices = 4
    patterns = {}
    for part, tune in (('verse', verse), ('chorus', chorus)):
        patterns[f'melody_{part}'] = pattern(tune, root, kind)
        played, turns = 0, []
        for note, length in tune:
            turns.append(None if note is None else played % voices)
            played += note is not None
        for voice in range(voices):
            steps = [
                (note, length, {'grab': True}) if turn == voice else (None, length)
                for (note, length), turn in zip(tune, turns)
            ]
            patterns[f'voice_{voice + 1}_{part}'] = pattern(steps, root, kind)
    tracks = {'SILENT melody': {'mute': True}, **{f'voice {n}': {} for n in range(1, voices + 1)}}

    def scene(name, part, playing):
        cells = {'SILENT melody': {'pattern': f'melody_{part}'}}
        for n in playing:
            cells[f'voice {n}'] = {'pattern': f'voice_{n}_{part}', 'grab_track': 'SILENT melody'}
        return {'name': name, 'tracks': cells}

    scenes = [
        scene('Verse: SILENT melody only (unmute it)', 'verse', []),
        scene('Chorus: voice 1 alone', 'chorus', [1]),
        scene('Verse: voices 1 and 2', 'verse', [1, 2]),
        scene('Chorus: voices 1 to 3', 'chorus', [1, 2, 3]),
        scene('Verse: all four voices', 'verse', [1, 2, 3, 4]),
        scene('Chorus: all four voices', 'chorus', [1, 2, 3, 4]),
        scene('Verse: voices 2 and 4', 'verse', [2, 4]),
    ]
    write('grab_demo.yml', [
        'Grab demo: four tracks take turns playing a melody that a silent track holds, called hocketing.',
        'Run it with: llamatron examples/grab_demo.yml --to ableton --replace',
        '',
        'The tune is The Wellerman, a New Zealand whaling song from the 19th century, in A minor as',
        'the sung setting on thesession.org (tune 20383, setting 8) has it, an octave higher. No',
        'tempo is known from the original, so 100 BPM is an estimate of how it\'s commonly sung.',
        '',
        'The SILENT melody track plays the verse or the chorus, but it has mute: true, so Live',
        'starts with it switched off. Its clips are still written, so you can switch it on to hear',
        'the tune. The four voice tracks each grab from it, in turn: voice 1 grabs the 1st, 5th and',
        '9th notes, voice 2 the 2nd, 6th and 10th, and so on round, starting again with each verse',
        'or chorus. Each voice has a verse and a chorus pattern, and each copies the melody\'s',
        'durations, with Grab on its own notes and rests on the others\', as you would program it',
        'by hand. Put a different sound on each voice to hear the tune pass between',
        'them. Every voice\'s own notes are the melody\'s too, so it still plays if the grab is',
        'removed, but with the grab, changing a note in melody_verse or melody_chorus changes it for',
        'whichever voice plays it.',
    ], song('Grab demo', WELLERMAN_TEMPO, 'A Minor', {'A Minor': {'root': root, 'type': kind}}, patterns, tracks, scenes))


def arrangement_demo():
    root, kind = 'A', 'minor'
    verse, chorus = abc_wellerman()

    def chords(changes):
        return pattern([(note, length, {'chord': symbol}) for note, symbol, length in changes], root, kind)

    patterns = {
        # The notes: two melody patterns and two chord patterns, which every other part reuses.
        'melody_verse': pattern(verse, root, kind),
        'melody_chorus': pattern(chorus, root, kind),
        'chords_verse': chords(WELLERMAN_VERSE_CHORDS),
        'chords_chorus': chords(WELLERMAN_CHORUS_CHORDS),
        # The rhythms: each is one bar or so long and loops, and grabs its notes from another track.
        'bass_rhythm': pattern(with_rows([('A1', '1/8')] * 8, grab=True, velocity=[110, 70, 90, 70]), root, kind),
        'counter_rhythm': pattern(with_rows([('A3', '1/4'), (None, '1/8'), ('A3', '1/8')], grab=True, velocity=80), root, kind),
        'stomp': pattern([('C1', '1/4'), (None, '1/4')], drum=True),
        'clap': pattern([(None, '1/4'), ('D#1', '1/4')], drum=True),
    }
    arps = {'pluck': {'step': '1/8', 'order': 'up_down'}}
    chains = {'pluck': [{'arp': 'pluck'}]}
    tracks = {
        'lead': {},
        'harmony': {'transpose': 2},
        'counter': {'transpose': -5},
        'pad': {},
        'pluck': {'transpose': 7},
        'bass': {'transpose': -7},
        'stomp': {'drum': True},
        'clap': {'drum': True},
    }

    def scene(name, part, parts):
        melody, harmony = f'melody_{part}', f'chords_{part}'
        cells = {
            'lead': {'pattern': melody},
            'harmony': {'pattern': melody},
            'counter': {'pattern': 'counter_rhythm', 'grab_track': 'lead', 'loop': True},
            'pad': {'pattern': harmony},
            'pluck': {'pattern': harmony, 'chain': 'pluck'},
            'bass': {'pattern': 'bass_rhythm', 'grab_track': 'pad', 'loop': True},
            'stomp': {'pattern': 'stomp', 'loop': True},
            'clap': {'pattern': 'clap', 'loop': True},
        }
        return {'name': name, 'tracks': {track: cells[track] for track in tracks if track in parts}}

    scenes = [
        scene('Verse: lead alone', 'verse', ['lead']),
        scene('Chorus: lead and pad', 'chorus', ['lead', 'pad']),
        scene('Verse: bass grabs the pad', 'verse', ['lead', 'pad', 'bass']),
        scene('Chorus: stomp and clap', 'chorus', ['lead', 'pad', 'bass', 'stomp', 'clap']),
        scene('Verse: harmony is the lead moved', 'verse', ['lead', 'harmony', 'pad', 'bass', 'stomp', 'clap']),
        scene('Chorus: counter grabs the lead', 'chorus', ['lead', 'harmony', 'counter', 'pad', 'bass', 'stomp', 'clap']),
        scene('Verse: pluck arpeggiates the pad', 'verse', ['lead', 'counter', 'pluck', 'bass', 'stomp', 'clap']),
        scene('Chorus: everything', 'chorus', list(tracks)),
    ]
    write('arrangement_demo.yml', [
        'Arrangement demo: eight parts of The Wellerman built from four note patterns.',
        'Run it with: llamatron examples/arrangement_demo.yml --to ableton --replace',
        '',
        'The tune is the same sung setting of The Wellerman as grab_demo.yml uses, in A minor at an',
        'estimated 100 BPM. The point here is how few patterns an arrangement needs. Only four',
        'patterns hold notes: melody_verse, melody_chorus, chords_verse and chords_chorus. Every',
        'other part reuses them, either directly with a track setting, or by grabbing them:',
        '',
        '- lead plays the melody patterns as written.',
        '- harmony plays the same melody patterns, with transpose: 2 on its track, so it follows',
        '  the lead a third higher, moving along the scale rather than by a fixed interval.',
        '- pad plays the chord patterns as written.',
        '- pluck plays the same chord patterns through an arpeggiator chain, transposed an octave up.',
        '- bass has a one-bar rhythm, bass_rhythm, with Grab on every step. It grabs from the pad,',
        '  which gives the lowest note of each chord, the root, and transpose: -7 puts it an octave',
        '  lower. It loops, so it lasts as long as the scene, and it follows any chord change.',
        '- counter has its own short rhythm that grabs from the lead, so it samples the melody',
        '  in a simpler rhythm, a sixth lower (transpose: -5).',
        '- stomp and clap are one-bar drum patterns that loop.',
        '',
        'So to change the tune, edit melody_verse or melody_chorus, and the lead, harmony and',
        'counter all change. To change the harmony, edit a chord pattern, and the pad, pluck and',
        'bass all follow. Each scene is a verse or a chorus and adds or swaps a part.',
    ], song('Arrangement demo', WELLERMAN_TEMPO, 'A Minor', {'A Minor': {'root': root, 'type': kind}}, patterns,
            tracks, scenes, arps=arps, chains=chains))


# ---------------------------------------------------------------------------------------------
# Morphing: a 16-step minimal techno groove, with Beethoven's Für Elise as one of the riffs.

def sixteenths(notes, **rows):
    steps = [(note, '1/16') for note in notes]
    return with_rows(steps, **rows) if rows else steps


def morph_demo():
    root, kind = 'A', 'minor'
    elise = ['E4', 'D#4', 'E4', 'D#4', 'E4', 'B3', 'D4', 'C4', 'A3', None, 'C3', 'E3', 'A3', 'B3', None, 'E3']
    blip = ['E3', None, None, 'E3', None, None, 'E3', None, None, 'E3', None, None, 'E3', None, 'E4', None]
    pulse = ['A1', None, 'A1', 'A1', None, 'A1', None, 'A1', 'A1', None, 'A1', 'A1', None, 'A1', None, 'A1']
    walk = ['A1', None, 'A1', 'C2', None, 'E2', None, 'A1', 'G1', None, 'G1', 'B1', None, 'D2', 'E2', None]
    patterns = {
        'kick': pattern([('C1', '1/4')] * 4, drum=True),
        'hat': pattern([(None, '1/8'), ('F#1', '1/8')] * 2, drum=True),
        'bass_pulse': pattern(sixteenths(pulse, velocity=[120, 60, 90, 70], cc1=[30] + [None] * 15), root, kind),
        'bass_walk': pattern(sixteenths(walk, velocity=[120, 60, 100, 80], cc1=[90] + [None] * 15), root, kind),
        'lead_blip': pattern(sixteenths(blip, velocity=90, cc1=[20] + [None] * 15), root, kind),
        'lead_elise': pattern(sixteenths(elise, velocity=[110, 80, 100, 80], cc1=[110] + [None] * 15), root, kind, prefer='#'),
    }
    tracks = {'kick': {'drum': True}, 'hat': {'drum': True}, 'bass': {'cc': [74, None, None, None]}, 'lead': {'cc': [74, None, None, None]}}

    def scene(name, bass=None, lead=None):
        cells = {'kick': {'pattern': 'kick', 'loop': True}, 'hat': {'pattern': 'hat', 'loop': True}}
        if bass:
            cells['bass'] = bass
        if lead:
            cells['lead'] = lead
        return {'name': name, 'tracks': cells}

    def morph(source, target, style, repeat=8):
        return {'pattern': source, 'repeat': repeat, 'morph_to': target, 'morph_style': style}

    scenes = [
        scene('Groove: bass pulse', bass={'pattern': 'bass_pulse', 'repeat': 8}),
        scene('Bass pulse morphs right into walk', bass=morph('bass_pulse', 'bass_walk', 'right')),
        scene('Bass walk, lead blip', bass={'pattern': 'bass_walk', 'loop': True}, lead={'pattern': 'lead_blip', 'repeat': 8}),
        scene('Lead blip morphs left into Elise', bass={'pattern': 'bass_walk', 'loop': True}, lead=morph('lead_blip', 'lead_elise', 'left')),
        scene('Lead blip morphs middle into Elise', bass={'pattern': 'bass_walk', 'loop': True}, lead=morph('lead_blip', 'lead_elise', 'middle')),
        scene('Elise morphs right back to blip', bass={'pattern': 'bass_walk', 'loop': True}, lead=morph('lead_elise', 'lead_blip', 'right')),
        scene('Both morph slowly, 16 repeats', bass=morph('bass_walk', 'bass_pulse', 'middle', 16), lead=morph('lead_blip', 'lead_elise', 'right', 16)),
        scene('Elise and walk, settled', bass={'pattern': 'bass_walk', 'loop': True}, lead={'pattern': 'lead_elise', 'repeat': 8}),
    ]
    write('morph_demo.yml', [
        'Morph demo: a 16-step minimal techno groove whose parts slowly turn into other patterns.',
        'Run it with: llamatron examples/morph_demo.yml --to ableton --replace',
        '',
        'A clip with a repeat above 1 and a morph_to plays its pattern on the first repeat and the',
        'morph_to pattern on the last, moving step by step from one to the other in between. The',
        'morph_style says where the change starts: left sweeps in from the first step, right from',
        'the last, and middle from the center outwards. Each pattern here is 16 sixteenth notes,',
        'one bar at 126 BPM, so a morph over 8 repeats takes 8 bars.',
        '',
        'The lead morphs from a sparse blip into the opening of Beethoven\'s Für Elise (1810), and',
        'the bass between a one-note pulse and a walking line. CC 1 on both is sent to CC 74,',
        'usually the filter cutoff, and a morph uses the target\'s CC values where the target plays,',
        'so the filter opens as the morph arrives. The last scene morphs both parts over 16 bars.',
    ], song('Morph demo', 126, 'A Minor', {'A Minor': {'root': root, 'type': kind}}, patterns, tracks, scenes))


# ---------------------------------------------------------------------------------------------
# Directions: In the Hall of the Mountain King, from the flutetunes.com transcription, B minor at
# 138 BPM, with its detached notes written as plain eighths.

MOUNTAIN = [
    ('B2', '1/8'), ('C#3', '1/8'), ('D3', '1/8'), ('E3', '1/8'), ('F#3', '1/8'), ('D3', '1/8'), ('F#3', '1/4'),
    ('F3', '1/8'), ('C#3', '1/8'), ('F3', '1/4'), ('E3', '1/8'), ('C3', '1/8'), ('E3', '1/4'),
    ('B2', '1/8'), ('C#3', '1/8'), ('D3', '1/8'), ('E3', '1/8'), ('F#3', '1/8'), ('D3', '1/8'), ('F#3', '1/8'), ('B3', '1/8'),
    ('A3', '1/8'), ('F#3', '1/8'), ('D3', '1/8'), ('F#3', '1/8'), ('A3', '1/2'),
]


def direction_demo():
    root, kind = 'B', 'minor'
    patterns = {
        'theme': pattern(MOUNTAIN, root, kind, prefer='b'),
        'theme_pendulum': pattern(MOUNTAIN, root, kind, prefer='b', direction='pendulum'),
        'pedal': pattern([('B1', '1/4'), ('D2', '1/4'), ('F#1', '1/4'), ('A1', '1/4')], root, kind),
    }
    directions = ['forward', 'reverse_a', 'reverse_b', 'alternate', 'pendulum', 'random', 'brownian', 'eitherway']
    scenes = []
    for direction in directions:
        cell = {'pattern': 'theme', 'repeat': 2}
        if direction != 'forward':
            cell['direction'] = direction
        scenes.append({'name': f'Clip direction: {direction}', 'tracks': {
            'theme': cell, 'pedal': {'pattern': 'pedal', 'loop': True},
        }})
    scenes.append({'name': 'Pattern direction: pendulum', 'tracks': {
        'theme': {'pattern': 'theme_pendulum', 'repeat': 2}, 'pedal': {'pattern': 'pedal', 'loop': True},
    }})
    scenes.append({'name': 'Clip forward overrides pattern', 'tracks': {
        'theme': {'pattern': 'theme_pendulum', 'repeat': 2, 'direction': 'forward'}, 'pedal': {'pattern': 'pedal', 'loop': True},
    }})
    scenes.append({'name': 'Theme and pedal both reverse_a', 'tracks': {
        'theme': {'pattern': 'theme', 'repeat': 2, 'direction': 'reverse_a'},
        'pedal': {'pattern': 'pedal', 'loop': True, 'direction': 'reverse_a'},
    }})
    write('direction_demo.yml', [
        'Direction demo: one theme played in each of the Cirklon\'s step directions.',
        'Run it with: llamatron examples/direction_demo.yml --to ableton --replace',
        '',
        'The theme is the opening of Grieg\'s In the Hall of the Mountain King (1875), in B minor at',
        '138 BPM as the flutetunes.com transcription has it, with its short detached notes written',
        'as plain eighths. Its F and C naturals use the Accidental row. A pedal bass loops under it.',
        '',
        'Each scene plays the theme twice. A direction changes the order the steps play in, but',
        'never how long a pass lasts: the last step is cut to fit, so every scene is the same',
        'length. Positions carry on from the first pass into the second, which you can hear in',
        'pendulum, random and brownian. Random directions use the song\'s seed, so a render always',
        'plays the same.',
        '',
        'A direction can be set on a pattern, like theme_pendulum, or on a clip, and a clip\'s',
        'direction overrides its pattern\'s, which the last scenes show. So "Pattern direction:',
        'pendulum" sounds like "Clip direction: pendulum", and "Clip forward overrides pattern"',
        'sounds like "Clip direction: forward", on purpose. The last scene reverses the pedal too.',
    ], song('Direction demo', 138, 'B Minor', {'B Minor': {'root': root, 'type': kind}}, patterns,
            {'theme': {}, 'pedal': {}}, scenes))


# ---------------------------------------------------------------------------------------------
# A basic classical arrangement: Pachelbel's Canon in D, from the flutetunes.com transcription.

def basic_classical_demo():
    root, kind = 'D', 'major'
    quarters = lambda notes: [(note, '1/4') for note in notes]  # noqa: E731
    eighths = lambda notes: [(note, '1/8') for note in notes]  # noqa: E731
    patterns = {
        'ground_bass': pattern(quarters(['D2', 'A1', 'B1', 'F#1', 'G1', 'D1', 'G1', 'A1']), root, kind),
        'canon_falling_quarters': pattern(quarters(['F#4', 'E4', 'D4', 'C#4', 'B3', 'A3', 'B3', 'C#4']), root, kind),
        'canon_answering_quarters': pattern(quarters(['D4', 'C#4', 'B3', 'A3', 'G3', 'F#3', 'G3', 'E3']), root, kind),
        'canon_flowing_eighths': pattern(eighths(['D3', 'F#3', 'A3', 'G3', 'F#3', 'D3', 'F#3', 'E3',
                                                  'D3', 'B2', 'D3', 'A3', 'G3', 'B3', 'A3', 'G3']), root, kind),
        'ending_bass': pattern([('D1', 2)], root, kind),
        'ending_top': pattern([('D4', 2)], root, kind),
        'ending_middle': pattern([('A3', 2)], root, kind),
        'ending_low': pattern([('F#3', 2)], root, kind),
    }
    lines = ['canon_falling_quarters', 'canon_answering_quarters', 'canon_flowing_eighths']

    def scene(name, violins, tempo=None):
        cells = {'cello': {'pattern': 'ground_bass'}}
        for number, line in enumerate(violins, 1):
            if line:
                cells[f'violin {number}'] = {'pattern': line}
        result = {'name': name}
        if tempo:
            result['tempo'] = tempo
        result['tracks'] = cells
        return result

    scenes = [
        scene('Ground bass alone', []),
        scene('Violin 1 enters', [lines[0]]),
        scene('Violin 2 follows in canon', [lines[1], lines[0]]),
        scene('Violin 3 follows in canon', [lines[2], lines[1], lines[0]]),
        scene('The three lines rotate', [lines[0], lines[2], lines[1]]),
        scene('The lines rotate again', [lines[1], lines[0], lines[2]]),
        {'name': 'Final chord, slower', 'tempo': 36, 'tracks': {
            'violin 1': {'pattern': 'ending_top'}, 'violin 2': {'pattern': 'ending_middle'},
            'violin 3': {'pattern': 'ending_low'}, 'cello': {'pattern': 'ending_bass'},
        }},
    ]
    write('basic_classical_demo.yml', [
        'Basic classical demo: the opening of Pachelbel\'s Canon in D, with only patterns and scenes.',
        'Run it with: llamatron examples/basic_classical_demo.yml --to ableton --replace',
        '',
        'This uses no chains, grabs or ratchets: just named patterns on four tracks, the way you',
        'might copy a score in. The notes and the tempo of 44 come from the flutetunes.com',
        'transcription, and the last scene slows to 36, as that transcription does at the end.',
        'Put string sounds on the tracks.',
        '',
        'A canon is one line played by several voices, each starting later. So the three violin',
        'tracks share the same three patterns, and each scene moves every pattern down one violin:',
        'violin 2 plays in each scene what violin 1 played in the scene before. Every scene is two',
        'bars, one pass of the ground bass that the cello repeats under everything. Because every',
        'line fits over the ground bass, the lines can keep rotating, which is how the Canon goes on.',
    ], song('Basic classical demo', 44, 'D Major', {'D Major': {'root': root, 'type': kind}}, patterns,
            {'violin 1': {}, 'violin 2': {}, 'violin 3': {}, 'cello': {}}, scenes))


# ---------------------------------------------------------------------------------------------
# The Entertainer, from the Mutopia Project's public domain typesetting of the 1902 edition.

MEASURE = F(1, 2)
PHRASE = 4 * MEASURE
VOICES = 3
# Each strain in the order the piece plays, with its repeats written out, as
# (name, number of four-bar phrases, scale).
STRAINS = [
    ('Intro', 1, 'C Major'), ('A', 4, 'C Major'), ('A repeat', 4, 'C Major'), ('B', 4, 'C Major'),
    ('B repeat', 4, 'C Major'), ('A return', 4, 'C Major'), ('C trio', 4, 'F Major'), ('C repeat', 4, 'F Major'),
    ('Bridge', 1, 'C Major'), ('D', 4, 'C Major'), ('D repeat', 4, 'C Major'),
]


def entertainer_notes(track):
    file = mido.MidiFile(os.path.join(SOURCES, 'entertainer.mid'))
    ticks = file.ticks_per_beat * 4
    time, held, notes = 0, {}, []
    for message in file.tracks[track]:
        time += message.time
        if message.type == 'note_on' and message.velocity > 0:
            held.setdefault(message.note, []).append((time, message.velocity))
        elif message.type in ('note_on', 'note_off') and held.get(message.note):
            start, velocity = held[message.note].pop(0)
            notes.append((F(start, ticks), message.note, F(time - start, ticks), velocity))
    return notes


def split_voices(notes, from_top):
    """Split a hand into voices by rank at each onset: from the top for treble, the bottom for bass.

    A fourth note at the same moment, which happens 19 times in the piece, is left out.
    """
    onsets = collections.defaultdict(list)
    for start, number, length, velocity in notes:
        onsets[start].append((number, length, velocity))
    voices = [[] for _ in range(VOICES)]
    for start in sorted(onsets):
        ranked = sorted(onsets[start], reverse=from_top)
        for rank, (number, length, velocity) in enumerate(ranked[:VOICES]):
            voices[rank].append((start, number, length, velocity))
    return voices


def phrase_steps(voice, phrase):
    """Return one voice's steps in one four-bar phrase, with notes cut at the next note or the phrase's end."""
    begin, end = phrase * PHRASE, (phrase + 1) * PHRASE
    starts = [note for note in voice if begin <= note[0] < end]
    steps, time = [], begin
    for index, (start, number, length, velocity) in enumerate(starts):
        if start > time:
            steps.append((None, start - time))
        following = starts[index + 1][0] if index + 1 < len(starts) else end
        played = min(start + length, following)
        steps.append((number, played - start, {'velocity': max(1, min(127, velocity))}))
        if played < following:
            steps.append((None, following - played))
        time = following
    if not starts:
        return None
    if time < end:
        steps.append((None, end - time))
    return steps


def entertainer_demo():
    parts = {'treble': split_voices(entertainer_notes(1), True), 'bass': split_voices(entertainer_notes(2), False)}
    scales = {'C Major': {'root': 'C', 'type': 'major'}, 'F Major': {'root': 'F', 'type': 'major'}}
    tracks = {f'{hand} {rank + 1}': {} for hand in parts for rank in range(VOICES)}
    patterns, seen, scenes = {}, {}, []
    phrase = 0
    for strain, count, scale in STRAINS:
        for number in range(count):
            bars = f'{number * 4 + 1}-{number * 4 + 4}'
            cells = {}
            for hand, voices in parts.items():
                for rank, voice in enumerate(voices):
                    steps = phrase_steps(voice, phrase)
                    if steps is None:
                        continue
                    track = f'{hand} {rank + 1}'
                    data = pattern(steps, scales[scale]['root'], 'major')
                    key = (track, repr(data))
                    if key not in seen:
                        base = strain.split()[0]
                        name = f'{base} {bars} {track}' if count > 1 else f'{base} {track}'
                        while name in patterns:
                            name += "'"
                        patterns[name] = data
                        seen[key] = name
                    cells[track] = {'pattern': seen[key]}
            scene = {'name': f'{strain}, bars {bars}' if count > 1 else strain}
            if scale != 'C Major':
                scene['scale'] = scale
            scene['tracks'] = cells
            scenes.append(scene)
            phrase += 1
    write('entertainer_demo.yml', [
        'The Entertainer: the whole of Scott Joplin\'s 1902 rag, four bars at a time.',
        'Run it with: llamatron examples/entertainer_demo.yml --to ableton --replace',
        '',
        'This is a longer piece, to get a feel for a full composition in the tracker. The notes,',
        'velocities and tempo come from the Mutopia Project\'s public domain typesetting of the',
        'original 1902 edition, at its marking of 72 quarter notes a minute ("Not fast"). Put a',
        'piano on all six tracks.',
        '',
        'Each scene is one four-bar phrase, so its patterns line up with four bars of the sheet',
        'music, and the scenes play the strains in order with their repeats written out: Intro,',
        'A twice, B twice, A again, the C trio twice (in F major, set on those scenes), a bridge,',
        'and D twice. A phrase that comes back exactly reuses its pattern, so the repeats add',
        'scenes but few patterns. A pattern whose name ends in \' differs from the one before it,',
        'usually at a repeat\'s second ending.',
        '',
        'A pattern plays one note or one chord symbol at a time, and a piano part has chords that',
        'no symbol fits, so each hand is split into voices. "treble 1" is the top note of the right',
        'hand, the melody, and "treble 2" and "treble 3" are the notes under it. "bass 1" is the',
        'lowest note of the left hand, and "bass 2" and "bass 3" are the notes above it. A voice',
        'with nothing to play in a phrase has no clip there. Notes held over a phrase\'s end are',
        'cut there and the next phrase plays them again, and the rare fourth note of a chord is',
        'left out.',
    ], song('The Entertainer', 72, 'C Major', scales, patterns, tracks, scenes, author='Scott Joplin'))


def main(output='examples'):
    """Write every demo into a folder, examples/ unless told otherwise."""
    global OUTPUT
    OUTPUT = output
    scale_demo()
    arpeggiator_demo()
    ratchet_demo()
    chain_demo()
    grab_demo()
    arrangement_demo()
    morph_demo()
    direction_demo()
    basic_classical_demo()
    entertainer_demo()


if __name__ == '__main__':
    main()
