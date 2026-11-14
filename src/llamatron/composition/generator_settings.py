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

"""The settings of a named arp or AutoRatchet, which chains use by name.

A generator's settings are checked when the file is read, like every other part of a set, so
that a problem is reported with the name of the generator, whether or not a chain uses it. They
are checked again when a chain makes the generator, since settings can be built without a file.
"""

from llamatron.composition.checks import Bars, check_keys, in_whole_notes, is_true_or_false, number, is_whole_number, is_whole_number_from, listed, reading, time_length
from llamatron.composition.file_format import (
    FIXED_CHORDS, GENERATOR_RESTART, RESTARTS, TENSIONS, Accidental, EuclidPart, NamedRhythm, Restart, StrumDirection, StrumPart, DRIFT_DIRECTIONS, DRIFT_VERSIONS, REGISTER_NAMES, SHAPE_PARTS, SHAPE_THENS, DriftValue, GeneratorKind, RegisterName, Shape, ShapePart, shape_setting, Section,
)
from llamatron.composition.named_scale import scale_type_names
from llamatron.composition.strum import strum_part_settings, strum_values
from llamatron.composition.shapes import NO_ACCENT, UNCHANGED, ShapeValues, shape_part_settings, shape_values
from llamatron.music.note import ROOT_NAMES
from llamatron.composition.limits import MAX_RUSH_OR_DRAG, MAX_SHORTEN, MAX_STEP_ROW, MIN_SHORTEN, MIN_STEP_ROW, DEFAULT_EUCLID_STEPS, MAX_ACCENT, MIN_ACCENT, MAX_PROGRESSION_CHORDS, MIN_PROGRESSION_CHORDS, MAX_PROGRESSION_DEGREE, MAX_PROGRESSION_INVERSION, MIN_PROGRESSION_DEGREE, MAX_DRIFT_DEGREE, MAX_PROBABILITY, MAX_REGISTER_VALUE, MIN_PROBABILITY, MIN_REGISTER_VALUE
from llamatron.composition.llama_data import LlamaData, or_default, own_copy
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.corrections import LEFT_OUT, NO_NEAREST_VALUE
from llamatron.composition.setting import Checked, Choice, Flag, Text, WholeNumber, check_settings, described
from llamatron.music.note import MAX_OCTAVE, MIN_OCTAVE
from llamatron.support.rational import Rational
from llamatron.generators.progression import Progression
from llamatron.generators.voice_leading import VoiceLeading
from llamatron.generators.euclid import EuclidMask
from llamatron.generators.glide import Glide
from llamatron.generators.shorten import Shorten
from llamatron.composition.euclid import NAMED_RHYTHMS, euclid_part_settings, euclid_values
from llamatron.generators.arp import MAX_OCTAVE_RANGE, MAX_OFFSET, MAX_OFFSETS, MIN_OFFSETS, Arp, ChordOrder, OctaveJump, _check_offsets
from llamatron.generators.auto_ratchet import AutoRatchet
from llamatron.strings.errors import (
    ERR_NOT_TEXT,
    ERR_BAD_SHAPE_PERCENT,
    ERR_BAD_PROGRESSION_CHORDS,
    ERR_BAD_PROGRESSION_ROW, ERR_BAD_PROGRESSION_TENSIONS,
    ERR_VOICE_LEADING_RANGE,
    ERR_ROOT_IN_BASS_NOT_TRUE_OR_FALSE,
    ERR_EUCLID_TOO_MANY_HITS,
    ERR_BAD_STEP_ROW,
    ERR_BAD_GLIDE_AMOUNT,
    ERR_DRIFT_BAD_ROOT, ERR_DRIFT_BAD_SCALE,
    ERR_GENERATOR_BAD_ADD, ERR_GENERATOR_BAD_STEP_ADDS,
    ERR_GENERATOR_BAD_OCTAVE_RANGE, ERR_GENERATOR_BAD_OFFSETS, ERR_GENERATOR_NO_SUCH_SETTING, ERR_GENERATOR_NOT_A_LIST,
    ERR_GENERATOR_NOT_INTEGER, ERR_NEEDS_SETTING, ERR_NO_OFFSETS, ERR_NO_SUCH_OFFSET, ERR_NOT_A_CHOICE, ERR_NOT_SETTINGS,
)
from llamatron.support.revised import notes_change

MIN_OCTAVE_RANGE = 1
# An offset that leaves the note where it is, which a new step of offsets starts with.
NO_OFFSET = 0
# What a new AutoRatchet does: splits each note in two.
NEW_AUTO_RATCHET_COUNTS = [2]


# Every generator's Restart: when it starts over, every clip unless set (the user's design of 2026-11-11).
RESTART_SETTING = Choice(name=GENERATOR_RESTART, choices=RESTARTS, default=LEFT_OUT, error=ERR_NOT_A_CHOICE)


class ArpSetting:
    """An arpeggiator's settings, as a file names them."""

    RESTART = GENERATOR_RESTART

    STEP = 'step'
    ORDER = 'order'
    SEED = 'seed'
    OCTAVE_RANGE = 'octave_range'
    OCTAVE_JUMP = 'octave_jump'
    OFFSETS = 'offsets'
    # How much each note the arp plays adds to each register, and what each step of the offsets adds, the user's design of 2026-11-11.
    AX_ADD = 'ax_add'
    BX_ADD = 'bx_add'
    CX_ADD = 'cx_add'
    DX_ADD = 'dx_add'
    AX_STEP_ADDS = 'ax_step_adds'
    BX_STEP_ADDS = 'bx_step_adds'
    CX_STEP_ADDS = 'cx_step_adds'
    DX_STEP_ADDS = 'dx_step_adds'


