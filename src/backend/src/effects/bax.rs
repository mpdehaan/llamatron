// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Bax, a tone control after Peter Baxandall's published circuit of 1952: a gentle shelf of 6 dB an octave under its
//! bass turnover and another over its treble turnover, each lifting or cutting by its own number of decibels.

use crate::dsp::{flushed, HIGHEST_SHARE};
use crate::protocol::values::number;
use llamatron_names::spec;
use rmpv::Value;
use std::f64::consts::PI;

/// Where Bax's shelves turn over, in hertz, fixed as on a hi-fi tone control.
const BASS_TURNOVER_HERTZ: f64 = 100.0;
const TREBLE_TURNOVER_HERTZ: f64 = 10_000.0;
/// Decibels to a gain: twenty to a power of ten.
pub(crate) const DECIBELS_PER_DECADE: f64 = 20.0;

/// Bax's two shelves, one after the other, the bass's and the treble's.
pub struct Bax {
    bass: Shelf,
    treble: Shelf,
}

impl Bax {
    /// Bax from its spec: its Bass and Treble in decibels, at a sample rate.
    pub fn compiled(spec: &Value, rate: f64) -> Bax {
        Bax {
            bass: Shelf::new(number(spec, spec::BASS, 0.0), BASS_TURNOVER_HERTZ, End::Under, rate),
            treble: Shelf::new(number(spec, spec::TREBLE, 0.0), TREBLE_TURNOVER_HERTZ, End::Over, rate),
        }
    }

    /// One sample through both shelves.
    #[inline]
    pub fn process(&mut self, input: f64) -> f64 {
        self.treble.process(self.bass.process(input))
    }

    /// Back to rest.
    pub fn reset(&mut self) {
        self.bass.reset();
        self.treble.reset();
    }
}

/// One of Bax's shelves: a first-order filter's two feed-forward coefficients and its feedback, with its last input
/// and output.
struct Shelf {
    forward: f64,
    forward_last: f64,
    back: f64,
    last_in: f64,
    last_out: f64,
}

/// Which end a shelf lifts or cuts: what lies under its turnover, or over it.
#[derive(Clone, Copy, PartialEq, Eq)]
enum End {
    Under,
    Over,
}

/// The circuit's squared gain at some hertz: one end lifted or cut by a gain, turning over at a cutoff, as a gentle
/// shelf of 6 dB an octave.
fn circuit_power(hertz: f64, gain: f64, cutoff: f64, end: End) -> f64 {
    let ratio = hertz / cutoff;
    // The shelf is 1 + (gain - 1) times the share past the turnover: s/(s + c) over it, c/(s + c) under it.
    let (real, imaginary) = match end {
        End::Over => (ratio * ratio, ratio),
        End::Under => (1.0, -ratio),
    };
    let size = 1.0 + ratio * ratio;
    let (past_real, past_imaginary) = (real / size, imaginary / size);
    let response_real = 1.0 + (gain - 1.0) * past_real;
    let response_imaginary = (gain - 1.0) * past_imaginary;
    response_real * response_real + response_imaginary * response_imaginary
}

impl Shelf {
    /// A shelf turning over at some hertz, lifting or cutting one end by some decibels. A cut moves the turnover by the
    /// cut's own gain, so that it is the exact mirror of a lift of as many decibels, as deep and turning at the same
    /// place, rather than a shallower cut.
    // The filter's level is matched to the circuit's at the bottom of the band, at the turnover and at the top, rather
    // than warped by the bilinear transform, which would squeeze the circuit's whole treble into the band and lift too
    // much near its top: after Vicanek, "Matched One-Pole Digital Shelving Filters" (2016). The design's working is our
    // own: a first-order filter's squared level is (B0 + B1 cos w)/(A0 + A1 cos w), and the three levels make a
    // quadratic for its feedback whose roots multiply to one, the stable one taken.
    fn new(decibels: f64, hertz: f64, end: End, rate: f64) -> Shelf {
        let gain = 10f64.powf(decibels / DECIBELS_PER_DECADE);
        let cutoff = match (gain < 1.0, end) {
            (false, _) => hertz,
            (true, End::Under) => hertz / gain,
            (true, End::Over) => hertz * gain,
        };
        let matched = cutoff.min(HIGHEST_SHARE * rate);
        let bottom = circuit_power(0.0, gain, cutoff, end);
        let top = circuit_power(rate / 2.0, gain, cutoff, end);
        let middle = circuit_power(matched, gain, cutoff, end);
        let cosine = (2.0 * PI * matched / rate).cos();
        let (low_share, high_share) = ((1.0 + cosine) / 2.0, (1.0 - cosine) / 2.0);
        let outer = bottom * low_share + top * high_share - middle;
        let inner = 2.0 * (bottom * low_share - top * high_share - middle * cosine);
        let back = if outer.abs() < 1e-12 {
            0.0
        } else {
            let root = (inner * inner - 4.0 * outer * outer).max(0.0).sqrt();
            let first = (-inner + root) / (2.0 * outer);
            if first.abs() <= 1.0 {
                first
            } else {
                1.0 / first
            }
        };
        let at_bottom = bottom.sqrt() * (1.0 + back);
        let at_top = top.sqrt() * (1.0 - back);
        Shelf {
            forward: (at_bottom + at_top) / 2.0,
            forward_last: (at_bottom - at_top) / 2.0,
            back,
            last_in: 0.0,
            last_out: 0.0,
        }
    }

