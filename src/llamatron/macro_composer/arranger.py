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

import math
import os
import random
from fractions import Fraction

from llamatron.macro_composer.melody import ENGINE, GRID, sketched
from llamatron.macro_composer.melody import ANSWER_RHYTHMS, RHYTHMS, SPAN
from llamatron.macro_composer.notation import ACCIDENTAL, DEGREE, DRUM, FLAT, HITS, LINES, LOUD, NONE, OCTAVE, REST, SHARP, SOFT, STEP, STEPS, VELOCITY, CHORD, clamped, drum_rows
from llamatron.macro_composer.players import player_name
from llamatron.support.safe_yaml import load_safely
from llamatron.strings.errors import ERR_NO_STYLE_FORM, ERR_NO_STYLE_FORMS, ERR_NO_STYLE_KIND, ERR_NO_SUCH_SECTION, ERR_NO_TRAIT_VALUE, ERR_PICK_NEEDS
from llamatron.strings.macro_composer import MSG_MADE_PICK, MSG_MADE_SCENE, MSG_MADE_SONG_NOTES, MSG_PART_AT_LEVEL, MSG_PART_OF_SECTION, MSG_PLAYED_BY, MSG_REPEATED_SCENE, MSG_SECTION_START_PART, MSG_TIMING_CHAIN

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
# The roles a song leaves out of its band, by name.
WITHOUT = 'without'
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
CHORD_TRAIT_FIELD = 'chord_trait'
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
# The fields of a player: a role says which instrument's player plays it, a song gives each instrument's complexity, and a
# style says, for each instrument and complexity, what that player picks and how the player keeps time.
PLAYER = 'player'
PLAYERS = 'players'
SAYS = 'says'
TIMING = 'timing'
UNEVEN = 'uneven'
ADDS = 'adds'
VARIES = 'varies'
CHOICES = 'choices'
SILENCES = 'silences'
FILL_EVERY = 'fill_every'
ALLOWS = 'intensity'
CRASH_START = 'crash'
ENDS = 'ends'
# A song's pick of the engine its tunes are made by, and a role's own voice and habits for it.
MELODY_ENGINE = 'melody_engine'
VOICE = 'voice'
HABITS = 'habits'
STYLE_TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'style_templates')
STYLE_SUFFIX = '.yml'
# A scale's name from its root and type, and what a drum's uneven hits are seeded by: the song's seed, the drum and the section.
SCALE_NAME = '{} {}'
DRUM_SEED = '{} {} {}'
FILE_ENCODING = 'utf-8'
FORMS = 'forms'
LENGTH = 'length'
SECONDS_IN_A_MINUTE = 60
BEATS_IN_A_WHOLE = 4
BUSY = 'busy'
GUITARIFY_OF_PLAYER = 'guitarify'
RUSH = 'rush'
DRAG = 'drag'
RUSHES = 'rushes'
DRAGS = 'drags'
RAW = 'raw'
AMOUNT = 'amount'
GENERATOR_STEPS = 'steps'
GUITARIFIES = 'guitarifies'
# The set's section that holds each kind of generator a value may bring.
SECTION_OF_KIND = {'guitarify': 'guitarifies', 'arp': 'arps', 'strum': 'strums'}
VOICE_LEADING_KIND = 'voice_leading'
HELD_CHORD = '3'
MAJOR = 'major'
BY_SECTION = 'by_section'
# The keys whose home note is the lowest of an octave: a band written for the middle of its range plays an octave up in them.
LOW_ROOTS = ('C', 'C#', 'Db', 'D', 'D#', 'Eb')
SOFT_SHARE = Fraction(2, 3)



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
        raise ValueError(ERR_NO_STYLE_KIND.format(style[NAME], song[TEMPLATE], listed(templates)))
    picks = {**templates[song[TEMPLATE]]}
    picks.update(song.get(PICKS, {}))
    for trait in style[TRAITS]:
        values = values_of(style=style, trait=trait)
        if not values:
            continue
        if trait not in picks:
            fitting = [entry for entry in values.values() if fits(entry=entry, picks=picks)]
            picks[trait] = max(fitting, key=share_of)[VALUE]
        if picks[trait] not in values:
            raise ValueError(ERR_NO_TRAIT_VALUE.format(trait, picks[trait], listed(values)))
    for trait, value in picks.items():
        for needed, wanted in values_of(style=style, trait=trait).get(value, {}).get(NEEDS, {}).items():
            if picks.get(needed) != wanted:
                raise ValueError(ERR_PICK_NEEDS.format(trait, value, needed, wanted, picks.get(needed)))
    return picks


