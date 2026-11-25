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
use std::f64::consts::PI;
use std::sync::Arc;

const MIDDLE_C: f64 = 60.0;
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

/// The knobs as shares from 0 to 1, and what the note brings.
struct Strike {
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
pub fn render_hit(machine: &str, knobs: &[f64], pitch: f64, velocity: f64, rate: f64) -> Hit {
    let knob = |place: usize| knobs.get(place).copied().unwrap_or(64.0) / KNOB_TOP;
    let strike = Strike {
        pitch: knob(0),
        decay: knob(1),
        color: knob(2),
        shape: knob(3),
        sweep: knob(4),
        tuning: 2f64.powf((pitch - MIDDLE_C) / 12.0),
        hardness: velocity / 127.0,
        rate,
    };
    let whole: Vec<String> = knobs.iter().map(|knob| format!("{}", *knob as i64)).collect();
    let seed = dsp::crc32(format!("{machine}:{}:{pitch}:{velocity}", whole.join(",")).as_bytes());
    let mut noise = Random::new(seed as u64);
    let made = match machine {
        "hard_kick" => hard_kick(&strike, &mut noise),
        "synth_kick" => synth_kick(&strike),
        "snare" => snare(&strike, &mut noise),
        "clap" => clap(&strike, &mut noise),
        "rim" => rim(&strike),
        "hats" => hats(&strike, &mut noise),
        "cowbell" => cowbell(&strike),
        "acoustic_tom" => acoustic_tom(&strike, &mut noise),
        "karplus_drum" => karplus_drum(&strike, &mut noise),
        _ => kick(&strike, &mut noise),
    };
    Arc::new(finished(made, rate))
}

/// A hit high-passed against DC, faded where it falls silent, at its peak gain.
fn finished(mut hit: Vec<f64>, rate: f64) -> Vec<f32> {
    dsp::filtered(&mut [Biquad::high_pass(DC_BLOCK_HZ, BUTTERWORTH_Q, rate)], &mut hit);
    let loudest = hit.iter().fold(0.0_f64, |most, sample| most.max(sample.abs())).max(1e-12);
    let floor = 10f64.powf(SILENT_DB / 20.0) * loudest;
    let end = hit.iter().rposition(|sample| sample.abs() > floor).map(|place| place + 1).unwrap_or(hit.len());
    hit.truncate(end);
    let fade = ((END_FADE_SECONDS * rate) as usize).min(end);
    for place in 0..fade {
        hit[end - fade + place] *= 1.0 - place as f64 / (fade.max(2) - 1) as f64;
    }
    let peak = hit.iter().fold(0.0_f64, |most, sample| most.max(sample.abs()));
    let gain = if peak > 0.0 { 10f64.powf(-3.0 / 20.0) / peak } else { 0.0 };
    hit.iter().map(|sample| (sample * gain) as f32).collect()
}

fn length(seconds: f64, rate: f64) -> usize {
    ((seconds * 1.2 + 0.01).min(LONGEST_HIT_SECONDS) * rate) as usize
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
        self.phase += 2.0 * PI * frequency / self.rate;
        self.phase
    }
}

fn clip(body: &mut [f64], gain: f64) {
    let scale = 1.0 / gain.tanh();
    for sample in body.iter_mut() {
        let mut clipped = (gain * *sample).tanh() * scale;
        if gain > 8.0 {
            clipped = (clipped * 1.1).clamp(-1.0, 1.0);
        }
        *sample = clipped;
    }
}

fn click(body: &mut [f64], rate: f64, level: f64) {
    let width = ((0.001 * rate) as usize).max(1);
    let mut click = vec![0.0; body.len().min(width * 8)];
    for (place, sample) in click.iter_mut().enumerate().take(width) {
        *sample = level * 0.5 * (1.0 + (PI * place as f64 / (width.max(2) - 1) as f64).cos());
    }
    dsp::filtered(&mut [Biquad::high_pass(1000.0, BUTTERWORTH_Q, rate)], &mut click);
    for (sample, added) in body.iter_mut().zip(click) {
        *sample += added;
    }
}

