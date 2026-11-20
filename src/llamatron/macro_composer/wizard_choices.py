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

from llamatron.composition import generator_settings, limits
from llamatron.composition.file_format import Section
from llamatron.composition.generator_settings import PhrasingSettings
from llamatron.composition.setlist import Setlist
from llamatron.composition.song_file_error import SongFileError
from llamatron.macro_composer import arranger, composer as set_writer, hook_writing, interplay as interplay_values, joins as joins_values, line_edits, loudness_steps, melody as melody_writer, notation as tune_notation, phrasing, riffs as riffs_values, song_plan, wizard_limits
from llamatron.macro_composer.arranger import arranged, bar_length, chord_of, fits_by_halves, form_of, forms_of, picked, section_of, share_in, share_of, shares_a_bar, style_in, style_named, style_names, values_of, variant_named, variants_of
from llamatron.macro_composer.band_choices import BandChoices
from llamatron.macro_composer.choices_part import set_each_kept
from llamatron.macro_composer.composer import composed
from llamatron.macro_composer.hook_choices import HookChoices
from llamatron.macro_composer.kit_choices import KitChoices
from llamatron.macro_composer.player_choices import PlayerChoices
from llamatron.macro_composer.riff_choices import RiffChoices
from llamatron.macro_composer.riffs import flattened_in
from llamatron.macro_composer.solo_choices import SoloChoices
from llamatron.macro_composer.song_plan import faded, SongPlan
from llamatron.macro_composer.sound_choices import SoundChoices
from llamatron.macro_composer.tune_choices import TuneChoices
from llamatron.music import note as note_values
from llamatron.playback.song_renderer import SongRenderer
from llamatron.strings import errors, macro_composer as composer_text, marks as marks_text
from llamatron.support import version as version_values
from llamatron.support.kept import kept_while


def data_laid_over(*, under, over):
    """Plain data with other data laid over it: a mapping's fields are laid over field by field, and anything else is replaced."""
    if isinstance(under, dict) and isinstance(over, dict):
        return {**under, **{field: data_laid_over(under=under[field], over=value) if field in under else value for field, value in over.items()}}
    return over


@functools.cache
def style_of(genre):
    """Return a genre's style template, read once however often it is asked for; nothing changes it."""
    return style_named(genre)


def genre_names():
    """Return the genres there are, by the names their choices are kept under, in the order of their titles."""
    return sorted(style_names(), key=genre_title)


def genre_title(genre):
    """Return a genre's name as people read it."""
    return style_of(genre)[arranger.TITLE]


def own_copy_of(entry):
    """Return a section's entry sharing no list and no dictionary with the entry given."""
    return copy.deepcopy(entry)