# Each register's per-note add and its row of adds under the offsets, by register.
ARP_NOTE_ADDS = {RegisterName.AX: ArpSetting.AX_ADD, RegisterName.BX: ArpSetting.BX_ADD, RegisterName.CX: ArpSetting.CX_ADD, RegisterName.DX: ArpSetting.DX_ADD}
ARP_STEP_ADDS = {
    RegisterName.AX: ArpSetting.AX_STEP_ADDS, RegisterName.BX: ArpSetting.BX_STEP_ADDS, RegisterName.CX: ArpSetting.CX_STEP_ADDS, RegisterName.DX: ArpSetting.DX_STEP_ADDS,
}


class DriftSetting:
    """A drift's own settings, as a file names them. Each version's settings are named in VERSIONED, with the version's letter in front."""

    RESTART = GENERATOR_RESTART

    EVERY = 'every'
    STEPS_TO_B = 'steps_to_b'
    DIRECTION = 'direction'
    SEED = 'seed'


# Each register's add at a drift's trigger, by register.
DRIFT_ADDS = {RegisterName.AX: DriftValue.AX_ADD, RegisterName.BX: DriftValue.BX_ADD, RegisterName.CX: DriftValue.CX_ADD, RegisterName.DX: DriftValue.DX_ADD}
# A version's values, in the order the editor lists them: (name, lowest, highest) for each number, and the two choices.
DRIFT_NUMBERS = [
    *[(name, MIN_REGISTER_VALUE, MAX_REGISTER_VALUE) for name in DRIFT_ADDS.values()],
    (DriftValue.VELOCITY, -MAX_REGISTER_VALUE, MAX_REGISTER_VALUE),
    (DriftValue.PROBABILITY, -MAX_PROBABILITY, MAX_PROBABILITY),
    (DriftValue.DEGREE, -MAX_DRIFT_DEGREE, MAX_DRIFT_DEGREE),
    (DriftValue.DEGREE_RANDOM, MIN_PROBABILITY, MAX_DRIFT_DEGREE),
    (DriftValue.SCALE_PROBABILITY, MIN_PROBABILITY, MAX_PROBABILITY),
    (DriftValue.ROOT_PROBABILITY, MIN_PROBABILITY, MAX_PROBABILITY),
]
DRIFT_CHOICES = [DriftValue.SCALE, DriftValue.ROOT]
DRIFT_VALUES = [
    *DRIFT_ADDS.values(), DriftValue.VELOCITY, DriftValue.PROBABILITY, DriftValue.DEGREE, DriftValue.DEGREE_RANDOM,
    DriftValue.SCALE, DriftValue.SCALE_PROBABILITY, DriftValue.ROOT, DriftValue.ROOT_PROBABILITY,
]
VERSIONED = '{version}_{value}'
# How many triggers a drift takes from A to B, unless it says.
DEFAULT_STEPS_TO_B = 16
MIN_STEPS_TO_B = 1
MAX_STEPS_TO_B = 999


def versioned(*, version, value):
    """Return the file's name for one version's value, like a_velocity."""
    return VERSIONED.format(version=version, value=value)


def _check_scale_name(value):
    if not isinstance(value, str) or not value:
        raise InvalidValue(ERR_DRIFT_BAD_SCALE.format(value=value))


def _check_root(value):
    if value not in ROOT_NAMES:
        raise InvalidValue(ERR_DRIFT_BAD_ROOT.format(roots=listed(ROOT_NAMES), value=value))


class AutoRatchetSetting:
    """An AutoRatchet's settings, as a file names them."""

    RESTART = GENERATOR_RESTART

    COUNTS = 'counts'


# The choices for settings that pick one of several names, by the name a file uses.


def written_name(member):
    """Return a chord order or octave jump as a file writes it, like 'up' or 'after_each_note'."""
    return member.name.lower()


ORDERS = {written_name(member): member for member in ChordOrder}
OCTAVE_JUMPS = {written_name(member): member for member in OctaveJump}


def _order(name):
    """Return the chord order a file's name for one means."""
    return ORDERS[name]


def _octave_jump(name):
    """Return the octave jump a file's name for one means."""
    return OCTAVE_JUMPS[name]


def _check_arp_offsets(value):
    """Refuse offsets the arp itself would refuse."""
    try:
        _check_offsets(value)
    except ValueError as error:
        raise InvalidValue(ERR_GENERATOR_BAD_OFFSETS.format(problem=error)) from None


def _nearest_offsets(offsets):
    """Return offsets with each one further than the arp allows at the furthest it does, or NO_NEAREST_VALUE unless they're the right number of whole numbers and silent steps."""
    if not isinstance(offsets, list) or not MIN_OFFSETS <= len(offsets) <= MAX_OFFSETS:
        return NO_NEAREST_VALUE
    if not all(offset is None or is_whole_number(offset) for offset in offsets):
        return NO_NEAREST_VALUE
    return [offset if offset is None else min(max(offset, -MAX_OFFSET), MAX_OFFSET) for offset in offsets]


def _is_step_add(value):
    return value is None or is_whole_number_from(value=value, lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE)


def _check_step_adds(value):
    """Refuse a row of adds under the offsets unless it is a list of 1 to 16 adds or blanks."""
    if not isinstance(value, list) or not MIN_OFFSETS <= len(value) <= MAX_OFFSETS or not all(_is_step_add(add) for add in value):
        raise InvalidValue(ERR_GENERATOR_BAD_STEP_ADDS.format(most=MAX_OFFSETS, lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE, value=value))


def _check_counts(value):
    if not isinstance(value, list):
        raise InvalidValue(ERR_GENERATOR_NOT_A_LIST.format(name=AutoRatchetSetting.COUNTS, value=value))


