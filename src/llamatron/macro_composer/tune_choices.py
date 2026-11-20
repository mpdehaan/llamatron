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

"""The song wizard's choices of the tunes: one for each kind of section the tune's player plays in, who plays the tune, its takes, and the notes written by hand."""

import copy
import zlib

from llamatron.composition.song_file_error import SongFileError
from llamatron.macro_composer import arranger, players as players_values, tune_fit, wizard_limits
from llamatron.macro_composer.arranger import bar_length
from llamatron.macro_composer.choices_part import ChoicesPart
from llamatron.strings import errors


class TuneChoices(ChoicesPart):
    """What was chosen of the song's tunes. Who plays the tune, the takes and the notes written by hand are part of what is laid over the song's picks, which the arranger reads, and are reached through the choices."""

    __slots__ = ()

    # The tunes: one for each kind of section the tune's player plays in. A tune is written by the choices until a person edits its
    # pattern by hand; from then on the pattern is the person's own, and no choice writes over it.

    def tune_kinds(self):
        """Return each kind of section the song has a tune in, once, in the form's order: the kinds whose sections the tune's player plays in."""
        player = self._choices.get_band().tune_player()
        kinds = []
        for place, kind in enumerate(self._choices.section_kinds_in_form()):
            if kind not in kinds and player is not None and player in self._choices.section(place).plays() and not self._choices.section(place).is_held():
                kinds.append(kind)
        return kinds

    def tune_place(self, kind):
        """Return the place in the form of the first section of a kind the tune's player plays in, or None."""
        player = self._choices.get_band().tune_player()
        places = range(len(self._choices.section_labels()))
        return next((place for place in places if self._choices.section(place).kind() == kind and player in self._choices.section(place).plays() and not self._choices.section(place).is_held()), None)

    def tune_is_own(self, kind):
        """Return whether a kind of section's tune was written by hand, so that nothing the wizard chooses writes over it."""
        return kind in (self._choices.get_extra(arranger.OWN_TUNES) or {})

    def tune_pattern_name(self, kind):
        """Return the name of the pattern that holds a kind of section's tune in the set the choices make, or None where the set has none."""
        return self._tune_in_made(kind)[0]

    def tune_pattern(self, kind):
        """Return a kind of section's tune as a pattern's data: the person's own, or the tune the choices write as they stand. None where no tune is made."""
        own = (self._choices.get_extra(arranger.OWN_TUNES) or {}).get(kind)
        return copy.deepcopy(own if own is not None else self._tune_in_made(kind)[1])

    def _tune_in_made(self, kind):
        """The name and the data of the pattern the tune's player plays in the first section of a kind, in the set the choices make,
        found once for the choices as they stand, since a page asks at every key and the answer means making the song."""
        return self._choices.remembered(key=(wizard_limits.TUNE_MADE_ANSWER, kind), compute=lambda: self._found_tune_in_made(kind))

    def _found_tune_in_made(self, kind):
        place = self.tune_place(kind)
        if place is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        player = self.tune_player_in(kind)
        if player is None:
            return None, None
        setlist, name = self._choices.written_for_trial()
        scenes = setlist.get_song(name).get_scenes()
        slot = scenes[place].get_clip_slot(player) if place < len(scenes) and scenes[place].has_clip_slot(player) else None
        if slot is None:
            return None, None
        return slot.get_pattern_name(), setlist.get_pattern(slot.get_pattern_name()).to_data()

    # Who plays the tune: one player for the song, and another, or nobody, for a kind of section. The player given the tune plays it
    # in place of the usual part there, and the player who had it rests.

    def tune_players_offered(self):
        """Return the players who may be given the tune, by name: every player of notes in the band but the bass."""
        return [role for role in self._choices.get_band().roles_in() if self._choices.get_sounds().has_sound(role) and self._choices.get_band().role_named(role).get(arranger.PLAYER) != players_values.BASS]

    def tune_played_by(self):
        """Return the player who plays the tune in the song: the one chosen while in the band, or else the player the genre gives the tune."""
        chosen = self._choices.get_extra(arranger.TUNE_BY_SONG)
        return chosen if chosen in self.tune_players_offered() else self._choices.get_band().tune_player()

    def set_tune_played_by(self, role):
        """Give the song's tune to a player, or back to the player the genre gives it with None."""
        if role is not None and role not in self.tune_players_offered():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_TUNE_PLAYER.format(value=role))
        self._choices.set_extra(name=arranger.TUNE_BY_SONG, value=None if role is None or role == self._choices.get_band().tune_player() else role)
        self._choices.clear_answers()

    def tune_played_by_in(self, kind):
        """Return what a kind of section says of who plays its tune: a player's name, NOBODY, or None where the kind goes by the song."""
        chosen = (self._choices.get_extra(arranger.TUNE_BY) or {}).get(kind)
        return chosen if chosen == arranger.NOBODY or chosen in self.tune_players_offered() else None

    def tune_player_in(self, kind):
        """Return the player who plays the tune in a kind of section, or None where nobody does."""
        chosen = self.tune_played_by_in(kind)
        if chosen == arranger.NOBODY:
            return None
        return chosen or self.tune_played_by()

    def set_tune_played_by_in(self, *, kind, role):
        """Give a kind of section's tune to a player, to nobody with NOBODY, or back to the song's player with None."""
        if self.tune_place(kind) is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        if role is not None and role != arranger.NOBODY and role not in self.tune_players_offered():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_TUNE_PLAYER.format(value=role))
        by = dict(self._choices.get_extra(arranger.TUNE_BY) or {})
        if role is None:
            by.pop(kind, None)
        else:
            by[kind] = role
        self._choices.set_extra(name=arranger.TUNE_BY, value=by or None)
        self._choices.clear_answers()

    # A tune written by hand and the chords under it: when the chords change, the tune can be fitted to them.

    def own_tune_chords(self):
        """Return, for each kind of section whose tune was written by hand, the chords its first section hears, so that a change of
        chords under such a tune can be told. A kind whose chords cannot be told is left out."""
        heard = {}
        for kind in (self._choices.get_extra(arranger.OWN_TUNES) or {}):
            try:
                place = self.tune_place(kind)
                if place is not None:
                    heard[kind] = copy.deepcopy(self._choices.section(place).own(field=arranger.CHORDS) or (self._choices.made_song_plan().chords_at(place) if self._choices.has_song_plan() else self._choices.section(place).chords_at()))
            except (ValueError, KeyError, IndexError, SongFileError):
                continue
        return heard

    def fit_tune(self, kind):
        """Fit a kind of section's tune, written by hand, to the chords its section now hears: each long note that is no note of its
        chord moves to the nearest note of the chord, and short notes stay (tune_fit.py)."""
        chords = self.own_tune_chords().get(kind)
        if chords is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        own = self._choices.get_extra(arranger.OWN_TUNES)[kind]
        self.set_tune_pattern(kind=kind, pattern=tune_fit.fitted(pattern=own, chords=chords, bar=bar_length(self._choices.meter())))

    def tune_take(self, kind):
        """Return which take of its tune a kind of section has: the first, the tune the choices write, or a later one asked for."""
        return (self._choices.get_extra(wizard_limits.TUNE_TAKES) or {}).get(kind, wizard_limits.FIRST_TUNE_TAKE)

    def new_tune_take(self, kind):
        """Have another tune written for a kind of section, the rest of the song left as it was. Notes written by hand for the kind
        are given up for it."""
        if self.tune_place(kind) is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        self._choices.set_extra(name=wizard_limits.TUNE_TAKES, value={**(self._choices.get_extra(wizard_limits.TUNE_TAKES) or {}), kind: self.tune_take(kind) + 1})
        self._keep_own_tune(kind=kind, pattern=None)
        self._choices.clear_answers()

    def _keep_own_tune(self, *, kind, pattern):
        """Keep a pattern as the notes written by hand of a kind of section's tune, or let them go with None."""
        own = dict(self._choices.get_extra(arranger.OWN_TUNES) or {})
        if pattern is None:
            own.pop(kind, None)
        else:
            own[kind] = copy.deepcopy(pattern)
        self._choices.set_extra(name=arranger.OWN_TUNES, value=own or None)

    def taken_tunes(self):
        """The pattern of each kind of section whose tune is a later take and not written by hand, by kind."""
        takes = (self._choices.get_extra(wizard_limits.TUNE_TAKES) or {})
        own = (self._choices.get_extra(arranger.OWN_TUNES) or {})
        taken = {}
        for kind in sorted(takes):
            if kind not in own and takes[kind] != wizard_limits.FIRST_TUNE_TAKE:
                pattern = self._choices.remembered(key=(wizard_limits.TUNE_TAKEN_ANSWER, kind), compute=lambda kind=kind: self._tune_taken(kind=kind, take=takes[kind]))
                if pattern is not None:
                    taken[kind] = pattern
        return taken

    def _tune_taken(self, *, kind, take):
        """The tune another take draws for a kind of section: the kind's tune in the song these choices would make from a seed of
        the take's own, with the same chords and no tune of another take or written by hand, or None where that song has none."""
        other = self._choices.made_again()
        other.set_extra(name=wizard_limits.TUNE_TAKES, value=None)
        other.set_extra(name=arranger.OWN_TUNES, value=None)
        trait = self._choices.progression_trait()
        drawn = self._choices.progressions_by_chance()[:1]
        if trait is not None and drawn:
            other.get_band().set_way(trait=trait, value=drawn[0])
        other.set_seed(zlib.crc32(wizard_limits.TUNE_TAKE_SEED.format(seed=self._choices.get_seed(), kind=kind, take=take).encode()) % (wizard_limits.LAST_SEED + 1))
        try:
            return other.get_tunes()._found_tune_in_made(kind)[1]
        except (ValueError, IndexError, KeyError, SongFileError):
            return None

    def set_tune_pattern(self, *, kind, pattern):
        """Keep a pattern's data as a kind of section's own tune, or forget the person's own with None, so that the choices write the
        tune again. A kind with no tune, and a pattern the song cannot be made with, are refused and nothing changes."""
        if self.tune_place(kind) is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        before = copy.deepcopy(self._choices.get_extra(arranger.OWN_TUNES))
        self._keep_own_tune(kind=kind, pattern=pattern)
        self._choices.clear_answers()
        try:
            self._choices.written_for_trial()
        except Exception as problem:
            self._choices.set_extra(name=arranger.OWN_TUNES, value=None)
            if before is not None:
                self._choices.set_extra(name=arranger.OWN_TUNES, value=before)
            self._choices.clear_answers()
            raise ValueError(errors.ERR_WIZARD_TUNE_PATTERN.format(problem=problem)) from problem
