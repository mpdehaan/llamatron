// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The built-in drum machine, MechaDrum: each recipe renders one whole hit from its five knobs, Pitch, Decay, Color, Shape
//! and Sweep, each 0 to 127, a note's pitch tuning it in half steps from middle C and its velocity brightening it.
//!
//! The recipes honour the classic drum machines' circuits (.claude/notes/synthesis/DRUMS.md): a sine resonator swept down
//! for the kicks, detuned tones and snapped noise for the snare, noise bursts for the clap, six clashing squares for the
//! hats, two squares through a band pass for the cowbell; and two are physical models: the acoustic tom, a struck
//! circular membrane's modes, and the Karplus-Strong drum, a waveguide whose samples flip sign at random.
//!
//! A hit is rendered on the reader thread when its note arrives, never in the audio callback, and kept. Its noise is
//! seeded by what it is, so that a replay and a WAV export match to the sample. Every hit ends alike: a DC-blocking high
//! pass, a fade where it falls silent, and a gain so that its loudest moment peaks at -3 dB.

use crate::dsp::{self, band_pass_pair, Biquad, Random, BUTTERWORTH_Q};
use crate::registry::{self, Entry};
use llamatron_names::spec;
use std::f64::consts::{PI, TAU};
use std::sync::Arc;

const MIDDLE_C: f64 = 60.0;
/// The knob's middle, where a knob a spec leaves out stands; each knob's place among the five; a velocity's top; the
/// semitones of an octave and the ratio an octave multiplies a frequency by.
const MIDDLE_KNOB: f64 = 64.0;
const PITCH_KNOB: usize = 0;
const DECAY_KNOB: usize = 1;
const COLOR_KNOB: usize = 2;
const SHAPE_KNOB: usize = 3;
const SWEEP_KNOB: usize = 4;
const VELOCITY_TOP: f64 = 127.0;
const SEMITONES_AN_OCTAVE: f64 = 12.0;
const OCTAVE: f64 = 2.0;
/// Decibels as an amplitude: ten to the power of a twentieth of them.
const DECIBEL_BASE: f64 = 10.0;
const DECIBELS_A_DECADE: f64 = 20.0;
/// The peak every hit is scaled to, in decibels; the smallest peak a hit is scaled from, so that silence divides by
/// nothing; and the fewest samples a fade or a click's rise is spread over.
const PEAK_DB: f64 = -3.0;
const SMALLEST_PEAK: f64 = 1e-12;
const FEWEST_SPREAD_SAMPLES: usize = 2;
/// How much longer a hit runs than its decay, and a little more, so that its tail is never cut.
const TAIL_STRETCH: f64 = 1.2;
const TAIL_PAD_SECONDS: f64 = 0.01;
/// Half, as a raised cosine's mean and a mix's even share.
const HALF: f64 = 0.5;
/// The share of the sample rate under which every tone and band pass is kept, clear of the top.
const HIGHEST_SHARE: f64 = 0.45;
/// Where clipping turns hard: past this gain the clipped wave is pushed a little further, squaring it.
const HARD_CLIP_GAIN: f64 = 8.0;
const HARD_CLIP_PUSH: f64 = 1.1;
/// A click: how long it rises and falls, how far its silence runs after, as widths, and the high pass it is shaped by.
const CLICK_SECONDS: f64 = 0.001;
const CLICK_WIDTHS: usize = 8;
const CLICK_HIGH_PASS_HERTZ: f64 = 1000.0;
/// A noise burst's band pass.
const BURST_Q: f64 = 0.7;
const KNOB_TOP: f64 = 127.0;
const SILENT_DB: f64 = -80.0;
const END_FADE_SECONDS: f64 = 0.005;
const DC_BLOCK_HZ: f64 = 20.0;
const T60: f64 = 6.91;
const LONGEST_HIT_SECONDS: f64 = 4.0;
const HAT_PITCHES: [f64; 6] = [205.3, 304.4, 369.6, 522.7, 540.0, 800.0];
/// The circular membrane's mode frequencies as ratios of its lowest, the zeros of the Bessel functions.
const MEMBRANE_RATIOS: [f64; 10] = [1.000, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501, 3.600, 4.060];
/// The modes a strike at the centre rings, those with no diameter of rest.
const CENTER_MODES: [f64; 3] = [1.000, 2.296, 3.600];

/// One hit of a drum, at the sample rate it was rendered for.
pub type Hit = Arc<Vec<f32>>;

/// The knobs as shares from 0 to 1, and what the note brings, which each machine's recipe reads.
pub struct Strike {
    pitch: f64,
    decay: f64,
    color: f64,
    shape: f64,
    sweep: f64,
    tuning: f64,
    hardness: f64,
    rate: f64,
}

/// One hit of a machine by its name, at its knobs, a note's pitch and velocity, and a sample rate; a machine this daemon
/// does not know plays the kick, so that a newer tracker never crashes it.
/// How a drum machine renders a hit: from the strike its knobs and the note make, drawing from the hit's own noise.
pub type Build = fn(&Strike, &mut Random) -> Vec<f64>;

/// The kick's recipe, which a new drum starts on.
const KICK_BUILD: Build = |strike, noise| kick(strike, noise);

/// Every drum machine, by the name a spec gives it, the file that holds it, and how it renders a hit.
pub static REGISTRY: &[Entry<Build>] = &[
    Entry {
        name: spec::KICK,
        file: "mod.rs",
        build: KICK_BUILD,
    },
    Entry {
        name: spec::HARD_KICK,
        file: "mod.rs",
        build: |strike, noise| hard_kick(strike, noise),
    },
    Entry {
        name: spec::SYNTH_KICK,
        file: "mod.rs",
        build: |strike, _noise| synth_kick(strike),
    },
    Entry {
        name: spec::SNARE,
        file: "mod.rs",
        build: |strike, noise| snare(strike, noise),
    },
    Entry {
        name: spec::CLAP,
        file: "mod.rs",
        build: |strike, noise| clap(strike, noise),
    },
    Entry {
        name: spec::RIM,
        file: "mod.rs",
        build: |strike, _noise| rim(strike),
    },
    Entry {
        name: spec::HATS,
        file: "mod.rs",
        build: |strike, noise| hats(strike, noise),
    },
    Entry {
        name: spec::COWBELL,
        file: "mod.rs",
        build: |strike, _noise| cowbell(strike),
    },
    Entry {
        name: spec::ACOUSTIC_TOM,
        file: "mod.rs",
        build: |strike, noise| acoustic_tom(strike, noise),
    },
    Entry {
        name: spec::KARPLUS_DRUM,
        file: "mod.rs",
        build: |strike, noise| karplus_drum(strike, noise),
    },
];