fn noise_burst(body: &mut [f64], noise: &mut Random, rate: f64, level: f64, decay: f64, centre: f64) {
    if level <= 0.0 {
        return;
    }
    let mut burst: Vec<f64> = (0..body.len())
        .map(|place| noise.normal() * (-(place as f64 / rate) / decay).exp() * level)
        .collect();
    dsp::filtered(&mut band_pass_pair(centre, 0.7, rate), &mut burst);
    for (sample, added) in body.iter_mut().zip(burst) {
        *sample += added;
    }
}

fn kick(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let f0 = 30.0 * 2f64.powf(3.0 * strike.pitch) * strike.tuning;
    let decay = 0.06 * 50f64.powf(strike.decay);
    let drop = 15.0 * strike.sweep.powf(1.5);
    let tau = 0.004 + 0.056 * strike.sweep.powi(2);
    let harmonics = ((strike.color - 0.66) / 0.34).max(0.0);
    let mut phase = Phase::new(rate);
    let mut body: Vec<f64> = (0..length(decay, rate))
        .map(|place| {
            let t = place as f64 / rate;
            let angle = phase.next(f0 * (1.0 + drop * (-t / tau).exp()));
            (angle.sin() + harmonics / 2.0 * (2.0 * angle).sin() + harmonics / 4.0 * (3.0 * angle).sin()) * (-T60 * t / decay).exp()
        })
        .collect();
    click(&mut body, rate, (strike.color / 0.33).min(1.0) * (0.5 + 0.5 * strike.hardness));
    noise_burst(&mut body, noise, rate, ((strike.color - 0.33) / 0.33).clamp(0.0, 1.0) * 0.3, 0.004, 3000.0);
    clip(&mut body, 1.0 + 19.0 * strike.shape.powi(2));
    body
}

fn hard_kick(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let f0 = 35.0 * (200.0f64 / 35.0).powf(strike.pitch) * strike.tuning;
    let decay = 0.06 * 30f64.powf(strike.decay);
    let hold = 0.15 * strike.shape.powi(2);
    let sweep = 12.0 * strike.sweep.powf(1.5);
    let tau = 0.004 + 0.04 * strike.sweep.powi(2);
    let mut phase = Phase::new(rate);
    let tick = (0.0003 * rate) as usize;
    let mut body: Vec<f64> = (0..length(decay + hold, rate))
        .map(|place| {
            let t = place as f64 / rate;
            let level = if t < hold { 1.0 } else { (-T60 * (t - hold) / decay).exp() };
            let mut sample = phase.next(f0 * (1.0 + sweep * (-t / tau).exp())).sin() * level;
            if place < tick {
                sample += strike.color * (0.5 + 0.5 * strike.hardness);
            }
            sample
        })
        .collect();
    noise_burst(&mut body, noise, rate, 0.06 + 0.2 * strike.color, 0.01, 3000.0);
    clip(&mut body, 2.0);
    body
}

fn synth_kick(strike: &Strike) -> Vec<f64> {
    let rate = strike.rate;
    let f0 = 30.0 * (200.0f64 / 30.0).powf(strike.pitch) * strike.tuning;
    let decay = 0.04 * 50f64.powf(strike.decay);
    let octaves = 5.0 * strike.sweep;
    let tau = 0.005 + 0.075 * strike.sweep.powi(2);
    let curve = 1.0 - 0.6 * (strike.shape / 0.5).min(1.0);
    let lowest = (4.0 * f0).max(300.0);
    let mut phase = Phase::new(rate);
    let mut filter = Biquad::low_pass(4000.0, BUTTERWORTH_Q, rate);
    let mut body = Vec::with_capacity(length(decay, rate));
    for place in 0..length(decay, rate) {
        let t = place as f64 / rate;
        let frequency = f0 * 2f64.powf(octaves * (-t / tau).exp());
        let angle = phase.next(frequency);
        if place % 64 == 0 {
            // The low pass falls with the pitch envelope, its coefficients moved every 64 samples, its state kept.
            let cutoff = lowest + (4000.0 - lowest) * (-t / tau).exp();
            let moved = Biquad::low_pass(cutoff, BUTTERWORTH_Q, rate);
            filter = Biquad {
                s1: filter.s1,
                s2: filter.s2,
                ..moved
            };
        }
        let wave = morphed(angle, frequency, strike.color, rate) * (-T60 * t / decay).exp().powf(curve);
        body.push(filter.process(wave) * (0.8 + 0.2 * strike.hardness));
    }
    clip(&mut body, 1.0 + 9.0 * ((strike.shape - 0.5) / 0.5).max(0.0));
    body
}

