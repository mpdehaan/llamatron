# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of the guitarify generator: their names, their checks and their defaults, as a set file holds them."""

from llamatron.engine.generators import settings_base
from llamatron.engine.generators.guitarify import schema as guitar_bars
from llamatron.engine.generators.guitarify.generator import Guitarify
from llamatron.engine.generators.settings_base import GeneratorSettings
from llamatron.model.file import corrections
from llamatron.model.file.checks import Bars, is_true_or_false, listed, time_length
from llamatron.model.file.invalid_value import InvalidValue
from llamatron.model.objects.llama_data import or_default
from llamatron.model.objects.traits import HasCells
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Approach, ChordColor, GuitarifySetting, SingleNotes, Stroke, Tuning
from llamatron.model.schema.setting import Checked, Choice, described, Flag, WholeNumber
from llamatron.user_strings import errors

# What a Guitarify does with each setting left out: both halves on, a standard guitar held in the open position with no capo, single
# notes left alone, the default bar, nothing ringing on, and a strum of normal spread, fading a little, slightly loose, its upstrokes
# catching the top four strings.
DEFAULT_GUITAR_POSITION = 0


DEFAULT_GUITAR_CAPO = 0


DEFAULT_GUITAR_STRINGS = 6


DEFAULT_GUITAR_SPREAD = 8


DEFAULT_GUITAR_FADE = 20


DEFAULT_GUITAR_LOOSE_TIMING = 10


DEFAULT_GUITAR_UPSTROKE = 4


MIN_GUITAR_STRINGS = 3


MAX_GUITAR_STRINGS = 6


MAX_GUITAR_FRET = 12


MAX_GUITAR_BAR = 32


MAX_GUITAR_SPREAD = 60


MAX_GUITAR_PERCENT = 50


# An upstroke that catches every string.
EVERY_STRING = 0


def _check_guitar_bar(values):
    """Check a bar of strokes: a list of 1 to MAX_GUITAR_BAR, each a stroke's name."""
    if not (isinstance(values, list) and 1 <= len(values) <= MAX_GUITAR_BAR and all(value in file_format.STROKES for value in values)):
        raise InvalidValue(errors.ERR_BAD_GUITAR_BAR.format(name=GuitarifySetting.BAR, most=MAX_GUITAR_BAR, choices=listed(file_format.STROKES), value=values))


def _check_guitar_accents(values):
    """Check the accents beside a bar of strokes: a list of at most MAX_GUITAR_BAR, each on or off."""
    if not (isinstance(values, list) and len(values) <= MAX_GUITAR_BAR and all(is_true_or_false(value) for value in values)):
        raise InvalidValue(errors.ERR_BAD_GUITAR_ACCENTS.format(name=GuitarifySetting.ACCENTS, most=MAX_GUITAR_BAR, value=values))


def _guitar_flag(name):
    return Flag(name=name, error=errors.ERR_GUITARIFY_NOT_TRUE_OR_FALSE.format(name=name))


