# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

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

from llamatron.model.schema.file_format import VelocitySetting
from llamatron.music_theory.composing import joins as joins_values
from llamatron.user_strings import song_wizard as wizard_text
from llamatron.wizards.create_song import hook_writing, melody as melody_values, wizard_names

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
ENERGY_OF_KIND = 'energy'
RISING = 'rising'
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
SCENE_FIELDS = (wizard_names.TEMPO_OF_PLACE, wizard_names.TEMPO_END_OF_PLACE, wizard_names.ROOT_OF_PLACE, wizard_names.TYPE_OF_PLACE)
SCENE_TEMPO = 'tempo'
# The tempo a scene's Tempo Ramp In reaches, over the whole scene, from the scene's tempo.
SCENE_TEMPO_END = 'tempo_in_end'
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
# How loud a section's scene plays: the level that holds, the level a ramp in starts from and its bars, and the level a ramp out ends at and its bars.
SCENE_VELOCITY = VelocitySetting.LEVEL
SCENE_VELOCITY_IN_START = VelocitySetting.IN_START
SCENE_VELOCITY_IN_OVER = VelocitySetting.IN_OVER
SCENE_VELOCITY_OUT_END = VelocitySetting.OUT_END
SCENE_VELOCITY_OUT_OVER = VelocitySetting.OUT_OVER
FADES_IN = 'fades_in'
FADE_FIELDS = (wizard_names.SONG_PLAN_FADES, wizard_names.FADE_LEVEL, wizard_names.FADE_OVER, FADES_IN)


def faded(*, own, loud):
    """Return the scene's velocity of a section that fades, from what the section says of its fade and how loud the section is
    played: a fade in is a ramp in that rises from the fade's level to the section's loudness over the fade's bars and stays
    there, and a fade out is a ramp out that falls from the section's loudness to the fade's level over the fade's bars, the
    last of the section. A fade that says no bars takes the whole section, which whoever writes the scene knows the bars of."""
    # A fade's level is a percentage of each note's written velocity, as a scene's velocity is.
    level = own.get(wizard_names.FADE_LEVEL, wizard_names.FADED)
    over = own.get(wizard_names.FADE_OVER)
    if own.get(FADES_IN):
        velocity = {SCENE_VELOCITY: loud, SCENE_VELOCITY_IN_START: level}
        if over:
            velocity[SCENE_VELOCITY_IN_OVER] = over
        return velocity
    velocity = {SCENE_VELOCITY: loud, SCENE_VELOCITY_OUT_END: level}
    if over:
        velocity[SCENE_VELOCITY_OUT_OVER] = over
    return velocity
CYMBAL = 'cymbal'
# What a song may say of its fills: the trait that names the fill, the value for none, how often they come and the count for never.
FILLS_TRAIT = 'fills'
NO_FILL = 'none'
FILLS_COME = 'fills_come'
NO_FILLS = 0
CHORUS = 'chorus'
MINOR = 'minor'
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
    return max(wizard_names.LOWEST_ENERGY, min(wizard_names.HIGHEST_ENERGY, int(round(energy))))


def loudness_at(energy):
    """How loud a section of an Energy is, as a share of what is written."""
    return round(QUIETEST + (within(energy) - wizard_names.LOWEST_ENERGY) * (LOUDEST - QUIETEST) / (wizard_names.HIGHEST_ENERGY - wizard_names.LOWEST_ENERGY))


def level_at(*, energy, points):
    """Return the level a player reaches at an Energy: how many of the player's change points the Energy has passed, at least one."""
    passed = 0
    for point in points:
        if energy >= point:
            passed += 1
    return max(1, passed)


# What the song says of a place that the plan works out from, and so does not lay over the section.
PLANNED_FROM = (wizard_names.SONG_PLAN_ENERGY, wizard_names.SONG_PLAN_SETUP, wizard_names.JOINS_LEAVES, wizard_names.SONG_PLAN_RISES, *FADE_FIELDS, *SCENE_FIELDS)


def _scene_name(*, name, count):
    """Return the name of a section's scene: the section's name, numbered from its second time on."""
    if count == 1:
        return name
    return wizard_text.MSG_REPEATED_SCENE.format(name, count)


def _last_place_of(*, kinds, kind):
    """Return the place of the last section of a kind, or None."""
    last = None
    for place, each in enumerate(kinds):
        if each == kind:
            last = place
    return last