class GeneratorSettings(LlamaData):
    """The settings of one named generator, kept as the file writes them until a chain uses them.

    Each subclass says which generator it makes, describes each setting it allows once
    (composition/setting.py), and says which are required and which the generator takes as
    something other than what the file writes.
    """

    __slots__ = ('_settings',)

    GENERATOR = None
    SETTINGS = {}
    REQUIRED = []
    # What turns a setting as the file writes it into what the generator takes, for the settings where the two differ.
    TAKEN_AS = {}

    def __init__(self, settings):
        # Kept as given, as a copy, so that the object shares nothing with the data it was read from. Reading a file checks the data first.
        self.note_change()
        self._settings = own_copy(settings) or {}

    @classmethod
    def from_data(cls, *, data, where, song=None):
        with reading(where):
            cls.check_data({} if data is None else data)
        return cls(data)

    @classmethod
    def check_data(cls, data):
        """Raise InvalidValue unless data holds only settings this generator has, each one right, and every one it needs."""
        if not isinstance(data, dict):
            raise InvalidValue(ERR_NOT_SETTINGS.format(value=data))
        check_keys(data=data, allowed=set(cls.SETTINGS))
        check_settings(settings=cls.SETTINGS, data=data)
        for name in cls.REQUIRED:
            if name not in data:
                raise InvalidValue(ERR_NEEDS_SETTING.format(name=name))

    def to_data(self):
        return own_copy(self._settings)

    def _written(self, name):
        """Return a setting as the file writes it, or None if the file leaves it out."""
        return self._settings.get(name) if isinstance(self._settings, dict) else None

    def copy(self):
        return type(self)(self.to_data())

    @notes_change
    def set_setting(self, *, name, value):
        """Set one setting by its file name, checking it as reading a file does, or None to leave it out.

        The settings are a table, one description each, so one generic setter checks them all
        the same way.
        """
        if not isinstance(self._settings, dict):
            raise InvalidValue(ERR_NOT_SETTINGS.format(value=self._settings))
        if name not in self.SETTINGS:
            raise InvalidValue(ERR_GENERATOR_NO_SUCH_SETTING.format(name=name, names=listed(sorted(self.SETTINGS))))
        if value is None:
            self._settings.pop(name, None)
        else:
            self.SETTINGS[name].check(value)
            self._settings[name] = own_copy(value)

    def get_restart(self):
        """Return when the generator starts over, every clip unless set."""
        return self._written(GENERATOR_RESTART) or Restart.EVERY_CLIP

    def make_generator(self, *, where, default_seed, default_step=None, bar=None, continuation=None):
        """Return the generator these settings describe, or raise SongFileError if they're wrong.

        where names the chain using it. default_seed is used by a generator that chooses at
        random, when its settings don't give a seed, default_step, the step size of the
        pattern the clip plays, by one whose step is left as "(pattern)", and bar, the length of
        the song's bar, by one whose time is written in bars.
        """
        with reading(where):
            self.check_data(self._settings)
            values = self._with_defaults(values=self._taken_values(), default_seed=default_seed, default_step=default_step, bar=bar)
            # Restart is the renderer's to read; the generator is handed where it carries on from instead.
            values.pop(GENERATOR_RESTART, None)
            return self.GENERATOR(**values, continuation=continuation)

    def _taken_values(self):
        """Return the settings as the generator takes them: a length as a number, a choice as what its name means, and the rest as written."""
        return {name: self.TAKEN_AS[name](value) if name in self.TAKEN_AS else value for name, value in self._settings.items()}

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        """Return the generator's values, with a seed and a step added where it needs them. Most don't."""
        return values


class ArpSettings(GeneratorSettings):
    """An arpeggiator's settings: its step length, order, seed, octave range and jump, and offsets."""

    __slots__ = ()

    GENERATOR = Arp
    SETTINGS = described(
        Checked(name=ArpSetting.STEP, check=time_length),
        Choice(name=ArpSetting.ORDER, choices=sorted(ORDERS), default=LEFT_OUT, error=ERR_NOT_A_CHOICE),
        WholeNumber(name=ArpSetting.SEED, error=ERR_GENERATOR_NOT_INTEGER),
        WholeNumber(name=ArpSetting.OCTAVE_RANGE, lowest=MIN_OCTAVE_RANGE, highest=MAX_OCTAVE_RANGE, error=ERR_GENERATOR_BAD_OCTAVE_RANGE),
        Choice(name=ArpSetting.OCTAVE_JUMP, choices=sorted(OCTAVE_JUMPS), default=LEFT_OUT, error=ERR_NOT_A_CHOICE),
        Checked(name=ArpSetting.OFFSETS, check=_check_arp_offsets, nearest=_nearest_offsets),
        *[WholeNumber(name=name, lowest=MIN_REGISTER_VALUE, highest=MAX_REGISTER_VALUE, error=ERR_GENERATOR_BAD_ADD) for name in ARP_NOTE_ADDS.values()],
        *[Checked(name=name, check=_check_step_adds) for name in ARP_STEP_ADDS.values()],
        RESTART_SETTING,
    )
    # A step left out is "(pattern)": the step size of the pattern the clip plays (the user's rule of 2026-11-11).
    REQUIRED = []
    TAKEN_AS = {ArpSetting.STEP: time_length, ArpSetting.ORDER: _order, ArpSetting.OCTAVE_JUMP: _octave_jump}

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        if ArpSetting.SEED not in values:
            values[ArpSetting.SEED] = default_seed
        if ArpSetting.STEP not in values:
            values[ArpSetting.STEP] = default_step
        elif isinstance(values[ArpSetting.STEP], Bars):
            values[ArpSetting.STEP] = bar * values[ArpSetting.STEP].count
        return values

    # Each setting as the file writes it, or None when the file leaves it out, for the tracker to show.

    def get_step(self):
        return self._written(ArpSetting.STEP)

    def get_order(self):
        return self._written(ArpSetting.ORDER)

    def get_seed(self):
        return self._written(ArpSetting.SEED)

    def get_octave_range(self):
        return self._written(ArpSetting.OCTAVE_RANGE)

    def get_octave_jump(self):
        return self._written(ArpSetting.OCTAVE_JUMP)

    def get_offsets(self):
        offsets = self._written(ArpSetting.OFFSETS)
        return None if offsets is None else list(offsets)

    def get_note_add(self, register):
        """Return how much each note the arp plays adds to a register, or None for nothing."""
        return self._written(ARP_NOTE_ADDS[register])

    def get_step_adds(self, register):
        """Return what each step of the offsets adds to a register, one a step with None for nothing, or None when the arp has no offsets."""
        offsets = self.get_offsets()
        if offsets is None:
            return None
        adds = self._written(ARP_STEP_ADDS[register]) or []
        return [adds[place] if place < len(adds) else None for place in range(len(offsets))]

    def adds_to_registers(self):
        """Return whether its notes or its offsets' steps add to any register."""
        return any(self.get_note_add(register) for register in REGISTER_NAMES) or any(any(self.get_step_adds(register) or []) for register in REGISTER_NAMES)

    def set_step_add(self, *, register, step, add):
        """Set what one step of the offsets adds to a register, where None or 0 adds nothing; a row that adds nothing is left out of the file."""
        self._offsets_to_change(step)
        adds = self.get_step_adds(register)
        adds[step] = add or None
        self.set_setting(name=ARP_STEP_ADDS[register], value=adds if any(adds) else None)

    @classmethod
    def new(cls):
        """Return the settings a new arp starts with: an upward order, its step the pattern's."""
        return cls({ArpSetting.ORDER: written_name(ChordOrder.UP)})

    # Editing the offsets one step at a time, as the offsets editor does.

    def set_offset(self, *, step, offset):
        """Set one step of the offsets, where None is a silent step."""
        offsets = self._offsets_to_change(step)
        offsets[step] = offset
        self.set_setting(name=ArpSetting.OFFSETS, value=offsets)

    def insert_offset(self, step):
        """Add a step that leaves the note where it is, before a step of the offsets, or at the end."""
        offsets = self.get_offsets()
        if offsets is None or not is_whole_number_from(value=step, lowest=0, highest=len(offsets)):
            raise InvalidValue(ERR_NO_SUCH_OFFSET.format(step=step, count=len(offsets or [])))
        rows = {register: self.get_step_adds(register) for register in REGISTER_NAMES}
        offsets.insert(step, NO_OFFSET)
        self.set_setting(name=ArpSetting.OFFSETS, value=offsets)
        for register, adds in rows.items():
            if any(adds):
                self.set_setting(name=ARP_STEP_ADDS[register], value=adds[:step] + [None] + adds[step:])

    def remove_offset(self, step):
        offsets = self._offsets_to_change(step)
        rows = {register: self.get_step_adds(register) for register in REGISTER_NAMES}
        offsets.pop(step)
        self.set_setting(name=ArpSetting.OFFSETS, value=offsets or None)
        for register, adds in rows.items():
            kept = adds[:step] + adds[step + 1:]
            self.set_setting(name=ARP_STEP_ADDS[register], value=kept if any(kept) else None)

    def _offsets_to_change(self, step):
        """Return a copy of the offsets with a step to change, or raise InvalidValue if there's no such step."""
        offsets = self.get_offsets()
        if offsets is None:
            raise InvalidValue(ERR_NO_OFFSETS)
        if not is_whole_number_from(value=step, lowest=0, highest=len(offsets) - 1):
            raise InvalidValue(ERR_NO_SUCH_OFFSET.format(step=step, count=len(offsets)))
        return offsets


