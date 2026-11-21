# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""How the song is laid out, as the song wizard's choices hold it: the form suggested or the song's own sections, and how the
song starts and ends."""

import copy

from llamatron.caching.cached import as_is, cached_while
from llamatron.model.file import version as version_values
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.schema import limits
from llamatron.user_strings import errors, marks as marks_text
from llamatron.wizards.create_song import arranger, interplay as interplay_values, notation as tune_notation, song_plan, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import bar_length, forms_of, share_of
from llamatron.wizards.create_song.choices_part import ChoicesPart, chosen_only
from llamatron.wizards.create_song.section_choices import own_copy_of
from llamatron.wizards.create_song.song_plan import faded


class FormChoices(ChoicesPart):
    """What was chosen of the song's form: the form suggested by the subgenre, or the song's own sections once a person has
    changed them, and how the song starts and ends, as ways, the first player and the setup's bars."""

    __slots__ = ('_form', '_sections', '_stages', '_cached')

    def __init__(self, *, choices):
        ChoicesPart.__init__(self, choices=choices)
        self._cached = {}
        self.reset()

    def reset(self):
        """Go back to the form the subgenre suggests, started and ended as it starts and ends them."""
        self._form = None
        # The form's sections once a person has changed them, each its kind and what it changes of the kind; None while a suggested form is followed.
        self._sections = None
        # How the song starts and ends, as chosen: the ways, the first player and the setup's bars.
        self._stages = {}

    def style_key(self):
        """Return what the style is worked out from: the genre, the subgenre and the kind of song chosen."""
        choices = self._choices
        return (choices.get_genre(), choices.get_subgenre(), choices.get_variant())

    # What a song keeps of the form.

    def get_written_form(self):
        """Return the form chosen by name, or None while the subgenre's commonest is followed."""
        return self._form

    def get_stages(self):
        """Return how the song starts and ends as chosen, which no caller changes."""
        return self._stages

    def to_data(self):
        """Return what a song keeps of the form, as plain data a song file saves: only what was chosen."""
        held = {
            arranger.FORM: self._form,
            wizard_limits.OWN_SECTIONS: self._saved_own_sections(),
            wizard_limits.STAGES_SAVED: dict(self._stages) or None,
        }
        return chosen_only(held)

    def _saved_own_sections(self):
        """Return a copy of the form's own sections, or None while the form is one the subgenre suggests."""
        if self._sections is None:
            return None
        return [own_copy_of(entry) for entry in self._sections]

    def restore(self, saved):
        """Restore the form's own sections and how the song starts and ends, as a song kept them, leaving out what no longer fits."""
        sections = saved.value(wizard_limits.OWN_SECTIONS)
        if sections:
            saved.apply(self.set_own_sections, sections=sections)
        stages = saved.mapping(wizard_limits.STAGES_SAVED)
        if stages:
            saved.apply(self.restore_stages, stages=stages)

    def add_picks(self, picks):
        """Add the song's form to its picks: its own sections where a person changed them, or the form chosen by name."""
        if self.has_own_form():
            picks[arranger.FORM] = self.form_sections()
        else:
            picks[arranger.FORM] = self.get_form()

    def snapshot(self):
        """Return a copy of the song's own sections and its stages, to go back to after a change that fails."""
        return copy.deepcopy((self._sections, self._stages))

    def go_back_to(self, snapshot):
        """Put back the sections and stages of a snapshot taken before a change the song could not be made with."""
        self._sections, self._stages = snapshot

    def get_own_sections(self):
        return self._sections

    def restore_own_sections(self, sections):
        """Put back the form's own sections as they were kept before a change the song could not be made with."""
        self._sections = sections

    def _forms(self):
        return forms_of(style=self._choices.style(), song={arranger.TEMPLATE: self._choices.get_subgenre()}) if self._choices.is_ready() else []

    def forms(self):
        """Return the names of the forms the subgenre suggests, the commonest first."""
        return [form[arranger.NAME] for form in sorted(self._forms(), key=share_of, reverse=True)]

    def get_form(self):
        """Return the form chosen, or the commonest of the subgenre's until one is, or None before a subgenre is chosen."""
        if self._form is not None:
            return self._form
        forms = self.forms()
        return forms[0] if forms else None

    def form_section_count(self, form):
        """Return how many sections a suggested form has."""
        return len(next((form_[arranger.SECTIONS] for form_ in self._forms() if form_[arranger.NAME] == form), []))

    def set_form(self, form):
        """Choose one of the forms the subgenre suggests, which puts its sections in place of any a person changed. How the song was
        chosen to start and to end is kept, with who starts alone and how long a stage lasts, where the new form can start and end so."""
        if form not in self.forms():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_FORM.format(value=form))
        start = self.get_start() if wizard_limits.START_SAVED in self._stages else None
        end = self.get_end() if wizard_limits.END_SAVED in self._stages else None
        kept = {field: value for field, value in self._stages.items() if field not in (wizard_limits.START_SAVED, wizard_limits.END_SAVED)}
        self._form = form
        self._sections = None
        self._stages = {}
        self._choices.clear_answers()
        for way, offered, set_way in ((start, self.starts, self.set_start), (end, self.ends, self.set_end)):
            if way is not None and way in offered():
                self._stages.update(kept)
                try:
                    set_way(way)
                except ValueError:
                    # A way the new form cannot be made with is given up, and the form starts or ends as it usually does.
                    pass
        if wizard_limits.START_SAVED not in self._stages and wizard_limits.END_SAVED not in self._stages:
            self._stages = {}

    def has_own_form(self):
        """Return whether a person has changed the form's sections, so that the form is no longer one the subgenre suggests."""
        return self._sections is not None

    def section_entries(self):
        """Return the sections in order, each its kind and what it changes of the kind: the song's own, or the chosen form's."""
        if self._sections is not None:
            return self._sections
        return self.form_section_entries()

    def _entries_key(self):
        """What the suggested form's sections are worked out from: the style and the form chosen."""
        return (*self.style_key(), self._form)

    def _labels_key(self):
        """What the sections' labels are worked out from: the form chosen, while a suggested form is followed, and the song's own
        sections' kinds once it has its own."""
        if self._sections is None:
            return self._entries_key()
        return tuple(entry[arranger.KIND] for entry in self._sections)

    @cached_while(_entries_key, said=as_is)
    def form_section_entries(self):
        """Return the sections of the form chosen, each its kind, worked out once for a form, since a page asks for the sections
        many times a key. A caller that changes a section changes its own copy (own_section_entries)."""
        chosen = self.get_form()
        kinds = next((form[arranger.SECTIONS] for form in self._forms() if form[arranger.NAME] == chosen), [])
        return [{arranger.KIND: kind} for kind in kinds]

    def own_section_entries(self):
        """Return the song's own sections to change, starting them from the chosen form the first time."""
        if self._sections is None:
            self._sections = [dict(entry) for entry in self.section_entries()]
        return self._sections

    def form_sections(self):
        """Return the sections of the form in the order they play, by name. A section is named after its kind, and one that
        differs from the first of its kind, in its bars or its players, gets a letter after the name, since sections of one
        name are the same section played again."""
        names = []
        seen = {}
        for place, entry in enumerate(self.section_entries()):
            own = (entry.get(arranger.BARS), tuple(entry[arranger.PLAYS]) if arranger.PLAYS in entry else None)
            if not self._choices.has_song_plan() and self._own_without_plan(entry):
                # A section with chords, a tempo, a key or a scale of its own is a section of its own, where no plan makes one for each place.
                # A fade is told apart by its way, since a kind that opens the song and closes it fades in at one and out at the other.
                own = (*own, repr(sorted(self._choices.section(place).with_fade_way(own=self._own_without_plan(entry)).items(), key=str)))
            # The kind as the genre describes it comes first, so that an unchanged section keeps the kind's plain name.
            variants = seen.setdefault(entry[arranger.KIND], [(None, None)])
            if own not in variants:
                variants.append(own)
            place = variants.index(own)
            names.append(entry[arranger.KIND] if not place else marks_text.MSG_WIZARD_SECTION_VARIANT.format(kind=entry[arranger.KIND], letter=chr(ord(wizard_limits.FIRST_VARIANT_LETTER) + place)))
        return names

    @cached_while(_labels_key, said=as_is)
    def section_labels(self):
        """Return what each section is shown as, in order: its kind, and where the form has several of a kind, the kind with
        a dash and the section's count among them, as the tracker numbers every name it makes."""
        kinds = [entry[arranger.KIND] for entry in self.section_entries()]
        counts = {}
        labels = []
        for kind in kinds:
            counts[kind] = counts.get(kind, 0) + 1
            labels.append(kind if kinds.count(kind) == 1 else marks_text.MSG_WIZARD_SECTION_NUMBERED.format(kind=kind, number=counts[kind]))
        return tuple(labels)

    def song_sections(self):
        """Return the song's own sections as the arranger reads them, by name: each its kind and what it changes, with the chords and the scene's
        tempo, key and scale a section was given where no plan lays those out by place."""
        named = zip(self.form_sections(), self.section_entries())
        return {name: {**tune_notation.without_fields(entry=entry, fields=(wizard_limits.OWN_OF_SECTION,)), **self._as_section(place=place, entry=entry)} for place, (name, entry) in enumerate(named)}

    def _own_without_plan(self, entry):
        """What a section was given of its own that a song with no plan can still take: chords, a tempo, the tempo at its end, a key and a scale."""
        return {field: value for field, value in entry.get(wizard_limits.OWN_OF_SECTION, {}).items() if field in (*wizard_limits.OWN_WITHOUT_PLAN, *wizard_limits.FADE_OWN) or field == wizard_limits.LINES_OF_SECTION}

    def _as_section(self, *, place, entry):
        if self._choices.has_song_plan():
            return {}
        own = self._own_without_plan(entry)
        settings = {}
        if wizard_names.TEMPO_OF_PLACE in own:
            settings[song_plan.SCENE_TEMPO] = own[wizard_names.TEMPO_OF_PLACE]
        if wizard_names.TEMPO_END_OF_PLACE in own:
            settings[song_plan.SCENE_TEMPO_END] = own[wizard_names.TEMPO_END_OF_PLACE]
        if wizard_names.ROOT_OF_PLACE in own or wizard_names.TYPE_OF_PLACE in own:
            settings[song_plan.SCALE_OF_PLACE] = {wizard_names.ROOT_OF_PLACE: own.get(wizard_names.ROOT_OF_PLACE, self._choices.get_root()), wizard_names.TYPE_OF_PLACE: own.get(wizard_names.TYPE_OF_PLACE, self._choices.get_scale_type())}
        if own.get(wizard_names.SONG_PLAN_FADES):
            settings.update(faded(own=self._choices.section(place).with_fade_way(own=own), loud=wizard_names.UNFADED))
        if own.get(wizard_limits.LINES_OF_SECTION):
            return {wizard_limits.PLAN: self._choices.plan_with_lines(kind=entry[arranger.KIND], plan=None, lines=own[wizard_limits.LINES_OF_SECTION]), **({wizard_names.ARRANGER_CHORDS: copy.deepcopy(own[wizard_names.ARRANGER_CHORDS])} if wizard_names.ARRANGER_CHORDS in own else {}), **({arranger.SCENE_SETTINGS: settings} if settings else {})}
        return {**({wizard_names.ARRANGER_CHORDS: copy.deepcopy(own[wizard_names.ARRANGER_CHORDS])} if wizard_names.ARRANGER_CHORDS in own else {}), **({arranger.SCENE_SETTINGS: settings} if settings else {})}

    def section_kinds(self):
        """Return the kinds of section the subgenre can play, in the genre's order: a kind nobody of the subgenre's band plays
        in, which would make no section at all, is left out, as is one whose parts do not fill its own length."""
        if not self._choices.is_ready():
            return []
        sections = self._choices.style()[arranger.SECTIONS]
        return [kind for kind, section in sections.items()
                if self._choices.fills(kind=kind, bars=wizard_limits.HELD_BARS if section.get(arranger.HELD) else section[arranger.BARS])]

    def add_section(self, *, place, kind):
        """Put a new section of a kind before a place in the form, as the genre describes the kind."""
        if kind not in self.section_kinds():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION_KIND.format(value=kind))
        if isinstance(place, bool) or not isinstance(place, int) or not 0 <= place <= len(self.section_entries()):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION.format(value=place))
        self.own_section_entries().insert(place, {arranger.KIND: kind})

    def set_own_sections(self, *, sections):
        """Take a form's sections a song kept, each through the setters, or none of them where one no longer fits."""
        kept = self._sections
        self._sections = []
        try:
            for place, entry in enumerate(sections):
                self.add_section(place=place, kind=entry[arranger.KIND])
                if arranger.BARS in entry:
                    self._choices.section(place).set_bars(bars=entry[arranger.BARS])
                for role in self._choices.get_band().roles():
                    if arranger.PLAYS in entry and (role in entry[arranger.PLAYS]) != (role in self._choices.section(place).plays()) and role in entry[arranger.PLAYS]:
                        self._choices.section(place).set_plays(role=role, on=True)
                for role in self._choices.get_band().roles():
                    if arranger.PLAYS in entry and role not in entry[arranger.PLAYS] and role in self._choices.section(place).plays():
                        self._choices.section(place).set_plays(role=role, on=False)
                if wizard_limits.BESIDE_SAVED in entry:
                    # What the answering player does in the section is kept as chosen, and is used wherever somebody answers there.
                    if entry[wizard_limits.BESIDE_SAVED] not in interplay_values.WAYS:
                        raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=entry[wizard_limits.BESIDE_SAVED]))
                    self._sections[place][wizard_limits.BESIDE_SAVED] = entry[wizard_limits.BESIDE_SAVED]
                if entry.get(wizard_limits.OWN_OF_SECTION):
                    self._sections[place][wizard_limits.OWN_OF_SECTION] = {field: self._choices.checked_own(field=field, value=value) for field, value in entry[wizard_limits.OWN_OF_SECTION].items()}
            if not self._sections:
                raise ValueError(errors.ERR_WIZARD_LAST_SECTION)
        except (KeyError, TypeError, ValueError):
            self._sections = kept
            raise ValueError(errors.ERR_WIZARD_BAD_SECTIONS.format(value=sections)) from None

    def _usual_form_kinds(self):
        return next((form[arranger.SECTIONS] for form in self._forms() if form[arranger.NAME] == self.get_form()), [])

    def intro_kind(self):
        """The kind of section a song of the subgenre opens with: the first of its form's, where that kind has no tune."""
        kinds = self._usual_form_kinds()
        sections = self._choices.style()[arranger.SECTIONS]
        if not kinds or sections[kinds[0]].get(arranger.HELD):
            return None
        # A kind with a tune opens the song only where the form plays the kind once, at its start: one played again later is the song's body.
        return kinds[0] if not sections[kinds[0]].get(wizard_limits.PLAN) or kinds.count(kinds[0]) == 1 else None

    def _ending_kind(self):
        """The kind of section that is one held chord, where the subgenre has one."""
        return next((kind for kind in self.section_kinds() if self._choices.style()[arranger.SECTIONS][kind].get(arranger.HELD)), None)

    def _outro_kind(self):
        """The kind of section played after the last tune: the genre's outro where it has one, else its intro again."""
        return wizard_limits.OUTRO_KIND if wizard_limits.OUTRO_KIND in self.section_kinds() else self.intro_kind()

    def _stage_players(self, kind):
        """Who plays in a kind of section, the first player first and the rest in the band's order."""
        plays = [role for role in self._choices.get_band().roles() if role in self._choices.style()[arranger.SECTIONS][kind].get(arranger.PLAYS, []) and self._choices.player(role).is_in()]
        first = self.get_first_player()
        return [first, *(role for role in plays if role != first)] if first in plays else plays

    def first_players(self):
        """Return who can start the song alone: the players of its opening kind of section."""
        kind = self.intro_kind()
        return [] if kind is None else [role for role in self._choices.get_band().roles() if role in self._choices.style()[arranger.SECTIONS][kind].get(arranger.PLAYS, []) and self._choices.player(role).is_in()]

    def get_first_player(self):
        """Return who starts the song alone and is left alone at its end: the one chosen, or the first of the opening's players who is not the drummer."""
        offered = self.first_players()
        if self._stages.get(wizard_limits.FIRST_PLAYER_SAVED) in offered:
            return self._stages[wizard_limits.FIRST_PLAYER_SAVED]
        return next((role for role in offered if role != self._choices.drums_role()), offered[0] if offered else None)

    def _setup_bars_possible(self):
        """How long a stage could last, in bars: half the opening kind's length, the length and twice it."""
        kind = self.intro_kind()
        if kind is None:
            return []
        usual = self._choices.style()[arranger.SECTIONS][kind][arranger.BARS]
        return sorted({usual // wizard_limits.HALF, usual, usual * wizard_limits.HALF} - {0})

    def setup_bars_offered(self):
        """Return how long a stage of a start or an ending may last, in bars: of the lengths a stage could last, those the song as it starts and ends can be made with."""
        return list(self._choices.offered(key=wizard_limits.SETUP_BARS_ANSWER, compute=lambda: [bars for bars in self._setup_bars_possible() if bars == self.get_setup_bars() or self._setup_bars_work(bars)]))

    def _setup_bars_work(self, bars):
        trial = self._choices.copied_for_trial()
        try:
            form = trial.get_song_form()
            form._restaged(change=lambda: form._stages.update({wizard_limits.SETUP_BARS_SAVED: bars}))
        except ValueError:
            return False
        return True

    def get_setup_bars(self):
        possible = self._setup_bars_possible()
        kept = self._stages.get(wizard_limits.SETUP_BARS_SAVED)
        return kept if kept in possible else (self._choices.style()[arranger.SECTIONS][self.intro_kind()][arranger.BARS] if possible else None)

    def _stage(self, *, kind, plays=None, own=None):
        """One stage: a section of a kind, played by some of its players for the setup's bars, with what the stage is given of its own."""
        usual = self._choices.style()[arranger.SECTIONS][kind]
        entry = {arranger.KIND: kind}
        if plays is not None and sorted(plays) != sorted(usual.get(arranger.PLAYS, [])):
            entry[arranger.PLAYS] = [role for role in self._choices.get_band().roles() if role in plays]
        if not usual.get(arranger.HELD) and self.get_setup_bars() != usual[arranger.BARS]:
            entry[arranger.BARS] = self.get_setup_bars()
        if own:
            entry[wizard_limits.OWN_OF_SECTION] = dict(own)
        return entry

    def _start_stages(self, way):
        """The sections a way of starting puts before the song's first tune, or None where the subgenre cannot start that way."""
        kind = self.intro_kind()
        drums = self._choices.drums_role()
        if kind is None:
            return None
        players = self._stage_players(kind)
        whole = {arranger.KIND: kind}
        if way == wizard_limits.FULL_BAND:
            return [whole]
        if way == wizard_limits.STRAIGHT_IN:
            return []
        if way == wizard_limits.DRUMS_FIRST and drums in players and len(players) > 1:
            return [self._stage(kind=kind, plays=[drums]), whole]
        if way == wizard_limits.DRUM_FILL_IN and drums in players and self._choices.has_song_plan():
            return [self._stage(kind=kind, plays=[drums], own={wizard_names.JOINS_LEAVES: wizard_limits.LEAVES_BIG_FILL})]
        if way == wizard_limits.ONE_PLAYER_FIRST and len(players) > 1 and players[0] != drums:
            return [self._stage(kind=kind, plays=players[:1]), whole]
        if way == wizard_limits.LAYERS and len(players) > 2:
            return [self._stage(kind=kind, plays=players[:count]) for count in range(1, len(players) + 1)]
        return None

    def _end_stages(self, way):
        """The sections a way of ending puts after the song's last tune, or None where the subgenre cannot end that way."""
        held = self._ending_kind()
        outro = self._outro_kind()
        chord = [{arranger.KIND: held}] if held is not None else []
        if way == wizard_limits.HELD_CHORD and held is not None:
            return chord
        if way == wizard_limits.HARD_STOP:
            return []
        if outro is None:
            return None
        players = self._stage_players(outro)
        if way == wizard_limits.OUTRO_THEN_CHORD and held is not None:
            return [self._stage(kind=outro), *chord]
        if way == wizard_limits.SLOWS_DOWN:
            return [self._stage(kind=outro, own={wizard_names.TEMPO_END_OF_PLACE: max(self._choices.get_tempo() * wizard_limits.SLOWED_TO[0] // wizard_limits.SLOWED_TO[1], limits.MIN_TEMPO)}), *chord]
        if way == wizard_limits.STRIPS_DOWN and len(players) > 2:
            return [*(self._stage(kind=outro, plays=players[:count]) for count in range(len(players) - 1, 0, -1)), *chord]
        if way == wizard_limits.ONE_PLAYER_ALONE and len(players) > 1:
            return [self._stage(kind=outro, plays=players[:1]), *chord]
        if way == wizard_limits.REPEAT_AND_FADE:
            return [self._stage(kind=outro, own={wizard_names.SONG_PLAN_FADES: True})]
        return None

    def starts(self):
        """Return the ways the song can start, the plainest first."""
        return [way for way in wizard_limits.STARTS if self._start_stages(way) is not None] if self._choices.is_ready() else []

    def ends(self):
        """Return the ways the song can end."""
        return [way for way in wizard_limits.ENDS if self._end_stages(way) is not None] if self._choices.is_ready() else []

    def head_count(self):
        """How many sections open the song before its first tune: those the way of starting kept made, while they stand as made, else the sections of the opening kind."""
        kept = self._start_stages(self._stages.get(wizard_limits.START_SAVED)) if wizard_limits.START_SAVED in self._stages else None
        entries = self.section_entries()
        if kept is not None and entries[:len(kept)] == kept:
            return len(kept)
        count = 0
        while count < len(entries) - 1 and entries[count][arranger.KIND] == self.intro_kind():
            count += 1
        return count

    def tail_count(self):
        """How many sections close the song after its last tune: those the way of ending kept made, while they stand as made, else the held chord and the outro before it."""
        kept = self._end_stages(self._stages.get(wizard_limits.END_SAVED)) if wizard_limits.END_SAVED in self._stages else None
        entries = self.section_entries()
        if kept is not None and (not kept or entries[-len(kept):] == kept):
            return len(kept)
        count = 0
        closing = (self._ending_kind(), wizard_limits.OUTRO_KIND)
        while count < len(entries) - 1 and entries[len(entries) - 1 - count][arranger.KIND] in closing:
            count += 1
        return count

    def get_start(self):
        """Return the way the song starts, or None where its opening sections are a person's own."""
        entries = self.section_entries()
        head = entries[:self.head_count()]
        kept = self._stages.get(wizard_limits.START_SAVED)
        if kept in self.starts() and self._start_stages(kept) == head:
            return kept
        return next((way for way in self.starts() if self._start_stages(way) == head), None)

    def get_end(self):
        """Return the way the song ends, or None where its closing sections are a person's own."""
        entries = self.section_entries()
        tail = entries[len(entries) - self.tail_count():]
        kept = self._stages.get(wizard_limits.END_SAVED)
        if kept in self.ends() and self._end_stages(kept) == tail:
            return kept
        return next((way for way in self.ends() if self._end_stages(way) == tail), None)

    def _restaged(self, *, change, start=None, end=None):
        """Change how the song starts or ends: the sections between stay, and the stages are made again. A song that cannot then be made is as it was."""
        before = (copy.deepcopy(self._sections), dict(self._stages))
        entries = [own_copy_of(entry) for entry in self.section_entries()]
        head, tail = self.head_count(), self.tail_count()
        start = self.get_start() if start is None else start
        end = self.get_end() if end is None else end
        body = entries[head:len(entries) - tail]
        try:
            change()
            opening = entries[:head] if start is None else self._start_stages(start)
            closing = entries[len(entries) - tail:] if end is None else self._end_stages(end)
            if opening is None or closing is None or not body:
                raise ValueError(errors.ERR_WIZARD_START_UNMADE.format(problem=start if opening is None else end))
            self._sections = [*(own_copy_of(entry) for entry in opening), *body, *(own_copy_of(entry) for entry in closing)]
            if start is not None:
                self._stages[wizard_limits.START_SAVED] = start
            if end is not None:
                self._stages[wizard_limits.END_SAVED] = end
            self._choices.clear_answers()
            self._choices.written_setlist(name=wizard_limits.PREVIEW_NAME, version=version_values.VERSION)
        except (ValueError, KeyError, IndexError, SongFileError) as problem:
            self._sections, self._stages = before
            self._choices.clear_answers()
            raise ValueError(errors.ERR_WIZARD_START_UNMADE.format(problem=problem)) from None

    def set_start(self, way):
        if way not in self.starts():
            raise ValueError(errors.ERR_WIZARD_START.format(value=way))
        self._restaged(change=lambda: None, start=way)

    def set_end(self, way):
        if way not in self.ends():
            raise ValueError(errors.ERR_WIZARD_END.format(value=way))
        self._restaged(change=lambda: None, end=way)

    def set_first_player(self, role):
        if role not in self.first_players():
            raise ValueError(errors.ERR_WIZARD_FIRST_PLAYER.format(value=role))
        self._restaged(change=lambda: self._stages.update({wizard_limits.FIRST_PLAYER_SAVED: role}))

    def set_setup_bars(self, bars):
        if isinstance(bars, bool) or bars not in self.setup_bars_offered():
            raise ValueError(errors.ERR_WIZARD_SETUP_BARS.format(value=bars))
        self._restaged(change=lambda: self._stages.update({wizard_limits.SETUP_BARS_SAVED: bars}))

    def form_questions(self):
        """Return the questions a form is made from, in order, each its name, the answers offered and the usual answer."""
        kinds = self.section_kinds()
        questions = [(wizard_limits.VERSES_FIRST, wizard_limits.COUNTS_ONE_OR_TWO, wizard_limits.ONE)]
        if wizard_limits.PRE_CHORUS in kinds:
            questions.append((wizard_limits.PRE_CHORUSES, wizard_limits.PRE_CHORUS_ANSWERS, wizard_limits.NO))
        if wizard_limits.BRIDGE in kinds:
            questions.append((wizard_limits.BRIDGE, wizard_limits.YES_OR_NO, wizard_limits.YES))
        if wizard_limits.SOLO in kinds:
            questions.append((wizard_limits.SOLOS, wizard_limits.SOLO_COUNTS, wizard_limits.ONE))
        if wizard_limits.DRUM_SOLO_KIND in kinds:
            questions.append((wizard_limits.DRUM_SOLO_KIND, wizard_limits.YES_OR_NO, wizard_limits.NO))
        return [*questions, (wizard_limits.LAST_CHORUSES, wizard_limits.COUNTS_ONE_OR_TWO, wizard_limits.TWO)] if wizard_limits.CHORUS_KIND in kinds and wizard_limits.VERSE_KIND in kinds else []

    def form_of_answers(self, answers):
        """Return the kinds of section, in order, of the form some answers ask for: a question left out takes its usual answer."""
        asked = {name: (offered, usual) for name, offered, usual in self.form_questions()}
        if not asked:
            raise ValueError(errors.ERR_WIZARD_NO_FORM_QUESTIONS)
        given = {}
        for name, (offered, usual) in asked.items():
            given[name] = answers.get(name, usual)
            if given[name] not in offered:
                raise ValueError(errors.ERR_WIZARD_FORM_ANSWER.format(name=name, value=given[name]))
        unknown = [name for name in answers if name not in asked]
        if unknown:
            raise ValueError(errors.ERR_WIZARD_FORM_ANSWER.format(name=unknown[0], value=answers[unknown[0]]))
        kinds = self.section_kinds()
        before = given.get(wizard_limits.PRE_CHORUSES, wizard_limits.NO)
        solos = wizard_limits.SOLO_COUNTS.index(given.get(wizard_limits.SOLOS, wizard_limits.NONE_OF))

        def chorus(count):
            """A chorus, with a pre-chorus before it where the answers ask for one before this chorus."""
            return ([wizard_limits.PRE_CHORUS] if before == wizard_limits.BEFORE_EVERY or (before == wizard_limits.BEFORE_FIRST_TWO and count <= 2) else []) + [wizard_limits.CHORUS_KIND]
        form = [wizard_limits.INTRO] if wizard_limits.INTRO in kinds else []
        form += [wizard_limits.VERSE_KIND] * wizard_limits.COUNTS_ONE_OR_TWO.index(given[wizard_limits.VERSES_FIRST]) + [wizard_limits.VERSE_KIND] + chorus(1) + [wizard_limits.VERSE_KIND] + chorus(2)
        # The middle of the song: a first solo, the bridge, the drummer alone, and the solo that leads back to the last choruses.
        form += [wizard_limits.SOLO] if solos == 2 else []
        form += [wizard_limits.BRIDGE] if given.get(wizard_limits.BRIDGE) == wizard_limits.YES else []
        form += [wizard_limits.DRUM_SOLO_KIND] if given.get(wizard_limits.DRUM_SOLO_KIND) == wizard_limits.YES else []
        form += [wizard_limits.SOLO] if solos else []
        form += chorus(3) + [wizard_limits.CHORUS_KIND] * wizard_limits.COUNTS_ONE_OR_TWO.index(given[wizard_limits.LAST_CHORUSES])
        return form + ([wizard_limits.ENDING] if wizard_limits.ENDING in kinds else [])

    def set_form_from_answers(self, answers):
        """Make the form some answers ask for the song's own, in place of its sections, or leave the form as it was where the answers are refused."""
        self.set_own_sections(sections=[{arranger.KIND: kind} for kind in self.form_of_answers(answers)])
        self._choices.clear_answers()

    def form_seconds(self, *, form=None):
        """Return how long the song lasts at the tempo chosen, in seconds; or how long a suggested form would, when one is named."""
        if form is None:
            bars = sum(self._choices.section(place).bars() for place in range(len(self.section_entries())))
        else:
            style = self._choices.style()
            kinds = next((form_[arranger.SECTIONS] for form_ in self._forms() if form_[arranger.NAME] == form), [])
            bars = sum(wizard_limits.HELD_BARS if style[arranger.SECTIONS][kind].get(arranger.HELD) else style[arranger.SECTIONS][kind][arranger.BARS] for kind in kinds)
        return float(bars * bar_length(self._choices.meter()) * wizard_limits.QUARTERS_IN_WHOLE * wizard_limits.SECONDS_IN_MINUTE / self._choices.get_tempo())

    def forms_by_length(self):
        """Return the forms' names from the shortest to the longest, forms of one length in the order they are suggested."""
        return sorted(self.forms(), key=lambda form: self.form_seconds(form=form))

    def section_kinds_in_form(self):
        """Return the kind of each section of the song's form, in order."""
        return [self._choices.section(place).kind() for place in range(len(self.section_labels()))]

    def forget_section_beside(self):
        """Forget what single sections were given of what the answering player does, which a plan for every section takes the place of."""
        if self._sections is not None:
            for entry in self._sections:
                entry.pop(wizard_limits.BESIDE_SAVED, None)

    def restore_stages(self, *, stages):
        """Take how a song starts and ends as a song kept it: the sections are the song's already, so only what was chosen is kept, where it is still offered."""
        kept = {field: value for field, value in stages.items() if field in (wizard_limits.START_SAVED, wizard_limits.END_SAVED, wizard_limits.FIRST_PLAYER_SAVED, wizard_limits.SETUP_BARS_SAVED)}
        self._stages = {field: value for field, value in kept.items() if isinstance(value, (str, int)) and not isinstance(value, bool)}