/// The files of the drums' folder that are no machine of their own: none today.
pub const HELPERS: &[&str] = &[];

pub fn render_hit(machine: &str, knobs: &[f64], pitch: f64, velocity: f64, rate: f64) -> Hit {
    let knob = |place: usize| knobs.get(place).copied().unwrap_or(MIDDLE_KNOB) / KNOB_TOP;
    let strike = Strike {
        pitch: knob(PITCH_KNOB),
        decay: knob(DECAY_KNOB),
        color: knob(COLOR_KNOB),
        shape: knob(SHAPE_KNOB),
        sweep: knob(SWEEP_KNOB),
        tuning: OCTAVE.powf((pitch - MIDDLE_C) / SEMITONES_AN_OCTAVE),
        hardness: velocity / VELOCITY_TOP,
        rate,
    };
    let whole: Vec<String> = knobs.iter().map(|knob| format!("{}", *knob as i64)).collect();
    let seed = dsp::crc32(format!("{machine}:{}:{pitch}:{velocity}", whole.join(",")).as_bytes());
    let mut noise = Random::new(seed as u64);
    // A machine no registry holds plays the kick, the machine a new drum starts on.
    let build = registry::find(REGISTRY, machine).map_or(KICK_BUILD, |entry| entry.build);
    let made = build(&strike, &mut noise);
    Arc::new(finished(made, rate))
}

/// A hit high-passed against DC, faded where it falls silent, at its peak gain.
fn finished(mut hit: Vec<f64>, rate: f64) -> Vec<f32> {
    dsp::filtered(&mut [Biquad::high_pass(DC_BLOCK_HZ, BUTTERWORTH_Q, rate)], &mut hit);
    let loudest = hit.iter().fold(0.0_f64, |most, sample| most.max(sample.abs())).max(SMALLEST_PEAK);
    let floor = DECIBEL_BASE.powf(SILENT_DB / DECIBELS_A_DECADE) * loudest;
    let end = hit.iter().rposition(|sample| sample.abs() > floor).map(|place| place + 1).unwrap_or(hit.len());
    hit.truncate(end);
    let fade = ((END_FADE_SECONDS * rate) as usize).min(end);
    for place in 0..fade {
        hit[end - fade + place] *= 1.0 - place as f64 / (fade.max(FEWEST_SPREAD_SAMPLES) - 1) as f64;
    }
    let peak = hit.iter().fold(0.0_f64, |most, sample| most.max(sample.abs()));
    let gain = if peak > 0.0 {
        DECIBEL_BASE.powf(PEAK_DB / DECIBELS_A_DECADE) / peak
    } else {
        0.0
    };
    hit.iter().map(|sample| (sample * gain) as f32).collect()
}

/// How many samples a hit of a decay runs for: a little longer than the decay, never longer than the longest hit.
fn length(seconds: f64, rate: f64) -> usize {
    ((seconds * TAIL_STRETCH + TAIL_PAD_SECONDS).min(LONGEST_HIT_SECONDS) * rate) as usize
}

/// A phase that runs on by a frequency each sample, starting at zero, as the running sum the recipes read.
struct Phase {
    phase: f64,
    rate: f64,
}

impl Phase {
    fn new(rate: f64) -> Phase {
        Phase { phase: 0.0, rate }
    }

    #[inline]
    fn next(&mut self, frequency: f64) -> f64 {
        self.phase += TAU * frequency / self.rate;
        self.phase
    }
}

/// A hit soft-clipped at a gain, scaled back to full at its top, and pushed harder past the hard-clip gain.
fn clip(body: &mut [f64], gain: f64) {
    let scale = 1.0 / gain.tanh();
    for sample in body.iter_mut() {
        let mut clipped = (gain * *sample).tanh() * scale;
        if gain > HARD_CLIP_GAIN {
            clipped = (clipped * HARD_CLIP_PUSH).clamp(-1.0, 1.0);
        }
        *sample = clipped;
    }
}

/// A click added to a hit's start: a raised cosine a millisecond wide at a level, high-passed.
fn click(body: &mut [f64], rate: f64, level: f64) {
    let width = ((CLICK_SECONDS * rate) as usize).max(1);
    let mut click = vec![0.0; body.len().min(width * CLICK_WIDTHS)];
    for (place, sample) in click.iter_mut().enumerate().take(width) {
        *sample = level * HALF * (1.0 + (PI * place as f64 / (width.max(FEWEST_SPREAD_SAMPLES) - 1) as f64).cos());
    }
    dsp::filtered(&mut [Biquad::high_pass(CLICK_HIGH_PASS_HERTZ, BUTTERWORTH_Q, rate)], &mut click);
    for (sample, added) in body.iter_mut().zip(click) {
        *sample += added;
    }
}

/// A burst of noise added to a hit: falling over a decay, at a level, band-passed around a centre.
fn noise_burst(body: &mut [f64], noise: &mut Random, rate: f64, level: f64, decay: f64, centre: f64) {
    if level <= 0.0 {
        return;
    }
    let mut burst: Vec<f64> = (0..body.len())
        .map(|place| noise.normal() * (-(place as f64 / rate) / decay).exp() * level)
        .collect();
    dsp::filtered(&mut band_pass_pair(centre, BURST_Q, rate), &mut burst);
    for (sample, added) in body.iter_mut().zip(burst) {
        *sample += added;
    }
}

/// A power of two, by which a knob's share is squared to give its top more of its range.
const SQUARED: i32 = 2;
/// The second and third harmonics, by their numbers.
const SECOND_HARMONIC: f64 = 2.0;
const THIRD_HARMONIC: f64 = 3.0;

