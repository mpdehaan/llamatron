# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Each built-in engine as a preset of parts, the suggestion a sound starts from: its voice layer, its oscillators, its three
envelopes, its filter, its effects and its matrix. Choosing an engine fills every part from its preset; a part changed or
swapped afterwards is the sound's own. A part's setting left out is its preset's where the part is still the preset's type.

Basic is a polysynth: three oscillators through a ladder each note's own, snappy envelopes, velocity opening the filter. SID is
the home computer's chip: its own ADSR, no filter yet. Pocket is the handheld's chip: its stepped envelope, no filter. Fishline
is the acid bass: its oscillator, its accent gate, a short sweep into the diode, a drive, one voice sliding legato. Drum is the
drum machine, its hits rendered ahead.
"""

from llamatron.model.schema import defaults, file_format
from llamatron.model.schema.file_format import AcidWave, Curve, Effect, EffectSetting, EnvelopeType, FilterSharing, FilterType, MatrixDestination, MatrixSetting, MatrixSource, OscillatorType, PartSetting, SoundEngine, SoundPart, SoundSetting

# Fishline's Env Mod at full moved the cutoff three of four octaves, and its drive pushed a quarter as hard as the Drive effect.
ACID_ENV_SHARE = 0.75
ACID_DRIVE_SHARE = 0.25
# A pitch envelope of no amount, and an envelope that moves nothing: what Env3 is where nothing is pitched.
QUIET = {PartSetting.TYPE: EnvelopeType.ADSR, PartSetting.ATTACK: 0, PartSetting.HOLD: 0, PartSetting.DECAY: 10, PartSetting.SNAP: 0, PartSetting.SUSTAIN: 0,
         PartSetting.RELEASE: 10}
NO_FILTER = {PartSetting.TYPE: FilterType.NONE}
SWEEP = {PartSetting.TYPE: EnvelopeType.ADSR, PartSetting.ATTACK: 0, PartSetting.HOLD: 0, PartSetting.DECAY: defaults.DEFAULT_FILTER_DECAY_MS, PartSetting.SNAP: 0,
         PartSetting.SUSTAIN: 0, PartSetting.RELEASE: defaults.DEFAULT_FILTER_DECAY_MS}
# Velocity opens Basic's filter a little, harder notes brighter.
BRIGHTER_WHEN_HARD = 15

PRESETS = {
    SoundEngine.BASIC: {
        SoundSetting.VOICES: defaults.DEFAULT_VOICES, SoundSetting.LEGATO: False, SoundSetting.GLIDE: 0, SoundSetting.FILTER_SHARING: FilterSharing.PER_NOTE,
        SoundPart.OSCILLATORS: {PartSetting.TYPE: OscillatorType.BASIC},
        SoundPart.ENV1: {PartSetting.TYPE: EnvelopeType.ADSR},
        SoundPart.ENV2: {PartSetting.TYPE: EnvelopeType.ADSR, PartSetting.ATTACK: 0, PartSetting.DECAY: defaults.DEFAULT_ENVELOPE_DECAY, PartSetting.SUSTAIN: 20},
        SoundPart.ENV3: QUIET,
        SoundPart.FILTER: {PartSetting.TYPE: FilterType.LADDER},
        SoundSetting.EFFECTS: [],
        SoundSetting.MATRIX: [{MatrixSetting.SOURCE: MatrixSource.VELOCITY, MatrixSetting.VIA: MatrixSource.NONE, MatrixSetting.DESTINATION: MatrixDestination.CUTOFF,
                               MatrixSetting.AMOUNT: BRIGHTER_WHEN_HARD}],
    },
    SoundEngine.SID: {
        SoundSetting.VOICES: 1, SoundSetting.LEGATO: False, SoundSetting.GLIDE: 0, SoundSetting.FILTER_SHARING: FilterSharing.SHARED,
        SoundPart.OSCILLATORS: {PartSetting.TYPE: OscillatorType.SID},
        SoundPart.ENV1: {PartSetting.TYPE: EnvelopeType.SID_ADSR},
        SoundPart.ENV2: QUIET, SoundPart.ENV3: QUIET, SoundPart.FILTER: NO_FILTER, SoundSetting.EFFECTS: [], SoundSetting.MATRIX: [],
    },
    SoundEngine.POCKET: {
        SoundSetting.VOICES: 1, SoundSetting.LEGATO: False, SoundSetting.GLIDE: 0, SoundSetting.FILTER_SHARING: FilterSharing.SHARED,
        SoundPart.OSCILLATORS: {PartSetting.TYPE: OscillatorType.POCKET},
        SoundPart.ENV1: {PartSetting.TYPE: EnvelopeType.CHIP_STEPS},
        SoundPart.ENV2: QUIET, SoundPart.ENV3: QUIET, SoundPart.FILTER: NO_FILTER, SoundSetting.EFFECTS: [], SoundSetting.MATRIX: [],
    },
    SoundEngine.FISHLINE: {
        SoundSetting.VOICES: 1, SoundSetting.LEGATO: True, SoundSetting.GLIDE: defaults.DEFAULT_SLIDE_MS, SoundSetting.FILTER_SHARING: FilterSharing.PER_NOTE,
        SoundPart.OSCILLATORS: {PartSetting.TYPE: OscillatorType.ACID, PartSetting.ACID_WAVE: AcidWave.SAW},
        SoundPart.ENV1: {PartSetting.TYPE: EnvelopeType.ACID_GATE},
        SoundPart.ENV2: SWEEP, SoundPart.ENV3: QUIET,
        SoundPart.FILTER: {PartSetting.TYPE: FilterType.DIODE, PartSetting.CUTOFF: defaults.DEFAULT_ACID_CUTOFF, PartSetting.RESONANCE: defaults.DEFAULT_ACID_RESONANCE,
                      PartSetting.ENV_AMOUNT: round(defaults.DEFAULT_ENV_MOD * ACID_ENV_SHARE), PartSetting.KEY_TRACK: 0, PartSetting.DRIVE: 0},
        SoundSetting.EFFECTS: [{EffectSetting.EFFECT: Effect.DRIVE, EffectSetting.CURVE: Curve.SOFT, EffectSetting.AMOUNT: round(defaults.DEFAULT_ACID_DRIVE * ACID_DRIVE_SHARE)}],
        SoundSetting.MATRIX: [],
    },
    SoundEngine.DRUM: {
        SoundSetting.VOICES: 1, SoundSetting.LEGATO: False, SoundSetting.GLIDE: 0, SoundSetting.FILTER_SHARING: FilterSharing.SHARED,
        SoundPart.OSCILLATORS: {PartSetting.TYPE: OscillatorType.DRUM},
        SoundPart.ENV1: QUIET, SoundPart.ENV2: QUIET, SoundPart.ENV3: QUIET, SoundPart.FILTER: NO_FILTER, SoundSetting.EFFECTS: [], SoundSetting.MATRIX: [],
    },
}
# Which engine shows each oscillator type, as its parts are named on the page ("Oscillators: Fishline").
ENGINE_OF_OSCILLATOR = {OscillatorType.BASIC: SoundEngine.BASIC, OscillatorType.SID: SoundEngine.SID, OscillatorType.POCKET: SoundEngine.POCKET,
                        OscillatorType.ACID: SoundEngine.FISHLINE, OscillatorType.DRUM: SoundEngine.DRUM}


def preset_part(*, engine, part):
    """Return an engine's preset part, a mapping of its type and the settings it sets."""
    return PRESETS[engine][part]


def preset_value(*, engine, name):
    """Return one of an engine's preset's voice settings, or its effects or matrix."""
    return PRESETS[engine][name]


def engines_of_role(role):
    return file_format.ENGINES_OF_ROLE[role]
