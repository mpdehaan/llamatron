# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's choices of the band: who plays, how each plays and how busy each is, a player's gauges, rows, loudness and Musician, and one guitarist or two."""

from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, band, characters, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import values_of
from llamatron.wizards.create_song.characters import preset
from llamatron.wizards.create_song.choices_part import add_counted, ChoicesPart, chosen_only
from llamatron.wizards.create_song.own_values import is_integer_between


class BandChoices(ChoicesPart):
    """What was chosen of the band: each trait's way of playing where one was chosen, how busy each instrument's player is, the gauges and rows a player was given, the players left out, and how many guitarists."""

    __slots__ = ('_ways', '_levels', '_own_gauges', '_rows', '_without')

    def __init__(self, *, choices):
        ChoicesPart.__init__(self, choices=choices)
        self.reset()

    def reset(self):
        """Go back to a band with nothing chosen: no way of playing, no level, nobody left out."""
        # Each trait's way of playing where one was chosen, how busy each instrument's player is, and the players left out.
        self._ways = {}
        self._without = []
        self.forget_players()

    def forget_players(self):
        """Forget how busy each player is, and the gauges and rows each was given."""
        self._levels = {}
        self._own_gauges = {}
        self._rows = {}

    def take_usual(self):
        """Take the band the subgenre usually has: each player at the usual level, with no gauge or row of the player's own."""
        self._levels = {player: wizard_limits.USUAL_BUSY for player in self._choices.style().get(arranger.PLAYERS, {})}
        self._own_gauges = {}
        self._rows = {}

    # What a song keeps of the band.

    def to_data(self):
        """Return what a song keeps of the band, as plain data a song file saves: only what was chosen."""
        held = {
            arranger.PICKS: dict(self._ways) or None,
            arranger.PLAYERS: dict(self._levels) or None,
            arranger.WITHOUT: list(self._without) or None,
            wizard_limits.PLAYER_GAUGES_SAVED: self._saved_gauges() or None,
            wizard_limits.PLAYER_ROWS_SAVED: self._saved_rows() or None,
        }
        return chosen_only(held)

    def _saved_gauges(self):
        """Return the gauges each player has moved from the preset, each a copy, leaving out a player who has moved none."""
        kept = {}
        for player, places in self._own_gauges.items():
            if places:
                kept[player] = dict(places)
        return kept

    def _saved_rows(self):
        """Return the rows each player has of its own, each a copy, leaving out a player who has none."""
        kept = {}
        for role, rows in self._rows.items():
            if rows:
                kept[role] = _rows_copied(rows)
        return kept

    def restore(self, saved):
        """Restore what a song saved of the band: each trait's way, each player's level and gauges, who is left out, how many
        guitarists play, leaving out whatever no longer fits."""
        ways = saved.mapping(arranger.PICKS)
        for trait, value in ways.items():
            saved.apply(self.set_way, trait=trait, value=value)
        levels = saved.mapping(arranger.PLAYERS)
        for player, level in levels.items():
            saved.apply(self.take_level, player=player, level=level)
        self._restore_gauges(saved)
        for role in saved.listing(arranger.WITHOUT):
            player = self._choices.player(role)
            saved.apply(player.set_in, False)

    def _restore_gauges(self, saved):
        """Restore the gauges each player had moved."""
        gauges = saved.mapping(wizard_limits.PLAYER_GAUGES_SAVED)
        for player, places in gauges.items():
            places_kept = saved.as_mapping(places)
            for gauge, place in places_kept.items():
                saved.apply(self.restore_player_gauge, player=player, gauge=gauge, place=place)

    def restore_rows(self, saved):
        """Restore the rows each player had of its own, which only a melody style that deals rows allows."""
        rows_by_role = saved.mapping(wizard_limits.PLAYER_ROWS_SAVED)
        for role, rows in rows_by_role.items():
            rows_kept = saved.as_mapping(rows)
            player = self._choices.player(role)
            for name, values in rows_kept.items():
                saved.apply(player.set_row, name=name, values=values)

    def add_picks(self, picks):
        """Add the band's picks to the song's: each trait's way, each instrument's player, who is left out and the rows the
        players have of their own."""
        ways = picks.setdefault(arranger.PICKS, {})
        ways.update(self._ways)
        picks[arranger.PLAYERS] = self._players_of_song()
        picks[arranger.WITHOUT] = self._without_of_song()
        habits = self._role_habits_of_song()
        if habits:
            picks[arranger.ROLE_HABITS] = habits

    def counted(self):
        """Return every setting of the band, each under a name of its own, so that two bands can be compared setting by setting."""
        counted = {
            (wizard_limits.GENRE_SETTING, arranger.WITHOUT): sorted(self._without),
        }
        add_counted(counted, kind=arranger.PICKS, held=self._ways)
        add_counted(counted, kind=arranger.PLAYERS, held=self._levels)
        add_counted(counted, kind=wizard_limits.PLAYER_GAUGES_SAVED, held=self._own_gauges)
        add_counted(counted, kind=wizard_limits.PLAYER_ROWS_SAVED, held=self._rows)
        return counted

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



    def roles_shown(self):
        """Return the players the screen shows: every player, but for the player of the solo where one guitarist plays both."""
        guitarists = self._choices.guitarists()
        hidden = guitarists.hidden_player()
        return [role for role in self.roles() if role != hidden]

    def _without_of_song(self):
        """Return the players the song leaves out: those left out, and with them the solo of one guitarist who is left out."""
        without = list(self._without)
        guitarists = self._choices.guitarists()
        if guitarists.has_one():
            one = guitarists.one_plays()
            if one[wizard_limits.CHORDS_PLAYER] in without and one[wizard_limits.SOLO_PLAYER] not in without:
                without.append(one[wizard_limits.SOLO_PLAYER])
        return without

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
        owned = self._traits_of_players()
        style = self._choices.style()
        written = style[arranger.TRAITS]
        for trait in traits:
            if trait not in owned and isinstance(written.get(trait), list):
                return trait
        return None

    def _traits_of_players(self):
        """Return every trait a player of the band owns."""
        owned = set()
        for role in self.roles():
            player = self._choices.player(role)
            owned.update(player.traits())
        return owned

    def song_ways(self, trait):
        """Return the ways a trait of the whole song may go beside the other picks, the commonest first."""
        ways = values_of(style=self._choices.style(), trait=trait)
        by_share = sorted(ways.values(), key=self._choices.share_in_subgenre, reverse=True)
        return [entry[arranger.VALUE] for entry in by_share if self.works(trait=trait, value=entry[arranger.VALUE])]

    def get_way(self, trait):
        return self._choices.picks()[trait]

    def set_way(self, *, trait, value):
        if not self._choices.is_ready() or value not in values_of(style=self._choices.style(), trait=trait) or not self.works(trait=trait, value=value):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY.format(trait=trait, value=value))
        self._ways[trait] = value


    def take_level(self, *, player, level):
        """Give an instrument's player a level of busyness the genre writes; every gauge of the player goes back to the preset's place."""
        style = self._choices.style()
        players = style.get(arranger.PLAYERS, {})
        levels = players.get(player, {})
        if isinstance(level, bool) or not isinstance(level, int) or level not in levels:
            raise ValueError(errors.ERR_WIZARD_BUSY.format(low=wizard_limits.LEAST_BUSY, high=wizard_limits.MOST_BUSY, value=level))
        self._levels[player] = level
        # A preset chosen puts every gauge of the player back where the preset has it.
        self._own_gauges.pop(player, None)



    def tune_player(self):
        """Return the player who has the tune: the first player of lines who answers nobody and is in the band, or None."""
        sounds = self._choices.get_sounds()
        for role in self.roles_in():
            entry = self.role_named(role)
            if not sounds.has_sound(role) or entry.get(arranger.ANSWERS):
                continue
            player = self._choices.player(role)
            if player.plays_lines():
                return role
        return None


    # A player's gauges: where each stands, the preset's place until moved.

    def character(self, player):
        """Return the character of an instrument's player: the preset's, with the gauges moved, or None where the song names no player."""
        if player not in self._levels:
            return None
        return {**preset(self._levels[player]), **self._own_gauges.get(player, {})}

    def _players_of_song(self):
        """Return each instrument's player for the song: a level, or the places of every gauge where one was moved."""
        players = {}
        for player, level in self._levels.items():
            if self._own_gauges.get(player):
                players[player] = self.character(player)
            else:
                players[player] = level
        return players


    def restore_player_gauge(self, *, player, gauge, place):
        """Put back a gauge a song saved of an instrument's player; a gauge at the preset's place is the preset's again."""
        is_place = is_integer_between(place, low=wizard_names.CHARACTERS_LOWEST, high=wizard_names.CHARACTERS_HIGHEST)
        if not is_place or gauge not in characters.GAUGES or player not in self._levels:
            raise ValueError(errors.ERR_WIZARD_PLAYER_GAUGE.format(low=wizard_names.CHARACTERS_LOWEST, high=wizard_names.CHARACTERS_HIGHEST, value=place))
        own = self._own_gauges.setdefault(player, {})
        own[gauge] = place
        if place == characters.PRESET_PLACE[self._levels[player]]:
            # A gauge moved back to the preset's place is the preset's again.
            del own[gauge]



    def _habits_of(self, *, role, rows):
        """Return a player's own rows that the player is dealt, each a copy."""
        dealt = self._choices.player(role).rows()
        return {name: list(row) for name, row in rows.items() if name in dealt}

    def _role_habits_of_song(self):
        """Return the rows the song's players have of their own, for the players who play and are dealt rows."""
        habits = {}
        for role, rows in self._rows.items():
            player = self._choices.player(role)
            if player.is_in() and player.rows():
                habits[role] = self._habits_of(role=role, rows=rows)
        return habits

    # The musicians: each player's clips are played by a Musician generator, the one the player is given or the person's own.

    def has_musicians(self):
        """Return whether the genre's songs give each player a Musician."""
        return self._choices.get_genre() is not None and self._choices.style()[arranger.GENRE] not in band.GENRES_WITHOUT_MUSICIANS


def _rows_copied(rows):
    """Return a player's rows by name, each a copy."""
    return {name: list(row) for name, row in rows.items()}
