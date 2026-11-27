// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What keeps the built-in synths safe for ears and speakers whatever a patch does, with no setting that turns it off
//! (.claude/notes/synthesis/SYNTH_SAFETY.md, and the Python engine's safety.py, every check of which is kept).
//!
//! An instrument's chunk that holds a number not finite, or a peak far past anything a patch makes, is a fault: the
//! instrument is silenced and set back to rest. The output's guard then finishes the whole mix, in order:
//!
//! - anything not finite becomes silence, and the band filters start again;
//! - a fourth-order high pass at 18 Hz takes out DC and subsonic movement, a second-order low pass at 18 kHz the
//!   ultrasonic hash;
//! - a limiter looking ahead within the chunk holds every sample under -1 dB of full scale, rising back at 30 dB a second;
//! - a slow guard against sustained loudness: past -8 dBFS over about three seconds turns the whole down at 2 dB a second,
//!   by 12 dB at most, and back up at 1 dB a second;
//! - a backstop bending everything over 0.9 smoothly under 0.98;
//! - and a latch: three faults within a second, or the limiter pulling down 20 dB for half a second, fade the output to
//!   silence until the tracker's silence (Ctrl+T) clears it.

use crate::dsp::{Biquad, BUTTERWORTH_FOUR_Q, BUTTERWORTH_Q, HIGHEST_SHARE};
use crate::engine::MOST_FRAMES;

pub const RUNAWAY: f32 = 16.0;
const LOWEST_KEPT: f64 = 18.0;
const HIGHEST_KEPT: f64 = 18000.0;
const CEILING: f64 = 0.891;
const RELEASE_DB_PER_SECOND: f64 = 30.0;
const LOUDNESS_SECONDS: f64 = 3.0;
const LOUDEST: f64 = 0.158_489_319_246_111_35;
const TURN_DOWN_DB_PER_SECOND: f64 = 2.0;
const TURN_UP_DB_PER_SECOND: f64 = 1.0;
const MOST_TURNED_DOWN_DB: f64 = 12.0;
const KNEE: f64 = 0.9;
const BACKSTOP: f64 = 0.98;
const FAULTS_TO_LATCH: usize = 3;
const FAULT_WINDOW_SECONDS: f64 = 1.0;
const HARD_LIMITING_DB: f64 = 20.0;
const HARD_LIMITING_SECONDS: f64 = 0.5;
const UNMUTE_SECONDS: f64 = 0.05;

/// Whether an instrument's chunk is a fault: a number not finite, or far louder than any patch makes.
pub fn is_runaway(buffer: &[f32]) -> bool {
    buffer.iter().any(|sample| !sample.is_finite() || sample.abs() > RUNAWAY)
}

fn decibels(gain: f64) -> f64 {
    20.0 * gain.max(1e-12).log10()
}

/// The output's guard.
pub struct OutputGuard {
    sections: [Biquad; 3],
    gain: f64,
    loudness: f64,
    turned: f64,
    muted: bool,
    unmuting: f64,
    fault_times: [f64; FAULTS_TO_LATCH],
    fault_count: usize,
    hard_for: usize,
    played: usize,
    rate: f64,
    pub faults: u64,
    ahead: Vec<f64>,
    work: Vec<f64>,
}

impl OutputGuard {
    pub fn new(rate: f64) -> OutputGuard {
        let sections = [
            Biquad::high_pass(LOWEST_KEPT, BUTTERWORTH_FOUR_Q[0], rate),
            Biquad::high_pass(LOWEST_KEPT, BUTTERWORTH_FOUR_Q[1], rate),
            Biquad::low_pass(HIGHEST_KEPT.min(HIGHEST_SHARE * rate), BUTTERWORTH_Q, rate),
        ];
        OutputGuard {
            sections,
            gain: 1.0,
            loudness: 0.0,
            turned: 1.0,
            muted: false,
            unmuting: 1.0,
            fault_times: [f64::NEG_INFINITY; FAULTS_TO_LATCH],
            fault_count: 0,
            hard_for: 0,
            played: 0,
            rate,
            faults: 0,
            ahead: vec![0.0; MOST_FRAMES],
            work: vec![0.0; MOST_FRAMES],
        }
    }

    pub fn is_muted(&self) -> bool {
        self.muted
    }

    /// Clear the latch, as the tracker's silence does: the output fades back in.
    pub fn clear(&mut self) {
        if self.muted {
            self.muted = false;
            self.unmuting = 0.0;
        }
        self.fault_times = [f64::NEG_INFINITY; FAULTS_TO_LATCH];
        self.hard_for = 0;
    }

    /// Count a fault; enough of them close together latch the output silent.
    pub fn fault(&mut self) {
        self.faults += 1;
        let now = self.played as f64 / self.rate;
        self.fault_times[self.fault_count % FAULTS_TO_LATCH] = now;
        self.fault_count += 1;
        if self.fault_times.iter().all(|time| now - time < FAULT_WINDOW_SECONDS) {
            self.muted = true;
        }
    }