/// The sine kick's voicing: its lowest pitch in hertz and the octaves Pitch spans; its shortest decay and the factor
/// Decay spans; how far its pitch drops at full Sweep, as a multiple, along a curve, over a time from its quickest to its
/// span; where Color starts adding harmonics and over what span, each harmonic's share by its divisor; the click up to a
/// third of Color; the noise from a third of Color over a third, at its level, decay and centre; and the most drive.
const KICK_LOWEST_HERTZ: f64 = 30.0;
const KICK_OCTAVES: f64 = 3.0;
const KICK_SHORTEST_DECAY: f64 = 0.06;
const KICK_DECAY_SPAN: f64 = 50.0;
const KICK_MOST_DROP: f64 = 15.0;
const KICK_DROP_CURVE: f64 = 1.5;
const KICK_QUICKEST_DROP: f64 = 0.004;
const KICK_DROP_TIME_SPAN: f64 = 0.056;
const KICK_HARMONICS_FROM: f64 = 0.66;
const KICK_HARMONICS_SPAN: f64 = 0.34;
const KICK_SECOND_DIVISOR: f64 = 2.0;
const KICK_THIRD_DIVISOR: f64 = 4.0;
const KICK_CLICK_COLOR: f64 = 0.33;
const KICK_NOISE_FROM: f64 = 0.33;
const KICK_NOISE_SPAN: f64 = 0.33;
const KICK_NOISE_LEVEL: f64 = 0.3;
const KICK_NOISE_DECAY: f64 = 0.004;
const KICK_NOISE_HERTZ: f64 = 3000.0;
const KICK_MOST_DRIVE: f64 = 19.0;

/// The sine kick: a sine swept down from above its pitch, its harmonics, click and noise brought in by Color.
fn kick(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let f0 = KICK_LOWEST_HERTZ * OCTAVE.powf(KICK_OCTAVES * strike.pitch) * strike.tuning;
    let decay = KICK_SHORTEST_DECAY * KICK_DECAY_SPAN.powf(strike.decay);
    let drop = KICK_MOST_DROP * strike.sweep.powf(KICK_DROP_CURVE);
    let tau = KICK_QUICKEST_DROP + KICK_DROP_TIME_SPAN * strike.sweep.powi(SQUARED);
    let harmonics = ((strike.color - KICK_HARMONICS_FROM) / KICK_HARMONICS_SPAN).max(0.0);
    let mut phase = Phase::new(rate);
    let mut body: Vec<f64> = (0..length(decay, rate))
        .map(|place| {
            let t = place as f64 / rate;
            let angle = phase.next(f0 * (1.0 + drop * (-t / tau).exp()));
            (angle.sin() + harmonics / KICK_SECOND_DIVISOR * (SECOND_HARMONIC * angle).sin() + harmonics / KICK_THIRD_DIVISOR * (THIRD_HARMONIC * angle).sin())
                * (-T60 * t / decay).exp()
        })
        .collect();
    click(&mut body, rate, (strike.color / KICK_CLICK_COLOR).min(1.0) * (HALF + HALF * strike.hardness));
    let noise_level = ((strike.color - KICK_NOISE_FROM) / KICK_NOISE_SPAN).clamp(0.0, 1.0) * KICK_NOISE_LEVEL;
    noise_burst(&mut body, noise, rate, noise_level, KICK_NOISE_DECAY, KICK_NOISE_HERTZ);
    // At Shape 0 the kick is left unclipped, so that with Color 0 it is the pure decaying sine of the classic sine kick.
    if strike.shape > 0.0 {
        clip(&mut body, 1.0 + KICK_MOST_DRIVE * strike.shape.powi(SQUARED));
    }
    body
}

/// The hard kick's voicing: its pitch from its lowest to its highest in hertz; its shortest decay and Decay's span; the
/// longest it holds at full Shape; how far its pitch drops at full Sweep along a curve, over a time from its quickest to
/// its span; its tick's length; its noise's least level and Color's share, decay and centre; and its drive.
const HARD_KICK_LOWEST_HERTZ: f64 = 35.0;
const HARD_KICK_HIGHEST_HERTZ: f64 = 200.0;
const HARD_KICK_SHORTEST_DECAY: f64 = 0.06;
const HARD_KICK_DECAY_SPAN: f64 = 30.0;
const HARD_KICK_LONGEST_HOLD: f64 = 0.15;
const HARD_KICK_MOST_DROP: f64 = 12.0;
const HARD_KICK_DROP_CURVE: f64 = 1.5;
const HARD_KICK_QUICKEST_DROP: f64 = 0.004;
const HARD_KICK_DROP_TIME_SPAN: f64 = 0.04;
const HARD_KICK_TICK_SECONDS: f64 = 0.0003;
const HARD_KICK_NOISE_LEVEL: f64 = 0.06;
const HARD_KICK_NOISE_COLOR: f64 = 0.2;
const HARD_KICK_NOISE_DECAY: f64 = 0.01;
const HARD_KICK_NOISE_HERTZ: f64 = 3000.0;
const HARD_KICK_DRIVE: f64 = 2.0;

/// The hard kick: a sine held and swept down hard, a tick at its start, noise and drive.
fn hard_kick(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let f0 = HARD_KICK_LOWEST_HERTZ * (HARD_KICK_HIGHEST_HERTZ / HARD_KICK_LOWEST_HERTZ).powf(strike.pitch) * strike.tuning;
    let decay = HARD_KICK_SHORTEST_DECAY * HARD_KICK_DECAY_SPAN.powf(strike.decay);
    let hold = HARD_KICK_LONGEST_HOLD * strike.shape.powi(SQUARED);
    let sweep = HARD_KICK_MOST_DROP * strike.sweep.powf(HARD_KICK_DROP_CURVE);
    let tau = HARD_KICK_QUICKEST_DROP + HARD_KICK_DROP_TIME_SPAN * strike.sweep.powi(SQUARED);
    let mut phase = Phase::new(rate);
    let tick = (HARD_KICK_TICK_SECONDS * rate) as usize;
    let mut body: Vec<f64> = (0..length(decay + hold, rate))
        .map(|place| {
            let t = place as f64 / rate;
            let level = if t < hold { 1.0 } else { (-T60 * (t - hold) / decay).exp() };
            let mut sample = phase.next(f0 * (1.0 + sweep * (-t / tau).exp())).sin() * level;
            if place < tick {
                sample += strike.color * (HALF + HALF * strike.hardness);
            }
            sample
        })
        .collect();
    let noise_level = HARD_KICK_NOISE_LEVEL + HARD_KICK_NOISE_COLOR * strike.color;
    noise_burst(&mut body, noise, rate, noise_level, HARD_KICK_NOISE_DECAY, HARD_KICK_NOISE_HERTZ);
    clip(&mut body, HARD_KICK_DRIVE);
    body
}