def style_names():
    """The names of the style templates there are."""
    return sorted(name[:-len(STYLE_SUFFIX)] for name in os.listdir(STYLE_TEMPLATES) if name.endswith(STYLE_SUFFIX))


def style_named(name):
    """A style template, read from its file."""
    with open(os.path.join(STYLE_TEMPLATES, name + STYLE_SUFFIX), encoding=FILE_ENCODING) as file:
        return load_safely(file)


def player_of(*, style, instrument, complexity):
    """What a style says of an instrument's player at a complexity, or nothing."""
    return style.get(PLAYERS, {}).get(instrument, {}).get(complexity, {})


def players_in(*, style, roles, levels, section):
    """Each role's player in a section: the song's, held to the complexity the section allows the instrument."""
    return {role[ROLE]: player_of(style=style, instrument=role.get(PLAYER), complexity=level_in(levels=levels, role=role, section=section)) for role in roles}


def level_in(*, levels, role, section):
    """The complexity a role's player plays at in a section, or nothing where the song names no player for the role."""
    if role.get(PLAYER) not in levels:
        return None
    return min(levels[role[PLAYER]], section.get(ALLOWS, {}).get(role[PLAYER], levels[role[PLAYER]]))


def timing_generators(*, move):
    """A track's Rush and Drag: every step moved by the amount the player gives, or neither doing anything, there to be changed."""
    return {kind: ({GENERATOR_STEPS: [True], AMOUNT: move[kind]} if kind in move else {GENERATOR_STEPS: [False]}) for kind in (RUSH, DRAG)}


def uneven_drum(*, part, by, dice):
    """A drum's part as a pattern whose hits each differ a little in loudness, as a person's do."""
    pattern = drum_rows(drum=part[DRUM], hits=part[HITS], loud=part[LOUD], soft=part[SOFT], step_size=part[STEP])
    pattern[VELOCITY] = [None if loud is None else clamped(loud + dice.randint(-by, by)) for loud in pattern[VELOCITY]]
    return {RAW: pattern}


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


def hits_of(marks):
    """A decoration's drum as hits: it says how many steps its bar has and which are soft and which loud."""
    return [LOUD if place in marks.get(LOUD, []) else SOFT if place in marks.get(SOFT, []) else NONE for place in range(marks[STEPS])]


def choice_that_fits(*, choices, picks):
    """The first of a decoration's choices that fits the song's picks, as each drum's hits, or nothing."""
    for choice in choices or []:
        if fits(entry=choice, picks=picks):
            return {piece: hits_of(marks) for piece, marks in choice[BAR].items()}, choice.get(SILENCES, [])
    return {}, []