class AutoRatchetSettings(GeneratorSettings):
    """An AutoRatchet's settings: the counts it cycles through."""

    __slots__ = ()

    GENERATOR = AutoRatchet
    SETTINGS = described(Checked(name=AutoRatchetSetting.COUNTS, check=_check_counts), RESTART_SETTING)
    REQUIRED = [AutoRatchetSetting.COUNTS]

    def get_counts(self):
        """Return its counts as the file writes them, or None when the file leaves them out."""
        counts = self._written(AutoRatchetSetting.COUNTS)
        return None if counts is None else list(counts)

    @classmethod
    def new(cls):
        """Return the settings a new AutoRatchet starts with."""
        return cls({AutoRatchetSetting.COUNTS: list(NEW_AUTO_RATCHET_COUNTS)})


class ProgressionSetting:
    """A Progression's settings, as a file names them: its chords as degrees, a sharp or flat and an inversion for each, and how long each chord lasts."""

    RESTART = GENERATOR_RESTART

    EVERY = 'every'
    CHORDS = 'chords'
    ACCIDENTALS = 'accidentals'
    INVERSIONS = 'inversions'
    # The user's design: the scale type each chord borrows, its named quality, and the tensions on top, each beside the chords.
    SCALES = 'scales'
    QUALITIES = 'qualities'
    TENSIONS = 'tensions'


def _check_progression_chords(chords):
    """Check a progression's chords: a list of 1 to MAX_PROGRESSION_CHORDS degrees."""
    fits = isinstance(chords, list) and MIN_PROGRESSION_CHORDS <= len(chords) <= MAX_PROGRESSION_CHORDS and all(
        is_whole_number_from(value=degree, lowest=MIN_PROGRESSION_DEGREE, highest=MAX_PROGRESSION_DEGREE) for degree in chords)
    if not fits:
        raise InvalidValue(ERR_BAD_PROGRESSION_CHORDS.format(most=MAX_PROGRESSION_CHORDS, lowest=MIN_PROGRESSION_DEGREE, highest=MAX_PROGRESSION_DEGREE, value=chords))


def _row_of(*, name, allowed):
    """Return a check of a list beside the chords, each step one of the allowed values or nothing."""
    def check(values):
        if not isinstance(values, list) or not all(value is None or value in allowed for value in values):
            raise InvalidValue(ERR_BAD_PROGRESSION_ROW.format(name=name, choices=listed(allowed), value=values))
    return check


def _tensions_row(values):
    """Check a progression's tensions: a list beside the chords, each step a list of some of the tensions, each once, or nothing."""
    def is_tensions(value):
        return isinstance(value, (list, tuple)) and len(value) > 0 and len(set(value)) == len(value) and all(tension in TENSIONS for tension in value)
    if not isinstance(values, list) or not all(value is None or is_tensions(value) for value in values):
        raise InvalidValue(ERR_BAD_PROGRESSION_TENSIONS.format(name=ProgressionSetting.TENSIONS, choices=listed(TENSIONS), value=values))


