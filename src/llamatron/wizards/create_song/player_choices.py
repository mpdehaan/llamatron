# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""One player of the band, as the song wizard's choices hold the player: how the player plays, how busy, how loud, the player's gauges, rows and Musician."""

from llamatron.engine.generators.musician.model import MusicianSetting, MusicianSettings
from llamatron.model.file.song_file_error import SongFileError
from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, band, melody as melody_writer, notation as tune_notation, song_plan, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import fits, share_of, values_of
from llamatron.wizards.create_song.characters import gauges_of
from llamatron.wizards.create_song.own_values import is_integer_between
from llamatron.wizards.create_song.player_loudness import PlayerLoudness
from llamatron.wizards.create_song.player_sections import PlayerSections



def _is_row(*, values, low, high):
    """Return whether values are a row a player can be given: a list of as many cells as a row holds, each an integer from low to high."""
    if not isinstance(values, (list, tuple)):
        return False
    if not wizard_limits.FEWEST_ROW_CELLS <= len(values) <= wizard_limits.MOST_ROW_CELLS:
        return False
    for value in values:
        if not is_integer_between(value, low=low, high=high):
            return False
    return True


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
        band = self._band()
        if band.is_left_out(self._role):
            return False
        entry = self._role_entry()
        if entry.get(arranger.DRUMS):
            return True
        trait = entry[arranger.TRAIT]
        return self._choices.trait_has_sound(trait=trait, value=band.get_way(trait))

    def _role_entry(self):
        """Return what the genre writes of the player."""
        band = self._band()
        return band.role_named(self._role)

    def _instrument(self):
        """Return the instrument the player plays, as the genre names it."""
        entry = self._role_entry()
        return entry.get(arranger.PLAYER)

    def can_play(self):
        """Return whether a player can be in the band at all: the drums always, and a player of notes where a way of playing that sounds fits the subgenre."""
        entry = self._band().role_named(self._role)
        return bool(entry.get(arranger.DRUMS)) or self.is_in() or bool(self.ways(trait=entry[arranger.TRAIT]))

    def title(self):
        """Return what a player is called on the screen: the clearer name the genre gives the player, which may follow how the
        player plays, as a lead that is a singer or a lead guitar; or the player's name where the genre gives no other."""
        entry = self._role_entry()
        guitarists = self._choices.guitarists()
        if guitarists.has_one():
            one = guitarists.one_plays()
            if self._role == one[wizard_limits.CHORDS_PLAYER]:
                return one[arranger.ROLE_TITLE]
        traits = self.traits()
        by_way = entry.get(arranger.ROLE_TITLES, {})
        way = None
        if len(traits) == 1:
            band = self._band()
            way = band.get_way(traits[0])
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
        entry = self._role_entry()
        drums = bool(entry.get(arranger.DRUMS))
        picks = self._choices.picks()
        band = self._band()
        by_share = sorted(values_of(style=style, trait=trait).values(), key=share_of, reverse=True)
        ways = []
        for way in by_share:
            value = way[arranger.VALUE]
            sounds = drums or arranger.SOUND in way
            if sounds and fits(entry=way, picks=picks) and band.works(trait=trait, value=value):
                ways.append(value)
        return ways

    def has_busy(self):
        """Return whether a player's busyness can be chosen: the genre says how the player's instrument is played at each level."""
        style = self._choices.style()
        return self._instrument() in style.get(arranger.PLAYERS, {})

    def get_busy(self):
        """Return how busy a player is, from LEAST_BUSY to MOST_BUSY, or None where the song names no level."""
        band = self._band()
        return band.instrument_level(self._instrument())

    def set_busy(self, level):
        """Choose how busy a player is. Players of one instrument, as a lead and a solo, share the level."""
        if not self.has_busy():
            raise ValueError(errors.ERR_WIZARD_BUSY.format(low=wizard_limits.LEAST_BUSY, high=wizard_limits.MOST_BUSY, value=level))
        self._band().take_level(player=self._band().role_named(self._role)[arranger.PLAYER], level=level)

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
        self._band().restore_player_gauge(player=self._band().role_named(self._role)[arranger.PLAYER], gauge=gauge, place=place)

    def preset(self):
        """Return the level of the preset a player is, or None for a player whose gauges were moved from it."""
        band = self._band()
        return band.instrument_preset(self._instrument())

    def rows(self):
        """Return the rows of numbers a player's notes are dealt, by name, while the song's tunes are written in the serial style
        and the player plays lines of the tune in some section of the form; none otherwise."""
        if not self._choices.is_ready():
            return []
        melody = self._choices.melody()
        sounds = self._choices.get_sounds()
        if melody.engine() != melody_writer.SERIAL or not sounds.has_sound(self._role) or not self.plays_lines():
            return []
        # A player who plays in no section of the song's form is dealt nothing, so has no row to change.
        if not self._plays_somewhere():
            return []
        return list(wizard_limits.PLAYER_ROWS)

    def _plays_somewhere(self):
        """Return whether the player plays in any section of the song's form."""
        form = self._choices.get_song_form()
        for place in range(len(form.section_entries())):
            section = self._choices.section(place)
            if self._role in section.plays():
                return True
        return False

    def genre_row(self, name):
        """Return a player's row as the genre gives it, or the row that plays as none would."""
        melody = self._choices.melody()
        entry = self._role_entry()
        habits = dict(melody.habits())
        habits.update(entry.get(arranger.HABITS, {}))
        row = habits.get(name) or wizard_limits.ROWS_UNASKED[name]
        return list(row)

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
        if not _is_row(values=values, low=low, high=high):
            raise ValueError(errors.ERR_WIZARD_ROW.format(name=name, low=low, high=high, fewest=wizard_limits.FEWEST_ROW_CELLS, most=wizard_limits.MOST_ROW_CELLS, value=values))
        if list(values) == self.genre_row(name=name):
            self.clear_row(name=name)
        else:
            band = self._band()
            band.keep_row(role=self._role, name=name, values=list(values))

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
        """Give a player a Musician of the person's own, its settings by name, or None for the one players are given. The tracks
        the Musician reads are the song's to say and are not saved. Settings no Musician has, or values a setting cannot take, are refused."""
        musicians = dict(self._choices.get_extra(arranger.MUSICIANS) or {})
        if settings is None:
            musicians.pop(self._role, None)
        else:
            musicians[self._role] = self._musician_saved(settings)
        self._choices.set_extra(name=arranger.MUSICIANS, value=musicians or None)
        self._choices.clear_answers()

    def _musician_saved(self, settings):
        """Return a Musician's settings as the song saves them, leaving out the tracks it reads, or refuse them."""
        try:
            given = {}
            for name, value in dict(settings).items():
                if name not in (MusicianSetting.TUNE_FROM, MusicianSetting.CHORDS_FROM):
                    given[name] = value
            musician = MusicianSettings.handed_over(data=given, where=band.musician_name(self._role))
            return musician.to_data()
        except (SongFileError, TypeError, ValueError) as problem:
            raise ValueError(errors.ERR_WIZARD_MUSICIAN.format(value=settings, problem=problem)) from None

    def get_octave(self):
        """Return the octave the player plays in."""
        entry = self._role_entry()
        return entry.get(tune_notation.OCTAVE, wizard_limits.USUAL_OCTAVE)

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
        """Return whether how the player answers to Energy changes the song, found by making it at the evenest and the most dramatic."""
        made = []
        for reacts in (wizard_names.LOWEST_ENERGY, wizard_names.HIGHEST_ENERGY):
            trial = self._choices.copied_for_trial()
            extras = trial.plan_extras()
            given = dict(extras.get(song_plan.REACTS) or {})
            given[self._person()] = reacts
            extras[song_plan.REACTS] = given
            made.append(trial.patterns_of_song())
        return made[0] != made[1]

    def get_reacts(self):
        return (self._choices.plan_extras().get(song_plan.REACTS) or {}).get(self._person(), song_plan.USUAL_CONTRAST)

    def set_reacts(self, reacts):
        """Have the player answer to Energy evenly, at the lowest, or dramatically, at the highest. Two players who are one person answer alike."""
        if not self.reacts() or not is_integer_between(reacts, low=wizard_names.LOWEST_ENERGY, high=wizard_names.HIGHEST_ENERGY):
            raise ValueError(errors.ERR_WIZARD_REACTS.format(low=wizard_names.LOWEST_ENERGY, high=wizard_names.HIGHEST_ENERGY, value=reacts))
        extras = self._choices.plan_extras()
        kept = dict(extras.get(song_plan.REACTS) or {})
        kept.pop(self._person(), None)
        if reacts != song_plan.USUAL_CONTRAST:
            kept[self._person()] = reacts
        extras.pop(song_plan.REACTS, None)
        if kept:
            extras[song_plan.REACTS] = kept
        self._choices.clear_answers()

    def loudness(self):
        """Return how loud the player is: the player's levels and dynamics."""
        return PlayerLoudness(choices=self._choices, role=self._role)

    def sections(self):
        """Return where the player plays in the form: where the player comes in and when the player lays out."""
        return PlayerSections(choices=self._choices, role=self._role)