/// A wave morphing from a sine at Color 0 through a triangle to a square at full Color, of odd harmonics under 8 kHz.
fn morphed(angle: f64, frequency: f64, color: f64, rate: f64) -> f64 {
    let mut wave = angle.sin();
    if color <= 0.0 {
        return wave;
    }
    for number in [3.0, 5.0, 7.0, 9.0, 11.0, 13.0_f64] {
        if frequency * number >= 8000.0_f64.min(rate * 0.45) {
            break;
        }
        let sign = if ((number as i64 - 1) / 2) % 2 == 0 { 1.0 } else { -1.0 };
        let triangle = sign / (number * number);
        let weight = triangle * (color * 2.0).min(1.0) + (1.0 / number - triangle) * (color * 2.0 - 1.0).max(0.0);
        wave += weight * (number * angle).sin();
    }
    wave
}

fn snare(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let f1 = 120.0 * 4f64.powf(strike.pitch) * strike.tuning;
    let f2 = f1 * 1.47 * (1.0 + 0.04 * strike.color);
    let decay = 0.06 * 15f64.powf(strike.decay);
    let count = length(decay, rate);
    let mut rattle: Vec<f64> = (0..count).map(|_| noise.normal()).collect();
    dsp::filtered(&mut [Biquad::high_pass(600.0 + 3400.0 * strike.color, BUTTERWORTH_Q, rate)], &mut rattle);
    let (mut first, mut second) = (Phase::new(rate), Phase::new(rate));
    let mut body: Vec<f64> = rattle
        .iter()
        .enumerate()
        .map(|(place, rattled)| {
            let t = place as f64 / rate;
            let bump = 1.0 + strike.sweep * (-t / 0.008).exp();
            let tones = (triangle(first.next(f1 * bump)) + triangle(second.next(f2 * bump))) * (-T60 * t / (0.35 * decay)).exp();
            let snap = if t < 0.003 { 2.0 } else { 1.0 } * (-T60 * t / decay).exp();
            tones * (1.0 - strike.shape) * 0.6 + rattled * snap * (0.6 + 0.4 * strike.hardness) * strike.shape
        })
        .collect();
    clip(&mut body, 3.0);
    body
}

fn triangle(angle: f64) -> f64 {
    2.0 / PI * angle.sin().asin()
}

fn clap(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let centre = (700.0 * 4f64.powf(strike.pitch) * strike.tuning).min(rate * 0.45);
    let decay = 0.08 * 15f64.powf(strike.decay);
    let bursts = 3 + (3.0 * strike.color).round() as usize;
    let spacing = 0.014 - 0.007 * strike.color;
    let count = length(bursts as f64 * spacing + decay, rate);
    let starts: Vec<f64> = (0..bursts).map(|burst| burst as f64 * spacing + noise.between(0.0, 0.001)).collect();
    let last = (bursts - 1) as f64 * spacing;
    let tail_level = 10f64.powf((-30.0 + 30.0 * strike.shape) / 20.0);
    let quick = 0.006 - 0.004 * strike.hardness;
    let mut body: Vec<f64> = (0..count)
        .map(|place| {
            let t = place as f64 / rate;
            let mut shape: f64 = starts
                .iter()
                .filter(|start| t >= **start)
                .map(|start| ((t - start) / 0.0015).min(1.0) * (-(t - start) / quick).exp())
                .sum();
            if t >= last {
                shape += (-T60 * (t - last) / decay).exp() * tail_level;
            }
            noise.normal() * shape
        })
        .collect();
    dsp::filtered(&mut band_pass_pair(centre * (1.0 + 0.3 * strike.sweep), 2.0, rate), &mut body);
    body
}

