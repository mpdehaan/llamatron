# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""One section of the song wizard's form, as the wizard's choices hold it: its kind, its length, who plays in it, what it is
given of its own over the plan and the song, and its lines."""

import copy

from llamatron.composition import limits
from llamatron.composition.song_file_error import SongFileError
from llamatron.macro_composer import arranger, joins as joins_values, line_edits, melody as melody_writer, notation as tune_notation, phrasing, song_plan, wizard_limits
from llamatron.macro_composer.arranger import chord_of, fits_by_halves, picked, section_of, shares_a_bar, values_of
from llamatron.macro_composer.choices_part import kept_until_choices_change
from llamatron.strings import errors
from llamatron.support import version as version_values


def own_copy_of(entry):
    """Return a section's entry sharing no list and no dictionary with the entry given."""
    return copy.deepcopy(entry)


def chords_from_text(text):
    """Return chords typed as degrees with a space between, a flat or a sharp before a degree, such as 6 4 1 b7, two chords that share a bar joined by a dash, such as 1-5, as the arranger reads them."""
    def chord_typed(word):
        mark = word[0] if word and word[0] in wizard_limits.MARKS_TYPED else None
        number = word[1:] if mark else word
        if not number.isdigit() or not wizard_limits.FIRST_DEGREE_OF_SCALE <= int(number) <= wizard_limits.LAST_DEGREE_OF_SCALE:
            raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
        return {tune_notation.DEGREE: int(number), tune_notation.ACCIDENTAL: wizard_limits.MARKS_TYPED[mark]} if mark else int(number)
    chords = []
    for word in str(text).split():
        # Two chords joined by a dash share a bar, each half of it.
        halves = word.split(wizard_limits.SHARES_A_BAR)
        if len(halves) > wizard_limits.CHORDS_IN_A_SHARED_BAR:
            raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
        chords.append(chord_typed(word) if len(halves) == 1 else [chord_typed(half) for half in halves])
    if not chords:
        raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
    if any(shares_a_bar(chord) for chord in chords) and not fits_by_halves(chords):
        raise ValueError(errors.ERR_WIZARD_CHORDS_SHARED.format(most=limits.MAX_PROGRESSION_CHORDS // wizard_limits.CHORDS_IN_A_SHARED_BAR, value=text))
    return chords


def chords_as_text(chords):
    """Return chords as they are typed."""
    marks = {accidental: mark for mark, accidental in wizard_limits.MARKS_TYPED.items()}

    def typed(chord):
        return marks.get(chord_of(chord).get(tune_notation.ACCIDENTAL), '') + str(chord_of(chord)[tune_notation.DEGREE])
    def bar_typed(chord):
        return wizard_limits.SHARES_A_BAR.join(typed(half) for half in chord) if shares_a_bar(chord) else typed(chord)
    return ' '.join(bar_typed(chord) for chord in chords)


class SectionChoices:
    """One section of the form, by its place. The form's sections are held by the choices as plain entries, and what the
    section is given of its own is kept in its entry; the choices make a section object whenever one is asked for, so that a
    page writes choices.section(place).set_bars(bars=8)."""

    __slots__ = ('_choices', '_place')

    def __init__(self, *, choices, place):
        self._choices = choices
        self._place = place

    def get_place(self):
        return self._place

    def answers_kept_by(self):
        """Return the choices that keep a section's answers, and which section asked, by its place."""
        return self._choices, self._place

    def entry(self):
        entries = self._choices.get_song_form().section_entries()
        if isinstance(self._place, bool) or not isinstance(self._place, int) or not 0 <= self._place < len(entries):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION.format(value=self._place))
        return entries[self._place]

    def as_played(self):
        """Return a section as it will be played: its kind as the genre describes it, with what the section changes."""
        entry = self.entry()
        return section_of(name=entry[arranger.KIND], style=self._choices.style(), song={arranger.SECTIONS: {entry[arranger.KIND]: entry}})

    def kind(self):
        return self.entry()[arranger.KIND]

    def is_held(self):
        """Return whether a section is one held chord, which lasts a bar whatever is said."""
        return bool(self.as_played().get(arranger.HELD))

    def bars(self):
        section = self.as_played()
        return wizard_limits.HELD_BARS if section.get(arranger.HELD) else section[arranger.BARS]

    def plays(self):
        """Return who plays in a section, by the names the genre gives its players."""
        return list(self.as_played().get(arranger.PLAYS, []))

    def usually_plays(self):
        """Return who plays in a section of its kind as the genre has the kind."""
        return list(self.usual().get(arranger.PLAYS, []))

    def copy(self):
        """Put a copy of a section straight after it."""
        entry = own_copy_of(self.entry())
        self._choices.get_song_form().own_section_entries().insert(self._place + 1, entry)

    def remove(self):
        self.entry()
        if len(self._choices.get_song_form().section_entries()) == 1:
            raise ValueError(errors.ERR_WIZARD_LAST_SECTION)
        del self._choices.get_song_form().own_section_entries()[self._place]

    def move(self, *, offset):
        """Move a section earlier or later in the form, and return whether it moved, which it cannot past either end."""
        self.entry()
        moved = self._place + offset
        if not 0 <= moved < len(self._choices.get_song_form().section_entries()):
            return False
        entries = self._choices.get_song_form().own_section_entries()
        entries.insert(moved, entries.pop(self._place))
        return True

    def set_kind(self, *, kind):
        """Make a section another kind, as the genre describes that kind: what the section changed of its old kind is dropped."""
        self.entry()
        if kind not in self._choices.get_song_form().section_kinds():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION_KIND.format(value=kind))
        self._choices.get_song_form().own_section_entries()[self._place] = {arranger.KIND: kind}

    def usual(self):
        return self._choices.style()[arranger.SECTIONS][self.entry()[arranger.KIND]]

    def bars_offered(self):
        """Return the lengths a section may have, in bars: half its kind's usual length, the usual and twice that, leaving out
        any the genre's parts cannot fill, and nothing for a held section."""
        return list(self._choices.offered(key=(wizard_limits.BARS_ANSWER, self._place), compute=lambda: self._bars_offered()))

    def _bars_offered(self):
        if self.is_held():
            return []
        usual = self.usual()[arranger.BARS]
        lengths = sorted({usual // wizard_limits.HALF, usual, usual * wizard_limits.HALF, self.bars()} - {0})
        return [bars for bars in lengths if bars == usual or self.bars_fit(bars=bars)]

    def bars_fit(self, *, bars):
        """Return whether the players of a section can fill the section at a length: on their own, and then in this song, where
        a part may be written differently beside another section of the kind."""
        if not self._choices.fills(kind=self.entry()[arranger.KIND], bars=bars, plays=tuple(self.plays())):
            return False
        trial = self._choices.copied_for_trial()
        trial.get_song_form().own_section_entries()[self._place][arranger.BARS] = bars
        try:
            trial.written_setlist(name=self.entry()[arranger.KIND], version=version_values.VERSION)
        except (ValueError, SongFileError):
            return False
        return True

    def set_bars(self, *, bars):
        if isinstance(bars, bool) or not isinstance(bars, int) or bars not in self.bars_offered():
            raise ValueError(errors.ERR_WIZARD_SECTION_BARS.format(value=bars))
        entry = self._choices.get_song_form().own_section_entries()[self._place]
        entry.pop(arranger.BARS, None)
        if bars != self.usual()[arranger.BARS]:
            entry[arranger.BARS] = bars

    def set_plays(self, *, role, on):
        """Have a player play in a section or sit it out. A section keeps one player, and a length its players can fill."""
        self._choices.get_band().role_named(role)
        plays = [name for name in self._choices.get_band().roles() if (name in self.plays() or (on and name == role)) and (on or name != role)]
        if not plays:
            raise ValueError(errors.ERR_WIZARD_SECTION_NEEDS_PLAYER)
        entry = self._choices.get_song_form().own_section_entries()[self._place]
        entry.pop(arranger.PLAYS, None)
        if sorted(plays) != sorted(self.usual().get(arranger.PLAYS, [])):
            entry[arranger.PLAYS] = plays
        # A length the players left cannot fill gives way to the kind's usual length.
        if arranger.BARS in entry and not self.bars_fit(bars=entry[arranger.BARS]):
            del entry[arranger.BARS]

    def own_fields(self):
        """Return the fields a section can be given of its own, in the order shown: none without a plan, and no join for the last section or a held one."""
        if not self._choices.is_ready() or self.is_held():
            return []
        fade = self.fade_fields()
        if not self._choices.has_song_plan():
            return [*wizard_limits.OWN_WITHOUT_PLAN, *fade]
        joins = self._choices.plan_joins()
        leaves = [joins_values.LEAVES, song_plan.SETUP] if self._place < len(joins) and joins[self._place] is not None else []
        shape = [wizard_limits.SHAPE_OF_SECTION] if self.shapes() else []
        rises = [song_plan.RISES] if self._place < len(joins) and joins[self._place] is not None else []
        return [song_plan.ENERGY, *shape, *rises, *fade, *leaves, arranger.CHORDS, song_plan.TEMPO_OF_PLACE, song_plan.TEMPO_END_OF_PLACE, song_plan.ROOT_OF_PLACE, song_plan.TYPE_OF_PLACE]

    def fade_way(self):
        """Return how a section can fade: in, for a section that opens the song before its first tune; out, for one that closes
        the song after its last; and None for any other and for a held chord."""
        if self.is_held():
            return None
        if self._place < self._choices.get_song_form().head_count():
            return wizard_limits.FADE_IN
        return wizard_limits.FADE_OUT if self._place >= len(self._choices.get_song_form().section_entries()) - self._choices.get_song_form().tail_count() else None

    def fade_fields(self):
        """Return the fields of a section's fade, in the order shown: the switch where the section can fade, and while it is on,
        the level the fade starts from or ends at, and the bars the fade takes, the first of the section for a fade in and the last for a fade out."""
        way = self.fade_way()
        if way is None:
            return []
        if not self.entry().get(wizard_limits.OWN_OF_SECTION, {}).get(song_plan.FADES):
            return [song_plan.FADES]
        return [song_plan.FADES, song_plan.FADE_LEVEL, song_plan.FADE_OVER]

    def with_fade_way(self, *, own):
        """What a section says of its own, with whether its fade is a fade in and the bars the fade takes, never more than the section has."""
        if not own.get(song_plan.FADES):
            return {field: value for field, value in own.items() if field not in (song_plan.FADES, song_plan.FADE_LEVEL, song_plan.FADE_OVER)}
        if self.fade_way() is None:
            # A section that fades was moved to where none does.
            return {field: value for field, value in own.items() if field not in (song_plan.FADES, song_plan.FADE_LEVEL, song_plan.FADE_OVER)}
        return {**own, **({song_plan.FADES_IN: True} if self.fade_way() == wizard_limits.FADE_IN else {}), song_plan.FADE_OVER: min(own.get(song_plan.FADE_OVER, self.bars()), self.bars())}

    def shapes(self):
        """Return the shapes a section's lines may take besides its kind's own, by name."""
        return list(self.usual().get(wizard_limits.SHAPES, {}))

    def own(self, *, field):
        """Return what a section was given of its own for a field, or None."""
        return copy.deepcopy(self.entry().get(wizard_limits.OWN_OF_SECTION, {}).get(field))

    def from_plan(self, *, field):
        """Return what a section takes for a field where it is given nothing: the plan's Energy and join, the progression's chords, the song's tempo and key."""
        if field == arranger.CHORDS:
            return chords_as_text(self.chords_at())
        if field in (song_plan.TEMPO_OF_PLACE, song_plan.TEMPO_END_OF_PLACE):
            return self.own(field=song_plan.TEMPO_OF_PLACE) or self._choices.get_tempo()
        if field in (song_plan.ROOT_OF_PLACE, song_plan.TYPE_OF_PLACE):
            return self._choices.get_root() if field == song_plan.ROOT_OF_PLACE else self._choices.get_scale_type()
        if field == song_plan.FADES:
            return False
        if field == song_plan.FADE_LEVEL:
            return song_plan.FADED
        if field == song_plan.FADE_OVER:
            return self.bars()
        self._choices.plan_extras()
        if field == song_plan.ENERGY:
            return self._choices.energies()[self._place]
        if field == joins_values.LEAVES:
            join = self._choices.plan_joins()[self._place] or {}
            if join.get(joins_values.TAIL):
                return join[joins_values.TAIL]
            # A fill is said by its size, as it is chosen.
            fills = self._choices.style()[song_plan.PLAN_OF_SONG].get(song_plan.FILL_SIZES, {})
            return next((way for way, given in wizard_limits.LEAVES_AS_JOIN.items() if song_plan.FILL_SIZE in given and fills.get(given[song_plan.FILL_SIZE]) == join.get(joins_values.FILL_OF_JOIN)), wizard_limits.LEAVES_NOTHING)
        if field == song_plan.SETUP:
            return wizard_limits.SETUP_USUAL
        if field == wizard_limits.SHAPE_OF_SECTION:
            # A solo after the song's first is a stage, which takes the next of its kind's shapes.
            return self._choices.plan_shapes()[self._place] or wizard_limits.SHAPE_USUAL
        if field == song_plan.RISES:
            return self.entry()[arranger.KIND] in self._choices.style()[song_plan.PLAN_OF_SONG].get(song_plan.RISING, [])
        if field == arranger.CHORDS:
            return chords_as_text(self._choices.made_song_plan().chords_at(self._place))
        if field in (song_plan.TEMPO_OF_PLACE, song_plan.TEMPO_END_OF_PLACE):
            return self.own(field=song_plan.TEMPO_OF_PLACE) or self._choices.get_tempo()
        return self._choices.get_root() if field == song_plan.ROOT_OF_PLACE else self._choices.get_scale_type()

    def chords_at(self):
        """The chords a section plays where it is given none: its kind's own, the progression's for the kind, or the progression's."""
        style = self._choices.style()
        picks = picked(style=style, song=self._choices.song_picks(wizard_limits.PREVIEW_NAME))
        entry = values_of(style=style, trait=self._choices.progression_trait())[picks[self._choices.progression_trait()]]
        kind = self.entry()[arranger.KIND]
        return [chord_of(chord) for chord in style[arranger.SECTIONS][kind].get(arranger.CHORDS) or entry.get(arranger.BY_SECTION, {}).get(kind) or entry[arranger.PATTERN]]

    def plan(self):
        """The plan of lines a section is played by, with what its lines were given."""
        if self._choices.has_song_plan():
            by_place = self._choices.extras_with_sections().get(song_plan.PLAN_OF_SONG, {}).get(song_plan.BY_PLACE) or []
            given = by_place[self._place].get(wizard_limits.PLAN) if self._place < len(by_place) and by_place[self._place] else None
            if given is not None:
                return given
        return self._choices.plan_with_lines(kind=self.entry()[arranger.KIND], plan=None, lines=self.entry().get(wizard_limits.OWN_OF_SECTION, {}).get(wizard_limits.LINES_OF_SECTION, {}))

    def lines(self):
        """Return a section's lines in order, each a mapping: who plays the line, its notes (line_edits.py) or None where nobody of the band plays the line,
        whether its breath and early note can be set (a new idea of the tune in a song in four, not the hook), and what the line was given of its own."""
        self.entry()
        return self._lines()

    @kept_until_choices_change
    def _lines(self):
        made = self._choices.made_form()
        scene = made[arranger.FORM][self._place]
        own = self.entry().get(wizard_limits.OWN_OF_SECTION, {}).get(wizard_limits.LINES_OF_SECTION, {})
        seen = set()
        lines = []
        for count, entry in enumerate(self.plan()):
            player = self._choices.get_band().answered_by() if entry.get(melody_writer.ANSWER) else self._choices.get_band().tune_player()
            part = made[arranger.PARTS].get((scene.get(wizard_limits.PLAY_OF_SCENE, {}).get(player) or {}).get(wizard_limits.PART))
            notes = copy.deepcopy(part[tune_notation.LINES][count]) if part is not None and tune_notation.LINES in part and count < len(part[tune_notation.LINES]) else None
            letter = (bool(entry.get(melody_writer.ANSWER)), entry.get(melody_writer.LINE, str(count)))
            new = letter not in seen
            seen.add(letter)
            breathes = new and notes is not None and not entry.get(melody_writer.HOOK) and self._choices.counts_in_four() and melody_writer.LINE_NOTES not in (own.get(count) or {})
            lines.append({wizard_limits.LINE_PLAYER: player, melody_writer.LINE_NOTES: notes, wizard_limits.LINE_BREATHES: breathes, wizard_limits.LINE_IS_HOOK: bool(entry.get(melody_writer.HOOK)), wizard_limits.LINE_OWN: copy.deepcopy(own.get(count) or {})})
        return lines

    def set_line(self, *, line, field, value):
        """Give one line of a section its own notes, breath or early note, or give the field back with None. What the song cannot then be made with is refused."""
        lines = self.lines()
        if isinstance(line, bool) or not isinstance(line, int) or not 0 <= line < len(lines) or field not in (melody_writer.LINE_NOTES, phrasing.LINE_BREATH, phrasing.LINE_EARLY):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=line))
        if field == melody_writer.LINE_NOTES and value is not None and (lines[line][melody_writer.LINE_NOTES] is None or not isinstance(value, list) or line_edits.steps_of(self._choices.checked_line(line=value, steps=line_edits.steps_of(lines[line][melody_writer.LINE_NOTES]))) == 0):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))
        own = {count: dict(given) for count, given in (self.entry().get(wizard_limits.OWN_OF_SECTION, {}).get(wizard_limits.LINES_OF_SECTION) or {}).items()}
        given = own.setdefault(line, {})
        given.pop(field, None)
        if value is not None:
            given[field] = value
        own = {count: given for count, given in own.items() if given}
        self.store_own(field=wizard_limits.LINES_OF_SECTION, value=own or None)

    def set_own(self, *, field, value):
        """Give a section something of its own, or give the field back with None. What the song cannot then be made with is refused, and nothing changes."""
        if field not in (*wizard_limits.OWN_WITHOUT_PLAN, *wizard_limits.FADE_OWN):
            self._choices.plan_extras()
        self.store_own(field=field, value=value)

    def store_own(self, *, field, value):
        self.entry()
        checked = None if value is None else self._choices.checked_own(field=field, value=value)
        if field == wizard_limits.SHAPE_OF_SECTION and checked is not None and checked not in self.shapes():
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))
        if field in (song_plan.FADES, song_plan.FADE_LEVEL, song_plan.FADE_OVER) and checked is not None and (field not in (song_plan.FADES, *self.fade_fields()) or self.fade_way() is None or (field == song_plan.FADE_OVER and checked > self.bars())):
            # Only a section that opens or closes the song fades, and a fade's level and bars are a fade's that is switched on.
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))
        before = copy.deepcopy(self._choices.get_song_form().get_own_sections())
        entry = self._choices.get_song_form().own_section_entries()[self._place]
        own = entry.setdefault(wizard_limits.OWN_OF_SECTION, {})
        own.pop(field, None)
        if checked is not None:
            own[field] = checked
        if field == song_plan.FADES and not checked:
            # A fade switched off keeps nothing of how it faded.
            own.pop(song_plan.FADES, None)
            own.pop(song_plan.FADE_LEVEL, None)
            own.pop(song_plan.FADE_OVER, None)
        if not own:
            del entry[wizard_limits.OWN_OF_SECTION]
        self._choices.clear_answers()
        try:
            self._choices.written_setlist(name=wizard_limits.PREVIEW_NAME, version=version_values.VERSION)
        except (ValueError, KeyError, IndexError, SongFileError) as problem:
            self._choices.get_song_form().restore_own_sections(before)
            self._choices.clear_answers()
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN_UNMADE.format(field=field, value=value, problem=problem)) from None
