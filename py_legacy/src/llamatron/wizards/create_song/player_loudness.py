# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How loud one player of the band is, as the song wizard's choices hold it: the player's four levels and dynamics."""

from llamatron.music_theory.composing import loudness, notation as tune_notation
from llamatron.music_theory.composing.loudness import drum_levels, note_levels, with_own
from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, wizard_limits, wizard_names
from llamatron.wizards.create_song.own_values import is_integer_between


class PlayerLoudness:
    """How loud one player is: the four levels the genre gives the player, with the song's own in their places, and how far
    the player's loud and soft notes lie from the normal ones. Reached as choices.player(role).loudness()."""

    __slots__ = ('_choices', '_role')

    def __init__(self, *, choices, role):
        self._choices = choices
        self._role = role

    def _role_entry(self):
        """Return what the genre writes of the player."""
        band = self._choices.get_band()
        return band.role_named(self._role)

    def has_levels(self):
        """Return whether the player has levels to choose: a player in the band who drums or plays notes at a velocity."""
        band = self._choices.get_band()
        player = self._choices.player(self._role)
        if not self._choices.is_ready() or self._role not in band.roles() or not player.is_in():
            return False
        entry = self._role_entry()
        return bool(entry.get(arranger.DRUMS)) or tune_notation.VELOCITY in entry

    def levels_of_style(self):
        """Return the four levels the genre gives the player: the whole kit's for the drummer, and a player of notes' from the
        player's velocity."""
        entry = self._role_entry()
        if entry.get(arranger.DRUMS):
            style = self._choices.style()
            return drum_levels(style[arranger.LOUDNESS][arranger.DRUMS])
        return note_levels(entry[tune_notation.VELOCITY])

    def levels(self):
        """Return the player's four levels by name, the genre's with the song's own in their places; the drummer's are the
        whole kit's, which every piece of the kit follows in proportion."""
        return with_own(levels=self.levels_of_style(), own=self._own_levels())

    def _own_levels(self):
        """Return the levels of the song's own the player was given, by name, or None."""
        loudness_of = self._choices.get_extra(arranger.LOUDNESS) or {}
        return loudness_of.get(self._role)

    def level_is_own(self, level):
        """Return whether a level of the player's was given a velocity of the song's own."""
        own = self._own_levels() or {}
        return level in own

    def levels_offered(self):
        """Return the player's levels that the song plays, from the quietest up: a level no note of the player's is played at is
        not offered. Found by making the song with each level moved, and kept until a choice changes."""
        if not self.has_levels():
            return []
        return self._choices.offered(key=(wizard_limits.LEVELS_ANSWER, self._role), compute=self._levels_heard)

    def _levels_heard(self):
        """Return the player's levels that change the song when moved, each tried a little louder or softer than it is."""
        plain = self._parts_as_written()
        heard = []
        for level in tune_notation.LOUDNESS_LEVELS:
            trial = self._choices.copied_for_trial()
            trial_loudness = PlayerLoudness(choices=trial, role=self._role)
            now = trial_loudness.levels()[level]
            tried = now + wizard_limits.LEVEL_TRIAL
            if now > wizard_limits.MIDDLE_VELOCITY:
                tried = now - wizard_limits.LEVEL_TRIAL
            loudness_of = dict(trial.get_extra(arranger.LOUDNESS) or {})
            own = dict(loudness_of.get(self._role, {}))
            own[level] = tried
            loudness_of[self._role] = own
            trial.set_extra(name=arranger.LOUDNESS, value=loudness_of)
            self._dynamics_as_written(trial)
            if trial.patterns_of_song() != plain:
                heard.append(level)
        return heard

    def _dynamics_as_written(self, trial):
        """Give a trial of the choices the player's dynamics as the genre writes them, so that a level is heard apart from the normal one."""
        dynamics = trial.get_extra(arranger.DYNAMICS) or {}
        others = {player: given for player, given in dynamics.items() if player != self._role}
        trial.set_extra(name=arranger.DYNAMICS, value=others or None)

    def _parts_as_written(self):
        """Return the song's parts with the player's dynamics as the genre writes them."""
        trial = self._choices.copied_for_trial()
        self._dynamics_as_written(trial)
        return trial.patterns_of_song()

    def set_level(self, *, level, number):
        """Give the player a level of the song's own, a velocity, or give the level back to the genre with None."""
        is_number = number is None or is_integer_between(number, low=tune_notation.LOWEST_VELOCITY, high=tune_notation.HIGHEST_VELOCITY)
        if not self.has_levels() or level not in tune_notation.LOUDNESS_LEVELS or not is_number:
            raise ValueError(errors.ERR_WIZARD_LOUDNESS.format(low=tune_notation.LOWEST_VELOCITY, high=tune_notation.HIGHEST_VELOCITY, value=(self._role, level, number)))
        loudness_of = self._levels_copied()
        own = loudness_of.setdefault(self._role, {})
        own.pop(level, None)
        if number is not None and number != self.levels_of_style()[level]:
            own[level] = number
        kept = {player: levels for player, levels in loudness_of.items() if levels}
        self._choices.set_extra(name=arranger.LOUDNESS, value=kept or None)
        self._choices.clear_answers()

    def _levels_copied(self):
        """Return a copy of every player's levels of the song's own, by player."""
        loudness_of = self._choices.get_extra(arranger.LOUDNESS) or {}
        return {player: dict(levels) for player, levels in loudness_of.items()}

    def has_dynamics(self):
        """Return whether the player's dynamics are heard: whether the song differs with the player's notes all alike and at
        their widest, found by making the song both ways and kept until a choice changes."""
        if not self.has_levels():
            return False
        return self._choices.offered(key=(wizard_limits.DYNAMICS_ANSWER, self._role), compute=self._dynamics_are_heard)

    def _dynamics_are_heard(self):
        """Return whether the song differs with the player's dynamics at the least and at the most."""
        made = []
        for dynamics in (wizard_names.LEAST_DYNAMICS, wizard_names.MOST_DYNAMICS):
            trial = self._choices.copied_for_trial()
            dynamics_of = dict(trial.get_extra(arranger.DYNAMICS) or {})
            dynamics_of[self._role] = dynamics
            trial.set_extra(name=arranger.DYNAMICS, value=dynamics_of)
            made.append(trial.patterns_of_song())
        return made[0] != made[1]

    def get_dynamics(self):
        """Return how far the player's loud and soft notes lie from the normal ones."""
        dynamics_of = self._choices.get_extra(arranger.DYNAMICS) or {}
        return dynamics_of.get(self._role, loudness.USUAL_DYNAMICS)

    def set_dynamics(self, dynamics):
        """Say how far the player's loud and soft notes lie from the player's normal ones: not at all at the least, as the genre
        writes them in the middle, and twice as far at the most."""
        if not self.has_levels() or not is_integer_between(dynamics, low=wizard_names.LEAST_DYNAMICS, high=wizard_names.MOST_DYNAMICS):
            raise ValueError(errors.ERR_WIZARD_DYNAMICS.format(low=wizard_names.LEAST_DYNAMICS, high=wizard_names.MOST_DYNAMICS, value=dynamics))
        dynamics_of = dict(self._choices.get_extra(arranger.DYNAMICS) or {})
        dynamics_of.pop(self._role, None)
        if dynamics != loudness.USUAL_DYNAMICS:
            dynamics_of[self._role] = dynamics
        self._choices.set_extra(name=arranger.DYNAMICS, value=dynamics_of or None)
        self._choices.clear_answers()