def widened(*, hits, to):
    """A bar's hits on a finer grid."""
    finer = []
    for hit in hits:
        finer += [hit] + [NONE] * (to // len(hits) - 1)
    return finer


def laid_over(*, bar, more):
    """A bar with a decoration's hits wherever the bar has none."""
    return [added if hit == NONE else hit for hit, added in zip(bar, more)]


def drum_parts(*, style, picks, roles, meter, phrase_bars, drummer, section_bars):
    """Each drum the picks play, as a part some bars long: the kind's own bar, decorated as the drummer decorates it, a bar of
    the bars of each phrase that the drummer varies each a little different, and its last bar the fill. A drummer who says nothing plays the kind's bar
    and the song's fill at the end of every phrase."""
    bars = {}
    for role in roles:
        if role.get(DRUMS):
            for trait in role[DRUMS]:
                bars.update(values_of(style=style, trait=trait)[picks[trait]].get(BAR, {}))
    # A section always ends on the fill, so that it hands over to the next: the part is no longer than divides the section.
    length = math.gcd(drummer.get(FILL_EVERY, phrase_bars) or phrase_bars, section_bars)
    fill, silences = choice_that_fits(choices=drummer.get(FILL), picks=picks)
    if not fill:
        fill = values_of(style=style, trait=FILLS).get(picks.get(FILLS), {}).get(FILL, {})
    if drummer.get(FILL_EVERY) == 0:
        fill, silences = {}, []
    adds, _ = choice_that_fits(choices=drummer.get(ADDS), picks=picks)
    varied = []
    for variation in drummer.get(VARIES, []):
        more, _ = choice_that_fits(choices=variation[CHOICES], picks=picks)
        varied.append((variation[BARS], more))
    parts = {}
    every = [bars, adds, fill] + [more for _, more in varied]
    for piece in list(dict.fromkeys(piece for layer in every for piece in layer)):
        layers = [layer[piece] for layer in every if piece in layer]
        grid = math.lcm(*(len(layer) for layer in layers))
        plain = widened(hits=bars.get(piece, [NONE]), to=grid)
        if piece in adds:
            plain = laid_over(bar=plain, more=widened(hits=adds[piece], to=grid))
        hits = []
        for bar in range(1, length + 1):
            if bar == length and piece in fill:
                hits += widened(hits=fill[piece], to=grid)
            elif bar == length and piece in silences:
                hits += [NONE] * grid
            else:
                played = plain
                for which, more in varied:
                    if piece in more and (bar - 1) % phrase_bars + 1 in which:
                        played = laid_over(bar=played, more=widened(hits=more[piece], to=grid))
                hits += played
        loud = style[LOUDNESS].get(piece, style[LOUDNESS][DRUMS])
        parts[piece] = {DRUM: piece, STEP: step_of(meter=meter, grid=grid), LOUD: loud, SOFT: int(loud * SOFT_SHARE), HITS: hits}
    return parts


def one_hit(*, style, meter, drum):
    """One bar in which a drum is hit once, on the first beat."""
    loud = style[LOUDNESS].get(drum, style[LOUDNESS][DRUMS])
    return {DRUM: drum, STEP: EIGHTH, LOUD: loud, SOFT: loud, HITS: [LOUD] + [NONE] * (int(bar_length(meter) * EIGHTHS_IN_WHOLE) - 1)}


def lasts(note):
    """How many steps a note or a rest of a figure lasts."""
    return note.get(REST, note.get(STEPS, 0))


def with_ending(*, bar, ends):
    """A figure's bar whose last steps are a decoration's notes: what the bar played before them stays, a note they cut into shortened."""
    room = sum(lasts(note) for note in bar) - sum(lasts(note) for note in ends)
    kept = []
    for note in bar:
        if room <= 0:
            break
        length = min(lasts(note), room)
        kept.append({**note, (REST if REST in note else STEPS): length})
        room -= length
    return kept + [dict(note) for note in ends]


def decorated_figure(*, bars, player, phrase_bars):
    """A figure as a player plays it: a phrase of its bars, the bars the player varies ending in the player's own notes. A player
    who varies nothing plays the figure as written, and a variation written on a grid the figure's does not divide by is left out."""
    grid = sum(lasts(note) for note in bars[0])
    fitting = [variation for variation in player.get(VARIES, []) if ENDS in variation and grid % variation[GRID] == 0]
    if not fitting or phrase_bars % len(bars):
        return [[dict(note) for note in bar] for bar in bars]
    phrase = [[dict(note) for note in bars[count % len(bars)]] for count in range(phrase_bars)]
    for variation in fitting:
        finer = grid // variation[GRID]
        ends = [{**note, (REST if REST in note else STEPS): lasts(note) * finer} for note in variation[ENDS]]
        for bar in variation[BARS]:
            phrase[bar - 1] = with_ending(bar=phrase[bar - 1], ends=ends)
    return phrase


def figure_part(*, entry, role, meter, player, phrase_bars):
    """A value's figure as a tune's part, as a player plays it; the figure's bars are its lines."""
    bars = entry[FIGURE]
    grid = sum(lasts(note) for note in bars[0])
    return {STEP: step_of(meter=meter, grid=grid), OCTAVE: role[OCTAVE], VELOCITY: role[VELOCITY],
            LINES: decorated_figure(bars=bars, player=player, phrase_bars=phrase_bars)}


def held_part(*, role, meter, chord):
    """One bar of the home note or chord, held."""
    note = {DEGREE: 1, STEPS: int(bar_length(meter) * EIGHTHS_IN_WHOLE)}
    if chord:
        note[CHORD] = HELD_CHORD
    return {STEP: EIGHTH, OCTAVE: role[OCTAVE], VELOCITY: role[VELOCITY], LINES: [[note]]}


def tune_part(*, lines, role, meter, grid):
    return {STEP: step_of(meter=meter, grid=grid), OCTAVE: role[OCTAVE], VELOCITY: role[VELOCITY], LINES: lines}


def habits_of(*, habits, player):
    """A style's melody habits as a player keeps them: a wider or narrower range, and the busier rhythms for a busy player."""
    kept = {**habits, **({SPAN: player[SPAN]} if SPAN in player else {})}
    if player.get(BUSY):
        kept[RHYTHMS] = habits[ANSWER_RHYTHMS]
    return kept


def band_said(*, style, song, roles):
    """Who plays, for the notes: each instrument's player by name, with what the style says of the player."""
    said = []
    for instrument, complexity in song.get(PLAYERS, {}).items():
        if any(role.get(PLAYER) == instrument for role in roles):
            player = player_of(style=style, instrument=instrument, complexity=complexity)
            said.append(MSG_PLAYED_BY.format(instrument, player_name(instrument=instrument, complexity=complexity), player.get(SAYS, '')).strip())
    return said


def section_of(*, name, style, song):
    """A section as the song describes it over what the style says of a section of its name."""
    of_song = song.get(SECTIONS, {}).get(name, {})
    kind = of_song.get(KIND, name)
    if kind not in style[SECTIONS] and not of_song:
        raise ValueError(ERR_NO_SUCH_SECTION.format(name))
    return {**style[SECTIONS].get(kind, {}), **of_song, KIND: kind}


def tempo_of(*, style, song, picks):
    return song.get(TEMPO, picks.get(TEMPO, style[TRAITS][TEMPO][USUAL]))


def forms_of(*, style, song):
    """The forms a style suggests for the song's kind, each with how common it is, or the style's usual ones."""
    forms = style.get(FORMS, {})
    return forms.get(song[TEMPLATE]) or forms.get(USUAL, [])


def seconds_of(*, sections, style, song, meter, tempo):
    """How long a form lasts: its sections' bars at the song's tempo."""
    bars = 0
    for name in sections:
        section = section_of(name=name, style=style, song=song)
        bars += 1 if section.get(HELD) else section[BARS]
    return float(bars * bar_length(meter) * BEATS_IN_A_WHOLE * SECONDS_IN_A_MINUTE / tempo)


def form_of(*, style, song, meter, tempo):
    """The sections a song plays, in order. A song may list them; or name one of the forms its style suggests for its kind;
    or say how long it should last, in seconds, and take the suggested form that comes nearest, a longer form being one written
    with more themes and changes and never the same form repeated; or say nothing and take the commonest."""
    given = song.get(FORM)
    if isinstance(given, list):
        return given
    forms = forms_of(style=style, song=song)
    if given is not None:
        named = [form for form in forms if form[NAME] == given]
        if not named:
            raise ValueError(ERR_NO_STYLE_FORM.format(style[NAME], given, song[TEMPLATE]))
        return named[0][SECTIONS]
    if not forms:
        raise ValueError(ERR_NO_STYLE_FORMS.format(style[NAME]))
    if LENGTH in song:
        return min(forms, key=lambda form: abs(seconds_of(sections=form[SECTIONS], style=style, song=song, meter=meter, tempo=tempo) - song[LENGTH]))[SECTIONS]
    return max(forms, key=share_of)[SECTIONS]


def arranged(*, style, song):
    """A song's picks as a MacroComposer input."""
    picks = picked(style=style, song=song)
    meter = str(picks.get(METER, COMMON_TIME))
    tempo = tempo_of(style=style, song=song, picks=picks)
    form_names = form_of(style=style, song=song, meter=meter, tempo=tempo)
    lift = 1 if song[KEY][ROOT] in LOW_ROOTS else 0
    roles = [{**role, OCTAVE: role[OCTAVE] + lift} if OCTAVE in role else role for role in style[ROLES]]
    phrase_bars = style.get(PHRASE_BARS, DEFAULT_PHRASE_BARS)
    chord_trait = style.get(CHORD_TRAIT_FIELD, CHORD_TRAIT)
    chord_entry = values_of(style=style, trait=chord_trait)[picks[chord_trait]]
    scale_type = song[KEY].get(TYPE, chord_entry.get(SCALE_TYPE, MAJOR))
    scale = SCALE_NAME.format(song[KEY][ROOT], scale_type.capitalize())
    habits = style[MELODY] if GRID in style[MELODY] else style[MELODY][meter]
    levels = song.get(PLAYERS, {})
    without = song.get(WITHOUT, [])
    no_drums = any(role.get(DRUMS) and role[ROLE] in without for role in roles)
    playing = players_in(style=style, roles=roles, levels=levels, section={})
    drummer = next((playing[role[ROLE]] for role in roles if role.get(DRUMS)), {})
    drum_traits = [trait for role in roles for trait in role.get(DRUMS, [])] + [FILLS]
    parts = {}
    drum_sets = {}
    drums_of = {}
    for name in form_names:
        section = section_of(name=name, style=style, song=song)
        if no_drums or section.get(HELD) or DRUMS not in section[PLAYS] or name in drums_of:
            continue
        level = min(levels[DRUMS], section.get(ALLOWS, {}).get(DRUMS, levels[DRUMS])) if DRUMS in levels else None
        changed = {trait: value for trait, value in section.get(PICKS, {}).items()
                   if trait in drum_traits and fits(entry=values_of(style=style, trait=trait)[value], picks=picks)}
        plays = player_of(style=style, instrument=DRUMS, complexity=level)
        key = (level, tuple(sorted(changed.items())), math.gcd(plays.get(FILL_EVERY, phrase_bars) or phrase_bars, section[BARS]))
        if key not in drum_sets:
            made = drum_parts(style=style, picks={**picks, **changed}, roles=roles, meter=meter, phrase_bars=phrase_bars, drummer=plays, section_bars=section[BARS])
            drum_sets[key] = {}
            for piece, part in made.items():
                if plays.get(UNEVEN):
                    part = uneven_drum(part=part, by=plays[UNEVEN], dice=random.Random(DRUM_SEED.format(song.get(SEED, 0), piece, section[KIND])))
                named = piece if key[:2] == (levels.get(DRUMS), ()) and piece not in parts else MSG_PART_OF_SECTION.format(piece, section[KIND])
                parts[named] = part
                drum_sets[key][piece] = named
        drums_of[name] = drum_sets[key]
    drum_tracks = list(dict.fromkeys(piece for pieces in drums_of.values() for piece in pieces))
    timing = {piece: timing_generators(move=drummer.get(TIMING, {}).get(piece, {})) for piece in drum_tracks}
    # The user's rule for a song that is made: the chords first, then the lead and the backing, the bass, and the drums last.
    tracks = {}
    instruments = {DRUM_KIT: None}
    progressions = {}
    chains = {}
    extra = {}
    shaped = []
    pitched = []
    for role in roles:
        if role.get(DRUMS) or role[ROLE] in without:
            continue
        entry = values_of(style=style, trait=role[TRAIT])[picks[role[TRAIT]]]
        if SOUND not in entry:
            continue
        instruments[entry[SOUND]] = style[SOUNDS][entry[SOUND]]
        tracks[role[ROLE]] = entry[SOUND]
        pitched.append((role, entry))
        if FIGURE in entry:
            parts[role[ROLE]] = figure_part(entry=entry, role=role, meter=meter, player=playing[role[ROLE]], phrase_bars=phrase_bars)
            shaped.append(role[ROLE])
        parts[MSG_PART_OF_SECTION.format(role[ROLE], HELD)] = held_part(role=role, meter=meter, chord=any(CHORD in note for bar in entry.get(FIGURE, []) for note in bar))
        timing[role[ROLE]] = timing_generators(move=playing[role[ROLE]].get(TIMING, {}))
        for generator in entry.get(GENERATORS, []):
            for kind, settings in generator.items():
                extra.setdefault(SECTION_OF_KIND[kind], {})[role[ROLE]] = dict(settings)
        if role[ROLE] in extra.get(GUITARIFIES, {}):
            extra[GUITARIFIES][role[ROLE]].update(playing[role[ROLE]].get(GUITARIFY_OF_PLAYER, {}))
    for track, moves in timing.items():
        chains[MSG_TIMING_CHAIN.format(track)] = [{RUSH: track}, {DRAG: track}]
        extra.setdefault(RUSHES, {})[track] = moves[RUSH]
        extra.setdefault(DRAGS, {})[track] = moves[DRAG]
    tracks.update({piece: DRUM_KIT for piece in drum_tracks})
    form = []
    notes = []
    met = {}
    for count, name in enumerate(form_names, start=1):
        section = section_of(name=name, style=style, song=song)
        met[name] = met.get(name, 0) + 1
        scene_name = name if met[name] == 1 else MSG_REPEATED_SCENE.format(name, met[name])
        bars = 1 if section.get(HELD) else section[BARS]
        chords = [chord_of(chord) for chord in section.get(CHORDS) or chord_entry.get(BY_SECTION, {}).get(section[KIND]) or chord_entry[PATTERN]]
        play = {}
        if section.get(HELD):
            if not no_drums:
                held = MSG_PART_OF_SECTION.format(CRASH, HELD)
                parts[held] = one_hit(style=style, meter=meter, drum=CRASH)
                parts[MSG_PART_OF_SECTION.format(KICK, HELD)] = one_hit(style=style, meter=meter, drum=KICK)
                if CRASH not in tracks:
                    tracks[CRASH] = DRUM_KIT
                    drum_tracks.append(CRASH)
                play[CRASH] = held
            if KICK in tracks:
                play[KICK] = {PART: MSG_PART_OF_SECTION.format(KICK, HELD), ONCE: True}
            for role, entry in pitched:
                if FIGURE in entry and role[ROLE] in section.get(PLAYS, [role[ROLE]]):
                    play[role[ROLE]] = {PART: MSG_PART_OF_SECTION.format(role[ROLE], HELD), ONCE: True}
        else:
            for piece, part in drums_of.get(name, {}).items():
                play[piece] = {PART: part, CHAINS: [MSG_TIMING_CHAIN.format(piece)]}
            if section.get(CRASH_START) and name in drums_of:
                start = MSG_SECTION_START_PART.format(CRASH)
                parts[start] = one_hit(style=style, meter=meter, drum=CRASH)
                if CRASH not in tracks:
                    tracks[CRASH] = DRUM_KIT
                    drum_tracks.append(CRASH)
                play.setdefault(CRASH, {PART: start, ONCE: True})
            here = players_in(style=style, roles=roles, levels=levels, section=section)
            progression = MSG_PART_OF_SECTION.format(name, CHORDS)
            progressions[progression] = progression_of(chords=chords, every=section.get(EVERY, chord_entry.get(EVERY)))
            for role, entry in pitched:
                if role[ROLE] not in section[PLAYS]:
                    continue
                if FIGURE in entry:
                    chain = MSG_PART_OF_SECTION.format(name, role[ROLE])
                    chains[chain] = [{PROGRESSION: progression}] + [{kind: role[ROLE]} for generator in entry.get(GENERATORS, []) for kind in generator]
                    if role.get(VOICE_LEADING):
                        chains[chain].append({VOICE_LEADING_KIND: NEAR})
                    chains[chain] += [{RUSH: role[ROLE]}, {DRAG: role[ROLE]}]
                    figure = role[ROLE]
                    if here[role[ROLE]] != playing[role[ROLE]]:
                        figure = MSG_PART_AT_LEVEL.format(role[ROLE], level_in(levels=levels, role=role, section=section))
                        if figure not in parts:
                            parts[figure] = figure_part(entry=entry, role=role, meter=meter, player=here[role[ROLE]], phrase_bars=phrase_bars)
                            shaped.append(figure)
                    play[role[ROLE]] = {PART: figure, CHAINS: [chain]}
                    continue
                part = MSG_PART_OF_SECTION.format(name, role[ROLE])
                if part not in parts:
                    given = section.get(LINES_GIVEN, {}).get(role[ROLE])
                    lines = given or sketched(habits={**habits_of(habits=habits, player=here[role[ROLE]]), **role.get(HABITS, {}), **song.get(MELODY, {})}, plan=section[PLAN], chords=chords, scale_type=scale_type, seed=song.get(SEED, 0), answers=bool(role.get(ANSWERS)),
                                               engine=song.get(MELODY_ENGINE, role.get(ENGINE)), voice=role.get(VOICE))
                    if all(all(REST in note for note in line) for line in lines):
                        continue
                    parts[part] = tune_part(lines=lines, role=role, meter=meter, grid=habits[GRID])
                    shaped.append(part)
                if part in parts:
                    play[role[ROLE]] = {PART: part, ONCE: True, CHAINS: [MSG_TIMING_CHAIN.format(role[ROLE])]}
        if not play:
            # Nothing of the song's picks plays in this section, as pads alone where the song has no chord part: it is left out.
            met[name] -= 1
            continue
        form.append({SCENE: scene_name, BARS: bars, PLAY: play})
        notes.append(MSG_MADE_SCENE.format(count, scene_name, bars))
    generators = {PROGRESSIONS: progressions, **extra}
    if any(role.get(VOICE_LEADING) for role, _ in pitched):
        generators[VOICE_LEADINGS] = {NEAR: dict(NEAR_VOICES)}
    said = '\n'.join(band_said(style=style, song=song, roles=roles) + [MSG_MADE_PICK.format(trait, value) for trait, value in picks.items()])
    given = {
        NAME: song[NAME], TITLE: song[TITLE], DESCRIPTION: song.get(DESCRIPTION, song[TITLE]), GENRE: style[GENRE],
        NOTES: MSG_MADE_SONG_NOTES.format(title=song[TITLE], style=style[TITLE], template=song[TEMPLATE], picks=said, form='\n'.join(notes)),
        SCALES: {scale: {ROOT: song[KEY][ROOT], TYPE: scale_type}}, SCALE: scale, TEMPO: tempo,
        FEEL: style[FEEL], SHAPED: shaped, INSTRUMENTS: instruments, TRACKS: tracks, DRUM_TRACKS: drum_tracks, GENERATORS: generators, CHAINS: chains,
        PARTS: parts, FORM: form,
    }
    if meter != COMMON_TIME:
        given[TIME_SIGNATURE] = meter
    return given
