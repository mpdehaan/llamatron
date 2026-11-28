// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The filter parts of a voice's Filter slot, each a zero-delay-feedback model solved a sample at a time (the topology
//! preserving transform), so that the cutoff can sweep as fast as an envelope moves it with no step or blow-up:
//!
//! - Ladder: four one-pole stages in a loop, its feedback through a saturating input, stopping just short of
//!   self-oscillation at full resonance, as no filter here oscillates on its own, and thinning its bass as resonance
//!   rises, as the transistor ladder does; a slope of one to four poles taps an earlier stage, the feedback still from the last.
//! - Diode: the acid bass's ladder, its feedback weaker so that it stops short of oscillating and keeps its bass, driven
//!   harder before and soft-clipped after, its floor lowered a little by its Env amount as that circuit's is.
//! - OTA: the creamier ladder, a softer drive before it.
//! - Multimode: a state-variable filter, low, band, high or notch, its Q from the resonance.
//! - Sallen-Key: the resonant two-pole circuit (sallen_key.rs), low or high pass, two poles with a high-pass in its loop, Drive
//!   pushing the loop's saturation so that it screams, harder near full resonance, stopping short of self-oscillation.
//!
//! The cutoff is moved in octaves a sample by Env2 through the Env amount, key tracking and the mod matrix; its
//! coefficients are worked out again every `COEFFICIENT_STEP` samples, which no ear can hear as steps.

pub mod diode;
pub mod gate;
pub mod ladder;
pub mod multimode;
pub mod ota;
pub mod sallen_key;

use crate::dsp::oversample::Halfband;
use crate::dsp::saturation::SmoothTanh;
use crate::dsp::{flushed, HIGHEST_SHARE};
use crate::filters::diode::AcidFilterState;
#[cfg(test)]
use crate::filters::ladder::LadderUnit;
use crate::filters::ladder::{LadderSettings, LadderState};
use crate::filters::sallen_key::SallenKeyState;
use crate::protocol::values::{number, word};
use crate::registry::{self, Entry};
use rmpv::Value;
use std::f64::consts::PI;

pub const ENVELOPE_OCTAVES: f64 = 4.0;
const LOWEST_CUTOFF: f64 = 20.0;
const ENV_MOD_DIP: f64 = 0.5;
const OTA_FEEDBACK: f64 = 3.8;
const LOWEST_Q: f64 = 0.5;
const MOST_Q: f64 = 20.0;
const HIGH_SHARE: f64 = 0.3;
const HIGH_Q: f64 = 10.0;
const MOST_DRIVE: f64 = 10.0;
const DIODE_PUSH: f64 = 1.5;
const OTA_PUSH: f64 = 1.2;
const COEFFICIENT_STEP: usize = 4;
/// How much faster an oversampled filter runs, and the set Resonance past which a saturating filter is oversampled.
const OVERSAMPLED: f64 = 2.0;
const OVERSAMPLED_FROM_RESONANCE: f64 = 0.5;
/// How much of the bass Resonance thins the Ladder gives back unless set: most of it, so that a resonant bass keeps
/// its weight, a little of the circuit's own thinning still heard.
const DEFAULT_BASS_COMPENSATION: f64 = 0.8;
/// How many octaves Filter FM moves the cutoff at full, by the oscillator at full level.
const FM_OCTAVES: f64 = 2.0;

/// The Filter slot's name when it holds no filter.
pub const NO_FILTER: &str = "none";

/// What a registered filter is: one of the filters this module runs, or the low-pass gate, a part of its own
/// (`gate.rs`) that is the voice's filter and amp together.
pub enum Slot {
    Filter(FilterKind),
    Gate,
    /// The slot left empty: no filter.
    Empty,
}

