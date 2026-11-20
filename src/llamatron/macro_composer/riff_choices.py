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

"""The song wizard's choices of the riffs: the riffs written, who knows each, and who plays which in each kind of section."""

import copy

from llamatron.composition import naming
from llamatron.composition.file_format import PatternSetting
from llamatron.composition.song_file_error import SongFileError
from llamatron.macro_composer import arranger, notation as tune_notation, riffs as riffs_values, wizard_limits
from llamatron.macro_composer.arranger import arranged, bar_length, in_octaves_of
from llamatron.macro_composer.choices_part import ChoicesPart
from llamatron.macro_composer.riffs import bars_of as riff_bars_of, flattened_in, line_of as riff_line_of
from llamatron.strings import errors, macro_composer as composer_text, names as names_text


class RiffChoices(ChoicesPart):
    """What was chosen of the song's riffs: the riffs, each with its name, the player it was written for and how it is drawn; the riffs each player knows; and the riff each player plays in a kind of section."""

    __slots__ = ('_held',)

    def __init__(self, *, choices):
        ChoicesPart.__init__(self, choices=choices)
        self.reset()

    def reset(self):
        """Go back to a song with no riff."""
        # The riffs, who knows each and who plays which where, each under its name of RIFFS_KEPT once the song has any.
        self._held = {}

    # What a song keeps of the riffs.

    def to_data(self):
        """Return what a song keeps of the riffs, as plain data the caller may change."""
        return copy.deepcopy(self._held)

    def read(self, data):
        """Take the riffs out of what a song kept, in place of the riffs held."""
        self._held = {kept: data[kept] for kept in wizard_limits.RIFFS_KEPT if kept in data}

    def written_count(self, *, by_hand):
        """Return how many riffs have notes written by hand, or how many have not."""
        return len([entry for entry in self._held.get(wizard_limits.RIFF_BOOK, []) if (entry.get(arranger.RIFF_OWN) is not None) == by_hand])

    def play_in(self, *, kind, role, riff):
        """Have a player play a riff in a kind of section, or none of them with None."""
        played = self._held.setdefault(wizard_limits.RIFFS_PLAYED, {}).setdefault(kind, {})
        played.pop(role, None)
        if riff is not None:
            played[role] = riff
        self._tidy_riffs()

    def play_nowhere(self):
        """Have nobody play a riff in any kind of section, the riffs themselves kept."""
        self._held.pop(wizard_limits.RIFFS_PLAYED, None)

    def play_alone(self, *, kind, role, riff):
        """Have one riff played, by one player in one kind of section, and no other anywhere, the riff moving with the chords as a riff does until told otherwise."""
        self._riff_entry(riff).pop(riffs_values.RIFF_WITH_CHORDS, None)
        self._held[wizard_limits.RIFFS_PLAYED] = {kind: {role: riff}}

    # The riffs: figures of a bar or two that a player repeats in place of the accompaniment. A riff is written for one player of
    # the band, in that player's octave, and exists whether or not anybody plays it yet; each player knows some of the song's
    # riffs; and in each kind of section a player plays the accompaniment, the melody or one of the riffs the player knows.

    def _riff_able(self):
        """The players who can play a riff: those whose part in the song is a figure, found by asking for a riff from everybody everywhere."""
        trial = self._choices.trial_for_riffs()
        trial.clear_answers()
        trial.get_riffs().play_nowhere()
        trial.set_extra(name=riffs_values.RIFF, value={riffs_values.RIFF_ROLES: self._choices.get_band().roles_in(), riffs_values.RIFF_KINDS: self._choices.get_song_form().section_kinds()})
        try:
            parts = arranged(style=self._choices.style(), song=trial.song_picks(wizard_limits.PREVIEW_NAME))[arranger.PARTS]
        except (ValueError, KeyError, SongFileError):
            return []
        return [role for role in self._choices.get_band().roles_in() if composer_text.MSG_PART_OF_SECTION.format(role, riffs_values.RIFF) in parts]

    def riff_instruments(self):
        """Return the players of the band a riff can be written for, by name: those whose part in the song is a figure, never the drummer."""
        return list(self._choices.remembered(key=wizard_limits.RIFF_ABLE_ANSWER, compute=self._riff_able)) if self._choices.is_ready() else []

    def _riff_able_in(self, kind):
        """The players a riff would be heard from in a kind of section, found by asking for one there from every player of a figure
        with no other riff in the song: a player who sits the kind out, or whose sections there a riff's bars do not fill, has none."""
        able = self.riff_instruments()
        trial = self._choices.trial_for_riffs()
        trial.get_riffs().play_nowhere()
        trial.set_extra(name=arranger.MORE_RIFFS, value=[{arranger.NAME: wizard_limits.TRIAL_RIFF, riffs_values.RIFF_ROLES: able, riffs_values.RIFF_KINDS: [kind]}])
        try:
            parts = arranged(style=self._choices.style(), song=trial.song_picks(wizard_limits.PREVIEW_NAME))[arranger.PARTS]
        except (ValueError, KeyError, SongFileError):
            return []
        return [role for role in able if composer_text.MSG_PART_OF_SECTION.format(role, wizard_limits.TRIAL_RIFF) in parts]

    def riff_players_in(self, kind):
        """Return the players a riff can be heard from in a kind of section, by name."""
        if not self._choices.is_ready() or kind not in self._choices.get_song_form().section_kinds_in_form() or self.riff_place(kind) is None:
            return []
        return list(self._choices.remembered(key=(wizard_limits.RIFF_ABLE_ANSWER, kind), compute=lambda: self._riff_able_in(kind)))

    def riff_place(self, kind):
        """Return the place in the form of the first section of a kind that is played and not one held chord, where a riff of the kind is heard, or None."""
        places = range(len(self._choices.get_song_form().section_labels()))
        return next((place for place in places if self._choices.section(place).kind() == kind and not self._choices.section(place).is_held()), None)

    def _riffs(self):
        """The song's riffs whose player is in the band and can play one: a riff of a player who is out waits, unseen, for the player to come back."""
        able = self.riff_instruments()
        return [entry for entry in self._held.get(wizard_limits.RIFF_BOOK, []) if entry[arranger.RIFF_FOR] in able]

    def _riff_entry(self, riff):
        found = next((entry for entry in self._riffs() if entry[arranger.NAME] == riff), None)
        if found is None:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_RIFF.format(value=riff))
        return found

    def riff_names(self):
        """Return the names of the song's riffs, in the order they were made."""
        return [entry[arranger.NAME] for entry in self._riffs()]

    def riffs_for(self, role):
        """Return the names of the riffs written for a player, in the order they were made."""
        return [entry[arranger.NAME] for entry in self._riffs() if entry[arranger.RIFF_FOR] == role]

    def riff_written_for(self, riff):
        """Return the player a riff was written for."""
        return self._riff_entry(riff)[arranger.RIFF_FOR]

    def riff_setting(self, *, riff, field):
        """Return how a riff is drawn in one way: how many bars, what it is made of, what fills its gaps or what it does as the chords change."""
        return self._riff_entry(riff).get(field, wizard_limits.RIFF_SETTINGS[field][0])

    def riff_is_edited(self, riff):
        """Return whether a riff's notes were written by hand, so that only regenerating writes over them."""
        return self._riff_entry(riff).get(arranger.RIFF_OWN) is not None

    def riff_bar_count(self, riff):
        """Return how many bars a riff lasts."""
        entry = self._riff_entry(riff)
        eighths = self.riff_steps_in_bar()
        if entry.get(arranger.RIFF_OWN) is not None:
            return max(entry[arranger.RIFF_OWN].get(PatternSetting.STEPS, eighths) // eighths, 1)
        return riff_bars_of(line=riff_line_of(riff=entry, seed=0, eighths=eighths, flattened=flattened_in(self._choices.get_scale_type())), eighths=eighths)

    def riff_steps_in_bar(self):
        """Return how many steps, eighths, a bar of a riff has."""
        return int(bar_length(self._choices.meter()) * arranger.EIGHTHS_IN_WHOLE)

    def riff_kinds_used(self, riff):
        """Return the kinds of section a riff is played in by anybody in the band, in the form's order."""
        self._riff_entry(riff)
        played = self.riffs_played()
        return [kind for kind in dict.fromkeys(self._choices.get_song_form().section_kinds_in_form()) if riff in played.get(kind, {}).values()]

    def add_riff(self, *, role, settings=None):
        """Write a new riff for a player and return its name: the player knows the riff, and nobody plays it yet. What is no
        setting of a riff, and a player a riff cannot be written for, are refused."""
        settings = dict(settings or {})
        if role not in self.riff_instruments() or any(field not in wizard_limits.NEW_RIFF_SETTINGS or value not in wizard_limits.RIFF_SETTINGS[field] for field, value in settings.items()):
            raise ValueError(errors.ERR_WIZARD_RIFF.format(value=(role, settings)))
        riff = naming.new_name(word=names_text.MSG_NEW_RIFF_WORD, taken=self._riff_names_taken())
        chosen = {field: value for field, value in settings.items() if value != wizard_limits.RIFF_SETTINGS[field][0]}
        self._keep_riff({**chosen, arranger.NAME: riff, arranger.RIFF_FOR: role, arranger.RIFF_DRAWN_AS: riff})
        return riff

    def _riff_names_taken(self):
        """Every riff's name, those of players who are out included, which wait."""
        return [entry[arranger.NAME] for entry in self._held.get(wizard_limits.RIFF_BOOK, [])]

    def _keep_riff(self, entry):
        """Put a riff among the song's, known by the player it was written for."""
        self._held.setdefault(wizard_limits.RIFF_BOOK, []).append(entry)
        known = self._held.setdefault(wizard_limits.RIFFS_KNOWN, {}).setdefault(entry[arranger.RIFF_FOR], [])
        known.append(entry[arranger.NAME])
        self._choices.clear_answers()

    def rename_riff(self, *, riff, name):
        """Give a riff another name, wherever the riff is known and played; its notes stay. A name another riff has is refused."""
        entry = self._riff_entry(riff)
        if name != riff and name.lower() in [taken.lower() for taken in self._riff_names_taken() if taken != riff]:
            raise ValueError(errors.ERR_WIZARD_RIFF_NAME_TAKEN.format(name=name))
        entry[arranger.NAME] = name
        for known in self._held.get(wizard_limits.RIFFS_KNOWN, {}).values():
            known[:] = [name if other == riff else other for other in known]
        for by in self._held.get(wizard_limits.RIFFS_PLAYED, {}).values():
            for role in by:
                if by[role] == riff:
                    by[role] = name
        self._choices.clear_answers()

    def copy_riff(self, *, riff, role):
        """Copy a riff for a player and return the copy's name: the same notes, in the player's own octave, known by the player
        and played by nobody yet."""
        entry = self._riff_entry(riff)
        if role not in self.riff_instruments():
            raise ValueError(errors.ERR_WIZARD_RIFF.format(value=(riff, role)))
        copied = copy.deepcopy(entry)
        copied[arranger.NAME] = naming.copy_name(name=riff, taken=self._riff_names_taken())
        if copied.get(arranger.RIFF_OWN) is not None:
            copied[arranger.RIFF_OWN] = in_octaves_of(pattern=copied[arranger.RIFF_OWN], by=self._choices.get_band().role_named(role)[tune_notation.OCTAVE] - self._choices.get_band().role_named(entry[arranger.RIFF_FOR])[tune_notation.OCTAVE], group=role)
        copied[arranger.RIFF_FOR] = role
        self._keep_riff(copied)
        return copied[arranger.NAME]

    def delete_riff(self, riff):
        """Take a riff out of the song: nobody knows it any more, and whoever played it plays the accompaniment again."""
        entry = self._riff_entry(riff)
        self._held[wizard_limits.RIFF_BOOK].remove(entry)
        for known in self._held.get(wizard_limits.RIFFS_KNOWN, {}).values():
            known[:] = [other for other in known if other != riff]
        for by in self._held.get(wizard_limits.RIFFS_PLAYED, {}).values():
            for role in [role for role, played in by.items() if played == riff]:
                del by[role]
        self._tidy_riffs()

    def _tidy_riffs(self):
        """Leave nothing empty among what the song keeps of its riffs."""
        for kept in (wizard_limits.RIFFS_KNOWN, wizard_limits.RIFFS_PLAYED):
            held = {name: value for name, value in self._held.get(kept, {}).items() if value}
            self._held.pop(kept, None)
            if held:
                self._held[kept] = held
        if not self._held.get(wizard_limits.RIFF_BOOK):
            self._held.pop(wizard_limits.RIFF_BOOK, None)
        self._choices.clear_answers()

    def regenerate_riff(self, riff):
        """Have other notes written for a riff, with nothing kept of the old ones, written by hand or not."""
        entry = self._riff_entry(riff)
        entry[riffs_values.RIFF_TAKE] = entry.get(riffs_values.RIFF_TAKE, riffs_values.FIRST_TAKE) + 1
        entry.pop(arranger.RIFF_OWN, None)
        self._choices.clear_answers()

    def set_riff_pattern(self, *, riff, pattern):
        """Keep a pattern's data as a riff's own notes, as the player the riff was written for plays them. A pattern the song
        cannot be made with is refused and nothing changes."""
        entry = self._riff_entry(riff)
        before = copy.deepcopy(self._held.get(wizard_limits.RIFF_BOOK))
        entry[arranger.RIFF_OWN] = copy.deepcopy(pattern)
        self._choices.clear_answers()
        try:
            self.riff_heard(riff)
            self._choices.written_for_trial()
        except Exception as problem:
            # A pattern written by hand can fail in any way a set's data can, as a tune's can.
            self._held[wizard_limits.RIFF_BOOK] = before
            self._choices.clear_answers()
            raise ValueError(errors.ERR_WIZARD_RIFF_UNMADE.format(value=riff, problem=problem)) from None

    def riff_heard(self, riff):
        """Return where a riff is heard alone, played or not, as the set a song is made in, the song's name, the place of a
        section in its form, the player's track and the name of the pattern that holds the riff's notes: the song the choices
        make with the riff's own player playing it, moving with each chord, in the first kind of section that can hold it."""
        return self._choices.remembered(key=(wizard_limits.RIFF_HEARD_ANSWER, riff), compute=lambda: self._riff_heard(riff))

    def _riff_heard(self, riff):
        entry = self._riff_entry(riff)
        role = entry[arranger.RIFF_FOR]
        kind = next((kind for kind in dict.fromkeys(self._choices.get_song_form().section_kinds_in_form()) if role in self.riff_players_in(kind) and self._choices.section(self.riff_place(kind)).bars() % self.riff_bar_count(riff) == 0), None)
        if kind is None:
            raise ValueError(errors.ERR_WIZARD_RIFF_FITS_NOWHERE.format(riff=riff))
        trial = self._choices.trial_for_riffs()
        trial.get_riffs().play_alone(kind=kind, role=role, riff=riff)
        # The melody stays with whoever has it, so the riff's player is free of it in the trial's section.
        if trial.get_tunes().tune_player_in(kind) == role:
            trial.set_extra(name=arranger.TUNE_BY, value={**(trial.get_extra(arranger.TUNE_BY) or {}), kind: arranger.NOBODY})
        setlist, name = trial.written_for_trial()
        pattern = composer_text.MSG_PART_OF_SECTION.format(role, riff)
        if not setlist.has_pattern(pattern):
            raise ValueError(errors.ERR_WIZARD_RIFF_FITS_NOWHERE.format(riff=riff))
        return setlist, name, self.riff_place(kind), role, pattern

    # Riff Assign: the riffs each player knows. A player knows the riffs written for the player until one is taken away, and may be
    # given a riff written for another player, which the player then plays in the player's own octave.

    def riffs_known_by(self, role):
        """Return the names of the riffs a player knows, in the order the player was given them."""
        names = self.riff_names()
        return [riff for riff in self._held.get(wizard_limits.RIFFS_KNOWN, {}).get(role, []) if riff in names] if role in self.riff_instruments() else []

    def riffs_to_give(self, role):
        """Return the names of the song's riffs a player does not know yet."""
        known = self.riffs_known_by(role)
        return [riff for riff in self.riff_names() if riff not in known] if role in self.riff_instruments() else []

    def give_riff(self, *, role, riff):
        """Have a player know a riff, to play wherever Section Players says."""
        if riff not in self.riffs_to_give(role):
            raise ValueError(errors.ERR_WIZARD_RIFF.format(value=(riff, role)))
        self._held.setdefault(wizard_limits.RIFFS_KNOWN, {}).setdefault(role, []).append(riff)
        self._choices.clear_answers()

    def kinds_playing(self, *, role, riff):
        """Return the kinds of section a player plays a riff in, in the form's order."""
        played = self.riffs_played()
        return [kind for kind in dict.fromkeys(self._choices.get_song_form().section_kinds_in_form()) if played.get(kind, {}).get(role) == riff]

    def take_riff_from(self, *, role, riff):
        """Have a player know a riff no longer: wherever the player played it, the player plays the accompaniment again."""
        if riff not in self.riffs_known_by(role):
            raise ValueError(errors.ERR_WIZARD_RIFF.format(value=(riff, role)))
        self._held[wizard_limits.RIFFS_KNOWN][role].remove(riff)
        for by in self._held.get(wizard_limits.RIFFS_PLAYED, {}).values():
            if by.get(role) == riff:
                del by[role]
        self._tidy_riffs()

    # Section Players: what each player plays in each kind of section. A player plays one thing in a section: the accompaniment the
    # genre writes, the melody, or a riff the player knows.

    def riffs_played(self):
        """What the song keeps of who plays which riff, by kind of section and player, leaving out a riff the player no longer
        knows and a player who has the melody there."""
        played = {}
        for kind, by in self._held.get(wizard_limits.RIFFS_PLAYED, {}).items():
            here = {role: riff for role, riff in by.items() if riff in self.riffs_known_by(role)}
            if here:
                played[kind] = here
        return played

    def riffs_arranged(self):
        """The song's riffs as the arranger places them: for each riff and each player who plays it, the kinds of section the
        player plays it in, with who the riff was written for and the name its notes are drawn by."""
        if not self._held.get(wizard_limits.RIFFS_PLAYED):
            # Nobody plays a riff, which is also so of every song made to find who could.
            return []
        played = self.riffs_played()
        arranged_riffs = []
        for entry in self._riffs():
            for role in self._choices.get_band().roles_in():
                kinds = [kind for kind, by in played.items() if by.get(role) == entry[arranger.NAME] and self._choices.section_part(kind=kind, role=role) == entry[arranger.NAME]]
                if kinds:
                    arranged_riffs.append({**copy.deepcopy(entry), riffs_values.RIFF_ROLES: [role], riffs_values.RIFF_KINDS: kinds})
        return arranged_riffs

    def remove_riffs(self, goes):
        """Take out of the song every riff a test says goes, with who knows it and who plays it."""
        gone = [entry[arranger.NAME] for entry in self._held.get(wizard_limits.RIFF_BOOK, []) if goes(entry)]
        for kept in (riffs_values.RIFF, arranger.MORE_RIFFS):
            self._held.pop(kept, None)
        self._held[wizard_limits.RIFF_BOOK] = [entry for entry in self._held.get(wizard_limits.RIFF_BOOK, []) if entry[arranger.NAME] not in gone]
        for known in self._held.get(wizard_limits.RIFFS_KNOWN, {}).values():
            known[:] = [riff for riff in known if riff not in gone]
        for by in self._held.get(wizard_limits.RIFFS_PLAYED, {}).values():
            for role in [role for role, riff in by.items() if riff in gone]:
                del by[role]
        self._tidy_riffs()

    def take_riff_of_genre(self):
        """Give the song the riff its kind of music is built on, where the subgenre has one and its players can play it: written
        for the first of its players, known by each, and played by each in the intro, the outro and the verses, where the form
        has them. A person may then change the riff or delete it. A riff written by hand is kept from genre to genre."""
        self.remove_riffs(lambda entry: entry.get(wizard_limits.RIFF_OF_GENRE) and entry.get(arranger.RIFF_OWN) is None)
        usual = self._choices.style().get(riffs_values.RIFF)
        if not usual:
            return
        players = [role for role in usual.get(riffs_values.RIFF_ROLES, []) if role in self.riff_instruments()]
        if not players:
            return
        riff = naming.new_name(word=names_text.MSG_NEW_RIFF_WORD, taken=self._riff_names_taken())
        settings = {field: usual[field] for field, ways in wizard_limits.RIFF_SETTINGS.items() if usual.get(field) in ways[1:]}
        self._keep_riff({**settings, arranger.NAME: riff, arranger.RIFF_FOR: players[0], arranger.RIFF_DRAWN_AS: riff, wizard_limits.RIFF_OF_GENRE: True})
        for role in players[1:]:
            self._held[wizard_limits.RIFFS_KNOWN].setdefault(role, []).append(riff)
        for kind in (self._choices.get_song_form().intro_kind() or wizard_limits.INTRO_KIND, wizard_limits.OUTRO_KIND, wizard_limits.VERSE_KIND):
            here = {role: riff for role in players if role in self.riff_players_in(kind) and self._choices.section_part(kind=kind, role=role) == wizard_limits.ACCOMPANIMENT}
            if here:
                self._held.setdefault(wizard_limits.RIFFS_PLAYED, {})[kind] = here
        self._choices.clear_answers()

    def take_riffs_of_older_song(self):
        """Bring the riffs of a song kept before riffs stood on their own over to the song's riffs: the song's first riff and each
        riff added, written for its first player, known by each of its players and played by each in its kinds of section."""
        older = [entry for entry in [self._choices.get_extra(riffs_values.RIFF), *(self._choices.get_extra(arranger.MORE_RIFFS) or [])] if isinstance(entry, dict) and entry.get(riffs_values.RIFF_ROLES)]
        self._choices.set_extra(name=riffs_values.RIFF, value=None)
        self._choices.set_extra(name=arranger.MORE_RIFFS, value=None)
        for entry in older:
            name = entry.get(arranger.NAME) or naming.new_name(word=names_text.MSG_NEW_RIFF_WORD, taken=self._riff_names_taken())
            kept = {field: value for field, value in entry.items() if field in wizard_limits.RIFF_SETTINGS or field in (riffs_values.RIFF_TAKE, arranger.RIFF_OWN)}
            # The first riff's notes were drawn by the song's seed alone, which no name stands for: a kept song draws a new seed all the same.
            self._held.setdefault(wizard_limits.RIFF_BOOK, []).append({**kept, arranger.NAME: name, arranger.RIFF_FOR: entry[riffs_values.RIFF_ROLES][0], arranger.RIFF_DRAWN_AS: name})
            for role in entry[riffs_values.RIFF_ROLES]:
                self._held.setdefault(wizard_limits.RIFFS_KNOWN, {}).setdefault(role, []).append(name)
                for kind in entry.get(riffs_values.RIFF_KINDS, []):
                    self._held.setdefault(wizard_limits.RIFFS_PLAYED, {}).setdefault(kind, {})[role] = name