    /// Make a chunk of the mix safe, in place.
    pub fn guard(&mut self, mix: &mut [f32]) {
        let count = mix.len().min(MOST_FRAMES);
        self.played += count;
        if mix.iter().any(|sample| !sample.is_finite()) {
            self.fault();
            mix.fill(0.0);
            for section in self.sections.iter_mut() {
                section.reset();
            }
        }
        for place in 0..count {
            let mut sample = mix[place] as f64;
            for section in self.sections.iter_mut() {
                sample = section.process(sample);
            }
            self.work[place] = sample;
        }
        for section in self.sections.iter_mut() {
            section.flush();
        }
        self.limit(count);
        self.hold_down(count);
        for place in 0..count {
            let sample = self.work[place];
            let size = sample.abs();
            let bent = if size > KNEE {
                sample.signum() * (KNEE + (BACKSTOP - KNEE) * ((size - KNEE) / (BACKSTOP - KNEE)).tanh())
            } else {
                sample
            };
            mix[place] = bent as f32;
        }
        self.latch(&mut mix[..count]);
    }

    /// Hold the chunk under the ceiling: each sample's gain at most what every later peak of the chunk needs, ramped from
    /// the last chunk's gain and rising back in decibels.
    fn limit(&mut self, count: usize) {
        if count == 0 {
            return;
        }
        let peak = self.work[..count].iter().fold(0.0_f64, |most, sample| most.max(sample.abs()));
        if self.gain >= 1.0 && peak <= CEILING {
            self.hard_for = 0;
            return;
        }
        let mut lowest = 1.0_f64;
        for place in (0..count).rev() {
            lowest = lowest.min((CEILING / self.work[place].abs().max(1e-12)).min(1.0));
            self.ahead[place] = lowest;
        }
        let released = self.gain * 10f64.powf(RELEASE_DB_PER_SECOND * count as f64 / self.rate / 20.0);
        let end = 1.0_f64.min(released).min(self.ahead[count - 1]);
        let mut least = 1.0_f64;
        for place in 0..count {
            let ramp = if count > 1 {
                self.gain + (end - self.gain) * place as f64 / (count - 1) as f64
            } else {
                end
            };
            let gain = ramp.min(self.ahead[place]);
            least = least.min(gain);
            self.work[place] *= gain;
            if place == count - 1 {
                self.gain = gain;
            }
        }
        if decibels(least) < -HARD_LIMITING_DB {
            self.hard_for += count;
            if self.hard_for as f64 >= HARD_LIMITING_SECONDS * self.rate {
                self.muted = true;
            }
        } else {
            self.hard_for = 0;
        }
    }

    /// Turn the chunk down slowly while it has stayed far louder than music does.
    fn hold_down(&mut self, count: usize) {
        if count == 0 {
            return;
        }
        let power = self.work[..count].iter().map(|sample| sample * sample).sum::<f64>() / count as f64;
        self.loudness += (1.0 - (-(count as f64) / (LOUDNESS_SECONDS * self.rate)).exp()) * (power - self.loudness);
        let seconds = count as f64 / self.rate;
        let before = self.turned;
        if self.loudness > LOUDEST {
            self.turned = 10f64
                .powf(-MOST_TURNED_DOWN_DB / 20.0)
                .max(self.turned * 10f64.powf(-TURN_DOWN_DB_PER_SECOND * seconds / 20.0));
        } else if self.turned < 1.0 {
            self.turned = 1.0_f64.min(self.turned * 10f64.powf(TURN_UP_DB_PER_SECOND * seconds / 20.0));
        }
        if before == 1.0 && self.turned == 1.0 {
            return;
        }
        for place in 0..count {
            self.work[place] *= before + (self.turned - before) * place as f64 / count as f64;
        }
    }

    /// Fade the chunk to silence while the latch holds, and back in once cleared.
    fn latch(&mut self, mix: &mut [f32]) {
        let count = mix.len();
        if count == 0 {
            return;
        }
        if self.muted {
            let from = self.unmuting;
            for (place, sample) in mix.iter_mut().enumerate() {
                *sample *= (from * (1.0 - place as f64 / count as f64)) as f32;
            }
            self.unmuting = 0.0;
        } else if self.unmuting < 1.0 {
            let from = self.unmuting;
            let after = 1.0_f64.min(from + count as f64 / (UNMUTE_SECONDS * self.rate));
            for (place, sample) in mix.iter_mut().enumerate() {
                *sample *= (from + (after - from) * place as f64 / count as f64) as f32;
            }
            self.unmuting = after;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_full_scale_square_comes_out_under_the_ceiling() {
        let mut guard = OutputGuard::new(48000.0);
        let mut most: f32 = 0.0;
        for chunk in 0..100 {
            let mut mix: Vec<f32> = (0..128).map(|place| if (chunk * 128 + place) / 50 % 2 == 0 { 4.0 } else { -4.0 }).collect();
            guard.guard(&mut mix);
            most = mix.iter().fold(most, |most, sample| most.max(sample.abs()));
        }
        assert!(most <= BACKSTOP as f32 + 1e-6, "{most}");
    }

    #[test]
    fn three_faults_within_a_second_latch_the_output_until_cleared() {
        let mut guard = OutputGuard::new(48000.0);
        for _ in 0..3 {
            guard.fault();
        }
        assert!(guard.is_muted());
        guard.clear();
        assert!(!guard.is_muted());
    }

    #[test]
    fn a_number_not_finite_becomes_silence() {
        let mut guard = OutputGuard::new(48000.0);
        let mut mix = vec![f32::NAN; 128];
        guard.guard(&mut mix);
        assert!(mix.iter().all(|sample| *sample == 0.0));
    }
}
