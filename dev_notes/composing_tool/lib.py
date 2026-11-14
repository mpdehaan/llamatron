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

"""A small composing tool: songs written as short text specifications, written out as llamatron set files.

Melody tokens, separated by spaces, one per step:
  .        a rest
  -        a tie, holding the note before
  5        degree 5 in the pattern's octave; b3 / #4 with an accidental
  5' 5,    up or down an octave (repeatable)
  1:5      with a chord symbol (scale triad 5, or a named one like m7, dom7)
  5!90     with a velocity
Drum lines: one character per step, x loud, o soft, . rest.
"""

import os
import re
from fractions import Fraction

import yaml

ROOT = '/Users/michaeldehaan/Devel/llamatron'
DRUM_NOTES = {
    'kick': ('C', None, 3), 'snare': ('D', None, 3), 'stick': ('C', '#', 3), 'clap': ('D', '#', 3),
    'hat': ('F', '#', 3), 'pedal': ('G', '#', 3), 'open': ('A', '#', 3), 'crash': ('C', '#', 4),
    'ride': ('D', '#', 4), 'tom_lo': ('A', None, 3), 'tom_mid': ('B', None, 3), 'tom_hi': ('D', None, 4),
    'tamb': ('F', '#', 4), 'cowbell': ('G', '#', 4), 'claves': ('D', '#', 6), 'shaker': ('A', '#', 5),
    'bongo': ('C', None, 5), 'conga': ('D', None, 5), 'timbale': ('E', None, 5), 'splash': ('G', None, 4),
}
TOKEN = re.compile(r"^([b#]?)(\d)([',]*)(?::([A-Za-z0-9#b]+))?(?:!(\d+))?$")


def mel(text, *, octave=5, step='1/8', direction=None):
    tokens = text.split()
    degree, acc, octv, chord, vel, tie = [], [], [], [], [], []
    for token in tokens:
        if token in ('.', '-'):
            degree.append(None); acc.append(None); octv.append(None); chord.append(None); vel.append(None)
            tie.append(token == '-')
            continue
        m = TOKEN.match(token)
        assert m, token
        a, d, marks, c, v = m.groups()
        degree.append(int(d)); acc.append(a or None)
        octv.append(octave + marks.count("'") - marks.count(','))
        chord.append(c); vel.append(int(v) if v else None); tie.append(False)
    p = {'steps': len(tokens), 'step_size': step, 'degree': degree, 'octave': octv}
    for name, row in (('accidental', acc), ('chord', chord), ('velocity', vel)):
        if any(x is not None for x in row):
            p[name] = row
    if any(tie):
        p['tie'] = tie
    if direction:
        p['direction'] = direction
    return p


def drum(line, voice, *, step='1/16'):
    letter, accidental, octave = DRUM_NOTES[voice]
    line = line.replace(' ', '').replace('|', '')
    degree, acc, octv, vel = [], [], [], []
    for ch in line:
        hit = ch in 'xo'
        degree.append(letter if hit else None)
        acc.append(accidental if hit and accidental else None)
        octv.append(octave if hit else None)
        vel.append({'x': 110, 'o': 70}.get(ch))
    p = {'steps': len(line), 'drum': True, 'step_size': step, 'degree': degree, 'octave': octv, 'velocity': vel}
    if any(acc):
        p['accidental'] = acc
    return p


def pass_length(pattern):
    return pattern['steps'] * Fraction(pattern['step_size'])


