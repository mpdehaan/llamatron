# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The choices of a song's melodies: the style the tune is written in, its gauges and habits and the settings of its engine, a
part of the song wizard's choices reached as choices.melody()."""

from llamatron.user_strings import errors
from llamatron.wizards.create_song import arranger, melody as melody_writer, wizard_limits, wizard_names
from llamatron.wizards.create_song.choices_part import add_counted, ChoicesPart, chosen_only



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

    def restore(self, saved):
        """Restore the melody's style, gauges and settings a song kept, leaving out any that no longer fits."""
        style = saved.value(wizard_limits.MELODY_STYLE)
        if style:
            saved.apply(self._restore_style, style=style)
        gauges = saved.mapping(wizard_limits.GAUGES_SAVED)
        for name, position in gauges.items():
            saved.apply(self.set_style_gauge, name=name, position=position)
        settings = saved.mapping(wizard_limits.MELODY_SETTINGS_SAVED)
        for name, value in settings.items():
            saved.apply(self._restore_setting, name=name, value=value)

    def to_data(self):
        """Return what a song keeps of the melody, as plain data a song file saves: only what was chosen."""
        held = {
            wizard_limits.MELODY_STYLE: self._melody,
            wizard_limits.GAUGES_SAVED: dict(self._gauges) or None,
            wizard_limits.MELODY_SETTINGS_SAVED: dict(self._melody_settings) or None,
        }
        return chosen_only(held)

    def add_picks(self, picks):
        """Add the melody's picks to the song's: the style chosen, and what the song says of its melody."""
        if self._melody is not None:
            picks[arranger.MELODY_ENGINE] = self._melody
        picks[arranger.MELODY] = self._said()

    def forget_gauges_and_settings(self):
        """Let go of the gauges and settings chosen, as the band is forgotten."""
        self._gauges = {}
        self._melody_settings = {}

    def style_gauges(self):
        """Return the names of the smart melody style's gauges while the song's tunes are sketched by it or by the hooks style, and none otherwise."""
        return list(melody_writer.DEFAULT_GAUGES) if self._melody in wizard_limits.GAUGED_STYLES else []

    def get_style_gauge(self, name):
        """Return where a gauge stands, from LOWEST_GAUGE to HIGHEST_GAUGE: where it was moved to, else where the genre sets it."""
        if name in self._gauges:
            return self._gauges[name]
        habits = self._choices.style()[arranger.MELODY]
        habits = habits if melody_writer.GRID in habits else habits[self._choices.meter()]
        return habits.get(melody_writer.SMART, {}).get(name, melody_writer.DEFAULT_GAUGES[name])

    def set_style_gauge(self, *, name, position):
        if name not in melody_writer.DEFAULT_GAUGES or isinstance(position, bool) or not isinstance(position, int) or not melody_writer.LOWEST_GAUGE <= position <= melody_writer.HIGHEST_GAUGE:
            raise ValueError(errors.ERR_WIZARD_GAUGE.format(name=name, low=melody_writer.LOWEST_GAUGE, high=melody_writer.HIGHEST_GAUGE, value=position))
        self._gauges[name] = position

    def habits(self):
        """Return the genre's melody habits for the song's meter."""
        habits = self._choices.style()[arranger.MELODY]
        return habits if melody_writer.GRID in habits else habits[self._choices.meter()]

    def settings(self):
        """Return the names of the settings the song's melody style has of its own, the usual style's while none is chosen."""
        return list(wizard_limits.MELODY_SETTINGS_OF[self._melody]) if self._choices.is_ready() else []

    def setting_range(self, name):
        """Return the lowest and highest a melody setting that is a number may be."""
        return wizard_limits.MELODY_NUMBERS[name]

    def setting_is_switch(self, name):
        return name in wizard_limits.MELODY_SWITCHES

    def get_setting(self, name):
        """Return a melody setting: what it was set to, else what the genre's habits say, else what the style does unasked."""
        if name in self._melody_settings:
            return self._melody_settings[name]
        habits = self.habits()
        if name in wizard_limits.MELODY_SWITCHES:
            return bool(habits.get(name, wizard_limits.MELODY_SWITCHES[name]))
        return {**melody_writer.DEFAULT_EVOLVE, **habits.get(melody_writer.EVOLVE, {})}[name]

    def set_setting(self, *, name, value):
        """Set a setting of the song's melody style, refusing one the style does not have."""
        if name not in self.settings():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY_SETTING.format(value=name))
        self._restore_setting(name=name, value=value)

    def _restore_setting(self, *, name, value):
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

    def _said(self):
        """Return what the song says of its melody over the genre's habits: how the hook and the lines around it are written, the
        smart style's gauges where one was moved, and the settings set of the style in use; a setting of another style is kept
        and says nothing."""
        hook = self._choices.get_hook()
        said = {wizard_names.HOOK_WRITING: hook.writing_said(), wizard_names.BODY_WRITING: hook.body_writing_said()}
        if self._melody in wizard_limits.GAUGED_STYLES and self._gauges:
            said[melody_writer.SMART] = self._smart_gauges()
        evolve = {}
        for name, value in self._settings_of_style().items():
            if name in wizard_limits.EVOLVE_SETTINGS:
                evolve[name] = value
            else:
                said[name] = value
        if evolve:
            said[melody_writer.EVOLVE] = self._evolve_said(evolve)
        return said

    def _smart_gauges(self):
        """Return the place of every gauge of the smart style: where it was moved, or where it starts."""
        gauges = {name: self.get_style_gauge(name) for name in melody_writer.DEFAULT_GAUGES}
        gauges.update(self._gauges)
        return gauges

    def _settings_of_style(self):
        """Return the settings set of the style in use."""
        offered = wizard_limits.MELODY_SETTINGS_OF[self._melody]
        return {name: value for name, value in self._melody_settings.items() if name in offered}

    def _evolve_said(self, evolve):
        """Return how the melody evolves: the defaults, then the genre's habits, then the settings chosen."""
        habits = self.habits()
        said = dict(melody_writer.DEFAULT_EVOLVE)
        said.update(habits.get(melody_writer.EVOLVE, {}))
        said.update(evolve)
        return said

    def styles(self):
        """Return the melody styles the subgenre's tunes can be sketched by, leaving out any that makes no song of it and any
        that sketches them just as the genre does unasked."""
        if not self._choices.is_ready():
            return []
        choices_module = _choices_module()
        kind_of_song = dict(genre=self._choices.get_genre(), subgenre=self._choices.get_subgenre(), variant=self._choices.get_variant())
        styles = []
        for style in wizard_limits.MELODY_STYLES:
            if choices_module.melody_works(**kind_of_song, style=style) and not choices_module.melody_is_usual(**kind_of_song, style=style):
                styles.append(style)
        return styles

    def genre_style(self):
        """Return the melody style the genre's own tunes are sketched by, which a song takes while none is chosen."""
        return self.habits().get(melody_writer.ENGINE, melody_writer.STEP_WALK)

    def engine(self):
        """Return the melody style the song's melodies are written by: the one the character chosen writes by, else one chosen by
        name, else the genre's own."""
        ways = self._choices.melody_ways()
        return wizard_limits.CHARACTER_ENGINES.get(ways.get_character()) or self._melody or self.genre_style()

    def set_style(self, style):
        if style is not None and style not in self.styles():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY.format(value=style))
        self._melody = style

    def _restore_style(self, *, style):
        self.set_style(style)

    def carries_in(self, *, kind, role):
        """Whether a player may be given the melody in a kind of section: a kind that has a melody, and a player who can carry one."""
        return kind in self._choices.get_tunes().tune_kinds() and role in self._choices.get_tunes().tune_players_offered()

    def players(self):
        """Return the players who carry a melody somewhere in the song, by name: each kind of section's, and the soloist."""
        return {self._choices.get_tunes().tune_player_in(kind) for kind in self._choices.get_tunes().tune_kinds()} | {wizard_limits.SOLO}

    def counted(self):
        """Return every setting of the melody, each under a name of its own, so that two songs can be compared setting by setting."""
        counted = {(wizard_limits.GENRE_SETTING, wizard_limits.MELODY_STYLE): self._melody}
        add_counted(counted, kind=wizard_limits.GAUGES_SAVED, held=self._gauges)
        add_counted(counted, kind=wizard_limits.MELODY_SETTINGS_SAVED, held=self._melody_settings)
        return counted
