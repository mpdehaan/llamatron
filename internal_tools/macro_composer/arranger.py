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

"""The arranger: a song's picks and a style template made into a MacroComposer input, a whole song.

A style template lists a style's traits, each with its values and how common each is; a value of a trait a band plays holds
the bar it plays: a drum's hits, or a figure of notes written over chord one, which a Progression moves through the song's
chords. A song's picks say which template of the style it starts from, the picks it changes, its key, its tempo, its
sections with their chords and its form. The arranger decides nothing but the tune, and that only where the song gives none:
it then sketches one by rule from the style's melody habits and the song's seed (melody.py). What it writes is an input the
MacroComposer composes, so every choice can be read and changed there.
"""

from fractions import Fraction

from melody import GRID, sketched
from notation import ACCIDENTAL, DEGREE, DRUM, FLAT, HITS, LINES, LOUD, NONE, OCTAVE, REST, SHARP, SOFT, STEP, STEPS, VELOCITY, CHORD

# The fields of a style template.
NAME = 'name'
TITLE = 'title'
GENRE = 'genre'
FEEL = 'feel'
TEMPLATES = 'templates'
TRAITS = 'traits'
ROLES = 'roles'
SOUNDS = 'sounds'
SECTIONS = 'sections'
MELODY = 'melody'
LOUDNESS = 'loudness'
# The fields of a trait's value.
VALUE = 'value'
SHARE = 'share'
NEEDS = 'needs'
BAR = 'bar'
FILL = 'fill'
FIGURE = 'figure'
SOUND = 'sound'
GENERATORS = 'generators'
PATTERN = 'pattern'
EVERY = 'every'
SCALE_TYPE = 'scale_type'
# The fields of a role.
ROLE = 'role'
TRAIT = 'trait'
DRUMS = 'drums'
TUNE = 'tune'
ANSWERS = 'answers'
FOLLOWS_CHORDS = 'follows_chords'
VOICE_LEADING = 'voice_leading'
# The fields of a section.
BARS = 'bars'
PLAYS = 'plays'
PLAN = 'plan'
CHORDS = 'chords'
HELD = 'held'
LINES_GIVEN = 'tunes'
# The fields of a song's picks.
STYLE = 'style'
TEMPLATE = 'template'
PICKS = 'picks'
KEY = 'key'
ROOT = 'root'
TYPE = 'type'
TEMPO = 'tempo'
SEED = 'seed'
FORM = 'form'
DESCRIPTION = 'description'
# The traits the arranger reads by name.
METER = 'meter'
CHORD_TRAIT = 'chords'
FILLS = 'fills'
PHRASE_BARS = 'phrase_bars'
USUAL = 'usual'
# What the MacroComposer's input names.
NOTES = 'notes'
SCALES = 'scales'
SCALE = 'scale'
TIME_SIGNATURE = 'time_signature'
SHAPED = 'shaped'
INSTRUMENTS = 'instruments'
TRACKS = 'tracks'
DRUM_TRACKS = 'drum_tracks'
CHAINS = 'chains'
PARTS = 'parts'
SCENE = 'scene'
PLAY = 'play'
PART = 'part'
ONCE = 'once'
PROGRESSIONS = 'progressions'
PROGRESSION = 'progression'
ACCIDENTALS = 'accidentals'
VOICE_LEADINGS = 'voice_leadings'
NEAR = 'near'
DRUM_KIT = 'drum kit'
CRASH = 'crash'
KICK = 'kick'
COMMON_TIME = '4/4'
ACCIDENTAL_MARKS = {SHARP: '#', FLAT: 'b'}
NEAR_VOICES = {'lowest_octave': 3, 'highest_octave': 5}
DEFAULT_PHRASE_BARS = 4
EIGHTH = '1/8'
EIGHTHS_IN_WHOLE = 8
KIND = 'kind'
# The set's section that holds each kind of generator a value may bring.
SECTION_OF_KIND = {'guitarify': 'guitarifies', 'arp': 'arps', 'strum': 'strums'}
VOICE_LEADING_KIND = 'voice_leading'
HELD_STEPS = 2
HELD_CHORD = 'M'
SOFT_SHARE = Fraction(2, 3)

