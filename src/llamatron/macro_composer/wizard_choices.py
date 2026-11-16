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

import functools
import random

from llamatron.composition.file_format import Section
from llamatron.composition.limits import MAX_TEMPO, MIN_TEMPO
from llamatron.composition.setlist import Setlist
from llamatron.macro_composer.arranger import (
    COMMON_TIME, DRUMS, KIND, METER, PICKS, PLAYER, PLAYERS, ROLE, ROLES, SOUND, TRAIT, VALUE, WITHOUT, bar_length, fits,
    BARS, CHORD_TRAIT, CHORD_TRAIT_FIELD, FORM, HELD, PLAYS, GENRE, KEY, NAME, ROOT, SCALE_TYPE, SECTIONS, SEED, STYLE, TEMPLATE, TEMPLATES, TEMPO, TITLE, TRAITS, TYPE, USUAL,
    arranged, forms_of, picked, section_of, share_of, style_named, style_names, values_of,
)
from llamatron.macro_composer.composer import composed
from llamatron.composition.song_file_error import SongFileError
from llamatron.music.note import ROOT_NAMES
from llamatron.playback.song_renderer import SongRenderer
from llamatron.strings.marks import MSG_WIZARD_SECTION_VARIANT
from llamatron.support.version import VERSION as A_VERSION
from llamatron.strings.errors import ERR_WIZARD_BAD_SECTIONS, ERR_WIZARD_BUSY, ERR_WIZARD_LAST_PLAYER, ERR_WIZARD_LAST_SECTION, ERR_WIZARD_NO_SUCH_SECTION, ERR_WIZARD_NO_SUCH_SECTION_KIND, ERR_WIZARD_SECTION_BARS, ERR_WIZARD_SECTION_NEEDS_PLAYER, ERR_WIZARD_NO_SUCH_FORM, ERR_WIZARD_NO_SUCH_PLAYER, ERR_WIZARD_NO_SUCH_WAY, ERR_WIZARD_NO_WAY, ERR_WIZARD_NO_SUCH_GENRE, ERR_WIZARD_NO_SUCH_ROOT, ERR_WIZARD_NO_SUCH_SCALE_TYPE, ERR_WIZARD_NO_SUCH_SUBGENRE, ERR_WIZARD_NOT_READY, ERR_WIZARD_SEED, ERR_WIZARD_TEMPO

