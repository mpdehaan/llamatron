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

"""The song wizard's choices of the band: who plays, how each plays and how busy each is, the player who answers the tune, a player's gauges, rows, loudness and Musician, and one guitarist or two."""

from llamatron.composition.generator_settings import MusicianSetting, MusicianSettings
from llamatron.composition.song_file_error import SongFileError
from llamatron.macro_composer import arranger, band, characters, interplay as interplay_values, loudness, melody as melody_writer, notation as tune_notation, wizard_limits
from llamatron.macro_composer.arranger import fits, share_of, values_of
from llamatron.macro_composer.characters import gauges_of, preset
from llamatron.macro_composer.choices_part import ChoicesPart
from llamatron.macro_composer.loudness import drum_levels, note_levels, with_own
from llamatron.strings import errors


class BandChoices(ChoicesPart):
    """What was chosen of the band: each trait's way of playing where one was chosen, how busy each instrument's player is, the gauges and rows a player was given, the players left out, who answers the tune, and how many guitarists."""

    __slots__ = ('_ways', '_levels', '_own_gauges', '_rows', '_beside', '_without', '_guitarists')

    def __init__(self, *, choices):
        ChoicesPart.__init__(self, choices=choices)
        self.reset()

    def reset(self):
        """Go back to a band with nothing chosen: no way of playing, no level, nobody left out, two guitarists."""
        # Each trait's way of playing where one was chosen, how busy each instrument's player is, and the players left out.
        self._ways = {}
        self._without = []
        # How many guitarists the band has: two, one for the chords and one for the solo, or one who plays both.
        self._guitarists = wizard_limits.TWO_GUITARISTS
        self.forget_players()

    def forget_players(self):
        """Forget how busy each player is, the gauges and rows each was given, and who answers the tune."""
        self._levels = {}
        self._own_gauges = {}
        self._rows = {}
        self._beside = None

    def take_usual(self):
        """Take the band the subgenre usually has: each player at the usual level, with no gauge or row of the player's own, and the usual player beside the tune."""
        self._levels = {player: wizard_limits.USUAL_BUSY for player in self._choices.style().get(arranger.PLAYERS, {})}
        self._own_gauges = {}
        self._rows = {}
        self._beside = self.usual_beside()

    # What a song keeps of the band.

    def to_data(self):
        """Return what a song keeps of the band, as plain data: only what was chosen."""
        held = {arranger.PICKS: dict(self._ways) or None, arranger.PLAYERS: dict(self._levels) or None, arranger.WITHOUT: list(self._without) or None,
                wizard_limits.PLAYER_GAUGES_KEPT: {player: dict(places) for player, places in self._own_gauges.items() if places} or None,
                wizard_limits.PLAYER_ROWS_KEPT: {role: {name: list(row) for name, row in rows.items()} for role, rows in self._rows.items() if rows} or None,
                wizard_limits.BESIDE_KEPT: dict(self._beside) if self._beside is not None else None,
                wizard_limits.GUITARISTS_KEPT: self._guitarists if self._guitarists != wizard_limits.TWO_GUITARISTS else None}
        return {field: value for field, value in held.items() if value is not None}

    def counted(self):
        """Return every setting of the band, each under a name of its own, so that two bands can be compared setting by setting."""
        by_name = {(wizard_limits.GENRE_SETTING, name): value for name, value in (
            (wizard_limits.BESIDE_KEPT, self._beside), (arranger.WITHOUT, sorted(self._without)), (wizard_limits.GUITARISTS_KEPT, self._guitarists))}
        for kept_as, held in ((arranger.PICKS, self._ways), (arranger.PLAYERS, self._levels), (wizard_limits.PLAYER_GAUGES_KEPT, self._own_gauges), (wizard_limits.PLAYER_ROWS_KEPT, self._rows)):
            for name, value in held.items():
                if isinstance(value, dict):
                    by_name.update({(kept_as, name, inner): each for inner, each in value.items()})
                else:
                    by_name[(kept_as, name)] = value
        return by_name

    def get_ways(self):
        """Return each trait's way of playing where one was chosen, as held and not to be changed."""
        return self._ways

    def forget_way(self, trait):
        """Leave a trait's way of playing to the subgenre again."""
        self._ways.pop(trait, None)

    def role_named(self, role):
        found = next((entry for entry in self._choices.style()[arranger.ROLES] if entry[arranger.ROLE] == role), None) if self._choices.is_ready() else None
        if found is None:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER.format(value=role))
        return found

    def roles(self):
        """Return the players the genre's band may have, by name, in the genre's order."""
        return [entry[arranger.ROLE] for entry in self._choices.style()[arranger.ROLES]] if self._choices.is_ready() else []

    def role_traits(self, role):
        """Return what is chosen about how a player plays: the one way of a player of notes, or each part of the drums."""
        entry = self.role_named(role)
        if not entry.get(arranger.DRUMS):
            return [entry[arranger.TRAIT]]
        # A break takes the place of every way the drums are played but the percussion's.
        return [trait for trait in entry[arranger.DRUMS] if self._choices.get_kit().get_break() is None or trait == arranger.KEPT_BESIDE_A_BREAK]

    def role_is_in(self, role):
        """Return whether a player is in the band: not left out, and, for a player of notes, playing in a way that sounds."""
        entry = self.role_named(role)
        return role not in self._without and (bool(entry.get(arranger.DRUMS)) or self._choices.trait_has_sound(trait=entry[arranger.TRAIT], value=self.get_way(entry[arranger.TRAIT])))

    def role_can_play(self, role):
        """Return whether a player can be in the band at all: the drums always, and a player of notes where a way of playing that sounds fits the subgenre."""
        entry = self.role_named(role)
        return bool(entry.get(arranger.DRUMS)) or self.role_is_in(role) or bool(self.ways(role=role, trait=entry[arranger.TRAIT]))

    def role_title(self, role):
        """Return what a player is called on the screen: the clearer name the genre gives the player, which may follow how the
        player plays, as a lead that is a singer or a lead guitar; or the player's name where the genre gives no other."""
        entry = self.role_named(role)
        if self.has_one_guitarist() and role == self._one_guitarist()[wizard_limits.CHORDS_PLAYER]:
            return self._one_guitarist()[arranger.ROLE_TITLE]
        traits = self.role_traits(role)
        by_way = entry.get(arranger.ROLE_TITLES, {})
        way = self.get_way(traits[0]) if len(traits) == 1 else None
        return by_way.get(way, entry.get(arranger.ROLE_TITLE, role))

    # One guitarist or two: a band whose one guitarist plays the chords and takes the solo, the chords
    # stopping where the solo plays, shown as one player.

    def _one_guitarist(self):
        return self._choices.style().get(wizard_limits.ONE_GUITARIST) if self._choices.is_ready() else None

    def offers_one_guitarist(self):
        """Return whether the band can have one guitarist: the genre says which two players the one would be, and the solo can be a guitar's."""
        one = self._one_guitarist()
        return bool(one) and self.role_can_play(one[wizard_limits.CHORDS_PLAYER]) and one[wizard_limits.SOLO_WAY] in self.ways(role=one[wizard_limits.SOLO_PLAYER], trait=self.role_named(one[wizard_limits.SOLO_PLAYER])[arranger.TRAIT])

    def get_guitarists(self):
        return self._guitarists

    def has_one_guitarist(self):
        return self._guitarists == wizard_limits.ONE_GUITARIST_COUNT

    def set_guitarists(self, count):
        """Choose two guitarists or one. One guitarist takes the solo on the guitar, whatever took it before."""
        if isinstance(count, bool) or count not in wizard_limits.GUITARIST_COUNTS or (count == wizard_limits.ONE_GUITARIST_COUNT and not self.offers_one_guitarist()):
            raise ValueError(errors.ERR_WIZARD_GUITARISTS.format(value=count))
        self._guitarists = count
        if count == wizard_limits.ONE_GUITARIST_COUNT:
            one = self._one_guitarist()
            if one[wizard_limits.SOLO_PLAYER] in self._without:
                self._without.remove(one[wizard_limits.SOLO_PLAYER])
            self._ways[self.role_named(one[wizard_limits.SOLO_PLAYER])[arranger.TRAIT]] = one[wizard_limits.SOLO_WAY]

    def take_kept_guitarists(self, *, count):
        self.set_guitarists(count)

    def roles_shown(self):
        """Return the players the screen shows: every player, but for the player of the solo where one guitarist plays both."""
        hidden = self._one_guitarist()[wizard_limits.SOLO_PLAYER] if self.has_one_guitarist() else None
        return [role for role in self.roles() if role != hidden]

    def without_of_song(self):
        """Return the players the song leaves out: those left out, and with them the solo of one guitarist who is left out."""
        without = list(self._without)
        if self.has_one_guitarist():
            one = self._one_guitarist()
            if one[wizard_limits.CHORDS_PLAYER] in without and one[wizard_limits.SOLO_PLAYER] not in without:
                without.append(one[wizard_limits.SOLO_PLAYER])
        return without

    def plays_of_one_guitarist(self, plays):
        """Return who plays in a section where one guitarist plays both parts: the chords stop where the solo plays."""
        one = self._one_guitarist()
        if self.has_one_guitarist() and one[wizard_limits.SOLO_PLAYER] in plays and one[wizard_limits.CHORDS_PLAYER] in plays:
            return [role for role in plays if role != one[wizard_limits.CHORDS_PLAYER]]
        return None

    def roles_in(self):
        return [role for role in self.roles() if self.role_is_in(role)]

    def set_role_in(self, *, role, on):
        """Put a player in the band or leave the player out. A player whose usual way is to sit out comes in playing the commonest way that fits."""
        entry = self.role_named(role)
        if not on:
            if self.roles_in() == [role]:
                raise ValueError(errors.ERR_WIZARD_LAST_PLAYER)
            if role not in self._without:
                self._without.append(role)
            return
        if role in self._without:
            self._without.remove(role)
        if not entry.get(arranger.DRUMS) and not self._choices.trait_has_sound(trait=entry[arranger.TRAIT], value=self.get_way(entry[arranger.TRAIT])):
            ways = self.ways(role=role, trait=entry[arranger.TRAIT])
            if not ways:
                raise ValueError(errors.ERR_WIZARD_NO_WAY.format(value=role))
            self._ways[entry[arranger.TRAIT]] = ways[0]

    def _works(self, *, trait, value):
        """Return whether a way of playing can be chosen beside the other picks, some ways needing a meter or a feel."""
        try:
            self._choices.picks_with({**self._ways, trait: value})
        except ValueError:
            return False
        return True

    def ways(self, *, role, trait):
        """Return the ways a player may play a trait beside the other picks, the commonest first; for a player of notes, only ways that sound."""
        style = self._choices.style()
        drums = bool(self.role_named(role).get(arranger.DRUMS))
        picks = self._choices.picks()
        entries = [entry for entry in sorted(values_of(style=style, trait=trait).values(), key=share_of, reverse=True) if (drums or arranger.SOUND in entry) and fits(entry=entry, picks=picks)]
        return [entry[arranger.VALUE] for entry in entries if self._works(trait=trait, value=entry[arranger.VALUE])]

    # What the whole song has a way of: its chords, its feel and its drum fills, each a trait of the genre no one player owns.

    def song_trait(self, traits):
        """Return the first of some traits the genre has that no player owns, as chords under either name a genre gives them, or None."""
        if not self._choices.is_ready():
            return None
        of_players = {trait for role in self.roles() for trait in self.role_traits(role)}
        return next((trait for trait in traits if trait not in of_players and isinstance(self._choices.style()[arranger.TRAITS].get(trait), list)), None)

    def song_ways(self, trait):
        """Return the ways a trait of the whole song may go beside the other picks, the commonest first."""
        entries = sorted(values_of(style=self._choices.style(), trait=trait).values(), key=self._choices.share_in_subgenre, reverse=True)
        return [entry[arranger.VALUE] for entry in entries if self._works(trait=trait, value=entry[arranger.VALUE])]

    def get_way(self, trait):
        return self._choices.picks()[trait]

    def set_way(self, *, trait, value):
        if not self._choices.is_ready() or value not in values_of(style=self._choices.style(), trait=trait) or not self._works(trait=trait, value=value):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY.format(trait=trait, value=value))
        self._ways[trait] = value

    def has_busy(self, role):
        """Return whether a player's busyness can be chosen: the genre says how the player's instrument is played at each level."""
        return self.role_named(role).get(arranger.PLAYER) in self._choices.style().get(arranger.PLAYERS, {})

    def get_busy(self, role):
        """Return how busy a player is, from LEAST_BUSY to MOST_BUSY, or None where the song names no level."""
        return self._levels.get(self.role_named(role).get(arranger.PLAYER))

    def set_busy(self, *, role, level):
        """Choose how busy a player is. Players of one instrument, as a lead and a solo, share the level."""
        if not self.has_busy(role):
            raise ValueError(errors.ERR_WIZARD_BUSY.format(low=wizard_limits.LEAST_BUSY, high=wizard_limits.MOST_BUSY, value=level))
        self.take_level(player=self.role_named(role)[arranger.PLAYER], level=level)

    def take_level(self, *, player, level):
        if isinstance(level, bool) or not isinstance(level, int) or level not in self._choices.style().get(arranger.PLAYERS, {}).get(player, {}):
            raise ValueError(errors.ERR_WIZARD_BUSY.format(low=wizard_limits.LEAST_BUSY, high=wizard_limits.MOST_BUSY, value=level))
        self._levels[player] = level
        # A preset chosen puts every gauge of the player back where the preset has it.
        self._own_gauges.pop(player, None)

    # How loud a player is: four named levels, a ghost note, a soft note, a normal note and an accent, and the player's dynamics,
    # how far the levels lie from the normal one.

    def _levels_of_style(self, role):
        """The four levels the genre gives a player: the whole kit's for the drummer, and a player of notes' from the player's velocity."""
        entry = self.role_named(role)
        if entry.get(arranger.DRUMS):
            return drum_levels(self._choices.style()[arranger.LOUDNESS][arranger.DRUMS])
        return note_levels(entry[tune_notation.VELOCITY])

    def has_loudness(self, role):
        """Return whether a player has levels to choose: a player in the band who drums or plays notes at a velocity."""
        return self._choices.is_ready() and role in self.roles() and self.role_is_in(role) and (bool(self.role_named(role).get(arranger.DRUMS)) or tune_notation.VELOCITY in self.role_named(role))

    def loudness_levels(self, role):
        """Return a player's four levels by name, the genre's with the song's own in their places; the drummer's are the whole kit's,
        which every piece of the kit follows in proportion."""
        return with_own(levels=self._levels_of_style(role), own=(self._choices.get_extra(arranger.LOUDNESS) or {}).get(role))

    def loudness_level_is_own(self, *, role, level):
        return level in (self._choices.get_extra(arranger.LOUDNESS) or {}).get(role, {})

    def loudness_levels_offered(self, role):
        """Return the levels of a player that the song plays, from the quietest up: a level no note of the player's is played at is
        not offered. Found by making the song with each level moved, and kept until a choice changes."""
        if not self.has_loudness(role):
            return []
        return self._choices.offered(key=(wizard_limits.LEVELS_ANSWER, role), compute=lambda: self._levels_heard(role))

    def _levels_heard(self, role):
        plain = self._parts_as_written(role)
        heard = []
        for level in loudness.LEVELS:
            trial = self._choices.copied_for_trial()
            now = trial.get_band().loudness_levels(role)[level]
            tried = now - wizard_limits.LEVEL_TRIAL if now > wizard_limits.MIDDLE_VELOCITY else now + wizard_limits.LEVEL_TRIAL
            of_players = dict(trial.get_extra(arranger.LOUDNESS) or {})
            trial.set_extra(name=arranger.LOUDNESS, value={**of_players, role: {**of_players.get(role, {}), level: tried}})
            # The player's dynamics as written, so that a level is heard apart from the normal one.
            trial.set_extra(name=arranger.DYNAMICS, value={player: dynamics for player, dynamics in (trial.get_extra(arranger.DYNAMICS) or {}).items() if player != role} or None)
            if trial.patterns_of_song() != plain:
                heard.append(level)
        return heard

    def _parts_as_written(self, role):
        """The song's parts with a player's dynamics as the genre writes them."""
        trial = self._choices.copied_for_trial()
        trial.set_extra(name=arranger.DYNAMICS, value={player: dynamics for player, dynamics in (trial.get_extra(arranger.DYNAMICS) or {}).items() if player != role} or None)
        return trial.patterns_of_song()

    def set_loudness_level(self, *, role, level, number):
        """Give a player a level of the song's own, a velocity, or give the level back to the genre with None."""
        is_number = number is None or (isinstance(number, int) and not isinstance(number, bool) and tune_notation.LOWEST_VELOCITY <= number <= tune_notation.HIGHEST_VELOCITY)
        if not self.has_loudness(role) or level not in loudness.LEVELS or not is_number:
            raise ValueError(errors.ERR_WIZARD_LOUDNESS.format(low=tune_notation.LOWEST_VELOCITY, high=tune_notation.HIGHEST_VELOCITY, value=(role, level, number)))
        of_players = {player: dict(levels) for player, levels in (self._choices.get_extra(arranger.LOUDNESS) or {}).items()}
        own = of_players.setdefault(role, {})
        own.pop(level, None)
        if number is not None and number != self._levels_of_style(role)[level]:
            own[level] = number
        of_players = {player: levels for player, levels in of_players.items() if levels}
        self._choices.set_extra(name=arranger.LOUDNESS, value=of_players or None)
        self._choices.clear_answers()

    def has_dynamics(self, role):
        """Return whether a player's dynamics are heard: whether the song differs with the player's notes all alike and at their widest,
        found by making the song both ways and kept until a choice changes."""
        if not self.has_loudness(role):
            return False
        return self._choices.offered(key=(wizard_limits.DYNAMICS_ANSWER, role), compute=lambda: self._dynamics_are_heard(role))

    def _dynamics_are_heard(self, role):
        made = []
        for dynamics in (loudness.LEAST_DYNAMICS, loudness.MOST_DYNAMICS):
            trial = self._choices.copied_for_trial()
            trial.set_extra(name=arranger.DYNAMICS, value={**(trial.get_extra(arranger.DYNAMICS) or {}), role: dynamics})
            made.append(trial.patterns_of_song())
        return made[0] != made[1]

    def get_dynamics(self, role):
        return (self._choices.get_extra(arranger.DYNAMICS) or {}).get(role, loudness.USUAL_DYNAMICS)

    def set_dynamics(self, *, role, dynamics):
        """Say how far a player's loud and soft notes lie from the player's normal ones: not at all at the least, as the genre writes them
        in the middle, and twice as far at the most."""
        if not self.has_loudness(role) or isinstance(dynamics, bool) or not isinstance(dynamics, int) or not loudness.LEAST_DYNAMICS <= dynamics <= loudness.MOST_DYNAMICS:
            raise ValueError(errors.ERR_WIZARD_DYNAMICS.format(low=loudness.LEAST_DYNAMICS, high=loudness.MOST_DYNAMICS, value=dynamics))
        of_players = dict(self._choices.get_extra(arranger.DYNAMICS) or {})
        of_players.pop(role, None)
        if dynamics != loudness.USUAL_DYNAMICS:
            of_players[role] = dynamics
        self._choices.set_extra(name=arranger.DYNAMICS, value=of_players or None)
        self._choices.clear_answers()

    # The player beside the tune: who answers the player who has the tune, and what the answering player does in each section.

    def _interplay(self):
        """Return what the genre says of playing beside the tune: a plan of what is done in each kind of section, with a plan of its own for some subgenres, and how busy."""
        return self._choices.style().get(wizard_limits.INTERPLAY, {}) if self._choices.is_ready() else {}

    def _usual_answerer(self):
        """Return the player the genre has answer the tune, where the player can play in the subgenre, or None."""
        role = next((entry[arranger.ROLE] for entry in self._choices.style()[arranger.ROLES] if entry.get(arranger.ANSWERS)), None) if self._choices.is_ready() else None
        return role if role is not None and role in self.roles_shown() and self.role_can_play(role) else None

    def tune_player(self):
        """Return the player who has the tune: the first player of lines who answers nobody and is in the band, or None."""
        return next((role for role in self.roles_in() if self._choices.get_sounds().has_sound(role) and not self.role_named(role).get(arranger.ANSWERS) and self._plays_lines(role)), None)

    def _plays_lines(self, role):
        entry = self.role_named(role)
        return arranger.FIGURE not in values_of(style=self._choices.style(), trait=entry[arranger.TRAIT])[self.get_way(entry[arranger.TRAIT])]

    def answerers(self):
        """Return the players who may answer the tune, by name: the genre's answering player while in the band, and none where the song keeps to
        what was made before answering could be chosen."""
        usual = self._usual_answerer()
        return [] if self._beside is None or usual is None or not self.role_is_in(usual) else [usual]

    def answered_by(self):
        """Return the player who answers the tune, or None where nobody does."""
        return self._beside[wizard_limits.BY] if self._beside is not None and self._beside[wizard_limits.BY] in self.answerers() and self.role_is_in(self._beside[wizard_limits.BY]) else None

    def set_answered_by(self, role):
        """Choose who answers the tune, or nobody with None."""
        if role is not None and role not in self.answerers():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ANSWERER.format(value=role))
        if self._beside is None:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ANSWERER.format(value=role))
        self._beside[wizard_limits.BY] = role

    def ways_beside(self):
        """Return what a player beside the tune may do in a section, in order."""
        return list(interplay_values.WAYS)

    def get_role_plan(self):
        """Return the one thing the answering player does in every section, or None where the player goes by the genre's plan, section by section."""
        return self._beside[wizard_limits.WAY] if self._beside is not None else None

    def set_role_plan(self, way):
        """Have the answering player do one thing in every section, or go by the genre's plan with None. Either drops what single sections were given."""
        if self.answered_by() is None or (way is not None and way not in interplay_values.WAYS):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=way))
        self._beside[wizard_limits.WAY] = way
        self._choices.forget_section_beside()

    def section_has_role(self, place):
        """Return whether the answering player has something to choose in a section: somebody answers, and the tune's player plays in the section."""
        return self.answered_by() is not None and not self._choices.section_is_held(place) and self.tune_player() in self._choices.section_plays(place)

    def planned_role(self, place):
        """Return what the plan has the answering player do in a section: the one thing chosen for every section, or what the genre's plan
        says of the section's kind, the subgenre's own plan first, and waiting where the plan says nothing."""
        if self._beside[wizard_limits.WAY] is not None:
            return self._beside[wizard_limits.WAY]
        interplay = self._interplay()
        kind = self._choices.section_entry(place)[arranger.KIND]
        plan = {**interplay.get(wizard_limits.PLAN, {}), **interplay.get(wizard_limits.BY_SUBGENRE, {}).get(self._choices.get_subgenre(), {})}
        return plan.get(kind, interplay_values.WAITS)

    def section_role_is_own(self, place):
        """Return whether a section was given a role of its own, apart from the plan."""
        return wizard_limits.BESIDE_KEPT in self._choices.section_entry(place)

    def section_role(self, place):
        """Return what the answering player does in a section: the section's own choice, or the plan's."""
        if not self.section_has_role(place):
            raise ValueError(errors.ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=place))
        return self._choices.section_entry(place).get(wizard_limits.BESIDE_KEPT, self.planned_role(place))

    def set_section_role(self, *, place, way):
        """Choose what the answering player does in one section, or give the section back to the plan with None."""
        if not self.section_has_role(place):
            raise ValueError(errors.ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=place))
        if way is not None and way not in interplay_values.WAYS:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=way))
        if way is None and not self.section_role_is_own(place):
            return
        entry = self._choices.own_section_entries()[place]
        entry.pop(wizard_limits.BESIDE_KEPT, None)
        if way is not None:
            entry[wizard_limits.BESIDE_KEPT] = way

    def has_fills_busy(self):
        """Return whether how busy the answering player is can be chosen: somebody answers."""
        return self.answered_by() is not None

    def get_fills_busy(self):
        return self._beside[wizard_limits.BUSY_BESIDE]

    def set_fills_busy(self, busy):
        if not self.has_fills_busy() or isinstance(busy, bool) or not isinstance(busy, int) or not interplay_values.LEAST_BUSY <= busy <= interplay_values.MOST_BUSY:
            raise ValueError(errors.ERR_WIZARD_FILLS_BUSY.format(low=interplay_values.LEAST_BUSY, high=interplay_values.MOST_BUSY, value=busy))
        self._beside[wizard_limits.BUSY_BESIDE] = busy

    def usual_beside(self):
        """Return how a new song starts: answered by the genre's answering player, going by the genre's plan, as busy as the genre says."""
        return {wizard_limits.BY: self._usual_answerer(), wizard_limits.WAY: None, wizard_limits.BUSY_BESIDE: self._interplay().get(wizard_limits.BUSY_BESIDE, interplay_values.USUAL_BUSY)}

    def beside_of_song(self):
        """Return the song's player beside the tune, with what the player does in each section of the form in order, or nothing for a song that
        keeps to what was made before answering could be chosen, and for a genre nobody answers in."""
        usual = self._usual_answerer()
        if self._beside is None or usual is None or not self.role_is_in(usual):
            return {}
        answered = self.answered_by() is not None
        ways = [self.section_role(place) if answered and self.section_has_role(place) else interplay_values.WAITS for place in range(len(self._choices.section_entries()))]
        return {arranger.BESIDE: {arranger.ROLE: usual, arranger.BESIDE_BUSY: self._beside[wizard_limits.BUSY_BESIDE], arranger.BESIDE_WAYS: ways}}

    def take_kept_beside(self, *, kept):
        usual = self.usual_beside()
        by = kept.get(wizard_limits.BY)
        way = kept.get(wizard_limits.WAY)
        busy = kept.get(wizard_limits.BUSY_BESIDE, usual[wizard_limits.BUSY_BESIDE])
        # Who answers is kept as chosen even where the player cannot answer now, as the solo's player hidden by one guitarist, and answers again once the player can.
        if (by is not None and by not in self.roles()) or (way is not None and way not in interplay_values.WAYS):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ANSWERER.format(value=by))
        if isinstance(busy, bool) or not isinstance(busy, int) or not interplay_values.LEAST_BUSY <= busy <= interplay_values.MOST_BUSY:
            raise ValueError(errors.ERR_WIZARD_FILLS_BUSY.format(low=interplay_values.LEAST_BUSY, high=interplay_values.MOST_BUSY, value=busy))
        self._beside = {wizard_limits.BY: by, wizard_limits.WAY: way, wizard_limits.BUSY_BESIDE: busy}

    # A player's gauges: where each stands, the preset's place until moved.

    def character(self, player):
        """Return the character of an instrument's player: the preset's, with the gauges moved, or None where the song names no player."""
        if player not in self._levels:
            return None
        return {**preset(self._levels[player]), **self._own_gauges.get(player, {})}

    def players_of_song(self):
        """Return each instrument's player for the song: a level, or the places of every gauge where one was moved."""
        return {player: self.character(player) if self._own_gauges.get(player) else level for player, level in self._levels.items()}

    def player_gauges(self, role):
        """Return the gauges a player has: those the genre's levels of the player's instrument say anything by."""
        if not self.has_busy(role):
            return []
        return gauges_of(self._choices.style()[arranger.PLAYERS][self.role_named(role)[arranger.PLAYER]])

    def get_player_gauge(self, *, role, gauge):
        """Return where a gauge of a player stands, from the lowest place to the highest."""
        if gauge not in self.player_gauges(role):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER_GAUGE.format(value=gauge))
        return self.character(self.role_named(role)[arranger.PLAYER])[gauge]

    def set_player_gauge(self, *, role, gauge, place):
        """Move a gauge of a player. Players of one instrument, as a lead and a solo, share their gauges."""
        if gauge not in self.player_gauges(role):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER_GAUGE.format(value=gauge))
        self.take_kept_player_gauge(player=self.role_named(role)[arranger.PLAYER], gauge=gauge, place=place)

    def take_kept_player_gauge(self, *, player, gauge, place):
        if isinstance(place, bool) or not isinstance(place, int) or not characters.LOWEST <= place <= characters.HIGHEST or gauge not in characters.GAUGES or player not in self._levels:
            raise ValueError(errors.ERR_WIZARD_PLAYER_GAUGE.format(low=characters.LOWEST, high=characters.HIGHEST, value=place))
        own = self._own_gauges.setdefault(player, {})
        own[gauge] = place
        if place == characters.PRESET_PLACE[self._levels[player]]:
            # A gauge moved back to the preset's place is the preset's again.
            del own[gauge]

    def player_preset(self, role):
        """Return the level of the preset a player is, or None for a player whose gauges were moved from it."""
        player = self.role_named(role).get(arranger.PLAYER)
        return None if self._own_gauges.get(player) else self._levels.get(player)

    # The serial style's rows of numbers, a player's own.

    def player_rows(self, role):
        """Return the rows of numbers a player's notes are dealt, by name, while the song's tunes are written in the serial style
        and the player plays lines of the tune in some section of the form; none otherwise."""
        if not self._choices.is_ready() or self._choices.melody_engine() != melody_writer.SERIAL or not self._choices.get_sounds().has_sound(role) or not self._plays_lines(role):
            return []
        # A player who plays in no section of the song's form is dealt nothing, so has no row to change.
        if not any(role in self._choices.section_plays(place) for place in range(len(self._choices.section_entries()))):
            return []
        return list(wizard_limits.PLAYER_ROWS)

    def genre_row(self, *, role, name):
        """Return a player's row as the genre gives it, or the row that plays as none would."""
        habits = {**self._choices.melody_habits(), **self.role_named(role).get(arranger.HABITS, {})}
        return list(habits.get(name) or wizard_limits.ROWS_UNASKED[name])

    def get_player_row(self, *, role, name):
        """Return a player's row as the song will deal it: the player's own, or the genre's for the player."""
        if name not in self.player_rows(role):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ROW.format(value=name))
        return list(self._rows.get(role, {}).get(name) or self.genre_row(role=role, name=name))

    def player_row_is_own(self, *, role, name):
        """Return whether a player's row was changed from the genre's."""
        return name in self._rows.get(role, {})

    def row_limits(self, name):
        """Return the lowest and the highest number a cell of a row can hold."""
        return wizard_limits.ROW_LIMITS[name]

    def set_player_row(self, *, role, name, values):
        """Give a player a row of the player's own; the genre's own row given back is no row of the player's."""
        if name not in self.player_rows(role):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ROW.format(value=name))
        low, high = wizard_limits.ROW_LIMITS[name]
        if not isinstance(values, (list, tuple)) or not wizard_limits.FEWEST_ROW_CELLS <= len(values) <= wizard_limits.MOST_ROW_CELLS or any(
                isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high for value in values):
            raise ValueError(errors.ERR_WIZARD_ROW.format(name=name, low=low, high=high, fewest=wizard_limits.FEWEST_ROW_CELLS, most=wizard_limits.MOST_ROW_CELLS, value=values))
        if list(values) == self.genre_row(role=role, name=name):
            self.clear_player_row(role=role, name=name)
        else:
            self._rows.setdefault(role, {})[name] = list(values)

    def clear_player_row(self, *, role, name):
        """Give a player's row back to the genre."""
        self._rows.get(role, {}).pop(name, None)
        if not self._rows.get(role):
            self._rows.pop(role, None)

    def take_kept_player_row(self, *, role, name, values):
        self.set_player_row(role=role, name=name, values=values)

    def role_habits_of_song(self):
        """The rows the song's players have of their own, for the players the rows are dealt to."""
        return {role: {name: list(row) for name, row in rows.items() if name in self.player_rows(role)} for role, rows in self._rows.items() if self.role_is_in(role) and self.player_rows(role)}

    # The musicians: each player's clips are played by a Musician generator, the one the player is given or the person's own.

    def has_musicians(self):
        """Return whether the genre's songs give each player a Musician."""
        return self._choices.get_genre() is not None and self._choices.style()[arranger.GENRE] not in band.GENRES_WITHOUT_MUSICIANS

    def musician_name(self, role):
        """Return what the Musician of a player is called in the song made."""
        return band.musician_name(role)

    def player_musician(self, role):
        """Return the settings of the Musician the person gave a player, or None where the player has the one players are given."""
        own = (self._choices.get_extra(arranger.MUSICIANS) or {}).get(role)
        return None if own is None else dict(own)

    def set_player_musician(self, *, role, settings):
        """Give a player a Musician of the person's own, its settings by name, or None for the one players are given. The tracks the
        Musician reads are the song's to say and are not kept. Settings no Musician has, or values a setting cannot take, are refused."""
        kept = dict(self._choices.get_extra(arranger.MUSICIANS) or {})
        if settings is None:
            kept.pop(role, None)
        else:
            try:
                given = {name: value for name, value in dict(settings).items() if name not in (MusicianSetting.TUNE_FROM, MusicianSetting.CHORDS_FROM)}
                kept[role] = MusicianSettings.from_data(data=given, where=band.musician_name(role)).to_data()
            except (SongFileError, TypeError, ValueError) as problem:
                raise ValueError(errors.ERR_WIZARD_MUSICIAN.format(value=settings, problem=problem)) from None
        self._choices.set_extra(name=arranger.MUSICIANS, value=kept or None)
        self._choices.clear_answers()
