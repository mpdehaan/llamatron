// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The curves several parts saturate through, and their anti-aliased forms: the log of the hyperbolic cosine, the
//! antiderivative of tanh, a tanh averaged over each sample's span by it, and a cheap soft limit close to tanh.

/// Two inputs closer than this are one: the antiderivative's difference over them would lose its precision, so the
/// curve is read at their middle instead.
pub const CLOSEST_INPUTS: f64 = 1e-6;

/// The log of the hyperbolic cosine, the antiderivative of tanh, written so that it never overflows.
#[inline]
pub fn log_cosh(x: f64) -> f64 {
    let size = x.abs();
    size + (-TWICE * size).exp().ln_1p() - std::f64::consts::LN_2
}

/// Twice, by which log cosh's exponent and a span's midpoint are reckoned.
const TWICE: f64 = 2.0;
/// The soft limit's ends, where it reaches one, and its Padé coefficients: x(27 + x²)/(27 + 9x²).
pub const SOFT_LIMIT_END: f64 = 3.0;
const PADE_CONSTANT: f64 = 27.0;
const PADE_SQUARE: f64 = 9.0;

/// A soft limit close to tanh and far cheaper, x(27 + x²)/(27 + 9x²), held at its ends past three, where it reaches one.
// After stmlib's SoftLimit (stmlib/dsp/dsp.h, Emilie Gillet, MIT); the implementation here is our own.
#[inline]
pub fn soft_limit(x: f64) -> f64 {
    let held = x.clamp(-SOFT_LIMIT_END, SOFT_LIMIT_END);
    let square = held * held;
    held * (PADE_CONSTANT + square) / (PADE_CONSTANT + PADE_SQUARE * square)
}

/// What the soft limit scales a value by, soft_limit(y)/y, worked out without the division, inside its ends.
#[inline]
pub fn soft_limit_share(y: f64) -> f64 {
    let square = y * y;
    (PADE_CONSTANT + square) / (PADE_CONSTANT + PADE_SQUARE * square)
}

/// A tanh whose output is its average over the span from the last input to this one, by its antiderivative, so that a
/// curve pushed hard folds far less back down; what a filter's Drive runs on.
// Antiderivative anti-aliasing after Parker, Zavalishin and Le Bivic (DAFx 2016); our own implementation.
#[derive(Clone, Copy, Debug, Default)]
pub struct SmoothTanh {
    previous: f64,
}

impl SmoothTanh {
    /// The tanh's average from the last input to this one.
    #[inline]
    pub fn process(&mut self, input: f64) -> f64 {
        let span = input - self.previous;
        let out = if span.abs() < CLOSEST_INPUTS {
            ((input + self.previous) / TWICE).tanh()
        } else {
            (log_cosh(input) - log_cosh(self.previous)) / span
        };
        self.previous = input;
        out
    }
}
