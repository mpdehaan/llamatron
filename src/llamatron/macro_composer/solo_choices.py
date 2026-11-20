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

"""The song wizard's choices of the solos: each solo of the song is its player's own notes, the wizard's until edited by hand, in a take that can be drawn again."""

import copy
import zlib

from llamatron.composition.song_file_error import SongFileError
from llamatron.macro_composer import arranger, wizard_limits
from llamatron.macro_composer.choices_part import ChoicesPart
from llamatron.strings import errors


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
        return [place for place in range(len(self._choices.section_labels())) if self._choices.section(place).kind() == wizard_limits.SOLO and player in self._choices.section(place).plays() and not self._choices.section(place).is_held()]

    def _soloist(self):
        """The genre's answering player while in the band, who plays the solos whether or not the player also answers the tune,
        and whether or not the band shows the player apart: a band with one guitarist shows its two guitar players as one."""
        role = next((entry[arranger.ROLE] for entry in self._choices.style()[arranger.ROLES] if entry.get(arranger.ANSWERS)), None) if self._choices.is_ready() else None
        return role if role is not None and role in self._choices.get_band().roles_in() else None

    def solo_player(self):
        """Return who plays the song's solos, or None where the song has none."""
        return self._soloist() if self.solo_places() else None

    def _solo_number_at(self, place):
        """A solo's number among the form's sections of the kind solo, counted from 1, which is what its own notes are kept under."""
        return len([other for other in range(place + 1) if self._choices.section(other).kind() == wizard_limits.SOLO])

    def solo_is_own(self, place):
        """Return whether the solo at a place of the form was written by hand for the player who now plays it."""
        return self.solo_player() in (self._choices.get_extra(arranger.OWN_SOLOS) or {}).get(self._solo_number_at(place), {})

    def solo_pattern_name(self, place):
        """Return the name of the pattern that holds the solo at a place of the form in the set the choices make, or None where the set has none."""
        return self._solo_in_made(place)[0]

    def solo_pattern(self, place):
        """Return the solo at a place of the form as a pattern's data, the person's own or the solo the choices write, or None where nobody plays one."""
        return copy.deepcopy(self._solo_in_made(place)[1])

    def _solo_in_made(self, place):
        return self._choices.remembered(key=(wizard_limits.SOLO_MADE_ANSWER, place), compute=lambda: self._found_solo_in_made(place))

    def _found_solo_in_made(self, place):
        if place not in self.solo_places():
            return None, None
        setlist, name = self._choices.written_for_trial()
        scenes = setlist.get_song(name).get_scenes()
        role = self.solo_player()
        slot = scenes[place].get_clip_slot(role) if place < len(scenes) and scenes[place].has_clip_slot(role) else None
        if slot is None:
            return None, None
        return slot.get_pattern_name(), setlist.get_pattern(slot.get_pattern_name()).to_data()

    def solo_take(self, place):
        """Return which take the solo at a place of the form is: the first, the solo the choices write, or a later one asked for."""
        return (self._choices.get_extra(wizard_limits.SOLO_TAKES) or {}).get(self._solo_number_at(place), wizard_limits.FIRST_TUNE_TAKE)

    def new_solo_take(self, place):
        """Have another solo written for the solo at a place of the form, the rest of the song left as it was. Notes written by
        hand for that solo are given up for it."""
        if place not in self.solo_places():
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=wizard_limits.SOLO))
        number = self._solo_number_at(place)
        self._choices.set_extra(name=wizard_limits.SOLO_TAKES, value={**(self._choices.get_extra(wizard_limits.SOLO_TAKES) or {}), number: self.solo_take(place) + 1})
        self._keep_own_solo(number=number, role=self.solo_player(), pattern=None)
        self._choices.clear_answers()

    def _keep_own_solo(self, *, number, role, pattern):
        """Keep a pattern as a player's own notes of the solo of a number, or let the player's own go with None; a solo nobody has notes of their own for is not kept at all."""
        own = {solo: dict(players) for solo, players in (self._choices.get_extra(arranger.OWN_SOLOS) or {}).items()}
        if pattern is None:
            own.get(number, {}).pop(role, None)
        else:
            own.setdefault(number, {})[role] = copy.deepcopy(pattern)
        own = {solo: players for solo, players in own.items() if players}
        self._choices.set_extra(name=arranger.OWN_SOLOS, value=own or None)

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
                pattern = self._choices.remembered(key=(wizard_limits.SOLO_TAKEN_ANSWER, number), compute=lambda number=number: self._solo_taken(number=number, take=takes[number]))
                if pattern is not None:
                    taken[number] = {role: copy.deepcopy(pattern)}
        return taken

    def _solo_taken(self, *, number, take):
        """The solo another take draws: that solo in the song these choices would make from a seed of the take's own, with the same
        chords and no solo of another take or written by hand, or None where that song has none."""
        other = self._choices.made_again()
        other.set_extra(name=wizard_limits.SOLO_TAKES, value=None)
        other.set_extra(name=arranger.OWN_SOLOS, value=None)
        trait = self._choices.progression_trait()
        drawn = self._choices.progressions_by_chance()[:1]
        if trait is not None and drawn:
            other.get_band().set_way(trait=trait, value=drawn[0])
        other.set_seed(zlib.crc32(wizard_limits.SOLO_TAKE_SEED.format(seed=self._choices.get_seed(), number=number, take=take).encode()) % (wizard_limits.LAST_SEED + 1))
        try:
            place = next(place for place in other.get_solos().solo_places() if other.get_solos()._solo_number_at(place) == number)
            return other.get_solos()._found_solo_in_made(place)[1]
        except (StopIteration, ValueError, IndexError, KeyError, SongFileError):
            return None

    def set_solo_pattern(self, *, place, pattern):
        """Keep a pattern's data as the own notes of the solo at a place of the form, for the player who plays the solo, or forget
        the person's own with None, so that the choices write the solo again. A place nobody plays a solo at, and a pattern the
        song cannot be made with, are refused and nothing changes."""
        if place not in self.solo_places():
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=wizard_limits.SOLO))
        role = self.solo_player()
        number = self._solo_number_at(place)
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
