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

"""The song plan: every section of a song given an Energy, and what follows from it worked out before the song is arranged.

A song that asks for a plan has each place of its form made a section of its own, so that a second verse can differ from the
first. Each takes an Energy from 1 to 10: the style's for the section's kind, a little more each time the kind returns, the
most at the last chorus, pulled apart or together by the song's Contrast; a song may give any section's Energy itself. From
the Energy come how far each player goes toward their own way of playing, each player changing at points of their own; who
plays; the cymbal; how loud the section is, ordinary playing kept under full so that a chorus can grow; and how the section
leaves for the next: the size of the fill, a drop-out, stops or a build, never the same twice running, and the chord of its
last bar set up for what follows. Energy never changes a tune's notes.

Everything worked out here is written into the song's sections, where the arranger reads it, and anything a song says of a
section itself is kept over what the plan would say.
"""

import random

from llamatron.macro_composer import hook_kinds
from llamatron.macro_composer.joins import BUILD, DROP_OUT, FILL_OF_JOIN, LEAVES, STOPS, TAIL, TAIL_EIGHTHS
from llamatron.macro_composer.melody import BREATHES, FIRST_HOOK_TAKE, HOOK, HOOK_KIND, HOOK_KINDS, HOOK_TAKE
from llamatron.strings.macro_composer import MSG_PLAN_ENERGY, MSG_PLAN_HOOK, MSG_PLAN_LEAVES_FILL, MSG_PLAN_LEAVES_TAIL, MSG_PLAN_SET_UP, MSG_PLAN_STAGE, MSG_REPEATED_SCENE

