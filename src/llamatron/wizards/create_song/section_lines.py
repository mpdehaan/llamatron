# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The lines of one section of the song wizard's form: the plan of lines the section is played by, each line as the song
makes it, and what a line is given of its own."""

import copy

from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, line_edits, melody as melody_writer, notation as tune_notation, own_values, song_plan, wizard_limits
from llamatron.wizards.create_song.choices_part import cached_until_choices_change
from llamatron.wizards.create_song.own_values import checked_line


class SectionLines:
    """The lines of one section of the form, by the section's place: the plan the section is played by, and each line as the
    song makes it, with who plays it, its notes, whether it breathes and what it was given of its own. Reached as
    choices.section(place).lines()."""

    __slots__ = ('_choices', '_place')

    def __init__(self, *, choices, place):
        self._choices = choices
        self._place = place

    def answers_kept_by(self):
        """Return the choices that keep the lines' answers, and which section asked, by its place."""
        return self._choices, self._place

    def as_made(self):
        """Return the section's lines in order, each a mapping: who plays the line, its notes (line_edits.py) or None where
        nobody of the band plays the line, whether its breath and early note can be set (a new idea of the tune in a song in
        four, not the hook), and what the line was given of its own."""
        section = self._choices.section(self._place)
        # A section no longer in the form is refused.
        section.entry()
        return self._lines()

    def _own_lines(self):
        """Return what each line of the section was given of its own, by the line's number."""
        section = self._choices.section(self._place)
        return section.own(field=wizard_limits.LINES_OF_SECTION) or {}

    def plan(self):
        """Return the plan of lines the section is played by, with what its lines were given."""
        section = self._choices.section(self._place)
        if self._choices.has_song_plan():
            given = self._plan_given()
            if given is not None:
                return given
        return self._choices.plan_with_lines(kind=section.kind(), plan=None, lines=self._own_lines())

    def _plan_given(self):
        """Return the plan of lines the song's plan gives this section, or None."""
        extras = self._choices.extras_with_sections()
        plan = extras.get(song_plan.PLAN_OF_SONG, {})
        by_place = plan.get(song_plan.BY_PLACE) or []
        if self._place >= len(by_place) or not by_place[self._place]:
            return None
        return by_place[self._place].get(wizard_limits.PLAN)

    @cached_until_choices_change
    def _lines(self):
        """Return each line of the section as the song makes it: who plays it, its notes, whether it breathes, whether it is the
        hook, and what it was given of its own."""
        made = self._choices.made_form()
        scene = made[arranger.FORM][self._place]
        own = self._own_lines()
        seen = set()
        lines = []
        for count, entry in enumerate(self.plan()):
            player = self._line_player(entry)
            notes = self._notes_of_line(made=made, scene=scene, player=player, count=count)
            letter = (bool(entry.get(melody_writer.ANSWER)), entry.get(melody_writer.LINE, str(count)))
            new = letter not in seen
            seen.add(letter)
            given = own.get(count) or {}
            breathes = new and notes is not None and self._line_breathes(entry=entry, given=given)
            lines.append({wizard_limits.LINE_PLAYER: player, melody_writer.LINE_NOTES: notes, wizard_limits.LINE_BREATHES: breathes,
                          wizard_limits.LINE_IS_HOOK: bool(entry.get(melody_writer.HOOK)), wizard_limits.LINE_OWN: copy.deepcopy(given)})
        return lines

    def _line_player(self, entry):
        """Return who plays a line of the plan: the player who answers the tune for an answer, else the tune's player."""
        if entry.get(melody_writer.ANSWER):
            interplay = self._choices.interplay()
            return interplay.answered_by()
        band = self._choices.get_band()
        return band.tune_player()

    @staticmethod
    def _notes_of_line(*, made, scene, player, count):
        """Return a copy of the notes a player's part plays for a line of a scene, or None where the part writes no such line."""
        play = scene.get(wizard_limits.PLAY_OF_SCENE, {})
        played = play.get(player) or {}
        part = made[arranger.PARTS].get(played.get(wizard_limits.PART))
        if part is None or tune_notation.LINES not in part:
            return None
        part_lines = part[tune_notation.LINES]
        if count >= len(part_lines):
            return None
        return copy.deepcopy(part_lines[count])

    def _line_breathes(self, *, entry, given):
        """Return whether a line breathes: not the hook, not notes written by hand, and only in a song in four."""
        if entry.get(melody_writer.HOOK) or melody_writer.LINE_NOTES in given:
            return False
        return self._choices.counts_in_four()

    def set_line(self, *, line, field, value):
        """Give one line of a section its own notes, breath or early note, or give the field back with None. What the song cannot
        then be made with is refused."""
        lines = self.as_made()
        is_place = isinstance(line, int) and not isinstance(line, bool) and 0 <= line < len(lines)
        if not is_place or field not in own_values.LINE_FIELDS:
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=line))
        if field == melody_writer.LINE_NOTES and value is not None and not self._notes_fit(written=lines[line][melody_writer.LINE_NOTES], value=value):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))
        own = self._own_lines_copied()
        given = own.setdefault(line, {})
        given.pop(field, None)
        if value is not None:
            given[field] = value
        kept = {count: given for count, given in own.items() if given}
        section = self._choices.section(self._place)
        section.store_own(field=wizard_limits.LINES_OF_SECTION, value=kept or None)

    @staticmethod
    def _notes_fit(*, written, value):
        """Return whether notes written by hand can stand for a line the song makes: a list of notes as long as the line, with a
        note in it; notes that cannot are refused by the check itself."""
        if written is None or not isinstance(value, list):
            return False
        checked = checked_line(line=value, steps=line_edits.steps_of(written))
        return line_edits.steps_of(checked) != 0

    def _own_lines_copied(self):
        """Return a copy of what each line of the section was given of its own, by the line's number."""
        return {count: dict(given) for count, given in self._own_lines().items()}
