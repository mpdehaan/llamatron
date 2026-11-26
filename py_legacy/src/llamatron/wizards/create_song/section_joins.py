# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How each section of a planned song leaves for the next: a stop, a build, the song's one drop-out or a fill, the chord its
last bar sets the next up with, and the drummer's fills inside a section and the markers its phrases end on."""

from llamatron.music_theory.composing import joins as joins_values
from llamatron.wizards.create_song import song_plan, wizard_names


class SectionJoins:
    """The joins of a planned song, worked out by its plan: what each section leaves with, by what follows, how far the Energy
    moves and what was done last, and the fills the song's drummer plays. Made by the song's plan, which it asks of its sections."""

    __slots__ = ('_plan', '_song', '_of_style')

    def __init__(self, *, plan):
        self._plan = plan
        self._song = plan.get_song()
        self._of_style = plan.style_plan()

    def joins(self):
        """Return what each section leaves with, the song's own join where it gives one, and None for a section no join is
        worked out for."""
        allowed = self._plan.for_subgenre(field=song_plan.TAILS_ALLOWED, default=(joins_values.DROP_OUT, joins_values.STOPS, joins_values.BUILD))
        last_chorus = self._last_choruses_start()
        joins = []
        before = {}
        dropped = False
        for place in range(self._plan.section_count()):
            if not self.stays(place):
                joins.append(None)
                continue
            join = self._planned_join(place=place, allowed=allowed, last_chorus=last_chorus, before=before, dropped=dropped)
            if join.get(joins_values.TAIL) == joins_values.DROP_OUT:
                dropped = True
            if wizard_names.JOINS_LEAVES in self._plan.given_at(place):
                # A join the song gives is the whole join, and a drop-out with no length takes the tempo's.
                join = self._given_join(place)
            joins.append(join)
            before = join
        return joins

    def stays(self, place):
        """Return whether a section is one a join is worked out for: played by the band, with a section after it."""
        section = self._plan.section_at(place)
        return place < self._plan.section_count() - 1 and not section.get(song_plan.HELD) and not section.get(song_plan.DRUM_SOLO)

    def _planned_join(self, *, place, allowed, last_chorus, before, dropped):
        """Return the join the plan works out for a section: a stop before the drummer alone, the song's one drop-out before
        the last chorus, a build where the section rises, else a fill as big as the rise, never the same twice running."""
        following = self._plan.section_at(place + 1)
        if following.get(song_plan.DRUM_SOLO) and joins_values.STOPS in allowed:
            return {joins_values.TAIL: joins_values.STOPS}
        into_last_chorus = place + 1 == last_chorus
        section = self._plan.section_at(place)
        if into_last_chorus and section[song_plan.KIND] != song_plan.CHORUS and joins_values.DROP_OUT in allowed and not dropped:
            # The one silence of the song: the band stops for about a second, and the last chorus comes in whole.
            return {joins_values.TAIL: joins_values.DROP_OUT, joins_values.TAIL_EIGHTHS: self._drop_eighths()}
        if self._plan.rises(place) and joins_values.BUILD in allowed and before.get(joins_values.TAIL) != joins_values.BUILD:
            return {joins_values.TAIL: joins_values.BUILD}
        if following.get(song_plan.HELD):
            return {}
        rise = self._plan.energy_at(place + 1) - self._plan.energy_at(place)
        size = _fill_size(rise=rise, into_last_chorus=into_last_chorus)
        if before.get(joins_values.FILL_OF_JOIN) == self.fill(size):
            size = song_plan.OTHER_SIZE[size]
        fill = self.fill(size)
        if not fill:
            return {}
        return {joins_values.FILL_OF_JOIN: fill}

    def _drop_eighths(self):
        """Return how many eighths the song's drop-out lasts: about a second, so fewer at a slow tempo."""
        if self._plan.get_tempo() >= song_plan.FAST_TEMPO:
            return song_plan.DROP_EIGHTHS_FAST
        return song_plan.DROP_EIGHTHS_SLOW

    def _given_join(self, place):
        """Return the join the song gives a section, with its fill by size and a drop-out's length the tempo's where none is given."""
        given = self._plan.given_at(place)
        join = dict(given[wizard_names.JOINS_LEAVES] or {})
        if song_plan.FILL_SIZE in join:
            size = join.pop(song_plan.FILL_SIZE)
            if self.fill(size):
                join[joins_values.FILL_OF_JOIN] = self.fill(size)
        if join.get(joins_values.TAIL) == joins_values.DROP_OUT and joins_values.TAIL_EIGHTHS not in join:
            join[joins_values.TAIL_EIGHTHS] = self._drop_eighths()
        return join

    def _last_choruses_start(self):
        """Return the place of the first of the choruses the song ends with, or nothing for a song with no chorus."""
        places = []
        for place in range(self._plan.section_count()):
            section = self._plan.section_at(place)
            if section[song_plan.KIND] == song_plan.CHORUS:
                places.append(place)
        if not places:
            return None
        start = places[-1]
        while start - 1 in places:
            start -= 1
        return start

    def last_chord(self, place):
        """Return the chord a section's last bar takes to set up the next, or nothing: a section that rises into one starting
        at home, or that would sit on home into home, ends on the approach chord, where the subgenre sets joins up at all."""
        if not self.stays(place) or not self._sets_up(place):
            return None
        following = self._plan.section_at(place + 1)
        if following.get(song_plan.HELD) or following.get(song_plan.DRUM_SOLO):
            return None
        last = self._plan.chords_at(place)[-1]
        first = self._plan.chords_at(place + 1)[0]
        approach = song_plan.APPROACH
        if self._plan.get_scale_type() == song_plan.MINOR:
            approach = song_plan.APPROACH_IN_MINOR
        at_home = first.get(song_plan.DEGREE) == song_plan.HOME and song_plan.ACCIDENTAL not in first
        rises = self._plan.energy_at(place + 1) > self._plan.energy_at(place)
        if not at_home or last.get(song_plan.DEGREE) == approach or not (rises or last.get(song_plan.DEGREE) == song_plan.HOME):
            return None
        return approach

    def _sets_up(self, place):
        """Return whether a section may set the next up: the song does not say not at all there, and the subgenre sets joins up."""
        given = self._plan.given_at(place)
        if given.get(wizard_names.SONG_PLAN_SETUP) == wizard_names.NOT_AT_ALL:
            return False
        return self._song.get(song_plan.TEMPLATE) not in self._of_style.get(song_plan.NO_SETUP, [])

    def fill(self, size):
        """Return the fill of a size: the style's, unless the song chose its fill, which is then the fill of every size, or
        chose none, or asked for no fills at all."""
        if self._song.get(song_plan.FILLS_COME) == song_plan.NO_FILLS:
            return None
        picks = self._song.get(song_plan.PICKS, {})
        chosen = picks.get(song_plan.FILLS_TRAIT)
        if chosen == song_plan.NO_FILL:
            return None
        if chosen is not None:
            return chosen
        fills = self._of_style.get(song_plan.FILL_SIZES, {})
        return fills.get(size)

    def fill_inside_every(self, *, place):
        """Return how many bars apart the fills inside a section come, or nothing for none: as the song asks, and otherwise
        every four bars of a long section from an Energy up."""
        section = self._plan.section_at(place)
        bars = section.get(song_plan.BARS, 0)
        asked = self._song.get(song_plan.FILLS_COME)
        if asked is not None:
            if isinstance(asked, int) and 0 < asked < bars:
                return asked
            return None
        if bars > song_plan.FILL_INSIDE_BARS and self._plan.energy_at(place) >= song_plan.FILL_INSIDE_FROM:
            return song_plan.FILL_INSIDE_BARS
        return None

    def marker(self, *, place):
        """Return the marker the section's phrases end on, or nothing: the style's, in a section longer than a phrase, unless
        the song says how often its fills come, chose its fill or asked for none."""
        picks = self._song.get(song_plan.PICKS, {})
        if self._song.get(song_plan.FILLS_COME) is not None or picks.get(song_plan.FILLS_TRAIT) is not None:
            return None
        section = self._plan.section_at(place)
        if section.get(song_plan.BARS, 0) > song_plan.MARKER_BARS:
            return self._of_style.get(song_plan.MARKER)
        return None


def _fill_size(*, rise, into_last_chorus):
    """Return how big a fill leads into the next section: the biggest into the last chorus or a big rise, middling into any
    rise, and small otherwise."""
    if rise >= song_plan.BIG_RISE or into_last_chorus:
        return song_plan.BIG
    if rise > 0:
        return song_plan.MEDIUM
    return song_plan.SMALL