# The fields of a song's plan, and of the plan a style gives.
PLAN_OF_SONG = 'song_plan'
CONTRAST = 'contrast'
# How strongly each player answers to Energy, by the player's name: the usual, or less for a player who plays evenly and more for a dramatic one.
REACTS = 'reacts'
GROWTH = 'growth'
PHRASING = 'phrasing'
# How the lines breathe, where the song asks: the fields of phrasing.py.
PHRASING_WAYS = 'phrasing_ways'
BY_PLACE = 'sections'
ENERGY = 'energy'
ENERGY_OF_KIND = 'energy'
RISING = 'rising'
# Whether a place of the form rises, where the song says so itself.
RISES = 'rises'
LAST_CHORUS = 'last_chorus'
CHANGE_POINTS = 'levels'
COMES_IN = 'comes_in'
CYMBALS = 'cymbal'
# The Energy from which a section has the kit's percussion, which a quieter section goes without.
PERCUSSION_FROM = 'percussion_from'
PERCUSSION = 'percussion'
NO_PERCUSSION = 'none'
FILL_SIZES = 'fills'
TAILS_ALLOWED = 'tails'
NO_SETUP = 'no_setup'
SETUP = 'setup'
NOT_AT_ALL = 'not at all'
USUAL = 'usual'
# The fields of a song and of a section, as the arranger reads them.
FORM = 'form'
SECTIONS = 'sections'
KIND = 'kind'
BARS = 'bars'
PLAYS = 'plays'
PICKS = 'picks'
HELD = 'held'
ALLOWS = 'intensity'
CRASH_START = 'crash'
SEED = 'seed'
TEMPLATE = 'template'
MELODY = 'melody'
SECTION_PLAN = 'plan'
# A kind of section that is staged plays another of its shapes each time it comes after the first, with lines of its own.
STAGED = 'staged'
SHAPES = 'shapes'
LINE = 'line'
HOOK_LINE = 'hook'
STAGE_LINE = '{} stage {}'
# What a place of the form may say of its scene: a tempo, the tempo it reaches by its end, and the root and the type of a scale of its own.
TEMPO_OF_PLACE = 'tempo'
TEMPO_END_OF_PLACE = 'tempo_end'
ROOT_OF_PLACE = 'root'
TYPE_OF_PLACE = 'type'
SCENE_FIELDS = (TEMPO_OF_PLACE, TEMPO_END_OF_PLACE, ROOT_OF_PLACE, TYPE_OF_PLACE)
SCENE_TEMPO = 'tempo'
SCENE_TEMPO_START = 'tempo_start'
SCENE_TEMPO_END = 'tempo_end'
# A scene's scale, as its root and type, which the arranger names and adds to the set's scales.
SCALE_OF_PLACE = 'scale'
KEY_OF_SONG = 'key'
# A join's fill given by its size, for the style's fill of that size.
FILL_SIZE = 'fill_size'
SCENE_SETTINGS = 'settings'
DRAWN_AS = 'drawn_as'
SAID_OF_SECTION = 'said'
DRUM_SOLO = 'drum_solo'
FILL_INSIDE = 'fill_inside'
FILL_INSIDE_EVERY = 'fill_inside_every'
# A marker: a stroke or two the style's plan writes, laid over the last bar of each phrase inside a section that has no fill there.
MARKER = 'marker'
MARKER_EVERY = 'marker_every'
LAST_CHORD = 'last_chord'
DEGREE = 'degree'
ACCIDENTAL = 'accidental'
SWELL_START = 'swell_start'
SWELL_END = 'swell_end'
# A section that fades: softer bar by bar to this share of what is written, from all of it where no plan says how loud the section is.
FADES = 'fades'
FADED = 20
UNFADED = 100
CYMBAL = 'cymbal'
# What a song may say of its fills: the trait that names the fill, the value for none, how often they come and the count for never.
FILLS_TRAIT = 'fills'
NO_FILL = 'none'
FILLS_COME = 'fills_come'
NO_FILLS = 0
CHORUS = 'chorus'
MINOR = 'minor'
# Energy: its limits, the kind's where a style says nothing, the middle that Contrast pulls about, and the usual Contrast and growth.
LOWEST_ENERGY = 1
HIGHEST_ENERGY = 10
USUAL_ENERGY = 6
MIDDLE_ENERGY = 6
USUAL_CONTRAST = 5
USUAL_GROWTH = 1
USUAL_LAST_CHORUS = 10
# The Energy at which a player reaches each level where a style says nothing, and how far a song's seed moves a player's points.
USUAL_CHANGE_POINTS = (1, 4, 7, 9)
POINT_MOVES = (-1, 0, 0, 1)
POINT_SEED = '{} plan {}'
# How loud a section is, as a share of what is written: ordinary playing leaves room above it. A rising section starts as one two lower would.
QUIETEST = 80
LOUDEST = 100
RISES_FROM = 2
# The sizes of fill, by how far the Energy rises into the next section, and the Energy at which a section has a small fill inside it, every so many bars.
SMALL = 'small'
MEDIUM = 'medium'
BIG = 'big'
BIG_RISE = 3
FILL_INSIDE_FROM = 5
FILL_INSIDE_BARS = 8
MARKER_BARS = 4
OTHER_SIZE = {BIG: MEDIUM, MEDIUM: SMALL, SMALL: MEDIUM}
# A crash starts a section that arrives at this Energy or more from below, and a drop-out lasts about a second: so many eighths by the tempo.
CRASH_FROM = 6
FAST_TEMPO = 120
DROP_EIGHTHS_FAST = 4
DROP_EIGHTHS_SLOW = 2
# The chord a last bar takes to set up a section that starts at home: the fifth, or in a minor key the seventh, a whole step under home.
HOME = 1
APPROACH = 5
APPROACH_IN_MINOR = 7


def within(energy):
    return max(LOWEST_ENERGY, min(HIGHEST_ENERGY, int(round(energy))))


def loudness_at(energy):
    """How loud a section of an Energy is, as a share of what is written."""
    return round(QUIETEST + (within(energy) - LOWEST_ENERGY) * (LOUDEST - QUIETEST) / (HIGHEST_ENERGY - LOWEST_ENERGY))


def level_at(*, energy, points):
    """The level a player reaches at an Energy: how many of the player's change points the Energy has passed."""
    return max(1, sum(1 for point in points if energy >= point))