MSG_NOTES = '{title}: a {style} song, {template}, made by the MacroComposer from the style template and the song\'s picks.\n\n{picks}\n\n{form}\n'
MSG_PICK = '{}: {}.'
MSG_SCENE = 'Scene {}, {}, {} bars.'
MSG_FILL_PART = '{} fill'
MSG_SECTION_PART = '{} {}'
MSG_REPEATED_SCENE = '{} {}'
ERR_NO_TEMPLATE = 'the style ({}) has no template called ({}); it has: {}'
ERR_NO_VALUE = 'the trait ({}) has no value called ({}); it has: {}'
ERR_NEEDS = 'the pick {} = {} needs {} = {}, and the song picks {}'
ERR_NO_SECTION = 'the form names the section ({}), which neither the song nor the style describes'
ERR_BARS = 'the section ({}) lasts {} bars, which phrases of {} bars do not fill'


def listed(names):
    return ', '.join(sorted(str(name) for name in names))


def values_of(*, style, trait):
    return {entry[VALUE]: entry for entry in style[TRAITS][trait]} if isinstance(style[TRAITS].get(trait), list) else {}


def fits(*, entry, picks):
    return all(picks.get(trait) == wanted for trait, wanted in entry.get(NEEDS, {}).items() if trait in picks)


def picked(*, style, song):
    """Every trait's pick: the song's own, else its template's, else the commonest value that fits what is picked."""
    templates = style[TEMPLATES]
    if song[TEMPLATE] not in templates:
        raise ValueError(ERR_NO_TEMPLATE.format(style[NAME], song[TEMPLATE], listed(templates)))
    picks = {**templates[song[TEMPLATE]], **song.get(PICKS, {})}
    for trait in style[TRAITS]:
        values = values_of(style=style, trait=trait)
        if not values:
            continue
        if trait not in picks:
            fitting = [entry for entry in values.values() if fits(entry=entry, picks=picks)]
            picks[trait] = max(fitting, key=share_of)[VALUE]
        if picks[trait] not in values:
            raise ValueError(ERR_NO_VALUE.format(trait, picks[trait], listed(values)))
    for trait, value in picks.items():
        for needed, wanted in values_of(style=style, trait=trait).get(value, {}).get(NEEDS, {}).items():
            if picks.get(needed) != wanted:
                raise ValueError(ERR_NEEDS.format(trait, value, needed, wanted, picks.get(needed)))
    return picks


def share_of(entry):
    return entry[SHARE]


def bar_length(meter):
    return Fraction(meter)


def step_of(*, meter, grid):
    return str(bar_length(meter) / grid)


def chord_of(entry):
    return entry if isinstance(entry, dict) else {DEGREE: entry}


def progression_of(*, chords, every):
    """A list of chords as a Progression's settings."""
    made = {CHORDS: [chord_of(chord)[DEGREE] for chord in chords]}
    marks = [ACCIDENTAL_MARKS.get(chord_of(chord).get(ACCIDENTAL)) for chord in chords]
    if any(marks):
        made[ACCIDENTALS] = marks
    if every:
        made[EVERY] = every
    return made


def drum_parts(*, style, picks, roles, meter, phrase_bars):
    """Each drum the picks play, as a part a phrase long whose last bar is the fill."""
    bars = {}
    for role in roles:
        if role.get(DRUMS):
            for trait in role[DRUMS]:
                bars.update(values_of(style=style, trait=trait)[picks[trait]].get(BAR, {}))
    fill = values_of(style=style, trait=FILLS).get(picks.get(FILLS), {}).get(FILL, {})
    parts = {}
    for piece in list(bars) + [piece for piece in fill if piece not in bars]:
        plain = bars.get(piece) or [NONE] * len(fill[piece])
        last = fill.get(piece, plain)
        if len(last) != len(plain):
            last = plain
        loud = style[LOUDNESS].get(piece, style[LOUDNESS][DRUMS])
        parts[piece] = {DRUM: piece, STEP: step_of(meter=meter, grid=len(plain)), LOUD: loud, SOFT: int(loud * SOFT_SHARE), HITS: plain * (phrase_bars - 1) + last}
    return parts