# What a progression's sharp-or-flat and inversion rows may hold beside nothing.
PROGRESSION_ACCIDENTALS = [Accidental.SHARP, Accidental.FLAT]
PROGRESSION_INVERSIONS = list(range(1, MAX_PROGRESSION_INVERSION + 1))
# A new progression's one chord, I, which moves nothing until it's edited (the user's choice of 2026-11-11).
NEW_PROGRESSION_CHORDS = [1]
# The rows beside a progression's chords, each as long as the chords.
PROGRESSION_ROWS = (
    ProgressionSetting.ACCIDENTALS, ProgressionSetting.INVERSIONS, ProgressionSetting.SCALES, ProgressionSetting.QUALITIES, ProgressionSetting.TENSIONS,
)


class ProgressionSettings(GeneratorSettings):
    """A Progression's settings: its chords, each with a sharp or flat and an inversion, and how long each lasts, a bar when left out."""

    __slots__ = ()

    GENERATOR = Progression
    SETTINGS = described(
        Checked(name=ProgressionSetting.EVERY, check=time_length),
        Checked(name=ProgressionSetting.CHORDS, check=_check_progression_chords),
        Checked(name=ProgressionSetting.ACCIDENTALS, check=_row_of(name=ProgressionSetting.ACCIDENTALS, allowed=PROGRESSION_ACCIDENTALS)),
        Checked(name=ProgressionSetting.INVERSIONS, check=_row_of(name=ProgressionSetting.INVERSIONS, allowed=PROGRESSION_INVERSIONS)),
        Checked(name=ProgressionSetting.SCALES, check=_row_of(name=ProgressionSetting.SCALES, allowed=scale_type_names())),
        Checked(name=ProgressionSetting.QUALITIES, check=_row_of(name=ProgressionSetting.QUALITIES, allowed=list(FIXED_CHORDS))),
        Checked(name=ProgressionSetting.TENSIONS, check=_tensions_row),
        RESTART_SETTING,
    )
    REQUIRED = [ProgressionSetting.CHORDS]
    TAKEN_AS = {ProgressionSetting.EVERY: time_length}

    @classmethod
    def new(cls):
        """Return the settings a new progression starts with: the one chord I."""
        return cls({ProgressionSetting.CHORDS: list(NEW_PROGRESSION_CHORDS)})

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        every = values.get(ProgressionSetting.EVERY, Bars(1))
        values[ProgressionSetting.EVERY] = bar * every.count if isinstance(every, Bars) else every
        chords = values[ProgressionSetting.CHORDS]
        for row in PROGRESSION_ROWS:
            values[row] = _lined_up(values=values.get(row), count=len(chords))
        return values

    def get_every(self):
        return self._written(ProgressionSetting.EVERY)

    def get_chords(self):
        return list(self._written(ProgressionSetting.CHORDS) or NEW_PROGRESSION_CHORDS)

    def get_accidentals(self):
        return _lined_up(values=self._written(ProgressionSetting.ACCIDENTALS), count=len(self.get_chords()))

    def get_inversions(self):
        return _lined_up(values=self._written(ProgressionSetting.INVERSIONS), count=len(self.get_chords()))

    def get_scales(self):
        """Return the scale type each chord borrows, or None for the clip's own."""
        return _lined_up(values=self._written(ProgressionSetting.SCALES), count=len(self.get_chords()))

    def get_qualities(self):
        """Return each chord's named quality, a chord symbol, or None for the chord its scale builds."""
        return _lined_up(values=self._written(ProgressionSetting.QUALITIES), count=len(self.get_chords()))

    def get_tensions(self):
        """Return each chord's tensions as a tuple, lowest first, or None for none."""
        return [None if value is None else tuple(tension for tension in TENSIONS if tension in value) for value in _lined_up(values=self._written(ProgressionSetting.TENSIONS), count=len(self.get_chords()))]


def _lined_up(*, values, count):
    """Return a row beside the chords as long as the chords, a missing step being nothing."""
    values = list(values or [])
    return (values + [None] * count)[:count]


class VoiceLeadingSetting:
    """A Voice leading's settings, as a file names them: the octaves its chords stay within, and whether the root stays in the bass."""

    RESTART = GENERATOR_RESTART

    LOWEST_OCTAVE = 'lowest_octave'
    HIGHEST_OCTAVE = 'highest_octave'
    ROOT_IN_BASS = 'root_in_bass'


# A voice leading's chords stay from the bottom of octave 4 to the top of octave 6, around middle C, unless set; the root moves with the chord.
DEFAULT_VOICING_LOWEST_OCTAVE = 4
DEFAULT_VOICING_HIGHEST_OCTAVE = 6
DEFAULT_ROOT_IN_BASS = False


class VoiceLeadingSettings(GeneratorSettings):
    """A Voice leading's settings: its range of octaves and whether the root stays in the bass, each left out for its default."""

    __slots__ = ()

    GENERATOR = VoiceLeading
    SETTINGS = described(
        WholeNumber(name=VoiceLeadingSetting.LOWEST_OCTAVE, lowest=MIN_OCTAVE, highest=MAX_OCTAVE, error=ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=VoiceLeadingSetting.HIGHEST_OCTAVE, lowest=MIN_OCTAVE, highest=MAX_OCTAVE, error=ERR_BAD_SHAPE_PERCENT),
        Flag(name=VoiceLeadingSetting.ROOT_IN_BASS, error=ERR_ROOT_IN_BASS_NOT_TRUE_OR_FALSE),
        RESTART_SETTING,
    )

    @classmethod
    def new(cls):
        return cls({})

    @classmethod
    def check_data(cls, data):
        super().check_data(data)
        lowest = data.get(VoiceLeadingSetting.LOWEST_OCTAVE, DEFAULT_VOICING_LOWEST_OCTAVE)
        highest = data.get(VoiceLeadingSetting.HIGHEST_OCTAVE, DEFAULT_VOICING_HIGHEST_OCTAVE)
        if lowest > highest:
            raise InvalidValue(ERR_VOICE_LEADING_RANGE.format(lowest=lowest, highest=highest))

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        values.setdefault(VoiceLeadingSetting.LOWEST_OCTAVE, DEFAULT_VOICING_LOWEST_OCTAVE)
        values.setdefault(VoiceLeadingSetting.HIGHEST_OCTAVE, DEFAULT_VOICING_HIGHEST_OCTAVE)
        values.setdefault(VoiceLeadingSetting.ROOT_IN_BASS, DEFAULT_ROOT_IN_BASS)
        return values

    def get_lowest_octave(self):
        return or_default(value=self._written(VoiceLeadingSetting.LOWEST_OCTAVE), default=DEFAULT_VOICING_LOWEST_OCTAVE)

    def get_highest_octave(self):
        return or_default(value=self._written(VoiceLeadingSetting.HIGHEST_OCTAVE), default=DEFAULT_VOICING_HIGHEST_OCTAVE)

    def keeps_root_in_bass(self):
        return bool(self._written(VoiceLeadingSetting.ROOT_IN_BASS))


