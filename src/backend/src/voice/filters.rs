// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The filter parts of a voice's Filter slot, each a zero-delay-feedback model solved a sample at a time (the topology
//! preserving transform), so that the cutoff can sweep as fast as an envelope moves it with no step or blow-up:
//!
//! - Ladder: four one-pole stages in a loop, its feedback through a saturating input, so that it self-oscillates at full
//!   resonance into a clean sine bounded by the saturation, and thins its bass as resonance rises, as the transistor
//!   ladder does; a slope of one to four poles taps an earlier stage, the feedback still from the last.
//! - Diode: the acid bass's ladder, its feedback weaker so that it stops short of oscillating and keeps its bass, driven
//!   harder before and soft-clipped after, its floor lowered a little by its Env amount as that circuit's is.
//! - OTA: the creamier ladder, a softer drive before it.
//! - Multimode: a state-variable filter, low, band, high or notch, its Q from the resonance.
//! - Sallen-Key: the resonant two-pole circuit (sallen_key.rs), low or high pass, two poles with a high-pass in its loop, Drive
//!   pushing the loop's saturation so that it screams, harder near full resonance, stopping short of self-oscillation.
//!
//! The cutoff is moved in octaves a sample by Env2 through the Env amount, key tracking and the mod matrix; its
//! coefficients are worked out again every `COEFFICIENT_STEP` samples, which no ear can hear as steps.

use crate::dsp::{flushed, HIGHEST_SHARE};
use crate::protocol::values::{number, word};
use crate::voice::acid::{self, AcidFilterState};
use crate::voice::sallen_key::{self, SallenKeyState};
use rmpv::Value;
use std::f64::consts::PI;

pub const ENVELOPE_OCTAVES: f64 = 4.0;
const LOWEST_CUTOFF: f64 = 20.0;
const ENV_MOD_DIP: f64 = 0.5;
/// The ladder's loop gain at full resonance: just past four, where the loop oscillates, held by the saturation.
const LADDER_FEEDBACK: f64 = 4.1;
const OTA_FEEDBACK: f64 = 3.8;
const LOWEST_Q: f64 = 0.5;
const MOST_Q: f64 = 20.0;
const HIGH_SHARE: f64 = 0.3;
const HIGH_Q: f64 = 10.0;
const MOST_DRIVE: f64 = 10.0;
const DIODE_PUSH: f64 = 1.5;
const OTA_PUSH: f64 = 1.2;
const COEFFICIENT_STEP: usize = 4;
/// Where the soft limit reaches one and holds.
const SOFT_LIMIT_END: f64 = 3.0;
/// The least a stage's saturation may slow it, so that a very loud stage never stops.
const LEAST_SQUASH: f64 = 0.01;
/// The feedback past which the ladder is near self-oscillation, and the level of the noise that lets it ring up there,
/// 120 dB under full scale.
const RINGS_FROM_FEEDBACK: f64 = 3.8;
const NOISE_FLOOR: f64 = 1e-6;
/// How many octaves Filter FM moves the cutoff at full, by the oscillator at full level.
const FM_OCTAVES: f64 = 2.0;

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
    pub poles: usize,
    /// How far the oscillator moves the Diode's cutoff, in octaves at full level: Filter FM, the classic modification.
    pub fm: f64,
    pub rate: f64,
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
    /// The ladder's stages' last outputs, from which each stage's saturation is worked out for the next sample.
    outputs: [f64; 4],
    /// The seeded noise under a filter near self-oscillation, so that it rings up from silence; the same every playing.
    noise: u64,
}

/// A soft limit close to tanh and far cheaper, x(27 + x²)/(27 + 9x²), held at its ends past three, where it reaches one.
// After stmlib's SoftLimit (stmlib/dsp/dsp.h, Emilie Gillet, MIT); the implementation here is our own.
#[inline]
fn soft_limit(x: f64) -> f64 {
    let held = x.clamp(-SOFT_LIMIT_END, SOFT_LIMIT_END);
    let square = held * held;
    held * (27.0 + square) / (27.0 + 9.0 * square)
}

/// What a stage's saturation scales its gain by: soft_limit(y)/y, worked out without the division, never under
/// LEAST_SQUASH.
#[inline]
fn soft_squash(y: f64) -> f64 {
    if y.abs() >= SOFT_LIMIT_END {
        return (1.0 / y.abs()).max(LEAST_SQUASH);
    }
    let square = y * y;
    (27.0 + square) / (27.0 + 9.0 * square)
}

