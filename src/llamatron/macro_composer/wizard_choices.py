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
"""What the song wizard is told, and the song made from it.

A WizardChoices holds the choices of one run of the wizard: the genre, a style template; the subgenre, one of the template's
kinds; the key, the tempo and the form. Choosing a subgenre fills the rest in with what the subgenre usually has, so that a
person who chooses nothing more still gets a song that sounds right, and may then change anything. The choices are kept in
the song they made, as plain data, so that the wizard can start from them again; the seed that fixed every roll of the
dice is kept with them and never shown.
"""

import copy
import functools
import random

from llamatron.composition.file_format import Section
from llamatron.composition.limits import MAX_TEMPO, MIN_TEMPO
from llamatron.composition.setlist import Setlist
from llamatron.macro_composer.interplay import LEAST_BUSY as LEAST_BUSY_BESIDE, MOST_BUSY as MOST_BUSY_BESIDE, USUAL_BUSY as USUAL_BUSY_BESIDE, WAITS, WAYS as WAYS_BESIDE
from llamatron.macro_composer.characters import GAUGES as PLAYER_GAUGES, HIGHEST as HIGHEST_PLACE, LOWEST as LOWEST_PLACE, PRESET_PLACE, gauges_of, preset
from llamatron.macro_composer.arranger import (
    ACCIDENTAL_MARKS, BY_SECTION, PATTERN, chord_of, COMMON_TIME, DEFAULT_PHRASE_BARS, DRUMS, DRUM_TRACKS, EACH_SECTION, FILLS_COME, FILL_EVERY, KIND, PARTS, PHRASE_BARS, QUIET_NOTES, MELODY_ENGINE, METER, PICKS, ROLE_SOUNDS, ROLE_TITLE, ROLE_TITLES, SOUNDS, WITHOUT_PIECES, PLAYER, PLAYERS, ROLE, ROLES, SOUND, TRAIT, VALUE, WITHOUT, bar_length, fits,
    BARS, CHORD_TRAIT, CHORD_TRAIT_FIELD, FORM, HELD, PLAYS, GENRE, KEY, NAME, ROOT, SCALE_TYPE, SECTIONS, SEED, STYLE, TEMPLATE, TEMPLATES, TEMPO, TITLE, TRAITS, TYPE, USUAL,
    BREAK, BREAK_CUT, HIGHEST_NOTE, KEPT_BESIDE_A_BREAK, LOWEST_NOTE, MELODY, NO_BREAK, PIECE_SOUNDS, PLAYED_DRUM, PLAYED_NOTE, PLAYED_SOUND,
    ANSWERS, BESIDE, BESIDE_BUSY, BESIDE_WAYS, FIGURE,
    arranged, forms_of, picked, player_of, section_of, share_in, share_of, style_named, style_names, values_of,
)
from llamatron.macro_composer.composer import composed
from llamatron.composition.song_file_error import SongFileError
from llamatron.macro_composer.breaks import LEAST_CUT, MOST_CUT, break_names
from llamatron.macro_composer.notation import ACCIDENTAL, DEGREE, KIT, OCTAVE
from llamatron.macro_composer.melody import CHROMATIC, DEFAULT_EVOLVE, EVOLVE, HALF_STEPS, LEAPS, MOVE, NOTES_IN_OCTAVE, DEFAULT_GAUGES, EVOLVING, GRID, HIGHEST_GAUGE, HOOK, LOWEST_GAUGE, ROTATE, ROTATIONS, SERIAL, SMART, STEP_WALK
from llamatron.music.note import ROOT_NAMES, SEMITONES_ABOVE_C
from llamatron.playback.song_renderer import SongRenderer
from llamatron.composition.limits import GM_FAMILY_SIZE, MAX_GM_SOUND, MIN_GM_SOUND
from llamatron.strings.labels import MSG_GM_SOUNDS
from llamatron.strings.marks import MSG_WIZARD_SECTION_NUMBERED, MSG_WIZARD_SECTION_VARIANT
from llamatron.support.version import VERSION as A_VERSION
from llamatron.strings.errors import ERR_WIZARD_FILLS_BUSY, ERR_WIZARD_NO_SUCH_ANSWERER, ERR_WIZARD_NO_SUCH_WAY_BESIDE, ERR_WIZARD_SECTION_HAS_NO_ROLE, ERR_WIZARD_NO_SUCH_PLAYER_GAUGE, ERR_WIZARD_PLAYER_GAUGE, ERR_WIZARD_PIECE_HAS_NO_NOTE, ERR_WIZARD_PIECE_NOTE, ERR_WIZARD_PIECE_SOUND, ERR_WIZARD_BREAK_CUT, ERR_WIZARD_MELODY_NUMBER, ERR_WIZARD_MELODY_SWITCH, ERR_WIZARD_NO_SUCH_MELODY_SETTING, ERR_WIZARD_GAUGE, ERR_WIZARD_NO_SUCH_BREAK, ERR_WIZARD_BAD_SECTIONS, ERR_WIZARD_FILLS, ERR_WIZARD_QUIET_NOTES, ERR_WIZARD_LAST_PIECE, ERR_WIZARD_NO_SUCH_PIECE, ERR_WIZARD_GUITARISTS, ERR_WIZARD_BAND_SOUNDS, ERR_WIZARD_SOUND, ERR_WIZARD_NO_SUCH_MELODY, ERR_WIZARD_NO_HOOK, ERR_WIZARD_BUSY, ERR_WIZARD_LAST_PLAYER, ERR_WIZARD_LAST_SECTION, ERR_WIZARD_NO_SUCH_SECTION, ERR_WIZARD_NO_SUCH_SECTION_KIND, ERR_WIZARD_SECTION_BARS, ERR_WIZARD_SECTION_NEEDS_PLAYER, ERR_WIZARD_NO_SUCH_FORM, ERR_WIZARD_NO_SUCH_PLAYER, ERR_WIZARD_NO_SUCH_WAY, ERR_WIZARD_NO_WAY, ERR_WIZARD_NO_SUCH_GENRE, ERR_WIZARD_NO_SUCH_ROOT, ERR_WIZARD_NO_SUCH_SCALE_TYPE, ERR_WIZARD_NO_SUCH_SUBGENRE, ERR_WIZARD_NOT_READY, ERR_WIZARD_SEED, ERR_WIZARD_TEMPO

# The fields of the choices as a song keeps them.
SUBGENRE = 'subgenre'
# The ends of a style's usual tempos, in its template.
LOWEST = 'lowest'
HIGHEST = 'highest'
# The scale types a song may be made in, the plainest first, and the root each starts on until one is chosen.
MAJOR = 'major'
# The octave of a player whose style names none.
USUAL_OCTAVE = 4
MINOR = 'minor'
SCALE_TYPES = [MAJOR, MINOR]
USUAL_ROOTS = {MAJOR: 'C', MINOR: 'E'}
# How long a section that is one held chord lasts, in bars.
HELD_BARS = 1
# The seeds a run draws from: large enough that two runs seldom share one, small enough to read in a file.
# What a progression left to chance is drawn by, and how many times the subgenre's usual one counts.
PROGRESSION_SEED = 'progression {}'
USUAL_COUNTS = 2
FIRST_SEED = 1
LAST_SEED = 999999


@functools.cache
def style_of(genre):
    """Return a genre's style template, read once however often it is asked for; nothing changes it."""
    return style_named(genre)


def genre_names():
    """Return the genres there are, by the names their choices are kept under, in the order of their titles."""
    return sorted(style_names(), key=genre_title)


def genre_title(genre):
    """Return a genre's name as people read it."""
    return style_of(genre)[TITLE]


# How often a fill comes, by position: never, at the end of each section, every four bars, every two.
FEWEST_FILLS = 1
EACH_SECTION_FILLS = 2
MOST_FILLS = 4
FILLS_EVERY = {1: 0, 4: 2, 3: 4, 2: EACH_SECTION}
FILLS_KEPT = 'fills'
QUIET_NOTES_KEPT = 'quiet_notes'
# The drum break chosen, kept as its name or as NO_BREAK where a subgenre built on a break plays none, how far it is cut up,
# and the smart melody style's gauges that were moved.
BREAK_KEPT = 'break'
BREAK_CUT_KEPT = 'break_cut'
GAUGES_KEPT = 'melody_gauges'
MELODY_SETTINGS_KEPT = 'melody_settings'
HOOK_KEPT = 'hook'
# What pieces of the kit sound as, kept as the song's picks hold them, and the note a piece first plays in a General MIDI sound.
PIECE_SOUNDS_KEPT = 'piece_sounds'
PLAYER_GAUGES_KEPT = 'player_gauges'
# The answers remembered until a choice changes.
PIECES_ANSWER = 'pieces'
QUIET_NOTES_ANSWER = 'quiet notes'
BARS_ANSWER = 'bars offered'
# What is kept of the player beside the tune: who answers, the one thing done in every section or None for the genre's plan, and how busy; and a section's own choice.
BESIDE_KEPT = 'beside'
BY = 'by'
WAY = 'way'
BUSY_BESIDE = 'busy'
# What a genre says of playing beside the tune.
INTERPLAY = 'interplay'
PLAN = 'plan'
BY_SUBGENRE = 'by_subgenre'
USUAL_PIECE_NOTE = 48
# The key a song keeps the kit's pieces that are switched off under.
PIECES_OFF_KEPT = 'pieces_off'
# One guitarist or two, and the key a template describes its one guitarist under, with the players and the way it names.
TWO_GUITARISTS = 2
ONE_GUITARIST_COUNT = 1
GUITARIST_COUNTS = (ONE_GUITARIST_COUNT, TWO_GUITARISTS)
GUITARISTS_KEPT = 'guitarists'
ONE_GUITARIST = 'one_guitarist'
CHORDS_PLAYER = 'chords'
SOLO_PLAYER = 'solo'
SOLO_WAY = 'way'
# The band's Sounds: every player's usual sound, or the nearest acoustic, electric or synthetic one.
USUAL_SOUNDS = 'usual'
ACOUSTIC = 'acoustic'
ELECTRIC = 'electric'
SYNTH = 'synth'
BAND_SOUNDS = (USUAL_SOUNDS, ACOUSTIC, ELECTRIC, SYNTH)
SOUNDS_KEPT = 'sounds'
BAND_SOUNDS_KEPT = 'band_sounds'
# The key a template keeps the sounds that stand in for a player under, by player and subgenre.
STAND_INS = 'stand_ins'
# General MIDI's families, eight sounds each, by their place; the last two, percussive sounds and sound effects, play no notes a part can use.
PIANOS = 0
ORGANS = 2
GUITARS = 3
BASSES = 4
STRINGS = 5
ENSEMBLES = 6
BRASS = 7
REEDS = 8
PIPES = 9
SYNTH_LEADS = 10
SYNTH_PADS = 11
# The nearest sound of each kind for a sound of a family, by General MIDI number: an acoustic band's guitar is a steel-string
# guitar, its bass an upright, its keyboard a piano; an electric band's keyboard is an electric piano; a synth band's guitar a saw lead.
NEAREST = {
    ACOUSTIC: {PIANOS: 1, ORGANS: 1, GUITARS: 26, BASSES: 33, SYNTH_LEADS: 74, SYNTH_PADS: 49},
    ELECTRIC: {PIANOS: 5, GUITARS: 28, BASSES: 34, SYNTH_LEADS: 30, SYNTH_PADS: 17},
    SYNTH: {PIANOS: 6, ORGANS: 90, GUITARS: 82, BASSES: 39, STRINGS: 51, ENSEMBLES: 55, BRASS: 63, REEDS: 81, PIPES: 83},
}
# The sounds that are already of each kind and so stay: acoustic pianos, guitars and bass; electric pianos, guitars and basses; synth basses and strings.
KEPT_BY = {
    ACOUSTIC: (1, 2, 3, 4, 25, 26, 33),
    ELECTRIC: (5, 6, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38),
    SYNTH: (39, 40, 51, 52, 55, 63, 64),
}