/// The synth kick's voicing: its pitch from its lowest to its highest in hertz; its shortest decay and Decay's span; the
/// octaves its pitch falls at full Sweep, over a time from its quickest to its span; how far Shape bends its decay, up to
/// half of Shape; its low pass's top, and its lowest as a multiple of the pitch and in hertz, moved every so many samples;
/// its level, part fixed and part by velocity; and the most drive past half of Shape.
const SYNTH_KICK_LOWEST_HERTZ: f64 = 30.0;
const SYNTH_KICK_HIGHEST_HERTZ: f64 = 200.0;
const SYNTH_KICK_SHORTEST_DECAY: f64 = 0.04;
const SYNTH_KICK_DECAY_SPAN: f64 = 50.0;
const SYNTH_KICK_FALL_OCTAVES: f64 = 5.0;
const SYNTH_KICK_QUICKEST_FALL: f64 = 0.005;
const SYNTH_KICK_FALL_TIME_SPAN: f64 = 0.075;
const SYNTH_KICK_MOST_BEND: f64 = 0.6;
const SYNTH_KICK_LOW_PASS_TOP_HERTZ: f64 = 4000.0;
const SYNTH_KICK_LOW_PASS_PITCHES: f64 = 4.0;
const SYNTH_KICK_LOW_PASS_LOWEST_HERTZ: f64 = 300.0;
const SYNTH_KICK_LOW_PASS_EVERY: usize = 64;
const SYNTH_KICK_FIXED_LEVEL: f64 = 0.8;
const SYNTH_KICK_VELOCITY_LEVEL: f64 = 0.2;
const SYNTH_KICK_MOST_DRIVE: f64 = 9.0;

/// The synth kick: a morphing wave whose pitch falls by octaves through a low pass that falls with it.
fn synth_kick(strike: &Strike) -> Vec<f64> {
    let rate = strike.rate;
    let f0 = SYNTH_KICK_LOWEST_HERTZ * (SYNTH_KICK_HIGHEST_HERTZ / SYNTH_KICK_LOWEST_HERTZ).powf(strike.pitch) * strike.tuning;
    let decay = SYNTH_KICK_SHORTEST_DECAY * SYNTH_KICK_DECAY_SPAN.powf(strike.decay);
    let octaves = SYNTH_KICK_FALL_OCTAVES * strike.sweep;
    let tau = SYNTH_KICK_QUICKEST_FALL + SYNTH_KICK_FALL_TIME_SPAN * strike.sweep.powi(SQUARED);
    let curve = 1.0 - SYNTH_KICK_MOST_BEND * (strike.shape / HALF).min(1.0);
    let lowest = (SYNTH_KICK_LOW_PASS_PITCHES * f0).max(SYNTH_KICK_LOW_PASS_LOWEST_HERTZ);
    let mut phase = Phase::new(rate);
    let mut filter = Biquad::low_pass(SYNTH_KICK_LOW_PASS_TOP_HERTZ, BUTTERWORTH_Q, rate);
    let mut body = Vec::with_capacity(length(decay, rate));
    for place in 0..length(decay, rate) {
        let t = place as f64 / rate;
        let frequency = f0 * OCTAVE.powf(octaves * (-t / tau).exp());
        let angle = phase.next(frequency);
        if place % SYNTH_KICK_LOW_PASS_EVERY == 0 {
            // The low pass falls with the pitch envelope, its coefficients moved every 64 samples, its state kept.
            let cutoff = lowest + (SYNTH_KICK_LOW_PASS_TOP_HERTZ - lowest) * (-t / tau).exp();
            let moved = Biquad::low_pass(cutoff, BUTTERWORTH_Q, rate);
            filter = Biquad {
                s1: filter.s1,
                s2: filter.s2,
                ..moved
            };
        }
        let wave = morphed(angle, frequency, strike.color, rate) * (-T60 * t / decay).exp().powf(curve);
        body.push(filter.process(wave) * (SYNTH_KICK_FIXED_LEVEL + SYNTH_KICK_VELOCITY_LEVEL * strike.hardness));
    }
    clip(&mut body, 1.0 + SYNTH_KICK_MOST_DRIVE * ((strike.shape - HALF) / HALF).max(0.0));
    body
}

/// The odd harmonics a morphing wave adds, the top under which it adds them, the step between odd numbers by which
/// their signs alternate, and twice, the factor by which Color's first half reaches the triangle and its second the
/// square.
const MORPHED_HARMONICS: [f64; 6] = [3.0, 5.0, 7.0, 9.0, 11.0, 13.0];
const MORPHED_TOP_HERTZ: f64 = 8000.0;
const ODD_STEP: i64 = 2;
const TWICE: f64 = 2.0;

/// A wave morphing from a sine at Color 0 through a triangle to a square at full Color, of odd harmonics under 8 kHz.
fn morphed(angle: f64, frequency: f64, color: f64, rate: f64) -> f64 {
    let mut wave = angle.sin();
    if color <= 0.0 {
        return wave;
    }
    for number in MORPHED_HARMONICS {
        if frequency * number >= MORPHED_TOP_HERTZ.min(rate * HIGHEST_SHARE) {
            break;
        }
        let sign = if ((number as i64 - 1) / ODD_STEP) % ODD_STEP == 0 { 1.0 } else { -1.0 };
        let triangle = sign / (number * number);
        let weight = triangle * (color * TWICE).min(1.0) + (1.0 / number - triangle) * (color * TWICE - 1.0).max(0.0);
        wave += weight * (number * angle).sin();
    }
    wave
}

/// The snare's voicing: its lower tone's lowest pitch in hertz and the factor Pitch spans; its upper tone's ratio to it,
/// spread a little by Color; its shortest decay and Decay's span; its rattle's high pass, from its lowest by Color's
/// span; Sweep's bump's time; the tones' share of the decay; the snap's length and its boost; the tones' and the
/// rattle's levels, the rattle's part by velocity; and its drive.
const SNARE_LOWEST_HERTZ: f64 = 120.0;
const SNARE_PITCH_SPAN: f64 = 4.0;
const SNARE_UPPER_RATIO: f64 = 1.47;
const SNARE_UPPER_SPREAD: f64 = 0.04;
const SNARE_SHORTEST_DECAY: f64 = 0.06;
const SNARE_DECAY_SPAN: f64 = 15.0;
const SNARE_RATTLE_LOWEST_HERTZ: f64 = 600.0;
const SNARE_RATTLE_COLOR_HERTZ: f64 = 3400.0;
const SNARE_BUMP_SECONDS: f64 = 0.008;
const SNARE_TONES_DECAY: f64 = 0.35;
const SNARE_SNAP_SECONDS: f64 = 0.003;
const SNARE_SNAP_BOOST: f64 = 2.0;
const SNARE_TONES_LEVEL: f64 = 0.6;
const SNARE_RATTLE_LEVEL: f64 = 0.6;
const SNARE_RATTLE_VELOCITY: f64 = 0.4;
const SNARE_DRIVE: f64 = 3.0;

