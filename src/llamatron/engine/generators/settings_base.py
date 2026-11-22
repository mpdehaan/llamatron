# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What every generator's settings share: the class each plugin's settings extend, which reads, checks and writes a
generator's settings and makes the generator that runs, and the Restart setting."""

from llamatron.caching.revised import notes_change
from llamatron.model.file import corrections
from llamatron.model.file.checks import listed, pass_over_unknown, reading, refuse_unknown
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.conditions import statements_setting
from llamatron.model.objects.llama_data import HoldsSettings, own_copy
from llamatron.model.objects.traits import BypassedWhen
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Restart
from llamatron.model.schema.setting import check_settings, Choice, Flag
from llamatron.user_strings import errors

# Every generator's Restart: when it starts over, every clip unless set.
RESTART_SETTING = Choice(name=file_format.GENERATOR_RESTART, choices=file_format.RESTARTS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE)
# Every generator's switch, first of its settings: on unless written off.
ENABLED_SETTING = Flag(name=file_format.GENERATOR_ENABLED, error=errors.ERR_GENERATOR_ENABLED_NOT_TRUE_OR_FALSE)
# Every generator keeps a table of statements about the registers, written last, which says when a clip's pass goes by it untouched.
BYPASS_STATEMENTS = statements_setting(file_format.BYPASS_WHEN)


