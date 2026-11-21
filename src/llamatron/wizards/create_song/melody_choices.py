# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The choices of a song's melodies: the style the tune is written in, its gauges and habits, the settings of its engine, and
what each kind of section's melody is chosen to do, a part of the song wizard's choices reached as choices.melodies()."""

from llamatron.model.file.song_file_error import SongFileError
from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, hook_writing, melody as melody_writer, notation as tune_notation, wizard_limits, wizard_names
from llamatron.wizards.create_song.arranger import arranged
from llamatron.wizards.create_song.choices_part import ChoicesPart, set_each_kept
from llamatron.wizards.create_song.riffs import flattened_in



def _choices_module():
    """Return the module of the wizard's choices, imported as it is first needed: it holds this part, and its functions that
    find whether a melody style works make a song from choices of their own."""
    from llamatron.wizards.create_song import wizard_choices
    return wizard_choices

class MelodyChoices(ChoicesPart):
    """What was chosen of the song's melodies, held by this part, asking the choices it belongs to for what every part shares."""

    __slots__ = ('_melody', '_gauges', '_melody_settings')

    def __init__(self, *, choices):
        super().__init__(choices=choices)
        self._melody = None
        self._gauges = {}
        self._melody_settings = {}

    def get_style(self):
        """Return the melody's style as chosen, or None for the genre's."""
        return self._melody

    def get_gauges(self):
        return self._gauges

    def get_settings(self):
        return self._melody_settings

    def forget_style(self):
        """Let the melody's style go back to the genre's, as another genre or subgenre is chosen."""
        self._melody = None

    def read_style(self, *, data):
        """Take the melody's style a song kept, leaving it out where it no longer fits."""
        set_each_kept([(self._set_kept_melody, [dict(style=data[wizard_limits.MELODY_STYLE])] if data.get(wizard_limits.MELODY_STYLE) else [])])

    def read_gauges(self, *, data):
        """Take the melody's gauges a song kept, leaving out any that no longer fits."""
        set_each_kept([(self.set_melody_gauge, [dict(name=name, position=position) for name, position in (data.get(wizard_limits.GAUGES_KEPT) or {}).items()])])

    def read_settings(self, *, data):
        """Take the melody's settings a song kept, leaving out any that no longer fits."""
        set_each_kept([(self._set_kept_melody_setting, [dict(name=name, value=value) for name, value in (data.get(wizard_limits.MELODY_SETTINGS_KEPT) or {}).items()])])

    def forget_gauges_and_settings(self):
        """Let go of the gauges and settings chosen, as the band is forgotten."""
        self._gauges = {}
        self._melody_settings = {}

    def melody_gauges(self):
        """Return the names of the smart melody style's gauges while the song's tunes are sketched by it or by the hooks style, and none otherwise."""
        return list(melody_writer.DEFAULT_GAUGES) if self._melody in wizard_limits.GAUGED_STYLES else []

    def get_melody_gauge(self, name):
        """Return where a gauge stands, from LOWEST_GAUGE to HIGHEST_GAUGE: where it was moved to, else where the genre sets it."""
        if name in self._gauges:
            return self._gauges[name]
        habits = self._choices.style()[arranger.MELODY]
        habits = habits if melody_writer.GRID in habits else habits[self._choices.meter()]
        return habits.get(melody_writer.SMART, {}).get(name, melody_writer.DEFAULT_GAUGES[name])

    def set_melody_gauge(self, *, name, position):
        if name not in melody_writer.DEFAULT_GAUGES or isinstance(position, bool) or not isinstance(position, int) or not melody_writer.LOWEST_GAUGE <= position <= melody_writer.HIGHEST_GAUGE:
            raise ValueError(errors.ERR_WIZARD_GAUGE.format(name=name, low=melody_writer.LOWEST_GAUGE, high=melody_writer.HIGHEST_GAUGE, value=position))
        self._gauges[name] = position

    def melody_habits(self):
        """Return the genre's melody habits for the song's meter."""
        habits = self._choices.style()[arranger.MELODY]
        return habits if melody_writer.GRID in habits else habits[self._choices.meter()]

    def melody_settings(self):
        """Return the names of the settings the song's melody style has of its own, the usual style's while none is chosen."""
        return list(wizard_limits.MELODY_SETTINGS_OF[self._melody]) if self._choices.is_ready() else []

    def melody_setting_range(self, name):
        """Return the lowest and highest a melody setting that is a number may be."""
        return wizard_limits.MELODY_NUMBERS[name]

    def melody_setting_is_switch(self, name):
        return name in wizard_limits.MELODY_SWITCHES

    def get_melody_setting(self, name):
        """Return a melody setting: what it was set to, else what the genre's habits say, else what the style does unasked."""
        if name in self._melody_settings:
            return self._melody_settings[name]
        habits = self.melody_habits()
        if name in wizard_limits.MELODY_SWITCHES:
            return bool(habits.get(name, wizard_limits.MELODY_SWITCHES[name]))
        return {**melody_writer.DEFAULT_EVOLVE, **habits.get(melody_writer.EVOLVE, {})}[name]

    def set_melody_setting(self, *, name, value):
        """Set a setting of the song's melody style, refusing one the style does not have."""
        if name not in self.melody_settings():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY_SETTING.format(value=name))
        self._set_kept_melody_setting(name=name, value=value)

    def _set_kept_melody_setting(self, *, name, value):
        if name in wizard_limits.MELODY_SWITCHES:
            if not isinstance(value, bool):
                raise ValueError(errors.ERR_WIZARD_MELODY_SWITCH.format(name=name, value=value))
        elif name in wizard_limits.MELODY_NUMBERS:
            low, high = wizard_limits.MELODY_NUMBERS[name]
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(errors.ERR_WIZARD_MELODY_NUMBER.format(name=name, low=low, high=high, value=value))
        else:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY_SETTING.format(value=name))
        self._melody_settings[name] = value

    def song_melody(self):
        """Return what the song says of its melody over the genre's habits: the smart style's gauges where one was moved, and
        the settings set of the style in use; a setting of another style is kept and says nothing."""
        said = {wizard_names.HOOK_WRITING: {hook_writing.BEHAVIOR: self._choices.get_hook().get_hook_behavior(), hook_writing.GAUGES: {name: self._choices.get_hook().get_hook_gauge(name) for name in hook_writing.HOOK_GAUGES}},
                wizard_names.BODY_WRITING: {hook_writing.GAUGES: {name: self._choices.get_hook().get_body_gauge(name) for name in hook_writing.BODY_GAUGES}}}
        if self._melody in wizard_limits.GAUGED_STYLES and self._gauges:
            said[melody_writer.SMART] = {**{name: self.get_melody_gauge(name) for name in melody_writer.DEFAULT_GAUGES}, **self._gauges}
        own = {name: value for name, value in self._melody_settings.items() if name in wizard_limits.MELODY_SETTINGS_OF[self._melody]}
        evolve = {name: value for name, value in own.items() if name in wizard_limits.EVOLVE_SETTINGS}
        if evolve:
            said[melody_writer.EVOLVE] = {**melody_writer.DEFAULT_EVOLVE, **self.melody_habits().get(melody_writer.EVOLVE, {}), **evolve}
        said.update({name: value for name, value in own.items() if name not in wizard_limits.EVOLVE_SETTINGS})
        return said

    def melody_styles(self):
        """Return the melody styles the subgenre's tunes can be sketched by, leaving out any that makes no song of it."""
        if not self._choices.is_ready():
            return []
        return [style for style in wizard_limits.MELODY_STYLES if _choices_module().melody_works(genre=self._choices.get_genre(), subgenre=self._choices.get_subgenre(), variant=self._choices.get_variant(), style=style)
                and not _choices_module().melody_is_usual(genre=self._choices.get_genre(), subgenre=self._choices.get_subgenre(), variant=self._choices.get_variant(), style=style)]

    def genre_melody(self):
        """Return the melody style the genre's own tunes are sketched by, which a song takes while none is chosen."""
        return self.melody_habits().get(melody_writer.ENGINE, melody_writer.STEP_WALK)

    def melody_engine(self):
        """Return the melody style the song's melodies are written by: the one the character chosen writes by, else one chosen by
        name, else the genre's own."""
        return wizard_limits.CHARACTER_ENGINES.get(self.get_melody_character()) or self._melody or self.genre_melody()

    def get_melody(self):
        """Return the melody style chosen, or None while each player's tunes are sketched as the genre says."""
        return self._melody

    def set_melody(self, style):
        if style is not None and style not in self.melody_styles():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY.format(value=style))
        self._melody = style

    def _set_kept_melody(self, *, style):
        self.set_melody(style)

    def melody_fields(self):
        """Return the fields of the whole song's melodies that are heard in the subgenre, in the order shown."""
        if not self._choices.is_ready() or not self._choices.get_tunes().tune_kinds():
            return []
        return [field for field in wizard_limits.MELODY_WAYS if len(self.melody_ways_offered(field)) > 1]

    def melody_ways_offered(self, field):
        """Return the values of a field of the whole song's melodies that are heard in the song as it stands: the genre's own,
        each other that makes another song, and the one chosen."""
        heard = self._melody_values_heard(field=field)
        return [value for value in wizard_limits.MELODY_WAYS[field] if value == wizard_limits.USUAL_MELODY_WAYS[field] or value in heard or value == self.get_melody_way(field)]

    def _melody_values_heard(self, *, field, kind=None):
        """The values of a melody field, of the song or of a kind of section, that make another song than the field left
        unchosen does, found by arranging the song each way, once, until a choice changes."""
        return self._choices.offered(key=(wizard_limits.MELODY_HEARD_ANSWER, field, kind), compute=lambda: self._found_melody_values_heard(field=field, kind=kind))

    def _found_melody_values_heard(self, *, field, kind):
        made = {}
        for value in (None, *(wizard_limits.SECTION_MELODY_WAYS if kind is not None else wizard_limits.MELODY_WAYS)[field]):
            trial = type(self._choices).from_data(self._choices.to_data())
            trial.melodies().keep_melody_chosen(field=field, value=value, kind=kind)
            try:
                made[value] = arranged(style=_choices_module().style_of(self._choices.get_genre()), song=trial.song_picks(self._choices.get_subgenre()))[arranger.PARTS]
            except (ValueError, IndexError, KeyError, SongFileError):
                made[value] = made.get(None)
        return [value for value in made if value is not None and made[value] != made[None]]

    def get_melody_way(self, field):
        """Return what the song says of its melodies in one field: the genre's own until another is chosen."""
        chosen = (self._choices.get_extra(wizard_limits.MELODY_CHOSEN) or {}).get(field)
        return chosen if chosen in wizard_limits.MELODY_WAYS[field] else wizard_limits.USUAL_MELODY_WAYS[field]

    def genre_melody_way(self, field):
        """Return the genre's own value of a field of the whole song's melodies."""
        return wizard_limits.USUAL_MELODY_WAYS[field]

    def set_melody_way(self, *, field, value):
        """Choose how busy the song's melodies are, how wide they range or how much they repeat; the genre's own is asked for by its name."""
        if field not in wizard_limits.MELODY_WAYS or value not in wizard_limits.MELODY_WAYS[field]:
            raise ValueError(errors.ERR_WIZARD_MELODY_WAY.format(field=field, value=value))
        self.keep_melody_chosen(field=field, value=None if value == wizard_limits.USUAL_MELODY_WAYS[field] else value)

    def keep_melody_chosen(self, *, field, value, kind=None):
        """Keep one thing chosen of the melodies, for the song or for a kind of section, or forget it with None."""
        chosen = dict(self._choices.get_extra(wizard_limits.MELODY_CHOSEN) or {})
        self._choices.set_extra(name=wizard_limits.MELODY_CHOSEN, value=chosen)
        held = chosen if kind is None else chosen.setdefault(melody_writer.BY_KIND, {}).setdefault(kind, {})
        held.pop(field, None)
        if value is not None:
            held[field] = value
        if kind is not None:
            chosen[melody_writer.BY_KIND] = {name: own for name, own in chosen[melody_writer.BY_KIND].items() if own}
            if not chosen[melody_writer.BY_KIND]:
                del chosen[melody_writer.BY_KIND]
        if not chosen:
            self._choices.set_extra(name=wizard_limits.MELODY_CHOSEN, value=None)
        self._choices.clear_answers()

    def melody_characters_offered(self):
        """Return the characters a melody of the subgenre can be given: each whose engine can write the subgenre's melodies, an
        engine with no gauges only where the genre does not write by it already."""
        if not self._choices.is_ready() or not self._choices.get_tunes().tune_kinds():
            return []
        given = dict(genre=self._choices.get_genre(), subgenre=self._choices.get_subgenre(), variant=self._choices.get_variant())
        offered = []
        for character in wizard_limits.CHARACTERS:
            engine = wizard_limits.CHARACTER_ENGINES[character]
            if _choices_module().melody_works(style=engine, **given) and (engine in wizard_limits.GAUGED_STYLES or not _choices_module().melody_is_usual(style=engine, **given)):
                offered.append(character)
        return offered

    def get_melody_character(self):
        """Return the character chosen for the song's melodies, or None while they are written as the genre writes them."""
        chosen = (self._choices.get_extra(wizard_limits.MELODY_CHOSEN) or {}).get(wizard_limits.MELODY_CHARACTER)
        return chosen if chosen in self.melody_characters_offered() else None

    def set_melody_character(self, character):
        """Choose the character of the song's melodies, or the genre's own with None."""
        if character is not None and character not in self.melody_characters_offered():
            raise ValueError(errors.ERR_WIZARD_MELODY_WAY.format(field=wizard_limits.MELODY_CHARACTER, value=character))
        self.keep_melody_chosen(field=wizard_limits.MELODY_CHARACTER, value=character)

    def section_melody_fields(self, kind):
        """Return the fields of one kind of section's melody that are heard in the subgenre: how high it sits and how busy it is."""
        if not self._choices.is_ready() or kind not in self._choices.get_tunes().tune_kinds() or kind not in self._choices.style()[arranger.SECTIONS]:
            return []
        return [field for field in wizard_limits.SECTION_MELODY_WAYS if self.section_melody_ways_offered(kind=kind, field=field)]

    def section_melody_ways_offered(self, *, kind, field):
        """Return the values of a field of a kind of section's own melody that are heard in the song as it stands: each that
        makes another song than the field left to the genre or the song, and the one chosen."""
        heard = self._melody_values_heard(field=field, kind=kind)
        return [value for value in wizard_limits.SECTION_MELODY_WAYS[field] if value in heard or value == self.get_section_melody(kind=kind, field=field)]

    def get_section_melody(self, *, kind, field):
        """Return what a kind of section says of its own melody in one field, or None where nothing was chosen."""
        chosen = (self._choices.get_extra(wizard_limits.MELODY_CHOSEN) or {}).get(melody_writer.BY_KIND, {}).get(kind, {}).get(field)
        return chosen if chosen in wizard_limits.SECTION_MELODY_WAYS[field] else None

    def set_section_melody(self, *, kind, field, value):
        """Choose how high a kind of section's melody sits or how busy it is, or leave it to the genre or the song with None."""
        if field not in wizard_limits.SECTION_MELODY_WAYS or (value is not None and value not in wizard_limits.SECTION_MELODY_WAYS[field]) or kind not in self._choices.get_tunes().tune_kinds():
            raise ValueError(errors.ERR_WIZARD_MELODY_WAY.format(field=field, value=(kind, value)))
        self.keep_melody_chosen(field=field, value=value, kind=kind)

    def melody_picks(self, picks):
        """What the arranger is handed of the melodies chosen, over the song's picks: what is asked of the plans' lines, the engine
        a character writes by, and the habits a range and a character change."""
        chosen = self._choices.get_extra(wizard_limits.MELODY_CHOSEN)
        if not chosen or not self._choices.is_ready():
            return {}
        said = {}
        asks = {}
        if chosen.get(melody_writer.REPEATS) in melody_writer.REPEATS_WAYS:
            asks[melody_writer.REPEATS] = chosen[melody_writer.REPEATS]
        if chosen.get(wizard_limits.MELODY_BUSY) in wizard_limits.BUSY_POSITIONS:
            asks[melody_writer.LINE_BUSY] = wizard_limits.BUSY_POSITIONS[chosen[wizard_limits.MELODY_BUSY]]
        by_kind = {}
        for kind, own in chosen.get(melody_writer.BY_KIND, {}).items():
            of_kind = {**({wizard_names.MELODY_HEIGHT: own[wizard_names.MELODY_HEIGHT]} if own.get(wizard_names.MELODY_HEIGHT) in melody_writer.HEIGHTS else {}), **({melody_writer.LINE_BUSY: wizard_limits.BUSY_POSITIONS[own[wizard_limits.MELODY_BUSY]]} if own.get(wizard_limits.MELODY_BUSY) in wizard_limits.BUSY_POSITIONS else {})}
            if of_kind:
                by_kind[kind] = of_kind
        if by_kind:
            asks[melody_writer.BY_KIND] = by_kind
        if asks:
            said[melody_writer.MELODY_ASKS] = asks
        habits = dict(picks.get(arranger.MELODY, {}))
        genre_habits = self.melody_habits()
        if chosen.get(wizard_limits.MELODY_RANGE) in wizard_limits.SPAN_CHANGES and melody_writer.SPAN in genre_habits:
            habits[melody_writer.SPAN] = max(wizard_limits.LEAST_SPAN, genre_habits[melody_writer.SPAN] + wizard_limits.SPAN_CHANGES[chosen[wizard_limits.MELODY_RANGE]])
        character = self.get_melody_character()
        if character is not None:
            said[arranger.MELODY_ENGINE] = wizard_limits.CHARACTER_ENGINES[character]
            if character in wizard_limits.CHARACTER_GAUGES:
                habits[melody_writer.SMART] = {**{name: self.get_melody_gauge(name) for name in melody_writer.DEFAULT_GAUGES}, **wizard_limits.CHARACTER_GAUGES[character]}
            if character == wizard_limits.BLUESY:
                flattened = flattened_in(self._choices.get_scale_type())
                habits[melody_writer.LADDER] = [{tune_notation.DEGREE: degree, **({tune_notation.ACCIDENTAL: tune_notation.FLAT} if degree in flattened else {})} for degree in wizard_limits.BLUES_DEGREES]
                habits[melody_writer.HOME] = {tune_notation.DEGREE: wizard_limits.BLUES_HOME}
        if habits:
            said[arranger.MELODY] = habits
        return said

    def carries_melody_in(self, *, kind, role):
        """Whether a player may be given the melody in a kind of section: a kind that has a melody, and a player who can carry one."""
        return kind in self._choices.get_tunes().tune_kinds() and role in self._choices.get_tunes().tune_players_offered()

    def melody_players(self):
        """Return the players who carry a melody somewhere in the song, by name: each kind of section's, and the soloist."""
        return {self._choices.get_tunes().tune_player_in(kind) for kind in self._choices.get_tunes().tune_kinds()} | {wizard_limits.SOLO}