def song(*, stem, folder, title, description, genre, tempo, root, kind, about, keep, instruments, tracks,
         patterns, scenes, progressions=None, arps=None, strums=None, auto_ratchets=None, voice_leadings=None,
         euclids=None, chains=None, groove=None, extra_scales=None, step_size=None, time_signature=None, drifts=None,
         densities=None, swells=None, articulates=None, glides=None, shortens=None):
    """tracks: {name: (instrument or None, settings)}; scenes: [(name, bars, {track: pattern | (pattern, [chains]) | (pattern, [chains], settings)}, about)]."""
    chains = dict(chains or {})
    for name in (progressions or {}):
        chains.setdefault(name, [{'progression': name}])
    drum_kit = any(t[0] == 'drum kit' for t in tracks.values())
    insts = {name: {'device': '*FluidSynth', 'gm_sound': gm} for name, gm in instruments.items()}
    if drum_kit:
        insts['drum kit'] = {'device': '*FluidSynth'}
    song_tracks = {}
    for name, (inst, settings) in tracks.items():
        t = dict(settings)
        if inst == 'drum kit':
            t['drum'] = True
        if inst:
            t['instrument'] = inst
        song_tracks[name] = t
    song_scenes = []
    total = Fraction(0)
    text_scenes = []
    bar = Fraction(time_signature) if time_signature else Fraction(1)
    for number, scene_spec in enumerate(scenes, 1):
        name, bars, clips, what = scene_spec[:4]
        scene_settings = scene_spec[4] if len(scene_spec) > 4 else {}
        parsed = {}
        for track, value in clips.items():
            if isinstance(value, str):
                parsed[track] = (value, [], {})
            elif len(value) == 2:
                parsed[track] = (value[0], value[1], {})
            else:
                parsed[track] = value
        anchor = max(parsed, key=lambda t: pass_length(patterns[parsed[t][0]]))
        length = Fraction(bars) * bar
        cells = {}
        for track, (pattern, chain_list, settings) in parsed.items():
            cell = {'pattern': pattern}
            if chain_list:
                cell['chains'] = list(chain_list)
            if track == anchor:
                times = length / pass_length(patterns[pattern])
                assert times.denominator == 1 and times >= 1, (stem, name, track, times)
                if times > 1:
                    cell['repeat'] = int(times)
            else:
                assert pass_length(patterns[pattern]) <= length, (stem, name, track)
                cell['loop'] = True
            cell.update(settings)
            cells[track] = cell
        song_scenes.append({'name': name, **scene_settings, 'tracks': cells})
        tempo_here = scene_settings.get('tempo_start', scene_settings.get('tempo', tempo))
        total += length * 240 / ((tempo_here + scene_settings.get('tempo_end', tempo_here)) / 2)
        text_scenes.append(f'Scene {number}, {name}, {bars} bars: {what}')
    seconds = float(total)
    paragraphs = '\n'.join(line.strip() for line in about.strip().splitlines())
    notes = (paragraphs + f'\n\nRun it with: llamatron examples/{folder}/{stem}.yml\n\n' + '\n'.join(text_scenes)
             + '\n\nWhen changing this demo:\n' + '\n'.join(f'- {k}' for k in keep) + '\n')
    scale_name = f'{root} {kind.replace("_", " ").title()}'
    scales = {scale_name: {'root': root, 'type': kind}}
    scales.update(extra_scales or {})
    data = {
        'title': title, 'description': description, 'notes': notes, 'real_time': True, 'protected': True,
        'scales': scales, 'patterns': patterns,
    }
    if step_size:
        data['step_size'] = step_size
    for key, value in (('arps', arps), ('auto_ratchets', auto_ratchets), ('progressions', progressions),
                       ('voice_leadings', voice_leadings), ('strums', strums), ('euclids', euclids), ('drifts', drifts),
                       ('densities', densities), ('swells', swells), ('articulates', articulates), ('glides', glides), ('shortens', shortens)):
        if value:
            data[key] = value
    if chains:
        data['chains'] = chains
    data['instruments'] = insts
    s = {'tempo': tempo}
    if time_signature:
        s['time_signature'] = time_signature
    s.update({'scale': scale_name, 'genre': genre})
    if groove:
        s['groove'] = groove
    s['tracks'] = song_tracks
    s['scenes'] = song_scenes
    data['songs'] = {stem: s}
    return stem, folder, data, seconds


def write(spec):
    from llamatron.composition.setlist import Setlist
    stem, folder, data, seconds = spec
    notes = data.pop('notes')
    path = os.path.join(ROOT, 'examples', folder, stem + '.yml')
    with open(path, 'w') as f:
        yaml.safe_dump(data, f, sort_keys=False)
    data['notes'] = notes
    raw = yaml.safe_load(open(path))
    raw = {'title': raw['title'], 'description': raw['description'], 'notes': notes, **{k: v for k, v in raw.items() if k not in ('title', 'description')}}
    with open(path, 'w') as f:
        yaml.safe_dump(raw, f, sort_keys=False, width=200)
    setlist = Setlist.read_file(path)
    setlist.write_file(path)
    return path, seconds