class StrumSettings(GeneratorSettings):
    """A Strum generator's settings, which win over a clip's and its track's: its direction, spread, fade, loose timing and upstroke strings.

    Like a drift, it runs on no clip's notes: the renderer reads it for each clip that names it,
    and the exporters' timing strums the notes (exporters/timing.py), so GENERATOR is None.
    """

    __slots__ = ()

    GENERATOR = None
    SETTINGS = described(*strum_part_settings(lambda part: part), RESTART_SETTING)

    @classmethod
    def new(cls):
        """Return the settings a new Strum starts with: by the beat, so that it strums at once."""
        return cls({StrumPart.DIRECTION: StrumDirection.BY_THE_BEAT})

    def get_strum_setting(self, part):
        return self._written(part)

    def get_strum(self):
        """Return how it strums, by the beat when its direction is blank."""
        return strum_values(lambda part: self._written(part) if part != StrumPart.DIRECTION else self._written(part) or StrumDirection.BY_THE_BEAT)


class EuclidSettings(GeneratorSettings):
    """A Euclid generator's settings, a mask painted on clips on top of their track's: its hits, steps, rotation and step, a bar of sixteenths at the pattern's step size unless set."""

    __slots__ = ()

    GENERATOR = EuclidMask
    SETTINGS = described(*euclid_part_settings(lambda part: part), RESTART_SETTING)
    TAKEN_AS = {EuclidPart.STEP: time_length}

    @classmethod
    def new(cls):
        """Return the settings a new Euclid starts with: the tresillo, three hits over eight steps."""
        hits, steps = NAMED_RHYTHMS[NamedRhythm.TRESILLO]
        return cls({EuclidPart.HITS: hits, EuclidPart.STEPS: steps})

    @classmethod
    def check_data(cls, data):
        super().check_data(data)
        _check_hits_fit(hits=data.get(EuclidPart.HITS), steps=data.get(EuclidPart.STEPS))

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        mask = euclid_values(lambda part: values.get(part))
        step = values.get(EuclidPart.STEP)
        if isinstance(step, Bars):
            step = bar * step.count
        return {EuclidPart.HITS: mask.hits, EuclidPart.STEPS: mask.steps, EuclidPart.ROTATE: mask.rotate, EuclidPart.STEP: step or default_step}

    def get_euclid_setting(self, part):
        return self._written(part)

    def get_euclid(self):
        return euclid_values(self._written)


def _check_hits_fit(*, hits, steps):
    """Refuse more hits than steps, a bar of sixteenths when the steps are left out."""
    if hits is not None and hits > (DEFAULT_EUCLID_STEPS if steps is None else steps):
        raise InvalidValue(ERR_EUCLID_TOO_MANY_HITS.format(hits=hits, steps=DEFAULT_EUCLID_STEPS if steps is None else steps))


class StepRowSetting:
    """A Glide's, a Shorten's, a Rush's or a Drag's settings, as a file names them: its row of steps, each on or off, how long each step is, and how much a step that's on changes its note."""

    RESTART = GENERATOR_RESTART
    STEPS = 'steps'
    STEP = 'step'
    GLIDE_AMOUNT = 'glide_amount'
    SHORTEN = 'shorten'
    AMOUNT = 'amount'


# A gliding note runs 1/128 into the next unless set, as the pattern's Glide row has always had it, from 1/256 to 1/16; a shortened note plays 70%; a rush moves a note 15% of a step early and a drag 20% late.
DEFAULT_GLIDE_AMOUNT = Rational(1, 128)
LEAST_GLIDE_AMOUNT = Rational(1, 256)
MOST_GLIDE_AMOUNT = Rational(1, 16)
DEFAULT_SHORTEN = 70
DEFAULT_RUSH = 15
DEFAULT_DRAG = 20
NEW_STEP_ROW = [True, False, False, False]
NO_RUSH_OR_DRAG = 0


def _check_step_row(values):
    """Check a row of steps: a list of 1 to MAX_STEP_ROW, each on or off."""
    fits = isinstance(values, list) and MIN_STEP_ROW <= len(values) <= MAX_STEP_ROW and all(is_true_or_false(value) for value in values)
    if not fits:
        raise InvalidValue(ERR_BAD_STEP_ROW.format(name=StepRowSetting.STEPS, most=MAX_STEP_ROW, value=values))


def _check_glide_amount(value):
    amount = number(value)
    if not LEAST_GLIDE_AMOUNT <= amount <= MOST_GLIDE_AMOUNT:
        raise InvalidValue(ERR_BAD_GLIDE_AMOUNT.format(least=LEAST_GLIDE_AMOUNT, most=MOST_GLIDE_AMOUNT, value=value))


# What every row of steps holds besides its amount: the row, its step and its Restart.
STEP_ROW_SETTINGS = (Checked(name=StepRowSetting.STEPS, check=_check_step_row), Checked(name=StepRowSetting.STEP, check=time_length), RESTART_SETTING)


