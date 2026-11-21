# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's choices of the band: who plays, how each plays and how busy each is, the player who answers the tune, a player's gauges, rows, loudness and Musician, and one guitarist or two."""

from llamatron.song_wizard import arranger, band, characters, interplay as interplay_values, wizard_limits
from llamatron.song_wizard.arranger import values_of
from llamatron.song_wizard.characters import preset
from llamatron.song_wizard.choices_part import ChoicesPart
from llamatron.user_strings import errors


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
                wizard_limits.PLAYER_ROWS_KEPT: {role: _rows_copied(rows) for role, rows in self._rows.items() if rows} or None,
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

    def take_kept_without(self, role):
        """Leave out a player a kept song left out."""
        self._choices.player(role).set_in(False)

    def is_left_out(self, role):
        """Return whether a player was left out of the band."""
        return role in self._without

    def leave_out(self, role):
        """Leave a player out of the band."""
        if role not in self._without:
            self._without.append(role)

    def take_back(self, role):
        """Take a player left out back into the band."""
        if role in self._without:
            self._without.remove(role)

    def keep_way(self, *, trait, value):
        """Keep a way of playing for a trait, already found to fit."""
        self._ways[trait] = value

    def instrument_level(self, instrument):
        """Return how busy the players of an instrument are, or None where the song names no level."""
        return self._levels.get(instrument)

    def instrument_preset(self, instrument):
        """Return the level of the preset the players of an instrument are, or None where their gauges were moved from it."""
        return None if self._own_gauges.get(instrument) else self._levels.get(instrument)

    def own_row_of(self, *, role, name):
        """Return a row of numbers a player was given of the song's own, as held and not to be changed, or None."""
        return self._rows.get(role, {}).get(name)

    def keep_row(self, *, role, name, values):
        """Keep a row of numbers of the song's own for a player, or let it go with None."""
        if values is None:
            self._rows.get(role, {}).pop(name, None)
            if not self._rows.get(role):
                self._rows.pop(role, None)
        else:
            self._rows.setdefault(role, {})[name] = values

    def get_ways(self):
        """Return each trait's way of playing where one was chosen, as held and not to be changed."""
        return self._ways

    def forget_way(self, trait):
        """Leave a trait's way of playing to the subgenre again."""
        self._ways.pop(trait, None)

    def role_named(self, role):
        found = self._choices.roles_by_name().get(role)
        if found is None:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER.format(value=role))
        return found

    def roles(self):
        """Return the players the genre's band may have, by name, in the genre's order."""
        return [entry[arranger.ROLE] for entry in self._choices.style()[arranger.ROLES]] if self._choices.is_ready() else []


    # One guitarist or two: a band whose one guitarist plays the chords and takes the solo, the chords
    # stopping where the solo plays, shown as one player.

    def one_guitarist(self):
        return self._choices.style().get(wizard_limits.ONE_GUITARIST) if self._choices.is_ready() else None

    def offers_one_guitarist(self):
        """Return whether the band can have one guitarist: the genre says which two players the one would be, and the solo can be a guitar's."""
        one = self.one_guitarist()
        return bool(one) and self._choices.player(one[wizard_limits.CHORDS_PLAYER]).can_play() and one[wizard_limits.SOLO_WAY] in self._choices.player(one[wizard_limits.SOLO_PLAYER]).ways(trait=self.role_named(one[wizard_limits.SOLO_PLAYER])[arranger.TRAIT])

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
            one = self.one_guitarist()
            if one[wizard_limits.SOLO_PLAYER] in self._without:
                self._without.remove(one[wizard_limits.SOLO_PLAYER])
            self._ways[self.role_named(one[wizard_limits.SOLO_PLAYER])[arranger.TRAIT]] = one[wizard_limits.SOLO_WAY]

    def take_kept_guitarists(self, *, count):
        self.set_guitarists(count)

    def roles_shown(self):
        """Return the players the screen shows: every player, but for the player of the solo where one guitarist plays both."""
        hidden = self.one_guitarist()[wizard_limits.SOLO_PLAYER] if self.has_one_guitarist() else None
        return [role for role in self.roles() if role != hidden]

    def without_of_song(self):
        """Return the players the song leaves out: those left out, and with them the solo of one guitarist who is left out."""
        without = list(self._without)
        if self.has_one_guitarist():
            one = self.one_guitarist()
            if one[wizard_limits.CHORDS_PLAYER] in without and one[wizard_limits.SOLO_PLAYER] not in without:
                without.append(one[wizard_limits.SOLO_PLAYER])
        return without

    def plays_of_one_guitarist(self, plays):
        """Return who plays in a section where one guitarist plays both parts: the chords stop where the solo plays."""
        one = self.one_guitarist()
        if self.has_one_guitarist() and one[wizard_limits.SOLO_PLAYER] in plays and one[wizard_limits.CHORDS_PLAYER] in plays:
            return [role for role in plays if role != one[wizard_limits.CHORDS_PLAYER]]
        return None

    def roles_in(self):
        return [role for role in self.roles() if self._choices.player(role).is_in()]


    def works(self, *, trait, value):
        """Return whether a way of playing can be chosen beside the other picks, some ways needing a meter or a feel."""
        try:
            self._choices.picks_with({**self._ways, trait: value})
        except ValueError:
            return False
        return True


    # What the whole song has a way of: its chords, its feel and its drum fills, each a trait of the genre no one player owns.

    def song_trait(self, traits):
        """Return the first of some traits the genre has that no player owns, as chords under either name a genre gives them, or None."""
        if not self._choices.is_ready():
            return None
        of_players = {trait for role in self.roles() for trait in self._choices.player(role).traits()}
        return next((trait for trait in traits if trait not in of_players and isinstance(self._choices.style()[arranger.TRAITS].get(trait), list)), None)

    def song_ways(self, trait):
        """Return the ways a trait of the whole song may go beside the other picks, the commonest first."""
        entries = sorted(values_of(style=self._choices.style(), trait=trait).values(), key=self._choices.share_in_subgenre, reverse=True)
        return [entry[arranger.VALUE] for entry in entries if self.works(trait=trait, value=entry[arranger.VALUE])]

    def get_way(self, trait):
        return self._choices.picks()[trait]

    def set_way(self, *, trait, value):
        if not self._choices.is_ready() or value not in values_of(style=self._choices.style(), trait=trait) or not self.works(trait=trait, value=value):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY.format(trait=trait, value=value))
        self._ways[trait] = value


    def take_level(self, *, player, level):
        if isinstance(level, bool) or not isinstance(level, int) or level not in self._choices.style().get(arranger.PLAYERS, {}).get(player, {}):
            raise ValueError(errors.ERR_WIZARD_BUSY.format(low=wizard_limits.LEAST_BUSY, high=wizard_limits.MOST_BUSY, value=level))
        self._levels[player] = level
        # A preset chosen puts every gauge of the player back where the preset has it.
        self._own_gauges.pop(player, None)


    # The player beside the tune: who answers the player who has the tune, and what the answering player does in each section.

    def _interplay(self):
        """Return what the genre says of playing beside the tune: a plan of what is done in each kind of section, with a plan of its own for some subgenres, and how busy."""
        return self._choices.style().get(wizard_limits.INTERPLAY, {}) if self._choices.is_ready() else {}

    def _usual_answerer(self):
        """Return the player the genre has answer the tune, where the player can play in the subgenre, or None."""
        role = next((entry[arranger.ROLE] for entry in self._choices.style()[arranger.ROLES] if entry.get(arranger.ANSWERS)), None) if self._choices.is_ready() else None
        return role if role is not None and role in self.roles_shown() and self._choices.player(role).can_play() else None

    def tune_player(self):
        """Return the player who has the tune: the first player of lines who answers nobody and is in the band, or None."""
        return next((role for role in self.roles_in() if self._choices.get_sounds().has_sound(role) and not self.role_named(role).get(arranger.ANSWERS) and self._choices.player(role).plays_lines()), None)


    def answerers(self):
        """Return the players who may answer the tune, by name: the genre's answering player while in the band, and none where the song keeps to
        what was made before answering could be chosen."""
        usual = self._usual_answerer()
        return [] if self._beside is None or usual is None or not self._choices.player(usual).is_in() else [usual]

    def answered_by(self):
        """Return the player who answers the tune, or None where nobody does."""
        return self._beside[wizard_limits.BY] if self._beside is not None and self._beside[wizard_limits.BY] in self.answerers() and self._choices.player(self._beside[wizard_limits.BY]).is_in() else None

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
        self._choices.get_song_form().forget_section_beside()

    def section_has_role(self, place):
        """Return whether the answering player has something to choose in a section: somebody answers, and the tune's player plays in the section."""
        return self.answered_by() is not None and not self._choices.section(place).is_held() and self.tune_player() in self._choices.section(place).plays()

    def planned_role(self, place):
        """Return what the plan has the answering player do in a section: the one thing chosen for every section, or what the genre's plan
        says of the section's kind, the subgenre's own plan first, and waiting where the plan says nothing."""
        if self._beside[wizard_limits.WAY] is not None:
            return self._beside[wizard_limits.WAY]
        interplay = self._interplay()
        kind = self._choices.section(place).entry()[arranger.KIND]
        plan = {**interplay.get(wizard_limits.PLAN, {}), **interplay.get(wizard_limits.BY_SUBGENRE, {}).get(self._choices.get_subgenre(), {})}
        return plan.get(kind, interplay_values.WAITS)

    def section_role_is_own(self, place):
        """Return whether a section was given a role of its own, apart from the plan."""
        return wizard_limits.BESIDE_KEPT in self._choices.section(place).entry()

    def section_role(self, place):
        """Return what the answering player does in a section: the section's own choice, or the plan's."""
        if not self.section_has_role(place):
            raise ValueError(errors.ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=place))
        return self._choices.section(place).entry().get(wizard_limits.BESIDE_KEPT, self.planned_role(place))

    def set_section_role(self, *, place, way):
        """Choose what the answering player does in one section, or give the section back to the plan with None."""
        if not self.section_has_role(place):
            raise ValueError(errors.ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=place))
        if way is not None and way not in interplay_values.WAYS:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=way))
        if way is None and not self.section_role_is_own(place):
            return
        entry = self._choices.get_song_form().own_section_entries()[place]
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
        if self._beside is None or usual is None or not self._choices.player(usual).is_in():
            return {}
        answered = self.answered_by() is not None
        ways = [self.section_role(place) if answered and self.section_has_role(place) else interplay_values.WAITS for place in range(len(self._choices.get_song_form().section_entries()))]
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


    def take_kept_player_gauge(self, *, player, gauge, place):
        if isinstance(place, bool) or not isinstance(place, int) or not characters.LOWEST <= place <= characters.HIGHEST or gauge not in characters.GAUGES or player not in self._levels:
            raise ValueError(errors.ERR_WIZARD_PLAYER_GAUGE.format(low=characters.LOWEST, high=characters.HIGHEST, value=place))
        own = self._own_gauges.setdefault(player, {})
        own[gauge] = place
        if place == characters.PRESET_PLACE[self._levels[player]]:
            # A gauge moved back to the preset's place is the preset's again.
            del own[gauge]


    def row_limits(self, name):
        """Return the lowest and the highest number a cell of a row can hold."""
        return wizard_limits.ROW_LIMITS[name]


    def take_kept_player_row(self, *, role, name, values):
        self._choices.player(role).set_row(name=name, values=values)

    def _habits_of(self, *, role, rows):
        """Return a player's own rows that the player is dealt, each a copy."""
        dealt = self._choices.player(role).rows()
        return {name: list(row) for name, row in rows.items() if name in dealt}

    def role_habits_of_song(self):
        """The rows the song's players have of their own, for the players the rows are dealt to."""
        return {role: self._habits_of(role=role, rows=rows) for role, rows in self._rows.items() if self._choices.player(role).is_in() and self._choices.player(role).rows()}

    # The musicians: each player's clips are played by a Musician generator, the one the player is given or the person's own.

    def has_musicians(self):
        """Return whether the genre's songs give each player a Musician."""
        return self._choices.get_genre() is not None and self._choices.style()[arranger.GENRE] not in band.GENRES_WITHOUT_MUSICIANS


def _rows_copied(rows):
    """Return a player's rows by name, each a copy."""
    return {name: list(row) for name, row in rows.items()}
