# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's choices of the solos: each solo of the song is its player's own notes, the wizard's until edited by hand, in a take that can be drawn again."""

import copy

from llamatron.model.file.song_file_error import SongFileError
from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, wizard_limits
from llamatron.wizards.create_song.choices_part import cached_until_choices_change, ChoicesPart


class SoloChoices(ChoicesPart):
    """What was chosen of the song's solos. The takes and the notes written by hand are part of what is laid over the song's picks, which the arranger reads, and are reached through the choices."""

    __slots__ = ()

    # The solos: each solo of the song is its player's own notes, the wizard's until edited by hand.

    def solo_places(self):
        """Return the place in the form of each solo somebody other than the drummer plays, in the form's order: the sections of
        the kind solo that the genre's answering player plays in."""
        player = self._soloist()
        if player is None:
            return []
        return self._choices.places_of(kind=wizard_limits.SOLO, player=player)

    def _soloist(self):
        """Return the genre's answering player while in the band, who plays the solos whether or not the player also answers the
        tune, and whether or not the band shows the player apart: a band with one guitarist shows its two guitar players as one."""
        interplay = self._choices.interplay()
        role = interplay.genre_answerer()
        band = self._choices.get_band()
        if role in band.roles_in():
            return role
        return None

    def solo_player(self):
        """Return who plays the song's solos, or None where the song has none."""
        return self._soloist() if self.solo_places() else None

    def number_at(self, place):
        """Return a solo's number among the form's solos, counted from 1, which its own notes are saved under."""
        return self._choices.number_of_kind_at(place=place, kind=wizard_limits.SOLO)

    def place_of_number(self, number):
        """Return the place in the form of the solo of a number, or None."""
        for place in self.solo_places():
            if self.number_at(place) == number:
                return place
        return None

    def solo_is_own(self, place):
        """Return whether the solo at a place of the form was written by hand for the player who now plays it."""
        return self.solo_player() in (self._choices.get_extra(arranger.OWN_SOLOS) or {}).get(self.number_at(place), {})

    def solo_pattern_name(self, place):
        """Return the name of the pattern that holds the solo at a place of the form in the set the choices make, or None where the set has none."""
        return self.made_solo(place)[0]

    def solo_pattern(self, place):
        """Return the solo at a place of the form as a pattern's data, the person's own or the solo the choices write, or None where nobody plays one."""
        return copy.deepcopy(self.made_solo(place)[1])

    @cached_until_choices_change
    def made_solo(self, place):
        """Return the name and the data of the pattern the soloist plays in the solo at a place of the form, in the song the
        choices make, or two Nones where nobody plays a solo there."""
        if place not in self.solo_places():
            return None, None
        return self._choices.pattern_played_at(place=place, role=self.solo_player())

    def solo_take(self, place):
        """Return which take the solo at a place of the form is: the first, the solo the choices write, or a later one asked for."""
        return (self._choices.get_extra(wizard_limits.SOLO_TAKES) or {}).get(self.number_at(place), wizard_limits.FIRST_TUNE_TAKE)

    def new_solo_take(self, place):
        """Have another solo written for the solo at a place of the form, the rest of the song left as it was. Notes written by
        hand for that solo are given up for it."""
        if place not in self.solo_places():
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=wizard_limits.SOLO))
        number = self.number_at(place)
        takes = dict(self._choices.get_extra(wizard_limits.SOLO_TAKES) or {})
        takes[number] = self.solo_take(place) + 1
        self._choices.set_extra(name=wizard_limits.SOLO_TAKES, value=takes)
        self._keep_own_solo(number=number, role=self.solo_player(), pattern=None)
        self._choices.clear_answers()

    def _keep_own_solo(self, *, number, role, pattern):
        """Save a pattern as a player's own notes of the solo of a number, or let the player's own go with None; a solo nobody
        has notes of their own for is not saved at all."""
        saved = self._choices.get_extra(arranger.OWN_SOLOS) or {}
        own = {solo: dict(players) for solo, players in saved.items()}
        if pattern is None:
            players = own.get(number, {})
            players.pop(role, None)
        else:
            players = own.setdefault(number, {})
            players[role] = copy.deepcopy(pattern)
        kept = {solo: players for solo, players in own.items() if players}
        self._choices.set_extra(name=arranger.OWN_SOLOS, value=kept or None)

    def taken_solos(self):
        """The pattern of each solo that is a later take and not written by hand, under the solo's number and its player's name."""
        takes = self._choices.get_extra(wizard_limits.SOLO_TAKES) or {}
        if not takes:
            return {}
        own = self._choices.get_extra(arranger.OWN_SOLOS) or {}
        role = self._soloist()
        taken = {}
        for number in sorted(takes):
            if role is not None and role not in own.get(number, {}) and takes[number] != wizard_limits.FIRST_TUNE_TAKE:
                pattern = self._solo_taken(number=number, take=takes[number])
                if pattern is not None:
                    taken[number] = {role: copy.deepcopy(pattern)}
        return taken

    @cached_until_choices_change
    def _solo_taken(self, *, number, take):
        """Return the solo another take draws: that solo in the song these choices would make from a seed of the take's own, with
        the same chords and no solo of another take or written by hand, or None where that song has none."""
        seed_text = wizard_limits.SOLO_TAKE_SEED.format(seed=self._choices.get_seed(), number=number, take=take)
        other = self._choices.again_for_take(cleared=(wizard_limits.SOLO_TAKES, arranger.OWN_SOLOS), seed_text=seed_text)
        solos = other.get_solos()
        try:
            place = solos.place_of_number(number)
            if place is None:
                return None
            _, pattern = solos.made_solo(place)
        except (ValueError, IndexError, KeyError, SongFileError):
            return None
        return pattern

    def set_solo_pattern(self, *, place, pattern):
        """Keep a pattern's data as the own notes of the solo at a place of the form, for the player who plays the solo, or forget
        the person's own with None, so that the choices write the solo again. A place nobody plays a solo at, and a pattern the
        song cannot be made with, are refused and nothing changes."""
        if place not in self.solo_places():
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=wizard_limits.SOLO))
        role = self.solo_player()
        number = self.number_at(place)
        before = copy.deepcopy(self._choices.get_extra(arranger.OWN_SOLOS))
        self._keep_own_solo(number=number, role=role, pattern=pattern)
        self._choices.clear_answers()
        try:
            self._choices.written_for_trial()
        except Exception as problem:
            self._choices.set_extra(name=arranger.OWN_SOLOS, value=None)
            if before is not None:
                self._choices.set_extra(name=arranger.OWN_SOLOS, value=before)
            self._choices.clear_answers()
            raise ValueError(errors.ERR_WIZARD_TUNE_PATTERN.format(problem=problem)) from problem