class StepRowSettings(GeneratorSettings):
    """What a Glide's, a Shorten's, a Rush's and a Drag's settings share: a row of on-or-off steps from each clip's start, each step as long as its step, the clip's pattern's step size unless set."""

    __slots__ = ()

    REQUIRED = [StepRowSetting.STEPS]

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: four steps, the first on."""
        return cls({StepRowSetting.STEPS: list(NEW_STEP_ROW)})

    def get_steps(self):
        return [bool(value) for value in (self._written(StepRowSetting.STEPS) or NEW_STEP_ROW)]

    def get_step(self):
        return self._written(StepRowSetting.STEP)

    def step_length(self, *, default_step, bar):
        """Return how long each step is, in whole notes."""
        step = self.get_step()
        return default_step if step is None else in_whole_notes(time=step, bar=bar)

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        return {StepRowSetting.STEPS: self.get_steps(), StepRowSetting.STEP: self.step_length(default_step=default_step, bar=bar), **self.amounts()}

    def amounts(self):
        """Return the generator's amount, as its generator takes it."""
        return {}


class GlideSettings(StepRowSettings):
    """A Glide's settings: its row, and how far a note starting on a step that's on runs into the next."""

    __slots__ = ()

    GENERATOR = Glide
    SETTINGS = described(STEP_ROW_SETTINGS[0], STEP_ROW_SETTINGS[1], Checked(name=StepRowSetting.GLIDE_AMOUNT, check=_check_glide_amount), STEP_ROW_SETTINGS[2])

    def amounts(self):
        return {StepRowSetting.GLIDE_AMOUNT: self.get_glide_amount()}

    def get_written_glide_amount(self):
        """Return the glide amount as the file writes it, or None when it's left out."""
        return self._written(StepRowSetting.GLIDE_AMOUNT)

    def get_glide_amount(self):
        written = self._written(StepRowSetting.GLIDE_AMOUNT)
        return DEFAULT_GLIDE_AMOUNT if written is None else number(written)


class ShortenSettings(StepRowSettings):
    """A Shorten's settings: its row, and how much of itself a note starting on a step that's on plays."""

    __slots__ = ()

    GENERATOR = Shorten
    SETTINGS = described(
        STEP_ROW_SETTINGS[0], STEP_ROW_SETTINGS[1], WholeNumber(name=StepRowSetting.SHORTEN, lowest=MIN_SHORTEN, highest=MAX_SHORTEN, error=ERR_BAD_SHAPE_PERCENT),
        STEP_ROW_SETTINGS[2],
    )

    def amounts(self):
        return {StepRowSetting.SHORTEN: self.get_shorten()}

    def get_shorten(self):
        return or_default(value=self._written(StepRowSetting.SHORTEN), default=DEFAULT_SHORTEN)


class MovingRowSettings(StepRowSettings):
    """A Rush's or a Drag's settings: its row, and how far a note starting on a step that's on moves, as a share of a step.

    It runs on no clip's notes itself: the renderer reads it for each clip that names it, and the
    exporters' timing moves the notes, on top of the groove (exporters/timing.py), so GENERATOR is None.
    """

    __slots__ = ()

    GENERATOR = None
    DEFAULT_AMOUNT = None
    SETTINGS = described(
        STEP_ROW_SETTINGS[0], STEP_ROW_SETTINGS[1], WholeNumber(name=StepRowSetting.AMOUNT, lowest=NO_RUSH_OR_DRAG, highest=MAX_RUSH_OR_DRAG, error=ERR_BAD_SHAPE_PERCENT),
        STEP_ROW_SETTINGS[2],
    )

    def get_amount(self):
        return or_default(value=self._written(StepRowSetting.AMOUNT), default=self.DEFAULT_AMOUNT)


class RushSettings(MovingRowSettings):
    """A Rush's settings: a note starting on a step that's on plays early."""

    __slots__ = ()

    DEFAULT_AMOUNT = DEFAULT_RUSH


class DragSettings(MovingRowSettings):
    """A Drag's settings: a note starting on a step that's on plays late."""

    __slots__ = ()

    DEFAULT_AMOUNT = DEFAULT_DRAG


class ShapeSetting:
    """A Density, Swell or Articulate generator's settings, as a file names them: a Swell's accent besides the four every shape has."""

    RESTART = GENERATOR_RESTART

    START = 'start'
    END = 'end'
    OVER = 'over'
    THEN = 'then'
    ACCENT = 'accent'


def _drift_settings():
    """Return a drift's settings, each described once: its own, then each version's values, A's first."""
    numbers = {name: (lowest, highest) for name, lowest, highest in DRIFT_NUMBERS}
    versions = []
    for version in DRIFT_VERSIONS:
        for value in DRIFT_VALUES:
            name = versioned(version=version, value=value)
            if value == DriftValue.SCALE:
                versions.append(Checked(name=name, check=_check_scale_name))
            elif value == DriftValue.ROOT:
                versions.append(Checked(name=name, check=_check_root))
            else:
                lowest, highest = numbers[value]
                versions.append(WholeNumber(name=name, lowest=lowest, highest=highest, error=ERR_GENERATOR_BAD_ADD))
    return described(
        Checked(name=DriftSetting.EVERY, check=time_length),
        WholeNumber(name=DriftSetting.STEPS_TO_B, lowest=MIN_STEPS_TO_B, highest=MAX_STEPS_TO_B, error=ERR_GENERATOR_BAD_ADD),
        Choice(name=DriftSetting.DIRECTION, choices=DRIFT_DIRECTIONS, default=LEFT_OUT, error=ERR_NOT_A_CHOICE),
        WholeNumber(name=DriftSetting.SEED, error=ERR_GENERATOR_NOT_INTEGER),
        *versions,
        RESTART_SETTING,
    )