fn rim(strike: &Strike) -> Vec<f64> {
    let rate = strike.rate;
    let frequency = 250.0 * (900.0f64 / 250.0).powf(strike.pitch) * strike.tuning;
    let factor = 0.4 * 10f64.powf(strike.decay);
    let (mut low, mut high) = (Phase::new(rate), Phase::new(rate));
    let mut body: Vec<f64> = (0..length(0.05 * factor, rate))
        .map(|place| {
            let t = place as f64 / rate;
            let drop = 1.0 - 0.15 * strike.sweep * (1.0 - (-t / 0.005).exp());
            let lower = low.next(frequency * drop).sin() * (-T60 * t / (0.025 * factor)).exp();
            let upper = high.next(frequency * 3.66 * drop).sin() * (-T60 * t / (0.012 * factor)).exp();
            lower * (1.0 - strike.color * 0.5) + upper * (0.3 + 0.7 * strike.color)
        })
        .collect();
    click(&mut body, rate, 0.4 + 0.4 * strike.hardness);
    clip(&mut body, 1.0 + 11.0 * strike.shape);
    body
}

fn hats(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let scale = 0.5 * 4f64.powf(strike.pitch) * strike.tuning;
    let decay = 0.015 * 100f64.powf(strike.decay);
    let count = length(decay, rate);
    // Six squares in clashing ratios, naive and so a little aliased, as the digital edge of the classic circuit has it.
    let mut source: Vec<f64> = (0..count)
        .map(|place| {
            let t = place as f64 / rate;
            let metal: f64 = HAT_PITCHES.iter().map(|pitch| (2.0 * PI * pitch * scale * t).sin().signum()).sum::<f64>() / HAT_PITCHES.len() as f64;
            metal * strike.color + noise.normal() * 0.4 * (1.0 - strike.color)
        })
        .collect();
    let band = band_pass_pair((8000.0 * (1.0 - 0.3 * strike.sweep)).min(rate * 0.45), 1.5 + 2.5 * strike.shape, rate);
    let [first, second] = band;
    dsp::filtered(
        &mut [first, second, Biquad::high_pass(6000.0_f64.min(rate * 0.4), BUTTERWORTH_Q, rate)],
        &mut source,
    );
    for (place, sample) in source.iter_mut().enumerate() {
        let t = place as f64 / rate;
        let gap = if t > 0.002 && t < 0.006 { 1.0 - 0.75 * strike.shape } else { 1.0 };
        *sample *= (t / 0.0005).min(1.0) * (-T60 * t / decay).exp() * gap * (0.7 + 0.3 * strike.hardness);
    }
    source
}

fn cowbell(strike: &Strike) -> Vec<f64> {
    let rate = strike.rate;
    let frequency = 300.0 * (1100.0f64 / 300.0).powf(strike.pitch) * strike.tuning;
    let decay = 0.1 * 12f64.powf(strike.decay);
    let (mut low, mut high) = (Phase::new(rate), Phase::new(rate));
    let mut squares: Vec<f64> = (0..length(decay, rate))
        .map(|place| {
            let bump = 1.0 + 0.3 * strike.sweep * (-(place as f64 / rate) / 0.006).exp();
            low.next(frequency * bump).sin().signum() + high.next(frequency * 1.48 * bump).sin().signum()
        })
        .collect();
    let [first, second] = band_pass_pair((2.6 * frequency).min(rate * 0.45), 3.0, rate);
    dsp::filtered(&mut [first, second], &mut squares);
    let floor = 0.2 + 0.6 * strike.shape;
    for (place, sample) in squares.iter_mut().enumerate() {
        let t = place as f64 / rate;
        *sample *= (1.0 - floor) * (-T60 * t / 0.03).exp() + floor * (-T60 * t / decay).exp();
    }
    dsp::filtered(
        &mut [Biquad::low_pass((4000.0 - 2500.0 * strike.color).max(20.0), BUTTERWORTH_Q, rate)],
        &mut squares,
    );
    for sample in squares.iter_mut() {
        *sample *= 0.7 + 0.3 * strike.hardness;
    }
    clip(&mut squares, 1.0 + 2.0 * strike.color);
    squares
}

