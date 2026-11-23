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
from llamatron.music_theory.composing import notation as tune_notation
from llamatron.user_strings import errors, marks as marks_text
from llamatron.wizards.create_song import arranger, interplay as interplay_values, song_plan, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import bar_length, forms_of, share_of
from llamatron.wizards.create_song.choices_part import add_counted, ChoicesPart, chosen_only
from llamatron.wizards.create_song.own_values import checked_own
from llamatron.wizards.create_song.section_choices import own_copy_of
from llamatron.wizards.create_song.song_plan import faded

# What a song saves of how it starts and ends.
STAGE_FIELDS = (wizard_limits.START_SAVED, wizard_limits.END_SAVED, wizard_limits.FIRST_PLAYER_SAVED, wizard_limits.SETUP_BARS_SAVED)


def _chorus(*, count, before):
    """Return a chorus, with a pre-chorus before it where the answers ask for one before this chorus."""
    if before == wizard_limits.BEFORE_EVERY or (before == wizard_limits.BEFORE_FIRST_TWO and count <= 2):
        return [wizard_limits.PRE_CHORUS, wizard_limits.CHORUS_KIND]
    return [wizard_limits.CHORUS_KIND]


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
        return len(self._kinds_of_form(form))

    def _kinds_of_form(self, name):
        """Return the kinds of section a suggested form plays, in order, or none where the subgenre suggests no form of the name."""
        for form in self._forms():
            if form[arranger.NAME] == name:
                return form[arranger.SECTIONS]
        return []

    def _kind_entry(self, kind):
        """Return what the genre writes of a kind of section."""
        style = self._choices.style()
        sections = style[arranger.SECTIONS]
        return sections[kind]

    def _usual_bars(self, kind):
        """Return how many bars a kind of section usually lasts: a held chord, one bar's worth, and any other its written length."""
        section = self._kind_entry(kind)
        if section.get(arranger.HELD):
            return wizard_limits.HELD_BARS
        return section[arranger.BARS]

    def _players_of_kind(self, kind):
        """Return who of the band plays in a kind of section, in the band's order, leaving out a player who is not in the band."""
        section = self._kind_entry(kind)
        written = section.get(arranger.PLAYS, [])
        band = self._choices.get_band()
        players = []
        for role in band.roles():
            player = self._choices.player(role)
            if role in written and player.is_in():
                players.append(role)
        return players

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
        kinds = [entry[arranger.KIND] for entry in self._sections]
        return tuple(kinds)

    @cached_while(_entries_key, said=as_is)
    def form_section_entries(self):
        """Return the sections of the form chosen, each its kind, worked out once for a form, since a page asks for the sections
        many times a key. A caller that changes a section changes its own copy (own_section_entries)."""
        kinds = self._kinds_of_form(self.get_form())
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
            kind = entry[arranger.KIND]
            own = self._what_tells_apart(place=place, entry=entry)
            # The kind as the genre describes it comes first, so that an unchanged section keeps the kind's plain name.
            variants = seen.setdefault(kind, [(None, None)])
            if own not in variants:
                variants.append(own)
            names.append(self._variant_name(kind=kind, number=variants.index(own)))
        return names

    def _what_tells_apart(self, *, place, entry):
        """Return what tells a section apart from others of its kind: its bars and its players, and where no plan makes a section
        for each place, what it was given of its own."""
        plays = None
        if arranger.PLAYS in entry:
            plays = tuple(entry[arranger.PLAYS])
        own = (entry.get(arranger.BARS), plays)
        if self._choices.has_song_plan():
            return own
        given = self._own_without_plan(entry)
        if not given:
            return own
        # A section with chords, a tempo, a key or a scale of its own is a section of its own, where no plan makes one for each place.
        # A fade is told apart by its way, since a kind that opens the song and closes it fades in at one and out at the other.
        section = self._choices.section(place)
        fade = section.fade()
        with_fade = fade.with_way(own=given)
        return (*own, repr(sorted(with_fade.items(), key=str)))

    @staticmethod
    def _variant_name(*, kind, number):
        """Return the name of a kind's variant: the kind's own for the first, and the kind with a letter for each after it."""
        if not number:
            return kind
        letter = chr(ord(wizard_limits.FIRST_VARIANT_LETTER) + number)
        return marks_text.MSG_WIZARD_SECTION_VARIANT.format(kind=kind, letter=letter)

    @cached_while(_labels_key, said=as_is)
    def section_labels(self):
        """Return what each section is shown as, in order: its kind, and where the form has several of a kind, the kind with
        a dash and the section's count among them, as the tracker numbers every name it makes."""
        kinds = [entry[arranger.KIND] for entry in self.section_entries()]
        counts = {}
        labels = []
        for kind in kinds:
            counts[kind] = counts.get(kind, 0) + 1
            if kinds.count(kind) == 1:
                labels.append(kind)
            else:
                labels.append(marks_text.MSG_WIZARD_SECTION_NUMBERED.format(kind=kind, number=counts[kind]))
        return tuple(labels)

    def song_sections(self):
        """Return the song's own sections as the arranger reads them, by name: each its kind and what it changes, with the chords
        and the scene's tempo, key and scale a section was given where no plan lays those out by place."""
        sections = {}
        named = zip(self.form_sections(), self.section_entries())
        for place, (name, entry) in enumerate(named):
            section = dict(tune_notation.without_fields(entry=entry, fields=(wizard_limits.OWN_OF_SECTION,)))
            section.update(self._as_section(place=place, entry=entry))
            sections[name] = section
        return sections

    def _own_without_plan(self, entry):
        """Return what a section was given of its own that a song with no plan can still take: chords, a tempo, the tempo at its
        end, a key, a scale, a fade and its lines."""
        given = entry.get(wizard_limits.OWN_OF_SECTION, {})
        kept = {}
        for field, value in given.items():
            if field in wizard_limits.OWN_WITHOUT_PLAN or field in wizard_limits.FADE_OWN or field == wizard_limits.LINES_OF_SECTION:
                kept[field] = value
        return kept

    def _as_section(self, *, place, entry):
        """Return what a section of a song with no plan says of its own as the arranger reads it: its lines laid into its plan,
        its chords and its scene's settings."""
        if self._choices.has_song_plan():
            return {}
        own = self._own_without_plan(entry)
        section = {}
        if own.get(wizard_limits.LINES_OF_SECTION):
            section[wizard_limits.PLAN] = self._choices.plan_with_lines(kind=entry[arranger.KIND], plan=None, lines=own[wizard_limits.LINES_OF_SECTION])
        if wizard_names.ARRANGER_CHORDS in own:
            section[wizard_names.ARRANGER_CHORDS] = copy.deepcopy(own[wizard_names.ARRANGER_CHORDS])
        settings = self._scene_settings(place=place, own=own)
        if settings:
            section[arranger.SCENE_SETTINGS] = settings
        return section

    def _scene_settings(self, *, place, own):
        """Return the settings a section's scene takes of what it was given of its own: its tempos, its key and scale, and its fade."""
        settings = {}
        if wizard_names.TEMPO_OF_PLACE in own:
            settings[song_plan.SCENE_TEMPO] = own[wizard_names.TEMPO_OF_PLACE]
        if wizard_names.TEMPO_END_OF_PLACE in own:
            settings[song_plan.SCENE_TEMPO_END] = own[wizard_names.TEMPO_END_OF_PLACE]
        if wizard_names.ROOT_OF_PLACE in own or wizard_names.TYPE_OF_PLACE in own:
            root = own.get(wizard_names.ROOT_OF_PLACE, self._choices.get_root())
            scale_type = own.get(wizard_names.TYPE_OF_PLACE, self._choices.get_scale_type())
            settings[song_plan.SCALE_OF_PLACE] = {wizard_names.ROOT_OF_PLACE: root, wizard_names.TYPE_OF_PLACE: scale_type}
        if own.get(wizard_names.SONG_PLAN_FADES):
            section = self._choices.section(place)
            fade = section.fade()
            settings.update(faded(own=fade.with_way(own=own), loud=wizard_names.UNFADED))
        return settings

    def section_kinds(self):
        """Return the kinds of section the subgenre can play, in the genre's order: a kind nobody of the subgenre's band plays
        in, which would make no section at all, is left out, as is one whose parts do not fill its own length."""
        if not self._choices.is_ready():
            return []
        style = self._choices.style()
        kinds = []
        for kind in style[arranger.SECTIONS]:
            if self._choices.fills(kind=kind, bars=self._usual_bars(kind)):
                kinds.append(kind)
        return kinds

    def add_section(self, *, place, kind):
        """Put a new section of a kind before a place in the form, as the genre describes the kind."""
        if kind not in self.section_kinds():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION_KIND.format(value=kind))
        if isinstance(place, bool) or not isinstance(place, int) or not 0 <= place <= len(self.section_entries()):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION.format(value=place))
        self.own_section_entries().insert(place, {arranger.KIND: kind})

    def set_own_sections(self, *, sections):
        """Take a form's sections a song saved, each through the setters, or none of them where one no longer fits."""
        kept = self._sections
        self._sections = []
        try:
            for place, entry in enumerate(sections):
                self._add_saved_section(place=place, entry=entry)
            if not self._sections:
                raise ValueError(errors.ERR_WIZARD_LAST_SECTION)
        except (KeyError, TypeError, ValueError):
            self._sections = kept
            raise ValueError(errors.ERR_WIZARD_BAD_SECTIONS.format(value=sections)) from None

    def _add_saved_section(self, *, place, entry):
        """Add a section a song saved, through the setters: its kind, its bars, who plays in it, what the answering player does
        in it and what it was given of its own."""
        self.add_section(place=place, kind=entry[arranger.KIND])
        section = self._choices.section(place)
        if arranger.BARS in entry:
            section.set_bars(bars=entry[arranger.BARS])
        if arranger.PLAYS in entry:
            self._set_saved_players(section=section, plays=entry[arranger.PLAYS])
        if wizard_limits.BESIDE_SAVED in entry:
            # What the answering player does in the section is saved as chosen, and is used wherever somebody answers there.
            way = entry[wizard_limits.BESIDE_SAVED]
            if way not in interplay_values.WAYS:
                raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=way))
            self._sections[place][wizard_limits.BESIDE_SAVED] = way
        if entry.get(wizard_limits.OWN_OF_SECTION):
            own = {}
            for field, value in entry[wizard_limits.OWN_OF_SECTION].items():
                own[field] = checked_own(field=field, value=value)
            self._sections[place][wizard_limits.OWN_OF_SECTION] = own

    def _set_saved_players(self, *, section, plays):
        """Have exactly the players a song saved play in a section: each named joins, then each not named leaves."""
        band = self._choices.get_band()
        for role in band.roles():
            if role in plays and role not in section.plays():
                section.set_plays(role=role, on=True)
        for role in band.roles():
            if role not in plays and role in section.plays():
                section.set_plays(role=role, on=False)

    def _usual_form_kinds(self):
        """Return the kinds of section of the form chosen, in order."""
        return self._kinds_of_form(self.get_form())

    def intro_kind(self):
        """The kind of section a song of the subgenre opens with: the first of its form's, where that kind has no tune."""
        kinds = self._usual_form_kinds()
        sections = self._choices.style()[arranger.SECTIONS]
        if not kinds or sections[kinds[0]].get(arranger.HELD):
            return None
        # A kind with a tune opens the song only where the form plays the kind once, at its start: one played again later is the song's body.
        return kinds[0] if not sections[kinds[0]].get(wizard_limits.PLAN) or kinds.count(kinds[0]) == 1 else None

    def _ending_kind(self):
        """Return the kind of section that is one held chord, where the subgenre has one."""
        for kind in self.section_kinds():
            section = self._kind_entry(kind)
            if section.get(arranger.HELD):
                return kind
        return None

    def _outro_kind(self):
        """The kind of section played after the last tune: the genre's outro where it has one, else its intro again."""
        return wizard_limits.OUTRO_KIND if wizard_limits.OUTRO_KIND in self.section_kinds() else self.intro_kind()

    def _stage_players(self, kind):
        """Return who plays in a kind of section, the first player first and the rest in the band's order."""
        plays = self._players_of_kind(kind)
        first = self.get_first_player()
        if first not in plays:
            return plays
        others = [role for role in plays if role != first]
        return [first, *others]

    def first_players(self):
        """Return who can start the song alone: the players of its opening kind of section."""
        kind = self.intro_kind()
        if kind is None:
            return []
        return self._players_of_kind(kind)

    def get_first_player(self):
        """Return who starts the song alone and is left alone at its end: the one chosen, or the first of the opening's players
        who is not the drummer."""
        offered = self.first_players()
        chosen = self._stages.get(wizard_limits.FIRST_PLAYER_SAVED)
        if chosen in offered:
            return chosen
        drummer = self._choices.drums_role()
        for role in offered:
            if role != drummer:
                return role
        if offered:
            return offered[0]
        return None

    def _setup_bars_possible(self):
        """How long a stage could last, in bars: half the opening kind's length, the length and twice it."""
        kind = self.intro_kind()
        if kind is None:
            return []
        usual = self._choices.style()[arranger.SECTIONS][kind][arranger.BARS]
        return sorted({usual // wizard_limits.HALF, usual, usual * wizard_limits.HALF} - {0})

    def setup_bars_offered(self):
        """Return how long a stage of a start or an ending may last, in bars: of the lengths a stage could last, those the song
        as it starts and ends can be made with."""
        offered = self._choices.offered(key=wizard_limits.SETUP_BARS_ANSWER, compute=self._setup_bars_working)
        return list(offered)

    def _setup_bars_working(self):
        """Return the lengths a stage could last that the song can be made with, and the length chosen."""
        chosen = self.get_setup_bars()
        working = []
        for bars in self._setup_bars_possible():
            if bars == chosen or self._setup_bars_work(bars):
                working.append(bars)
        return working

    def _setup_bars_work(self, bars):
        trial = self._choices.copied_for_trial()
        try:
            form = trial.get_song_form()
            form._restaged(change=lambda: form._stages.update({wizard_limits.SETUP_BARS_SAVED: bars}))
        except ValueError:
            return False
        return True

    def get_setup_bars(self):
        """Return how long a stage of a start or an ending lasts, in bars: the length chosen, or the opening kind's own, or None
        where no stage can be set up."""
        possible = self._setup_bars_possible()
        chosen = self._stages.get(wizard_limits.SETUP_BARS_SAVED)
        if chosen in possible:
            return chosen
        if not possible:
            return None
        intro = self._kind_entry(self.intro_kind())
        return intro[arranger.BARS]

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
        """Return the sections a way of ending puts after the song's last tune, or None where the subgenre cannot end that way."""
        held = self._ending_kind()
        outro = self._outro_kind()
        chord = []
        if held is not None:
            chord = [{arranger.KIND: held}]
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
            slowing = self._stage(kind=outro, own={wizard_names.TEMPO_END_OF_PLACE: self._slowed_tempo()})
            return [slowing, *chord]
        if way == wizard_limits.STRIPS_DOWN and len(players) > 2:
            return [*self._stripping_stages(kind=outro, players=players), *chord]
        if way == wizard_limits.ONE_PLAYER_ALONE and len(players) > 1:
            return [self._stage(kind=outro, plays=players[:1]), *chord]
        if way == wizard_limits.REPEAT_AND_FADE:
            return [self._stage(kind=outro, own={wizard_names.SONG_PLAN_FADES: True})]
        return None

    def _slowed_tempo(self):
        """Return the tempo an ending that slows down slows to, never below the slowest tempo."""
        slowed = self._choices.get_tempo() * wizard_limits.SLOWED_TO[0] // wizard_limits.SLOWED_TO[1]
        return max(slowed, limits.MIN_TEMPO)

    def _stripping_stages(self, *, kind, players):
        """Return the stages of an ending that strips down: the kind played by one player fewer each time, down to the first alone."""
        stages = []
        for count in range(len(players) - 1, 0, -1):
            stages.append(self._stage(kind=kind, plays=players[:count]))
        return stages

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
        chosen = self._stages.get(wizard_limits.START_SAVED)
        if chosen in self.starts() and self._start_stages(chosen) == head:
            return chosen
        for way in self.starts():
            if self._start_stages(way) == head:
                return way
        return None

    def get_end(self):
        """Return the way the song ends, or None where its closing sections are a person's own."""
        entries = self.section_entries()
        tail = entries[len(entries) - self.tail_count():]
        chosen = self._stages.get(wizard_limits.END_SAVED)
        if chosen in self.ends() and self._end_stages(chosen) == tail:
            return chosen
        for way in self.ends():
            if self._end_stages(way) == tail:
                return way
        return None

    def _restaged(self, *, change, start=None, end=None):
        """Change how the song starts or ends: the sections between stay, and the stages are made again. A song that cannot then
        be made is as it was."""
        sections_before = copy.deepcopy(self._sections)
        stages_before = dict(self._stages)
        if start is None:
            start = self.get_start()
        if end is None:
            end = self.get_end()
        entries = [own_copy_of(entry) for entry in self.section_entries()]
        head = self.head_count()
        tail = self.tail_count()
        try:
            change()
            self._lay_out_stages(entries=entries, head=head, tail=tail, start=start, end=end)
            self._choices.clear_answers()
            self._choices.written_setlist(name=wizard_limits.PREVIEW_NAME, version=version_values.VERSION)
        except (ValueError, KeyError, IndexError, SongFileError) as problem:
            self._sections = sections_before
            self._stages = stages_before
            self._choices.clear_answers()
            raise ValueError(errors.ERR_WIZARD_START_UNMADE.format(problem=problem)) from None

    def _lay_out_stages(self, *, entries, head, tail, start, end):
        """Lay out the song's sections again: the stages of a way of starting and of ending, or the person's own where none is
        named, around the sections between, which stay as they are."""
        body = entries[head:len(entries) - tail]
        opening = entries[:head]
        if start is not None:
            opening = self._start_stages(start)
        closing = entries[len(entries) - tail:]
        if end is not None:
            closing = self._end_stages(end)
        if opening is None:
            raise ValueError(errors.ERR_WIZARD_START_UNMADE.format(problem=start))
        if closing is None or not body:
            raise ValueError(errors.ERR_WIZARD_START_UNMADE.format(problem=end))
        opening_copies = [own_copy_of(entry) for entry in opening]
        closing_copies = [own_copy_of(entry) for entry in closing]
        self._sections = [*opening_copies, *body, *closing_copies]
        if start is not None:
            self._stages[wizard_limits.START_SAVED] = start
        if end is not None:
            self._stages[wizard_limits.END_SAVED] = end

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
        """Return the questions a form is made from, in order, each its name, the answers offered and the usual answer: none
        where the subgenre has no verse and chorus to make a form of."""
        kinds = self.section_kinds()
        if wizard_limits.CHORUS_KIND not in kinds or wizard_limits.VERSE_KIND not in kinds:
            return []
        questions = [(wizard_limits.VERSES_FIRST, wizard_limits.COUNTS_ONE_OR_TWO, wizard_limits.ONE)]
        if wizard_limits.PRE_CHORUS in kinds:
            questions.append((wizard_limits.PRE_CHORUSES, wizard_limits.PRE_CHORUS_ANSWERS, wizard_limits.NO))
        if wizard_limits.BRIDGE in kinds:
            questions.append((wizard_limits.BRIDGE, wizard_limits.YES_OR_NO, wizard_limits.YES))
        if wizard_limits.SOLO in kinds:
            questions.append((wizard_limits.SOLOS, wizard_limits.SOLO_COUNTS, wizard_limits.ONE))
        if wizard_limits.DRUM_SOLO_KIND in kinds:
            questions.append((wizard_limits.DRUM_SOLO_KIND, wizard_limits.YES_OR_NO, wizard_limits.NO))
        questions.append((wizard_limits.LAST_CHORUSES, wizard_limits.COUNTS_ONE_OR_TWO, wizard_limits.TWO))
        return questions

    def form_of_answers(self, answers):
        """Return the kinds of section, in order, of the form some answers ask for: a question left out takes its usual answer."""
        given = self._answers_given(answers)
        kinds = self.section_kinds()
        before = given.get(wizard_limits.PRE_CHORUSES, wizard_limits.NO)
        solos = wizard_limits.SOLO_COUNTS.index(given.get(wizard_limits.SOLOS, wizard_limits.NONE_OF))
        form = []
        if wizard_limits.INTRO in kinds:
            form.append(wizard_limits.INTRO)
        form.extend([wizard_limits.VERSE_KIND] * wizard_limits.COUNTS_ONE_OR_TWO.index(given[wizard_limits.VERSES_FIRST]))
        form.append(wizard_limits.VERSE_KIND)
        form.extend(_chorus(count=1, before=before))
        form.append(wizard_limits.VERSE_KIND)
        form.extend(_chorus(count=2, before=before))
        # The middle of the song: a first solo, the bridge, the drummer alone, and the solo that leads back to the last choruses.
        if solos == 2:
            form.append(wizard_limits.SOLO)
        if given.get(wizard_limits.BRIDGE) == wizard_limits.YES:
            form.append(wizard_limits.BRIDGE)
        if given.get(wizard_limits.DRUM_SOLO_KIND) == wizard_limits.YES:
            form.append(wizard_limits.DRUM_SOLO_KIND)
        if solos:
            form.append(wizard_limits.SOLO)
        form.extend(_chorus(count=3, before=before))
        form.extend([wizard_limits.CHORUS_KIND] * wizard_limits.COUNTS_ONE_OR_TWO.index(given[wizard_limits.LAST_CHORUSES]))
        if wizard_limits.ENDING in kinds:
            form.append(wizard_limits.ENDING)
        return form

    def _answers_given(self, answers):
        """Return every question's answer, a question left out taking its usual answer, refusing an answer not offered and an
        answer to a question not asked."""
        asked = {}
        for name, offered, usual in self.form_questions():
            asked[name] = (offered, usual)
        if not asked:
            raise ValueError(errors.ERR_WIZARD_NO_FORM_QUESTIONS)
        given = {}
        for name, (offered, usual) in asked.items():
            answer = answers.get(name, usual)
            if answer not in offered:
                raise ValueError(errors.ERR_WIZARD_FORM_ANSWER.format(name=name, value=answer))
            given[name] = answer
        for name in answers:
            if name not in asked:
                raise ValueError(errors.ERR_WIZARD_FORM_ANSWER.format(name=name, value=answers[name]))
        return given

    def set_form_from_answers(self, answers):
        """Make the form some answers ask for the song's own, in place of its sections, or leave the form as it was where the answers are refused."""
        kinds = self.form_of_answers(answers)
        sections = [{arranger.KIND: kind} for kind in kinds]
        self.set_own_sections(sections=sections)
        self._choices.clear_answers()

    def form_seconds(self, *, form=None):
        """Return how long the song lasts at the tempo chosen, in seconds; or how long a suggested form would, when one is named."""
        bars = 0
        if form is None:
            for place in range(len(self.section_entries())):
                section = self._choices.section(place)
                bars += section.bars()
        else:
            for kind in self._kinds_of_form(form):
                bars += self._usual_bars(kind)
        whole_notes = bars * bar_length(self._choices.meter())
        return float(whole_notes * wizard_limits.QUARTERS_IN_WHOLE * wizard_limits.SECONDS_IN_MINUTE / self._choices.get_tempo())

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
        """Take how a song starts and ends as a song saved it: the sections are the song's already, so only what was chosen is
        kept, where it is a name or a number."""
        kept = {}
        for field, value in stages.items():
            named = isinstance(value, (str, int)) and not isinstance(value, bool)
            if field in STAGE_FIELDS and named:
                kept[field] = value
        self._stages = kept

    def counted(self):
        """Return how the song starts and ends as chosen, each under a name of its own, so that two songs can be compared setting by setting."""
        counted = {}
        add_counted(counted, kind=wizard_limits.STAGES_SAVED, held=self._stages)
        return counted

    def own_chords_count(self):
        """Return how many sections were given chords of their own."""
        count = 0
        for entry in self.section_entries():
            own = entry.get(wizard_limits.OWN_OF_SECTION, {})
            if own.get(wizard_names.ARRANGER_CHORDS):
                count += 1
        return count