class GeneratorSettings(BypassedWhen, HoldsSettings):
    """The settings of one named generator, kept as the file writes them until a chain uses them.

    Each subclass says which generator it makes, describes each setting it allows once
    (model/schema/setting.py), and says which are required and which the generator takes as
    something other than what the file writes.
    """

    __slots__ = ('_built_in', '_keeper')

    BYPASS_SETTING = file_format.BYPASS_WHEN
    GENERATOR = None
    SETTINGS = {}
    # What turns a setting as the file writes it into what the generator takes, for the settings where the two differ.
    TAKEN_AS = {}
    # Whether its generators may add to the registers as they play, which a plugin whose settings answer adds_to_registers() says.
    MAY_ADD_TO_REGISTERS = False

    def __init_subclass__(cls, **named):
        """Give every kind of settings its switch, as its first setting, and the table of statements that bypasses its generator,
        as its last."""
        super().__init_subclass__(**named)
        shared = (file_format.BYPASS_WHEN, file_format.GENERATOR_ENABLED)
        settings = {name: description for name, description in cls.SETTINGS.items() if name not in shared}
        cls.SETTINGS = {file_format.GENERATOR_ENABLED: ENABLED_SETTING, **settings, file_format.BYPASS_WHEN: BYPASS_STATEMENTS}

    def adds_to_registers(self):
        """Return whether its generator adds to the registers as it plays: no, unless a plugin's settings say otherwise."""
        return False

    def __init__(self, settings, *, built_in=False, keeper=None):
        """built_in says whether these are the settings of a clip's or a track's built-in generator, which is switched off until
        switched on, where a generator of the set's list is on until switched off. keeper, given with a built-in's, is handed
        the settings after every change, so that the clip or track holding them keeps them and says it changed."""
        # Kept as given, as a copy, so that the object shares nothing with the data it was read from. Reading a file checks the data first.
        self.note_change()
        self._settings = own_copy(settings) or {}
        self._built_in = built_in
        self._keeper = keeper

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            if data is None:
                data = {}
            if not isinstance(data, dict):
                raise InvalidValue(errors.ERR_NOT_SETTINGS.format(value=data))
            cls.pass_over_unknown_names(data)
            cls.check_data(data)
        return cls(data)

    @classmethod
    def pass_over_unknown_names(cls, data):
        """Take out of a file's data every name this generator doesn't have, so that a file from another version opens."""
        pass_over_unknown(data=data, allowed=cls.SETTINGS)

    @classmethod
    def handed_over(cls, *, data, where):
        """Return the settings the program itself hands over, such as the song wizard's, refusing a name this generator doesn't
        have, which from_data passes over as a file from another version may hold one."""
        with reading(where):
            cls.check_data(data)
        return cls(data)

    @classmethod
    def check_data(cls, data):
        """Raise InvalidValue unless data holds only settings this generator has, each one right. Reading a
        file passes over the names it doesn't know first (from_data), so a name refused here is one the program itself handed over."""
        if not isinstance(data, dict):
            raise InvalidValue(errors.ERR_NOT_SETTINGS.format(value=data))
        refuse_unknown(data=data, allowed=cls.SETTINGS)
        check_settings(settings=cls.SETTINGS, data=data)

    def to_data(self):
        return own_copy(self._settings)

    def get_written(self, name):
        """Return a setting as the file writes it, or None if the file leaves it out. Only what is written is held, in the order written."""
        if not isinstance(self._settings, dict):
            return None
        return self._settings.get(name)

    def copy(self):
        return type(self)(self.to_data(), built_in=self._built_in)

    def set_setting(self, *, name, value):
        """Set one setting by its file name, checking it as reading a file does, or None to leave it out."""
        self.set_written(name=name, value=value)

    @notes_change
    def set_written(self, *, name, value, song=None):
        """Store one setting by its file name, checking it as reading a file does, or None to leave it out.

        The settings are a table, one description each, so one generic setter checks them all
        the same way. No setting of a generator names anything of a song, so song is not read.
        """
        if not isinstance(self._settings, dict):
            raise InvalidValue(errors.ERR_NOT_SETTINGS.format(value=self._settings))
        if name not in self.SETTINGS:
            raise InvalidValue(errors.ERR_GENERATOR_NO_SUCH_SETTING.format(name=name, names=listed(sorted(self.SETTINGS))))
        if value is None:
            self._settings.pop(name, None)
        else:
            self.SETTINGS[name].check(value)
            self._settings[name] = own_copy(value)
        if self._keeper is not None:
            self._keeper(self)

    def limits_of(self, name):
        """Return the lowest and highest a whole number of these settings may be, by the setting's file name: its description's,
        unless a kind's settings narrow them by another of its settings."""
        described = self.SETTINGS[name]
        return described.get_lowest(), described.get_highest()

    def is_enabled(self):
        """Return whether the generator runs: a generator of the set's list unless switched off, a built-in one only once
        switched on."""
        written = self.get_written(file_format.GENERATOR_ENABLED)
        if written is None:
            return not self._built_in
        return written

    def is_built_in(self):
        """Return whether these are a clip's or a track's built-in generator's settings."""
        return self._built_in

    def get_restart(self):
        """Return when the generator starts over, every clip unless set."""
        return self.get_written(file_format.GENERATOR_RESTART) or Restart.EVERY_CLIP

    def make_generator(self, *, where, default_seed, default_step=None, bar=None, continuation=None, tempo=None):
        """Return the generator these settings describe, or raise SongFileError if they're wrong.

        where names the chain using it. default_seed is used by a generator that chooses at
        random, when its settings don't give a seed, default_step, the step size of the
        pattern the clip plays, by one whose step is left as "(pattern)", and bar, the length of
        the song's bar, by one whose time is written in bars, and tempo, the scene's, by one
        that works in milliseconds.
        """
        with reading(where):
            self.check_data(self._settings)
            values = self._with_defaults(values=self._taken_values(), default_seed=default_seed, default_step=default_step, bar=bar)
            values = self._with_tempo(values=values, tempo=tempo)
            # Restart is the Realizer's to read; the generator is handed where it carries on from instead.
            values.pop(file_format.GENERATOR_RESTART, None)
            return self.GENERATOR(**values, continuation=continuation)

    def _taken_values(self):
        """Return the settings as the generator takes them: a length as a number, a choice as what its name means, and the rest as written."""
        taken = {}
        for name, value in self._settings.items():
            if name in (file_format.BYPASS_WHEN, file_format.GENERATOR_ENABLED):
                continue
            if name in self.TAKEN_AS:
                value = self.TAKEN_AS[name](value)
            taken[name] = value
        return taken

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        """Return the generator's values, with a seed and a step added where it needs them. Most don't."""
        return values

    def _with_tempo(self, *, values, tempo):
        """Return the generator's values, with the scene's tempo added where it needs it. Most don't."""
        return values