/// White noise from -1 to 1, a xorshift a sample, seeded the same every playing.
#[inline]
fn noise(state: &mut u64) -> f64 {
    if *state == 0 {
        *state = 0x2545_F491_4F6C_DD1D;
    }
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    (*state >> 11) as f64 / (1u64 << 52) as f64 - 1.0
}

impl FilterState {
    /// Back to rest, so that a runaway filter starts clean.
    pub fn reset(&mut self) {
        *self = FilterState::default();
    }
}

impl FilterPart {
    /// The filter a spec describes, or None for none or the low-pass gate.
    pub fn compiled(spec: &Value, rate: f64) -> Option<FilterPart> {
        let kind = match word(spec, "type", "none") {
            "ladder" => FilterKind::Ladder,
            "diode" => FilterKind::Diode,
            "ota" => FilterKind::Ota,
            "multimode" => FilterKind::Multimode,
            "sallen_key" => FilterKind::SallenKey,
            _ => return None,
        };
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
                let (scale, offset) = acid::envelope_mapping(cutoff, amount);
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
        Some(FilterPart {
            kind,
            mode,
            cutoff,
            resonance: number(spec, "resonance", 0.0).clamp(0.0, 1.0),
            amount,
            key_track: number(spec, "key_track", 0.0),
            push,
            poles: (number(spec, "poles", 4.0) as usize).clamp(1, 4),
            fm: number(spec, "filter_fm", 0.0) * FM_OCTAVES,
            rate,
        })
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
        if self.kind == FilterKind::SallenKey {
            return self.sallen_key(state, input, octaves, resonance_moved);
        }
        if state.countdown == 0 {
            self.prepare(state, octaves, resonance_moved);
            state.countdown = COEFFICIENT_STEP;
        }
        state.countdown -= 1;
        let driven = if self.push != 1.0 {
            (input * self.push).tanh() / self.push.tanh()
        } else {
            input
        };
        let out = if self.is_ladder() {
            // Near self-oscillation a seeded noise far under hearing lets the loop ring up from silence, as a circuit's
            // does.
            let floor = if state.feedback > RINGS_FROM_FEEDBACK {
                NOISE_FLOOR * noise(&mut state.noise)
            } else {
                0.0
            };
            self.ladder(state, driven + floor)
        } else {
            self.state_variable(state, driven)
        };
        for stage in state.stages.iter_mut().chain(state.outputs.iter_mut()) {
            *stage = flushed(*stage);
        }
        self.finished(out, resonance_moved)
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
            state.countdown = COEFFICIENT_STEP;
        }
        state.countdown -= 1;
        let driven = if self.push != 1.0 {
            (input * self.push).tanh() / self.push.tanh()
        } else {
            input
        };
        acid.process(driven)
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
            state.sallen_key.prepare(form, cutoff, resonance, self.rate);
            state.countdown = COEFFICIENT_STEP;
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
        state.g = (PI * cutoff / self.rate).tan();
        let resonance = (self.resonance + resonance_moved).clamp(0.0, 1.0);
        state.feedback = match self.kind {
            FilterKind::Ladder => LADDER_FEEDBACK * resonance,
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

    /// The ladder: the loop solved for its input without delay, the input saturated, then the four stages run, each
    /// saturating too: each stage's gain is scaled by tanh(y)/y of its last output, so that a loud stage slows as a
    /// transistor pair does, and the zero-delay solve takes each stage's own share.
    // The stages' saturation after the linearised tanh of VCV Fundamental's VCF (VCVRack/Fundamental, src/VCF.cpp,
    // GPL-3.0-or-later), folded into our own zero-delay ladder, its tanh stmlib's soft limit; the implementation is ours.
    #[inline]
    fn ladder(&self, state: &mut FilterState, input: f64) -> f64 {
        let g = state.g;
        let mut shares = [0.0; 4];
        let mut rests = [0.0; 4];
        for (place, last) in state.outputs.iter().enumerate() {
            let squash = soft_squash(*last);
            let stage_g = g * squash;
            let rest = 1.0 / (1.0 + stage_g);
            rests[place] = rest;
            shares[place] = stage_g * rest;
        }
        let [s1, s2, s3, s4] = state.stages;
        let [g1, g2, g3, g4] = shares;
        let carried = g4 * g3 * g2 * rests[0] * s1 + g4 * g3 * rests[1] * s2 + g4 * rests[2] * s3 + rests[3] * s4;
        let all = g1 * g2 * g3 * g4;
        let k = state.feedback;
        let solved = (input - k * carried) / (1.0 + k * all);
        let mut signal = soft_limit(solved);
        let mut taps = [0.0; 4];
        for place in 0..4 {
            let stage = &mut state.stages[place];
            let moved = (signal - *stage) * shares[place];
            let out = moved + *stage;
            *stage = out + moved;
            signal = out;
            taps[place] = out;
        }
        state.outputs = taps;
        taps[self.poles - 1]
    }

    /// The state-variable filter (two integrators), its damping the stored feedback, its output by the mode.
    #[inline]
    fn state_variable(&self, state: &mut FilterState, input: f64) -> f64 {
        let g = state.g;
        let damping = state.feedback;
        let [first, second, _, _] = state.stages;
        let high = (input - (damping + g) * first - second) / (1.0 + damping * g + g * g);
        let band = g * high + first;
        let low = g * band + second;
        state.stages[0] = g * high + band;
        state.stages[1] = g * band + low;
        match self.mode {
            FilterMode::Low => low,
            FilterMode::Band => band * damping,
            FilterMode::High => high,
            FilterMode::Notch => input - band * damping,
        }
    }

    /// The output finished as its circuit does: the ladder's bass partly made up.
    #[inline]
    fn finished(&self, out: f64, resonance_moved: f64) -> f64 {
        let resonance = (self.resonance + resonance_moved).clamp(0.0, 1.0);
        match self.kind {
            FilterKind::Ladder => out * (1.0 + 0.5 * 3.95 * resonance),
            _ => out,
        }
    }
}

const CELL_POWER: f64 = 1.4;
const LIT_OHMS: f64 = 5000.0;
const DARK_OHMS: f64 = 1.0e7;
const DIVIDER_OHMS: f64 = 10000.0;
const LEAST_GATE_Q: f64 = 0.5;
const MOST_GATE_Q: f64 = 25.0;
const PING_LEVEL: f64 = 0.45;
const MIDDLE_C: f64 = 60.0;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum GateMode {
    Vca,
    Lowpass,
    Both,
}

/// What the gate reads of its note at one sample: Env1's light from 0 to about 1, how many samples into the note, its
/// pitch and level, and the cutoff moved in octaves.
#[derive(Clone, Copy)]
pub struct GateNote {
    pub light: f64,
    pub place: f64,
    pub pitch: f64,
    pub level: f64,
    pub octaves: f64,
}

/// The low-pass gate: one photoresistor, lit by Env1, sets both loudness and cutoff, never two envelopes. VCA is loudness
/// alone; Lowpass the cutoff alone through a resonant two-pole, so that a falling cutoff rings a pitch that drops as the
/// gate closes; Both loudness and a one-pole's cutoff together, the classic pluck. The Input feeds it the oscillator, a ping
/// alone (a short strike each note rung through the gate), or both; key tracking moves its open cutoff with the note, so
/// that a pinged gate plays in tune.
#[derive(Clone, Copy, Debug)]
pub struct GatePart {
    pub mode: GateMode,
    damping: f64,
    open: f64,
    key_track: f64,
    pub feeds_oscillator: bool,
    feeds_ping: bool,
    ping_samples: f64,
    rate: f64,
}

impl GatePart {
    pub fn compiled(spec: &Value, rate: f64) -> Option<GatePart> {
        if word(spec, "type", "none") != "low_pass_gate" {
            return None;
        }
        let mode = match word(spec, "mode", "both") {
            "vca" => GateMode::Vca,
            "lowpass" => GateMode::Lowpass,
            _ => GateMode::Both,
        };
        let input = word(spec, "input", "oscillator");
        let resonance = number(spec, "resonance", 0.0).clamp(0.0, 1.0);
        Some(GatePart {
            mode,
            damping: 1.0 / (LEAST_GATE_Q + resonance * (MOST_GATE_Q - LEAST_GATE_Q)),
            open: number(spec, "open", 8000.0),
            key_track: number(spec, "key_track", 0.0),
            feeds_oscillator: input != "ping",
            feeds_ping: input != "oscillator",
            ping_samples: number(spec, "ping_width", 0.002) * rate,
            rate,
        })
    }

