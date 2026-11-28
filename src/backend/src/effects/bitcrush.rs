// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Bitcrush: each sample held for as long as its Rate gives, the hold falling between samples where the rate puts it and
//! its step smoothed, then rounded to a converter's codes for its Bits, with triangular dither before the rounding when
//! asked.

use crate::dsp::blep;
use crate::protocol::values::{number, truth};
use llamatron_names::spec;
use rmpv::Value;

use crate::dsp::{OCTAVE, SHARE_BITS, SHARE_SHIFT, XORSHIFT_SHIFTS};
/// From this many bits on, Bitcrush leaves the level alone.
const MOST_CRUSHED_BITS: f64 = 16.0;

/// The bits a Bitcrush keeps where its spec names none.
const DEFAULT_BITS: f64 = 16.0;

/// Where Bitcrush's dither starts, the same every playing.
const DITHER_SEED: u64 = crate::dsp::GOLDEN_GAMMA;

/// Triangular noise from -1 to 1, the sum of two uniform draws, from a seeded xorshift.
#[inline]
fn dither_noise(state: &mut u64) -> f64 {
    let mut draw = || {
        let [first, second, third] = XORSHIFT_SHIFTS;
        *state ^= *state << first;
        *state ^= *state >> second;
        *state ^= *state << third;
        (*state >> SHARE_SHIFT) as f64 / (1u64 << SHARE_BITS) as f64
    };
    draw() + draw() - 1.0
}

/// Bitcrush's settings and what it keeps from sample to sample.
pub struct Bitcrush {
    /// Half the converter's codes, 0 for no rounding.
    levels: f64,
    /// Whether triangular noise of one code each way is added before the rounding, and its seeded state.
    dither: bool,
    noise: u64,
    /// The hold's rate as a share of the sample rate, 0 for no hold, and where the hold stands in its cycle.
    step: f64,
    phase: f64,
    held: f64,
    /// The input a sample before, from which a hold falling between samples takes its value.
    previous: f64,
    /// The share of a hold's step smoothing owed to the next sample.
    next: f64,
}

impl Bitcrush {
    /// Bitcrush from its spec: its Bits, Dither and Rate in hertz, at a sample rate.
    pub fn compiled(spec: &Value, rate: f64) -> Bitcrush {
        let bits = number(spec, spec::BITS, DEFAULT_BITS);
        let hold_rate = number(spec, spec::RATE, 0.0);
        Bitcrush {
            levels: if bits < MOST_CRUSHED_BITS { OCTAVE.powf(bits - 1.0) } else { 0.0 },
            dither: truth(spec, spec::DITHER, false),
            noise: DITHER_SEED,
            step: if hold_rate > 0.0 && hold_rate < rate { hold_rate / rate } else { 0.0 },
            phase: 0.0,
            held: 0.0,
            previous: 0.0,
            next: 0.0,
        }
    }

    /// One sample crushed.
    #[inline]
    pub fn process(&mut self, dry: f64) -> f64 {
        let mut wet = dry;
        if self.step > 0.0 {
            // The hold falls where its rate puts it, between samples, taking the input as it was at that
            // moment, and its step is smoothed over this sample and the next, so that any Rate stays in tune.
            // After Plaits' SampleRateReducer (plaits/dsp/fx/sample_rate_reducer.h, Emilie Gillet, MIT); our
            // own implementation.
            let mut this = self.next;
            self.next = 0.0;
            self.phase += self.step;
            if self.phase >= 1.0 {
                self.phase -= 1.0;
                let after = self.phase / self.step;
                let fresh = self.previous + (dry - self.previous) * (1.0 - after);
                let jump = fresh - self.held;
                this += jump * blep::this_sample(after);
                self.next += jump * blep::next_sample(after);
                self.held = fresh;
            }
            self.next += self.held;
            self.previous = dry;
            wet = this;
        }
        if self.levels > 0.0 {
            // A converter of n bits has 2^n codes, two's complement, from -2^(n-1) to 2^(n-1) - 1, so that
            // silence stays silent and one bit gives two levels.
            // Dither adds triangular noise of one code each way before the rounding, so that a quiet sound
            // sinks into a soft hiss rather than into silence or a buzz that follows it.
            let shaken = if self.dither {
                wet * self.levels + dither_noise(&mut self.noise)
            } else {
                wet * self.levels
            };
            wet = shaken.round().clamp(-self.levels, self.levels - 1.0) / self.levels;
        }
        wet
    }

    /// Back to rest.
    pub fn reset(&mut self) {
        self.phase = 0.0;
        self.held = 0.0;
        self.previous = 0.0;
        self.next = 0.0;
    }
}