BEATS = {
    # one bar of sixteenths per voice
    'rock': {'kick': 'x.......x.x.....', 'snare': '....x.......x...', 'hat': 'x.o.x.o.x.o.x.o.'},
    'four': {'kick': 'x...x...x...x...', 'clap': '....x.......x...', 'open': '..x...x...x...x.', 'hat': 'xoxoxoxoxoxoxoxo'},
    'disco': {'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'open': '..x...x...x...x.', 'hat': 'x.o.x.o.x.o.x.o.'},
    'punk': {'kick': 'x.x.....x.x.....', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'},
    'half': {'kick': 'x.........x.....', 'snare': '........x.......', 'hat': 'x.o.x.o.x.o.x.o.'},
    'shuffle': {'kick': 'x.......x.......', 'snare': '....x.......x...', 'ride': 'x..ox..ox..ox..o'},
    'surf': {'kick': 'x.x...x.x.x...x.', 'snare': '....x.......x..o', 'ride': 'x.x.x.x.x.x.x.x.'},
    'swing': {'kick': 'x.......x.......', 'stick': '....x.......x...', 'ride': 'x...x..ox...x..o'},
    'march': {'kick': 'x.......x.......', 'snare': 'x.oox.o.x.oox.oo', 'hat': '....x.......x...'},
    'funk': {'kick': 'x.....x...x..x..', 'snare': '....x..o.o..x...', 'hat': 'xoxoxoxoxoxoxoxo'},
    'trance': {'kick': 'x...x...x...x...', 'clap': '....x.......x...', 'open': '..x...x...x...x.', 'hat': '.o.o.o.o.o.o.o.o'},
    'game': {'kick': 'x.....x.x.......', 'snare': '....x.......x.x.', 'hat': 'x.x.x.x.x.x.x.x.'},
    'ballad': {'kick': 'x.........x.....', 'stick': '....x.......x...', 'hat': 'x...x...x...x...'},
    'latin': {'kick': 'x..x..x.x..x..x.', 'conga': '..x.x...x.x.x.x.', 'cowbell': 'x.x.xx.x.x.xx.x.', 'shaker': 'xoxoxoxoxoxoxoxo'},
    'eurodance': {'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'open': '..x...x...x...x.', 'hat': 'xxxxxxxxxxxxxxxx'},
}


def beat(style, *, prefix=None, fill=False):
    """The patterns of a beat, named prefix_voice (the style's name by default)."""
    prefix = prefix or style
    out = {}
    for voice, line in BEATS[style].items():
        out[f'{prefix}_{voice}'] = drum(line, voice)
    return out


def fill_bar(*, prefix):
    """A one-bar drum fill: toms down and a crash, over two bars of the beat would be too long, so it is one bar."""
    return {
        f'{prefix}_fill_snare': drum('x.x.x.xxx.x.xxxx', 'snare'),
        f'{prefix}_fill_tom': drum('............x.x.', 'tom_lo'),
    }


def kit_tracks(style):
    return {voice: ('drum kit', {}) for voice in BEATS[style]}


def kit_clips(style, *, prefix=None, only=None):
    prefix = prefix or style
    return {voice: f'{prefix}_{voice}' for voice in BEATS[style] if only is None or voice in only}


def band(*, drums, harmony=('bass', 'chords')):
    """Return a function making scenes for a band: the drum clips (a dict, or a dict of dicts by name), and the
    harmony tracks, each playing the pattern of its own name through the scene's progression chain."""
    def scene(name, bars, prog, about, *, lead=None, kit='main', without=(), extra=None, chains=None, settings=None):
        clips = {}
        if kit and kit in drums:
            clips.update(drums[kit])
        for track in harmony:
            if track in without:
                continue
            clips[track] = (track, [prog] + list(chains or [])) if prog else track
        if lead:
            clips.update(lead if isinstance(lead, dict) else {'lead': lead})
        for track in without:
            clips.pop(track, None)
        clips.update(extra or {})
        return (name, bars, clips, about, settings or {})
    return scene
