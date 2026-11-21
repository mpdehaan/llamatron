# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""One section of the song wizard's form, as the wizard's choices hold it: its kind, its length, who plays in it, what it is
given of its own over the plan and the song, and its lines."""

import copy

from llamatron.model.file import version as version_values
from llamatron.model.file.song_file_error import SongFileError
from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, interplay as interplay_values, joins as joins_values, section_fade, song_plan, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import chord_of, picked, section_of, values_of
from llamatron.wizards.create_song.own_values import checked_own, chords_as_text
from llamatron.wizards.create_song.section_fade import SectionFade
from llamatron.wizards.create_song.section_lines import SectionLines


def own_copy_of(entry):
    """Return a section's entry sharing no list and no dictionary with the entry given."""
    return copy.deepcopy(entry)



# What the song's plan gives a section.
PLANNED_FIELDS = (wizard_names.SONG_PLAN_ENERGY, wizard_names.JOINS_LEAVES, wizard_names.SONG_PLAN_SETUP, wizard_limits.SHAPE_OF_SECTION, wizard_names.SONG_PLAN_RISES)


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
        form = self._choices.get_song_form()
        entries = form.own_section_entries()
        entries.insert(self._place + 1, entry)

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
        kind = self.kind()
        if not self._choices.fills(kind=kind, bars=bars, plays=tuple(self.plays())):
            return False
        trial = self._choices.copied_for_trial()
        trial_form = trial.get_song_form()
        entries = trial_form.own_section_entries()
        entries[self._place][arranger.BARS] = bars
        try:
            trial.written_setlist(name=kind, version=version_values.VERSION)
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
        """Return the fields a section can be given of its own, in the order shown: none without a plan, and no join for the last
        section or a held one."""
        if not self._choices.is_ready() or self.is_held():
            return []
        fade_fields = self.fade().fields()
        if not self._choices.has_song_plan():
            return [*wizard_limits.OWN_WITHOUT_PLAN, *fade_fields]
        leaves = self._leaves_for_next()
        fields = [wizard_names.SONG_PLAN_ENERGY]
        if self.shapes():
            fields.append(wizard_limits.SHAPE_OF_SECTION)
        if leaves:
            fields.append(wizard_names.SONG_PLAN_RISES)
        fields.extend(fade_fields)
        if leaves:
            fields.extend([wizard_names.JOINS_LEAVES, wizard_names.SONG_PLAN_SETUP])
        fields.extend([wizard_names.ARRANGER_CHORDS, wizard_names.TEMPO_OF_PLACE, wizard_names.TEMPO_END_OF_PLACE, wizard_names.ROOT_OF_PLACE, wizard_names.TYPE_OF_PLACE])
        return fields

    def _leaves_for_next(self):
        """Return whether the plan has the section leave for the next one."""
        joins = self._choices.plan_joins()
        return self._place < len(joins) and joins[self._place] is not None

    def shapes(self):
        """Return the shapes a section's lines may take besides its kind's own, by name."""
        return list(self.usual().get(wizard_limits.SHAPES, {}))

    def own(self, *, field):
        """Return what a section was given of its own for a field, or None."""
        given = self._own_given()
        return copy.deepcopy(given.get(field))

    def _own_given(self):
        """Return what the section was given of its own, as its entry holds it; no caller changes it."""
        entry = self.entry()
        return entry.get(wizard_limits.OWN_OF_SECTION, {})

    def from_plan(self, *, field):
        """Return what a section takes for a field where it is given nothing: the song's chords, tempo and key, no fade, and the
        plan's Energy, join, setup, shape and rise."""
        if field in section_fade.FADE_FIELDS:
            fade = self.fade()
            return fade.from_plan(field)
        if field in PLANNED_FIELDS:
            return self._planned(field)
        return self._from_song(field)

    def _from_song(self, field):
        """Return what the song gives a section that was given no chords, tempo or key of its own."""
        if field == wizard_names.ARRANGER_CHORDS:
            return chords_as_text(self.chords_at())
        if field == wizard_names.ROOT_OF_PLACE:
            return self._choices.get_root()
        if field == wizard_names.TYPE_OF_PLACE:
            return self._choices.get_scale_type()
        # Both of a section's tempos start from its own first tempo, or the song's.
        return self.own(field=wizard_names.TEMPO_OF_PLACE) or self._choices.get_tempo()

    def _planned(self, field):
        """Return what the song's plan gives a section: its Energy, how it leaves for the next, its setup, its shape and whether it rises."""
        # The plan's place in the extras is made here, and a song with no plan is refused.
        self._choices.plan_extras()
        if field == wizard_names.SONG_PLAN_ENERGY:
            energies = self._choices.energies()
            return energies[self._place]
        if field == wizard_names.JOINS_LEAVES:
            return self._planned_leaving()
        if field == wizard_names.SONG_PLAN_SETUP:
            return wizard_limits.SETUP_USUAL
        if field == wizard_limits.SHAPE_OF_SECTION:
            # A solo after the song's first is a stage, which takes the next of its kind's shapes.
            shapes = self._choices.plan_shapes()
            return shapes[self._place] or wizard_limits.SHAPE_USUAL
        style = self._choices.style()
        plan = style[song_plan.PLAN_OF_SONG]
        return self.kind() in plan.get(song_plan.RISING, [])

    def _planned_leaving(self):
        """Return how the plan has the section leave for the next: its tail, or the size of its fill, or nothing."""
        joins = self._choices.plan_joins()
        join = joins[self._place] or {}
        if join.get(joins_values.TAIL):
            return join[joins_values.TAIL]
        # A fill is said by its size, as it is chosen.
        style = self._choices.style()
        plan = style[song_plan.PLAN_OF_SONG]
        fills = plan.get(song_plan.FILL_SIZES, {})
        fill = join.get(joins_values.FILL_OF_JOIN)
        for way, given in wizard_limits.LEAVES_AS_JOIN.items():
            if song_plan.FILL_SIZE in given and fills.get(given[song_plan.FILL_SIZE]) == fill:
                return way
        return wizard_limits.LEAVES_NOTHING

    def chords_at(self):
        """Return the chords a section plays where it is given none: its kind's own, the progression's for the kind, or the progression's."""
        style = self._choices.style()
        song = self._choices.song_picks(wizard_limits.PREVIEW_NAME)
        picks = picked(style=style, song=song)
        trait = self._choices.progression_trait()
        ways = values_of(style=style, trait=trait)
        entry = ways[picks[trait]]
        kind = self.kind()
        sections = style[arranger.SECTIONS]
        by_section = entry.get(arranger.BY_SECTION, {})
        written = sections[kind].get(wizard_names.ARRANGER_CHORDS) or by_section.get(kind) or entry[arranger.PATTERN]
        return [chord_of(chord) for chord in written]

    def set_own(self, *, field, value):
        """Give a section something of its own, or give the field back with None. What the song cannot then be made with is refused, and nothing changes."""
        if field not in (*wizard_limits.OWN_WITHOUT_PLAN, *wizard_limits.FADE_OWN):
            self._choices.plan_extras()
        self.store_own(field=field, value=value)

    def store_own(self, *, field, value):
        """Give the section a value of its own for a field, or give the field back with None. A value the section cannot take,
        and one the song cannot then be made with, are refused and nothing changes."""
        # A section no longer in the form is refused.
        self.entry()
        checked = None
        if value is not None:
            checked = checked_own(field=field, value=value)
        if checked is not None and not self._takes_own(field=field, checked=checked):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))
        form = self._choices.get_song_form()
        before = copy.deepcopy(form.get_own_sections())
        self._write_own(field=field, checked=checked)
        self._choices.clear_answers()
        try:
            self._choices.written_setlist(name=wizard_limits.PREVIEW_NAME, version=version_values.VERSION)
        except (ValueError, KeyError, IndexError, SongFileError) as problem:
            form.restore_own_sections(before)
            self._choices.clear_answers()
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN_UNMADE.format(field=field, value=value, problem=problem)) from None

    def _takes_own(self, *, field, checked):
        """Return whether the section can take a value of its own: a shape its kind has, and a fade only where the section opens
        or closes the song, its level and bars only while the fade is switched on, and never more bars than the section has."""
        if field == wizard_limits.SHAPE_OF_SECTION:
            return checked in self.shapes()
        if field not in section_fade.FADE_FIELDS:
            return True
        fade = self.fade()
        if fade.way() is None:
            return False
        if field != wizard_names.SONG_PLAN_FADES and field not in fade.fields():
            return False
        return field != wizard_names.FADE_OVER or checked <= self.bars()

    def _write_own(self, *, field, checked):
        """Write a value of the section's own into its entry, or take the field away with None; a fade switched off keeps
        nothing of how it faded, and a section left with nothing of its own holds no place for it."""
        form = self._choices.get_song_form()
        entries = form.own_section_entries()
        entry = entries[self._place]
        own = entry.setdefault(wizard_limits.OWN_OF_SECTION, {})
        own.pop(field, None)
        if checked is not None:
            own[field] = checked
        if field == wizard_names.SONG_PLAN_FADES and not checked:
            for fade_field in section_fade.FADE_FIELDS:
                own.pop(fade_field, None)
        if not own:
            del entry[wizard_limits.OWN_OF_SECTION]

    def has_own_role(self):
        """Return whether the section gives the answering player a role of its own, apart from the plan."""
        return wizard_limits.BESIDE_SAVED in self.entry()

    def has_role(self):
        """Return whether the answering player has something to choose in the section: somebody answers, and the tune's player
        plays in the section."""
        interplay = self._choices.interplay()
        if interplay.answered_by() is None or self.is_held():
            return False
        band = self._choices.get_band()
        return band.tune_player() in self.plays()

    def role(self):
        """Return what the answering player does in the section: the section's own choice, or the plan's."""
        if not self.has_role():
            raise ValueError(errors.ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=self._place))
        if self.has_own_role():
            return self.entry()[wizard_limits.BESIDE_SAVED]
        interplay = self._choices.interplay()
        return interplay.planned_role(self._place)

    def set_own_role(self, way):
        """Choose what the answering player does in the section, or give the section back to the plan with None."""
        if not self.has_role():
            raise ValueError(errors.ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=self._place))
        if way is not None and way not in interplay_values.WAYS:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=way))
        if way is None and not self.has_own_role():
            return
        form = self._choices.get_song_form()
        entries = form.own_section_entries()
        entry = entries[self._place]
        entry.pop(wizard_limits.BESIDE_SAVED, None)
        if way is not None:
            entry[wizard_limits.BESIDE_SAVED] = way

    def own_chords_typed(self):
        """Return the chords the section was given of its own as they are typed, or None where it was given none."""
        own = self.own(field=wizard_names.ARRANGER_CHORDS)
        if own is None:
            return None
        return chords_as_text(own)

    def lines(self):
        """Return the section's lines: the plan it is played by, and each line as the song makes it."""
        return SectionLines(choices=self._choices, place=self._place)

    def fade(self):
        """Return the section's fade: whether it can fade in or out, and how."""
        return SectionFade(choices=self._choices, place=self._place)