def one_hit(*, style, meter, drum):
    """One bar in which a drum is hit once, on the first beat."""
    loud = style[LOUDNESS].get(drum, style[LOUDNESS][DRUMS])
    return {DRUM: drum, STEP: EIGHTH, LOUD: loud, SOFT: loud, HITS: [LOUD] + [NONE] * (int(bar_length(meter) * EIGHTHS_IN_WHOLE) - 1)}


def figure_part(*, entry, role, meter):
    """A value's figure as a tune's part; the figure's bars are its lines."""
    bars = entry[FIGURE]
    grid = sum(note.get(REST, note.get(STEPS, 0)) for note in bars[0])
    return {STEP: step_of(meter=meter, grid=grid), OCTAVE: role[OCTAVE], VELOCITY: role[VELOCITY], LINES: [[dict(note) for note in bar] for bar in bars]}


def held_part(*, role, meter, chord):
    """One bar of the home note or chord, held."""
    note = {DEGREE: 1, STEPS: HELD_STEPS}
    if chord:
        note[CHORD] = HELD_CHORD
    return {STEP: step_of(meter=meter, grid=HELD_STEPS), OCTAVE: role[OCTAVE], VELOCITY: role[VELOCITY], LINES: [[note]]}


def tune_part(*, lines, role, meter, grid):
    return {STEP: step_of(meter=meter, grid=grid), OCTAVE: role[OCTAVE], VELOCITY: role[VELOCITY], LINES: lines}


def section_of(*, name, style, song):
    """A section as the song describes it over what the style says of a section of its name."""
    of_song = song.get(SECTIONS, {}).get(name, {})
    kind = of_song.get(KIND, name)
    if kind not in style[SECTIONS] and not of_song:
        raise ValueError(ERR_NO_SECTION.format(name))
    return {**style[SECTIONS].get(kind, {}), **of_song}