def family_of(sound):
    """Return the place of the General MIDI family a sound is in."""
    return (sound - MIN_GM_SOUND) // GM_FAMILY_SIZE


# The melody styles, and the key a song keeps the one chosen under.
MELODY_STYLES = (SMART, STEP_WALK, SERIAL, EVOLVING)
# The melody styles the seven gauges steer.
GAUGED_STYLES = (SMART,)
# A melody style's own settings, by the style, the usual style's under None: for the evolving style how far each new line moves
# up and how many notes later it starts, each a number with its lowest and highest; for the serial style whether the row is
# all twelve notes, whether a note may leap to any octave and whether a form of the row may start anywhere in it, each true or
# false with what it is where the genre does not say. How far a tune ranges is not one: it is the Range gauge of the player.
MELODY_SETTINGS_OF = {None: (), STEP_WALK: (), SMART: (), EVOLVING: (MOVE, ROTATE), SERIAL: (CHROMATIC, LEAPS, ROTATIONS)}
MELODY_NUMBERS = {MOVE: (0, 4), ROTATE: (0, 4)}
MELODY_SWITCHES = {CHROMATIC: False, LEAPS: False, ROTATIONS: True}
EVOLVE_SETTINGS = (MOVE, ROTATE)
MELODY_STYLE = 'melody_style'
# The traits of the whole song the wizard offers: the chords, under either name a genre gives them, the feel and the drum fills.
PROGRESSION_TRAITS = ('chords', 'harmony')
FILLS_TRAITS = ('fills',)
# The key a song keeps its own sections under, and the letter the first section that differs from its kind's first is named with.
OWN_SECTIONS = 'own_sections'
FIRST_VARIANT_LETTER = 'a'
# How near a made section's length must be to the length asked, in seconds: far less than any bar lasts.
PART_OF_A_BAR = 0.01
# A section may be half or twice its kind's usual length.
HALF = 2
# How busy a player may be, and how busy each is until chosen: a little past the plainest, so that a song has turns and fills.
LEAST_BUSY = 1
MOST_BUSY = 4
USUAL_BUSY = 2
def own_copy_of(entry):
    """Return a section's entry sharing no list with the entry given."""
    return {field: (list(value) if isinstance(value, list) else value) for field, value in entry.items()}


@functools.cache
def melody_works(*, genre, subgenre, style):
    """Return whether a subgenre's tunes can be sketched by a melody style, found by making a song, once: a genre whose tunes
    are written as rows, with no rhythms to walk, takes only the style it was written for."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.set_seed(FIRST_SEED)
    try:
        Setlist.from_data(data=composed(given=arranged(style=style_of(genre), song={**choices.song_picks(subgenre), MELODY_ENGINE: style}), version=A_VERSION))
    except (ValueError, IndexError, KeyError, SongFileError):
        return False
    return True


@functools.cache
def melody_is_usual(*, genre, subgenre, style):
    """Return whether a melody style sketches a subgenre's tunes just as the genre does unasked, found by making both, once:
    such a style is the usual one under its own name, and is nothing to choose."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.set_seed(FIRST_SEED)
    song = choices.song_picks(subgenre)
    return arranged(style=style_of(genre), song={**song, MELODY_ENGINE: style})[PARTS] == arranged(style=style_of(genre), song=song)[PARTS]