def chords_from_text(text):
    """Return chords typed as degrees with a space between, a flat or a sharp before a degree, such as 6 4 1 b7, two chords that share a bar joined by a dash, such as 1-5, as the arranger reads them."""
    def chord_typed(word):
        mark = word[0] if word and word[0] in wizard_limits.MARKS_TYPED else None
        number = word[1:] if mark else word
        if not number.isdigit() or not wizard_limits.FIRST_DEGREE_OF_SCALE <= int(number) <= wizard_limits.LAST_DEGREE_OF_SCALE:
            raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
        return {tune_notation.DEGREE: int(number), tune_notation.ACCIDENTAL: wizard_limits.MARKS_TYPED[mark]} if mark else int(number)
    chords = []
    for word in str(text).split():
        # Two chords joined by a dash share a bar, each half of it.
        halves = word.split(wizard_limits.SHARES_A_BAR)
        if len(halves) > wizard_limits.CHORDS_IN_A_SHARED_BAR:
            raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
        chords.append(chord_typed(word) if len(halves) == 1 else [chord_typed(half) for half in halves])
    if not chords:
        raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
    if any(shares_a_bar(chord) for chord in chords) and not fits_by_halves(chords):
        raise ValueError(errors.ERR_WIZARD_CHORDS_SHARED.format(most=limits.MAX_PROGRESSION_CHORDS // wizard_limits.CHORDS_IN_A_SHARED_BAR, value=text))
    return chords


def chords_as_text(chords):
    """Return chords as they are typed."""
    marks = {accidental: mark for mark, accidental in wizard_limits.MARKS_TYPED.items()}

    def typed(chord):
        return marks.get(chord_of(chord).get(tune_notation.ACCIDENTAL), '') + str(chord_of(chord)[tune_notation.DEGREE])
    return ' '.join(wizard_limits.SHARES_A_BAR.join(typed(half) for half in chord) if shares_a_bar(chord) else typed(chord) for chord in chords)


@functools.cache
def melody_works(*, genre, subgenre, style, variant=None):
    """Return whether a subgenre's tunes can be sketched by a melody style, found by making a song, once: a genre whose tunes
    are written as rows, with no rhythms to walk, takes only the style it was written for."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.take_variant(variant)
    choices.set_seed(wizard_limits.FIRST_SEED)
    try:
        Setlist.from_data(data=composed(given=arranged(style=style_of(genre), song={**choices.song_picks(subgenre), arranger.MELODY_ENGINE: style}), version=version_values.VERSION))
    except (ValueError, IndexError, KeyError, SongFileError):
        return False
    return True


@functools.cache
def melody_is_usual(*, genre, subgenre, style, variant=None):
    """Return whether a melody style sketches a subgenre's tunes just as the genre does unasked, found by making both, once:
    such a style is the usual one under its own name, and is nothing to choose."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.take_variant(variant)
    choices.set_seed(wizard_limits.FIRST_SEED)
    song = choices.song_picks(subgenre)
    return arranged(style=style_of(genre), song={**song, arranger.MELODY_ENGINE: style})[arranger.PARTS] == arranged(style=style_of(genre), song=song)[arranger.PARTS]


@functools.cache
def hook_matters(*, genre, subgenre, form, variant=None):
    """Return whether a hook changes a subgenre's song in a form, found by making the song with one and without, once: where
    nobody carries a tune in the sections that mark a hook, a hook is nothing to choose."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.take_variant(variant)
    choices.set_form(form)
    choices.set_seed(wizard_limits.FIRST_SEED)
    song = choices.song_picks(subgenre)
    return arranged(style=style_of(genre), song={**song, melody_writer.HOOK: True})[arranger.PARTS] != arranged(style=style_of(genre), song={**song, melody_writer.HOOK: False})[arranger.PARTS]


@functools.cache
def bars_work(*, genre, subgenre, kind, bars, plays=None, variant=None):
    """Return whether a subgenre's parts can fill a section of a kind at a length, found by making one and measuring it, once:
    some parts are written over several bars and divide only some lengths, and some, as a chorus of twelve bars, last as long
    as they are written whatever is asked. Given the section's players, only their parts are asked, since a part that sits
    out cannot time the section."""
    style = style_in(style=style_of(genre), template=subgenre, variant=variant)
    song = {arranger.NAME: kind, arranger.TITLE: kind, arranger.STYLE: genre, arranger.TEMPLATE: subgenre, arranger.VARIANT: variant, arranger.KEY: {arranger.ROOT: wizard_limits.USUAL_ROOTS[wizard_limits.MAJOR], arranger.TYPE: wizard_limits.MAJOR}, arranger.SEED: wizard_limits.FIRST_SEED,
            arranger.FORM: [kind], arranger.SECTIONS: {kind: {arranger.KIND: kind, arranger.BARS: bars, **({} if plays is None else {arranger.PLAYS: list(plays)})}}}
    try:
        given = arranged(style=style, song=song)
        made = Setlist.from_data(data=composed(given=given, version=version_values.VERSION)).get_song(kind)
        seconds = sum(float(scene.seconds) for scene in SongRenderer(made).estimate())
    except (ValueError, SongFileError):
        return False
    wanted = float(bars * bar_length(str(picked(style=style, song=song).get(arranger.METER, arranger.COMMON_TIME))) * wizard_limits.QUARTERS_IN_WHOLE * wizard_limits.SECONDS_IN_MINUTE / made.get_tempo())
    return abs(seconds - wanted) < wizard_limits.PART_OF_A_BAR



def section_labels_key(choices):
    """What the sections' labels are worked out from: the form chosen, while a suggested form is followed, and the song's own
    sections' kinds once it has its own."""
    if choices._sections is None:
        return (choices._genre, choices._subgenre, choices._variant, choices._form)
    return tuple(entry[arranger.KIND] for entry in choices._sections)

class WizardChoices:
    """The choices of one run of the song wizard."""

    __slots__ = ('_extras', '_stages', '_genre', '_subgenre', '_root', '_scale_type', '_tempo', '_form', '_seed', '_sections', '_melody', '_hook', '_sounds_part', '_solos', '_tunes', '_band', '_kit', '_riffs_part', '_gauges', '_melody_settings', '_answers', '_answers_of', '_offers', '_offers_of', '_offers_held', '_offers_mixed', '_kept', '_variant')

    def __init__(self):
        # Answers found by making the song, each kept until a choice changes.
        self._answers = {}
        self._answers_of = None
        # Answers that only say what a page offers, which fields show and which values a field lists, each found by making
        # the song more than once. A page holds them while one cell's value is stepped, so that each step does not make
        # those songs again, and lets them go when the cursor leaves the cell (hold_offers).
        self._offers = {}
        self._offers_of = None
        self._offers_held = False
        self._offers_mixed = False
        # The answers of the methods written under kept_while, each with the key it was worked out for.
        self._kept = {}
        self._genre = None
        self._subgenre = None
        # The kind of song the subgenre makes, where the subgenre holds several.
        self._variant = None
        self._root = None
        self._scale_type = None
        self._tempo = None
        self._form = None
        self._seed = None
        # The form's sections once a person has changed them, each its kind and what it changes of the kind; None while a suggested form is followed.
        self._sections = None
        # The melody style chosen for the song's tunes, or None for the one the genre gives each player.
        self._melody = None
        # The parts of the choices, each holding what was chosen of one thing of the song.
        self._band = BandChoices(choices=self)
        self._kit = KitChoices(choices=self)
        self._hook = HookChoices(choices=self)
        self._riffs_part = RiffChoices(choices=self)
        self._sounds_part = SoundChoices(choices=self)
        self._solos = SoloChoices(choices=self)
        self._tunes = TuneChoices(choices=self)
        self._gauges = {}
        self._melody_settings = {}
        # What a song file lays over the song's picks: the song's plan, and anything a section is given, as its chords or a tune.
        self._extras = {}
        # How the song starts and ends, as chosen: the ways, the first player and the setup's bars.
        self._stages = {}

    # Reading and keeping the choices.

    @classmethod
    def from_data(cls, data):
        """Return the choices a song kept, leaving out whatever no longer fits, as a genre renamed since: what is left out is chosen again."""
        choices = cls()
        setters = [(arranger.GENRE, choices.set_genre), (wizard_limits.SUBGENRE, choices.set_subgenre), (arranger.VARIANT, choices.take_variant), (arranger.ROOT, choices.set_root), (arranger.TYPE, choices.set_scale_type), (arranger.TEMPO, choices.set_tempo), (arranger.FORM, choices.set_form), (arranger.SEED, choices.set_seed)]
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
        # A song kept before answering could be chosen keeps to what was made then.
        self._band.forget_players()
        # And a song kept has the riff it kept, or none: the riff its kind of music gives a new song is no part of it.
        self._extras.pop(riffs_values.RIFF, None)
        kept = [(self._band.set_way, [dict(trait=trait, value=value) for trait, value in (data.get(arranger.PICKS) or {}).items()]),
                (self._band.take_level, [dict(player=player, level=level) for player, level in (data.get(arranger.PLAYERS) or {}).items()]),
                (self._band.take_kept_player_gauge, [dict(player=player, gauge=gauge, place=place) for player, places in (data.get(wizard_limits.PLAYER_GAUGES_KEPT) or {}).items() for gauge, place in places.items()]),
                (self._band.take_kept_without, [dict(role=role) for role in data.get(arranger.WITHOUT) or []]),
                (self._kit.read, [dict(data=data)]),
                (self._band.take_kept_guitarists, [dict(count=data[wizard_limits.GUITARISTS_KEPT])] if data.get(wizard_limits.GUITARISTS_KEPT) else []),
                (self._sounds_part.read, [dict(data=data)]),
                (self._band.take_kept_beside, [dict(kept=data[wizard_limits.BESIDE_KEPT])] if isinstance(data.get(wizard_limits.BESIDE_KEPT), dict) else []),
                (self.set_own_sections, [dict(sections=data[wizard_limits.OWN_SECTIONS])] if data.get(wizard_limits.OWN_SECTIONS) else []),
                (self._set_kept_melody, [dict(style=data[wizard_limits.MELODY_STYLE])] if data.get(wizard_limits.MELODY_STYLE) else []),
                (self._hook.read, [dict(data=data)]),
                (self.set_melody_gauge, [dict(name=name, position=position) for name, position in (data.get(wizard_limits.GAUGES_KEPT) or {}).items()]),
                (self._band.take_kept_player_row, [dict(role=role, name=name, values=values) for role, rows in (data.get(wizard_limits.PLAYER_ROWS_KEPT) or {}).items() for name, values in rows.items()]
                 if isinstance(data.get(wizard_limits.PLAYER_ROWS_KEPT), dict) and all(isinstance(rows, dict) for rows in data[wizard_limits.PLAYER_ROWS_KEPT].values()) else []),
                (self._set_kept_melody_setting, [dict(name=name, value=value) for name, value in (data.get(wizard_limits.MELODY_SETTINGS_KEPT) or {}).items()]),
                (self._set_kept_extras, [dict(extras=data[wizard_limits.EXTRAS_KEPT])] if data.get(wizard_limits.EXTRAS_KEPT) else []),
                (self._set_kept_stages, [dict(stages=data[wizard_limits.STAGES_KEPT])] if isinstance(data.get(wizard_limits.STAGES_KEPT), dict) else [])]
        set_each_kept(kept)

    def to_data(self):
        """Return the choices made, as plain data a song keeps."""
        band = self._band.to_data()
        held = {arranger.GENRE: self._genre, wizard_limits.SUBGENRE: self._subgenre, arranger.VARIANT: self._variant, arranger.ROOT: self._root, arranger.TYPE: self._scale_type, arranger.TEMPO: self._tempo, arranger.FORM: self._form, arranger.SEED: self._seed,
                **{field: band.get(field) for field in (arranger.PICKS, arranger.PLAYERS, arranger.WITHOUT, wizard_limits.PLAYER_GAUGES_KEPT, wizard_limits.PLAYER_ROWS_KEPT, wizard_limits.BESIDE_KEPT)},
                wizard_limits.OWN_SECTIONS: [own_copy_of(entry) for entry in self._sections] if self._sections is not None else None,
                wizard_limits.MELODY_STYLE: self._melody, **self._hook.to_data(), **self._sounds_part.to_data(),
                wizard_limits.GUITARISTS_KEPT: band.get(wizard_limits.GUITARISTS_KEPT),
                **self._kit.to_data(), wizard_limits.GAUGES_KEPT: dict(self._gauges) or None, wizard_limits.MELODY_SETTINGS_KEPT: dict(self._melody_settings) or None,
                wizard_limits.EXTRAS_KEPT: self.get_song_extras() or None, wizard_limits.STAGES_KEPT: dict(self._stages) or None}
        return {field: value for field, value in held.items() if value is not None}

    # The genre and the subgenre, which everything else follows.

    def player(self, role):
        """Return the choices of one player of the band, by the player's name in the genre's band."""
        return PlayerChoices(choices=self, role=role)

    def get_band(self):
        """Return the choices of the band, a part of these choices."""
        return self._band

    def get_kit(self):
        """Return the choices of the drum kit, a part of these choices."""
        return self._kit

    def get_tunes(self):
        """Return the choices of the tunes, a part of these choices."""
        return self._tunes

    def get_solos(self):
        """Return the choices of the solos, a part of these choices."""
        return self._solos

    def get_sounds(self):
        """Return the choices of the sounds, a part of these choices."""
        return self._sounds_part

    def get_riffs(self):
        """Return the choices of the riffs, a part of these choices."""
        return self._riffs_part

    def get_hook(self):
        """Return the choices of the hook, a part of these choices."""
        return self._hook

    def get_genre(self):
        return self._genre

    def set_genre(self, genre):
        """Choose a genre, which leaves the subgenre to be chosen again, since each genre has its own."""
        if genre not in style_names():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_GENRE.format(value=genre))
        if genre != self._genre:
            self._genre = genre
            self._subgenre = None
            self._variant = None
            self._form = None
            self._sections = None
            self._stages = {}
            self._melody = None
            self._hook.reset()
            # A plan is one genre's: its energies and its joins are the genre's own.
            self._extras.pop(song_plan.PLAN_OF_SONG, None)
            self._extras.pop(arranger.MELODY, None)
            self._extras.pop(arranger.GROOVE, None)
            # A player's loudness is one genre's player's.
            self._extras.pop(arranger.DYNAMICS, None)
            self._extras.pop(arranger.LOUDNESS, None)
            self._extras.pop(wizard_limits.TUNE_TAKES, None)
            self._extras.pop(wizard_limits.MELODY_CHOSEN, None)
            # A riff whose notes were written by hand is the person's own, which no genre gives up: whoever knows it plays it again
            # wherever a band has the player and a form has the kind of section.
            self._riffs_part.remove_riffs(lambda entry: entry.get(arranger.RIFF_OWN) is None)
            self._extras.pop(arranger.TUNE_BY, None)
            self._extras.pop(arranger.TUNE_BY_SONG, None)
            self._forget_band()

    def lost_with_genre(self):
        """Return what choosing another genre would give up of what was chosen by hand and what it would keep, each a dictionary of
        counts by kind that leaves out a kind counting nothing. Before a subgenre is chosen nothing has been chosen to lose."""
        if self._genre is None or self._subgenre is None:
            return {}, {}
        usual = WizardChoices()
        usual.set_genre(self._genre)
        usual.set_subgenre(self._subgenre)
        if self._variant != usual._variant:
            usual.set_variant(self._variant)
        own = self._band_as_counted()
        untouched = usual._band_as_counted()
        settings = sum(1 for name in own.keys() | untouched.keys() if own.get(name) != untouched.get(name))
        settings += sum(1 for name in wizard_limits.EXTRAS_OF_ONE_GENRE if self._extras.get(name))
        lost = {wizard_limits.LOST_BAND_SETTINGS: settings,
                wizard_limits.LOST_OWN_CHORDS: sum(1 for entry in self.section_entries() if entry.get(wizard_limits.OWN_OF_SECTION, {}).get(arranger.CHORDS)),
                wizard_limits.LOST_FORM: int(self._sections is not None or self._form != usual._form),
                wizard_limits.LOST_TUNE_TAKES: len(self._extras.get(wizard_limits.TUNE_TAKES, {})) + int(self._hook.get_hook_take() != melody_writer.FIRST_HOOK_TAKE),
                wizard_limits.LOST_RIFFS: self._riffs_part.written_count(by_hand=False)}
        kept = {wizard_limits.KEPT_OWN_TUNES: len(self._extras.get(arranger.OWN_TUNES, {})), wizard_limits.KEPT_OWN_RIFFS: self._riffs_part.written_count(by_hand=True)}
        return {kind: count for kind, count in lost.items() if count}, {kind: count for kind, count in kept.items() if count}

    def _band_as_counted(self):
        """Return every setting of the band another genre forgets, each under a name of its own, so that two bands can be compared
        setting by setting."""
        by_name = {(wizard_limits.GENRE_SETTING, name): value for name, value in (
            (wizard_limits.MELODY_STYLE, self._melody),)}
        for kept_as, held in ((wizard_limits.GAUGES_KEPT, self._gauges), (wizard_limits.MELODY_SETTINGS_KEPT, self._melody_settings), (wizard_limits.STAGES_KEPT, self._stages)):
            for name, value in held.items():
                if isinstance(value, dict):
                    by_name.update({(kept_as, name, inner): each for inner, each in value.items()})
                else:
                    by_name[(kept_as, name)] = value
        return {**by_name, **self._band.counted(), **self._kit.counted(), **self._hook.counted(), **self._sounds_part.counted()}

    def subgenres(self):
        """Return the chosen genre's subgenres, sorted by name, or none before a genre is chosen."""
        return sorted(self.style()[arranger.TEMPLATES]) if self._genre else []

    def get_subgenre(self):
        return self._subgenre

    def set_subgenre(self, subgenre):
        """Choose a subgenre of the genre, and take its usual tempo, scale and form, which a person may then change."""
        if subgenre not in self.subgenres():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SUBGENRE.format(value=subgenre))
        if subgenre != self._subgenre:
            self._subgenre = subgenre
            # The commonest kind of song the subgenre holds, which a person may change.
            self._variant = next(iter(self.variants()), None)
            self._take_usual_of_subgenre()

    def variants(self):
        """Return the kinds of song the subgenre holds, by name, the commonest first, or none where the subgenre is one kind."""
        if self._subgenre is None:
            return []
        return [entry[arranger.NAME] for entry in variants_of(style=style_of(self._genre), template=self._subgenre)]

    def get_variant(self):
        return self._variant

    def variant_says(self, *, variant=None):
        """Return the line that says what a kind of song is, the chosen kind unless one is named, or None."""
        entry = variant_named(style=style_of(self._genre), template=self._subgenre, variant=variant or self._variant) if self._subgenre else None
        return entry.get(arranger.VARIANT_SAYS) if entry else None

    def set_variant(self, variant):
        """Choose the kind of song the subgenre makes, and take the kind's usual tempo, scale, form and band, as choosing a subgenre does."""
        if variant not in self.variants():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_VARIANT.format(choices=', '.join(self.variants()), value=variant))
        if variant != self._variant:
            self._variant = variant
            self._take_usual_of_subgenre()

    def take_variant(self, variant):
        """Choose a kind of song a kept song or a check names, where the subgenre has that kind; none leaves the subgenre's commonest."""
        if variant is not None:
            self.set_variant(variant)

    def _take_usual_of_subgenre(self):
        """Take what the subgenre and its kind of song usually have, leaving behind whatever was chosen for another."""
        self._forget_band()
        self._tempo = self.usual_tempo()
        self._scale_type = self.usual_scale_type()
        self._root = wizard_limits.USUAL_ROOTS[self._scale_type]
        self._form = None
        self._sections = None
        self._stages = {}
        self._melody = None
        self._hook.reset(writing=False)
        self._band.take_usual()
        # A swing chosen was chosen beside another subgenre's or kind's own.
        self._extras.pop(arranger.GROOVE, None)
        self._riffs_part.take_riff_of_genre()

    def is_ready(self):
        """Return whether a song can be made: a genre and a subgenre are chosen, and the rest has its usual values."""
        return self._subgenre is not None

    # What the subgenre usually has.

    @kept_while(lambda choices: (choices._genre, choices._subgenre, choices._variant, repr(choices._band.get_ways())))
    def picks(self):
        """Return every trait's pick: the ways of playing chosen, and the subgenre's for the rest. The picks are worked out once
        for a genre, a subgenre and the ways chosen, and a caller never changes what is returned."""
        return self.picks_with(self._band.get_ways())

    def usual_tempo(self):
        style = self.style()
        return self.picks().get(arranger.TEMPO, style[arranger.TRAITS][arranger.TEMPO][arranger.USUAL])

    def tempo_range(self):
        """Return the lowest and the highest tempo the genre usually has, which is said beside the tempo and never enforced."""
        tempos = self.style()[arranger.TRAITS][arranger.TEMPO]
        return tempos[wizard_limits.LOWEST], tempos[wizard_limits.HIGHEST]

    def usual_scale_type(self):
        """Return the scale type the subgenre's chords are usually in, or major where its chords say nothing of one."""
        style = self.style()
        trait = style.get(arranger.CHORD_TRAIT_FIELD, arranger.CHORD_TRAIT)
        entry = values_of(style=style, trait=trait).get(self.picks().get(trait), {})
        usual = entry.get(arranger.SCALE_TYPE, wizard_limits.MAJOR)
        return usual if usual in wizard_limits.SCALE_TYPES else wizard_limits.MAJOR

    # The key and the tempo.

    def get_root(self):
        return self._root

    def set_root(self, root):
        if root not in note_values.ROOT_NAMES:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ROOT.format(value=root))
        self._root = root

    def get_scale_type(self):
        return self._scale_type

    def set_scale_type(self, scale_type):
        if scale_type not in wizard_limits.SCALE_TYPES:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SCALE_TYPE.format(value=scale_type))
        self._scale_type = scale_type

    def get_tempo(self):
        return self._tempo

    def set_tempo(self, tempo):
        """Set the tempo to any the tracker plays; the genre's usual range is advice."""
        if isinstance(tempo, bool) or not isinstance(tempo, int) or not limits.MIN_TEMPO <= tempo <= limits.MAX_TEMPO:
            raise ValueError(errors.ERR_WIZARD_TEMPO.format(low=limits.MIN_TEMPO, high=limits.MAX_TEMPO, value=tempo))
        self._tempo = tempo

    # The swing.

    def has_swing(self):
        """Return whether the song can be swung: a subgenre in four whose bars are not written in triplets, which swing already."""
        if not self.is_ready() or self.meter() != arranger.COMMON_TIME:
            return False
        habits = self.style().get(arranger.MELODY, {})
        return (habits if melody_writer.GRID in habits else habits.get(arranger.COMMON_TIME, {})).get(melody_writer.GRID) != wizard_limits.TRIPLET_GRID

    def swings(self):
        return list(wizard_limits.SWINGS)

    def swing_of_genre(self):
        """Return the swing the subgenre is usually played with, or none."""
        return self.style().get(arranger.GROOVE, arranger.NO_GROOVE) if self.has_swing() else arranger.NO_GROOVE

    def get_swing(self):
        return self._extras.get(arranger.GROOVE, self.swing_of_genre())

    def set_swing(self, swing):
        """Say the swing the song is played with, one of the grooves every set has or none; the subgenre's own is kept as the subgenre's."""
        if not self.has_swing() or swing not in wizard_limits.SWINGS:
            raise ValueError(errors.ERR_WIZARD_SWING.format(choices=', '.join(wizard_limits.SWINGS), value=swing))
        self._extras.pop(arranger.GROOVE, None)
        if swing != self.swing_of_genre():
            self._extras[arranger.GROOVE] = swing
        self.clear_answers()

    # The form.

    def _forms(self):
        return forms_of(style=self.style(), song={arranger.TEMPLATE: self._subgenre}) if self.is_ready() else []

    def forms(self):
        """Return the names of the forms the subgenre suggests, the commonest first."""
        return [form[arranger.NAME] for form in sorted(self._forms(), key=share_of, reverse=True)]

    def get_form(self):
        """Return the form chosen, or the commonest of the subgenre's until one is, or None before a subgenre is chosen."""
        if self._form is not None:
            return self._form
        forms = self.forms()
        return forms[0] if forms else None

    def form_section_count(self, form):
        """Return how many sections a suggested form has."""
        return len(next((form_[arranger.SECTIONS] for form_ in self._forms() if form_[arranger.NAME] == form), []))

    def set_form(self, form):
        """Choose one of the forms the subgenre suggests, which puts its sections in place of any a person changed. How the song was
        chosen to start and to end is kept, with who starts alone and how long a stage lasts, where the new form can start and end so."""
        if form not in self.forms():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_FORM.format(value=form))
        start = self.get_start() if wizard_limits.START_KEPT in self._stages else None
        end = self.get_end() if wizard_limits.END_KEPT in self._stages else None
        kept = {field: value for field, value in self._stages.items() if field not in (wizard_limits.START_KEPT, wizard_limits.END_KEPT)}
        self._form = form
        self._sections = None
        self._stages = {}
        self.clear_answers()
        for way, offered, set_way in ((start, self.starts, self.set_start), (end, self.ends, self.set_end)):
            if way is not None and way in offered():
                self._stages.update(kept)
                try:
                    set_way(way)
                except ValueError:
                    # A way the new form cannot be made with is given up, and the form starts or ends as it usually does.
                    pass
        if wizard_limits.START_KEPT not in self._stages and wizard_limits.END_KEPT not in self._stages:
            self._stages = {}

    # The form's sections, which follow the form chosen until a person changes one; the form is then the song's own.

    def has_own_form(self):
        """Return whether a person has changed the form's sections, so that the form is no longer one the subgenre suggests."""
        return self._sections is not None

    def section_entries(self):
        """Return the sections in order, each its kind and what it changes of the kind: the song's own, or the chosen form's."""
        if self._sections is not None:
            return self._sections
        return self.form_section_entries()

    @kept_while(lambda choices: (choices._genre, choices._subgenre, choices._variant, choices._form))
    def form_section_entries(self):
        """Return the sections of the form chosen, each its kind, worked out once for a form, since a page asks for the sections
        many times a key. A caller that changes a section changes its own copy (own_section_entries)."""
        chosen = self.get_form()
        return [{arranger.KIND: kind} for kind in next((form[arranger.SECTIONS] for form in self._forms() if form[arranger.NAME] == chosen), [])]

    def own_section_entries(self):
        """Return the song's own sections to change, starting them from the chosen form the first time."""
        if self._sections is None:
            self._sections = [dict(entry) for entry in self.section_entries()]
        return self._sections

    def section_entry(self, place):
        entries = self.section_entries()
        if isinstance(place, bool) or not isinstance(place, int) or not 0 <= place < len(entries):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION.format(value=place))
        return entries[place]

    def form_sections(self):
        """Return the sections of the form in the order they play, by name. A section is named after its kind, and one that
        differs from the first of its kind, in its bars or its players, gets a letter after the name, since sections of one
        name are the same section played again."""
        names = []
        seen = {}
        for place, entry in enumerate(self.section_entries()):
            own = (entry.get(arranger.BARS), tuple(entry[arranger.PLAYS]) if arranger.PLAYS in entry else None)
            if not self.has_song_plan() and self._own_without_plan(entry):
                # A section with chords, a tempo, a key or a scale of its own is a section of its own, where no plan makes one for each place.
                # A fade is told apart by its way, since a kind that opens the song and closes it fades in at one and out at the other.
                own = (*own, repr(sorted(self._with_fade_way(place=place, own=self._own_without_plan(entry)).items(), key=str)))
            # The kind as the genre describes it comes first, so that an unchanged section keeps the kind's plain name.
            variants = seen.setdefault(entry[arranger.KIND], [(None, None)])
            if own not in variants:
                variants.append(own)
            place = variants.index(own)
            names.append(entry[arranger.KIND] if not place else marks_text.MSG_WIZARD_SECTION_VARIANT.format(kind=entry[arranger.KIND], letter=chr(ord(wizard_limits.FIRST_VARIANT_LETTER) + place)))
        return names

    @kept_while(section_labels_key)
    def section_labels(self):
        """Return what each section is shown as, in order: its kind, and where the form has several of a kind, the kind with
        a dash and the section's count among them, as the tracker numbers every name it makes."""
        kinds = [entry[arranger.KIND] for entry in self.section_entries()]
        counts = {}
        labels = []
        for kind in kinds:
            counts[kind] = counts.get(kind, 0) + 1
            labels.append(kind if kinds.count(kind) == 1 else marks_text.MSG_WIZARD_SECTION_NUMBERED.format(kind=kind, number=counts[kind]))
        return tuple(labels)

    def _song_sections(self):
        """Return the song's own sections as the arranger reads them, by name: each its kind and what it changes, with the chords and the scene's
        tempo, key and scale a section was given where no plan lays those out by place."""
        return {name: {**{field: value for field, value in entry.items() if field != wizard_limits.OWN_OF_SECTION}, **self._as_section(place=place, entry=entry)} for place, (name, entry) in enumerate(zip(self.form_sections(), self.section_entries()))}

    def _plan_with_lines(self, *, kind, plan, lines):
        """A section's plan of lines with what each line was given of its own laid over it: its notes, its breath and whether a note comes early."""
        usual = self.style()[arranger.SECTIONS][kind].get(wizard_limits.PLAN, []) if plan is None else plan
        return [{**entry, **(lines.get(count) or {})} for count, entry in enumerate(copy.deepcopy(usual))]

    def _own_without_plan(self, entry):
        """What a section was given of its own that a song with no plan can still take: chords, a tempo, the tempo at its end, a key and a scale."""
        return {field: value for field, value in entry.get(wizard_limits.OWN_OF_SECTION, {}).items() if field in (*wizard_limits.OWN_WITHOUT_PLAN, *wizard_limits.FADE_OWN) or field == wizard_limits.LINES_OF_SECTION}

    def _as_section(self, *, place, entry):
        if self.has_song_plan():
            return {}
        own = self._own_without_plan(entry)
        settings = {}
        if song_plan.TEMPO_OF_PLACE in own:
            settings[song_plan.SCENE_TEMPO] = own[song_plan.TEMPO_OF_PLACE]
        if song_plan.TEMPO_END_OF_PLACE in own:
            settings[song_plan.SCENE_TEMPO_END] = own[song_plan.TEMPO_END_OF_PLACE]
        if song_plan.ROOT_OF_PLACE in own or song_plan.TYPE_OF_PLACE in own:
            settings[song_plan.SCALE_OF_PLACE] = {song_plan.ROOT_OF_PLACE: own.get(song_plan.ROOT_OF_PLACE, self._root), song_plan.TYPE_OF_PLACE: own.get(song_plan.TYPE_OF_PLACE, self._scale_type)}
        if own.get(song_plan.FADES):
            settings.update(faded(own=self._with_fade_way(place=place, own=own), loud=song_plan.UNFADED))
        if own.get(wizard_limits.LINES_OF_SECTION):
            return {wizard_limits.PLAN: self._plan_with_lines(kind=entry[arranger.KIND], plan=None, lines=own[wizard_limits.LINES_OF_SECTION]), **({arranger.CHORDS: copy.deepcopy(own[arranger.CHORDS])} if arranger.CHORDS in own else {}), **({arranger.SCENE_SETTINGS: settings} if settings else {})}
        return {**({arranger.CHORDS: copy.deepcopy(own[arranger.CHORDS])} if arranger.CHORDS in own else {}), **({arranger.SCENE_SETTINGS: settings} if settings else {})}

    def section_as_played(self, place):
        """Return a section as it will be played: its kind as the genre describes it, with what the section changes."""
        entry = self.section_entry(place)
        return section_of(name=entry[arranger.KIND], style=self.style(), song={arranger.SECTIONS: {entry[arranger.KIND]: entry}})

    def section_kinds(self):
        """Return the kinds of section the subgenre can play, in the genre's order: a kind nobody of the subgenre's band plays
        in, which would make no section at all, is left out, as is one whose parts do not fill its own length."""
        if not self.is_ready():
            return []
        sections = self.style()[arranger.SECTIONS]
        return [kind for kind, section in sections.items()
                if bars_work(genre=self._genre, subgenre=self._subgenre, variant=self._variant, kind=kind, bars=wizard_limits.HELD_BARS if section.get(arranger.HELD) else section[arranger.BARS])]

    def section_kind(self, place):
        return self.section_entry(place)[arranger.KIND]

    def section_is_held(self, place):
        """Return whether a section is one held chord, which lasts a bar whatever is said."""
        return bool(self.section_as_played(place).get(arranger.HELD))

    def section_bars(self, place):
        section = self.section_as_played(place)
        return wizard_limits.HELD_BARS if section.get(arranger.HELD) else section[arranger.BARS]

    def section_plays(self, place):
        """Return who plays in a section, by the names the genre gives its players."""
        return list(self.section_as_played(place).get(arranger.PLAYS, []))

    def section_usually_plays(self, place):
        """Return who plays in a section of its kind as the genre has the kind."""
        return list(self._usual(place).get(arranger.PLAYS, []))

    def add_section(self, *, place, kind):
        """Put a new section of a kind before a place in the form, as the genre describes the kind."""
        if kind not in self.section_kinds():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION_KIND.format(value=kind))
        if isinstance(place, bool) or not isinstance(place, int) or not 0 <= place <= len(self.section_entries()):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION.format(value=place))
        self.own_section_entries().insert(place, {arranger.KIND: kind})

    def copy_section(self, place):
        """Put a copy of a section straight after it."""
        entry = own_copy_of(self.section_entry(place))
        self.own_section_entries().insert(place + 1, entry)

    def remove_section(self, place):
        self.section_entry(place)
        if len(self.section_entries()) == 1:
            raise ValueError(errors.ERR_WIZARD_LAST_SECTION)
        del self.own_section_entries()[place]

    def move_section(self, *, place, offset):
        """Move a section earlier or later in the form, and return whether it moved, which it cannot past either end."""
        self.section_entry(place)
        moved = place + offset
        if not 0 <= moved < len(self.section_entries()):
            return False
        entries = self.own_section_entries()
        entries.insert(moved, entries.pop(place))
        return True

    def set_section_kind(self, *, place, kind):
        """Make a section another kind, as the genre describes that kind: what the section changed of its old kind is dropped."""
        self.section_entry(place)
        if kind not in self.section_kinds():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION_KIND.format(value=kind))
        self.own_section_entries()[place] = {arranger.KIND: kind}

    def _usual(self, place):
        return self.style()[arranger.SECTIONS][self.section_entry(place)[arranger.KIND]]

    def bars_offered(self, place):
        """Return the lengths a section may have, in bars: half its kind's usual length, the usual and twice that, leaving out
        any the genre's parts cannot fill, and nothing for a held section."""
        return list(self.offered(key=(wizard_limits.BARS_ANSWER, place), compute=lambda: self._bars_offered(place)))

    def _bars_offered(self, place):
        if self.section_is_held(place):
            return []
        usual = self._usual(place)[arranger.BARS]
        lengths = sorted({usual // wizard_limits.HALF, usual, usual * wizard_limits.HALF, self.section_bars(place)} - {0})
        return [bars for bars in lengths if bars == usual or self._bars_fit(place=place, bars=bars)]

    def _bars_fit(self, *, place, bars):
        """Return whether the players of a section can fill the section at a length: on their own, and then in this song, where
        a part may be written differently beside another section of the kind."""
        if not bars_work(genre=self._genre, subgenre=self._subgenre, variant=self._variant, kind=self.section_entry(place)[arranger.KIND], bars=bars, plays=tuple(self.section_plays(place))):
            return False
        trial = self.copied_for_trial()
        trial.own_section_entries()[place][arranger.BARS] = bars
        try:
            trial.written_setlist(name=self.section_entry(place)[arranger.KIND], version=version_values.VERSION)
        except (ValueError, SongFileError):
            return False
        return True

    def set_section_bars(self, *, place, bars):
        if isinstance(bars, bool) or not isinstance(bars, int) or bars not in self.bars_offered(place):
            raise ValueError(errors.ERR_WIZARD_SECTION_BARS.format(value=bars))
        entry = self.own_section_entries()[place]
        entry.pop(arranger.BARS, None)
        if bars != self._usual(place)[arranger.BARS]:
            entry[arranger.BARS] = bars

    def set_section_plays(self, *, place, role, on):
        """Have a player play in a section or sit it out. A section keeps one player, and a length its players can fill."""
        self._band.role_named(role)
        plays = [name for name in self._band.roles() if (name in self.section_plays(place) or (on and name == role)) and (on or name != role)]
        if not plays:
            raise ValueError(errors.ERR_WIZARD_SECTION_NEEDS_PLAYER)
        entry = self.own_section_entries()[place]
        entry.pop(arranger.PLAYS, None)
        if sorted(plays) != sorted(self._usual(place).get(arranger.PLAYS, [])):
            entry[arranger.PLAYS] = plays
        # A length the players left cannot fill gives way to the kind's usual length.
        if arranger.BARS in entry and not self._bars_fit(place=place, bars=entry[arranger.BARS]):
            del entry[arranger.BARS]

    def set_own_sections(self, *, sections):
        """Take a form's sections a song kept, each through the setters, or none of them where one no longer fits."""
        kept = self._sections
        self._sections = []
        try:
            for place, entry in enumerate(sections):
                self.add_section(place=place, kind=entry[arranger.KIND])
                if arranger.BARS in entry:
                    self.set_section_bars(place=place, bars=entry[arranger.BARS])
                for role in self._band.roles():
                    if arranger.PLAYS in entry and (role in entry[arranger.PLAYS]) != (role in self.section_plays(place)) and role in entry[arranger.PLAYS]:
                        self.set_section_plays(place=place, role=role, on=True)
                for role in self._band.roles():
                    if arranger.PLAYS in entry and role not in entry[arranger.PLAYS] and role in self.section_plays(place):
                        self.set_section_plays(place=place, role=role, on=False)
                if wizard_limits.BESIDE_KEPT in entry:
                    # What the answering player does in the section is kept as chosen, and is used wherever somebody answers there.
                    if entry[wizard_limits.BESIDE_KEPT] not in interplay_values.WAYS:
                        raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=entry[wizard_limits.BESIDE_KEPT]))
                    self._sections[place][wizard_limits.BESIDE_KEPT] = entry[wizard_limits.BESIDE_KEPT]
                if entry.get(wizard_limits.OWN_OF_SECTION):
                    self._sections[place][wizard_limits.OWN_OF_SECTION] = {field: self._checked_own(field=field, value=value) for field, value in entry[wizard_limits.OWN_OF_SECTION].items()}
            if not self._sections:
                raise ValueError(errors.ERR_WIZARD_LAST_SECTION)
        except (KeyError, TypeError, ValueError):
            self._sections = kept
            raise ValueError(errors.ERR_WIZARD_BAD_SECTIONS.format(value=sections)) from None

    # How the song starts and ends: stages before the first section with a tune and after the last, each a section of its own.

    def _drums_role(self):
        return next((role for role in self._band.roles() if self._band.role_named(role).get(arranger.DRUMS) and self.player(role).is_in()), None)

    def _usual_form_kinds(self):
        return next((form[arranger.SECTIONS] for form in self._forms() if form[arranger.NAME] == self.get_form()), [])

    def intro_kind(self):
        """The kind of section a song of the subgenre opens with: the first of its form's, where that kind has no tune."""
        kinds = self._usual_form_kinds()
        sections = self.style()[arranger.SECTIONS]
        if not kinds or sections[kinds[0]].get(arranger.HELD):
            return None
        # A kind with a tune opens the song only where the form plays the kind once, at its start: one played again later is the song's body.
        return kinds[0] if not sections[kinds[0]].get(wizard_limits.PLAN) or kinds.count(kinds[0]) == 1 else None

    def _ending_kind(self):
        """The kind of section that is one held chord, where the subgenre has one."""
        return next((kind for kind in self.section_kinds() if self.style()[arranger.SECTIONS][kind].get(arranger.HELD)), None)

    def _outro_kind(self):
        """The kind of section played after the last tune: the genre's outro where it has one, else its intro again."""
        return wizard_limits.OUTRO_KIND if wizard_limits.OUTRO_KIND in self.section_kinds() else self.intro_kind()

    def _stage_players(self, kind):
        """Who plays in a kind of section, the first player first and the rest in the band's order."""
        plays = [role for role in self._band.roles() if role in self.style()[arranger.SECTIONS][kind].get(arranger.PLAYS, []) and self.player(role).is_in()]
        first = self.get_first_player()
        return [first, *(role for role in plays if role != first)] if first in plays else plays

    def first_players(self):
        """Return who can start the song alone: the players of its opening kind of section."""
        kind = self.intro_kind()
        return [] if kind is None else [role for role in self._band.roles() if role in self.style()[arranger.SECTIONS][kind].get(arranger.PLAYS, []) and self.player(role).is_in()]

    def get_first_player(self):
        """Return who starts the song alone and is left alone at its end: the one chosen, or the first of the opening's players who is not the drummer."""
        offered = self.first_players()
        if self._stages.get(wizard_limits.FIRST_PLAYER_KEPT) in offered:
            return self._stages[wizard_limits.FIRST_PLAYER_KEPT]
        return next((role for role in offered if role != self._drums_role()), offered[0] if offered else None)

    def _setup_bars_possible(self):
        """How long a stage could last, in bars: half the opening kind's length, the length and twice it."""
        kind = self.intro_kind()
        if kind is None:
            return []
        usual = self.style()[arranger.SECTIONS][kind][arranger.BARS]
        return sorted({usual // wizard_limits.HALF, usual, usual * wizard_limits.HALF} - {0})

    def setup_bars_offered(self):
        """Return how long a stage of a start or an ending may last, in bars: of the lengths a stage could last, those the song as it starts and ends can be made with."""
        return list(self.offered(key=wizard_limits.SETUP_BARS_ANSWER, compute=lambda: [bars for bars in self._setup_bars_possible() if bars == self.get_setup_bars() or self._setup_bars_work(bars)]))

    def _setup_bars_work(self, bars):
        trial = self.copied_for_trial()
        try:
            trial._restaged(change=lambda: trial._stages.update({wizard_limits.SETUP_BARS_KEPT: bars}))
        except ValueError:
            return False
        return True

    def get_setup_bars(self):
        possible = self._setup_bars_possible()
        kept = self._stages.get(wizard_limits.SETUP_BARS_KEPT)
        return kept if kept in possible else (self.style()[arranger.SECTIONS][self.intro_kind()][arranger.BARS] if possible else None)

    def _stage(self, *, kind, plays=None, own=None):
        """One stage: a section of a kind, played by some of its players for the setup's bars, with what the stage is given of its own."""
        usual = self.style()[arranger.SECTIONS][kind]
        entry = {arranger.KIND: kind}
        if plays is not None and sorted(plays) != sorted(usual.get(arranger.PLAYS, [])):
            entry[arranger.PLAYS] = [role for role in self._band.roles() if role in plays]
        if not usual.get(arranger.HELD) and self.get_setup_bars() != usual[arranger.BARS]:
            entry[arranger.BARS] = self.get_setup_bars()
        if own:
            entry[wizard_limits.OWN_OF_SECTION] = dict(own)
        return entry

    def _start_stages(self, way):
        """The sections a way of starting puts before the song's first tune, or None where the subgenre cannot start that way."""
        kind = self.intro_kind()
        drums = self._drums_role()
        if kind is None:
            return None
        players = self._stage_players(kind)
        whole = {arranger.KIND: kind}
        if way == wizard_limits.FULL_BAND:
            return [whole]
        if way == wizard_limits.STRAIGHT_IN:
            return []
        if way == wizard_limits.DRUMS_FIRST and drums in players and len(players) > 1:
            return [self._stage(kind=kind, plays=[drums]), whole]
        if way == wizard_limits.DRUM_FILL_IN and drums in players and self.has_song_plan():
            return [self._stage(kind=kind, plays=[drums], own={joins_values.LEAVES: wizard_limits.LEAVES_BIG_FILL})]
        if way == wizard_limits.ONE_PLAYER_FIRST and len(players) > 1 and players[0] != drums:
            return [self._stage(kind=kind, plays=players[:1]), whole]
        if way == wizard_limits.LAYERS and len(players) > 2:
            return [self._stage(kind=kind, plays=players[:count]) for count in range(1, len(players) + 1)]
        return None

    def _end_stages(self, way):
        """The sections a way of ending puts after the song's last tune, or None where the subgenre cannot end that way."""
        held = self._ending_kind()
        outro = self._outro_kind()
        chord = [{arranger.KIND: held}] if held is not None else []
        if way == wizard_limits.HELD_CHORD and held is not None:
            return chord
        if way == wizard_limits.HARD_STOP:
            return []
        if outro is None:
            return None
        players = self._stage_players(outro)
        if way == wizard_limits.OUTRO_THEN_CHORD and held is not None:
            return [self._stage(kind=outro), *chord]
        if way == wizard_limits.SLOWS_DOWN:
            return [self._stage(kind=outro, own={song_plan.TEMPO_END_OF_PLACE: max(self._tempo * wizard_limits.SLOWED_TO[0] // wizard_limits.SLOWED_TO[1], limits.MIN_TEMPO)}), *chord]
        if way == wizard_limits.STRIPS_DOWN and len(players) > 2:
            return [*(self._stage(kind=outro, plays=players[:count]) for count in range(len(players) - 1, 0, -1)), *chord]
        if way == wizard_limits.ONE_PLAYER_ALONE and len(players) > 1:
            return [self._stage(kind=outro, plays=players[:1]), *chord]
        if way == wizard_limits.REPEAT_AND_FADE:
            return [self._stage(kind=outro, own={song_plan.FADES: True})]
        return None

    def starts(self):
        """Return the ways the song can start, the plainest first."""
        return [way for way in wizard_limits.STARTS if self._start_stages(way) is not None] if self.is_ready() else []

    def ends(self):
        """Return the ways the song can end."""
        return [way for way in wizard_limits.ENDS if self._end_stages(way) is not None] if self.is_ready() else []

    def _head(self):
        """How many sections open the song before its first tune: those the way of starting kept made, while they stand as made, else the sections of the opening kind."""
        kept = self._start_stages(self._stages.get(wizard_limits.START_KEPT)) if wizard_limits.START_KEPT in self._stages else None
        entries = self.section_entries()
        if kept is not None and entries[:len(kept)] == kept:
            return len(kept)
        count = 0
        while count < len(entries) - 1 and entries[count][arranger.KIND] == self.intro_kind():
            count += 1
        return count

    def _tail(self):
        """How many sections close the song after its last tune: those the way of ending kept made, while they stand as made, else the held chord and the outro before it."""
        kept = self._end_stages(self._stages.get(wizard_limits.END_KEPT)) if wizard_limits.END_KEPT in self._stages else None
        entries = self.section_entries()
        if kept is not None and (not kept or entries[-len(kept):] == kept):
            return len(kept)
        count = 0
        closing = (self._ending_kind(), wizard_limits.OUTRO_KIND)
        while count < len(entries) - 1 and entries[len(entries) - 1 - count][arranger.KIND] in closing:
            count += 1
        return count

    def get_start(self):
        """Return the way the song starts, or None where its opening sections are a person's own."""
        entries = self.section_entries()
        head = entries[:self._head()]
        kept = self._stages.get(wizard_limits.START_KEPT)
        if kept in self.starts() and self._start_stages(kept) == head:
            return kept
        return next((way for way in self.starts() if self._start_stages(way) == head), None)

    def get_end(self):
        """Return the way the song ends, or None where its closing sections are a person's own."""
        entries = self.section_entries()
        tail = entries[len(entries) - self._tail():]
        kept = self._stages.get(wizard_limits.END_KEPT)
        if kept in self.ends() and self._end_stages(kept) == tail:
            return kept
        return next((way for way in self.ends() if self._end_stages(way) == tail), None)

    def _restaged(self, *, change, start=None, end=None):
        """Change how the song starts or ends: the sections between stay, and the stages are made again. A song that cannot then be made is as it was."""
        before = (copy.deepcopy(self._sections), dict(self._stages))
        entries = [own_copy_of(entry) for entry in self.section_entries()]
        head, tail = self._head(), self._tail()
        start = self.get_start() if start is None else start
        end = self.get_end() if end is None else end
        body = entries[head:len(entries) - tail]
        try:
            change()
            opening = entries[:head] if start is None else self._start_stages(start)
            closing = entries[len(entries) - tail:] if end is None else self._end_stages(end)
            if opening is None or closing is None or not body:
                raise ValueError(errors.ERR_WIZARD_START_UNMADE.format(problem=start if opening is None else end))
            self._sections = [*(own_copy_of(entry) for entry in opening), *body, *(own_copy_of(entry) for entry in closing)]
            if start is not None:
                self._stages[wizard_limits.START_KEPT] = start
            if end is not None:
                self._stages[wizard_limits.END_KEPT] = end
            self.clear_answers()
            self.written_setlist(name=wizard_limits.PREVIEW_NAME, version=version_values.VERSION)
        except (ValueError, KeyError, IndexError, SongFileError) as problem:
            self._sections, self._stages = before
            self.clear_answers()
            raise ValueError(errors.ERR_WIZARD_START_UNMADE.format(problem=problem)) from None

    def set_start(self, way):
        if way not in self.starts():
            raise ValueError(errors.ERR_WIZARD_START.format(value=way))
        self._restaged(change=lambda: None, start=way)

    def set_end(self, way):
        if way not in self.ends():
            raise ValueError(errors.ERR_WIZARD_END.format(value=way))
        self._restaged(change=lambda: None, end=way)

    def set_first_player(self, role):
        if role not in self.first_players():
            raise ValueError(errors.ERR_WIZARD_FIRST_PLAYER.format(value=role))
        self._restaged(change=lambda: self._stages.update({wizard_limits.FIRST_PLAYER_KEPT: role}))

    def set_setup_bars(self, bars):
        if isinstance(bars, bool) or bars not in self.setup_bars_offered():
            raise ValueError(errors.ERR_WIZARD_SETUP_BARS.format(value=bars))
        self._restaged(change=lambda: self._stages.update({wizard_limits.SETUP_BARS_KEPT: bars}))

    # A form made from a few answers, each question asked only where the subgenre can play the kind of section it is about.

    def form_questions(self):
        """Return the questions a form is made from, in order, each its name, the answers offered and the usual answer."""
        kinds = self.section_kinds()
        questions = [(wizard_limits.VERSES_FIRST, wizard_limits.COUNTS_ONE_OR_TWO, wizard_limits.ONE)]
        if wizard_limits.PRE_CHORUS in kinds:
            questions.append((wizard_limits.PRE_CHORUSES, wizard_limits.PRE_CHORUS_ANSWERS, wizard_limits.NO))
        if wizard_limits.BRIDGE in kinds:
            questions.append((wizard_limits.BRIDGE, wizard_limits.YES_OR_NO, wizard_limits.YES))
        if wizard_limits.SOLO in kinds:
            questions.append((wizard_limits.SOLOS, wizard_limits.SOLO_COUNTS, wizard_limits.ONE))
        if wizard_limits.DRUM_SOLO_KIND in kinds:
            questions.append((wizard_limits.DRUM_SOLO_KIND, wizard_limits.YES_OR_NO, wizard_limits.NO))
        return [*questions, (wizard_limits.LAST_CHORUSES, wizard_limits.COUNTS_ONE_OR_TWO, wizard_limits.TWO)] if wizard_limits.CHORUS_KIND in kinds and wizard_limits.VERSE_KIND in kinds else []

    def form_of_answers(self, answers):
        """Return the kinds of section, in order, of the form some answers ask for: a question left out takes its usual answer."""
        asked = {name: (offered, usual) for name, offered, usual in self.form_questions()}
        if not asked:
            raise ValueError(errors.ERR_WIZARD_NO_FORM_QUESTIONS)
        given = {}
        for name, (offered, usual) in asked.items():
            given[name] = answers.get(name, usual)
            if given[name] not in offered:
                raise ValueError(errors.ERR_WIZARD_FORM_ANSWER.format(name=name, value=given[name]))
        unknown = [name for name in answers if name not in asked]
        if unknown:
            raise ValueError(errors.ERR_WIZARD_FORM_ANSWER.format(name=unknown[0], value=answers[unknown[0]]))
        kinds = self.section_kinds()
        before = given.get(wizard_limits.PRE_CHORUSES, wizard_limits.NO)
        solos = wizard_limits.SOLO_COUNTS.index(given.get(wizard_limits.SOLOS, wizard_limits.NONE_OF))

        def chorus(count):
            """A chorus, with a pre-chorus before it where the answers ask for one before this chorus."""
            return ([wizard_limits.PRE_CHORUS] if before == wizard_limits.BEFORE_EVERY or (before == wizard_limits.BEFORE_FIRST_TWO and count <= 2) else []) + [wizard_limits.CHORUS_KIND]
        form = [wizard_limits.INTRO] if wizard_limits.INTRO in kinds else []
        form += [wizard_limits.VERSE_KIND] * wizard_limits.COUNTS_ONE_OR_TWO.index(given[wizard_limits.VERSES_FIRST]) + [wizard_limits.VERSE_KIND] + chorus(1) + [wizard_limits.VERSE_KIND] + chorus(2)
        # The middle of the song: a first solo, the bridge, the drummer alone, and the solo that leads back to the last choruses.
        form += [wizard_limits.SOLO] if solos == 2 else []
        form += [wizard_limits.BRIDGE] if given.get(wizard_limits.BRIDGE) == wizard_limits.YES else []
        form += [wizard_limits.DRUM_SOLO_KIND] if given.get(wizard_limits.DRUM_SOLO_KIND) == wizard_limits.YES else []
        form += [wizard_limits.SOLO] if solos else []
        form += chorus(3) + [wizard_limits.CHORUS_KIND] * wizard_limits.COUNTS_ONE_OR_TWO.index(given[wizard_limits.LAST_CHORUSES])
        return form + ([wizard_limits.ENDING] if wizard_limits.ENDING in kinds else [])

    def set_form_from_answers(self, answers):
        """Make the form some answers ask for the song's own, in place of its sections, or leave the form as it was where the answers are refused."""
        self.set_own_sections(sections=[{arranger.KIND: kind} for kind in self.form_of_answers(answers)])
        self.clear_answers()

    # The band: who plays, how each plays and how busy each is.

    def _forget_band(self):
        self._band.reset()
        self._sounds_part.reset()
        self._kit.reset()
        self._gauges = {}
        self._melody_settings = {}

    @kept_while(lambda choices: (choices._genre, choices._subgenre, choices._variant))
    def style(self):
        """Return the genre's style template as the subgenre chosen has it, worked out once for a genre, a subgenre and a kind, and
        never changed by a caller."""
        return style_in(style=style_of(self._genre), template=self._subgenre, variant=self._variant)


    def trait_has_sound(self, *, trait, value):
        return arranger.SOUND in values_of(style=self.style(), trait=trait)[value]


    def copied_for_trial(self):
        """A copy of the choices to try something on, which remembers nothing and holds nothing: the answers kept are large,
        and copying them only to throw them away took as long as writing a song."""
        answers, offers, kept = self._answers, self._offers, self._kept
        self._answers, self._offers, self._kept = {}, {}, {}
        try:
            trial = copy.deepcopy(self)
        finally:
            self._answers, self._offers, self._kept = answers, offers, kept
        trial._offers_held = False
        trial._offers_mixed = False
        return trial

    def offered(self, *, key, compute):
        """Return an answer about what a page offers, worked out from these choices and kept as _offered keeps one."""
        return self._offered(key=key, compute=compute)

    def _offered(self, *, key, compute):
        """Return an answer that only says what a page offers, a field shown or the values a field lists, kept until a choice
        changes, or while the offers are held, until they are let go. Nothing a song is made from may be kept here: a held
        answer is that of the choices as they were when the hold began."""
        state = repr(self.to_data())
        if state != self._offers_of and not self._offers_held:
            self._offers = {}
            self._offers_of = state
        if key not in self._offers:
            if state != self._offers_of:
                # Found while held, for choices other than those the rest were found for: letting go forgets them all,
                # even when the choices are by then back as they were.
                self._offers_mixed = True
            self._offers[key] = compute()
        return self._offers[key]

    def hold_offers(self):
        """Keep what the pages offer as it stands, through the changes that follow, until release_offers: a page holds the
        offers while one cell's value is stepped, since each step would else make several songs to find again which fields
        show, and nothing a person is looking at changes for it but the cell stepped."""
        self._offers_held = True

    def release_offers(self):
        """Let the held offers go: the next asking finds them again for the choices as they now stand, and keeps them where
        the choices are again as they were when the offers were found, so that a value stepped away and back costs nothing."""
        self._offers_held = False
        if self._offers_mixed:
            self._offers_of = None
            self._offers_mixed = False

    def holds_offers(self):
        return self._offers_held

    def remembered(self, *, key, compute):
        """Return an answer that is found by making the song, worked out once for the choices as they stand: a page asks the
        same thing at every key, and making a song each time made the keys slow. Everything a song keeps of the choices says
        whether they changed."""
        state = repr(self.to_data())
        if state != self._answers_of:
            self.clear_answers()
            self._answers_of = state
        if key not in self._answers:
            self._answers[key] = compute()
        return self._answers[key]


    # The smart melody style's gauges, shown while the song's tunes are sketched by it.

    def melody_gauges(self):
        """Return the names of the smart melody style's gauges while the song's tunes are sketched by it or by the hooks style, and none otherwise."""
        return list(melody_writer.DEFAULT_GAUGES) if self._melody in wizard_limits.GAUGED_STYLES else []

    def get_melody_gauge(self, name):
        """Return where a gauge stands, from LOWEST_GAUGE to HIGHEST_GAUGE: where it was moved to, else where the genre sets it."""
        if name in self._gauges:
            return self._gauges[name]
        habits = self.style()[arranger.MELODY]
        habits = habits if melody_writer.GRID in habits else habits[self.meter()]
        return habits.get(melody_writer.SMART, {}).get(name, melody_writer.DEFAULT_GAUGES[name])

    def set_melody_gauge(self, *, name, position):
        if name not in melody_writer.DEFAULT_GAUGES or isinstance(position, bool) or not isinstance(position, int) or not melody_writer.LOWEST_GAUGE <= position <= melody_writer.HIGHEST_GAUGE:
            raise ValueError(errors.ERR_WIZARD_GAUGE.format(name=name, low=melody_writer.LOWEST_GAUGE, high=melody_writer.HIGHEST_GAUGE, value=position))
        self._gauges[name] = position

    def melody_habits(self):
        """Return the genre's melody habits for the song's meter."""
        habits = self.style()[arranger.MELODY]
        return habits if melody_writer.GRID in habits else habits[self.meter()]

    def melody_settings(self):
        """Return the names of the settings the song's melody style has of its own, the usual style's while none is chosen."""
        return list(wizard_limits.MELODY_SETTINGS_OF[self._melody]) if self.is_ready() else []

    def melody_setting_range(self, name):
        """Return the lowest and highest a melody setting that is a number may be."""
        return wizard_limits.MELODY_NUMBERS[name]

    def melody_setting_is_switch(self, name):
        return name in wizard_limits.MELODY_SWITCHES

    def get_melody_setting(self, name):
        """Return a melody setting: what it was set to, else what the genre's habits say, else what the style does unasked."""
        if name in self._melody_settings:
            return self._melody_settings[name]
        habits = self.melody_habits()
        if name in wizard_limits.MELODY_SWITCHES:
            return bool(habits.get(name, wizard_limits.MELODY_SWITCHES[name]))
        return {**melody_writer.DEFAULT_EVOLVE, **habits.get(melody_writer.EVOLVE, {})}[name]

    def set_melody_setting(self, *, name, value):
        """Set a setting of the song's melody style, refusing one the style does not have."""
        if name not in self.melody_settings():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY_SETTING.format(value=name))
        self._set_kept_melody_setting(name=name, value=value)

    def _set_kept_melody_setting(self, *, name, value):
        if name in wizard_limits.MELODY_SWITCHES:
            if not isinstance(value, bool):
                raise ValueError(errors.ERR_WIZARD_MELODY_SWITCH.format(name=name, value=value))
        elif name in wizard_limits.MELODY_NUMBERS:
            low, high = wizard_limits.MELODY_NUMBERS[name]
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(errors.ERR_WIZARD_MELODY_NUMBER.format(name=name, low=low, high=high, value=value))
        else:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY_SETTING.format(value=name))
        self._melody_settings[name] = value


    def _song_melody(self):
        """Return what the song says of its melody over the genre's habits: the smart style's gauges where one was moved, and
        the settings set of the style in use; a setting of another style is kept and says nothing."""
        said = {hook_writing.HOOK_WRITING: {hook_writing.BEHAVIOR: self._hook.get_hook_behavior(), hook_writing.GAUGES: {name: self._hook.get_hook_gauge(name) for name in hook_writing.HOOK_GAUGES}},
                hook_writing.BODY_WRITING: {hook_writing.GAUGES: {name: self._hook.get_body_gauge(name) for name in hook_writing.BODY_GAUGES}}}
        if self._melody in wizard_limits.GAUGED_STYLES and self._gauges:
            said[melody_writer.SMART] = {**{name: self.get_melody_gauge(name) for name in melody_writer.DEFAULT_GAUGES}, **self._gauges}
        own = {name: value for name, value in self._melody_settings.items() if name in wizard_limits.MELODY_SETTINGS_OF[self._melody]}
        evolve = {name: value for name, value in own.items() if name in wizard_limits.EVOLVE_SETTINGS}
        if evolve:
            said[melody_writer.EVOLVE] = {**melody_writer.DEFAULT_EVOLVE, **self.melody_habits().get(melody_writer.EVOLVE, {}), **evolve}
        said.update({name: value for name, value in own.items() if name not in wizard_limits.EVOLVE_SETTINGS})
        return said


    def _sections_of_song(self):
        """Return the sections the song describes itself, by name: its own form's, each with its kind and what it changes; and,
        for one guitarist, each section the solo plays in with the chords left out."""
        if self.has_own_form():
            sections = self._song_sections()
            for place, name in enumerate(self.form_sections()):
                plays = self._band.plays_of_one_guitarist(self.section_plays(place))
                if plays is not None:
                    sections[name][arranger.PLAYS] = plays
            return sections
        sections = {}
        for kind in set(self.form_sections()):
            plays = self._band.plays_of_one_guitarist(list(self.style()[arranger.SECTIONS][kind].get(arranger.PLAYS, [])))
            if plays is not None:
                sections[kind] = {arranger.KIND: kind, arranger.PLAYS: plays}
        return sections


    # What a sound is tried with: a run of the song's scale from its root, in the player's octave.

    def root_half_steps(self):
        """Return the song's root as half steps above C, within an octave."""
        return note_values.SEMITONES_ABOVE_C[self._root] % melody_writer.NOTES_IN_OCTAVE

    def scale_half_steps(self):
        """Return the notes of the song's scale as half steps above its root, the major scale's where the melody engines know none for the scale type."""
        return melody_writer.HALF_STEPS.get(self._scale_type, melody_writer.HALF_STEPS[wizard_limits.MAJOR])

    def role_octave(self, role):
        """Return the octave a player plays in."""
        return self._band.role_named(role).get(tune_notation.OCTAVE, wizard_limits.USUAL_OCTAVE)


    def picks_with(self, ways):
        return picked(style=self.style(), song={arranger.TEMPLATE: self._subgenre, arranger.PICKS: ways})


    def share_in_subgenre(self, entry):
        """Return how common a value is in the subgenre chosen."""
        return share_in(style=self.style(), entry=entry, template=self._subgenre)

    # The melody style, which every tune of the song is sketched by.

    def melody_styles(self):
        """Return the melody styles the subgenre's tunes can be sketched by, leaving out any that makes no song of it."""
        if not self.is_ready():
            return []
        return [style for style in wizard_limits.MELODY_STYLES if melody_works(genre=self._genre, subgenre=self._subgenre, variant=self._variant, style=style)
                and not melody_is_usual(genre=self._genre, subgenre=self._subgenre, variant=self._variant, style=style)]

    def genre_melody(self):
        """Return the melody style the genre's own tunes are sketched by, which a song takes while none is chosen."""
        return self.melody_habits().get(melody_writer.ENGINE, melody_writer.STEP_WALK)

    def melody_engine(self):
        """Return the melody style the song's melodies are written by: the one the character chosen writes by, else one chosen by
        name, else the genre's own."""
        return wizard_limits.CHARACTER_ENGINES.get(self.get_melody_character()) or self._melody or self.genre_melody()

    def get_melody(self):
        """Return the melody style chosen, or None while each player's tunes are sketched as the genre says."""
        return self._melody

    def set_melody(self, style):
        if style is not None and style not in self.melody_styles():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY.format(value=style))
        self._melody = style

    def _set_kept_melody(self, *, style):
        self.set_melody(style)


    # The meter and the length, which follow from the subgenre, the tempo and the form.

    def meter(self):
        """Return the meter the subgenre is played in."""
        return str(self.picks().get(arranger.METER, arranger.COMMON_TIME))

    def form_seconds(self, *, form=None):
        """Return how long the song lasts at the tempo chosen, in seconds; or how long a suggested form would, when one is named."""
        if form is None:
            bars = sum(self.section_bars(place) for place in range(len(self.section_entries())))
        else:
            style = self.style()
            kinds = next((form_[arranger.SECTIONS] for form_ in self._forms() if form_[arranger.NAME] == form), [])
            bars = sum(wizard_limits.HELD_BARS if style[arranger.SECTIONS][kind].get(arranger.HELD) else style[arranger.SECTIONS][kind][arranger.BARS] for kind in kinds)
        return float(bars * bar_length(self.meter()) * wizard_limits.QUARTERS_IN_WHOLE * wizard_limits.SECONDS_IN_MINUTE / self._tempo)

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
            raise ValueError(errors.ERR_WIZARD_SEED.format(value=seed))
        self._seed = seed

    def draw_seed(self, *, dice=None):
        """Draw a new seed at random, for a song from scratch or a new take."""
        self._seed = (dice or random.Random()).randint(wizard_limits.FIRST_SEED, wizard_limits.LAST_SEED)

    # The song.

    # The progression left to chance: a song whose progression nobody chose takes one of the subgenre's by the
    # seed, so that two runs differ in more than their tunes.

    def progression_trait(self):
        return self._band.song_trait(wizard_limits.PROGRESSION_TRAITS)

    def has_any_progression(self):
        """Return whether the progression is left to chance: no progression was chosen."""
        return self.progression_trait() is not None and self.progression_trait() not in self._band.get_ways()

    def set_any_progression(self):
        """Leave the progression to chance again."""
        self._band.forget_way(self.progression_trait())

    def progression_chords(self, progression):
        """Return a progression's chords for each kind of section the song's form plays, in the form's order, each chord its
        degree and its sharp or flat as a set file writes one; a section played as one held chord is left out. Nothing for a
        progression written another way than as degrees."""
        entry = values_of(style=self.style(), trait=self.progression_trait())[progression]
        if arranger.PATTERN not in entry:
            return []
        chords = {}
        for place, kind in enumerate(self.section_kinds_in_form()):
            if kind not in chords and not self.section_is_held(place):
                written = entry.get(arranger.BY_SECTION, {}).get(kind) or entry[arranger.PATTERN]
                chords[kind] = [(chord_of(chord)[tune_notation.DEGREE], arranger.ACCIDENTAL_MARKS.get(chord_of(chord).get(tune_notation.ACCIDENTAL))) for chord in written]
        return list(chords.items())

    def progression_scale_type(self, progression):
        """Return the scale type a progression's chords were written for, major where the genre does not say."""
        return values_of(style=self.style(), trait=self.progression_trait())[progression].get(arranger.SCALE_TYPE, wizard_limits.MAJOR)

    def progression_degrees(self, progression):
        """Return the chords a progression is known by, its first written, each a degree and its sharp or flat; or nothing."""
        entry = values_of(style=self.style(), trait=self.progression_trait())[progression]
        return [(chord_of(chord)[tune_notation.DEGREE], arranger.ACCIDENTAL_MARKS.get(chord_of(chord).get(tune_notation.ACCIDENTAL))) for chord in entry.get(arranger.PATTERN, [])]

    def section_kinds_in_form(self):
        """Return the kind of each section of the song's form, in order."""
        return [self.section_kind(place) for place in range(len(self.section_labels()))]

    def progressions_by_chance(self):
        """Return the progressions the song may take, in the order the seed draws them: a commoner one likelier to come first, the
        subgenre's usual one counted twice. With no seed, or a progression chosen, there is nothing to draw."""
        trait = self.progression_trait()
        if not self.has_any_progression() or self._seed is None:
            return []
        usual = self.picks()[trait]
        entries = values_of(style=self.style(), trait=trait)
        left = self._band.song_ways(trait)
        # A progression written for the other of major and minor is left to be chosen by hand: its chords were not meant for the song's scale.
        suited = [way for way in left if entries[way].get(arranger.SCALE_TYPE, wizard_limits.MAJOR) == self._scale_type]
        left = suited or left
        # A progression the subgenre's family never uses is left to be chosen by hand too.
        left = [way for way in left if self.share_in_subgenre(entries[way])] or left
        dice = random.Random(wizard_limits.PROGRESSION_SEED.format(self._seed))
        drawn = []
        while left:
            weights = [self.share_in_subgenre(entries[way]) * (wizard_limits.USUAL_COUNTS if way == usual else 1) or 1 for way in left]
            drawn.append(dice.choices(left, weights=weights)[0])
            left.remove(drawn[-1])
        return drawn

    def song_picks(self, name, *, progression=None):
        """Return the choices as a song's picks, which the arranger makes a song of: with a progression left to chance, the one
        given, or the first the seed draws."""
        drawn = [progression] if progression else self.progressions_by_chance()[:1]
        if drawn:
            return {**self._song_picks(name), arranger.PICKS: {**self._band.get_ways(), **self._kit.trait_picks(), self.progression_trait(): drawn[0]}}
        return self._song_picks(name)

    def _song_picks(self, name):
        picks = data_laid_over(under=self._picks_chosen(name), over=self._extras_with_sections())
        # The riffs are kept as the panels show them; the arranger is handed each riff with who plays it where. A song with no
        # riff of its own asks for none, where the arranger would else take the genre's.
        for kept in (wizard_limits.RIFF_BOOK, wizard_limits.RIFFS_KNOWN, wizard_limits.RIFFS_PLAYED, wizard_limits.MELODY_CHOSEN, wizard_limits.HOOKS_CHOSEN):
            picks.pop(kept, None)
        picks.update(self._hook.hooks_of_song())
        picks.setdefault(riffs_values.RIFF, {})
        riffs = [*picks.get(arranger.MORE_RIFFS, []), *self._riffs_part.riffs_arranged()]
        if riffs:
            picks[arranger.MORE_RIFFS] = riffs
        picks.update(self._melody_picks(picks))
        # The takes are kept as numbers; the arranger is handed the tune each number draws.
        picks.pop(wizard_limits.TUNE_TAKES, None)
        picks.pop(wizard_limits.SOLO_TAKES, None)
        for number, players in self._solos.taken_solos().items():
            picks.setdefault(arranger.OWN_SOLOS, {}).setdefault(number, {}).update(players)
        taken = self._tunes.taken_tunes()
        delivery = self.tune_phrasing()
        picks.pop(arranger.TUNE_PHRASING, None)
        if delivery is not None:
            picks[arranger.TUNE_PHRASING] = delivery
        return {**picks, arranger.TAKEN_TUNES: taken} if taken else picks

    def _extras_with_sections(self):
        """The song's extras, the plan in them holding what each section of the form was given of its own, by place."""
        if not self.has_song_plan():
            return self._extras
        plan = self._extras[song_plan.PLAN_OF_SONG] if isinstance(self._extras.get(song_plan.PLAN_OF_SONG), dict) else {}
        if not (any(entry.get(wizard_limits.OWN_OF_SECTION) for entry in self.section_entries()) or self._intro_hook_kept() is not None):
            # A song planned because its genre plans every song asks for the plan as one that was switched on does.
            return {**self._extras, song_plan.PLAN_OF_SONG: plan}
        given = list(plan.get(song_plan.BY_PLACE) or [])
        by_place = []
        for place, entry in enumerate(self.section_entries()):
            own = dict(entry.get(wizard_limits.OWN_OF_SECTION) or {})
            if joins_values.LEAVES in own:
                own[joins_values.LEAVES] = dict(wizard_limits.LEAVES_AS_JOIN[own[joins_values.LEAVES]])
            if wizard_limits.SHAPE_OF_SECTION in own:
                # A shape the kind no longer has, as after the section was made another kind, is left as the kind's own.
                shape = self.style()[arranger.SECTIONS][entry[arranger.KIND]].get(wizard_limits.SHAPES, {}).get(own.pop(wizard_limits.SHAPE_OF_SECTION))
                if shape is not None:
                    own[wizard_limits.PLAN] = copy.deepcopy(shape)
            own.pop(wizard_limits.INTRO_HOOK, None)
            own.update(self._intro_hook_at(place))
            own = self._with_fade_way(place=place, own=own)
            if own.get(wizard_limits.LINES_OF_SECTION):
                own[wizard_limits.PLAN] = self._plan_with_lines(kind=entry[arranger.KIND], plan=own.get(wizard_limits.PLAN), lines=own[wizard_limits.LINES_OF_SECTION])
            own.pop(wizard_limits.LINES_OF_SECTION, None)
            by_place.append({**((given[place] or {}) if place < len(given) else {}), **own})
        return {**self._extras, song_plan.PLAN_OF_SONG: {**plan, song_plan.BY_PLACE: by_place}}

    # The hook said in the intro, before anybody sings it, by the player who answers the tune or the tune's own player.

    def intro_hook_players(self):
        """Return the players who can say the hook in the intro: the tune's player and the player who answers the tune, where the song has a hook, a plan and an intro the band plays."""
        if not self.has_song_plan() or not self._hook.can_have_hook() or not self._hook.has_hook() or not self.counts_in_four() or not self._intro_places():
            return []
        return [role for role in (self._band.answered_by(), self._band.tune_player()) if role is not None]

    def _intro_places(self):
        return [place for place, entry in enumerate(self.section_entries()) if entry[arranger.KIND] == wizard_limits.INTRO and not self.section_is_held(place)]

    def get_intro_hook(self):
        """Return who says the hook in the intro, or None for nobody."""
        role = self._intro_hook_kept()
        return role if role in self.intro_hook_players() else None

    def _intro_hook_kept(self):
        """Who was chosen to say the hook in the intro, while that player is still one who could: asked while the song is made, so it makes no song to answer."""
        role = self._extras.get(song_plan.PLAN_OF_SONG, {}).get(wizard_limits.INTRO_HOOK) if isinstance(self._extras.get(song_plan.PLAN_OF_SONG), dict) else None
        able = role is not None and self._hook.can_have_hook() and self._hook.has_hook() and role in (self._band.answered_by(), self._band.tune_player())
        return role if able else None

    def set_intro_hook(self, role):
        if role is not None and role not in self.intro_hook_players():
            raise ValueError(errors.ERR_WIZARD_INTRO_HOOK.format(value=role))
        self._plan().pop(wizard_limits.INTRO_HOOK, None)
        if role is not None:
            self._plan()[wizard_limits.INTRO_HOOK] = role
        self.clear_answers()

    # The intro's melody: the hook as the chosen player says it, until the notes are edited by hand.

    def intro_parts(self):
        """Return the place in the form of each part of the intro the band plays, in order: an intro may be several sections,
        a player joining with each."""
        return self._intro_places() if self.is_ready() else []

    def add_intro_part(self):
        """Put another part at the end of the intro, played by everybody the intro has, and return its place in the form."""
        parts = self._intro_places()
        place = parts[-1] + 1 if parts else 0
        self.add_section(place=place, kind=wizard_limits.INTRO)
        self.clear_answers()
        return place

    def remove_intro_part(self, place):
        """Take a part out of the intro. The notes written by hand for the part go with it, and those of the parts after it stay theirs."""
        if place not in self._intro_places():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION.format(value=place))
        number = self._intro_number_at(place)
        self.remove_section(place)
        own = self._extras.get(arranger.OWN_INTROS, {})
        moved = {(kept if kept < number else kept - 1): players for kept, players in own.items() if kept != number}
        self._extras.pop(arranger.OWN_INTROS, None)
        if moved:
            self._extras[arranger.OWN_INTROS] = moved
        self.clear_answers()

    def intro_melody_player(self, place):
        """Return who says the hook in a part of the intro, or None for nobody: the part's own player, or where the part says
        nothing, the player the song has say the hook in its intro."""
        if place not in self._intro_places():
            return None
        own = self.section_entry(place).get(wizard_limits.OWN_OF_SECTION, {}).get(wizard_limits.INTRO_HOOK)
        if own == arranger.NOBODY:
            return None
        offered = self.intro_hook_players()
        return own if own in offered else self.get_intro_hook()

    def set_intro_melody(self, *, place, role):
        """Have a player say the hook in one part of the intro, or nobody with None. The other parts stay as they are."""
        if place not in self._intro_places() or (role is not None and role not in self.intro_hook_players()):
            raise ValueError(errors.ERR_WIZARD_INTRO_HOOK.format(value=role))
        self._set_own(place=place, field=wizard_limits.INTRO_HOOK, value=arranger.NOBODY if role is None else role)

    def intro_melody_place(self):
        """Return the place in the form of the first part of the intro somebody says the hook in, or None where nobody does."""
        return next((place for place in self._intro_places() if self.intro_melody_player(place) is not None), None)

    def _intro_number_at(self, place):
        """A part's number among the form's sections of the kind intro, counted from 1, which is what its own notes are kept under."""
        return len([other for other in range(place + 1) if self.section_kind(other) == wizard_limits.INTRO])

    def _melody_place_or(self, place):
        return self.intro_melody_place() if place is None else place

    def intro_is_own(self, *, place=None):
        """Return whether the melody of a part of the intro, the first with a melody where none is named, was written by hand
        for the player who now plays it."""
        place = self._melody_place_or(place)
        role = None if place is None else self.intro_melody_player(place)
        return role is not None and (role in self._extras.get(arranger.OWN_INTROS, {}).get(self._intro_number_at(place), {}) or role in self._extras.get(arranger.OWN_INTRO, {}))

    def intro_pattern_name(self, *, place=None):
        """Return the name of the pattern that holds the melody of a part of the intro in the set the choices make, or None where the set has none."""
        return self._intro_in_made(self._melody_place_or(place))[0]

    def intro_pattern(self, *, place=None):
        """Return the melody of a part of the intro as a pattern's data, the person's own or the hook as the choices write it, or None where nobody plays one."""
        return copy.deepcopy(self._intro_in_made(self._melody_place_or(place))[1])

    def _intro_in_made(self, place):
        return self.remembered(key=(wizard_limits.INTRO_MADE_ANSWER, place), compute=lambda: self._found_intro_in_made(place))

    def _found_intro_in_made(self, place):
        role = None if place is None else self.intro_melody_player(place)
        if role is None:
            return None, None
        setlist, name = self.written_for_trial()
        scenes = setlist.get_song(name).get_scenes()
        slot = scenes[place].get_clip_slot(role) if place < len(scenes) and scenes[place].has_clip_slot(role) else None
        if slot is None:
            return None, None
        return slot.get_pattern_name(), setlist.get_pattern(slot.get_pattern_name()).to_data()

    def set_intro_pattern(self, *, pattern, place=None):
        """Keep a pattern's data as the own melody of a part of the intro, the first with a melody where none is named, for the
        player who plays it there, or forget the person's own with None, so that the player says the hook again. A part nobody
        plays a melody in, and a pattern the song cannot be made with, are refused and nothing changes."""
        place = self._melody_place_or(place)
        role = None if place is None else self.intro_melody_player(place)
        if role is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=wizard_limits.INTRO))
        number = self._intro_number_at(place)
        before = (copy.deepcopy(self._extras.get(arranger.OWN_INTROS)), copy.deepcopy(self._extras.get(arranger.OWN_INTRO)))
        own = self._extras.setdefault(arranger.OWN_INTROS, {})
        if pattern is None:
            own.get(number, {}).pop(role, None)
            # Notes kept for every part of the intro at once, as an older song kept them, are given back with the part's.
            self._extras.get(arranger.OWN_INTRO, {}).pop(role, None)
        else:
            own.setdefault(number, {})[role] = copy.deepcopy(pattern)
        for empty in [key for key, players in own.items() if not players]:
            del own[empty]
        for kept in (arranger.OWN_INTROS, arranger.OWN_INTRO):
            if not self._extras.get(kept):
                self._extras.pop(kept, None)
        self.clear_answers()
        try:
            self.written_for_trial()
        except Exception as problem:
            for kept, was in zip((arranger.OWN_INTROS, arranger.OWN_INTRO), before):
                self._extras.pop(kept, None)
                if was is not None:
                    self._extras[kept] = was
            self.clear_answers()
            raise ValueError(errors.ERR_WIZARD_TUNE_PATTERN.format(problem=problem)) from problem


    def _intro_hook_at(self, place):
        """What an intro is given so that somebody says the hook in it: a line of the hook for each two bars, as answers where the answering player says them, and the player among those who play."""
        if place not in self._intro_places():
            return {}
        own = self.section_entry(place).get(wizard_limits.OWN_OF_SECTION, {}).get(wizard_limits.INTRO_HOOK)
        able = [role for role in (self._band.answered_by(), self._band.tune_player()) if role is not None] if self._hook.can_have_hook() and self._hook.has_hook() else []
        role = None if own == arranger.NOBODY else own if own in able else self._intro_hook_kept()
        if role is None:
            return {}
        answers = {melody_writer.ANSWER: True} if role == self._band.answered_by() else {}
        lines = [{melody_writer.LINE: melody_writer.HOOK, melody_writer.HOOK: True, wizard_limits.HIGHER: True, **answers, **({wizard_limits.VARIED: True} if count % 2 else {})} for count in range(max(self.section_bars(place) // wizard_limits.BARS_IN_A_LINE, 1))]
        return {wizard_limits.PLAN: lines, arranger.PLAYS: list(dict.fromkeys([*self.section_plays(place), role]))}

    # What a section of a planned song is given of its own, over the plan and the song: each is None until given, and None gives it back.

    def section_own_fields(self, place):
        """Return the fields a section can be given of its own, in the order shown: none without a plan, and no join for the last section or a held one."""
        if not self.is_ready() or self.section_is_held(place):
            return []
        fade = self.fade_fields(place)
        if not self.has_song_plan():
            return [*wizard_limits.OWN_WITHOUT_PLAN, *fade]
        joins = self.remembered(key=wizard_limits.JOINS_ANSWER, compute=lambda: self.made_song_plan().joins())
        leaves = [joins_values.LEAVES, song_plan.SETUP] if place < len(joins) and joins[place] is not None else []
        shape = [wizard_limits.SHAPE_OF_SECTION] if self.section_shapes(place) else []
        rises = [song_plan.RISES] if place < len(joins) and joins[place] is not None else []
        return [song_plan.ENERGY, *shape, *rises, *fade, *leaves, arranger.CHORDS, song_plan.TEMPO_OF_PLACE, song_plan.TEMPO_END_OF_PLACE, song_plan.ROOT_OF_PLACE, song_plan.TYPE_OF_PLACE]

    def fade_way(self, place):
        """Return how a section can fade: in, for a section that opens the song before its first tune; out, for one that closes
        the song after its last; and None for any other and for a held chord."""
        if self.section_is_held(place):
            return None
        if place < self._head():
            return wizard_limits.FADE_IN
        return wizard_limits.FADE_OUT if place >= len(self.section_entries()) - self._tail() else None

    def fade_fields(self, place):
        """Return the fields of a section's fade, in the order shown: the switch where the section can fade, and while it is on,
        the level the fade starts from or ends at, and the bars the fade takes, the first of the section for a fade in and the last for a fade out."""
        way = self.fade_way(place)
        if way is None:
            return []
        if not self.section_entry(place).get(wizard_limits.OWN_OF_SECTION, {}).get(song_plan.FADES):
            return [song_plan.FADES]
        return [song_plan.FADES, song_plan.FADE_LEVEL, song_plan.FADE_OVER]

    def _with_fade_way(self, *, place, own):
        """What a section says of its own, with whether its fade is a fade in and the bars the fade takes, never more than the section has."""
        if not own.get(song_plan.FADES):
            return {field: value for field, value in own.items() if field not in (song_plan.FADES, song_plan.FADE_LEVEL, song_plan.FADE_OVER)}
        if self.fade_way(place) is None:
            # A section that fades was moved to where none does.
            return {field: value for field, value in own.items() if field not in (song_plan.FADES, song_plan.FADE_LEVEL, song_plan.FADE_OVER)}
        return {**own, **({song_plan.FADES_IN: True} if self.fade_way(place) == wizard_limits.FADE_IN else {}), song_plan.FADE_OVER: min(own.get(song_plan.FADE_OVER, self.section_bars(place)), self.section_bars(place))}

    def section_shapes(self, place):
        """Return the shapes a section's lines may take besides its kind's own, by name."""
        return list(self._usual(place).get(wizard_limits.SHAPES, {}))

    def section_own(self, *, place, field):
        """Return what a section was given of its own for a field, or None."""
        return copy.deepcopy(self.section_entry(place).get(wizard_limits.OWN_OF_SECTION, {}).get(field))

    def section_from_plan(self, *, place, field):
        """Return what a section takes for a field where it is given nothing: the plan's Energy and join, the progression's chords, the song's tempo and key."""
        if field == arranger.CHORDS:
            return chords_as_text(self.chords_at(place))
        if field in (song_plan.TEMPO_OF_PLACE, song_plan.TEMPO_END_OF_PLACE):
            return self.section_own(place=place, field=song_plan.TEMPO_OF_PLACE) or self._tempo
        if field in (song_plan.ROOT_OF_PLACE, song_plan.TYPE_OF_PLACE):
            return self._root if field == song_plan.ROOT_OF_PLACE else self._scale_type
        if field == song_plan.FADES:
            return False
        if field == song_plan.FADE_LEVEL:
            return song_plan.FADED
        if field == song_plan.FADE_OVER:
            return self.section_bars(place)
        self._plan()
        if field == song_plan.ENERGY:
            return self.energies()[place]
        if field == joins_values.LEAVES:
            join = self.remembered(key=wizard_limits.JOINS_ANSWER, compute=lambda: self.made_song_plan().joins())[place] or {}
            if join.get(joins_values.TAIL):
                return join[joins_values.TAIL]
            # A fill is said by its size, as it is chosen.
            fills = self.style()[song_plan.PLAN_OF_SONG].get(song_plan.FILL_SIZES, {})
            return next((way for way, given in wizard_limits.LEAVES_AS_JOIN.items() if song_plan.FILL_SIZE in given and fills.get(given[song_plan.FILL_SIZE]) == join.get(joins_values.FILL_OF_JOIN)), wizard_limits.LEAVES_NOTHING)
        if field == song_plan.SETUP:
            return wizard_limits.SETUP_USUAL
        if field == wizard_limits.SHAPE_OF_SECTION:
            # A solo after the song's first is a stage, which takes the next of its kind's shapes.
            return self.remembered(key=wizard_limits.STAGES_ANSWER, compute=lambda: self.made_song_plan().shapes())[place] or wizard_limits.SHAPE_USUAL
        if field == song_plan.RISES:
            return self.section_entry(place)[arranger.KIND] in self.style()[song_plan.PLAN_OF_SONG].get(song_plan.RISING, [])
        if field == arranger.CHORDS:
            return chords_as_text(self.made_song_plan().chords_at(place))
        if field in (song_plan.TEMPO_OF_PLACE, song_plan.TEMPO_END_OF_PLACE):
            return self.section_own(place=place, field=song_plan.TEMPO_OF_PLACE) or self._tempo
        return self._root if field == song_plan.ROOT_OF_PLACE else self._scale_type

    def chords_at(self, place):
        """The chords a section plays where it is given none: its kind's own, the progression's for the kind, or the progression's."""
        style = self.style()
        picks = picked(style=style, song=self.song_picks(wizard_limits.PREVIEW_NAME))
        entry = values_of(style=style, trait=self.progression_trait())[picks[self.progression_trait()]]
        kind = self.section_entry(place)[arranger.KIND]
        return [chord_of(chord) for chord in style[arranger.SECTIONS][kind].get(arranger.CHORDS) or entry.get(arranger.BY_SECTION, {}).get(kind) or entry[arranger.PATTERN]]

    def _checked_own(self, *, field, value):
        if field == song_plan.ENERGY and not isinstance(value, bool) and isinstance(value, int) and song_plan.LOWEST_ENERGY <= value <= song_plan.HIGHEST_ENERGY:
            return value
        if field == joins_values.LEAVES and value in wizard_limits.LEAVES_AS_JOIN:
            return value
        if field == song_plan.SETUP and value == song_plan.NOT_AT_ALL:
            return value
        if field in (song_plan.RISES, song_plan.FADES) and isinstance(value, bool):
            return value
        if field == wizard_limits.INTRO_HOOK and isinstance(value, str):
            return value
        if field == song_plan.FADE_LEVEL and not isinstance(value, bool) and isinstance(value, int) and song_plan.FADED <= value <= song_plan.LOUDEST_FADE_LEVEL:
            return value
        if field == song_plan.FADE_OVER and not isinstance(value, bool) and isinstance(value, int) and value >= 1:
            return value
        if field == wizard_limits.LINES_OF_SECTION and isinstance(value, dict):
            return {int(count): self._checked_line_own(given) for count, given in value.items() if given}
        if field == wizard_limits.SHAPE_OF_SECTION and isinstance(value, str):
            return value
        if field == arranger.CHORDS:
            return chords_from_text(chords_as_text(value) if isinstance(value, list) else value)
        if field in (song_plan.TEMPO_OF_PLACE, song_plan.TEMPO_END_OF_PLACE) and not isinstance(value, bool) and isinstance(value, int) and limits.MIN_TEMPO <= value <= limits.MAX_TEMPO:
            return value
        if field == song_plan.ROOT_OF_PLACE and value in note_values.ROOT_NAMES:
            return value
        if field == song_plan.TYPE_OF_PLACE and value in wizard_limits.SCALE_TYPES:
            return value
        raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))

    def _checked_line_own(self, given):
        """What one line of a section was given of its own, checked: notes written by hand, a breath in eighths and whether a note comes early."""
        if not isinstance(given, dict) or not set(given) <= {melody_writer.LINE_NOTES, phrasing.LINE_BREATH, phrasing.LINE_EARLY}:
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=wizard_limits.LINES_OF_SECTION, value=given))
        checked = {}
        if melody_writer.LINE_NOTES in given:
            checked[melody_writer.LINE_NOTES] = self.checked_line(line=given[melody_writer.LINE_NOTES], steps=line_edits.steps_of(given[melody_writer.LINE_NOTES]) if isinstance(given[melody_writer.LINE_NOTES], list) and all(isinstance(note, dict) for note in given[melody_writer.LINE_NOTES]) else 0)
        if phrasing.LINE_BREATH in given:
            if isinstance(given[phrasing.LINE_BREATH], bool) or not isinstance(given[phrasing.LINE_BREATH], int) or not phrasing.NO_BREATH <= given[phrasing.LINE_BREATH] <= phrasing.LONGEST_BREATH:
                raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=phrasing.LINE_BREATH, value=given[phrasing.LINE_BREATH]))
            checked[phrasing.LINE_BREATH] = given[phrasing.LINE_BREATH]
        if phrasing.LINE_EARLY in given:
            if not isinstance(given[phrasing.LINE_EARLY], bool):
                raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=phrasing.LINE_EARLY, value=given[phrasing.LINE_EARLY]))
            checked[phrasing.LINE_EARLY] = given[phrasing.LINE_EARLY]
        return checked

    # A section's lines, one by one: who plays each, its notes as the song has them, and what the line is given of its own.

    def _made_form(self):
        """The song arranged as the choices stand: its parts and its form, kept until a choice changes."""
        return self.remembered(key=wizard_limits.ARRANGED_ANSWER, compute=lambda: arranged(style=self.style(), song=self.song_picks(wizard_limits.PREVIEW_NAME)))

    def _plan_at(self, place):
        """The plan of lines a section is played by, with what its lines were given."""
        if self.has_song_plan():
            by_place = self._extras_with_sections().get(song_plan.PLAN_OF_SONG, {}).get(song_plan.BY_PLACE) or []
            given = by_place[place].get(wizard_limits.PLAN) if place < len(by_place) and by_place[place] else None
            if given is not None:
                return given
        return self._plan_with_lines(kind=self.section_entry(place)[arranger.KIND], plan=None, lines=self.section_entry(place).get(wizard_limits.OWN_OF_SECTION, {}).get(wizard_limits.LINES_OF_SECTION, {}))

    def tune_steps_in_bar(self):
        """Return how many steps a bar of the tune has."""
        return self.melody_habits()[melody_writer.GRID]

    def section_lines(self, place):
        """Return a section's lines in order, each a mapping: who plays the line, its notes (line_edits.py) or None where nobody of the band plays the line,
        whether its breath and early note can be set (a new idea of the tune in a song in four, not the hook), and what the line was given of its own."""
        self.section_entry(place)
        return self.remembered(key=(wizard_limits.LINES_ANSWER, place), compute=lambda: self._section_lines(place))

    def _section_lines(self, place):
        made = self._made_form()
        scene = made[arranger.FORM][place]
        own = self.section_entry(place).get(wizard_limits.OWN_OF_SECTION, {}).get(wizard_limits.LINES_OF_SECTION, {})
        seen = set()
        lines = []
        for count, entry in enumerate(self._plan_at(place)):
            player = self._band.answered_by() if entry.get(melody_writer.ANSWER) else self._band.tune_player()
            part = made[arranger.PARTS].get((scene.get(wizard_limits.PLAY_OF_SCENE, {}).get(player) or {}).get(wizard_limits.PART))
            notes = copy.deepcopy(part[tune_notation.LINES][count]) if part is not None and tune_notation.LINES in part and count < len(part[tune_notation.LINES]) else None
            letter = (bool(entry.get(melody_writer.ANSWER)), entry.get(melody_writer.LINE, str(count)))
            new = letter not in seen
            seen.add(letter)
            breathes = new and notes is not None and not entry.get(melody_writer.HOOK) and self.counts_in_four() and melody_writer.LINE_NOTES not in (own.get(count) or {})
            lines.append({wizard_limits.LINE_PLAYER: player, melody_writer.LINE_NOTES: notes, wizard_limits.LINE_BREATHES: breathes, wizard_limits.LINE_IS_HOOK: bool(entry.get(melody_writer.HOOK)), wizard_limits.LINE_OWN: copy.deepcopy(own.get(count) or {})})
        return lines

    def set_section_line(self, *, place, line, field, value):
        """Give one line of a section its own notes, breath or early note, or give the field back with None. What the song cannot then be made with is refused."""
        lines = self.section_lines(place)
        if isinstance(line, bool) or not isinstance(line, int) or not 0 <= line < len(lines) or field not in (melody_writer.LINE_NOTES, phrasing.LINE_BREATH, phrasing.LINE_EARLY):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=line))
        if field == melody_writer.LINE_NOTES and value is not None and (lines[line][melody_writer.LINE_NOTES] is None or not isinstance(value, list) or line_edits.steps_of(self.checked_line(line=value, steps=line_edits.steps_of(lines[line][melody_writer.LINE_NOTES]))) == 0):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))
        own = {count: dict(given) for count, given in (self.section_entry(place).get(wizard_limits.OWN_OF_SECTION, {}).get(wizard_limits.LINES_OF_SECTION) or {}).items()}
        given = own.setdefault(line, {})
        given.pop(field, None)
        if value is not None:
            given[field] = value
        own = {count: given for count, given in own.items() if given}
        self._set_own(place=place, field=wizard_limits.LINES_OF_SECTION, value=own or None)

    def set_section_own(self, *, place, field, value):
        """Give a section something of its own, or give the field back with None. What the song cannot then be made with is refused, and nothing changes."""
        if field not in (*wizard_limits.OWN_WITHOUT_PLAN, *wizard_limits.FADE_OWN):
            self._plan()
        self._set_own(place=place, field=field, value=value)

    def _set_own(self, *, place, field, value):
        self.section_entry(place)
        checked = None if value is None else self._checked_own(field=field, value=value)
        if field == wizard_limits.SHAPE_OF_SECTION and checked is not None and checked not in self.section_shapes(place):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))
        if field in (song_plan.FADES, song_plan.FADE_LEVEL, song_plan.FADE_OVER) and checked is not None and (field not in (song_plan.FADES, *self.fade_fields(place)) or self.fade_way(place) is None or (field == song_plan.FADE_OVER and checked > self.section_bars(place))):
            # Only a section that opens or closes the song fades, and a fade's level and bars are a fade's that is switched on.
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))
        before = copy.deepcopy(self._sections)
        entry = self.own_section_entries()[place]
        own = entry.setdefault(wizard_limits.OWN_OF_SECTION, {})
        own.pop(field, None)
        if checked is not None:
            own[field] = checked
        if field == song_plan.FADES and not checked:
            # A fade switched off keeps nothing of how it faded.
            own.pop(song_plan.FADES, None)
            own.pop(song_plan.FADE_LEVEL, None)
            own.pop(song_plan.FADE_OVER, None)
        if not own:
            del entry[wizard_limits.OWN_OF_SECTION]
        self.clear_answers()
        try:
            self.written_setlist(name=wizard_limits.PREVIEW_NAME, version=version_values.VERSION)
        except (ValueError, KeyError, IndexError, SongFileError) as problem:
            self._sections = before
            self.clear_answers()
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN_UNMADE.format(field=field, value=value, problem=problem)) from None

    def _picks_chosen(self, name):
        return {arranger.NAME: name, arranger.TITLE: name, arranger.STYLE: self._genre, arranger.TEMPLATE: self._subgenre, arranger.VARIANT: self._variant, arranger.KEY: {arranger.ROOT: self._root, arranger.TYPE: self._scale_type}, arranger.TEMPO: self._tempo, arranger.FORM: self.form_sections() if self.has_own_form() else self.get_form(), arranger.SEED: self._seed,
                arranger.PICKS: {**self._band.get_ways(), **self._kit.trait_picks()}, arranger.PLAYERS: self._band.players_of_song(), arranger.WITHOUT: self._band.without_of_song(), **self._band.beside_of_song(),
                **({arranger.SECTIONS: self._sections_of_song()} if self._sections_of_song() else {}),
                **({arranger.MELODY_ENGINE: self._melody} if self._melody is not None else {}),
                **self._hook.song_settings(),
                **({arranger.MELODY: self._song_melody()} if self._song_melody() else {}),
                **({arranger.ROLE_HABITS: self._band.role_habits_of_song()} if self._band.role_habits_of_song() else {}),
                **({arranger.ROLE_SOUNDS: self._sounds_part.sounds_of_song()} if self._sounds_part.sounds_of_song() else {}),
                **self._kit.song_settings()}

    def set_song_extras(self, extras):
        """Lay a song file's own picks over what the choices make: the song's plan, and whatever a section is given."""
        if not isinstance(extras, dict):
            raise ValueError(errors.ERR_WIZARD_EXTRAS.format(value=extras))
        self._extras = copy.deepcopy(extras)
        self._riffs_part.read(self._extras)
        for kept in wizard_limits.RIFFS_KEPT:
            self._extras.pop(kept, None)
        self.clear_answers()

    # The song plan, which a song made on the wizard's page asks for with a switch, and its settings.

    def has_song_plan(self):
        """Return whether the song is planned section by section (song_plan.py): a genre that says how its songs are planned plans every
        song until the plan is switched off."""
        kept = self._extras.get(song_plan.PLAN_OF_SONG)
        return self.can_have_song_plan() if kept is None else kept is not False

    def can_have_song_plan(self):
        """Return whether the genre says how a song of its own is planned."""
        return self.is_ready() and song_plan.PLAN_OF_SONG in self.style()

    def set_song_plan(self, on):
        if not isinstance(on, bool):
            raise ValueError(errors.ERR_WIZARD_SWITCH.format(value=on))
        if on and not self.can_have_song_plan():
            raise ValueError(errors.ERR_WIZARD_GENRE_HAS_NO_PLAN)
        if on and not isinstance(self._extras.get(song_plan.PLAN_OF_SONG), dict):
            self._extras[song_plan.PLAN_OF_SONG] = {}
        if not on:
            self._extras[song_plan.PLAN_OF_SONG] = False
            # What the plan alone reads of the melody goes with the plan; a hook written by hand stays.
            kept = {field: value for field, value in self._extras.pop(arranger.MELODY, {}).items() if field == melody_writer.HOOK_NOTES}
            if kept:
                self._extras[arranger.MELODY] = kept
        self.clear_answers()

    def _plan(self):
        if not self.has_song_plan():
            raise ValueError(errors.ERR_WIZARD_NO_SONG_PLAN)
        if not isinstance(self._extras.get(song_plan.PLAN_OF_SONG), dict):
            self._extras[song_plan.PLAN_OF_SONG] = {}
        return self._extras[song_plan.PLAN_OF_SONG]

    def get_contrast(self):
        return self._plan().get(song_plan.CONTRAST, song_plan.USUAL_CONTRAST)

    def set_contrast(self, contrast):
        if isinstance(contrast, bool) or not isinstance(contrast, int) or not song_plan.LOWEST_ENERGY <= contrast <= song_plan.HIGHEST_ENERGY:
            raise ValueError(errors.ERR_WIZARD_CONTRAST.format(low=song_plan.LOWEST_ENERGY, high=song_plan.HIGHEST_ENERGY, value=contrast))
        self._plan()[song_plan.CONTRAST] = contrast
        self.clear_answers()

    # A player, as a person in the band: how strongly the player answers to Energy, where the player comes in and where the player lays out.

    def reacts(self, role):
        """Return whether a player answers to Energy more or less than the band: a player of a planned song whose playing the plan holds back or lets go,
        which is found by making the song with the player even and dramatic, and kept until a choice changes."""
        if not (self.has_song_plan() and self.player(role).is_in() and arranger.PLAYER in self._band.role_named(role)):
            return False
        return self.offered(key=(wizard_limits.REACTS_ANSWER, self._band.role_named(role)[arranger.PLAYER]), compute=lambda: self._reacts_is_heard(role))

    def _reacts_is_heard(self, role):
        made = []
        for reacts in (song_plan.LOWEST_ENERGY, song_plan.HIGHEST_ENERGY):
            trial = self.copied_for_trial()
            trial._plan()[song_plan.REACTS] = {**(trial._plan().get(song_plan.REACTS) or {}), self._band.role_named(role)[arranger.PLAYER]: reacts}
            made.append(trial.patterns_of_song())
        return made[0] != made[1]

    def get_reacts(self, role):
        return (self._plan().get(song_plan.REACTS) or {}).get(self._band.role_named(role)[arranger.PLAYER], song_plan.USUAL_CONTRAST)

    def set_reacts(self, *, role, reacts):
        """Have a player answer to Energy evenly, at the lowest, or dramatically, at the highest. Two players who are one person, as a singer who also plays, answer alike."""
        if not self.reacts(role) or isinstance(reacts, bool) or not isinstance(reacts, int) or not song_plan.LOWEST_ENERGY <= reacts <= song_plan.HIGHEST_ENERGY:
            raise ValueError(errors.ERR_WIZARD_REACTS.format(low=song_plan.LOWEST_ENERGY, high=song_plan.HIGHEST_ENERGY, value=reacts))
        kept = dict(self._plan().get(song_plan.REACTS) or {})
        kept.pop(self._band.role_named(role)[arranger.PLAYER], None)
        if reacts != song_plan.USUAL_CONTRAST:
            kept[self._band.role_named(role)[arranger.PLAYER]] = reacts
        self._plan().pop(song_plan.REACTS, None)
        if kept:
            self._plan()[song_plan.REACTS] = kept
        self.clear_answers()

    def _comes_in_places(self):
        """Where each way of coming in puts a player's first section, for the ways the form has a place for, in the order they are offered."""
        kinds = self.section_kinds_in_form()
        intro = self.intro_kind()
        after_intro = next((place for place, kind in enumerate(kinds) if kind != intro), None)
        choruses = [place for place, kind in enumerate(kinds) if kind == wizard_limits.CHORUS_KIND]
        verse = next((place for place, kind in enumerate(kinds) if kind == wizard_limits.VERSE_KIND), None)
        found = {wizard_limits.FROM_THE_START: 0, wizard_limits.AFTER_THE_INTRO: after_intro, wizard_limits.IN_FIRST_CHORUS: choruses[0] if choruses else None,
                 wizard_limits.AFTER_FIRST_VERSE: verse + 1 if verse is not None and verse + 1 < len(kinds) else None, wizard_limits.IN_LAST_CHORUS: choruses[-1] if len(choruses) > 1 else None}
        places = {}
        for way in wizard_limits.COMES_IN_WAYS:
            if found[way] is not None and found[way] not in places.values():
                places[way] = found[way]
        return places

    def comes_in_offered(self, role):
        """Return the ways a player may come in, where the song has sections and the player is in the band."""
        return list(self._comes_in_places()) if self.is_ready() and self.player(role).is_in() else []

    def _first_place(self, role):
        return next((place for place in range(len(self.section_entries())) if role in self.section_plays(place)), None)

    def get_comes_in(self, role):
        """Return the way a player comes in, or None where the player's first section is none of the ways' or the player plays nowhere."""
        first = self._first_place(role)
        return next((way for way, place in self._comes_in_places().items() if place == first), None)

    def _usually_plays(self, *, place, role):
        return role in self._usual(place).get(arranger.PLAYS, [])

    def _quiet_places(self):
        """The places of the form a player who lays out when it is quiet sits out: those of a low Energy in a planned song."""
        return [place for place, energy in enumerate(self.energies()) if energy <= wizard_limits.QUIET_ENERGY] if self.has_song_plan() else []

    def _breakdown_places(self):
        return [place for place, kind in enumerate(self.section_kinds_in_form()) if kind in wizard_limits.BREAKDOWN_KINDS]

    def _laid_out(self, *, role, way, first):
        """Which sections a player plays under a way of laying out, from the player's first section on: never is every section the genre gives the player any part in."""
        out = {wizard_limits.NEVER_LAYS_OUT: [], wizard_limits.IN_BREAKDOWNS: self._breakdown_places(), wizard_limits.WHEN_QUIET: self._quiet_places()}[way]
        return [place for place in range(first, len(self.section_entries())) if place == first or (place not in out and (not self.section_is_held(place) or self._usually_plays(place=place, role=role)))]

    def lays_out_offered(self, role):
        """Return the ways a player may lay out: never, only in the breakdowns where the form has one, and whenever it is quiet in a planned song with a quiet section."""
        if not self.comes_in_offered(role) or self._first_place(role) is None:
            return []
        return [wizard_limits.NEVER_LAYS_OUT, *([wizard_limits.IN_BREAKDOWNS] if self._breakdown_places() else []), *([wizard_limits.WHEN_QUIET] if self._quiet_places() else [])]

    def get_lays_out(self, role):
        """Return the way a player lays out, or None where the sections the player plays are none of the ways'."""
        first = self._first_place(role)
        plays = [place for place in range(len(self.section_entries())) if role in self.section_plays(place)]
        return next((way for way in self.lays_out_offered(role) if self._laid_out(role=role, way=way, first=first) == plays), None)

    def set_comes_in(self, *, role, way):
        """Have a player come in at a place of the form and sit out every section before it; the sections after are left as they are."""
        if way not in self.comes_in_offered(role):
            raise ValueError(errors.ERR_WIZARD_COMES_IN.format(value=way))
        first = self._comes_in_places()[way]
        plays = [place for place in range(first, len(self.section_entries())) if place == first or role in self.section_plays(place)]
        self._set_plays_of(role=role, plays=plays)

    def set_lays_out(self, *, role, way):
        """Have a player lay out never, only in the breakdowns, or whenever it is quiet, from the player's first section on."""
        if way not in self.lays_out_offered(role):
            raise ValueError(errors.ERR_WIZARD_LAYS_OUT.format(value=way))
        self._set_plays_of(role=role, plays=self._laid_out(role=role, way=way, first=self._first_place(role)))

    def _set_plays_of(self, *, role, plays):
        """Have a player play in the sections at these places and no others; a section that would be left with nobody, or a song that cannot then be made, is refused."""
        kept = copy.deepcopy((self._sections, self._stages))
        try:
            for place in range(len(self.section_entries())):
                if (place in plays) != (role in self.section_plays(place)):
                    self.set_section_plays(place=place, role=role, on=place in plays)
            self.clear_answers()
            self.written_for_trial()
        except (ValueError, SongFileError) as problem:
            self._sections, self._stages = kept
            self.clear_answers()
            raise ValueError(errors.ERR_WIZARD_PLAYS_UNMADE.format(problem=problem)) from None

    # How the tune is delivered: one Phrasing generator on the tune's clips, with its own settings where they were changed.

    def tune_phrasing(self):
        """Return the settings of the Phrasing the tune's clips run, each given only where it is not what a Phrasing starts with, or
        None where the tune is played as written, with no Phrasing."""
        kept = self._extras.get(arranger.TUNE_PHRASING, {})
        return None if kept is False else dict(kept)

    def set_tune_phrasing(self, settings):
        """Say how the tune is delivered: a Phrasing's settings by name, None for a Phrasing as one starts, or False for no
        Phrasing. Settings no Phrasing has, or values a setting cannot take, are refused."""
        if settings is False:
            self._extras[arranger.TUNE_PHRASING] = False
        else:
            try:
                given = {name: value for name, value in dict(settings or {}).items() if value != generator_settings.PHRASING_DEFAULTS.get(name, value) or name not in generator_settings.PHRASING_DEFAULTS}
                kept = PhrasingSettings.from_data(data=given, where=composer_text.MSG_TUNE_PHRASING_NAME).to_data()
            except (SongFileError, TypeError, ValueError) as problem:
                raise ValueError(errors.ERR_WIZARD_TUNE_PHRASING.format(value=settings, problem=problem)) from None
            self._extras.pop(arranger.TUNE_PHRASING, None)
            if kept:
                self._extras[arranger.TUNE_PHRASING] = kept
        self.clear_answers()


    def has_phrasing(self):
        """Return whether the tune's lines breathe."""
        return bool(self._plan().get(song_plan.PHRASING, True))

    def set_phrasing(self, on):
        if not isinstance(on, bool):
            raise ValueError(errors.ERR_WIZARD_SWITCH.format(value=on))
        self._plan()[song_plan.PHRASING] = on
        self.clear_answers()

    def phrasing_way(self, name):
        """Return how the lines breathe in one respect: how long the breaths are, which lines are the shorter, or how many lines in four have a note come early."""
        return self._plan().get(song_plan.PHRASING_WAYS, {}).get(name, phrasing.USUAL_WAYS[name])

    def set_phrasing_way(self, *, name, value):
        offered = wizard_limits.PHRASING_OFFERED.get(name)
        if offered is None or isinstance(value, bool) or value not in offered:
            raise ValueError(errors.ERR_WIZARD_PHRASING.format(name=name, value=value))
        ways = self._plan().setdefault(song_plan.PHRASING_WAYS, {})
        ways.pop(name, None)
        if value != phrasing.USUAL_WAYS[name]:
            ways[name] = value
        if not ways:
            del self._plan()[song_plan.PHRASING_WAYS]
        self.clear_answers()

    def counts_in_four(self):
        """Return whether the song is in four with a tune written in eighths, where a hook is of a kind and a tune's lines breathe: both
        are written for a bar of eight eighths, which a shuffle's bar of triplets is not."""
        in_four = str(picked(style=self.style(), song=self.song_picks(wizard_limits.PREVIEW_NAME)).get(arranger.METER, arranger.COMMON_TIME)) == arranger.COMMON_TIME
        return in_four and not self.melody_habits()[melody_writer.GRID] % phrasing.EIGHTHS_IN_BAR


    # The melodies: what a song says of them all, and what a kind of section says of its own. Each field starts at what the genre
    # does, and only a field that changes the subgenre's songs is offered.

    def melody_fields(self):
        """Return the fields of the whole song's melodies that are heard in the subgenre, in the order shown."""
        if not self.is_ready() or not self._tunes.tune_kinds():
            return []
        return [field for field in wizard_limits.MELODY_WAYS if len(self.melody_ways_offered(field)) > 1]

    def melody_ways_offered(self, field):
        """Return the values of a field of the whole song's melodies that are heard in the song as it stands: the genre's own,
        each other that makes another song, and the one chosen."""
        heard = self._melody_values_heard(field=field)
        return [value for value in wizard_limits.MELODY_WAYS[field] if value == wizard_limits.USUAL_MELODY_WAYS[field] or value in heard or value == self.get_melody_way(field)]

    def _melody_values_heard(self, *, field, kind=None):
        """The values of a melody field, of the song or of a kind of section, that make another song than the field left
        unchosen does, found by arranging the song each way, once, until a choice changes."""
        return self.offered(key=(wizard_limits.MELODY_HEARD_ANSWER, field, kind), compute=lambda: self._found_melody_values_heard(field=field, kind=kind))

    def _found_melody_values_heard(self, *, field, kind):
        made = {}
        for value in (None, *(wizard_limits.SECTION_MELODY_WAYS if kind is not None else wizard_limits.MELODY_WAYS)[field]):
            trial = WizardChoices.from_data(self.to_data())
            trial._keep_melody_chosen(field=field, value=value, kind=kind)
            try:
                made[value] = arranged(style=style_of(self._genre), song=trial.song_picks(self._subgenre))[arranger.PARTS]
            except (ValueError, IndexError, KeyError, SongFileError):
                made[value] = made.get(None)
        return [value for value in made if value is not None and made[value] != made[None]]

    def get_melody_way(self, field):
        """Return what the song says of its melodies in one field: the genre's own until another is chosen."""
        chosen = self._extras.get(wizard_limits.MELODY_CHOSEN, {}).get(field)
        return chosen if chosen in wizard_limits.MELODY_WAYS[field] else wizard_limits.USUAL_MELODY_WAYS[field]

    def genre_melody_way(self, field):
        """Return the genre's own value of a field of the whole song's melodies."""
        return wizard_limits.USUAL_MELODY_WAYS[field]

    def set_melody_way(self, *, field, value):
        """Choose how busy the song's melodies are, how wide they range or how much they repeat; the genre's own is asked for by its name."""
        if field not in wizard_limits.MELODY_WAYS or value not in wizard_limits.MELODY_WAYS[field]:
            raise ValueError(errors.ERR_WIZARD_MELODY_WAY.format(field=field, value=value))
        self._keep_melody_chosen(field=field, value=None if value == wizard_limits.USUAL_MELODY_WAYS[field] else value)

    def _keep_melody_chosen(self, *, field, value, kind=None):
        """Keep one thing chosen of the melodies, for the song or for a kind of section, or forget it with None."""
        chosen = self._extras.setdefault(wizard_limits.MELODY_CHOSEN, {})
        held = chosen if kind is None else chosen.setdefault(melody_writer.BY_KIND, {}).setdefault(kind, {})
        held.pop(field, None)
        if value is not None:
            held[field] = value
        if kind is not None:
            chosen[melody_writer.BY_KIND] = {name: own for name, own in chosen[melody_writer.BY_KIND].items() if own}
            if not chosen[melody_writer.BY_KIND]:
                del chosen[melody_writer.BY_KIND]
        if not chosen:
            del self._extras[wizard_limits.MELODY_CHOSEN]
        self.clear_answers()

    def melody_characters_offered(self):
        """Return the characters a melody of the subgenre can be given: each whose engine can write the subgenre's melodies, an
        engine with no gauges only where the genre does not write by it already."""
        if not self.is_ready() or not self._tunes.tune_kinds():
            return []
        given = dict(genre=self._genre, subgenre=self._subgenre, variant=self._variant)
        offered = []
        for character in wizard_limits.CHARACTERS:
            engine = wizard_limits.CHARACTER_ENGINES[character]
            if melody_works(style=engine, **given) and (engine in wizard_limits.GAUGED_STYLES or not melody_is_usual(style=engine, **given)):
                offered.append(character)
        return offered

    def get_melody_character(self):
        """Return the character chosen for the song's melodies, or None while they are written as the genre writes them."""
        chosen = self._extras.get(wizard_limits.MELODY_CHOSEN, {}).get(wizard_limits.MELODY_CHARACTER)
        return chosen if chosen in self.melody_characters_offered() else None

    def set_melody_character(self, character):
        """Choose the character of the song's melodies, or the genre's own with None."""
        if character is not None and character not in self.melody_characters_offered():
            raise ValueError(errors.ERR_WIZARD_MELODY_WAY.format(field=wizard_limits.MELODY_CHARACTER, value=character))
        self._keep_melody_chosen(field=wizard_limits.MELODY_CHARACTER, value=character)

    def section_melody_fields(self, kind):
        """Return the fields of one kind of section's melody that are heard in the subgenre: how high it sits and how busy it is."""
        if not self.is_ready() or kind not in self._tunes.tune_kinds() or kind not in self.style()[arranger.SECTIONS]:
            return []
        return [field for field in wizard_limits.SECTION_MELODY_WAYS if self.section_melody_ways_offered(kind=kind, field=field)]

    def section_melody_ways_offered(self, *, kind, field):
        """Return the values of a field of a kind of section's own melody that are heard in the song as it stands: each that
        makes another song than the field left to the genre or the song, and the one chosen."""
        heard = self._melody_values_heard(field=field, kind=kind)
        return [value for value in wizard_limits.SECTION_MELODY_WAYS[field] if value in heard or value == self.get_section_melody(kind=kind, field=field)]

    def get_section_melody(self, *, kind, field):
        """Return what a kind of section says of its own melody in one field, or None where nothing was chosen."""
        chosen = self._extras.get(wizard_limits.MELODY_CHOSEN, {}).get(melody_writer.BY_KIND, {}).get(kind, {}).get(field)
        return chosen if chosen in wizard_limits.SECTION_MELODY_WAYS[field] else None

    def genre_height_in(self, kind):
        """Return how high the genre sets a kind of section's melody: high where its plan lifts a line, else in the middle."""
        plan = self.style()[arranger.SECTIONS].get(kind, {}).get(wizard_limits.PLAN, [])
        return melody_writer.HIGH if any(entry.get(wizard_limits.HIGHER) for entry in plan) else melody_writer.MIDDLE

    def set_section_melody(self, *, kind, field, value):
        """Choose how high a kind of section's melody sits or how busy it is, or leave it to the genre or the song with None."""
        if field not in wizard_limits.SECTION_MELODY_WAYS or (value is not None and value not in wizard_limits.SECTION_MELODY_WAYS[field]) or kind not in self._tunes.tune_kinds():
            raise ValueError(errors.ERR_WIZARD_MELODY_WAY.format(field=field, value=(kind, value)))
        self._keep_melody_chosen(field=field, value=value, kind=kind)

    def _melody_picks(self, picks):
        """What the arranger is handed of the melodies chosen, over the song's picks: what is asked of the plans' lines, the engine
        a character writes by, and the habits a range and a character change."""
        chosen = self._extras.get(wizard_limits.MELODY_CHOSEN)
        if not chosen or not self.is_ready():
            return {}
        said = {}
        asks = {}
        if chosen.get(melody_writer.REPEATS) in melody_writer.REPEATS_WAYS:
            asks[melody_writer.REPEATS] = chosen[melody_writer.REPEATS]
        if chosen.get(wizard_limits.MELODY_BUSY) in wizard_limits.BUSY_POSITIONS:
            asks[melody_writer.LINE_BUSY] = wizard_limits.BUSY_POSITIONS[chosen[wizard_limits.MELODY_BUSY]]
        by_kind = {}
        for kind, own in chosen.get(melody_writer.BY_KIND, {}).items():
            of_kind = {**({melody_writer.HEIGHT: own[melody_writer.HEIGHT]} if own.get(melody_writer.HEIGHT) in melody_writer.HEIGHTS else {}), **({melody_writer.LINE_BUSY: wizard_limits.BUSY_POSITIONS[own[wizard_limits.MELODY_BUSY]]} if own.get(wizard_limits.MELODY_BUSY) in wizard_limits.BUSY_POSITIONS else {})}
            if of_kind:
                by_kind[kind] = of_kind
        if by_kind:
            asks[melody_writer.BY_KIND] = by_kind
        if asks:
            said[melody_writer.MELODY_ASKS] = asks
        habits = dict(picks.get(arranger.MELODY, {}))
        genre_habits = self.melody_habits()
        if chosen.get(wizard_limits.MELODY_RANGE) in wizard_limits.SPAN_CHANGES and melody_writer.SPAN in genre_habits:
            habits[melody_writer.SPAN] = max(wizard_limits.LEAST_SPAN, genre_habits[melody_writer.SPAN] + wizard_limits.SPAN_CHANGES[chosen[wizard_limits.MELODY_RANGE]])
        character = self.get_melody_character()
        if character is not None:
            said[arranger.MELODY_ENGINE] = wizard_limits.CHARACTER_ENGINES[character]
            if character in wizard_limits.CHARACTER_GAUGES:
                habits[melody_writer.SMART] = {**{name: self.get_melody_gauge(name) for name in melody_writer.DEFAULT_GAUGES}, **wizard_limits.CHARACTER_GAUGES[character]}
            if character == wizard_limits.BLUESY:
                flattened = flattened_in(self._scale_type)
                habits[melody_writer.LADDER] = [{tune_notation.DEGREE: degree, **({tune_notation.ACCIDENTAL: tune_notation.FLAT} if degree in flattened else {})} for degree in wizard_limits.BLUES_DEGREES]
                habits[melody_writer.HOME] = {tune_notation.DEGREE: wizard_limits.BLUES_HOME}
        if habits:
            said[arranger.MELODY] = habits
        return said


    def trial_for_riffs(self):
        """A copy of the choices to try something on, which remembers who can play a riff and nothing else."""
        answers = self._answers
        trial = self.copied_for_trial()
        trial._answers = {key: value for key, value in answers.items() if wizard_limits.RIFF_ABLE_ANSWER in (key, key[0] if isinstance(key, tuple) else None)}
        return trial


    def section_player_kinds(self):
        """Return the kinds of section the song's form has, once each, in the form's order."""
        return list(dict.fromkeys(self.section_kinds_in_form())) if self.is_ready() else []

    def section_players(self, kind):
        """Return the players who have something to choose in a kind of section, by name, in the band's order: whoever can
        play the melody or a riff there."""
        return [role for role in self._band.roles_in() if len(self.section_parts_offered(kind=kind, role=role)) > 1] if self.is_ready() else []

    def _carries_melody_in(self, *, kind, role):
        """Whether a player may be given the melody in a kind of section: a kind that has a melody, and a player who can carry one."""
        return kind in self._tunes.tune_kinds() and role in self._tunes.tune_players_offered()

    def section_parts_offered(self, *, kind, role):
        """Return what a player may play in a kind of section: the accompaniment, or for the player the genre gives the melody
        to, a rest; the melody, where the player can carry it there; and each riff the player knows, where a riff can be
        heard from the player there."""
        own = self._band.tune_player()
        offered = [wizard_limits.RESTS_PART if role == own else wizard_limits.ACCOMPANIMENT]
        if self._carries_melody_in(kind=kind, role=role):
            offered.append(wizard_limits.MELODY_PART)
        if role in self._riffs_part.riff_players_in(kind):
            offered += self._riffs_part.riffs_known_by(role)
        return offered

    def section_part(self, *, kind, role):
        """Return what a player plays in a kind of section: ACCOMPANIMENT, RESTS_PART, MELODY_PART or a riff's name."""
        if self._carries_melody_in(kind=kind, role=role) and self._tunes.tune_player_in(kind) == role:
            return wizard_limits.MELODY_PART
        riff = self._riffs_part.riffs_played().get(kind, {}).get(role)
        if riff is not None and role in self._riffs_part.riff_players_in(kind):
            return riff
        return wizard_limits.RESTS_PART if role == self._band.tune_player() else wizard_limits.ACCOMPANIMENT

    def set_section_part(self, *, kind, role, part):
        """Choose what a player plays in a kind of section. A player given the melody takes it from whoever had it there; a
        player who gives the melody up leaves the section with none, or with the song's own player where another had been
        chosen for the kind. What is not offered, and a song that cannot then be made, are refused and nothing changes."""
        if part not in self.section_parts_offered(kind=kind, role=role):
            raise ValueError(errors.ERR_WIZARD_SECTION_PART.format(value=part, kind=kind, player=role))
        before = (copy.deepcopy(self._extras), self._riffs_part.to_data())
        had = self.section_part(kind=kind, role=role)
        by = self._extras.setdefault(arranger.TUNE_BY, {})
        if part == wizard_limits.MELODY_PART:
            by.pop(kind, None)
            if role != self._tunes.tune_played_by():
                by[kind] = role
        elif had == wizard_limits.MELODY_PART:
            by.pop(kind, None)
            if role == self._tunes.tune_played_by():
                by[kind] = arranger.NOBODY
        if not by:
            del self._extras[arranger.TUNE_BY]
        self._riffs_part.play_in(kind=kind, role=role, riff=None if part in (wizard_limits.ACCOMPANIMENT, wizard_limits.RESTS_PART, wizard_limits.MELODY_PART) else part)
        try:
            self.written_for_trial()
        except (ValueError, KeyError, IndexError, SongFileError) as problem:
            self._extras = before[0]
            self._riffs_part.read(before[1])
            self.clear_answers()
            raise ValueError(errors.ERR_WIZARD_RIFF_UNMADE.format(value=(kind, role, part), problem=problem)) from None


    def checked_line(self, *, line, steps):
        """A line written by hand, checked: notes of a degree of the scale and rests, each a whole number of steps, as long as the line it stands for, with a note in it."""
        if not isinstance(line, list) or not all(isinstance(note, dict) for note in line):
            raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=line))
        for note in line:
            length = note.get(tune_notation.REST, note.get(tune_notation.STEPS))
            degree = note.get(tune_notation.DEGREE, line_edits.FIRST_DEGREE)
            numbers = [length, degree, note.get(tune_notation.OCTAVE, 0)]
            if any(isinstance(number, bool) or not isinstance(number, int) for number in numbers) or length < 1 or not line_edits.FIRST_DEGREE <= degree <= line_edits.NOTES_IN_SCALE:
                raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=note))
            if tune_notation.REST not in note and not line_edits.LOWEST_PLACE <= line_edits.place_of(note) <= line_edits.HIGHEST_PLACE:
                raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=note))
        if line_edits.steps_of(line) != steps or all(tune_notation.REST in note for note in line):
            raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=line))
        return copy.deepcopy(line)

    def made_song_plan(self):
        """The plan of the song as the choices stand."""
        song = self.song_picks(wizard_limits.PREVIEW_NAME)
        style = self.style()
        picks = picked(style=style, song=song)
        chord_entry = values_of(style=style, trait=self.progression_trait())[picks[self.progression_trait()]]

        def chords_of(section):
            return [chord_of(chord) for chord in section.get(arranger.CHORDS) or chord_entry.get(arranger.BY_SECTION, {}).get(section[arranger.KIND]) or chord_entry[arranger.PATTERN]]
        return SongPlan(style=style, song=song, form_names=song[arranger.FORM] if isinstance(song[arranger.FORM], list) else form_of(style=style, song=song, meter=str(picks.get(arranger.METER, arranger.COMMON_TIME)), tempo=self._tempo),
                        tempo=self._tempo, scale_type=self._scale_type, chords_of=chords_of)

    def energies(self):
        """Return the Energy of each section of the form, in order, as the plan works them out."""
        self._plan()
        return self.remembered(key=wizard_limits.ENERGY_ANSWER, compute=lambda: self.made_song_plan().energies())

    def _said_of_sections(self):
        planned = self.made_song_plan().planned()
        return [planned[arranger.SECTIONS][name][song_plan.SAID_OF_SECTION] for name in planned[arranger.FORM]]

    def said_of_sections(self):
        """Return what the plan says of each section of the form, in order: its Energy, how it leaves and, once, the hook's kind."""
        self._plan()
        return self.remembered(key=wizard_limits.PLAN_ANSWER, compute=self._said_of_sections)

    # What a panel listens to: the song made as the choices stand, and where in it the hook, the tune and a section are.

    def made_for_listening(self):
        """Return the set these choices make, to be heard and thrown away, with its one song's name."""
        return self.made_setlist(name=wizard_limits.PREVIEW_NAME, version=version_values.VERSION), wizard_limits.PREVIEW_NAME

    def patterns_of_song(self):
        """The patterns the song plays, straight from the writer, for a question that asks only whether a choice changes the
        notes: the set itself is never built, which takes as long again as writing the song. A pattern no clip plays is left
        out, as the set made leaves it out. Choices the writer cannot make a song of are answered from the set, which tries
        the other progressions drawn."""
        try:
            data = composed(given=arranged(style=self.style(), song=self.song_picks(wizard_limits.PREVIEW_NAME)), version=version_values.VERSION)
        except (ValueError, IndexError, KeyError, SongFileError):
            return self.written_for_trial()[0].to_data()[Section.PATTERNS]
        scenes = data[set_writer.SONGS][wizard_limits.PREVIEW_NAME][set_writer.SCENES]
        played = {clip[set_writer.PATTERN] for scene in scenes for clip in scene[set_writer.TRACKS].values()}
        return {name: pattern for name, pattern in data[Section.PATTERNS].items() if name in played}

    def written_for_trial(self):
        """The set these choices write, with its one song's name, for a question that is answered by making the song: whether
        a song can be made, or whether a choice changes its notes. No such question needs the players' trades of loudness,
        which change no note, so none pays for them."""
        return self.written_setlist(name=wizard_limits.PREVIEW_NAME, version=version_values.VERSION), wizard_limits.PREVIEW_NAME


    def tune_scene(self):
        """Return the place in the form of the first section the tune's player plays in, or None."""
        player = self._band.tune_player()
        return next((place for place in range(len(self.section_labels())) if player in self.section_plays(place) and not self.section_is_held(place)), None)

    def get_extra(self, name):
        """Return one thing laid over the song's picks, as held and not to be changed, or None where the song has none of the name."""
        return self._extras.get(name)

    def set_extra(self, *, name, value):
        """Lay one thing over the song's picks under a name, or take the name away with None."""
        if value is None:
            self._extras.pop(name, None)
        else:
            self._extras[name] = value

    def clear_answers(self):
        """Let go of every answer found by making the song, after a change that what a song keeps does not show."""
        self._answers = {}

    def hook_changes_song(self):
        """Return whether a hook changes the song in its form: always in a form of the song's own, and in a form of the subgenre's where a player carries a tune in the sections that mark a hook."""
        return self.has_own_form() or hook_matters(genre=self._genre, subgenre=self._subgenre, variant=self._variant, form=self.get_form())

    def forget_section_beside(self):
        """Forget what single sections were given of what the answering player does, which a plan for every section takes the place of."""
        if self._sections is not None:
            for entry in self._sections:
                entry.pop(wizard_limits.BESIDE_KEPT, None)

    def made_again(self):
        """Return other choices made from what a song would keep of these, to change and make a song from without touching these."""
        return WizardChoices.from_data(self.to_data())

    def get_song_extras(self):
        """Return everything laid over the song's picks, the riffs among it, as data the caller may change."""
        return {**copy.deepcopy(self._extras), **self._riffs_part.to_data()}

    def _set_kept_extras(self, *, extras):
        self.set_song_extras(extras)
        self._riffs_part.take_riffs_of_older_song()

    def _set_kept_stages(self, *, stages):
        """Take how a song starts and ends as a song kept it: the sections are the song's already, so only what was chosen is kept, where it is still offered."""
        kept = {field: value for field, value in stages.items() if field in (wizard_limits.START_KEPT, wizard_limits.END_KEPT, wizard_limits.FIRST_PLAYER_KEPT, wizard_limits.SETUP_BARS_KEPT)}
        self._stages = {field: value for field, value in kept.items() if isinstance(value, (str, int)) and not isinstance(value, bool)}

    def made_setlist(self, *, name, version):
        """Return a set holding the one song these choices make, under a name, with all the song uses, the song keeping the choices:
        the song as written, and then each player's trade of loudness for a much denser part, so that no section arrives too loud.
        A melody is left on top. The trade is counted from what is written: nothing is played to make a song."""
        made = self.written_setlist(name=name, version=version)
        loudness_steps.with_trades(song=made.get_item(section=Section.SONGS, name=name), kept=self.melody_players())
        return made

    def written_setlist(self, *, name, version):
        """Return the set as written, before any player trades loudness: what a report holds the song made against.

        A run that has no seed yet draws one first, so that the same choices make the same song again.
        """
        if not self.is_ready():
            raise ValueError(errors.ERR_WIZARD_NOT_READY)
        if self._seed is None:
            self.draw_seed()
        made = None
        # A progression drawn by chance that makes no song of these choices, as one too long for a section's bars, gives way to the next drawn.
        for progression in self.progressions_by_chance()[:-1]:
            try:
                made = Setlist.from_data(data=composed(given=arranged(style=self.style(), song=self.song_picks(name, progression=progression)), version=version))
                break
            except (ValueError, IndexError, KeyError, SongFileError):
                made = None
        if made is None:
            last = self.progressions_by_chance()[-1:]
            given = arranged(style=self.style(), song=self.song_picks(name, progression=last[0] if last else None))
            made = Setlist.from_data(data=composed(given=given, version=version))
        made.get_item(section=Section.SONGS, name=name).set_wizard_choices(self.to_data())
        # A part written for a section that leaves the part out is played by nothing, and would be left behind in the open set.
        made.remove_unused()
        # Each pattern goes in the group named after the track that plays it.
        made.group_patterns_by_track(made.get_item(section=Section.SONGS, name=name))
        return made

    def melody_players(self):
        """Return the players who carry a melody somewhere in the song, by name: each kind of section's, and the soloist."""
        return {self._tunes.tune_player_in(kind) for kind in self._tunes.tune_kinds()} | {wizard_limits.SOLO}