def arranged(*, style, song):
    """A song's picks as a MacroComposer input."""
    picks = picked(style=style, song=song)
    meter = picks.get(METER, COMMON_TIME)
    roles = style[ROLES]
    phrase_bars = style.get(PHRASE_BARS, DEFAULT_PHRASE_BARS)
    scale_type = song[KEY][TYPE]
    scale = '{} {}'.format(song[KEY][ROOT], scale_type.capitalize())
    habits = style[MELODY]
    parts = drum_parts(style=style, picks=picks, roles=roles, meter=meter, phrase_bars=phrase_bars)
    drum_tracks = list(parts)
    tracks = {piece: DRUM_KIT for piece in drum_tracks}
    instruments = {DRUM_KIT: None}
    progressions = {}
    chains = {}
    extra = {}
    shaped = []
    pitched = []
    for role in roles:
        if role.get(DRUMS):
            continue
        entry = values_of(style=style, trait=role[TRAIT])[picks[role[TRAIT]]]
        if SOUND not in entry:
            continue
        instruments[entry[SOUND]] = style[SOUNDS][entry[SOUND]]
        tracks[role[ROLE]] = entry[SOUND]
        pitched.append((role, entry))
        if FIGURE in entry:
            parts[role[ROLE]] = figure_part(entry=entry, role=role, meter=meter)
            shaped.append(role[ROLE])
        parts[MSG_SECTION_PART.format(role[ROLE], HELD)] = held_part(role=role, meter=meter, chord=bool(role.get(VOICE_LEADING)))
        for generator in entry.get(GENERATORS, []):
            for kind, settings in generator.items():
                extra.setdefault(SECTION_OF_KIND[kind], {})[role[ROLE]] = settings
    form = []
    notes = []
    met = {}
    for count, name in enumerate(song[FORM], start=1):
        section = section_of(name=name, style=style, song=song)
        met[name] = met.get(name, 0) + 1
        scene_name = name if met[name] == 1 else MSG_REPEATED_SCENE.format(name, met[name])
        bars = 1 if section.get(HELD) else section[BARS]
        if not section.get(HELD) and bars % phrase_bars:
            raise ValueError(ERR_BARS.format(name, bars, phrase_bars))
        chord_entry = values_of(style=style, trait=CHORD_TRAIT)[picks[CHORD_TRAIT]]
        chords = [chord_of(chord) for chord in section.get(CHORDS, chord_entry[PATTERN])]
        play = {}
        if section.get(HELD):
            held = MSG_SECTION_PART.format(CRASH, HELD)
            parts[held] = one_hit(style=style, meter=meter, drum=CRASH)
            parts[MSG_SECTION_PART.format(KICK, HELD)] = one_hit(style=style, meter=meter, drum=KICK)
            if CRASH not in tracks:
                tracks[CRASH] = DRUM_KIT
                drum_tracks.append(CRASH)
            play[CRASH] = held
            if KICK in tracks:
                play[KICK] = {PART: MSG_SECTION_PART.format(KICK, HELD), ONCE: True}
            for role, entry in pitched:
                if FIGURE in entry and role[ROLE] in section.get(PLAYS, [role[ROLE]]):
                    play[role[ROLE]] = {PART: MSG_SECTION_PART.format(role[ROLE], HELD), ONCE: True}
        else:
            if DRUMS in section[PLAYS]:
                for piece in drum_tracks:
                    if piece in parts:
                        play[piece] = piece
            progression = MSG_SECTION_PART.format(name, CHORDS)
            progressions[progression] = progression_of(chords=chords, every=section.get(EVERY, chord_entry.get(EVERY)))
            for role, entry in pitched:
                if role[ROLE] not in section[PLAYS]:
                    continue
                if FIGURE in entry:
                    chain = MSG_SECTION_PART.format(name, role[ROLE])
                    chains[chain] = [{PROGRESSION: progression}] + [{kind: role[ROLE]} for generator in entry.get(GENERATORS, []) for kind in generator]
                    if role.get(VOICE_LEADING):
                        chains[chain].append({VOICE_LEADING_KIND: NEAR})
                    play[role[ROLE]] = {PART: role[ROLE], CHAINS: [chain]}
                    continue
                part = MSG_SECTION_PART.format(name, role[ROLE])
                if part not in parts:
                    given = section.get(LINES_GIVEN, {}).get(role[ROLE])
                    lines = given or sketched(habits=habits, plan=section[PLAN], chords=chords, scale_type=scale_type, seed=song.get(SEED, 0), answers=bool(role.get(ANSWERS)))
                    if all(all(REST in note for note in line) for line in lines):
                        continue
                    parts[part] = tune_part(lines=lines, role=role, meter=meter, grid=habits[GRID])
                    shaped.append(part)
                if part in parts:
                    play[role[ROLE]] = {PART: part, ONCE: True}
        form.append({SCENE: scene_name, BARS: bars, PLAY: play})
        notes.append(MSG_SCENE.format(count, scene_name, bars))
    generators = {PROGRESSIONS: progressions, **extra}
    if any(role.get(VOICE_LEADING) for role, _ in pitched):
        generators[VOICE_LEADINGS] = {NEAR: dict(NEAR_VOICES)}
    said = '\n'.join(MSG_PICK.format(trait, value) for trait, value in picks.items())
    given = {
        NAME: song[NAME], TITLE: song[TITLE], DESCRIPTION: song.get(DESCRIPTION, song[TITLE]), GENRE: style[GENRE],
        NOTES: MSG_NOTES.format(title=song[TITLE], style=style[TITLE], template=song[TEMPLATE], picks=said, form='\n'.join(notes)),
        SCALES: {scale: {ROOT: song[KEY][ROOT], TYPE: scale_type}}, SCALE: scale, TEMPO: song.get(TEMPO, picks.get(TEMPO, style[TRAITS][TEMPO][USUAL])),
        FEEL: style[FEEL], SHAPED: shaped, INSTRUMENTS: instruments, TRACKS: tracks, DRUM_TRACKS: drum_tracks, GENERATORS: generators, CHAINS: chains,
        PARTS: parts, FORM: form,
    }
    if meter != COMMON_TIME:
        given[TIME_SIGNATURE] = meter
    return given