/// The snare: two detuned triangle tones and snapped, high-passed noise, Shape trading one for the other.
fn snare(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let f1 = SNARE_LOWEST_HERTZ * SNARE_PITCH_SPAN.powf(strike.pitch) * strike.tuning;
    let f2 = f1 * SNARE_UPPER_RATIO * (1.0 + SNARE_UPPER_SPREAD * strike.color);
    let decay = SNARE_SHORTEST_DECAY * SNARE_DECAY_SPAN.powf(strike.decay);
    let count = length(decay, rate);
    let mut rattle: Vec<f64> = (0..count).map(|_| noise.normal()).collect();
    let rattle_hertz = SNARE_RATTLE_LOWEST_HERTZ + SNARE_RATTLE_COLOR_HERTZ * strike.color;
    dsp::filtered(&mut [Biquad::high_pass(rattle_hertz, BUTTERWORTH_Q, rate)], &mut rattle);
    let (mut first, mut second) = (Phase::new(rate), Phase::new(rate));
    let mut body: Vec<f64> = rattle
        .iter()
        .enumerate()
        .map(|(place, rattled)| {
            let t = place as f64 / rate;
            let bump = 1.0 + strike.sweep * (-t / SNARE_BUMP_SECONDS).exp();
            let tones = (triangle(first.next(f1 * bump)) + triangle(second.next(f2 * bump))) * (-T60 * t / (SNARE_TONES_DECAY * decay)).exp();
            let snap = if t < SNARE_SNAP_SECONDS { SNARE_SNAP_BOOST } else { 1.0 } * (-T60 * t / decay).exp();
            tones * (1.0 - strike.shape) * SNARE_TONES_LEVEL + rattled * snap * (SNARE_RATTLE_LEVEL + SNARE_RATTLE_VELOCITY * strike.hardness) * strike.shape
        })
        .collect();
    clip(&mut body, SNARE_DRIVE);
    body
}

/// A triangle wave at a phase, from the arcsine of its sine, scaled to full.
fn triangle(angle: f64) -> f64 {
    TWICE / PI * angle.sin().asin()
}

/// The clap's voicing: its band's lowest centre in hertz and Pitch's span; its shortest decay and Decay's span; its
/// fewest bursts and the most Color adds; the bursts' widest spacing and how much Color narrows it; each burst's random
/// lateness; its tail's quietest level in decibels and Shape's span; each burst's longest fall and how much velocity
/// quickens it, and its rise; Sweep's lift of the band; and the band's width.
const CLAP_LOWEST_HERTZ: f64 = 700.0;
const CLAP_PITCH_SPAN: f64 = 4.0;
const CLAP_SHORTEST_DECAY: f64 = 0.08;
const CLAP_DECAY_SPAN: f64 = 15.0;
const CLAP_FEWEST_BURSTS: usize = 3;
const CLAP_MORE_BURSTS: f64 = 3.0;
const CLAP_WIDEST_SPACING: f64 = 0.014;
const CLAP_NARROWING: f64 = 0.007;
const CLAP_LATENESS: f64 = 0.001;
const CLAP_QUIETEST_TAIL_DB: f64 = -30.0;
const CLAP_TAIL_SPAN_DB: f64 = 30.0;
const CLAP_LONGEST_FALL: f64 = 0.006;
const CLAP_QUICKENING: f64 = 0.004;
const CLAP_RISE_SECONDS: f64 = 0.0015;
const CLAP_SWEEP_LIFT: f64 = 0.3;
const CLAP_BAND_Q: f64 = 2.0;

/// The clap: a few noise bursts in quick succession, then a tail, through a band pass.
fn clap(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let centre = (CLAP_LOWEST_HERTZ * CLAP_PITCH_SPAN.powf(strike.pitch) * strike.tuning).min(rate * HIGHEST_SHARE);
    let decay = CLAP_SHORTEST_DECAY * CLAP_DECAY_SPAN.powf(strike.decay);
    let bursts = CLAP_FEWEST_BURSTS + (CLAP_MORE_BURSTS * strike.color).round() as usize;
    let spacing = CLAP_WIDEST_SPACING - CLAP_NARROWING * strike.color;
    let count = length(bursts as f64 * spacing + decay, rate);
    let starts: Vec<f64> = (0..bursts).map(|burst| burst as f64 * spacing + noise.between(0.0, CLAP_LATENESS)).collect();
    let last = (bursts - 1) as f64 * spacing;
    let tail_level = DECIBEL_BASE.powf((CLAP_QUIETEST_TAIL_DB + CLAP_TAIL_SPAN_DB * strike.shape) / DECIBELS_A_DECADE);
    let quick = CLAP_LONGEST_FALL - CLAP_QUICKENING * strike.hardness;
    let mut body: Vec<f64> = (0..count)
        .map(|place| {
            let t = place as f64 / rate;
            let mut shape: f64 = starts
                .iter()
                .filter(|start| t >= **start)
                .map(|start| ((t - start) / CLAP_RISE_SECONDS).min(1.0) * (-(t - start) / quick).exp())
                .sum();
            if t >= last {
                shape += (-T60 * (t - last) / decay).exp() * tail_level;
            }
            noise.normal() * shape
        })
        .collect();
    dsp::filtered(
        &mut band_pass_pair(centre * (1.0 + CLAP_SWEEP_LIFT * strike.sweep), CLAP_BAND_Q, rate),
        &mut body,
    );
    body
}

/// The rim shot's voicing: its pitch from its lowest to its highest in hertz; its shortest length factor and Decay's
/// span; its length, as a share of the factor; how far Sweep drops its pitch and how quickly; its two tones' ratio and
/// decays; Color's trade between them; its click, part fixed and part by velocity; and its most drive.
const RIM_LOWEST_HERTZ: f64 = 250.0;
const RIM_HIGHEST_HERTZ: f64 = 900.0;
const RIM_SHORTEST_FACTOR: f64 = 0.4;
const RIM_DECAY_SPAN: f64 = 10.0;
const RIM_LENGTH: f64 = 0.05;
const RIM_MOST_DROP: f64 = 0.15;
const RIM_DROP_SECONDS: f64 = 0.005;
const RIM_UPPER_RATIO: f64 = 3.66;
const RIM_LOWER_DECAY: f64 = 0.025;
const RIM_UPPER_DECAY: f64 = 0.012;
const RIM_UPPER_LEAST: f64 = 0.3;
const RIM_UPPER_COLOR: f64 = 0.7;
const RIM_CLICK_LEVEL: f64 = 0.4;
const RIM_CLICK_VELOCITY: f64 = 0.4;
const RIM_MOST_DRIVE: f64 = 11.0;

