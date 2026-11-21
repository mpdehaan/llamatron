# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""One player of the band, as the song wizard's choices hold the player: how the player plays, how busy, how loud, the player's gauges, rows and Musician."""

from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects.generator_settings import MusicianSetting, MusicianSettings
from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, band, loudness, melody as melody_writer, notation as tune_notation, song_plan, wizard_limits
from llamatron.wizards.create_song.arranger import fits, share_of, values_of
from llamatron.wizards.create_song.characters import gauges_of
from llamatron.wizards.create_song.loudness import drum_levels, note_levels, with_own


class PlayerChoices:
    """One player of the band, by the player's name in the genre's band. What the players of one instrument share, as a lead and a solo do their level and
    gauges, is held by the band; what is the player's alone, as the player's rows, is held by the band under the player's name. The choices make a player
    object whenever one is asked for, so that a page writes choices.player(role).set_busy(level)."""

    __slots__ = ('_choices', '_role')

    def __init__(self, *, choices, role):
        self._choices = choices
        self._role = role

    def get_role(self):
        return self._role

    def _band(self):
        return self._choices.get_band()

    def traits(self):
        """Return what is chosen about how a player plays: the one way of a player of notes, or each part of the drums."""
        entry = self._band().role_named(self._role)
        if not entry.get(arranger.DRUMS):
            return [entry[arranger.TRAIT]]
        # A break takes the place of every way the drums are played but the percussion's.
        return [trait for trait in entry[arranger.DRUMS] if self._choices.get_kit().get_break() is None or trait == arranger.KEPT_BESIDE_A_BREAK]

    def is_in(self):
        """Return whether a player is in the band: not left out, and, for a player of notes, playing in a way that sounds."""
        entry = self._band().role_named(self._role)
        return not self._band().is_left_out(self._role) and (bool(entry.get(arranger.DRUMS)) or self._choices.trait_has_sound(trait=entry[arranger.TRAIT], value=self._band().get_way(entry[arranger.TRAIT])))

    def can_play(self):
        """Return whether a player can be in the band at all: the drums always, and a player of notes where a way of playing that sounds fits the subgenre."""
        entry = self._band().role_named(self._role)
        return bool(entry.get(arranger.DRUMS)) or self.is_in() or bool(self.ways(trait=entry[arranger.TRAIT]))

    def title(self):
        """Return what a player is called on the screen: the clearer name the genre gives the player, which may follow how the
        player plays, as a lead that is a singer or a lead guitar; or the player's name where the genre gives no other."""
        entry = self._band().role_named(self._role)
        if self._band().has_one_guitarist() and self._role == self._band().one_guitarist()[wizard_limits.CHORDS_PLAYER]:
            return self._band().one_guitarist()[arranger.ROLE_TITLE]
        traits = self.traits()
        by_way = entry.get(arranger.ROLE_TITLES, {})
        way = self._band().get_way(traits[0]) if len(traits) == 1 else None
        return by_way.get(way, entry.get(arranger.ROLE_TITLE, self._role))

    def set_in(self, on):
        """Put a player in the band or leave the player out. A player whose usual way is to sit out comes in playing the commonest way that fits."""
        entry = self._band().role_named(self._role)
        if not on:
            if self._band().roles_in() == [self._role]:
                raise ValueError(errors.ERR_WIZARD_LAST_PLAYER)
            self._band().leave_out(self._role)
            return
        self._band().take_back(self._role)
        if not entry.get(arranger.DRUMS) and not self._choices.trait_has_sound(trait=entry[arranger.TRAIT], value=self._band().get_way(entry[arranger.TRAIT])):
            ways = self.ways(trait=entry[arranger.TRAIT])
            if not ways:
                raise ValueError(errors.ERR_WIZARD_NO_WAY.format(value=self._role))
            self._band().keep_way(trait=entry[arranger.TRAIT], value=ways[0])

    def ways(self, trait):
        """Return the ways a player may play a trait beside the other picks, the commonest first; for a player of notes, only ways that sound."""
        style = self._choices.style()
        drums = bool(self._band().role_named(self._role).get(arranger.DRUMS))
        picks = self._choices.picks()
        entries = [entry for entry in sorted(values_of(style=style, trait=trait).values(), key=share_of, reverse=True) if (drums or arranger.SOUND in entry) and fits(entry=entry, picks=picks)]
        return [entry[arranger.VALUE] for entry in entries if self._band().works(trait=trait, value=entry[arranger.VALUE])]

    def has_busy(self):
        """Return whether a player's busyness can be chosen: the genre says how the player's instrument is played at each level."""
        return self._band().role_named(self._role).get(arranger.PLAYER) in self._choices.style().get(arranger.PLAYERS, {})

    def get_busy(self):
        """Return how busy a player is, from LEAST_BUSY to MOST_BUSY, or None where the song names no level."""
        return self._band().instrument_level(self._band().role_named(self._role).get(arranger.PLAYER))

    def set_busy(self, level):
        """Choose how busy a player is. Players of one instrument, as a lead and a solo, share the level."""
        if not self.has_busy():
            raise ValueError(errors.ERR_WIZARD_BUSY.format(low=wizard_limits.LEAST_BUSY, high=wizard_limits.MOST_BUSY, value=level))
        self._band().take_level(player=self._band().role_named(self._role)[arranger.PLAYER], level=level)

    def _levels_of_style(self):
        """The four levels the genre gives a player: the whole kit's for the drummer, and a player of notes' from the player's velocity."""
        entry = self._band().role_named(self._role)
        if entry.get(arranger.DRUMS):
            return drum_levels(self._choices.style()[arranger.LOUDNESS][arranger.DRUMS])
        return note_levels(entry[tune_notation.VELOCITY])

    def has_loudness(self):
        """Return whether a player has levels to choose: a player in the band who drums or plays notes at a velocity."""
        return self._choices.is_ready() and self._role in self._band().roles() and self.is_in() and (bool(self._band().role_named(self._role).get(arranger.DRUMS)) or tune_notation.VELOCITY in self._band().role_named(self._role))

    def loudness_levels(self):
        """Return a player's four levels by name, the genre's with the song's own in their places; the drummer's are the whole kit's,
        which every piece of the kit follows in proportion."""
        return with_own(levels=self._levels_of_style(), own=(self._choices.get_extra(arranger.LOUDNESS) or {}).get(self._role))

    def loudness_level_is_own(self, level):
        return level in (self._choices.get_extra(arranger.LOUDNESS) or {}).get(self._role, {})

    def loudness_levels_offered(self):
        """Return the levels of a player that the song plays, from the quietest up: a level no note of the player's is played at is
        not offered. Found by making the song with each level moved, and kept until a choice changes."""
        if not self.has_loudness():
            return []
        return self._choices.offered(key=(wizard_limits.LEVELS_ANSWER, self._role), compute=lambda: self._levels_heard())

    def _levels_heard(self):
        plain = self._parts_as_written()
        heard = []
        for level in loudness.LEVELS:
            trial = self._choices.copied_for_trial()
            now = trial.player(self._role).loudness_levels()[level]
            tried = now - wizard_limits.LEVEL_TRIAL if now > wizard_limits.MIDDLE_VELOCITY else now + wizard_limits.LEVEL_TRIAL
            of_players = dict(trial.get_extra(arranger.LOUDNESS) or {})
            trial.set_extra(name=arranger.LOUDNESS, value={**of_players, self._role: {**of_players.get(self._role, {}), level: tried}})
            # The player's dynamics as written, so that a level is heard apart from the normal one.
            trial.set_extra(name=arranger.DYNAMICS, value={player: dynamics for player, dynamics in (trial.get_extra(arranger.DYNAMICS) or {}).items() if player != self._role} or None)
            if trial.patterns_of_song() != plain:
                heard.append(level)
        return heard

    def _parts_as_written(self):
        """The song's parts with a player's dynamics as the genre writes them."""
        trial = self._choices.copied_for_trial()
        trial.set_extra(name=arranger.DYNAMICS, value={player: dynamics for player, dynamics in (trial.get_extra(arranger.DYNAMICS) or {}).items() if player != self._role} or None)
        return trial.patterns_of_song()

    def set_loudness_level(self, *, level, number):
        """Give a player a level of the song's own, a velocity, or give the level back to the genre with None."""
        is_number = number is None or (isinstance(number, int) and not isinstance(number, bool) and tune_notation.LOWEST_VELOCITY <= number <= tune_notation.HIGHEST_VELOCITY)
        if not self.has_loudness() or level not in loudness.LEVELS or not is_number:
            raise ValueError(errors.ERR_WIZARD_LOUDNESS.format(low=tune_notation.LOWEST_VELOCITY, high=tune_notation.HIGHEST_VELOCITY, value=(self._role, level, number)))
        of_players = {player: dict(levels) for player, levels in (self._choices.get_extra(arranger.LOUDNESS) or {}).items()}
        own = of_players.setdefault(self._role, {})
        own.pop(level, None)
        if number is not None and number != self._levels_of_style()[level]:
            own[level] = number
        of_players = {player: levels for player, levels in of_players.items() if levels}
        self._choices.set_extra(name=arranger.LOUDNESS, value=of_players or None)
        self._choices.clear_answers()

    def has_dynamics(self):
        """Return whether a player's dynamics are heard: whether the song differs with the player's notes all alike and at their widest,
        found by making the song both ways and kept until a choice changes."""
        if not self.has_loudness():
            return False
        return self._choices.offered(key=(wizard_limits.DYNAMICS_ANSWER, self._role), compute=lambda: self._dynamics_are_heard())

    def _dynamics_are_heard(self):
        made = []
        for dynamics in (loudness.LEAST_DYNAMICS, loudness.MOST_DYNAMICS):
            trial = self._choices.copied_for_trial()
            trial.set_extra(name=arranger.DYNAMICS, value={**(trial.get_extra(arranger.DYNAMICS) or {}), self._role: dynamics})
            made.append(trial.patterns_of_song())
        return made[0] != made[1]

    def get_dynamics(self):
        return (self._choices.get_extra(arranger.DYNAMICS) or {}).get(self._role, loudness.USUAL_DYNAMICS)

    def set_dynamics(self, dynamics):
        """Say how far a player's loud and soft notes lie from the player's normal ones: not at all at the least, as the genre writes them
        in the middle, and twice as far at the most."""
        if not self.has_loudness() or isinstance(dynamics, bool) or not isinstance(dynamics, int) or not loudness.LEAST_DYNAMICS <= dynamics <= loudness.MOST_DYNAMICS:
            raise ValueError(errors.ERR_WIZARD_DYNAMICS.format(low=loudness.LEAST_DYNAMICS, high=loudness.MOST_DYNAMICS, value=dynamics))
        of_players = dict(self._choices.get_extra(arranger.DYNAMICS) or {})
        of_players.pop(self._role, None)
        if dynamics != loudness.USUAL_DYNAMICS:
            of_players[self._role] = dynamics
        self._choices.set_extra(name=arranger.DYNAMICS, value=of_players or None)
        self._choices.clear_answers()

    def plays_lines(self):
        entry = self._band().role_named(self._role)
        return arranger.FIGURE not in values_of(style=self._choices.style(), trait=entry[arranger.TRAIT])[self._band().get_way(entry[arranger.TRAIT])]

    def gauges(self):
        """Return the gauges a player has: those the genre's levels of the player's instrument say anything by."""
        if not self.has_busy():
            return []
        return gauges_of(self._choices.style()[arranger.PLAYERS][self._band().role_named(self._role)[arranger.PLAYER]])

    def get_gauge(self, gauge):
        """Return where a gauge of a player stands, from the lowest place to the highest."""
        if gauge not in self.gauges():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER_GAUGE.format(value=gauge))
        return self._band().character(self._band().role_named(self._role)[arranger.PLAYER])[gauge]

    def set_gauge(self, *, gauge, place):
        """Move a gauge of a player. Players of one instrument, as a lead and a solo, share their gauges."""
        if gauge not in self.gauges():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER_GAUGE.format(value=gauge))
        self._band().take_kept_player_gauge(player=self._band().role_named(self._role)[arranger.PLAYER], gauge=gauge, place=place)

    def preset(self):
        """Return the level of the preset a player is, or None for a player whose gauges were moved from it."""
        return self._band().instrument_preset(self._band().role_named(self._role).get(arranger.PLAYER))

    def rows(self):
        """Return the rows of numbers a player's notes are dealt, by name, while the song's tunes are written in the serial style
        and the player plays lines of the tune in some section of the form; none otherwise."""
        if not self._choices.is_ready() or self._choices.melody_engine() != melody_writer.SERIAL or not self._choices.get_sounds().has_sound(self._role) or not self.plays_lines():
            return []
        # A player who plays in no section of the song's form is dealt nothing, so has no row to change.
        if not any(self._role in self._choices.section(place).plays() for place in range(len(self._choices.get_song_form().section_entries()))):
            return []
        return list(wizard_limits.PLAYER_ROWS)

    def genre_row(self, name):
        """Return a player's row as the genre gives it, or the row that plays as none would."""
        habits = {**self._choices.melody_habits(), **self._band().role_named(self._role).get(arranger.HABITS, {})}
        return list(habits.get(name) or wizard_limits.ROWS_UNASKED[name])

    def get_row(self, name):
        """Return a player's row as the song will deal it: the player's own, or the genre's for the player."""
        if name not in self.rows():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ROW.format(value=name))
        return list(self._band().own_row_of(role=self._role, name=name) or self.genre_row(name=name))

    def row_is_own(self, name):
        """Return whether a player's row was changed from the genre's."""
        return self._band().own_row_of(role=self._role, name=name) is not None

    def set_row(self, *, name, values):
        """Give a player a row of the player's own; the genre's own row given back is no row of the player's."""
        if name not in self.rows():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ROW.format(value=name))
        low, high = wizard_limits.ROW_LIMITS[name]
        if not isinstance(values, (list, tuple)) or not wizard_limits.FEWEST_ROW_CELLS <= len(values) <= wizard_limits.MOST_ROW_CELLS or any(
                isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high for value in values):
            raise ValueError(errors.ERR_WIZARD_ROW.format(name=name, low=low, high=high, fewest=wizard_limits.FEWEST_ROW_CELLS, most=wizard_limits.MOST_ROW_CELLS, value=values))
        if list(values) == self.genre_row(name=name):
            self.clear_row(name=name)
        else:
            self._band().keep_row(role=self._role, name=name, values=list(values))

    def clear_row(self, name):
        """Give a player's row back to the genre."""
        self._band().keep_row(role=self._role, name=name, values=None)

    def musician_name(self):
        """Return what the Musician of a player is called in the song made."""
        return band.musician_name(self._role)

    def get_musician(self):
        """Return the settings of the Musician the person gave a player, or None where the player has the one players are given."""
        own = (self._choices.get_extra(arranger.MUSICIANS) or {}).get(self._role)
        return None if own is None else dict(own)

    def set_musician(self, settings):
        """Give a player a Musician of the person's own, its settings by name, or None for the one players are given. The tracks the
        Musician reads are the song's to say and are not kept. Settings no Musician has, or values a setting cannot take, are refused."""
        kept = dict(self._choices.get_extra(arranger.MUSICIANS) or {})
        if settings is None:
            kept.pop(self._role, None)
        else:
            try:
                given = {name: value for name, value in dict(settings).items() if name not in (MusicianSetting.TUNE_FROM, MusicianSetting.CHORDS_FROM)}
                kept[self._role] = MusicianSettings.handed_over(data=given, where=band.musician_name(self._role)).to_data()
            except (SongFileError, TypeError, ValueError) as problem:
                raise ValueError(errors.ERR_WIZARD_MUSICIAN.format(value=settings, problem=problem)) from None
        self._choices.set_extra(name=arranger.MUSICIANS, value=kept or None)
        self._choices.clear_answers()

    def get_octave(self):
        """Return the octave the player plays in."""
        return self._band().role_named(self._role).get(tune_notation.OCTAVE, wizard_limits.USUAL_OCTAVE)

    # The player as a person in the band: how strongly the player answers to Energy, where the player comes in and where the player lays out.

    def _person(self):
        """The player's name in the genre's band, which two roles played by one person, as a singer who also plays, share."""
        return self._band().role_named(self._role)[arranger.PLAYER]

    def reacts(self):
        """Return whether the player answers to Energy more or less than the band: a player of a planned song whose playing the plan holds back or lets go,
        which is found by making the song with the player even and dramatic, and kept until a choice changes."""
        if not (self._choices.has_song_plan() and self.is_in() and arranger.PLAYER in self._band().role_named(self._role)):
            return False
        return self._choices.offered(key=(wizard_limits.REACTS_ANSWER, self._person()), compute=self._reacts_is_heard)

    def _reacts_is_heard(self):
        made = []
        for reacts in (song_plan.LOWEST_ENERGY, song_plan.HIGHEST_ENERGY):
            trial = self._choices.copied_for_trial()
            trial.plan_extras()[song_plan.REACTS] = {**(trial.plan_extras().get(song_plan.REACTS) or {}), self._person(): reacts}
            made.append(trial.patterns_of_song())
        return made[0] != made[1]

    def get_reacts(self):
        return (self._choices.plan_extras().get(song_plan.REACTS) or {}).get(self._person(), song_plan.USUAL_CONTRAST)

    def set_reacts(self, reacts):
        """Have the player answer to Energy evenly, at the lowest, or dramatically, at the highest. Two players who are one person answer alike."""
        if not self.reacts() or isinstance(reacts, bool) or not isinstance(reacts, int) or not song_plan.LOWEST_ENERGY <= reacts <= song_plan.HIGHEST_ENERGY:
            raise ValueError(errors.ERR_WIZARD_REACTS.format(low=song_plan.LOWEST_ENERGY, high=song_plan.HIGHEST_ENERGY, value=reacts))
        extras = self._choices.plan_extras()
        kept = dict(extras.get(song_plan.REACTS) or {})
        kept.pop(self._person(), None)
        if reacts != song_plan.USUAL_CONTRAST:
            kept[self._person()] = reacts
        extras.pop(song_plan.REACTS, None)
        if kept:
            extras[song_plan.REACTS] = kept
        self._choices.clear_answers()

    def comes_in_offered(self):
        """Return the ways the player may come in, where the song has sections and the player is in the band."""
        return list(self._choices.comes_in_places()) if self._choices.is_ready() and self.is_in() else []

    def _plays_at(self):
        """The places of the form's sections the player plays in."""
        return [place for place in range(self._choices.section_count()) if self._role in self._choices.section(place).plays()]

    def _first_place(self):
        return next(iter(self._plays_at()), None)

    def get_comes_in(self):
        """Return the way the player comes in, or None where the player's first section is none of the ways' or the player plays nowhere."""
        first = self._first_place()
        return next((way for way, place in self._choices.comes_in_places().items() if place == first), None)

    def _laid_out(self, *, way, first):
        """Which sections the player plays under a way of laying out, from the player's first section on: never is every section the genre gives the player any part in."""
        out = {wizard_limits.NEVER_LAYS_OUT: [], wizard_limits.IN_BREAKDOWNS: self._choices.breakdown_places(), wizard_limits.WHEN_QUIET: self._choices.quiet_places()}[way]
        return [place for place in range(first, self._choices.section_count()) if place == first or (place not in out and (not self._choices.section(place).is_held() or self._usually_plays(place)))]

    def _usually_plays(self, place):
        return self._role in self._choices.section(place).usual().get(arranger.PLAYS, [])

    def lays_out_offered(self):
        """Return the ways the player may lay out: never, only in the breakdowns where the form has one, and whenever it is quiet in a planned song with a quiet section."""
        if not self.comes_in_offered() or self._first_place() is None:
            return []
        return [wizard_limits.NEVER_LAYS_OUT, *([wizard_limits.IN_BREAKDOWNS] if self._choices.breakdown_places() else []), *([wizard_limits.WHEN_QUIET] if self._choices.quiet_places() else [])]

    def get_lays_out(self):
        """Return the way the player lays out, or None where the sections the player plays are none of the ways'."""
        first = self._first_place()
        plays = self._plays_at()
        return next((way for way in self.lays_out_offered() if self._laid_out(way=way, first=first) == plays), None)

    def set_comes_in(self, way):
        """Have the player come in at a place of the form and sit out every section before it; the sections after are left as they are."""
        if way not in self.comes_in_offered():
            raise ValueError(errors.ERR_WIZARD_COMES_IN.format(value=way))
        first = self._choices.comes_in_places()[way]
        plays = [place for place in range(first, self._choices.section_count()) if place == first or self._role in self._choices.section(place).plays()]
        self._choices.set_plays_of(role=self._role, plays=plays)

    def set_lays_out(self, way):
        """Have the player lay out never, only in the breakdowns, or whenever it is quiet, from the player's first section on."""
        if way not in self.lays_out_offered():
            raise ValueError(errors.ERR_WIZARD_LAYS_OUT.format(value=way))
        self._choices.set_plays_of(role=self._role, plays=self._laid_out(way=way, first=self._first_place()))
