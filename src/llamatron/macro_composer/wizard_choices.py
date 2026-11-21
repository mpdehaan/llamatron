# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
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

from llamatron.caching.kept import kept_while
from llamatron.macro_composer import arranger, composer as set_writer, hook_writing, joins as joins_values, line_edits, loudness_steps, melody as melody_writer, notation as tune_notation, phrasing, riffs as riffs_values, song_plan, wizard_limits
from llamatron.macro_composer.arranger import arranged, bar_length, chord_of, form_of, picked, share_in, style_in, style_named, style_names, values_of, variant_named, variants_of
from llamatron.macro_composer.band_choices import BandChoices
from llamatron.macro_composer.choices_part import kept_until_choices_change, set_each_kept
from llamatron.macro_composer.composer import composed
from llamatron.macro_composer.form_choices import FormChoices
from llamatron.macro_composer.hook_choices import HookChoices
from llamatron.macro_composer.kit_choices import KitChoices
from llamatron.macro_composer.player_choices import PlayerChoices
from llamatron.macro_composer.riff_choices import RiffChoices
from llamatron.macro_composer.riffs import flattened_in
from llamatron.macro_composer.section_choices import chords_as_text, chords_from_text, own_copy_of, SectionChoices
from llamatron.macro_composer.solo_choices import SoloChoices
from llamatron.macro_composer.song_plan import SongPlan
from llamatron.macro_composer.sound_choices import SoundChoices
from llamatron.macro_composer.tune_choices import TuneChoices
from llamatron.model.file import version as version_values
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects import generator_settings
from llamatron.model.objects.generator_settings import PhrasingSettings
from llamatron.model.objects.setlist import Setlist
from llamatron.model.values import note as note_values
from llamatron.model.vocabulary import limits
from llamatron.model.vocabulary.file_format import Section
from llamatron.playback.song_renderer import SongRenderer
from llamatron.user_strings import errors, macro_composer as composer_text


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
    choices.get_song_form().set_form(form)
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



def style_key(choices):
    """What the style is worked out from: the genre, the subgenre and the kind of song chosen. The answers kept by it, and the
    picks kept by it with the ways chosen, are made from their keys and nothing else, so they cannot go stale and the tests
    need not work them out again (caching/kept.py)."""
    return (choices.get_genre(), choices.get_subgenre(), choices.get_variant())


