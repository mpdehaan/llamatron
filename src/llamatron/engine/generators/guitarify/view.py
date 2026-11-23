# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Guitarify generator's page: its Mode, then in Strum mode the Strum column (Direction and the four settings both modes share),
or in Guitar mode the Left Hand column, how chords are held, and the Right Hand column, how they are struck, then its Restart."""

from llamatron.engine.generators.guitarify import model, strings
from llamatron.model.schema import file_format
from llamatron.model.schema.file_format import Approach, ChordColor, GuitarifySetting, SingleNotes, StrumDirection, Tuning
from llamatron.model.schema.generator_views import ChoiceView, ColumnView, GeneratorView, GuitarBarView, NumberView, RestartView, ToggleView
from llamatron.user_strings import labels

MODE_NAMES = {model.GUITAR: strings.MSG_GUITAR_MODE, model.STRUM: strings.MSG_STRUM_MODE}
DIRECTION_NAMES = {
    StrumDirection.BY_THE_BEAT: strings.MSG_BY_THE_BEAT, StrumDirection.DOWN: strings.MSG_DOWN, StrumDirection.UP: strings.MSG_UP,
    StrumDirection.DOWN_UP: strings.MSG_DOWN_UP,
}

# What both modes share: how a strum's strings are spread, how they fade, how loose their timing is, and how many an upstroke catches.
SPREAD = NumberView(setting=GuitarifySetting.SPREAD, label=labels.MSG_GUITAR_SPREAD_LABEL, default=model.DEFAULT_GUITAR_SPREAD, shown=strings.MSG_MILLISECONDS)
FADE = NumberView(setting=GuitarifySetting.FADE, label=labels.MSG_GUITAR_FADE_LABEL, default=model.DEFAULT_GUITAR_FADE)
LOOSE_TIMING = NumberView(setting=GuitarifySetting.LOOSE_TIMING, label=labels.MSG_GUITAR_LOOSE_TIMING_LABEL, default=model.DEFAULT_GUITAR_LOOSE_TIMING)
UPSTROKE = NumberView(setting=GuitarifySetting.UPSTROKE, label=labels.MSG_GUITAR_UPSTROKE_LABEL, default=model.DEFAULT_GUITAR_UPSTROKE, zero_shown=strings.MSG_EVERY_STRING)

VIEW = GeneratorView(
    mode=ChoiceView(setting=GuitarifySetting.MODE, label=strings.MSG_MODE_LABEL, choices=tuple(model.MODES), default=model.DEFAULT_MODE, names=MODE_NAMES),
    columns=(
        ColumnView(heading=strings.MSG_STRUM_HEADING, modes=(model.STRUM,), settings=(
            ChoiceView(setting=GuitarifySetting.DIRECTION, label=strings.MSG_DIRECTION_LABEL, choices=tuple(model.DIRECTIONS), default=model.DEFAULT_DIRECTION, names=DIRECTION_NAMES),
            SPREAD, FADE, LOOSE_TIMING, UPSTROKE,
        )),
        ColumnView(heading=strings.MSG_LEFT_HAND_HEADING, modes=(model.GUITAR,), settings=(
            ToggleView(setting=GuitarifySetting.SHAPE, label=labels.MSG_GUITAR_SHAPE_LABEL, default=True),
            ChoiceView(setting=GuitarifySetting.TUNING, label=labels.MSG_GUITAR_TUNING_LABEL, choices=tuple(file_format.TUNINGS), default=Tuning.STANDARD, names=labels.MSG_GUITAR_TUNING_NAMES),
            NumberView(setting=GuitarifySetting.POSITION, label=labels.MSG_GUITAR_POSITION_LABEL, default=model.DEFAULT_GUITAR_POSITION, shown=strings.MSG_FRET, zero_shown=strings.MSG_OPEN_POSITION),
            NumberView(setting=GuitarifySetting.CAPO, label=labels.MSG_GUITAR_CAPO_LABEL, default=model.DEFAULT_GUITAR_CAPO, shown=strings.MSG_FRET, zero_shown=strings.MSG_NO_CAPO),
            NumberView(setting=GuitarifySetting.STRINGS, label=labels.MSG_GUITAR_STRINGS_LABEL, default=model.DEFAULT_GUITAR_STRINGS),
            ChoiceView(setting=GuitarifySetting.SINGLE_NOTES, label=labels.MSG_GUITAR_SINGLE_NOTES_LABEL, choices=tuple(file_format.SINGLE_NOTES), default=SingleNotes.LEAVE, names=labels.MSG_GUITAR_SINGLE_NOTES_NAMES),
            ChoiceView(setting=GuitarifySetting.COLOR, label=labels.MSG_GUITAR_COLOR_LABEL, choices=tuple(file_format.CHORD_COLORS), default=ChordColor.AS_WRITTEN, names=labels.MSG_GUITAR_COLOR_NAMES),
        )),
        ColumnView(heading=strings.MSG_RIGHT_HAND_HEADING, modes=(model.GUITAR,), settings=(
            ToggleView(setting=GuitarifySetting.STROKES, label=labels.MSG_GUITAR_STROKES_LABEL, default=True),
            GuitarBarView(label=labels.MSG_GUITAR_BAR_LABEL),
            ToggleView(setting=GuitarifySetting.LET_RING, label=labels.MSG_GUITAR_LET_RING_LABEL),
            SPREAD, FADE, LOOSE_TIMING, UPSTROKE,
            ChoiceView(setting=GuitarifySetting.APPROACH, label=labels.MSG_GUITAR_APPROACH_LABEL, choices=tuple(file_format.APPROACHES), default=Approach.OFF, names=labels.MSG_GUITAR_APPROACH_NAMES),
        )),
        ColumnView(heading=None, settings=(RestartView(),), under=True),
    ),
    help=strings.HELP_PAGE,
)