/// A struck circular membrane: its modes at the Bessel ratios, each rung by where it is struck (Shape, from the centre to
/// the edge) and how hard the mallet is (Color and the velocity, a hard mallet's short contact ringing the high modes), each
/// fading faster the higher it is, the tension gliding down after a hard hit as a real head's does, and the shell's noise.
fn acoustic_tom(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let f0 = 60.0 * (400.0f64 / 60.0).powf(strike.pitch) * strike.tuning;
    let decay = 0.1 * 25f64.powf(strike.decay);
    let count = length(decay, rate);
    let width = 0.004 - 0.0037 * (strike.color + 0.2 * strike.hardness).min(1.0);
    let mut body = vec![0.0; count];
    for ratio in MEMBRANE_RATIOS {
        let frequency = f0 * ratio;
        if frequency >= rate * 0.45 {
            continue;
        }
        let centre = if CENTER_MODES.contains(&ratio) { 1.0 } else { 0.15 };
        let amplitude = (centre * (1.0 - strike.shape) + strike.shape) / (1.0 + (frequency * width * 2.0).powi(2));
        let mode_decay = decay / (1.0 + 0.6 * (ratio - 1.0));
        let mut phase = Phase::new(rate);
        for (place, sample) in body.iter_mut().enumerate() {
            let t = place as f64 / rate;
            let glide = 1.0 + 0.08 * strike.sweep * strike.hardness * (-t / 0.04).exp();
            *sample += amplitude * phase.next(frequency * glide).sin() * (-T60 * t / mode_decay).exp();
        }
    }
    let mut shell: Vec<f64> = (0..count).map(|_| noise.normal()).collect();
    let [first, second] = band_pass_pair((5.0 * f0).min(rate * 0.45), 1.0, rate);
    dsp::filtered(&mut [first, second], &mut shell);
    for (place, (sample, rattle)) in body.iter_mut().zip(shell).enumerate() {
        *sample += rattle * (-T60 * (place as f64 / rate) / 0.2).exp() * 0.03;
    }
    body
}

/// Karplus and Strong's drum, a waveguide: a burst of noise circulating in a delay line a period long, each pass averaged
/// with its neighbour, which dulls and fades it, and each sample's sign flipped at random by Shape, which turns a plucked
/// string into a drum; Color brightens the burst and the averaging, Sweep drops the pitch at the start.
fn karplus_drum(strike: &Strike, noise: &mut Random) -> Vec<f64> {
    let rate = strike.rate;
    let frequency = 50.0 * 16f64.powf(strike.pitch) * strike.tuning;
    let decay = 0.05 * 40f64.powf(strike.decay);
    let total = length(decay, rate);
    let period = ((rate / frequency).round() as usize).max(2);
    let mut line: Vec<f64> = (0..period).map(|_| noise.normal()).collect();
    if strike.color < 1.0 {
        let cutoff = (500.0 + 15000.0 * strike.color * (0.6 + 0.4 * strike.hardness)).min(rate * 0.45);
        dsp::filtered(&mut [Biquad::low_pass(cutoff, BUTTERWORTH_Q, rate)], &mut line);
    }
    let loss = 10f64.powf(-3.0 * period as f64 / (decay * rate));
    let blend = 1.0 - strike.shape * 0.5;
    let bright = 0.5 + 0.45 * strike.color;
    let mut out = Vec::with_capacity(total);
    while out.len() < total {
        let since = out.len() as f64 / rate;
        let length = ((period as f64 / (1.0 + strike.sweep * (-since / 0.03).exp())).round() as usize).max(2);
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

    const MACHINES: [&str; 10] = [
        "kick",
        "hard_kick",
        "synth_kick",
        "snare",
        "clap",
        "rim",
        "hats",
        "cowbell",
        "acoustic_tom",
        "karplus_drum",
    ];

    #[test]
    fn every_machine_renders_a_finite_hit_peaking_at_minus_three_decibels() {
        for machine in MACHINES {
            let hit = render_hit(machine, &[64.0; 5], 60.0, 100.0, 48000.0);
            assert!(hit.len() > 100, "{machine}");
            let peak = hit.iter().fold(0.0_f32, |most, sample| most.max(sample.abs()));
            assert!(hit.iter().all(|sample| sample.is_finite()), "{machine}");
            assert!((peak - 0.7079).abs() < 0.01, "{machine} {peak}");
        }
    }

    #[test]
    fn a_hit_renders_the_same_every_time() {
        assert_eq!(
            render_hit("snare", &[64.0; 5], 62.0, 90.0, 44100.0),
            render_hit("snare", &[64.0; 5], 62.0, 90.0, 44100.0)
        );
    }
}