@functools.cache
def hook_matters(*, genre, subgenre, form):
    """Return whether a hook changes a subgenre's song in a form, found by making the song with one and without, once: where
    nobody carries a tune in the sections that mark a hook, a hook is nothing to choose."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.set_form(form)
    choices.set_seed(FIRST_SEED)
    song = choices.song_picks(subgenre)
    return arranged(style=style_of(genre), song={**song, HOOK: True})[PARTS] != arranged(style=style_of(genre), song={**song, HOOK: False})[PARTS]


@functools.cache
def bars_work(*, genre, subgenre, kind, bars, plays=None):
    """Return whether a subgenre's parts can fill a section of a kind at a length, found by making one and measuring it, once:
    some parts are written over several bars and divide only some lengths, and some, as a chorus of twelve bars, last as long
    as they are written whatever is asked. Given the section's players, only their parts are asked, since a part that sits
    out cannot time the section."""
    style = style_of(genre)
    song = {NAME: kind, TITLE: kind, STYLE: genre, TEMPLATE: subgenre, KEY: {ROOT: USUAL_ROOTS[MAJOR], TYPE: MAJOR}, SEED: FIRST_SEED,
            FORM: [kind], SECTIONS: {kind: {KIND: kind, BARS: bars, **({} if plays is None else {PLAYS: list(plays)})}}}
    try:
        given = arranged(style=style, song=song)
        made = Setlist.from_data(data=composed(given=given, version=A_VERSION)).get_song(kind)
        seconds = sum(float(scene.seconds) for scene in SongRenderer(made).estimate())
    except (ValueError, SongFileError):
        return False
    wanted = float(bars * bar_length(str(picked(style=style, song=song).get(METER, COMMON_TIME))) * QUARTERS_IN_WHOLE * SECONDS_IN_MINUTE / made.get_tempo())
    return abs(seconds - wanted) < PART_OF_A_BAR


# A tempo counts quarter notes a minute.
QUARTERS_IN_WHOLE = 4
SECONDS_IN_MINUTE = 60


class WizardChoices:
    """The choices of one run of the song wizard."""

    __slots__ = ('_genre', '_subgenre', '_root', '_scale_type', '_tempo', '_form', '_seed', '_ways', '_levels', '_own_gauges', '_beside', '_without', '_sections', '_melody', '_hook', '_sounds', '_band_sounds', '_guitarists', '_pieces_off', '_break', '_break_cut', '_gauges', '_piece_sounds', '_fills', '_quiet_notes', '_melody_settings', '_answers', '_answers_of')

    def __init__(self):
        # Answers found by making the song, each kept until a choice changes.
        self._answers = {}
        self._answers_of = None
        self._genre = None
        self._subgenre = None
        self._root = None
        self._scale_type = None
        self._tempo = None
        self._form = None
        self._seed = None
        # The band: each trait's way of playing where one was chosen, how busy each instrument's player is, and the players left out.
        self._ways = {}
        self._levels = {}
        self._own_gauges = {}
        self._beside = None
        self._without = []
        # The form's sections once a person has changed them, each its kind and what it changes of the kind; None while a suggested form is followed.
        self._sections = None
        # The melody style chosen for the song's tunes, or None for the one the genre gives each player.
        self._melody = None
        # Whether the song has a hook, or None while the genre says.
        self._hook = None
        # The sounds chosen: the band's, one of BAND_SOUNDS, which every player follows, and each player's own General MIDI sound, which overrides it.
        self._band_sounds = USUAL_SOUNDS
        self._sounds = {}
        # How many guitarists the band has: two, one for the chords and one for the solo, or one who plays both.
        self._guitarists = TWO_GUITARISTS
        # The pieces of the drum kit switched off.
        self._pieces_off = []
        # How often a fill comes, a position from FEWEST_FILLS to MOST_FILLS, or None while the drummer decides; and whether the snare's quiet notes are played.
        self._fills = None
        self._quiet_notes = True
        self._break = None
        self._break_cut = None
        self._gauges = {}
        self._melody_settings = {}
        self._piece_sounds = {}

    # Reading and keeping the choices.

    @classmethod
    def from_data(cls, data):
        """Return the choices a song kept, leaving out whatever no longer fits, as a genre renamed since: what is left out is chosen again."""
        choices = cls()
        setters = [(GENRE, choices.set_genre), (SUBGENRE, choices.set_subgenre), (ROOT, choices.set_root), (TYPE, choices.set_scale_type), (TEMPO, choices.set_tempo), (FORM, choices.set_form), (SEED, choices.set_seed)]
        for field, setter in setters:
            if (data or {}).get(field) is not None:
                try:
                    setter(data[field])
                except (TypeError, ValueError):
                    pass
        if choices.is_ready():
            choices._read_band(data)
        return choices

    def _read_band(self, data):
        """Take the band a song kept, each part through its setter, leaving out what no longer fits. A song kept before the
        band could be chosen names no levels, and is read as having none, so that the same choices still make the same song."""
        self._levels = {}
        self._own_gauges = {}
        # A song kept before answering could be chosen keeps to what was made then.
        self._beside = None
        kept = [(self.set_way, [dict(trait=trait, value=value) for trait, value in (data.get(PICKS) or {}).items()]),
                (self._set_level, [dict(player=player, level=level) for player, level in (data.get(PLAYERS) or {}).items()]),
                (self._set_kept_player_gauge, [dict(player=player, gauge=gauge, place=place) for player, places in (data.get(PLAYER_GAUGES_KEPT) or {}).items() for gauge, place in places.items()]),
                (self.set_role_in, [dict(role=role, on=False) for role in data.get(WITHOUT) or []]),
                (self.set_piece_on, [dict(piece=piece, on=False) for piece in data.get(PIECES_OFF_KEPT) or []]),
                (self._set_kept_fills, [dict(position=data[FILLS_KEPT])] if data.get(FILLS_KEPT) is not None else []),
                (self._set_kept_quiet_notes, [dict(on=False)] if data.get(QUIET_NOTES_KEPT) is False else []),
                (self._set_kept_break, [dict(name=data[BREAK_KEPT])] if data.get(BREAK_KEPT) else []),
                (self._set_kept_piece_sound, [dict(piece=piece, sounds_as=sounds_as) for piece, sounds_as in (data.get(PIECE_SOUNDS_KEPT) or {}).items()]),
                (self._set_kept_break_cut, [dict(position=data[BREAK_CUT_KEPT])] if data.get(BREAK_CUT_KEPT) is not None else []),
                (self._set_kept_guitarists, [dict(count=data[GUITARISTS_KEPT])] if data.get(GUITARISTS_KEPT) else []),
                (self._set_kept_band_sounds, [dict(sounds=data[BAND_SOUNDS_KEPT])] if data.get(BAND_SOUNDS_KEPT) else []),
                (self.set_sound, [dict(role=role, sound=sound) for role, sound in (data.get(SOUNDS_KEPT) or {}).items()]),
                (self._set_kept_beside, [dict(kept=data[BESIDE_KEPT])] if isinstance(data.get(BESIDE_KEPT), dict) else []),
                (self.set_own_sections, [dict(sections=data[OWN_SECTIONS])] if data.get(OWN_SECTIONS) else []),
                (self._set_kept_melody, [dict(style=data[MELODY_STYLE])] if data.get(MELODY_STYLE) else []),
                (self._set_kept_hook, [dict(on=data[HOOK_KEPT])] if isinstance(data.get(HOOK_KEPT), bool) else []),
                (self.set_gauge, [dict(name=name, position=position) for name, position in (data.get(GAUGES_KEPT) or {}).items()]),
                (self._set_kept_melody_setting, [dict(name=name, value=value) for name, value in (data.get(MELODY_SETTINGS_KEPT) or {}).items()])]
        for setter, every in kept:
            for named in every:
                try:
                    setter(**named)
                except (TypeError, ValueError):
                    pass

    def to_data(self):
        """Return the choices made, as plain data a song keeps."""
        held = {GENRE: self._genre, SUBGENRE: self._subgenre, ROOT: self._root, TYPE: self._scale_type, TEMPO: self._tempo, FORM: self._form, SEED: self._seed,
                PICKS: dict(self._ways) or None, PLAYERS: dict(self._levels) or None, WITHOUT: list(self._without) or None,
                PLAYER_GAUGES_KEPT: {player: dict(places) for player, places in self._own_gauges.items() if places} or None,
                BESIDE_KEPT: dict(self._beside) if self._beside is not None else None,
                OWN_SECTIONS: [own_copy_of(entry) for entry in self._sections] if self._sections is not None else None,
                MELODY_STYLE: self._melody, HOOK_KEPT: self._hook, SOUNDS_KEPT: dict(self._sounds) or None,
                BAND_SOUNDS_KEPT: self._band_sounds if self._band_sounds != USUAL_SOUNDS else None,
                GUITARISTS_KEPT: self._guitarists if self._guitarists != TWO_GUITARISTS else None,
                PIECES_OFF_KEPT: list(self._pieces_off) or None, FILLS_KEPT: self._fills, QUIET_NOTES_KEPT: None if self._quiet_notes else False,
                BREAK_KEPT: self._break, BREAK_CUT_KEPT: self._break_cut, GAUGES_KEPT: dict(self._gauges) or None, MELODY_SETTINGS_KEPT: dict(self._melody_settings) or None,
                PIECE_SOUNDS_KEPT: {piece: dict(sounds_as) for piece, sounds_as in self._piece_sounds.items()} or None}
        return {field: value for field, value in held.items() if value is not None}

    # The genre and the subgenre, which everything else follows.

    def get_genre(self):
        return self._genre

    def set_genre(self, genre):
        """Choose a genre, which leaves the subgenre to be chosen again, since each genre has its own."""
        if genre not in style_names():
            raise ValueError(ERR_WIZARD_NO_SUCH_GENRE.format(value=genre))
        if genre != self._genre:
            self._genre = genre
            self._subgenre = None
            self._form = None
            self._sections = None
            self._melody = None
            self._hook = None
            self._forget_band()

    def subgenres(self):
        """Return the chosen genre's subgenres, sorted by name, or none before a genre is chosen."""
        return sorted(style_of(self._genre)[TEMPLATES]) if self._genre else []

    def get_subgenre(self):
        return self._subgenre

    def set_subgenre(self, subgenre):
        """Choose a subgenre of the genre, and take its usual tempo, scale and form, which a person may then change."""
        if subgenre not in self.subgenres():
            raise ValueError(ERR_WIZARD_NO_SUCH_SUBGENRE.format(value=subgenre))
        if subgenre != self._subgenre:
            self._subgenre = subgenre
            self._forget_band()
            self._tempo = self.usual_tempo()
            self._scale_type = self.usual_scale_type()
            self._root = USUAL_ROOTS[self._scale_type]
            self._form = None
            self._sections = None
            self._melody = None
            self._hook = None
            self._levels = {player: USUAL_BUSY for player in style_of(self._genre).get(PLAYERS, {})}
            self._own_gauges = {}
            self._beside = self._usual_beside()

    def is_ready(self):
        """Return whether a song can be made: a genre and a subgenre are chosen, and the rest has its usual values."""
        return self._subgenre is not None

    # What the subgenre usually has.

    def _picks(self):
        """Return every trait's pick: the ways of playing chosen, and the subgenre's for the rest."""
        return self._picks_with(self._ways)

    def usual_tempo(self):
        style = style_of(self._genre)
        return self._picks().get(TEMPO, style[TRAITS][TEMPO][USUAL])

    def tempo_range(self):
        """Return the lowest and the highest tempo the genre usually has, which is said beside the tempo and never enforced."""
        tempos = style_of(self._genre)[TRAITS][TEMPO]
        return tempos[LOWEST], tempos[HIGHEST]

    def usual_scale_type(self):
        """Return the scale type the subgenre's chords are usually in, or major where its chords say nothing of one."""
        style = style_of(self._genre)
        trait = style.get(CHORD_TRAIT_FIELD, CHORD_TRAIT)
        entry = values_of(style=style, trait=trait).get(self._picks().get(trait), {})
        usual = entry.get(SCALE_TYPE, MAJOR)
        return usual if usual in SCALE_TYPES else MAJOR

    # The key and the tempo.

    def get_root(self):
        return self._root

    def set_root(self, root):
        if root not in ROOT_NAMES:
            raise ValueError(ERR_WIZARD_NO_SUCH_ROOT.format(value=root))
        self._root = root

    def get_scale_type(self):
        return self._scale_type

    def set_scale_type(self, scale_type):
        if scale_type not in SCALE_TYPES:
            raise ValueError(ERR_WIZARD_NO_SUCH_SCALE_TYPE.format(value=scale_type))
        self._scale_type = scale_type

    def get_tempo(self):
        return self._tempo

    def set_tempo(self, tempo):
        """Set the tempo to any the tracker plays; the genre's usual range is advice."""
        if isinstance(tempo, bool) or not isinstance(tempo, int) or not MIN_TEMPO <= tempo <= MAX_TEMPO:
            raise ValueError(ERR_WIZARD_TEMPO.format(low=MIN_TEMPO, high=MAX_TEMPO, value=tempo))
        self._tempo = tempo

    # The form.

    def _forms(self):
        return forms_of(style=style_of(self._genre), song={TEMPLATE: self._subgenre}) if self.is_ready() else []

    def forms(self):
        """Return the names of the forms the subgenre suggests, the commonest first."""
        return [form[NAME] for form in sorted(self._forms(), key=share_of, reverse=True)]

    def get_form(self):
        """Return the form chosen, or the commonest of the subgenre's until one is, or None before a subgenre is chosen."""
        if self._form is not None:
            return self._form
        forms = self.forms()
        return forms[0] if forms else None

    def form_section_count(self, form):
        """Return how many sections a suggested form has."""
        return len(next((form_[SECTIONS] for form_ in self._forms() if form_[NAME] == form), []))

    def set_form(self, form):
        """Choose one of the forms the subgenre suggests, which puts its sections in place of any a person changed."""
        if form not in self.forms():
            raise ValueError(ERR_WIZARD_NO_SUCH_FORM.format(value=form))
        self._form = form
        self._sections = None

    # The form's sections, which follow the form chosen until a person changes one; the form is then the song's own.

    def has_own_form(self):
        """Return whether a person has changed the form's sections, so that the form is no longer one the subgenre suggests."""
        return self._sections is not None

    def _entries(self):
        """Return the sections in order, each its kind and what it changes of the kind: the song's own, or the chosen form's."""
        if self._sections is not None:
            return self._sections
        chosen = self.get_form()
        return [{KIND: kind} for kind in next((form[SECTIONS] for form in self._forms() if form[NAME] == chosen), [])]

    def _own_entries(self):
        """Return the song's own sections to change, starting them from the chosen form the first time."""
        if self._sections is None:
            self._sections = [dict(entry) for entry in self._entries()]
        return self._sections

    def _entry(self, place):
        entries = self._entries()
        if isinstance(place, bool) or not isinstance(place, int) or not 0 <= place < len(entries):
            raise ValueError(ERR_WIZARD_NO_SUCH_SECTION.format(value=place))
        return entries[place]

    def form_sections(self):
        """Return the sections of the form in the order they play, by name. A section is named after its kind, and one that
        differs from the first of its kind, in its bars or its players, gets a letter after the name, since sections of one
        name are the same section played again."""
        names = []
        seen = {}
        for entry in self._entries():
            own = (entry.get(BARS), tuple(entry[PLAYS]) if PLAYS in entry else None)
            # The kind as the genre describes it comes first, so that an unchanged section keeps the kind's plain name.
            variants = seen.setdefault(entry[KIND], [(None, None)])
            if own not in variants:
                variants.append(own)
            place = variants.index(own)
            names.append(entry[KIND] if not place else MSG_WIZARD_SECTION_VARIANT.format(kind=entry[KIND], letter=chr(ord(FIRST_VARIANT_LETTER) + place)))
        return names

    def section_labels(self):
        """Return what each section is shown as, in order: its kind, and where the form has several of a kind, the kind with
        a dash and the section's count among them, as the tracker numbers every name it makes."""
        kinds = [entry[KIND] for entry in self._entries()]
        counts = {}
        labels = []
        for kind in kinds:
            counts[kind] = counts.get(kind, 0) + 1
            labels.append(kind if kinds.count(kind) == 1 else MSG_WIZARD_SECTION_NUMBERED.format(kind=kind, number=counts[kind]))
        return labels

    def _song_sections(self):
        """Return the song's own sections as the arranger reads them, by name: each its kind and what it changes."""
        return {name: dict(entry) for name, entry in zip(self.form_sections(), self._entries())}

    def _section(self, place):
        """Return a section as it will be played: its kind as the genre describes it, with what the section changes."""
        entry = self._entry(place)
        return section_of(name=entry[KIND], style=style_of(self._genre), song={SECTIONS: {entry[KIND]: entry}})

    def section_kinds(self):
        """Return the kinds of section the subgenre can play, in the genre's order: a kind nobody of the subgenre's band plays
        in, which would make no section at all, is left out, as is one whose parts do not fill its own length."""
        if not self.is_ready():
            return []
        sections = style_of(self._genre)[SECTIONS]
        return [kind for kind, section in sections.items()
                if bars_work(genre=self._genre, subgenre=self._subgenre, kind=kind, bars=HELD_BARS if section.get(HELD) else section[BARS])]

    def section_kind(self, place):
        return self._entry(place)[KIND]

    def section_is_held(self, place):
        """Return whether a section is one held chord, which lasts a bar whatever is said."""
        return bool(self._section(place).get(HELD))

    def section_bars(self, place):
        section = self._section(place)
        return HELD_BARS if section.get(HELD) else section[BARS]

    def section_plays(self, place):
        """Return who plays in a section, by the names the genre gives its players."""
        return list(self._section(place).get(PLAYS, []))

    def add_section(self, *, place, kind):
        """Put a new section of a kind before a place in the form, as the genre describes the kind."""
        if kind not in self.section_kinds():
            raise ValueError(ERR_WIZARD_NO_SUCH_SECTION_KIND.format(value=kind))
        if isinstance(place, bool) or not isinstance(place, int) or not 0 <= place <= len(self._entries()):
            raise ValueError(ERR_WIZARD_NO_SUCH_SECTION.format(value=place))
        self._own_entries().insert(place, {KIND: kind})

    def copy_section(self, place):
        """Put a copy of a section straight after it."""
        entry = own_copy_of(self._entry(place))
        self._own_entries().insert(place + 1, entry)

    def remove_section(self, place):
        self._entry(place)
        if len(self._entries()) == 1:
            raise ValueError(ERR_WIZARD_LAST_SECTION)
        del self._own_entries()[place]

    def move_section(self, *, place, offset):
        """Move a section earlier or later in the form, and return whether it moved, which it cannot past either end."""
        self._entry(place)
        moved = place + offset
        if not 0 <= moved < len(self._entries()):
            return False
        entries = self._own_entries()
        entries.insert(moved, entries.pop(place))
        return True

    def set_section_kind(self, *, place, kind):
        """Make a section another kind, as the genre describes that kind: what the section changed of its old kind is dropped."""
        self._entry(place)
        if kind not in self.section_kinds():
            raise ValueError(ERR_WIZARD_NO_SUCH_SECTION_KIND.format(value=kind))
        self._own_entries()[place] = {KIND: kind}

    def _usual(self, place):
        return style_of(self._genre)[SECTIONS][self._entry(place)[KIND]]

    def bars_offered(self, place):
        """Return the lengths a section may have, in bars: half its kind's usual length, the usual and twice that, leaving out
        any the genre's parts cannot fill, and nothing for a held section."""
        return list(self._remembered(key=(BARS_ANSWER, place), compute=lambda: self._bars_offered(place)))

    def _bars_offered(self, place):
        if self.section_is_held(place):
            return []
        usual = self._usual(place)[BARS]
        lengths = sorted({usual // HALF, usual, usual * HALF, self.section_bars(place)} - {0})
        return [bars for bars in lengths if bars == usual or self._bars_fit(place=place, bars=bars)]

    def _bars_fit(self, *, place, bars):
        """Return whether the players of a section can fill the section at a length: on their own, and then in this song, where
        a part may be written differently beside another section of the kind."""
        if not bars_work(genre=self._genre, subgenre=self._subgenre, kind=self._entry(place)[KIND], bars=bars, plays=tuple(self.section_plays(place))):
            return False
        trial = copy.deepcopy(self)
        trial._answers = {}
        trial._own_entries()[place][BARS] = bars
        try:
            trial.made_setlist(name=self._entry(place)[KIND], version=A_VERSION)
        except (ValueError, SongFileError):
            return False
        return True

    def set_section_bars(self, *, place, bars):
        if isinstance(bars, bool) or not isinstance(bars, int) or bars not in self.bars_offered(place):
            raise ValueError(ERR_WIZARD_SECTION_BARS.format(value=bars))
        entry = self._own_entries()[place]
        entry.pop(BARS, None)
        if bars != self._usual(place)[BARS]:
            entry[BARS] = bars

    def set_section_plays(self, *, place, role, on):
        """Have a player play in a section or sit it out. A section keeps one player, and a length its players can fill."""
        self._role(role)
        plays = [name for name in self.roles() if (name in self.section_plays(place) or (on and name == role)) and (on or name != role)]
        if not plays:
            raise ValueError(ERR_WIZARD_SECTION_NEEDS_PLAYER)
        entry = self._own_entries()[place]
        entry.pop(PLAYS, None)
        if sorted(plays) != sorted(self._usual(place).get(PLAYS, [])):
            entry[PLAYS] = plays
        # A length the players left cannot fill gives way to the kind's usual length.
        if BARS in entry and not self._bars_fit(place=place, bars=entry[BARS]):
            del entry[BARS]

    def set_own_sections(self, *, sections):
        """Take a form's sections a song kept, each through the setters, or none of them where one no longer fits."""
        kept = self._sections
        self._sections = []
        try:
            for place, entry in enumerate(sections):
                self.add_section(place=place, kind=entry[KIND])
                if BARS in entry:
                    self.set_section_bars(place=place, bars=entry[BARS])
                for role in self.roles():
                    if PLAYS in entry and (role in entry[PLAYS]) != (role in self.section_plays(place)) and role in entry[PLAYS]:
                        self.set_section_plays(place=place, role=role, on=True)
                for role in self.roles():
                    if PLAYS in entry and role not in entry[PLAYS] and role in self.section_plays(place):
                        self.set_section_plays(place=place, role=role, on=False)
                if BESIDE_KEPT in entry:
                    # What the answering player does in the section is kept as chosen, and is used wherever somebody answers there.
                    if entry[BESIDE_KEPT] not in WAYS_BESIDE:
                        raise ValueError(ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=entry[BESIDE_KEPT]))
                    self._sections[place][BESIDE_KEPT] = entry[BESIDE_KEPT]
            if not self._sections:
                raise ValueError(ERR_WIZARD_LAST_SECTION)
        except (KeyError, TypeError, ValueError):
            self._sections = kept
            raise ValueError(ERR_WIZARD_BAD_SECTIONS.format(value=sections)) from None

    # The band: who plays, how each plays and how busy each is.

    def _forget_band(self):
        self._ways = {}
        self._levels = {}
        self._own_gauges = {}
        self._beside = None
        self._without = []
        self._sounds = {}
        self._band_sounds = USUAL_SOUNDS
        self._guitarists = TWO_GUITARISTS
        self._pieces_off = []
        self._fills = None
        self._quiet_notes = True
        self._break = None
        self._break_cut = None
        self._gauges = {}
        self._melody_settings = {}
        self._piece_sounds = {}

    def _role(self, role):
        found = next((entry for entry in style_of(self._genre)[ROLES] if entry[ROLE] == role), None) if self.is_ready() else None
        if found is None:
            raise ValueError(ERR_WIZARD_NO_SUCH_PLAYER.format(value=role))
        return found

    def roles(self):
        """Return the players the genre's band may have, by name, in the genre's order."""
        return [entry[ROLE] for entry in style_of(self._genre)[ROLES]] if self.is_ready() else []

    def role_traits(self, role):
        """Return what is chosen about how a player plays: the one way of a player of notes, or each part of the drums."""
        entry = self._role(role)
        if not entry.get(DRUMS):
            return [entry[TRAIT]]
        # A break takes the place of every way the drums are played but the percussion's.
        return [trait for trait in entry[DRUMS] if self.get_break() is None or trait == KEPT_BESIDE_A_BREAK]

    def _has_sound(self, *, trait, value):
        return SOUND in values_of(style=style_of(self._genre), trait=trait)[value]

    def role_is_in(self, role):
        """Return whether a player is in the band: not left out, and, for a player of notes, playing in a way that sounds."""
        entry = self._role(role)
        return role not in self._without and (bool(entry.get(DRUMS)) or self._has_sound(trait=entry[TRAIT], value=self.get_way(entry[TRAIT])))

    def role_can_play(self, role):
        """Return whether a player can be in the band at all: the drums always, and a player of notes where a way of playing that sounds fits the subgenre."""
        entry = self._role(role)
        return bool(entry.get(DRUMS)) or self.role_is_in(role) or bool(self.ways(role=role, trait=entry[TRAIT]))

    def role_title(self, role):
        """Return what a player is called on the screen: the clearer name the genre gives the player, which may follow how the
        player plays, as a lead that is a singer or a lead guitar; or the player's name where the genre gives no other."""
        entry = self._role(role)
        if self.has_one_guitarist() and role == self._one_guitarist()[CHORDS_PLAYER]:
            return self._one_guitarist()[ROLE_TITLE]
        traits = self.role_traits(role)
        by_way = entry.get(ROLE_TITLES, {})
        way = self.get_way(traits[0]) if len(traits) == 1 else None
        return by_way.get(way, entry.get(ROLE_TITLE, role))

    # The drum kit's pieces, each switched on or off: a stroke on a piece that is off is left out, never
    # moved to another piece.

    def _remembered(self, *, key, compute):
        """Return an answer that is found by making the song, worked out once for the choices as they stand: a page asks the
        same thing at every key, and making a song each time made the keys slow. Everything a song keeps of the choices says
        whether they changed."""
        state = repr(self.to_data())
        if state != self._answers_of:
            self._answers = {}
            self._answers_of = state
        if key not in self._answers:
            self._answers[key] = compute()
        return self._answers[key]

    def pieces(self):
        """Return the pieces of the kit the drums play in the song as chosen, in the order the song has them, on or off."""
        return list(self._remembered(key=PIECES_ANSWER, compute=self._pieces))

    def _pieces(self):
        if not self.is_ready():
            return []
        song = {**self.song_picks(self._subgenre), WITHOUT_PIECES: [], PIECE_SOUNDS: {}}
        return list(arranged(style=style_of(self._genre), song=song)[DRUM_TRACKS])

    def piece_is_on(self, piece):
        return piece not in self._pieces_off

    def set_piece_on(self, *, piece, on):
        """Switch a piece of the kit on or off. The last piece stays on: a band with no drums leaves the drums out."""
        if piece not in self.pieces():
            raise ValueError(ERR_WIZARD_NO_SUCH_PIECE.format(value=piece))
        if on:
            if piece in self._pieces_off:
                self._pieces_off.remove(piece)
            return
        if [name for name in self.pieces() if self.piece_is_on(name)] == [piece]:
            raise ValueError(ERR_WIZARD_LAST_PIECE)
        if piece not in self._pieces_off:
            self._pieces_off.append(piece)

    # How often the drummer plays a fill, and the snare's quiet notes.

    def _drummer(self):
        """Return what the genre says of its drummer at the level the drums are busy."""
        drums = next((role for role in self.roles() if not self.has_sound(role)), None)
        return player_of(style=style_of(self._genre), instrument=DRUMS, character=self._character(DRUMS)) if drums else {}

    def get_fills(self):
        """Return how often a fill comes, from FEWEST_FILLS, never, to MOST_FILLS: the position chosen, or the one nearest to
        what the drummer does at the level the drums are busy."""
        if self._fills is not None:
            return self._fills
        every = self._drummer().get(FILL_EVERY, style_of(self._genre).get(PHRASE_BARS, DEFAULT_PHRASE_BARS))
        if every == 0:
            return FEWEST_FILLS
        return next((position for position, bars in FILLS_EVERY.items() if isinstance(bars, int) and 0 < every <= bars), EACH_SECTION_FILLS)

    def set_fills(self, position):
        if isinstance(position, bool) or not isinstance(position, int) or not FEWEST_FILLS <= position <= MOST_FILLS:
            raise ValueError(ERR_WIZARD_FILLS.format(value=position))
        self._fills = position

    def _set_kept_fills(self, *, position):
        self.set_fills(position)

    # What a piece of the kit sounds as: its own drum, another drum of the kit, or a General MIDI sound on one note.

    def kit_drums(self):
        """Return the drums of the kit a piece may sound as."""
        return list(KIT)

    def piece_sound(self, piece):
        """Return what a piece of the kit sounds as: None for its own drum, the name of another drum of the kit, or a General MIDI sound's number."""
        sounds_as = self._piece_sounds.get(piece, {})
        return sounds_as.get(PLAYED_DRUM, sounds_as.get(PLAYED_SOUND))

    def piece_note(self, piece):
        """Return the MIDI note a piece plays in its General MIDI sound, or None for a piece that sounds as a drum."""
        return self._piece_sounds.get(piece, {}).get(PLAYED_NOTE)

    def set_piece_sound(self, *, piece, sound):
        """Have a piece of the kit sound as another drum of the kit, by name, or as a General MIDI sound, by number, on the note the
        piece had or the usual one; or None, as its own drum again."""
        if piece not in self.pieces():
            raise ValueError(ERR_WIZARD_NO_SUCH_PIECE.format(value=piece))
        if sound is None or sound == piece:
            self._piece_sounds.pop(piece, None)
        elif isinstance(sound, str) and sound in KIT:
            self._piece_sounds[piece] = {PLAYED_DRUM: sound}
        elif not isinstance(sound, (bool, str)) and isinstance(sound, int) and MIN_GM_SOUND <= sound <= MAX_GM_SOUND:
            self._piece_sounds[piece] = {PLAYED_SOUND: sound, PLAYED_NOTE: self.piece_note(piece) or USUAL_PIECE_NOTE}
        else:
            raise ValueError(ERR_WIZARD_PIECE_SOUND.format(value=sound))

    def set_piece_note(self, *, piece, note):
        """Choose the note a piece plays in its General MIDI sound."""
        if self.piece_note(piece) is None:
            raise ValueError(ERR_WIZARD_PIECE_HAS_NO_NOTE.format(value=piece))
        if isinstance(note, bool) or not isinstance(note, int) or not LOWEST_NOTE <= note <= HIGHEST_NOTE:
            raise ValueError(ERR_WIZARD_PIECE_NOTE.format(low=LOWEST_NOTE, high=HIGHEST_NOTE, value=note))
        self._piece_sounds[piece][PLAYED_NOTE] = note

    def _set_kept_piece_sound(self, *, piece, sounds_as):
        self.set_piece_sound(piece=piece, sound=sounds_as.get(PLAYED_DRUM, sounds_as.get(PLAYED_SOUND)))
        if PLAYED_NOTE in sounds_as:
            self.set_piece_note(piece=piece, note=sounds_as[PLAYED_NOTE])

    # The drum break: a bar of drums played as one thing, in place of the kick's, the snare's and the cymbal's own ways.

    def breaks(self):
        """Return the drum breaks the song may play: every break where the band has drums and the meter is the one a break
        is written in, and none otherwise."""
        if not self.is_ready() or self.meter() != COMMON_TIME or not any(not self.has_sound(role) for role in self.roles()):
            return []
        return break_names()

    def get_break(self):
        """Return the break the drums play, the one chosen or the subgenre's own, or None where they play none."""
        if not self.breaks():
            return None
        name = self._break if self._break is not None else self._picks().get(BREAK, NO_BREAK)
        return None if name == NO_BREAK else name

    def set_break(self, name):
        """Choose the break the drums play, or None for none."""
        if name is not None and name not in self.breaks():
            raise ValueError(ERR_WIZARD_NO_SUCH_BREAK.format(value=name))
        self._break = NO_BREAK if name is None else name

    def _set_kept_break(self, *, name):
        self.set_break(None if name == NO_BREAK else name)

    def get_break_cut(self):
        """Return how far the break is cut up, from LEAST_CUT, as written, to MOST_CUT."""
        return self._break_cut if self._break_cut is not None else self._picks().get(BREAK_CUT, LEAST_CUT)

    def set_break_cut(self, position):
        if isinstance(position, bool) or not isinstance(position, int) or not LEAST_CUT <= position <= MOST_CUT:
            raise ValueError(ERR_WIZARD_BREAK_CUT.format(low=LEAST_CUT, high=MOST_CUT, value=position))
        self._break_cut = position

    def _set_kept_break_cut(self, *, position):
        self.set_break_cut(position)

    def _break_picks(self):
        """Return the song's picks of a break and its cut, where either was chosen."""
        return {**({BREAK: self._break} if self._break is not None else {}), **({BREAK_CUT: self._break_cut} if self._break_cut is not None else {})}

    # The smart melody style's gauges, shown while the song's tunes are sketched by it.

    def gauges(self):
        """Return the names of the smart melody style's gauges while the song's tunes are sketched by it or by the hooks style, and none otherwise."""
        return list(DEFAULT_GAUGES) if self._melody in GAUGED_STYLES else []

    def get_gauge(self, name):
        """Return where a gauge stands, from LOWEST_GAUGE to HIGHEST_GAUGE: where it was moved to, else where the genre sets it."""
        if name in self._gauges:
            return self._gauges[name]
        habits = style_of(self._genre)[MELODY]
        habits = habits if GRID in habits else habits[self.meter()]
        return habits.get(SMART, {}).get(name, DEFAULT_GAUGES[name])

    def set_gauge(self, *, name, position):
        if name not in DEFAULT_GAUGES or isinstance(position, bool) or not isinstance(position, int) or not LOWEST_GAUGE <= position <= HIGHEST_GAUGE:
            raise ValueError(ERR_WIZARD_GAUGE.format(name=name, low=LOWEST_GAUGE, high=HIGHEST_GAUGE, value=position))
        self._gauges[name] = position

    def _melody_habits(self):
        """Return the genre's melody habits for the song's meter."""
        habits = style_of(self._genre)[MELODY]
        return habits if GRID in habits else habits[self.meter()]

    def melody_settings(self):
        """Return the names of the settings the song's melody style has of its own, the usual style's while none is chosen."""
        return list(MELODY_SETTINGS_OF[self._melody]) if self.is_ready() else []

    def melody_setting_range(self, name):
        """Return the lowest and highest a melody setting that is a number may be."""
        return MELODY_NUMBERS[name]

    def melody_setting_is_switch(self, name):
        return name in MELODY_SWITCHES

    def get_melody_setting(self, name):
        """Return a melody setting: what it was set to, else what the genre's habits say, else what the style does unasked."""
        if name in self._melody_settings:
            return self._melody_settings[name]
        habits = self._melody_habits()
        if name in MELODY_SWITCHES:
            return bool(habits.get(name, MELODY_SWITCHES[name]))
        return {**DEFAULT_EVOLVE, **habits.get(EVOLVE, {})}[name]

    def set_melody_setting(self, *, name, value):
        """Set a setting of the song's melody style, refusing one the style does not have."""
        if name not in self.melody_settings():
            raise ValueError(ERR_WIZARD_NO_SUCH_MELODY_SETTING.format(value=name))
        self._set_kept_melody_setting(name=name, value=value)

    def _set_kept_melody_setting(self, *, name, value):
        if name in MELODY_SWITCHES:
            if not isinstance(value, bool):
                raise ValueError(ERR_WIZARD_MELODY_SWITCH.format(name=name, value=value))
        elif name in MELODY_NUMBERS:
            low, high = MELODY_NUMBERS[name]
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(ERR_WIZARD_MELODY_NUMBER.format(name=name, low=low, high=high, value=value))
        else:
            raise ValueError(ERR_WIZARD_NO_SUCH_MELODY_SETTING.format(value=name))
        self._melody_settings[name] = value

    def _song_melody(self):
        """Return what the song says of its melody over the genre's habits: the smart style's gauges where one was moved, and
        the settings set of the style in use; a setting of another style is kept and says nothing."""
        said = {}
        if self._melody in GAUGED_STYLES and self._gauges:
            said[SMART] = {**{name: self.get_gauge(name) for name in DEFAULT_GAUGES}, **self._gauges}
        own = {name: value for name, value in self._melody_settings.items() if name in MELODY_SETTINGS_OF[self._melody]}
        evolve = {name: value for name, value in own.items() if name in EVOLVE_SETTINGS}
        if evolve:
            said[EVOLVE] = {**DEFAULT_EVOLVE, **self._melody_habits().get(EVOLVE, {}), **evolve}
        said.update({name: value for name, value in own.items() if name not in EVOLVE_SETTINGS})
        return said

    def _set_kept_quiet_notes(self, *, on):
        self.set_quiet_notes(on)

    def has_quiet_notes(self):
        """Return whether the snare of the song as chosen has quiet notes, soft strokes between the main ones, to switch off."""
        return self._remembered(key=QUIET_NOTES_ANSWER, compute=self._has_quiet_notes)

    def _has_quiet_notes(self):
        if not self.is_ready():
            return False
        song = {name: value for name, value in self.song_picks(self._subgenre).items() if name != QUIET_NOTES}
        style = style_of(self._genre)
        # Found by arranging the song both ways, since a drummer's unevenness has made numbers of the strokes by then.
        return arranged(style=style, song=song)[PARTS] != arranged(style=style, song={**song, QUIET_NOTES: False})[PARTS]

    def plays_quiet_notes(self):
        return self._quiet_notes

    def set_quiet_notes(self, on):
        if not isinstance(on, bool):
            raise ValueError(ERR_WIZARD_QUIET_NOTES.format(value=on))
        self._quiet_notes = on

    # One guitarist or two: a band whose one guitarist plays the chords and takes the solo, the chords
    # stopping where the solo plays, shown as one player.

    def _one_guitarist(self):
        return style_of(self._genre).get(ONE_GUITARIST) if self.is_ready() else None

    def offers_one_guitarist(self):
        """Return whether the band can have one guitarist: the genre says which two players the one would be, and the solo can be a guitar's."""
        one = self._one_guitarist()
        return bool(one) and self.role_can_play(one[CHORDS_PLAYER]) and one[SOLO_WAY] in self.ways(role=one[SOLO_PLAYER], trait=self._role(one[SOLO_PLAYER])[TRAIT])

    def get_guitarists(self):
        return self._guitarists

    def has_one_guitarist(self):
        return self._guitarists == ONE_GUITARIST_COUNT

    def set_guitarists(self, count):
        """Choose two guitarists or one. One guitarist takes the solo on the guitar, whatever took it before."""
        if isinstance(count, bool) or count not in GUITARIST_COUNTS or (count == ONE_GUITARIST_COUNT and not self.offers_one_guitarist()):
            raise ValueError(ERR_WIZARD_GUITARISTS.format(value=count))
        self._guitarists = count
        if count == ONE_GUITARIST_COUNT:
            one = self._one_guitarist()
            if one[SOLO_PLAYER] in self._without:
                self._without.remove(one[SOLO_PLAYER])
            self._ways[self._role(one[SOLO_PLAYER])[TRAIT]] = one[SOLO_WAY]

    def _set_kept_guitarists(self, *, count):
        self.set_guitarists(count)

    def roles_shown(self):
        """Return the players the screen shows: every player, but for the player of the solo where one guitarist plays both."""
        hidden = self._one_guitarist()[SOLO_PLAYER] if self.has_one_guitarist() else None
        return [role for role in self.roles() if role != hidden]

    def _song_without(self):
        """Return the players the song leaves out: those left out, and with them the solo of one guitarist who is left out."""
        without = list(self._without)
        if self.has_one_guitarist():
            one = self._one_guitarist()
            if one[CHORDS_PLAYER] in without and one[SOLO_PLAYER] not in without:
                without.append(one[SOLO_PLAYER])
        return without

    def _plays_of_one_guitarist(self, plays):
        """Return who plays in a section where one guitarist plays both parts: the chords stop where the solo plays."""
        one = self._one_guitarist()
        if self.has_one_guitarist() and one[SOLO_PLAYER] in plays and one[CHORDS_PLAYER] in plays:
            return [role for role in plays if role != one[CHORDS_PLAYER]]
        return None

    def _sections_of_song(self):
        """Return the sections the song describes itself, by name: its own form's, each with its kind and what it changes; and,
        for one guitarist, each section the solo plays in with the chords left out."""
        if self.has_own_form():
            sections = self._song_sections()
            for place, name in enumerate(self.form_sections()):
                plays = self._plays_of_one_guitarist(self.section_plays(place))
                if plays is not None:
                    sections[name][PLAYS] = plays
            return sections
        sections = {}
        for kind in set(self.form_sections()):
            plays = self._plays_of_one_guitarist(list(style_of(self._genre)[SECTIONS][kind].get(PLAYS, [])))
            if plays is not None:
                sections[kind] = {KIND: kind, PLAYS: plays}
        return sections

    # A player's sound: the one the player's way of playing has, moved by the band's Sounds, unless the player has a sound of its own.

    def has_sound(self, role):
        """Return whether a player's sound can be chosen: a player of notes, never the drums, whose kit the grooves are written for."""
        return not self._role(role).get(DRUMS)

    def usual_sound(self, role):
        """Return the General MIDI sound a player usually plays with: what the genre has stand in for the player in the subgenre,
        as it does for a singer, whose voice General MIDI plays poorly, or the sound of the player's way."""
        style = style_of(self._genre)
        stands_in = style.get(STAND_INS, {}).get(role, {}).get(self._subgenre)
        return style[SOUNDS][stands_in] if stands_in else self._way_sound(role)

    def _way_sound(self, role):
        """Return the General MIDI sound a player's way of playing has, which the arranger gives the player unless the song says another."""
        style = style_of(self._genre)
        entry = values_of(style=style, trait=self._role(role)[TRAIT])[self.get_way(self._role(role)[TRAIT])]
        return style[SOUNDS][entry[SOUND]]

    def get_band_sounds(self):
        return self._band_sounds

    def set_band_sounds(self, sounds):
        if sounds not in BAND_SOUNDS:
            raise ValueError(ERR_WIZARD_BAND_SOUNDS.format(value=sounds))
        self._band_sounds = sounds

    def _set_kept_band_sounds(self, *, sounds):
        self.set_band_sounds(sounds)

    def band_sound(self, role):
        """Return the sound the band's Sounds gives a player: the usual one, or the nearest of the family chosen, a sound
        already of that family staying as it is."""
        usual = self.usual_sound(role)
        if self._band_sounds == USUAL_SOUNDS or usual in KEPT_BY[self._band_sounds]:
            return usual
        return NEAREST[self._band_sounds].get(family_of(usual), usual)

    def has_own_sound(self, role):
        return role in self._sounds

    def get_sound(self, role):
        """Return the General MIDI sound a player plays with: the player's own, or the band's."""
        return self._sounds.get(role, self.band_sound(role)) if role in self._sounds else self.band_sound(role)

    def set_sound(self, *, role, sound):
        """Give a player a sound of its own, any General MIDI sound; or None, to follow the band's again."""
        if not self.has_sound(role):
            raise ValueError(ERR_WIZARD_NO_SUCH_PLAYER.format(value=role))
        if sound is None:
            self._sounds.pop(role, None)
            return
        if isinstance(sound, bool) or not isinstance(sound, int) or not MIN_GM_SOUND <= sound <= MAX_GM_SOUND:
            raise ValueError(ERR_WIZARD_SOUND.format(low=MIN_GM_SOUND, high=MAX_GM_SOUND, value=sound))
        self._sounds[role] = sound

    # What a sound is tried with: a run of the song's scale from its root, in the player's octave.

    def root_half_steps(self):
        """Return the song's root as half steps above C, within an octave."""
        return SEMITONES_ABOVE_C[self._root] % NOTES_IN_OCTAVE

    def scale_half_steps(self):
        """Return the notes of the song's scale as half steps above its root, the major scale's where the melody engines know none for the scale type."""
        return HALF_STEPS.get(self._scale_type, HALF_STEPS[MAJOR])

    def role_octave(self, role):
        """Return the octave a player plays in."""
        return self._role(role).get(OCTAVE, USUAL_OCTAVE)

    def genre_sounds(self, role):
        """Return the genre's own sounds that suit a player, each a General MIDI number: the sounds of the ways the player can play."""
        style = style_of(self._genre)
        found = []
        for entry in values_of(style=style, trait=self._role(role)[TRAIT]).values():
            if SOUND in entry and style[SOUNDS][entry[SOUND]] not in found:
                found.append(style[SOUNDS][entry[SOUND]])
        for stands_in in style.get(STAND_INS, {}).get(role, {}).values():
            if style[SOUNDS][stands_in] not in found:
                found.append(style[SOUNDS][stands_in])
        return found

    def sound_name(self, sound):
        """Return what a General MIDI sound is called: by the genre where the genre names it, or by General MIDI."""
        named = [name for name, number in style_of(self._genre)[SOUNDS].items() if number == sound]
        return named[0] if named else MSG_GM_SOUNDS[sound - MIN_GM_SOUND]

    def _song_sounds(self):
        """Return the sounds the song chooses itself, by player: each player in the band whose sound is not its way's usual one."""
        return {role: self.get_sound(role) for role in self.roles_in() if self.has_sound(role) and self.role_can_play(role) and self.get_sound(role) != self._way_sound(role)}

    def roles_in(self):
        return [role for role in self.roles() if self.role_is_in(role)]

    def set_role_in(self, *, role, on):
        """Put a player in the band or leave the player out. A player whose usual way is to sit out comes in playing the commonest way that fits."""
        entry = self._role(role)
        if not on:
            if self.roles_in() == [role]:
                raise ValueError(ERR_WIZARD_LAST_PLAYER)
            if role not in self._without:
                self._without.append(role)
            return
        if role in self._without:
            self._without.remove(role)
        if not entry.get(DRUMS) and not self._has_sound(trait=entry[TRAIT], value=self.get_way(entry[TRAIT])):
            ways = self.ways(role=role, trait=entry[TRAIT])
            if not ways:
                raise ValueError(ERR_WIZARD_NO_WAY.format(value=role))
            self._ways[entry[TRAIT]] = ways[0]

    def _picks_with(self, ways):
        return picked(style=style_of(self._genre), song={TEMPLATE: self._subgenre, PICKS: ways})

    def _works(self, *, trait, value):
        """Return whether a way of playing can be chosen beside the other picks, some ways needing a meter or a feel."""
        try:
            self._picks_with({**self._ways, trait: value})
        except ValueError:
            return False
        return True

    def ways(self, *, role, trait):
        """Return the ways a player may play a trait beside the other picks, the commonest first; for a player of notes, only ways that sound."""
        style = style_of(self._genre)
        drums = bool(self._role(role).get(DRUMS))
        picks = self._picks()
        entries = [entry for entry in sorted(values_of(style=style, trait=trait).values(), key=share_of, reverse=True) if (drums or SOUND in entry) and fits(entry=entry, picks=picks)]
        return [entry[VALUE] for entry in entries if self._works(trait=trait, value=entry[VALUE])]

    # What the whole song has a way of: its chords, its feel and its drum fills, each a trait of the genre no one player owns.

    def song_trait(self, traits):
        """Return the first of some traits the genre has that no player owns, as chords under either name a genre gives them, or None."""
        if not self.is_ready():
            return None
        of_players = {trait for role in self.roles() for trait in self.role_traits(role)}
        return next((trait for trait in traits if trait not in of_players and isinstance(style_of(self._genre)[TRAITS].get(trait), list)), None)

    def song_ways(self, trait):
        """Return the ways a trait of the whole song may go beside the other picks, the commonest first."""
        entries = sorted(values_of(style=style_of(self._genre), trait=trait).values(), key=self._share, reverse=True)
        return [entry[VALUE] for entry in entries if self._works(trait=trait, value=entry[VALUE])]

    def _share(self, entry):
        """Return how common a value is in the subgenre chosen."""
        return share_in(style=style_of(self._genre), entry=entry, template=self._subgenre)

    # The melody style, which every tune of the song is sketched by.

    def melody_styles(self):
        """Return the melody styles the subgenre's tunes can be sketched by, leaving out any that makes no song of it."""
        if not self.is_ready():
            return []
        return [style for style in MELODY_STYLES if melody_works(genre=self._genre, subgenre=self._subgenre, style=style)
                and not melody_is_usual(genre=self._genre, subgenre=self._subgenre, style=style)]

    def get_melody(self):
        """Return the melody style chosen, or None while each player's tunes are sketched as the genre says."""
        return self._melody

    def set_melody(self, style):
        if style is not None and style not in self.melody_styles():
            raise ValueError(ERR_WIZARD_NO_SUCH_MELODY.format(value=style))
        self._melody = style

    def _set_kept_melody(self, *, style):
        self.set_melody(style)

    # The hook, which a song has or has not, apart from the melody style that writes its other lines.

    def can_have_hook(self):
        """Return whether a hook can be made at all: a section of the song's form marks a line as its hook, and, in a form of
        the subgenre's own, a player carries a tune there."""
        if not self.is_ready() or not any(entry.get(HOOK) for place in range(len(self._entries())) for entry in self._section(place).get(PLAN, [])):
            return False
        return self.has_own_form() or hook_matters(genre=self._genre, subgenre=self._subgenre, form=self.get_form())

    def usual_hook(self):
        """Return whether the genre's songs have a hook unless a person says otherwise."""
        return self.can_have_hook() and bool(style_of(self._genre).get(HOOK, False))

    def has_hook(self):
        return self.usual_hook() if self._hook is None else self._hook

    def set_hook(self, on):
        if on and not self.can_have_hook():
            raise ValueError(ERR_WIZARD_NO_HOOK)
        self._hook = None if bool(on) == self.usual_hook() else bool(on)

    def _set_kept_hook(self, *, on):
        self.set_hook(on)

    def get_way(self, trait):
        return self._picks()[trait]

    def set_way(self, *, trait, value):
        if not self.is_ready() or value not in values_of(style=style_of(self._genre), trait=trait) or not self._works(trait=trait, value=value):
            raise ValueError(ERR_WIZARD_NO_SUCH_WAY.format(trait=trait, value=value))
        self._ways[trait] = value

    def has_busy(self, role):
        """Return whether a player's busyness can be chosen: the genre says how the player's instrument is played at each level."""
        return self._role(role).get(PLAYER) in style_of(self._genre).get(PLAYERS, {})

    def get_busy(self, role):
        """Return how busy a player is, from LEAST_BUSY to MOST_BUSY, or None where the song names no level."""
        return self._levels.get(self._role(role).get(PLAYER))

    def set_busy(self, *, role, level):
        """Choose how busy a player is. Players of one instrument, as a lead and a solo, share the level."""
        if not self.has_busy(role):
            raise ValueError(ERR_WIZARD_BUSY.format(low=LEAST_BUSY, high=MOST_BUSY, value=level))
        self._set_level(player=self._role(role)[PLAYER], level=level)

    def _set_level(self, *, player, level):
        if isinstance(level, bool) or not isinstance(level, int) or level not in style_of(self._genre).get(PLAYERS, {}).get(player, {}):
            raise ValueError(ERR_WIZARD_BUSY.format(low=LEAST_BUSY, high=MOST_BUSY, value=level))
        self._levels[player] = level
        # A preset chosen puts every gauge of the player back where the preset has it.
        self._own_gauges.pop(player, None)

    # The player beside the tune: who answers the player who has the tune, and what the answering player does in each section.

    def _interplay(self):
        """Return what the genre says of playing beside the tune: a plan of what is done in each kind of section, with a plan of its own for some subgenres, and how busy."""
        return style_of(self._genre).get(INTERPLAY, {}) if self.is_ready() else {}

    def _usual_answerer(self):
        """Return the player the genre has answer the tune, where the player can play in the subgenre, or None."""
        role = next((entry[ROLE] for entry in style_of(self._genre)[ROLES] if entry.get(ANSWERS)), None) if self.is_ready() else None
        return role if role is not None and role in self.roles_shown() and self.role_can_play(role) else None

    def tune_player(self):
        """Return the player who has the tune: the first player of lines who answers nobody and is in the band, or None."""
        return next((role for role in self.roles_in() if self.has_sound(role) and not self._role(role).get(ANSWERS) and self._plays_lines(role)), None)

    def _plays_lines(self, role):
        entry = self._role(role)
        return FIGURE not in values_of(style=style_of(self._genre), trait=entry[TRAIT])[self.get_way(entry[TRAIT])]

    def answerers(self):
        """Return the players who may answer the tune, by name: the genre's answering player while in the band, and none where the song keeps to
        what was made before answering could be chosen."""
        usual = self._usual_answerer()
        return [] if self._beside is None or usual is None or not self.role_is_in(usual) else [usual]

    def answered_by(self):
        """Return the player who answers the tune, or None where nobody does."""
        return self._beside[BY] if self._beside is not None and self._beside[BY] in self.answerers() and self.role_is_in(self._beside[BY]) else None

    def set_answered_by(self, role):
        """Choose who answers the tune, or nobody with None."""
        if role is not None and role not in self.answerers():
            raise ValueError(ERR_WIZARD_NO_SUCH_ANSWERER.format(value=role))
        if self._beside is None:
            raise ValueError(ERR_WIZARD_NO_SUCH_ANSWERER.format(value=role))
        self._beside[BY] = role

    def ways_beside(self):
        """Return what a player beside the tune may do in a section, in order."""
        return list(WAYS_BESIDE)

    def get_role_plan(self):
        """Return the one thing the answering player does in every section, or None where the player goes by the genre's plan, section by section."""
        return self._beside[WAY] if self._beside is not None else None

    def set_role_plan(self, way):
        """Have the answering player do one thing in every section, or go by the genre's plan with None. Either drops what single sections were given."""
        if self.answered_by() is None or (way is not None and way not in WAYS_BESIDE):
            raise ValueError(ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=way))
        self._beside[WAY] = way
        if self._sections is not None:
            for entry in self._sections:
                entry.pop(BESIDE_KEPT, None)

    def section_has_role(self, place):
        """Return whether the answering player has something to choose in a section: somebody answers, and the tune's player plays in the section."""
        return self.answered_by() is not None and not self.section_is_held(place) and self.tune_player() in self.section_plays(place)

    def planned_role(self, place):
        """Return what the plan has the answering player do in a section: the one thing chosen for every section, or what the genre's plan
        says of the section's kind, the subgenre's own plan first, and waiting where the plan says nothing."""
        if self._beside[WAY] is not None:
            return self._beside[WAY]
        interplay = self._interplay()
        kind = self._entry(place)[KIND]
        plan = {**interplay.get(PLAN, {}), **interplay.get(BY_SUBGENRE, {}).get(self._subgenre, {})}
        return plan.get(kind, WAITS)

    def section_role_is_own(self, place):
        """Return whether a section was given a role of its own, apart from the plan."""
        return BESIDE_KEPT in self._entry(place)

    def section_role(self, place):
        """Return what the answering player does in a section: the section's own choice, or the plan's."""
        if not self.section_has_role(place):
            raise ValueError(ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=place))
        return self._entry(place).get(BESIDE_KEPT, self.planned_role(place))

    def set_section_role(self, *, place, way):
        """Choose what the answering player does in one section, or give the section back to the plan with None."""
        if not self.section_has_role(place):
            raise ValueError(ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=place))
        if way is not None and way not in WAYS_BESIDE:
            raise ValueError(ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=way))
        if way is None and not self.section_role_is_own(place):
            return
        entry = self._own_entries()[place]
        entry.pop(BESIDE_KEPT, None)
        if way is not None:
            entry[BESIDE_KEPT] = way

    def has_fills_busy(self):
        """Return whether how busy the answering player is can be chosen: somebody answers."""
        return self.answered_by() is not None

    def get_fills_busy(self):
        return self._beside[BUSY_BESIDE]

    def set_fills_busy(self, busy):
        if not self.has_fills_busy() or isinstance(busy, bool) or not isinstance(busy, int) or not LEAST_BUSY_BESIDE <= busy <= MOST_BUSY_BESIDE:
            raise ValueError(ERR_WIZARD_FILLS_BUSY.format(low=LEAST_BUSY_BESIDE, high=MOST_BUSY_BESIDE, value=busy))
        self._beside[BUSY_BESIDE] = busy

    def _usual_beside(self):
        """Return how a new song starts: answered by the genre's answering player, going by the genre's plan, as busy as the genre says."""
        return {BY: self._usual_answerer(), WAY: None, BUSY_BESIDE: self._interplay().get(BUSY_BESIDE, USUAL_BUSY_BESIDE)}

    def _song_beside(self):
        """Return the song's player beside the tune, with what the player does in each section of the form in order, or nothing for a song that
        keeps to what was made before answering could be chosen, and for a genre nobody answers in."""
        usual = self._usual_answerer()
        if self._beside is None or usual is None or not self.role_is_in(usual):
            return {}
        answered = self.answered_by() is not None
        ways = [self.section_role(place) if answered and self.section_has_role(place) else WAITS for place in range(len(self._entries()))]
        return {BESIDE: {ROLE: usual, BESIDE_BUSY: self._beside[BUSY_BESIDE], BESIDE_WAYS: ways}}

    def _set_kept_beside(self, *, kept):
        usual = self._usual_beside()
        by = kept.get(BY)
        way = kept.get(WAY)
        busy = kept.get(BUSY_BESIDE, usual[BUSY_BESIDE])
        # Who answers is kept as chosen even where the player cannot answer now, as the solo's player hidden by one guitarist, and answers again once the player can.
        if (by is not None and by not in self.roles()) or (way is not None and way not in WAYS_BESIDE):
            raise ValueError(ERR_WIZARD_NO_SUCH_ANSWERER.format(value=by))
        if isinstance(busy, bool) or not isinstance(busy, int) or not LEAST_BUSY_BESIDE <= busy <= MOST_BUSY_BESIDE:
            raise ValueError(ERR_WIZARD_FILLS_BUSY.format(low=LEAST_BUSY_BESIDE, high=MOST_BUSY_BESIDE, value=busy))
        self._beside = {BY: by, WAY: way, BUSY_BESIDE: busy}

    # A player's gauges: where each stands, the preset's place until moved.

    def _character(self, player):
        """Return the character of an instrument's player: the preset's, with the gauges moved, or None where the song names no player."""
        if player not in self._levels:
            return None
        return {**preset(self._levels[player]), **self._own_gauges.get(player, {})}

    def _players(self):
        """Return each instrument's player for the song: a level, or the places of every gauge where one was moved."""
        return {player: self._character(player) if self._own_gauges.get(player) else level for player, level in self._levels.items()}

    def player_gauges(self, role):
        """Return the gauges a player has: those the genre's levels of the player's instrument say anything by."""
        if not self.has_busy(role):
            return []
        return gauges_of(style_of(self._genre)[PLAYERS][self._role(role)[PLAYER]])

    def get_player_gauge(self, *, role, gauge):
        """Return where a gauge of a player stands, from the lowest place to the highest."""
        if gauge not in self.player_gauges(role):
            raise ValueError(ERR_WIZARD_NO_SUCH_PLAYER_GAUGE.format(value=gauge))
        return self._character(self._role(role)[PLAYER])[gauge]

    def set_player_gauge(self, *, role, gauge, place):
        """Move a gauge of a player. Players of one instrument, as a lead and a solo, share their gauges."""
        if gauge not in self.player_gauges(role):
            raise ValueError(ERR_WIZARD_NO_SUCH_PLAYER_GAUGE.format(value=gauge))
        self._set_kept_player_gauge(player=self._role(role)[PLAYER], gauge=gauge, place=place)

    def _set_kept_player_gauge(self, *, player, gauge, place):
        if isinstance(place, bool) or not isinstance(place, int) or not LOWEST_PLACE <= place <= HIGHEST_PLACE or gauge not in PLAYER_GAUGES or player not in self._levels:
            raise ValueError(ERR_WIZARD_PLAYER_GAUGE.format(low=LOWEST_PLACE, high=HIGHEST_PLACE, value=place))
        own = self._own_gauges.setdefault(player, {})
        own[gauge] = place
        if place == PRESET_PLACE[self._levels[player]]:
            # A gauge moved back to the preset's place is the preset's again.
            del own[gauge]

    def player_preset(self, role):
        """Return the level of the preset a player is, or None for a player whose gauges were moved from it."""
        player = self._role(role).get(PLAYER)
        return None if self._own_gauges.get(player) else self._levels.get(player)

    # The meter and the length, which follow from the subgenre, the tempo and the form.

    def meter(self):
        """Return the meter the subgenre is played in."""
        return str(self._picks().get(METER, COMMON_TIME))

    def form_seconds(self, *, form=None):
        """Return how long the song lasts at the tempo chosen, in seconds; or how long a suggested form would, when one is named."""
        if form is None:
            bars = sum(self.section_bars(place) for place in range(len(self._entries())))
        else:
            style = style_of(self._genre)
            kinds = next((form_[SECTIONS] for form_ in self._forms() if form_[NAME] == form), [])
            bars = sum(HELD_BARS if style[SECTIONS][kind].get(HELD) else style[SECTIONS][kind][BARS] for kind in kinds)
        return float(bars * bar_length(self.meter()) * QUARTERS_IN_WHOLE * SECONDS_IN_MINUTE / self._tempo)

    def forms_by_length(self):
        """Return the forms' names from the shortest to the longest, forms of one length in the order they are suggested."""
        return sorted(self.forms(), key=lambda form: self.form_seconds(form=form))

    def step_length(self, offset):
        """Choose the next longer form, or the next shorter, stopping at the longest and the shortest: the song's length
        follows its sections, so a length is chosen by choosing a form."""
        forms = self.forms_by_length()
        place = forms.index(self.get_form()) + offset
        if 0 <= place < len(forms):
            self.set_form(forms[place])

    # The seed, which fixes every roll of the dice and is never shown.

    def get_seed(self):
        return self._seed

    def set_seed(self, seed):
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(ERR_WIZARD_SEED.format(value=seed))
        self._seed = seed

    def forget_seed(self):
        """Leave the seed to be drawn when the song is made."""
        self._seed = None

    def draw_seed(self, *, dice=None):
        """Draw a new seed at random, for a song from scratch or a new take."""
        self._seed = (dice or random.Random()).randint(FIRST_SEED, LAST_SEED)

    # The song.

    # The progression left to chance: a song whose progression nobody chose takes one of the subgenre's by the
    # seed, so that two runs differ in more than their tunes.

    def progression_trait(self):
        return self.song_trait(PROGRESSION_TRAITS)

    def has_any_progression(self):
        """Return whether the progression is left to chance: no progression was chosen."""
        return self.progression_trait() is not None and self.progression_trait() not in self._ways

    def set_any_progression(self):
        """Leave the progression to chance again."""
        self._ways.pop(self.progression_trait(), None)

    def progression_chords(self, progression):
        """Return a progression's chords for each kind of section the song's form plays, in the form's order, each chord its
        degree and its sharp or flat as a set file writes one; a section played as one held chord is left out. Nothing for a
        progression written another way than as degrees."""
        entry = values_of(style=style_of(self._genre), trait=self.progression_trait())[progression]
        if PATTERN not in entry:
            return []
        chords = {}
        for place, kind in enumerate(self.section_kinds_in_form()):
            if kind not in chords and not self.section_is_held(place):
                written = entry.get(BY_SECTION, {}).get(kind) or entry[PATTERN]
                chords[kind] = [(chord_of(chord)[DEGREE], ACCIDENTAL_MARKS.get(chord_of(chord).get(ACCIDENTAL))) for chord in written]
        return list(chords.items())

    def progression_degrees(self, progression):
        """Return the chords a progression is known by, its first written, each a degree and its sharp or flat; or nothing."""
        entry = values_of(style=style_of(self._genre), trait=self.progression_trait())[progression]
        return [(chord_of(chord)[DEGREE], ACCIDENTAL_MARKS.get(chord_of(chord).get(ACCIDENTAL))) for chord in entry.get(PATTERN, [])]

    def section_kinds_in_form(self):
        """Return the kind of each section of the song's form, in order."""
        return [self.section_kind(place) for place in range(len(self.section_labels()))]

    def progressions_by_chance(self):
        """Return the progressions the song may take, in the order the seed draws them: a commoner one likelier to come first, the
        subgenre's usual one counted twice. With no seed, or a progression chosen, there is nothing to draw."""
        trait = self.progression_trait()
        if not self.has_any_progression() or self._seed is None:
            return []
        usual = self._picks()[trait]
        entries = values_of(style=style_of(self._genre), trait=trait)
        left = self.song_ways(trait)
        # A progression written for the other of major and minor is left to be chosen by hand: its chords were not meant for the song's scale.
        suited = [way for way in left if entries[way].get(SCALE_TYPE, MAJOR) == self._scale_type]
        left = suited or left
        # A progression the subgenre's family never uses is left to be chosen by hand too.
        left = [way for way in left if self._share(entries[way])] or left
        dice = random.Random(PROGRESSION_SEED.format(self._seed))
        drawn = []
        while left:
            weights = [self._share(entries[way]) * (USUAL_COUNTS if way == usual else 1) or 1 for way in left]
            drawn.append(dice.choices(left, weights=weights)[0])
            left.remove(drawn[-1])
        return drawn

    def song_picks(self, name, *, progression=None):
        """Return the choices as a song's picks, which the arranger makes a song of: with a progression left to chance, the one
        given, or the first the seed draws."""
        drawn = [progression] if progression else self.progressions_by_chance()[:1]
        if drawn:
            return {**self._song_picks(name), PICKS: {**self._ways, **self._break_picks(), self.progression_trait(): drawn[0]}}
        return self._song_picks(name)

    def _song_picks(self, name):
        return {NAME: name, TITLE: name, STYLE: self._genre, TEMPLATE: self._subgenre, KEY: {ROOT: self._root, TYPE: self._scale_type}, TEMPO: self._tempo, FORM: self.form_sections() if self.has_own_form() else self.get_form(), SEED: self._seed,
                PICKS: {**self._ways, **self._break_picks()}, PLAYERS: self._players(), WITHOUT: self._song_without(), **self._song_beside(),
                **({SECTIONS: self._sections_of_song()} if self._sections_of_song() else {}),
                **({MELODY_ENGINE: self._melody} if self._melody is not None else {}),
                **({HOOK: self._hook} if self._hook is not None else {}),
                **({MELODY: self._song_melody()} if self._song_melody() else {}),
                **({ROLE_SOUNDS: self._song_sounds()} if self._song_sounds() else {}),
                **({WITHOUT_PIECES: list(self._pieces_off)} if self._pieces_off else {}),
                **({PIECE_SOUNDS: {piece: dict(sounds_as) for piece, sounds_as in self._piece_sounds.items()}} if self._piece_sounds else {}),
                **({FILLS_COME: FILLS_EVERY[self._fills]} if self._fills is not None else {}),
                **({} if self._quiet_notes else {QUIET_NOTES: False})}

    def made_setlist(self, *, name, version):
        """Return a set holding the one song these choices make, under a name, with all the song uses, the song keeping the choices.

        A run that has no seed yet draws one first, so that the same choices make the same song again.
        """
        if not self.is_ready():
            raise ValueError(ERR_WIZARD_NOT_READY)
        if self._seed is None:
            self.draw_seed()
        made = None
        # A progression drawn by chance that makes no song of these choices, as one too long for a section's bars, gives way to the next drawn.
        for progression in self.progressions_by_chance()[:-1]:
            try:
                made = Setlist.from_data(data=composed(given=arranged(style=style_of(self._genre), song=self.song_picks(name, progression=progression)), version=version))
                break
            except (ValueError, IndexError, KeyError, SongFileError):
                made = None
        if made is None:
            last = self.progressions_by_chance()[-1:]
            given = arranged(style=style_of(self._genre), song=self.song_picks(name, progression=last[0] if last else None))
            made = Setlist.from_data(data=composed(given=given, version=version))
        made.get_item(section=Section.SONGS, name=name).set_wizard_choices(self.to_data())
        # A part written for a section that leaves the part out is played by nothing, and would be left behind in the open set.
        made.remove_unused()
        # Each pattern goes in the group named after the track that plays it.
        made.group_patterns_by_track(made.get_item(section=Section.SONGS, name=name))
        return made