    /// One sample through the gate: the oscillator's sample, the light from 0 to about 1, how many samples into its note,
    /// the note's pitch and level, and the cutoff moved in octaves.
    #[inline]
    pub fn process(&self, state: &mut FilterState, input: f64, note: GateNote) -> f64 {
        let GateNote {
            light,
            place,
            pitch,
            level,
            octaves,
        } = note;
        let mut source = if self.feeds_oscillator { input } else { 0.0 };
        if self.feeds_ping && place >= 0.0 && place < self.ping_samples {
            source += PING_LEVEL * level;
        }
        let conductance = light.max(0.0).powf(CELL_POWER) / LIT_OHMS + 1.0 / DARK_OHMS;
        if self.mode == GateMode::Vca {
            return source * gain(conductance);
        }
        if state.countdown == 0 {
            let opened = self.open * 2f64.powf(self.key_track * (pitch - MIDDLE_C) / 12.0);
            let cutoff = (opened * conductance * LIT_OHMS * 2f64.powf(octaves)).clamp(LOWEST_CUTOFF, HIGHEST_SHARE * self.rate);
            state.g = (PI * cutoff / self.rate).tan();
            state.countdown = COEFFICIENT_STEP;
        }
        state.countdown -= 1;
        let g = state.g;
        let out = if self.mode == GateMode::Both {
            let share = g / (1.0 + g);
            let moved = (source - state.stages[0]) * share;
            let out = moved + state.stages[0];
            state.stages[0] = out + moved;
            out * gain(conductance)
        } else {
            let [first, second, _, _] = state.stages;
            let high = (source - (self.damping + g) * first - second) / (1.0 + self.damping * g + g * g);
            let band = g * high + first;
            let low = g * band + second;
            state.stages[0] = g * high + band;
            state.stages[1] = g * band + low;
            low
        };
        for stage in state.stages.iter_mut().take(2) {
            *stage = flushed(*stage);
        }
        out
    }
}

/// The VCA's gain from the photoresistor, its divider normalized so that full light is full.
#[inline]
fn gain(conductance: f64) -> f64 {
    let full = DIVIDER_OHMS / (DIVIDER_OHMS + 2.0 * LIT_OHMS);
    DIVIDER_OHMS / (DIVIDER_OHMS + 2.0 / conductance) / full
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

    #[test]
    fn a_ladder_at_full_resonance_rings_on_by_itself_and_stays_bounded() {
        let ladder = part("ladder", 1.0);
        let mut state = FilterState::default();
        let mut late: f64 = 0.0;
        for place in 0..48000 {
            let input = if place == 0 { 1.0 } else { 0.0 };
            let out = ladder.process(&mut state, input, 0.0, 0.0);
            if place > 40000 {
                late = late.max(out.abs());
            }
        }
        assert!(late > 0.05 && late < 8.0, "{late}");
    }

    #[test]
    fn every_filter_stays_finite_under_a_wild_sweep() {
        for kind in ["ladder", "diode", "ota", "multimode", "sallen_key"] {
            let filter = part(kind, 1.0);
            let mut state = FilterState::default();
            for place in 0..48000 {
                let octaves = 8.0 * (place as f64 / 300.0).sin();
                let out = filter.process(&mut state, (place as f64 * 0.37).sin(), octaves, 0.0);
                assert!(out.is_finite() && out.abs() < 16.0, "{kind}");
            }
        }
    }

    /// A ladder at full resonance rings up from silence, from its noise floor, as a circuit's does, the same every playing.
    #[test]
    fn a_ladder_at_full_resonance_rings_up_from_silence() {
        let ringing = || {
            let ladder = part("ladder", 1.0);
            let mut state = FilterState::default();
            (0..96_000).map(|_| ladder.process(&mut state, 0.0, 0.0, 0.0)).collect::<Vec<f64>>()
        };
        let heard = ringing();
        let late = heard[90_000..].iter().fold(0.0_f64, |most, sample| most.max(sample.abs()));
        assert!(late > 0.05, "{late}");
        assert_eq!(heard, ringing(), "the same every playing");
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
}
