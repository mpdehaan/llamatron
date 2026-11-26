# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A Musician's page: the Player column (Instrument, Chords from for an instrument that plays pitches, Tune from, Activity), the
Touch column (Loudness and Looseness as gauges, Gives way once a tune track is named, Accents, Notes, and Range for an instrument
that plays pitches), and the table of what the musician does in each kind of section the song's scenes have."""

from llamatron.engine.generators.musician import model, schema, strings
from llamatron.engine.generators.musician.model import MusicianSetting
from llamatron.model.schema.generator_views import ChoiceView, ColumnView, GaugeView, GeneratorView, InheritedChoiceView, SectionsView, TrackView, WhenView
from llamatron.user_strings import labels, legends, marks


def _choice(*, setting, label, choices):
    """Return a choice of the musician's, left out of the file at what a musician does unasked."""
    return ChoiceView(setting=setting, label=label, choices=tuple(choices), default=model.MUSICIAN_DEFAULTS[setting])


def _from_instrument(*, setting, label, choices):
    """Return a choice the instrument makes until the musician is told otherwise."""
    return InheritedChoiceView(
        setting=setting, label=label, choices=tuple(choices), inherited_choice=labels.MSG_MUSICIAN_INSTRUMENT_CHOICE,
        inherited_shown=marks.MSG_FROM_INSTRUMENT_SHOWN, inherited_what=legends.MSG_FROM_INSTRUMENT_WHAT,
    )


VIEW = GeneratorView(
    columns=(
        ColumnView(heading=strings.MSG_PLAYER_HEADING, settings=(
            _choice(setting=MusicianSetting.INSTRUMENT, label=labels.MSG_MUSICIAN_INSTRUMENT_LABEL, choices=schema.INSTRUMENTS),
            WhenView(view=TrackView(setting=MusicianSetting.CHORDS_FROM, label=labels.MSG_CHORDS_FROM_LABEL), when=model.PLAYS_PITCHES),
            TrackView(setting=MusicianSetting.TUNE_FROM, label=labels.MSG_TUNE_FROM_LABEL),
            _choice(setting=MusicianSetting.ACTIVITY, label=labels.MSG_MUSICIAN_ACTIVITY_LABEL, choices=schema.ACTIVITIES),
        )),
        ColumnView(heading=strings.MSG_TOUCH_HEADING, settings=(
            GaugeView(
                setting=MusicianSetting.LOUDNESS, label=labels.MSG_MUSICIAN_LOUDNESS_LABEL, lowest=schema.QUIETEST, highest=schema.LOUDEST,
                default=model.MUSICIAN_DEFAULTS[MusicianSetting.LOUDNESS],
            ),
            GaugeView(
                setting=MusicianSetting.LOOSENESS, label=labels.MSG_MUSICIAN_LOOSENESS_LABEL, lowest=schema.TIGHT, highest=schema.LOOSEST,
                default=model.MUSICIAN_DEFAULTS[MusicianSetting.LOOSENESS],
            ),
            WhenView(view=_from_instrument(setting=MusicianSetting.GIVES_WAY, label=labels.MSG_MUSICIAN_GIVES_WAY_LABEL, choices=schema.GIVES_WAY), when=model.NAMES_A_TUNE),
            _choice(setting=MusicianSetting.ACCENTS, label=labels.MSG_MUSICIAN_ACCENTS_LABEL, choices=schema.ACCENTS),
            _from_instrument(setting=MusicianSetting.NOTES, label=labels.MSG_MUSICIAN_NOTES_LABEL, choices=schema.NOTE_LENGTHS),
            WhenView(view=_choice(setting=MusicianSetting.RANGE, label=labels.MSG_MUSICIAN_RANGE_LABEL, choices=schema.RANGES), when=model.PLAYS_PITCHES),
        )),
        ColumnView(heading=None, settings=(
            SectionsView(
                caption=strings.MSG_SECTIONS_CAPTION, plays=schema.PLAYS, plays_label=labels.MSG_MUSICIAN_PLAYS_LABEL, played=schema.PLAYED,
                played_label=labels.MSG_MUSICIAN_PLAYED_LABEL, played_choices=tuple(schema.FORMS), defaults=dict(model.MUSICIAN_SECTION_DEFAULTS),
            ),
        )),
    ),
    help=strings.HELP_PAGE,
)