/// The rim shot: two short sine tones in a clashing ratio, a click and drive.
fn rim(strike: &Strike) -> Vec<f64> {
    let rate = strike.rate;
    let frequency = RIM_LOWEST_HERTZ * (RIM_HIGHEST_HERTZ / RIM_LOWEST_HERTZ).powf(strike.pitch) * strike.tuning;
    let factor = RIM_SHORTEST_FACTOR * RIM_DECAY_SPAN.powf(strike.decay);
    let (mut low, mut high) = (Phase::new(rate), Phase::new(rate));
    let mut body: Vec<f64> = (0..length(RIM_LENGTH * factor, rate))
        .map(|place| {
            let t = place as f64 / rate;
            let drop = 1.0 - RIM_MOST_DROP * strike.sweep * (1.0 - (-t / RIM_DROP_SECONDS).exp());
            let lower = low.next(frequency * drop).sin() * (-T60 * t / (RIM_LOWER_DECAY * factor)).exp();
            let upper = high.next(frequency * RIM_UPPER_RATIO * drop).sin() * (-T60 * t / (RIM_UPPER_DECAY * factor)).exp();
            lower * (1.0 - strike.color * HALF) + upper * (RIM_UPPER_LEAST + RIM_UPPER_COLOR * strike.color)
        })
        .collect();
    click(&mut body, rate, RIM_CLICK_LEVEL + RIM_CLICK_VELOCITY * strike.hardness);
    clip(&mut body, 1.0 + RIM_MOST_DRIVE * strike.shape);
    body
}

/// The hats' voicing: their pitches' lowest scale and Pitch's span; their shortest decay and Decay's span; the noise's
/// level where Color leaves the squares; the band's highest centre, how far Sweep lowers it, and its width from its
/// narrowest by Shape's span; the high pass's corner and its share of the rate; Shape's gap's start, end and depth; the
/// rise; and the level, part fixed and part by velocity.
const HATS_LOWEST_SCALE: f64 = 0.5;
const HATS_PITCH_SPAN: f64 = 4.0;
const HATS_SHORTEST_DECAY: f64 = 0.015;
const HATS_DECAY_SPAN: f64 = 100.0;
const HATS_NOISE_LEVEL: f64 = 0.4;
const HATS_BAND_HERTZ: f64 = 8000.0;
const HATS_SWEEP_LOWERING: f64 = 0.3;
const HATS_NARROWEST_Q: f64 = 1.5;
const HATS_Q_SPAN: f64 = 2.5;
const HATS_HIGH_PASS_HERTZ: f64 = 6000.0;
const HATS_HIGH_PASS_SHARE: f64 = 0.4;
const HATS_GAP_FROM: f64 = 0.002;
const HATS_GAP_TO: f64 = 0.006;
const HATS_GAP_DEPTH: f64 = 0.75;
const HATS_RISE_SECONDS: f64 = 0.0005;
const HATS_FIXED_LEVEL: f64 = 0.7;
const HATS_VELOCITY_LEVEL: f64 = 0.3;

/// The hats: six clashing squares and noise, band-passed and high-passed, Shape opening a gap at their start.
fn hats(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let scale = HATS_LOWEST_SCALE * HATS_PITCH_SPAN.powf(strike.pitch) * strike.tuning;
    let decay = HATS_SHORTEST_DECAY * HATS_DECAY_SPAN.powf(strike.decay);
    let count = length(decay, rate);
    // Six squares in clashing ratios, naive and so a little aliased, as the digital edge of the classic circuit has it.
    let mut source: Vec<f64> = (0..count)
        .map(|place| {
            let t = place as f64 / rate;
            let metal: f64 = HAT_PITCHES.iter().map(|pitch| (TAU * pitch * scale * t).sin().signum()).sum::<f64>() / HAT_PITCHES.len() as f64;
            metal * strike.color + noise.normal() * HATS_NOISE_LEVEL * (1.0 - strike.color)
        })
        .collect();
    let centre = (HATS_BAND_HERTZ * (1.0 - HATS_SWEEP_LOWERING * strike.sweep)).min(rate * HIGHEST_SHARE);
    let band = band_pass_pair(centre, HATS_NARROWEST_Q + HATS_Q_SPAN * strike.shape, rate);
    let [first, second] = band;
    dsp::filtered(
        &mut [
            first,
            second,
            Biquad::high_pass(HATS_HIGH_PASS_HERTZ.min(rate * HATS_HIGH_PASS_SHARE), BUTTERWORTH_Q, rate),
        ],
        &mut source,
    );
    for (place, sample) in source.iter_mut().enumerate() {
        let t = place as f64 / rate;
        let gap = if t > HATS_GAP_FROM && t < HATS_GAP_TO {
            1.0 - HATS_GAP_DEPTH * strike.shape
        } else {
            1.0
        };
        *sample *= (t / HATS_RISE_SECONDS).min(1.0) * (-T60 * t / decay).exp() * gap * (HATS_FIXED_LEVEL + HATS_VELOCITY_LEVEL * strike.hardness);
    }
    source
}

/// The cowbell's voicing: its pitch from its lowest to its highest in hertz; its shortest decay and Decay's span; Sweep's
/// bump and its time; its two squares' ratio; the band's centre as a multiple of the pitch, and its width; the held
/// floor's least and Shape's span, and the quick part's decay; the low pass's top, how far Color lowers it, and its
/// lowest; the level, part fixed and part by velocity; and Color's drive.
const COWBELL_LOWEST_HERTZ: f64 = 300.0;
const COWBELL_HIGHEST_HERTZ: f64 = 1100.0;
const COWBELL_SHORTEST_DECAY: f64 = 0.1;
const COWBELL_DECAY_SPAN: f64 = 12.0;
const COWBELL_BUMP: f64 = 0.3;
const COWBELL_BUMP_SECONDS: f64 = 0.006;
const COWBELL_RATIO: f64 = 1.48;
const COWBELL_BAND_PITCHES: f64 = 2.6;
const COWBELL_BAND_Q: f64 = 3.0;
const COWBELL_LEAST_FLOOR: f64 = 0.2;
const COWBELL_FLOOR_SPAN: f64 = 0.6;
const COWBELL_QUICK_DECAY: f64 = 0.03;
const COWBELL_LOW_PASS_HERTZ: f64 = 4000.0;
const COWBELL_COLOR_LOWERING: f64 = 2500.0;
const COWBELL_LOWEST_LOW_PASS: f64 = 20.0;
const COWBELL_FIXED_LEVEL: f64 = 0.7;
const COWBELL_VELOCITY_LEVEL: f64 = 0.3;
const COWBELL_COLOR_DRIVE: f64 = 2.0;