# The fields of the choices as a song keeps them.
SUBGENRE = 'subgenre'
# The ends of a style's usual tempos, in its template.
LOWEST = 'lowest'
HIGHEST = 'highest'
# The scale types a song may be made in, the plainest first, and the root each starts on until one is chosen.
MAJOR = 'major'
MINOR = 'minor'
SCALE_TYPES = [MAJOR, MINOR]
USUAL_ROOTS = {MAJOR: 'C', MINOR: 'E'}
# How long a section that is one held chord lasts, in bars.
HELD_BARS = 1
# The seeds a run draws from: large enough that two runs seldom share one, small enough to read in a file.
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
def bars_work(*, genre, subgenre, kind, bars):
    """Return whether a subgenre's parts can fill a section of a kind at a length, found by making one and measuring it, once:
    some parts are written over several bars and divide only some lengths, and some, as a chorus of twelve bars, last as long
    as they are written whatever is asked."""
    style = style_of(genre)
    song = {NAME: kind, TITLE: kind, STYLE: genre, TEMPLATE: subgenre, KEY: {ROOT: USUAL_ROOTS[MAJOR], TYPE: MAJOR}, SEED: FIRST_SEED,
            FORM: [kind], SECTIONS: {kind: {KIND: kind, BARS: bars}}}
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

    __slots__ = ('_genre', '_subgenre', '_root', '_scale_type', '_tempo', '_form', '_seed', '_ways', '_levels', '_without', '_sections')

    def __init__(self):
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
        self._without = []
        # The form's sections once a person has changed them, each its kind and what it changes of the kind; None while a suggested form is followed.
        self._sections = None

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
        kept = [(self.set_way, [dict(trait=trait, value=value) for trait, value in (data.get(PICKS) or {}).items()]),
                (self._set_level, [dict(player=player, level=level) for player, level in (data.get(PLAYERS) or {}).items()]),
                (self.set_role_in, [dict(role=role, on=False) for role in data.get(WITHOUT) or []]),
                (self.set_own_sections, [dict(sections=data[OWN_SECTIONS])] if data.get(OWN_SECTIONS) else [])]
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
                OWN_SECTIONS: [own_copy_of(entry) for entry in self._sections] if self._sections is not None else None}
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
            self._levels = {player: USUAL_BUSY for player in style_of(self._genre).get(PLAYERS, {})}

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

    def section_facts(self, name):
        """Return how many bars a section of the form lasts and who plays in it, by the section's name."""
        place = self.form_sections().index(name)
        return self.section_bars(place), self.section_plays(place)

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
        if self.section_is_held(place):
            return []
        usual = self._usual(place)[BARS]
        lengths = sorted({usual // HALF, usual, usual * HALF, self.section_bars(place)} - {0})
        return [bars for bars in lengths if bars == usual or bars_work(genre=self._genre, subgenre=self._subgenre, kind=self._entry(place)[KIND], bars=bars)]

    def set_section_bars(self, *, place, bars):
        if isinstance(bars, bool) or not isinstance(bars, int) or bars not in self.bars_offered(place):
            raise ValueError(ERR_WIZARD_SECTION_BARS.format(value=bars))
        entry = self._own_entries()[place]
        entry.pop(BARS, None)
        if bars != self._usual(place)[BARS]:
            entry[BARS] = bars

    def set_section_plays(self, *, place, role, on):
        """Have a player play in a section or sit it out. A section keeps one player."""
        self._role(role)
        plays = [name for name in self.roles() if (name in self.section_plays(place) or (on and name == role)) and (on or name != role)]
        if not plays:
            raise ValueError(ERR_WIZARD_SECTION_NEEDS_PLAYER)
        entry = self._own_entries()[place]
        entry.pop(PLAYS, None)
        if sorted(plays) != sorted(self._usual(place).get(PLAYS, [])):
            entry[PLAYS] = plays

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
            if not self._sections:
                raise ValueError(ERR_WIZARD_LAST_SECTION)
        except (KeyError, TypeError, ValueError):
            self._sections = kept
            raise ValueError(ERR_WIZARD_BAD_SECTIONS.format(value=sections)) from None

    # The band: who plays, how each plays and how busy each is.

    def _forget_band(self):
        self._ways = {}
        self._levels = {}
        self._without = []

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
        return list(entry[DRUMS]) if entry.get(DRUMS) else [entry[TRAIT]]

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
        follows its sections, so a length is chosen by choosing a form (the user's design)."""
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

    def song_picks(self, name):
        """Return the choices as a song's picks, which the arranger makes a song of."""
        return {NAME: name, TITLE: name, STYLE: self._genre, TEMPLATE: self._subgenre, KEY: {ROOT: self._root, TYPE: self._scale_type}, TEMPO: self._tempo, FORM: self.form_sections() if self.has_own_form() else self.get_form(), SEED: self._seed,
                PICKS: dict(self._ways), PLAYERS: dict(self._levels), WITHOUT: list(self._without),
                **({SECTIONS: self._song_sections()} if self.has_own_form() else {})}

    def made_setlist(self, *, name, version):
        """Return a set holding the one song these choices make, under a name, with all the song uses, the song keeping the choices.

        A run that has no seed yet draws one first, so that the same choices make the same song again.
        """
        if not self.is_ready():
            raise ValueError(ERR_WIZARD_NOT_READY)
        if self._seed is None:
            self.draw_seed()
        given = arranged(style=style_of(self._genre), song=self.song_picks(name))
        made = Setlist.from_data(data=composed(given=given, version=version))
        made.get_item(section=Section.SONGS, name=name).set_wizard_choices(self.to_data())
        # A part written for a section that leaves the part out is played by nothing, and would be left behind in the open set.
        made.remove_unused()
        return made