/// Every filter, by the name a spec gives it, the file that holds it, and what it is.
pub static REGISTRY: &[Entry<Slot>] = &[
    Entry {
        name: NO_FILTER,
        file: "mod.rs",
        build: Slot::Empty,
    },
    Entry {
        name: "diode",
        file: "diode.rs",
        build: Slot::Filter(FilterKind::Diode),
    },
    Entry {
        name: "ladder",
        file: "ladder.rs",
        build: Slot::Filter(FilterKind::Ladder),
    },
    Entry {
        name: gate::LOW_PASS_GATE,
        file: "gate.rs",
        build: Slot::Gate,
    },
    Entry {
        name: "multimode",
        file: "multimode.rs",
        build: Slot::Filter(FilterKind::Multimode),
    },
    Entry {
        name: "ota",
        file: "ota.rs",
        build: Slot::Filter(FilterKind::Ota),
    },
    Entry {
        name: "sallen_key",
        file: "sallen_key.rs",
        build: Slot::Filter(FilterKind::SallenKey),
    },
];

/// The files of the filters' folder that are no filter of their own but a part one uses: none today.
pub const HELPERS: &[&str] = &[];

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FilterKind {
    Ladder,
    Diode,
    Ota,
    Multimode,
    SallenKey,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FilterMode {
    Low,
    Band,
    High,
    Notch,
}

/// A filter's settings, shared by every note that has its own.
#[derive(Clone, Copy, Debug)]
pub struct FilterPart {
    pub kind: FilterKind,
    pub mode: FilterMode,
    pub cutoff: f64,
    pub resonance: f64,
    pub amount: f64,
    pub key_track: f64,
    pub push: f64,
    /// The Ladder's own settings: its unit, seeded by the instrument, Drive, Bass compensation and slope.
    pub ladder: LadderSettings,
    pub poles: usize,
    /// How far the oscillator moves the Diode's cutoff, in octaves at full level: Filter FM, the classic modification.
    pub fm: f64,
    pub rate: f64,
    /// Whether it runs at twice the rate: a saturating filter pushed hard enough for its saturation to alias, by Drive or
    /// by a set Resonance past half, decided once as the instrument is compiled, so that its delay never changes mid-note.
    pub oversampled: bool,
    /// Whether its coefficients are worked out every sample, where the Mod Matrix moves its cutoff at audio rate, rather
    /// than every COEFFICIENT_STEP samples.
    pub every_sample: bool,
}

/// What a filter keeps from sample to sample: its stages' states, its coefficients and when they were worked out.
#[derive(Clone, Copy, Default, Debug)]
pub struct FilterState {
    stages: [f64; 4],
    g: f64,
    feedback: f64,
    countdown: usize,
    /// The Diode filter's own circuit, the acid bass's (acid.rs), made the first time it plays.
    acid: Option<AcidFilterState>,
    /// The Sallen-Key's circuit, its coefficients and sections.
    sallen_key: SallenKeyState,
    /// Twice the rate for a saturating filter pushed hard (FilterPart::oversampled).
    halfband: Halfband,
    /// Drive's curve, anti-aliased, at the rate the filter runs at.
    drive_curve: SmoothTanh,
    /// The Ladder's circuit.
    ladder: LadderState,
    /// The ladder's stages' last outputs, from which each stage's saturation is worked out for the next sample.
    outputs: [f64; 4],
}

impl FilterState {
    /// Seed what wanders slowly in the filter from the note's own random number, from -1 to 1.
    pub fn seed(&mut self, random: f64) {
        self.ladder.seed(random);
    }

    /// Back to rest, so that a runaway filter starts clean.
    pub fn reset(&mut self) {
        *self = FilterState::default();
    }
}

impl FilterPart {
    /// The filter a spec describes, or None for none or the low-pass gate.
    pub fn compiled(spec: &Value, rate: f64) -> Option<FilterPart> {
        // No filter, the low-pass gate (its own part), or a name no registry holds builds no filter here.
        let entry = registry::find(REGISTRY, word(spec, "type", NO_FILTER))?;
        let Slot::Filter(kind) = entry.build else { return None };
        let mode = match word(spec, "mode", "low") {
            "band" if kind == FilterKind::Multimode => FilterMode::Band,
            "notch" if kind == FilterKind::Multimode => FilterMode::Notch,
            "high" if !matches!(kind, FilterKind::Ladder | FilterKind::Diode | FilterKind::Ota) => FilterMode::High,
            _ => FilterMode::Low,
        };
        let mut amount = number(spec, "env_amount", 0.0);
        let mut cutoff = number(spec, "cutoff", 1200.0);
        if kind == FilterKind::Diode {
            // The acid bass's measured mapping: the Env amount sets how far the envelope sweeps, and lowers where the
            // sweep starts, by the cutoff's place in the circuit's range; an amount below zero closes the filter instead.
            if amount >= 0.0 {
                let (scale, offset) = diode::envelope_mapping(cutoff, amount);
                cutoff *= 2f64.powf(-scale * offset);
                amount = scale / ENVELOPE_OCTAVES;
            } else {
                cutoff *= 2f64.powf(-ENV_MOD_DIP * amount.abs());
            }
        }
        let mut push = 1.0 + number(spec, "drive", 0.0) * MOST_DRIVE;
        match kind {
            FilterKind::Diode => push *= DIODE_PUSH,
            FilterKind::Ota => push *= OTA_PUSH,
            _ => {}
        }
        let resonance = number(spec, "resonance", 0.0).clamp(0.0, 1.0);
        let poles = (number(spec, "poles", 4.0) as usize).clamp(1, 4);
        let saturates = matches!(kind, FilterKind::Ladder | FilterKind::Ota | FilterKind::SallenKey);
        let driven = number(spec, "drive", 0.0) > 0.0;
        // Drive's curve makes harmonics far above the note, so any driven filter runs it at twice the rate or more.
        // The Ladder's circuit runs at four times the rate always, and the Diode's at its own.
        let oversampled = kind != FilterKind::Ladder && ((saturates && resonance > OVERSAMPLED_FROM_RESONANCE) || (driven && kind != FilterKind::Diode));
        Some(FilterPart {
            kind,
            mode,
            cutoff,
            resonance,
            amount,
            key_track: number(spec, "key_track", 0.0),
            push,
            ladder: LadderSettings::new(number(spec, "drive", 0.0), number(spec, "bass_compensation", DEFAULT_BASS_COMPENSATION), poles),
            poles,
            fm: number(spec, "filter_fm", 0.0) * FM_OCTAVES,
            rate,
            oversampled,
            every_sample: false,
        })
    }

    /// How many samples its coefficients last: one where its cutoff moves at audio rate, else COEFFICIENT_STEP.
    fn coefficient_step(&self) -> usize {
        if self.every_sample {
            1
        } else {
            COEFFICIENT_STEP
        }
    }

    /// The rate it runs at: twice the instrument's where it is oversampled.
    fn running_rate(&self) -> f64 {
        if self.oversampled {
            OVERSAMPLED * self.rate
        } else {
            self.rate
        }
    }

    fn is_ladder(&self) -> bool {
        matches!(self.kind, FilterKind::Ladder | FilterKind::Diode | FilterKind::Ota)
    }

    /// One sample through the filter, its cutoff moved by octaves and its resonance by a share.
    #[inline]
    pub fn process(&self, state: &mut FilterState, input: f64, octaves: f64, resonance_moved: f64) -> f64 {
        if self.kind == FilterKind::Diode {
            return self.acid(state, input, octaves, resonance_moved);
        }
        if self.kind == FilterKind::Ladder {
            return self.transistor_ladder(state, input, octaves, resonance_moved);
        }
        if self.kind == FilterKind::SallenKey {
            if !self.oversampled {
                return self.sallen_key(state, input, octaves, resonance_moved);
            }
            // Twice the rate, so that the loop's saturation does not fold its harmonics back down.
            let (first, second) = state.halfband.up(input);
            let first = self.sallen_key(state, first, octaves, resonance_moved);
            let second = self.sallen_key(state, second, octaves, resonance_moved);
            return state.halfband.down(first, second);
        }
        if state.countdown == 0 {
            self.prepare(state, octaves, resonance_moved);
            state.countdown = self.coefficient_step();
        }
        state.countdown -= 1;
        let out = if self.oversampled {
            // Twice the rate, so that Drive's curve and the saturating stages do not fold their harmonics back down.
            let (first, second) = state.halfband.up(input);
            let first = self.driven(state, first);
            let first = self.core(state, first);
            let second = self.driven(state, second);
            let second = self.core(state, second);
            state.halfband.down(first, second)
        } else {
            let driven = self.driven(state, input);
            self.core(state, driven)
        };
        for stage in state.stages.iter_mut().chain(state.outputs.iter_mut()) {
            *stage = flushed(*stage);
        }
        out
    }

    /// A sample pushed through Drive's curve, kept at full scale; untouched without Drive.
    #[inline]
    fn driven(&self, state: &mut FilterState, input: f64) -> f64 {
        if self.push != 1.0 {
            state.drive_curve.process(input * self.push) / self.push.tanh()
        } else {
            input
        }
    }

    /// A sample through the ladder or the state-variable filter, at the rate the filter runs at.
    #[inline]
    fn core(&self, state: &mut FilterState, input: f64) -> f64 {
        if self.is_ladder() {
            self.ota_stages(state, input)
        } else {
            self.state_variable(state, input)
        }
    }

    /// The Ladder: the transistor ladder's circuit (ladder.rs), its coefficients worked out again every COEFFICIENT_STEP
    /// samples as the cutoff moves.
    #[inline]
    fn transistor_ladder(&self, state: &mut FilterState, input: f64, octaves: f64, resonance_moved: f64) -> f64 {
        if state.countdown == 0 {
            let cutoff = self.cutoff * 2f64.powf(octaves);
            let resonance = (self.resonance + resonance_moved).clamp(0.0, 1.0);
            let step = self.coefficient_step();
            state.ladder.prepare(&self.ladder, cutoff, resonance, self.rate, step);
            state.countdown = step;
        }
        state.countdown -= 1;
        state.ladder.process(&self.ladder, input, self.rate)
    }

    /// The Diode filter: the acid bass's own circuit after Open303 (acid.rs), its input pushed by Drive, its coefficients
    /// worked out again every COEFFICIENT_STEP samples as the cutoff moves.
    #[inline]
    fn acid(&self, state: &mut FilterState, input: f64, octaves: f64, resonance_moved: f64) -> f64 {
        let acid = state.acid.get_or_insert_with(|| AcidFilterState::new(self.rate));
        // Filter FM moves the cutoff at the audio's own rate, so its coefficients are worked out every sample.
        if state.countdown == 0 || self.fm != 0.0 {
            let cutoff = self.cutoff * 2f64.powf(octaves + self.fm * input);
            let resonance = (self.resonance + resonance_moved).clamp(0.0, 1.0);
            acid.prepare(cutoff, resonance, self.rate);
            state.countdown = self.coefficient_step();
        }
        state.countdown -= 1;
        // Drive's curve runs inside the circuit's own four times the rate, so that its harmonics are filtered away.
        acid.process(input, self.push)
    }

    /// The Sallen-Key: the resonant two-pole circuit (sallen_key.rs), Drive pushing its loop's saturation rather than its input, as
    /// the circuit screams when its loop is driven; its coefficients worked out again every COEFFICIENT_STEP samples.
    #[inline]
    fn sallen_key(&self, state: &mut FilterState, input: f64, octaves: f64, resonance_moved: f64) -> f64 {
        let form = if self.mode == FilterMode::High {
            sallen_key::Form::High
        } else {
            sallen_key::Form::Low
        };
        if state.countdown == 0 {
            let cutoff = (self.cutoff * 2f64.powf(octaves)).clamp(LOWEST_CUTOFF, HIGHEST_SHARE * self.rate);
            let resonance = (self.resonance + resonance_moved).clamp(0.0, 1.0);
            state.sallen_key.prepare(form, cutoff, resonance, self.running_rate());
            state.countdown = self.coefficient_step();
        }
        state.countdown -= 1;
        let out = match form {
            sallen_key::Form::Low => state.sallen_key.low(input, self.push),
            sallen_key::Form::High => state.sallen_key.high(input, self.push),
        };
        state.sallen_key.flush(flushed);
        out
    }

    fn prepare(&self, state: &mut FilterState, octaves: f64, resonance_moved: f64) {
        let cutoff = (self.cutoff * 2f64.powf(octaves)).clamp(LOWEST_CUTOFF, HIGHEST_SHARE * self.rate);
        state.g = (PI * cutoff / self.running_rate()).tan();
        let resonance = (self.resonance + resonance_moved).clamp(0.0, 1.0);
        state.feedback = match self.kind {
            // The Ladder runs its own circuit (ladder.rs), never the shared ladder.
            FilterKind::Ladder => 0.0,
            // The Diode filter runs its own circuit (acid), never the shared ladder.
            FilterKind::Diode => 0.0,
            FilterKind::Ota => OTA_FEEDBACK * resonance,
            // The Sallen-Key runs its own circuit (sallen_key), never the state-variable filter.
            FilterKind::SallenKey => 0.0,
            FilterKind::Multimode => {
                let mut quality = LOWEST_Q + resonance * MOST_Q;
                if cutoff > HIGH_SHARE * self.rate {
                    quality = quality.min(HIGH_Q);
                }
                1.0 / quality
            }
        };
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn part(kind: &str, resonance: f64) -> FilterPart {
        let spec = Value::Map(vec![
            ("type".into(), kind.into()),
            ("cutoff".into(), 1000.0.into()),
            ("resonance".into(), resonance.into()),
        ]);
        FilterPart::compiled(&spec, 48000.0).unwrap()
    }

    /// A filter of a kind at a Resonance, a Drive and a cutoff.
    fn part_at(kind: &str, resonance: f64, drive: f64, cutoff: f64) -> FilterPart {
        let spec = Value::Map(vec![
            ("type".into(), kind.into()),
            ("cutoff".into(), cutoff.into()),
            ("resonance".into(), resonance.into()),
            ("drive".into(), drive.into()),
        ]);
        FilterPart::compiled(&spec, 48000.0).unwrap()
    }

    fn loudness(filter: &FilterPart, frequency: f64) -> f64 {
        let mut state = FilterState::default();
        let mut peak: f64 = 0.0;
        for place in 0..48000 {
            let out = filter.process(&mut state, 0.1 * (2.0 * PI * frequency * place as f64 / 48000.0).sin(), 0.0, 0.0);
            if place > 24000 {
                peak = peak.max(out.abs());
            }
        }
        peak / 0.1
    }

    #[test]
    fn a_ladder_passes_the_bass_and_cuts_four_poles_an_octave_above() {
        let ladder = part("ladder", 0.0);
        assert!(loudness(&ladder, 100.0) > 0.9);
        assert!(loudness(&ladder, 8000.0) < 0.01);
    }

    /// No filter self-oscillates at any setting: at full Resonance and full Drive an impulse's ringing dies away, and
    /// silence stays silent (`.claude/rules/SYNTHS.md`).
    #[test]
    fn no_filter_rings_on_by_itself() {
        let rate = 48000;
        let dies_within = 2 * rate;
        for kind in REGISTRY.iter().filter(|entry| matches!(entry.build, Slot::Filter(_))).map(|entry| entry.name) {
            for cutoff in [80.0, 1000.0, 8000.0] {
                let filter = part_at(kind, 1.0, 1.0, cutoff);
                let mut state = FilterState::default();
                let mut late: f64 = 0.0;
                for place in 0..dies_within + rate / 4 {
                    let input = if place == 0 { 1.0 } else { 0.0 };
                    let out = filter.process(&mut state, input, 0.0, 0.0);
                    if place > dies_within {
                        late = late.max(out.abs());
                    }
                }
                assert!(late < 1e-4, "{kind} at {cutoff} Hz still rings: {late}");
                let mut quiet = FilterState::default();
                let silent = (0..rate).all(|_| filter.process(&mut quiet, 0.0, 0.0, 0.0) == 0.0);
                assert!(silent, "{kind} at {cutoff} Hz sounds from silence");
            }
        }
    }

    #[test]
    fn every_filter_stays_finite_under_a_wild_sweep() {
        for kind in REGISTRY.iter().filter(|entry| matches!(entry.build, Slot::Filter(_))).map(|entry| entry.name) {
            let filter = part(kind, 1.0);
            let mut state = FilterState::default();
            for place in 0..48000 {
                let octaves = 8.0 * (place as f64 / 300.0).sin();
                let out = filter.process(&mut state, (place as f64 * 0.37).sin(), octaves, 0.0);
                assert!(out.is_finite() && out.abs() < 16.0, "{kind}");
            }
        }
    }

    /// A ladder's stages saturate: a sine near the cutoff loud comes out less than ten times as loud as it quiet.
    #[test]
    fn a_ladder_squashes_a_loud_sine() {
        let ladder = part("ladder", 0.5);
        let level = |amplitude: f64| {
            let mut state = FilterState::default();
            (0..48_000)
                .map(|place| {
                    ladder
                        .process(&mut state, amplitude * (2.0 * PI * 900.0 * place as f64 / 48_000.0).sin(), 0.0, 0.0)
                        .abs()
                })
                .skip(24_000)
                .fold(0.0_f64, f64::max)
        };
        let (quiet, loud) = (0.05, 0.5);
        assert!(level(loud) < 9.5 * level(quiet), "{} against {}", level(loud), level(quiet));
    }

    /// The state-variable filter's band integrator saturates: at full resonance a loud sine at its cutoff stays within a
    /// few times full scale, while a quiet one still rings up its peak.
    #[test]
    fn a_multimode_peak_is_held_round_when_loud() {
        let multimode = part("multimode", 1.0);
        let peak = |amplitude: f64| {
            let mut state = FilterState::default();
            (0..48_000)
                .map(|place| {
                    multimode
                        .process(&mut state, amplitude * (2.0 * PI * 1000.0 * place as f64 / 48_000.0).sin(), 0.0, 0.0)
                        .abs()
                })
                .fold(0.0_f64, f64::max)
        };
        let (quiet, loud) = (0.01, 1.0);
        assert!(peak(quiet) / quiet > 2.0, "a quiet sine still rings up");
        assert!(peak(loud) < 4.0, "{}", peak(loud));
    }

    /// Drive's curve runs inside each filter's oversampling and is anti-aliased: a loud 5 kHz sine through a fully driven
    /// filter comes out with its stray tones well under its harmonics. The Sallen-Key, whose Drive pushes its loop, is
    /// held by its own rebuild.
    #[test]
    fn a_driven_filter_folds_little_back_on_a_high_note() {
        use crate::dsp::spectrum::stray_decibels;
        let hertz = 5_003;
        let rate = 48_000;
        for (kind, most_stray) in [("ladder", -40.0), ("ota", -40.0), ("multimode", -40.0), ("diode", -30.0)] {
            let filter = part_at(kind, 0.6, 1.0, 9000.0);
            let mut state = FilterState::default();
            let tone = |place: usize| 0.9 * (2.0 * PI * hertz as f64 * place as f64 / rate as f64).sin();
            let out: Vec<f32> = (0..2 * rate).map(|place| filter.process(&mut state, tone(place), 0.0, 0.0) as f32).collect();
            let stray = stray_decibels(&out, rate, hertz);
            assert!(stray < most_stray, "{kind}: {stray:.1} dB");
        }
    }
    /// A Ladder's level in decibels for a quiet sine at a frequency, at a Resonance and a Bass compensation.
    fn ladder_level(frequency: f64, resonance: f64, compensation: f64) -> f64 {
        let spec = Value::Map(vec![
            ("type".into(), "ladder".into()),
            ("cutoff".into(), 1000.0.into()),
            ("resonance".into(), resonance.into()),
            ("bass_compensation".into(), compensation.into()),
        ]);
        let filter = FilterPart::compiled(&spec, 48000.0).expect("a ladder");
        20.0 * loudness(&filter, frequency).log10()
    }

    /// Resonance thins the Ladder's bass as the circuit's does, by 1/(1 + k), and full Bass compensation gives it back.
    #[test]
    fn bass_compensation_gives_back_the_bass_resonance_thins() {
        let bass = 100.0;
        let resonance = 0.9;
        let kept = ladder_level(bass, resonance, 1.0);
        let thinned = ladder_level(bass, resonance, 0.0);
        assert!(kept.abs() < 1.5, "kept at {kept:.1} dB");
        assert!(thinned < -9.0, "thinned to {thinned:.1} dB");
    }

    /// A Ladder's even harmonics come from its unit's offsets: a sine through a driven Ladder of a seeded unit has a second
    /// harmonic, and one through a perfectly matched unit has none.
    #[test]
    fn a_ladders_unit_gives_it_even_harmonics() {
        use crate::dsp::spectrum::harmonic_decibels;
        let hertz = 200;
        let second = |unit: LadderUnit| {
            let mut filter = part_at("ladder", 0.3, 0.5, 4000.0);
            filter.ladder.unit = unit;
            let mut state = FilterState::default();
            let out: Vec<f32> = (0..96_000)
                .map(|place| filter.process(&mut state, 0.5 * (2.0 * PI * hertz as f64 * place as f64 / 48000.0).sin(), 0.0, 0.0) as f32)
                .collect();
            harmonic_decibels(&out, 48_000, hertz, 2)
        };
        let matched = LadderUnit::matched();
        assert!(second(LadderUnit::seeded(1)) > -70.0, "a unit's own second harmonic");
        assert!(second(matched) < -100.0, "a matched unit has none");
    }

    /// A sine's third harmonic through an undriven-to-driven Ladder, in decibels under the sine.
    fn ladder_grit(drive: f64) -> f64 {
        use crate::dsp::spectrum::harmonic_decibels;
        let hertz = 100;
        let filter = part_at("ladder", 0.0, drive, 6000.0);
        let mut state = FilterState::default();
        let tone = |place: usize| 0.5 * (2.0 * PI * hertz as f64 * place as f64 / 48000.0).sin();
        let out: Vec<f32> = (0..96_000).map(|place| filter.process(&mut state, tone(place), 0.0, 0.0) as f32).collect();
        harmonic_decibels(&out, 48_000, hertz, 3)
    }

    /// The Ladder's grit rises with Drive at every quarter turn of the knob.
    #[test]
    fn ladder_grit_rises_with_drive() {
        let grits: Vec<f64> = [0.0, 0.25, 0.5, 0.75, 1.0].iter().map(|drive| ladder_grit(*drive)).collect();
        assert!(grits.windows(2).all(|pair| pair[1] > pair[0]), "{grits:?}");
    }

    /// The Ladder's resonant peak stands out at a moderate level, not only a quiet one: through full Resonance the
    /// harmonic of a saw at half of full scale nearest the cutoff stands well above the note itself.
    #[test]
    fn a_ladders_peak_stands_out_at_a_moderate_level() {
        use crate::dsp::spectrum::harmonic_decibels;
        let hertz = 110;
        let near_cutoff = 9;
        let filter = part_at("ladder", 1.0, 0.0, 1000.0);
        let mut state = FilterState::default();
        let saw = |place: usize| 0.5 * (2.0 * ((place as f64 * hertz as f64 / 48000.0).fract()) - 1.0);
        let out: Vec<f32> = (0..96_000).map(|place| filter.process(&mut state, saw(place), 0.0, 0.0) as f32).collect();
        let peak = harmonic_decibels(&out, 48_000, hertz, near_cutoff);
        assert!(peak > 8.0, "{peak:.1} dB over the note");
    }
}