/// The cowbell: two squares in a clashing ratio through a band pass, a quick fall over a held floor, and a low pass.
fn cowbell(strike: &Strike) -> Vec<f64> {
    let rate = strike.rate;
    let frequency = COWBELL_LOWEST_HERTZ * (COWBELL_HIGHEST_HERTZ / COWBELL_LOWEST_HERTZ).powf(strike.pitch) * strike.tuning;
    let decay = COWBELL_SHORTEST_DECAY * COWBELL_DECAY_SPAN.powf(strike.decay);
    let (mut low, mut high) = (Phase::new(rate), Phase::new(rate));
    let mut squares: Vec<f64> = (0..length(decay, rate))
        .map(|place| {
            let bump = 1.0 + COWBELL_BUMP * strike.sweep * (-(place as f64 / rate) / COWBELL_BUMP_SECONDS).exp();
            low.next(frequency * bump).sin().signum() + high.next(frequency * COWBELL_RATIO * bump).sin().signum()
        })
        .collect();
    let [first, second] = band_pass_pair((COWBELL_BAND_PITCHES * frequency).min(rate * HIGHEST_SHARE), COWBELL_BAND_Q, rate);
    dsp::filtered(&mut [first, second], &mut squares);
    let floor = COWBELL_LEAST_FLOOR + COWBELL_FLOOR_SPAN * strike.shape;
    for (place, sample) in squares.iter_mut().enumerate() {
        let t = place as f64 / rate;
        *sample *= (1.0 - floor) * (-T60 * t / COWBELL_QUICK_DECAY).exp() + floor * (-T60 * t / decay).exp();
    }
    let low_pass = (COWBELL_LOW_PASS_HERTZ - COWBELL_COLOR_LOWERING * strike.color).max(COWBELL_LOWEST_LOW_PASS);
    dsp::filtered(&mut [Biquad::low_pass(low_pass, BUTTERWORTH_Q, rate)], &mut squares);
    for sample in squares.iter_mut() {
        *sample *= COWBELL_FIXED_LEVEL + COWBELL_VELOCITY_LEVEL * strike.hardness;
    }
    clip(&mut squares, 1.0 + COWBELL_COLOR_DRIVE * strike.color);
    squares
}

/// A struck circular membrane: its modes at the Bessel ratios, each rung by where it is struck (Shape, from the centre to
/// the edge) and how hard the mallet is (Color and the velocity, a hard mallet's short contact ringing the high modes), each
/// fading faster the higher it is, the tension gliding down after a hard hit as a real head's does, and the shell's noise.
/// The acoustic tom's voicing: its pitch from its lowest to its highest in hertz; its shortest decay and Decay's span; the
/// mallet's softest contact and how much Color and velocity shorten it; how loud a mode with a diameter of rest rings
/// at the centre; how much faster each higher mode fades; the tension's glide and its time; the shell's band as a
/// multiple of the pitch, its width, its decay and its level.
const TOM_LOWEST_HERTZ: f64 = 60.0;
const TOM_HIGHEST_HERTZ: f64 = 400.0;
const TOM_SHORTEST_DECAY: f64 = 0.1;
const TOM_DECAY_SPAN: f64 = 25.0;
const TOM_SOFTEST_CONTACT: f64 = 0.004;
const TOM_CONTACT_SHORTENING: f64 = 0.0037;
const TOM_VELOCITY_HARDNESS: f64 = 0.2;
const TOM_OFF_CENTRE_LEVEL: f64 = 0.15;
const TOM_HIGHER_FADE: f64 = 0.6;
const TOM_GLIDE: f64 = 0.08;
const TOM_GLIDE_SECONDS: f64 = 0.04;
const TOM_SHELL_PITCHES: f64 = 5.0;
const TOM_SHELL_Q: f64 = 1.0;
const TOM_SHELL_DECAY: f64 = 0.2;
const TOM_SHELL_LEVEL: f64 = 0.03;

fn acoustic_tom(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let f0 = TOM_LOWEST_HERTZ * (TOM_HIGHEST_HERTZ / TOM_LOWEST_HERTZ).powf(strike.pitch) * strike.tuning;
    let decay = TOM_SHORTEST_DECAY * TOM_DECAY_SPAN.powf(strike.decay);
    let count = length(decay, rate);
    let width = TOM_SOFTEST_CONTACT - TOM_CONTACT_SHORTENING * (strike.color + TOM_VELOCITY_HARDNESS * strike.hardness).min(1.0);
    let mut body = vec![0.0; count];
    for ratio in MEMBRANE_RATIOS {
        let frequency = f0 * ratio;
        if frequency >= rate * HIGHEST_SHARE {
            continue;
        }
        let centre = if CENTER_MODES.contains(&ratio) { 1.0 } else { TOM_OFF_CENTRE_LEVEL };
        let amplitude = (centre * (1.0 - strike.shape) + strike.shape) / (1.0 + (frequency * width * TWICE).powi(SQUARED));
        let mode_decay = decay / (1.0 + TOM_HIGHER_FADE * (ratio - 1.0));
        let mut phase = Phase::new(rate);
        for (place, sample) in body.iter_mut().enumerate() {
            let t = place as f64 / rate;
            let glide = 1.0 + TOM_GLIDE * strike.sweep * strike.hardness * (-t / TOM_GLIDE_SECONDS).exp();
            *sample += amplitude * phase.next(frequency * glide).sin() * (-T60 * t / mode_decay).exp();
        }
    }
    let mut shell: Vec<f64> = (0..count).map(|_| noise.normal()).collect();
    let [first, second] = band_pass_pair((TOM_SHELL_PITCHES * f0).min(rate * HIGHEST_SHARE), TOM_SHELL_Q, rate);
    dsp::filtered(&mut [first, second], &mut shell);
    for (place, (sample, rattle)) in body.iter_mut().zip(shell).enumerate() {
        *sample += rattle * (-T60 * (place as f64 / rate) / TOM_SHELL_DECAY).exp() * TOM_SHELL_LEVEL;
    }
    body
}

