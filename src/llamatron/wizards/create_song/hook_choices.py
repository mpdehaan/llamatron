# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's choices of the hook: whether the song has one, where it sits, its takes, a second hook, and how the hook and its chorus's body are written."""

import copy

from llamatron.model.schema.file_format import SectionKind
from llamatron.user_strings import errors, song_wizard as wizard_text
from llamatron.wizards.create_song import arranger, hook_writing, line_edits, melody as melody_writer, notation as tune_notation, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import arranged
from llamatron.wizards.create_song.choices_part import cached_until_choices_change, ChoicesPart, chosen_only
from llamatron.wizards.create_song.melody import placement_of, plan_with_hook_placed
from llamatron.wizards.create_song.own_values import checked_line


class HookChoices(ChoicesPart):
    """What was chosen of the song's hook: whether the song has one, which take of it, and how it and the body of its chorus are written, each the genre's until the song says otherwise."""

    __slots__ = ('_hook', '_hook_take', '_writing')

    def __init__(self, *, choices):
        ChoicesPart.__init__(self, choices=choices)
        self.reset()

    def reset(self, *, writing=True):
        """Go back to the hook the genre gives, in its first take; how the hook is written goes back to the genre's too, unless writing is False."""
        # Whether the song has a hook, or None while the genre says.
        self._hook = None
        self._hook_take = melody_writer.FIRST_HOOK_TAKE
        if writing:
            # What the song chose of how its hook and its chorus's body are written, each a behavior or gauges moved from the genre's.
            self._writing = {}

    # What a song keeps of the hook, and what the hook adds to the song made.

    def to_data(self):
        """Return what a song keeps of the hook, as plain data a song file saves: only what was chosen."""
        held = {
            wizard_limits.HOOK_SAVED: self._hook,
            wizard_limits.HOOK_TAKE_SAVED: self._hook_take or None,
            wizard_limits.WRITING_SAVED: copy.deepcopy(self._writing) or None,
        }
        return chosen_only(held)

    def restore(self, saved):
        """Restore what a song saved of the hook, leaving out whatever is no longer allowed."""
        has_hook = saved.value(wizard_limits.HOOK_SAVED)
        if isinstance(has_hook, bool):
            saved.apply(self._restore_hook, on=has_hook)
        take = saved.value(wizard_limits.HOOK_TAKE_SAVED)
        if take:
            saved.apply(self._restore_hook_take, take=take)
        writing = saved.value(wizard_limits.WRITING_SAVED)
        if isinstance(writing, dict):
            saved.apply(self._restore_writing, writing=writing)

    def counted(self):
        """Return the hook's setting another genre forgets, under a name of its own, so that two songs can be compared setting by setting."""
        return {(wizard_limits.GENRE_SETTING, wizard_limits.HOOK_SAVED): self._hook}

    def add_picks(self, picks):
        """Add the hook's picks to the song's: whether the song has one, where that was chosen, and which take."""
        if self._hook is not None:
            picks[melody_writer.HOOK] = self._hook
        if self._hook_take:
            picks[melody_writer.HOOK_TAKE] = self._hook_take

    def writing_said(self):
        """Return how the hook's lines are written: the behavior, and the place of every gauge."""
        gauges = {name: self.get_hook_gauge(name) for name in hook_writing.HOOK_GAUGES}
        return {hook_writing.BEHAVIOR: self.get_hook_behavior(), hook_writing.GAUGES: gauges}

    def body_writing_said(self):
        """Return how the lines around the hook are written: the place of every gauge."""
        gauges = {name: self.get_body_gauge(name) for name in hook_writing.BODY_GAUGES}
        return {hook_writing.GAUGES: gauges}

    # The hook, which a song has or has not, apart from the melody style that writes its other lines.

    def can_have_hook(self):
        """Return whether a hook can be made at all: a section of the song's form marks a line as its hook, and, in a form of
        the subgenre's own, a player carries a tune there."""
        if not self._choices.is_ready() or not any(entry.get(melody_writer.HOOK) for place in range(len(self._choices.get_song_form().section_entries())) for entry in self._choices.section(place).as_played().get(wizard_limits.PLAN, [])):
            return False
        return self._choices.hook_changes_song()

    def hook_line_place(self):
        """Return where the song's hook line is while the song can have one: the kind of section that says it first and which of
        that kind's lines it is, counted from 1. None where the song can have no hook."""
        if not self.can_have_hook():
            return None
        for kind in self._choices.get_song_form().section_kinds_in_form():
            for count, entry in enumerate(self._hook_plan(kind)):
                if entry.get(melody_writer.HOOK):
                    return kind, count + 1
        return None

    def _hook_plan(self, kind):
        """A kind of section's plan of lines as the genre has it, the hook placed among them where the song chose its place."""
        plan = self._choices.style()[arranger.SECTIONS].get(kind, {}).get(wizard_limits.PLAN, [])
        placement = (self._choices.get_extra(wizard_limits.HOOKS_CHOSEN) or {}).get(melody_writer.PLACEMENT)
        return plan_with_hook_placed(plan=plan, placement=placement) if placement and kind == self._main_hook_kind() else plan

    def _main_hook_kind(self):
        """The kind of section that says the main hook: the first in the form whose plan marks a line as one, or None."""
        sections = self._choices.style()[arranger.SECTIONS]
        return next((kind for kind in self._choices.get_song_form().section_kinds_in_form() if says_hook(sections[kind])), None)

    # Where the main hook sits among the lines of its section, which the genre says until a person chooses.

    def hook_placements_offered(self):
        """Return the places the main hook can sit among its chorus's lines, where the chorus is of four lines in a shape that has a
        name; none elsewhere, as in a verse that ends on its refrain, where the hook has one place."""
        if not self.can_have_hook() or not self.has_hook() or self._main_hook_kind() != SectionKind.CHORUS or self.genre_hook_placement() is None:
            return []
        return list(melody_writer.PLACEMENTS)

    def genre_hook_placement(self):
        """Return where the genre places the hook among its section's lines, or None for a plan of no named shape."""
        kind = self._main_hook_kind()
        return None if kind is None else placement_of(self._choices.style()[arranger.SECTIONS][kind].get(wizard_limits.PLAN, []))

    def get_hook_placement(self):
        chosen = (self._choices.get_extra(wizard_limits.HOOKS_CHOSEN) or {}).get(melody_writer.PLACEMENT)
        return chosen if chosen in self.hook_placements_offered() else self.genre_hook_placement()

    def set_hook_placement(self, placement):
        """Choose where the main hook sits among its chorus's lines; the genre's own place is asked for by its name."""
        if placement not in self.hook_placements_offered():
            raise ValueError(errors.ERR_WIZARD_HOOK_PLACEMENT.format(value=placement))
        self._keep_hook_chosen(field=melody_writer.PLACEMENT, value=None if placement == self.genre_hook_placement() else placement)

    def _keep_hook_chosen(self, *, field, value):
        chosen = dict(self._choices.get_extra(wizard_limits.HOOKS_CHOSEN) or {})
        chosen.pop(field, None)
        if value is not None:
            chosen[field] = value
        self._choices.set_extra(name=wizard_limits.HOOKS_CHOSEN, value=chosen or None)
        self._choices.clear_answers()

    # The second hook: a short tag, unlike the main hook, sung in another kind of section by the melody's player.

    def second_hook_kinds(self):
        """Return the kinds of section the song's second hook can be sung in: those of the form that can carry a tag, where the song
        has a main hook, a player for its melody, and a bar a tag can be written in."""
        if not self.can_have_hook() or not self.has_hook() or self._choices.get_band().tune_player() is None or not self._choices.counts_in_four():
            return []
        in_form = self._choices.get_song_form().section_kinds_in_form()
        return [kind for kind in wizard_limits.SECOND_HOOK_KINDS if kind in in_form and kind != self._main_hook_kind()]

    def _second_hook_kept(self):
        kept = (self._choices.get_extra(wizard_limits.HOOKS_CHOSEN) or {}).get(melody_writer.SECOND_HOOK)
        return kept if isinstance(kept, dict) and kept.get(melody_writer.SUNG_IN) in self.second_hook_kinds() else None

    def has_second_hook(self):
        return self._second_hook_kept() is not None

    def get_second_hook_kind(self):
        """Return the kind of section the second hook is sung in, or None while the song has none."""
        kept = self._second_hook_kept()
        return None if kept is None else kept[melody_writer.SUNG_IN]

    def get_second_hook_take(self):
        kept = self._second_hook_kept()
        return melody_writer.FIRST_HOOK_TAKE if kept is None else kept.get(melody_writer.TAG_TAKE, melody_writer.FIRST_HOOK_TAKE)

    def set_second_hook(self, kind):
        """Give the song a second hook sung in a kind of section, or take the second hook away with None."""
        if kind is not None and kind not in self.second_hook_kinds():
            raise ValueError(errors.ERR_WIZARD_SECOND_HOOK.format(value=kind))
        self._keep_hook_chosen(field=melody_writer.SECOND_HOOK, value=None if kind is None else {melody_writer.SUNG_IN: kind, melody_writer.TAG_TAKE: self.get_second_hook_take()})

    def new_second_hook(self):
        """Have another second hook made, every other line of the song left as it was."""
        if not self.has_second_hook():
            raise ValueError(errors.ERR_WIZARD_SECOND_HOOK.format(value=None))
        self._keep_hook_chosen(field=melody_writer.SECOND_HOOK, value={melody_writer.SUNG_IN: self.get_second_hook_kind(), melody_writer.TAG_TAKE: self.get_second_hook_take() + 1})

    def second_hook_scene(self):
        """Return the place in the form of the first section that sings the second hook, or None."""
        kind = self.get_second_hook_kind()
        return None if kind is None else next((place for place, of_place in enumerate(self._choices.get_song_form().section_kinds_in_form()) if of_place == kind), None)

    def hooks_of_song(self):
        """What the arranger is handed of the song's hooks: the main hook's kind of section and its place among the lines, and the
        second hook with its singer."""
        chosen = self._choices.get_extra(wizard_limits.HOOKS_CHOSEN)
        if not self._choices.is_ready() or not chosen:
            return {}
        hooks = {}
        placement = chosen.get(melody_writer.PLACEMENT)
        if placement in melody_writer.PLACEMENTS and self._main_hook_kind() is not None:
            hooks[melody_writer.MAIN_HOOK] = {melody_writer.SUNG_IN: self._main_hook_kind(), melody_writer.PLACEMENT: placement}
        second = chosen.get(melody_writer.SECOND_HOOK)
        if isinstance(second, dict) and second.get(melody_writer.SUNG_IN) in wizard_limits.SECOND_HOOK_KINDS and self._choices.get_band().tune_player() is not None:
            hooks[melody_writer.SECOND_HOOK] = {melody_writer.SUNG_IN: second[melody_writer.SUNG_IN], melody_writer.SUNG_BY: self._choices.get_band().tune_player(), melody_writer.TAG_TAKE: second.get(melody_writer.TAG_TAKE, melody_writer.FIRST_HOOK_TAKE)}
        return {melody_writer.HOOKS: hooks} if hooks else {}

    def usual_hook(self):
        """Return whether the genre's songs have a hook unless a person says otherwise."""
        return self.can_have_hook() and bool(self._choices.style().get(melody_writer.HOOK, False))

    def has_hook(self):
        return self.usual_hook() if self._hook is None else self._hook

    def hook_notes(self):
        """Return the hook as the song's tune player first plays it: how many steps the hook line lasts, how many steps a bar
        has, and each note as where it starts, how many steps it lasts and its MIDI note. None while the song has no hook.
        Found by arranging the song, and kept until a choice changes."""
        return self._found_hook_notes()

    @cached_until_choices_change
    def _hook_part(self):
        """The part of the tune's player in the first kind of section that says the hook, and which of its lines is the hook; nothing where nobody says one."""
        player = self._choices.get_band().tune_player()
        if not self.can_have_hook() or not self.has_hook() or player is None:
            return None, None
        kind = self._main_hook_kind()
        line = next(place for place, entry in enumerate(self._hook_plan(kind)) if entry.get(melody_writer.HOOK))
        part = arranged(style=self._choices.style(), song=self._choices.song_picks(kind))[arranger.PARTS].get(wizard_text.MSG_PART_OF_SECTION.format(kind, player))
        return (None, None) if part is None or tune_notation.LINES not in part else (part, line)

    @cached_until_choices_change
    def _found_hook_notes(self):
        part, line = self._hook_part()
        if part is None:
            return None
        at, notes = self._sounded(lines=[part[tune_notation.LINES][line]], octave=part[tune_notation.OCTAVE])
        return at, self._choices.melody().habits()[melody_writer.GRID], notes

    def _sounded(self, *, lines, octave):
        """Lines of a tune as how many steps they last and each note as where it starts, how many steps it lasts and its MIDI
        note, in the song's key, octave being the octave the lines are written against."""
        scale = self._choices.scale_half_steps()
        lowest = octave * melody_writer.NOTES_IN_OCTAVE + self._choices.root_half_steps()
        notes = []
        at = 0
        for line in lines:
            for note in line:
                length = note.get(tune_notation.STEPS, note.get(tune_notation.REST))
                if tune_notation.REST not in note:
                    octaves, place = divmod(note[tune_notation.DEGREE] - 1, len(scale))
                    notes.append((at, length, lowest + scale[place] + (octaves + note.get(tune_notation.OCTAVE, 0)) * melody_writer.NOTES_IN_OCTAVE + wizard_limits.HALF_STEPS_OF_ACCIDENTAL.get(note.get(tune_notation.ACCIDENTAL), 0)))
                at += length
        return at, notes

    def hook_kind(self):
        """Return the kind of section that says the main hook, or None where the song can have none."""
        place = self.hook_line_place()
        return None if place is None else place[0]

    def hook_bars(self):
        """Return the bars of its section that are the hook, the first and the last, counted from 1: the bars of the first line
        the section's plan marks as the hook. None where the song has no hook."""
        place = self.hook_line_place()
        if place is None or not self.has_hook():
            return None
        bars = self._choices.melody().habits()[melody_writer.LINE_BARS]
        return (place[1] - 1) * bars + 1, place[1] * bars

    def hook_section_notes(self):
        """Return the tune of the whole section that says the hook, as hook_notes returns the hook: how many steps it lasts, how
        many steps a bar has, and each note. The notes are the section's as they stand, a person's own where the section was
        edited by hand. None where the song has no hook or the section's notes do not divide into the melody's bars."""
        kind = self.hook_kind()
        if kind is None or not self.has_hook() or self._choices.get_tunes().tune_place(kind) is None or self._choices.get_tunes().tune_player_in(kind) is None:
            return None
        pattern = self._choices.get_tunes().tune_pattern(kind)
        bar = self._choices.melody().habits()[melody_writer.GRID]
        if pattern is None or pattern[tune_notation.STEPS] % bar:
            return None
        try:
            lines, octave, _ = tune_notation.tune_lines(pattern=pattern, bar=bar)
        except tune_notation.NotWritable:
            return None
        steps, notes = self._sounded(lines=lines, octave=octave)
        return (steps, bar, notes) if steps == pattern[tune_notation.STEPS] else None

    def set_hook(self, on):
        if on and not self.can_have_hook():
            raise ValueError(errors.ERR_WIZARD_NO_HOOK)
        self._hook = None if bool(on) == self.usual_hook() else bool(on)

    def _restore_hook(self, *, on):
        self.set_hook(on)

    def get_hook_take(self):
        """Return which take of the hook the song has: the first, or a later one asked for with a new hook."""
        return self._hook_take

    # How the hook and the body of its chorus are written: a behavior and gauges, the genre's until the song moves one.

    def writes_hook(self):
        """Return whether the song's hook is written by a behavior and gauges: a song with a hook whose bar is counted in eighths."""
        return self._choices.is_ready() and self.can_have_hook() and self.has_hook() and not self._choices.melody().habits()[melody_writer.GRID] % hook_writing.UNITS

    def genre_hook_behavior(self):
        return hook_writing.hook_ways(self._choices.melody().habits())[0]

    def get_hook_behavior(self):
        return self._writing.get(wizard_names.HOOK_WRITING, {}).get(hook_writing.BEHAVIOR, self.genre_hook_behavior())

    def set_hook_behavior(self, behavior):
        """Choose the way the hook is written; the genre's own way gives the choice back to the genre."""
        if behavior not in wizard_names.BEHAVIORS:
            raise ValueError(errors.ERR_WIZARD_HOOK_BEHAVIOR.format(value=behavior, choices=', '.join(wizard_names.BEHAVIORS)))
        self._keep_writing(part=wizard_names.HOOK_WRITING, field=hook_writing.BEHAVIOR, value=None if behavior == self.genre_hook_behavior() else behavior)

    def hook_gauges(self):
        """Return the hook's gauges that change a hook written the way the song's is."""
        return list(hook_writing.HOOK_GAUGES_OF[self.get_hook_behavior()]) if self.writes_hook() else []

    def genre_hook_gauge(self, name):
        return hook_writing.hook_ways(self._choices.melody().habits())[1][name]

    def get_hook_gauge(self, name):
        return self._writing.get(wizard_names.HOOK_WRITING, {}).get(hook_writing.GAUGES, {}).get(name, self.genre_hook_gauge(name))

    def set_hook_gauge(self, *, name, position):
        """Move one of the hook's gauges, or give the gauge back to the genre with None."""
        self._set_writing_gauge(part=wizard_names.HOOK_WRITING, names=hook_writing.HOOK_GAUGES, name=name, position=position, usual=self.genre_hook_gauge)

    def writes_body(self):
        """Return whether the lines of the chorus that are no hook are written by the body's gauges: where the hook is written and its section has such lines."""
        return self.writes_hook() and self._choices.melody().get_style() not in wizard_limits.ENGINES_OF_THEIR_OWN and self._body_entries() != []

    def is_body_of_hook(self, kind):
        """Return whether a kind of section is the one that holds the hook, in a song whose hook is written by its gauges: its panel
        then holds where the hook sits and the gauges of its other lines."""
        return self.writes_body() and kind == self._main_hook_kind()

    def _body_entries(self):
        """The lines of the hook's section that are no hook, each with whether a hook follows it and whether it closes the section."""
        kind = self._main_hook_kind()
        plan = [] if kind is None else self._hook_plan(kind)
        return [(entry, place + 1 < len(plan) and bool(plan[place + 1].get(melody_writer.HOOK)), place + 1 == len(plan)) for place, entry in enumerate(plan) if not entry.get(melody_writer.HOOK) and not entry.get(melody_writer.ANSWER)]

    def body_gauges(self):
        """Return the gauges of the chorus's body that change the song as it stands: Call and answer only where a line of the body
        returns, and Resolve only where a line's ending is not already decided by its place or by its answering."""
        if not self.writes_body():
            return []
        entries = self._body_entries()
        returns = any(entry.get(wizard_limits.VARIED) for entry, _, _ in entries)
        # A line that leads to a hook ends open and the section's last line ends on the home note, whatever Resolve says.
        answers = self.get_body_gauge(hook_writing.CALL_AND_ANSWER) >= hook_writing.ANSWERS_FROM
        free = any(not leads and not closes and not (answers and entry.get(wizard_limits.VARIED)) for entry, leads, closes in entries)
        needed = {hook_writing.CALL_AND_ANSWER: returns, hook_writing.RESOLVE: free}
        return [name for name in hook_writing.BODY_GAUGES if needed.get(name, True)]

    def genre_body_gauge(self, name):
        return hook_writing.body_ways(self._choices.melody().habits())[name]

    def get_body_gauge(self, name):
        return self._writing.get(wizard_names.BODY_WRITING, {}).get(hook_writing.GAUGES, {}).get(name, self.genre_body_gauge(name))

    def set_body_gauge(self, *, name, position):
        """Move one of the gauges of the chorus's body, or give the gauge back to the genre with None."""
        self._set_writing_gauge(part=wizard_names.BODY_WRITING, names=hook_writing.BODY_GAUGES, name=name, position=position, usual=self.genre_body_gauge)

    def writing_gauge_is_moved(self, *, part, name):
        """Return whether the song moved a gauge of its hook or of its chorus's body from where the genre has it."""
        return name in self._writing.get(part, {}).get(hook_writing.GAUGES, {})

    def _set_writing_gauge(self, *, part, names, name, position, usual):
        if name not in names or (position is not None and not hook_writing.is_position(position)):
            raise ValueError(errors.ERR_WIZARD_WRITING_GAUGE.format(name=name, low=wizard_names.HOOK_WRITING_LOWEST, high=wizard_names.HOOK_WRITING_HIGHEST, value=position))
        gauges = dict(self._writing.get(part, {}).get(hook_writing.GAUGES, {}))
        gauges.pop(name, None)
        if position is not None and position != usual(name):
            gauges[name] = position
        self._keep_writing(part=part, field=hook_writing.GAUGES, value=gauges or None)

    def _keep_writing(self, *, part, field, value):
        kept = self._writing.setdefault(part, {})
        kept.pop(field, None)
        if value is not None:
            kept[field] = value
        if not kept:
            del self._writing[part]
        self._choices.clear_answers()

    def _restore_writing(self, *, writing):
        """Take what a song saved of how its hook and its chorus's body are written, each part through its setter."""
        hook = writing.get(wizard_names.HOOK_WRITING) or {}
        if hook.get(hook_writing.BEHAVIOR) is not None:
            self.set_hook_behavior(hook[hook_writing.BEHAVIOR])
        for name, position in (hook.get(hook_writing.GAUGES) or {}).items():
            self.set_hook_gauge(name=name, position=position)
        for name, position in ((writing.get(wizard_names.BODY_WRITING) or {}).get(hook_writing.GAUGES) or {}).items():
            self.set_body_gauge(name=name, position=position)

    def new_hook(self):
        """Have another hook made, every other line of the song left as it was."""
        if not self.can_have_hook() or not self.has_hook():
            raise ValueError(errors.ERR_WIZARD_NO_HOOK)
        self._hook_take += 1

    def _restore_hook_take(self, *, take):
        if isinstance(take, bool) or not isinstance(take, int) or take < melody_writer.FIRST_HOOK_TAKE:
            raise ValueError(errors.ERR_WIZARD_HOOK_TAKE.format(value=take))
        self._hook_take = take

    # The hook's notes, the wizard's until a person writes them by hand.

    def hook_line(self):
        """Return the hook's line as the song has it, a list of notes and rests each so many steps long (line_edits.py), or None while the song has no hook."""
        if self.hook_notes() is None:
            return None
        return self._found_hook_line()

    @cached_until_choices_change
    def _found_hook_line(self):
        part, line = self._hook_part()
        return copy.deepcopy(part[tune_notation.LINES][line])

    def hook_is_own(self):
        """Return whether the hook's notes were written by hand."""
        return bool((self._choices.get_extra(arranger.MELODY) or {}).get(melody_writer.HOOK_NOTES))

    def pitch_of_place(self, place):
        """Return the MIDI note at a place of the song's scale as the tune's player plays it (line_edits.place_of), for a picture of a line."""
        scale = self._choices.scale_half_steps()
        octaves, degree = divmod(place, len(scale))
        return self._hook_part()[0][tune_notation.OCTAVE] * melody_writer.NOTES_IN_OCTAVE + self._choices.root_half_steps() + scale[degree] + octaves * melody_writer.NOTES_IN_OCTAVE

    def set_hook_line(self, line):
        """Write the hook's notes by hand, or give the hook back to the wizard with None. A line that is not as long as the hook's, or that the
        song cannot be made with, is refused and nothing changes."""
        if self.hook_line() is None:
            raise ValueError(errors.ERR_WIZARD_NO_HOOK)
        before = copy.deepcopy(self._choices.get_extra(arranger.MELODY))
        melody = dict(self._choices.get_extra(arranger.MELODY) or {})
        if line is None:
            melody.pop(melody_writer.HOOK_NOTES, None)
        else:
            melody[melody_writer.HOOK_NOTES] = checked_line(line=line, steps=line_edits.steps_of(self.hook_line()))
        self._choices.set_extra(name=arranger.MELODY, value=melody or None)
        self._choices.clear_answers()
        try:
            self._choices.written_for_trial()
        except Exception as problem:
            self._choices.set_extra(name=arranger.MELODY, value=None)
            if before is not None:
                self._choices.set_extra(name=arranger.MELODY, value=before)
            self._choices.clear_answers()
            raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=problem)) from problem

    def hook_scene(self):
        """Return the place in the form of the first section that says the hook, or None."""
        sections = self._choices.style()[arranger.SECTIONS]
        return next((place for place, kind in enumerate(self._choices.get_song_form().section_kinds_in_form()) if says_hook(sections[kind])), None)

    def sayers(self):
        """Return the players who can say the hook: the player who answers the tune and the tune's player, where the song has a hook."""
        if not self.can_have_hook() or not self.has_hook():
            return []
        interplay = self._choices.interplay()
        band = self._choices.get_band()
        sayers = []
        for role in (interplay.answered_by(), band.tune_player()):
            if role is not None:
                sayers.append(role)
        return sayers


def says_hook(section):
    """Return whether a kind of section's plan marks a line as the hook."""
    return any(entry.get(melody_writer.HOOK) for entry in section.get(wizard_limits.PLAN, []))
