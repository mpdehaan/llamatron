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
    COMMON_TIME, METER, bar_length,
    BARS, CHORD_TRAIT, CHORD_TRAIT_FIELD, FORM, HELD, PLAYS, GENRE, KEY, NAME, ROOT, SCALE_TYPE, SECTIONS, SEED, STYLE, TEMPLATE, TEMPLATES, TEMPO, TITLE, TRAITS, TYPE, USUAL,
    arranged, forms_of, picked, section_of, share_of, style_named, style_names, values_of,
)
from llamatron.macro_composer.composer import composed
from llamatron.music.note import ROOT_NAMES
from llamatron.strings.errors import ERR_WIZARD_NO_SUCH_FORM, ERR_WIZARD_NO_SUCH_GENRE, ERR_WIZARD_NO_SUCH_ROOT, ERR_WIZARD_NO_SUCH_SCALE_TYPE, ERR_WIZARD_NO_SUCH_SUBGENRE, ERR_WIZARD_NOT_READY, ERR_WIZARD_SEED, ERR_WIZARD_TEMPO

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


# A tempo counts quarter notes a minute.
QUARTERS_IN_WHOLE = 4
SECONDS_IN_MINUTE = 60


class WizardChoices:
    """The choices of one run of the song wizard."""

    __slots__ = ('_genre', '_subgenre', '_root', '_scale_type', '_tempo', '_form', '_seed')

    def __init__(self):
        self._genre = None
        self._subgenre = None
        self._root = None
        self._scale_type = None
        self._tempo = None
        self._form = None
        self._seed = None

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
        return choices

    def to_data(self):
        """Return the choices made, as plain data a song keeps."""
        held = {GENRE: self._genre, SUBGENRE: self._subgenre, ROOT: self._root, TYPE: self._scale_type, TEMPO: self._tempo, FORM: self._form, SEED: self._seed}
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
            self._tempo = self.usual_tempo()
            self._scale_type = self.usual_scale_type()
            self._root = USUAL_ROOTS[self._scale_type]
            self._form = None

    def is_ready(self):
        """Return whether a song can be made: a genre and a subgenre are chosen, and the rest has its usual values."""
        return self._subgenre is not None

    # What the subgenre usually has.

    def _picks(self):
        return picked(style=style_of(self._genre), song={TEMPLATE: self._subgenre})

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

    def set_form(self, form):
        if form not in self.forms():
            raise ValueError(ERR_WIZARD_NO_SUCH_FORM.format(value=form))
        self._form = form

    def form_sections(self):
        """Return the sections of the form in the order they play, by name."""
        chosen = self.get_form()
        return next((list(form[SECTIONS]) for form in self._forms() if form[NAME] == chosen), [])

    def section_facts(self, name):
        """Return how many bars a section of the form lasts and who plays in it, by the names the genre gives its players."""
        section = section_of(name=name, style=style_of(self._genre), song={})
        return (HELD_BARS if section.get(HELD) else section[BARS]), list(section.get(PLAYS, []))

    # The meter and the length, which follow from the subgenre, the tempo and the form.

    def meter(self):
        """Return the meter the subgenre is played in."""
        return str(self._picks().get(METER, COMMON_TIME))

    def form_seconds(self, *, form=None):
        """Return how long a form of the subgenre lasts at the tempo chosen, in seconds: the chosen form's, unless another is named."""
        sections = next((form_[SECTIONS] for form_ in self._forms() if form_[NAME] == (form or self.get_form())), [])
        bars = sum(self.section_facts(name)[0] for name in sections)
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
        return {NAME: name, TITLE: name, STYLE: self._genre, TEMPLATE: self._subgenre, KEY: {ROOT: self._root, TYPE: self._scale_type}, TEMPO: self._tempo, FORM: self.get_form(), SEED: self._seed}

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