    /// One sample through the shelf.
    #[inline]
    fn process(&mut self, input: f64) -> f64 {
        let out = self.forward * input + self.forward_last * self.last_in - self.back * self.last_out;
        self.last_in = input;
        self.last_out = flushed(out);
        out
    }

    /// Back to rest.
    fn reset(&mut self) {
        self.last_in = 0.0;
        self.last_out = 0.0;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const RATE: f64 = 48_000.0;

    /// The level of a steady sine at some hertz through a Bax, once its shelves have settled, against the sine's own.
    fn through_bax(bass: f64, treble: f64, hertz: f64) -> f64 {
        let spec = Value::Map(vec![(spec::BASS.into(), bass.into()), (spec::TREBLE.into(), treble.into())]);
        let mut bax = Bax::compiled(&spec, RATE);
        let samples = 48_000;
        let input: Vec<f64> = (0..samples).map(|place| 0.5 * (2.0 * PI * hertz * place as f64 / RATE).sin()).collect();
        let output: Vec<f64> = input.iter().map(|sample| bax.process(*sample)).collect();
        let before: f64 = input[samples / 2..].iter().map(|sample| sample.powi(2)).sum();
        let after: f64 = output[samples / 2..].iter().map(|sample| sample.powi(2)).sum();
        DECIBELS_PER_DECADE / 2.0 * (after / before).log10()
    }

    /// Bax at 0 dB leaves the sound as it is, and its shelves follow the circuit's own level across the band, to within a
    /// third of a decibel at their deepest, lifting or cutting either end, even near the top of the band.
    #[test]
    fn bax_follows_the_circuits_level_to_the_top_of_the_band() {
        let middle = 1_000.0;
        assert!(through_bax(0.0, 0.0, middle).abs() < 0.01, "Bax at 0 dB leaves the sound alone");
        let near = 0.35;
        for decibels in [15.0, 6.0, -6.0, -15.0] {
            for hertz in [200.0, 2_000.0, 5_000.0, 10_000.0, 15_000.0, 20_000.0] {
                let gain = 10f64.powf(decibels / DECIBELS_PER_DECADE);
                let cutoff = if gain < 1.0 { TREBLE_TURNOVER_HERTZ * gain } else { TREBLE_TURNOVER_HERTZ };
                let circuit = 10.0 * circuit_power(hertz, gain, cutoff, End::Over).log10();
                let heard = through_bax(0.0, decibels, hertz);
                assert!((heard - circuit).abs() < near, "treble {decibels} at {hertz}: {heard} against {circuit}");
            }
            for hertz in [30.0, 100.0, 400.0, 2_000.0] {
                let gain = 10f64.powf(decibels / DECIBELS_PER_DECADE);
                let cutoff = if gain < 1.0 { BASS_TURNOVER_HERTZ / gain } else { BASS_TURNOVER_HERTZ };
                let circuit = 10.0 * circuit_power(hertz, gain, cutoff, End::Under).log10();
                let heard = through_bax(decibels, 0.0, hertz);
                assert!((heard - circuit).abs() < near, "bass {decibels} at {hertz}: {heard} against {circuit}");
            }
        }
    }
}
