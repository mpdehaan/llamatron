# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's choices of the tunes: one for each kind of section the tune's player plays in, who plays the tune, its takes, and the notes written by hand."""

import copy

from llamatron.model.file.song_file_error import SongFileError
from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, players as players_values, tune_fit, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import bar_length
from llamatron.wizards.create_song.choices_part import cached_until_choices_change, ChoicesPart


class TuneChoices(ChoicesPart):
    """What was chosen of the song's tunes. Who plays the tune, the takes and the notes written by hand are part of what is laid over the song's picks, which the arranger reads, and are reached through the choices."""

    __slots__ = ()

    # The tunes: one for each kind of section the tune's player plays in. A tune is written by the choices until a person edits its
    # pattern by hand; from then on the pattern is the person's own, and no choice writes over it.

    def tune_kinds(self):
        """Return each kind of section the song has a tune in, once, in the form's order: the kinds whose sections the tune's player plays in."""
        player = self._choices.get_band().tune_player()
        kinds = []
        for place, kind in enumerate(self._choices.get_song_form().section_kinds_in_form()):
            if kind not in kinds and player is not None and player in self._choices.section(place).plays() and not self._choices.section(place).is_held():
                kinds.append(kind)
        return kinds

    def tune_place(self, kind):
        """Return the place in the form of the first section of a kind the tune's player plays in, or None."""
        band = self._choices.get_band()
        places = self._choices.places_of(kind=kind, player=band.tune_player())
        if places:
            return places[0]
        return None

    def tune_is_own(self, kind):
        """Return whether a kind of section's tune was written by hand, so that nothing the wizard chooses writes over it."""
        return kind in (self._choices.get_extra(arranger.OWN_TUNES) or {})

    def tune_pattern_name(self, kind):
        """Return the name of the pattern that holds a kind of section's tune in the set the choices make, or None where the set has none."""
        return self.made_tune(kind)[0]

    def tune_pattern(self, kind):
        """Return a kind of section's tune as a pattern's data: the person's own, or the tune the choices write as they stand.
        None where no tune is made."""
        own_tunes = self._choices.get_extra(arranger.OWN_TUNES) or {}
        own = own_tunes.get(kind)
        if own is None:
            _, own = self.made_tune(kind)
        return copy.deepcopy(own)

    @cached_until_choices_change
    def made_tune(self, kind):
        """Return the name and the data of the pattern the tune's player plays in the first section of a kind, in the set the
        choices make, found once for the choices as they stand, since a page asks at every key and the answer means making the song."""
        place = self.tune_place(kind)
        if place is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        player = self.tune_player_in(kind)
        if player is None:
            return None, None
        return self._choices.pattern_played_at(place=place, role=player)

    # Who plays the tune: one player for the song, and another, or nobody, for a kind of section. The player given the tune plays it
    # in place of the usual part there, and the player who had it rests.

    def tune_players_offered(self):
        """Return the players who may be given the tune, by name: every player of notes in the band but the bass."""
        band = self._choices.get_band()
        sounds = self._choices.get_sounds()
        offered = []
        for role in band.roles_in():
            entry = band.role_named(role)
            if sounds.has_sound(role) and entry.get(arranger.PLAYER) != players_values.BASS:
                offered.append(role)
        return offered

    def tune_played_by(self):
        """Return the player who plays the tune in the song: the one chosen while in the band, or else the player the genre gives the tune."""
        chosen = self._choices.get_extra(arranger.TUNE_BY_SONG)
        return chosen if chosen in self.tune_players_offered() else self._choices.get_band().tune_player()

    def set_tune_played_by(self, role):
        """Give the song's tune to a player, or back to the player the genre gives it with None."""
        if role is not None and role not in self.tune_players_offered():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_TUNE_PLAYER.format(value=role))
        band = self._choices.get_band()
        chosen = role
        if role == band.tune_player():
            chosen = None
        self._choices.set_extra(name=arranger.TUNE_BY_SONG, value=chosen)
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
        """Return, for each kind of section whose tune was written by hand, the chords its first section hears, so that a change
        of chords under such a tune can be told. A kind whose chords cannot be told is left out."""
        heard = {}
        for kind in self._choices.get_extra(arranger.OWN_TUNES) or {}:
            try:
                chords = self._chords_heard_by(kind)
            except (ValueError, KeyError, IndexError, SongFileError):
                continue
            if chords is not None:
                heard[kind] = chords
        return heard

    def _chords_heard_by(self, kind):
        """Return a copy of the chords the first section of a kind with the tune hears: its own, the plan's or the progression's;
        or None where no section of the kind has the tune."""
        place = self.tune_place(kind)
        if place is None:
            return None
        section = self._choices.section(place)
        own = section.own(field=wizard_names.ARRANGER_CHORDS)
        if own:
            return own
        if self._choices.has_song_plan():
            plan = self._choices.made_song_plan()
            return copy.deepcopy(plan.chords_at(place))
        return copy.deepcopy(section.chords_at())

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
        """Have another tune written for a kind of section, the rest of the song left as it was. Notes written by hand for the
        kind are given up for it."""
        if self.tune_place(kind) is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        takes = dict(self._choices.get_extra(wizard_limits.TUNE_TAKES) or {})
        takes[kind] = self.tune_take(kind) + 1
        self._choices.set_extra(name=wizard_limits.TUNE_TAKES, value=takes)
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
                pattern = self._tune_taken(kind=kind, take=takes[kind])
                if pattern is not None:
                    taken[kind] = pattern
        return taken

    @cached_until_choices_change
    def _tune_taken(self, *, kind, take):
        """Return the tune another take draws for a kind of section: the kind's tune in the song these choices would make from a
        seed of the take's own, with the same chords and no tune of another take or written by hand, or None where that song has none."""
        seed_text = wizard_limits.TUNE_TAKE_SEED.format(seed=self._choices.get_seed(), kind=kind, take=take)
        other = self._choices.again_for_take(cleared=(wizard_limits.TUNE_TAKES, arranger.OWN_TUNES), seed_text=seed_text)
        tunes = other.get_tunes()
        try:
            _, pattern = tunes.made_tune(kind)
        except (ValueError, IndexError, KeyError, SongFileError):
            return None
        return pattern

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