class SongPlan:
    """A song's plan, worked out from the song, its style and the chords each section plays."""

    __slots__ = ('_style', '_song', '_names', '_tempo', '_scale_type', '_chords_of', '_given', '_of_style', '_sections', '_energies', '_form_names', '_section_joins')

    def __init__(self, *, style, song, form_names, tempo, scale_type, chords_of):
        self._style = style
        self._song = song
        self._tempo = tempo
        self._scale_type = scale_type
        # The chords a section plays, given the section as the arranger reads it.
        self._chords_of = chords_of
        given = song[PLAN_OF_SONG]
        if not isinstance(given, dict):
            given = {}
        self._given = given
        self._of_style = style.get(PLAN_OF_SONG, {})
        self._form_names = list(form_names)
        self._names = []
        self._sections = []
        sections_of_song = song.get(SECTIONS, {})
        met = {}
        for name in form_names:
            met[name] = met.get(name, 0) + 1
            of_song = sections_of_song.get(name, {})
            kind = of_song.get(KIND, name)
            self._names.append(_scene_name(name=name, count=met[name]))
            section = dict(style[SECTIONS].get(kind, {}))
            section.update(of_song)
            section[KIND] = kind
            self._sections.append(section)
        self._energies = self._worked_energies()
        # Imported here, since the joins read this module's names.
        from llamatron.wizards.create_song.section_joins import SectionJoins
        self._section_joins = SectionJoins(plan=self)

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

    def given_at(self, place):
        """Return what the song gives one place of its form, or nothing."""
        by_place = self._given.get(BY_PLACE) or []
        if place >= len(by_place):
            return {}
        return by_place[place] or {}

    def for_subgenre(self, *, field, default):
        """A field of the style's plan that is given by subgenre, the usual where the song's subgenre has none."""
        given = self._of_style.get(field, {})
        return given.get(self._song.get(TEMPLATE), given.get(USUAL, default))

    # Energy.

    def _worked_energies(self):
        """Return the Energy of each section of the form: its kind's, growing each time the kind comes again, the last chorus at
        least the style's, drawn apart or together by the song's contrast, and the song's own where it gives one."""
        of_kind = self._of_style.get(ENERGY_OF_KIND, {})
        growth = self._given.get(GROWTH, self._of_style.get(GROWTH, USUAL_GROWTH))
        contrast = self._given.get(CONTRAST, USUAL_CONTRAST)
        kinds = [section[KIND] for section in self._sections]
        last_chorus = _last_place_of(kinds=kinds, kind=CHORUS)
        met = {}
        energies = []
        for place, kind in enumerate(kinds):
            met[kind] = met.get(kind, 0) + 1
            energy = of_kind.get(kind, USUAL_ENERGY) + growth * (met[kind] - 1)
            if place == last_chorus and met[kind] > 1:
                energy = max(energy, self._of_style.get(LAST_CHORUS, USUAL_LAST_CHORUS))
            energy = MIDDLE_ENERGY + (energy - MIDDLE_ENERGY) * contrast / USUAL_CONTRAST
            given = self.given_at(place)
            energies.append(within(given.get(wizard_names.SONG_PLAN_ENERGY, energy)))
        return energies

    def energies(self):
        """The Energy of each place of the form."""
        return list(self._energies)

    def chords_at(self, place):
        """The chords of a place of the form, as the song or the progression gives them."""
        return self._chords_of(self._sections[place])

    def joins(self):
        """Return what each place of the form leaves with, or None for a place that leaves with nothing worked out."""
        return self._section_joins.joins()

    def get_song(self):
        return self._song

    def style_plan(self):
        """Return what the genre's style says of planning a song."""
        return self._of_style

    def get_tempo(self):
        return self._tempo

    def get_scale_type(self):
        return self._scale_type

    def section_count(self):
        """Return how many places the form has."""
        return len(self._sections)

    def section_at(self, place):
        """Return the section at a place of the form, as the style and the song describe it; no caller changes it."""
        return self._sections[place]

    def energy_at(self, place):
        """Return the Energy of a place of the form."""
        return self._energies[place]

    # What follows from a section's Energy.

    def _points_of(self, instrument):
        """A player's change points: the style's, each moved a little by the song's seed, so that two songs' bands do not change together."""
        points = self._of_style.get(CHANGE_POINTS, {}).get(instrument, USUAL_CHANGE_POINTS)
        dice = random.Random(POINT_SEED.format(self._song.get(SEED, 0), instrument))
        return [points[0]] + [point + dice.choice(POINT_MOVES) for point in points[1:]]

    def _allowed(self, place):
        """Return the level each player may reach in a section, by the section's Energy."""
        pointed = self._of_style.get(CHANGE_POINTS, {})
        allows = self._sections[place].get(ALLOWS, {})
        instruments = list(dict.fromkeys([*pointed, *allows]))
        allowed = {}
        for instrument in instruments:
            felt = self._energy_felt(place=place, instrument=instrument)
            allowed[instrument] = level_at(energy=felt, points=self._points_of(instrument))
        return allowed

    def _energy_felt(self, *, place, instrument):
        """A section's Energy as one player answers to it: further from the middle for a dramatic player, nearer for an even one."""
        reacts = (self._given.get(REACTS) or {}).get(instrument, USUAL_CONTRAST)
        return within(MIDDLE_ENERGY + (self._energies[place] - MIDDLE_ENERGY) * reacts / USUAL_CONTRAST)

    def _plays(self, place):
        """Who plays in a section: the kind's players, but those who come in only at a higher Energy."""
        comes_in = self._of_style.get(COMES_IN, {})
        return [role for role in self._sections[place].get(PLAYS, []) if self._energies[place] >= comes_in.get(role, wizard_names.LOWEST_ENERGY)]

    def _cymbal(self, place):
        """The cymbal a section's Energy asks for, or nothing where the style says none."""
        chosen = None
        for energy, cymbal in self._of_style.get(CYMBALS, []):
            if self._energies[place] >= energy:
                chosen = cymbal
        return chosen

    def rises(self, place):
        """Whether a section grows louder through its bars and leaves with a build: a rising kind of the style's, or as the song says of the place."""
        return bool(self.given_at(place).get(wizard_names.SONG_PLAN_RISES, self._sections[place][KIND] in self._of_style.get(RISING, [])))

    def _loudness(self, place):
        energy = self._energies[place]
        rising = self.rises(place)
        if self.given_at(place).get(wizard_names.SONG_PLAN_FADES):
            return faded(own=self.given_at(place), loud=loudness_at(energy))
        if not rising:
            return {SCENE_VELOCITY: loudness_at(energy)}
        # A rising section climbs across all of its bars to where it arrives.
        return {SCENE_VELOCITY: loudness_at(self._arrives_at(place)), SCENE_VELOCITY_IN_START: loudness_at(energy - RISES_FROM)}

    def _arrives_at(self, place):
        """The Energy a rising section ends its climb at: that of the section it leads to where that one is higher, so that the climb arrives."""
        after = self._energies[place + 1] if place + 1 < len(self._energies) else self._energies[place]
        return max(self._energies[place], after)

    # Joins.

    def _scene_settings(self, place):
        """Return the settings of a section's scene the song gives the place: a tempo of its own, one it moves to by its end, and
        a key or a scale of its own."""
        at = self.given_at(place)
        settings = {}
        if wizard_names.TEMPO_OF_PLACE in at:
            settings[SCENE_TEMPO] = at[wizard_names.TEMPO_OF_PLACE]
        if wizard_names.TEMPO_END_OF_PLACE in at:
            settings[SCENE_TEMPO_END] = at[wizard_names.TEMPO_END_OF_PLACE]
        if wizard_names.ROOT_OF_PLACE in at or wizard_names.TYPE_OF_PLACE in at:
            key = self._song[KEY_OF_SONG]
            root = at.get(wizard_names.ROOT_OF_PLACE, key[wizard_names.ROOT_OF_PLACE])
            scale_type = at.get(wizard_names.TYPE_OF_PLACE, self._scale_type)
            settings[SCALE_OF_PLACE] = {wizard_names.ROOT_OF_PLACE: root, wizard_names.TYPE_OF_PLACE: scale_type}
        return settings

    # The song planned.

    def planned(self):
        """Return the song with a section for each place of its form, each saying what the plan worked out, and its tunes asked
        to breathe and its hook to be of a kind."""
        joins = self._section_joins.joins()
        stages = self.stages()
        hook_place = self._first_hook_place()
        sections = {}
        for place, name in enumerate(self._names):
            sections[name] = self._section_planned(place=place, joins=joins, stages=stages, hook_place=hook_place)
        song = dict(self._song)
        song[FORM] = list(self._names)
        song[SECTIONS] = sections
        song[MELODY] = self._melody_planned()
        return song

    def _section_planned(self, *, place, joins, stages, hook_place):
        """Return one section of the planned song: its kind, its stage, what the plan works out for a section the band plays
        through, the hook said, and what the song says of the section itself, which stands over what the plan worked out."""
        section = self._sections[place]
        sections_of_song = self._song.get(SECTIONS, {})
        of_song = sections_of_song.get(self._form_names[place], {})
        said = [wizard_text.MSG_PLAN_ENERGY.format(self._energies[place])]
        made = {KIND: section[KIND], DRAWN_AS: section[KIND]}
        if stages[place] is not None:
            stage, stage_plan = stages[place]
            made[SECTION_PLAN] = stage_plan
            said.append(wizard_text.MSG_PLAN_STAGE.format(stage))
        if not section.get(HELD) and not section.get(DRUM_SOLO):
            self._plan_played(made=made, said=said, place=place, joins=joins)
        if place == hook_place:
            said.append(wizard_text.MSG_PLAN_HOOK.format(self._hook_writing()[hook_writing.BEHAVIOR]))
        scene = dict(made.get(SCENE_SETTINGS, {}))
        scene.update(self._scene_settings(place))
        planned = dict(made)
        planned.update(of_song)
        planned.update(self._own_at(place))
        if scene:
            planned[SCENE_SETTINGS] = scene
        planned[SAID_OF_SECTION] = ' '.join(said)
        return planned

    def _plan_played(self, *, made, said, place, joins):
        """Add what the plan works out for a section the band plays through: who may play how much and who plays, the crash that
        starts it, its loudness, cymbal and percussion, how it leaves, and the chord it sets the next up with."""
        made[ALLOWS] = self._allowed(place)
        made[PLAYS] = self._plays(place)
        made[CRASH_START] = self._starts_on_crash(place=place, joins=joins)
        made[SCENE_SETTINGS] = self._loudness(place)
        made[PICKS] = self._picks_planned(place)
        if joins[place] is not None:
            self._plan_leaving(made=made, said=said, place=place, join=joins[place])
        last_chord = self._section_joins.last_chord(place)
        if last_chord is not None:
            made[LAST_CHORD] = last_chord
            said.append(wizard_text.MSG_PLAN_SET_UP.format(last_chord))

    def _starts_on_crash(self, *, place, joins):
        """Return whether a section starts on a crash: it arrives louder past the crash's Energy, or comes after a stop, a build
        or a drop-out, or after the drummer alone."""
        if place == 0:
            return False
        energy = self._energies[place]
        arrives = energy > self._energies[place - 1] and energy >= CRASH_FROM
        before = joins[place - 1] or {}
        after_tail = before.get(joins_values.TAIL) in (joins_values.DROP_OUT, joins_values.BUILD, joins_values.STOPS)
        after_drums = bool(self._sections[place - 1].get(DRUM_SOLO))
        return bool(arrives or after_tail or after_drums)

    def _picks_planned(self, place):
        """Return a section's picks with what the plan gives: the cymbal by Energy and the percussion from an Energy up, each
        left alone where the song chose it."""
        picks = dict(self._sections[place].get(PICKS, {}))
        song_picks = self._song.get(PICKS, {})
        # A cymbal the song chose is the drummer's all through; the plan's goes by Energy.
        if CYMBAL not in song_picks:
            cymbal = self._cymbal(place)
            if cymbal:
                picks[CYMBAL] = cymbal
        # Percussion the song chose plays all through; the kind's comes in from an Energy up, usually at the chorus.
        if PERCUSSION not in song_picks and self._energies[place] < self._of_style.get(PERCUSSION_FROM, wizard_names.LOWEST_ENERGY):
            picks[PERCUSSION] = NO_PERCUSSION
        return picks

    def _plan_leaving(self, *, made, said, place, join):
        """Add how a section leaves: its join, a small fill inside its bars and a marker where the plan has them, and what is said of the join."""
        made[wizard_names.JOINS_LEAVES] = join
        inside_every = self._section_joins.fill_inside_every(place=place)
        if inside_every and self._section_joins.fill(SMALL):
            made[FILL_INSIDE] = self._section_joins.fill(SMALL)
            made[FILL_INSIDE_EVERY] = inside_every
        marker = self._section_joins.marker(place=place)
        if marker:
            made[MARKER] = marker
            made[MARKER_EVERY] = MARKER_BARS
        if join.get(joins_values.TAIL):
            said.append(wizard_text.MSG_PLAN_LEAVES_TAIL.format(join[joins_values.TAIL]))
        elif join.get(joins_values.FILL_OF_JOIN):
            said.append(wizard_text.MSG_PLAN_LEAVES_FILL.format(join[joins_values.FILL_OF_JOIN]))

    def _hook_writing(self):
        """Return how the song's hook is written, or None."""
        melody = self._song.get(MELODY, {})
        return melody.get(wizard_names.HOOK_WRITING)

    def _first_hook_place(self):
        """Return the place of the first section whose plan says the hook, where the song writes a hook, or None."""
        if not self._hook_writing() or not self._has_hook():
            return None
        for place, section in enumerate(self._sections):
            for entry in section.get(SECTION_PLAN, []):
                if entry.get(melody_values.HOOK):
                    return place
        return None

    def _own_at(self, place):
        """Return what the song says of one place of its form that stands over the plan: all but what the plan works out from it."""
        own = {}
        for field, value in self.given_at(place).items():
            if field not in PLANNED_FROM:
                own[field] = value
        return own

    def _melody_planned(self):
        """Return what the song says of its melodies, with its tunes asked to breathe where the song's lines breathe."""
        melody = {}
        if self._given.get(PHRASING, True):
            melody[melody_values.BREATHES] = self._given.get(PHRASING_WAYS) or True
        melody.update(self._song.get(MELODY, {}))
        return melody

    def _has_hook(self):
        return bool(self._song.get(melody_values.HOOK, self._style.get(melody_values.HOOK, False)))