class SongPlan:
    """A song's plan, worked out from the song, its style and the chords each section plays."""

    __slots__ = ('_style', '_song', '_names', '_tempo', '_scale_type', '_chords_of', '_given', '_of_style', '_sections', '_energies', '_form_names')

    def __init__(self, *, style, song, form_names, tempo, scale_type, chords_of):
        self._style = style
        self._song = song
        self._tempo = tempo
        self._scale_type = scale_type
        # The chords a section plays, given the section as the arranger reads it.
        self._chords_of = chords_of
        self._given = song[PLAN_OF_SONG] if isinstance(song[PLAN_OF_SONG], dict) else {}
        self._of_style = style.get(PLAN_OF_SONG, {})
        self._form_names = list(form_names)
        self._names = []
        self._sections = []
        met = {}
        for name in form_names:
            met[name] = met.get(name, 0) + 1
            of_song = song.get(SECTIONS, {}).get(name, {})
            kind = of_song.get(KIND, name)
            self._names.append(name if met[name] == 1 else MSG_REPEATED_SCENE.format(name, met[name]))
            self._sections.append({**style[SECTIONS].get(kind, {}), **of_song, KIND: kind})
        self._energies = self._worked_energies()

    # The stages of a kind of section that is staged, as a solo: the first time the kind comes it plays its own plan, and each
    # time after another of its shapes in turn, so that no two running are alike, each with lines of its own.

    def stages(self):
        """Return, for each place of the form, the stage the place is: the shape's name and its plan, or None for a place that plays
        its kind's own plan."""
        met = {}
        found = []
        for section in self._sections:
            shapes = section.get(SHAPES) or {}
            met[section[KIND]] = met.get(section[KIND], 0) + 1
            stage = met[section[KIND]]
            if not section.get(STAGED) or not shapes or stage == 1:
                found.append(None)
                continue
            name = list(shapes)[(stage - 2) % len(shapes)]
            # The song's hook is the same line wherever it is said; every other line is the stage's own.
            plan = [{**entry, LINE: entry[LINE] if entry.get(HOOK_LINE) else STAGE_LINE.format(entry[LINE], stage)} for entry in shapes[name]]
            found.append((name, plan))
        return found

    def shapes(self):
        """Return the name of the shape each place takes as a stage, or None."""
        return [stage[0] if stage else None for stage in self.stages()]

    # What a song says of one place of its form.

    def _at(self, place):
        by_place = self._given.get(BY_PLACE) or []
        return (by_place[place] or {}) if place < len(by_place) else {}

    def _for_subgenre(self, *, field, default):
        """A field of the style's plan that is given by subgenre, the usual where the song's subgenre has none."""
        given = self._of_style.get(field, {})
        return given.get(self._song.get(TEMPLATE), given.get(USUAL, default))

    # Energy.

    def _worked_energies(self):
        of_kind = self._of_style.get(ENERGY_OF_KIND, {})
        growth = self._given.get(GROWTH, self._of_style.get(GROWTH, USUAL_GROWTH))
        contrast = self._given.get(CONTRAST, USUAL_CONTRAST)
        kinds = [section[KIND] for section in self._sections]
        last_chorus = max((place for place, kind in enumerate(kinds) if kind == CHORUS), default=None)
        met = {}
        energies = []
        for place, kind in enumerate(kinds):
            met[kind] = met.get(kind, 0) + 1
            energy = of_kind.get(kind, USUAL_ENERGY) + growth * (met[kind] - 1)
            if place == last_chorus and met[kind] > 1:
                energy = max(energy, self._of_style.get(LAST_CHORUS, USUAL_LAST_CHORUS))
            energy = MIDDLE_ENERGY + (energy - MIDDLE_ENERGY) * contrast / USUAL_CONTRAST
            energies.append(within(self._at(place).get(ENERGY, energy)))
        return energies

    def energies(self):
        """The Energy of each place of the form."""
        return list(self._energies)

    def chords_at(self, place):
        """The chords of a place of the form, as the song or the progression gives them."""
        return self._chords_of(self._sections[place])

    def joins(self):
        """What each place of the form leaves with, or None for a place that leaves with nothing worked out."""
        return self._joins()

    # What follows from a section's Energy.

    def _points_of(self, instrument):
        """A player's change points: the style's, each moved a little by the song's seed, so that two songs' bands do not change together."""
        points = self._of_style.get(CHANGE_POINTS, {}).get(instrument, USUAL_CHANGE_POINTS)
        dice = random.Random(POINT_SEED.format(self._song.get(SEED, 0), instrument))
        return [points[0]] + [point + dice.choice(POINT_MOVES) for point in points[1:]]

    def _allowed(self, place):
        """The level each player may reach in a section, by the section's Energy."""
        instruments = list(dict.fromkeys([*self._of_style.get(CHANGE_POINTS, {}), *self._sections[place].get(ALLOWS, {})]))
        return {instrument: level_at(energy=self._energy_felt(place=place, instrument=instrument), points=self._points_of(instrument)) for instrument in instruments}

    def _energy_felt(self, *, place, instrument):
        """A section's Energy as one player answers to it: further from the middle for a dramatic player, nearer for an even one."""
        reacts = (self._given.get(REACTS) or {}).get(instrument, USUAL_CONTRAST)
        return within(MIDDLE_ENERGY + (self._energies[place] - MIDDLE_ENERGY) * reacts / USUAL_CONTRAST)

    def _plays(self, place):
        """Who plays in a section: the kind's players, but those who come in only at a higher Energy."""
        comes_in = self._of_style.get(COMES_IN, {})
        return [role for role in self._sections[place].get(PLAYS, []) if self._energies[place] >= comes_in.get(role, LOWEST_ENERGY)]

    def _cymbal(self, place):
        """The cymbal a section's Energy asks for, or nothing where the style says none."""
        chosen = None
        for energy, cymbal in self._of_style.get(CYMBALS, []):
            if self._energies[place] >= energy:
                chosen = cymbal
        return chosen

    def _rises(self, place):
        """Whether a section grows louder through its bars and leaves with a build: a rising kind of the style's, or as the song says of the place."""
        return bool(self._at(place).get(RISES, self._sections[place][KIND] in self._of_style.get(RISING, [])))

    def _loudness(self, place):
        energy = self._energies[place]
        rising = self._rises(place)
        if self._at(place).get(FADES):
            return {SWELL_START: loudness_at(energy), SWELL_END: FADED}
        return {SWELL_START: loudness_at(energy - RISES_FROM if rising else energy), SWELL_END: loudness_at(energy)}

    # Joins.

    def _stays(self, place):
        """Whether a section is one a join is worked out for: played by the band, with a section after it."""
        section = self._sections[place]
        return place < len(self._sections) - 1 and not section.get(HELD) and not section.get(DRUM_SOLO)

    def _fill(self, size):
        """The fill of a size: the style's, unless the song chose its fill, which is then the fill of every size, or chose none, or asked for no fills at all."""
        if self._song.get(FILLS_COME) == NO_FILLS:
            return None
        chosen = self._song.get(PICKS, {}).get(FILLS_TRAIT)
        if chosen is not None:
            return None if chosen == NO_FILL else chosen
        return self._of_style.get(FILL_SIZES, {}).get(size)

    def _fill_inside_every(self, *, place):
        """How many bars apart the fills inside a section come, or nothing for none: as the song asks, and otherwise every four bars of a long section from an Energy up."""
        bars = self._sections[place].get(BARS, 0)
        asked = self._song.get(FILLS_COME)
        if asked is not None:
            return asked if isinstance(asked, int) and 0 < asked < bars else None
        return FILL_INSIDE_BARS if bars > FILL_INSIDE_BARS and self._energies[place] >= FILL_INSIDE_FROM else None

    def _marker(self, *, place):
        """The marker the section's phrases end on, or nothing: the style's, in a section longer than a phrase, unless the song says how
        often its fills come, chose its fill or asked for none."""
        if self._song.get(FILLS_COME) is not None or self._song.get(PICKS, {}).get(FILLS_TRAIT) is not None:
            return None
        return self._of_style.get(MARKER) if self._sections[place].get(BARS, 0) > MARKER_BARS else None

    def _joins(self):
        """What each section leaves with: the tail and the fill, by what follows, how far the Energy moves and what was done last."""
        allowed = self._for_subgenre(field=TAILS_ALLOWED, default=(DROP_OUT, STOPS, BUILD))
        kinds = [section[KIND] for section in self._sections]
        last_chorus = self._last_choruses_start(kinds)
        joins = []
        before = None
        dropped = False
        for place in range(len(self._sections)):
            if not self._stays(place):
                joins.append(None)
                continue
            rise = self._energies[place + 1] - self._energies[place]
            following = self._sections[place + 1]
            join = {}
            if following.get(DRUM_SOLO) and STOPS in allowed:
                join = {TAIL: STOPS}
            elif place + 1 == last_chorus and kinds[place] != CHORUS and DROP_OUT in allowed and not dropped:
                # The one silence of the song: the band stops for about a second, and the last chorus comes in whole.
                join = {TAIL: DROP_OUT, TAIL_EIGHTHS: DROP_EIGHTHS_FAST if self._tempo >= FAST_TEMPO else DROP_EIGHTHS_SLOW}
                dropped = True
            elif self._rises(place) and BUILD in allowed and (before or {}).get(TAIL) != BUILD:
                join = {TAIL: BUILD}
            elif not following.get(HELD):
                # The last chorus is come into on the biggest fill, whatever the rise.
                size = BIG if rise >= BIG_RISE or place + 1 == last_chorus else MEDIUM if rise > 0 else SMALL
                if (before or {}).get(FILL_OF_JOIN) == self._fill(size):
                    size = OTHER_SIZE[size]
                if self._fill(size):
                    join = {FILL_OF_JOIN: self._fill(size)}
            if LEAVES in self._at(place):
                # A join the song gives is the whole join, and a drop-out with no length takes the tempo's.
                join = self._given_join(place)
            joins.append(join)
            before = join
        return joins

    def _given_join(self, place):
        join = dict(self._at(place)[LEAVES] or {})
        if FILL_SIZE in join:
            size = join.pop(FILL_SIZE)
            if self._fill(size):
                join[FILL_OF_JOIN] = self._fill(size)
        if join.get(TAIL) == DROP_OUT and TAIL_EIGHTHS not in join:
            join[TAIL_EIGHTHS] = DROP_EIGHTHS_FAST if self._tempo >= FAST_TEMPO else DROP_EIGHTHS_SLOW
        return join

    def _scene_settings(self, place):
        """The settings of a section's scene the song gives the place: a tempo of its own, one it moves to by its end, and a key or a scale of its own."""
        at = self._at(place)
        settings = {}
        if TEMPO_OF_PLACE in at and TEMPO_END_OF_PLACE in at:
            settings.update({SCENE_TEMPO_START: at[TEMPO_OF_PLACE], SCENE_TEMPO_END: at[TEMPO_END_OF_PLACE]})
        elif TEMPO_END_OF_PLACE in at:
            settings.update({SCENE_TEMPO_START: self._tempo, SCENE_TEMPO_END: at[TEMPO_END_OF_PLACE]})
        elif TEMPO_OF_PLACE in at:
            settings[SCENE_TEMPO] = at[TEMPO_OF_PLACE]
        if ROOT_OF_PLACE in at or TYPE_OF_PLACE in at:
            settings[SCALE_OF_PLACE] = {ROOT_OF_PLACE: at.get(ROOT_OF_PLACE, self._song[KEY_OF_SONG][ROOT_OF_PLACE]), TYPE_OF_PLACE: at.get(TYPE_OF_PLACE, self._scale_type)}
        return settings

    def _last_chord(self, place):
        """The chord a section's last bar takes to set up the next, or nothing: a section that rises into one starting at home, or
        that would sit on home into home, ends on the approach chord, where the subgenre sets joins up at all."""
        if not self._stays(place) or self._at(place).get(SETUP) == NOT_AT_ALL or self._song.get(TEMPLATE) in self._of_style.get(NO_SETUP, []):
            return None
        following = self._sections[place + 1]
        if following.get(HELD) or following.get(DRUM_SOLO):
            return None
        last = self._chords_of(self._sections[place])[-1]
        first = self._chords_of(following)[0]
        approach = APPROACH_IN_MINOR if self._scale_type == MINOR else APPROACH
        at_home = first.get(DEGREE) == HOME and ACCIDENTAL not in first
        rises = self._energies[place + 1] > self._energies[place]
        if not at_home or last.get(DEGREE) == approach or not (rises or last.get(DEGREE) == HOME):
            return None
        return approach

    @staticmethod
    def _last_choruses_start(kinds):
        """The place of the first of the choruses a song ends with, or nothing for a song with no chorus."""
        places = [place for place, kind in enumerate(kinds) if kind == CHORUS]
        if not places:
            return None
        start = places[-1]
        while start - 1 in places:
            start -= 1
        return start

    # The song planned.

    def planned(self):
        """The song with a section for each place of its form, each saying what the plan worked out, and its tunes asked to
        breathe and its hook to be of a kind."""
        joins = self._joins()
        stages = self.stages()
        sections = {}
        hook_said = False
        for place, name in enumerate(self._names):
            section = self._sections[place]
            of_song = self._song.get(SECTIONS, {}).get(self._form_names[place], {})
            energy = self._energies[place]
            said = [MSG_PLAN_ENERGY.format(energy)]
            made = {KIND: section[KIND], DRAWN_AS: section[KIND]}
            if stages[place] is not None:
                made[SECTION_PLAN] = stages[place][1]
                said.append(MSG_PLAN_STAGE.format(stages[place][0]))
            if not section.get(HELD) and not section.get(DRUM_SOLO):
                arrives = place > 0 and energy > self._energies[place - 1] and energy >= CRASH_FROM
                after_tail = place > 0 and (joins[place - 1] or {}).get(TAIL) in (DROP_OUT, BUILD, STOPS)
                made.update({ALLOWS: self._allowed(place), PLAYS: self._plays(place), CRASH_START: bool(arrives or after_tail or (place > 0 and self._sections[place - 1].get(DRUM_SOLO))),
                             SCENE_SETTINGS: self._loudness(place)})
                # A cymbal the song chose is the drummer's all through; the plan's goes by Energy.
                cymbal = None if CYMBAL in self._song.get(PICKS, {}) else self._cymbal(place)
                made[PICKS] = {**section.get(PICKS, {}), **({CYMBAL: cymbal} if cymbal else {})}
                # Percussion the song chose plays all through; the kind's comes in from an Energy up, usually at the chorus.
                if PERCUSSION not in self._song.get(PICKS, {}) and energy < self._of_style.get(PERCUSSION_FROM, LOWEST_ENERGY):
                    made[PICKS][PERCUSSION] = NO_PERCUSSION
                if joins[place] is not None:
                    made[LEAVES] = joins[place]
                    inside_every = self._fill_inside_every(place=place)
                    if inside_every and self._fill(SMALL):
                        made[FILL_INSIDE] = self._fill(SMALL)
                        made[FILL_INSIDE_EVERY] = inside_every
                    marker = self._marker(place=place)
                    if marker:
                        made[MARKER] = marker
                        made[MARKER_EVERY] = MARKER_BARS
                    if joins[place].get(TAIL):
                        said.append(MSG_PLAN_LEAVES_TAIL.format(joins[place][TAIL]))
                    elif joins[place].get(FILL_OF_JOIN):
                        said.append(MSG_PLAN_LEAVES_FILL.format(joins[place][FILL_OF_JOIN]))
                last_chord = self._last_chord(place)
                if last_chord is not None:
                    made[LAST_CHORD] = last_chord
                    said.append(MSG_PLAN_SET_UP.format(last_chord))
            if not hook_said and self._has_hook() and any(entry.get(HOOK) for entry in section.get(SECTION_PLAN, [])) and self._given.get(HOOK_KINDS, True):
                kind = {**hook_kinds.kind_of(seed=self._song.get(SEED, 0), take=self._song.get(HOOK_TAKE, FIRST_HOOK_TAKE)), **self._song.get(MELODY, {}).get(HOOK_KIND, {})}
                said.append(MSG_PLAN_HOOK.format(hook_kinds.said_of(kind)))
                hook_said = True
            # What the song says of the section itself, and of this place of its form, stands over what the plan worked out.
            own = {field: value for field, value in self._at(place).items() if field not in (ENERGY, SETUP, LEAVES, RISES, FADES, *SCENE_FIELDS)}
            scene = {**made.get(SCENE_SETTINGS, {}), **self._scene_settings(place)}
            sections[name] = {**made, **of_song, **own, **({SCENE_SETTINGS: scene} if scene else {}), SAID_OF_SECTION: ' '.join(said)}
        melody = {**({BREATHES: self._given.get(PHRASING_WAYS) or True} if self._given.get(PHRASING, True) else {}), **({HOOK_KINDS: True} if self._given.get(HOOK_KINDS, True) else {}), **self._song.get(MELODY, {})}
        return {**self._song, FORM: list(self._names), SECTIONS: sections, MELODY: melody}

    def _has_hook(self):
        return bool(self._song.get(HOOK, self._style.get(HOOK, False)))