class WizardChoices:
    """The choices of one run of the song wizard."""

    __slots__ = ('_extras', '_genre', '_subgenre', '_root', '_scale_type', '_tempo', '_form_part', '_seed', '_melody', '_hook', '_sounds_part', '_solos', '_tunes', '_band', '_kit', '_riffs_part', '_gauges', '_melody_settings', '_answers', '_answers_of', '_offers', '_offers_of', '_offers_held', '_offers_mixed', '_kept', '_variant')

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
        self._seed = None
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
        self._form_part = FormChoices(choices=self)
        self._gauges = {}
        self._melody_settings = {}
        # What a song file lays over the song's picks: the song's plan, and anything a section is given, as its chords or a tune.
        self._extras = {}

    # Reading and keeping the choices.

    @classmethod
    def from_data(cls, data):
        """Return the choices a song kept, leaving out whatever no longer fits, as a genre renamed since: what is left out is chosen again."""
        choices = cls()
        setters = [(arranger.GENRE, choices.set_genre), (wizard_limits.SUBGENRE, choices.set_subgenre), (arranger.VARIANT, choices.take_variant), (arranger.ROOT, choices.set_root), (arranger.TYPE, choices.set_scale_type), (arranger.TEMPO, choices.set_tempo), (arranger.FORM, choices.get_song_form().set_form), (arranger.SEED, choices.set_seed)]
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
                (self._form_part.set_own_sections, [dict(sections=data[wizard_limits.OWN_SECTIONS])] if data.get(wizard_limits.OWN_SECTIONS) else []),
                (self._set_kept_melody, [dict(style=data[wizard_limits.MELODY_STYLE])] if data.get(wizard_limits.MELODY_STYLE) else []),
                (self._hook.read, [dict(data=data)]),
                (self.set_melody_gauge, [dict(name=name, position=position) for name, position in (data.get(wizard_limits.GAUGES_KEPT) or {}).items()]),
                (self._band.take_kept_player_row, [dict(role=role, name=name, values=values) for role, rows in (data.get(wizard_limits.PLAYER_ROWS_KEPT) or {}).items() for name, values in rows.items()]
                 if isinstance(data.get(wizard_limits.PLAYER_ROWS_KEPT), dict) and all(isinstance(rows, dict) for rows in data[wizard_limits.PLAYER_ROWS_KEPT].values()) else []),
                (self._set_kept_melody_setting, [dict(name=name, value=value) for name, value in (data.get(wizard_limits.MELODY_SETTINGS_KEPT) or {}).items()]),
                (self._set_kept_extras, [dict(extras=data[wizard_limits.EXTRAS_KEPT])] if data.get(wizard_limits.EXTRAS_KEPT) else []),
                (self._form_part.take_kept_stages, [dict(stages=data[wizard_limits.STAGES_KEPT])] if isinstance(data.get(wizard_limits.STAGES_KEPT), dict) else [])]
        set_each_kept(kept)

    def to_data(self):
        """Return the choices made, as plain data a song keeps."""
        band = self._band.to_data()
        held = {arranger.GENRE: self._genre, wizard_limits.SUBGENRE: self._subgenre, arranger.VARIANT: self._variant, arranger.ROOT: self._root, arranger.TYPE: self._scale_type, arranger.TEMPO: self._tempo, arranger.FORM: self._form_part.get_written_form(), arranger.SEED: self._seed,
                **{field: band.get(field) for field in (arranger.PICKS, arranger.PLAYERS, arranger.WITHOUT, wizard_limits.PLAYER_GAUGES_KEPT, wizard_limits.PLAYER_ROWS_KEPT, wizard_limits.BESIDE_KEPT)},
                wizard_limits.OWN_SECTIONS: [own_copy_of(entry) for entry in self._form_part.get_own_sections()] if self._form_part.has_own_form() else None,
                wizard_limits.MELODY_STYLE: self._melody, **self._hook.to_data(), **self._sounds_part.to_data(),
                wizard_limits.GUITARISTS_KEPT: band.get(wizard_limits.GUITARISTS_KEPT),
                **self._kit.to_data(), wizard_limits.GAUGES_KEPT: dict(self._gauges) or None, wizard_limits.MELODY_SETTINGS_KEPT: dict(self._melody_settings) or None,
                wizard_limits.EXTRAS_KEPT: self.get_song_extras() or None, wizard_limits.STAGES_KEPT: dict(self._form_part.get_stages()) or None}
        return {field: value for field, value in held.items() if value is not None}

    # The genre and the subgenre, which everything else follows.

    def player(self, role):
        """Return the choices of one player of the band, by the player's name in the genre's band."""
        return PlayerChoices(choices=self, role=role)

    def section(self, place):
        """Return one section of the form, by its place in the form, which answers what is chosen of the section and changes it."""
        return SectionChoices(choices=self, place=place)

    def fills(self, *, kind, bars, plays=None):
        """Return whether the subgenre's parts can fill a section of a kind at a length, played by the players given or by the kind's own."""
        return bars_work(genre=self._genre, subgenre=self._subgenre, variant=self._variant, kind=kind, bars=bars, plays=plays)

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

    def answers_kept_by(self):
        """Return the choices that keep the answers found by making the song, which are these, and that the choices asked."""
        return self, None

    def get_song_form(self):
        """Return the choices of the song's form and how it starts and ends, a part of these choices."""
        return self._form_part

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
            self._form_part.reset()
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
                wizard_limits.LOST_OWN_CHORDS: sum(1 for entry in self._form_part.section_entries() if entry.get(wizard_limits.OWN_OF_SECTION, {}).get(arranger.CHORDS)),
                wizard_limits.LOST_FORM: int(self._form_part.has_own_form() or self._form_part.get_written_form() != usual.get_song_form().get_written_form()),
                wizard_limits.LOST_TUNE_TAKES: len(self._extras.get(wizard_limits.TUNE_TAKES, {})) + int(self._hook.get_hook_take() != melody_writer.FIRST_HOOK_TAKE),
                wizard_limits.LOST_RIFFS: self._riffs_part.written_count(by_hand=False)}
        kept = {wizard_limits.KEPT_OWN_TUNES: len(self._extras.get(arranger.OWN_TUNES, {})), wizard_limits.KEPT_OWN_RIFFS: self._riffs_part.written_count(by_hand=True)}
        return {kind: count for kind, count in lost.items() if count}, {kind: count for kind, count in kept.items() if count}

    def _band_as_counted(self):
        """Return every setting of the band another genre forgets, each under a name of its own, so that two bands can be compared
        setting by setting."""
        by_name = {(wizard_limits.GENRE_SETTING, name): value for name, value in (
            (wizard_limits.MELODY_STYLE, self._melody),)}
        for kept_as, held in ((wizard_limits.GAUGES_KEPT, self._gauges), (wizard_limits.MELODY_SETTINGS_KEPT, self._melody_settings), (wizard_limits.STAGES_KEPT, self._form_part.get_stages())):
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
        self._form_part.reset()
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

    # The form's sections, which follow the form chosen until a person changes one; the form is then the song's own.

    def plan_with_lines(self, *, kind, plan, lines):
        """A section's plan of lines with what each line was given of its own laid over it: its notes, its breath and whether a note comes early."""
        usual = self.style()[arranger.SECTIONS][kind].get(wizard_limits.PLAN, []) if plan is None else plan
        return [{**entry, **(lines.get(count) or {})} for count, entry in enumerate(copy.deepcopy(usual))]

    # How the song starts and ends: stages before the first section with a tune and after the last, each a section of its own.

    def drums_role(self):
        """Return the band's drummer, where one plays in the song as chosen, or None."""
        return next((role for role in self._band.roles() if self._band.role_named(role).get(arranger.DRUMS) and self.player(role).is_in()), None)

    # A form made from a few answers, each question asked only where the subgenre can play the kind of section it is about.

    # The band: who plays, how each plays and how busy each is.

    def _forget_band(self):
        self._band.reset()
        self._sounds_part.reset()
        self._kit.reset()
        self._gauges = {}
        self._melody_settings = {}

    @kept_while(style_key)
    def style(self):
        """Return the genre's style template as the subgenre chosen has it, worked out once for a genre, a subgenre and a kind, and
        never changed by a caller."""
        return style_in(style=style_of(self._genre), template=self._subgenre, variant=self._variant)


    @kept_while(style_key)
    def trait_has_sound(self, *, trait, value):
        return arranger.SOUND in values_of(style=self.style(), trait=trait)[value]

    @kept_while(style_key)
    def roles_by_name(self):
        """Return each player the genre's band may have, by name, as the style says of the player, or nothing before a subgenre is
        chosen; worked out once for a style, since a page asks after the players many times a key."""
        return {entry[arranger.ROLE]: entry for entry in self.style()[arranger.ROLES]} if self.is_ready() else {}


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
        if self._form_part.has_own_form():
            sections = self._form_part.song_sections()
            for place, name in enumerate(self._form_part.form_sections()):
                plays = self._band.plays_of_one_guitarist(self.section(place).plays())
                if plays is not None:
                    sections[name][arranger.PLAYS] = plays
            return sections
        sections = {}
        for kind in set(self._form_part.form_sections()):
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

    def step_length(self, offset):
        """Choose the next longer form, or the next shorter, stopping at the longest and the shortest: the song's length
        follows its sections, so a length is chosen by choosing a form."""
        forms = self._form_part.forms_by_length()
        place = forms.index(self._form_part.get_form()) + offset
        if 0 <= place < len(forms):
            self._form_part.set_form(forms[place])

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
        for place, kind in enumerate(self._form_part.section_kinds_in_form()):
            if kind not in chords and not self.section(place).is_held():
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
        picks = data_laid_over(under=self._picks_chosen(name), over=self.extras_with_sections())
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

    def extras_with_sections(self):
        """The song's extras, the plan in them holding what each section of the form was given of its own, by place."""
        if not self.has_song_plan():
            return self._extras
        plan = self._extras[song_plan.PLAN_OF_SONG] if isinstance(self._extras.get(song_plan.PLAN_OF_SONG), dict) else {}
        if not (any(entry.get(wizard_limits.OWN_OF_SECTION) for entry in self._form_part.section_entries()) or self._intro_hook_kept() is not None):
            # A song planned because its genre plans every song asks for the plan as one that was switched on does.
            return {**self._extras, song_plan.PLAN_OF_SONG: plan}
        given = list(plan.get(song_plan.BY_PLACE) or [])
        by_place = []
        for place, entry in enumerate(self._form_part.section_entries()):
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
            own = self.section(place).with_fade_way(own=own)
            if own.get(wizard_limits.LINES_OF_SECTION):
                own[wizard_limits.PLAN] = self.plan_with_lines(kind=entry[arranger.KIND], plan=own.get(wizard_limits.PLAN), lines=own[wizard_limits.LINES_OF_SECTION])
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
        return [place for place, entry in enumerate(self._form_part.section_entries()) if entry[arranger.KIND] == wizard_limits.INTRO and not self.section(place).is_held()]

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
        self.plan_extras().pop(wizard_limits.INTRO_HOOK, None)
        if role is not None:
            self.plan_extras()[wizard_limits.INTRO_HOOK] = role
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
        self._form_part.add_section(place=place, kind=wizard_limits.INTRO)
        self.clear_answers()
        return place

    def remove_intro_part(self, place):
        """Take a part out of the intro. The notes written by hand for the part go with it, and those of the parts after it stay theirs."""
        if place not in self._intro_places():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION.format(value=place))
        number = self._intro_number_at(place)
        self.section(place).remove()
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
        own = self.section(place).entry().get(wizard_limits.OWN_OF_SECTION, {}).get(wizard_limits.INTRO_HOOK)
        if own == arranger.NOBODY:
            return None
        offered = self.intro_hook_players()
        return own if own in offered else self.get_intro_hook()

    def set_intro_melody(self, *, place, role):
        """Have a player say the hook in one part of the intro, or nobody with None. The other parts stay as they are."""
        if place not in self._intro_places() or (role is not None and role not in self.intro_hook_players()):
            raise ValueError(errors.ERR_WIZARD_INTRO_HOOK.format(value=role))
        self.section(place).store_own(field=wizard_limits.INTRO_HOOK, value=arranger.NOBODY if role is None else role)

    def intro_melody_place(self):
        """Return the place in the form of the first part of the intro somebody says the hook in, or None where nobody does."""
        return next((place for place in self._intro_places() if self.intro_melody_player(place) is not None), None)

    def _intro_number_at(self, place):
        """A part's number among the form's sections of the kind intro, counted from 1, which is what its own notes are kept under."""
        return len([other for other in range(place + 1) if self.section(other).kind() == wizard_limits.INTRO])

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

    @kept_until_choices_change
    def _intro_in_made(self, place):
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
        own = self.section(place).entry().get(wizard_limits.OWN_OF_SECTION, {}).get(wizard_limits.INTRO_HOOK)
        able = [role for role in (self._band.answered_by(), self._band.tune_player()) if role is not None] if self._hook.can_have_hook() and self._hook.has_hook() else []
        role = None if own == arranger.NOBODY else own if own in able else self._intro_hook_kept()
        if role is None:
            return {}
        answers = {melody_writer.ANSWER: True} if role == self._band.answered_by() else {}
        lines = [{melody_writer.LINE: melody_writer.HOOK, melody_writer.HOOK: True, wizard_limits.HIGHER: True, **answers, **({wizard_limits.VARIED: True} if count % 2 else {})} for count in range(max(self.section(place).bars() // wizard_limits.BARS_IN_A_LINE, 1))]
        return {wizard_limits.PLAN: lines, arranger.PLAYS: list(dict.fromkeys([*self.section(place).plays(), role]))}

    # What a section of a planned song is given of its own, over the plan and the song: each is None until given, and None gives it back.

    def checked_own(self, *, field, value):
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

    @kept_until_choices_change
    def made_form(self):
        """The song arranged as the choices stand: its parts and its form, kept until a choice changes."""
        return arranged(style=self.style(), song=self.song_picks(wizard_limits.PREVIEW_NAME))

    def tune_steps_in_bar(self):
        """Return how many steps a bar of the tune has."""
        return self.melody_habits()[melody_writer.GRID]

    def _picks_chosen(self, name):
        return {arranger.NAME: name, arranger.TITLE: name, arranger.STYLE: self._genre, arranger.TEMPLATE: self._subgenre, arranger.VARIANT: self._variant, arranger.KEY: {arranger.ROOT: self._root, arranger.TYPE: self._scale_type}, arranger.TEMPO: self._tempo, arranger.FORM: self._form_part.form_sections() if self._form_part.has_own_form() else self._form_part.get_form(), arranger.SEED: self._seed,
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

    def plan_extras(self):
        if not self.has_song_plan():
            raise ValueError(errors.ERR_WIZARD_NO_SONG_PLAN)
        if not isinstance(self._extras.get(song_plan.PLAN_OF_SONG), dict):
            self._extras[song_plan.PLAN_OF_SONG] = {}
        return self._extras[song_plan.PLAN_OF_SONG]

    def get_contrast(self):
        return self.plan_extras().get(song_plan.CONTRAST, song_plan.USUAL_CONTRAST)

    def set_contrast(self, contrast):
        if isinstance(contrast, bool) or not isinstance(contrast, int) or not song_plan.LOWEST_ENERGY <= contrast <= song_plan.HIGHEST_ENERGY:
            raise ValueError(errors.ERR_WIZARD_CONTRAST.format(low=song_plan.LOWEST_ENERGY, high=song_plan.HIGHEST_ENERGY, value=contrast))
        self.plan_extras()[song_plan.CONTRAST] = contrast
        self.clear_answers()

    # Where in the form a player can come in and lay out, which each player's part asks (player_choices.py).

    def comes_in_places(self):
        """Return where each way of coming in puts a player's first section, for the ways the form has a place for, in the order they are offered."""
        kinds = self._form_part.section_kinds_in_form()
        intro = self._form_part.intro_kind()
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

    def quiet_places(self):
        """Return the places of the form a player who lays out when it is quiet sits out: those of a low Energy in a planned song."""
        return [place for place, energy in enumerate(self.energies()) if energy <= wizard_limits.QUIET_ENERGY] if self.has_song_plan() else []

    def breakdown_places(self):
        """Return the places of the form's breakdowns."""
        return [place for place, kind in enumerate(self._form_part.section_kinds_in_form()) if kind in wizard_limits.BREAKDOWN_KINDS]

    def section_count(self):
        """Return how many sections the form holds."""
        return len(self._form_part.section_entries())

    def set_plays_of(self, *, role, plays):
        """Have a player play in the sections at these places and no others; a section that would be left with nobody, or a song that cannot then be made, is refused."""
        kept = self._form_part.kept()
        try:
            for place in range(self.section_count()):
                if (place in plays) != (role in self.section(place).plays()):
                    self.section(place).set_plays(role=role, on=place in plays)
            self.clear_answers()
            self.written_for_trial()
        except (ValueError, SongFileError) as problem:
            self._form_part.restore(kept)
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
                kept = PhrasingSettings.handed_over(data=given, where=composer_text.MSG_TUNE_PHRASING_NAME).to_data()
            except (SongFileError, TypeError, ValueError) as problem:
                raise ValueError(errors.ERR_WIZARD_TUNE_PHRASING.format(value=settings, problem=problem)) from None
            self._extras.pop(arranger.TUNE_PHRASING, None)
            if kept:
                self._extras[arranger.TUNE_PHRASING] = kept
        self.clear_answers()


    def has_phrasing(self):
        """Return whether the tune's lines breathe."""
        return bool(self.plan_extras().get(song_plan.PHRASING, True))

    def set_phrasing(self, on):
        if not isinstance(on, bool):
            raise ValueError(errors.ERR_WIZARD_SWITCH.format(value=on))
        self.plan_extras()[song_plan.PHRASING] = on
        self.clear_answers()

    def phrasing_way(self, name):
        """Return how the lines breathe in one respect: how long the breaths are, which lines are the shorter, or how many lines in four have a note come early."""
        return self.plan_extras().get(song_plan.PHRASING_WAYS, {}).get(name, phrasing.USUAL_WAYS[name])

    def set_phrasing_way(self, *, name, value):
        offered = wizard_limits.PHRASING_OFFERED.get(name)
        if offered is None or isinstance(value, bool) or value not in offered:
            raise ValueError(errors.ERR_WIZARD_PHRASING.format(name=name, value=value))
        ways = self.plan_extras().setdefault(song_plan.PHRASING_WAYS, {})
        ways.pop(name, None)
        if value != phrasing.USUAL_WAYS[name]:
            ways[name] = value
        if not ways:
            del self.plan_extras()[song_plan.PHRASING_WAYS]
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
        trial._answers = {key: value for key, value in answers.items() if RiffChoices.is_riff_able_answer(key)}
        return trial


    def section_player_kinds(self):
        """Return the kinds of section the song's form has, once each, in the form's order."""
        return list(dict.fromkeys(self._form_part.section_kinds_in_form())) if self.is_ready() else []

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
        self.plan_extras()
        return self._plan_energies()

    @kept_until_choices_change
    def _plan_energies(self):
        return self.made_song_plan().energies()

    @kept_until_choices_change
    def plan_joins(self):
        """Return how each section of the form leaves for the next, as the plan works them out, None for a section that does not."""
        return self.made_song_plan().joins()

    @kept_until_choices_change
    def plan_shapes(self):
        """Return the shape of each section of the form as the plan gives it, None for a section with none."""
        return self.made_song_plan().shapes()

    @kept_until_choices_change
    def _said_of_sections(self):
        planned = self.made_song_plan().planned()
        return [planned[arranger.SECTIONS][name][song_plan.SAID_OF_SECTION] for name in planned[arranger.FORM]]

    def said_of_sections(self):
        """Return what the plan says of each section of the form, in order: its Energy, how it leaves and, once, the hook's kind."""
        self.plan_extras()
        return self._said_of_sections()

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
        return next((place for place in range(len(self._form_part.section_labels())) if player in self.section(place).plays() and not self.section(place).is_held()), None)

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
        return self._form_part.has_own_form() or hook_matters(genre=self._genre, subgenre=self._subgenre, variant=self._variant, form=self._form_part.get_form())

    def made_again(self):
        """Return other choices made from what a song would keep of these, to change and make a song from without touching these."""
        return WizardChoices.from_data(self.to_data())

    def get_song_extras(self):
        """Return everything laid over the song's picks, the riffs among it, as data the caller may change."""
        return {**copy.deepcopy(self._extras), **self._riffs_part.to_data()}

    def _set_kept_extras(self, *, extras):
        self.set_song_extras(extras)
        self._riffs_part.take_riffs_of_older_song()

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
