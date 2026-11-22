# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Chords generator's page: its Mode, then the Progression column in Progression mode (Every, Chords) or the Follow column in
Follow Progression mode (Chords from), and in every mode the Voicing column (Voice leading, the octaves, the root in the bass)
and the generator's Restart."""

from llamatron.engine.generators.chords import model, strings
from llamatron.engine.generators.chords.model import ChordsSetting, ProgressionSetting
from llamatron.model.schema import file_format
from llamatron.model.schema.generator_views import ChoiceView, ColumnView, GeneratorView, OctaveView, ProgressionView, RestartView, TimeView, ToggleView, TrackView
from llamatron.user_strings import labels

MODE_NAMES = {model.VOICING: strings.MSG_VOICING_MODE, model.PROGRESSION: strings.MSG_PROGRESSION_MODE, model.FOLLOW_PROGRESSION: strings.MSG_FOLLOW_MODE}

VIEW = GeneratorView(
    mode=ChoiceView(setting=ChordsSetting.MODE, label=strings.MSG_MODE_LABEL, choices=tuple(model.MODES), default=model.DEFAULT_MODE, names=MODE_NAMES),
    columns=(
        ColumnView(heading=strings.MSG_PROGRESSION_HEADING, modes=(model.PROGRESSION,), settings=(
            TimeView(setting=ProgressionSetting.EVERY, label=labels.MSG_EVERY_LABEL, first=file_format.ONE_BAR_WRITTEN),
            ProgressionView(label=labels.MSG_CHORDS_LABEL),
        )),
        ColumnView(heading=strings.MSG_FOLLOW_HEADING, modes=(model.FOLLOW_PROGRESSION,), settings=(
            TrackView(setting=ChordsSetting.CHORDS_FROM, label=labels.MSG_CHORDS_FROM_LABEL),
        )),
        ColumnView(heading=strings.MSG_VOICING_HEADING, settings=(
            ToggleView(setting=ChordsSetting.VOICE_LEADING, label=strings.MSG_VOICE_LEADING_LABEL, by_mode={model.VOICING: True}),
            OctaveView(setting=ChordsSetting.LOWEST_OCTAVE, label=labels.MSG_LOWEST_OCTAVE_LABEL, default=model.DEFAULT_VOICING_LOWEST_OCTAVE),
            OctaveView(setting=ChordsSetting.HIGHEST_OCTAVE, label=labels.MSG_HIGHEST_OCTAVE_LABEL, default=model.DEFAULT_VOICING_HIGHEST_OCTAVE),
            ToggleView(setting=ChordsSetting.ROOT_IN_BASS, label=labels.MSG_ROOT_IN_BASS_LABEL),
            RestartView(),
        )),
    ),
    help=strings.HELP_PAGE,
)