/// Karplus and Strong's drum, a waveguide: a burst of noise circulating in a delay line a period long, each pass averaged
/// with its neighbour, which dulls and fades it, and each sample's sign flipped at random by Shape, which turns a plucked
/// string into a drum; Color brightens the burst and the averaging, Sweep drops the pitch at the start.
/// The Karplus-Strong drum's voicing: its pitch's lowest in hertz and Pitch's span; its shortest decay and Decay's span;
/// the shortest line; the burst's darkest low pass, how far Color opens it, part fixed and part by velocity; the line's
/// loss over its decay, in decades of amplitude; how far Shape flips signs; the averaging's dullest share and Color's
/// span; and how long Sweep's drop lasts.
const KARPLUS_LOWEST_HERTZ: f64 = 50.0;
const KARPLUS_PITCH_SPAN: f64 = 16.0;
const KARPLUS_SHORTEST_DECAY: f64 = 0.05;
const KARPLUS_DECAY_SPAN: f64 = 40.0;
const KARPLUS_SHORTEST_LINE: usize = 2;
const KARPLUS_DARKEST_HERTZ: f64 = 500.0;
const KARPLUS_COLOR_HERTZ: f64 = 15000.0;
const KARPLUS_FIXED_OPENING: f64 = 0.6;
const KARPLUS_VELOCITY_OPENING: f64 = 0.4;
const KARPLUS_LOSS_DECADES: f64 = -3.0;
const KARPLUS_MOST_FLIPPING: f64 = 0.5;
const KARPLUS_DULLEST: f64 = 0.5;
const KARPLUS_BRIGHTENING: f64 = 0.45;
const KARPLUS_DROP_SECONDS: f64 = 0.03;

fn karplus_drum(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let frequency = KARPLUS_LOWEST_HERTZ * KARPLUS_PITCH_SPAN.powf(strike.pitch) * strike.tuning;
    let decay = KARPLUS_SHORTEST_DECAY * KARPLUS_DECAY_SPAN.powf(strike.decay);
    let total = length(decay, rate);
    let period = ((rate / frequency).round() as usize).max(KARPLUS_SHORTEST_LINE);
    let mut line: Vec<f64> = (0..period).map(|_| noise.normal()).collect();
    if strike.color < 1.0 {
        let opening = KARPLUS_FIXED_OPENING + KARPLUS_VELOCITY_OPENING * strike.hardness;
        let cutoff = (KARPLUS_DARKEST_HERTZ + KARPLUS_COLOR_HERTZ * strike.color * opening).min(rate * HIGHEST_SHARE);
        dsp::filtered(&mut [Biquad::low_pass(cutoff, BUTTERWORTH_Q, rate)], &mut line);
    }
    let loss = DECIBEL_BASE.powf(KARPLUS_LOSS_DECADES * period as f64 / (decay * rate));
    let blend = 1.0 - strike.shape * KARPLUS_MOST_FLIPPING;
    let bright = KARPLUS_DULLEST + KARPLUS_BRIGHTENING * strike.color;
    let mut out = Vec::with_capacity(total);
    while out.len() < total {
        let since = out.len() as f64 / rate;
        let length = ((period as f64 / (1.0 + strike.sweep * (-since / KARPLUS_DROP_SECONDS).exp())).round() as usize).max(KARPLUS_SHORTEST_LINE);
        if length != line.len() {
            line = resampled(&line, length);
        }
        let last = line[length - 1];
        let mut previous = last;
        for sample in line.iter_mut() {
            let averaged = bright * *sample + (1.0 - bright) * previous;
            previous = *sample;
            let sign = if noise.uniform() < blend { 1.0 } else { -1.0 };
            *sample = averaged * sign * loss;
        }
        let take = length.min(total - out.len());
        out.extend_from_slice(&line[..take]);
    }
    out
}

/// A line stretched or squeezed to a new length by linear interpolation.
fn resampled(line: &[f64], length: usize) -> Vec<f64> {
    let span = (line.len() - 1) as f64;
    (0..length)
        .map(|place| {
            let position = place as f64 * span / (length - 1).max(1) as f64;
            let whole = position.floor() as usize;
            let next = (whole + 1).min(line.len() - 1);
            line[whole] + (line[next] - line[whole]) * (position - whole as f64)
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_machine_renders_a_finite_hit_peaking_at_minus_three_decibels() {
        for machine in REGISTRY.iter().map(|entry| entry.name) {
            let (rate, velocity, shortest_hit) = (48000.0, 100.0, 100);
            let hit = render_hit(machine, &[MIDDLE_KNOB; SWEEP_KNOB + 1], MIDDLE_C, velocity, rate);
            assert!(hit.len() > shortest_hit, "{machine}");
            let peak = hit.iter().fold(0.0_f32, |most, sample| most.max(sample.abs()));
            assert!(hit.iter().all(|sample| sample.is_finite()), "{machine}");
            let (minus_three_decibels, tolerance) = (0.7079, 0.01);
            assert!((peak - minus_three_decibels).abs() < tolerance, "{machine} {peak}");
        }
    }

    /// The sine kick: at Color, Shape and Sweep 0 the Kick is a pure decaying sine, its second and third harmonics more
    /// than 60 dB under its fundamental, ringing for as long as a long Decay asks.
    #[test]
    fn the_kick_at_no_color_shape_or_sweep_is_a_pure_sine() {
        let (rate, long_decay) = (48000.0, 100.0);
        let (middle_knob, middle_c, loudest) = (64.0, 60.0, 127.0);
        let hit = render_hit(spec::KICK, &[middle_knob, long_decay, 0.0, 0.0, 0.0], middle_c, loudest, rate);
        let fundamental = KICK_LOWEST_HERTZ * OCTAVE.powf(KICK_OCTAVES * middle_knob / KNOB_TOP);
        // A Hann window over a stretch of the ring, so that the decay's own spread of frequencies stays out of the reading.
        let (from_seconds, to_seconds) = (0.2, 0.7);
        let (from, to) = ((from_seconds * rate) as usize, (to_seconds * rate) as usize);
        let level = |frequency: f64| {
            let (mut real, mut imaginary) = (0.0, 0.0);
            for place in from..to {
                let window = HALF - HALF * (TAU * (place - from) as f64 / (to - from) as f64).cos();
                let angle = TAU * frequency * place as f64 / rate;
                real += hit[place] as f64 * window * angle.cos();
                imaginary += hit[place] as f64 * window * angle.sin();
            }
            (real * real + imaginary * imaginary).sqrt()
        };
        let quietest_db = -60.0;
        for harmonic in [SECOND_HARMONIC, THIRD_HARMONIC] {
            let below = DECIBELS_A_DECADE * (level(fundamental * harmonic) / level(fundamental)).log10();
            assert!(below < quietest_db, "harmonic {harmonic} at {below} dB");
        }
        assert!(hit.len() as f64 / rate > 1.0, "a long Decay rings over a second");
    }
}