class GuitarifySettings(HasCells, GeneratorSettings):
    """A Guitarify's settings: Shape and the strokes, each half with a switch, every setting left out for its default."""

    __slots__ = ()

    GENERATOR = Guitarify
    SETTINGS = described(
        _guitar_flag(GuitarifySetting.SHAPE),
        Choice(name=GuitarifySetting.TUNING, choices=file_format.TUNINGS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        WholeNumber(name=GuitarifySetting.POSITION, lowest=0, highest=MAX_GUITAR_FRET, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=GuitarifySetting.CAPO, lowest=0, highest=MAX_GUITAR_FRET, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=GuitarifySetting.STRINGS, lowest=MIN_GUITAR_STRINGS, highest=MAX_GUITAR_STRINGS, error=errors.ERR_BAD_SHAPE_PERCENT),
        Choice(name=GuitarifySetting.SINGLE_NOTES, choices=file_format.SINGLE_NOTES, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        Choice(name=GuitarifySetting.COLOR, choices=file_format.CHORD_COLORS, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        _guitar_flag(GuitarifySetting.STROKES),
        Checked(name=GuitarifySetting.BAR, check=_check_guitar_bar),
        Checked(name=GuitarifySetting.ACCENTS, check=_check_guitar_accents),
        Checked(name=GuitarifySetting.CELL, check=time_length),
        _guitar_flag(GuitarifySetting.LET_RING),
        WholeNumber(name=GuitarifySetting.SPREAD, lowest=0, highest=MAX_GUITAR_SPREAD, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=GuitarifySetting.FADE, lowest=0, highest=MAX_GUITAR_PERCENT, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=GuitarifySetting.LOOSE_TIMING, lowest=0, highest=MAX_GUITAR_PERCENT, error=errors.ERR_BAD_SHAPE_PERCENT),
        WholeNumber(name=GuitarifySetting.UPSTROKE, lowest=EVERY_STRING, highest=MAX_GUITAR_STRINGS, error=errors.ERR_BAD_SHAPE_PERCENT),
        Choice(name=GuitarifySetting.APPROACH, choices=file_format.APPROACHES, default=corrections.LEFT_OUT, error=errors.ERR_NOT_A_CHOICE),
        settings_base.RESTART_SETTING,
    )
    TAKEN_AS = {GuitarifySetting.CELL: time_length}

    @classmethod
    def new(cls):
        return cls({})

    def _with_defaults(self, *, values, default_seed, default_step, bar):
        cell = time_length(self.get_cell())
        return dict(
            shape=self.shapes(), tuning=self.get_tuning(), position=self.get_position(), capo=self.get_capo(), strings=self.get_strings(),
            single_notes=self.get_single_notes(), color=self.get_color(), approach=self.get_approach(), strokes=self.strikes(), bar=self.get_bar(), accents=self.get_accents(),
            cell=bar * cell.count if isinstance(cell, Bars) else cell, let_ring=self.lets_ring(), spread=self.get_spread(), fade=self.get_fade(),
            loose_timing=self.get_loose_timing(), upstroke=self.get_upstroke() or None, seed=default_seed,
        )

    def _with_tempo(self, *, values, tempo):
        return dict(values, tempo=tempo)

    def shapes(self):
        """Return whether the Shape half is on, which it is unless switched off."""
        return self.get_written(GuitarifySetting.SHAPE) is not False

    def strikes(self):
        """Return whether the Strokes half is on, which it is unless switched off."""
        return self.get_written(GuitarifySetting.STROKES) is not False

    def lets_ring(self):
        return bool(self.get_written(GuitarifySetting.LET_RING))

    def get_tuning(self):
        return self.get_written(GuitarifySetting.TUNING) or Tuning.STANDARD

    def get_position(self):
        return or_default(value=self.get_written(GuitarifySetting.POSITION), default=DEFAULT_GUITAR_POSITION)

    def get_capo(self):
        return or_default(value=self.get_written(GuitarifySetting.CAPO), default=DEFAULT_GUITAR_CAPO)

    def get_strings(self):
        return or_default(value=self.get_written(GuitarifySetting.STRINGS), default=DEFAULT_GUITAR_STRINGS)

    def get_single_notes(self):
        return self.get_written(GuitarifySetting.SINGLE_NOTES) or SingleNotes.LEAVE

    def get_color(self):
        return self.get_written(GuitarifySetting.COLOR) or ChordColor.AS_WRITTEN

    def get_approach(self):
        return self.get_written(GuitarifySetting.APPROACH) or Approach.OFF

    # Editing the bar one cell at a time, as its editor does: the bar, its accents and the cell's length are written together, so that a bar edited is a bar written in full.

    def set_bar(self, *, strokes, accents, cell=None):
        """Keep the bar's strokes and accents and, where given, its cell's length."""
        length = self.get_cell() if cell is None else cell
        self.set_setting(name=GuitarifySetting.BAR, value=list(strokes))
        self.set_setting(name=GuitarifySetting.ACCENTS, value=list(accents))
        self.set_setting(name=GuitarifySetting.CELL, value=length)

    def set_cell(self, *, step, value):
        """Give one cell of the bar a stroke."""
        strokes = self.get_bar()
        strokes[step] = value
        self.set_bar(strokes=strokes, accents=self.get_accents())

    def insert_cell(self, step):
        """Add a cell with no stroke and no accent before a cell of the bar."""
        strokes = self.get_bar()
        accents = self.get_accents()
        self.set_bar(strokes=strokes[:step] + [Stroke.NOTHING] + strokes[step:], accents=accents[:step] + [False] + accents[step:])

    def remove_cell(self, step):
        strokes = self.get_bar()
        accents = self.get_accents()
        self.set_bar(strokes=strokes[:step] + strokes[step + 1:], accents=accents[:step] + accents[step + 1:])

    def get_bar(self):
        """Return the stroke of each cell, the default bar's unless written."""
        return list(self.get_written(GuitarifySetting.BAR) or guitar_bars.READY_BARS[guitar_bars.DEFAULT_BAR].strokes)

    def get_accents(self):
        """Return whether each cell is accented, as long as the bar: the default bar's while the bar is unwritten, and none where a written bar has none."""
        if self.get_written(GuitarifySetting.BAR) is None and self.get_written(GuitarifySetting.ACCENTS) is None:
            return list(guitar_bars.READY_BARS[guitar_bars.DEFAULT_BAR].accents)
        count = len(self.get_bar())
        return (list(self.get_written(GuitarifySetting.ACCENTS) or []) + [False] * count)[:count]

    def get_cell(self):
        """Return how long a cell lasts, as a file writes it: the default bar's unless written."""
        return self.get_written(GuitarifySetting.CELL) or guitar_bars.READY_BARS[guitar_bars.DEFAULT_BAR].cell

    def get_spread(self):
        return or_default(value=self.get_written(GuitarifySetting.SPREAD), default=DEFAULT_GUITAR_SPREAD)

    def get_fade(self):
        return or_default(value=self.get_written(GuitarifySetting.FADE), default=DEFAULT_GUITAR_FADE)

    def get_loose_timing(self):
        return or_default(value=self.get_written(GuitarifySetting.LOOSE_TIMING), default=DEFAULT_GUITAR_LOOSE_TIMING)

    def get_upstroke(self):
        """Return how many of the top strings an upstroke catches, or EVERY_STRING for all."""
        return or_default(value=self.get_written(GuitarifySetting.UPSTROKE), default=DEFAULT_GUITAR_UPSTROKE)