class DriftSettings(GeneratorSettings):
    """A drift's settings: how often it triggers, how many triggers it takes from A to B, which way it moves, its seed, and what each version sets.

    A drift is not a generator a chain runs on a clip's notes: the render reads these settings
    as one process for the whole song (playback/drift.py), and every clip whose chain names the
    drift hears it, so GENERATOR is None and a chain step naming a drift changes nothing itself.
    """

    __slots__ = ()

    GENERATOR = None
    SETTINGS = _drift_settings()

    @classmethod
    def new(cls):
        """Return the settings a new drift starts with: nothing set, so it does nothing until a version is given values."""
        return cls({})

    def get_every(self):
        """Return how often it triggers, as the file writes it, or None for one bar of the song it plays in."""
        return self._written(DriftSetting.EVERY)

    def get_steps_to_b(self):
        return self._written(DriftSetting.STEPS_TO_B) or DEFAULT_STEPS_TO_B

    def get_direction(self):
        return self._written(DriftSetting.DIRECTION) or DRIFT_DIRECTIONS[0]

    def get_seed(self):
        return self._written(DriftSetting.SEED)

    def get_value(self, *, version, value):
        """Return one version's value as the file writes it, or None when the version leaves it out."""
        return self._written(versioned(version=version, value=value))

    def adds_to_registers(self):
        """Return whether either version adds to a register at its triggers."""
        return any(self.get_value(version=version, value=value) for version in DRIFT_VERSIONS for value in DRIFT_ADDS.values())


class ShapeSettings(GeneratorSettings):
    """A shape's settings as a generator a chain names, which wins over its clip's and its scene's: Density, Swell or Articulate, each a subclass.

    Like a drift, it runs on no clip's notes itself: the render reads it for each clip that
    names it (playback/shapes.py), so GENERATOR is None.
    """

    __slots__ = ()

    GENERATOR = None
    SHAPE = None

    @classmethod
    def new(cls):
        """Return the settings a new one starts with: nothing set, which plays as 100%, changing nothing until given values."""
        return cls({})

    def get_shape(self):
        """Return its shape's values, its start and end 100% when left blank."""
        written = {shape_setting(shape=self.SHAPE, part=part): self._written(part) for part in SHAPE_PARTS}
        values = shape_values(settings=written, shape=self.SHAPE)
        accent = self._written(ShapeSetting.ACCENT) or NO_ACCENT
        if values is None:
            return ShapeValues(UNCHANGED, UNCHANGED, written[shape_setting(shape=self.SHAPE, part=ShapePart.OVER)],
                               written[shape_setting(shape=self.SHAPE, part=ShapePart.THEN)] or SHAPE_THENS[0], accent)
        return values._replace(accent=accent)


class DensitySettings(ShapeSettings):
    """A Density generator's settings: the share of notes that play, from its start to its end."""

    __slots__ = ()

    SHAPE = Shape.DENSITY
    SETTINGS = described(*shape_part_settings(shape=Shape.DENSITY, named=lambda part: part), RESTART_SETTING)


class SwellSettings(ShapeSettings):
    """A Swell generator's settings: how loud the notes play, from its start to its end, and how much louder the strong beats are."""

    __slots__ = ()

    SHAPE = Shape.SWELL
    SETTINGS = described(
        *shape_part_settings(shape=Shape.SWELL, named=lambda part: part),
        WholeNumber(name=ShapeSetting.ACCENT, lowest=MIN_ACCENT, highest=MAX_ACCENT, error=ERR_BAD_SHAPE_PERCENT),
        RESTART_SETTING,
    )


class ArticulateSettings(ShapeSettings):
    """An Articulate generator's settings: how long each note sounds, as a share of what's written, from its start to its end."""

    __slots__ = ()

    SHAPE = Shape.ARTICULATE
    SETTINGS = described(*shape_part_settings(shape=Shape.ARTICULATE, named=lambda part: part), RESTART_SETTING)


# Each generator a chain step can name, and the class that holds its settings.
class HocketSetting:
    """A Hocket's settings, as a file names them: the track whose notes it shares out."""

    RESTART = GENERATOR_RESTART

    SOURCE = 'source'


class HocketSettings(GeneratorSettings):
    """A Hocket's settings: the source track whose notes the hocketing tracks take turns at, the user's design of 2026-11-11, and its Restart.

    Like a drift, it runs on no clip's notes itself: the renderer works out each scene's turns
    once from the source track's clip, and hands each hocketing clip its notes, which the
    exporters' timing adds to the clip's own (exporters/timing.py), so GENERATOR is None. The
    source names a track of the song it plays in, and a rename of that track follows.
    """

    __slots__ = ()

    GENERATOR = None
    SETTINGS = described(Text(name=HocketSetting.SOURCE, error=ERR_NOT_TEXT), RESTART_SETTING)
    REFERENCES = {Section.TRACKS: (HocketSetting.SOURCE,)}

    @classmethod
    def new(cls):
        """Return the settings a new Hocket starts with: no source, so that it hands out nothing until one is chosen."""
        return cls({})

    def get_source(self):
        """Return the name of the track whose notes it shares out, or None for none."""
        return self._written(HocketSetting.SOURCE)

    def names_item(self, *, section, name):
        return section == Section.TRACKS and self.get_source() == name

    @notes_change
    def _rename_own_references(self, *, section, old, new):
        self._settings[HocketSetting.SOURCE] = new


GENERATOR_SETTINGS = {
    GeneratorKind.ARP: ArpSettings, GeneratorKind.AUTO_RATCHET: AutoRatchetSettings, GeneratorKind.DRIFT: DriftSettings,
    GeneratorKind.PROGRESSION: ProgressionSettings, GeneratorKind.VOICE_LEADING: VoiceLeadingSettings,
    GeneratorKind.STRUM: StrumSettings, GeneratorKind.EUCLID: EuclidSettings, GeneratorKind.GLIDE: GlideSettings, GeneratorKind.SHORTEN: ShortenSettings,
    GeneratorKind.RUSH: RushSettings, GeneratorKind.DRAG: DragSettings,
    GeneratorKind.DENSITY: DensitySettings, GeneratorKind.SWELL: SwellSettings, GeneratorKind.ARTICULATE: ArticulateSettings,
    GeneratorKind.HOCKET: HocketSettings,
}

