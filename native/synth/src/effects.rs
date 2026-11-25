// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The effects an instrument's blocks hold, each applied to the instrument's mix a sample at a time, keeping what it
//! needs from one chunk to the next, and blended into what came before it by its Mix.
//!
//! The bitcrusher holds each sample for as long as its rate gives, then rounds to its bits. Drive shapes the mix by a
//! curve: soft and warm saturate, warm leaning to one side for even harmonics, hard clips, fold folds back past full scale
//! and wrap wraps round, the last two the harsh digital sounds of cheap grooveboxes.

use crate::value::{number, word};
use rmpv::Value;
use std::f64::consts::PI;

const MOST_GAIN: f64 = 20.0;
const MOST_FOLDING_GAIN: f64 = 4.0;
const WARM_LEAN: f64 = 0.3;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Curve {
    Soft,
    Warm,
    Hard,
    Fold,
    Wrap,
}

enum Kind {
    Bitcrush { levels: f64, step: f64, phase: f64, held: f64 },
    Drive { curve: Curve, gain: f64, scale: f64, offset: f64 },
}

pub struct Effect {
    kind: Kind,
    mix: f64,
}

/// An instrument's effects in order, from their specs.
pub fn compiled(specs: &[Value], rate: f64) -> Vec<Effect> {
    let mut effects = Vec::new();
    for spec in specs {
        let mix = number(spec, "mix", 1.0);
        let kind = match word(spec, "effect", "none") {
            "bitcrush" => bitcrush(spec, rate),
            "drive" => drive(spec),
            _ => continue,
        };
        effects.push(Effect { kind, mix });
    }
    effects
}

fn bitcrush(spec: &Value, rate: f64) -> Kind {
    let bits = number(spec, "bits", 16.0);
    let hold_rate = number(spec, "rate", 0.0);
    let levels = if bits < 16.0 { 2f64.powf(bits - 1.0) } else { 0.0 };
    let step = if hold_rate > 0.0 && hold_rate < rate { hold_rate / rate } else { 0.0 };
    Kind::Bitcrush {
        levels,
        step,
        phase: 0.0,
        held: 0.0,
    }
}

fn drive(spec: &Value) -> Kind {
    let curve = match word(spec, "curve", "soft") {
        "warm" => Curve::Warm,
        "hard" => Curve::Hard,
        "fold" => Curve::Fold,
        "wrap" => Curve::Wrap,
        _ => Curve::Soft,
    };
    let most = if matches!(curve, Curve::Fold | Curve::Wrap) {
        MOST_FOLDING_GAIN
    } else {
        MOST_GAIN
    };
    let gain = 1.0 + number(spec, "amount", 0.0) * most;
    let mut offset = 0.0;
    let mut scale = 1.0 / gain.tanh();
    if curve == Curve::Warm {
        // Leaning before the curve and taking the lean's own level away again leaves silence silent; the scale is the larger of
        // the two extremes, so that the curve reaches full scale on one side and stays under it on the other.
        offset = WARM_LEAN.tanh();
        scale = 1.0 / ((gain + WARM_LEAN).tanh() - offset).max(offset - (WARM_LEAN - gain).tanh());
    }
    Kind::Drive { curve, gain, scale, offset }
}

impl Effect {
    /// Shape a chunk of the instrument's mix in place.
    pub fn apply(&mut self, buffer: &mut [f32]) {
        let mix = self.mix;
        match &mut self.kind {
            Kind::Bitcrush { levels, step, phase, held } => {
                for sample in buffer.iter_mut() {
                    let dry = *sample as f64;
                    let mut wet = dry;
                    if *step > 0.0 {
                        let before = phase.floor();
                        *phase += *step;
                        if phase.floor() > before {
                            *held = dry;
                        }
                        if *phase >= 1.0 {
                            *phase -= 1.0;
                        }
                        wet = *held;
                    }
                    if *levels > 0.0 {
                        wet = (wet * *levels).round() / *levels;
                    }
                    *sample = (dry + (wet - dry) * mix) as f32;
                }
            }
            Kind::Drive { curve, gain, scale, offset } => {
                for sample in buffer.iter_mut() {
                    let dry = *sample as f64;
                    let driven = dry * *gain;
                    let wet = match curve {
                        Curve::Soft => driven.tanh() * *scale,
                        Curve::Warm => ((driven + WARM_LEAN).tanh() - *offset) * *scale,
                        Curve::Hard => driven.clamp(-1.0, 1.0),
                        Curve::Fold => (driven * PI / 2.0).sin(),
                        Curve::Wrap => (driven + 1.0).rem_euclid(2.0) - 1.0,
                    };
                    *sample = (dry + (wet - dry) * mix) as f32;
                }
            }
        }
    }

    /// Back to rest.
    pub fn reset(&mut self) {
        if let Kind::Bitcrush { phase, held, .. } = &mut self.kind {
            *phase = 0.0;
            *held = 0.0;
        }
    }
}
